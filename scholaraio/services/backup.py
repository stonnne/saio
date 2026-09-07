"""backup.py -- rsync-based ScholarAIO data backup."""

from __future__ import annotations

import json
import os
import shlex
import shutil
import sqlite3
import subprocess
import tempfile
import time
from collections.abc import Callable, Mapping, Sequence
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

from scholaraio import __version__
from scholaraio.core.config import BackupTargetConfig, Config

INSTANCE_BACKUP_KIND = "scholaraio-instance-backup"
INSTANCE_BACKUP_SCHEMA_VERSION = 1
INSTANCE_MANIFEST_RELATIVE_PATH = PurePosixPath(".scholaraio-control/backup-manifest.json")
SQLITE_HEADER = b"SQLite format 3\x00"
SQLITE_SUFFIXES = {".db", ".sqlite", ".sqlite3"}
SQLITE_TRANSIENT_SUFFIXES = ("-wal", "-shm", "-journal")


class BackupConfigError(ValueError):
    """Raised when backup configuration is missing or invalid."""


@dataclass
class BackupRunResult:
    """Structured result returned from a backup invocation."""

    command: list[str]
    returncode: int
    stdout: str
    stderr: str


def _resolve_target(cfg: Config, target_name: str) -> BackupTargetConfig:
    target = cfg.backup.targets.get(target_name)
    if target is None:
        raise BackupConfigError(f"unknown backup target: {target_name}")
    if not target.enabled:
        raise BackupConfigError(f"backup target is disabled: {target_name}")
    if not target.host:
        raise BackupConfigError(f"backup target {target_name!r} is missing host")
    if not target.path:
        raise BackupConfigError(f"backup target {target_name!r} is missing path")
    return target


def _resolve_identity_file(cfg: Config, identity_file: str) -> str:
    if not identity_file:
        return ""
    path = Path(identity_file).expanduser()
    if not path.is_absolute():
        path = (cfg._root / path).resolve()
    return str(path)


def _build_remote_shell_parts(cfg: Config, target: BackupTargetConfig) -> list[str]:
    parts = [cfg.backup.ssh_bin]
    keepalive_interval = min(60, cfg.backup.io_timeout_seconds)
    parts.extend(
        [
            "-o",
            f"ConnectTimeout={cfg.backup.connect_timeout_seconds}",
            "-o",
            f"ServerAliveInterval={keepalive_interval}",
            "-o",
            "ServerAliveCountMax=3",
        ]
    )
    if target.password:
        parts.extend(
            [
                "-o",
                "PreferredAuthentications=password,keyboard-interactive",
                "-o",
                "PubkeyAuthentication=no",
            ]
        )
    else:
        # Backups should fail fast instead of hanging on interactive SSH prompts.
        parts.extend(["-o", "BatchMode=yes"])
    if target.port and target.port != 22:
        parts.extend(["-p", str(target.port)])
    identity_file = _resolve_identity_file(cfg, target.identity_file)
    if identity_file:
        parts.extend(["-i", identity_file])
    return parts


def _build_remote_shell(cfg: Config, target: BackupTargetConfig) -> str:
    return shlex.join(_build_remote_shell_parts(cfg, target))


def _build_password_env(target: BackupTargetConfig) -> tuple[dict[str, str], str] | tuple[None, None]:
    if not target.password:
        return None, None

    fd, askpass_path = tempfile.mkstemp(prefix="scholaraio-backup-askpass-", text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write("#!/bin/sh\nprintf '%s\\n' \"$SCHOLARAIO_BACKUP_SSH_PASSWORD\"\n")
        os.chmod(askpass_path, 0o700)
    except Exception:
        try:
            os.unlink(askpass_path)
        except OSError:
            pass
        raise

    env = os.environ.copy()
    env.update(
        {
            "SCHOLARAIO_BACKUP_SSH_PASSWORD": target.password,
            "SSH_ASKPASS": askpass_path,
            "SSH_ASKPASS_REQUIRE": "force",
            "DISPLAY": "scholaraio-backup",
        }
    )
    return env, askpass_path


def _destination_for(target: BackupTargetConfig) -> str:
    remote = _remote_for(target)
    return f"{remote}:{target.path.rstrip('/')}/"


def _remote_for(target: BackupTargetConfig) -> str:
    return f"{target.user}@{target.host}" if target.user else target.host


def _validate_instance_target(target: BackupTargetConfig) -> None:
    if target.scope != "instance":
        raise BackupConfigError("restore requires a backup target with scope: instance")
    if target.mode != "default":
        raise BackupConfigError("instance backups require mode: default")
    if target.exclude:
        raise BackupConfigError("instance backups cannot use exclude patterns")


def _base_rsync_command(cfg: Config, target: BackupTargetConfig, *, dry_run: bool) -> list[str]:
    cmd = [
        cfg.backup.rsync_bin,
        "-a",
        "--stats",
        "--human-readable",
        f"--timeout={cfg.backup.io_timeout_seconds}",
    ]
    if target.compress:
        cmd.append("-z")
    if target.mode == "append":
        cmd.append("--append")
    elif target.mode == "append-verify":
        cmd.append("--append-verify")
    if dry_run:
        cmd.append("--dry-run")
    return cmd


def _instance_relative_path(cfg: Config, path: Path) -> Path:
    root = cfg._root.resolve()
    resolved = path.resolve()
    try:
        relative = resolved.relative_to(root)
    except ValueError as exc:
        raise BackupConfigError(f"instance backup path must be inside {root}: {resolved}") from exc
    if relative == Path("."):
        raise BackupConfigError("instance backup cannot use the entire instance root as one component")
    return relative


def _instance_component_paths(cfg: Config) -> list[Path]:
    candidates = [
        cfg._root / "config.yaml",
        cfg._root / "config.local.yaml",
        cfg.backup_source_dir,
        cfg.workspace_dir,
        cfg.published_dir,
        cfg.control_root,
    ]
    components: list[Path] = []
    seen: set[Path] = set()
    for path in candidates:
        if not path.exists():
            continue
        resolved = path.resolve()
        if resolved in seen:
            continue
        _instance_relative_path(cfg, path)
        seen.add(resolved)
        components.append(path)
    config_path = (cfg._root / "config.yaml").resolve()
    if config_path not in seen:
        raise BackupConfigError(f"instance backup requires config.yaml under {cfg._root}")
    return components


def _relative_rsync_source(cfg: Config, path: Path) -> str:
    relative = _instance_relative_path(cfg, path).as_posix()
    suffix = "/" if path.is_dir() else ""
    return f"{str(cfg._root.resolve()).rstrip('/')}/./{relative}{suffix}"


def _staged_rsync_source(snapshot_root: Path, relative_path: Path) -> str:
    if relative_path.is_absolute() or any(part in {"", ".", ".."} for part in relative_path.parts):
        raise BackupConfigError(f"unsafe SQLite snapshot path: {relative_path}")
    return f"{str(snapshot_root.resolve()).rstrip('/')}/./{relative_path.as_posix()}"


def _rsync_filter_literal(path: Path) -> str:
    value = path.as_posix().replace("\\", "\\\\")
    for character in ("*", "?", "["):
        value = value.replace(character, f"\\{character}")
    return value


def _discover_sqlite_databases(cfg: Config, components: Sequence[Path]) -> list[Path]:
    """Discover SQLite files inside instance components without following symlinks."""
    discovered: dict[Path, Path] = {}
    for component in components:
        candidates: list[Path] = []
        if component.is_dir():
            for directory, _subdirs, filenames in os.walk(component, followlinks=False):
                candidates.extend(
                    Path(directory) / filename
                    for filename in filenames
                    if Path(filename).suffix.lower() in SQLITE_SUFFIXES
                )
        elif component.suffix.lower() in SQLITE_SUFFIXES:
            candidates.append(component)

        for candidate in candidates:
            if candidate.is_symlink():
                continue
            try:
                with candidate.open("rb") as handle:
                    header = handle.read(len(SQLITE_HEADER))
            except OSError as exc:
                raise BackupConfigError(f"failed to inspect possible SQLite database {candidate}: {exc}") from exc
            if header != SQLITE_HEADER:
                continue
            relative = _instance_relative_path(cfg, candidate)
            discovered.setdefault(relative, candidate)
    return [discovered[path] for path in sorted(discovered, key=lambda item: item.as_posix())]


def _preserve_snapshot_parent_metadata(cfg: Config, source: Path, snapshot_root: Path) -> None:
    """Make staged implied directories match their live instance counterparts."""
    relative_parent = _instance_relative_path(cfg, source.parent)
    source_directory = cfg._root.resolve()
    snapshot_directory = snapshot_root.resolve()
    directory_pairs: list[tuple[Path, Path]] = []
    for part in relative_parent.parts:
        source_directory /= part
        snapshot_directory /= part
        snapshot_directory.mkdir(exist_ok=True)
        directory_pairs.append((source_directory, snapshot_directory))

    for source_directory, snapshot_directory in reversed(directory_pairs):
        source_stat = source_directory.stat()
        snapshot_stat = snapshot_directory.stat()
        expected_owner = (source_stat.st_uid, source_stat.st_gid)
        if (snapshot_stat.st_uid, snapshot_stat.st_gid) != expected_owner:
            try:
                os.chown(snapshot_directory, *expected_owner)
            except OSError as exc:
                raise BackupConfigError(
                    f"failed to preserve SQLite snapshot directory ownership for {relative_parent}: {exc}"
                ) from exc
        shutil.copystat(source_directory, snapshot_directory)


def _snapshot_sqlite_database(cfg: Config, source: Path, snapshot_root: Path, *, timeout_seconds: int) -> Path:
    relative = _instance_relative_path(cfg, source)
    destination = snapshot_root / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + timeout_seconds

    def check_deadline(_status: int, _remaining: int, _total: int) -> None:
        if time.monotonic() > deadline:
            raise TimeoutError(f"SQLite snapshot timed out after {timeout_seconds} seconds")

    try:
        source_uri = f"{source.resolve().as_uri()}?mode=ro"
        with (
            closing(sqlite3.connect(source_uri, uri=True, timeout=min(timeout_seconds, 60))) as source_conn,
            closing(sqlite3.connect(destination)) as destination_conn,
        ):
            source_conn.backup(destination_conn, pages=4096, progress=check_deadline, sleep=0.05)
            # The backup API may carry WAL journal mode into the copy.
            # Normalize the standalone artifact so it has no sidecars.
            destination_conn.execute("PRAGMA journal_mode=DELETE")
            check = destination_conn.execute("PRAGMA quick_check").fetchone()
            if check != ("ok",):
                raise sqlite3.DatabaseError(f"quick_check returned {check!r}")
        source_stat = source.stat()
        destination_stat = destination.stat()
        expected_owner = (source_stat.st_uid, source_stat.st_gid)
        if (destination_stat.st_uid, destination_stat.st_gid) != expected_owner:
            os.chown(destination, *expected_owner)
        shutil.copymode(source, destination)
        _preserve_snapshot_parent_metadata(cfg, source, snapshot_root)
    except (OSError, sqlite3.Error, TimeoutError) as exc:
        raise BackupConfigError(f"failed to create consistent SQLite snapshot for {relative}: {exc}") from exc
    return relative


def _prepare_sqlite_snapshots(
    cfg: Config,
    snapshot_root: Path,
    components: Sequence[Path],
) -> list[Path]:
    return [
        _snapshot_sqlite_database(
            cfg,
            source,
            snapshot_root,
            timeout_seconds=cfg.backup.process_timeout_seconds,
        )
        for source in _discover_sqlite_databases(cfg, components)
    ]


def _write_instance_manifest(cfg: Config, *, sqlite_databases: Sequence[Path] = ()) -> Path:
    cfg.control_root.mkdir(parents=True, exist_ok=True)
    components = _instance_component_paths(cfg)
    payload = {
        "kind": INSTANCE_BACKUP_KIND,
        "schema_version": INSTANCE_BACKUP_SCHEMA_VERSION,
        "scholaraio_version": __version__,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "sqlite_databases": [path.as_posix() for path in sqlite_databases],
        "components": [
            {
                "path": _instance_relative_path(cfg, path).as_posix(),
                "type": "directory" if path.is_dir() else "file",
            }
            for path in components
        ],
    }
    manifest_path = cfg.control_root / INSTANCE_MANIFEST_RELATIVE_PATH.name
    fd, temp_path = tempfile.mkstemp(prefix="backup-manifest-", suffix=".json", dir=cfg.control_root)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.chmod(temp_path, 0o600)
        os.replace(temp_path, manifest_path)
    except Exception:
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        raise
    return manifest_path


def build_rsync_command(
    cfg: Config,
    target_name: str,
    *,
    dry_run: bool = False,
    sqlite_snapshot_root: Path | None = None,
    sqlite_snapshot_paths: Sequence[Path] = (),
) -> list[str]:
    """Build the rsync command line for a configured backup target."""
    target = _resolve_target(cfg, target_name)
    cmd = _base_rsync_command(cfg, target, dry_run=dry_run)

    if target.scope == "instance":
        _validate_instance_target(target)
        # A restorable instance target represents the current runtime state.
        # Mirror deletions inside each component so removed papers or metadata
        # cannot reappear from stale remote files during a later restore.
        cmd.extend(["--relative", "--delete", "--delete-excluded"])
        components = _instance_component_paths(cfg)
        sqlite_paths = list(sqlite_snapshot_paths)
        if not sqlite_paths:
            sqlite_paths = [_instance_relative_path(cfg, path) for path in _discover_sqlite_databases(cfg, components)]
        for path in sqlite_paths:
            literal_path = _rsync_filter_literal(path)
            for suffix in SQLITE_TRANSIENT_SUFFIXES:
                cmd.append(f"--exclude=/{literal_path}{suffix}")
        sources: list[str] = []
        if sqlite_snapshot_root is not None:
            # Rsync keeps the first duplicate relative source path. Put staged
            # online-backup copies first so live database files never win.
            sources.extend(_staged_rsync_source(sqlite_snapshot_root, path) for path in sqlite_snapshot_paths)
        sources.extend(_relative_rsync_source(cfg, path) for path in components)
    else:
        for pattern in target.exclude:
            cmd.extend(["--exclude", pattern])
        sources = [f"{cfg.backup_source_dir}/"]
    cmd.extend(["-e", _build_remote_shell(cfg, target)])
    cmd.extend(sources)
    cmd.append(_destination_for(target))
    return cmd


def _run_command(cfg: Config, cmd: list[str], target: BackupTargetConfig) -> subprocess.CompletedProcess[str]:
    env, askpass_path = _build_password_env(target)
    run_kwargs: dict[str, Any] = {
        "check": False,
        "text": True,
        "capture_output": True,
        "timeout": cfg.backup.process_timeout_seconds,
    }
    if env is not None:
        run_kwargs["env"] = env
        run_kwargs["stdin"] = subprocess.DEVNULL
    try:
        return subprocess.run(cmd, **run_kwargs)
    except subprocess.TimeoutExpired as exc:
        program = Path(cmd[0]).name
        raise BackupConfigError(
            f"{program} timed out after {cfg.backup.process_timeout_seconds} seconds; "
            "increase backup.process_timeout_seconds if this transfer is expected to take longer"
        ) from exc
    except OSError as exc:
        detail = exc.strerror or str(exc)
        program = Path(cmd[0]).name
        raise BackupConfigError(f"failed to execute {program} {cmd[0]!r}: {detail}") from exc
    finally:
        if askpass_path:
            try:
                os.unlink(askpass_path)
            except OSError:
                pass


def run_backup(
    cfg: Config,
    target_name: str,
    *,
    dry_run: bool = False,
    on_command: Callable[[list[str]], None] | None = None,
) -> BackupRunResult:
    """Run an rsync backup for a configured target."""
    target = _resolve_target(cfg, target_name)
    if target.scope == "instance" and not dry_run:
        _validate_instance_target(target)
        components = _instance_component_paths(cfg)
        with tempfile.TemporaryDirectory(prefix="scholaraio-instance-snapshot-") as temp_dir:
            snapshot_root = Path(temp_dir)
            snapshot_paths = _prepare_sqlite_snapshots(cfg, snapshot_root, components)
            _write_instance_manifest(cfg, sqlite_databases=snapshot_paths)
            cmd = build_rsync_command(
                cfg,
                target_name,
                dry_run=False,
                sqlite_snapshot_root=snapshot_root,
                sqlite_snapshot_paths=snapshot_paths,
            )
            if on_command is not None:
                on_command(cmd)
            completed = _run_command(cfg, cmd, target)
    else:
        cmd = build_rsync_command(cfg, target_name, dry_run=dry_run)
        if on_command is not None:
            on_command(cmd)
        completed = _run_command(cfg, cmd, target)
    return BackupRunResult(
        command=cmd,
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def _remote_manifest_path(target: BackupTargetConfig) -> str:
    return f"{target.path.rstrip('/')}/{INSTANCE_MANIFEST_RELATIVE_PATH.as_posix()}"


def _validate_manifest(payload: object) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise BackupConfigError("remote backup manifest must be a JSON object")
    if payload.get("kind") != INSTANCE_BACKUP_KIND:
        raise BackupConfigError("remote target is not a ScholarAIO instance backup")
    if payload.get("schema_version") != INSTANCE_BACKUP_SCHEMA_VERSION:
        raise BackupConfigError(f"unsupported backup manifest schema: {payload.get('schema_version')!r}")
    raw_components = payload.get("components")
    if not isinstance(raw_components, list) or not raw_components:
        raise BackupConfigError("remote backup manifest has no components")

    components: list[dict[str, str]] = []
    for item in raw_components:
        if not isinstance(item, dict):
            raise BackupConfigError("remote backup manifest contains an invalid component")
        path_value = item.get("path")
        type_value = item.get("type")
        if not isinstance(path_value, str) or type_value not in {"file", "directory"}:
            raise BackupConfigError("remote backup manifest contains an invalid component")
        path = PurePosixPath(path_value)
        if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
            raise BackupConfigError(f"unsafe path in remote backup manifest: {path_value!r}")
        components.append({"path": path.as_posix(), "type": type_value})

    raw_sqlite_databases = payload.get("sqlite_databases", [])
    if not isinstance(raw_sqlite_databases, list):
        raise BackupConfigError("remote backup manifest has an invalid SQLite database list")
    sqlite_databases: list[str] = []
    for path_value in raw_sqlite_databases:
        if not isinstance(path_value, str):
            raise BackupConfigError("remote backup manifest has an invalid SQLite database path")
        path = PurePosixPath(path_value)
        if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
            raise BackupConfigError(f"unsafe SQLite path in remote backup manifest: {path_value!r}")
        sqlite_databases.append(path.as_posix())

    validated = dict(payload)
    validated["components"] = components
    validated["sqlite_databases"] = sqlite_databases
    return validated


def fetch_backup_manifest(cfg: Config, target_name: str) -> dict[str, Any]:
    """Fetch and validate the manifest for a remote instance backup."""
    target = _resolve_target(cfg, target_name)
    _validate_instance_target(target)
    remote_path = shlex.quote(_remote_manifest_path(target))
    command = [
        *_build_remote_shell_parts(cfg, target),
        _remote_for(target),
        f"cat -- {remote_path}",
    ]
    completed = _run_command(cfg, command, target)
    if completed.returncode != 0:
        detail = completed.stderr.strip() or f"ssh exit code {completed.returncode}"
        raise BackupConfigError(f"failed to read remote backup manifest: {detail}")
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise BackupConfigError("remote backup manifest is not valid JSON") from exc
    return _validate_manifest(payload)


def _restore_include_patterns(manifest: Mapping[str, Any]) -> list[str]:
    patterns: list[str] = []
    seen: set[str] = set()
    for component in manifest["components"]:
        path = PurePosixPath(component["path"])
        for index in range(1, len(path.parts)):
            parent = "/" + "/".join(path.parts[:index]) + "/"
            if parent not in seen:
                seen.add(parent)
                patterns.append(parent)
        suffix = "/***" if component["type"] == "directory" else ""
        pattern = f"/{path.as_posix()}{suffix}"
        if pattern not in seen:
            seen.add(pattern)
            patterns.append(pattern)
    return patterns


def resolve_restore_destination(destination: str | Path) -> Path:
    """Resolve and minimally validate a restore destination."""
    path = Path(destination).expanduser()
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    else:
        path = path.resolve()
    if path == Path(path.anchor):
        raise BackupConfigError("refusing to restore directly into a filesystem root")
    if path.exists() and not path.is_dir():
        raise BackupConfigError(f"restore destination is not a directory: {path}")
    return path


def _validate_restored_sqlite_databases(restore_root: Path, manifest: Mapping[str, Any]) -> None:
    root = restore_root.resolve()
    for path_value in manifest.get("sqlite_databases", []):
        relative = Path(*PurePosixPath(path_value).parts)
        database = (root / relative).resolve()
        try:
            database.relative_to(root)
        except ValueError as exc:
            raise BackupConfigError(f"restored SQLite path escapes destination: {path_value!r}") from exc
        if not database.is_file():
            raise BackupConfigError(f"restored SQLite database is missing: {relative}")
        try:
            for suffix in SQLITE_TRANSIENT_SUFFIXES:
                sidecar = database.with_name(f"{database.name}{suffix}")
                sidecar.unlink(missing_ok=True)
            source_uri = f"{database.as_uri()}?mode=ro&immutable=1"
            with closing(sqlite3.connect(source_uri, uri=True)) as connection:
                check = connection.execute("PRAGMA quick_check").fetchone()
            if check != ("ok",):
                raise sqlite3.DatabaseError(f"quick_check returned {check!r}")
        except (OSError, sqlite3.Error) as exc:
            raise BackupConfigError(f"restored SQLite database failed validation: {relative}: {exc}") from exc


def build_restore_command(
    cfg: Config,
    target_name: str,
    destination: str | Path,
    *,
    manifest: Mapping[str, Any],
    dry_run: bool = False,
) -> list[str]:
    """Build a manifest-scoped rsync restore command."""
    target = _resolve_target(cfg, target_name)
    _validate_instance_target(target)
    validated = _validate_manifest(dict(manifest))
    restore_root = resolve_restore_destination(destination)
    cmd = _base_rsync_command(cfg, target, dry_run=dry_run)
    for pattern in _restore_include_patterns(validated):
        cmd.append(f"--include={pattern}")
    cmd.append("--exclude=*")
    cmd.extend(["-e", _build_remote_shell(cfg, target)])
    cmd.append(_destination_for(target))
    cmd.append(f"{restore_root}/")
    return cmd


def run_restore(
    cfg: Config,
    target_name: str,
    destination: str | Path,
    *,
    dry_run: bool = False,
    force: bool = False,
    manifest: Mapping[str, Any] | None = None,
) -> BackupRunResult:
    """Restore a full instance backup into an empty or explicitly forced destination."""
    target = _resolve_target(cfg, target_name)
    _validate_instance_target(target)
    restore_root = resolve_restore_destination(destination)
    if not dry_run and not force and restore_root.exists() and any(restore_root.iterdir()):
        raise BackupConfigError(
            f"restore destination is not empty: {restore_root}; use --force to merge and overwrite matching files"
        )
    validated = _validate_manifest(dict(manifest)) if manifest is not None else fetch_backup_manifest(cfg, target_name)
    cmd = build_restore_command(
        cfg,
        target_name,
        restore_root,
        manifest=validated,
        dry_run=dry_run,
    )
    if not dry_run:
        restore_root.mkdir(parents=True, exist_ok=True)
    completed = _run_command(cfg, cmd, target)
    if completed.returncode == 0 and not dry_run:
        _validate_restored_sqlite_databases(restore_root, validated)
        local_config = restore_root / "config.local.yaml"
        if local_config.exists():
            local_config.chmod(0o600)
    return BackupRunResult(
        command=cmd,
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )
