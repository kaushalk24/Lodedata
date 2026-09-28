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
    W._more_totals(rebuilt, None)
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


def _keyed_from_scratch():
    """The network keyed in Lode Data in the user's recording 2: a Ripple
    named AL004, two MULTI OUT couplers on lines of cable 2, and branch 2 of
    120 ft (2 homes, a /23/) and 130 ft (3 homes, a /20/)."""
    from hfc.importer import library_from_spec_set, parameters_from_spec_set
    from hfc.plant import Design
    from hfc.entry import resolve_active, resolve_coupler, resolve_tap
    params = parameters_from_spec_set(SPEC)
    d = Design(name="Untitled", parameters=params, library=library_from_spec_set(SPEC, params))
    d.ensure_feeder()
    lib = d.library
    b1 = d.branch(1)
    ripple = resolve_active(lib, "70")
    n = b1.nodes[0]
    n.amp, n.amp_part, n.amp_label = ripple.active_id, ripple.id, "AL004"
    n.cab, n.cab_part = 2, line(d, 2).cab_part
    for k in (2, 3):
        b1.nodes.append(line(d, 2, seq=k))
        part, _ = resolve_coupler(lib, "100")
        child = d.add_branch(1, k)
        b1.nodes[k - 1].couplers.append(CouplerPlacement(part_id=part.id, coupler_id=100,
                                                         branch=child.number))
    b2 = d.branch(2)
    b2.nodes[0].ftg, b2.nodes[0].hc = 120, 2
    b2.nodes.append(line(d, 2, seq=2, ftg=130, hc=3))
    for node, code in ((b2.nodes[0], "2.23"), (b2.nodes[1], "2.20")):
        tap = resolve_tap(lib, code, node.hc)
        node.taps = [TapPlacement(part_id=tap.id, ports=tap.ports, value_db=tap.tap_value_db)]
    return d


def test_an_empty_network_is_the_programs_own_empty_file():
    """File > New saved untouched (the user's BLANK test, checked byte for
    byte outside this test): one branch, one line, Untitled spec files."""
    p = W.join(W.blank())
    assert len(p) == 48791
    net = N.read_network(p)
    assert [len(b.nodes) for b in net.branches.values()] == [1]
    assert net.branches[1].nodes[0].id == 127999 and net.branches[1].end_id == 127998
    assert struct.unpack_from("<III", p, W.P_BRANCHES) == (1, 127997, 127999)
    assert net.saved_with == ["Untitled"] * 8
    assert p[:22] == b"Lode Data Network File" and p[129:161] == bytes(32)
    # and writing it back changes nothing
    out, _ = W.build(W.blank(), W.outs_from_plain(p), fresh=True)
    assert out == p


def test_every_total_the_file_keeps_is_rebuilt():
    """Pads/EQs by bank and value, power stops, connectors by cable,
    underground housings, and taps, couplers, splitters, in-line devices,
    line extenders, amplifiers and supplies: AL004's exactly."""
    d, src = fresh()
    p = plain(src)
    info = W.SpecInfo(
        line_extenders={a.index for a in d.library.actives.values() if a.name.startswith("LE")},
        points=d.parameters.equipment_points, housings=[tuple(h) for h in d.parameters.housings])
    t = W.tallies(p, info)
    assert t[W.P_POWER_STOPS] == 2
    assert t[W.P_PARTS + 4 * W.PARTS_LINE_EXTENDERS] == 15 and t[W.P_PARTS + 4 * W.PARTS_AMPLIFIERS] == 12
    assert t[W.P_HOUSINGS + 4 * 1 + 2] == 5 and t[W.P_HOUSINGS + 4 * 3 + 2] == 1
    rebuilt = bytearray(p)
    W._more_totals(rebuilt, info)
    assert bytes(rebuilt) == p


def test_a_network_keyed_from_scratch_is_written_as_a_new_network():
    d = _keyed_from_scratch()
    # Lode Data's own figures for it (recording 2)
    rows = {(r.branch, r.node, r.end): r for r in build(d).rows}
    assert tuple(round(v, 2) for v in rows[(2, 1, False)].levels.values()) == (46.41, 37.35, 17.55, 17.19)
    assert tuple(round(v, 2) for v in rows[(2, 2, False)].levels.values()) == (42.70, 36.25, 18.55, 17.80)
    assert tuple(round(v, 2) for v in rows[(2, 3, True)].levels.values()) == (41.60, 35.55, 19.25, 18.50)
    assert [round(v, 2) for v in rows[(2, 1, False)].tap_levels[0]] == [23.41, 14.45, 40.45, 38.29]
    data, report = export_ntw(d, None, name="SCRATCH", header=NTW.read_bytes()[:512])
    net = links_ok(data)
    assert len(net.branches) == 3 and [len(b.nodes) for b in net.branches.values()] == [3, 2, 1]
    ids = sorted(n.id for b in net.branches.values() for n in b.nodes)
    assert ids[-1] == 127999 and ids[0] > 127980          # counted again from the first
    p = plain(data)
    assert W._stored_name(p) == "SCRATCH"
    assert net.saved_with == ["WV750-2026"] * 5 + ["Untitled"] * 3
    # nothing of AL004's is in it: what is not this network is the empty file's
    empty = W.join(W.blank(NTW.read_bytes()[:512]))
    assert p[:512] == empty[:512]
    for at in (23481, 36121, 36125, 36129):
        assert struct.unpack_from("<I", p, at)[0] == 0
    first = net.branches[1].nodes[0]
    # the Ripple, banks 4, holds each pad and EQ as (3, 0, 0), as on AL004
    assert p[first.offset + N.N_PADS:first.offset + N.N_PADS + 12] == b"\x03\x00\x00" * 4
    back = reread(data)
    assert screen_of(back) == screen_of(d)
    assert back.branch(1).nodes[0].amp_label == "AL004"
    # and saving it again builds on the file it now is
    again, _ = export_ntw(d, data, name="SCRATCH")
    assert again == data


def test_hc_is_red_when_the_homes_are_more_than_the_ports():
    """Recording 2: 2.2's 3 homes on a 2-port /20/ show red, 2.1's 2 on a
    2-port /23/ do not; a 4-port tap turns it back (the user)."""
    from hfc.entry import resolve_tap
    d = _keyed_from_scratch()
    red = lambda: {(r.branch, r.node) for r in build(d).rows if r.hc_severity == "red"}  # noqa: E731
    assert red() == {(2, 2)}
    node = d.branch(2).nodes[1]
    tap = resolve_tap(d.library, "4.20", node.hc)
    node.taps = [TapPlacement(part_id=tap.id, ports=tap.ports, value_db=tap.tap_value_db)]
    assert red() == set()
    node.taps, node.hc = [], 1                      # homes and no tap
    assert red() == {(2, 2)}
    two = resolve_tap(d.library, "2.20", 1)
    node.taps = [TapPlacement(part_id=two.id, ports=2), TapPlacement(part_id=two.id, ports=2)]
    node.hc = 4                                     # two 2-port taps: 4 ports
    assert red() == set()
    node.hc = 5
    assert red() == {(2, 2)}


def test_parts_the_spec_set_cannot_name_are_kept():
    """Opened with another spec set (a node upgrade), an active or tap it
    has no entry for stays in the file as it was, and still counts."""
    d, src = fresh()
    amp = d.branch(4).nodes[12]                      # AL00416's bridger, index 13
    tap = next(n for b in d.branches.values() for n in b.nodes if n.taps and n.taps[0].part_id)
    assert amp.amp
    amp.amp, amp.amp_part, amp.kept_active = "", None, 13
    tap.taps[0] = TapPlacement()                     # as the importer leaves an unknown tap
    data, _ = export_ntw(d, src)
    assert plain(data) == plain(src)


def test_the_spec_file_mismatch_lines():
    """The program's box on opening with other spec files: one line a file."""
    from hfc.importer import spec_mismatch
    net = N.read_network(plain(NTW.read_bytes()))
    assert spec_mismatch(net, "WV750-2026") == []
    lines = spec_mismatch(net, "")
    assert lines[:5] == [[w, "Project spec file loaded does not match spec file 'WV750-2026' saved with"]
                         for w in ("Parameters", "Actives", "Taps", "Couplers", "Cables")]
    assert lines[5:] == [["Prices", "Loaded."], ["Performance", "Loaded."], ["Map Grid", "Loaded."]]


def test_a_new_network_is_laid_out_as_the_program_lays_one_out():
    """The user's S3, keyed in Lode Data from an empty network: a Ripple on
    1.1 (not named), 1.2 100 ft on 406 with 2 homes and a 2.20, 1.3 with 4
    and a 4.20, a coupler 100 on 1.2 and 2.1 like 1.2.  Written from the
    empty file, the app's bytes are Lode Data's but for the two counts not
    decoded (23483, 36129) and where the cursor was; these are the facts."""
    tap = lambda code: [(3, code), None, None, None]                  # noqa: E731
    b1 = W.BranchOut(nodes=[
        W.NodeOut(active_index=22, pad_banks=[3, 3, 3, 3], taps=[None] * 4),
        W.NodeOut(ftg=100, hc=2, cable=406, taps=tap(0), branches=[2]),
        W.NodeOut(ftg=100, hc=4, cable=406, taps=tap(1))])
    b2 = W.BranchOut(nodes=[W.NodeOut(ftg=100, hc=2, cable=406, taps=tap(0))],
                     coupler_record=11, parent=(1, 2))
    plain, ids = W.build(W.blank(), [b1, b2], name="S3", spec="WV750-2026", fresh=True)
    # ids: the line and end line the network started with, then as keyed
    assert ids == {"nodes": [[127999, 127997, 127996], [127994]], "ends": [127998, 127995]}
    assert struct.unpack_from("<I", plain, W.P_NEXT_ID)[0] == 127993
    net = N.read_network(plain)
    first = net.branches[1].nodes[0]
    # a Ripple not yet named stays on the short record, pads (3, 0, 0)
    assert plain[first.offset + N.N_HAS_ACTIVE] == 0
    assert plain[first.offset + N.N_PADS:first.offset + N.N_PADS + 12] == b"\x03\x00\x00" * 4
    raw = W.split(plain)
    # branch 2's head: a keyed line's, pads (0, 0, 0)
    assert raw.branches[1].head[108:120] == bytes(12)
    # Prices, Performance, Map Grid: Untitled over the set's name
    for k in (5, 6, 7):
        at = W.P_SPECS[1] + 261 * k
        assert plain[at:at + 11] == b"Untitled\x006\x00"
    assert len(plain) == 56715


def test_an_active_placed_is_counted_by_its_place_in_the_actives_table():
    """The user placed 88 -- WV750's item 40, FML1G7J ALC LE -- on AL004 4.2:
    Lode Data counted it an amplifier (the block reads 1-0-0 9-7-0, 127 homes,
    631 ft), held 0 in its pads and EQs (NPB-0 SEQ-750-SCS6 NPB-0 MEQ-42-0)
    and showed its levels 39.66 35.67 18.96 17.69 in, 49 38 21 21 out."""
    from hfc.entry import resolve_active
    d, src = fresh()
    part = resolve_active(d.library, "88")
    assert part.index == 40
    n = d.branch(4).nodes[1]
    n.amp, n.amp_part, n.pads = part.active_id, part.id, [0, 0, 0, 0]
    rows = {(r.branch, r.node): r for r in build(d).rows if not r.end}
    r = rows[(4, 2)]
    assert [round(v, 2) for v in r.levels.values()] == [39.66, 35.67, 18.96, 17.69]
    assert [round(v, 2) for v in r.out_levels.values()] == [49.0, 38.0, 21.0, 21.0]
    assert (r.block["above"], r.block["below"]) == ([1, 0, 0], [9, 7, 0])
    assert (r.block["homes"], r.block["same_cable"]) == (127, 631)
    assert r.block["distances"] == [631] * 5 and r.block["losses"] == [9.34] * 3
    assert rows[(4, 4)].block["above"] == [1, 0, 0] and rows[(4, 4)].block["below"] == [8, 7, 0]
    a = r.amp_info
    assert a["parts"] == ["NPB-0", "NPB-0", "SEQ-750-SCS6", "MEQ-42-0"]
    assert (a["fwd_pad"], a["fwd_eq"], a["ret_pad"], a["ret_eq"]) == ("0", "SCS6", "0", "0")
    assert (a["cascade"], a["supply"], a["homes_down"]) == (1, "A", 127)
    # saved, it is an amplifier in the file's totals and holds (bank - 1, 0)
    data, _ = export_ntw(d, src)
    p = plain(data)
    net = N.read_network(p)
    nd = net.branches[4].nodes[1]
    assert nd.active_index == 40 and p[nd.offset + N.N_HAS_ACTIVE] == 0     # not named
    assert p[nd.offset + N.N_PADS:nd.offset + N.N_PADS + 12] == bytes([1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0])
    assert struct.unpack_from("<HH", p, W.P_PARTS + 4 * W.PARTS_AMPLIFIERS) == (13, 0)
    assert struct.unpack_from("<HH", p, W.P_PARTS + 4 * W.PARTS_LINE_EXTENDERS) == (15, 1)
