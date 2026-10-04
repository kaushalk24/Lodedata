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


def test_h043a_test_list_is_lodes():
    """N2 (4 Oct): all 12 lines, yellow, in Lode's order."""
    ntw, spec = _paths("H043A_MID.ntw")
    d, _ = design_from_ntw(ntw, spec)
    assert SC.build(d).tests == [("yellow", m) for m in (
        "Tap(1002)  0.08 over window at 2.25.", "Tap(5)  0.72 below window at 2.25.",
        "Tap(1002)  1.00 over window at 15.44.", "Tap(5)  0.69 below window at 33.6.",
        "Tap(1002)  0.50 over window at 38.6.", "Tap(5)  0.98 below window at 38.9.",
        "Tap(1002)  0.16 below min at 64.3.", "Tap(1002)  0.18 below min at 64.5.",
        "Tap(1002)  1.00 over window at 66.3.", "Tap(1002)  1.80 over window at 67.1.",
        "Tap(1002)  1.17 over window at 74.2.", "Tap(1002)  1.98 over window at 89.2.")]


@pytest.mark.parametrize("name", ["H043A_MID.ntw", "H043B_MID.ntw"])
def test_a_network_with_a_pcd_saves_as_it_came(name):
    """The PCD's networks are listed before branch 1 and its branch head
    holds coupler record 999: both kept.  The PCD is no coupler in the
    parts count and adds one connector on its line's cable.  The
    underground housings' tally is Lode's too (H043A_MID 179/23/8/7 of
    housings 1/3/4/5, H043B_MID 82/11/4/2): the file comes back byte for
    byte."""
    ntw, spec = _paths(name)
    src = ntw.read_bytes()
    d, _ = design_from_ntw(src, spec)
    out, _ = export_ntw(d, src, name=ntw.stem)
    assert out == src
    a = src[:PAYLOAD_START] + deobfuscate(src[PAYLOAD_START:])
    assert struct.unpack_from("<I", a, W.P_PCDS)[0]


def test_h043b_underground_housings_as_lode_draws_them():
    """n5a-n5f: the (n) under the node numbers.  A branch's 0-ft start gets
    none (7.1, its supply alone), the place it is at holds it (2.5); 2.9 and
    3.7 are an FM902T (16) and the tap on the 0-ft 8.1 / 4.1; 13.1 the
    FM902T alone (17.1's tap is on cable 0)."""
    ntw, spec = _paths("H043B_MID.ntw")
    d, _ = design_from_ntw(ntw, spec)
    got = {(r.branch, r.node): r.housing for r in SC.build(d).rows if not r.end}
    lode = {(1, 5): 1, (1, 6): 4, (1, 7): 0, (1, 8): 0, (1, 13): 4, (1, 14): 0,
            (2, 6): 0, (2, 9): 4, (2, 10): 1, (2, 11): 1, (3, 4): 0, (3, 5): 0, (3, 6): 0,
            (3, 7): 4, (3, 8): 1, (3, 9): 1, (13, 1): 3, (13, 2): 0, (13, 3): 1, (13, 4): 1,
            (13, 5): 0, (13, 6): 3, (7, 1): 0}
    assert {k: got[k] for k in lode} == lode
