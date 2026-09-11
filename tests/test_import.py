"""Lode Data file reading and spec-set upgrade."""
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))
sys.path.insert(0, str(ROOT / "tools"))

from hfc.importer import library_from_spec_set, inspect_ntw, relink_library, _tokens
from hfc.plant import Design, Node
from lodedata.obfuscation import NTW_KEY, deobfuscate, obfuscate, recover_key

# Real Lode Data files to check the readers against.  Drop them anywhere under
# ./samples (or point LODEDATA_SAMPLES at a directory) and these tests run;
# without them they skip, so the suite still passes on a clean checkout.
SAMPLES = Path(os.environ.get("LODEDATA_SAMPLES", ROOT / "samples"))


def _find(pattern: str) -> Path | None:
    if not SAMPLES.is_dir():
        return None
    return next(iter(sorted(SAMPLES.rglob(pattern))), None)


def _spec_base(stem_contains: str) -> Path | None:
    hit = _find(f"*{stem_contains}*.cbl")
    return hit.with_suffix("") if hit else None


KERMIT = _spec_base("KERMIT") or SAMPLES / "missing"
WVBECK = _spec_base("WVBeck") or SAMPLES / "missing"
NTW = _find("*.ntw") or SAMPLES / "missing.ntw"

needs_samples = pytest.mark.skipif(
    not KERMIT.with_suffix(".cbl").exists() or not WVBECK.with_suffix(".cbl").exists(),
    reason="sample spec sets not found; put them under ./samples "
           "or set LODEDATA_SAMPLES")


def test_obfuscation_round_trips():
    plain = bytes(range(256)) * 7
    assert deobfuscate(obfuscate(plain)) == plain


@needs_samples
def test_ntw_key_is_the_known_constant():
    payload = NTW.read_bytes()[512:]
    assert recover_key(payload) == NTW_KEY


@needs_samples
def test_ntw_header_is_read():
    info = inspect_ntw(NTW)
    assert info["magic"] == "Lode Data Network File"
    assert info["app_version"] == "Design 12.11"
    assert info["keystream_matches_known_key"] is True
    # a design file is mostly pre-allocated space
    assert 0 < info["live_percent"] < 10


@needs_samples
def test_cable_loop_resistance_matches_published_values():
    lib = library_from_spec_set(KERMIT)
    by_name = {c.name: c for c in lib.cables.values()}
    for name, expected in [("EX .500P3 AER", 1.72), ("EX .625P3 AER", 1.07),
                           ("EX .750P3 AER", 0.76), ("EX .875P3 AER", 0.55),
                           ("EX RG-6 AER", 36.0)]:
        assert abs(by_name[name].loop_resistance_ohm_per_1000ft - expected) < 0.01


@needs_samples
def test_tap_port_slots_decode_to_the_value_in_the_part_number():
    """The strongest check available on the tap layout.

    RMT2008-RF-20 is an 8-port 20 dB tap and RMT2002-RF-23 a 2-port 23 dB one.
    Reading the tap-value block at each port slot must return exactly those
    numbers -- which it does, for a vendor whose part numbers were never used
    to derive the offsets.
    """
    lib = library_from_spec_set(WVBECK)
    by_name = {t.name: t for t in lib.taps.values()}
    for part, ports, value in [("RMT2008-RF-20", 8, 20.0),
                               ("RMT2002-RF-23", 2, 23.0),
                               ("RMT2004-RF-17", 4, 17.0)]:
        tap = by_name[part]
        assert tap.ports == ports
        assert tap.tap_value_db == value
        assert abs(tap.tap_db(860) - value) < 0.01


@needs_samples
def test_tap_insertion_loss_rises_with_port_count():
    """A tap of the same value costs more through-loss the more ports it has."""
    lib = library_from_spec_set(WVBECK)
    by_name = {t.name: t for t in lib.taps.values()}
    two, four = by_name["RMT2002-RF-23"], by_name["RMT2004-RF-23"]
    assert four.through_db(860) > two.through_db(860)
    # insertion loss is far smaller than the tap value
    assert two.through_db(860) < two.tap_db(860) / 4


@needs_samples
def test_tap_port_slots_hold_across_two_vendors():
    for spec in (KERMIT, WVBECK):
        lib = library_from_spec_set(spec)
        assert {t.ports for t in lib.taps.values()} <= {2, 4, 6, 8}
        assert len(lib.taps) > 15


def test_token_split_ignores_punctuation():
    assert _tokens("EX .625P3 AER") == frozenset({"EX", "625P3", "AER"})


@needs_samples
def test_spec_upgrade_keeps_the_design_wired_up():
    """Swapping spec sets must keep every span pointing at the right cable."""
    old = library_from_spec_set(KERMIT)
    new = library_from_spec_set(WVBECK)
    d = Design(name="t", library=old)
    feeder = d.ensure_feeder()
    picks = ["EX .625P3 AER", "EX .875P3 UG", "EX .500P3 AER"]
    for name in picks:
        cid = next(c.id for c in old.cables.values() if c.name == name)
        feeder.nodes.append(Node(ftg=100, cab_part=cid))
    d.renumber(feeder)

    report = relink_library(d, new)
    assert report["matched"] > 40
    resolved = [new.cables[n.cab_part].name for n in feeder.nodes if n.cab_part]
    # size and aerial/underground must both survive the upgrade
    assert resolved == ["625P3 AER EXT", "875P3 UG EXT", "500P3 AER EXT"]
    assert d.validate() == []


@needs_samples
def test_upgrade_never_crosses_cable_sizes():
    old = library_from_spec_set(KERMIT)
    new = library_from_spec_set(WVBECK)
    d = Design(name="t", library=old)
    d.ensure_feeder()
    report = relink_library(d, new)
    for line in report["fuzzy"]:
        if not line.startswith("cables:"):
            continue
        before, after = line[len("cables:"):].split("->")
        digits_before = {t for t in _tokens(before) if any(c.isdigit() for c in t)}
        digits_after = {t for t in _tokens(after.split("(")[0]) if any(c.isdigit() for c in t)}
        assert digits_before & digits_after, line


@needs_samples
def test_cable_losses_land_on_the_four_design_frequencies():
    from hfc.model import DesignParameters
    params = DesignParameters(forward_low_mhz=54, forward_high_mhz=860,
                              return_low_mhz=5, return_high_mhz=42)
    lib = library_from_spec_set(KERMIT, params)
    c = next(c for c in lib.cables.values() if c.name == "EX .625P3 AER")
    at = dict((f, v) for f, v in c.attenuation)
    # the four columns of the cable spec: Rl, Rh, Low, High
    assert at == {5.0: 0.13, 42.0: 0.39, 54: 0.45, 860: 1.78}


@needs_samples
@pytest.mark.parametrize("spec", ["KERMIT", "WVBECK"])
def test_loss_columns_sit_at_the_expected_design_frequencies(spec):
    """Columns 0,1,6,7 are High, Low, Rh and Rl -- shown by their ratios.

    The values are hand-typed from manufacturer charts so no single cable
    follows the sqrt(f) law exactly, but across a whole spec file the median
    ratios pin down which frequency each column belongs to.  A wrong column
    assignment would be nowhere near these numbers.
    """
    import math
    import statistics
    import struct

    path = (KERMIT if spec == "KERMIT" else WVBECK).with_suffix(".cbl")
    data = path.read_bytes()
    low_over_high, rh_over_low, rl_over_low = [], [], []
    for r in range(100):
        seg = data[512 + r * 394: 512 + (r + 1) * 394]
        if seg[0] != 0x6F or not seg[5:30].split(b"\0")[0].strip():
            continue
        v = [x / 1e6 for x in struct.unpack_from("<10i", seg, 34)]
        if v[0] and v[1]:
            low_over_high.append(v[1] / v[0])
        if v[1] and v[6]:
            rh_over_low.append(abs(v[6]) / v[1])
        if v[1] and v[7]:
            rl_over_low.append(abs(v[7]) / v[1])

    assert len(low_over_high) >= 20
    # forward high sits about 16x the forward low: 54 MHz against 860
    assert abs(statistics.median(low_over_high) - math.sqrt(54 / 860)) < 0.02
    # return high is the 42 MHz column, return low the 5 MHz one
    assert abs(statistics.median(rh_over_low) - math.sqrt(42 / 54)) < 0.02
    assert abs(statistics.median(rl_over_low) - math.sqrt(5 / 54)) < 0.02


@needs_samples
@pytest.mark.parametrize("spec", ["KERMIT", "WVBECK"])
def test_even_cable_ids_are_aerial_and_odd_are_underground(spec):
    lib = library_from_spec_set(KERMIT if spec == "KERMIT" else WVBECK)
    checked = 0
    for c in lib.cables.values():
        name = c.name.upper()
        if "AER" in name or name.endswith(" AE"):
            expected = "aerial"
        elif "UG" in name or "UNDER" in name:
            expected = "underground"
        else:
            continue
        assert expected in c.notes, f"{c.name}: {c.notes}"
        checked += 1
    assert checked >= 20


@needs_samples
def test_directional_couplers_decode_to_their_rated_value():
    """RLDC-8/12/16 must come out as a real DC family.

    Port 0 is the through leg, the rest are tap legs -- the manual gives the
    Tap columns before the Thru columns in the file.
    """
    lib = library_from_spec_set(WVBECK)
    by_name = {p.name: p for p in lib.passives.values()}
    for part, rated in [("RLDC-8-15A", 8), ("RLDC-12-15A", 12), ("RLDC-16-15A", 16)]:
        thru, tap = by_name[part].port_losses[0], by_name[part].port_losses[1]
        assert abs(tap - rated) < 1.0, (part, tap)
        assert thru < tap
    # tighter coupling costs more on the through leg
    assert by_name["RLDC-8-15A"].port_losses[0] > by_name["RLDC-16-15A"].port_losses[0]


@needs_samples
def test_coupler_ids_and_tap_legs_match_the_parts():
    from lodedata.specs import load_spec_set
    spec = load_spec_set(WVBECK)
    by_name = {c.name: c for c in spec.couplers}
    # "helpful to use intuitive Coupler IDs, for instance 2 for a 2 way
    # splitter or 8 for a DC 8"
    assert by_name["RLS10-2-15A"].code == 2.0
    assert by_name["RLDC-8-15A"].code == 8.0
    assert by_name["RLDC-16-15A"].code == 16.0
    # a 3-way splitter creates two branches, a 2-way one
    assert by_name["RLS10-3-15A"].tap_legs == 2
    assert by_name["RLS10-2-15A"].tap_legs == 1
    # the internal-coupler flag is set on the part that says so
    assert by_name["INT 2-WAY"].internal


@needs_samples
def test_actives_carry_in_and_out_levels_at_the_four_frequencies():
    lib = library_from_spec_set(KERMIT)
    by_name = {a.name: a for a in lib.actives.values()}

    ble = by_name["BLE-7-750PSS"]
    assert [ble.in_forward_high, ble.in_forward_low,
            ble.in_return_high, ble.in_return_low] == [19.0, 15.0, 21.0, 21.0]
    assert [ble.out_forward_high, ble.out_forward_low,
            ble.out_return_high, ble.out_return_low] == [49.0, 38.0, 43.0, 43.0]
    assert ble.forward_max_gain_db == 30.0
    assert ble.forward_default_tilt_db == 11.0
    assert ble.return_max_gain_db == 22.0


@needs_samples
def test_input_level_99_marks_a_fibre_fed_node():
    lib = library_from_spec_set(KERMIT)
    by_name = {a.name: a for a in lib.actives.values()}
    node = by_name["BTN NODE-9"]
    assert not node.needs_rf_input
    assert node.kind == "node"
    assert node.forward_max_gain_db == 0.0
    # the sentinel classifies parts the name alone would miss
    assert by_name["5F31QSA004-9"].kind == "node"


@needs_samples
def test_active_power_tables_are_constant_power_curves():
    lib = library_from_spec_set(KERMIT)
    by_name = {a.name: a for a in lib.actives.values()}
    for name, watts in [("MB-750D-H", 43.0), ("BTN NODE-9", 71.0)]:
        part = by_name[name]
        assert len(part.power_draw) >= 4
        power = [v * a for v, a in part.power_draw]
        assert all(abs(w - watts) < 1.5 for w in power), (name, power)
        # draw must rise as the applied voltage sags
        assert part.current_at(45) > part.current_at(90)


@needs_samples
def test_diffing_a_file_against_itself_finds_nothing():
    from lodedata.diff import compare
    r = compare(NTW, NTW)
    assert r["bytes_changed"] == 0
    assert r["regions"] == []


@needs_samples
def test_diffing_finds_a_single_changed_field(tmp_path):
    """What a one-edit pair looks like: one small region, nothing else.

    This is the shape of pair that pins a field down -- open a design, change
    one tap, save under a new name.
    """
    from lodedata.diff import compare
    from lodedata.obfuscation import deobfuscate, obfuscate, PAYLOAD_START

    original = NTW.read_bytes()
    plain = bytearray(deobfuscate(original[PAYLOAD_START:]))
    # pretend one two-byte field somewhere in the live data changed
    spot = next(i for i in range(1000, len(plain) - 2) if plain[i] or plain[i + 1])
    plain[spot] = (plain[spot] + 7) & 0xFF
    edited = tmp_path / "edited.ntw"
    edited.write_bytes(original[:PAYLOAD_START] + obfuscate(bytes(plain)))

    r = compare(NTW, edited)
    assert r["bytes_changed"] == 1
    assert len(r["regions"]) == 1
    assert r["regions"][0].start == spot + PAYLOAD_START
