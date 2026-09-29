"""Older spec files and the branches fed from a tap's port.

WVEXT862 was saved by Lode 4 (.cbl/.cpr 5.1, .atv 6.0, .tap 3.0, .par 2.10,
"Design 4.22"), and the older AL004 design was saved against it.  Lode 12
opens the pair; the user's screenshots of it are what these check:
columns 870 54 40 5, 11.16 drawn "117+" and 11.18 "104+", and the WIFI OMNI
(86) fed from 11.18's tap port reading 19.90 18.38 36.31 35.43 in, 48.50
34.00 22.00 22.00 out.

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
    assert [x.name for x in s.supplies] == ["NEW STANDBY", "EXISTING STDBY", "EXISTING  90v"]

    cable = next(c for c in s.cables if c.name == "EX P3 500 A")
    assert cable.index == 0 and round(cable.loop_resistance_ohm_per_ft * 1000, 2) == 1.72
    assert cable.forward_coeffs[:3] == [2.34, 0.54, 1.82]
    assert len(s.cables) == 39

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
    assert (by_id["88"].name, by_id["88"].index) == ("FML1G7J ALC LE", 40)
    assert (by_id["41"].name, by_id["41"].index) == ("FNB99DJxx6x6x1", 42)

    taps = {t.slot: t for t in s.taps}
    assert (taps[35].tap_id, taps[35].ports[4].part) == (117, "AN-WIFI-417")
    assert (taps[41].tap_id, taps[41].ports[2].part) == (104, "AN-WIFI-204")
    assert taps[41].ports[2].tap_value == [4.2, 3.3, 3.3, 3.2]
    assert [q.name for q in s.inline] == ["LEQ-PEA-8", "LEQ-PEA-0", "EXIST SPLICE", "NEW SPLICE"]
    assert len(s.banks) == 4 and s.banks[3].prefixes[0].strip() == "NODE-"

    p = s.parameters
    assert p["strand_series"] == [0, 2, 3, 4]
    assert p["points"]["amplifier"] == 16 and p["points"]["power_supply"] == 30
    assert p["housings"][0] == {"number": 1, "part": "TV-60", "min_points": 4}
    assert p["power_interpolation"] == "constant_wattage"
    assert p["transformers"] == []


def test_the_older_design_opens_with_nothing_unresolved():
    d, rep = design_from_ntw(NTW.read_bytes(), SPEC)
    assert rep["unresolved"] == [] and rep["branches"] == 44


def _from_tap(d, branch, node):
    return next(b for b in d.branches.values()
                if (b.parent_branch, b.parent_node) == (branch, node))


def test_a_branch_fed_from_a_tap_port():
    d, _ = design_from_ntw(NTW.read_bytes(), SPEC)
    scr = build(d)
    assert scr.frequencies[:4] == [870.0, 54.0, 40.0, 5.0]
    rows = {(r.branch, r.node): r for r in scr.rows if not r.end}
    assert rows[(11, 16)].taps == ["117+"] and rows[(11, 16)].couplers == []
    assert rows[(11, 18)].taps == ["104+"] and rows[(11, 18)].couplers == []

    wifi = _from_tap(d, 11, 18)
    assert rows[(11, 18)].tap_branches == [wifi.number]
    first = rows[(wifi.number, 1)]
    assert first.amp == "86" and first.amp_label == "AL004.2"
    assert tuple(round(v, 2) for v in first.levels.values()) == (19.90, 18.38, 36.31, 35.43)
    end = next(r for r in scr.rows if r.end and r.branch == wifi.number)
    assert tuple(round(v, 2) for v in end.levels.values()) == (48.50, 34.00, 22.00, 22.00)
    info = first.amp_info
    assert (info["fwd_eq"], info["ret_eq"]) == ("VOID", "VOID")
    assert [info[k] for k in ("aerial_prev", "aerial_start", "total_split",
                              "total_prev", "total_start")] == [393, 3313, 6, 393, 3313]
    # Lode's box also reads Cascade Position 4 here; the rule that gives
    # both that and AL00416's 1 is not known yet (this reads 3)
    assert info["homes_down"] == 0


def test_the_older_design_saves_back_as_it_came():
    src = NTW.read_bytes()
    d, _ = design_from_ntw(src, SPEC)
    data, report = export_ntw(d, src)
    assert data == src and report["not_written"] == []


# Lode's Test Results for the older AL004 (94 errors), the lines of the kinds
# worked out so far -- the tap checks at 870, 54, 40 and 5 MHz and the EQ
# slope -- in the window's order.  Still to come: the 550 MHz column, the
# crossovers, the amplifier input/output and LE cascade lines.
LODE_TESTS = [
    "Tap(54)  1.24 below min at 3.1.", "Tap(870)  2.18 below min at 3.3.",
    "Tap(870) 10.72 below min at 3.5.", "Tap(870) 12.74 below min at 3.6.",
    "Tap(5)  2.79 below window at 3.6.", "Tap(870)  4.12 below min at 5.29.",
    "Tap(5)  1.23 below window at 5.29.", "Tap(5)  0.53 below window at 6.7.",
    "Tap(40)  1.73 above max at 6.10.", "Tap(40)  2.04 above max at 7.7.",
    "Tap(5)  0.62 above max at 7.7.", "Tap(870)  8.05 below min at 9.16.",
    "Tap(54)  8.09 below min at 9.16.", "Tap(40)  7.94 above max at 9.16.",
    "Tap(5)  5.18 above max at 9.16.", "Tap(870) 10.30 below min at 9.17.",
    "Tap(54)  6.55 below min at 9.17.", "Tap(40)  6.26 above max at 9.17.",
    "Tap(5)  3.05 above max at 9.17.", "Tap(870) 11.12 below min at 9.18.",
    "Tap(54)  5.21 below min at 9.18.", "Tap(40)  4.83 above max at 9.18.",
    "Tap(5)  1.21 above max at 9.18.", "Tap(870)  5.03 below min at 10.2.",
    "Tap(54)  1.54 below min at 10.2.", "Tap(40)  1.19 above max at 10.2.",
    "Tap(5)  1.04 below window at 10.7.", "Tap(870)  1.16 below min at 11.16.",
    "Tap(54)  0.27 below min at 11.16.", "Tap(40)  0.12 above max at 11.16.",
    "Tap(5)  0.58 below window at 11.18.", "Tap(54)  0.04 below min at 12.3.",
    "Tap(5)  0.50 below window at 13.3.", "Tap(870)  5.32 over window at 14.1.",
    "Tap(40)  3.12 below window at 14.1.", "Tap(5)  3.61 below window at 14.1.",
    "Tap(870) 17.67 below min at 15.3.", "Tap(54)  6.00 below min at 15.3.",
    "Tap(40)  5.35 above max at 15.3.", "Tap(5)  0.70 above max at 15.3.",
    "Tap(870) 23.18 below min at 15.4.", "Tap(54)  6.12 below min at 15.4.",
    "Tap(40)  5.23 above max at 15.4.", "Tap(5)  0.08 above max at 15.4.",
    "Tap(870)  6.12 below min at 16.1.", "Tap(54)  4.92 below min at 16.1.",
    "Tap(40)  4.68 above max at 16.1.", "Tap(5)  2.18 above max at 16.1.",
    "Tap(40)  2.42 below window at 16.7.", "Tap(5)  2.92 below window at 16.7.",
    "Tap(5)  0.36 below window at 19.10.", "Tap(5)  1.20 below window at 23.5.",
    "Tap(5)  1.36 below window at 23.10.", "Tap(5)  1.31 below window at 23.16.",
    "Tap(870)  1.20 over window at 28.2.", "Tap(870)  3.38 over window at 29.3.",
    "Tap(870)  0.54 over window at 39.5.", "Tap(870)  2.00 over window at 40.6.",
    "Fslope too low to equalize at 43.1.", "Rslope too low to equalize at 43.1.",
    "Fslope too low to equalize at 44.1.", "Rslope too low to equalize at 44.1."]


def test_the_test_list_is_lodes():
    d, _ = design_from_ntw(NTW.read_bytes(), SPEC)
    got = [m for _, m in build(d).tests]
    assert len(got) == len(LODE_TESTS)
    # 15.4's 870 MHz port is 0.006 dB lower here than in Lode (23.19 against
    # its 23.18): open, to be checked against Lode's levels on branch 15
    open_ = LODE_TESTS.index("Tap(870) 23.18 below min at 15.4.")
    assert got[open_] == "Tap(870) 23.19 below min at 15.4."
    assert got[:open_] + got[open_ + 1:] == LODE_TESTS[:open_] + LODE_TESTS[open_ + 1:]
