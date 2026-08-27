# User guide

## Install

Nothing to install beyond Python 3.10 or newer — the package uses only the
standard library.

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

`lode serve` opens a three-panel window: the plant on a pan/zoom canvas, the
properties of whatever is selected, and the design chart underneath. Every
edit re-solves the whole network immediately.

**Colour** follows the Parameters file's *Set Margin*: green in spec, amber
out of spec by less than the margin, red by more.

**Keys** — the original was driven from the 10-key pad; these are the modern
equivalent:

| Key | Action |
| --- | --- |
| `+` / `−` | next higher / lower tap value (or coupler, or active) at the cursor, and recalculate |
| `T` | add a tap after the selection |
| `C` | add a coupler after the selection |
| `E` | end the line |
| `A` | insert an amplifier ahead of the selection |
| `↑` `↓` | walk the plant in design order |
| `Del` | remove the selection and everything below it |
| `D` | run the automatic design tools |
| `F` | fit the plant to the window |
| `Ctrl`+`S` | save |

**Tabs** below the canvas: the live design chart, then the Actives, Tap
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
