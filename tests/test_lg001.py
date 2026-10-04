"""LG001 (WV750-2026's) opened with KERMIT750-2026 and five actives keyed on
branch 2, the user's 30a-30e (4 Oct): skipped unless both are under samples/.

KERMIT has no cable 24, so branch 2 loses nothing along its spans.  Every
figure on the five screens is the app's: the levels, the brackets, each
active's box and pads, every cyan block.  FM901e-B, FM902B and FM902T get
no forward EQ: 11 dB of tilt arrives where each wants less than none, and
with "Allow Over Equalization" unticked no EQ fits.
"""
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "app"), str(ROOT / "tools")]

from hfc.importer import design_from_ntw                              # noqa: E402
from hfc.screen import build, active_inputs, repick, as_shown         # noqa: E402
from hfc.entry import resolve_active, config_slot                     # noqa: E402

SAMPLES = Path(os.environ.get("LODEDATA_SAMPLES", ROOT / "samples"))


@pytest.fixture(scope="module")
def keyed():
    ntw = next(SAMPLES.rglob("LG001.ntw"), None) if SAMPLES.is_dir() else None
    spec = next(SAMPLES.rglob("KERMIT750-2026.par"), None) if SAMPLES.is_dir() else None
    if ntw is None or spec is None:
        pytest.skip("LG001 or KERMIT750-2026 not in samples")
    d = design_from_ntw(ntw.read_bytes(), spec.with_suffix(""))[0]
    for line, code in ((11, "65"), (21, "68"), (35, "69"), (47, "78"), (55, "88")):
        before = active_inputs(d)
        n = d.branch(2).nodes[line - 1]
        part = resolve_active(d.library, code)
        n.kept_active, n.pads = 0, [0, 0, 0, 0]
        n.amp_config = config_slot(part, code)
        n.amp = part.config_ids[n.amp_config] if n.amp_config else part.active_id
        n.amp_part = part.id
        repick(d, before, {id(n)})
    scr = build(d)
    return {r.node: r for r in scr.rows if r.branch == 2 and not r.end}


BOXES = {
    11: ("FM901e-B", "13", "VOID", "20", "0", [1886, 1886, 1886, 1886, 1886], 1, 37,
         ["NPB-13", "NPB-20", "<NO FWD EQ>", "MEQ-42-0"]),
    21: ("FM902B", "Flag", "", "Flag", "0", [1700, 3586, 1700, 1700, 3586], 2, 18,
         ["NPB-Flag", "NPB-Flag", "<NO FWD EQ>", "MEQ-85-0"]),
    35: ("FM902T", "Flag", "", "Flag", "0", [2877, 6463, 0, 2877, 6463], 3, 9,
         ["NPB-Flag", "NPB-Flag", "<NO FWD EQ>", "MEQ-85-0"]),
    47: ("FML332", "120", "CS9", "Flag", "0", [2738, 9201, 2738, 2738, 9201], 4, 8,
         ["NPB-120", "NPB-Flag", "CE-120-CS9", "MEQ-85-0"]),
    55: ("FML1G7J AGC LE", "10", "4", "11", "0", [665, 9866, 357, 665, 9866], 5, 4,
         ["NPB-10", "NPB-11", "SEQ-1G-4", "MEQ-42-0"]),
}


def test_each_keyed_active_as_its_box_shows_it(keyed):
    for line, (kind, fp, fe, rp, re_, dist, cascade, homes, parts) in BOXES.items():
        a = keyed[line].amp_info
        got = (a["type"], a["fwd_pad"], a["fwd_eq"], a["ret_pad"], a["ret_eq"],
               [round(a[k]) for k in ("aerial_prev", "aerial_start", "total_split",
                                      "total_prev", "total_start")],
               a["cascade"], a["homes_down"], a["parts"])
        assert got == (kind, fp, fe, rp, re_, dist, cascade, homes, parts), line
        assert a["supply"] == "B"


BLOCKS = {
    11: ([1886, 1886, 1886, 1886, 1886], [0.0, 0.0, 0.0], [1, 0, 0], [5, 4, 0], 37, 1886),
    21: ([1700, 3586, 1700, 1700, 3586], [0.0, 0.0, 0.0], [2, 0, 0], [4, 3, 0], 18, 1700),
    33: ([2877, 6463, 2877, 2877, 6463], [0.0, 0.0, 0.0], [2, 0, 0], [3, 2, 0], 9, 2877),
    34: ([2877, 6463, 0, 2877, 6463], [0.0, 0.0, 0.0], [2, 0, 0], [3, 2, 0], 9, 0),
    35: ([2877, 6463, 0, 2877, 6463], [0.0, 0.0, 0.0], [3, 0, 0], [3, 2, 0], 9, 0),
    36: ([0, 6463, 0, 0, 6463], [0.0, 0.0, 0.0], [3, 0, 0], [2, 1, 0], 8, 0),
    47: ([2738, 9201, 2738, 2738, 9201], [0.0, 0.0, 0.0], [4, 0, 0], [2, 1, 0], 8, 2738),
    48: ([0, 9201, 0, 0, 9201], [0.0, 0.0, 0.0], [4, 0, 0], [1, 1, 0], 8, 0),
    53: ([308, 9509, 186, 308, 9509], [3.31, 5.48, 5.48], [4, 0, 0], [1, 1, 0], 4, 186),
    55: ([665, 9866, 357, 665, 9866], [6.35, 11.84, 11.84], [5, 0, 0], [1, 1, 0], 4, 357),
    56: ([0, 9866, 0, 0, 9866], [0.0, 0.0, 11.84], [5, 0, 0], [0, 1, 0], 4, 0),
}


def test_the_expanded_display_and_the_brackets(keyed):
    for line, (dist, loss, above, below, homes, ftg) in BLOCKS.items():
        b = keyed[line].block
        got = ([round(v) for v in b["distances"]], [round(v, 2) for v in b["losses"]],
               b["above"], b["below"], b["homes"], round(b["same_cable"]))
        assert got == (dist, loss, above, below, homes, ftg), line
    for line in (8, 9, 10, 12, 13, 18, 19, 20, 22, 23, 32, 37, 44, 45, 46, 49, 52, 54, 57):
        assert not keyed[line].block, line
    cpl = {k: keyed[k].couplers for k in (11, 21, 33, 34, 35, 36, 48, 53, 56)}
    assert cpl == {11: ["2<6>"], 21: ["2{17}"], 33: ["17(8)"], 34: ["12(9)"], 35: ["2{11}"],
                   36: ["3(10)"], 48: ["12{12}"], 53: ["3[14]"], 56: ["9(15)"]}
    # the MB-JMP on 2.33 is the FM902T's (2.35), but above it: red
    assert keyed[33].coupler_severity == ["red"] and keyed[34].coupler_severity == [""]


def test_the_levels(keyed):
    lv = {k: [as_shown(keyed[k].levels[f]) for f in sorted(keyed[k].levels, reverse=True)]
          for k in (8, 11, 12, 21, 22, 35, 36, 47, 49, 52, 53, 54, 55, 56, 57)}
    want = {8: [37.10, 26.10, 17.00, 17.00], 11: [37.10, 26.10, 17.00, 17.00],
            12: [49.00, 38.00, 21.00, 21.00], 21: [49.00, 38.00, 21.00, 21.00],
            22: [49.00, 38.00, 17.00, 17.00], 35: [46.80, 36.50, 18.50, 18.50],
            36: [40.00, 29.00, 17.00, 17.00], 47: [35.10, 24.60, 21.40, 21.40],
            49: [44.63, 35.95, 18.98, 18.66], 52: [38.42, 33.31, 21.50, 20.70],
            53: [38.42, 33.31, 21.50, 20.70], 54: [29.19, 27.82, 26.85, 25.42],
            55: [27.16, 27.31, 27.29, 25.56], 56: [49.00, 38.00, 21.00, 21.00],
            57: [44.07, 35.69, 23.24, 22.95]}
    assert lv == want
    assert keyed[57].taps == ["/27/"] and keyed[57].tap_severity == ["yellow"]
