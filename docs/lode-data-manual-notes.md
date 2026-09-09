# Notes from the Lode Data Design Assistant manual

## How this was obtained, and what it is worth

`docs.lodedata.com` is refused by this environment's egress proxy, and so is
every other general website — the proxy runs a strict allowlist that permits
only GitHub and package registries. Probed directly: `pypi.org` 200,
`raw.githubusercontent.com` 301, and `docs.lodedata.com`, `en.wikipedia.org`,
`www.google.com`, `archive.org`, `scribd.com`, `pdfcoffee.com` all refused at
the CONNECT tunnel. So the pages could not be fetched.

What follows was recovered instead through **web search**, which reaches the
search index over a different path. Each entry below is quoted or closely
paraphrased from search results for the page named. That means:

* the **text** is genuine and quotable;
* the **screenshots are still missing entirely** — search returns no images,
  and much of this manual is pictures of the screen;
* coverage is partial. This is what a few dozen targeted queries surfaced, not
  the whole manual.

Everything here that changed the code is marked **[applied]**; everything still
open is in `open-questions.md`.

## Page inventory

The manual is bigger than the four pages first found. Full set seen in results:

| page | URL |
|---|---|
| Introduction | `/design/manual/` |
| Getting Started | `/design/manual/getting-started/` |
| Design Mode | `/design/manual/design/` |
| Active Entry Menu | `/design/manual/active-entry/` |
| Menus & Toolbars | `/design/manual/menus/` |
| Parameters | `/design/manual/parameters/` |
| Cables | `/design/manual/cables/` |
| Couplers | `/design/manual/couplers/` |
| Actives | `/design/manual/actives/` |
| Building Specification Files | `/design/manual/build-specs/` |
| Powering Mode | `/design/manual/powering/` |
| Reports | `/design/manual/reports/` |
| Utilities | `/design/manual/utilities/` |
| Performance File | `/design/manual/performance/` |
| Pricing | `/design/manual/pricing/` |
| Xspec | `/design/manual/xspec/` |
| Install | `/design/install/` |
| Macros | `/design/guides/macros/` |
| Plant Extension | `/design/guides/plant-extension/` |
| Tap Selection Group | `/design/guides/tap-selection-group/` |
| FAQ | `/FAQ/` |

---

## 1. What a spec file is

> "Specification files are the data files external to the Design Assistant
> program that the program uses to manage the user-defined parameters. They
> define every piece of equipment used by the Design Assistant and every
> operating parameter of the program."

Sample specs ship in a `SPECS` subdirectory and are explicitly *not* for real
design work. Directories are set per project under **File → Project Settings**.

This confirms the split seen in the binaries: a design file carries topology
and indices, and the spec set carries every part and parameter. It is why a
`.ntw` contains no text at all.

## 2. Cables **[applied]**

> "One hundred different types of cable, numbered 0 through 99, may be entered."

Matches the file exactly: the `.cbl` table is 100 records of 394 bytes.

> "Even-numbered cable types should be entered as aerial cable. Odd-number
> cable types are treated as underground cable."

Verified against both sample spec sets: 62 named cables, **zero** mismatches
between the record index parity and the AER/UG marker in the part name.

> "High refers to the forward high frequency; Low, the forward low; Rh, the
> return high; and Rl the return low frequency." — attenuation per 100 ft.

This resolves the loss block. Each block is ten `int32` fixed-point values:

| index | meaning |
|---|---|
| 0 | loss at forward **High** |
| 1 | loss at forward **Low** |
| 2–5 | the four optional extra forward frequencies |
| 6 | loss at return **Rh** (default 42 MHz), stored negative in `.cbl` |
| 7 | loss at return **Rl** (default 5 MHz), stored negative in `.cbl` |
| 8–9 | the two optional extra return frequencies |

Confirmed numerically across 62 cables in two independent spec files — median
ratios, since the values are hand-typed from manufacturer charts and no single
cable follows the √f law exactly:

| ratio | KERMIT | WVBeck | √f prediction |
|---|---|---|---|
| Low / High | 0.2528 | 0.2541 | √(54/860) = 0.2506 |
| Rh / Low | 0.8828 | 0.8750 | √(42/54) = 0.8819 |
| Rl / Low | 0.2989 | 0.2889 | √(5/54) = 0.3043 |

So these two spec sets were entered against roughly a **54 / 860 MHz forward**
band with the default **42 / 5 MHz return**, despite both being named "750".

> "Loop Res./1000 refers to electrical loop resistance in Ohms per 1000 feet,
> or per 1000 meters if meters had been specified in the Parameters. For fiber
> and any cables not intended to carry power, Loop should be set to 99, to
> cause an error in Powering if accidentally powered."

Confirms the loop-resistance field, its units, and gives a sentinel worth
honouring: **99 means never power this**.

## 3. Couplers **[applied]**

> "The four columns to the right of the 'Thru' label are used to enter the thru
> leg losses at the forward high, forward low, return high, and return low
> frequencies."

The same four-frequency layout as cables. A `.cpr` record is a 30-byte header
plus **two** ten-value loss blocks — one leg each. Decoding them that way
produces a coherent directional-coupler family:

| part | leg A | leg B |
|---|---|---|
| SSP-3K | 4.9 | 4.9 |
| SSP-7K | 8.1 | 3.5 |
| SSP-9K | 10.2 | 2.9 |
| SSP-12K | 13.4 | 2.2 |

Looser coupling costs more on one leg and less on the other, and the balanced
part has equal legs — exactly right. Which block the file calls "Thru" is not
settled; the numbers suggest leg A is the tap leg, so the app keeps file order
and lets you choose the port rather than guessing.

Also from that page:

> "Splitters can be defined as unequal splitters with zero loss on the through
> leg and negative amounts on the tap legs… a maximum of 2 tap legs."
> "Directional couplers and unbalanced 3-way splitters may be entered so that
> the high loss leg is directed to any of the branches."

## 4. Parameters

> "The default headings are high and low for the forward and RH (42) and RL (5)
> for the return. Two forward and two return frequencies are required for the
> Design Assistant to select forward and return equalizer values correctly…
> To customize a frequency heading, simply enter the desired frequency - for
> instance, 860 or 860 MHz. To enable extra forward and return frequencies just
> check the boxes next to the desired number of extra frequencies."

Four required frequencies plus optional extras — which is precisely the ten-slot
shape of the loss block. Also holds the units setting (feet or metres) and a
**tap selection tab** carrying the default tap-selection chart and the default
tap-optimisation mode.

## 5. Taps and Tap Selection Groups

> "A Tap Selection Group or TSG is created to have different manufacture tap
> types. A typical use case is mixing legacy tap types with new generation taps
> in a network file."
> "In version 10.50 … a TSG column was added to the Design, Active Entry and
> Entry modes… If the TSG has a value of 0 (blank) then the program will use
> the TSG assigned from the TSG dropdown."

TSG is a 1–99 value. Tap specs carry "loss values, insertion losses and
self-term parameters". Tap values are shown in brackets whose type encodes the
port count. This explains the `.tap` record shape: one record per tap value,
with several part-number slots and repeated sub-blocks.

Automatic tap optimisation has modes: **Off (OP-)** selects from the default
chart, **On Failure (Opf)** selects normally until there is not enough signal
downstream and then optimises.

## 6. Actives

> "Module input refers to the minimum signal level desired after the equalizer
> and pad, at the amplifier module inside the amp housing."
> "C/N[1] = 59 + input − noise figure = 59 + 11 − 9 = 61"

So the actives file carries module input, noise figure and output tilt, and the
program computes single-unit carrier-to-noise as `59 + input − NF`. The worked
tilt example: to reach a 7 dB output tilt from a 4 dB negative slope you drop
the low channel by 11 dB in total.

## 7. The modes — this is the real UX

**Entry mode** — where the strand data goes in, and it is keyboard-driven:

> "The decimal point (.) key is a field separator while entering footages,
> house counts, etc. … you type 1 0 7 to enter 107 feet and then press the
> period key to move the cursor into the house count column, type 2 then period
> to move to the cable column, then press 0 and then ENTER to enter the first
> span."

Columns are `ftg | hc | cab | lv`. Pressing Enter on that column group opens the
address-location dialog. Entry also holds map and location numbers.

**Active Entry mode** — "simply used for quick entry of strand and equipment
information", without the optimisation tools.

**Design mode** — the same rows plus computed results:

> "The Design screen displays the strand information input in the Entry
> (excluding the map and location numbers) as well as signal levels,
> amplifiers, taps, and couplers. Signal levels represent the input to the
> first piece of equipment on that line, and as you move down node by node,
> the dB level decreases as cable loss and equipment insertion loss are
> incurred."

Columns include an amplifier column (also holding in-line equalisers and Q
numbers), a coupler column, a cable ID column, a TSG column, and a tap column
"wide enough to display up to four taps on any one line. This provides a
maximum of 32 ports (four 8 port taps) on any one line."

Design mode adds: a pad and equaliser selector/editor at the cursor, quick
options to change the default tap-optimisation setting, and a **fixed flag** —
"if a node is fixed, the equipment at that node will not be modified by
semi-automatic design commands".

**Powering mode**:

> "The Powering display is very similar to the Design screen display except
> that instead of signal levels, voltage and current levels are displayed. The
> display also allows the placement of power stops and power supplies."

Three optimisation strategies: **Balanced Draw** (equal current in at least two
directions), **Maximum Low Voltage** (place so the lowest voltage is as high as
possible), **Minimum Square Voltage Drop** (minimum sum of squares of drop at
all powered devices). Supports **centralised** powering (one supply feeding
several nodes over powering cable) and **distributed** powering (power cable run
along an express run to a power inserter).

## 8. Starting a design

> "To start a new network file, hold the cursor over NEW and … click on
> NETWORK. The NEW NETWORK function will begin by prompting you for the name of
> the new network. Once the new network name is entered, the KEEP EXISTING
> LEVELS box is displayed. Next, it will automatically display the NETWORK
> INITIALIZATION WINDOW to define the starting signal levels and characteristics
> of the new network. Upon clearing the Network Initialization Window, the
> Design Assistant will automatically change to the ENTRY mode for immediate
> input of strand information."

## 9. Reports

BOM fly-out, five reports: **Control File BOM** (a group of networks combined),
**Single Network BOM**, **Map BOM** (by map number entered in Entry), **Powering
BOM** (by power-supply boundary), **Analysis Report** (redesigns each network by
forward execution).

Nine miscellaneous reports named in results: Macro Summary, Active report,
Control File Active report, Tap Distribution, Performance Distribution, Network
Notes, MDU report, Power Supply report.

Output goes to the Windows print dialog, and "it is also possible to print some
Design Assistant reports in a Excel format… simply type the name of the Excel
file followed by .XLS".

## 10. Menus

ALT plus the underlined letter opens a pull-down (ALT-F for File). File creates,
loads, unloads, prints and saves; Project Settings sets the directories.

---

## Sources

All of the above came from search results for these pages:
[Introduction](https://docs.lodedata.com/design/manual/),
[Getting Started](https://docs.lodedata.com/design/manual/getting-started/),
[Design Mode](https://docs.lodedata.com/design/manual/design/),
[Cables](https://docs.lodedata.com/design/manual/cables/),
[Couplers](https://docs.lodedata.com/design/manual/couplers/),
[Parameters](https://docs.lodedata.com/design/manual/parameters/),
[Actives](https://docs.lodedata.com/design/manual/actives/),
[Building Specification Files](https://docs.lodedata.com/design/manual/build-specs/),
[Powering Mode](https://docs.lodedata.com/design/manual/powering/),
[Reports](https://docs.lodedata.com/design/manual/reports/),
[Menus & Toolbars](https://docs.lodedata.com/design/manual/menus/),
[Tap Selection Group](https://docs.lodedata.com/design/guides/tap-selection-group/).
