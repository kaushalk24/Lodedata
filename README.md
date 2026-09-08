# Lodedata

Reverse engineering of the Lode Data Design Assistant file formats, and the
groundwork for an HFC network design application that can read them.

## Status

**Solved**

* The 512-byte header shared by every Lode Data file — magic, format version,
  authoring app version, licence id and user id.
* The `.ntw` network-file obfuscation: a fixed 100-byte **additive** keystream,
  key recovered and verified identical across all sample files. Design payloads
  can be read as plaintext.
* The equipment spec files (`.cbl`, `.cpr`, `.atv`, `.tap`) — record strides,
  part-number fields and the `int32 × 1e6` fixed-point number convention.
  Cable loop-resistance values decode to exactly the published figures for the
  real Commscope/other cables, which confirms the decode.

**Not solved yet** — both blocked on inputs I don't have; see
[`docs/open-questions.md`](docs/open-questions.md)

* The `.ntw` record layout (design files contain no text, only indices into the
  spec files, so there is nothing to bootstrap from without a known-content
  sample).
* The cable attenuation, tap-loss and amplifier-gain formulas — the numbers are
  readable, their exact meaning needs one screenshot each from the application.
* The application's UI and UX — `docs.lodedata.com` is blocked by this
  environment's network policy, so the manual has not been read.

## The design tool

A web application for keying in an HFC network from scratch and designing it:

* **Plant** — a cascade sheet you build device by device. Pick a row, add what
  it feeds (amplifier, tap, splitter, power inserter, power supply, terminator,
  subscriber), set the cable and span length, and every level recalculates.
* **Forward and return** — levels and tilt at both design frequencies of each
  band, amplifier gain, and the upstream level each tap port lands at the node
  with.
* **Powering** — current accumulated toward the supply, voltage drop from cable
  loop resistance, and a warning where a device falls under its minimum.
* **Design rules** — tap ports outside the level window, amplifier inputs too
  low, gain beyond what the part can deliver, devices under-volted.
* **Reports** — level sheet, bill of materials and powering, each downloadable
  as CSV.
* **Library** — cables, taps, passives, actives and power supplies. Ships with a
  standard 750 MHz library so you can start designing immediately, or attach a
  Lode Data spec set.
* **Spec upgrade** — attach a different spec set and every device is re-matched
  by part number, so the topology survives. Matching is exact first, then a
  token overlap that will find `625P3 AER EXT` for `EX .625P3 AER` but will
  never cross cable sizes or swap aerial for underground.

### Running it

```sh
pip install -r requirements.txt
./run.sh                       # http://127.0.0.1:8000
python3 -m pytest tests -q
```

## Layout

```
app/hfc/model.py         library parts, network model, sqrt(f) interpolation
app/hfc/engine.py        forward, return and powering calculations
app/hfc/reports.py       level sheet, bill of materials, powering
app/hfc/importer.py      Lode Data spec sets in, .ntw inspection, spec upgrade
app/hfc/starter.py       default 750 MHz equipment library
app/api.py               HTTP API and static hosting
app/web/                 the interface, no build step
tools/lodedata/          low-level Lode Data file readers and CLI
docs/file-formats.md     what the bytes mean, and how each claim was verified
docs/open-questions.md   what is needed to finish
tests/                   engine and importer tests
```

### The file reader on its own

```sh
PYTHONPATH=tools python3 -m lodedata info   AL005.ntw
PYTHONPATH=tools python3 -m lodedata decode AL005.ntw AL005.plain
PYTHONPATH=tools python3 -m lodedata spec   KERMIT750-2026 --json
```
