# Upgrading To 2.0

ScholarAIO 2.0 marks functional convergence around an All-in-One academic
harness for agents. It does not introduce a new runtime data layout for users
already on 1.4 or 1.5.

## What All-in-One Means In 2.0

All-in-One describes a coherent academic workflow: evidence, persistent state,
agent skills, CLI operations, research outputs, and verification live behind
one harness. Reasoning and orchestration remain with the active coding agent.

2.x development prioritizes reliability, workflow clarity, cross-agent
portability, and user experience. ScholarAIO is not expanding into a general
autoresearch platform, a multi-agent framework, or a catalogue of every
third-party scientific package.

## Upgrade From 1.4 Or 1.5

No data migration is required. Back up the runtime as usual, update the package,
and run the normal diagnostics:

```bash
pip install -U "scholaraio[full]"
scholaraio setup check
scholaraio index --rebuild
```

For a source checkout, replace the install command with:

```bash
git pull
pip install -e ".[full]"
```

The final command above must be run from the ScholarAIO repository root.

## Testing The Beta

The current release workflow validates prerelease tags without publishing them
to PyPI. To test `v2.0.0-beta.1`, use a separate source checkout:

```bash
git clone --branch v2.0.0-beta.1 https://github.com/zimoliao/scholaraio.git scholaraio-2.0-beta
cd scholaraio-2.0-beta
pip install -e .
scholaraio setup check
```

Keep an existing production checkout unchanged while evaluating the beta.

## Upgrade From 1.3 Or Earlier

Complete the explicit 1.4 runtime migration before using normal 2.0 workflows:

```bash
scholaraio migrate status
scholaraio migrate upgrade --migration-id upgrade-2.0.0 --confirm
scholaraio migrate verify --migration-id upgrade-2.0.0
scholaraio index --rebuild
scholaraio setup check
```

Keep an unchanged copy of the old `data/`, `workspace/`, and `config*.yaml`
files until migration verification passes. See [Upgrading To
1.4](upgrading-to-1.4.md) for the full migration and recovery procedure.

## Removed Or Narrowed Surfaces

- The old `websearch` skill and CLI command are removed. Use the active agent's
  native web search for live discovery; use `webextract` for rendered content
  extraction and `ingest-link` when the result should enter the library.
- The empty `scholaraio[draw]` extra is removed. Diagram source generation
  remains available; Graphviz and Inkscape are explicit system tools when
  rendering requires them.
- Legacy root-level Python facade modules and implicit legacy runtime-root
  detection remain removed. Use canonical package namespaces and the explicit
  migration workflow.
- Paper2Any and other large third-party workflows remain optional sidecars; they
  are not installed or required by the default ScholarAIO runtime.

## 2.x Compatibility Promise

The documented CLI, configuration, runtime layout, skill discovery, persistent
identifiers, and published API surfaces follow the [ScholarAIO 2.x Public
Contract](../design-docs/2.x-public-contract.md). New work should improve these
surfaces without quietly broadening the product into a new platform category.
