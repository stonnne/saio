"""Attach-asset CLI command handler.

Converts a *supplementary* PDF that sits alongside a paper into Markdown,
producing ``<paper_dir>/<name>.md`` next to the existing ``paper.md``.

This is deliberately separate from ``attach-pdf``. That command owns the
paper body and replaces ``images/`` wholesale; an asset must instead *merge*
into the shared ``images/`` directory, because ``paper.md`` already references
files there. Conversion therefore runs in a temporary directory and only
merged, non-conflicting results are moved into the paper directory.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import shutil
import sys
import tempfile
from pathlib import Path

# MinerU emits assets into one of these directories next to the Markdown file.
_IMAGE_DIR_CANDIDATES = ("images", "{stem}_images", "{stem}_mineru_images")

_IMAGE_REF = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")

_UNSAFE_NAME_CHARS = re.compile(r"[^A-Za-z0-9._-]+")

# ``paper.md`` belongs to attach-pdf / the ingest pipeline; refuse to shadow it.
_RESERVED_ASSET_NAMES = {"paper", "meta", "notes"}


def _ui(msg: str = "") -> None:
    try:
        from scholaraio.interfaces.cli import compat as cli_mod
    except ImportError:
        from scholaraio.core.log import ui as log_ui

        log_ui(msg)
        return
    cli_mod.ui(msg)


def _resolve_paper(paper_id: str, cfg) -> Path:
    from scholaraio.interfaces.cli import compat as cli_mod

    return cli_mod._resolve_paper(paper_id, cfg)


def sanitize_asset_name(raw: str) -> str:
    """Normalize a user-supplied asset name into a safe file stem.

    Raises:
        ValueError: if the name is empty or reserved for paper-owned files.
    """
    stem = _UNSAFE_NAME_CHARS.sub("-", (raw or "").strip()).strip("-._")
    if not stem:
        raise ValueError("Asset name must contain at least one letter, digit, dot, underscore, or hyphen")
    if stem.lower() in _RESERVED_ASSET_NAMES:
        raise ValueError(f"Asset name {stem!r} is reserved; use attach-pdf for the paper body")
    return stem


def find_mineru_images_dir(md_path: Path) -> Path | None:
    """Locate the image directory MinerU produced beside ``md_path``."""
    for pattern in _IMAGE_DIR_CANDIDATES:
        candidate = md_path.parent / pattern.format(stem=md_path.stem)
        if candidate.is_dir() and any(candidate.iterdir()):
            return candidate
    return None


def merge_asset_images(src_dir: Path | None, dest_dir: Path) -> dict[str, str]:
    """Additively merge MinerU assets into the paper's shared ``images/``.

    MinerU's own hash-based filenames are kept so output matches the existing
    library convention. An existing file is never overwritten: identical bytes
    are reused, and a name collision with different bytes falls back to a
    content-hash filename.

    Returns:
        Mapping of source filename to the filename actually landed in ``dest_dir``.
    """
    mapping: dict[str, str] = {}
    if src_dir is None:
        return mapping

    dest_dir.mkdir(parents=True, exist_ok=True)
    for src in sorted(src_dir.iterdir()):
        if not src.is_file():
            continue
        data = src.read_bytes()
        target = dest_dir / src.name
        if target.exists():
            if target.read_bytes() != data:
                target = dest_dir / f"{hashlib.sha256(data).hexdigest()}{src.suffix}"
                if not target.exists():
                    target.write_bytes(data)
        else:
            target.write_bytes(data)
        mapping[src.name] = target.name
    return mapping


def rewrite_image_refs(md: str, mapping: dict[str, str]) -> str:
    """Point Markdown image references at the merged ``images/`` filenames.

    References whose basename is not in ``mapping`` are left untouched.
    """

    def repl(match: re.Match[str]) -> str:
        alt, target = match.group(1), match.group(2).strip()
        landed = mapping.get(target.rsplit("/", 1)[-1])
        if landed is None:
            return match.group(0)
        return f"![{alt}](images/{landed})"

    return _IMAGE_REF.sub(repl, md)


def unresolved_image_refs(md: str, paper_dir: Path) -> list[str]:
    """Return image references that do not resolve inside ``paper_dir``."""
    refs = [m.group(2).strip() for m in _IMAGE_REF.finditer(md)]
    return [ref for ref in refs if not (paper_dir / ref).exists()]


def _convert_asset_pdf(pdf_path: Path, out_dir: Path, cfg):
    """Convert ``pdf_path`` into ``out_dir`` using the configured parser chain.

    Mirrors the local -> cloud -> fallback routing used by ``attach-pdf``.
    """
    from scholaraio.providers.mineru import (
        ConvertOptions,
        _convert_long_pdf,
        _convert_long_pdf_cloud,
        _get_pdf_page_count,
        _plan_cloud_chunking,
        check_server,
        convert_pdf,
        convert_pdf_cloud,
        validate_pdf_for_mineru,
    )

    mineru_opts = ConvertOptions(
        api_url=cfg.ingest.mineru_endpoint,
        output_dir=out_dir,
        backend=cfg.ingest.mineru_backend_local,
        cloud_model_version=cfg.ingest.mineru_model_version_cloud,
        lang=cfg.ingest.mineru_lang,
        parse_method=cfg.ingest.mineru_parse_method,
        formula_enable=cfg.ingest.mineru_enable_formula,
        table_enable=cfg.ingest.mineru_enable_table,
        poll_timeout=cfg.ingest.mineru_poll_timeout,
    )
    local_chunk_limit = getattr(cfg.ingest, "chunk_page_limit", 100)

    def _ensure_valid() -> None:
        validation = validate_pdf_for_mineru(pdf_path)
        if not validation.ok:
            _ui(f"PDF validation failed: {validation.error or 'PDF validation failed'}")
            sys.exit(1)

    if check_server(cfg.ingest.mineru_endpoint):
        _ensure_valid()
        page_count = _get_pdf_page_count(pdf_path)
        if page_count > local_chunk_limit:
            _ui(f"Detected long PDF ({page_count} pages, exceeds {local_chunk_limit} page limit), splitting...")
            return _convert_long_pdf(pdf_path, mineru_opts, chunk_size=local_chunk_limit)
        return convert_pdf(pdf_path, mineru_opts)

    api_key = cfg.resolved_mineru_api_key()
    if not api_key:
        _ui("MinerU is unreachable and no MinerU token is configured; using fallback parser")
        return None

    _ensure_valid()
    should_chunk, chunk_size, reason = _plan_cloud_chunking(pdf_path, default_chunk_size=local_chunk_limit)
    if not should_chunk:
        return convert_pdf_cloud(pdf_path, mineru_opts, api_key=api_key, cloud_url=cfg.ingest.mineru_cloud_url)

    _ui(f"Detected cloud PDF chunking requirement ({reason}), splitting into chunks...")
    try:
        return _convert_long_pdf_cloud(
            pdf_path,
            mineru_opts,
            api_key=api_key,
            cloud_url=cfg.ingest.mineru_cloud_url,
            chunk_size=chunk_size,
        )
    except ImportError as exc:
        _ui(f"Cloud chunking dependency is missing; trying fallback: {exc}. Install with: pip install scholaraio[pdf]")
    except Exception as exc:
        _ui(f"Cloud chunking failed; trying fallback: {exc}")
    return None


def cmd_attach_asset(args: argparse.Namespace, cfg) -> None:
    from scholaraio.providers.pdf_fallback import convert_pdf_with_fallback, preferred_parser_order

    paper_d = _resolve_paper(args.paper_id, cfg)
    src_path = Path(args.asset_path)
    dry_run = getattr(args, "dry_run", False)
    force = getattr(args, "force", False)

    if not src_path.exists():
        _ui(f"Error: asset file does not exist: {src_path}")
        sys.exit(1)
    if src_path.suffix.lower() != ".pdf":
        _ui(f"Error: attach-asset currently supports PDF only, got {src_path.suffix or 'no extension'}")
        sys.exit(1)

    try:
        asset_name = sanitize_asset_name(getattr(args, "name", None) or src_path.stem)
    except ValueError as exc:
        _ui(f"Error: {exc}")
        sys.exit(1)

    dest_pdf = paper_d / f"{asset_name}.pdf"
    out_md = paper_d / f"{asset_name}.md"
    images_dir = paper_d / "images"
    existing_images = len(list(images_dir.iterdir())) if images_dir.is_dir() else 0

    if dry_run:
        _ui(f"[dry-run] Paper directory: {paper_d}")
        _ui(f"[dry-run] Asset source: {src_path}")
        _ui(f"[dry-run] Target PDF: {dest_pdf}")
        _ui(f"[dry-run] Target Markdown: {out_md}")
        _ui(f"[dry-run] Images are merged into {images_dir} ({existing_images} existing files are preserved)")
        if out_md.exists():
            _ui(f"[dry-run] Warning: {out_md.name} already exists and requires --force to overwrite")
        _ui("[dry-run] Will run: MinerU conversion -> merge images -> rewrite image refs")
        _ui("[dry-run] Will NOT re-embed or rebuild the index; assets are not search bodies")
        _ui("[dry-run] If this looks correct, rerun without --dry-run")
        return

    if out_md.exists() and not force:
        _ui(f"Error: {paper_d.name}/{out_md.name} already exists; use --force to overwrite it")
        sys.exit(1)

    resolved_src = src_path.resolve()
    if resolved_src != dest_pdf.resolve():
        if dest_pdf.exists() and not force:
            _ui(f"Error: {paper_d.name}/{dest_pdf.name} already exists; use --force to replace it")
            sys.exit(1)
        shutil.copy2(resolved_src, dest_pdf)
        _ui(f"Copied asset PDF: {dest_pdf.name}")

    # Convert in a scratch directory so MinerU artifacts never collide with the
    # paper's own paper.md assets.
    with tempfile.TemporaryDirectory(prefix="scholaraio-asset-") as tmp:
        tmp_dir = Path(tmp)
        result = _convert_asset_pdf(dest_pdf, tmp_dir, cfg)

        md_path = result.md_path if result is not None and result.success else None
        if md_path is None or not md_path.exists():
            err = result.error if result is not None else "MinerU unavailable"
            _ui(f"MinerU conversion failed; trying fallback: {err}")
            fallback_md = tmp_dir / f"{asset_name}.md"
            ok, parser_name, fallback_err = convert_pdf_with_fallback(
                dest_pdf,
                fallback_md,
                parser_order=preferred_parser_order(
                    getattr(cfg.ingest, "pdf_preferred_parser", "mineru"),
                    getattr(cfg.ingest, "pdf_fallback_order", None),
                    auto_detect=getattr(cfg.ingest, "pdf_fallback_auto_detect", True),
                ),
                auto_detect=getattr(cfg.ingest, "pdf_fallback_auto_detect", True),
            )
            if not ok:
                _ui(f"Fallback parsing failed: {fallback_err}")
                sys.exit(1)
            _ui(f"Fell back to {parser_name}")
            md_path = fallback_md

        mapping = merge_asset_images(find_mineru_images_dir(md_path), images_dir)
        md = rewrite_image_refs(md_path.read_text(encoding="utf-8"), mapping)
        out_md.write_text(md, encoding="utf-8")

    unresolved = unresolved_image_refs(md, paper_d)
    _ui(f"Generated {paper_d.name}/{out_md.name} ({len(md):,} chars)")
    _ui(f"Merged {len(mapping)} images into images/ ({existing_images} pre-existing files preserved)")
    if unresolved:
        _ui(f"Warning: {len(unresolved)} image references do not resolve:")
        for ref in unresolved[:5]:
            _ui(f"  ! {ref}")
