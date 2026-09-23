# 04 — Target Architecture & Roadmap

What we build: an HFC design tool that **reaches Lode parity on the calculations**
([01](01-lode-design-assistant-teardown.md), [02](02-hfc-engineering-core.md)), is
**verified by golden tests** ([03](03-reverse-engineering-method.md)), and **goes beyond
Lode** where Lode is structurally weak: maps, full-band 1.2/1.8 GHz, digital performance,
collaboration.

## 1. Design principles

1. **The engine is a pure library.** Network + specs + rules in, results + violations out.
   No UI, no I/O, deterministic. Everything else (CLI, web UI, reports) sits on top of it.
2. **Designs and specs are data**: JSON/YAML in git. They can be diffed, reviewed and
   reproduced. A design review is a pull request.
3. **Every number is explainable.** The engine records *why* (e.g. "tap 14 rejected:
   port 15.99 < min 16.00") so designers can trust the auto-selection.
4. **Units are explicit** (`dBmV`, `dB`, `ft|m`, `MHz`, `°F|°C`). Round only for display.
5. **Parity first, then improve.** Named Lode-style frequency columns are a *view* over a
   continuous frequency model, and Lode-style error codes sit next to richer diagnostics.

## 2. Stack (recommendation)

| Layer | Choice | Why |
|---|---|---|
| Engine | **TypeScript** (strict), pure functions, `vitest` | One language for engine and UI; runs in the browser (instant recalculation while editing, as in Lode's Active Entry) and in Node (CLI, batch runs, CI) |
| Spec library | YAML files validated by JSON Schema (`zod`) | Human-editable like Lode's spec files, but versioned |
| I/O | CSV/XLSX (reports, Lode report import), GeoJSON/KML/Shapefile/DXF (maps) | Interop with Excel, GIS and AutoCAD |
| Web UI | React + **MapLibre GL** map, with a **node-grid editor** docked beside it | Map-first like modern tools, with the fast tabular editing Lode designers expect |
| Storage | Files first; later **Postgres + PostGIS** for multi-user work | Start simple |
| Repo | pnpm monorepo | `packages/engine`, `packages/catalog`, `packages/io`, `apps/cli`, `apps/web`, `validation/` |

Network sizes are small (thousands of nodes per node area), so performance is not a
constraint. Correctness and editing speed are.

## 3. Repository layout

```
docs/                       analysis & plans (this folder)
packages/
  engine/
    model/                  types: Network, Location, Span, Device, Port, Spec types
    rf/forward.ts           level propagation (02 §2)
    rf/select.ts            two-pass tap/coupler selection, pads/EQs (02 §3–4)
    rf/return.ts            unity-gain return path (02 §5)
    perf/                   analog (C/N, CTB, CSO, XMOD) + digital (SNR/MER, CIN, TCP)
    power/                  solver + PS optimizers (02 §7)
    rules/                  violation catalog (red/yellow), cascade rules
    autodesign/             amp placement, PS placement
    explain/                decision trace
  catalog/                  spec schemas + vendor libraries (cables, actives, taps, couplers, pads, EQs, PS)
  io/                       importers/exporters: CSV/XLSX reports, GeoJSON, DXF, Lode report normalizer
apps/
  cli/                      `hfc calc`, `hfc report bom`, `hfc validate`, batch mode (≈ Lode batch macros)
  web/                      map + grid editor, live recalc, reports
validation/
  golden/<case>/            probe + real networks with expected results (03 §4)
```

## 4. Domain model (core types)

```ts
// ---------- specs (≈ Lode spec files) ----------
type FreqMHz = number;
interface Curve { points: [FreqMHz, number][]; model?: { a: number; b: number } } // loss/gain vs f; cable fit a·√f + b·f

interface CableSpec   { id: string; name: string; attenuation: Curve /* dB per 100 ft|m @ Tref */;
                        tempCoeffPerDeg: number; loopOhmsPer1000: number /* 99 = not powerable */;
                        connectorPartNo?: string; category: 'hardline'|'drop'|'fiber' }
interface TapSpec     { id: string; partNo: string; value: number; ports: 1|2|4|8; terminating: boolean;
                        tapLeg: Curve; thruLeg?: Curve; maxAmpsThrough: number; takesPlugins: boolean; tsg: number }
interface CouplerSpec { id: string; partNo: string; kind: 'DC'|'splitter'|'drop-splitter';
                        legs: Curve[] /* [thru, tap1, tap2…]; drop-splitter has no thru */; maxAmpsThrough: number }
interface ActiveSpec  { id: string; partNo: string; role: 'node'|'trunk'|'bridger'|'LE'|'rpd';
                        fullGain: Curve; minInput: number; reserveGain: number;
                        designOutput: { f: FreqMHz; level: number }[];      // output-referenced alignment
                        configs: ActiveConfig[];                           // ≈ Lode's 8 columns per base unit
                        noiseFigure: Curve; tcpMax?: number;
                        vi: { vMin: number; amps: number }[] | { watts: number; efficiency: number };
                        maxAmpsThrough: number; split: SplitId }
interface PerfType    { name: string; additionFactor: number; derate: number; ref: 'input'|'output' } // ≈ Lode Performance tabs
interface DesignRules { units: 'ft'|'m'; tempRef: number; tempHot: number; tempCold: number;
                        columns: { name: string; f: FreqMHz; dir: 'fwd'|'ret' }[];   // Lode FH/FL/RH/RL/F3..
                        minTapPort: Record<string, number>; tapWindow: number; maxReturn: Record<string, number>;
                        returnAmpInput: Record<string, number>; allowOverEq: boolean;
                        maxLeCascade: 1|2|3; maxCascade?: number; psVoltage: 60|90; minDeviceVolts: number }

// ---------- network (≈ Lode .NTW) ----------
interface Location { id: string; kind: 'pole'|'pedestal'|'vault'|'building'; geom?: [number, number];
                     mapNo?: string; markedArea?: string }
interface Span     { id: string; from: string /* upstream location */; to: string; cableId: string;
                     length: number; placement: 'aerial'|'underground'; geom?: [number, number][] }
interface Device   { id: string; at: string /* location */; order: number;  // signal order within location
                     kind: 'active'|'tap'|'coupler'|'ps'|'powerInserter'|'terminator';
                     specId?: string;                      // undefined ⇒ auto-select
                     locked?: boolean;                     // user override, never auto-changed
                     orientation?: 'thruDownstream'|'tapDownstream';   // Lode −/−− notation
                     feeds?: { port: string; spanId: string }[];
                     plugins?: { pad?: string; eq?: string; config?: string };
                     tsg?: number; homes?: { res: number; com: number; mdu: number } }
interface Network  { id: string; rootDeviceId: string; locations: Location[]; spans: Span[]; devices: Device[] }

// ---------- results ----------
interface PortLevel  { deviceId: string; port: string; f: FreqMHz; dbmv: number }
interface Violation  { code: string; severity: 'red'|'yellow'; at: string; message: string; data?: unknown }
interface CalcResult { levels: PortLevel[]; selections: Record<string, string>; perf: unknown;
                       power: unknown; violations: Violation[]; trace: unknown[] }
```

**Topology:** the RF network must be a **rooted tree** (validate that it is acyclic and that
every device is reachable). Power zones are sub-trees bounded by power blocks.

## 5. Engine pipeline

```
validate topology
 → forward levels (provisional specs)
 → PASS 1 bottom-up Req()  → PASS 2 top-down select taps/couplers/pads/EQs   (repeat until stable, max 5)
 → return levels & max-return checks  (feeds back into tap selection → repeat)
 → performance at every tap (analog and/or digital, TCP)
 → powering solve (+ optional PS optimizer)
 → rules → violations (red/yellow) → reports
```
Locked devices are never changed. Auto-selected ones are recorded in `selections` with a trace.

## 6. Lode feature → our module (parity matrix)

| Lode feature | Our module | Phase |
|---|---|---|
| Spec files: Parameters, Actives, Taps, Couplers, Cables, Performance | `catalog` + `DesignRules` | 1 |
| Network node list, branches, coupler orientation | `model` + grid editor | 1 / 5 |
| Forward levels at named columns | `rf/forward` | 2 |
| Auto/semi-auto tap selection, TSG, tap window, tap combos | `rf/select` | 3 |
| Coupler selection, "cannot select coupler" | `rf/select` | 3 |
| Pad/EQ selection (never over-pad/over-EQ; allow over-EQ) | `rf/select` | 3 |
| Reserve gain flags, LE cascade rules (11/21/22/31/32/33) | `rules` | 3 |
| Return levels, Max Signals | `rf/return` | 3 |
| Performance file (12 types, addition factor, derate), Performance Distribution | `perf` | 4 |
| Powering mode, V–I tables, max amps through, PS errors | `power` | 4 |
| PS optimizers: Balanced Draw, Max Low Voltage, Min Square Voltage Drop | `autodesign` | 4 |
| BOM (single / map / powering; marked area, map no., cable category; RES/COM/MDU) | `reports` | 4 |
| Active report, Network Tap report (FWD/RET tilt), PS report | `reports` | 4 |
| Active Entry (instant recalculation while typing), Carry, Backfeed | `apps/web` | 5 |
| Macros / batch macros | `apps/cli` batch + scriptable API | 5 |
| MDU window / tap-port drop types | `rf/select` + drops | 5 |
| Drafting Assistant (AutoCAD) | `io` DXF/GeoJSON export, map-native UI | 5–6 |
| **Beyond Lode:** full-band / TCP / 1.8 GHz, digital MER/CIN, split & FDX, auto amp placement, temperature corners, collaboration | `rf`, `perf`, `autodesign`, web | 6 |

## 7. Roadmap

Effort is for one developer and is rough. The phases are sequential; each ends with its
acceptance test passing.

| Phase | Scope | Deliverables | Acceptance | Size |
|---|---|---|---|---|
| **0. Groundwork** | Collect the inputs (03 §6); full-text pass of the Lode manual; EULA check | Updated 01 with more VERIFIED/DOC tags; the equipment and design-rule inventory | Every Q# in 01 §8 has an owner and a planned experiment | ~1 wk |
| **1. Specs & model** | Schemas, validators, catalog for **your** equipment; network JSON format; topology validation | `packages/catalog`, `packages/engine/model`, 1 sample network | Your vendors' cables, taps, couplers and actives load and validate; the sample network passes topology checks | 1–2 wk |
| **2. Forward RF** | Cable model fit, level propagation, device order, connectors | `rf/forward`, CLI `hfc calc` | Probes E01–E05 match (Lode or hand calcs) ±0.05 dB | 1–2 wk |
| **3. Selection & return** | Two-pass tap/coupler selection, pads/EQs, reserve and cascade rules, return path | `rf/select`, `rf/return`, `rules` | E06–E13 match; **choices identical** on 3 real networks | 2–3 wk |
| **4. Perf, power, reports** | Analog perf + derate; powering solver + 3 optimizers; BOM, Active, Tap, Perf Distribution, PS reports (CSV/XLSX) | `perf`, `power`, `autodesign/ps`, `reports` | E14–E17 match; BOM line-for-line match on the golden cases | 2–3 wk |
| **5. Designer UX** | Web app: map + node grid, live recalc, carry/backfeed, locks, explain panel, drops/MDU, batch CLI | `apps/web`, `apps/cli` | A designer re-creates a real amp area faster than in their current process, with zero red violations | 3–5 wk |
| **6. Beyond Lode** | Full-band TCP, 1.2/1.8 GHz, digital SNR/MER + CIN, split/FDX, temperature corners, auto amp placement, GIS import (poles/addresses → spans/homes), DXF export | `perf/digital`, `autodesign/amps`, `io/gis` | A 1.8 GHz upgrade study on an existing area yields TCP/MER-compliant designs with a BOM delta | 4–6 wk |

## 8. Risks & mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Docs host blocked / manual only partly known | Wrong assumptions | Evidence tags; E-series experiments; allow `docs.lodedata.com` in the environment |
| No licensed Lode seat to test against | No parity oracle | Hand calcs + vendor guides + **field readings** (03 §5) |
| Inaccurate vendor data (tap losses vs frequency, amp gain curves) | Level error larger than the model error | Store raw datasheet points and fit residuals; spot-check with sweep data |
| Rounding and tie-break differences | Different equipment choices | Settle Q12 early (E06); make rounding a rule setting |
| Scope creep into GIS/CAD | Delays the engine | The engine and golden tests come first (Phases 1–4) before UI/GIS |
| EULA / IP exposure | Legal | Clean-room rules (03 §1); no binary RE, no dongle bypass, own names and UI |

## 9. Immediate next steps

1. Allow `docs.lodedata.com` in this environment's network settings, then run the
   full-text pass and update 01.
2. Send the equipment list + datasheets and your design rules (03 §6) so Phase 1 can start
   with real specs instead of placeholders.
3. Choose golden cases: 3–5 existing designs with their reports or prints.
4. Scaffold the monorepo and start Phase 1.
