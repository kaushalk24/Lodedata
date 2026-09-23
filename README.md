# Lodedata

Clean-room reverse engineering of the Lode Data *Design Assistant*, the basis for our own
HFC (hybrid fiber-coax) network design tool.

## Documents

| # | Document | What it covers |
|---|---|---|
| 01 | [Lode Design Assistant teardown](docs/01-lode-design-assistant-teardown.md) | How Lode works: data model, spec files, modes, algorithms, reports. Every claim carries an evidence tag, and open questions are listed |
| 02 | [HFC engineering core](docs/02-hfc-engineering-core.md) | The math the engine implements: cable loss, levels, two-pass tap/coupler selection, amps/pads/EQs, return path, performance, powering, 1.2/1.8 GHz extensions |
| 03 | [Reverse-engineering method](docs/03-reverse-engineering-method.md) | Clean-room rules, black-box experiment catalog (E01–E18), golden-test harness, the no-Lode-access path |
| 04 | [Architecture & roadmap](docs/04-architecture-and-roadmap.md) | Stack, repo layout, domain model, parity matrix, phased plan with acceptance criteria, risks |

## Status

Phase 0 (analysis and planning). The next step is listed in
[04 §9](docs/04-architecture-and-roadmap.md#9-immediate-next-steps).
