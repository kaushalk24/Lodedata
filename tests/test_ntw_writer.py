"""Writing .ntw files: AL004 back byte for byte, and edited designs written
with every link, id and total the program keeps.

Skipped unless AL004 and its WV750-2026 spec set are in samples/.
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
from hfc.plant import Node, TapPlacement, CouplerPlacement        # noqa: E402
from hfc.screen import build                                      # noqa: E402
from lodedata import network as N                                 # noqa: E402
from lodedata import writer as W                                  # noqa: E402
from lodedata.obfuscation import deobfuscate, PAYLOAD_START       # noqa: E402

SAMPLES = Path(os.environ.get("LODEDATA_SAMPLES", ROOT / "samples"))
PAIR = SAMPLES / "AL004-WV750"
NTW, SPEC = PAIR / "AL004.ntw", PAIR / "WV750-2026"

pytestmark = pytest.mark.skipif(
    not NTW.exists() or not SPEC.with_suffix(".tap").exists(),
    reason="AL004 + WV750-2026 not in samples/AL004-WV750")


def plain(data: bytes) -> bytes:
    return data[:PAYLOAD_START] + deobfuscate(data[PAYLOAD_START:])


def fresh():
    src = NTW.read_bytes()
    d, _ = design_from_ntw(src, SPEC)
    return d, src


def links_ok(data: bytes) -> N.NtwNetwork:
    """Every link and id as the program keeps them."""
    p = plain(data)
    net = N.read_network(p)
    raw = W.split(p)
    assert W.join(raw) == p
    assert list(net.branches) == list(range(1, len(net.branches) + 1))
    seen = set()
    for number, br in net.branches.items():
        rb = raw.branches[number - 1]
        head_parent, head_first, count = struct.unpack_from("<IIH", rb.head, 0)
        assert count == len(br.nodes) and head_first == br.nodes[0].id
        if number == 1:
            assert head_parent == 0
        else:
            pb, pn = br.parent
            assert head_parent == net.branches[pb].nodes[pn - 1].id
        for k, nd in enumerate(br.nodes):
            prev, nxt = struct.unpack_from("<II", p, nd.offset + 4)
            assert prev == (br.nodes[k - 1].id if k else number)
            assert nxt == (br.nodes[k + 1].id if k + 1 < len(br.nodes) else br.end_id)
            assert nd.id not in seen
            seen.add(nd.id)
            if p[nd.offset + N.N_HAS_ACTIVE]:
                assert struct.unpack_from("<I", p, nd.offset + W.N_SELF)[0] == nd.id
        assert rb.end[:4] == bytes(4)
        assert struct.unpack_from("<II", rb.end, 4) == (br.end_id, br.nodes[-1].id)
        assert br.end_id not in seen
        seen.add(br.end_id)
    assert struct.unpack_from("<I", p, W.P_BRANCHES)[0] == len(net.branches)
    assert struct.unpack_from("<I", p, W.P_NEXT_ID)[0] < min(seen)
    # the totals are what the network holds
    rebuilt = bytearray(p)
    W._totals(rebuilt, W._counts(W.outs_from_plain(p)), W._counts(W.outs_from_plain(p)))
    assert bytes(rebuilt) == p
    return net


def line(d, cab, **kw):
    """A new line with its cable part, as Insert and Alter set them."""
    part = next(c.id for c in d.library.cables.values() if c.cable_index == cab % 100)
    return Node(cab=cab, cab_part=part, **kw)


def screen_of(d):
    return [(r.branch, r.node, r.levels and tuple(round(v, 2) for v in r.levels.values()),
             tuple(r.taps), tuple(r.couplers), r.amp, r.amp_label, r.ftg, r.hc, r.cab)
            for r in build(d).rows if not r.end]


def reread(data: bytes):
    d, rep = design_from_ntw(data, SPEC)
    assert rep["unresolved"] == []
    return d


def test_al004_comes_back_byte_for_byte():
    p = plain(NTW.read_bytes())
    out, _ = W.build(W.split(p), W.outs_from_plain(p))
    assert out == p
    assert W.encode(out) == NTW.read_bytes()
    d, src = fresh()
    data, report = export_ntw(d, src)
    assert data == src and report["not_written"] == []


def test_the_totals_are_the_programs():
    """Footage by cable, homes, ports, taps by row, actives, in-line devices
    and couplers, aerial and underground: rebuilt from nothing they are the
    bytes Lode Data wrote."""
    p = plain(NTW.read_bytes())
    c = W._counts(W.outs_from_plain(p))
    blank = bytearray(p)
    blank[W.P_FTG:W.P_FTG + 8] = bytes(8)
    blank[W.P_FTG_CABLE:W.P_FTG_CABLE + 4000] = bytes(4000)
    blank[W.P_HOMES:W.P_HOMES + 24] = bytes(24)
    for name, (at, _) in W._PAIR_TABLES.items():
        for key in c[name]:
            struct.pack_into("<HH", blank, at(key), 0, 0)
    assert bytes(blank) != p
    W._totals(blank, {k: ({} if isinstance(v, dict) else v) for k, v in c.items()}, c)
    assert bytes(blank) == p
    # a few read by eye: 35612 ft aerial + 1354 ft underground, 162 + 19 homes
    assert struct.unpack_from("<II", p, W.P_FTG) == (35612, 1354)
    assert struct.unpack_from("<6I", p, W.P_HOMES) == (162, 19, 300, 22, 162, 19)


def test_edits_to_existing_lines_touch_only_their_fields():
    d, src = fresh()
    b4 = d.branch(4)
    b4.nodes[0].ftg = 500              # 4.1: 476 -> 500
    d.branch(25).nodes[7].hc = 3       # 25.8: 2 -> 3, a line with its house list filled in
    n42 = d.branch(4).nodes[1]         # 4.2: 410 -> 406, as Alter sets it
    n42.cab = 406
    n42.cab_part = next(c.id for c in d.library.cables.values() if c.cable_index == 6)
    data, report = export_ntw(d, src)
    assert report["not_written"] == []
    net = links_ok(data)
    assert net.branches[4].nodes[0].ftg == 500
    assert net.branches[25].nodes[7].hc == 3 and net.branches[4].nodes[1].cable == 406
    p0, p1 = plain(src), plain(data)
    assert len(p0) == len(p1)
    changed = {i for i in range(len(p0)) if p0[i] != p1[i]}
    n41, n258, n42 = (net.branches[4].nodes[0].offset, net.branches[25].nodes[7].offset,
                      net.branches[4].nodes[1].offset)
    homes = n258 + W.TAIL_HOMES + 8          # the third home's entry
    allowed = ({n41 + 12, n41 + 13, n258 + N.N_HC, n258 + W.TAIL_HC, homes, n42 + N.N_CABLE,
                n42 + N.N_CABLE + 1}
               | set(range(W.P_FTG, W.P_FTG + 8)) | set(range(W.P_FTG_CABLE, W.P_FTG_CABLE + 4000))
               | set(range(W.P_HOMES, W.P_HOMES + 24)))
    assert changed <= allowed, sorted(changed - allowed)[:10]
    assert screen_of(reread(data)) == screen_of(d)


def test_inserting_and_deleting_lines():
    d, src = fresh()
    b4 = d.branch(4)
    b4.nodes.insert(1, line(d, 410))                  # above 4.2, as Insert does
    b4.nodes.insert(4, line(d, 410, ftg=60, hc=2,      # a new line with a tap
                            taps=[TapPlacement(part_id=next(
                                t.id for t in d.library.taps.values() if t.row == 5 and t.ports == 2),
                                ports=2)]))
    del d.branch(20).nodes[2]                          # 20.3 deleted
    d.renumber(b4)
    d.renumber(d.branch(20))
    data, _ = export_ntw(d, src)
    net = links_ok(data)
    assert len(net.branches[4].nodes) == 31 and len(net.branches[20].nodes) == 18
    new = net.branches[4].nodes[1]
    assert new.ftg == 0 and new.cable == 410 and not new.taps
    tapped = net.branches[4].nodes[4]
    assert (tapped.ftg, tapped.hc, [(t.row, t.ports) for t in tapped.taps]) == (60, 2, [(5, 2)])
    # new lines take ids below every id in use, and the design keeps them
    old = {n.id for b in N.read_network(plain(src)).branches.values() for n in b.nodes}
    assert new.id < min(old) and b4.nodes[1].rec == new.id
    assert screen_of(reread(data)) == screen_of(d)
    # saving again over the new file changes nothing
    again, _ = export_ntw(d, data)
    assert again == data


def test_placing_and_removing_amplifiers():
    d, src = fresh()
    lib = d.library
    le = next(a for a in lib.actives.values() if a.active_id == "11")
    n48 = d.branch(4).nodes[7]
    n48.amp, n48.amp_part, n48.amp_label = le.active_id, le.id, "AL00499"
    n413 = d.branch(4).nodes[12]
    n413.amp, n413.amp_part, n413.amp_label, n413.pads = "", None, "", []
    data, _ = export_ntw(d, src)
    net = links_ok(data)
    p = plain(data)
    got48 = net.branches[4].nodes[7]
    assert got48.active_index == le.index and got48.label == "AL00499"
    assert p[got48.offset + N.N_HAS_ACTIVE] == 1
    # the program's picks for a placed amplifier are written
    assert len(got48.pads) == 4
    got413 = net.branches[4].nodes[12]
    assert got413.active_index == 0 and p[got413.offset + N.N_HAS_ACTIVE] == 0
    back = reread(data)
    assert back.branch(4).nodes[7].amp == "11" and back.branch(4).nodes[7].amp_label == "AL00499"
    assert screen_of(back) == screen_of(d)


def test_new_and_deleted_branches():
    d, src = fresh()
    lib = d.library
    two_way = next(p for p in lib.passives.values() if p.coupler_id == 8 and p.record > 0)
    child = d.add_branch(4, 9)
    child.nodes = [line(d, 410, seq=1, ftg=120), line(d, 410, seq=2, ftg=80, hc=1)]
    d.branch(4).nodes[8].couplers.append(
        CouplerPlacement(part_id=two_way.id, coupler_id=8, branch=child.number))
    gone = d.remove_branch(44)
    assert gone == [44]
    data, _ = export_ntw(d, src)
    net = links_ok(data)
    # 44 gone: 45 becomes 44, the new branch 45
    assert len(net.branches) == 45
    new = net.branches[45]
    assert new.parent == (4, 9) and new.coupler_record == two_way.record
    assert [n.ftg for n in new.nodes] == [120, 80]
    assert 45 in net.branches[4].nodes[8].branches
    back = reread(data)
    assert back.branch(45).nodes[1].ftg == 80
    assert struct.unpack_from("<HH", plain(data), W.P_COUPLERS + 4 * two_way.record)[0] == \
        struct.unpack_from("<HH", plain(src), W.P_COUPLERS + 4 * two_way.record)[0] + 1


def test_a_copied_line_gets_its_own_id():
    d, src = fresh()
    b4 = d.branch(4)
    copy = Node.from_dict(b4.nodes[12].to_dict())      # 4.13, amplifier AL00416
    copy.amp_label = "AL00498"
    b4.nodes.insert(13, copy)
    d.renumber(b4)
    data, _ = export_ntw(d, src)
    net = links_ok(data)
    a, b = net.branches[4].nodes[12], net.branches[4].nodes[13]
    assert a.id != b.id and a.label == "AL00416" and b.label == "AL00498"
    p = plain(data)
    assert struct.unpack_from("<I", p, a.offset + W.N_OBJECT) != \
        struct.unpack_from("<I", p, b.offset + W.N_OBJECT)


def test_deleting_a_branch_closes_up_the_numbers():
    """As Lode Data does: the branches after a deleted one move up."""
    d, src = fresh()
    assert d.remove_branch(44) == [44]
    assert sorted(d.branches) == list(range(1, 45))
    moved = d.branch(44)
    assert (moved.parent_branch, moved.parent_node) == (5, 9)
    assert [c.branch for c in d.branch(5).nodes[8].couplers] == [44]
    assert d.branch(20).nodes[16].couplers == []
    data, _ = export_ntw(d, src)
    net = links_ok(data)
    assert len(net.branches) == 44 and net.branches[44].parent == (5, 9)
    assert screen_of(reread(data)) == screen_of(d)
