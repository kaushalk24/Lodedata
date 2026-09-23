# Lodedata

Clean-room reverse engineering of the Lode Data *Design Assistant*, the basis for our own
HFC (hybrid fiber-coax) network design tool.

## Web app: HFC Plant Designer (`web/`)

A Lode-style design screen that runs in the browser. There is no build step and nothing to
install.

- **Run it:** open `web/index.html` in a browser.
- **Test the engine:** from the repo root, `node --test`.

| Lode concept | In the app |
|---|---|
| Node lines grouped into branches | The grid: one line per pole or pedestal (cable, feet, house count, TSG, equipment). Branch tabs sit above it |
| Levels after the footage, before equipment | `Hi` / `Lo` columns, plus tap port outputs and the return level each tap needs |
| Equipment notation | `11` active, `[26]` 4-port / `(26)` 2-port / `{26}` 8-port tap, `[*]` auto tap, `8[3]` coupler feeding branch 3, `-8[3]` reversed coupler, `*[3]` auto coupler, `PS` power supply |
| Spec files | Specs menu: Parameters, Cables, Actives, Taps (with TSG), Couplers. Saved as JSON |
| Modes | Design, Entry, Powering |
| Numbered toolbar | Esc + 1…9: Lock, Insert, Carry, Delete, Branch ▸, Test, ◂ Back, Add line, Mode |
| Automatic selection | Taps (highest value within the window, minimums and max return), couplers (bottom-up requirement), pads and EQs (never over-pad; over-EQ only if allowed) |
| Checks | Red = out of spec, yellow = marginal: tap levels, active input and reserve gain, LE cascade IDs 11/21/22/31/32/33, return level, C/N / CTB / CSO, voltage, current |
| Powering | Loop-resistance voltage drop with volt/amp step tables, plus a supply-placement optimizer (max low voltage, min square drop, balanced draw) |
| Reports | BOM, Active, Network Tap, Performance Distribution, Power Supply, Network Test. Each can be saved as CSV |

The sample specs are **illustrative placeholders**. Enter your manufacturers' datasheet values
under *Specs* before designing real plant. The math and rules are described in
[docs/02](docs/02-hfc-engineering-core.md). The app is plain HTML/JS to keep it simple; the
TypeScript and map stack in [docs/04](docs/04-architecture-and-roadmap.md) is the path if it
outgrows that.

## Documents

| # | Document | What it covers |
|---|---|---|
| 01 | [Lode Design Assistant teardown](docs/01-lode-design-assistant-teardown.md) | How Lode works: data model, spec files, modes, algorithms, reports. Every claim carries an evidence tag, and open questions are listed |
| 02 | [HFC engineering core](docs/02-hfc-engineering-core.md) | The math the engine implements: cable loss, levels, two-pass tap/coupler selection, amps/pads/EQs, return path, performance, powering, 1.2/1.8 GHz extensions |
| 03 | [Reverse-engineering method](docs/03-reverse-engineering-method.md) | Clean-room rules, black-box experiment catalog (E01–E18), golden-test harness, the no-Lode-access path |
| 04 | [Architecture & roadmap](docs/04-architecture-and-roadmap.md) | Stack, repo layout, domain model, parity matrix, phased plan with acceptance criteria, risks |
