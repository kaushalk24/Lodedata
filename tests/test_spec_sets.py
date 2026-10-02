"""Every spec set under samples/: read whole, by the files' own layout.

Skipped for the sets not present.  tools/spec_coverage.py lists what in each
file is still unexplained.
"""
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from lodedata import specs as S                                      # noqa: E402
import spec_coverage                                                  # noqa: E402

SAMPLES = Path(os.environ.get("LODEDATA_SAMPLES", ROOT / "samples"))
SETS = sorted({p.with_suffix("") for p in SAMPLES.rglob("*.par")
               if "partest" not in p.parts and p.with_suffix(".atv").exists()}) \
    if SAMPLES.is_dir() else []


def _set(name):
    base = next((b for b in SETS if b.name == name), None)
    if base is None:
        pytest.skip(f"{name} not in samples")
    return base


@pytest.mark.parametrize("base", SETS, ids=[b.name for b in SETS])
def test_every_file_is_a_layout_checked_against_lode(base):
    for ext in ("cbl", "cpr", "atv", "tap", "par"):
        assert spec_coverage.audit(base.with_suffix("." + ext))["seen"], ext


@pytest.mark.parametrize("base", SETS, ids=[b.name for b in SETS])
def test_every_named_active_in_the_table_is_read(base):
    # the table is 251 records (51 in the older file), read by that count:
    # every record with a name is an active
    data = base.with_suffix(".atv").read_bytes()
    classic = S._classic(data)
    start, stride, count, width = (1021, 318, 51, 15) if classic else (3021, 362, 251, 25)
    named = [i for i in range(1, count)
             if S._name(data[start + stride * i + 5:start + stride * i + 5 + width])]
    acts = S.read_actives(data)
    assert [a.index for a in acts] == named
    steps = S.CLASSIC_ATV_STEPS[1] if classic else S.ATV_STEPS[1]
    assert all(len(a.power_draw) <= steps for a in acts)


def test_kermits_actives_hold_casc_15():
    # the four bytes before the levels: KERMIT's actives Valid at Casc. 1-14
    # are Valid at 15 as well (bit 16)
    acts = {a.active_id: a for a in S.read_actives(_set("KERMIT750-2026").with_suffix(".atv").read_bytes())}
    assert acts["11"].cascading == 0x1FFFD and acts["70"].cascading == 0x7
    # and seven power steps, 38 V to 90 V on the MB-750D-H
    assert [v for v, _ in acts["63"].power_draw] == [38.0, 45.0, 52.0, 60.0, 70.0, 80.0, 90.0]


def test_the_current_record_keeps_in_and_out_at_f3():
    # +171 / +195: WV750's bridger 41 holds 10.1 / 43.0 there, as WVEXT862's
    # FNB99 41 does at +127 / +151 of the older record
    acts = {a.active_id: a for a in S.read_actives(_set("WV750-2026").with_suffix(".atv").read_bytes())}
    assert acts["41"].f3_levels == [10.1, 43.0] and acts["11"].f3_levels == [0.0, 0.0]
