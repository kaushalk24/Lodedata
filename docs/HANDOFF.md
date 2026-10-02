# Handoff — read this first in a new session

Everything a new session needs to carry on without losing anything: the
goal, how the user works, the rules learned, where the evidence is, what is
done and what comes next. Then read, in this order:

1. `docs/QUESTIONS.md` — every question still open, grouped in sets, with
   what the user sends for each. **Set A is next.**
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
  next set." Group questions in sets (QUESTIONS.md), send one set, fix
  everything it shows, then the next.
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
  clean; QUESTIONS 26 asks whether to scrub old history — unanswered).
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
3. `python -m pytest -q`. Expected with the samples zip in place and
   Playwright/Chromium present: **all pass, 34 skipped** — the 34 need the
   **WVBeck750** spec set, which no pack has (QUESTIONS 23). The browser
   tests use `/opt/pw-browsers/chromium` (or `CHROMIUM_PATH`).
4. `python tools/regression.py snapshot /tmp/base.json`, then
   `python tools/regression.py diff samples/regression-baseline.json /tmp/base.json`
   — the baseline in the pack was taken on commit e129475 (set A) and sent
   on 2 Oct; set A2 changed 23 of the 70 since (see "Set A2" below: the
   older AL004 + WVEXT862, Test lines with a port under zero, cascade
   positions with KERMIT's or SHINSTON's actives — AL004 + WV750 and SN001
   + SHINSTON unchanged). Exactly those 23, and nothing else, means the
   session starts where the last one ended. If the pack holds the 30 Sep
   baseline, from 5e55e0d, set A's changes differ too: the networks opened
   with WVEXT862, S3's 1.2 bracket and a few mismatched-spec combinations.
   `/tmp/base.json` is then the baseline for the regression check below.

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
* **Coupler brackets:** 85 of 85 seen match (AL004 29, older 28, SN001 28).
* **Cascade Position:** from the actives' Custom Cascading (file-formats
  3.3; every row of WVEXT862's and WVBeck750's tabs decoded): every box
  seen on all three networks.
* **Cable colours:** the cable number in the colour its cable file gives
  its series (file-formats 3.2), on all three spec sets; the cursor on ftg,
  hc, cab or lv lights all four.
* **Saving:** byte-for-byte round trips; Lode opened every file the app
  saved (seven edit tests, NEW_T1 keyed from scratch, Notes).
* **Keys and mouse:** Design screen menu digits, `0` Alter, `.`-moves,
  Insert, Delete, Amplifier Definition, Notes, Select Tap, double-click a
  coupler to enter its branch, **mouse wheel** moves the cursor within the
  branch and, up past the first line, back to the coupler line it was
  entered from (commit d4d2065).

## Next step

**The user's priority (2 Oct): the spec files first** — every region's spec
set must load, the spec being the key to every value. **Question set S** in
`docs/QUESTIONS.md` goes to the user next: every other spec set they have,
and the Spec Edit tabs (Taps, Actives, Couplers, Cables) that show the
fields still unexplained. `python tools/spec_coverage.py [base …]` measures
what each file's bytes mean to the readers and lists the rest
(file-formats "Decode status"); `tests/test_spec_sets.py` checks every set
under samples/. When a new set arrives: run the tool on it first — a file
of a version or size not seen is flagged — then the tests and the
regression check with it in samples/.

Done for it on 2 Oct, no screen or saved byte changed: the actives table is
read by its size (251 records, 51 in the older file — the banks start one
byte after it), not by whether its figures look likely; the power steps by
the record's room (six older, nine current); Custom Cascading as 32 bits
(KERMIT's line extenders hold Casc. 15); In and Out at F3 in the current
record (+171 / +195); the in-line table by its size.

**The regions' spec sets (2 Oct):** 168 different sets from 20 markets, all
164 complete ones load and open AL004 and SN001 without an error; 135 with
every value read, 11 with frequencies named high/low/Rh/Rl, 11 with one
actives table unread, 7 old formats (actives 2.20/3.0/5.0) not readable —
file-formats "The regions' spec sets". The gap that matters most: 14 current
1 GHz sets (Bullhead, Eureka) have a fourth forward frequency (F4) on, and
the app draws only F3 — asked first (S1a) for Lode's screen.

**Question set A3** (what set A2 raised) follows set S: an excluded active
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

After set A3: sets B–G of QUESTIONS.md, one at a time.

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
