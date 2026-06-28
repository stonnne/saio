---
name: research-project-structure
description: Use when scaffolding, standardizing, or reorganizing a scientific/engineering computing project (e.g. CFD/OpenFOAM, MD, FEM, data-analysis) into a durable, reproducible workspace; especially when a chosen directory needs the canonical archive/cases/doc/report/results/tools(/src) taxonomy, a project README, a discipline-aware .gitignore, and validation that nothing running is disturbed.
---

# Research Project Structure

Use this skill to turn an ad-hoc compute workspace into a maintainable, reproducible
research project. The canonical template is the layout used by
`workspace/jet-cooling` (a multi-case OpenFOAM study). It separates **source of
record** (cases, code) from **derived artifacts** (results, report) from
**knowledge** (doc) from **history** (archive), and keeps generated bulk out of
Git.

This skill owns the *whole-project* taxonomy. The `doc/` subtree is delegated to
the **`project-documentation`** skill — invoke that skill for the `doc/` interior
(common/ + topic pages + link validation). Do not duplicate its rules here.

## Core Principles

- **Pick the workspace explicitly first.** The target is the current directory or
  a named subdirectory. Never scaffold into the repo root or `scholaraio/` by
  accident. Confirm the path before creating folders.
- **Sources vs. derivatives.** `cases/` and `src/` are inputs you author and must
  keep. `results/` and `report/figures|data` are *regenerable* outputs — they are
  produced by `tools/` and `report/scripts/`, and are git-ignored.
- **One regeneration path per artifact.** Every figure/table/CSV under
  `results/` or `report/` must be reproducible by a named script. If you can't
  name the script, the artifact isn't structured yet.
- **Knowledge lives in `doc/`, not in case folders.** Conventions, geometry,
  workflow, and tool indexes go to `doc/common/`; per-topic findings go to
  `doc/<topic>/`. Use the `project-documentation` skill there.
- **History is parked, not deleted.** Superseded cases, old reports, and dead-end
  experiments move to `archive/` (or `report/_archive/`), never get rm'd, and
  never drive the current workflow.
- **Never disturb running compute.** Do not move, rename, or clean a case that is
  mid-solve, and do not delete time directories or `postProcessing/` the user may
  still need. Restructure metadata and docs around live runs.

## Canonical Tree

```text
<workspace>/
├── README.md            # project entrypoint: what it is, case table, how to run
├── .gitignore           # ignore regenerable bulk + runtime artifacts
├── archive/             # superseded cases, dead-ends, historical results
├── cases/               # SOURCE OF RECORD: one folder per compute case/config
│   ├── <case-a>/        #   solver/config inputs + (git-ignored) run outputs
│   └── <case-b>/
├── doc/                 # knowledge base — managed by `project-documentation`
│   ├── README.md            #   doc map / entrypoint
│   ├── common/              #   shared geometry, workflow, numerics, tooling index
│   ├── baseline/            #   reference/benchmark cases
│   └── <topic>/             #   topic-specific findings
├── report/              # data integration + deliverable generation
│   ├── README.md            #   how to reproduce the report
│   ├── main.tex / report.md #   the deliverable source
│   ├── data/                #   plot-source data, grouped by theme
│   ├── figures/             #   final figures referenced by the deliverable (git-ignored)
│   ├── scripts/             #   prepare_data + plot_* + build scripts
│   ├── slides/              #   talk deck (optional)
│   └── _archive/            #   superseded report snapshots
├── results/             # post-processed figures/tables from cases (git-ignored)
│   └── <study-name>/
├── tools/               # data-processing & case-management scripts
│   ├── README.md            #   tool index (points to doc/common/tooling.md)
│   ├── mesh/  flow/  thermal/  analysis/   # grouped by workflow stage
│   └── ...
└── src/                 # core solver/model code — OMIT if using an external
                         #   solver (e.g. stock OpenFOAM) and writing no custom code
```

`src/` is intentionally absent when the project runs an off-the-shelf solver
(the jet-cooling case uses stock OpenFOAM, so it has no `src/`). Add `src/` only
when you author custom solver code, libraries, or models that need to be tracked
and built.

## Workflow

### 1. Choose and confirm the workspace

Resolve the target directory. Default to the current directory; accept a
subdirectory if the user names one.

```bash
WS="${1:-.}"            # current dir, or a named subdir
mkdir -p "$WS" && cd "$WS"
pwd                      # echo the absolute path back to the user before proceeding
```

If the directory already has files, **inventory first** (do not overwrite):

```bash
find "$WS" -maxdepth 2 -not -path '*/.git/*' | sort
```

Classify what exists into the canonical buckets before moving anything.

### 2. Create the skeleton

Create only the folders the project needs. Always create `archive cases doc
report results tools`; add `src` only if custom code exists.

```bash
mkdir -p archive cases doc/common report/{data,figures,scripts} results tools
# add when authoring custom code:  mkdir -p src
```

### 3. Place the entrypoint files

- `README.md` — from `templates/README.template.md`. Fill: one-line description,
  repository-boundary note (if it is its own Git repo), a **case table**
  (`Case | Solver/Config | Role`), and a top-level "how to run / reproduce" pointer.
- `.gitignore` — from `templates/gitignore.template`. Tune the ignore patterns to
  the discipline (see template comments). The rule of thumb: **ignore anything a
  script can regenerate** (time directories, `postProcessing/`, `results/`,
  figures, Office files, logs, caches) and **keep anything authored by hand**
  (case dictionaries, the `0/` initial-condition dir, source, doc, report source).

### 4. Populate `doc/` via the project-documentation skill

Hand the `doc/` interior to the **`project-documentation`** skill. The
project-level requirement here: `doc/` must **comprehensively and in detail cover
the whole project** — geometry/domain, common workflow, numerics/config,
per-case methods and findings, mesh/data conventions, and a tooling index — not
just a thin index. Topic pages reference `doc/common/`; the doc tree gets its own
`doc/README.md` map and passes link validation.

### 5. Wire derived artifacts to their generators

For each study, ensure a named regeneration path exists:

- `cases/<case>/` → run via a `tools/` script (e.g. `tools/flow/make_*_case.py`,
  `tools/<stage>/run_*.py`).
- `results/<study>/` → produced by an analysis script
  (e.g. `tools/analysis/compare_*.py`).
- `report/figures/*` and `report/data/*` → produced by `report/scripts/plot_*.py`
  fed by `report/scripts/prepare_data.py`, which pulls from `results/` and
  `cases/`.

Record the script-per-artifact mapping in `tools/README.md` and
`report/README.md`. Group `tools/` by workflow stage (`mesh/`, `flow/`,
`thermal/`, `analysis/`, `report/`) rather than by creation date.

### 6. Park history in `archive/`

Move superseded cases, abandoned experiments, and old report snapshots into
`archive/` (or `report/_archive/`). Leave a one-line note in the relevant doc or
README saying what was archived and why. Never delete unless the user asks.

### 7. Validate

```bash
# regenerable bulk is actually ignored, hand-authored inputs are not
git status --short
git check-ignore -v results/ report/figures/some.png 2>/dev/null || true

# every referenced script exists
rg -n 'tools/|report/scripts/' README.md doc tools/README.md report/README.md

# doc link integrity — run the project-documentation skill's link checker
```

Confirm: the case table in `README.md` matches the folders in `cases/`; nothing
under a live run was moved; `git status` is not flooded with regenerable files.

## Folder Contracts (quick reference)

| Folder | Holds | Git | Regenerated by |
| --- | --- | --- | --- |
| `cases/` | solver/config inputs per case; run outputs alongside | inputs tracked, outputs ignored | authored by hand; runs via `tools/` |
| `src/` | custom solver/model/library code (optional) | tracked | n/a — it *is* the source |
| `doc/` | knowledge base (see `project-documentation`) | tracked | hand-written |
| `tools/` | data-processing & case-mgmt scripts, grouped by stage | tracked | hand-written |
| `results/` | post-processed figures/tables from cases | ignored | `tools/analysis/*` |
| `report/` | deliverable source, data, figures, scripts, slides | source tracked; `figures/`, Office files ignored | `report/scripts/*` |
| `archive/` | superseded/historical material | tracked (small) or ignored (bulky) | never — frozen |

## Style Rules

- Keep `README.md` short: identity, case table, run pointer. Push detail to `doc/`.
- One case = one folder under `cases/`; name it for its variable
  (`H0500-L2`, `Re1000`, `T300K`), not for a date.
- A study's outputs go under `results/<study-name>/`, never loose in the root.
- If the project is its own Git repo nested in a parent, state the **repository
  boundary** explicitly in `README.md` and `doc/README.md` (cd into the project
  before running Git), as jet-cooling does.
- Mark provisional results with a "status / caveats" note, mirroring the
  `project-documentation` convention.

## Done Criteria

- The workspace path was confirmed before any folder was created.
- `archive/ cases/ doc/ report/ results/ tools/` exist (plus `src/` iff custom code).
- `README.md` identifies the project and carries a case table matching `cases/`.
- `.gitignore` ignores regenerable bulk and keeps hand-authored inputs;
  `git status` is clean of generated files.
- `doc/` was built/repaired through the `project-documentation` skill and covers
  the whole project in detail, with a working `doc/README.md` and resolving links.
- Every `results/` and `report/` artifact has a named generating script.
- History is in `archive/`, not deleted; no live compute run was disturbed.
