"""Performance cascade, powering solve and the automatic design tools."""

import math
import unittest

from lode.engine.autodesign import AutoDesigner
from lode.engine.levels import LevelEngine
from lode.engine.performance import PerformanceEngine
from lode.engine.powering import PoweringEngine
from lode.library import generic750
from lode.network import Network, PowerSupply
from lode.units import log_combine


class TestCascadeArithmetic(unittest.TestCase):
    def test_addition_factors(self):
        # "the addition factor for carrier to noise is 10 ... for composite
        #  triple beat is 20"
        self.assertAlmostEqual(log_combine([61, 61], 10), 61 - 3.0103, places=3)
        self.assertAlmostEqual(log_combine([68, 68], 20), 68 - 6.0206, places=3)
        self.assertAlmostEqual(log_combine([65], 20), 65.0, places=6)
        self.assertTrue(math.isinf(log_combine([], 10)))

    def test_worse_contributor_dominates(self):
        self.assertAlmostEqual(log_combine([50, 80], 10), 49.9957, places=3)


class TestPerformanceEngine(unittest.TestCase):
    def setUp(self):
        self.specs = generic750()
        self.net = Network(name="perf")
        src = self.net.add_location(kind="source", label="ND1", device="ND-750")
        tap = self.net.add_location(kind="tap", label="1", device="T4-11", units=2)
        self.net.add_span(src.id, tap.id, cable="P3-500", length=200, port="OUT1")
        self.tap = tap
        self.sol = LevelEngine(self.specs, self.net).solve()

    def test_single_active_reports_its_own_specs(self):
        results = PerformanceEngine(self.specs, self.net, self.sol).solve()
        values = results[self.tap.id].values
        self.assertAlmostEqual(values["CN"], 51.0, places=6)
        self.assertAlmostEqual(values["CTB"], 65.0, places=6)
        self.assertEqual(results[self.tap.id].cascade, 1)

    def test_carrier_to_noise_uses_the_noise_figure_formula(self):
        # C/N[1] = 59 + input - noise figure
        net = Network(name="cn")
        src = net.add_location(kind="source", label="ND1", device="ND-750")
        amp = net.add_location(kind="active", label="LE1", device="LE-750")
        net.add_span(src.id, amp.id, cable="P3-500", length=1500, port="OUT1")
        tap = net.add_location(kind="tap", label="1", device="T4-11", units=2)
        net.add_span(amp.id, tap.id, cable="P3-500", length=100, port="OUT")
        sol = LevelEngine(self.specs, net).solve()
        results = PerformanceEngine(self.specs, net, sol).solve()
        contributions = {c.location: c for c in results[tap.id].contributions
                         if c.impairment == "CN"}
        amp_part = contributions[amp.id]
        expected = 59.0 + sol[amp.id].module_in["F1"] - 9.0
        self.assertAlmostEqual(amp_part.derated, expected, places=6)
        # and the cascade combines the node's 51 dB optical figure with it
        self.assertAlmostEqual(
            results[tap.id].values["CN"],
            log_combine([51.0, expected], 10.0), places=6)

    def test_objectives_raise_flags(self):
        self.specs.performance.by_id("CTB").objective = 99.0
        engine = PerformanceEngine(self.specs, self.net, self.sol)
        flags = engine.flags(engine.solve())
        self.assertTrue(any(f.code == "performance" for f in flags))


class TestPoweringEngine(unittest.TestCase):
    def setUp(self):
        self.specs = generic750()

    def _one_amp(self, length=1000, volts=90.0, amps=15.0, cable="P3-500"):
        net = Network(name="power")
        src = net.add_location(kind="source", label="ND1", device="ND-750")
        src.power_supply = PowerSupply(id="PS1", volts=volts, max_amps=amps)
        amp = net.add_location(kind="active", label="LE1", device="LE-750")
        net.add_span(src.id, amp.id, cable=cable, length=length, port="OUT1")
        return net, src, amp

    def test_voltage_drop_matches_hand_calculation(self):
        # 1000 ft of P3-500 is 1.10 ohms; the line extender draws about
        # 0.45 A at 90 V, so the drop settles near half a volt
        net, src, amp = self._one_amp()
        area = PoweringEngine(self.specs, net).solve()[0]
        node = area.nodes[amp.id]
        self.assertTrue(area.converged)
        self.assertAlmostEqual(node.volts, 89.50, delta=0.05)
        self.assertAlmostEqual(node.draw, 0.4526, delta=0.005)
        # the supply carries the node's own draw as well
        self.assertAlmostEqual(area.total_current, 1.20 + node.draw, delta=0.01)

    def test_interpolation_mode_changes_the_answer(self):
        net, src, amp = self._one_amp(length=40000)   # a deliberately long haul
        self.specs.parameters.powering.interpolation = "linear"
        linear = PoweringEngine(self.specs, net).solve()[0].nodes[amp.id]
        self.specs.parameters.powering.interpolation = "stair"
        stair = PoweringEngine(self.specs, net).solve()[0].nodes[amp.id]
        self.assertNotAlmostEqual(linear.draw, stair.draw, places=3)

    def test_under_voltage_is_flagged(self):
        net, src, amp = self._one_amp(length=60000, cable="RG-6")
        area = PoweringEngine(self.specs, net).solve()[0]
        codes = {f.code for f in area.flags}
        self.assertTrue({"under-voltage", "low-voltage"} & codes)

    def test_supply_overload_is_flagged(self):
        net, src, amp = self._one_amp(amps=1.0)
        area = PoweringEngine(self.specs, net).solve()[0]
        self.assertTrue(any(f.code == "supply-overload" for f in area.flags))

    def test_load_factor_scales_every_draw(self):
        net, src, amp = self._one_amp()
        plain = PoweringEngine(self.specs, net).solve()[0]
        peak = PoweringEngine(self.specs, net, load_factor=1.5).solve()[0]
        self.assertGreater(peak.total_current, plain.total_current * 1.4)

    def test_a_power_block_bounds_the_area(self):
        net, src, amp = self._one_amp()
        block = net.add_location(kind="coupler", label="PB1", device="PB")
        net.add_span(src.id, block.id, cable="P3-500", length=100, port="OUT2")
        beyond = net.add_location(kind="active", label="LE2", device="LE-750")
        net.add_span(block.id, beyond.id, cable="P3-500", length=100, port="THRU")
        area = PoweringEngine(self.specs, net).solve()[0]
        self.assertIn(block.id, area.nodes)      # the block itself is reached
        self.assertNotIn(beyond.id, area.nodes)  # nothing past it is


class TestAutoDesign(unittest.TestCase):
    def setUp(self):
        self.specs = generic750()

    def _run(self, spans, homes=2):
        net = Network(name="auto")
        cursor = net.add_location(kind="source", label="ND1", device="ND-750").id
        port = "OUT1"
        for index, length in enumerate(spans, start=1):
            loc = net.add_location(kind="tap", label=str(index),
                                   device="T4-4", units=homes)
            net.add_span(cursor, loc.id, cable="P3-500", length=length, port=port)
            cursor, port = loc.id, "THRU"
        return net

    def test_tap_values_step_down_with_the_level(self):
        net = self._run([250] * 6)
        run = AutoDesigner(self.specs, net).auto_taps()
        values = [self.specs.taps.by_id(l.device).value
                  for l in net.locations.values() if l.kind == "tap"]
        self.assertEqual(values, sorted(values, reverse=True))
        self.assertLess(run.passes, 12)

    def test_selection_meets_the_minimum_where_it_is_reachable(self):
        """Every tap makes the minimum, or the shortfall is reported."""
        net = self._run([250] * 6)
        run = AutoDesigner(self.specs, net).auto_taps()
        floor = self.specs.parameters.min_tap_level("F1")
        starved = 0
        for res in run.solution.taps():
            if res.fwd_tap["F1"] >= floor - 1e-9:
                continue
            starved += 1
            self.assertTrue(
                any(f.code == "tap-level" for f in res.flags),
                msg=f"{res.label} is below the minimum but was not flagged")
        # a run this long with no amplifier must run out somewhere
        self.assertGreater(starved, 0)

    def test_a_reachable_run_comes_out_entirely_in_spec(self):
        net = self._run([220] * 4)
        run = AutoDesigner(self.specs, net).auto_taps()
        floor = self.specs.parameters.min_tap_level("F1")
        for res in run.solution.taps():
            self.assertGreaterEqual(res.fwd_tap["F1"], floor - 1e-9)

    def test_ports_follow_the_homes_table(self):
        net = self._run([250] * 3, homes=6)
        AutoDesigner(self.specs, net).auto_ports()
        for loc in net.locations.values():
            if loc.kind == "tap":
                self.assertEqual(self.specs.taps.by_id(loc.device).ports, 8)

    def test_locked_locations_are_left_alone(self):
        net = self._run([250] * 4)
        target = [l for l in net.locations.values() if l.kind == "tap"][0]
        target.locked = True
        target.device = "T4-4"
        AutoDesigner(self.specs, net).auto_taps()
        self.assertEqual(target.device, "T4-4")

    def test_amplifiers_are_placed_where_signal_runs_out(self):
        net = self._run([300] * 14)
        before = AutoDesigner(self.specs, net).solve()
        self.assertTrue(before.errors)
        run = AutoDesigner(self.specs, net).full_design()
        self.assertGreater(
            sum(1 for l in net.locations.values() if l.kind == "active"), 0)
        self.assertEqual(run.solution.errors, [],
                         msg=[f.message for f in run.solution.errors])

    def test_a_placed_amplifier_is_itself_fed_properly(self):
        net = self._run([300] * 14)
        AutoDesigner(self.specs, net).full_design()
        solution = AutoDesigner(self.specs, net).solve()
        for res in solution.actives():
            if res.kind != "active":
                continue
            device = self.specs.actives.by_id(res.device)
            self.assertGreaterEqual(res.fwd_in["F1"],
                                    device.housing_input_min("F1") - 1e-9)

    def test_end_of_leg_taps_become_self_terminating(self):
        net = self._run([250] * 5)
        designer = AutoDesigner(self.specs, net)
        designer.auto_taps()
        designer.self_terminate()
        last = net.locations[[l for l in designer.solve().order][-1]]
        tap = self.specs.taps.by_id(last.device)
        self.assertTrue(tap.self_terminating or tap.value < 8)


if __name__ == "__main__":
    unittest.main()
