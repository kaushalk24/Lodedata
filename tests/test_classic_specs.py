"""Older spec files and the branches fed from a tap's port.

WVEXT862 was saved by Lode 4 (.cbl/.cpr 5.1, .atv 6.0, .tap 3.0, .par 2.10,
"Design 4.22"), and the older AL004 design was saved against it.  Lode 12
opens the pair; the user's screenshots of it are what these check:
columns 870 54 40 5 and 550 after cplr[branch], 11.16 drawn "117+" and 11.18
"104+", and the WIFI OMNI (86) fed from 11.18's tap port reading 19.90 18.38
36.31 35.43 (550: 19.55) in, 48.50 34.00 22.00 22.00 (0.00) out.

Skipped unless samples/AL004-WVEXT862 holds AL004.ntw and WVEXT862.*.
"""
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))
sys.path.insert(0, str(ROOT / "tools"))

from hfc.importer import design_from_ntw                          # noqa: E402
from hfc.exporter import export_ntw                               # noqa: E402
from hfc.screen import build                                      # noqa: E402
from lodedata.specs import load_spec_set                          # noqa: E402

SAMPLES = Path(os.environ.get("LODEDATA_SAMPLES", ROOT / "samples"))
PAIR = SAMPLES / "AL004-WVEXT862"
NTW, SPEC = PAIR / "AL004.ntw", PAIR / "WVEXT862"

pytestmark = pytest.mark.skipif(
    not NTW.exists() or not SPEC.with_suffix(".par").exists(),
    reason="the older AL004 + WVEXT862 not in samples/AL004-WVEXT862")


def test_the_older_spec_files_read_as_lode_shows_them():
    s = load_spec_set(SPEC)
    assert s.frequencies == {"F1": "870", "F2": "54", "F3": "550", "R1": "40", "R2": "5"}
    assert s.levels[:2] == [[19.0, 10.0, 45.0, 45.0], [22.0, 13.0, 45.0, 45.0]]
    # F3 = 550: Min 15 / 18 on levels 0 / 1, tap window 12
    assert [lv[0] for lv in s.parameters["extra_levels"][:2]] == [15.0, 18.0]
    assert s.parameters["tap_windows"]["F3"] == 12.0
    assert [x.name for x in s.supplies] == ["NEW STANDBY", "EXISTING STDBY", "EXISTING  90v"]

    cable = next(c for c in s.cables if c.name == "EX P3 500 A")
    assert cable.index == 0 and round(cable.loop_resistance_ohm_per_ft * 1000, 2) == 1.72
    assert cable.forward_coeffs[:3] == [2.34, 0.54, 1.82]
    assert len(s.cables) == 39
    # Series/Colors: cables 0-19 red on series 0, 2, 3 and 5, 0,200,0 on 1
    # and 4; 20-39 the other way about, red on 4 only; 6-9 untouched, 0,255,0
    red, green, bright = "#ff0000", "#00c800", "#00ff00"
    by_index = {c.index: c for c in s.cables}
    assert [c for c, _ in by_index[5].series] == [red, green, red, red, green, red] + [bright] * 4
    assert [c for c, _ in by_index[38].series] == [green] * 4 + [red, green] + [bright] * 4
    assert [n for _, n in by_index[5].series] == ["New Build", "Dual Cable", "Rebuild", "Overlash",
                                                  "Upgrade", "Dual New Build", "", "", "", ""]

    three_way = next(c for c in s.couplers if c.name == "MGLSH-3F")
    assert three_way.tap_legs == 2 and three_way.code == 3.0

    by_id = {a.active_id: a for a in s.actives}
    assert list(by_id)[:12] == ["11", "21", "22", "31", "32", "33",
                                "11H", "21H", "22H", "31H", "32H", "33H"]
    omni = by_id["86"]
    assert (omni.name, omni.index) == ("WIFI OMNI", 38)
    assert omni.input_levels == [0.0, -5.0, 22.0, 22.0]
    assert omni.output_levels == [48.5, 34.0, 47.0, 47.0]
    assert omni.banks == [3, 3, 3, 3]
    # In and Out at F3 (+127, +151): the LEs 14.1 in, 43.0 out; the bridgers
    # 10.1, 43.0; the NC4000 0, 41.1; the WIFI OMNI 0, 0
    assert omni.f3_levels == [0.0, 0.0]
    assert by_id["11"].f3_levels == [14.1, 43.0] and by_id["61"].f3_levels == [10.1, 43.0]
    assert by_id["64"].f3_levels == [0.0, 41.1]
    # Custom Cascading, the tab row by row as the user's set A2 shows it:
    # Cust. Casc. (bit 0), Exclude (bit 1), the Casc. k marked Valid (bit k + 1)
    def tab(a):
        c = a.cascading
        return ("Yes" if c & 1 else "No", "Exclude" if c >> 1 & 1 else "Include",
                [k for k in range(1, 15) if c >> (k + 1) & 1])
    lode = {"11": ("Yes", "Include", [1, 2, 3, 4, 5]), "21": ("Yes", "Include", [1, 2, 3, 4, 5]),
            "22": ("Yes", "Include", [2, 3, 4, 5, 6]), "31": ("Yes", "Include", [1, 2, 3, 4, 5]),
            "32": ("Yes", "Include", [2, 3, 4, 5, 6]), "33": ("Yes", "Include", [3, 4, 5, 6, 7]),
            "11H": ("Yes", "Include", [1, 2, 3, 4, 5]), "21H": ("Yes", "Include", [1, 2, 3, 4, 5]),
            "22H": ("Yes", "Include", [2, 3, 4, 5, 6]), "31H": ("Yes", "Include", [1, 2, 3, 4, 5]),
            "32H": ("Yes", "Include", [2, 3, 4, 5, 6]), "33H": ("Yes", "Include", [3, 4, 5, 6, 7]),
            "61": ("Yes", "Include", [1, 2, 3, 4]), "63": ("No", "Include", []),
            "64": ("No", "Include", []), "70": ("Yes", "Include", [1]),
            "85": ("No", "Include", []), "86": ("No", "Include", []), "88": ("No", "Include", []),
            "41": ("Yes", "Include", [1, 2, 3, 4, 5, 6, 7])}
    assert {i: tab(a) for i, a in by_id.items()} == lode
    assert (by_id["88"].name, by_id["88"].index) == ("FML1G7J ALC LE", 40)
    assert (by_id["41"].name, by_id["41"].index) == ("FNB99DJxx6x6x1", 42)

    taps = {t.slot: t for t in s.taps}
    assert (taps[35].tap_id, taps[35].ports[4].part) == (117, "AN-WIFI-417")
    assert (taps[41].tap_id, taps[41].ports[2].part) == (104, "AN-WIFI-204")
    assert taps[41].ports[2].tap_value == [4.2, 3.3, 3.3, 3.2]
    assert [q.name for q in s.inline] == ["LEQ-PEA-8", "LEQ-PEA-0", "EXIST SPLICE", "NEW SPLICE"]
    # an in-line device's fifth loss is F3: LEQ-PEA-8 takes 3.1 at 550
    assert (s.inline[0].losses, s.inline[0].f3) == ([1.8, 8.3, 1.2, 0.7], 3.1)
    assert len(s.banks) == 4 and s.banks[3].prefixes[0].strip() == "NODE-"

    p = s.parameters
    assert p["strand_series"] == [0, 2, 3, 4]
    assert p["points"]["amplifier"] == 16 and p["points"]["power_supply"] == 30
    assert p["housings"][0] == {"number": 1, "part": "TV-60", "min_points": 4}
    assert p["power_interpolation"] == "constant_wattage"
    assert p["transformers"] == []


def test_the_cable_numbers_in_their_series_colours():
    # the user's set A2 (4a, 4b): 25.2's 505 and 5.28's 515 red (series 5 of
    # cables 5 and 15), 5.9-5.22's 438 red (series 4 of cable 38), 404 405
    # 410 414 415 0,200,0; the box names the series
    d, _ = design_from_ntw(NTW.read_bytes(), SPEC)
    rows = {(r.branch, r.node): r for r in build(d).rows if not r.end}
    got = {k: (rows[k].cab, rows[k].cab_color, rows[k].cab_series)
           for k in ((25, 1), (25, 2), (25, 3), (5, 8), (5, 9), (5, 23), (5, 28), (5, 29))}
    assert got == {(25, 1): (404, "#00c800", "Upgrade"), (25, 2): (505, "#ff0000", "Dual New Build"),
                   (25, 3): (405, "#00c800", "Upgrade"), (5, 8): (410, "#00c800", "Upgrade"),
                   (5, 9): (438, "#ff0000", "Upgrade"), (5, 23): (414, "#00c800", "Upgrade"),
                   (5, 28): (515, "#ff0000", "Dual New Build"), (5, 29): (415, "#00c800", "Upgrade")}


def test_the_older_design_opens_with_nothing_unresolved():
    d, rep = design_from_ntw(NTW.read_bytes(), SPEC)
    assert rep["unresolved"] == [] and rep["branches"] == 44


def _from_tap(d, branch, node):
    return next(b for b in d.branches.values()
                if (b.parent_branch, b.parent_node) == (branch, node))


def test_a_branch_fed_from_a_tap_port():
    d, _ = design_from_ntw(NTW.read_bytes(), SPEC)
    scr = build(d)
    assert scr.frequencies == [870.0, 54.0, 40.0, 5.0] and scr.extra_frequencies == [550.0]
    rows = {(r.branch, r.node): r for r in scr.rows if not r.end}
    assert rows[(11, 16)].taps == ["117+"] and rows[(11, 16)].couplers == []
    assert rows[(11, 18)].taps == ["104+"] and rows[(11, 18)].couplers == []

    wifi = _from_tap(d, 11, 18)
    assert rows[(11, 18)].tap_branches == [wifi.number]
    first = rows[(wifi.number, 1)]
    assert first.amp == "86" and first.amp_label == "AL004.2"
    assert first.as_dict()["levels"] == [19.90, 18.38, 36.31, 35.43]
    assert first.as_dict()["extra_levels"] == [19.55]
    end = next(r for r in scr.rows if r.end and r.branch == wifi.number)
    assert end.as_dict()["levels"] == [48.50, 34.00, 22.00, 22.00]
    assert end.as_dict()["extra_levels"] == [0.00]
    info = first.amp_info
    assert (info["fwd_eq"], info["ret_eq"]) == ("VOID", "VOID")
    assert [info[k] for k in ("aerial_prev", "aerial_start", "total_split",
                              "total_prev", "total_start")] == [393, 3313, 6, 393, 3313]
    # Cascade Position 4, as Lode's box (28 Sep): the node 1, AL00416 2,
    # AL00419 3.  (The 29 Sep box of the WIFI OMNI from 11.16 read 3 --
    # asked again)
    assert info["cascade"] == 4 and info["homes_down"] == 0


def test_the_older_design_saves_back_as_it_came():
    src = NTW.read_bytes()
    d, _ = design_from_ntw(src, SPEC)
    data, report = export_ntw(d, src)
    assert data == src and report["not_written"] == []


# Lode's Test Results for the older AL004, all 94 errors in the window's
# order (the user's screenshots, SHINSTON2 5a-5c): the tap checks at 870,
# 54, 550, 40 and 5 MHz, the crossovers (WVEXT862's Max. Crossover is 0.00),
# the actives' inputs and outputs with their pads and EQs, the Custom
# Cascading line and the EQ slope.  A crossover is printed seven wide,
# "Crossover of    3.85", as Lode's pixels show (the user: match it)
LODE_TESTS = [
    "Tap(54)  1.24 below min at 3.1.", "Tap(550)  0.74 below min at 3.1.",
    "Tap(870)  2.18 below min at 3.3.", "Tap(550)  0.32 below min at 3.3.",
    "Tap(870) 10.72 below min at 3.5.", "Tap(550)  6.52 below min at 3.5.", "Crossover of    3.85 at 3.5.",
    "Tap(870) 12.74 below min at 3.6.", "Tap(550)  5.64 below min at 3.6.",
    "Tap(5)  2.79 below window at 3.6.", "Crossover of   11.22 at 3.6.",
    "870 input   10.97 to LE at 4.13.", "54 input   24.90 to LE at 4.13.",
    "870 input    9.17 to LE at 5.12.", "54 input   24.50 to LE at 5.12.",
    "Tap(870)  4.12 below min at 5.29.", "Tap(550)  0.50 below min at 5.29.",
    "Tap(5)  1.23 below window at 5.29.", "Crossover of    2.01 at 5.29.", "Tap(5)  0.53 below window at 6.7.",
    "Tap(40)  1.73 above max at 6.10.", "Tap(40)  2.04 above max at 7.7.",
    "Tap(5)  0.62 above max at 7.7.", "Tap(870)  8.05 below min at 9.16.",
    "Tap(54)  8.09 below min at 9.16.", "Tap(550)  6.52 below min at 9.16.",
    "Tap(40)  7.94 above max at 9.16.",
    "Tap(5)  5.18 above max at 9.16.", "Tap(870) 10.30 below min at 9.17.",
    "Tap(54)  6.55 below min at 9.17.", "Tap(550)  7.67 below min at 9.17.",
    "Tap(40)  6.26 above max at 9.17.",
    "Tap(5)  3.05 above max at 9.17.", "Tap(870) 11.12 below min at 9.18.",
    "Tap(54)  5.21 below min at 9.18.", "Tap(550)  7.97 below min at 9.18.",
    "Tap(40)  4.83 above max at 9.18.",
    "Tap(5)  1.21 above max at 9.18.", "Tap(870)  5.03 below min at 10.2.",
    "Tap(54)  1.54 below min at 10.2.", "Tap(550)  3.48 below min at 10.2.",
    "Tap(40)  1.19 above max at 10.2.",
    "Tap(5)  1.04 below window at 10.7.", "Tap(870)  1.16 below min at 11.16.",
    "Tap(54)  0.27 below min at 11.16.", "Tap(550)  0.22 below min at 11.16.",
    "Tap(40)  0.12 above max at 11.16.",
    "Tap(5)  0.58 below window at 11.18.", "Tap(54)  0.04 below min at 12.3.",
    "Tap(5)  0.50 below window at 13.3.", "Tap(870)  5.32 over window at 14.1.",
    "Tap(550)  1.77 over window at 14.1.",
    "Tap(40)  3.12 below window at 14.1.", "Tap(5)  3.61 below window at 14.1.",
    "Tap(870) 17.67 below min at 15.3.", "Tap(54)  6.00 below min at 15.3.",
    "Tap(550) 13.13 below min at 15.3.",
    "Tap(40)  5.35 above max at 15.3.", "Tap(5)  0.70 above max at 15.3.",
    "Crossover of    2.67 at 15.3.",
    "Tap(870) 23.18 below min at 15.4.", "Tap(54)  6.12 below min at 15.4.",
    "Tap(550) 16.98 below min at 15.4.",
    "Tap(40)  5.23 above max at 15.4.", "Tap(5)  0.08 above max at 15.4.",
    "Crossover of    8.06 at 15.4.",
    "Tap(870)  6.12 below min at 16.1.", "Tap(54)  4.92 below min at 16.1.",
    "Tap(550)  4.96 below min at 16.1.",
    "Tap(40)  4.68 above max at 16.1.", "Tap(5)  2.18 above max at 16.1.",
    "Tap(40)  2.42 below window at 16.7.", "Tap(5)  2.92 below window at 16.7.",
    "Tap(5)  0.36 below window at 19.10.", "870 input   30.41 to LE at 19.11.",
    "Tap(5)  1.20 below window at 23.5.",
    "Tap(5)  1.36 below window at 23.10.", "Tap(5)  1.31 below window at 23.16.",
    "LE  11/5 before/0 after at 23.17.",
    "870 input   22.64 to LE at 25.3.", "54 input   18.03 to LE at 25.3.",
    "550 input   20.98 to LE at 25.3.", "40 output   36.64 from LE at 25.3.",
    "5 output   35.32 from LE at 25.3.",
    "870 input   11.12 to LE at 28.1.", "54 input   16.24 to LE at 28.1.",
    "Tap(870)  1.20 over window at 28.2.", "Tap(870)  3.38 over window at 29.3.",
    "Tap(870)  0.54 over window at 39.5.", "Tap(870)  2.00 over window at 40.6.",
    "Fslope too low to equalize at 43.1.", "Rslope too low to equalize at 43.1.",
    "Fslope too low to equalize at 44.1.", "Rslope too low to equalize at 44.1."]


def test_the_test_list_is_lodes():
    d, _ = design_from_ntw(NTW.read_bytes(), SPEC)
    tests = build(d).tests
    # every line, 15.4's three too: its 870 port, -4.191, is -4.19 on the
    # screen but -4.18 to the Test (as_tested), so 23.18, 16.98 and 8.06
    # (Lode's list of 1 Oct, and again of 2 Oct from AL004_SETA)
    assert [m for _, m in tests] == LODE_TESTS
    # the Tap(550) lines' colours, as Lode's list shows them: yellow within
    # the 0.50 tap margin (5.29's 0.50 too) and for the window, red beyond
    # (3.1, 3.3, 3.5, 3.6, 5.29, 9.16, 9.17, 9.18, 10.2, 11.16, 14.1, 15.3, 15.4, 16.1)
    assert [v for v, m in tests if m.startswith("Tap(550)")] == [
        "red", "yellow", "red", "red", "yellow", "red", "red", "red", "red", "yellow", "yellow",
        "red", "red", "red"]
    # the actives' lines are all red in Lode's list
    assert {v for v, m in tests if " LE " in m or m.startswith("LE ")} == {"red"}


def test_the_actives_as_lode_shows_them():
    # Cascade Position: WVEXT862's node (NC4000 here, HLN 3842 NODE in the
    # user's copy) is position 1 -- its Custom Cascading has no position 0 --
    # so every active reads one more than on AL004 (the user's set A boxes,
    # 1 Oct, every figure)
    d, _ = design_from_ntw(NTW.read_bytes(), SPEC)
    scr = build(d)
    rows = {(r.branch, r.node): r for r in scr.rows if not r.end}
    keys = ("name", "type", "fwd_pad", "fwd_eq", "ret_pad", "ret_eq", "aerial_prev",
            "aerial_start", "total_split", "total_prev", "total_start", "cascade", "supply",
            "homes_down")
    lode = {(6, 1): ["AL00415", "FNB99DJxx6x6x1", "6", "SCS3", "3", "2", 886, 886, 0, 886, 886, 2,
                     "AL004A", 7],
            (11, 10): ["AL00419", "FNB99DJxx6x6x1", "6", "0", "2", "2", 893, 2920, 652, 893, 2920,
                       3, "AL004A", 45],
            (25, 3): ["AL00429", "NL15DDJL THM", "10", "5", "8", "2", 74, 2994, 385, 459, 3379, 4,
                      "AL004A", 16],
            (23, 17): ["AL00431", "NL15DDJL THM", "10", "8", "11", "2", 591, 4786, 591, 591, 4786,
                       6, "AL004A", 3]}
    for k, want in lode.items():
        assert [rows[k].amp_info[x] for x in keys] == want, k
    assert [rows[(1, 1)].amp_info[x] for x in ("fwd_pad", "cascade", "supply", "homes_down")] \
        == [".", 1, "AL004A", 181]
    assert rows[(4, 13)].amp_info["cascade"] == 2          # SHINSTON3 1c
    # an input or output the active misses is drawn red, with its ID: 4.13's
    # 10.97 and 24.90 (SHINSTON3 1c), all of 25.3 (set A 3g)
    a, b = rows[(4, 13)].as_dict(), rows[(25, 3)].as_dict()
    assert (a["level_severity"], a["extra_severity"], a["amp_severity"]) == \
        (["red", "red", "", ""], [""], "red")
    assert (b["level_severity"], b["extra_severity"], b["amp_severity"]) == \
        (["red"] * 4, ["red"], "red")
    # the cascade line leaves 23.17's ID green (set A 3h)
    assert rows[(23, 17)].as_dict()["amp_severity"] == ""


def test_branches_6_and_7_as_lode_shows_them():
    # the user's screenshots: Q1 (LEQ-PEA-8, the in-line equaliser) reads EQ
    # at 6.9 and 7.6, Q5 stays Q5; the red taps and ports as Lode draws them
    from hfc.screen import as_shown
    d, _ = design_from_ntw(NTW.read_bytes(), SPEC)
    scr = build(d)
    want = {
        6: [(19.74, 18.22, 35.75, 33.97), (48.50, 34.00, 21.00, 21.00), (46.08, 33.43, 21.46, 21.17),
            (43.91, 32.94, 21.88, 21.32), (41.40, 32.36, 22.36, 21.49), (39.57, 31.94, 22.71, 21.61),
            (35.81, 31.09, 23.43, 21.87), (33.21, 30.03, 24.44, 22.94), (30.10, 29.32, 25.03, 23.15),
            (28.29, 21.01, 39.23, 36.85), (24.49, 18.11, 42.13, 39.75)],
        7: [(48.50, 34.00, 21.00, 21.00), (46.80, 33.30, 21.70, 21.90), (43.68, 32.57, 22.29, 22.12),
            (39.21, 31.09, 23.66, 23.05), (34.75, 29.56, 25.08, 24.16), (30.91, 28.22, 26.34, 25.32),
            (29.10, 19.91, 39.54, 38.02), (25.30, 17.01, 42.44, 40.92)]}
    for b, levels in want.items():
        rows = [r for r in scr.rows if r.branch == b]
        assert [tuple(as_shown(r.levels[f]) for f in scr.frequencies) for r in rows] == levels
    rows = {(r.branch, r.node): r for r in scr.rows if not r.end}
    assert [rows[k].amp for k in ((6, 3), (6, 9), (7, 3), (7, 6))] == ["Q5", "EQ", "Q5", "EQ"]
    assert rows[(6, 9)].amp_name == rows[(7, 6)].amp_name == "LEQ-PEA-8"
    assert [rows[k].taps for k in ((6, 7), (6, 9), (6, 10), (7, 6), (7, 7))] == \
        [["/14/"], ["{43}"], ["/ 8/"], ["{42}"], ["/ 8/"]]
    assert rows[(6, 7)].tap_severity == ["yellow"] and rows[(6, 10)].tap_severity == ["red"]
    ends = {b: [r for r in scr.rows if r.branch == b and r.end][0] for b in (6, 7)}
    assert [as_shown(v) for v in ends[6].port_levels] == [19.19, 13.51, 46.73, 44.45]
    assert [as_shown(v) for v in ends[7].port_levels] == [20.00, 12.41, 47.04, 45.62]
    assert ends[6].port_severity == ["", "", "red", ""] and ends[7].port_severity == ["", "", "red", "red"]


def test_the_couplers_are_drawn_as_lode_draws_them():
    # branch 4 (SHINSTON3 1c) and branch 11 (28 Sep 18:17), read glyph by
    # glyph: 4.14 is 3[11]{12} here -- 11's 105 is 4.16's span, but 4.16 is
    # on 100 and 4.14, a 0-ft line, on 410
    d, _ = design_from_ntw(NTW.read_bytes(), SPEC)
    scr = build(d)
    cpl = lambda b: [c for r in scr.rows if r.branch == b and not r.end for c in r.couplers]
    assert cpl(4) == ["12{6}", "100[9]", "3[11]{12}"]
    assert cpl(11) == ["2[19]", "1(21)", "16(22)", "100[23]", "3[24](27)", "8[25]"]
    assert cpl(6) == ["100[7]"] and cpl(7) == ["112(8)"]
    # set A (5a-5c, 3g): 16.4 8{17} -- 17 runs 169 ft along 16.3's span,
    # past the power stop on the coupler's own line; 9.14 2{14} on 404
    # cable, mileage, as long as 9.14's own span
    assert cpl(16) == ["8{17}"] and cpl(25) == ["2[26]"]
    assert cpl(9) == ["108<10>", "100{13}", "2{14}", "2[15]"]
    assert cpl(5) == ["12[28]", "100{39}", "100{32}", "2[37]", "12(38)"]


def test_the_550_column_is_lodes():
    # WVEXT862's third forward frequency, F3 = 550, drawn after the two
    # cplr[branch] columns: every value on the user's screenshots of branches
    # 4 (SHINSTON3 1c), 6 and 7 (4a, 4b), 11 (28 Sep, SHINSTON2 5e/5f) and the
    # two tap-fed branches (43.1, 44.1), end lines included.  Cables, couplers
    # and taps carry it in slot 2 of their loss blocks, an in-line device in
    # its fifth loss (6.9 and 7.6's EQ), an active its Out at F3
    d, _ = design_from_ntw(NTW.read_bytes(), SPEC)
    scr = build(d)
    lode = {
        4: [35.20, 33.28, 31.61, 30.11, 26.58, 24.79, 23.12, 21.88, 20.02, 18.21, 16.29, 15.59,
            14.37, 43.00, 38.40],
        6: [18.11, 43.00, 41.11, 39.44, 37.50, 36.09, 33.19, 31.24, 28.84, 25.73, 22.33],
        7: [43.00, 42.00, 39.57, 36.05, 32.59, 29.67, 26.56, 23.16],
        11: [35.10, 29.40, 27.71, 27.46, 24.87, 22.98, 21.75, 20.64, 19.09, 18.18, 43.00, 38.40,
             37.05, 34.85, 32.58, 32.58, 29.56, 23.46, 0.00],
        43: [14.67, 0.00], 44: [19.55, 0.00]}
    for b, want in lode.items():
        rows = [r.as_dict() for r in scr.rows if r.branch == b][:len(want)]
        assert [r["extra_levels"][0] for r in rows] == want, b
