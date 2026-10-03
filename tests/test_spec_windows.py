"""The Spec Edit windows against what Lode shows: the user's recording of
NBERN1GHz's Actives window (2 Oct), WV750-2026's six Parameters tabs and
WVEXT862's Cables tab (set A2, 4c).  Skipped for the sets not in samples/.
"""
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "app"), str(ROOT / "tools")]

from hfc import specwindow as W                                      # noqa: E402

SAMPLES = Path(os.environ.get("LODEDATA_SAMPLES", ROOT / "samples"))


def _set(name):
    base = next((p.with_suffix("") for p in SAMPLES.rglob(f"{name}.par")), None) \
        if SAMPLES.is_dir() else None
    if base is None:
        pytest.skip(f"{name} not in samples")
    return base


def _read(base, ext):
    return (base.parent / (base.name + ext)).read_bytes()


def _tabs(window):
    return {t["name"]: t for t in window["tabs"]}


def _heads(grid):
    return [c["head"] for c in grid["cols"]]


def test_nbern_actives_window_as_recorded():
    base = _set("NBERN1GHz")
    w = W.actives_window(_read(base, ".atv"), _read(base, ".par"), "NBERN1GHz.atv")
    assert w["title"] == "Design Assistant Actives Specs - NBERN1GHz.atv"
    tabs = _tabs(w)
    assert len(tabs) == 28 and [t["name"] for t in w["tabs"]][:4] == \
        ["Actives", "Reserve Gain", "Power Steps", "Pads/EQs Bank 1"]
    a = tabs["Actives"]["grid"]
    assert _heads(a)[:8] == ["It...", "Active ID", "Part Number", "In - 1002", "In - 102",
                             "In - 85", "In - 5", "Out - 1002"]
    assert _heads(a)[-3:] == ["In - 750", "In - F4", "In - F5"]
    rows = a["rows"]
    assert len(rows) == 250
    assert rows[0] == ["1", "11", "FM332", "16.30", "11.30", "11.00", "11.00", "53.00", "0 Out",
                       "39.00", "0 Out", "39.00", "0 Out", "39.00", "0 Out", "1", "1", "1", "1",
                       "13.90", "0.00", "0.00"]
    # 11H-33H: an ID and no part number; 21H-33H put out 52.00
    assert [r[1:3] + [r[7]] for r in rows[6:12]] == [["11H", "", "0.00"]] + \
        [[i, "", "52.00"] for i in ("21H", "22H", "31H", "32H", "33H")]
    assert rows[13][1:3] + [rows[13][19]] == ["62", "", "8.80"]
    assert rows[16][3] == "99.00" and rows[16][9] == "36.00"          # 65
    assert rows[22][2:7] + rows[22][15:19] == ["NC4000 1x1", "0.00", "0.00", "11.00", "11.00",
                                               "4", "4", "4", "4"]
    steps = tabs["Power Steps"]["grid"]
    assert _heads(steps)[-2:] == ["Voltage 8", "Amperage 8"]
    assert steps["rows"][0][2:16] == ["45.00", "0.73", "50.00", "0.63", "60.00", "0.47", "70.00",
                                      "0.38", "80.00", "0.33", "90.00", "0.32", "0.00", "0.00"]
    bank = tabs["Pads/EQs Bank 1"]["sub"]
    assert [s["name"] for s in bank] == ["Forward Pad", "Return Pad", "Forward EQ", "Return EQ"]
    assert [s["prefix"] for s in bank] == ["NPB-", "NPB-", "CE-120-", "MEQ-85-"]
    assert bank[0]["grid"]["rows"][21] == ["22", "BAD", "21.00"]
    assert _heads(bank[2]["grid"]) == ["It...", "Part Number", "Loss - 1002", "Loss - 102",
                                       "Loss - 750", "Loss - F4", "Loss - F5", "Loss - F6"]
    assert bank[2]["grid"]["rows"][0][:4] == ["1", "CS10", "9.40", "1.60"]
    assert bank[3]["grid"]["rows"][12][:4] == ["13", "Flag", "1.00", "13.00"]
    eq9 = tabs["EQs Bank 9"]
    assert eq9["prefix"].strip() == "2&4 PORT"
    assert eq9["grid"]["rows"][0] == ["1", "CS12", "14.30", "0.40", "9.50", "0.00", "0.00", "0.00",
                                      "0.30", "0.10", "0.00", "0.00"]
    assert tabs["EQs Bank 10"]["grid"]["rows"][11][:5] == ["12", "EQ14", "0.80", "12.20", "1.70"]
    inline = tabs["Inline EQs"]["grid"]["rows"]
    assert len(inline) == 24 and inline[0][:8] == ["1", "EQ", "FFE-8-85/RP+8P", "1.60", "8.90",
                                                   "9.70", "9.00", "2.90"]
    assert inline[8][1:4] == ["Q9", "FFE-8-120-FB", "2.90"]
    casc = tabs["Custom Cascading"]["grid"]
    assert _heads(casc)[-1] == "Casc. 19"
    assert casc["rows"][18][:9] == ["19", "67", "", "0 - No", "0 - Include", "0 - Invalid",
                                    "0 - Invalid", "0 - Invalid", "1 - Valid"]
    assert casc["rows"][22][3:6] == ["1 - Yes", "1 - Exclude", "1 - Valid"]
    config = tabs["Configuration Table"]["grid"]["rows"]
    assert config[0][:4] == ["1", "1/0", "FM332", "11"] and config[1][:4] == ["2", "1/1", "FM332", ""]
    assert config[248][1:4] == ["32/0", "NC2000 Line Powered", "80"]


def test_wv750_plug_ins_are_the_configuration_tables():
    """68N ... 68B (FM902B) take plug-ins 8 9 10 11 16: NEW FMB, UPGRADE FMB,
    MOVE FMB, SWAP LE TO FMB, SWAP FMT TO FMB; 78S (FML332) 4, SWAP BR TO LE."""
    base = _set("WV750-2026")
    tabs = _tabs(W.actives_window(_read(base, ".atv"), _read(base, ".par"), "WV750-2026.atv"))
    names = {int(r[0]): r[1] for r in tabs["Plug-Ins"]["grid"]["rows"]}
    rows = {r[1]: r for r in tabs["Configuration Table"]["grid"]["rows"]}
    fm902b = [rows[f"20/{k}"] for k in range(1, 6)]
    assert [r[3] for r in fm902b] == ["68N", "68U", "68M", "68S", "68B"]
    assert [names[int(r[4])] for r in fm902b] == ["NEW FMB", "UPGRADE FMB", "MOVE FMB",
                                                  "SWAP LE TO FMB", "SWAP FMT TO FMB"]
    assert names[int(rows["30/4"][4])] == "SWAP BR TO LE" and rows["30/4"][3] == "78S"


def test_wv750_parameters_window_as_its_six_tabs():
    base = _set("WV750-2026")
    w = W.parameters_window(_read(base, ".par"), "WV750-2026.par")
    assert [t["name"] for t in w["tabs"]] == ["General Parameters", "System Levels", "Tap Selection",
                                              "Powering", "Underground Housings", "Frequencies"]
    v = w["values"]
    assert (v["distance_units"], v["signal_display"], v["strand_series"]) == ("Ftg", "dBmV", [0, 2, 3, 4])
    assert (v["max_crossover"], v["max_return_crossover"], v["eq_placement"]) == ("3.00", "99.00", "EQ+")
    assert v["misc_parts"] == {"hth_connectors": "HOUS TO HOUS", "splices": "SGMC", "terminators": "GTRM"}
    assert (v["max_le_cascade"], v["allow_over_equalization"], v["tap_margin"]) == (3, True, "0.50")
    assert v["forward_windows"][:3] == [["750", "12.00"], ["54", "16.00"], ["550", "0.00"]]
    assert v["return_windows"] == [["40", "16.00"], ["5", "16.00"], ["R3", "0.00"], ["R4", "0.00"]]
    assert v["level_cols"][:6] == ["Level", "Min. 750", "Min. 54", "Max. 40", "Max. 5", "Min. 550"]
    assert v["level_rows"][1][:6] == ["1", "19.00", "12.00", "45.00", "45.00", "17.00"]
    assert v["max_amps_through"] == {"power_inserter": "16.00", "amplifier": "15.00",
                                     "bridger_port": "15.00", "coupler": "15.00",
                                     "line_extender": "15.00", "tap": "12.00"}
    assert v["supplies"][3] == [4, "NEW APLHA 90V PS", "90.00", "15.00", "85.00"]
    assert v["housings"][-1] == [5, "TV-1024", 27]
    assert v["forward"][:3] == [["750", True], ["54", True], ["550", False]]
    assert v["eq_selection"] == {"fwd_high": "750", "fwd_low": "54", "ret_high": "40", "ret_low": "5"}


def test_wvext862_cables_tab_as_4c():
    base = _set("WVEXT862")
    w = W.cables_window(_read(base, ".cbl"), _read(base, ".par"), "WVEXT862.cbl")
    g = _tabs(w)["Cables"]["grid"]
    assert _heads(g) == ["It...", "Cable ID", "Part Number", "Loop Res./1000", "870/100", "54/100",
                         "550/100", "F4/100", "F5/100", "F6/100", "40/100", "5/100", "R3/100", "R4/100"]
    assert len(g["rows"]) == 100
    assert g["rows"][0] == ["1", "0", "EX P3 500 A", "1.72", "2.340000", "0.540000", "1.820000",
                            "0.000000", "0.000000", "0.000000", "0.460000", "0.160000",
                            "0.000000", "0.000000"]
    assert g["rows"][29][:4] == ["30", "29", "", "0.00"]
    assert g["rows"][37][2:5] == ["NEW RG-6 U", "40.47", "6.100000"]
