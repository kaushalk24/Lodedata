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
from lodedata.specs import read_taps, read_actives, load_spec_set  # noqa: E402

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
    assert [r.taps for r in _rows(screen, 4)][26:] == [["[17]"], ["[11]"], ["/4/"]]
    assert [t for r in _rows(screen, 3) for t in r.taps] == ["[20]", "/17/", "/14/", "/8/"]


def test_taps_out_of_the_system_levels_are_flagged_as_on_screen(screen):
    # branch 3: /14/ (lv 1, needs 19) and /8/ (lv 0, needs 17) are red on the
    # Design screen, and so is the 11.31 port output under the last one
    sev = {t: s for r in _rows(screen, 3) for t, s in zip(r.taps, r.tap_severity)}
    assert sev == {"[20]": "", "/17/": "", "/14/": "red", "/8/": "red"}
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
    # within 0.03 V everywhere; see docs/open-questions.md for the residual
    rows = _rows(screen, 4)
    worst = max(abs(r.volts - v) for r, v in zip(rows, B4_VOLTS))
    assert worst < 0.03


def test_each_supply_carries_its_area(screen):
    load = {r.supply_label: round(r.current, 2) for r in screen.rows if r.supply}
    assert set(load) == {"A", "B", "C"}
    assert abs(load["A"] - 8.60) <= 0.011
