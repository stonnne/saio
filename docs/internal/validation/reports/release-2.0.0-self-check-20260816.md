# ScholarAIO 2.0.0 Stable Release Self-Check

Status: Local release gate passed; pull-request CI, tag publication, and PyPI verification pending

Date: 2026-08-16

Baseline: `origin/main` at `c5a19ff`

Candidate branch: `agent/release-2.0.0`

## Scope

This check covers the stable 2.0 distribution metadata, changelog and upgrade
guidance, post-beta backup and chunk-search changes, release automation, package
construction, clean installation, documentation, skills, and the full regression
suite.

It does not claim that the candidate pull request has passed remote CI, that the
`v2.0.0` tag or GitHub release exists, or that PyPI has published the artifact.

## Results

| Gate | Command or path | Result |
|---|---|---|
| Full regression suite | `python -m pytest -q -p no:cacheprovider` | 1627 passed |
| Lint | `python -m ruff check scholaraio tests scripts/check_release_metadata.py` | passed |
| Format | `python -m ruff format --check scholaraio tests scripts/check_release_metadata.py` | 225 files formatted |
| Type check | `python -m mypy scholaraio` | 147 source files, no issues |
| Skill harness | `python .claude/skills/_templates/validate_skills.py` | all skills passed |
| Documentation | `python -m mkdocs build --strict` | passed |
| Stable metadata | `GITHUB_REF_NAME=v2.0.0 python scripts/check_release_metadata.py` | version, changelog, classifier, and release date aligned |
| Prerelease compatibility | `GITHUB_REF_NAME=v2.0.0-beta.1 python scripts/check_release_metadata.py` | historical beta tag remains valid |
| Distribution build | `python -m build --sdist --wheel` | sdist and universal wheel built |
| Distribution metadata | `python -m twine check dist/*` | both artifacts passed |
| Clean wheel install | isolated virtual environment | `scholaraio==2.0.0`, `pip check`, CLI help, and stable classifier passed |
| Core dependency boundary | isolated wheel environment | `mineru_open_api` absent |

## Release Contract Checks

- Package, runtime, plugin, marketplace, and citation versions remain aligned at
  `2.0.0`.
- Stable tags now fail before publishing unless the exact tag has exactly one
  dated changelog section, the package has exactly one Production/Stable
  classifier, and the citation and changelog release dates agree on a valid ISO
  calendar date.
- `CHANGELOG.md` records the complete post-beta delta: full-instance backup and
  restore, SQLite-consistent backup hardening, bounded transfer execution,
  chunk paper-type normalization, and confirmed dead-code removal.
- English and Chinese README feature summaries describe the current full-instance
  backup and restore contract instead of the legacy data-only behavior.
- The 2.0 upgrade guide replaces beta-testing instructions with stable PyPI
  guidance and explicitly handles beta installations whose package metadata
  already reports `2.0.0`.
- The release workflow remains tag-triggered and uses PyPI trusted publishing;
  prerelease tags skip publication while `v2.0.0` will publish after its release
  smoke tests and distribution checks pass.

## Repository Readiness

- At the start of preparation, `main` had no open pull requests and its CI and
  documentation workflows were green at `c5a19ff`.
- The only open issue was enhancement request #129, which is unrelated to the
  2.0 compatibility and release gates.
- `v2.0.0` was not already present as a Git tag or GitHub release, and PyPI's
  latest public ScholarAIO version was `1.5.0`.

## Remaining Release Gates

1. Pass the candidate pull request's Linux/Python matrix, package smoke, and the
   macOS semantic smoke triggered by the package metadata change; retain the
   passing local strict-documentation build as release evidence.
2. Review and merge the candidate without adding unrelated changes.
3. Create `v2.0.0` on the resulting `main` commit and wait for the tag-triggered
   release workflow to publish through the protected `release` environment.
4. Verify `pip install scholaraio==2.0.0` from PyPI in a fresh environment, then
   publish a non-prerelease GitHub Release using the stable changelog entry and
   beta reinstall warning.
