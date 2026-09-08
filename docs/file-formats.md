# Lode Data file formats — reverse-engineering notes

Everything here was derived from the sample files supplied with this task:

| file | kind | source |
|---|---|---|
| `AL002.ntw` … `AL005.ntw` | network designs | written by *Design 12.11*, licence `LP-13X00J3`, user `vk1091` |
| `KERMIT750-2026.{par,cbl,cpr,tap,atv}` | equipment spec set | licence `LP-BSQN2J3` (`.atv`: `LP-990XYP3-1`) |
| `WVBeck750.{par,cbl,cpr,tap,atv}` | equipment spec set | same licences, different content |

Nothing below comes from vendor documentation — `docs.lodedata.com` is blocked by
this environment's egress policy, so every statement here is an inference from
the bytes, cross-checked against real HFC hardware specifications where possible.
Items that are still guesses are marked **(unconfirmed)**.

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
* `0xFFFF` / `0xFFFFFFFF` is the "unset / not connected" sentinel.
* Numbers are little-endian and follow the same 1e6 fixed-point convention as the
  spec files.
* Structure found so far: a 261-byte-stride block near the start whose first five
  records are an identical 10-byte value (a password or checksum block
  **(unconfirmed)**), then tables with strides around 21 bytes (3-byte entries of
  `int16 + byte`, `-1` when unused) and larger device tables. Full record layout
  is **not yet mapped** — see `docs/open-questions.md`.

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
| 1 | u16 | record index |
| 5 | char[25] | cable name, e.g. `EX .625P3 AER` |
| 30 | i32 | loop resistance, ohms per **foot** (`1070` → 1.07 Ω/1000 ft) |
| 34 | i32[10] | forward-path coefficients |
| 74 | i32[10] | return-path coefficients (identical to forward in every sample) |
| 114 | char[15] | footage/marker part, e.g. `FT-625` |
| 129 | char[15] | connector part, e.g. `PT-625` |
| 144 | i32[5] | flags, all `1` in the samples **(unconfirmed)** |

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
| 30 | i32[…] | port losses (through / tap), 1e6 fixed point |

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
| 59 | i32[…] | gains, levels and a frequency-response table |

The numeric block decodes to sensible amplifier data: `19.0, 15.0, 21.0, 21.0,
49.0, 38.0, 43.0, 43.0` (gain and operating-level figures) followed by pairs that
look like a response table — `(38, 0.69) (45, 0.62) (52, 0.58) (60, 0.54)
(70, 0.47) (80, 0.43) (90, 0.39)`. Which column is frequency and which is
gain/tilt is **unconfirmed**.

### 3.4 `.tap` — taps (908 bytes)

One record holds one tap *value*, with the part numbers for each port count:

| offset | field |
|---|---|
| 16 | 8-port part number, e.g. `MMT2830` |
| 134 | 2-port part number, e.g. `MMT2229` |
| 246 | 4-port part number, e.g. `MMT2429` |
| 588, 700 | two further part-number slots, unused in the samples |

Within a record there are sub-blocks on a 112/118-byte pitch, each ending in an
`0xFFFFFFFF` sentinel and carrying an incrementing index byte. Tap through-loss
and tap-loss values live in these sub-blocks; exact offsets are **unconfirmed**.

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
