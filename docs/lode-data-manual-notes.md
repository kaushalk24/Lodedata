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

The sidebar (from a screenshot you sent) gives the real structure:

```
Lode Data Docs
  Home
  Design Assistant
    Design Install
    Guides            >
    User Manual       >
      Introduction
      Command Line Switches
      Getting Started
      Menus & Toolbars
      Utilities
      Modes           >
      Reports
      Spec Files      >
      Macros
      Miscellaneous
      Troubleshooting
      Glossary
  Drafting Assistant  >
  Fiber Module        >
  FAQ
```

Pages confirmed to exist by search:

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
| Tap Port Drop Types | `/design/guides/drop-types/` |
| Command Line Switches | `/design/manual/command-line-switches/` |
| Glossary | `/design/manual/glossary/` |
| FAQ | `/FAQ/` |
| Fiber Module — database utilities, backup | `/fiber/server/...` |

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


---

# Second pass — the rest of the sidebar

## 11. The vocabulary (Glossary) — this is the data model

> **Node**: "A logical (as opposed to physical) unit that corresponds to one
> line of the Entry, Power or Design screens. In the real world outside of the
> computer, it can represent a pole for aerial plant, or a pedestal for
> underground plant. Several nodes can be located at the same pole or pedestal."

> **Branch**: "A branch can be thought of as one page on the display that begins
> from a coupler."

So the design is **a list of nodes per branch**, one screen line each, and
branches hang off couplers. Not a free-form graph — which is exactly the shape
a `.ntw` file's fixed tables would take.

Branch numbers carry their type in the bracket style:

| shown as | meaning |
|---|---|
| `[n]` | a normal branch, has information, not a back/forward feed |
| `(n)` | no footage on that branch |
| `{n}` | a backfeed |
| `<n>` | a forwardfeed |

Taps are printed the same way: "the tap value … within one of four different
types of brackets that identify the number of tap ports".

## 12. Actives — solved **[applied]**

> "The Actives file stores all the information about amplifier types, inputs and
> outputs, pad and equalizer information, power requirements, etc."
> "The Actives tab … defines the signal levels required at the forward and
> return inputs, as well as the forward and return outputs produced by each
> active as indicated by the column prefix In or Out."

That decodes the `.atv` numeric block completely. At +59 there are two sets of
four values — In then Out — each at the four design frequencies, followed by a
**voltage / current draw table**:

| part | In (Fh, Fl, Rh, Rl) | Out (Fh, Fl, Rh, Rl) | gain | tilt |
|---|---|---|---|---|
| BLE-7-750PSS | 19, 15, 21, 21 | 49, 38, 43, 43 | 30 dB | 11 dB |
| MB-750D-H | 12, 11, 21, 21 | 49, 38, 40, 40 | 37 dB | 11 dB |
| BTN NODE-9 | **99**, 0, 27, 27 | 46, 36, 0, 0 | — | 10 dB |

**99 in the forward input is the "no RF input" sentinel** — the same convention
as loop resistance 99 on cables. It marks a fibre-fed optical node, and it
classifies parts the name alone would miss (`5F31QSA004-9` is a node).

The trailing table is `(volts, amps)` pairs, and it is a **constant-power
curve** — which is why the file carries a table instead of one number:

| MB-750D-H | 38 V | 45 | 52 | 60 | 70 | 80 | 90 |
|---|---|---|---|---|---|---|---|
| amps | 1.12 | 0.96 | 0.83 | 0.72 | 0.62 | 0.54 | 0.48 |
| watts | 42.6 | 43.2 | 43.2 | 43.2 | 43.4 | 43.2 | 43.2 |

Also on that page: each active references a **bank** of pad and equalizer values
via `Fwd Pad`, `Ret Pad`, `Fwd EQ`, `Ret EQ` columns, and active IDs are
editable on a Configuration Table page.

## 13. Taps

Tap specs are entered per port count — there is a "2 Port Taps" tab — holding
"loss values, insertion losses, and self-term parameters". Taps can be
**self-terminating** ("an 8 port 11 tap can be self terminating"), which matters
because a self-terminated tap needs no separate terminator.

## 14. Tap port drop types

Branches created through the Tap Port Window with a drop count type are drops.
Three types: **RES**, **COM**, **MDU**. A commercial flag makes the house count
tally as commercial in the BOM.

> "Typically, you need 1 port for 1 house count, 2 ports for a 2 house count …
> but this provides the flexibility to tap for more or less than 100% of the
> homes. If your house count at any one node exceeds 63, the Design Assistant
> maximum, it will be necessary to 'break up' the house count and put it on two
> nodes separated by a zero footage."

**House count per node maxes at 63** — a 6-bit field, which is a useful hint for
the `.ntw` record layout. Drop quantity maxes at 8 (the largest tap), and a
2-way drop splitter turns 8 into 16 drops.

## 15. Performance file — the distortion model

> "The addition factor for carrier to noise is 10 because it uses a 10 log rule,
> while the addition factor for composite triple beat (CTB) is 20 because it
> uses a 20 log rule."

Per distortion type it holds:

* **Signal Band** — which frequency it is tracked at, forward high or forward low
* **Derate factor** — degradation per 1 dB of level change; "a positive number
  keys off input level and a negative number keys off output level"
* **Source Level** — the level of that distortion before any equipment, i.e. at
  the headend, hub or fibre

With the actives page's `C/N = 59 + input − noise figure`, that is a complete
cascade distortion model: seed at the source level, accumulate each active by
its log rule, derate by level offset.

## 16. Utilities — the navigation and annotation commands

The Utilities page is a long list of cursor commands. Confirmed:

* **Jump to Amp / Power Supply** — type part of a label and it jumps to the
  first match; the whole label is not needed.
* **Dist** — total distance between the node at the cursor and any other node,
  "these nodes not needing to be in the same branch".
* **Note** — a sticky note of free text at any node.
* **Overhead view** — full-screen plan view of the network; arrow keys move the
  cursor, node number shown top-left.
* **Map carry** — copies the map number under the cursor to nodes you move to.
* **Amplifier Definition window** — a unique name up to **256 characters** per
  amplifier, openable from Design or Powering mode; power supplies can be named
  the same way.
* Next/Previous Active, Split, Power Supply, Transformer, PCD — cursor jumps.
* **Transformers** "provide a voltage boost downstream of transformer
  placement".
* **PCD (Power Connecting Device)** — "used to create desired connections
  whether within a single network or spanning across multiple networks. To place
  a PCD, put your cursor in the coupler column, press 0 to alter and enter 1000
  as the id number".

Navigation keys on that page: arrows move between entries; `ESCAPE` or
`NUM LOCK` closes a window saving its contents; `PAGE DOWN` on a network
position creates or loads that network, prompting to save; `DELETE` removes one.
A number in brackets after a two-character extension means compressed legs were
appended with `AUTOAPPEND` or `APPENDAREA`, and the right arrow jumps to the
start of that appended branch.

## 17. Modes

> "The mode pull-down menu can be used to switch the Design Assistant to DESIGN,
> ENTRY, ACTIVE ENTRY or POWERING mode. This pull-down is there mostly to aid
> new users; experienced users usually find it faster to change modes using the
> screen menu options."

Screen menus are number-keyed — "the NETWORK MODIFIED menu allows you to quickly
3 RESTORE, 7 SAVE, or 9 SWITCH modes". The whole program is built for the
keyboard; the mouse is the beginner's path.

Active Entry exists "to enable quick design where levels and equipment values
are calculated as entry is done".

## 18. Files and organisation

> "Spec files are the backbone of The Design Assistant, and in order for the
> program to calculate a network properly you must have a PARAMETERS, TAPS,
> ACTIVE, COUPLERS, and CABLES spec file. Your spec files must all have the same
> name in order for this to work properly."

Confirms the five-file set sharing a base name, which is how the reader here
already loads them. Directories: `Networks`, `Specs`, `Misc`, set under Project
Settings; system files under
`C:\Program Files\Lode Data Corporation\Design Assistant`.

A **Control file** is "a group of network files that are added together",
letting a BOM or Active Report span many networks at once.

## 19. Macros

Macros record keystrokes and mouse clicks and replay them on a hot key;
terminate recording with `*`, run with `* n` or from the macro manager. There is
batch macro functionality that "will open each network we select and run the
macro". A Macro Summary report lists hot key, keystroke count and description.

## 20. Command line switches

Placed **outside** the quoted path on the shortcut Target line, e.g.
`"...\Design Assistant\10.4\Dapc64.exe" /b`.

## 21. Troubleshooting

* A `.LCK` file next to the `.NTW` marks it open by another user; deleting the
  stale `.LCK` releases it. **So a design has a sidecar lock file.**
* "If a branch contains a loop (a branch connected in more than one location to
  its parent branch) … generally indicates corruption within the network."
* "An empty branch contains no nodes at all, and you should place at least a
  single zero node in the branch or eliminate the branch completely."
* Legacy errors occur "when opening legacy network files where branches were
  deleted improperly".

## Additional sources

[Utilities](https://docs.lodedata.com/design/manual/utilities/),
[Glossary](https://docs.lodedata.com/design/manual/glossary/),
[Performance File](https://docs.lodedata.com/design/manual/performance/),
[Tap Port Drop Types](https://docs.lodedata.com/design/guides/drop-types/),
[Command Line Switches](https://docs.lodedata.com/design/manual/command-line-switches/),
[Macros](https://docs.lodedata.com/design/guides/macros/),
[Active Entry Menu](https://docs.lodedata.com/design/manual/active-entry/),
[FAQ](https://docs.lodedata.com/FAQ/).


---

# Third pass — from the screenshots

The PDFs carry the screen images, so the interface could finally be read rather
than guessed at. Design, Entry and Power are the same node lines with different
columns:

```
Design  Node | 860 | 54 | 42 | 5 | ftg | hc | cab | lv | amp | TSG |
        tap1 tap2 tap3 tap4 | cplr[branch] | cplr[branch] | 550
Entry   Branch | Node | ftg | hc | cab | lv | TSG | Map | Loc |
        [Branch1] | [Branch2] | Amp Name
Power   Node | Volt | Current | ftg-hc-cab-lv | amp | amp ID# | supply | % |
        cplr[branch] | cplr[branch] | NIU
```

Black ground, green data, yellow column headers, a solid green block for the
cursor, and three rows of numbered screen-menu commands coloured per mode —
green in Design, cyan in Entry, yellow on the first row in Power.

## Tap display — the bracket is the port count

Quoted exactly:

```
/26/  represents a two-port 26 tap
[26]  represents a 4-port 26 tap
{26}  represents a 6-port (if any)
<26>  represents a 8-port 26 tap
```

The tap column is four wide, "a maximum house count of 32, four 8-port taps on
a single node/line".

## Branch display — the bracket is the branch type

The coupler columns show "the coupler ID # as well as the branch number that is
created by that coupler. The value of the coupler is outside of the brackets
and the branch number is inside of them."

| shown | meaning |
|---|---|
| `[#]` | normal branch |
| `(#)` | no footage in the branch (not the same as empty) |
| `{#}` | backfeed |
| `<#>` | forwardfeed |

## Which leg is the through leg

A designation between the coupler ID and the brackets says where the low-loss
leg goes:

| shown | through (low-loss) leg |
|---|---|
| `8[2]` | downstream — the standard case |
| `8 -[2]` | to the branch in the left-most coupler column |
| `3[2][3]` | downstream; both tap legs feed branches 2 and 3 |
| `3 -[2][3]` | to branch 2 |
| `3 =[2][3]` | `--`, which looks like `=`: to the right-most column, branch 3 |

This changes the arithmetic, not just the picture, so it is modelled.

## Navigation — "." is a prefix, not just a separator

| keys | effect |
|---|---|
| `↑` `↓` | up/down one node |
| `←` `→` | left/right one column |
| `. ↑` `. ↓` | top / bottom of the current branch |
| `. →` `. ←` | into the branch beginning on the highlighted node / back |
| `Page Up` `Page Down` | back / forward one branch |
| `. Page Up` `. Page Down` | first / last branch |
| `Insert` `. Insert` | insert a line at / below the cursor |
| `Delete` `. Delete` | delete a line / undelete |
| `.` while typing | field separator: `107 . 2 . 0` |
| `Num Lock` | remapped to Esc; also opens the NETWORK MODIFIED menu (3 Restore, 7 Save, 9 Switch) |
| `/` | backspace in Entry; toggles standard/expanded display in Design |
| `*` | macros; `* *` opens the macro manager |

So **one branch is on screen at a time** — "a branch can be thought of as one
page on the display" — and you page between them. That is how the app now works.
