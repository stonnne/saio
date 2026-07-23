# ScholarAIO

**Scholar All-In-One** — an academic harness for AI agents.

ScholarAIO provides the durable academic context and workflow contracts around a coding agent: evidence, project state, skills, CLI operations, research outputs, and verification. The active agent remains responsible for reasoning and orchestration.

In 2.x, **All-in-One means one coherent academic workflow**, not a distribution of every scientific package or a general autoresearch platform. See the repository-root [strategy](https://github.com/zimoliao/scholaraio/blob/main/STRATEGY.md) and the [2.x public contract](design-docs/2.x-public-contract.md).

## Features

- **PDF Ingestion**: Convert PDFs to structured Markdown via MinerU (cloud or local)
- **Publisher PDF Fetch**: Download DOI or publisher-page PDFs through the user's current legal access context, including direct campus-network mode and selected/all-library refetch
- **Hybrid Search**: FTS5 keyword search + FAISS semantic search + RRF fusion
- **Topic Modeling**: BERTopic clustering with interactive HTML visualizations
- **Citation Graph**: View references, citing papers, and shared references
- **BibTeX Export**: Filtered export with standard citation formats
- **Library WebUI**: Browse, filter, run ranked retrieval, copy canonical BibTeX, and open PDFs inline or in the operating system's default viewer
- **Paper Translation**: Translate papers with concurrent chunked LLM calls and optional portable bundles
- **Literature Exploration**: Multi-dimensional OpenAlex queries with isolated data
- **Workspace Management**: Organize papers into subsets for focused work
- **Federated Discovery**: Search your library, explore silos, and arXiv in one flow
- **Research Insights**: Inspect search/read behavior trends and semantic neighbor recommendations
- **Scientific Tool Docs**: Query indexed official docs for scientific computing tools with `toolref`
- **Bounded Tool Adapters**: Keep external integrations optional, isolated, testable, and subject to the 2.x integration gate
- **Office Document Inspection**: Verify DOCX / PPTX / XLSX structure with `document inspect`
- **Agent Skills**: Reusable workflows for search, writing, scientific runtime, and more
- **Writing Router**: Start with `academic-writing` to route reviews, guided deep reading, paper sections, rebuttals, posters, and technical reports to the right workflow

## Quick Start

```bash
pip install "scholaraio[full]"
scholaraio setup
```

See [Installation](getting-started/installation.md) for detailed instructions.
See [Upgrading To 2.0](getting-started/upgrading-to-2.0.md) for compatibility and migration guidance.
If you are working from a local clone or contributing to ScholarAIO itself, use the editable install path shown there instead.
See [Agent Setup](getting-started/agent-setup.md) for repo-open vs plugin setup paths.
See [Repository Knowledge Map](DESIGN.md) for the agent-facing documentation structure.
See [Agent Reference](guide/agent-reference.md) for the deeper agent, skill, and runtime map.
See [Translation Guide](guide/translate.md) for translation, resume, and portable export behavior.
See [Insights Guide](guide/insights.md) for reading/search behavior analytics.
See [Library WebUI](guide/library-webui.md) for browser-based filtering, ranked search, citation copy, and PDF workflows.
See [API Reference](api/index.md) for Python module documentation.

## Two Usage Modes

| Mode | Interface | Best for |
|------|-----------|----------|
| **Agent** | Supported coding agent | Full research workflow via natural language |
| **CLI** | Terminal | Scripting and automation |

## Repository Knowledge

ScholarAIO is agent-first infrastructure, so repository-local documentation is
part of the runtime surface for agents. Start with [Repository Knowledge
Design](DESIGN.md), then follow the relevant design, product-spec, generated
reference, guide, or API page.
