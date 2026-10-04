"""What Lode writes when a network is changed and saved: the user's pairs of
4 Oct, each AL004 (WV750-2026) saved before and after one change -- H_A /
H_B (2.1 given 2 homes, a 0-ft line inserted under it), PS_A / PS_B (a power
inserter on 2.1, supply C on the new branch 46) -- and BH_KEYED, Q1's
network keyed on BH1GHzMid.  The app makes the same change and must write
the same bytes, but for the cursor Lode saves (41425: the branch and line it
was on) and the counters not decoded yet.  Skipped unless the files are
under samples/.
"""
import os
import struct
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "app"), str(ROOT / "tools")]

from hfc.importer import design_from_ntw                              # noqa: E402
from hfc.exporter import export_ntw                                   # noqa: E402
from hfc.plant import CouplerPlacement, Node                          # noqa: E402
from hfc.entry import resolve_coupler                                 # noqa: E402
from lodedata import writer as W                                      # noqa: E402
from lodedata.obfuscation import deobfuscate, PAYLOAD_START           # noqa: E402

SAMPLES = Path(os.environ.get("LODEDATA_SAMPLES", ROOT / "samples"))
CURSOR = set(range(W.P_CURSOR, W.P_CURSOR + 8))


def _find(name):
    p = next(SAMPLES.rglob(name), None) if SAMPLES.is_dir() else None
    if p is None:
        pytest.skip(f"{name} not in samples")
    return p


def _plain(data: bytes) -> bytes:
    return data[:PAYLOAD_START] + deobfuscate(data[PAYLOAD_START:])


def _differ(a: bytes, b: bytes) -> set:
    assert len(a) == len(b)
    return {i for i in range(len(a)) if a[i] != b[i]}


@pytest.fixture()
def api(monkeypatch, tmp_path):
    """The app's own edit functions, on a database of its own."""
    monkeypatch.setenv("LODEDATA_DB", str(tmp_path / "t.db"))
    sys.modules.pop("api", None)
    import api as A
    yield A
    sys.modules.pop("api", None)


def _open(A, ntw: Path, spec: Path) -> str:
    data = ntw.read_bytes()
    d, _ = design_from_ntw(data, spec)
    d.id = A.new_id("ntw")
    A.save(d)
    A.keep_ntw_file(d.id, data)
    return d.id


def test_new_homes_and_an_inserted_line_are_saved_as_lode_saves_them(api):
    """H_B: 2.1's hc 0 -> 2 fills its empty house list (1 1 4 4 ...) and
    takes its arrow off (fixed flag 0, 36.png); the line inserted under it
    is a new record, list all 4."""
    h_a, h_b = _find("H_A.ntw"), _find("H_B.ntw")
    spec = _find("WV750-2026.par").with_suffix("")
    nid = _open(api, h_a, spec)
    api.edit_node(nid, 2, 1, api.NodeEdit(hc=2))
    api.insert_node(nid, 2, api.InsertNode(after=1, cable_from_previous=True))
    d = api.load(nid)
    assert [(n.hc, n.fixed) for n in d.branch(2).nodes] == [(2, False), (0, False)]
    out, _ = export_ntw(d, h_a.read_bytes(), name="H_B")
    assert _differ(_plain(out), _plain(h_b.read_bytes())) <= CURSOR


def test_a_new_power_supply_is_saved_as_lode_saves_it(api):
    """PS_B: coupler 1 (CLPS-3009PI, the power inserter) keyed on 2.1 makes
    branch 46, one 0-ft line; supply C, NEW APLHA 90V PS (type 4), on it.
    The supply's record: the longer one, its block at +808 as Lode starts
    it, no house list.  36121 (+2 in Lode's) is not decoded yet."""
    ps_a, ps_b = _find("PS_A.ntw"), _find("PS_B.ntw")
    spec = _find("WV750-2026.par").with_suffix("")
    nid = _open(api, ps_a, spec)
    placed = api.set_coupler(nid, 2, 1, api.CouplerEdit(code="1"))["placed"]
    assert (placed["name"], placed["branch"]) == ("CLPS-3009PI", 46)
    d = api.load(nid)
    line = d.branch(46).nodes[0]
    sup = next(s for s in d.library.power_supplies.values() if s.type_id == 4)
    # Lode's file holds the name as "C " (as typed)
    line.supply_label, line.supply_part, line.supply_volts = "C ", sup.id, sup.volts
    out, _ = export_ntw(d, ps_a.read_bytes(), name="PS_B")
    assert _differ(_plain(out), _plain(ps_b.read_bytes())) <= CURSOR | {36121}


def test_bh_keyed_pads_as_lode_picked_them():
    """Q1's network keyed on BH1GHzMid: 71 (NC4000 2x2) on 1.1 holds 0 0 7 0
    -- the pick at the 0.00 its line reads, its bank's row of no tilt -- and
    11 (FM332) on 1.3, 190 ft on, Flag / CS8 / Flag / 2 (21 21 2 1)."""
    from hfc.importer import library_from_spec_set, parameters_from_spec_set
    from hfc.plant import Design
    from hfc.entry import resolve_active
    from hfc import screen as SC
    keyed = _find("BH_KEYED.ntw")
    spec = _find("BH1GHzMid.par").with_suffix("")
    params = parameters_from_spec_set(spec)
    d = Design(name="BH_KEYED", parameters=params, library=library_from_spec_set(spec, params))
    d.ensure_feeder()
    lib = d.library
    cable0 = next(c.id for c in lib.cables.values() if c.cable_index == 0)
    b1 = d.branch(1)
    b1.nodes[0].cab_part = cable0
    node = resolve_active(lib, "71")
    b1.nodes[0].amp, b1.nodes[0].amp_part, b1.nodes[0].pads = node.active_id, node.id, [0, 0, 0, 0]
    SC.repick(d, {}, keyed={id(b1.nodes[0])})
    le = resolve_active(lib, "11")
    b1.nodes += [Node(seq=2, ftg=190, hc=2, cab_part=cable0),
                 Node(seq=3, amp=le.active_id, amp_part=le.id, pads=[0, 0, 0, 0], cab_part=cable0),
                 Node(seq=4, cab_part=cable0)]
    SC.repick(d, SC.active_inputs(d), keyed={id(b1.nodes[2])})
    assert [n.pads for n in b1.nodes] == [[0, 0, 7, 0], [], [21, 21, 2, 1], []]
    out, _ = export_ntw(d, None, name="BH_KEYED", header=keyed.read_bytes()[:512])
    a, b = _plain(out), _plain(keyed.read_bytes())
    # every pad and EQ tally as Lode's
    pads = range(W.P_PAD_TALLY, W.P_PAD_TALLY + 4 * W.PAD_TALLY_SIZE)
    assert not {i for i in _differ(a, b) if i in pads}
    assert struct.unpack_from("<II", b, W.P_CURSOR) == (1, 3)


def test_bh_keyed_test_list_is_lodes():
    """1c: "Not enough taps at node 1.2." (2 homes, no tap), and nothing
    else -- the FM332 on 1.3 at its Flag pads is within its In and Out."""
    from hfc.screen import build
    keyed = _find("BH_KEYED.ntw")
    d, _ = design_from_ntw(keyed.read_bytes(), _find("BH1GHzMid.par").with_suffix(""))
    assert build(d).tests == [("red", "Not enough taps at node 1.2.")]


def test_ps_b_branch_46_as_lode_draws_it():
    """35b / 35c: 46.1 behind 2.1's power inserter reads -50.00 -61.00
    116.00 116.00; supply C, in the area 18.1's A already powers, is drawn
    all the same -- C in the cplr column, its box NEW APLHA 90V PS, and in
    Power 85.61 V, 0.00 A, C  \\04  0%."""
    from hfc.screen import build
    d, _ = design_from_ntw(_find("PS_B.ntw").read_bytes(), _find("WV750-2026.par").with_suffix(""))
    r = next(r for r in build(d).rows if (r.branch, r.node, r.end) == (46, 1, False))
    assert r.as_dict()["levels"] == [-50.0, -61.0, 116.0, 116.0]
    assert (round(r.volts, 2), r.current) == (85.61, 0.0)
    assert (r.supply_label, r.supply_type, r.supply_name, r.supply_pct) == (
        "C", 4, "NEW APLHA 90V PS", 0)
