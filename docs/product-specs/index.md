# Product Specs

Status: Current index

Last Updated: 2026-07-21

Product specs capture user-visible behavior and workflow contracts. They are
separate from implementation plans so agents can understand what should happen
without replaying historical work.

The current cross-product direction lives in the repository-root
[`STRATEGY.md`](https://github.com/zimoliao/scholaraio/blob/main/STRATEGY.md). Product specs in this directory should
describe user-visible behavior within that boundary, while the
[ScholarAIO 2.x Public Contract](../design-docs/2.x-public-contract.md) defines
the compatibility policy.

## Rules

- Add a product spec when behavior spans multiple commands, skills, or user
  workflows.
- Keep implementation sequencing in internal maintenance records.
- Keep architecture constraints in `docs/design-docs/`.
