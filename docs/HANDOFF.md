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
  download link after pushing:
  https://github.com/kaushalk24/Lodedata/archive/refs/heads/claude/lode-data-reverse-engineer-65vgkc.zip
  (the user runs it on Windows with `run.bat`, http://localhost:8000).

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
   — must print "0 of 70 changed": the new session starts exactly where the
   last one ended (the baseline was taken on commit d4d2065's engine with
   the full samples pack). `/tmp/base.json` is then the baseline for the
   regression check below.

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
| `app/api.py` | FastAPI; networks in SQLite (`data/designs.db`) |
| `app/web/` | the UI: 12.11's menus, screen menus, grid, tip box, dialogs, keys, mouse |
| `tests/test_ntw.py` | AL004 against the user's screenshots, Parameters chains, Test list |
| `tests/test_ntw_writer.py` | byte-for-byte saves, totals, new networks |
| `tests/test_classic_specs.py` | older AL004 + WVEXT862 |
| `tests/test_sn001.py` | SN001 + SHINSTON |
| `tests/test_ui.py` | the page in a real browser (Playwright) |

## Where it stands

* **AL004 + WV750:** 45 branches, 275 lines, all resolved. Every number on
  every Design screenshot (branches 1, 3, 4, 6, 9, 11, 14, 18–22, 34), the
  Power screen of branch 4 (29 volts, 29 currents), the 37-line Test list
  (and the 36-line one with changed settings), expanded display blocks, info
  boxes, Select Tap, pads/EQs (the program's pick on all 27 actives).
* **Older AL004 + WVEXT862:** opens with nothing unresolved and saves byte
  for byte; branches 6 and 7 match line for line; 67 of Lode's 94 Test lines.
* **SN001 + SHINSTON:** 47 branches, 390 lines; branches 1, 2, 5, 8, 15, 18,
  24, 28 match; 15-line Test list; Notes written exactly as Lode writes them.
* **Coupler brackets:** 64 of 64 seen match (AL004 23, older 13, SN001 28).
* **Saving:** byte-for-byte round trips; Lode opened every file the app
  saved (seven edit tests, NEW_T1 keyed from scratch, Notes).
* **Keys and mouse:** Design screen menu digits, `0` Alter, `.`-moves,
  Insert, Delete, Amplifier Definition, Notes, Select Tap, double-click a
  coupler to enter its branch, **mouse wheel** moves the cursor within the
  branch and, up past the first line, back to the coupler line it was
  entered from (commit d4d2065).

## Next step

**Question set A** (older AL004) in `docs/QUESTIONS.md` was sent to the user
and is waiting for their screenshots: cascade position (2/3/4 vs the app's
1/3/3), the red "64" on 11.18, the "input … to LE" / "output … from LE" /
"LE 11/5 before/0 after" Test lines, 15.4's 23.18 vs 23.19, and four
brackets not yet on screen.

With that set, build the **550 (F3) column** and its **14 Tap(550) Test
lines** — this needs nothing from the user:

* WVEXT862's Parameters has a third forward frequency, F3 = 550
  (file-formats 3.0: "870 54 550 / 40 5"; Min F3 per level at 2976 + 24·lv
  in the current `.par`, file-formats 3.5). Lode shows the column between
  54 and 40 with WVEXT862 (19.55 at 44.1, 0.00 under it); with WV750 F3 is
  off and there is no column.
* Cable, coupler and tap loss blocks carry it: slot 2 of the ten-slot block
  (0 F-high, 1 F-low, 2–5 F3–F6, 6 Rh, 7 Rl, 8–9 R3–R4; file-formats 3.1).
* Older `.atv` actives hold F3–F6 inputs at +135 and outputs at +151 (i32
  ×1e6): 0 inputs; outputs 43.0 on the LEs and FNB99, 41.1 on NC4000, 43.5
  on HLN 3842 NODE. Checked by hand against Lode's screen: 4.1 = 35.20 and
  4.2 = 33.28.
* Then compare every 550 value on the older-AL004 screenshots (sets
  SHINSTON2 5a–5f, SHINSTON3 1c/4a/4b in the evidence pack) and the Tap(550)
  lines of its 94-line Test list, and run the regression check (AL004 and
  SN001 must not change).

After set A: sets B–G of QUESTIONS.md, one at a time.

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
