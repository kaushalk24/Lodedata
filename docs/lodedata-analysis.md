# How the Lode Data Design Assistant works

An analysis of the original, and how each piece is reproduced in OpenLode.

Everything below is drawn from Lode Data Corporation's **public**
documentation at `docs.lodedata.com` and their product pages. No proprietary
files, binaries or equipment data were used, and none are redistributed here.
OpenLode is an independent re-implementation of the *workflow and the
engineering*, not a port of anyone's code.

---

## 1. What the product is

The Design Assistant is "a Computer Aided Engineering System for the design
and optimization of Broadband coaxial networks, ranging from citywide cable TV
networks to computer Local Area Networks". It was introduced in **1983** as an
engineering tool for broadband coaxial systems and grew into the most widely
used HFC design package in the industry.

It sits at the centre of a small family of tools:

| Product | Role |
| --- | --- |
| **Design Assistant** | RF and powering engineering: levels, plug-ins, distortion, powering, reports |
| **Drafting Assistant** | Turns AutoCAD into a CATV mapping program; imports the designed network so "all cable types, tap values, amplifiers, and data blocks" come across |

The Design Assistant supports **any manufacturer's equipment** and up to **ten
design frequencies**, with "instant recalculations of what-if scenarios". That
last phrase is the whole design philosophy: the model is small enough, and the
maths cheap enough, that the entire plant re-solves on every keystroke.

## 2. The seven specification files

> "Spec files are the backbone of The Design Assistant, and in order for the
> program to calculate a network properly you must have a PARAMETERS, TAPS,
> ACTIVE, COUPLERS, and CABLES spec file."

Two more — PRICING and PERFORMANCE — are optional, making seven in total. Each
is created and edited separately, and each can be printed from the *Specs*
menu.

| File | Holds | OpenLode |
| --- | --- | --- |
| **PARAMETERS** | six tabs of global settings: units, design frequencies, level windows, tap sizing, powering defaults | `lode/specs/parameters.py` → `.par` |
| **CABLES** | attenuation per 100 ft at each frequency, loop resistance per 1000 ft, price | `lode/specs/cables.py` → `.cab` |
| **TAPS** | tap value, port count, tap-port loss, insertion loss, self-terminating flag, tap selection group | `lode/specs/taps.py` → `.tap` |
| **COUPLERS** | thru-leg loss, number of tap legs, tap-leg loss | `lode/specs/couplers.py` → `.cpl` |
| **ACTIVES** | gain, design output, module input, noise figure, distortion specs, pads, equalizers, powering V/A pairs | `lode/specs/actives.py` → `.act` |
| **PERFORMANCE** | how each impairment derates with level and combines down a cascade | `lode/specs/performance.py` → `.prf` |
| **PRICING** | material and labour against part numbers | `lode/specs/pricing.py` → `.prc` |

### How spec files get loaded

Three mechanisms in the original, all reproduced:

1. **Individually** — *File → Open → Parameters / Actives / Taps / Couplers /
   Cables / Pricing / Performance*.
2. **As a project** — the Project Settings file, extension **`.DAP`** ("Design
   Assistant Project"), stores the directories the program searches, so it
   "will always be able to find the desired specification and network files".
   Choosing *SET ALL FILES* prompts for the parameter file `*.PAR` and takes
   the rest of the set with it.
3. **From an Xspec** — extension `.XSP`, "a file that stores up to ten
   different sets of specification files for quick and easy access …
   accessible by pressing `. . 1` in the Design menu"; pressing line number
   `0`–`9` loads that set. The one restriction is that every file listed on a
   line must live in the same directory.

OpenLode keeps all three (`ProjectSettings`, `Xspec`, `SpecSet.load_dir`) and
adds cross-file validation, which the original leaves to the designer: it
checks that every device carries a value at every *enabled* frequency column
and that the defaults named in Parameters actually exist.

### Frequency columns

> "Two forward and two return frequencies are required for the Design
> Assistant to select forward and return equalizer values correctly."

Up to **six forward** (`F1`–`F6`) and **four return** (`R1`–`R4`) columns are
supported, with `F3`–`F6` and `R3`–`R4` switched on from the Frequencies tab
of Parameters and the headings freely renamed. Every loss figure in every
other spec file is indexed by these columns — which is why Parameters is the
master file of the set.

By convention `F1` is *forward high*, `F2` *forward low*, `R1` *return high*,
`R2` *return low*: exactly the "High, Low, Rh, Rl per 100ft" columns of the
cables file.

## 3. The calculations

### 3.1 Levels, pads and equalizers

Forward levels march away from the source, losing `atten × length / 100` per
span and the tabulated loss of every passive. At each amplifier the engine
re-establishes the design output with a **pad** (flat) and an **equalizer**
(sloped). Two unknowns, so two frequencies suffice:

```
o_h = i_h + g_h − p − e_h
o_l = i_l + g_l − p − e_l
────────────────────────────  subtract: the pad cancels
e_h − e_l = (i_h − i_l) + (g_h − g_l) − (o_h − o_l)
```

Pick the stocked equalizer closest to that slope, then back-substitute for the
pad. **Allow Over Equalization** decides whether an equalizer that slopes
*harder* than required may be used — "it will select the equalizers that come
the closest to the desired slope even if it creates an over-equalized
situation".

### 3.2 Housing versus module levels

Amplifier figures in the ACTIVES file are **module** levels. The level the
designer sees on screen is at the **housing** — the end of the incoming cable,
before the housing's internal losses. The manual's own example:

> "assume you have a forward-high-channel module input of 16.50 dB. In this
> case, your forward-high-channel housing input minimum is 19.50 dB and the
> Design Assistant would show an error on an amplifier where the
> forward-high-channel level at the end of the incoming piece of cable is less
> than 19.50 dB."

So `housing_input_min = module_input + housing_offset`, 3.00 dB in that
example. OpenLode stores the offset per device and flags the same error.

### 3.3 Tap windows and the margin

Two windows bound every tap port:

* forward — a **minimum** tap output, plus a **tap window** giving the
  maximum: "if you have a minimum tap output specification of 16 dB (Forward
  high), and are not allowed to exceed 26 dB from that tap port, you would
  enter a 10.00 for the tap window";
* return — a **maximum** level a subscriber device must transmit into the
  port, because "the return input to a tap can rise above the maximum before
  it is flagged as red".

**Set Margin** turns those bounds into the familiar traffic lights: "sets how
far a tap has to be out of spec before being displayed red. If a tap is less
than the margin value out of spec, it will be displayed in yellow."

*Enforce Tap Window* forces outputs to sit inside the window rather than
merely above the minimum — "used primarily when using taps with plug-in pads
and equalizers".

**Maximum crossover** is the third guard: "the maximum that the forward low
signal may exceed the forward high signal before an in-line equalizer is
placed".

### 3.4 The return path

The return is designed against each amplifier's *fixed* module input
requirement. Working outward from every active, the engine accumulates return
losses down to each tap and reports the level a subscriber device must
transmit for the amplifier to see its required input — the number the tap's
return maximum is checked against. Between actives the reverse holds: the
downstream amplifier's return output is fixed, so whatever surplus arrives
upstream is taken up by a return pad.

### 3.5 Distortion and noise

The PERFORMANCE file carries two numbers per impairment, and between them they
define the entire cascade model.

**Addition factor** — the log rule used when contributors are summed: "the
addition factor for carrier to noise is 10 because it is calculated using a
10 log rule. The addition factor for composite triple beat is 20 because it is
calculated using a 20 log rule."

```
total = −X · log10( Σ 10^(−sᵢ / X) )      X = 10, 15 or 20
```

**Derate factor** — "the amount of degradation that occurs with a 1 dB change
in signal level. A positive number will cause the Design Assistant to key off
the input level for that particular distortion type, whereas a negative number
will cause it to key off the output level."

> "Carrier to noise gets 1 dB worse for every 1 dB decrease in input level, so
> you would enter a positive 1 … Composite triple beat gets 2 dB worse for
> every 1 dB increase in output level, so you would enter a negative 2."

Both collapse to one rule:

```
spec_actual = spec_base + derate × (level_key − level_ref)
level_key = input level if derate > 0, else output level
```

Carrier-to-noise is not tabulated but derived from the noise figure:

> "the formula to calculate the single unit base distortion level of
> carrier-to-noise for an amplifier that has an input of 11 and a noise figure
> of 9 is: C/N[1] = 59 + input − noise figure = 59 + 11 − 9 = 61."

The result appears in the **Performance Distribution** report, "a breakdown of
the expected performance for each type of distortion (c/n, ctb, etc) at every
tap in the currently loaded network".

### 3.6 Powering

Powering Mode carries AC over the same coax. Two details make it interesting,
and both are in the manual:

* draw depends on the voltage that actually arrives — "powering data are
  entered in voltage-current pairs in ascending order of voltage for each
  device. That is, for a given device, from Vmin to V2, it uses A1 amperes;
  from V2 to V3, A2 amperes are used" — and linear interpolation
  "eliminat[es] the jumps that occur in the stair step method";
* every device has a rating: "the maximum amperage through each piece of
  equipment can be specified. If the Max A number is exceeded, the offending
  device will be flagged in red."

Since current depends on voltage and voltage depends on current, the network
is solved by fixed-point iteration. The original also offers a peak-usage
study that forces telephony lines off-hook "in such a way that the overall
current draw is maximized"; OpenLode models this as a load factor plus
per-location extra load.

## 4. Design Mode

> "The Design and Active Entry mode is where all actual design work is done.
> The Design mode/menu contains many powerful design optimization tools."

This is the part that is easiest to get wrong, and the part that decides
whether the tool is usable. Three things define it.

### It is typed, not clicked

The original is famously fast because it is **10-key driven**: "all actual
design work … is done using the 10-key pad on the keyboard to maximize
efficiency", with NUM LOCK remapped to ESC and the screen menus arranged so
commands fall under the numeric keypad.

The entry loop is a grid of columns, and **the period key is the field
separator**: you "type the values and then press the period (.) key to move
the cursor into the next column (such as the house count column)". You start
a run at zero — "a 0 distance in the footage column means no cable loss has
been applied" — and then walk the street: footage, house count, tap value,
next pole.

The `+` and `-` keys step equipment in place: "pressing the + key will change
it to the next higher value tap or two-way coupler and recalculate signal
levels, or if used in a tap column where there is no tap present, it will
select a tap to put there."

One semantic detail matters for reading the screen at all: "the signal levels
displayed are the levels after the footage that is on the same line, but
before any equipment." A row's level is what arrives at that pole, not what
leaves it.

### It is scoped to one leg

You do not look at the whole plant at once; you design a trunk line or a
feeder leg. The **Amplifier Definition Window** "allows you to specify a name
for the amplifier at the cursor location and assign the feeder legs that begin
from that amp/LE as well as move to, rename, or delete these feeder legs", and
navigation runs the other way too: "when invoked from a feeder leg, the
navigate command will load the trunk line to which the feeder leg is attached
and place the cursor at the amplifier from which it originates."

### Legs can be rearranged

Legs are not fixed to the port they were drawn on: they can be moved, renamed
and swapped between the ports of a device. On a directional coupler that is a
real engineering decision — which street gets the low-loss through leg.

### How OpenLode reproduces it

The browser front end is a **leg-scoped design grid**, not a whole-network
table. Four columns are typed into (Loc, Ft, Units, Tap) and the rest is the
calculated answer. The period key steps fields; `Enter` drops to the next pole
and, at the foot of a leg, creates it. Tap values are typed as values (`17`),
with the port count coming from the house count through the Parameters file's
Homes / Number of Ports table. `>` and `<` move into and back out of legs,
landing the cursor on the originating device exactly as the navigate command
does; `S` swaps legs; `N` names one.

Naming is given slightly more power here than in the original: a named span
*starts* a leg even where the plant does not branch, so a long run can be
split into the legs a designer actually thinks in. Clearing the name merges
it back.

Two implementation notes that turned out to matter more than expected:

* **Deleting a pole splices rather than removes.** The pole's footage is added
  to the span below it, so removing a pole from the middle of a leg leaves the
  geography of everything below untouched. Anything else would silently move
  every pole on the street.
* **The grid owns the keyboard by state, not by DOM focus.** Re-solving the
  network rebuilds the table, and a focus-based scheme drops the keystroke
  that lands during the rebuild — which showed up as swallowed digits and
  arrow keys jumping to another leg.

Sticky notes ("entry of a text note at any node in the network") are kept
as-is. **Tap Selection Groups** let a design draw from different tap families
in different places: "a 1–99 value to specify the group to be used for tap
selection as defined in the Tap specs", created in the original by leaving a
blank line between groups. OpenLode makes the group an explicit `tsg` field —
the same idea without the fragile blank-line encoding.

## 4b. Design-test errors

The help file's index names every error the Design Assistant's **Test**
command can raise. That list is effectively its rule book, so OpenLode
implements it:

| Design Assistant error | OpenLode flag |
| --- | --- |
| Tapout(h) / Tapout(l) below min | `tap-level` |
| Tapout(rh) / Tapout(rl) above max | `return-tap-level` |
| High / Low input of xxx to LE | `housing-input`, `under-driven`, `over-driven` |
| Rh / Rl output of xxx from LE | `return-short` |
| Fslope / Rslope too low to equalize | `equalization` |
| Crossover above max | `crossover` |
| Not enough taps / Not enough drops | `not-enough-taps` |
| Invalid terminating tap used | `invalid-terminating-tap` |
| Nonexistent tap used | `missing-tap` |
| LE X/N before/M after (LE cascade violation) | `le-cascade` |
| Unused LE placed | `unused-active` |
| Performance errors | `performance` |
| Branch does not begin anywhere / contains no nodes / not fed by a coupler | `Network.validate()` |

Two carry new parameters: `max_le_cascade` (how many line extenders may
follow one another, 0 to disable) and `check_tap_ports` (flag a tap whose
ports cannot serve the units at that location). An end of line on a through
tap is flagged as well, since it needs a terminator or a self-terminating tap.

## 5. Reports

The original offers nine miscellaneous reports — Macro Summary, Active,
Control File Active, Tap Distribution, Performance Distribution, Network
Notes, MDU, Power Supply and Control File PS — plus the Bill of Materials, and
"printing to a .XLS file allows for customized spreadsheets containing Bill of
Materials or Active Report information".

OpenLode ships ten reports covering the same ground (macros and control files
excepted, having no counterpart here) and renders each as text, CSV, JSON or a
real `.xlsx` workbook written with nothing but the standard library.

## 6. What is deliberately different

| Original | OpenLode | Why |
| --- | --- | --- |
| Binary/fixed-width spec files | JSON with a CSV projection | readable, diffable, scriptable; still one file per spec type with the same extensions |
| AutoCAD hand-off via Drafting Assistant | `.dsn` JSON plus CSV/XLSX exports | no CAD dependency; the model is open for any downstream tool |
| Blank-line tap selection groups | explicit `tsg` field | the encoding was a frequent source of error |
| Macros recording keystrokes | Python API + CLI | scripting a documented model beats replaying keystrokes |
| Windows desktop application | Python package, CLI and local web app | runs anywhere Python 3.10+ runs, with no dependencies |
| Manual amplifier placement | `auto_actives` places them | the manual's own advice — "since you are out of signal, the most logical step is to place an amplifier" — made automatic |
| Legs fixed by topology | a named span also starts a leg | lets a designer split a long run into the legs they think in |

## Sources

- [Design Assistant](https://lodedata.com/products/design-assistant/) · [Lode Data](https://www.lodedata.com/)
- [Manual: Introduction](https://docs.lodedata.com/design/manual/) · [Getting Started](https://docs.lodedata.com/design/manual/getting-started/) · [Menus & Toolbars](https://docs.lodedata.com/design/manual/menus/)
- [Parameters](https://docs.lodedata.com/design/manual/parameters/) · [Actives](https://docs.lodedata.com/design/manual/actives/) · [Cables](https://docs.lodedata.com/design/manual/cables/) · [Couplers](https://docs.lodedata.com/design/manual/couplers/) · [Performance File](https://docs.lodedata.com/design/manual/performance/) · [Pricing](https://docs.lodedata.com/design/manual/pricing/) · [Building Specification Files](https://docs.lodedata.com/design/manual/build-specs/) · [Xspec](https://docs.lodedata.com/design/manual/xspec/)
- [Design Mode](https://docs.lodedata.com/design/manual/design/) · [Powering Mode](https://docs.lodedata.com/design/manual/powering/) · [Reports](https://docs.lodedata.com/design/manual/reports/) · [Utilities](https://docs.lodedata.com/design/manual/utilities/)
- [Tap Selection Group](https://docs.lodedata.com/design/guides/tap-selection-group/) · [Plant Extension](https://docs.lodedata.com/design/guides/plant-extension/) · [Macros](https://docs.lodedata.com/design/guides/macros/) · [FAQ](https://docs.lodedata.com/FAQ/)
