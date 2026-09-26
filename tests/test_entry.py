"""Typing equipment at the cell, the way it goes in during design."""
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))
sys.path.insert(0, str(ROOT / "tools"))

from hfc.entry import resolve_tap, resolve_coupler, resolve_active, EntryError
from hfc.importer import library_from_spec_set
from hfc.plant import (Design, Node, CouplerPlacement, THROUGH_DOWNSTREAM,
                       THROUGH_FIRST, THROUGH_SECOND)
from hfc.screen import build
from hfc.starter import starter_library

SAMPLES = Path(os.environ.get("LODEDATA_SAMPLES", ROOT / "samples"))


def _spec(stem):
    hit = next(iter(sorted(SAMPLES.rglob(f"*{stem}*.cbl"))), None) if SAMPLES.is_dir() else None
    return hit.with_suffix("") if hit else None


WVBECK = _spec("WVBeck")
needs_samples = pytest.mark.skipif(
    WVBECK is None, reason="sample spec set not found; see samples/README.md")


# --------------------------------------------------------------------- taps
@needs_samples
@pytest.mark.parametrize("code,ports,value", [
    ("2.23", 2, 23.0),
    ("4.23", 4, 23.0),
    ("8.20", 8, 20.0),
    ("2.17", 2, 17.0),
    ("4.11", 4, 11.0),
])
def test_typing_ports_dot_value_finds_the_tap(code, ports, value):
    lib = library_from_spec_set(WVBECK)
    tap = resolve_tap(lib, code)
    assert tap.ports == ports
    assert abs(tap.tap_value_db - value) < 0.5


def test_a_bare_value_picks_a_port_count_from_the_house_count():
    lib = starter_library()
    assert resolve_tap(lib, "23", houses=2).ports == 2
    assert resolve_tap(lib, "23", houses=3).ports == 4
    assert resolve_tap(lib, "23", houses=8).ports == 8


def test_zero_clears_a_tap():
    assert resolve_tap(starter_library(), "0") is None
    assert resolve_tap(starter_library(), "") is None


def test_an_unknown_tap_says_what_the_spec_has():
    with pytest.raises(EntryError) as e:
        resolve_tap(starter_library(), "4.99")
    assert "no 4-port 99 tap" in str(e.value)
    assert "23" in str(e.value)          # lists the values it does have


def test_a_bad_port_count_is_rejected():
    with pytest.raises(EntryError) as e:
        resolve_tap(starter_library(), "5.23")
    assert "port count" in str(e.value)


# ----------------------------------------------------------------- couplers
@needs_samples
@pytest.mark.parametrize("code,name,through", [
    ("2", "RLS10-2-15A", THROUGH_DOWNSTREAM),
    ("3", "RLS10-3-15A", THROUGH_DOWNSTREAM),
    ("8", "RLDC-8-15A", THROUGH_DOWNSTREAM),
    ("-8", "RLDC-8-15A", THROUGH_FIRST),
    ("--3", "RLS10-3-15A", THROUGH_SECOND),
    ("=3", "RLS10-3-15A", THROUGH_SECOND),
    ("8-", "RLDC-8-15A", THROUGH_FIRST),       # as keyed in the program
    ("3=", "RLS10-3-15A", THROUGH_SECOND),
    ("3--", "RLS10-3-15A", THROUGH_SECOND),
])
def test_typing_a_coupler_id_finds_it_and_reads_the_leg_designation(code, name, through):
    lib = library_from_spec_set(WVBECK)
    part, thr = resolve_coupler(lib, code)
    assert part.name == name
    assert thr == through


def test_zero_clears_a_coupler():
    part, _ = resolve_coupler(starter_library(), "0")
    assert part is None


def test_an_unknown_coupler_says_what_the_spec_has():
    with pytest.raises(EntryError) as e:
        resolve_coupler(starter_library(), "77")
    assert "no coupler with ID 77" in str(e.value)


# ------------------------------------------------------------------ actives
def test_typing_an_active_id_finds_it():
    lib = starter_library()
    assert resolve_active(lib, "11").name == "Line extender"
    assert resolve_active(lib, "61").name == "Optical node (4 out)"
    assert resolve_active(lib, "0") is None
    with pytest.raises(EntryError):
        resolve_active(lib, "999")


# ------------------------------------------------- the swap changes levels
def _design_with_dc(through):
    """A DC feeding a branch, with the through leg where `through` says."""
    d = Design(library=starter_library())
    d.source_dbmv, d.source_tilt_db = 50.0, 10.0
    feeder = d.ensure_feeder()
    dc = d.library.passives["psv_DC_8_coupler"]     # legs 1.4 thru / 8.5 tap
    child = d.add_branch(1, 1)
    child.nodes = [Node(seq=1)]
    feeder.nodes[0].couplers.append(
        CouplerPlacement(part_id=dc.id, coupler_id=8, branch=child.number))
    feeder.nodes[0].through_leg = through
    feeder.nodes.append(Node(seq=2))
    d.renumber(feeder)
    return d


def test_swapping_the_legs_moves_the_loss_between_the_paths():
    fh = 750.0
    plain = build(_design_with_dc(THROUGH_DOWNSTREAM))
    swapped = build(_design_with_dc(THROUGH_FIRST))

    def levels(scr):
        branch = next(r for r in scr.rows if r.branch != 1)
        downstream = [r for r in scr.rows if r.branch == 1][-1]
        return branch.levels[fh], downstream.levels[fh]

    b_plain, d_plain = levels(plain)
    b_swap, d_swap = levels(swapped)

    # normally the branch pays the 8.5 dB tap leg and downstream the 1.4 dB thru
    assert d_plain > b_plain
    # after the swap the branch gets the low-loss leg and downstream the high
    assert b_swap > d_swap
    # and the two legs simply trade places
    assert abs(b_swap - d_plain) < 0.01
    assert abs(d_swap - b_plain) < 0.01


def test_the_screen_shows_the_leg_designation():
    # a new branch has no footage yet, so it is drawn <2>, as AL004 draws its
    # empty branches (16<19>, 3[21]<24>)
    assert build(_design_with_dc(THROUGH_DOWNSTREAM)).rows[0].couplers[0] == "8<2>"
    assert build(_design_with_dc(THROUGH_FIRST)).rows[0].couplers[0] == "8-<2>"


def test_a_branch_with_mileage_footage_is_drawn_square():
    d = _design_with_dc(THROUGH_DOWNSTREAM)
    child = d.branches[2]
    child.nodes[0].ftg, child.nodes[0].cab = 120, 410      # series 4: mileage
    assert build(d).rows[0].couplers[0] == "8[2]"
    child.nodes[0].cab = 110                               # series 1: parallel
    assert build(d).rows[0].couplers[0] == "8<2>"
