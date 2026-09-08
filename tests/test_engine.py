"""Hand-checked cascade so the numbers can be trusted."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from hfc.model import Network, Element, DesignParameters, interpolate_sqrt
from hfc.starter import starter_library
from hfc.engine import calculate
from hfc.reports import bill_of_materials, level_report


def build():
    net = Network(name="test", library=starter_library(),
                  parameters=DesignParameters())
    net.add(Element(id="n1", type="node", label="Node 1",
                    part_id="act_Optical_node_4_out",
                    source_dbmv=50.0, source_tilt_db=10.0))
    # 500 ft of .750 P3 to a 23 dB 4-port tap
    net.add(Element(id="t1", type="tap", label="Tap 1", parent_id="n1",
                    parent_port=0, cable_id="cbl_p750_P3", length_ft=500,
                    part_id="tap_4x23", houses=4))
    # another 300 ft to a 17 dB tap
    net.add(Element(id="t2", type="tap", label="Tap 2", parent_id="t1",
                    parent_port=0, cable_id="cbl_p750_P3", length_ft=300,
                    part_id="tap_4x17", houses=4))
    return net


def test_cable_interpolation_matches_published_values():
    # .500 P3 is 1.42 dB/100ft at 750 MHz and 0.38 at 55 MHz
    pts = [(55.0, 0.38), (750.0, 1.42)]
    assert abs(interpolate_sqrt(pts, 750.0) - 1.42) < 1e-9
    assert abs(interpolate_sqrt(pts, 300.0) - 0.90) < 0.05


def test_forward_cascade():
    net = build()
    res = calculate(net)
    assert res.problems == []

    node = res.rows["n1"]
    assert node.output.high == 50.0
    assert node.output.low == 40.0        # 10 dB tilt

    # 500 ft of .750 P3: 0.99 dB/100ft at 750 -> 4.95 dB
    t1 = res.rows["t1"]
    assert abs(t1.span_loss_high - 4.95) < 0.01
    assert abs(t1.input.high - 45.05) < 0.01
    # 23 dB tap port
    assert abs(t1.tap_port.high - 22.05) < 0.01

    # tap 1 through loss at 750 is 0.8 dB, then 300 ft = 2.97 dB
    t2 = res.rows["t2"]
    assert abs(t2.input.high - (45.05 - 0.8 - 2.97)) < 0.01
    assert abs(t2.tap_port.high - (t2.input.high - 17.0)) < 0.01


def test_tilt_is_carried_through():
    net = build()
    res = calculate(net)
    t2 = res.rows["t2"]
    # low frequency loses less, so tilt shrinks going downstream
    assert t2.input.tilt < res.rows["n1"].output.tilt


def test_amplifier_gain_and_limit_warning():
    net = build()
    net.add(Element(id="a1", type="amplifier", label="LE 1", parent_id="t2",
                    parent_port=0, cable_id="cbl_p500_P3", length_ft=800,
                    part_id="act_Line_extender"))
    res = calculate(net)
    a1 = res.rows["a1"]
    assert a1.gain_high is not None
    assert abs(a1.output.high - 48.0) < 1e-9        # part default
    assert abs(a1.gain_high - (48.0 - a1.input.high)) < 1e-9

    # force an impossible gain and the warning must appear
    net.elements["a1"].output_dbmv = 95.0
    res = calculate(net)
    assert any("tops out" in w for w in res.rows["a1"].warnings)


def test_return_path_reaches_the_node():
    net = build()
    res = calculate(net)
    r = res.rows["t2"].return_at_node
    assert r is not None
    # 45 dBmV transmit, minus tap value and the upstream losses
    assert r.high < net.parameters.return_transmit_dbmv


def test_powering_drops_voltage_with_distance():
    net = build()
    net.add(Element(id="ps", type="power_supply", label="PS1",
                    parent_id="n1", parent_port=1, supply_volts=90.0))
    net.add(Element(id="a1", type="amplifier", label="LE 1", parent_id="t2",
                    parent_port=0, cable_id="cbl_p500_P3", length_ft=2000,
                    part_id="act_Line_extender"))
    res = calculate(net)
    assert res.rows["a1"].volts is not None
    assert res.rows["a1"].volts < 90.0
    assert res.rows["a1"].segment_current_a >= 1.0


def test_tap_level_window_warnings():
    net = build()
    net.elements["t1"].part_id = "tap_4x4"     # far too little tap value
    res = calculate(net)
    assert any("above the" in w for w in res.rows["t1"].warnings)


def test_delete_removes_the_subtree():
    net = build()
    removed = net.remove("t1")
    assert set(removed) == {"t1", "t2"}
    assert net.validate() == []


def test_bom_counts_parts_and_footage():
    net = build()
    bom = {(r["category"], r["item"]): r["quantity"] for r in bill_of_materials(net)}
    assert bom[("Cable", ".750 P3")] == 800.0
    assert bom[("Tap", "4-port 23 dB tap")] == 1


def test_level_report_has_a_row_per_element():
    net = build()
    assert len(level_report(net)) == len(net.elements)


def test_round_trip_serialisation():
    net = build()
    again = Network.from_dict(net.to_dict())
    assert again.name == net.name
    assert len(again.elements) == len(net.elements)
    assert calculate(again).totals == calculate(net).totals
