"""Lode Data file reading and spec-set upgrade."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))
sys.path.insert(0, str(ROOT / "tools"))

from hfc.importer import library_from_spec_set, inspect_ntw, relink_library, _tokens
from hfc.model import Network, Element
from lodedata.obfuscation import NTW_KEY, deobfuscate, obfuscate, recover_key

SAMPLES = Path("/tmp/claude-0/-home-user-Lodedata/"
               "76afb63c-24f1-5bbe-9e80-a65f74c9f2ec/scratchpad/uploads")
KERMIT = SAMPLES / "c710d98c-OneDrive_1_8282026" / "KERMIT750-2026"
WVBECK = SAMPLES / "ea8baba7-OneDrive_2_8282026" / "WVBeck750"
NTW = SAMPLES / "6f0a4dc0-OneDrive_1_8282026_1" / "AL005.ntw"

needs_samples = pytest.mark.skipif(
    not KERMIT.with_suffix(".cbl").exists(), reason="sample files not present")


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
def test_tap_values_come_from_the_part_numbers():
    lib = library_from_spec_set(KERMIT)
    by_name = {t.name: t for t in lib.taps.values()}
    assert by_name["MMT2830"].tap_value_db == 30.0
    assert by_name["MMT2830"].ports == 8
    assert by_name["MMT2229"].ports == 2
    assert by_name["MMT2429"].ports == 4


def test_token_split_ignores_punctuation():
    assert _tokens("EX .625P3 AER") == frozenset({"EX", "625P3", "AER"})


@needs_samples
def test_spec_upgrade_keeps_the_design_wired_up():
    old = library_from_spec_set(KERMIT)
    new = library_from_spec_set(WVBECK)
    net = Network(name="t", library=old)
    picks = ["EX .625P3 AER", "EX .875P3 UG", "EX .500P3 AER"]
    for i, name in enumerate(picks):
        cid = next(c.id for c in old.cables.values() if c.name == name)
        net.add(Element(id=f"e{i}", type="tap", cable_id=cid, length_ft=100))

    report = relink_library(net, new)
    assert report["matched"] > 40
    resolved = [new.cables[net.elements[f"e{i}"].cable_id].name for i in range(3)]
    # size and aerial/underground must both survive the upgrade
    assert resolved == ["625P3 AER EXT", "875P3 UG EXT", "500P3 AER EXT"]
    assert net.validate() == []


@needs_samples
def test_upgrade_never_crosses_cable_sizes():
    old = library_from_spec_set(KERMIT)
    new = library_from_spec_set(WVBECK)
    net = Network(name="t", library=old)
    report = relink_library(net, new)
    for line in report["fuzzy"]:
        if not line.startswith("cables:"):
            continue
        before, after = line[len("cables:"):].split("->")
        digits_before = {t for t in _tokens(before) if any(c.isdigit() for c in t)}
        digits_after = {t for t in _tokens(after.split("(")[0]) if any(c.isdigit() for c in t)}
        assert digits_before & digits_after, line
