# Handoff — read this first in a new session

## The goal

Rebuild the Lode Data **Design Assistant** 12.11 (HFC/CATV network design
software) as a web app that looks and behaves the same:

* key in a network from scratch with the same keyboard-driven screens
* open a real `.ntw` with its spec set
* "upgrade" a network by attaching a different spec set

The user is a Lode Data designer. What they want:

* Match the real program exactly; don't guess. When evidence is missing,
  ask them for a specific screenshot.
* Don't overengineer.
* Work through open questions **one at a time**.

## Repository and git

* Repo `kaushalk24/Lodedata`, branch `claude/lode-data-reverse-engineer-65vgkc`.
* Commit with `-c user.email=kaushall2424@gmail.com -c user.name="Kaushal"`.
  End messages with the Co-Authored-By / Claude-Session trailers the session
  gives you.
* Push with `git push -u origin claude/lode-data-reverse-engineer-65vgkc`.
  No pull requests unless asked.

## Run and test

* Windows: double-click `run.bat`. Linux: `./run.sh`. Both start
  `uvicorn api:app --app-dir app` on port 8000.
* `python -m pytest -q` → 104 tests. The browser tests use Playwright with
  `/opt/pw-browsers/chromium`.
* The sample-based tests **skip unless the sample files are present**:
  * `samples/AL004-WV750/AL004.ntw`
  * `samples/AL004-WV750/WV750-2026.{par,atv,tap,cpr,cbl}` — the user's
    `aloo4_apec.zip`
  * optionally `samples/partest/paratest.par`, `s1.par` … `s8.par` and
    `v1.par` … `v10.par`: the user's test copy of the .par and two chains of
    saves changing one setting each
  * optionally the older `samples/KERMIT750-2026.*`, `samples/WVBeck750.*` and
    `samples/AL00{2,3,4,5}.ntw` from the earlier OneDrive zips
* `samples/` is gitignored; a new session needs these files uploaded again.

## Where things are

| path | what |
|---|---|
| `tools/lodedata/obfuscation.py` | .ntw decryption: `plain = nibswap((cipher - KEY[i%100]) & 0xFF)` from offset 512 |
| `tools/lodedata/network.py` | .ntw layout: branch records, node records, all fields |
| `tools/lodedata/specs.py` | .cbl .cpr .atv (+ in-line Q table) .tap (454-byte rows) .par (levels, supplies, frequencies) |
| `app/hfc/importer.py` | spec set → Library; `design_from_ntw()` |
| `app/hfc/screen.py` | the engine: Design levels, tap checks, end lines, coupler brackets, powering, amp info |
| `app/hfc/model.py`, `plant.py` | parts library; Design / Branch / Node |
| `app/api.py` | FastAPI; `POST /api/import/ntw` takes the .ntw plus spec files |
| `app/web/` | the UI: menus as in 12.11, screen menus, grid, info box, Project Settings |
| `tests/test_ntw.py` | AL004 checked against the user's screenshots |
| `docs/file-formats.md` | every decoded format, with how each was confirmed |
| `docs/open-questions.md` | **the queue of open questions** |
| `docs/lode-data-manual-notes.md` | notes from the vendor manual |

## Where it stands

AL004 imports with every reference resolved: 45 branches, 275 nodes. The
Design screen matches every screenshot number on branches 1, 4, 6, 9, 11, 18,
19, 21 and 22, including:

* end-of-branch lines and tap port outputs
* tap colours
* the coupler column
* the info boxes (tap, coupler preview, power supply, amplifier)

Power currents and volts match on all 29 lines of branch 4.

## Rules learned from the user's screens

* Levels shown are after the span on that line, before its equipment.
* Order of equipment on a line: amp (replaces the level) → in-line Qn → taps
  (cascaded) → couplers.
* Leg designations:
  * `8[2]`: the downstream leg is the high (thru) leg.
  * `8-[2]` (keyed `8-` or `-8`): the thru leg goes to the branch.
  * `3=`: the thru leg goes to the second branch.
* Power:
  * current is constant-wattage, interpolated between the power steps
  * voltage drop = current × span resistance, the span's resistance being
    whole milliohms, truncated (feet × µΩ/ft // 1000)
  * a node's current is the current in the span on its supply side
  * a power stop cuts the span leading into its node
* Coupler brackets (nothing in the file stores them): `<n>` if the branch has
  no footage on non-1xx cable and its first span matches the nearest span
  behind or ahead of the coupler on the parent branch (what BkFeed/FwdFd
  copy), otherwise `[n]`. Confirmed by experiment (11.1 changed 105 → 106
  turned 4.14 into `3-[11]<12>`) and by 6.1's `100[7]`.
* Cable ID 0 is a real cable (index 0), not "none".
* "Mileage" for the bracket rule = footage on a series ticked under
  Parameters → Strand/Trench Types (WV750: 000 200 300 400).
* Taps: 8-port is `<n>` on the Design screen, `{n}` in the preview box.
* Tap test (Test, screen menu 5): below min / above max (yellow within the
  tap margin, red beyond), over window (forward above min + window) and
  below window (return below max − window), both yellow, crossover (> Max.
  Crossover, yellow); levels compared to the hundredth. AL004's 37-line list
  is reproduced exactly (`tests/test_ntw.py`).
* Levels print to the hundredth, halves up: AL004 34.7 shows 21.115 as
  21.12 and 37.865 as 37.87 (`as_shown` in `app/hfc/screen.py`).
* Keys: in Design the digits are the screen menu; `0` Alters (tap prompt
  "Enter desired tap {# of ports}.{ID #}: [home] for list", Home = Select
  Tap), `5` Test, `/` expanded display, Esc closes. Entry types directly.

## Next step

Questions 1, 2, 3, 5 and the Parameters file are closed. Waiting on the user
for the open points in items 7 and 8 of `docs/open-questions.md` (the
expanded display's open points in item 7,
the Alter prompts on other columns, Select Tap's tabs). Then item 4, Pads/EQ.
