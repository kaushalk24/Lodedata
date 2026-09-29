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
