# Evidence index

Every file, screenshot and recording the user captured in Lode Data 12.11,
what each one proved, and where that is now pinned (tests, docs). The rules
themselves are written up in `file-formats.md` and `open-questions.md`; this
file says **where each rule came from**, so nothing has to be taken on trust
and nothing is lost between sessions.

The evidence itself is **never committed** (company designs; file headers
carry licence and user ids). It travels in two zips kept by the user and
uploaded again at the start of a new session:

| zip | unzip into | holds |
|---|---|---|
| `lodedata-samples.zip` | the repository root (makes `samples/…`) | every `.ntw`, spec set and test save — what the tests read |
| `lodedata-evidence.zip` | anywhere outside the repository, e.g. `~/evidence` | the screenshots below, named as in this index |

Screen recordings are too large to carry (50–150 MB each); the user keeps
them. What each one showed is written down below and in the docs.

Wording used here: **AL004** = `AL004.ntw` with WV750-2026 (current Lode 12
spec set); **older AL004** = the August `AL004.ntw` with WVEXT862 (Lode 4
spec files); **SN001** = `SN001_MID.ntw` with "SHINN1GHz Mid" (SHINSTON).

## 1. Files (in `lodedata-samples.zip`)

| file(s) in `samples/` | from the user | what it is / proved | pinned in |
|---|---|---|---|
| `AL004-WV750/AL004.ntw` + `WV750-2026.*` | 26 Sep (`aloo4_apec.zip`) | the reference design; byte-for-byte round trip; every screen check | `test_ntw.py`, `test_ntw_writer.py`, `test_ui.py` |
| `AL004-WVEXT862/AL004.ntw` + `WVEXT862.*` | Aug OneDrive zip / 28 Sep | older Lode 4 spec formats (file-formats 3.0); tap-fed branches 43/44; Max. Crossover 0.00 is a limit | `test_classic_specs.py` |
| `SN001-SHINSTON/SN001_MID.ntw` + `SHINN1GHz Mid.*` | 29 Sep (`SHINSTON.zip`) | Notes text at +698 moves the rest of the record; configuration IDs 63U/11U; supply labels 1A…; .atv 11.1 | `test_sn001.py` |
| `SN001-SHINSTON/SN001_NOTES_test.ntw` | 29 Sep (`SHINSTON3.zip`) | Lode's own save of the app's Notes: identical to the app's bytes but for the header licence fields, the name at 44542 and the cursor | `test_sn001.py::test_notes_are_written_as_lode_data_writes_them` |
| `partest/paratest.par` | 26 Sep | a distinct value in every Parameters field → most offsets | `test_ntw.py::test_a_test_copy_with_distinct_values_places_every_field` |
| `partest/s1.par` … `s8.par` | 26 Sep (`s.zip`) | save chain 1, one setting per save (Distance Units, Signal Display, Show Count Types, 800 Series, EQ Placement, Optimization, Enforce Tap Window, Flag Hi/Lo Tilt) | `…::test_each_save_in_the_chain_changes_one_setting` |
| `partest/v1.par` … `v9.par` | 26 Sep (`v.zip`) | save chain 2 (dM/EQ-/OP+, 600/700/900 Series, Enforce Tap Tilt, Pre Load, Min F4–F6 / Max R3–R4, transformers, Freqs. for Active EQ Selection) | `…::test_the_second_save_chain_places_the_rest` |
| `partest/v10.par` | 26 Sep | transformer names ABC-2 / DEF-3 saved; transformer 1's first letter is overwritten by the 900 Series byte | same test |
| `partest/act.atv` | 26 Sep | BRIDGER 61's Ret Pad bank set to 2 moved byte +4 alone → bank byte order | `test_ntw.py::test_the_return_pad_bank_is_the_fifth_byte` |
| `KERMIT750/KERMIT750-2026.*` | Aug OneDrive zip | second current-format spec set (Parameters offsets checked against it; keying tests' tap codes) | `test_import.py`, `test_entry.py`, `test_ui.py` |
| `designs/AL002.ntw`, `AL003.ntw`, `AL005.ntw` | Aug OneDrive zip | older designs: short-record actives (AL002), preamble tallies, the every-file × every-spec check | `test_ntw_writer.py` (totals), regression check |
| `keyed/BLANK_test.ntw` | 28 Sep | Lode's empty network; the app rebuilds it byte for byte; networks keyed from scratch are written over it | `test_ntw_writer.py::test_an_empty_network_is_the_programs_own_empty_file` |
| `keyed/S1.ntw`, `S2.ntw`, `S3.ntw` | 28 Sep (`S.zip`) | from BLANK: amp 70 + a tapped line; a second line; a coupler and branch 2 → id order, short record for an unnamed active, branch-head layout, 23483 counts taps | `test_ntw_writer.py::test_a_new_network_is_laid_out_as_the_program_lays_one_out` |
| `app-saved/NEW_T1.ntw` | written by the app, 28 Sep | the recording-2 network keyed from scratch, licence and user fields blank: Lode opened it (only the "which spec set" message) | `test_ntw_writer.py::test_a_network_keyed_from_scratch_is_written_as_a_new_network` |
| `app-saved/SN001_NOTES.ntw`, `AL004_NOTES.ntw` | written by the app, 29 Sep | Notes test files: SN001's was opened and re-saved by Lode (= `SN001_NOTES_test.ntw`); AL004's is still to be opened (QUESTIONS 38) | `test_sn001.py` |
| `bullhead/H043A_MID.ntw`, `H043B_MID.ntw` (+ `regions/BH1GHzMid/`) | 3 Oct (`wxext862-4.zip`) | Bullhead networks on BH1GHzMid joined by a PCD (they share a supply). Every one of their 48 actives holds the pads / EQs the pick gives at the app's levels once couplers are read with sign and zeros (FMT Split -9 forward, 0 return) and the return EQ honours "Allow Over Equalization"; H043B's Test list = Lode's (2a); the PCD's network table before branch 1 and coupler record 999; saved back byte for byte but the underground housings' tally | `test_bullhead.py` |
| `AL005-Beckley750/Beckley750.*` | 3 Oct (`4_2.zip`, `23/`) | AL005's own spec set (older layout, Parameters 7.0 not yet checked against Lode): AL005 opens with every part resolved; its 22 actives' stored pads / EQs are the pick at the app's levels. The `23/WVEXT862` sent with it is byte for byte the pack's | `test_spec_sets.py` (xfail: Parameters 7.0 unchecked) |

**Not in the pack (ask the user again if needed):**
* **The regions' spec sets** (2 Oct, `OneDrive_2026-10-02_7.zip`, 104 MB,
  seven zips inside, ~950 files, 168 different sets from 20 markets and
  areas) — what loads: file-formats "The regions' spec sets". Read in the
  session's scratchpad only; not put in `samples/` (the user's files, large).
* **WVBeck750** spec set (`.par .atv .tap .cpr .cbl`) — 34 tests in
  `test_import.py` / `test_entry.py` need it together with KERMIT750 and skip
  without it (QUESTIONS 22). The user uploaded it as `WVBeck750.zip` on
  29 Sep: on a scratch copy all 34 pass and the regression check keeps its
  70 and adds 14; not put in `samples/` until the user says so.
* `BH_TEST.ntw` (3 Oct, sent for the BH network): the same size and number
  of branches as H043B_MID — not used; asked what it is (QUESTIONS N8).
* `TEST_OL.atv` (3 Oct): BH1GHzMid.atv saved after setting row 1's Out/Loss
  beside Out - 1002 to Loss: one data byte differs, 518 (0 -> 1); Lode also
  wrote it as version 12.1 with 24 records of 461 bytes added at the end.
  Kept with the evidence.
* The vendor manual (22 PDFs, 234 pages, sent in the first sessions) — its
  content is in `lode-data-manual-notes.md`.

## 2. Screenshots pasted into the chat (`lodedata-evidence.zip` → `chat-screenshots/`)

Named by the time they were sent (UTC). Earlier screenshots (first sessions,
before 26 Sep 08:26: AL004 branches 3, 4, 9, 11, 18, 19, 21, 22, the branch 4
Power screen, the menus) are not in the pack; their numbers are pinned in
`test_ntw.py`.

| file | shows | proved |
|---|---|---|
| `2026-09-26T0826_01.png` | AL004 branch 1, Design | `570<2> 570[3] 570[4] 570[5]`: the bracket is not stored in the file; branch 3 breaks the "1xx = not mileage" rule |
| `2026-09-26T1006_01.png`, `_02.png` | branches 11 and 4 after 11.1's footage 105 → 106 (not saved) | 4.14 turns `3-[11]<12>`: `<n>` needs the first span to equal the parent's span; 8-port tap `<15>` on screen, `{15}` in the preview |
| `2026-09-26T1026_01.png`, `_02.png` | branch 6 (`100[7]`) and the user's design drawing of the bridger's internal DC-12 | the span match looks at the coupler's own branch only; node box = address + cable (+ distances on an amp's line); cable 0 is a real cable; screen colours measured |
| `2026-09-26T1148_01.png`, `_02.png` | the test `.par`'s System Levels and Powering tabs before saving | checked the edit (tap margin had to be put back to 0.50) |
| `2026-09-26T1402_01.png`, `_02.png` | branch 6 with the 6.8 tap box, and with the Q2 box | the pad `<43>` is an in-line EQ + pad, "Inline EQ Type: LEQ-PEA-0"; red 46.73 at 6.9 |
| `2026-09-26T1615_01.png` | System Levels tab | where the return tap window is (for the Test experiment) |
| `2026-09-26T1619_01.png` | Test Results, rows 1–31, with return window 15.50 and Max. Crossover 3.50 | "Tap(5) 0.29 below window at 3.6"; Max. Crossover is the setting |
| `2026-09-26T1623_01.png` | Test Results rows 32–36 | all 36 lines match (`test_the_return_window_and_max_crossover_are_the_parameters`) |
| `2026-09-26T1635_01.png` | expanded display (`/`) at 4.24–4.26 | the cyan block: five distances + three 750 losses; `2-0-0 2-3-0 45 652` counts |
| `2026-09-26T1650_01.png` | branch 22 with `/` | the middle count is line extenders; "same cable" means the cable, not its code (385); amplifier lines `[AL00429]` / `< A>` |
| `2026-09-26T1726_01.png`, `_02.png`, `_03.png` | branch 34 (two screens) and branch 4 from the top, with `/` | levels round half up (21.115 → 21.12); homes print three wide with no gap (`127886`); only a 0-ft first line gets a block; white `(n)` = underground housing size |
| `2026-09-26T1741_01.webp`, `_02.webp` | Spec Edit → Actives tab with the Fwd Pad / Ret Pad / Fwd EQ / Ret EQ bank columns | those columns are bank numbers, stored less one before the active's name |
| `2026-09-26T1802_01.png` | 34.6's amp box after reopening | the untrimmed `SPB-  16` was session state; box = 16/4/14/2, cascade 4, supply B |
| `2026-09-26T1821_01.png` | Amplifier Definition window (`.` `+` on the amp column) | Power Supply, Amp ID, OK; Feedermaker Networks section left out at the user's request |
| `2026-09-26T1842_01.png` | "Amp Exists" box | duplicate names refused, any case; the window closes behind it |
| `2026-09-28T1108_01.png` | Lode's warning opening the app's first test files | "Filename AL004 has changed to …": the file keeps its own name at 44542; a save now writes it |
| `2026-09-28T1339_01.png` | 4.9 after `0 8` in the coupler column | the new branch is numbered after the highest (46); its first line takes the coupler line's cable (410) |
| `2026-09-28T1705_01.png` | AL004 branch 4 opened with **no** spec, 4.13's box | default Active IDs (`61`), taps `[ 0]` / `/ 0/`, couplers `0[9]`, the no-spec amp box |
| `2026-09-28T1705_02.webp`, `_03.webp` | Lode's own Unnamed Actives Specs table (two screens) | the default Active IDs with no spec: items 1–12 `11`…`33H`, 13–41 `61`–`89`, 42–50 `41`–`49`, then `###` |
| `2026-09-28T1739_01.webp` | Actives tab (Active ID, part, In/Out levels, banks) | every WV750 row the app reads matches |
| `2026-09-28T1743_01.png`, `_02.png` | Bridgers and Feedermakers tabs | neither says which active is an LE |
| `2026-09-28T1746_01.png` | 4.2 with `88` (FML1G7J ALC LE) placed, `/` on | `1-0-0 9-7-0`: LE vs amplifier goes by the place in the Actives table (items 1–12 are LEs), not the name; a placed active stores 0 pads/EQs; an unnamed active has no Amp Name line |
| `2026-09-28T1801_01.png`, `_02.png` | Delete on 4.14 (two branches), and `0` `0` on the splitter | "Branches 11, 12, begin at this node … these branches …"; `0` takes the splitter off both, leaving `- <11>` `- <12>` |
| `2026-09-28T1817_01.png` … `_03.png` | older AL004 (WVEXT862) branch 11 and its tap-fed branches | `117+` / `104+` taps feeding branches; 44.1 = 19.90 18.38 36.31 35.43; the 550 column after cplr[branch] (44.1 19.55, branch 11's 19 values) — `test_classic_specs.py::test_the_550_column_is_lodes` |

## 3. Screenshot sets sent as zips (`lodedata-evidence.zip`)

| folder | sent | answers |
|---|---|---|
| `2026-09-26_parameter-spec-images/` (6) | all six Spec Edit → Parameters tabs of WV750-2026 | Parameters mapped (file-formats 3.5); Strand/Trench Types decide "mileage"; span resistance truncated to whole milliohms (29/29 volts) |
| `2026-09-26_pad-eq/` (5) | Pads/EQs Bank tabs | names of the twelve numbers per bank row; the program's pad/EQ pick reproduced on 27 actives (108 values) |
| `2026-09-28_9-28-2026/` (3) | `4.png` current AL004 branch 44 (from 20.17: one 0-ft line, 44.1's node box); `5.png` branch 43 (from 9.20: supply C in the cplr column, 43.1's box with EXISTING 90v); `6.png` the user's design drawing of the terminated leg at AL00431 | in the current AL004, 43 and 44 are ordinary coupler branches (44 terminated, 43 carries a supply) |
| `2026-09-29_SHINSTON/` (9) | labelled by question: `1` branch 1 (Notes ♪, no Enter dialog), `2` branches 1–2, `3` Test list, `4a/4b` amp boxes 1.15/1.27, `5A/5B` expanded 1.15/1.22, `6A/6b` supply 4.1 | SN001 levels on 91 lines; configuration IDs; Notes; supply label 1A in the cplr column |
| `2026-09-29_SHINSTON2/` (15) | `1a–1e` brackets at 8.3, 15.10, 18.9, 24.7, 28.9; `2` Edit Notes window; `3a/3b` node box 1.2 / 1.29; `4` branch 5; `5a–5f` older AL004 Test list (94 lines) and 43.1 amp box | preview box layout, Q1 = "EQ", `117]`, Fslope/Rslope lines, notes rows end `~0`; the 14 Tap(550) lines and their colours (`test_the_test_list_is_lodes`), 43.1's 550 = 14.67 |
| `2026-09-29_SHINSTON3/` (10) | `1a–1c` notes in Lode (1c is the older AL004); `2` AL004 branch 9 with 9.2's power stop off → 9.1 `108<10>`; `3a–3c` AL004 branches 14 and 20 + 20.15 tap box; `4a/4b` older AL004 6.9 / 7.6 = EQ; `5` SN001 28.16 node box | the final `<n>` rule (power stop ends the walk); half-up 34.76 / 21.98 / 41.23; the node box on a branch's last line; the 550 column of branches 4, 6 and 7 (1c, 4a, 4b; an in-line device's fifth loss is F3) |
| `2026-10-02_setA/` (18; sent as `wxext862.zip`) | set A: `1a–1c` amp boxes 1.1 (HLN 3842 NODE), 6.1, 11.10; `2` 11.18 with no active, its tap box; `3a–3f` every WVEXT862 Parameters tab; `3g/3h` branches 25 and 23 with the 25.3 / 23.17 amp boxes; `4a/4b` branch 15 with the 15.3 / 15.4 tap boxes; `5a–5c` older AL004 branches 16, 9, 5; `5d` AL004 branch 5 | Cascade Position from Custom Cascading (`test_classic_specs.py::test_the_actives_as_lode_shows_them`, `test_ntw.py::test_amplifier_info_box`); the input/output check, its red cells and Lode's full 94-line list (`test_the_test_list_is_lodes`); brackets 16.4 `8<17>`, 9.14 `2<14>`, 5.19 `100<29>`/`100<32>`, 9.1 `108<10>`, 5.9 `1<45>` (`test_the_couplers_are_drawn_as_lode_draws_them`, `test_coupler_column_matches_the_screen`); every Parameters field as read; 15.4's screen equal to the app's. The red 505/438/515 cable numbers: set A2. `1a` (HLN 3842 NODE alone on 1.1, five lines on branch 1) was another copy of the older AL004: AL004_SETA.ntw (set A2) is the pack's file |
| `2026-10-02_setA2/` (14 + AL004_SETA.ntw; sent as `wxext862-2.zip`) | set A2: `AL004_SETA.ntw` (the pack's older AL004 but for the header's licence fields and the saved name — not added to the pack); `2A–2C` its Test list, 94 lines; `3A/3B` amp boxes 43.1, 44.1 (WIFI OMNI); `4a` branch 25 with the cursor on 25.2's red 505 and its box; `4b` branch 5 from 1.4 with the cursor on 5.9's 438; `4c/4d` WVEXT862 Spec Edit → Cables (IDs 0–52); `5` S3's 1.2 `100<2>` (cursor on it, red); `6a/6b` WVBeck750 and `6c/6d` WVEXT862 Spec Edit → Actives → Custom Cascading | Lode's Test list = the app's, every line, 15.4's three through the Test's rounding (`test_the_test_list_is_lodes`); 43.1 / 44.1 every figure, Cascade Position 4; branches 25 and 5 every number and colour; red cable numbers = the cable file's Series/Colors (`test_the_cable_numbers_in_their_series_colours`, `test_sn001.py::test_the_amp_and_tap_columns_are_lodes`, `test_ui.py::test_the_older_al004_with_its_older_spec_set`), the box naming the series; S3's 1.2 `100<2>` (the corrected bracket rule); Custom Cascading row for row (`test_the_older_spec_files_read_as_lode_shows_them`). Why S3's coupler is red: set of 3 Oct (an internal coupler away from an active) |
| `2026-10-02_specs/` (3 + the recording below; sent with `NBERN1GHz.zip`) | `1` BH1GHzMid keyed from File → New (1.1 amp 71, 1.2–1.4 coupler 99 to branches 2–4, 1.5 190 ft hc 2 `/26/`, 1.6 189 ft hc 5 `<21>`, 1.7 amp 11) with 1.7's box; `2` the same on HUMB1GHzMid (couplers `92`); `3` LK002 on LKMac862, branch 1 of 73, 1.1's node box | every figure of `1` and `2` — the four columns, 550 / 860 / 870 after the cplr columns, the end lines — is the app's (`test_keyed_regions.py`); column heads are the Parameters' labels (`3`: high low Rh Rl); a coupler record with an ID and no name (92) and a tap row with an ID and no part (21) are drawn, the levels going on through them; a keyed line's blank cab is cable 0; the pad / EQ pick with the Flag row and "Allow Over Equalization" unticked (1.7's Flag / CS2 / Flag / 3 and Flag / CS1 / Flag / 3) |
| `2026-10-03_set/` (35 + 5 recordings; sent as `wxext862-4.zip`, `wxext862-5.zip`, `4.zip`, `19a.zip`, `4_2.zip`) | answers to QUESTIONS 1-24 of 3 Oct: `1a/1b` BH keyed, the FM332's box as keyed and after 1.3's ftg 0 -> 900, `1c` its Test list; `2a` H043B's Test list; `3a` HUMB keyed on its own spec, `<20>` box; `4a` branch 2 behind 92; `5` 1.8 `/12/`; `6a-6c` a Ripple on AL004 4.20 (boxes 4.20, 4.24, 4.13); `7a/7b` S3's MULTI OUT red on 1.2, green moved under the Ripple; `10a/10b` BH Reserve Gain; `11.mp4` BH Actives tab scrolled right; `13b-13h` WV750 Plug-Ins and Configuration Table; `14.mp4`, `14a-14c` BH Taps window; `15.mp4` HUMB Couplers window; `16a-16d` WVEXT862 Connectors and Series/Colors; `17a/17b` BUCH Reserve Gain; `19a.mp4`, `19b-19f` NPG550 (old) Actives, Couplers and Taps windows; `20` LK002's PCD at 1.5 | pads / EQs picked as an amp is keyed and whenever its input changes (Flag/CS8/Flag/2, then 060/13/190/6; 4.24 FLAG/SCS6/20/0) and the return EQ not over-equalizing (`test_keyed_regions.py`, `test_ntw.py::test_a_ripple_placed_in_the_middle_of_a_cascade`); a 0 in a spec column is 0 dB and a negative coupler figure a gain (4a's -48.00 37.00 11.00 11.00, H043A/B); every figure of 3a and 5; a node mid-line reads the levels arriving, its return checked; an excluded active's Cascade Position counts those before it; an internal coupler away from an active red (`test_s3s_multi_out_100_ft_from_its_ripple_is_red`); the Spec Edit windows: Actives' last columns, Configuration Quantity, the Taps window, the Couplers window, Connectors, Series/Colors (`test_spec_windows.py`); BUCH row 42 RA-KIT-40L; a PCD drawn as the other network and line, "PCD branch connected to Network:" |

(The user's text for SHINSTON3 Q2 said "102[34]"; the screenshot shows
`108<10>` at 9.1 — the screenshot was followed.)

## 4. Screen recordings (kept by the user, not in the packs)

| recording | showed | settled |
|---|---|---|
| `Recording 2026-09-26 065053.mp4` (51 s) | `0` Alter + Home → Select Tap; `/` expanded display; `5` Test Results window; Esc closes | Design keys are the screen menu; Select Tap colours; the 37-line Test list; expanded display lines |
| `Recording 2026-09-27 072517.mp4` | the app: double-click on a coupler not entering, the too-big info box | coupler double-click; the tip box as Lode draws it; View → Show Tips |
| `Lode ntw open/1.mp4` | opening AL004 before attaching a spec | Spec File Mismatch box ("does not match 'WV750-2026' saved with"); no-spec screen (high low Rh Rl, 0.00, `0<2>`, cab 0 blank) |
| `Lode ntw open/2.mp4` | Project Settings on startup, keying a network from scratch with and without a spec | Project Settings / Errors Loading Project boxes; the recording-2 network's levels (2.1, 2.2, end line) reproduced; hc red when homes > ports |
| `COUPLER RCORDINGS/Recording 2026-09-28 093302.mp4` (85 s) | `0` on a coupler with lines, deleting lines, the power stop, Delete Branch(es)? | `0` keeps the branch (`- [55]`, starts at 0.00); "Cannot delete a line with a power stop."; `+` in Powering toggles a stop; Delete Branch(es)? wording |
| `NBERN1GHz.mp4` (85 s, 2 Oct; in `NBERN1GHz.zip`) | Spec Edit → Actives on NBERN1GHz-7-29-2025: every one of the 28 tabs, clicked through (Actives, Reserve Gain, Power Steps, Pads/EQs Bank 1 with its four sub-tabs, Bank 2, EQs Bank 9, 10, 16, Plug-Ins, Plug-Ins Powering, Configuration Table, Bridgers, Feedermakers, Inline EQs, Custom Cascading, Boosters, Booster Powering) | the Actives window as the app draws it — tabs, columns and their widths, row for row (`test_spec_windows.py`); eight power steps; 24 in-line devices with ten losses; every record a row, named or not; EQs Banks 9–16 at 172024; the multi-row tab strip (the picked tab's row moves next to the page) |

## 5. Answers given in words (no file)

Recorded as rules in the docs; listed here so their source is known.

* Tap colours: yellow = at the border (margin), green good, red not working;
  26 is WV750's highest tap, some specs have 29 (26 Sep).
* Keying in Design: `0` then `.` runs ftg → hc → cab → lv and stops at lv;
  taps `0 2 . 4`; `.` `+` on the amp column names the amplifier (tap1 shows
  the name until a tap goes there); `Insert` adds a 0-ft line above, `.`
  `Insert` below, the cursor stays; an inserted line takes the cable of the
  line above (26 Sep).
* Names: duplicates refused in any case; `.` `+` offers the last name, `+` /
  `-` step it (AL00410 → AL00411) (26 Sep).
* Select Tap: a double-click places the tap, replacing the slot's (26 Sep).
* Feedermaker Networks in Amplifier Definition: not used — leave out (26 Sep).
* Branch numbering: deleting renumbers later branches (2(3), 8(4), 12(5) →
  delete 2(3) → 8(3), 12(4)); a new coupler gets the next number after the
  highest (28 Sep).
* Save Network writes back into the opened file; Save As a new name; Lode
  opened all seven app-saved test files and NEW_T1 with every change (28 Sep).
* A network can be opened without a spec and the spec attached later, and a
  different spec set must never be blocked (node upgrades) (28 Sep).
* hc red when homes exceed the ports of all taps on the line (28 Sep).
* Typing `12` over `8[22]` keeps branch 22: `12[22]` (28 Sep).
* Delete on a freed `- <11>` deletes the line with both branches (28 Sep).
* Notes are `..+`, amplifier name `.+` (29 Sep).
* The mouse wheel moves the cursor within the branch; up past its first line
  returns to the coupler line it was entered from (29 Sep).
* Later topics, not started: the design engine itself (Recalc, AutoCpl …),
  and connecting two networks (PCD connect, shared power supply).
* 3 Oct: Recalc (8) changes nothing; the amp's box changed when 1.3's ftg
  changed. H043A_MID and H043B_MID share a power supply through a PCD.
  HUMB has no tap 21 (screenshot 2 was a BH-keyed network with HUMB loaded)
  and on HUMB the node split is 99, not 92. A network belongs to one spec
  set (opened without one, Lode names it); mismatched combinations do not
  matter; where they occur, keep the tap IDs and show them as Lode does.
  A Ripple (70) is a node, never placed between actives in a real design.
  S3's 100 is a node's leg coupler: at 0 ft only. Crossover lines: match
  Lode. Bridgers / Feedermakers: no network known that uses them. LK002's
  1.5 is a PCD. AL002 and AL003 are WVEXT862's, AL005 Beckley750's.
* The app must keep nothing about a network once it closes (30 Sep).
* Set A (2 Oct): with WVEXT862 the node counts as cascade 1, "not the case
  every time and rare"; 11.18 holds no active, the WiFi tap in its tap
  column (the red 64 seen on 29 Sep was not in the file).
* Set A2 (2 Oct), cable series: 5xx are risers, aerial to underground or
  back, 20 or 25 ft by region, drawn red in WVEXT862 but not in every spec;
  1xx are double runs; 4xx here is not a 4th run; 2xx are rarely used,
  sometimes for a riser. Do not send the samples and evidence zips or the
  download links after every push — only when really needed or asked.
