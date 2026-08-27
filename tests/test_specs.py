"""Spec files: parsing, validation and the documented worked examples."""

import os
import tempfile
import unittest

from lode.library import generic750
from lode.specs import (ActivesSpec, CablesSpec, ParametersSpec, SpecError,
                        SpecSet, Xspec, XspecEntry)
from lode.specs.actives import Active
from lode.specs.cables import Cable
from lode.specs.performance import PerformanceSpec


class TestParameters(unittest.TestCase):
    def test_two_forward_frequencies_are_required(self):
        params = ParametersSpec.default()
        params.frequencies = [f for f in params.frequencies
                              if f.id in ("F1", "R1", "R2")]
        with self.assertRaises(SpecError) as ctx:
            params.validate()
        self.assertIn("two forward frequencies", str(ctx.exception))

    def test_tap_window_is_minimum_plus_window(self):
        # "a minimum tap output specification of 16 dB (Forward high), and are
        #  not allowed to exceed 26 dB ... you would enter a 10.00"
        params = ParametersSpec.default()
        params.min_tap_output = {"F1": 16.0}
        params.tap_window = 10.0
        self.assertEqual(params.min_tap_level("F1"), 16.0)
        self.assertEqual(params.max_tap_level("F1"), 26.0)

    def test_homes_to_ports_table(self):
        params = ParametersSpec.default()
        self.assertEqual(params.ports_for_homes(1), 2)
        self.assertEqual(params.ports_for_homes(3), 4)
        self.assertEqual(params.ports_for_homes(40), 8)

    def test_unknown_frequency_column_is_rejected(self):
        params = ParametersSpec.default()
        params.frequencies[0].id = "F9"
        with self.assertRaises(SpecError):
            params.validate()


class TestActives(unittest.TestCase):
    def test_housing_input_from_module_input(self):
        # "a forward-high-channel module input of 16.50 dB ... your
        #  forward-high-channel housing input minimum is 19.50 dB"
        active = Active(id="X", gain={"F1": 30}, module_input={"F1": 16.50},
                        housing_offset=3.0)
        self.assertAlmostEqual(active.housing_input_min("F1"), 19.50)

    def test_voltage_current_pairs_stair_and_linear(self):
        # "from Vmin to V2, it uses A1 amperes; from V2 to V3, A2 amperes"
        active = Active(id="X", gain={"F1": 1},
                        va_pairs=[[40, 1.0], [60, 0.8], [90, 0.5]])
        self.assertAlmostEqual(active.current_at(40), 1.0)
        self.assertAlmostEqual(active.current_at(50, "stair"), 1.0)
        self.assertAlmostEqual(active.current_at(50, "linear"), 0.9)
        self.assertAlmostEqual(active.current_at(120), 0.5)   # held at the top
        self.assertAlmostEqual(active.current_at(10), 1.0)    # held at the bottom

    def test_category_is_validated(self):
        spec = ActivesSpec(rows=[Active(id="X", category="nonsense",
                                        gain={"F1": 1})])
        with self.assertRaises(SpecError):
            spec.validate()


class TestPerformanceRules(unittest.TestCase):
    def test_derate_sign_selects_input_or_output(self):
        # "a positive number will cause the Design Assistant to key off the
        #  input level ... a negative number will cause it to key off the
        #  output level"
        spec = PerformanceSpec.default()
        cn, ctb = spec.by_id("CN"), spec.by_id("CTB")
        self.assertTrue(cn.keys_off_input)
        self.assertFalse(ctb.keys_off_input)

        cn.reference_level = 11.0
        # C/N gets 1 dB worse for every 1 dB decrease in input level
        self.assertAlmostEqual(cn.derate_spec(61.0, 8.0, 46.0), 58.0)
        ctb.reference_level = 46.0
        # CTB gets 2 dB worse for every 1 dB increase in output level
        self.assertAlmostEqual(ctb.derate_spec(68.0, 16.0, 48.0), 64.0)

    def test_no_reference_level_means_no_derating(self):
        spec = PerformanceSpec.default()
        cn = spec.by_id("CN")
        cn.reference_level = None
        self.assertAlmostEqual(cn.derate_spec(51.0, -20.0, 90.0), 51.0)


class TestCables(unittest.TestCase):
    def test_loss_is_per_hundred_units(self):
        cable = Cable(id="C", atten={"F1": 1.42}, loop_res=1.10)
        self.assertAlmostEqual(cable.loss("F1", 250), 3.55)
        self.assertAlmostEqual(cable.loss("F1", 250, factor=1.1), 3.905)
        self.assertAlmostEqual(cable.resistance(500), 0.55)

    def test_missing_attenuation_is_rejected(self):
        with self.assertRaises(SpecError):
            CablesSpec(rows=[Cable(id="C")]).validate()


class TestTapSelectionGroups(unittest.TestCase):
    def setUp(self):
        self.specs = generic750()

    def test_group_is_sorted_by_value(self):
        values = [t.value for t in self.specs.taps.group(1, 4)]
        self.assertEqual(values, sorted(values))

    def test_bracket_style_shows_port_count(self):
        self.assertEqual(self.specs.taps.by_id("T2-11").display(), "[11]")
        self.assertEqual(self.specs.taps.by_id("T4-11").display(), "(11)")
        self.assertEqual(self.specs.taps.by_id("T8-11").display(), "{11}")


class TestSpecSetRoundTrip(unittest.TestCase):
    def test_save_and_reload_is_lossless(self):
        original = generic750()
        with tempfile.TemporaryDirectory() as tmp:
            original.save_dir(tmp)
            reloaded = SpecSet.load_dir(tmp)
        self.assertEqual(reloaded.validate(), [])
        self.assertEqual(len(reloaded.taps), len(original.taps))
        self.assertEqual(reloaded.actives.by_id("LE-750").design_output,
                         original.actives.by_id("LE-750").design_output)
        self.assertEqual(
            [e.value for e in reloaded.actives.by_id("LE-750").equalizers],
            [e.value for e in original.actives.by_id("LE-750").equalizers])

    def test_incomplete_set_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            generic750().parameters.save(os.path.join(tmp, "only.par"))
            with self.assertRaises(SpecError) as ctx:
                SpecSet.load_dir(tmp)
        self.assertIn("incomplete", str(ctx.exception))

    def test_cross_file_warnings(self):
        specs = generic750()
        specs.parameters.default_cable = "NOT-A-CABLE"
        self.assertTrue(any("NOT-A-CABLE" in w for w in specs.validate()))

    def test_xspec_quick_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            generic750().save_dir(os.path.join(tmp, "lib"))
            path = os.path.join(tmp, "quick.xsp")
            Xspec(entries=[XspecEntry(line=0, name="lib",
                                      directory="lib")]).save(path)
            loaded = Xspec.load(path).load_line(0)
        self.assertEqual(len(loaded.actives), 4)
        with self.assertRaises(SpecError):
            Xspec().load_line(3)


class TestCsvProjection(unittest.TestCase):
    def test_rows_flatten_to_csv(self):
        text = generic750().cables.to_csv()
        self.assertIn("id,description", text)
        self.assertIn("P3-500", text)


if __name__ == "__main__":
    unittest.main()
