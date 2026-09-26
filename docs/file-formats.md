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

Everything after the header is scrambled byte by byte: the two **nibbles of
each plaintext byte are swapped**, then a **fixed 100-byte keystream is added**:

```
cipher[i] = (nibswap(plain[i]) + KEY[i % 100]) & 0xFF
plain[i]  = nibswap((cipher[i] - KEY[i % 100]) & 0xFF)
nibswap(x) = ((x << 4) | (x >> 4)) & 0xFF
```

The key is a constant compiled into the application. It is byte-identical in all
sample files despite different licences, users, sizes and designs:

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
all samples agree. Phase is 0 relative to offset 512.

The nibble swap is invisible on zeros (`nibswap(0) == 0`), which is why a plain
"subtract the key" decode looked right at first: padding came out clean and the
sentinels came out as `0xFFFF`, but every real value was nibble-swapped
garbage. It was found with known plaintext from the AL004 design and its Power
mode screen: with the swap, the amplifier labels `AL00416` / `AL00419` and the
node-1 footage `476` decode exactly. (XOR with the same key is also wrong — it
produces bit-mask artefacts.)

### What the decoded payload looks like

* 96–97 % of the payload is zeros — the tables are pre-allocated far beyond what
  a given design uses.
* **Text is stored in clear** once decoded (fixed-width, NUL padded):
  * the spec set name five times at a 261-byte stride from payload start
    (`WV750-2026`, one per spec file type), and again five times further on;
  * `Untitled` three times, and the network name (`AL004`) twice;
  * the **labels** typed against nodes/actives (`AL00401` … `AL00432`,
    `AL004A`).
* Part numbers are **not** stored as names, so equipment is referenced by the
  spec's numeric IDs (cable ID, coupler ID, tap ID, active ID). That is why a
  design cannot be opened without a spec set, and why re-pointing a design at a
  new spec set is meaningful.
* `0xFFFF` / `0xFFFFFFFF` is the "unset / not connected" sentinel.
* Numbers are little-endian.
* The network itself — branches of node records — is mapped in section 3.7.

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

The trailing table is the manual's **Power Steps** page. How it is read
between steps is a Parameters setting — "Power interpolation: Step, Linear or
Constant Wattage". WV750-2026 runs **constant wattage**: the draw is
interpolated in watts and divided by the voltage. That reproduces every one of
the 29 currents on AL004's branch 4 Power screen (e.g. the Ripple node at
85.6 V draws 1.74 A; holding the 80 V step would give 1.86). The table works
out as near-constant power, which is why it exists at all:

| MB-750D-H | 38 V | 45 | 52 | 60 | 70 | 80 | 90 |
|---|---|---|---|---|---|---|---|
| amps | 1.12 | 0.96 | 0.83 | 0.72 | 0.62 | 0.54 | 0.48 |
| watts | 42.6 | 43.2 | 43.2 | 43.2 | 43.4 | 43.2 | 43.2 |

**The volts need one more rule: a span's resistance is whole milliohms,
truncated** — feet × the cable file's µΩ/ft, integer-divided by 1000 (136 ft of
EX P3 750 A, 760 µΩ/ft, is 0.103 Ω, not 0.10336). With it all 29 volts on
branch 4 match to the hundredth, and AL00415's map tag (86.78 V, 0.79 A);
without it the drop runs ~0.5 % high and 16 of 29 are off by 0.01–0.02 V.
Checked against the alternatives: truncating to 0.1 mΩ or 10 mΩ, rounding
instead, or rounding currents, span drops or node volts each leave 12–27 of
the 29 wrong. The Parameters file has no resistance or temperature setting.

**Active IDs and the index a design uses.** The actives table starts six
records into the record area: a design file stores an active as an index `i`,
and its record is `i + 6`. The Active ID shown in the amp column is *text* —
the manual allows "numeric or alphabetic", and WV750 has `11H`, `21H` — held in
the Configuration Table part of the record: eight 18-byte slots from +214, the
ID 5 bytes into each. Slot 0 is the base unit, the others plug-in variants
(`FM902B` = `68`, `68N`, `68U`, `68M`, `68S`, `68B`). WV750's default scheme:
11/21/22/31/32/33 line extenders by cascade position, 11H–33H alternates,
61 and 41 Bridgers, 63–71 and 78 nodes and fibre receivers (70 = `Ripple`).

An In level of 0 on both forward columns (WV750's `Ripple`, `NC4000`) marks a
fibre-fed node, like the 99 sentinel.

### 3.4 `.tap` — taps: 454-byte rows — solved

After the header comes a 129-byte prefix, then **512 rows of 454 bytes** from
offset 641. A row is one **Tap ID** with a part for each port count:

| row offset | field | drawn as |
|---|---|---|
| 0 | i32 ×1e6 Tap ID | |
| 5 | 2-port part | `/26/` |
| 117 | 4-port part | `[26]` |
| 229 | 6-port part | `{26}` |
| 341 | 8-port part | `<26>` |

Each part slot is 112 bytes: the part number, then two ten-slot loss blocks in
the same layout as cables and couplers — **Tap Value** (toward the ports) at
+25 and **Tap Losses** (insertion) at +65. An all-zero insertion block marks a
terminating tap: nothing continues past it and the screen shows 0.00 on the
line below.

A design stores a tap as **(row, port code)**, port code 0/1/2/3 = 2/4/6/8
ports. Confirmed on AL004: rows 3, 5, 7, 9, 10 and 11 of WV750-2026 are Tap IDs
20, 17, 14, 11, 8 and 4, and its Design screen shows exactly `[20]`, `/17/`,
`/14/`, `/11/`, `/ 8/`, `/ 4/` where the file has those rows. 8-port taps are
often a row of their own (WV750 has 8-port 18 on row 4, 2/4-port 17 on row 5).

An earlier reading used 908-byte records at 512 with the 8-port part at +16.
It lined up for 2/4-port parts on even rows only, skipped every odd row and
paired each 8-port part with the row before it. Corrected here.

On the Design screen a 6-port-slot part (WV750's LEQ\RC pads) is drawn `<43>`;
the branch preview in the info box draws 2-port `(n)`, 4-port `[n]`, 8-port
`{n}`.

WV750's six tap families (Tap IDs): MGT 4–24, LEQ\RC pads 30–45 (6-port slot),
AN-WIFI 104–124, RMT1 204–235, RMT2 404–426.

### 3.4b `.atv` in-line devices (Q1, Q2 …)

The Actives file's Bridgers/Feedermakers/Inline Eqs page: 69-byte records from
offset 169372 (the file is a fixed 273200 bytes), record n = Qn. Name, then at
+29 the losses at the four design columns F1, F2, R1, R2. WV750: Q1 LEQ-PEA-8,
Q2 LEQ-PEA-0 (1.2 / 1.0 / 1.2 / 0.7), Q3 FFE-8-120-85/RP-R, Q5 EXIST SPLICE,
Q6 NEW SPLICE, Q10–Q13 REMOVE/MOVE LE/BR markers. Placed in the amp column the
device's loss applies before the node's taps; on AL004 6.8 that gives exactly
the screen's 30.73 / 32.31 / 39.23 / 36.85 on 6.9.

### 3.5 `.par` — system design parameters

Mapped against screenshots of all six Spec Edit → Parameters tabs of
WV750-2026.par, and cross-checked by diffing KERMIT750-2026.par (same
offsets, different values). Numbers are i32 ×1e6 unless marked u8/u16.
**Proven** = a value on the screen that no other field shares, or a
whole table that matches row for row.

| offset | field | WV750 | status |
|---|---|---|---|
| 512 | u8[33] Tap Selection, Ports → Tap Type, ports 0–32, as port code 0/1/2/3 = 2/4/6/8 | 1–2 → 2, 3–4 → 4, 5+ → 8 | proven |
| 545 | u8[33] Tap Selection, Homes → Number of Ports, homes 0–32 | n → n | proven |
| 578 + 25·k | char[25] HTH Connectors, Splices, Terminators (3 more blank slots follow) | HOUS TO HOUS, SGMC, GTRM | proven |
| 728 + 25·k | char[25] underground housing part numbers, 13 slots | TV-60 … TV-1024 | proven |
| 1053 | u8 Strand/Trench Types 000–500, bit n = series n00 ticked | 0x1D = 000 200 300 400 | proven for the pattern; 800 is elsewhere (3914), 600/700/900 not placed |
| 1056 | u8 points, Equalizer | 5 | proven (test copy: 9) |
| 1057 | u8 points, Amplifier | 16 (KERMIT 36) | proven |
| 1058 | u8 points, Line Extender | 11 | proven |
| 1059, 1060, 1061 | u8 points, 2/4/6 Port Tap, 8 Port Tap, Coupler | 5 5 5 | proven (test copy: 6 7 8) |
| 1062 | u8 points, Power Supply | 30 | proven |
| 1063 + k | u8 housing k+1 Minimum Size (Points) | 4 6 11 17 27 | proven |
| 1082 | ×4: 12, 16, 16, 16 | same in KERMIT | unknown — equals the four design tap windows |
| 1098 + 4·k | NIU: System Penetration %, Offhook %, Ring %, Additional Line %, Offhook Limit | 0 ×5 (KERMIT 47 53 51 54 0) | proven (test copy: 1 2 3 4 5). Whole numbers: 1.11 typed comes back as 1.0 |
| 1118 | Max. Crossover | 3.00 | proven (test copy: 3.25) |
| 1122 | Max Return Crossover | 99.00 | proven |
| 1126 | Max. LE Cascade | 3 (KERMIT 2) | proven (test copy: 4) |
| 1130 | Lines per Form | 0 (KERMIT 45) | proven (test copy: 44) |
| 1134 | Tap Margin | 0.50 | proven |
| 1138 | Signal Display, 0 dBmV / 1 dBuV | 0 | proven (save chain s2) |
| 1142 | Distance Units, 0 Ftg / 1 m (dM not seen) | 0 | proven (save chain s1) |
| 1146 | Replacement Cables, Backfeed | 0 | proven (test copy: 7) |
| 1154 + 20·lv | System Levels lv 0–15: Min 750, Min 54, Max 40, Max 5, then one more (0) | 17 10 45 45 / 19 12 45 45 | proven (5th unknown) |
| 1470 | Replacement Cables, Fwd. Feed | 0 | proven (test copy: 9) |
| 1474 | u8 Power Interpolation, 0 Step / 1 Linear / 2 Constant Wattage | 2 (KERMIT 0) | proven (test copy: 1) |
| 1478 | u8 Overvoltage Check, 1 = On | 0 (KERMIT 1) | proven (test copy: 1; Pre Load left Off) |
| 1482 | Optimization, 0 OP- / 1 OFf (OP+ not seen) | 0 | proven (save chain s6) |
| 1486 + 4·k | Maximum Amperage Through: Power Inserter, Amplifier, Bridger Port, Coupler, Line Extender, Tap | 16 15 15 15 15 12 | proven (test copy: 16 15.1 15.2 15.3 15.4 12) |
| 1510 | Default EQ Placement, 1 EQ+ / 2 EQe (EQ- not seen) | 1 (KERMIT 1) | proven (save chain s5) |
| 1567 + 25·k | power supply ID k+1 part number, 25 slots | EXISTING STDBY … | proven |
| 2212 + 20·k | power supply ID k+1: Voltage Rating, Current Rating, % Capacity | 60/15/85, 60/15/90, 90/15/90, 90/15/85 | proven |
| 2972 | i32 raw 7777 | same in KERMIT | unknown (a marker?) |
| 2976 + 24·lv | Min 550 (freq 3) of level lv, then presumably Min F4–F6, Max R3–R4 | 15 / 17 | Min F3 proven; the rest of the 24 bytes assumed |
| 3792 + 10·k | frequency k (F1–F6, R1–R4): char[5] label, u8 enabled, i32 tap window | 750 54 550* F4* F5* F6* 40 5 R3* R4* (*off); windows 12 16 · 16 16 | proven |
| 3894, 3898 | u8 1, 1 | same in KERMIT and the test copy | unknown |
| 3900, 3905 | u8 pairs 100/30, 101/30 | same in KERMIT and the test copy | unknown — not the replacement cables |
| 3904 | u8 Enforce Tap Window | 0 | proven (save chain s7) |
| 3909 | u8 Max. Tap Cascade | 0 | proven (test copy: 6) |
| 3911 | u8 Allow Over Equalization | 1 (KERMIT 0) | proven (test copy: unticked → 0) |
| 3914 | u8 Strand/Trench Types, 800 Series | 0 | proven (save chain s4) |
| 3916 | Transformer 1 part number, typed `XFMR-T1`, saved as `FMR-T1` (no `X` anywhere in the file); then the voltage as text ` 60.5` at 3923 | blank | partly |
| 4171 | Transformer 1 voltage, i32 ×1e6 (unaligned) | 0 | proven (test copy: 60.5) |
| 6001 | u8 Flag Hi/Lo Tilt | 0 | proven (save chain s8) |
| 6002 + 16·lv | System Levels Max Tilt Fwd, Min Tilt Fwd, Max Tilt Ret, Min Tilt Ret | 0 | proven (test copy level 0: 1.10 2.20 3.30 4.40) |
| 6514 | u8 Show Count Types | 0 | proven (save chain s3) |

The user's test copy (WV750-2026.par re-saved with a distinct value in every
field, `samples/partest/paratest.par`) placed most of the rest. Re-saving
also writes the header as format 12.1, blanks the licence and user ids, and
adds one byte at the end (6516 bytes).

A chain of eight saves, each undoing one setting of the test copy
(`samples/partest/s1.par` … `s8.par`), placed the eight radio and checkbox
fields that had all saved as 1. Saving also stamps the saver's licence and
user ids into the header.

Still not placed: Strand/Trench 600, 700 and 900; Enforce Tap Tilt; Pre Load;
the third choice of Distance Units (dM), EQ Placement (EQ-) and Optimization
(OP+); Freqs. for Active EQ Selection; Min F4–F6 / Max R3–R4 (assumed to
follow Min F3 at 2976); transformers 2–8.

What the replica uses: frequencies and System Levels (tap colours), tap
margin, Strand/Trench Types (a branch with footage only on unticked series
can be `<n>`), Power Interpolation, and the supply table.

### 3.6 `.cpr` record mark

The first byte of a live cable or coupler record is the file's format version
(major·10 + minor): `0x6F` in an 11.1 file, `0x79` in a 12.1 file. WV750's
`.cpr` is 12.1, which is why an earlier reader that looked for `0x6F` found no
couplers in it.

### 3.7 `.ntw` — the network

The payload is the branches in order, each

```
branch record   1966 bytes
node records    1970 bytes, or 2504 when the node carries an active
end record      44 bytes, starting 4 bytes after the last node record
```

Records are also linked: each starts with its own id, the previous node's id
(the branch number for a branch's first node) and the next node's id.

Node record, offsets from its id:

| offset | field |
|---|---|
| 0 / 4 / 8 | u32 id, previous id (or branch number), next id |
| 12 | u16 footage |
| 14 + 21·k | tap slot k (0–3): i32 tap-file row (−1 empty), u8 port code |
| 98, 102 | u32 branch started here, first and second coupler column |
| 106, 107 | amp column: an active when both bytes are the actives index; an in-line device Qn when they are 80−n and 24−n (Q1 = 79/23, Q2 = 78/22, Q5 = 75/19) |
| 112 + 3·k | forward pad, return pad, forward EQ, return EQ (amps only) |
| 128 | u8 fixed (locked) — drawn as `→` left of the footage |
| 129 | u8 house count |
| 130 | u16 cable ID as displayed (series·100 + cable file index) |
| 132 | u8 lv (System Levels row) |
| 133 | u8 power stop in the span leading to this node |
| 135 | u8 power supply type (Parameters file) |
| 701 | u8 extended record (actives and power supplies) — the record is then 2504 bytes |
| 726 | power supply label (`A`) |
| 981 | Amplifier Definition name (`AL00416`) |

Branch record: +0 id of the node carrying its coupler (0 for branch 1), +4
first node id, +8 u16 node count, +126 u8 coupler file record + 1 (the coupler
that starts the branch), +131 non-zero when this branch takes the through leg
(`3-<11><12>`). End record: the last node's next id, then the last node's id.
Both checked on all 45 AL004 branches.

**No branch type is stored.** `<n>` against `[n]` (forwardfeed/backfeed against
normal) is not in the branch record, the coupler's node, the branch's nodes,
the end record, or any per-branch byte, bit or list anywhere in the file:
AL004's branches 2 `<2>` and 3 `[3]` have byte-identical branch records and
coupler nodes apart from ids. The program derives it — see open question 1.

Everything above was checked against AL004's screens: all 29 footages, cables,
house counts, taps, couplers, both amplifiers and their names on branch 4;
181 homes in total (the node's "Housecounts downstream"); 120 downstream of
AL00416 (its info box); pads 4 and 14 on AL00416 (its info box says Fwd Pad 4,
Ret Pad 14). The power stop field is confirmed on one design only.

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
