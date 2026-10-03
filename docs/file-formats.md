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
| `AL002.ntw` … `AL005.ntw` | network designs | written by *Design 12.11*, with a licence id and user id |
| `KERMIT750-2026.{par,cbl,cpr,tap,atv}` | equipment spec set | with a licence id (the `.atv` another) |
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
| 129 | 16 | licence / dongle id, `LP-` and letters and digits, NUL-terminated |
| 145 | 16 | user id, NUL-terminated |
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

### Decode status (2 Oct) — what is still not known

`python tools/spec_coverage.py` maps every byte the readers use and lists
the rest. Bytes in use explained, blank text aside (WV750 / WVEXT862 /
KERMIT / SHINSTON): cables 100 / 100 / 100 / 100 %; couplers 99.9 / 99.9 /
100 / 99.9; actives 96 / 99.8 / 97 / 93; taps 29 / 63 / 25 / 25;
parameters 97 / 95 / 97 / 95. Every file of the five sets is a layout
already checked against Lode (`tests/test_spec_sets.py`); a set with another
version or size is reported by the tool. What no file explains yet:

* **Taps.** Byte +4 of each row (1–4: WV750 4 on most rows, 1 on 17, 2 on
  the AN-WIFI rows); in each port slot, after the two loss blocks, the port
  code (0–3, redundant), a byte 1 on a few rows (WVEXT862's two AN-WIFI
  taps that feed branches), and four bytes FF FF FF FF (KERMIT's 6-port
  rows 08 08 08 08); bytes 580 (35.0 in WV750 and WVEXT862, 0 in the others)
  and 640 (1) of the file.
* **Actives** (most of it placed 2 Oct from the user's recording of
  NBERN1GHz's Actives window, every tab: 3.3, 3.4d). Still unknown: where
  the Actives tab's **Out/Loss** columns are kept (every row of the
  recording reads `0 Out`); the two figures after the power steps (+163,
  +167) and after In F6 (+187, +191) — R3/R4? — and the three bytes before
  the Configuration Table; the Configuration Table's **Quantity** columns
  (Plugin 1 is +10 of each slot); the Plug-Ins / Plug-Ins Powering figures
  (only the names are placed), Bridgers, Feedermakers and the 12.1 file's 24
  boosters — empty in every file sent, so drawn empty as Lode draws them for
  NBERN1GHz.
* **Couplers.** The code at +1, shown as the coupler's ID (`100`, `12`, `2`);
  how it packs a family and a value (408, 612, 216) is not known.
* **Cables.** The second loss block (equal to the first in every file) and
  the five flags (all 1).
* **Parameters.** Four fixed figures that no tab shows (1082: the tap
  windows again; 2972: 7777; 3900 / 3905: 100/30, 101/30).

### The regions' spec sets (2 Oct) — what loads

The user sent every region's spec sets (seven OneDrive zips, ~950 files: 20
markets and areas, each with dated versions and old specs). 185 sets, 168
different by content: 164 complete, 4 missing files. Every complete set
loads, and opens AL004 and SN001 through the app (screen, powering, Test
list) without an error. By what the readers make of them:

| sets | what |
|---|---|
| 135 | every value read (names, losses, levels, steps, tap IDs, frequencies all sensible) |
| 11 | the same, but the Parameters name the frequencies `high`, `low`, `Rh`, `Rl` instead of MHz (all in old-spec folders): Lode heads the columns with those names (LK002 on LKMac862, the user's screenshot), and so does the app; it takes 750 / 54 / 42 / 5 inside, which only keeps the columns apart |
| 11 | the same, but the actives file fills EQs Banks 9–16 (3.4d; New Bern's `2&4 PORT` and `8 PORT` banks, the user's recording): New Bern's 1 GHz set (all six dates) and its old 750, and one each of Tyler, Bullhead, Narrows and a Beverly-Elkins "don't use" set |
| 7 | old formats not yet readable, all in old-spec folders: actives 2.20, 3.0 and 5.0 (Bossier's bymac862, Bullhead's npg550 / npg750 / npg860, Georgetown's gefd862 / jarr625, Beckley Stephenson's steph870), with their cables and couplers 2.10 and Parameters 2.10 of 2162 bytes where present |

Every current set (89, outside the old-spec and "don't use" folders) loads
with every value read; 8 of them hold the unread table. Versions met that
share a checked layout are listed in `tools/spec_coverage.py`
(`SAME_LAYOUT`): Parameters of 3095, 3106, 5186 and 5190 bytes are the
3102-byte layout with fields added at the end; taps 10.0 are the older rows,
256 of them; the rest are new version numbers on the same sizes.

**More than one extra frequency.** 86 sets have F3 on (the 1 GHz specs: 1002
102 862 / 85 5, or 750, 550 …), and 14 — Bullhead's and Eureka's current 1
GHz specs — F4 as well (1002 102 550 860 or 870 / 85 5). F4 sits next to F3
everywhere: an active's In at +175 and Out at +199 (Bullhead's FM332 In 12.2
/ 12.9, Out 45 / 50 at 550 / 860), slot 3 of the cable, coupler and tap
blocks (its .500 cable 1.82 at 550, 2.34 at 860), Min F4 beside Min F3 in
the extra levels (14 / 17). The current record's In / Out at F3 (+171 /
+195) is borne out on all the 1 GHz specs (In 15.3 / 12.9 / 10.3 and Out 52
/ 50 / 38 at 1002 / 862 / 102 on their LEs). The app draws one extra
column (F3) only: an F4 column and its tap tests are not built.

**Now drawn (2 Oct, the user's screenshots).** Every extra forward frequency
the Parameters have on gets its column after the two cplr[branch] columns,
in F order, headed with its label, carried through cables, couplers, taps,
in-line devices and actives at its own slot, its tap ports tested against
its Min and tap window: BH1GHzMid keyed in Lode (1.1 amp 71, three 99
couplers, 190 ft /26/, 189 ft <21>, amp 11) reads 1002 102 85 5 … 550 860,
and every one of its 64 figures is the app's; HUMB1GHzMid (550 870) the
same (`tests/test_keyed_regions.py`). **Column heads are the Parameters'
labels**, whatever they say: LK002 on LKMac862 is headed `high low Rh Rl`.

### 3.0 Older spec files (WVEXT862, Lode 4)

WVEXT862 was saved by an older program: format versions `.cbl`/`.cpr` 5.1,
`.atv` 6.0, `.tap` 3.0, `.par` 2.10 (its header's text reads "Design 4.22"),
against 11.1/12.1 in the current files. Lode 12 opens it with the older AL004
design. The fields are the same; part names are 15 characters where the
current files have 25, so every field after a name moves up 10, and the
tables are smaller. A reader tells them apart by the version at byte 26
(below 11: older).

| file | older layout | current |
|---|---|---|
| `.cbl` | 512 + 384·n, 100 records, marker 0x33 (5·10 + 1); name char[15], then resistance +20, loss blocks +24/+64, parts +104/+119, Series/Colors +154 | 394-byte records, fields +30 … |
| `.cpr` | 616 + 104·n; name char[15]; loss blocks +20/+60, tap legs +100, internal +103 | 626 + 114·n |
| `.atv` actives | index i at 1021 + 318·i, 51 records (0 – 50); name char[15] at +5 (its last two characters are the current file's housing field), levels +39, Custom Cascading u32 +35, power steps +79 (six), In F3 +127, Out F3 +151, Configuration Table +170 | index i at 3021 + 362·i, 251 records (the banks start one byte after); levels +59, Custom Cascading u32 +55, power steps +99 (room for nine), In F3 +171, Out F3 +195 (WV750's bridger 41: 10.1 / 43.0, as WVEXT862's FNB99), table +214 |
| `.atv` banks | 4 banks from 17240, same 8816-byte bank and 68-byte row | 8 banks from 93884 |
| `.atv` 11.1 (SHINSTON, 262 136 bytes) | as the current 12.1 file up to the in-line devices; the 11 064 bytes it lacks are past them, where nothing is read | 273 200 bytes |
| `.atv` in-line | 25 records of 59 bytes from 57464, name char[15], losses +19 (F1 F2 R1 R2 F3 …) | 40 of 69 from 169372, +29 |
| `.tap` | 63 rows of 414 bytes from 641; part slots of 102 at +5/+107/+209/+311, part char[15], loss blocks +15/+55 | 512 rows of 454, slots of 112 |
| `.par` | 3102 bytes, below | 6515/6516 |

The older `.par` holds the current fields at fixed shifts: 512 – 577 as is
(tap type by ports, ports by homes); miscellaneous parts char[15] from 578;
housings char[15] from 668; strand types, points and housing sizes at −190
(863 …; room for 9 sizes); the tap windows, NIU, crossovers, cascades,
levels, interpolation, max amps and EQ placement at −200 (levels at 954);
15 power supplies, names char[15] from 1357 and the table from 1602; the
extra levels, frequency table, EQ selection and the tap-window, tap-cascade
and over-equalization flags at −810 (frequencies at 2982). It ends there:
no 600 – 900 series, transformers, tilts, count types or pre-load. Read
this way WVEXT862 gives 870 54 550 / 40 5, levels 0 – 1 of 19/10/45/45 and
22/13/45/45, TV-60 … TV-1024 at 4 6 11 17 27, supplies NEW STANDBY,
EXISTING STDBY, EXISTING 90v, and WIFI OMNI (86, index 38) in 0 −5 22 22,
out 48.5 34 47 47 — what Lode draws on the older AL004's branch fed from
11.18.

**The third forward frequency (F3).** WVEXT862 has F3 = 550 on (Min F3 15 /
18 on levels 0 / 1 at 2976 + 24·lv, window 12). Lode then draws a 550
column after the two cplr[branch] columns — the level at the line's input,
and on the line under a branch what continues past the last tap — while
the tap box and the port levels under the tap columns keep 870 54 / 40 5.
It comes from slot 2 of the cable, coupler and tap blocks (3.1), from an
in-line device's fifth loss (3.4b) and from an older active's In at +127
(right after its six power steps) and Out at +151: in 14.1 on the LEs, 10.1
on the FNB99s, 0 on the nodes and WIFI OMNIs; out 43.0 on the LEs and
FNB99, 41.1 on the NC4000, 43.5 on HLN 3842 NODE, 0 on the WIFI OMNIs (43.1
and 44.1's end lines read 0.00). All 57 values on the older AL004's screenshots match
(branches 4, 6, 7, 11, 43, 44). The Test list checks the ports in the
Parameters' order — "Tap(550) 0.74 below min at 3.1." after 3.1's 54 —
min/max, then windows ("Tap(550) 1.77 over window at 14.1."), then the
crossover.

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
| 164 + 23·k | 10 × 23 bytes | **Series/Colors**, series k = 0–9: u32 Windows colour (0x00BBGGRR), 4 bytes always 0, char[15] the series' name |

**Series/Colors** (Spec Edit → Cables, third tab). A line's cable number on
the Design screen is series·100 + cable ID, and Lode draws it in the colour
this cable holds for that series; the line's box adds the series' name from
column 15 ("EX P3 625 U    Dual New Build"). Untouched slots are 0,255,0
with no name: all of WV750's, KERMIT's and WVBeck750's. SHINSTON sets
cables 0–39 to 0,200,0 on series 0–5 (SN001's 15.29 "10", by its 140 and 40
at 0,255,0, the user's SHINSTON2 1b). WVEXT862 (older record, slots at
+154) names series 0 New Build, 1 Dual Cable, 2 Rebuild, 3 Overlash,
4 Upgrade, 5 Dual New Build on every cable, colours cables 0–19 red
(255,0,0) on 0, 2, 3, 5 and 0,200,0 on 1, 4, and cables 20–39 0,200,0 but
red on 4: so the older AL004's 505, 515 and 438 are red and 404–415 green,
every number on the user's set A2 screenshots. Measured on those: the
levels are 0,191,0, the cable numbers exactly their stored colour, and with
the cursor on ftg, hc, cab or lv all four are lit, the cable cell in its
colour with black text.

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

**A record with an ID and no part number is a coupler.** HUMB1GHzMid's
record 10 is ID 92 with no name (every loss 0 but the tap leg's 99 at
1002, the internal flag set): the user keyed 92 at 1.2–1.4 and Lode drew
`92<2>` … in green, the levels going on through it unchanged. LKMac1GHz,
GEFD1GHz and others hold such records too (99 at F1 and F2). What the
branch behind one starts at is not seen yet (QUESTIONS 4).

### 3.3 `.atv` — actives: amplifiers, line extenders, nodes (362 bytes)

| offset | type | field |
|---|---|---|
| 1–4 | u8 ×4 | the Pads/EQs Banks less one: forward EQ, return EQ, forward pad, return pad (the Actives tab's Fwd Pad / Ret Pad / Fwd EQ / Ret EQ) |
| 5 | char[25] | **Part Number**, e.g. `BLE-7-750PSS`, `BTN NODE-12`, `FM902B` |
| 30 | char[25] | **Ret. Mod. Part Number** (Reserve Gain tab): Buckhannon's item 42 `RA-KIT-40L`, KERMIT's `RA-KIT\40`; NUL-ended, what follows the NUL is left from an older entry (an earlier reading split it into two "option parts") |
| 55 | u32 | **Custom Cascading** (below) |
| 59 | i32[4] | **In** — level required at F1, F2, R1, R2 (the Actives tab's `In - 1002 … In - 5`) |
| 75 | i32[4] | **Out** — level produced at the same four |
| 91, 95 | i32 | **Fwd Reserve Gain**, **Ret Reserve Gain** (BH1GHzMid's FM332s 2.00 forward; 0 elsewhere) |
| 99 | i32[2]×8 | **Power Steps**: "Min. Voltage", "Amperage 1" … "Voltage 8", "Amperage 8" — eight, as the tab has them (NBERN1GHz's FM332 45 V 0.73 A … 90 V 0.32 A) |
| 171 | i32[4] | **In** at F3, F4, F5, F6 (`In - 750` 13.90 on NBERN1GHz's FM332; BH1GHzMid's 12.2 / 12.9 at 550 / 860) |
| 195 | i32[4] | **Out** at F3–F6 (BH1GHzMid's FM332 45.0 / 50.0: the screenshot's 550 and 860 at 1.2–1.4; WV750's WIFI units 44.5 at F5) |
| 214 | 8 × 18 | **Configuration Table**: the Active ID 5 bytes into each slot, **Plugin 1** at +10 (the Plug-Ins row: WV750's `68N` 8 NEW FMB … `68B` 16 SWAP FMT TO FMB) |

The older record: name char[15], Ret. Mod. Part Number char[15] at +20,
Custom Cascading +35, levels +39, six power steps +79, In F3–F6 +127, Out
F3–F6 +151, the Configuration Table +170.

Every one of the 250 records is a row of the Actives window, named or not:
NBERN1GHz's 11H–33H, 62 and 64–70 have an Active ID and no part number, and
the recording shows them so (`tests/test_spec_windows.py`).

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

**Custom Cascading** (the Actives window's tab, one row per active): a u32
at +55 (+35 in the older record), the four bytes before the levels. Bit 0
is **Cust. Casc.** (1 Yes, 0 No), bit 1 **Exclude** (1 Exclude, 0 Include),
bit k + 1 **Casc. k** (1 Valid), k = 1–19. KERMIT's actives Valid at 1–14
hold Casc. 15 as well (bit 16, the third byte); no file sets 16–19. Every row of
WVEXT862's and WVBeck750's tabs reads so (the user's set A2). WV750: the
LEs `11` 0x3FFD (Yes, Include, Casc. 1–12), `22` 0x7FF9 (2–13), `33`
0xFFF1 (3–14); `Ripple` 0x0007 (Yes, Exclude, Casc. 1); NC4000 0 (No);
FM901e-B 0x7FFC (No, yet Casc. 1–13). WVEXT862: `11` 0x007D (1–5), `22`
0x00F9 (2–6), `33` 0x01F1 (3–7), the FNB99 bridger 0x003D (1–4), HLN 3842
NODE 0x0005 (Yes, Include, Casc. 1), NC4000 0. WVBeck750: every LE and node
type Casc. 1–10, Ripple and FML332 Exclude. Cascade Position counts the
actives from the node down, itself included, but not those excluded — so
AL00416 reads 1 on AL004 (Ripple excluded) and 2 on the older AL004 (NC4000
included), Lode's boxes; an active with Cust. Casc. Yes at a position not
Valid is Lode's "LE  11/5 before/0 after at 23.17." (open-questions).

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

**A row with a Tap ID and no part for a port count is still that tap.**
HUMB1GHzMid's row 6 is Tap ID 21 with every slot empty; the user keyed 21
with 5 homes at 1.6 and Lode drew `<21>` in yellow, the levels going on
unchanged (1.7 = 1.6). Read as what the file holds — no part number, tap
value 0, insertion 0 — the port reads the line's level, 12.57 dB over its
10 dB window at 1002, which is yellow; having no part it is not a
terminating tap. The port count comes from the Parameters' Tap Selection
(homes → ports → tap type: 5 homes → 8-port in all three specs), as the
user's hc 2 `/26/` and hc 5 `<21>` show.

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
`{n}`. The Design screen's tap column is four characters wide, so a 3-digit
tap loses its opening bracket: SN001's `117]` and `111]` (5.11, 5.12, 18.12,
28.11); the preview box, five wide, draws it whole, `[114]`.

**The preview box** (a coupler's info box), measured on SN001's 1.2, 15.10,
18.9, 24.7 and 28.9: the branch's first ten lines (the line under the last
node counts as one), each field a fixed width — node 4, each level 7, ftg 5,
hc 4, cab 4, lv 3, two spaces and the active left-aligned in 3, each tap 5,
each coupler 12. `Start` and `Levels` are padded to 7. The levels are printed
as computed, not as the Design screen rounds them (2.5's 32.055 is 32.05
here, 32.06 on the screen); hc and lv print 0; every branch is `[n]`
(the screen's `108<19>` is `108[19]`); an in-line device is not shown (20.9's
EQ).

WV750's six tap families (Tap IDs): MGT 4–24, LEQ\RC pads 30–45 (6-port slot),
AN-WIFI 104–124, RMT1 204–235, RMT2 404–426.

### 3.4b `.atv` in-line devices (Q1, Q2 …)

The Actives window's Inline EQs tab: 24 rows, `EQ` then Q2–Q24 (the user's
recording of NBERN1GHz) — 69-byte records from offset 169372, record n = Qn,
n = 1–24 (what follows the 24th is another table). Name, then at +29 ten
losses in the order the tab heads them: F1, F2, R1, R2, F3, F4, F5, F6, R3,
R4 (NBERN1GHz's EQ FFE-8-85/RP+8P 1.60 8.90 9.70 9.00 2.90; the older
AL004's LEQ-PEA-8: 3.1 at 550 on 6.9 and 7.6, as Lode's screens). WV750: Q1 LEQ-PEA-8,
Q2 LEQ-PEA-0 (1.2 / 1.0 / 1.2 / 0.7), Q3 FFE-8-120-85/RP-R, Q5 EXIST SPLICE,
Q6 NEW SPLICE, Q10–Q13 REMOVE/MOVE LE/BR markers. Placed in the amp column the
device's loss applies before the node's taps; on AL004 6.8 that gives exactly
the screen's 30.73 / 32.31 / 39.23 / 36.85 on 6.9.

The amp column shows Q1 as `EQ`: SN001's 5.12, 8.7 and 15.26 (Q1,
FFE-8-120-85/RP) read EQ while 5.5 reads Q8, 5.6 Q6 and AL004's 6.8 Q2. The
manual's amp column holds "in-line equalisers and Q numbers"; both spec sets
keep an equaliser in record 1. Nothing in the device record or the line
record marks it otherwise.

### 3.4d The rest of the actives file (the recording's other tabs)

| offset | what |
|---|---|
| 93884 | Pads/EQs Banks 1–8 (3.4c) |
| 164412 | **Plug-Ins**: 32 records of 155 bytes, the **Plugin Module Part #** char[15] at +140; record 0 is "no plug-in". WV750: 4 SWAP BR TO LE, 5 NEW LE, 6 UPGRADE LE, 7 MOVE LE, 8 NEW FMB … 17 SWAP FMB TO FMT — exactly the plug-ins its Configuration Table's variants name (68N–68B on the FM902B, 69N–69T on the FM902T, 78N–78S on the FML332). The Atten. columns, AGC/Step Down and the Plug-Ins Powering steps: where in the 140 bytes is not known (zero in every file) |
| 169372 | Inline EQs, 25 × 69 (3.4b) |
| 171097 | 9 records of 103 bytes, records 1–8 the **Feedermakers** rows (BH1GHzMid and HUMB1GHzMid hold −1 at +51 of each; nothing else in any file) |
| 172024 | **EQs Bank 9 – 16**: 8 banks of 128 rows of 88 bytes — the bank's **Prefix** char[11] (repeated on every row: NBERN1GHz's 9 `2&4 PORT`, 10 `8 PORT`), the **Part Number** from +11, ten losses at +48 in the loss block's order F1–F6, R1–R4 (`CS12` 14.30 0.40 9.50 … 0.30 0.10). Ends at 262136, the 11.1 file's end |
| 262136 | the 12.1 file only: 24 × 461 bytes, **Boosters** B1–B24 (empty in every file) |

The Bridgers tab (BR1, BR2) is not placed (empty in every file).

### 3.4c `.atv` Pads/EQs Banks 1–8

The Actives window's Pads/EQs Bank tabs. Bank k starts at
93884 + 8816·(k − 1): 129 rows of 68 bytes, then four part-number prefixes,
char[11] each — forward pad, return pad, forward EQ, return EQ.

| offset in row | type | field |
|---|---|---|
| 0 | char[5] | forward pad label, right-aligned as stored (`"   8"`) |
| 5 | char[5] | return pad label |
| 10 | i32[12] ×1e6 | the bank tabs' numbers: forward pad dB Loss; forward EQ Loss at 750, 54, 550, F4, F5, F6; return pad dB Loss; return EQ Loss at 40, 5, R3, R4 |
| 58 | char[5] | forward EQ label |
| 63 | char[5] | return EQ label |

Row 0 is `VOID`; a column ends at its row labelled `FLAG` (`Flag` in the
1 GHz specs), and that row is a choice like the others: its pad is 21 dB,
one past the largest, and Lode picks it when no pad is large enough —
"Forward Pad: Flag", "Return Pad: Flag" on 1.7 of the user's BH1GHzMid and
HUMB1GHzMid screenshots; a stored value that points at it shows `FLAG`
(AL003's 52.7 return pad 21, which the app showed as "21"). A design stores
row − 1 in the node's pad bytes (network 112–123), so AL00416's forward EQ 16
is row 17, `"  12"` — what its info box shows. The expanded display names the
part as prefix + label: WV750 bank 1 is `SPB-`, `SPB-`, `SEQ-750-`,
`MEQ-42-`, so 4.24 reads `SPB-7`, `SEQ-750-0`, `SPB-2`, `MEQ-42-2`. Checked on
all six amplifiers whose pads the screens show.

Each active names its banks in the four bytes before its name, less one:
+1 forward EQ, +2 return EQ, +3 forward pad, +4 return pad (FM901e-B: pads
2 2, EQs 1 1 on the Actives tab, stored 0 0 1 1; setting BRIDGER 61's Ret Pad
to 2 changed +4 alone). Every WV750 active reads back as its Actives tab
row. The EQ pair is taken to run forward then return like the pads.

**How the program picks them** — reproduces all 27 LEs and bridgers of
AL004, 108 stored values:

* EQ: the row whose tilt is nearest the one needed. Forward, tilt is Loss-54
  − Loss-750 (an `SCS` cable simulator's is negative) and the need is the
  active's In-750 − In-54 less the input's 750 − 54. Return, tilt is Loss-5
  − Loss-40 and the need is the level needed here at 40 less at 5.
* Pad: the largest that still leaves, after it and the EQ's loss, the input
  at or above In-750 and In-54 (forward), or the active's Out-40 and Out-5
  at or above the levels needed here (return).
* **With "Allow Over Equalization" unticked** (General Parameters; BH1GHzMid
  and HUMB1GHzMid, not WV750) the forward EQ is the nearest of those that
  leave no more tilt than the active's own In tilt. BH1GHzMid's FM332 at
  1.7: 39.67 / 33.70 in, In 15.3 / 10.3 — CS1 would leave 5.18 against 5.00,
  so Lode shows CS2 (4.48); HUMB1GHzMid's (39.57 / 33.90, In 14.3 / 9.3)
  CS1. Applied always, the rule would change 16 of AL004's 27 — so it is the
  setting. The return EQ: no case yet where the two would differ.

A spec saved from the editor after the Design screen has shown a pad or EQ
writes that label trimmed (`"  16"` → `"16"`) — on AL004, exactly 34.6's
four, the ones that first showed with their spaces (`SPB-  16`) and trimmed
after reopening — evidently the program trims a label in its own memory
once it has used it. The replica always shows them trimmed.

WV750's banks: 1 the LEs and bridgers (`SPB-`/`SEQ-750-`/`MEQ-42-`), 2 the
FM901e and FML1G7J pads (`NPB-`), 3 the WiFi units, 4 the nodes (`NODE-`),
5 the FM902s and FML332 (`NPB-`/`CE-120-`/`MEQ-85-`).

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
| 1053 | u8 Strand/Trench Types 000–500, bit n = series n00 ticked | 0x1D = 000 200 300 400 | proven (600–900 are bytes at 3912–3915) |
| 1056 | u8 points, Equalizer | 5 | proven (test copy: 9) |
| 1057 | u8 points, Amplifier | 16 (KERMIT 36) | proven |
| 1058 | u8 points, Line Extender | 11 | proven |
| 1059, 1060, 1061 | u8 points, 2/4/6 Port Tap, 8 Port Tap, Coupler | 5 5 5 | proven (test copy: 6 7 8) |
| 1062 | u8 points, Power Supply | 30 | proven |
| 1063 + k | u8 housing k+1 Minimum Size (Points) | 4 6 11 17 27 | proven |
| 1082 | ×4: 12, 16, 16, 16 | same in KERMIT | unknown — equals the four design tap windows |
| 1098 + 4·k | NIU: System Penetration %, Offhook %, Ring %, Additional Line %, Offhook Limit | 0 ×5 (KERMIT 47 53 51 54 0) | proven (test copy: 1 2 3 4 5). Whole numbers: 1.11 typed comes back as 1.0 |
| 1118 | Max. Crossover (0.00 is a limit: WVEXT862 holds it and Lode lists every positive crossover) | 3.00 | proven (test copy: 3.25) |
| 1122 | Max Return Crossover | 99.00 | proven |
| 1126 | Max. LE Cascade | 3 (KERMIT 2) | proven (test copy: 4) |
| 1130 | Lines per Form | 0 (KERMIT 45) | proven (test copy: 44) |
| 1134 | Tap Margin | 0.50 | proven |
| 1138 | Signal Display, 0 dBmV / 1 dBuV | 0 | proven (save chain s2) |
| 1142 | Distance Units, 0 Ftg / 1 m / 2 dM | 0 | proven (chains s1, v1) |
| 1146 | Replacement Cables, Backfeed | 0 | proven (test copy: 7) |
| 1154 + 20·lv | System Levels lv 0–15: Min 750, Min 54, Max 40, Max 5, then one more (0) | 17 10 45 45 / 19 12 45 45 | proven (5th unknown) |
| 1470 | Replacement Cables, Fwd. Feed | 0 | proven (test copy: 9) |
| 1474 | u8 Power Interpolation, 0 Step / 1 Linear / 2 Constant Wattage | 2 (KERMIT 0) | proven (test copy: 1) |
| 1478 | u8 Overvoltage Check, 1 = On | 0 (KERMIT 1) | proven (test copy: 1; Pre Load left Off) |
| 1482 | Optimization, 0 OP- / 1 OFf / 2 OP+ | 0 | proven (chains s6, v1) |
| 1486 + 4·k | Maximum Amperage Through: Power Inserter, Amplifier, Bridger Port, Coupler, Line Extender, Tap | 16 15 15 15 15 12 | proven (test copy: 16 15.1 15.2 15.3 15.4 12) |
| 1510 | Default EQ Placement, 0 EQ- / 1 EQ+ / 2 EQe | 1 (KERMIT 1) | proven (chains s5, v1) |
| 1567 + 25·k | power supply ID k+1 part number, 25 slots | EXISTING STDBY … | proven |
| 2212 + 20·k | power supply ID k+1: Voltage Rating, Current Rating, % Capacity | 60/15/85, 60/15/90, 90/15/90, 90/15/85 | proven |
| 2972 | i32 raw 7777 | same in KERMIT | unknown (a marker?) |
| 2976 + 24·lv | per level: Min F3 (550), Min F4, Min F5, Min F6, Max R3, Max R4 | 15 / 17, rest 0 | proven (v7 level 0: 1.25 2.25 3.35 4.25 5.25) |
| 3792 + 10·k | frequency k (F1–F6, R1–R4): char[5] label, u8 enabled, i32 tap window | 750 54 550* F4* F5* F6* 40 5 R3* R4* (*off); windows 12 16 · 16 16 | proven |
| 3892 + 2·k | u16 Freqs. for Active EQ Selection: Fwd High, Fwd Low (index into F1–F6), Ret High, Ret Low (index into R1–R4) | 0 1 0 1 = 750 54 40 5 | proven (v8, v9 swapped each pair) |
| 3900, 3905 | u8 pairs 100/30, 101/30 | same in KERMIT and the test copy | unknown — not the replacement cables |
| 3904 | u8 Enforce Tap Window | 0 | proven (save chain s7) |
| 3909 | u8 Max. Tap Cascade | 0 | proven (test copy: 6) |
| 3911 | u8 Allow Over Equalization | 1 (KERMIT 0) | proven (test copy: unticked → 0) |
| 3912–3915 | u8 Strand/Trench Types 600, 700, 800, 900 Series | 0 0 0 0 | proven (chains s4, v2–v4) |
| 3915 + 260·k | Transformer k+1, 8 records of 260 bytes: char[256] part number, then i32 ×1e6 voltage (at 4171, 4431, 4691 …) | blank | proven (v7, v10: FMR-T1 60.5, ABC-2 70.25, DEF-3 80.75) |
| 6000 | u8 Enforce Tap Tilt | 0 | proven (chain v5) |
| 6001 | u8 Flag Hi/Lo Tilt | 0 | proven (save chain s8) |
| 6002 + 16·lv | System Levels Max Tilt Fwd, Min Tilt Fwd, Max Tilt Ret, Min Tilt Ret | 0 | proven (test copy level 0: 1.10 2.20 3.30 4.40) |
| 6514 | u8 Show Count Types | 0 | proven (save chain s3) |
| 6515 | u8 Pre Load/Test Attached Networks — only in the 6516-byte files version 12 writes | absent | proven (chain v6) |

The user's test copy (WV750-2026.par re-saved with a distinct value in every
field, `samples/partest/paratest.par`) placed most of the rest. Re-saving
also writes the header as format 12.1, blanks the licence and user ids, and
adds one byte at the end (6516 bytes).

A chain of eight saves, each undoing one setting of the test copy
(`samples/partest/s1.par` … `s8.par`), placed the eight radio and checkbox
fields that had all saved as 1. Saving also stamps the saver's licence and
user ids into the header.

A second chain from s8 (`v1.par` … `v9.par`) placed everything else on the
six tabs. Every setting on them is now located.

**Transformer 1's first letter is lost.** Its part number starts on byte
3915, which is also the 900 Series flag, so saving overwrites the letter
with 0 or 1: typed `XFMR-T1`, the file holds `\x01FMR-T1` (900 ticked). The
reader takes slot 1's name from 3916. After a name the rest of the field can
hold leftovers (` 60.5`), so names end at the first NUL. The first time the
user typed transformers 2 and 3 only their voltages were saved; typed again
(v10) the names were saved too.

Bytes that no tab shows and that no setting tried has changed, the same in
every file: 1054–1055 (32, 32); 1082 (12, 16, 16, 16 — equal to the four
design tap windows); the fifth value of each System Levels record at
1154 + 20·lv + 16 (0); 2972 (raw 7777);
3900 and 3905 (100/30, 101/30).

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

### 3.8 `.ntw` — everything a writer needs

`tools/lodedata/writer.py` writes a design back over the file it came from.
AL004 goes through it and comes back byte for byte, both from its own records
and from the app's design model (`tests/test_ntw_writer.py`). Offsets below are
from the start of the file, header included.

**The whole file** is the header, a 44 295-byte preamble, then the branches
to the end of the file. There is no trailer, checksum or length field.

**Ids.** Every node, every branch's end line and every active or supply has
a u32 id from one counter that counts down from 127 999. AL004 uses 127 649
– 127 999. The next free id is at 41409 (127 648), and 41413 holds 127 999.
Ids of deleted nodes are not reused. A node links to its neighbours by id:
+4 the previous node, or the branch number on a branch's first node; +8 the
next node, or the end line's id on the last.

**Branch head** (1966 bytes): laid out like a node record less its own id.
+0 is the id of the node carrying its coupler (0 on branch 1), +4 the first
node's id, +8 the u16 node count and +10 four empty tap slots. +126 is the
coupler record + 1 and +131 is 4 on the branch taking the through leg. Branch
numbers are the file order, 1…n; no number is stored.

**End** (48 bytes): 4 zero bytes, the end line's id, the last node's id, zeros.

**Node record**, beyond 3.7:

| offset | field |
|---|---|
| 14 + 21·k | tap slot: i32 row (−1 empty), u8 port code, then `ff ff 00` ×4 and 4 zeros on every slot |
| 108 | u8 1 on a node carrying an in-line device Qn |
| 111 | u8 the active's Configuration Table slot: 0 the base ID (every active of AL002 – AL005), 2 on SN001's, which Lode shows as `63U` / `11U` (FM902B: 63 63N 63U 63M …), 3 on its 5.8 (`11M`) |
| 112 + 3·k | (flag, value, 0): the pads/EQs. A node whose amplifier was taken away keeps them (9.20 holds 9.21's) |
| 137 | u32 id of the active or supply placed here; 0 once it is taken away |
| 698 | the line's Notes, C-style — see below |
| 718 | u32 the node's own id, in an extended record |
| 726 | char[16] power supply label, NUL-terminated; the rest is left (18.1: `A\0004A`, once `AL004A`) |
| 981 | char[16] amplifier name, the same way |
| 1706 | u8 the house count again |
| 1714 | 32 × u32: all 4 on every record that holds or has held an active |
| 1842 | 32 × u32: 1 for each home, then 4 — on the lines where it is filled in (125 of 275), all 0 on the rest. It is not rewritten when the house count goes to 0: SN001_MID's 8.3 holds 0 homes over 1 1 1 |

An extended record (2504 bytes) is the same record with 534 zero bytes put in
at +1706: the three tail fields move to 2240, 2248 and 2376. Taking the
active away takes the block out again.

**The line's Notes.** At +698 every line holds a C string: its Notes (Lode's
`..+ Notes`). Lode marks a line that has them with a yellow ♪ after the cable
(SN001's 1.1, the user's screenshot). It is empty (one NUL) in every design
but SN001_MID, whose 1.1 holds 63 characters:
`SHIN1 - 4953 - P-003938~0POWERED BY PS "PS1A"~0DATE :02/20/26~0`. The record
grows by the text's length and every field after it moves with it: 1.1's
extended flag is at 764 and its own id at 781, and 1.2 starts 2504 + 63
bytes on. The offsets in these tables past 698 are those of an empty text.
Read without it, SN001 came out as one branch of garbage with 826 305 bytes
left over, which is why the app could not attach its spec set. After the
text come two zero bytes, then the flag (701 in an empty-text record): one
text and two fixed bytes, or three texts of which only the first was ever
filled — every file fits both. `~0` ends each row: Lode's Edit Notes window
shows 1.1's note as three rows (SHIN1 - 4953 - P-003938 / POWERED BY PS
"PS1A" / DATE :02/20/26). An edited note is written the same way, each row
followed by `~0`; a note left alone goes back as it was. Lode Data read the
app's notes (1.1 given a fourth row, a new note on 1.2) and its own save of
that file is the app's byte for byte, but for the header's licence fields,
the name it was saved under and its cursor (41425: on 1.2). Nothing else in the
record counts the note: the only bytes of 1.1 unlike every other extended
record are its ids, active, pads and two fields (137, 718 of an empty-text
record) that vary on every active and read 255 at 718 on every file's fibre
node, note or none. A branch head (a line's record less its
first 4 bytes) would hold the same field at +694; it is empty in every file.

The power supply label at 726 is the whole C string: SN001's supplies are
`1A`, `1B`, `1C`, and Lode shows `1A` in 1.1's amp box and 4.1's supply box.
On the Design screen the label sits in the first free cplr[branch] column,
cyan (4.1). The node box on a supply's line (4.1, no active) carries the
distances and homes and then the supply's own lines. So does the node box of
any line with the expanded display's block and no active: a coupler line
(1.2: all 0, 227 homes; AL004's 9.1), a branch's last line (28.16: 739 9856
739 739 9856, 2 homes) or its 0-ft first line; not 8.1 (334 ft, bare).

**A pad or EQ column with nothing in its bank** is blank in the amp box:
SN001's Ripple-2 on 1.1 (bank 4) shows Forward Pad and Return Pad empty, and
VOID for both EQs (stored 255).

**Preamble.** Parts are counted by where the part is. A part on an
underground node counts as underground: the node's cable file index is odd.
Rebuilt from nothing, these are the bytes Lode Data wrote:

| offset | holds |
|---|---|
| 512 + 261·k | the five spec file names (MAX_PATH slots) |
| 1817 | u32 feet aerial, underground (35 612, 1 354) |
| 1825 | u32 feet per cable: [100 cable file index][10 series] |
| 5825 | u32 homes aerial, underground; tap ports aerial, underground; homes again (162, 19, 300, 22, 162, 19) |
| 5869 + 4128·k + 4·(bank·129 + value) | (u16 aerial, u16 UG) actives by pad or EQ: k = 0 forward pad, 1 return pad, 2 forward EQ, 3 return EQ, each as the node holds it — (bank − 1, value, 0) at +112 + 3·k, value signed. AL004's Ripple, banks 4, holds (3, 0) four times; an LE, bank 1, (0, v) |
| 22377 + 4·i | (u16 aerial, u16 underground) actives of index i |
| 23381 + 4·n | the same for in-line device Qn |
| 23477 | u32 power stops (AL004: 2) |
| 23481, 23483 | u16 70 and 81 on AL004, 0 on an empty network — **not decoded** |
| 23513 + 16·row + 4·code | taps by tap-file row and port code |
| 31705 + 4·code | taps by port code |
| 31721 + 4·r | couplers by record + 1; a 3-way splitter feeding two branches counts once |
| 35723 + 4·i | u16 connectors on cable file index i: one at each end of a span (a line with footage) that meets a device — the location it runs from or to holds a tap, coupler, active, in-line device or supply, or it is a branch's start at its coupler (a branch whose first line is 0 ft still starts there) |
| 36121, 36125, 36129 | (u16 aerial, u16 UG) three counts — **not decoded** (AL004: 58/1, 0/1, 28/4; 0 on an empty network) |
| 36141 + 4·n | (u16 aerial, u16 UG) Underground Housing n, one per underground location: its equipment points (Parameters: amplifier or line extender, tap or 8-port tap, coupler — a splitter feeding two branches is one — equalizer for an in-line device, power supply) reach the housing's Minimum Size |
| 36201 + 4·k | (u16 aerial, u16 UG): 0 taps, 1 couplers, 2 splitters (both branches of a line off one coupler record), 3 in-line devices, 4 line extenders — actives table items 1 – 12, 5 all other actives, 12 always 1 (the empty network too), 56 + t supplies of type t |
| 41401 | u16 41, u8 1, u8 1, u32 branch count, the id counter |
| 41425 | u32 branch, u32 line, u8 1: where the program's cursor was (AL005: 12, 25; else 1, 1) |
| 42366 + 261·k | the 8 files it was saved with: Parameters, Actives, Taps, Couplers, Cables, Prices, Performance, Map Grid (the program's "Spec File Mismatch" box lists them in this order) |
| 44542 | the file name it was saved as, without `.ntw`. Opening a file under another name, the program warns "Filename AL004 has changed to AL004_T2_insert. Setting all PCDs to open." |

The writer rewrites the decoded totals, the branch count and the id counter.
Everything not decoded is left as the file had it. Every total above is
rebuilt exactly from the network on AL002, AL005 and both AL004s; AL003's
pad/EQ tally holds 34 entries more than its actives, all at bank 4 value 0,
which no line of it accounts for.

**The empty network.** The program's File > New saved untouched (the user's
BLANK test) is 48 791 bytes: the header, a preamble all zero but the spec
names (Untitled, 5 + 8 times), the file name, 41401 – 41415 and 41425 as above,
and 36249 = 1; then branch 1 with one line (id 127 999, end 127 998, next free
127 997). That line's pads are (255, 255, 0) ×4 and its house list empty; lines
keyed later hold (0, 0, 0). `writer.blank()` rebuilds it byte for byte, and a
network keyed from scratch is written over it. The header is the same in
every file bar the licence and user fields.

**A network keyed from scratch** (the user's S1 – S3, keyed in Lode Data from
the empty network with WV750-2026). Written from `writer.blank()`, the app's
file is Lode Data's byte for byte but for 23483, 36129 and where the cursor
was (41425). What they showed:

* An active stays on the short record until it is named: S1's Ripple on 1.1
  has no name and no long record. Naming it (or placing a supply) takes the
  long record and an object id. AL002's 22 unnamed actives are the same.
* Ids: the network starts with 1.1 = 127 999 and its end line 127 998; lines
  keyed after take the next ids, and a branch placed later takes its end
  line's first (S3: 1.2 127 997, 1.3 127 996, branch 2's end 127 995, 2.1
  127 994).
* A branch placed later has a keyed line's head: pads (0, 0, 0).
* Set All Files writes the set's name into all eight saved-with slots;
  Prices, Performance and Map Grid then keep Untitled over it, leaving the
  name's tail: `Untitled\0` then `6` of WV750-2026.
* 23483 counts 1, 2, 3 over S1 – S3 (one per tap keyed) and 23481 stays 0;
  36129 is the taps ending a branch there (1, 1, 2), as on both AL004s
  (28/4, 27/4) — but on AL002, AL003, AL005 and SN001 (25/0 against 42/1
  such taps, 19 of them terminating) neither rule holds, so both stay as
  the file has them.

**Actives on the short record.** AL002 holds 22 of its 39 actives on 1970-byte
records with no name and no object id. Both kinds are kept as they are.

**A coupler taken off, its branch kept.** Typing 0 on a coupler whose branch
has lines on it takes the coupler off and leaves the branch, drawn `- [55]`
and fed by nothing: it starts at 0.00 (the user's recording, AL002 55.1:
112 ft of cable 0 reads −2.42 −0.60 0.52 0.18). How the program saves one is
not seen yet; this writer keeps it as below.

**A branch fed from a tap's port.** The older AL004's branches 43 and 44 have
coupler 0, are listed on no line, and their head's first field is the id of
the line they hang from, 11.16 and 11.18. Each of those lines has one tap,
and Lode draws it `117+` (AN-WIFI-417, 4-port) and `104+` (AN-WIFI-204,
2-port), its info box reading `Branch:`. The branch starts at the port's
level: 11.18's 24.24 21.71 32.98 32.22 less the tap value (4.2 3.3, return
plus 3.3 3.2), then 6 ft of cable 0, gives 44.1's 19.90 18.38 36.31 35.43,
Lode's screen to the hundredth. Nothing in the head or the tap slot says
which tap feeds it; with one tap on the line it is that one. The amp box
counts the line as a split: 44.1 is 6 ft from its previous act-split.
Lode numbers them as the file does: the tap boxes at 11.16 and 11.18 read
Branch: 43 and Branch: 44, and the Test list has 43.1 and 44.1.

**A pad or EQ of 255.** A design stores a bank row minus one, so 255 is row 0,
VOID in every bank seen: the WIFI OMNIs on 43.1 and 44.1 hold 255 for both
EQs and Lode's box shows Forward Eq VOID, Return Eq VOID.

**Fslope / Rslope.** An active whose Pads/EQs bank has no forward EQ gets
"Fslope too low to equalize at b.n." in the Test list (yellow), no return EQ
"Rslope …", the pair ahead of the line's tap checks: SN001's Ripple-2 on 1.1
(bank 4, empty) and the older AL004's WIFI OMNIs on 43.1 and 44.1 (bank 3,
forward pads only). AL004's Ripple (bank 4, a row in each column) has none.

**No spec set.** Opened with none, the program shows levels 0.00, the level
columns as high low Rh Rl, every coupler's ID as 0 (0<2> 0[3] …) and AL004's
Ripple, index 22, as 70 — its default Configuration Table gives index + 48,
which WV750 keeps for every active it did not rename (13 → 61 … 40 → 88).

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
