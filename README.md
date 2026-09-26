# Lodedata

Reverse engineering of the Lode Data Design Assistant file formats, and the
groundwork for an HFC network design application that can read them.

## Status

**Solved**

* The 512-byte header shared by every Lode Data file — magic, format version,
  authoring app version, licence id and user id.
* The `.ntw` network-file obfuscation: nibble swap plus a fixed 100-byte
  additive keystream, key recovered and verified identical across all sample files. Design payloads
  can be read as plaintext.
* The equipment spec files (`.cbl`, `.cpr`, `.atv`, `.tap`) — record layouts,
  part numbers, loss blocks, Tap IDs, Active IDs, and the `int32 × 1e6`
  fixed-point convention. Cable loop resistance decodes to the published
  figures for real cables.
* The `.ntw` network layout: branches, nodes, footage, house count, cable, lv,
  taps, couplers and leg designations, amplifiers and their names, pads, power
  supplies. A real design (AL004) imports with every reference resolved.
* The Parameters file's frequency labels, System Levels, tap margin and power
  supply table.
* The calculations, checked against AL004's own screens: Design levels match
  on every line, Power currents match, Power volts are within 0.02 V.

**Not solved yet** — see [`docs/open-questions.md`](docs/open-questions.md)
for each item and the screenshot that would settle it: the `<n>` / `[n]` branch
brackets, the rest of the Parameters file, pad and EQ values, in-line devices in
the amp column, and the last 0.02 V of the Power screen.

## The design tool

A replica of the Design Assistant screen, built on the reverse-engineered spec
files. Three modes over the same node lines, as the real program has:

* **Design** — `Node | 860 | 54 | 42 | 5 | ftg | hc | cab | lv | amp | TSG |
  tap1..tap4 | cplr[branch] | cplr[branch]`. Forward levels fall downstream as
  cable and insertion loss accumulate; return levels rise, being what a
  transmitter at that point must produce to reach the node.
* **Entry** — `Branch | Node | ftg | hc | cab | lv | TSG | Map | Loc |
  [Branch1] | [Branch2] | Amp Name`, for keying strand in quickly.
* **Power** — `Node | Volt | Current | ftg-hc-cab-lv | amp | amp ID# | supply |
  cplr[branch]`, with voltage drop and constant-power current draw.

The data model is Lode Data's, from the glossary: a **node** is one line of the
screen — a pole or a pedestal — and a **branch** is a run of nodes beginning at
a coupler. Placing a coupler creates the branch it feeds, and that branch is
drawn where its coupler sits, with line art down the left gutter.

Details carried over from the manual: taps print in the bracket of their port
count (`/2/ [4] {6} <8>`) showing the Tap ID; branch numbers print in the
bracket of their type (`[n]` normal, `(n)` no footage, `{n}` backfeed,
`<n>` forwardfeed); a fibre-fed node shows no RF input; the numbered screen
menu carries the real command names.

**Keying it in.** Equipment is typed at the cell, not picked from a list.

| column | type | meaning |
|---|---|---|
| `ftg hc cab lv` | `107 . 2 . 0` | 107 feet, 2 houses, cable 0 — `.` steps to the next field |
| `tap1..tap4` | `2.23` `4.23` `8.20` | port count and tap value; a bare `23` takes the port count from the house count |
| `cplr[branch]` | `2` `3` `8` | the Coupler ID — a 2-way splitter, a 3-way, a DC-8 |
| | `-8` | the same DC with its legs swapped: through (low loss) leg to the branch, tap (high loss) leg downstream |
| | `--3` or `=3` | through leg to the right-most branch |
| `amp` | `11` `61` | the Active ID |
| any | `0` | clears the cell; on a coupler it removes the branch too |

Arrow keys move the cursor, `Enter` commits, `Insert` and `Delete` add and
remove a node line, `Esc` abandons what you were typing. Typing a code that
isn't in the spec set is refused with a list of what is — `no 4-port 99 tap in
the spec set — it has 11, 17, 23, ...`.

## Layout

```
app/hfc/model.py         library parts and sqrt(f) interpolation
app/hfc/plant.py         branches of nodes -- the network itself
app/hfc/screen.py        what the Design / Entry / Power screens show
app/hfc/reports.py       level sheet, bill of materials, powering
app/hfc/importer.py      Lode Data spec sets in, .ntw inspection, spec upgrade
app/hfc/starter.py       default 750 MHz equipment library
app/api.py               HTTP API and static hosting
app/web/                 the interface, no build step
tools/lodedata/          low-level Lode Data file readers and CLI
docs/file-formats.md     what the bytes mean, and how each claim was verified
docs/lode-data-manual-notes.md  what the vendor manual says, and how it was obtained
docs/open-questions.md   what is needed to finish
tests/                   engine and importer tests
```

### The file reader on its own

```sh
PYTHONPATH=tools python3 -m lodedata info   AL005.ntw
PYTHONPATH=tools python3 -m lodedata decode AL005.ntw AL005.plain
PYTHONPATH=tools python3 -m lodedata spec   KERMIT750-2026 --json
```
