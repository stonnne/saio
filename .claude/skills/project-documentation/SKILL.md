---
name: project-documentation
description: Use when planning, reorganizing, standardizing, or writing project documentation for a code/scientific project; especially when docs need a durable folder taxonomy, shared common references, topic-focused pages, consistent style, link migration, and validation after moving or rewriting Markdown files.
---

# Project Documentation

Use this skill to turn project documentation from an accumulated set of notes into a maintainable documentation system. The pattern is based on the `workspace/jet-cooling/doc` cleanup: separate public/common knowledge from topic-specific pages, keep each page scoped, and validate links and generated artifacts after moving files.

## Core Principles

- **One entrypoint:** keep a short `doc/README.md` or equivalent that explains the documentation map and links to every major section.
- **Common first:** extract shared geometry, runtime conventions, commands, schemas, terminology, and tool indexes into `common/` pages. Topic pages should reference these instead of repeating them.
- **Topic isolation:** each topic page should contain only what is specific to that topic: assumptions, settings, workflow, outputs, status, and caveats.
- **Stable taxonomy:** classify docs by user intent and maintenance ownership, not by file creation history.
- **Consistent page shape:** use the same section order for similar pages, so future edits are predictable.
- **Link integrity:** after moving or rewriting docs, verify Markdown links and update scripts that emit documentation assets.

## Workflow

### 1. Inventory

Start by listing documents and headings:

```bash
find <project>/doc -maxdepth 3 -type f | sort
for f in <project>/doc/**/*.md <project>/doc/*.md; do
  printf '%s\n' "$f"
  rg -n '^# |^## |^### ' "$f"
done
```

Also scan top-level `README.md`, tool READMEs, archive docs, and scripts that refer to doc paths.

Classify each document as one of:

- `common`: shared facts and conventions used by multiple pages
- `baseline`: reference cases, benchmark cases, or canonical implementations
- `topic`: user-facing workflow or feature area
- `mesh` / `data` / `analysis` / domain-specific folders as appropriate
- `archive`: historical notes that should not drive current workflows

### 2. Design the Target Tree

Prefer a small, durable tree. For scientific or engineering projects, this shape usually works:

```text
doc/
├── README.md
├── common/
│   ├── geometry.md
│   ├── workflow.md
│   ├── numerics.md
│   └── tooling.md
├── baseline/
├── <domain-topic>/
└── <implementation-topic>/
```

Adjust folder names to the project. Avoid over-splitting before there is a real maintenance boundary.

### 3. Extract Common Content

Move repeated or cross-cutting material into `common/`:

- project geometry, coordinate systems, naming, units
- shared runtime workflow and commands
- shared numerical or configuration conventions
- tool/script index
- shared data schemas or output locations

Common docs should not become long manuals. They should define stable facts and point topic docs to the right source of truth.

### 4. Rewrite Topic Pages

Use a consistent shape. For workflow/topic docs:

```text
# Title

## 1. Purpose and Scope
## 2. Dependencies and References
## 3. Topic-Specific Setup
## 4. Run or Reproduce
## 5. Outputs and Results
## 6. Current Status and Caveats
```

For common reference docs:

```text
# Title

## 1. Scope
## 2. Conventions
## 3. Details
## 4. Used By
```

Keep tables for stable parameters, commands for reproducible workflows, and prose for decisions and caveats. Move long historical reasoning to archive docs unless it is required to reproduce current results.

### 5. Migrate Files Carefully

Use normal file moves for pure relocation. Update all relative links after moves. If external users likely link to old paths, leave short redirect stubs:

```markdown
# Moved

This document moved to [new/path.md](new/path.md).
```

If docs are only internal and all links can be updated, do not keep stubs; a clean tree is easier to maintain.

Also update scripts that generate doc assets, such as plot/image outputs:

```python
OUT = REPO / "doc" / "mesh" / "figure.png"
```

### 6. Validate

At minimum, run:

```bash
rg -n 'old-doc-name|old/path|stale-title' <project>/doc <project>/README.md <project>/tools
python -m py_compile <changed-python-scripts>
```

Check active Markdown links with a small script:

```bash
python - <<'PY'
from pathlib import Path
import re

paths = [Path("README.md")]
paths += list(Path("doc").glob("**/*.md"))
missing = []
for md in paths:
    text = md.read_text(errors="replace")
    for m in re.finditer(r"\[[^\]]+\]\(([^)]+)\)", text):
        target = m.group(1).split("#", 1)[0]
        if not target or re.match(r"[a-z]+://", target) or target.startswith("mailto:"):
            continue
        if target.startswith("<") and target.endswith(">"):
            target = target[1:-1]
        if not (md.parent / target).resolve().exists():
            missing.append((md, m.group(1)))
if missing:
    for md, target in missing:
        print(f"{md}: missing {target}")
    raise SystemExit(1)
print(f"checked {len(paths)} markdown files; all relative links resolve")
PY
```

Exclude historical `archive/` docs from this check unless the task is specifically to repair archive links.

## Style Rules

- Keep the top-level README short; it should route readers, not duplicate details.
- Keep each document’s title literal and stable.
- Use numbered major sections for long technical docs.
- Prefer tables for parameters, case lists, and output files.
- Prefer command blocks for reproduction steps.
- Explicitly mark “current status” and “caveats” when results are provisional.
- Do not mix historical design debates into the current workflow page; link archive notes instead.
- When reorganizing, do not touch running case directories, result files, or generated runtime data unless the user asks.

## Done Criteria

A documentation cleanup is complete when:

- `doc/README.md` explains the new map.
- Common facts live in `common/` and are referenced by topic docs.
- Topic docs contain only topic-specific material.
- Top-level README and tool READMEs point to the new paths.
- Generated figure/script output paths match the new tree.
- Active Markdown links resolve.
- Any running scientific or compute workflows are not interrupted.
