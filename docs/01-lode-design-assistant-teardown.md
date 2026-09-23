# 01 — Teardown of Lode Data *Design Assistant*

How the product is put together, rebuilt from its public manual at
<https://docs.lodedata.com/design/manual/>.

> **Evidence levels.** Every claim below carries one tag:
>
> - **[DOC]** stated in the Lode manual (source page linked).
> - **[INF]** inferred from documented behaviour. It is probably right but must be
>   confirmed with the experiments in [03-reverse-engineering-method.md](03-reverse-engineering-method.md).
> - **[UNK]** known to exist, but how it works is not yet known.
>
> This first pass was built from search-indexed excerpts of the manual, because
> the build environment could not reach `docs.lodedata.com` directly. Section 9 lists
> the pages to read in full on the next pass.

---

## 1. What the product is

| Aspect | Finding | Evidence |
|---|---|---|
| Category | CAE tool for designing and optimizing broadband coax / HFC networks, from city CATV systems to broadband LANs | [DOC] [Introduction](https://docs.lodedata.com/design/manual/) |
| Age / lineage | Introduced in **1983**. The UI is keystroke-driven (`NUM LOCK 9`, `ESC 9`, `DOT 2`, number-key toolbars), the FAQ recommends the *Terminal* font, and the key bindings still match its DOS origins | [DOC] [Introduction](https://docs.lodedata.com/design/manual/), [FAQ](https://docs.lodedata.com/FAQ/) |
| Licensing | USB hardware security key ("dongle"). Network licensing for 20+ seats | [DOC] [FAQ](https://docs.lodedata.com/FAQ/), [Glossary](https://docs.lodedata.com/design/manual/glossary/) |
| Core value | "Performs thousands of calculations instantly": levels, part numbers, equipment types, specs, footages, house counts, powering | [DOC] [Introduction](https://docs.lodedata.com/design/manual/) |
| Known versions | 7.04, 8.10, 10.50 (added the TSG column), 11.00 (added Tap Port Drop Types) | [DOC] [TSG](https://docs.lodedata.com/design/guides/tap-selection-group/), [Drop Types](https://docs.lodedata.com/design/guides/drop-types/) |
| Ecosystem | **Drafting Assistant**: AutoCAD add-on that imports DA networks (cable types, tap values, amps, data blocks) for strand maps and construction prints. **Fiber Module**: an Oracle-backed fiber database | [DOC] [lodedata.com/drafting-assistant](https://www.lodedata.com/drafting-assistant), [Fiber DB utilities](https://docs.lodedata.com/fiber/server/db-utilities/) |

**Key finding:** Lode is **not** a map-first GIS tool. It is a **table-driven tree
calculator**: a network is an ordered list of *nodes* (lines on screen) joined into
branches, evaluated against a set of user-editable *specification tables*. Maps
are handled separately, in AutoCAD, through the Drafting Assistant.

---

## 2. Reconstructed architecture

```
                 ┌──────────────────────────── SPEC FILES (user-maintained tables) ───────────────────────────┐
                 │ Parameters  Actives(.ATV)  Taps  Couplers  Cables  Performance   (+ TSGs inside Taps)        │
                 └───────────────┬───────────────────────────────────────────────────────────────────────────┘
                                 │ loaded per project (same base name recommended)          [DOC] Getting Started
                                 ▼
 ┌─────────────┐   ┌───────────────────────────────── CALC ENGINE ─────────────────────────────────┐
 │ NETWORK     │   │  forward levels @ N freq columns  →  auto-select taps / couplers / pads / EQs  │
 │ (.NTW)      │──▶│  return levels   @ M freq columns  →  cascade rules  →  performance (C/N,CTB…) │
 │ node list + │   │  powering: V/I per node → PS placement optimizers                              │
 │ branches    │   │  "Test network" → error list (red = out of spec, yellow = marginal)            │
 └─────────────┘   └───────────────┬───────────────────────────────────────────────────────────────┘
        ▲                          │
        │ 4 edit MODES             ▼
 Design / Entry /           REPORTS: BOM (single / map / powering), Active (xlsx), Network Tap,
 Active Entry / Powering    Performance Distribution, Power Supply, + misc.   Macros & Batch Macros
                                   │
                                   ▼
                     Drafting Assistant (AutoCAD) import → strand maps / as-builts
```

---

## 3. Data model

### 3.1 Network file (`.NTW`) [DOC] [Getting Started](https://docs.lodedata.com/design/manual/getting-started/)

- **Network**: "a relatively independent piece of design that is being worked on at one
  time" [DOC] [Glossary](https://docs.lodedata.com/design/manual/glossary/). It is usually one
  amplifier serving area or one node area. [INF]
- **Node**: "a logical (as opposed to physical) unit that corresponds to one line of the
  Entry, Power or Design screens". In the field it is usually a **pole** (aerial) or a
  **pedestal** (underground). [DOC] [Design Mode](https://docs.lodedata.com/design/manual/design/)
- **Node capacity** [DOC]: **1 active, up to 4 taps, 2 couplers (feeding up to 2
  branches), 1 power supply**, plus ancillary equipment and the computed levels and connectors.
- **Span**: each node line carries the **cable type, footage and house count** of the span
  that *arrives* at it. [DOC] (Utilities / Design Mode)
- **Displayed level** = level **after the footage on that line but before any equipment**,
  i.e. the input to the first device at that node. [DOC] [Design Mode](https://docs.lodedata.com/design/manual/design/)
- **Branch notation**: `[n]` is the number of the branch that starts at this node. The number
  directly left of it is the **coupler ID** that feeds it. Example from the manual:
  `11  [26]  8 [3]` means *active ID 11 (line extender) → 26 dB 4-port tap → DC-8 creating
  branch 3*. [DOC]
- **Equipment order inside a node**: active → taps → couplers. [INF] (from the
  example above)
- **Node address**: `branch.line`. The error text "Cannot select coupler at node x.x" is the
  clue. [INF]
- **Tap display**: the tap value is drawn inside one of **four bracket styles**, one per port
  count (max 8 ports). `[ ]` = 4-port. [DOC] / mapping of the other three [UNK]
- **Coupler orientation**: plain value = thru leg continues downstream on branch 1 and the
  tap leg feeds branch 2. A leading **negative** reverses this, so the high-loss leg goes
  downstream and the low-loss leg goes to the branch. A **double negative** exists. [DOC] /
  what the double negative means [UNK]
- Other per-node attributes: **TSG** (1–99), **map number**, **marked area**, **MDU / drop
  info**, **aerial vs underground**. [DOC] / [INF] (BOM grouping by marked area, map number,
  PS area, cable category)

### 3.2 Specification files [DOC] [Building Specification Files](https://docs.lodedata.com/design/manual/build-specs/)

"Data files external to the program that define every piece of equipment and every
operating parameter." A project normally shares one base name across all spec files.

| Spec file | Contents (known) | Evidence |
|---|---|---|
| **Parameters** | 6 tabs. Units (ft/m). **Frequencies tab**: forward *High* and *Low* by default, return *RH (42)* and *RL (5)* by default. Extra columns **F3–F6** (forward) and **R3–R4** (return) can be enabled and renamed. **Min tap output** per frequency and **tap window** (e.g. min 16 dBmV FH, window 10, so max 26). **Max return levels** (Rh, Rl, R3, R4). **Allow Over Equalization** checkbox. **Max LE Cascade** (1–3). **Maximum crossover** [UNK meaning]. **Pedestal sizing**. **Power supply info** | [DOC] [Parameters](https://docs.lodedata.com/design/manual/parameters/) |
| **Actives** (`.ATV`) | Active IDs. LE cascade IDs **11 / 21,22 / 31,32,33** must sit on the first lines. **Configuration table**: 8 custom configurations per base unit (plug-in combos such as `11`, `11a`, `11b`, `11c`), each with its own base distortion column #1–#8. Min input and **reserve gain** (e.g. reserve 2.00 on a 17 dBmV min input gives yellow at 17–19, red below 17). **Noise figure** (C/N single-unit = 59 + input − NF). **Voltage–current pairs** in ascending voltage (A1 = highest draw at Vmin). **Max amperage through** | [DOC] [Actives](https://docs.lodedata.com/design/manual/actives/), [Build Specs](https://docs.lodedata.com/design/manual/build-specs/), [Powering](https://docs.lodedata.com/design/manual/powering/) |
| **Taps** | Part number and Tap ID. Port count (≤ 8). **Tap-leg** and **thru-leg** losses at FH, FL, RH, RL, plus every extra enabled frequency. Self-terminating flag. Flag for whether it takes plug-in pads/EQs. Grouped into **Tap Selection Groups (TSG 1–99)**; a new group starts after a blank row | [DOC] [TSG](https://docs.lodedata.com/design/guides/tap-selection-group/), [Design Mode](https://docs.lodedata.com/design/manual/design/) |
| **Couplers** | Part number (≤ 14 chars) and Coupler ID. **Tap-leg(s)** and **thru-leg** losses per enabled frequency. Covers DCs, 2-way / 3-way equal and **unequal** splitters, no-loss splitters, and **drop splitters** (no thru leg; number of tap legs = number of ports) | [DOC] [Couplers](https://docs.lodedata.com/design/manual/couplers/) |
| **Cables** | Up to **100 cable types (IDs 0–99)**. Physical type, **attenuation factors**, **loop resistance per 1000 ft/m**, connector information. Set loop = **99** on fiber and unpowered cable so powering errors out if one is accidentally powered | [DOC] [Cables](https://docs.lodedata.com/design/manual/cables/) |
| **Performance** | Up to **12 distortion types**, one tab each (C/N, CTB, CSO, XMOD, …). Each has an **addition factor** (10 for C/N, i.e. 10·log; 20 for CTB, i.e. 20·log) and a **derate factor** (dB of degradation per 1 dB change in level) | [DOC] [Performance File](https://docs.lodedata.com/design/manual/performance/) |

### 3.3 Frequency model

Lode uses **named frequency columns**, not a continuous spectrum: 2 forward + 2 return by
default, and up to 6 forward + 4 return when enabled [DOC]. Every loss table (cable, tap,
coupler) needs a value in every enabled column. [DOC] This is its **biggest structural
limitation** for 1.2 / 1.8 GHz and DOCSIS 4.0 work, where you need total composite power
(TCP) and tilt across the whole band (see [02](02-hfc-engineering-core.md) §8).

---

## 4. Modes (workflow engine)

| Mode | Purpose | Evidence |
|---|---|---|
| **Entry** | Fast entry of strand data (spans, cable, footage, house counts, equipment), usually without the design tools [INF] | [DOC] [Menus](https://docs.lodedata.com/design/manual/menus/) |
| **Active Entry** | Quick design: levels and equipment values are **calculated as you type**. No menus or buttons. Suits small extensions. Reached with `NUM LOCK 9` or `ESC 9` from Design | [DOC] [Active Entry](https://docs.lodedata.com/design/manual/active-entry/) |
| **Design** | The main workspace. Auto and semi-auto selection, **Carry** (`3` picks up an active, `3` drops it elsewhere), **Backfeed** (`DOT 2`), insert vs exchange editing, **Test network** (signal, performance and cascade errors) | [DOC] [Design Mode](https://docs.lodedata.com/design/manual/design/), [Plant Extension](https://docs.lodedata.com/design/guides/plant-extension/) |
| **Powering** | Same grid, but shows **voltage and current** instead of signal levels. PS placement optimizers | [DOC] [Powering](https://docs.lodedata.com/design/manual/powering/) |

The typical Lode workflow, pieced together from the guides [INF]:

1. Field walk-out / strand map
2. **Entry**: spans, footages, house counts, branches
3. **Design**: place actives, auto-select taps, couplers, pads and EQs, then Test network; fix
   errors by carrying amps, backfeeding and changing coupler values
4. **Powering**: place and optimize power supplies
5. **Reports**: BOM, Active, Tap, Performance
6. **Drafting Assistant**: import into AutoCAD for construction prints

---

## 5. Algorithms (what is documented)

### 5.1 Tap selection [DOC] [Parameters](https://docs.lodedata.com/design/manual/parameters/), [Design Mode](https://docs.lodedata.com/design/manual/design/)
- Automatic and **semi-automatic** modes exist.
- Constraints: **min forward tap output** per frequency, **tap window** (max = min + window),
  **max return level**. Setting max return too low forces lower tap values. Both forward and
  return levels drive the choice.
- The choice is limited to the node's **TSG**. The global TSG dropdown applies to nodes where TSG = 0/blank.
- **Tap optimization**: can pick a *combination* of taps (e.g. a 2-port plus a 4-port instead of
  an 8-port) when the combined insertion loss is lower, to push more signal downstream.
- **MDU window / Tap Port Drop Types (v11)**: selection can instead be driven by **drop length,
  drop coupler loss, drop cable type, number of drops**. Ports are tagged RES / COM / MDU.

### 5.2 Coupler selection [DOC] [Design Mode](https://docs.lodedata.com/design/manual/design/)
- Picks a coupler that can feed both the thru path and the branch (including branches that
  are off screen). Fails with **"Cannot select coupler at node x.x"**.
- This requires a **bottom-up "required input level" calculation per subtree**. [INF]

### 5.3 Pads and equalizers [DOC] [Design Mode](https://docs.lodedata.com/design/manual/design/), [Actives](https://docs.lodedata.com/design/manual/actives/)
- Selected automatically for actives, and for taps flagged as taking plug-ins.
- **Pads never over-pad**: needing 1.6 dB of pad gives a 1.0 dB pad, i.e. the largest
  available value that does not exceed the requirement.
- **EQs never over-equalize** unless *Allow Over Equalization* is on. Then the closest fit
  wins, even if it over-equalizes.

### 5.4 Active placement and cascade rules [DOC] [Parameters](https://docs.lodedata.com/design/manual/parameters/), [Actives](https://docs.lodedata.com/design/manual/actives/)
- **Max LE cascade** ∈ {1, 2, 3}. IDs encode cascade position: `11` = only LE; `21`, `22` =
  1st and 2nd of 2; `31`, `32`, `33` = 1st, 2nd and 3rd of 3.
- Error text carries **X** (the device), **N** (# of LEs/amps before it) and **M** (# after it).
- **Reserve gain** gives a yellow flag, so the designer knows spacing is close to the limit.
- Placement is manual (Carry, Backfeed) with instant recalculation. The docs do not describe
  a fully automatic amplifier placement. [INF]

### 5.5 Performance [DOC] [Performance File](https://docs.lodedata.com/design/manual/performance/), [Build Specs](https://docs.lodedata.com/design/manual/build-specs/)
- Single-unit base distortion for each active configuration (#1–#8).
- Cascade combining uses the addition factor: `total = −k·log10(Σ 10^(−x_i/k))`, with k = 10 or 20 (or any user value).
- Level-dependent **derate** per dB of deviation from the reference level.
- **Performance Distribution report**: every distortion type **at every tap**.

### 5.6 Powering [DOC] [Powering](https://docs.lodedata.com/design/manual/powering/), [Cables](https://docs.lodedata.com/design/manual/cables/)
- Voltage drop comes from **loop resistance** (Ω per 1000 ft/m) multiplied by footage.
- Loads are **voltage-dependent step tables**: A1 from Vmin to V2, A2 from V2 to V3, and so on.
  These are constant-power-like switch-mode loads, so the solve is **nonlinear** and needs
  iteration. [INF]
- Limits: **max amps through** each device, PS capacity, min voltage per device.
  Errors: *excess current draw at PS*, *excess current through device*, *insufficient voltage*.
- **PS placement optimizers** (three objectives):
  1. **Balanced Draw**: equal current in at least two directions.
  2. **Maximum Low Voltage**: maximize the minimum device voltage.
  3. **Minimum Square Voltage Drop**: minimize Σ (voltage drop)² over powered devices.

---

## 6. Reports [DOC] [Reports](https://docs.lodedata.com/design/manual/reports/), [Utilities](https://docs.lodedata.com/design/manual/utilities/)

| Report | Content |
|---|---|
| **Bill of Materials** | Aerial, underground and total plant mileage, part numbers and quantities. Can be grouped by **marked area, PS area, cable category, map number**. Variants: **Single Network**, **Map BOM**, **Powering BOM** (per PS boundary). Residential vs **commercial/MDU** house counts |
| **Active report** (Excel only) | Per active: type, name, inputs, outputs, pads/EQs, and more |
| **Network Tap report** | Per tap, including **FWD TILT** and **RET TILT** columns |
| **Performance Distribution** | Every distortion type at every tap |
| **Power Supply report** | One of 9 miscellaneous reports |
| **Error display** | Red = out of spec, yellow = marginal |

Automation: **Macros** record keystrokes and mouse actions. **Batch macros** run a macro over
every network file in a folder, e.g. mass BOM runs. [DOC] [Macros](https://docs.lodedata.com/design/guides/macros/)

---

## 7. Where Lode's value actually lives

1. **The RF and powering math is standard industry practice** (see [02](02-hfc-engineering-core.md)).
   Nothing proprietary is needed to reproduce it.
2. The actual value is in:
   - **Selection heuristics** (tap, coupler, pad, EQ, tap-combination optimization) that match
     how an experienced designer expects equipment to be chosen.
   - **The powering solver and its three PS-placement objectives.**
   - **Workflow speed**: instant recalculation while editing, carry and backfeed, macros.
   - **The equipment libraries**, which each customer builds and maintains.
3. **Structural weaknesses we can beat:**
   - Discrete frequency columns (max 6 forward / 4 return), so no full-band TCP or tilt
     modeling at 1.2 / 1.8 GHz, and nothing FDX- or ESD-aware.
   - Analog-era performance model (CTB/CSO/XMOD) with no native MER/SNR or CIN budget for
     all-digital QAM/OFDM loading.
   - Maps live in a separate AutoCAD product, so footage and house counts are keyed in by hand
     instead of derived from geometry.
   - Dongle-bound desktop software, not collaborative, and hard to diff or review designs.

---

## 8. Open questions (drive the experiments in 03)

| # | Question | Why it matters |
|---|---|---|
| Q1 | How are cable attenuation factors stored (dB/100 ft per column, or model coefficients)? Is there any interpolation? | Level accuracy |
| Q2 | Is there a design temperature, and how do attenuation and loop resistance vary with it? | Hot/cold checks |
| Q3 | How are connector losses applied (per device port? per span end?) | Small but cumulative error |
| Q4 | Active model: fixed output levels (output-referenced), or input + gain? How are tilt and EQ applied? | Core of level calc |
| Q5 | Exact tap-selection order and tie-breaking; how house count maps to port count | Matching designer expectations |
| Q6 | What does the coupler "double negative" mean? | Network notation |
| Q7 | How is the return path referenced (unity gain at return amp inputs?) | Return design |
| Q8 | What is "maximum crossover" in Parameters? | Unknown design rule |
| Q9 | How are pedestals sized? | BOM / underground |
| Q10 | Does the powering solver interpolate the V–I steps or use them as-is? How does it converge? | Voltage accuracy |
| Q11 | What candidate set and search do the PS optimizers use (every node? greedy?) | Reproducing the optimizer |
| Q12 | How are levels rounded for display vs used internally? | Golden-test tolerance |
| Q13 | Mapping of the four tap bracket styles to port counts | Import and display parity |

## 9. Pages to read in full on the next pass

`/design/manual/` (intro), `getting-started/`, `menus/`, `design/`, `active-entry/`,
`powering/`, `parameters/`, `actives/`, `taps` (if present), `couplers/`, `cables/`,
`performance/`, `build-specs/`, `reports/`, `utilities/`, `glossary/`;
guides: `macros/`, `plant-extension/`, `tap-selection-group/`, `drop-types/`;
`/FAQ/`, `/design/install/`.
