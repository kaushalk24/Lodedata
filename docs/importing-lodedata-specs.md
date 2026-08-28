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
