"""SN001_MID and its SHINSTON spec set (SHINN1GHz Mid): a line with text.

SN001's 1.1 holds 63 characters of text at +698 of its record; every field
after it moves by as much, so the file could not be read -- and Project
Settings could not attach the spec set to it ("826305 bytes after the last
branch").  Read with the text, it is 47 branches of 390 lines, every
reference resolved against SHINSTON, and it comes back byte for byte.

Skipped unless samples/SN001-SHINSTON holds SN001_MID.ntw and the five
"SHINN1GHz Mid" files.
"""
import os
import struct
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))
sys.path.insert(0, str(ROOT / "tools"))

from hfc.importer import design_from_ntw                          # noqa: E402
from hfc.exporter import export_ntw                               # noqa: E402
from hfc.plant import Node                                        # noqa: E402
from lodedata import network as N                                 # noqa: E402
from lodedata import writer as W                                  # noqa: E402
from lodedata.obfuscation import deobfuscate, PAYLOAD_START       # noqa: E402
from lodedata.specs import load_spec_set                          # noqa: E402

SAMPLES = Path(os.environ.get("LODEDATA_SAMPLES", ROOT / "samples"))
PAIR = SAMPLES / "SN001-SHINSTON"
NTW, SPEC = PAIR / "SN001_MID.ntw", PAIR / "SHINN1GHz Mid"

pytestmark = pytest.mark.skipif(
    not NTW.exists() or not SPEC.with_suffix(".par").exists(),
    reason="SN001_MID + SHINN1GHz Mid not in samples/SN001-SHINSTON")

TEXT = b'SHIN1 - 4953 - P-003938~0POWERED BY PS "PS1A"~0DATE :02/20/26~0'


def plain(data: bytes) -> bytes:
    return data[:PAYLOAD_START] + deobfuscate(data[PAYLOAD_START:])


def test_a_line_with_text_is_read():
    p = plain(NTW.read_bytes())
    net = N.read_network(p)
    assert len(net.branches) == 47 and net.node_count == 390 and net.name == "SN001"
    first = net.branches[1].nodes[0]
    assert first.text == TEXT and first.size == N.ACTIVE_NODE_RECORD + len(TEXT)
    assert first.active_index == 13 and first.label == "SN001"
    # the fields after the text are where the text leaves them
    assert p[first.offset + N.N_HAS_ACTIVE + len(TEXT)] == 1
    assert struct.unpack_from("<I", p, first.offset + W.N_SELF + len(TEXT))[0] == first.id
    assert sum(1 for b in net.branches.values() for n in b.nodes if n.text) == 1
    # power supply labels are C strings: 1A 1B 1C, not one letter
    assert sorted(n.supply for b in net.branches.values() for n in b.nodes if n.supply) == \
        ["1A", "1B", "1C"]


def test_it_comes_back_byte_for_byte():
    src = NTW.read_bytes()
    p = plain(src)
    out, _ = W.build(W.split(p), W.outs_from_plain(p))
    assert out == p and W.encode(out) == src
    d, rep = design_from_ntw(src, SPEC)
    assert rep["unresolved"] == [] and rep["branches"] == 47
    data, report = export_ntw(d, src)
    assert data == src and report["not_written"] == []


def test_every_count_table_rebuilds_from_nothing():
    p = plain(NTW.read_bytes())
    regions = [(W.P_FTG, 8), (W.P_FTG_CABLE, 4000), (W.P_HOMES, 24), (W.P_ACTIVES, 4 * 252),
               (W.P_INLINE, 4 * 24), (W.P_TAPS, 16 * 512), (W.P_TAP_PORTS, 16),
               (W.P_COUPLERS, 4 * 252)]
    z = bytearray(p)
    for at, n in regions:
        z[at:at + n] = bytes(n)
    counts = W._counts(W.outs_from_plain(p))
    W._totals(z, counts, counts)
    assert bytes(z) == p


def test_editing_keeps_the_text_and_every_link():
    src = NTW.read_bytes()
    d, _ = design_from_ntw(src, SPEC)
    b1 = d.branch(1)
    b1.nodes[0].ftg = 12                               # 1.1, the line with text
    cable = next(c.id for c in d.library.cables.values() if c.cable_index == 42)
    b1.nodes.insert(1, Node(cab=442, cab_part=cable))  # a new 1.2
    d.renumber(b1)
    data, _ = export_ntw(d, src)
    p = plain(data)
    net = N.read_network(p)
    assert W.join(W.split(p)) == p
    first = net.branches[1].nodes[0]
    assert (first.text, first.ftg, first.label) == (TEXT, 12, "SN001")
    assert len(net.branches[1].nodes) == 30 and not net.branches[1].nodes[1].text
    for br in net.branches.values():
        for k, nd in enumerate(br.nodes):
            prev, nxt = struct.unpack_from("<II", p, nd.offset + 4)
            assert prev == (br.nodes[k - 1].id if k else br.number)
            assert nxt == (br.nodes[k + 1].id if k + 1 < len(br.nodes) else br.end_id)
    again, _ = design_from_ntw(data, SPEC)
    assert again.branch(1).nodes[0].ftg == 12


def test_the_spec_set_reads_in_full():
    s = load_spec_set(SPEC)
    assert s.headers["atv"].format_version == "11.1" and s.headers["cbl"].format_version == "12.1"
    assert s.frequencies == {"F1": "1002", "F2": "102", "R1": "85", "R2": "5"}
    assert s.levels[:2] == [[18.0, 9.0, 42.0, 42.0], [21.0, 10.5, 42.0, 42.0]]
    assert (len(s.cables), len(s.couplers), len(s.taps), len(s.banks)) == (34, 21, 39, 8)
    # 13 actives: record 0 ("BRIDGER", every level 0) is never placed
    assert [a.active_id for a in s.actives] == ["11", "21", "22", "31", "32", "33",
                                               "61", "62", "63", "71", "72", "85", "86"]
    assert [q.name for q in s.inline][:2] == ["FFE-8-120-85/RP", "FFE-8-120-FB"]
    assert [x.name for x in s.supplies] == ["ALPHA XM-2 EX", "ALPHA XM-2 N", "ALPHA XM2 90V",
                                            "NEW ALPHA XM2 90V"]
    assert s.parameters["power_interpolation"] == "step"


# The user's screenshots of SN001 in Lode Data with SHINSTON: branch 1
# (1.1 - 1.29 and the end line) and branch 2 (2.1 - 2.61), at 1002 102 85 5
LODE_B1 = [
    (0.00, 0.00, 0.00, 0.00), (53.00, 37.00, 9.00, 9.00), (53.00, 37.00, 9.00, 9.00),
    (53.00, 37.00, 9.00, 9.00), (53.00, 37.00, 9.00, 9.00), (49.73, 36.08, 9.86, 9.19),
    (47.72, 35.52, 10.38, 9.31), (44.83, 34.70, 11.14, 9.48), (41.14, 33.67, 12.10, 9.70),
    (38.27, 32.86, 12.85, 9.87), (36.54, 32.37, 13.30, 9.97), (32.62, 31.27, 14.33, 10.20),
    (29.25, 30.33, 15.21, 10.40), (20.84, 27.96, 17.41, 10.89), (20.84, 27.96, 17.41, 10.89),
    (43.36, 34.29, 11.52, 9.57), (39.84, 33.30, 12.44, 9.77), (35.86, 32.18, 13.48, 10.01),
    (27.31, 29.78, 15.72, 10.51), (25.48, 29.26, 16.20, 10.62), (22.11, 28.32, 17.08, 10.82),
    (14.15, 26.08, 19.16, 11.29), (47.46, 35.44, 10.45, 9.33), (41.54, 33.78, 12.00, 9.67),
    (36.03, 32.23, 13.44, 10.00), (30.66, 30.72, 14.84, 10.31), (25.75, 29.34, 16.12, 10.60),
    (48.10, 35.62, 10.28, 9.29), (43.87, 34.43, 11.39, 9.54), (41.47, 33.33, 12.39, 10.64)]
LODE_B2 = [
    (49.13, 35.91, 10.01, 9.23), (45.76, 34.97, 10.89, 9.43), (42.34, 34.00, 11.79, 9.63),
    (38.17, 32.83, 12.88, 9.87), (35.41, 32.06, 13.60, 10.04), (32.71, 31.30, 14.30, 10.19),
    (28.55, 30.13, 15.39, 10.44), (25.86, 29.37, 16.10, 10.60), (23.10, 28.60, 16.82, 10.76),
    (19.28, 27.52, 17.82, 10.98), (16.13, 26.64, 18.64, 11.17), (12.91, 25.73, 19.48, 11.36),
    (49.92, 36.14, 9.80, 9.18), (46.93, 35.29, 10.59, 9.36), (43.35, 34.29, 11.52, 9.57),
    (39.83, 33.30, 12.44, 9.77), (37.09, 32.53, 13.16, 9.94), (34.52, 31.81, 13.83, 10.09),
    (31.38, 30.92, 14.65, 10.27), (29.56, 30.41, 15.13, 10.38), (27.68, 29.88, 15.62, 10.49),
    (23.93, 28.83, 16.60, 10.71), (20.73, 27.93, 17.44, 10.90), (17.37, 26.99, 18.32, 11.10),
    (14.77, 26.25, 19.00, 11.25), (50.02, 36.16, 9.78, 9.18), (47.23, 35.38, 10.51, 9.34),
    (44.39, 34.58, 11.25, 9.51), (41.08, 33.65, 12.12, 9.70), (37.94, 32.77, 12.94, 9.89),
    (35.89, 32.19, 13.47, 10.01), (34.03, 31.67, 13.96, 10.12), (29.74, 30.46, 15.08, 10.37),
    (25.84, 29.37, 16.10, 10.60), (22.51, 28.43, 16.97, 10.79), (19.60, 27.61, 17.73, 10.96),
    (16.82, 26.83, 18.46, 11.13), (12.90, 25.73, 19.48, 11.36), (53.00, 37.00, 9.00, 9.00),
    (49.06, 35.56, 10.37, 9.70), (47.73, 35.19, 10.72, 9.77), (44.72, 34.34, 11.51, 9.95),
    (42.27, 33.65, 12.15, 10.10), (39.35, 32.83, 12.91, 10.27), (36.87, 32.14, 13.56, 10.41),
    (31.48, 30.62, 14.97, 10.73), (26.71, 29.28, 16.22, 11.01), (22.23, 28.02, 17.39, 11.27),
    (20.73, 27.60, 17.78, 11.36), (17.38, 26.66, 18.66, 11.56), (49.56, 36.03, 9.90, 9.20),
    (46.57, 35.19, 10.68, 9.38), (46.19, 35.09, 10.78, 9.40), (43.13, 34.23, 11.58, 9.58),
    (33.26, 31.45, 14.16, 10.16), (32.88, 31.35, 14.26, 10.18), (32.88, 31.35, 14.26, 10.18),
    (29.82, 30.49, 15.06, 10.36), (27.46, 29.82, 15.68, 10.50), (25.69, 29.32, 16.14, 10.61),
    (24.08, 28.87, 16.56, 10.70)]
LODE_TESTS = [
    # Lode's Test Results window, all 15 (SN001_MID's 1.1 Ripple-2 has no EQ
    # in its bank, forward or return)
    "Fslope too low to equalize at 1.1.", "Rslope too low to equalize at 1.1.",
    "Tap(1002)  1.90 over window at 5.2.", "Tap(102)  0.03 below min at 5.10.",
    "Tap(5)  0.29 below window at 13.3.", "Tap(5)  0.39 below window at 18.20.",
    "Tap(1002)  2.90 over window at 23.1.", "Tap(1002)  1.00 over window at 24.23.",
    "Tap(5)  0.78 below window at 32.2.", "Tap(5)  0.87 below window at 34.7.",
    "Tap(1002)  0.14 below min at 35.9.", "Tap(5)  0.41 below window at 37.5.",
    "Tap(5)  0.51 below window at 40.4.", "Tap(1002)  1.00 over window at 46.5.",
    "Tap(1002)  2.20 over window at 46.6."]


@pytest.fixture(scope="module")
def sn001():
    from hfc.screen import build
    d, _ = design_from_ntw(NTW.read_bytes(), SPEC)
    return d, build(d)


def _levels(scr, branch):
    from hfc.screen import as_shown
    return [tuple(as_shown(r.levels[f]) for f in scr.frequencies)
            for r in scr.rows if r.branch == branch]


def test_the_design_screen_is_lodes(sn001):
    d, scr = sn001
    assert scr.frequencies == [1002.0, 102.0, 85.0, 5.0]
    assert _levels(scr, 1) == LODE_B1
    assert _levels(scr, 2)[:61] == LODE_B2
    assert _levels(scr, 4) == [(-46.0, -62.0, 108.0, 108.0)] * 2   # through the SSP-PIK's 99 dB leg
    rows = {(r.branch, r.node): r for r in scr.rows if not r.end}
    # the Configuration Table slot each line keeps: 63U, 11U (and 5.8's 11M)
    assert [rows[k].amp for k in ((1, 1), (1, 15), (1, 22), (1, 27), (2, 12), (5, 8))] == \
        ["61", "63U", "63U", "11U", "63U", "11M"]
    assert [rows[(1, k)].couplers for k in (2, 3, 4, 22)] == [["61[2]"], ["61[13]"], ["61<14>"], ["63[36]"]]
    assert rows[(2, 39)].couplers == ["60<4>"] and rows[(2, 25)].couplers == ["63<40>"]
    assert [rows[(1, k)].power_stop for k in (5, 14)] == [True, True]
    assert rows[(1, 29)].taps == ["[20]"]
    end = next(r for r in scr.rows if r.branch == 1 and r.end)
    assert [round(v + 1e-9, 2) for v in end.port_levels] == [23.87, 14.43, 31.39, 29.54]
    # the line with Notes, and the supply on 4.1
    assert rows[(1, 1)].note.startswith("SHIN1 - 4953") and rows[(4, 1)].supply_label == "1A"
    assert [t[1] for t in scr.tests] == LODE_TESTS


def test_the_info_boxes_are_lodes(sn001):
    d, scr = sn001
    rows = {(r.branch, r.node): r for r in scr.rows if not r.end}
    keys = ("fwd_pad", "fwd_eq", "ret_pad", "ret_eq", "aerial_prev", "aerial_start",
            "total_split", "total_prev", "total_start", "cascade", "supply", "homes_down")
    box = lambda k: tuple(rows[k].amp_info[x] for x in keys)
    assert box((1, 1)) == ("", "VOID", "", "VOID", 0, 0, 0, 0, 0, 0, "1A", 227)
    assert box((1, 15)) == ("100", "9", "180", "7", 2102, 2102, 2102, 2102, 2102, 1, "1B", 131)
    assert box((1, 22)) == ("030", "15", "160", "9", 2539, 4641, 2539, 2539, 4641, 2, "1B", 4)
    assert box((1, 27)) == ("060", "14", "190", "6", 1781, 6422, 1781, 1781, 6422, 3, "1B", 1)
    assert rows[(1, 15)].amp_info["parts"] == ["NPB-100", "NPB-180", "CE-120-9", "MEQ-85-7"]
    b = rows[(1, 15)].block
    assert (b["distances"], b["losses"], b["above"], b["below"], b["homes"], b["same_cable"]) == \
        ([2102] * 5, [32.16] * 3, [1, 0, 0], [9, 16, 0], 131, 2102)
    b = rows[(1, 22)].block
    assert (b["distances"], b["losses"], b["above"], b["below"], b["homes"]) == \
        ([2539, 4641, 2539, 2539, 4641], [38.85, 38.85, 71.01], [2, 0, 0], [1, 2, 0], 4)
    assert rows[(4, 1)].block["distances"] == [0, 7740, 0, 0, 7740]


def test_a_configuration_id_is_typed_and_kept():
    from hfc.entry import resolve_active, config_slot
    d, _ = design_from_ntw(NTW.read_bytes(), SPEC)
    part = resolve_active(d.library, "63U")
    assert part.name == "FM902B" and config_slot(part, "63U") == 2 and config_slot(part, "63") == 0
    # 1.27 made an 11M on a copy: the file keeps slot 3 there
    n = d.branch(1).nodes[26]
    n.amp, n.amp_config = "11M", 3
    data, _ = export_ntw(d, NTW.read_bytes())
    p = plain(data)
    nd = N.read_network(p).branches[1].nodes[26]
    assert nd.config == 3 and p[nd.offset + N.N_CONFIG] == 3
    assert design_from_ntw(data, SPEC)[0].branch(1).nodes[26].amp == "11M"


# The user's second set of SN001 screenshots (Design screen, branches 5, 8,
# 15, 18, 24, 28): every line, the line under the last node, its port levels.
LODE_SHOTS = {
    5: [(53.00, 37.00, 9.00, 9.00), (50.90, 35.70, 10.30, 10.30), (43.75, 33.23, 12.56, 11.69),
        (34.57, 29.84, 15.79, 13.82), (30.94, 28.79, 16.75, 14.04), (30.94, 28.79, 16.75, 14.04),
        (27.40, 27.76, 17.69, 14.26), (19.51, 25.48, 19.78, 14.74), (45.99, 34.97, 10.86, 9.43),
        (45.99, 34.97, 10.86, 9.43), (37.23, 32.45, 13.13, 10.44), (31.94, 30.31, 15.20, 11.92),
        (25.64, 17.81, 27.10, 24.32)],
    8: [(24.01, 19.49, 26.13, 24.33), (21.90, 18.88, 26.69, 24.46), (53.00, 37.00, 9.00, 9.00),
        (47.26, 34.55, 11.39, 10.94), (43.06, 33.17, 12.63, 11.86), (37.45, 31.15, 14.48, 13.16),
        (32.22, 29.63, 15.87, 13.48), (24.82, 18.47, 26.38, 24.12), (0.0, 0.0, 0.0, 0.0)],
    15: [(53.00, 37.00, 9.00, 9.00), (42.49, 33.34, 12.50, 10.80), (38.66, 32.26, 13.50, 11.02),
         (35.97, 31.50, 14.20, 11.18), (32.14, 30.43, 15.20, 11.40), (28.35, 29.36, 16.20, 11.63),
         (25.79, 28.64, 16.86, 11.78), (23.48, 27.99, 17.47, 11.91), (20.34, 26.78, 18.63, 12.56),
         (16.87, 25.80, 19.54, 12.77), (53.00, 37.00, 9.00, 9.00), (50.81, 36.39, 9.57, 9.13),
         (48.06, 35.61, 10.29, 9.29), (44.83, 34.70, 11.14, 9.48), (42.69, 34.10, 11.70, 9.61),
         (40.99, 33.62, 12.14, 9.71), (38.24, 32.85, 12.86, 9.87), (30.61, 27.94, 17.74, 14.38),
         (28.82, 27.44, 18.20, 14.48), (25.92, 26.62, 18.96, 14.65), (23.18, 25.85, 19.68, 14.81),
         (19.23, 24.74, 20.71, 15.05), (15.16, 23.60, 21.78, 15.28), (47.39, 35.38, 10.49, 9.35),
         (41.94, 33.80, 11.93, 9.68), (35.37, 31.41, 14.14, 11.31), (25.26, 17.75, 27.00, 23.66),
         (53.00, 37.00, 9.00, 9.00), (48.16, 35.61, 10.23, 9.77), (43.15, 34.00, 11.67, 10.74),
         (36.32, 31.61, 13.85, 12.11), (27.14, 28.37, 16.86, 14.36), (53.00, 37.00, 9.00, 9.00),
         (45.60, 34.87, 10.91, 9.93), (43.20, 33.77, 11.91, 11.03)],
    18: [(53.00, 37.00, 9.00, 9.00), (47.43, 34.72, 11.21, 10.50), (42.65, 33.38, 12.46, 10.79),
         (38.02, 32.08, 13.67, 11.06), (33.15, 30.71, 14.94, 11.34), (28.99, 29.54, 16.03, 11.59),
         (23.77, 28.08, 17.39, 11.90), (18.79, 26.67, 18.70, 12.19), (15.53, 25.76, 19.55, 12.38),
         (50.36, 36.24, 9.70, 9.16), (41.94, 33.64, 12.05, 10.35), (36.47, 32.06, 13.50, 10.68),
         (29.66, 29.48, 15.97, 12.25), (53.00, 37.00, 9.00, 9.00), (46.10, 32.28, 13.69, 13.47),
         (43.36, 31.49, 14.42, 13.64), (36.89, 29.21, 16.50, 14.99), (33.49, 28.23, 17.40, 15.20),
         (53.00, 37.00, 9.00, 9.00), (42.65, 34.01, 11.69, 10.11), (39.55, 32.61, 12.99, 11.71)],
    24: [(28.29, 27.29, 18.34, 14.51), (25.72, 26.56, 19.02, 14.66), (23.49, 25.94, 19.60, 14.80),
         (20.91, 25.21, 20.27, 14.95), (17.07, 24.13, 21.28, 15.17), (13.33, 23.08, 22.26, 15.39),
         (12.73, 22.58, 22.76, 15.89), (50.28, 36.23, 9.71, 9.16), (47.95, 35.58, 10.32, 9.30),
         (45.27, 34.83, 11.02, 9.45), (40.58, 33.51, 12.25, 9.73), (36.67, 32.41, 13.27, 9.96),
         (33.43, 31.50, 14.12, 10.15), (31.95, 31.08, 14.50, 10.24), (28.76, 30.19, 15.34, 10.43),
         (21.37, 28.11, 17.27, 10.86), (15.71, 26.52, 18.75, 11.19), (45.64, 34.87, 10.95, 9.45),
         (41.88, 33.79, 11.95, 9.69), (33.02, 31.22, 14.30, 10.23), (24.35, 28.72, 16.60, 10.77),
         (19.79, 27.40, 17.81, 11.05), (53.00, 37.00, 9.00, 9.00), (41.59, 33.30, 12.39, 10.66),
         (29.00, 29.15, 16.21, 12.84), (53.00, 37.00, 9.00, 9.00), (38.77, 30.17, 15.58, 14.39),
         (35.67, 28.77, 16.88, 15.99)],
    28: [(53.00, 37.00, 9.00, 9.00), (45.14, 32.41, 13.50, 12.73), (41.94, 31.49, 14.35, 12.93),
         (38.24, 30.42, 15.33, 13.16), (34.36, 29.30, 16.36, 13.40), (31.37, 28.43, 17.15, 13.58),
         (25.67, 26.78, 18.67, 13.93), (22.25, 25.80, 19.57, 14.14), (16.03, 24.00, 21.22, 14.53),
         (47.66, 35.46, 10.42, 9.33), (35.95, 31.91, 13.64, 10.72), (26.08, 28.45, 16.92, 12.48),
         (53.00, 37.00, 9.00, 9.00), (42.27, 33.91, 11.79, 10.13), (39.78, 33.19, 12.45, 10.29),
         (35.31, 31.89, 13.64, 10.56), (32.91, 30.59, 14.94, 11.86)],
}
LODE_PORTS = {5: [18.84, 9.91, 35.00, 31.92], 8: [20.52, 14.17, 30.68, 28.42],
              15: [25.60, 14.87, 30.91, 29.93], 18: [27.15, 18.51, 27.19, 25.61],
              24: [23.27, 14.67, 31.08, 29.89], 28: [18.31, 14.89, 30.64, 27.56]}


@pytest.mark.parametrize("branch", sorted(LODE_SHOTS))
def test_more_branches_are_lodes(sn001, branch):
    from hfc.screen import as_shown
    d, scr = sn001
    assert _levels(scr, branch) == LODE_SHOTS[branch]
    end = next(r for r in scr.rows if r.branch == branch and r.end)
    assert [as_shown(v) for v in end.port_levels] == LODE_PORTS[branch]


def test_the_amp_and_tap_columns_are_lodes(sn001):
    d, scr = sn001
    rows = {(r.branch, r.node): r for r in scr.rows if not r.end}
    # the in-line equaliser (Q1) reads EQ; the other in-line devices Qn
    assert [rows[k].amp for k in ((5, 5), (5, 6), (5, 8), (5, 9), (5, 12), (8, 7), (15, 26))] == \
        ["Q8", "Q6", "11M", "Q8", "EQ", "EQ", "EQ"]
    # a 3-digit tap in the 4-wide column loses its opening bracket
    assert [rows[k].taps for k in ((5, 11), (5, 12), (18, 12), (28, 11), (28, 16))] == \
        [["117]"], ["111]"], ["117]"], ["117]"], ["117]"]]
    assert [rows[k].taps for k in ((8, 7), (8, 8), (18, 20))] == [["/10/"], ["/ 4/"], ["[15]"]]


def test_the_node_box_lists_distances_where_lode_does(sn001):
    d, scr = sn001
    rows = {(r.branch, r.node): r for r in scr.rows if not r.end}
    # 1.2, a coupler line: all 0 and 227 homes; 4.1 starts a branch at 0 ft;
    # 8.1 (334 ft, nothing on it) has the short box
    assert rows[(1, 2)].node_box and rows[(1, 2)].block["distances"] == [0, 0, 0, 0, 0]
    assert rows[(1, 2)].block["homes"] == 227
    assert rows[(4, 1)].node_box and not rows[(8, 1)].node_box
    keys = ("fwd_pad", "fwd_eq", "ret_pad", "ret_eq", "aerial_prev", "aerial_start",
            "total_split", "total_prev", "total_start", "cascade", "supply", "homes_down")
    assert tuple(rows[(5, 8)].amp_info[x] for x in keys) == \
        ("000", "17", "160", "6", 1265, 11294, 1040, 1265, 11294, 5, "1A", 3)


def test_the_preview_box_gets_the_levels_as_computed(sn001):
    # 2.5 at 102 MHz is 32.055: the Design screen shows 32.06, the preview
    # box (printing the value as computed) 32.05
    d, scr = sn001
    r = next(r for r in scr.rows if (r.branch, r.node) == (2, 5)).as_dict()
    assert r["levels"][1] == 32.06 and f"{r['raw_levels'][1]:.2f}" == "32.05"


def test_notes_are_written_a_row_to_each_tilde_0():
    src = NTW.read_bytes()
    d, _ = design_from_ntw(src, SPEC)
    d.branch(1).nodes[0].note = "EDITED~0SECOND ROW~0"      # 1.1 had three rows
    d.branch(1).nodes[1].note = "NEW~0"                     # 1.2 had none
    data, report = export_ntw(d, src)
    assert not report["not_written"]
    net = N.read_network(plain(data))
    assert [nd.text for nd in net.branches[1].nodes[:3]] == [b"EDITED~0SECOND ROW~0", b"NEW~0", b""]
    assert len(data) == len(src) - len(TEXT) + 20 + 5
    again, _ = design_from_ntw(data, SPEC)
    assert again.branch(1).nodes[1].note == "NEW~0"
    assert export_ntw(again, data)[0] == data
