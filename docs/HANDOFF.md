# Handoff — read this first in a new session

The current state of the project, written so a new session can continue
without the earlier chats. Checkpoint: **4 Oct 2026, end of session**. Code
checkpoint **d1761f1**; the handoff commit after it changes only docs (its
message begins "Handoff checkpoint"). Both private packs carry
`HANDOFF-CHECKPOINT.txt` (in the samples pack: `samples/HANDOFF-CHECKPOINT.txt`)
with the exact SHA, test and regression figures.

Read next, only as far as the work needs:

1. `docs/QUESTIONS.md` — the **CURRENT OPEN QUEUE** at the top and the
   status register of every question ever asked. Never ask the user again
   anything marked SOLVED, SUPERSEDED or NO LONGER RELEVANT.
2. `docs/EVIDENCE.md` — every file, screenshot and recording, what it proved
   and which test pins it. Look up the rows for the question at hand.
3. `docs/file-formats.md` — every decoded byte (`.ntw` §3.7–3.8, spec files
   §3.0–3.5). Read the section the work touches.
4. `docs/open-questions.md` — each screen rule with its evidence.
5. `docs/lode-data-manual-notes.md` — the vendor manual's content.

`README.md`'s "Status" is from the first week and out of date; do not edit
`README.md` unless the user asks.

## Project

Rebuild Lode Data **Design Assistant 12.11** (HFC / CATV network design) so
it looks and behaves exactly like it: read, display, edit and save `.ntw`
networks with their spec sets (`.par .atv .tap .cpr .cbl`); a saved file
must open in Lode Data with every change.

**The product is `LodeData.exe` on Windows** (Windows 11 laptops, no server;
`desktop/README.md`). Inside, a FastAPI engine (`app/`) serves a page
(`app/web/`) shown in a WebView window (`desktop/lodedata_desktop.py`).
Open/Save go through `showOpenFilePicker` / `showSaveFilePicker`, which the
program replaces with Windows' dialogs (`desktopFile` in `app/web/app.js`).
The repo also holds server files from an earlier request (`DEPLOY.md`,
`install.sh`, `start-server.sh`, `run-tests.sh`, `deploy/`,
`tests/test_server.py`): not the focus; keep their tests passing.

## Product requirements (the user's)

* Exact Lode compatibility first. **Do not guess** missing behaviour: ask
  for a precise screenshot / recording / test save (say exactly what to do
  in Lode, what to send, what it settles). Ask only what cannot be solved
  otherwise.
* **Don't overengineer; add no feature not asked for.**
* A change made for one file must not change any file that already works:
  run the regression check before every push; if a change would alter an
  existing file's screen or saved bytes, ask first, with the evidence.
* Analyze every number on every screenshot, not just the one asked about.
  Where the user's words and a screenshot disagree, follow the screenshot
  and say so.
* **Sessions are ephemeral:** after closing and reopening the exe, no network
  opened before may come back — no recent list, no session restore (the
  user, 30 Sep). Networks live in a `%TEMP%` folder for the run only; the
  page keeps nothing in its own storage; the build checks nothing is left.
  Saved `.ntw` files stay where the user saved them.
* Keep `desktop/LodeData.exe.config` beside the exe (build.bat copies it):
  without it a copy unzipped from a download cannot open its window.
* Do not send the samples / evidence zips or download links after every
  push — only when the user asks or a new chat would otherwise start from a
  wrong baseline. Report plainly: what matches, what does not, what was
  guessed.

## Security — never break these

* **Never commit** `.ntw`, spec or test files, screenshots, recordings or the
  zips. `samples/` is gitignored; only `samples/README.md` is tracked
  (`git add -f`).
* **Never write licence numbers or user ids** from the files' 512-byte
  headers into docs, tests, code, commit messages or logs shown to the user.
  (Old commits before 26 Sep still quote some: QUESTIONS 42 asks whether to
  rewrite history.)

## Git and build

* Repo `kaushalk24/Lodedata`, branch **`claude/lode-data-reverse-engineer-65vgkc`**
  (keep working on it even if the environment names another branch).
* Commit as the user: `git -c user.email=kaushall2424@gmail.com -c user.name="Kaushal" commit`,
  ending with the Co-Authored-By / Claude-Session trailers the session
  gives. No model names in commits, docs or code. Push with
  `git push -u origin claude/lode-data-reverse-engineer-65vgkc`. No pull
  requests unless asked.
* Every push runs **"Windows program"** (`.github/workflows/windows-exe.yml`
  → `desktop/build.bat`) on a Windows runner: builds `LodeData.exe`, starts
  it as built and as unzipped from a download, checks nothing is kept, and
  publishes the release `windows-latest` (`LodeData-windows.zip`). After
  each push check the run is green:
  `gh api "repos/kaushalk24/Lodedata/actions/runs?head_sha=<sha>"`.
  New Python dependencies go in `requirements.txt` (and `desktop/build.bat`
  if PyInstaller misses them); new page files under `app/web/`.

## What works today

* **`.ntw` reading** (`tools/lodedata/network.py`): header + obfuscated
  payload, the 44 295-byte preamble, branch heads, node records (1970 /
  2504 bytes, Notes text at +698 moving the rest), taps, couplers, actives,
  in-line devices, supplies, power stops, fixed flags, the PCD network table.
* **`.ntw` writing** (`tools/lodedata/writer.py`) over the opened file:
  every golden network re-saves byte for byte (exceptions below); every
  decoded preamble total rebuilt (pads/EQs, actives, taps, couplers,
  connectors, underground housings, parts); new lines, branches, actives,
  supplies, house lists as Lode writes them (H_B, PS_B, S1–S3); a network
  keyed from scratch over Lode's own empty file. Lode has opened every file
  the app saved.
* **Spec sets** (`tools/lodedata/specs.py`): current (Lode 12) and older
  (Lode 4) layouts of all five files; 164 of the regions' 168 sets load.
  **Not read:** the oldest actives 2.20 / 3.0 / 5.0 (NPG550 and six others).
* **Screen engine** (`app/hfc/screen.py`): levels at every frequency incl.
  F3–F6 extra columns; taps (2/4/6/8-port glyphs, several per line, tap-fed
  branches `117+`), couplers and the four branch brackets, splitters,
  PCD cells; actives with Cascade Position (Custom Cascading), pads/EQs
  picked as Lode picks them (keyed or input changed; Allow Over
  Equalization; `<NO FWD EQ>`); in-line devices; the Test list word for word
  (taps min/max/window/crossover, active input/output, Fslope/Rslope,
  cascade, "Not enough taps"); info boxes; the expanded display (`/`) with
  blocks, housings, pad/EQ lines; cable numbers in series colours; Notes;
  Powering (volts, currents, supplies, power stops, 60 V for an unlisted
  supply type).
* **UI** (`app/web/`): 12.11's menus, screen menus, Design / Entry / Power
  modes, keys (`0` Alter, `.` moves, Insert, Delete, Amplifier Definition,
  Notes, Select Tap, Num Lock's Network Modified box, Deleting Branch box),
  mouse (double-click brackets, wheel), Spec Edit windows (Actives, Cables,
  Parameters, Taps, Couplers — shown, not edited), Save / Save As.

### Golden datasets (network + its own spec set: must stay exact)

| network (`samples/…`) | spec set | validates |
|---|---|---|
| `AL004-WV750/AL004.ntw` | WV750-2026 | the reference: every screen since 26 Sep, Test list (38), Power branch 4, byte-for-byte save |
| `AL004-WVEXT862/AL004.ntw` | WVEXT862 | older spec formats, 550 column, 94-line Test list, tap-fed branches 43/44 |
| `SN001-SHINSTON/SN001_MID.ntw`, `SN001_NOTES_test.ntw` | SHINN1GHz Mid | Notes, configuration IDs, Lode's save of the app's notes |
| `app-saved/AL004_NOTES.ntw`, `SN001_NOTES.ntw`, `NEW_T1.ntw` | WV750-2026 / SHINN1GHz Mid | files the app wrote and Lode opened |
| `bullhead/H043A_MID.ntw`, `H043B_MID.ntw` | BH1GHzMid (`regions/`) | PCDs, coupler signs, 48 actives' picks, both Test lists, housings |
| `designs/AL002.ntw`, `AL003.ntw` | WVEXT862 | short-record actives, Power on an unlisted supply type (AL002 branch 4) |
| `designs/AL005.ntw` | Beckley750 | Parameters 7.0, 51-line Test list |
| `designs/LG001.ntw` | WV750-2026 (also opened with KERMIT750 in `test_lg001.py`) | brackets, `<NO FWD EQ>` |
| `keyed/BLANK_test.ntw`, `S1`–`S3.ntw` | none / WV750-2026 | Lode's empty network and a network keyed from it |
| `lode-saved/H_A`, `H_B`, `PS_A`, `PS_B.ntw` | WV750-2026 | Lode's saves before/after one edit |
| `lode-saved/BH_KEYED.ntw` | BH1GHzMid | a keyed network's picks and tallies |
| `partest/*.par`, `act.atv` | — | Parameters offsets (save chains) |

KERMIT750, WVBeck750, HUMB1GHzMid and NBERN1GHz are spec sets only (keying
tests, spec windows). Every other network × spec pairing is
**exploratory**: the user (3 Oct) — mismatched pairs do not matter.

## Known gaps

**Awaiting evidence (QUESTIONS open queue):** 88's pad pick (N1b; the app
picks, Lode does not); TSG/Map/Loc/address not written (34); keying a
supply's type and name in Power (35b); Network Modified's Restore / Switch
(33b, "not implemented yet"); the saved cursor (43); the oldest actives
formats (N11b; decode 19a first); `↕` in Power (44); Priority 7 (39–42:
design commands such as AutoCpl / WillWrk, connecting networks,
Pricing / Performance / Control windows).

**Engineering unknowns, kept as the file has them (not asked):** preamble
23481 / 23483 and the three pairs at 36121 (file-formats 3.8); 36201 k = 12;
Out/Loss bytes past 519; the block's third count (0); what the status bar's
"Import" pane shows.

**Known minor bugs (not fixed at the checkpoint; no screen difference):**

* PS_B re-saved writes supply label `C\0` where Lode's file holds `C `
  (trailing space, +727 of 46.1's record): the reader strips the space, the
  writer then sees a changed label. 1 byte.
* NEW_T1 (written by an older app build) re-saves 3 bytes different in the
  Prices / Performance / Map Grid saved-with names (the current
  "Untitled\0 + tail" rule).
* AL003's pad/EQ tally: 34 more entries in the file than its actives
  (bank 4 value 0) — 8 bytes differ on re-save; unexplained.
* The "bucking power" flag (two supplies in one area, no stop between) is
  the app's own, not seen in Lode; it marks 18.1 red on PS_B and AL002.

**Not implemented on purpose:** Feedermaker Networks in Amplifier
Definition, Bridgers / Feedermakers tabs (unused), editing spec files,
most Tools / Global Change / Reports menu items (they say "not implemented
yet").

## Testing

* Private samples: `lodedata-samples.zip` unzipped in the repo root →
  `samples/…` (layout in `samples/README.md`). Without it every
  sample-reading test skips.
* `python -m pytest -q` (≈ 6½ min). Browser tests need Playwright with
  Chromium at `/opt/pw-browsers/chromium` (or `CHROMIUM_PATH`). Checkpoint:
  **261 passed, 0 failed, 0 skipped, 0 xfail** with the full pack.
* Regression, every network × every spec set (22 × 10 = 220):

      python tools/regression.py snapshot /tmp/after.json
      python tools/regression.py diff samples/regression-baseline.json /tmp/after.json

  The pack's `samples/regression-baseline.json` was taken on d1761f1:
  expected **"0 of 220 changed"**. After a change, every golden pair that
  moves must be the change intended (and evidenced); exploratory pairs move
  whenever a shared rule changes (60 V fallback, coupler signs…) and need
  no evidence, but must not error. All 220 open without an error; the
  golden pairs have no unresolved part but AL002's two type-5 supplies.

## Session start procedure

1. `git fetch origin claude/lode-data-reverse-engineer-65vgkc && git checkout claude/lode-data-reverse-engineer-65vgkc`;
   check HEAD is the SHA in `samples/HANDOFF-CHECKPOINT.txt` (or a later
   commit the user made since).
2. `unzip -o lodedata-samples.zip -d .` (repo root) → `samples/`.
3. Unzip `lodedata-evidence.zip` outside the repo (e.g. the scratchpad);
   `docs/EVIDENCE.md` names files by its folders.
4. `pip install -r requirements.txt pytest playwright` if missing; run
   `python -m pytest -q` → 261 passed.
5. Regression as above → 0 of 220 changed.
6. If both match the checkpoint, read QUESTIONS.md's open queue.
7. Continue with the user's new instruction, or the first item below.

## Next step

With no answer needed: **decode the oldest actives formats (2.20 / 3.0 /
5.0)** from the user's recording of NPG550's Actives window
(`2026-10-03_set/19a.mp4`, every tab; 19b–19f its Couplers and Taps
windows). Read NPG550's files from the regions' spec sets if the user
uploads them again (not in the samples pack). Then the open queue's
answers as they arrive, in its order.

## Where things are

| path | what |
|---|---|
| `tools/lodedata/obfuscation.py` | `.ntw` payload: `plain = nibswap((cipher - KEY[i % 100]) & 0xFF)` from offset 512 |
| `tools/lodedata/network.py` | `.ntw` reader |
| `tools/lodedata/writer.py` | `.ntw` writer over the opened file; preamble totals; `blank()` = Lode's empty file |
| `tools/lodedata/specs.py` | the five spec files, current and older layouts |
| `tools/lodedata/diff.py`, `cli.py` | `python -m lodedata diff a.ntw b.ntw` — which bytes a save changed |
| `tools/regression.py` | every network × every spec set check |
| `tools/spec_coverage.py` | what each spec file's bytes mean to the readers |
| `app/hfc/importer.py` | spec set → library; `design_from_ntw()` |
| `app/hfc/screen.py` | the engine: levels, Test list, brackets, boxes, powering, housings, pick |
| `app/hfc/exporter.py` | design → writer input |
| `app/hfc/entry.py` | typed codes: taps `4.23`, couplers `-8` / `3=`, Active IDs |
| `app/hfc/specwindow.py` | the Spec Edit windows' contents |
| `app/hfc/model.py`, `plant.py` | parts library; Design / Branch / Node |
| `app/api.py` | FastAPI; networks in SQLite for the run only |
| `app/web/` | the page: menus, grid, tip box, dialogs, keys, mouse |
| `desktop/` | the Windows program and its build |
| `tests/test_ntw.py`, `test_ntw_writer.py`, `test_screen.py` | AL004 screens, Parameters chains, saving |
| `tests/test_classic_specs.py`, `test_sn001.py`, `test_bullhead.py`, `test_al005.py`, `test_lg001.py` | the other golden networks |
| `tests/test_lode_saved.py` | Lode's own saves rebuilt through the API |
| `tests/test_keyed_regions.py`, `test_spec_windows.py`, `test_spec_sets.py` | regions' spec sets |
| `tests/test_import.py`, `test_entry.py` | importing and keying (KERMIT750 + WVBeck750) |
| `tests/test_ui.py` | the page in a real browser |

## Tooling notes

* Never `pkill -f` a pattern that appears in your own command line — it
  kills the shell. Stop servers by pid.
* `git add` of a gitignored path aborts the whole add; `-f` only for
  `samples/README.md`.
* Screen recordings: extract frames when the screen changes (plus a settled
  frame 0.5 s later) to read them. Read glyphs pixel by pixel when brackets
  matter (`<` pointed, `(` flat middle, `{` notched).
* The API can be driven without a browser: set `LODEDATA_DB` to a temp file,
  `import api`, then `api.edit_node(...)` etc. (`tests/test_lode_saved.py`).
