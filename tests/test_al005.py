"""AL005 on its own spec set, Beckley750 (an older Parameters layout, file
version 7.0): Lode's Parameters window, all six tabs (n9a-n9g, 4 Oct), and
its Test list, all 51 lines (n10a/n10b).  Skipped unless they are under
samples/.
"""
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "app"), str(ROOT / "tools")]

from hfc import specwindow as SW                                     # noqa: E402
from hfc.importer import design_from_ntw                              # noqa: E402
from hfc.screen import build                                          # noqa: E402

SAMPLES = Path(os.environ.get("LODEDATA_SAMPLES", ROOT / "samples"))


def _find(name):
    p = next(SAMPLES.rglob(name), None) if SAMPLES.is_dir() else None
    if p is None:
        pytest.skip(f"{name} not in samples")
    return p


def test_beckley750_parameters_window_as_its_six_tabs():
    par = _find("Beckley750.par")
    v = SW.parameters_window(par.read_bytes(), par.name)["values"]
    # General Parameters (n9a)
    assert (v["distance_units"], v["signal_display"], v["show_count_types"]) == ("Ftg", "dBmV", False)
    assert v["strand_series"] == [0, 2, 4]
    assert set(v["niu"].values()) == {"0.00"}
    assert (v["max_crossover"], v["max_return_crossover"], v["eq_placement"]) == ("3.00", "99.00", "EQ-")
    assert v["replacement_cables"] == {"backfeed": 0, "fwd_feed": 0}
    assert v["misc_parts"] == {"hth_connectors": "H-H CONNECTORS", "splices": "SPLICE",
                               "terminators": "TERMINATOR"}
    assert (v["lines_per_form"], v["max_tap_cascade"], v["max_le_cascade"]) == (0, 0, 3)
    assert v["allow_over_equalization"] is True
    # System Levels (n9b)
    assert v["tap_margin"] == "0.50"
    assert v["forward_windows"] == [["750", "8.50"], ["54", "12.00"], ["550", "10.50"],
                                    ["F4", "0.00"], ["F5", "0.00"], ["F6", "0.00"]]
    assert v["return_windows"] == [["40", "99.00"], ["5", "99.00"], ["R3", "0.00"], ["R4", "0.00"]]
    rows = v["level_rows"]
    assert len(rows) == 16
    assert rows[0][:6] == ["0", "17.00", "10.00", "45.00", "45.00", "15.00"]
    assert rows[1][:6] == ["1", "20.00", "13.00", "45.00", "45.00", "18.00"]
    assert rows[4][:6] == ["4", "10.00", "10.00", "45.00", "45.00", "10.00"]
    assert all(set(r[1:]) == {"0.00"} for k, r in enumerate(rows) if k not in (0, 1, 4))
    assert all(set(r[6:]) == {"0.00"} for r in rows)
    # Tap Selection (n9c, n9d)
    assert (v["optimization"], v["enforce_tap_window"], v["enforce_tap_tilt"],
            v["flag_hi_lo_tilt"]) == ("OP-", False, False, False)
    assert v["ports_by_homes"] == [[h, 2 if h <= 2 else 4 if h <= 4 else 8 if h <= 8 else h + h % 2]
                                   for h in range(1, 33)]
    assert v["tap_type_by_ports"] == [[n, 2 if n <= 2 else 4 if n <= 4 else 8] for n in range(1, 33)]
    # Powering (n9e): 25 supply rows, though the older file keeps 15
    assert (v["power_interpolation"], v["overvoltage_check"], v["pre_load"]) == (
        "constant_wattage", False, False)
    assert v["max_amps_through"] == {"power_inserter": "15.00", "amplifier": "15.00",
                                     "bridger_port": "0.00", "coupler": "15.00",
                                     "line_extender": "15.00", "tap": "12.00"}
    assert v["transformers"] == [[k, "", "0.00"] for k in range(1, 9)]
    assert v["supplies"][:5] == [[1, "NEW STANDBY", "60.00", "15.00", "85.00"],
                                 [2, "EXISTING STDBY", "60.00", "15.00", "90.00"],
                                 [3, "MOVED STDBY", "60.00", "15.00", "85.00"],
                                 [4, "NEW 90V 15A", "90.00", "15.00", "85.00"],
                                 [5, "EX 90V 15A", "90.00", "15.00", "90.00"]]
    assert v["supplies"][5:] == [[k, "", "0.00", "0.00", "0.00"] for k in range(6, 26)]
    # Underground Housings (n9f)
    assert v["points"] == {"amplifier": 16, "line_extender": 11, "tap": 5, "tap_8_port": 5,
                           "coupler": 5, "power_supply": 30, "equalizer": 5}
    assert v["housings"] == [[1, "TV-60", 4], [2, "TV-80", 6], [3, "TV-104", 11],
                             [4, "TV-106", 17], [5, "TV-1024", 27]]
    # Frequencies (n9g)
    assert v["forward"] == [["750", True], ["54", True], ["550", True], ["F4", False],
                            ["F5", False], ["F6", False]]
    assert v["return"] == [["40", True], ["5", True], ["R3", False], ["R4", False]]
    assert v["eq_selection"] == {"fwd_high": "750", "fwd_low": "54", "ret_high": "40", "ret_low": "5"}


LODE_TESTS = [
    ("yellow", "Fslope too low to equalize at 1.1."), ("yellow", "Rslope too low to equalize at 1.1."),
    ("red", "Tap(750)  7.64 below min at 1.34."), ("red", "Tap(550)  5.20 below min at 1.34."),
    ("red", "Tap(750)  7.75 below min at 1.35."), ("red", "Tap(550)  4.64 below min at 1.35."),
    ("yellow", "Crossover of    3.41 at 1.35."),
    ("red", "Tap(750) 10.09 below min at 1.36."), ("red", "Tap(550)  5.96 below min at 1.36."),
    ("yellow", "Crossover of    6.92 at 1.36."),
    ("yellow", "Tap(750)  2.20 over window at 2.2."), ("yellow", "Tap(550)  0.25 over window at 2.2."),
    ("red", "Tap(54)  1.62 below min at 5.7."), ("red", "Tap(550)  0.77 below min at 5.7."),
    ("yellow", "Tap(750)  0.50 below min at 6.2."), ("yellow", "Tap(550)  0.27 below min at 6.2."),
    ("red", "Tap(750)  9.71 below min at 8.2."), ("red", "Tap(54)  0.95 below min at 8.2."),
    ("red", "Tap(550)  8.17 below min at 8.2."), ("red", "Tap(40)  1.35 above max at 8.2."),
    ("red", "750 input    4.47 to LE at 8.6."), ("red", "54 input   20.74 to LE at 8.6."),
    ("yellow", "Tap(750)  3.43 over window at 12.32."), ("yellow", "Tap(550)  0.25 over window at 12.32."),
    ("yellow", "Tap(750)  1.50 over window at 13.1."),
    ("yellow", "Tap(750) 15.60 over window at 13.12."), ("yellow", "Tap(54)  0.10 over window at 13.12."),
    ("yellow", "Tap(550) 10.15 over window at 13.12."),
    ("yellow", "Tap(750)  1.50 over window at 14.5."), ("yellow", "Tap(750)  2.35 over window at 17.2."),
    ("red", "Tap(750)  1.20 below min at 18.2."), ("red", "Tap(54)  6.10 below min at 18.2."),
    ("red", "Tap(550)  2.60 below min at 18.2."), ("red", "Tap(40)  7.10 above max at 18.2."),
    ("red", "Tap(5)  7.20 above max at 18.2."),
    ("red", "Tap(750)  4.05 below min at 18.4."), ("red", "Tap(54)  2.49 below min at 18.4."),
    ("red", "Tap(550)  4.10 below min at 18.4."), ("red", "Tap(40)  3.30 above max at 18.4."),
    ("red", "Tap(5)  2.19 above max at 18.4."),
    ("red", "Tap(750)  4.06 below min at 18.5."), ("red", "Tap(54)  6.59 below min at 18.5."),
    ("red", "Tap(550)  5.29 below min at 18.5."),
    ("red", "Tap(750)  2.33 below min at 18.6."), ("red", "Tap(54)  1.76 below min at 18.6."),
    ("red", "Tap(550)  2.64 below min at 18.6."),
    ("red", "Tap(40)  0.60 above max at 19.2."), ("yellow", "Tap(5)  0.20 above max at 19.2."),
    ("yellow", "Tap(750)  0.22 over window at 21.1."),
    ("yellow", "Tap(750)  0.40 below min at 24.4."), ("red", "Tap(550)  0.89 below min at 24.4.")]


def test_al005_test_list_is_lodes():
    """Every line, its colour and its place (n10a/n10b: "51 Errors")."""
    ntw = _find("AL005.ntw")
    par = _find("Beckley750.par")
    d, _ = design_from_ntw(ntw.read_bytes(), par.with_suffix(""))
    assert build(d).tests == LODE_TESTS
