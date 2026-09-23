# 03 — Reverse-Engineering Method

We reverse engineer **behaviour, not code**. The goal is a clean-room tool whose numbers
match Lode's on the same inputs, which is a stronger guarantee than reading any binary would
give.

## 1. Ground rules (clean room)

1. **Allowed inputs:** Lode's public manual; our own observations of a **licensed** copy
   (screens, exported reports); manufacturer datasheets; industry references; field
   measurements from our own plant.
2. **Not allowed:** decompiling or disassembling Lode binaries; bypassing or emulating the USB
   security key; copying the manual's text or screens into our product; using "Lode Data" or
   "Design Assistant" as names in our product.
3. **Read the Lode licence (EULA) before running experiments on a licensed seat.** Some licences
   restrict benchmarking or reverse engineering. If yours does, use the "no Lode access" path
   in §5. *(This is not legal advice. For anything commercial, ask counsel.)*
4. **Importing Lode files:** start with **documented exports** (the Active report is Excel;
   other reports print or export to files). Parsing the native `.NTW` / `.ATV` formats is a
   separate, lower-priority decision, made only after reviewing the licence.

## 2. Method: black-box differential testing

```
 Probe network (tiny, controlled)  ──►  Lode (licensed seat)  ──►  export/report  ─┐
                  │                                                                 ├─► diff (tolerance) ─► model fix
                  └──────────────────►  our engine            ──►  same schema    ─┘
```

1. Build **minimal probe networks** that isolate one behaviour each (catalog below).
2. Sweep one input at a time (length, level, house count, spec value) in small steps and
   record Lode's output.
3. Fit or confirm our formula. Record the result as a **finding** with an evidence tag
   (DOC/INF → **VERIFIED**) in [01](01-lode-design-assistant-teardown.md).
4. Freeze each probe and its expected output as a **golden test** in `validation/golden/`,
   so parity never regresses.
5. Then scale up: **real production networks** (tens to hundreds of nodes), compared node by node.

## 3. Experiment catalog

Each experiment answers one of the open questions (Q#) in [01 §8](01-lode-design-assistant-teardown.md#8-open-questions-drive-the-experiments-in-03).

| ID | Hypothesis / question | Setup | Record | Pass when |
|---|---|---|---|---|
| **E01** Cable model (Q1) | Span loss = attenuation(column) × length / 100, with no interpolation | 1 active → 1 span, one cable type; lengths 50, 100, 200, 500, 1000 ft | Levels at every enabled column | Loss is linear in length; slope matches the Cables-file value |
| **E02** Extra columns (Q1) | F3–F6 / R3–R4 require explicit per-column data | Enable F3; leave the cable value blank, then fill it | Level at F3 | We know whether Lode interpolates |
| **E03** Temperature (Q2) | Some design temperature scales attenuation and loop resistance | Look for a temperature field in Parameters; vary it | Levels, voltages | Coefficient recovered, or confirmed absent |
| **E04** Connectors (Q3) | Connector loss is applied per device port | Same span with and without devices; vary connector spec | Levels, BOM connector counts | Loss per connector and count rule known |
| **E05** Device order in node | active → taps (1..4) → couplers | Node with active + 2 taps + DC | Levels at each port and branch | Order confirmed |
| **E06** Tap selection (Q5, Q12) | Picks the highest value with port ≥ min, within window, meeting max return | 1 span + 1 tap; sweep input in 0.01 dB steps across each threshold | Tap chosen | Threshold function matches, including rounding |
| **E07** House count → ports (Q5) | Port count = smallest family ≥ homes; combinations allowed | Homes = 1..10 | Tap(s) chosen | Mapping and combination rule known |
| **E08** Tap combinations | Lowest summed insertion loss wins | Homes = 6 (2+4 vs 8) | Choice | Matches §3.4 of [02](02-hfc-engineering-core.md) |
| **E09** Active model (Q4) | Output-referenced: fixed design outputs; pad/EQ fill the gap | 1 active; sweep input ±10 dB; sweep input tilt | Output, pad, EQ chosen | Formula in [02 §4](02-hfc-engineering-core.md) reproduces every case |
| **E10** Reserve gain & flags | Yellow in [min, min+reserve), red below min | Sweep input around min | Colour / error | Thresholds match |
| **E11** Cascade rules | IDs 11/21/22/31/32/33 and the (X, N, M) error format | Chain 1–4 LEs with various IDs | Errors | Rule table reproduced |
| **E12** Coupler selection (Q6) | Req-based two-pass selection; meaning of the double negative | One DC with two branches of varying need; try −, −− | Coupler chosen, errors | Selection and notation known |
| **E13** Return path (Q7) | Unity gain referenced to the return-amp input; Max Signals caps the required return level | Vary tap values and spans upstream of a return amp | Return levels per port | Formula in [02 §5](02-hfc-engineering-core.md) matches |
| **E14** Performance | Addition factor and derate as documented | 1 amp at ref output ±1 dB; cascades of 2 and 3 | C/N, CTB, CSO at taps | ≤ 0.1 dB difference |
| **E15** Powering solve (Q10) | Loop R × length; step-table loads; iterative solve | 1 PS + 1 load at 500/1000/2000 ft; then 3 loads | V and I per node | ≤ 0.1 V difference |
| **E16** PS optimizers (Q11) | Candidate set = every node; the objective functions in [02 §7.3](02-hfc-engineering-core.md) | Small asymmetric tree, run all three optimizers | PS location chosen | Same pick |
| **E17** BOM rules (Q9) | Footage by aerial/UG; connectors; pedestals sized by device count | Known small network | BOM lines | Line-for-line match |
| **E18** Crossover (Q8) | Meaning of "maximum crossover" | Vary the parameter and look for errors or changes | Any effect | Meaning documented |

## 4. Golden-file harness

- **Layout:** `validation/golden/<case>/` holds `input.network.json`, `specs/*.yaml`,
  `lode/*.csv` (reports exported from Lode) and `expected.json` (normalized).
- **Normalizer:** converts Lode report exports (Active, Tap, Performance Distribution, BOM,
  Power Supply) to one CSV schema: `node_id, device, freq_col, level_dbmv, …`.
- **Diff tolerances (start values; tighten once Q12 is answered):**
  - levels ±0.05 dB
  - voltages ±0.05 V
  - performance ±0.1 dB
  - **equipment choices must match exactly** (tap values, pads, EQs, couplers)
  - BOM quantities must match exactly
- **Report:** a per-node mismatch table. The first mismatch along a path is the root cause,
  and everything downstream of it is derived.
- **CI:** every golden case runs on every commit.

## 5. If there is no Lode access

The tool can still be built and trusted. Swap the oracle:

1. **Hand and spreadsheet calcs** for every probe in §3 (the same probes, with a different oracle).
2. **Manufacturer design guides and datasheets** (published example cascades, tap tables).
3. **Field truth:** meter or sweep readings from your own plant (amp inputs and outputs, tap
   ports, EOL), compared with our model of the **as-built** network. This is the best oracle,
   since it checks against the real plant rather than against Lode.
4. Keep the Lode-parity features (Lode-style named columns, error codes, reports), so that when
   access does become available the golden harness can be switched on.

## 6. What to collect now (checklist)

- [ ] Give the build environment access to `docs.lodedata.com`, for a full-text pass over every page listed in 01 §9
- [ ] Our equipment list: cable types, amp and node models, tap and coupler families, pads, EQs, power supplies, with **datasheets**
- [ ] Our design rules: min/max tap levels, window, amp output levels and tilt, return input level, splits, max cascade, temperature range
- [ ] 3–5 existing designs (Lode files plus exported reports, or construction prints) to act as golden cases
- [ ] Field readings for at least one designed amp area
- [ ] The Lode EULA text (see §1.3)
