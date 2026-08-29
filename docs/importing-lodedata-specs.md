# Importing a Lode Data equipment library

Real libraries live in Lode Data's own binary format and **differ from region
to region**. OpenLode reads them directly, so you can design against the
library your system already uses.

```bash
lode import /path/to/library --name KERMIT750      # a folder of spec files
lode import KERMIT750.par KERMIT750.cbl ...        # or name them
lode import ... --dry-run                          # report without writing
```

In the browser, **Import specs** on the toolbar takes the same files, asks
what to call the set, and switches to it. Give each region its own name; the
spec-set picker beside it swaps between them.

Files read: `.par` parameters · `.cbl` cables · `.cpr` couplers · `.tap` taps ·
`.atv` actives.

## Read the import report

Every import prints a report listing what was read from each record, and what
was **rejected and why**. Check it against Lode Data's own spec printout
before you design against the set. An equipment library that is silently wrong
is worse than one that refuses to load.

## The format

Established by inspection of real files, then checked against published
hardline data.

A 512-byte header (title, licence, user), then fixed-length records. Numbers
are **scaled integers**, not floats:

| Quantity | Type | Scale |
| --- | --- | --- |
| decibels, signal levels | `int32` | 1 000 000 per dB |
| loop resistance | `uint16` | 1 000 per ohm |

Return-path figures are stored **negative** and taken as magnitudes. Each
parameter group is ten consecutive `int32` slots — `F1`–`F6` then `R1`–`R4` —
matching the frequency columns declared in the Parameters file; disabled
columns are zero. Blocks sit 40 bytes apart.

| File | Framing | Blocks |
| --- | --- | --- |
| `.cbl` | header 512, stride 394, records start `0x6f` | name +5, loop res +30, attenuation +34 |
| `.cpr` | first `0x6f` after the header, stride 114 | value +1, name +5, thru +30, tap leg +70 |
| `.tap` | records delimited by `FF FF FF FF` | tap loss name+18, through loss name+58 |
| `.atv` | stride 362, anchored on the device name | parameter pairs from name+54 |
| `.par` | ten 10-byte frequency slots | 5-byte label, enabled flag, value |

**Verification.** RG-6 decodes to 5.65 dB/100 ft at 750 MHz, `.875` P3 to
1.29 and `.500` P3 to 2.16 — all matching published data — and loop resistance
orders correctly by cable size (`.875` 0.55 Ω/1000 ft through RG-6 at 36.0).

## What is *not* read yet

Be explicit about this before trusting a study:

- **Parameters**: only the frequency table. Level windows — minimum tap
  output, tap window, return maximum, set margin — are **not** read. Set them
  on the Parameters tab.
- **Actives**: module input and design output only, identified by their tilt.
  Noise figure, distortion specs, equalizer tables and powering current draws
  are placeholders. Fill them in before running a performance or powering
  study.
- **Couplers**: leg counts are inferred — a coupler with tap-leg losses is
  given one tap leg. Check multi-leg splitters.
- **Taps**: port count and value come from the part number
  (`MMT2830` → 8-port 30 dB). Unrecognised patterns default to 4 ports and are
  listed in the report.

## What gets rejected, and why

Three guards stop a bad record becoming a bad design:

1. **Plug-ins are not taps.** Lode Data keeps pads and equalizers in the taps
   file. A pad selected as a tap would pass every level check and be
   catastrophically wrong, so rows matching `PAD`, `EQ`, `JUMPER`,
   `TERMINATOR` are separated out.
2. **A lossless tap is rejected.** A tap with no port loss at the design
   frequency would be chosen ahead of every real one.
3. **Values must be physically bounded** — tap loss 0.5–60 dB, through loss
   0–25 dB, coupler loss 0–40 dB. A record that decodes to 587 dB has a
   different layout, so it is rejected and named rather than imported.

Some families genuinely use a different record layout (an extra six-byte field
ahead of the block — the 112 versus 118 byte records). The reader tries the
alternate offset, and rejects the record if that fails too. Enter those
families by hand on the Taps tab; everything else imports.


---

# Network files (`.ntw`) — container solved, layout not yet

`lode inspect-network AL005.ntw --dump 4` deobfuscates a design file and
reports what is in it. It does **not** yet rebuild plant topology, and it says
so, because importing a design on a guess would hand you a plant that is not
yours.

## What is established

**Header** — 512 bytes, the same shape as the spec files: title
(`Lode Data Network File`), version (`Design 12.11`), licence, user.

**Body** — obfuscated by XOR against a **fixed 100-byte keystream that is
constant across files**. Four sample networks from one operator, of four
different sizes and three different users, share it byte for byte.

The period was *measured*, not assumed. At lag 100 the body self-matches on
**93.98%** of bytes; every other lag up to 700 sits near **2.9%**.

The keystream is recovered from the file itself: a design is mostly unused
record slots holding one repeated template, so the most common 100-byte block
is the keystream XOR that template. XOR every block against it and about
**96% of the body becomes zero** — the signature of real sparse structured
data. (The raw file contains *no* zero bytes at all, which is what gives the
obfuscation away in the first place.)

## What is not established, and why

The template is not all zeros. So the recovered stream is
`plaintext XOR template` — differences, not values. Decoded records come out
as arrays of four-byte groups in which only the leading byte varies, and
almost always between `0x40` and `0xC0`: a single differing bit. That is
exactly what a difference against a non-zero template looks like, and it means
absolute footages, tap values and house counts are still hidden.

## Getting existing designs in *today*

The Design Assistant prints any network, and a printed **design chart**
carries everything needed to rebuild the plant: location, the footage of the
span feeding it, house count and device. Reading the report is more reliable
than an inferred byte layout, because it reads the same numbers the designer
sees on screen.

Export the design chart from Lode Data (CSV, tab-separated or plain text),
then:

```bash
lode -s KERMIT750 import-design MYPLANT.csv --name myplant
```

Columns are matched **by name, not position** — `Ft`, `Footage`, `Distance`,
`Span` and `Length` are all understood as footage, and likewise for the rest —
so column order and extra columns do not matter. A bare tap value (`17`
rather than `T4-17`) is resolved through the spec set using the house count
and the Homes / Number of Ports table.

**Branches.** If the export has a `Leg`/`Branch` column, and a `From`/`Parent`
naming where each leg attaches, the topology is rebuilt exactly. Without one
the chart is read as a single run and the importer says so rather than
inventing branches. OpenLode's own design chart now exports both columns, so
a chart exported from OpenLode and read back is lossless — verified by a test
that re-solves the rebuilt plant and requires every tap level to match to
three decimals.

What the chart does not carry: power supplies, and manual pad/equalizer
overrides. Add those after import.

## What would finish the binary format

**Known plaintext.** Either of these pins the layout in one pass:

1. **A small design and its numbers.** Save a network in Lode Data with
   distinctive values — three or four poles at footages like 111, 222, 333 and
   tap values 11, 17, 23 — and send the `.ntw` together with what the design
   screen shows. Searching the deobfuscated body for those exact numbers
   locates every field at once.
2. **Two saves differing by one edit.** Save a design, change *one* footage,
   save again under a new name. The bytes that differ are that field, and its
   scale follows immediately.

Option 2 is the stronger one: it isolates a single field with no ambiguity.
With either, reading and writing `.ntw` becomes straightforward — the
container work is already done.
