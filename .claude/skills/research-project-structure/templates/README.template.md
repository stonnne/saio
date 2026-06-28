# <Project Name>

<One or two sentences: what is modeled/computed, the solver/method, and the goal.>

Problem statement: [`problem-statement.md`](problem-statement.md). <!-- if present -->
Full documentation lives in [`doc/`](doc/README.md).

## Repository Boundary
<!-- Keep this section only if the project is its own Git repo nested in a parent. -->

`<workspace>` is its own Git repository. When checking status, reviewing diffs, or
committing this project's documentation, cases, tools, or results, run Git from:

```bash
cd <absolute-path-to-workspace>
git status --short
```

Do not infer this project's Git state from the parent repository.

## Cases

| Case | Solver / Config | Role |
| --- | --- | --- |
| `cases/<case-a>` | `<solver>` | <reference / baseline> |
| `cases/<case-b>` | `<solver>` | <variant / study> |

<!-- One row per folder under cases/. The table must match the folders. -->

## Layout

| Path | Purpose |
| --- | --- |
| `cases/` | Source-of-record compute cases (inputs tracked; run outputs git-ignored) |
| `src/` | Custom solver/model code (omit when using an external solver) |
| `doc/` | Knowledge base — start at [`doc/README.md`](doc/README.md) |
| `tools/` | Data-processing and case-management scripts, grouped by stage |
| `results/` | Post-processed figures/tables from cases (regenerate via `tools/`) |
| `report/` | Deliverable source, data, figures, build scripts |
| `archive/` | Superseded cases and historical results |

## Reproduce

```bash
# 1. (re)run / set up cases
python tools/<stage>/<make-or-run-script>.py
# 2. post-process into results/
python tools/analysis/<compare-script>.py
# 3. rebuild report figures + document
python report/scripts/plot_all.py && bash report/scripts/build_pdf.sh
```

## Status & Caveats

<!-- Mark anything provisional: unconverged runs, surrogate models, pending validation. -->
