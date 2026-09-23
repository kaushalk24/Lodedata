# 02 — HFC Engineering Core (the calculation engine)

This is the math and the algorithms our tool must implement. It is standard coax/HFC
practice, **not copied from Lode**. Where Lode behaviour is documented, it is cross-referenced
to [01](01-lode-design-assistant-teardown.md) so we can reach parity first and then go
further.

**Conventions**

- Levels in **dBmV** (75 Ω); losses and gains in **dB**. A loss is a positive number that
  gets subtracted.
- **Tilt** `T = L(f_high) − L(f_low)`. Positive tilt means the high channels sit higher (up-tilt).
- Frequencies in MHz. Lengths are stored in **feet or metres, per project** (as Lode does), and
  converted internally to metres.
- Internal math is float64. Rounding happens **only at display and report time**, because the
  worked example below shows a 0.01 dB rounding difference can change a tap value.
- All example numbers are **illustrative**. Always load real values from manufacturer
  datasheets into the spec library.

---

## 1. Cable attenuation

Two loss mechanisms: conductor (skin-effect) loss, which grows with √f, and dielectric loss,
which grows with f.

```
α(f, T) = [ a·√f + b·f ] · [1 + c·(T − T_ref)]            dB per 100 ft (or per 100 m)
```

- Fit `a, b` by least squares to the datasheet points (typically 5 MHz to 1794 MHz).
  Store the **datasheet points themselves** and the fitted coefficients, and warn when the
  fit residual is more than 0.05 dB/100 ft.
- `c ≈ 0.0011 /°F` (≈ 0.2 %/°C). This is the industry rule of thumb of *about 1 % per 10 °F*.
  `T_ref = 68 °F (20 °C)`.
- Span loss: `Loss_span(f) = α(f,T) · length/100 + connector losses`.
- Lode stores one attenuation value per enabled frequency column (FH, FL, RH, RL, F3–F6,
  R3–R4). A continuous model reproduces those exactly when evaluated at the column
  frequencies, and it also supports full-band work (§8).

## 2. Forward level propagation

Walk the tree from the source (fiber node RF output or amplifier output), for every frequency `f`:

```
L_in(node) = L_out(parent) − Loss_span(f)                    # the level Lode displays: after footage, before equipment
then, for each device at the node in order (active → taps → couplers):
    tap:      port_out = L − tap_leg(f)      ;  L = L − thru_leg(f)        (terminating taps end the line)
    coupler:  branch_in = L − tap_leg(f)     ;  L = L − thru_leg(f)        (negative orientation swaps legs)
    splitter: each leg  = L − leg_loss_i(f)
    active:   L = amplifier model (§4)
```

## 3. Taps and couplers: two-pass selection

### 3.1 Why two passes
- On a **single line**, choosing the **highest tap value that still meets the minimum
  port level** is *optimal*: within one port-count family, a higher tap value has lower
  insertion loss, so it leaves the most signal for everything downstream. A single greedy
  forward pass is enough.
- At a **coupler or splitter** you must know what each subtree *needs* before choosing
  the coupler value. That calls for a **bottom-up "required input" pass** first. Lode's
  "Cannot select coupler at node x.x" is exactly the failure of this check.

### 3.2 Pass 1: bottom-up required input `Req(v, f)`
```
Req(past end-of-line) = −∞   (nothing required)
At node v with span loss S, tap candidates C (limited to v's TSG and port count ≥ homes at v).
Walk v's devices in REVERSE signal order (couplers → taps → active):
    need = Req(thru child)
    if v has a coupler feeding branch child b:
        need = min over coupler k of max( thru_k(f) + need,  tap_k(f) + Req(b, f) )
    for each tap position at v, last → first:
        need = min over t in C of max( Min_port(f) + tap_leg_t(f),  thru_leg_t(f) + need )
        # terminating taps are candidates only when need = −∞
    if v has an active:
        check_output(active, need)         # its design output must cover `need`, else error
        need = In_min + Reserve            # upstream only has to feed the active's input
    Req(v, f) = S(f) + need
```
Do this for each constrained frequency (at least FH, plus FL when a minimum is set on it).
For each node, keep the argmin tap and coupler as the **provisional** choice.

### 3.3 Pass 2: top-down selection
```
L = L_in(v)
for each tap position: pick the HIGHEST tap value t such that
      L − tap_leg_t(f) ≥ Min_port(f)                for every constrained f
      L − tap_leg_t(f) ≤ Min_port(f) + Window       (tap window, Lode Parameters)
      Return_required(t) ≤ Max_return(r)            for every return column r (§5)
   and L − thru_leg_t(f) ≥ Req(downstream, f)       (do not starve downstream)
at a coupler: among couplers with  L − thru_k ≥ Req(thru child)  AND  L − tap_k ≥ Req(branch child)
      pick the one with the LOWEST thru loss (keeps the most signal on the continuing line)
      none feeds both → pick the lowest thru loss among those that still feed the branch
                        (a short thru side shows up as errors at the downstream nodes where it runs out)
      none feeds the branch → error "cannot select coupler at node b.n" (Lode reports this when
                        off-screen branches cannot be fed; an amplifier is needed upstream or in the branch)
```

### 3.4 Tap-combination optimization (Lode feature)
Where a node has more homes than one tap covers, also try **combinations** (e.g. 2-port + 4-port
instead of 8-port) and keep the one with the lowest summed thru loss that still satisfies §3.3.

### 3.5 Pads and EQs in taps
Only for taps flagged as taking plug-ins. The same rules as actives (§4.2) apply.

### 3.6 Worked example: one line extender feeding six 4-port taps at 1002 MHz

Assumptions (illustrative): LE output 46.0 dBmV at 1002 MHz. Cable 1.55 dB/100 ft at 1002 MHz.
Min port 16.0 dBmV, window 10 dB. 4-port tap values 8 (terminating), 11, 14, 17, 20, 23, 26, 29, 32
with thru losses 32/29: 0.9, 26: 1.0, 23: 1.2, 20: 1.5, 17: 2.0, 14: 2.8, 11: 3.6.

| Node | Span (ft) | Span loss | Input (displayed) | Tap chosen | Port out | Thru loss | Level to next |
|---|---|---|---|---|---|---|---|
| 1 | 150 | 2.33 | 43.68 | 26 | 17.68 | 1.0 | 42.68 |
| 2 | 125 | 1.94 | 40.74 | 23 | 17.74 | 1.2 | 39.54 |
| 3 | 140 | 2.17 | 37.37 | 20 | 17.37 | 1.5 | 35.87 |
| 4 | 130 | 2.02 | 33.85 | 17 | 16.85 | 2.0 | 31.85 |
| 5 | 120 | 1.86 | 29.99 | **11** | 18.99 | 3.6 | 26.39 |
| 6 | 120 | 1.86 | 24.53 | 8 (term.) | 16.53 | — | — |

At node 5 a **14 dB tap would give 15.99 dBmV, 0.01 dB below the minimum**, so the engine
drops to 11. If you round the input to 30.0 before selecting, you get 14 instead. This is why
the rounding rule (open question Q12 in 01) must be pinned down before golden tests can pass.

## 4. Actives (amplifiers, nodes, line extenders)

### 4.1 Output-referenced model (industry standard; confirm against Lode with experiment E09)
An amplifier is aligned to fixed **design output levels** at a reference high frequency and a
reference low frequency (set per active type or per Parameters). Pads and EQ condition the input
so the amp can reach those outputs:

```
Operational gain (at f)   G_op(f) = Out_design(f) − In(f)
Full gain                 G_full(f)           (datasheet, including the built-in slope S_amp = G_full(FH) − G_full(FL))
Min input                 In_min(FH)          flag RED if In < In_min; YELLOW if In < In_min + Reserve_gain   (Lode: reserve gain)
```

### 4.2 EQ and pad selection (Lode rules)
```
Input tilt           T_in  = In(FH) − In(FL)
Target output tilt   T_out = Out_design(FH) − Out_design(FL)
Needed EQ tilt       E     = T_out − S_amp − T_in
EQ choice            largest available EQ ≤ E            (never over-equalize)
                     | closest to E                       (if "Allow Over Equalization")
Needed pad           P     = In(FH) + G_full(FH) − EQ_loss(FH) − Out_design(FH)
Pad choice           largest available pad ≤ P           (never over-pad; 1.6 dB needed → 1.0 dB pad)
Resulting output     Out(f) = In(f) − pad(f) − EQ_loss(f) + G_full(f)   → report the deviation from design
```
Plug-in configurations (Lode's 8 columns per base unit): model each configuration as the
base unit plus a list of plug-ins (pads, EQs, diplex filter, ADU/AGC, return module). Each
configuration has its **own gain and distortion data**.

### 4.3 Cascade rules
- Keep a **cascade depth** per active: node + N, and the number of LEs after the last
  trunk/bridger.
- Enforce `Max LE cascade ∈ {1,2,3}` and report errors as `(X, N before, M after)`, as Lode does.
- Modern design rules add **N+0**, **N+1** and **N+x max** limits, set per project.

### 4.4 Automatic amplifier placement (our addition; Lode placement is manual)
Walk each path downstream. When a node's `Req(v)` cannot be met from the available level,
place a new active at the **furthest upstream candidate location whose input is still at least
`In_min + Reserve`**. Then re-run passes 1–2. Candidates must be powered locations
(poles/pedestals), and each placement must satisfy the cascade limits. Keep the manual tools too:
*carry* (move an active and recalculate), *backfeed* (feed taps back toward the source from an amp).

## 5. Return (upstream) path: unity gain

Design goal: **every return amplifier's return input sees the same level**, whichever home
transmits. Each return amp's gain therefore equals the loss of the path back to the next
upstream return input.

```
Return_required(tap port p, r) = RAI(r)                                  # design return-amp input level, e.g. 15 dBmV per 6.4 MHz
                               + tap_leg(r) at p
                               + Σ thru/coupler losses(r) and cable loss(r) from p up to the serving return amp input
                               + drop loss(r) (drop cable + splitters, MDU window)
Check: Return_required ≤ Max_return(r)       # Lode "Max Signals" Rh, Rl, R3, R4 → drives tap selection (§3.3)
                                             # set from modem Tx capability minus margin (fleet dependent)
Return amp output(r) = RAI_upstream(r) + loss(r) back to the upstream return amp input (or node return input)
```
Check at both the **highest and lowest return frequencies**, and at **hot and cold
temperature**. The spread between the best-case and worst-case home is what uses up the modem
transmit window.

## 6. Performance: legacy analog model (Lode parity)

Single unit:
```
C/N_1 = 59.2 + In − NF                  (4 MHz NTSC noise bandwidth; Lode uses 59)
      = 57.4 + In − NF                  (6 MHz)
distortion_1(Out) = D_ref − derate·(Out − Out_ref)   # CTB derate 2, CSO 1, XMOD 2 (dB per dB)
```
Cascade, using the addition factor `k` (a user value per distortion type, as in Lode):
```
D_total = −k · log10( Σ_i 10^(−D_i / k) )      # k = 10 C/N, 20 CTB/XMOD, ~15 CSO (configurable)
```
Examples: 3 identical amps at C/N 61 dB give **56.2 dB**. 3 amps at CTB 70 dBc give **60.5 dBc**.
Calculate at **every tap** (Lode's *Performance Distribution* report) by combining every active
upstream of that tap, plus the node/optical contribution as another term.

## 7. Powering

### 7.1 Model
- Coax carries 60 or 90 VAC quasi-square-wave. Each span is a resistor
  `R = R_loop(Ω/1000 ft) · L/1000 · [1 + α_R (T − 20 °C)]` with α_R ≈ 0.0039/°C (Cu), ≈ 0.0040/°C (Al).
- **Loads** are actives, modeled as switch-mode (roughly constant power). Two options:
  - Lode-style **step table** (V1..Vn → A1..An, A1 the highest draw at the lowest voltage).
  - Continuous `I = P / (V·η)`. Offer both and use the table for parity.
- Passives: `Max amps through` (and power blocking or power-passing per port). Cables: fiber and
  unpowered cable get `R_loop = 99` so they error if powered, as Lode does.

### 7.2 Solver (tree, one or more supplies separated by power blocks)
```
V(all) = V_ps
repeat until max |ΔV| < 0.01 V (cap iterations and damp the step when the step table oscillates):
    I_load(n)      = f_load(V(n))
    I_through(span)= Σ I_load of everything downstream of the span within the PS zone
    V(child)       = V(parent) − I_through(span) · R(span)
checks: V(n) ≥ V_min(n) ; I_through ≤ max_through(device, cable, connector) ; Σ I at PS ≤ PS rating
```
Example: 90 V supply → 1000 ft → LE1 (0.8 A) → 1000 ft → LE2 (0.8 A), with R_loop 1.6 Ω/1000 ft.
Span 1 carries 1.6 A and drops 2.56 V, so V1 = 87.44 V. Span 2 carries 0.8 A and drops 1.28 V,
so V2 = 86.16 V. Under a constant-power load the currents rise slightly as the voltage falls,
which is why the solve iterates.

### 7.3 PS placement optimizers (Lode's three objectives)
Evaluate each candidate PS location (every powered-capable node, with an O(N) solve each, so
O(N²) total, which is fast at feeder scale):
1. **Balanced Draw**: minimize the spread of current between the ≥ 2 directions out of the PS.
2. **Maximum Low Voltage**: maximize `min_n V(n)`.
3. **Minimum Square Voltage Drop**: minimize `Σ_n (V_ps − V(n))²`.

For multiple supplies: partition with power blocks (a greedy split at the largest-current
edge, then local search over block positions), subject to PS capacity.

## 8. Modern HFC extensions (beyond Lode's column model)

| Topic | What the engine needs |
|---|---|
| **Full-band modeling** | Evaluate every spec as a function of f on a grid (e.g. every 6 MHz), not only on named columns. Keep named columns as views, for Lode parity |
| **Total Composite Power (TCP)** | `TCP = 10·log10 Σ 10^(P_i/10)` over the channel plan (flat plan: `P + 10·log10 N`). Check against the amp TCP limit at 1.2 and 1.8 GHz |
| **Digital performance** | SNR/MER budget with thermal noise + **composite intermodulation noise (CIN)** + optical/RPD + CMTS terms, all added on a power (10·log) basis. Targets per modulation, e.g. about 41 dB for 4096-QAM (confirm with your CMTS vendor) |
| **Split changes** | 5–42/65, 5–85 (mid), 5–204 (high), DOCSIS 4.0 ESD 300/396/492/684. Diplexer choice per active and per tap, with guard-band losses |
| **DOCSIS 4.0 FDX** | 108–684 MHz shared band. Needs interference-group analysis (tap-to-tap isolation, return loss) and FDX amplifier echo-cancellation specs |
| **DAA / Remote PHY / Remote MACPHY** | The node becomes an RPD with a fixed digital RF output and high MER, so it is modeled as a source active |
| **Temperature** | Design at 68 °F, then check hot (e.g. 120–140 °F aerial) and cold (−40 °F), taking amplifier thermal/AGC compensation into account |
| **Drops / MDU** | Tap port → drop cable (RG6/RG11 attenuation × length) → splitters → outlet. Check forward min at the outlet and return max at the modem (Lode MDU window / drop types) |
| **Fiber node** | Optical budget: laser power − fiber/connector/splice/splitter loss gives the node optical input, which sets RF output (analog) or checks the digital-link margin |
