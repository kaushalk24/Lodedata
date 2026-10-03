"""Bullhead's H043A_MID and H043B_MID on BH1GHzMid (the user's files, 3 Oct;
skipped unless they and the spec set are under samples/).

The two share a power supply through a PCD.  Every amplifier and line
extender in them holds the pads and EQs the program picked for the levels it
saw, so each one checks the levels the app computes there: all 48, 192
values, once the FM902T's own output split ("FMT Split", -9 at the forward
columns, 0 at the return) is read with its sign and its zeros.  H043B's Test
list is the user's 2a, both lines.
"""
import os
import struct
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "app"), str(ROOT / "tools")]

from hfc.importer import design_from_ntw                              # noqa: E402
from hfc.exporter import export_ntw                                   # noqa: E402
from hfc import screen as SC                                          # noqa: E402
from lodedata import writer as W                                      # noqa: E402
from lodedata.obfuscation import deobfuscate, PAYLOAD_START           # noqa: E402

SAMPLES = Path(os.environ.get("LODEDATA_SAMPLES", ROOT / "samples"))


def _paths(name):
    ntw = next(SAMPLES.rglob(name), None) if SAMPLES.is_dir() else None
    spec = next(SAMPLES.rglob("BH1GHzMid.par"), None) if SAMPLES.is_dir() else None
    if ntw is None or spec is None:
        pytest.skip(f"{name} or BH1GHzMid not in samples")
    return ntw, spec.with_suffix("")


@pytest.mark.parametrize("name, actives", [("H043A_MID.ntw", 32), ("H043B_MID.ntw", 16)])
def test_every_stored_pad_and_eq_is_the_pick_for_the_apps_levels(name, actives):
    ntw, spec = _paths(name)
    d, _ = design_from_ntw(ntw, spec)
    s = SC.build(d)
    checked = 0
    for r in s.rows:
        if r.end:
            continue
        nd = d.branch(r.branch).nodes[r.node - 1]
        part = d.library.actives.get(nd.amp_part) if nd.amp else None
        if not part or len(part.pad_eq) != 4 or len(nd.pads) < 4:
            continue
        assert SC.choose_pads_eqs(part, r.levels, d.parameters) == nd.pads[:4], (r.branch, r.node)
        checked += 1
    assert checked == actives


def test_h043b_test_list_is_lodes():
    ntw, spec = _paths("H043B_MID.ntw")
    d, _ = design_from_ntw(ntw, spec)
    assert SC.build(d).tests == [("yellow", "Tap(1002)  1.18 over window at 12.2."),
                                 ("yellow", "Tap(1002)  1.00 over window at 18.8.")]


@pytest.mark.parametrize("name", ["H043A_MID.ntw", "H043B_MID.ntw"])
def test_a_network_with_a_pcd_saves_as_it_came_but_the_underground_housings(name):
    """The PCD's networks are listed before branch 1 and its branch head
    holds coupler record 999: both kept.  The PCD is no coupler in the
    parts count and adds one connector on its line's cable.  Only the
    underground housings' tally differs (not decoded for these yet)."""
    ntw, spec = _paths(name)
    src = ntw.read_bytes()
    d, _ = design_from_ntw(src, spec)
    out, _ = export_ntw(d, src, name=ntw.stem)
    a = src[:PAYLOAD_START] + deobfuscate(src[PAYLOAD_START:])
    b = out[:PAYLOAD_START] + deobfuscate(out[PAYLOAD_START:])
    assert len(a) == len(b)
    differ = {i for i in range(len(a)) if a[i] != b[i]}
    housings = range(W.P_HOUSINGS, W.P_HOUSINGS + 4 * 15)
    assert differ and all(i in housings for i in differ)
    assert struct.unpack_from("<I", a, W.P_PCDS)[0]
