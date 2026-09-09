# Lode Data file formats — reverse-engineering notes

Everything here was derived from the sample files supplied with this task:

There are **seven** spec file types, not five: `.PAR`, `.ATV`, `.TAP`, `.CPR`,
`.CBL`, plus `.PRC` (Pricing) and `.PER` (Performance). The samples supplied
here cover the first five. A design needs Parameters, Taps, Actives, Couplers
and Cables, and "your spec files must all have the same name".

The `.atv` file also holds more than the Actives table — Reserve Gain, Power
Steps, Pads/EQ banks 1–8 and a Configuration Table are further pages. Where the
Actives table ends is not mapped, so the reader validates each record instead of
assuming: past the end the fixed stride reads into another page and yields
levels like 538.97 dB. In both sample sets the real actives occupy slots 7–46.

| file | kind | source |
|---|---|---|
| `AL002.ntw` … `AL005.ntw` | network designs | written by *Design 12.11*, licence `LP-13X00J3`, user `vk1091` |
| `KERMIT750-2026.{par,cbl,cpr,tap,atv}` | equipment spec set | licence `LP-BSQN2J3` (`.atv`: `LP-990XYP3-1`) |
| `WVBeck750.{par,cbl,cpr,tap,atv}` | equipment spec set | same licences, different content |

The layouts below were inferred from the bytes and cross-checked against real
HFC hardware specifications. Several of them have since been **confirmed against
the vendor manual**, recovered through web search because `docs.lodedata.com`
itself is blocked by this environment's egress proxy — see
`lode-data-manual-notes.md` for how, and for what that does and does not prove.
Items still unverified are marked **(unconfirmed)**.

---

## 1. The common 512-byte header

Every Lode Data file — network and spec alike — starts with the same header.

| offset | size | field |
|---|---|---|
| 0 | 26 | magic string, NUL-padded |
| 26 | 1 | format major version |
| 27 | 1 | format minor version (always `1` in the samples) |
| 28 | 100 | application version string, e.g. `Design 12.11` (only `.ntw` fills this in) |
| 128 | 1 | zero |
| 129 | 16 | licence / dongle id, e.g. `LP-13X00J3`, NUL-terminated |
| 145 | 16 | user id, e.g. `vk1091`, `SEASTMAN`, `CCJ` |
| 161 | 351 | reserved; `.ntw` sets a single byte `0xE2` at offset 402 **(unconfirmed)** |
| 512 | — | payload starts |

Magic strings seen, and the format major they carry:

| magic | ext | major |
|---|---|---|
| `Lode Data Network File` | `.ntw` | 12 |
| `Lode Data Actives File` | `.atv` | 12 |
| `Lode Data Cables File` | `.cbl` | 11 |
| `Lode Data Couplers File` | `.cpr` | 11 |
| `Lode Data Taps File` | `.tap` | 11 |
| `Lode Data Parameters File` | `.par` | 11 |

The licence id and user id are stamped per-file, not per-set: in both sample spec
sets the `.atv` file carries a *different* licence and user from its four
siblings, i.e. the actives table was authored separately and shipped alongside.

---

## 2. `.ntw` payload obfuscation — solved

Everything after the header is scrambled with a **fixed 100-byte additive
keystream**:

```
cipher[i] = (plain[i] + KEY[i % 100]) & 0xFF
plain[i]  = (cipher[i] - KEY[i % 100]) & 0xFF
```

The key is a constant compiled into the application. It is byte-identical in all
four sample files despite different licences, users, sizes and designs:

```
5d7e57377b74352c3915272eca57591d29175c4f2384292d30371140762b4651
3c2f7182647e5620103d4cab73603e616d24c41b2b5d6fd2d75464156a4c6463
9611726b167e435a353f5f35747be4445d155928ad54c42f123cb2182ed73e18
162a69c2
```

How it was recovered: a design file is mostly untouched pre-allocated table
space, i.e. plaintext zeros, so the ciphertext there *is* the keystream. The
longest run satisfying `c[i] == c[i+100]` is ~8 000 bytes and hands over the key
directly. `lodedata.obfuscation.recover_key()` re-derives it from any file and
all four samples agree.

The cipher is **additive, not XOR**. This matters and it is the trap in this
format: XOR-decoding with the same key also turns the padding into zeros, so it
looks right, but every real field comes out as a bit-mask artefact
(`0x01/0x03/0x07/0x0f/…`) because `key ^ (key−1)` is a mask. Subtracting instead
turns those same bytes into clean `0xFFFF` ("empty" sentinels) and clean
fixed-point numbers. Phase is 0 relative to offset 512; all 100 phases were
tested and only phase 0 produces a low-entropy result.

### What the decoded payload looks like

* 96–97 % of the payload is zeros — the tables are pre-allocated far beyond what
  a given design uses. `AL002.ntw` is 951 KB and holds ~40 KB of live data.
* **There are no text strings anywhere in a `.ntw` file.** Verified over all 100
  key phases. Part numbers are therefore stored as *indices into the spec files*,
  not as names — which is exactly why a design cannot be opened without its spec
  set, and why re-pointing a design at a new spec set is a meaningful operation.
  The manual confirms the split: spec files "define every piece of equipment used
  by the Design Assistant and every operating parameter of the program".
* `0xFFFF` / `0xFFFFFFFF` is the "unset / not connected" sentinel.
* Numbers are little-endian and follow the same 1e6 fixed-point convention as the
  spec files.
* Structure found so far: a 261-byte-stride block near the start whose first five
  records are an identical 10-byte value (a password or checksum block
  **(unconfirmed)**), then tables with strides around 21 bytes (3-byte entries of
  `int16 + byte`, `-1` when unused) and larger device tables. Full record layout
  is **not yet mapped** — see `docs/open-questions.md`.

Constraints the manual gives for that mapping, all useful when the tables are
finally identified:

* A **node** is one screen line — a pole or pedestal — and a **branch** is a run
  of nodes starting from a coupler. So the design is branches of nodes, not a
  free-form graph.
* **House count per node maxes at 63**, a 6-bit field.
* Branch type is carried alongside the branch number: normal, no-footage,
  backfeed, forwardfeed.
* A `.LCK` sidecar next to the `.NTW` marks the file open by another user.

---

## 3. Spec files — record tables

All four data spec files are flat arrays of fixed-stride records after the
header, pre-allocated to a constant capacity (which is why two different spec
sets are byte-for-byte the same length).

| file | data starts | stride | capacity | used in `KERMIT750-2026` |
|---|---|---|---|---|
| `.cbl` cables | 512 | 394 | 100 | 24 |
| `.cpr` couplers | 626 | 114 | 1064 | 44 |
| `.atv` actives | 849 | 362 | ~753 | 40 |
| `.tap` taps | 512 | 908 | 256 | 25 |
| `.par` parameters | 512 | single record | — | — |

**Numeric convention: signed little-endian `int32` holding the real value × 1 000 000.**
Confirmed independently three ways — cable loop resistance, coupler values that
match their own part numbers, and amplifier gains that come out as exact
integers (19.0, 15.0, 21.0, 49.0, 38.0, 43.0 dB).

Live `.cbl` and `.cpr` records begin with the marker byte `0x6F`; empty slots are
zero-filled. Strings are NUL-terminated inside fixed-width fields, often
right-aligned with leading spaces.

### 3.1 `.cbl` — cable types (394 bytes)

| offset | type | field |
|---|---|---|
| 0 | u8 | `0x6F` record marker |
| 1 | u16 | cable ID, 0–99. **Even = aerial, odd = underground** |
| 5 | char[25] | cable name, e.g. `EX .625P3 AER` |
| 30 | i32 | loop resistance, ohms per **foot** (`1070` → 1.07 Ω/1000 ft). `99` means never power this — the convention for fibre |
| 34 | i32[10] | loss block (see below) |
| 74 | i32[10] | second loss block, identical to the first in every sample **(unconfirmed what distinguishes them)** |
| 114 | char[15] | footage/marker part, e.g. `FT-625` |
| 129 | char[15] | connector part, e.g. `PT-625` |
| 144 | i32[5] | flags, all `1` in the samples **(unconfirmed)** |

The table is exactly 100 records, matching the manual's "one hundred different
types of cable, numbered 0 through 99". The aerial/underground parity rule holds
for all 62 named cables across both sample spec sets, with no exceptions.

**The loss block** — the same ten-slot layout is used by the coupler file:

| index | meaning |
|---|---|
| 0 | dB/100 ft at the forward **High** frequency |
| 1 | dB/100 ft at the forward **Low** frequency |
| 2–5 | the four optional extra forward frequencies |
| 6 | at the return **Rh** frequency (default 42 MHz) — stored negative here |
| 7 | at the return **Rl** frequency (default 5 MHz) — stored negative here |
| 8–9 | the two optional extra return frequencies |

The frequencies themselves live in the Parameters file, so an importer has to be
told the frequency plan rather than assume one. Confirmed numerically over 62
cables in two independent spec sets — medians, because the values are hand-typed
from manufacturer charts and no individual cable follows the √f law exactly:

| ratio | KERMIT | WVBeck | √f prediction |
|---|---|---|---|
| Low / High | 0.2528 | 0.2541 | √(54/860) = 0.2506 |
| Rh / Low | 0.8828 | 0.8750 | √(42/54) = 0.8819 |
| Rl / Low | 0.2989 | 0.2889 | √(5/54) = 0.3043 |

Both sample sets were therefore entered against roughly a 54 / 860 MHz forward
band with the default 42 / 5 MHz return, despite both being named "750".

Loop resistance is the strongest confirmation that the decode is right — the
values land exactly on the published figures for the real cables:

| cable | file | published |
|---|---|---|
| `.500 P3` | 1.72 Ω/1000 ft | 1.72 |
| `.625 P3` | 1.07 | 1.07 |
| `.750 P3` | 0.76 | 0.76 |
| `.875 P3` | 0.55 | 0.55 |
| `RG-6` | 36.00 | ~36 |
| `540 QR` | 1.61 | ~1.6 |

The coefficient block is the attenuation model. Only the first two or three
entries are used (`.500P3` → `2.16, 0.52`; `RG-6` → `5.65, 1.60, 2.45`), plus a
negative pair at indices 6–7 (`−0.48, −0.16`). The coefficients are consistent
across cables (`b ≈ 0.25·a`, `c ≈ 0.84·a`) and reproduce the correct *relative*
attenuation between cable sizes, but the absolute scaling does not fall out
without knowing the normalising frequency — **the exact formula is unconfirmed**
and is the single highest-value thing to pin down (see open questions).

### 3.2 `.cpr` — couplers, splitters, power inserters (114 bytes)

| offset | type | field |
|---|---|---|
| 0 | u8 | `0x6F` record marker |
| 1 | i32 | packed value code |
| 5 | char[25] | part number, e.g. `SSP-7K`, `RLDC12-8`, `MDU COUPLER` |
| 30 | i32[10] | **Tap** leg loss block |
| 70 | i32[10] | **Thru** leg loss block |
| 110 | u8 | tap legs, stored as the count minus one |
| 113 | u8 | internal-coupler flag |

Same loss-block layout as the cable file — the manual describes "four columns to
the right of the Thru label … at the forward high, forward low, return high, and
return low frequencies". Decoding the two blocks that way produces a coherent
directional-coupler family:

| part | leg A | leg B |
|---|---|---|
| SSP-3K | 4.9 | 4.9 |
| SSP-7K | 8.1 | 3.5 |
| SSP-9K | 10.2 | 2.9 |
| SSP-12K | 13.4 | 2.2 |

Looser coupling costs more on one leg and less on the other, and the balanced
part has equal legs. The manual settles the order: "The next columns labeled
**Tap** … The four columns to the right of that labeled **Thru**". Decoding
`WVBeck750` that way gives a textbook directional-coupler family — RLDC-8
3.5/8.8 dB, RLDC-12 2.9/12.5, RLDC-16 2.9/16.5 — and the coupler ID column
comes out as the manual describes ("2 for a 2 way splitter or 8 for a DC 8"):
`RLS10-2-15A` → 2, `RLDC-8-15A` → 8, `RLDC-16-15A` → 16. The 3-way splitter
reports two tap legs and the part named `INT 2-WAY` has the internal flag set.

The code at +1 is exactly the dB value in the part number for the simple parts
(`SSP-3K` → 3, `SSP-7K` → 7, `SSP-9K` → 9, `SSP-12K` → 12) but is a packed
family+value for the rest (`RLDC12-8` → 408, `GNA INT DC-12` → 612,
`MGDCH-2116F` → 216) — **splitting rule unconfirmed**.

### 3.3 `.atv` — actives: amplifiers, line extenders, nodes (362 bytes)

| offset | type | field |
|---|---|---|
| 5 | char[13] | model, e.g. `BLE-7-750PSS`, `BTN NODE-12`, `FM902B` |
| 18 | char[2] | housing code, e.g. `S` |
| 20 | char[10] | (blank in samples) |
| 30 | char[10] | option/kit part, e.g. `RA-KIT\40` |
| 40 | char[5] | second option part, e.g. `T\40` |
| 45 | char[10] | (blank in samples) |
| 59 | i32[4] | **In** — level required at forward High, forward Low, return Rh, return Rl. The manual's own column headings read `In - 860 | In - 54 | In - 42 | In - 5`, matching the frequencies derived independently from the cable ratios |
| 75 | i32[4] | **Out** — level produced at the same four frequencies |
| 91 | i32[2] | zero in every sample |
| 99 | i32[2]×n | **Power Steps**: (volts, amps) pairs, ends at a zero entry |

Confirmed by the manual: the actives file holds "the signal levels required at
the forward and return inputs, as well as the forward and return outputs
produced by each active as indicated by the column prefix In or Out", plus
"power requirements".

| part | In (Fh, Fl, Rh, Rl) | Out (Fh, Fl, Rh, Rl) | forward gain | output tilt |
|---|---|---|---|---|
| BLE-7-750PSS | 19, 15, 21, 21 | 49, 38, 43, 43 | 30 dB | 11 dB |
| MB-750D-H | 12, 11, 21, 21 | 49, 38, 40, 40 | 37 dB | 11 dB |
| BTN NODE-9 | **99**, 0, 27, 27 | 46, 36, 0, 0 | — | 10 dB |

These are *module* levels, not housing levels: the manual adds roughly 3 dB for
the input test point, diplex filter and the equalizer's minimum high-channel
loss to get the housing input minimum that an incoming cable level is checked
against.

**A forward input of 99 is the "no RF input" sentinel** — the same convention as
loop resistance 99 on cables. It marks a fibre-fed optical node, and identifies
parts whose name does not say so (`5F31QSA004-9`).

The trailing table is the manual's **Power Steps** page, and it is a *step*
function rather than a curve to interpolate: "from Vmin to V2, it uses A1
amperes; from V2 to V3, A2 amperes are used". The lowest voltage present is
Vmin, "the lowest voltage at which the active will operate". It works out as
constant power, which is why a table is needed at all — an active draws more as
the applied voltage sags:

| MB-750D-H | 38 V | 45 | 52 | 60 | 70 | 80 | 90 |
|---|---|---|---|---|---|---|---|
| amps | 1.12 | 0.96 | 0.83 | 0.72 | 0.62 | 0.54 | 0.48 |
| watts | 42.6 | 43.2 | 43.2 | 43.2 | 43.4 | 43.2 | 43.2 |

### 3.4 `.tap` — taps (908 bytes) — solved

One record holds one tap *value*, with a sub-block per port count. The manual:
"63 different types of taps may be entered. Each type is available in 2-way,
4-way, 6-way, and 8-way."  The file allocates 256 slots; the samples use
indices 0–38.

| offset | port count | drawn as |
|---|---|---|
| 16 | 8-port | `<26>` |
| 134 | 2-port | `/26/` |
| 246 | 4-port | `[26]` |
| 358 | 6-port | `{26}` |

The bracket style is how the Design screen identifies the port count, quoted
from the manual. Beside the port slots, **offset +129 holds the Tap ID** — the
row's identifying value, which "usually corresponds to the actual tap value"
and is what the screen prints inside the brackets. It matches the value in the
2-port part number in every record of both sample spec sets, and the rows
descend from the highest value, as the manual says they should.

Each slot holds a 14-character part number, then two ten-slot loss blocks in
the same layout as cables and couplers:

| relative to the part number | field |
|---|---|
| +25 | **Tap Value** — loss toward the tap ports |
| +65 | **Tap Losses** — insertion loss, hard cable in to hard cable out |

Verified against a vendor whose part numbers played no part in deriving the
offsets: in `WVBeck750`, `RMT2008-RF-20` at the 8-port slot decodes to exactly
20.0 dB, `RMT2002-RF-23` at the 2-port slot to 23.0, `RMT2004-RF-17` at the
4-port slot to 17.0. Insertion loss behaves correctly too — the 4-port version
of a 23 dB tap costs more through-loss (1.2 dB) than the 2-port (0.9 dB).

Not yet located inside the record: the Self Term and Active flags, the Active
Taps powering table, Tap Swap Options and the Pad/EQ bank pointers, all of
which the manual says live in this file.

### 3.5 `.par` — system design parameters

A single record holding the system-wide settings. Readable content includes a
byte table (values `0x03`) and an index ramp `0x00…0x20` (33 entries — a
frequency/channel plan of 33 points **(unconfirmed)**), the string
`HOUS TO HOUS`, device-class abbreviations (`SGMC`, `GTRM`/`NATOR`), and a list
of named plans: `TV-60`, `TV-80`, `TV-104`, `TV-106`, `TV-1024`. Field-level
layout is **not yet mapped**.

---

## 4. Tooling in this repo

```
PYTHONPATH=tools python3 -m lodedata info   <any lode data file>...
PYTHONPATH=tools python3 -m lodedata decode <in.ntw> <out.bin>
PYTHONPATH=tools python3 -m lodedata spec   <base path without extension> [--json]
```

`info` also re-derives the `.ntw` keystream from the file itself and reports
whether it matches the known constant — a cheap check that a new sample uses the
same scheme.
