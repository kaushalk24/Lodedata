# Handoff — read this first in a new session

Everything a new session needs to carry on without losing anything: the
goal, how the user works, the rules learned, where the evidence is, what is
done and what comes next. Then read, in this order:

1. `docs/QUESTIONS.md` — the questions still open, only those the app
   cannot settle without Lode (N1b, 34, 35b, 33b, 43, N11b, 44), then
   Priority 7 (39–42); each says why, what to do in Lode step by step, what
   to send, what it settles and what the app does meanwhile. Below them,
   every answer so far.
2. `docs/open-questions.md` — each rule with its evidence, and the list
   "Still to confirm" at the end.
3. `docs/EVIDENCE.md` — every file, screenshot and recording the user sent,
   what it proved and which test pins it.
4. `docs/file-formats.md` — every decoded byte of the `.ntw` and spec files.
5. `docs/lode-data-manual-notes.md` — the vendor manual (22 PDFs, read in
   full in the first sessions).

`README.md`'s "Status" section is from the first week and out of date; the
files above are current. Do not edit `README.md` unless the user asks.

## The goal

Rebuild Lode Data **Design Assistant 12.11** (HFC/CATV network design) as a
web app that looks and behaves exactly like it: read, display, edit and save
`.ntw` files — saved files must open in Lode Data with every change — for
every spec set, at least:

| name used here | network | spec set | notes |
|---|---|---|---|
| AL004 | `AL004.ntw` | WV750-2026 | current Lode 12 files; the reference |
| older AL004 | the August `AL004.ntw` | WVEXT862 | Lode 4 spec formats (file-formats 3.0) |
| SN001 | `SN001_MID.ntw` | SHINN1GHz Mid (SHINSTON) | lines with Notes text; 1 GHz |

The user is a Lode Data designer. Current focus: **the application itself**.
(An earlier request added server deployment files — `DEPLOY.md`,
`install.sh`, `start-server.sh`, `run-tests.sh`, `deploy/` and
`tests/test_server.py`. They are not the focus; leave them as they are and
keep their tests passing.)

**The Windows program.** The users run the app as `LodeData.exe` on
Windows 11 laptops — no server (`desktop/README.md`). Every push to the
branch is built and checked by GitHub Actions on a Windows machine
(`.github/workflows/windows-exe.yml` → `desktop/build.bat`) and published as
the release "windows-latest":
https://github.com/kaushalk24/Lodedata/releases/download/windows-latest/LodeData-windows.zip
After each push, check that run went green (Actions → "Windows program").
Do not paste this link or the source link after every push — the user
asked (2 Oct) to get them only when they ask for them. Keep it working:
new Python dependencies go in `requirements.txt` (and, if PyInstaller does
not find them, in `desktop/build.bat`); new files the page loads go under
`app/web/`; Open/Save in the page go through `showOpenFilePicker` /
`showSaveFilePicker`, which the program replaces with Windows' dialogs
(`desktopFile` in `app/web/app.js`). **Nothing about a network is kept once
the program closes** (the user, 30 Sep): the networks live in a folder of
its own in `%TEMP%` for the run only; the page keeps no network, file or
last-opened in its own storage; the server launchers clear
`data/designs.db` at each start. The build checks nothing is left. Keep `desktop/LodeData.exe.config`
beside the exe (build.bat copies it): without it a copy unzipped from a
download cannot open its window — the user's laptop showed this, and the
build's "as if downloaded" start checks it every time.

## How the user works — standing instructions

* "Match the real program exactly; don't guess." When evidence is missing,
  **ask** for a specific screenshot, recording or test save — say exactly
  what to do in Lode Data and what it will settle.
* "Don't overengineer." "Don't add any other features other than what I
  mentioned."
* "Altering anything to fit a spec or ntw file must not change any spec or
  ntw file that already works and reads well." Before every push run the
  regression check below; if a change would alter what an existing file
  shows or writes, **ask first**, with the evidence.
* "Iterate one set of questions at a time; after fixing everything, the
  next set." QUESTIONS.md is one numbered list in priority order (the
  user asked for it so, 3 Oct): send the top questions, fix everything
  the answers show, renumber, then the next.
* "Analyze everything in depth." Check every number on every screenshot,
  not just the one asked about. Zoom into screenshots; measure colours and
  character positions when layout matters.
* If the user's words and a screenshot disagree, follow the screenshot and
  say so (SHINSTON3 Q2: text "102[34]", screenshot `108<10>`).
* Report plainly: what matches, what does not, what was guessed. Give the
  download links only when the user asks for them (source:
  https://github.com/kaushalk24/Lodedata/archive/refs/heads/claude/lode-data-reverse-engineer-65vgkc.zip,
  run with `run.bat`, http://localhost:8000; the Windows program link is
  above).
* Do not send `lodedata-samples.zip` / `lodedata-evidence.zip` after every
  set. Keep `samples/` (and the unzipped evidence) up to date in the
  session, and send the zips only when really necessary — the user asks,
  or the regression baseline changed and a new chat would otherwise start
  from the wrong one (say so when that happens).

## Security — never break these

* **Never commit** `.ntw`, spec (`.par .atv .tap .cpr .cbl`) or test files.
  `samples/` is gitignored; only `samples/README.md` is tracked (add it with
  `git add -f`). Screenshots and recordings are never committed either.
* **Never write licence numbers or user ids** from the files' 512-byte
  headers into docs, tests, code or commit messages (the current files are
  clean; QUESTIONS 42 asks whether to scrub old history — unanswered).
* Test `.ntw` files for the user go by SendUserFile from the scratchpad.

## Git

* Repo `kaushalk24/Lodedata`, branch **`claude/lode-data-reverse-engineer-65vgkc`**
  (all work is there; a session may be assigned another branch name by the
  environment — keep working on this one unless the user says otherwise).
* Commit as the user: `git -c user.email=kaushall2424@gmail.com -c user.name="Kaushal" commit`,
  ending the message with the Co-Authored-By / Claude-Session trailers the
  session gives. No model names in commits. Push with
  `git push -u origin claude/lode-data-reverse-engineer-65vgkc`. No pull
  requests unless asked.
* A stop hook may ask to re-author commits as Claude; the user asked for
  their own name — keep it, and re-author only if the user asks.

## Setting up a new session

1. The user uploads `lodedata-samples.zip` (and `lodedata-evidence.zip`).
2. `unzip -o lodedata-samples.zip -d .` in the repository root → `samples/…`
   as listed in `samples/README.md`. Unzip the evidence outside the repo
   (e.g. the scratchpad); `docs/EVIDENCE.md` indexes it.
   The pack of 2 Oct lacks what came later; put it in place from the
   user's zips if they upload them: `WVBeck750.zip` → `samples/WVBeck750/`
   (Q22: yes), `6.zip`'s PS_A, PS_B, H_A, H_B, BH_KEYED `.ntw` →
   `samples/lode-saved/`, `4_2.zip`'s Beckley750 → `samples/AL005-Beckley750/`,
   `wxext862-4.zip`'s H043A/B_MID → `samples/bullhead/`, LG001 (`5.zip`) →
   `samples/designs/`, and BH1GHzMid, HUMB1GHzMid, NBERN1GHz of 29 Jul 2025
   (the regions' zip) → `samples/regions/<name>/`. Each test that needs a
   missing file skips.
3. `python -m pytest -q`. Expected with all of them in place and
   Playwright/Chromium present: **all pass, none skipped** (261 on 4 Oct).
   The browser tests use `/opt/pw-browsers/chromium` (or `CHROMIUM_PATH`).
4. `python tools/regression.py snapshot /tmp/base.json` on the current
   commit: that is the baseline for the regression check below. (The
   pack's `samples/regression-baseline.json` is from e129475, 2 Oct; every
   change since was intended and is listed under "Done" below.)

## Regression check (every change)

    python tools/regression.py snapshot /tmp/after.json
    python tools/regression.py diff /tmp/base.json /tmp/after.json

Opens every `.ntw` in `samples/` with no spec and with every spec set there,
and compares every screen row, the Test list, the branch list and the saved
bytes. Anything that changes must be the change intended; anything else is
asked about before pushing. Add every new sample the user sends to
`samples/` so it joins the check.

## Where things are

| path | what |
|---|---|
| `tools/lodedata/obfuscation.py` | `.ntw` payload: `plain = nibswap((cipher - KEY[i % 100]) & 0xFF)` from offset 512 |
| `tools/lodedata/network.py` | `.ntw` reader: branch records, node records (1970 / 2504 bytes, + text at +698), every field |
| `tools/lodedata/writer.py` | `.ntw` writer over the opened file; every preamble total rebuilt; `blank()` = Lode's empty file |
| `tools/lodedata/specs.py` | `.cbl .cpr .atv .tap .par`, current and older (Lode 4) layouts by the version at byte 26 |
| `tools/lodedata/diff.py`, `cli.py` | `python -m lodedata diff a.ntw b.ntw` — what bytes a save changed |
| `tools/regression.py` | the every-file × every-spec check above |
| `app/hfc/importer.py` | spec set → library; `design_from_ntw()` (with or without a spec) |
| `app/hfc/screen.py` | the engine: levels, Test list, brackets, boxes, powering, expanded block |
| `app/hfc/exporter.py` | design → writer input |
| `app/hfc/entry.py` | typed codes: taps `4.23`, couplers `-8` / `3=`, Active IDs |
| `app/hfc/model.py`, `plant.py` | parts library; Design / Branch / Node |
| `app/api.py` | FastAPI; networks in SQLite (`data/designs.db`) while it runs only |
| `app/web/` | the UI: 12.11's menus, screen menus, grid, tip box, dialogs, keys, mouse |
| `tests/test_ntw.py` | AL004 against the user's screenshots, Parameters chains, Test list |
| `tests/test_ntw_writer.py` | byte-for-byte saves, totals, new networks |
| `tests/test_classic_specs.py` | older AL004 + WVEXT862 |
| `tests/test_sn001.py` | SN001 + SHINSTON |
| `tests/test_spec_sets.py` | every spec set under samples/, read whole |
| `tools/spec_coverage.py` | what each spec file's bytes mean to the readers, and what is left |
| `tests/test_ui.py` | the page in a real browser (Playwright) |
| `desktop/` | the Windows program: `lodedata_desktop.py` (window + engine), `build.bat`, `README.md` |
| `.github/workflows/windows-exe.yml` | builds and publishes `LodeData.exe` at every push |

## Where it stands

* **AL004 + WV750:** 45 branches, 275 lines, all resolved. Every number on
  every Design screenshot (branches 1, 3, 4, 6, 9, 11, 14, 18–22, 34), the
  Power screen of branch 4 (29 volts, 29 currents), the 37-line Test list
  (and the 36-line one with changed settings), expanded display blocks, info
  boxes, Select Tap, pads/EQs (the program's pick on all 27 actives).
* **Older AL004 + WVEXT862:** opens with nothing unresolved and saves byte
  for byte; branches 5 (from 5.13), 6, 7, 9, 11, 15, 16, 23 and 25 match
  line for line, with the 550 column (57 values) and the amp boxes of 6.1,
  11.10, 25.3, 23.17, 43.1 and 44.1 field for field; all 94 of Lode's Test
  lines in its order, every line (twice: 1 Oct, and 2 Oct from the user's
  AL004_SETA.ntw, which is the pack's file but for its header and name);
  cable numbers in their series' colours (505, 515, 438 red).
* **SN001 + SHINSTON:** 47 branches, 390 lines; branches 1, 2, 5, 8, 15, 18,
  24, 28 match; 15-line Test list; Notes written exactly as Lode writes them.
* **Coupler brackets:** four kinds, `(n)` `{n}` `<n>` `[n]` (4 Oct; Lode's
  glyphs measured pixel by pixel — `<`, `(` and `{` look alike at a glance):
  every bracket on every screenshot since 26 Sep matches, on AL004, the older
  AL004, SN001, LG001, S3 and the keyed BH/HUMB.
* **Cascade Position:** from the actives' Custom Cascading (file-formats
  3.3; every row of WVEXT862's and WVBeck750's tabs decoded): every box
  seen on all three networks.
* **Cable colours:** the cable number in the colour its cable file gives
  its series (file-formats 3.2), on all three spec sets; the cursor on ftg,
  hc, cab or lv lights all four.
* **Saving:** byte-for-byte round trips; Lode opened every file the app
  saved (seven edit tests, NEW_T1 keyed from scratch, Notes).
* **Extra frequencies (2 Oct, evening):** F3–F6, every one the Parameters
  have on, each its own column after the cplr columns, headed with the
  Parameters' label (LKMac862: `high low Rh Rl`). The user's BH1GHzMid and
  HUMB1GHzMid networks keyed through the app's API reproduce both
  screenshots, every figure (`tests/test_keyed_regions.py`).
* **Spec Edit windows (2 Oct, evening):** Spec Edit → Actives, Cables and
  Parameters open the program's own windows (title, File/Edit menus,
  toolbar, the multi-row tab strip, grids with `It...` numbers, Prefix
  boxes, Load / Cancel, status bar), every record of the network's own file
  (the app now keeps the five files with the network; `GET
  /api/networks/{id}/specs/atv|cbl|par`, `app/hfc/specwindow.py`). Shown
  only — nothing edits a spec file yet. Taps and Couplers still open the
  plain list until their windows were seen (built 3 Oct).
* **Keys and mouse:** Design screen menu digits, `0` Alter, `.`-moves,
  Insert, Delete, Amplifier Definition, Notes, Select Tap, double-click a
  coupler to enter its branch, **mouse wheel** moves the cursor within the
  branch and, up past the first line, back to the coupler line it was
  entered from (commit d4d2065).

## Next step

The answers to `docs/QUESTIONS.md`'s open list when they come (N1b, 34,
35b, 33b, 43, N11b, 44), then Priority 7 (39–42).
The work item that needs no answer first: **reading the oldest actives
formats** (2.20 / 3.0 / 5.0) from the user's recording of NPG550's Actives
window (`2026-10-03_set/19a.mp4`, every tab; 19b–19f its Couplers and Taps
windows, the older 10.0 / 3.0 layouts the readers already know); N11b's
keyed network then checks it.

**Done 4 Oct, evening** (the user's `6.zip`: answers to 22, 28, 33–38,
C1–C5, N1–N12; `EVIDENCE.md`, `2026-10-04b_set`):

* Underground housings: the rule (file-formats 3.8) gives every file's
  tally and every marker on H043B's n5a–f; H043A/B now save byte for byte.
* Saving as Lode saves: a new power supply's record (PS_B), the house list
  filled on an hc change and the arrow (fixed flag) cleared by it (H_B),
  both byte for byte but the cursor at 41425 (and PS_B's undecoded 36121);
  BH_KEYED's pads and tallies (`tests/test_lode_saved.py`).
* Pick: fibre-fed actives are picked too (BH_KEYED's NC4000 0 0 7 0); an
  EQ bank column with no rows gives 255.
* Screens: brackets — a 0-ft line on another cable ends the walk, the span
  reached may be on any cable (C1: LG001 11.5 `2<16>`; N3: H043B 1.3
  `99<2>`); no block on a branch's 0-ft first line (C3); pad / EQ labels
  untrimmed until the amp's box has been shown (C2); the PCD cell and "No
  Feeder" (N3/N4); "Not enough taps at node b.n." (N12); a supply type the
  spec does not list is 60 V, unpowered lines 0.00, NIU `Y`, the cab cell in
  its series' colour in Power (37); a supply in an area another supply
  already powers is still drawn — its label, type and % (35b/35c: PS_B's
  46.1; also AL002's 43.1).
* Keys: "Deleting Branch" before a tap feeding a branch is taken off (28);
  Num Lock's "Network Modified" box (33).
* Beckley750's Parameters checked against all six tabs; AL005's Test list
  (51 lines) is Lode's (`tests/test_al005.py`); WVBeck750 in the samples.
* Regression against 32e5eed: saved bytes change only for H043A/B (now the
  source's); on the networks' own spec sets the screens change only where
  the answers above say (brackets of LG001 11.5, H043B 1.3, AL003 10.4;
  blocks and node boxes on branches' 0-ft first lines; the PCD cells; the
  housings; AL002's 60 V and 43.1's supply label; "Not enough taps" lines on
  AL002, AL003, NEW_T1, H_B, BH_KEYED; the older AL004's 43.1/44.1
  `<NO RET EQ>`). The mismatched combinations move with the 60 V fallback.

**Done 4 Oct** (the user's answers to 25–33; `EVIDENCE.md`, `2026-10-04_set`):

* Brackets: `(n)` no footage, `{n}` along the parent's span behind (wins
  when both match), `<n>` along the span ahead, `[n]` the rest; the walk
  passes 0-ft lines and power stops, and from a 0-ft coupler line a span
  counts only on that line's cable (`screen.branch_kind`). 6-port slots
  `{n}`; the expanded amp lines in round brackets.
* Double-clicking the second bracket of a splitter enters its branch.
* The expanded display's block also on the last line of a cable (5.25,
  5.27), whose node box stays short.
* With Allow Over Equalization unticked and no EQ that fits: no forward EQ
  (255; `VOID` / blank in the box, `<NO FWD EQ>` with a reverse-cyan
  lead-in) — KERMIT750 on LG001.
* An internal coupler counts as at its active only after it (2.33's MB-JMP
  above the FM902T on 2.35: red).
* Regression against 8c39e19: no saved byte and no Test list changes on any
  network; on their own spec sets the screens change in the brackets, the
  new blocks, LG001 11.5 / H043A 1.3 / H043B 1.3 / AL003 10.4 (the 0-ft
  coupler-line cable rule; C1, N3, N4 ask) and `<NO FWD EQ>` on the older
  AL004's WIFI OMNIs (C4 asks).

**Done 3 Oct** (the user's answers to the morning's 1–24; `EVIDENCE.md`):

* Pads and EQs: picked as an active is keyed and again for every active
  whose input an edit changes (`screen.repick`, called by the API's edit
  endpoints through `load_for_edit` / `save`); with "Allow Over
  Equalization" unticked the return EQ is held back too. Opening a file
  changes nothing.
* Couplers: each column as it stands — 0 is 0 dB, a negative figure a gain
  (`importer._coupler_points`). Bullhead's FMT Split (-9 forward) put every
  active behind an FM902T 18 dB low; now H043A/B's 48 actives all hold the
  pick for the app's levels and H043B's Test list is Lode's.
* A fibre-fed active away from the network's first line shows the levels
  arriving and has its return checked; the first line reads 0.00 and a
  Lode spec set's network starts from 0.00 (the launch level is the sample
  specs' only). An excluded active's Cascade Position counts those before it.
* An internal coupler away from any active is red (S3's 1.2).
* Crossover lines seven wide.
* Taps: Self-Term. read from the file (current layout).
* PCD networks (H043A/B): the network table before branch 1 kept, the
  branch head's coupler field a u16 (999), PCDs left out of the coupler
  count and given one connector; a PCD's display and the underground
  housings' tally are open (part B).
* Spec Edit: the Actives tab's every column, Configuration Quantity, the
  Taps window (eleven tabs), the Couplers window (five), Cables' Connectors
  and Series/Colors.
* Regression against the morning's commit: every network on its own spec set
  changes only in the crossover lines' spacing; no saved byte changes; the
  mismatched combinations move (the couplers' signs and zeros, the 0.00
  start) — the user: those do not matter. New: H043A/B save; AL005 +
  Beckley750.

**Done 2 Oct, evening** (the user's BH / HUMB / LK002 screenshots and the
recording of NBERN1GHz's Actives window; `EVIDENCE.md`):

* Readers: power steps eight (the tab's); in-line devices 24 with all ten
  losses (the reader ran on into the next table); In / Out at F3–F6 (+171 /
  +195, the older +127 / +151); Ret. Mod. Part Number (+30) and reserve
  gains (+91 / +95); a coupler record with an ID and no name (HUMB's 92);
  the IDs of tap rows with no part (HUMB's 21); a bank column's Flag row,
  any case, is its last choice; EQs Banks 9–16, the Plug-Ins names, the
  Configuration Table's Plugin 1 (file-formats 3.3, 3.4b–d).
* Engine: every extra forward frequency (model `extra_*` lists in place of
  the single `f3` fields; networks stored before are converted on load);
  labels as column heads and in Test lines; an empty tap slot is drawn and
  passes the levels at 0 dB; keyed taps take the port count from the
  Parameters' Tap Selection (named parts first); a new line's blank cab is
  cable 0; the forward EQ pick honours "Allow Over Equalization".
* The regression check against the last commit (48cb7b8) changes 32 of 70,
  all networks opened with a spec set other than their own (or AL002 /
  AL003 / AL005, whose own sets are not in the pack): taps on empty slots
  now drawn, and stored pads pointing at a bank's FLAG row shown `FLAG`.
  Every pairing checked against Lode is unchanged, and nothing a save
  writes. Asked as QUESTIONS 9; the user (3 Oct): mismatched sets do not matter.
* `samples/regions/` (local only) holds BH1GHzMid, HUMB1GHzMid and
  NBERN1GHz of 29 Jul 2025 for `test_keyed_regions.py` and
  `test_spec_windows.py`; the pack the user holds does not have them yet —
  without them those tests skip.

**Earlier on 2 Oct, the spec files first** — every region's spec set must
load, the spec being the key to every value. `python tools/spec_coverage.py
[base …]` measures what each file's bytes mean to the readers and lists the
rest (file-formats "Decode status"); `tests/test_spec_sets.py` checks every
set under samples/. When a new set arrives: run the tool on it first — a
file of a version or size not seen is flagged — then the tests and the
regression check with it in samples/.

**The regions' spec sets (2 Oct):** 168 different sets from 20 markets, all
164 complete ones load and open AL004 and SN001 without an error; 7 old
formats (actives 2.20/3.0/5.0) not readable — file-formats "The regions'
spec sets".

**What set A2 raised** (answered 3 Oct): an excluded active
(a Ripple) put in the middle of a cascade on a copy of AL004, S3's red
coupler (the file and the window), and the crossover spacing (yes/no,
asked twice now).

**Set A2 (answered 2 Oct, `EVIDENCE.md` 3):** AL004_SETA.ntw is the pack's
older AL004 (set A's HLN screenshot was another copy) and its Test list is
the app's, all 94 lines; 15.4's three lines solved — the Test rounds a
level under zero a cent up (`screen.as_tested`); 43.1 and 44.1 Cascade
Position 4; red cable numbers solved — the cable file's Series/Colors slots
(`CableSpec.series`), drawn by the page with the cursor lighting ftg–lv and
the box naming the series; S3's 1.2 `100<2>` confirmed; Custom Cascading
decoded field by field (Cust. Casc., Exclude, Casc. 1–14) and the position
restated as a count of the actives not excluded (the same on every real
network). The regression check against the pack's baseline (e129475)
changes 23 of 70: the older AL004 + WVEXT862 (15.4's three lines, wanted);
lines whose port is under zero a cent lower on AL002, AL003 and AL005 with
WV750 and on mismatched combinations; and cascade positions on networks
opened with KERMIT's or SHINSTON's actives, whose "61" is an excluded node.
AL004 + WV750 and SN001 + SHINSTON are unchanged. The 23: AL002, AL003
and AL005 with each of the four sets (12); the older AL004 with each (4);
AL004 and AL004_NOTES with KERMIT and with SHINSTON (4); SN001_MID,
SN001_NOTES_test and SN001_NOTES with KERMIT (3). The samples pack was not
re-sent: a new session that finds exactly those 23 takes its own snapshot
as the baseline.

**Set A (answered 1–2 Oct, `EVIDENCE.md` 3):** cascade position from the
Custom Cascading bytes; Lode's input/output Test lines and red cells in
place of the app's old stand-in ("input below the module input", the whole
line red); the bracket rule corrected twice (16.4 `8<17>`, 9.14 `2<14>`);
In at 550 at +127. The regression check changed only the older AL004 among
the real networks, plus S3's 1.2 bracket (asked, A10), and networks opened
with others' spec sets.

**Done before set A: the 550 (F3) column** and its 14 Tap(550) Test lines
(`tests/test_classic_specs.py::test_the_550_column_is_lodes`,
`test_the_test_list_is_lodes`). What it rests on (file-formats 3.0, 3.1,
3.4b, 3.5):

* WVEXT862's Parameters has a third forward frequency, F3 = 550; with it on
  Lode draws its column **after the two cplr[branch] columns** (every
  older-AL004 screenshot; an earlier note here said "between 54 and 40" —
  wrong). The tap box and the port levels under the tap columns stay 870 54
  / 40 5. With WV750, SHINSTON, KERMIT or WVBeck F3 is off: no column.
* Cables, couplers and taps: slot 2 of the ten-slot blocks. In-line devices:
  their **fifth** loss (F1 F2 R1 R2 F3 — LEQ-PEA-8's 3.1 at 6.9 and 7.6).
  Older actives: In F3 at +127, Out F3 at +151. The F3 figures are kept
  beside each part, not among the points the other columns interpolate
  between, so every other level is bit for bit as before.
* The Test list checks a tap's ports in the Parameters' order, 870 54 550
  40 5, min/max first, then windows (F3: Min 15 / 18 on levels 0 / 1,
  window 12), then the crossover. A tap takes its worst port's colour, 550
  included (no tap on the older AL004 is out at 550 alone).
* Not built: where a current-layout (Lode 12) `.atv` keeps an active's F3
  levels — no current spec set has F3 on (values at +171 / +195 look like
  them); F4–F6 and R3–R4 (no spec set has them on).

After questions 1–10: the rest of QUESTIONS.md, in its order.

**Later topics the user named, not started:** the design engine itself
(what Recalc, AutoCpl and the other screen-menu commands do — "the main
question regarding the design"), and connecting networks (PCD connect,
networks sharing a power supply).

## Tooling notes

* Never `pkill -f` a pattern that appears in your own command line — it
  kills the shell. Stop servers by pid.
* `git add` of a gitignored path aborts the whole add; use `-f` only for
  `samples/README.md`.
* Screen recordings: extract frames when the screen changes (plus a
  settled frame 0.5 s later) to read them.
* LibreOffice/Playwright/Chromium: Chromium is at `/opt/pw-browsers/chromium`.
