"""The Design / Entry / Power screen: branches of nodes, levels and powering."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from hfc.model import DesignParameters, interpolate_sqrt
from hfc.plant import Design, Node, TapPlacement, CouplerPlacement, BRANCH_NORMAL
from hfc.screen import build
from hfc.starter import starter_library
from hfc.reports import bill_of_materials, level_report


def design():
    d = Design(name="test", library=starter_library(),
               parameters=DesignParameters(forward_low_mhz=54, forward_high_mhz=750),
               source_dbmv=50.0, source_tilt_db=10.0, supply_volts=90.0)
    feeder = d.ensure_feeder()
    lib = d.library
    cable = lib.cables["cbl_p750_P3"]
    node_part = lib.actives["act_Optical_node_4_out"]
    tap23 = lib.taps["tap_4x23"]
    tap17 = lib.taps["tap_4x17"]

    feeder.nodes[0].amp, feeder.nodes[0].amp_part = 61, node_part.id
    feeder.nodes[0].supply_volts = 90.0
    for ftg, hc, tap in [(500, 4, tap23), (300, 4, tap17)]:
        n = Node(ftg=ftg, hc=hc, cab=2, cab_part=cable.id)
        if tap:
            n.taps.append(TapPlacement(part_id=tap.id, ports=tap.ports,
                                       value_db=tap.tap_value_db))
        feeder.nodes.append(n)
    d.renumber(feeder)
    return d


def test_a_fibre_fed_node_shows_no_rf_input():
    scr = build(design())
    assert all(v == 0.0 for v in scr.rows[0].levels.values())


def test_forward_levels_fall_and_return_levels_rise_downstream():
    scr = build(design())
    p = design().parameters
    fh, rh = p.forward_high_mhz, p.return_high_mhz
    fwd = [r.levels[fh] for r in scr.rows[1:]]
    ret = [r.levels[rh] for r in scr.rows[1:]]
    assert fwd == sorted(fwd, reverse=True)
    assert ret == sorted(ret)


def test_cable_loss_matches_the_spec():
    d = design()
    scr = build(d)
    # .750 P3 is 0.99 dB/100ft at 750 MHz, so 500 ft costs 4.95 dB
    out = d.library.actives["act_Optical_node_4_out"].out_forward_high
    assert abs(scr.rows[1].levels[750.0] - (out - 4.95)) < 0.01


def test_tap_is_drawn_in_the_bracket_of_its_port_count():
    scr = build(design())
    assert scr.rows[1].taps == ["[23]"]        # 4-port
    d = design()
    lib = d.library
    n = d.branches[1].nodes[1]
    two = lib.taps["tap_2x23"]
    n.taps = [TapPlacement(part_id=two.id, ports=2, value_db=two.tap_value_db)]
    assert build(d).rows[1].taps == ["/23/"]   # 2-port


def test_a_coupler_starts_a_branch_walked_where_it_sits():
    d = design()
    feeder = d.branches[1]
    child = d.add_branch(1, 2)
    child.nodes = [Node(seq=1, ftg=100, hc=2, cab=2,
                        cab_part=d.library.cables["cbl_p750_P3"].id)]
    splitter = d.library.passives["psv_2_way_splitter"]
    feeder.nodes[1].couplers.append(
        CouplerPlacement(part_id=splitter.id, coupler_id=2, branch=child.number))
    scr = build(d)
    order = [(r.branch, r.node) for r in scr.rows]
    # the branch is walked immediately after the node carrying its coupler
    assert order.index((child.number, 1)) == order.index((1, 2)) + 1
    assert "2[%d]" % child.number in scr.rows[1].couplers[0]
    # and its levels sit below the feeder, having paid the tap leg
    assert scr.rows[2].levels[750.0] < scr.rows[1].levels[750.0]


def test_branch_rows_get_gutter_line_art():
    d = design()
    child = d.add_branch(1, 2)
    child.nodes = [Node(seq=1), Node(seq=2), Node(seq=3)]
    splitter = d.library.passives["psv_2_way_splitter"]
    d.branches[1].nodes[1].couplers.append(
        CouplerPlacement(part_id=splitter.id, branch=child.number))
    rows = [r for r in build(d).rows if r.branch == child.number]
    assert [r.gutter for r in rows] == ["┌", "│", "└"]


def test_powering_drops_voltage_and_draws_constant_power():
    d = design()
    scr = build(d)
    assert scr.rows[0].volts == 90.0
    assert scr.rows[0].current > 0        # the node draws
    assert scr.rows[-1].volts <= scr.rows[0].volts


def test_a_starved_amplifier_is_flagged_red():
    d = design()
    le = d.library.actives["act_Line_extender"]
    far = Node(ftg=4000, cab=2, cab_part=d.library.cables["cbl_p750_P3"].id,
               amp=11, amp_part=le.id)
    d.branches[1].nodes.append(far)
    d.renumber(d.branches[1])
    row = build(d).rows[-1]
    assert row.severity == "red"
    assert any("module input" in m for _, m in row.flags)


def test_deleting_a_branch_takes_its_children_with_it():
    d = design()
    b2 = d.add_branch(1, 1)
    b3 = d.add_branch(b2.number, 1)
    gone = d.remove_branch(b2.number)
    assert set(gone) == {b2.number, b3.number}
    assert d.validate() == []


def test_bom_counts_parts_and_footage():
    bom = {(r["category"], r["item"]): r["quantity"]
           for r in bill_of_materials(design())}
    assert bom[("Cable", ".750 P3")] == 800
    assert bom[("Tap", "4-port 23 dB tap")] == 1


def test_level_report_has_a_row_per_node():
    d = design()
    assert len(level_report(d)) == len(build(d).rows)


def test_round_trip_serialisation():
    d = design()
    again = Design.from_dict(d.to_dict())
    assert build(again).totals == build(d).totals


def test_no_spec_set_is_reported_as_a_problem():
    d = Design()
    d.ensure_feeder()
    assert any("no spec set" in p for p in build(d).problems)


def test_cable_interpolation_matches_published_values():
    pts = [(55.0, 0.38), (750.0, 1.42)]
    assert abs(interpolate_sqrt(pts, 750.0) - 1.42) < 1e-9
    assert abs(interpolate_sqrt(pts, 300.0) - 0.90) < 0.05
