"""A real design read back and recalculated, checked against its own screens.

AL004 with the WV750-2026 spec set, against what Lode Data shows for it: the
Design screen (levels at 750/54/40/5) and the Power screen (volts and amps) of
branch 4, and the Design screen of branch 3.  Values were read off photographs
of the screen, so they carry the screen's two decimals.
"""
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))
sys.path.insert(0, str(ROOT / "tools"))

from hfc.importer import design_from_ntw, library_from_spec_set   # noqa: E402
from hfc.screen import build                                      # noqa: E402
from lodedata.obfuscation import open_ntw                         # noqa: E402
from lodedata.network import read_network                         # noqa: E402
from lodedata.specs import read_taps, read_actives, load_spec_set, read_parameters  # noqa: E402

SAMPLES = Path(os.environ.get("LODEDATA_SAMPLES", ROOT / "samples"))
PAIR = SAMPLES / "AL004-WV750"
NTW, SPEC = PAIR / "AL004.ntw", PAIR / "WV750-2026"

pytestmark = pytest.mark.skipif(
    not NTW.exists() or not SPEC.with_suffix(".tap").exists(),
    reason="AL004 + WV750-2026 not in samples/AL004-WV750")

# branch 4, Design screen: 750, 54, 40, 5 on each of its 29 lines
B4_LEVELS = [
    (41.96, 36.24, 18.48, 17.52), (39.66, 35.67, 18.96, 17.69),
    (37.68, 35.17, 19.37, 17.84), (35.89, 34.72, 19.75, 17.97),
    (31.18, 33.04, 21.33, 19.25), (29.05, 32.51, 21.78, 19.40),
    (27.05, 32.01, 22.20, 19.55), (25.57, 31.64, 22.51, 19.66),
    (23.35, 31.09, 22.97, 19.83), (21.19, 30.55, 23.42, 19.99),
    (18.89, 29.97, 23.90, 20.16), (18.07, 29.77, 24.08, 20.22),
    (16.60, 29.40, 24.38, 20.33), (49.00, 38.00, 21.00, 21.00),
    (40.50, 30.70, 28.30, 28.50), (34.15, 26.21, 32.73, 32.52),
    (32.13, 25.71, 33.15, 32.67), (31.88, 25.46, 33.45, 33.17),
    (28.23, 24.04, 34.79, 34.09), (25.96, 23.48, 35.27, 34.26),
    (24.50, 23.11, 35.58, 34.37), (23.18, 22.78, 35.85, 34.46),
    (21.33, 22.32, 36.24, 34.60), (20.23, 22.05, 36.47, 34.68),
    (49.00, 38.00, 21.00, 21.00), (41.90, 33.50, 25.44, 25.12),
    (36.30, 31.03, 27.82, 27.22), (32.68, 29.74, 29.02, 28.36),
    (25.64, 25.71, 32.98, 32.02),
]
B4_FTG = [476, 155, 134, 121, 156, 144, 135, 100, 150, 146, 155, 56, 99, 0, 0,
          105, 136, 0, 112, 153, 99, 89, 125, 74, 0, 74, 125, 89, 99]
# branch 4, Power screen
B4_VOLTS = [86.24, 86.44, 86.62, 86.78, 87.07, 87.35, 87.61, 87.80, 88.09,
            88.36, 88.66, 88.77, 88.95, 88.95, 88.95, 89.41, 90.00, 90.00,
            89.76, 89.42, 89.21, 89.02, 88.75, 88.59, 88.59, 88.53, 88.53,
            88.53, 88.53]
B4_AMPS = [1.74, 1.74, 1.74, 2.53, 2.53, 2.53, 2.53, 2.53, 2.53, 2.53, 2.53,
           2.53, 4.92, 4.92, 5.74, 5.74, 8.60, 2.86, 2.86, 2.86, 2.86, 2.86,
           2.86, 2.86, 0.41, 0.41, 0.00, 0.00, 0.00]
B3_LEVELS = [
    (45.63, 37.16, 17.72, 17.25), (40.81, 35.48, 19.27, 18.41),
    (38.30, 34.85, 19.80, 18.60), (32.42, 32.91, 21.58, 19.84),
    (27.74, 31.73, 22.57, 20.18), (20.41, 29.48, 24.62, 21.61),
]


@pytest.fixture(scope="module")
def net():
    h, p = open_ntw(NTW)
    return read_network(h + p)


@pytest.fixture(scope="module")
def imported():
    return design_from_ntw(NTW, SPEC)


@pytest.fixture(scope="module")
def screen(imported):
    return build(imported[0])


def _rows(screen, branch):
    return [r for r in screen.rows if r.branch == branch and not r.end]


# ------------------------------------------------------------- file layout
def test_the_whole_network_is_read(net):
    assert net.name == "AL004"
    assert net.spec_names[0] == "WV750-2026"
    assert len(net.branches) == 45
    assert net.node_count == 275
    # the Ripple node's info box: "Housecounts downstream 181"
    assert sum(n.hc for b in net.branches.values() for n in b.nodes) == 181


def test_branch_4_footage_cable_and_houses(net):
    b4 = net.branches[4]
    assert [n.ftg for n in b4.nodes] == B4_FTG
    assert [n.cable for n in b4.nodes] == [410] * 25 + [100] * 4
    assert [n.hc for n in b4.nodes][26:] == [3, 3, 1]


def test_branch_4_couplers_amplifiers_and_supply(net):
    b4 = net.branches[4]
    started = {i: n.branches for i, n in enumerate(b4.nodes, 1) if n.branches}
    assert started == {4: [6], 13: [9], 14: [11, 12], 15: [17], 17: [18],
                       18: [19], 24: [20], 25: [21, 24], 26: [22]}
    labels = {i: n.label for i, n in enumerate(b4.nodes, 1) if n.label}
    assert labels == {13: "AL00416", 24: "AL00419"}
    assert net.branches[11].through                  # "3-<11><12>"
    assert net.branches[18].nodes[0].supply == "A"


def test_every_reference_resolves_against_its_spec_set(imported):
    design, report = imported
    assert report["unresolved"] == []
    b4 = design.branches[4]
    lib = design.library
    coupler = {n.seq: [(c.coupler_id, c.branch) for c in n.couplers]
               for n in b4.nodes if n.couplers}
    assert coupler[4] == [(12, 6)]
    assert coupler[13] == [(100, 9)]
    assert coupler[14] == [(3, 11), (3, 12)]
    assert coupler[17] == [(1, 18)]
    assert coupler[25] == [(3, 21), (3, 24)]
    assert b4.nodes[12].amp == "61" and b4.nodes[23].amp == "61"
    assert design.branches[1].nodes[0].amp == "70"
    taps = [(lib.taps[t.part_id].tap_id, t.ports) for n in b4.nodes[26:] for t in n.taps]
    assert taps == [(17, 4), (11, 4), (4, 2)]


# ------------------------------------------------------------------ specs
def test_tap_rows_carry_one_tap_id_across_port_counts():
    taps = {t.slot: t for t in read_taps(SPEC.with_suffix(".tap").read_bytes())}
    assert taps[3].tap_id == 20 and taps[3].ports[4].part == "MGT-2420C-USP"
    assert taps[4].tap_id == 18 and taps[4].ports[8].part == "MGT-2818C-USP"
    assert taps[11].tap_id == 4 and taps[11].ports[2].part == "MGT-2204C-USP"


def test_active_ids_come_from_the_configuration_table():
    acts = {a.index: a for a in read_actives(SPEC.with_suffix(".atv").read_bytes())}
    assert acts[13].active_id == "61" and acts[13].name.startswith("BRIDGER")
    assert acts[22].active_id == "70" and acts[22].name == "Ripple"
    assert acts[7].active_id == "11H"
    assert "68N" in acts[20].config_ids


def test_supplies_and_frequencies_come_from_the_parameters_file():
    spec = load_spec_set(SPEC)
    assert spec.frequencies == {"F1": "750", "F2": "54", "R1": "40", "R2": "5"}
    s3 = next(s for s in spec.supplies if s.type_id == 3)
    assert (s3.volts, s3.amps) == (90.0, 15.0)


def test_parameters_read_back_as_the_spec_edit_tabs_show_them():
    # Spec Edit -> Parameters on WV750-2026.par, all six tabs
    spec = load_spec_set(SPEC)
    p = spec.parameters
    # General Parameters
    assert p["strand_series"] == [0, 2, 3, 4]
    assert p["misc_parts"] == {"hth_connectors": "HOUS TO HOUS", "splices": "SGMC",
                               "terminators": "GTRM"}
    assert (p["max_crossover"], p["max_return_crossover"]) == (3.0, 99.0)
    # System Levels
    assert spec.tap_margin == 0.5
    assert spec.levels[:2] == [[17.0, 10.0, 45.0, 45.0], [19.0, 12.0, 45.0, 45.0]]
    assert [lv[0] for lv in p["extra_levels"][:2]] == [15.0, 17.0]   # Min. 550
    assert {k: v for k, v in p["tap_windows"].items() if v} == \
        {"F1": 12.0, "F2": 16.0, "R1": 16.0, "R2": 16.0}
    # Tap Selection
    assert [p["tap_type_by_ports"][n] for n in range(1, 8)] == [2, 2, 4, 4, 8, 8, 8]
    assert all(p["ports_by_homes"][n] == n for n in range(1, 27))
    # Powering
    assert p["power_interpolation"] == "constant_wattage"
    assert list(p["max_amps_through"].values()) == [16.0, 15.0, 15.0, 15.0, 15.0, 12.0]
    assert [(s.type_id, s.name, s.volts, s.amps, s.rating) for s in spec.supplies] == [
        (1, "EXISTING STDBY", 60.0, 15.0, 85.0), (2, "EXISTING STDBY", 60.0, 15.0, 90.0),
        (3, "EXISTING  90v", 90.0, 15.0, 90.0), (4, "NEW APLHA 90V PS", 90.0, 15.0, 85.0)]
    # Underground Housings
    assert [(h["part"], h["min_points"]) for h in p["housings"]] == [
        ("TV-60", 4), ("TV-80", 6), ("TV-104", 11), ("TV-106", 17), ("TV-1024", 27)]
    assert p["points"] == {"equalizer": 5, "amplifier": 16, "line_extender": 11, "tap": 5,
                           "tap_8_port": 5, "coupler": 5, "power_supply": 30}
    assert (p["max_le_cascade"], p["max_tap_cascade"], p["lines_per_form"]) == (3, 0, 0)
    assert p["allow_over_equalization"] and not p["overvoltage_check"]
    # Frequencies: Freqs. for Active EQ Selection
    assert p["eq_selection"] == {"fwd_high": "750", "fwd_low": "54", "ret_high": "40", "ret_low": "5"}


PARTEST = SAMPLES / "partest" / "paratest.par"


@pytest.mark.skipif(not PARTEST.exists(), reason="the user's test copy of the .par")
def test_a_test_copy_with_distinct_values_places_every_field():
    # WV750-2026.par re-saved by the user with one distinct value per field
    p = read_parameters(PARTEST.read_bytes())
    assert p["points"] == {"equalizer": 9, "amplifier": 16, "line_extender": 11, "tap": 6,
                           "tap_8_port": 7, "coupler": 8, "power_supply": 30}
    assert list(p["niu"].values()) == [1.0, 2.0, 3.0, 4.0, 5.0]
    assert (p["max_crossover"], p["max_return_crossover"]) == (3.25, 99.0)
    assert (p["max_le_cascade"], p["max_tap_cascade"], p["lines_per_form"]) == (4, 6, 44)
    assert p["replacement_cables"] == {"backfeed": 7, "fwd_feed": 9}
    assert not p["allow_over_equalization"] and p["overvoltage_check"]
    assert p["power_interpolation"] == "linear"
    assert list(p["max_amps_through"].values()) == [16.0, 15.1, 15.2, 15.3, 15.4, 12.0]
    assert p["tilts"][0] == [1.1, 2.2, 3.3, 4.4] and p["tilts"][1] == [0.0] * 4
    assert (p["distance_units"], p["signal_display"], p["eq_placement"], p["optimization"]) \
        == ("m", "dBuV", "EQe", "OFf")
    assert p["show_count_types"] and p["enforce_tap_window"] and p["flag_hi_lo_tilt"]
    assert p["strand_series"] == [0, 2, 3, 4, 8]


# The user then undid one setting per save, s1 ... s8: each file must differ
# from the one before in exactly that setting.
CHAIN = [("distance_units", "m", "Ftg"), ("signal_display", "dBuV", "dBmV"),
         ("show_count_types", True, False), ("strand_series", [0, 2, 3, 4, 8], [0, 2, 3, 4]),
         ("eq_placement", "EQe", "EQ+"), ("optimization", "OFf", "OP-"),
         ("enforce_tap_window", True, False), ("flag_hi_lo_tilt", True, False)]


@pytest.mark.skipif(not (PARTEST.parent / "s8.par").exists(), reason="the user's save chain")
def test_each_save_in_the_chain_changes_one_setting():
    before = read_parameters(PARTEST.read_bytes())
    for k, (key, was, now) in enumerate(CHAIN, start=1):
        after = read_parameters((PARTEST.parent / f"s{k}.par").read_bytes())
        changed = [f for f in after if after[f] != before[f]]
        assert changed == [key] and (before[key], after[key]) == (was, now), f"s{k}"
        before = after


# A second chain from s8: v1 ... v9, one step each, except v1 (three radio
# groups whose bytes were already known) and v7 (distinct numbers).
V_CHAIN = [
    {"distance_units": ("Ftg", "dM"), "eq_placement": ("EQ+", "EQ-"), "optimization": ("OP-", "OP+")},
    {"strand_series": ([0, 2, 3, 4], [0, 2, 3, 4, 6])},
    {"strand_series": ([0, 2, 3, 4, 6], [0, 2, 3, 4, 6, 7])},
    {"strand_series": ([0, 2, 3, 4, 6, 7], [0, 2, 3, 4, 6, 7, 9])},
    {"enforce_tap_tilt": (False, True)},
    {"pre_load": (False, True)},
    {"extra_levels": None, "transformer_volts": None},
    {"eq_selection": ({"fwd_high": "750", "fwd_low": "54", "ret_high": "40", "ret_low": "5"},
                      {"fwd_high": "54", "fwd_low": "750", "ret_high": "40", "ret_low": "5"})},
    {"eq_selection": ({"fwd_high": "54", "fwd_low": "750", "ret_high": "40", "ret_low": "5"},
                      {"fwd_high": "54", "fwd_low": "750", "ret_high": "5", "ret_low": "40"})},
]


@pytest.mark.skipif(not (PARTEST.parent / "v9.par").exists(), reason="the user's second save chain")
def test_the_second_save_chain_places_the_rest():
    before = read_parameters((PARTEST.parent / "s8.par").read_bytes())
    for k, want in enumerate(V_CHAIN, start=1):
        after = read_parameters((PARTEST.parent / f"v{k}.par").read_bytes())
        assert sorted(f for f in after if after[f] != before[f]) == sorted(want), f"v{k}"
        for key, pair in want.items():
            if pair:
                assert (before[key], after[key]) == pair, f"v{k} {key}"
        before = after
    # v7: level 0 Min F3..F6, Max R3, R4 and transformers 1-3
    assert before["extra_levels"][0] == [15.0, 1.25, 2.25, 3.35, 4.25, 5.25]
    assert before["transformer_volts"][:4] == [60.5, 70.25, 80.75, 0.0]


# ------------------------------------------------------------ calculations
def test_design_levels_match_the_screen(screen):
    rows = _rows(screen, 4)
    assert len(rows) == 29
    for r, want in zip(rows, B4_LEVELS):
        got = tuple(round(r.levels[f], 2) for f in screen.frequencies)
        assert got == want, f"4.{r.node}: {got} != {want}"
    for r, want in zip(_rows(screen, 3), B3_LEVELS):
        got = tuple(round(r.levels[f], 2) for f in screen.frequencies)
        assert got == want, f"3.{r.node}: {got} != {want}"


def test_the_node_shows_no_input_and_its_ports_the_node_output(screen):
    feeder = _rows(screen, 1)
    assert [round(v, 2) for v in feeder[0].levels.values()] == [0.0] * 4
    assert tuple(round(feeder[1].levels[f], 2) for f in screen.frequencies) == \
        (49.0, 38.0, 17.0, 17.0)


def test_tap_display_uses_the_tap_id_and_port_brackets(screen):
    assert [r.taps for r in _rows(screen, 4)][26:] == [["[17]"], ["[11]"], ["/ 4/"]]
    assert [t for r in _rows(screen, 3) for t in r.taps] == ["[20]", "/17/", "/14/", "/ 8/"]


def test_taps_out_of_the_system_levels_are_flagged_as_on_screen(screen):
    # branch 3: /14/ (lv 1, needs 19) and /8/ (lv 0, needs 17) are red on the
    # Design screen, and so is the 11.31 port output under the last one
    sev = {t: s for r in _rows(screen, 3) for t, s in zip(r.taps, r.tap_severity)}
    assert sev == {"[20]": "", "/17/": "", "/14/": "red", "/ 8/": "red"}
    end = next(r for r in screen.rows if r.branch == 3 and r.end)
    assert [round(v, 2) for v in end.port_levels] == [11.31, 21.98, 32.12, 29.21]
    assert end.port_severity[0] == "red"
    assert [round(end.levels[f], 2) for f in screen.frequencies] == [16.61, 26.58, 27.52, 24.51]


def test_a_terminating_tap_ends_the_line(screen):
    end = next(r for r in screen.rows if r.branch == 4 and r.end)
    assert [round(end.levels[f], 2) for f in screen.frequencies] == [0.0] * 4
    assert [round(v, 2) for v in end.port_levels] == [21.44, 22.41, 36.28, 35.32]


def test_power_screen_currents(screen):
    rows = _rows(screen, 4)
    got = [round(r.current, 2) for r in rows]
    off = [(r.node, g, w) for r, g, w in zip(rows, got, B4_AMPS) if abs(g - w) > 0.011]
    assert not off


def test_power_screen_volts(screen):
    # every volt exactly as shown, which needs each span's resistance
    # truncated to whole milliohms
    assert [round(r.volts, 2) for r in _rows(screen, 4)] == B4_VOLTS
    # the map tag of AL00415 (6.1, at 4.4's pole): 86.78 V, 0.79 A
    tag = next(r for r in screen.rows if (r.branch, r.node) == (6, 1))
    assert (round(tag.volts, 2), round(tag.current, 2)) == (86.78, 0.79)


def test_each_supply_carries_its_area(screen):
    load = {r.supply_label: round(r.current, 2) for r in screen.rows if r.supply}
    assert set(load) == {"A", "B", "C"}
    assert abs(load["A"] - 8.60) <= 0.011


# -------------------------------------------------- the branch screenshots
# From Design screen screenshots of AL004 (branch 6, and the branch previews
# the info box shows with the cursor on a coupler): 750, 54, 40, 5.
SHOTS = {
    6: [(23.89, 22.72, 31.75, 29.97), (46.76, 37.43, 21.46, 21.17),
        (44.76, 36.94, 21.88, 21.32), (42.46, 36.36, 22.36, 21.49),
        (40.77, 35.94, 22.71, 21.61), (37.31, 35.09, 23.43, 21.87),
        (34.80, 34.03, 24.44, 22.94), (31.94, 33.32, 25.03, 23.15),
        (30.73, 32.31, 39.23, 36.85), (26.93, 29.41, 42.13, 39.75)],
    9: [(49.00, 38.00, 21.00, 21.00), (46.40, 36.60, 22.40, 22.60),
        (41.96, 35.49, 23.33, 22.93), (39.99, 35.00, 23.74, 23.08),
        (37.31, 34.33, 24.30, 23.28), (34.93, 33.73, 24.80, 23.45),
        (32.71, 33.18, 25.27, 23.62), (30.65, 32.66, 25.70, 23.77),
        (29.29, 32.32, 25.98, 23.87), (24.69, 31.17, 26.95, 24.21)],
    11: [(41.23, 33.33, 25.58, 25.17), (36.99, 31.80, 27.01, 26.29),
         (29.68, 27.69, 30.92, 29.86), (0.00, 0.00, 0.00, 0.00)],
    18: [(-66.87, -73.29, 132.15, 131.67), (-66.87, -73.29, 132.15, 131.67)],
    19: [(15.88, 9.46, 49.45, 49.17), (15.88, 9.46, 49.45, 49.17)],
    21: [(39.23, 30.38, 28.57, 28.59), (37.73, 29.58, 29.37, 29.59)],
    22: [(33.60, 25.20, 33.74, 33.42), (30.26, 23.69, 35.24, 34.85),
         (23.85, 22.03, 36.64, 35.32), (49.00, 38.00, 21.00, 21.00),
         (42.78, 33.53, 25.41, 25.00), (39.78, 32.13, 26.81, 26.50)],
}
# "Start / Levels" in the coupler preview: what leaves the coupler
STARTS = {9: (49.00, 38.00, 21.00, 21.00), 11: (43.50, 33.90, 25.10, 25.00),
          18: (-66.87, -73.29, 132.15, 131.67), 19: (15.88, 9.46, 49.45, 49.17),
          21: (40.50, 30.70, 28.30, 28.50), 22: (33.60, 25.20, 33.74, 33.42)}


@pytest.mark.parametrize("branch", sorted(SHOTS))
def test_branch_levels_match_the_screenshots(screen, branch):
    rows = [r for r in screen.rows if r.branch == branch]   # end line included
    got = [tuple(round(r.levels[f], 2) for f in screen.frequencies) for r in rows]
    if branch == 9:              # the preview box shows its first ten lines
        got = got[:10]
    assert got == SHOTS[branch]


def test_coupler_preview_start_levels(screen):
    meta = {b["number"]: b for b in screen.branches}
    for branch, want in STARTS.items():
        assert tuple(meta[branch]["start"]) == want, branch


def test_in_line_q_device_and_the_pad_after_it(screen):
    # 6.2 carries Q5 (EXIST SPLICE, 0 dB), 6.8 Q2 (LEQ-PEA-0) then the
    # LEQ\RC PAD 13; the info box on that pad reads 26.54 26.82 39.23 36.85
    rows = {r.node: r for r in screen.rows if r.branch == 6 and not r.end}
    assert rows[2].amp == "Q5" and rows[8].amp == "Q2"
    assert rows[8].taps == ["<43>"]
    assert [round(v, 2) for v in rows[8].tap_levels[0]] == [26.54, 26.82, 39.23, 36.85]
    end = next(r for r in screen.rows if r.branch == 6 and r.end)
    assert [round(v, 2) for v in end.port_levels] == [21.63, 24.81, 46.73, 44.45]
    assert end.port_severity[2] == "red"


def test_fixed_nodes_carry_the_arrow(screen):
    b4 = {r.node: r.fixed for r in screen.rows if r.branch == 4 and not r.end}
    # every line but the two amplifiers shows "→" on the Design screen
    assert [n for n, f in b4.items() if not f] == [13, 24]


def test_amplifier_info_box(screen):
    row = next(r for r in screen.rows if (r.branch, r.node) == (4, 13))
    a = row.amp_info
    assert (a["name"], a["type"]) == ("AL00416", "BRIDGER 750 MHz")
    assert (a["fwd_pad"], a["ret_pad"]) == (4, 14)
    assert (a["aerial_prev"], a["aerial_start"], a["total_split"],
            a["total_prev"], a["total_start"]) == (2027, 2027, 1141, 2027, 2027)
    assert (a["cascade"], a["supply"], a["homes_down"]) == (1, "A", 120)


def test_power_supply_info(screen):
    ps = next(r for r in screen.rows if (r.branch, r.node) == (18, 1))
    assert (ps.supply_label, ps.supply_type, ps.supply_name) == ("A", 3, "EXISTING  90v")
    assert ps.supply_pct == 57


def test_coupler_column_matches_the_screen(screen):
    # the coupler column of branch 4 as the Design screen shows it, and the
    # first line of branch 9 as its preview box shows it
    got = [c for r in _rows(screen, 4) for c in r.couplers]
    assert got == ["12<6>", "100[9]", "3-<11><12>", "2[17]", "1<18>", "16<19>",
                   "100[20]", "3[21]<24>", "8[22]"]
    assert _rows(screen, 9)[0].couplers == ["108[10]"]
    # 7 runs along 4's 156 from the bridger at 4.4, but only its parent
    # branch 6 counts, whose span there is 121
    assert _rows(screen, 6)[0].couplers == ["100[7]"]


def test_branch_1_matches_the_screen(screen):
    # Design screen of branch 1: the node, then four 570 couplers.  Branch 3
    # is all 1xx cable yet drawn [3] -- it does not start along a parent span
    rows = [r for r in screen.rows if r.branch == 1]
    got = [tuple(round(r.levels[f], 2) for f in screen.frequencies) for r in rows]
    assert got == [(0.0, 0.0, 0.0, 0.0)] + [(49.0, 38.0, 17.0, 17.0)] * 5
    assert [r.amp for r in rows[:1]] == ["70"] and rows[0].amp_label == "AL004"
    assert [r.fixed for r in rows[:5]] == [False, True, True, True, True]
    assert rows[0].cab_name == "EX P3 500 A"          # cable 0, as its info box says
    assert [c for r in rows for c in r.couplers] == ["570<2>", "570[3]", "570[4]", "570[5]"]


def test_a_feed_stops_being_one_when_its_span_no_longer_matches():
    # The user changed 11.1 from 105 ft (4.16's span) to 106 in Lode Data:
    # 4.14 then showed 3-[11]<12>, and branch 11 these numbers
    design = design_from_ntw(NTW, SPEC)[0]
    design.branch(11).nodes[0].ftg = 106
    scr = build(design)
    assert [r for r in _rows(scr, 4) if r.node == 14][0].couplers == ["3-[11]<12>"]
    rows = [r for r in scr.rows if r.branch == 11]
    got = [tuple(round(r.levels[f], 2) for f in scr.frequencies) for r in rows]
    assert got == [(41.21, 33.33, 25.59, 25.17), (36.97, 31.79, 27.01, 26.29),
                   (29.65, 27.69, 30.93, 29.87), (0.0, 0.0, 0.0, 0.0)]
    # the 8-port tap on 11.2 is drawn <15> on the Design screen
    assert [t for r in rows for t in r.taps] == ["/17/", "<15>", "[ 8]"]
    assert [round(v, 2) for v in rows[-1].port_levels] == [21.55, 20.59, 38.13, 37.17]
    assert rows[-1].port_severity == [""] * 4
