# ScholarAIO 2.0.0 Beta 1 Self-Check

Status: Local release gate passed; remote CI and beta feedback pending

Date: 2026-07-21

Baseline: `origin/main` at `c55f214`

Candidate branch: `release/2.0.0-beta.1`

## Scope

This check covers the 2.0 functional-convergence contract, public positioning,
version alignment, optional-dependency boundary, agent-skill validation,
documentation, package construction, and the existing regression suite.

It does not claim that the beta tag has been created, that PyPI has published
2.0, or that real-user beta feedback has completed.

## Results

| Gate | Command or path | Result |
|---|---|---|
| Full regression suite | `python -m pytest -q -p no:cacheprovider` | 1643 passed |
| Focused 2.0/setup tests | version, release metadata, agent docs, setup, MinerU, CLI messages | 215 passed |
| Lint | `python -m ruff check scholaraio tests` | passed |
| Format | `python -m ruff format --check scholaraio tests` | 225 files formatted |
| Type check | `python -m mypy scholaraio` | 148 source files, no issues |
| Skill harness | `python .claude/skills/_templates/validate_skills.py` | all skills passed |
| Documentation | `python -m mkdocs build --strict` | passed |
| Prerelease metadata | `GITHUB_REF_NAME=v2.0.0-beta.1 python scripts/check_release_metadata.py` | tag/base metadata aligned |
| Clean wheel | isolated build and venv install | `scholaraio==2.0.0`, `pip check` passed |
| Core dependency boundary | isolated wheel environment | `mineru_open_api` absent; CLI help passed |

## Contract Checks

- `STRATEGY.md` defines the All-in-One academic-harness meaning, primary user,
  metrics, tracks, and explicit non-goals.
- `docs/design-docs/2.x-public-contract.md` defines stable surfaces,
  deprecation expectations, data-migration behavior, and the integration gate.
- `scientific-tool-onboarding` now starts with the integration gate instead of
  treating every proposed tool as an implementation request.
- `mineru-open-api` moved from mandatory dependencies to the isolated
  `mineru-cloud` extra and is not pulled in by `full`.
- Setup, cloud-parser failure guidance, and the plugin bootstrap consistently
  point to the published optional extra and fresh paper-library path.
- README, docs home, CLI help, package metadata, citation metadata, plugin
  manifests, and the bilingual agent entries use the academic-harness position
  while preserving the Scholar All-in-One name.

## Remaining Release Gates

1. Open the candidate pull request and pass the GitHub Linux/Python matrix,
   package-wheel smoke, documentation build, and existing macOS workflow.
2. Resolve or close superseded and out-of-scope backlog items against the 2.0
   boundary.
3. Merge the candidate and create `v2.0.0-beta.1`; the current release workflow
   validates prerelease tags but intentionally does not publish them to PyPI.
4. Run a short beta period with real libraries and at least one non-maintainer
   workflow before creating the stable `v2.0.0` tag.
