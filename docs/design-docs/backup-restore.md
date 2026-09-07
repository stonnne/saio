# Backup And Restore Contract

Status: Current

Last Updated: 2026-08-16

## Purpose

ScholarAIO backup targets have two explicit scopes:

- `data` preserves the original rsync behavior for `backup.source_dir`.
- `instance` preserves the runtime-instance surfaces required for a portable restore.

The default remains `data` so existing targets do not silently change their remote layout. A target switched to `instance` should point at a dedicated empty remote directory.

## Instance Backup Layout

An instance backup preserves paths relative to the runtime-instance root:

```text
config.yaml
config.local.yaml          # when present
data/                      # or the configured backup.source_dir
workspace/                 # configured workspace root
published/                 # configured published archive root
.scholaraio-control/
  backup-manifest.json
```

Configured component roots must resolve inside the runtime-instance root. Unknown files below included directories are preserved because rsync copies whole trees. Instance targets require `mode: default` and reject exclude patterns.

Each subsequent instance backup mirrors deletions within those component trees, so a paper or metadata file removed locally does not survive remotely and reappear during restore. Files outside the manifest-listed component roots are not part of the instance contract.

Before a real instance transfer, ScholarAIO discovers `.db`, `.sqlite`, and `.sqlite3` files in the component trees. Each recognized SQLite database is copied with SQLite's online backup API, normalized to a standalone database in `DELETE` journal mode, and verified with `PRAGMA quick_check`. These staged copies take precedence over the live files in the rsync source list; matching WAL, SHM, and rollback-journal sidecars are excluded and removed from the remote mirror. The manifest records the database paths that used this treatment.

The versioned manifest records the relative component paths, their file/directory types, and the SQLite paths captured through online backup. Restore fetches and validates this manifest before copying anything, then reopens every listed SQLite database and runs `quick_check` after a successful transfer. Absolute paths and traversal components are rejected, and data-only targets cannot be restored as full instances.

## Restore Safety

`backup restore` restores only manifest-listed components. It never copies arbitrary source-repository files from the remote target.

- Empty destinations are accepted by default.
- Non-empty destinations require `--force`.
- `--force` merges and overwrites matching runtime files but does not delete unrelated files.
- Filesystem roots are never valid destinations.
- Restored `config.local.yaml` is forced to owner-only (`0600`) permissions.

After relocation, path-bearing derived indexes may be stale even when the backup is complete. Users should run `scholaraio setup check` and rebuild path-sensitive indexes.

## Secret Handling

`config.local.yaml` is part of an instance backup because API keys and local target configuration are required for complete recovery. SSH encrypts it in transit and rsync preserves owner-only permissions, but the file remains plaintext at rest on the backup server. Operators must protect the remote account and storage.

Environment-only credentials are intentionally not captured. Disaster recovery on a replacement machine therefore starts with a minimal local target configuration (or SSH key) that can reach the remote backup; the restored local config then replaces that bootstrap state.

## Limitations

- Backup is an rsync mirror, not a versioned snapshot history.
- Each SQLite database is internally consistent, but snapshots of multiple databases are taken sequentially rather than as one cross-database transaction. Non-SQLite files are still copied from the live component trees.
- Fresh SQLite snapshots receive new timestamps and may be transferred again even when their logical contents have not changed.
- Restore does not install ScholarAIO source code, Python dependencies, system packages, SSH host trust, or environment-variable-only secrets.
