"""The forward and return level cascade, checked against hand calculations."""

import unittest

from lode.engine.levels import ERROR, LevelEngine, OK, WARN, classify, select_pad_eq
from lode.library import generic750
from lode.network import Network


def simple_run():
    """Node -> 250 ft of P3-500 -> a 17 dB four-port tap."""
    net = Network(name="hand-calc")
    src = net.add_location(kind="source", label="ND1", device="ND-750")
    tap = net.add_location(kind="tap", label="1", device="T4-17", units=4)
    net.add_span(src.id, tap.id, cable="P3-500", length=250, port="OUT1")
    return net, src, tap


class TestForwardCascade(unittest.TestCase):
    def setUp(self):
        self.specs = generic750()

    def test_levels_match_hand_calculation(self):
        net, src, tap = simple_run()
        sol = LevelEngine(self.specs, net).solve()

        # node module output 50.0 / 39.0, less the OUT1 port loss 3.9 / 3.5
        self.assertAlmostEqual(sol[src.id].fwd_ports["OUT1"]["F1"], 46.1, places=6)
        self.assertAlmostEqual(sol[src.id].fwd_ports["OUT1"]["F2"], 35.5, places=6)

        # 250 ft of P3-500 costs 1.42 x 2.5 = 3.55 dB at 750, 0.95 dB at 55
        self.assertAlmostEqual(sol[tap.id].fwd_in["F1"], 42.55, places=6)
        self.assertAlmostEqual(sol[tap.id].fwd_in["F2"], 34.55, places=6)

        # tap port loss 17.5 at 750, through loss 0.9
        self.assertAlmostEqual(sol[tap.id].fwd_tap["F1"], 25.05, places=6)
        self.assertAlmostEqual(sol[tap.id].fwd_ports["THRU"]["F1"], 41.65, places=6)

    def test_return_requirement_matches_hand_calculation(self):
        net, src, tap = simple_run()
        sol = LevelEngine(self.specs, net).solve()
        # node needs 16.0 dBmV at 42 MHz; +3.4 port, +0.825 cable, +16.3 tap
        self.assertAlmostEqual(sol[tap.id].rtn_req["R1"], 20.225, places=6)
        self.assertAlmostEqual(sol[tap.id].rtn_tap["R1"], 36.525, places=6)

    def test_self_terminating_tap_ends_the_line(self):
        net, src, tap = simple_run()
        net.locations[tap.id].device = "T4-17T"
        sol = LevelEngine(self.specs, net).solve()
        self.assertEqual(sol[tap.id].fwd_ports, {})

    def test_missing_device_is_an_error_not_a_crash(self):
        net, src, tap = simple_run()
        net.locations[tap.id].device = "NOPE"
        sol = LevelEngine(self.specs, net).solve()
        self.assertEqual(sol[tap.id].status, ERROR)
        self.assertTrue(any(f.code == "missing-tap" for f in sol.flags))


class TestPadAndEqualizerSelection(unittest.TestCase):
    """The two-frequency solve for the plug-ins."""

    def setUp(self):
        self.specs = generic750()
        self.le = self.specs.actives.by_id("LE-750")
        self.params = self.specs.parameters

    def test_solve_picks_the_documented_values(self):
        # module input 24.8 dBmV flat; gain 34/32; target output 46/37
        # required slope = (0) + (34-32) - (46-37) = -7 dB
        # the stocked equalizers slope by -value, so 6 dB is the closest fit
        # pad = 24.8 + 34 - 0.5 - 46 = 12.3 -> the 12 dB pad
        pad, eq, diag = select_pad_eq(
            self.le, {"F1": 24.8, "F2": 24.8}, self.params)
        self.assertEqual(eq.value, 6.0)
        self.assertEqual(pad, 12.0)
        self.assertAlmostEqual(diag["required_slope"], -7.0, places=6)
        self.assertAlmostEqual(diag["raw_pad"], 12.3, places=6)

    def test_over_equalization_can_be_forbidden(self):
        self.params.allow_over_equalization = False
        # a required slope of -7 may only be met by 6 dB (under), never 9 (over)
        _, eq, _ = select_pad_eq(self.le, {"F1": 24.8, "F2": 24.8}, self.params)
        self.assertEqual(eq.value, 6.0)

    def test_manual_overrides_win(self):
        pad, eq, _ = select_pad_eq(self.le, {"F1": 24.8, "F2": 24.8},
                                   self.params, pad_override=3, eq_override=12)
        self.assertEqual(pad, 3.0)
        self.assertEqual(eq.value, 12.0)

    def test_starved_amplifier_is_flagged(self):
        net = Network(name="starved")
        src = net.add_location(kind="source", label="ND1", device="ND-750")
        amp = net.add_location(kind="active", label="LE1", device="LE-750")
        net.add_span(src.id, amp.id, cable="P3-500", length=3000, port="OUT1")
        sol = LevelEngine(self.specs, net).solve()
        codes = {f.code for f in sol.flags}
        self.assertIn("housing-input", codes)
        self.assertIn("under-driven", codes)
        self.assertEqual(sol.status, ERROR)


class TestFlagging(unittest.TestCase):
    def test_margin_decides_yellow_versus_red(self):
        # "if a tap is less than the margin value out of spec, it will be
        #  displayed in yellow"
        self.assertEqual(classify(20.0, 16.0, 26.0, 1.0), OK)
        self.assertEqual(classify(15.5, 16.0, 26.0, 1.0), WARN)
        self.assertEqual(classify(14.5, 16.0, 26.0, 1.0), ERROR)
        self.assertEqual(classify(26.5, 16.0, 26.0, 1.0), WARN)
        self.assertEqual(classify(28.0, 16.0, 26.0, 1.0), ERROR)

    def test_tap_window_only_applies_when_enforced(self):
        specs = generic750()
        specs.parameters.min_tap_output = {"F1": 16.0}
        specs.parameters.tap_window = 4.0
        net, src, tap = simple_run()

        specs.parameters.enforce_tap_window = False
        sol = LevelEngine(specs, net).solve()   # tap port sits at 25.05 dBmV
        self.assertEqual(sol[tap.id].status, OK)

        specs.parameters.enforce_tap_window = True
        sol = LevelEngine(specs, net).solve()   # now above the 20 dBmV ceiling
        self.assertEqual(sol[tap.id].status, ERROR)

    def test_crossover_is_flagged_once_where_it_is_crossed(self):
        specs = generic750()
        net = Network(name="crossover")
        cursor = net.add_location(kind="source", label="ND1",
                                  device="ND-750").id
        port = "OUT1"
        for index in range(6):
            loc = net.add_location(kind="tap", label=str(index),
                                   device="T4-11", units=2)
            net.add_span(cursor, loc.id, cable="P3-500", length=400, port=port)
            cursor, port = loc.id, "THRU"
        sol = LevelEngine(specs, net).solve()
        crossover = [f for f in sol.flags if f.code == "crossover"]
        self.assertEqual(len(crossover), 1)


class TestTopology(unittest.TestCase):
    def test_branching_through_a_coupler(self):
        specs = generic750()
        net = Network(name="branch")
        src = net.add_location(kind="source", label="ND1", device="ND-750")
        cpl = net.add_location(kind="coupler", label="SP1", device="SP2")
        net.add_span(src.id, cpl.id, cable="P3-750", length=100, port="OUT1")
        left = net.add_location(kind="tap", label="L", device="T4-11", units=2)
        right = net.add_location(kind="tap", label="R", device="T4-11", units=2)
        net.add_span(cpl.id, left.id, cable="P3-500", length=100, port="THRU")
        net.add_span(cpl.id, right.id, cable="P3-500", length=100, port="TAP1")
        sol = LevelEngine(specs, net).solve()
        # a balanced two-way splits evenly, so both legs land on the same level
        self.assertAlmostEqual(sol[left.id].fwd_in["F1"],
                               sol[right.id].fwd_in["F1"], places=6)
        self.assertEqual(len(sol.order), 4)

    def test_a_second_feed_is_refused(self):
        net = Network(name="loop")
        a = net.add_location(kind="source", label="A", device="ND-750")
        b = net.add_location(kind="tap", label="B", device="T4-11")
        c = net.add_location(kind="tap", label="C", device="T4-11")
        net.add_span(a.id, b.id, cable="P3-500", length=100, port="OUT1")
        net.add_span(a.id, c.id, cable="P3-500", length=100, port="OUT2")
        with self.assertRaises(Exception):
            net.add_span(c.id, b.id, cable="P3-500", length=10, port="THRU")


if __name__ == "__main__":
    unittest.main()
