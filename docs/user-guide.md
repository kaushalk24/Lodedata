# User guide

## Install and open

Nothing to install beyond Python 3.10 or newer — the package uses only the
standard library.

The easiest way in is the launcher that ships with the project:

* **Windows** — double-click `Start OpenLode.bat`
* **macOS / Linux** — double-click `start-openlode.command`

Either one starts the app and opens your browser. Leave the window it opens
alone while you work; closing it (or Ctrl+C) stops the app.

### "No module named lode"

`python -m lode` runs a package in the **current folder**, so it only works
when you are inside the project folder — the one that contains `lode`,
`specs` and `networks`. Running it from `C:\Users\you>` or `~` gives:

```
python.exe: No module named lode
```

`cd` into the project folder first, or just use the launcher, which does that
for you. To find the folder on Windows:

```
dir /s /b /ad %USERPROFILE%\lode
```

and on macOS or Linux:

```
find ~ -type d -name lode 2>/dev/null
```

```bash
git clone <this repo> && cd Lodedata
python3 -m lode init          # creates specs/, networks/, reports/ and an example
```

Optionally `pip install -e .` to get a `lode` command on your path; every
example below works either way (`lode …` or `python3 -m lode …`).

## A first pass

```bash
lode specs                    # summarise and validate the equipment library
lode calc example             # solve the example and print the design chart
lode calc example -r flags    # just what is out of spec
lode design example           # size taps, place amplifiers, balance, save
lode report all example --xlsx reports/example.xlsx
lode serve                    # the browser front end
```

## Design Mode in the browser

`lode serve` opens a four-part window: the plant on a pan/zoom canvas, the
properties of whatever is selected, the **legs** of the plant, and the
**design grid** underneath. Every edit re-solves the whole network
immediately.

**Colour** follows the Parameters file's *Set Margin*: green in spec, amber
out of spec by less than the margin, red by more.

### The design grid

The grid is where designs get built, and it works the way the original does:
one leg at a time, typed rather than clicked.

The four left-hand columns are yours to type into — **Loc**, **Ft**,
**Units**, **Tap**. Everything right of them is the answer: levels, plug-ins
and status, recalculated as you go.

Walk a street like this:

1. put the cursor on the first pole and type its footage;
2. press `.` — the period is the field separator, as in the original — and the
   cursor steps to **Units**; type the house count;
3. press `.` again and type the **tap value** (`17`, not a part number: the
   port count comes from the house count via the Parameters file's Homes /
   Number of Ports table);
4. press `Enter`. The cursor drops to the next pole — and if you were on the
   last one, a new pole is added and you simply keep typing.

A `0` in the footage column applies no cable loss, which is how a device gets
hung on the same pole as the one above it.

| Key | Action |
| --- | --- |
| *any digit* | starts editing the cell under the cursor |
| `.` | commit, step to the next field (wraps to the next pole) |
| `Tab` / `Shift`+`Tab` | step fields without wrapping |
| `Enter` | commit, next pole; at the foot of a leg, add the next pole |
| `F2` | edit the current cell · `Esc` abandon the edit |
| `←` `→` `↑` `↓` | move the cursor |
| `+` / `−` | step the tap, coupler or active at the cursor |
| `Ins` | insert a pole ahead of the cursor |
| `Del` | splice the pole out, merging its footage into the span below |
| `>` | design a leg that starts at this pole |
| `<` or `U` | back up to the parent leg, cursor on its origin |
| `S` | swap the legs on this device |
| `N` | name the current leg |
| `D` | run the automatic design tools |
| `Ctrl`+`Z` / `Ctrl`+`Y` | undo / redo |
| `Ctrl`+`S` | save |

### Legs

A **leg** is one linear run: it starts at an output port of a branching device
and continues until the line ends or the plant branches again. A run carries
straight on through an in-line amplifier — you do not start a new leg at every
line extender.

The breadcrumb above the grid shows where you are (`TRUNK › SP1 [TAP1]`) with
the leg's pole count, footage and unit count; the **Legs** panel on the right
lists every leg, and clicking one opens it. `>` steps into a leg from the pole
it starts at, and `<` comes back up with the cursor on the device it hangs
from.

**Naming** a leg (`N`) does two things: it labels the leg everywhere it
appears, and it *starts* a leg at that span even where the plant does not
branch — so a long run can be split into the legs you actually think in
("MAPLE ST", then "OAK AVE" past the amplifier). Clearing the name merges the
run back together.

**Swapping** legs (`S`) exchanges the two branches hanging on a device. On a
directional coupler that is a real balancing move: it decides which street
gets the low-loss through leg and which gets the tap leg, without redrawing
anything.

**Tabs** below the canvas: the design grid, then the Actives, Tap
Distribution, Performance, Powering, BOM and Flags reports, and an editable
view of all seven spec files.

## The automatic design tools

`lode design <network>` (or the **Auto Design** button) runs, in order:

1. **rebalance** — clear manual pad and equalizer overrides;
2. **auto ports** — size every tap from its house count using the Homes /
   Number of Ports table;
3. **auto taps** — choose the tap value at every location: the *highest* value
   that still makes the minimum tap output, because a higher value has a lower
   through loss and leaves more signal for the rest of the leg. Iterated until
   stable;
4. **place amplifiers** — where a leg runs out of signal, insert a line
   extender at the last pole whose level can still drive it, then re-select
   taps below it;
5. **self terminate** — swap the last tap on each leg for its
   self-terminating equivalent.

Anything marked `locked` is left untouched, so hand-placed equipment survives
a re-design.

## Working with your own equipment

The shipped `generic750` library is representative, not any manufacturer's
data. To use real specs:

```bash
mkdir specs/acme
# write acme.par .cab .tap .cpl .act .prf .prc  (see docs/spec-file-reference.md)
lode -s acme specs             # validate before designing against it
lode -s acme calc mydesign
```

The spec editor tab in the browser edits the same files in place, and
`SpecSet.validate()` reports anything inconsistent — a device missing a value
at an enabled frequency, a default naming a part that does not exist, an
active with no noise figure when C/N is enabled.

## Scripting

The engines are a plain Python API:

```python
from lode.specs import SpecSet
from lode.network import Network
from lode.workspace import Workspace

ws = Workspace(".")
specs = ws.load_specs("generic")
net = ws.load_network("example")

analysis = ws.analyse(specs, net)
for res in analysis.solution.taps():
    print(res.label, res.fwd_tap["F1"], res.rtn_tap["R1"], res.status)

print(ws.report(specs, net, analysis, "bom").to_text())
```

`ws.design(specs, net)` runs the automatic tools; `ws.save_network(net)`
writes the result.

## Powering studies

```bash
lode power example                     # normal load
lode power example --load-factor 1.4   # peak-usage study
```

The solver iterates to convergence because current draw depends on the voltage
that actually arrives. It reports per-device voltage and draw, per-span current
and drop, and flags under-voltage, over-current and supply overload. A power
block or a non-power-passing device bounds the area.
