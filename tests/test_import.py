"""The Lode Data binary importer.

No customer library is committed here, so the fixtures are synthesised in the
same format the real files use -- which also documents that format precisely.
"""

import os
import struct
import tempfile
import unittest

from lode.library import generic750
from lode.importers.lodedata import (DB, OHM, ImportReport, _plausible,
                                     _ports_and_value, detect_kind, import_set,
                                     is_plugin, read_cables, read_taps)

HEADER = 512


def _header(title: str) -> bytearray:
    buf = bytearray(HEADER)
    buf[0:len(title)] = title.encode()
    buf[129:139] = b"LP-TEST123"
    buf[145:153] = b"TESTUSER"
    return buf


def _slots(values: dict) -> bytes:
    """Ten int32 slots: F1-F6 then R1-R4, at a million per dB."""
    columns = ("F1", "F2", "F3", "F4", "F5", "F6", "R1", "R2", "R3", "R4")
    out = b""
    for column in columns:
        out += struct.pack("<i", int(round(values.get(column, 0.0) * DB)))
    return out


def make_cables(path: str, rows) -> None:
    buf = _header("Lode Data Cables File")
    for index in range(100):
        rec = bytearray(394)
        rec[0] = 0x6F
        if index < len(rows):
            name, atten, loop, conn = rows[index]
            rec[5:5 + len(name)] = name.encode()
            struct.pack_into("<H", rec, 30, int(round(loop * OHM)))
            block = _slots(atten)
            rec[34:74] = block
            rec[74:114] = block
            rec[114:114 + len(conn)] = conn.encode()
        buf += rec
    open(path, "wb").write(bytes(buf))


def make_taps(path: str, rows) -> None:
    buf = _header("Lode Data Taps File")
    buf += bytes(64)
    for name, tap_loss, thru_loss in rows:
        rec = bytearray(112)
        rec[0:4] = b"\xff\xff\xff\xff"
        encoded = name.encode() + b"\x00"
        rec[11:11 + len(encoded)] = encoded
        rec[11 + 18:11 + 18 + 40] = _slots(tap_loss)
        rec[11 + 58:11 + 58 + 40] = _slots(thru_loss)
        buf += rec
    open(path, "wb").write(bytes(buf))


class TestFormatPrimitives(unittest.TestCase):
    def test_plugins_are_recognised(self):
        for name in ("LEQ\\RC PAD 15", "RC PAD 00", "MGLSH EQ 9",
                     "JUMPER", "TERMINATOR"):
            self.assertTrue(is_plugin(name), name)
        for name in ("MMT2429", "AN-WIFI-824", "RMT2128-RF-26"):
            self.assertFalse(is_plugin(name), name)

    def test_port_and_value_from_part_numbers(self):
        self.assertEqual(_ports_and_value("MMT2830"), (8, 30.0))
        self.assertEqual(_ports_and_value("MMT2229"), (2, 29.0))
        self.assertEqual(_ports_and_value("MMT2429"), (4, 29.0))
        self.assertEqual(_ports_and_value("AN-WIFI-824"), (8, 24.0))
        self.assertEqual(_ports_and_value("MGTS2000-2423"), (4, 23.0))
        self.assertEqual(_ports_and_value("NO DIGITS HERE"), (None, None))

    def test_plausibility_bounds_reject_misreads(self):
        self.assertTrue(_plausible({"F1": 17.5, "F2": 17.0}, 0.5, 60.0))
        self.assertFalse(_plausible({"F1": 587.3}, 0.5, 60.0))
        self.assertFalse(_plausible({}, 0.5, 60.0))

    def test_detect_kind_from_extension(self):
        self.assertEqual(detect_kind("x/KERMIT.cbl"), "cables")
        self.assertEqual(detect_kind("x/KERMIT.atv"), "actives")
        with self.assertRaises(ValueError):
            detect_kind("x/whatever.zzz")


class TestCableImport(unittest.TestCase):
    def test_values_and_resistance_round_trip(self):
        rows = [
            (".500P3 AER", {"F1": 2.16, "F2": 0.52, "R1": -0.48, "R2": -0.16},
             1.72, "FT-500"),
            (".875P3 AER", {"F1": 1.29, "F2": 0.30, "R1": -0.27, "R2": -0.09},
             0.55, "FT-875"),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "T.cbl")
            make_cables(path, rows)
            spec, report = read_cables(path)
        self.assertEqual(len(spec), 2)
        first = spec.rows[0]
        self.assertAlmostEqual(first.atten["F1"], 2.16, places=6)
        self.assertAlmostEqual(first.atten["F2"], 0.52, places=6)
        # return figures are stored negative and taken as magnitudes
        self.assertAlmostEqual(first.atten["R1"], 0.48, places=6)
        self.assertAlmostEqual(first.loop_res, 1.72, places=6)
        self.assertEqual(first.part_number, "FT-500")
        self.assertEqual(report.records_kept, 2)
        self.assertEqual(report.licence, "LP-TEST123")
        # the loss helper must agree with the imported figures
        self.assertAlmostEqual(first.loss("F1", 250), 5.40, places=6)


class TestTapImport(unittest.TestCase):
    def _read(self, rows):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "T.tap")
            make_taps(path, rows)
            return read_taps(path)

    def test_a_normal_family_imports(self):
        spec, report = self._read([
            ("MMT2830", {"F1": 29.7, "F2": 30.2, "R1": 30.2, "R2": 28.8},
             {"F1": 0.8, "F2": 0.4, "R1": 0.4, "R2": 0.4}),
            ("MMT2229", {"F1": 28.4, "F2": 28.8, "R1": 28.7, "R2": 27.2},
             {"F1": 0.8, "F2": 0.4, "R1": 0.4, "R2": 0.4}),
        ])
        self.assertEqual(len(spec), 2)
        eight = spec.by_id("MMT2830")
        self.assertEqual(eight.ports, 8)
        self.assertEqual(eight.value, 30.0)
        self.assertAlmostEqual(eight.tap_loss["F1"], 29.7, places=6)
        self.assertAlmostEqual(eight.insertion_loss["F1"], 0.8, places=6)
        self.assertEqual(spec.by_id("MMT2229").ports, 2)

    def test_plug_in_rows_never_become_taps(self):
        """A pad selected as a tap would be a silent design error."""
        spec, report = self._read([
            ("MMT2429", {"F1": 29.1}, {"F1": 0.8}),
            ("LEQ\\RC PAD 15", {"F1": 15.0}, {"F1": 15.0}),
        ])
        self.assertEqual([t.id for t in spec], ["MMT2429"])
        self.assertTrue(any("plug-in" in n for n in report.notes))

    def test_a_lossless_tap_is_rejected(self):
        """It would otherwise be chosen ahead of every real tap."""
        spec, report = self._read([
            ("MMT2429", {"F1": 29.1}, {"F1": 0.8}),
            ("GHOST-404", {"F2": 12.0}, {"F2": 1.0}),
        ])
        self.assertEqual([t.id for t in spec], ["MMT2429"])
        self.assertTrue(any("no port loss" in n for n in report.notes))

    def test_an_out_of_range_record_is_rejected(self):
        spec, report = self._read([
            ("MMT2429", {"F1": 29.1}, {"F1": 0.8}),
            ("BADLAYOUT-1", {"F1": 587.3, "F2": 594.6}, {"F1": 0.4}),
        ])
        self.assertEqual([t.id for t in spec], ["MMT2429"])
        self.assertTrue(any("physical range" in n for n in report.notes))


class TestWholeSet(unittest.TestCase):
    def test_a_set_without_parameters_is_flagged_not_guessed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "T.cbl")
            make_cables(path, [(".500P3", {"F1": 2.16, "F2": 0.52}, 1.72, "FT")])
            spec_set, importer = import_set([path], name="region-a")
        self.assertEqual(spec_set.name, "region-a")
        self.assertEqual(len(spec_set.cables), 1)
        text = importer.report_text()
        self.assertIn("no .par file supplied", text)

    def test_report_is_human_readable(self):
        report = ImportReport(source="/x/T.cbl", kind="cables",
                              title="Lode Data Cables File",
                              records_scanned=100, records_kept=24)
        report.note("check me")
        text = report.to_text()
        self.assertIn("CABLES <- T.cbl", text)
        self.assertIn("24 of 100", text)
        self.assertIn("! check me", text)


if __name__ == "__main__":
    unittest.main()


class TestNetworkContainer(unittest.TestCase):
    """The .ntw container: header, keystream recovery, deobfuscation."""

    KEY = bytes((i * 37 + 11) % 251 + 1 for i in range(100))   # no zero bytes

    def _build(self, records, template=None):
        """A .ntw-shaped file: 512-byte header then XOR-obfuscated records."""
        template = template or bytes(100)
        header = bytearray(512)
        header[0:22] = b"Lode Data Network File"
        header[28:40] = b"Design 12.11"
        header[129:139] = b"LP-TEST123"
        header[145:153] = b"TESTUSER"
        body = bytearray()
        for index in range(400):
            plain = records.get(index, template)
            body += bytes(a ^ b for a, b in zip(plain, self.KEY))
        return bytes(header) + bytes(body)

    def _write(self, data, tmp):
        path = os.path.join(tmp, "T.ntw")
        with open(path, "wb") as fh:
            fh.write(data)
        return path

    def test_header_and_keystream_recovery(self):
        from lode.importers import read_network

        marker = bytes([9] * 20 + [0] * 80)
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write(self._build({7: marker, 190: marker}), tmp)
            net = read_network(path)
        self.assertEqual(net.title, "Lode Data Network File")
        self.assertEqual(net.version, "Design 12.11")
        self.assertEqual(net.licence, "LP-TEST123")
        self.assertEqual(net.user, "TESTUSER")
        # the template dominates, so the recovered stream is the true key
        self.assertEqual(net.keystream, self.KEY)
        self.assertGreater(net.zero_fraction, 0.9)

    def test_the_marked_records_come_back(self):
        from lode.importers import read_network

        marker = bytes([9] * 20 + [0] * 80)
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write(self._build({7: marker}), tmp)
            net = read_network(path)
        start = 7 * 100
        self.assertEqual(net.plain[start:start + 20], bytes([9] * 20))
        clusters = net.clusters()
        self.assertTrue(any(a == start for a, _ in clusters), clusters)

    def test_periodicity_is_measured_not_assumed(self):
        from lode.importers import period_confidence, read_network

        with tempfile.TemporaryDirectory() as tmp:
            path = self._write(self._build({}), tmp)
            net = read_network(path)
            raw = open(path, "rb").read()
        # an all-template body repeats perfectly at the period
        self.assertAlmostEqual(net.period_confidence, 1.0, places=6)
        self.assertLess(period_confidence(raw, 37), 0.5)

    def test_the_unfinished_layout_is_declared(self):
        """The reader must not imply it can reconstruct topology."""
        from lode.importers import read_network

        with tempfile.TemporaryDirectory() as tmp:
            path = self._write(self._build({3: bytes([1] * 100)}), tmp)
            net = read_network(path)
        joined = " ".join(net.notes).lower()
        self.assertIn("not decoded yet", joined)
        self.assertIn("known plaintext", joined)
        self.assertIn("NOT decoded", net.summary())

    def test_compare_reports_a_shared_keystream(self):
        from lode.importers import compare

        with tempfile.TemporaryDirectory() as tmp:
            a = os.path.join(tmp, "A.ntw")
            b = os.path.join(tmp, "B.ntw")
            with open(a, "wb") as fh:
                fh.write(self._build({2: bytes([5] * 100)}))
            with open(b, "wb") as fh:
                fh.write(self._build({9: bytes([6] * 100)}))
            text = compare([a, b])
        self.assertIn("share one keystream: True", text)


class TestDesignChartImport(unittest.TestCase):
    """Rebuilding a plant from an exported report, since .ntw is not decoded."""

    def _chart(self, text, specs=None):
        from lode.importers import read_design_chart

        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "chart.csv")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(text)
            return read_design_chart(path, name="t", specs=specs)

    def test_a_simple_run_rebuilds(self):
        net, report = self._chart(
            "Loc,Type,Device,Cable,Length,Units\n"
            "ND1,source,ND-750,,0,0\n"
            "1,tap,T4-17,P3-500,250,3\n"
            "2,tap,T4-14,P3-500,300,4\n")
        self.assertEqual(len(net.locations), 3)
        self.assertEqual(net.stats()["footage"], 550.0)
        self.assertEqual(report.rows_used, 3)
        self.assertEqual(net.validate(), [])

    def test_column_names_are_matched_not_positions(self):
        """Lode Data's exporter names columns its own way."""
        net, report = self._chart(
            "Footage;House Count;Location;Equipment\n"
            "0;0;ND1;ND-750\n"
            "250;3;A1;T4-17\n")
        self.assertEqual(report.columns["footage"], "Footage")
        self.assertEqual(report.columns["units"], "House Count")
        self.assertEqual(len(net.locations), 2)
        self.assertEqual(net.locations[net.ordered()[1].id].units, 3)

    def test_tab_separated_is_read(self):
        net, _ = self._chart("Loc\tLength\tUnits\tDevice\n"
                             "ND1\t0\t0\tND-750\nA1\t400\t2\tT4-20\n")
        self.assertEqual(len(net.locations), 2)
        self.assertEqual(net.feed_span(net.ordered()[1].id).length, 400.0)

    def test_legs_rebuild_the_branches(self):
        net, report = self._chart(
            "Loc,Leg,From,Type,Device,Cable,Length,Units\n"
            "ND1,TRUNK,,source,ND-750,,0,0\n"
            "SP1,TRUNK,,coupler,SP2,P3-500,200,0\n"
            "A1,SP1-THRU,SP1,tap,T4-17,P3-500,150,2\n"
            "A2,SP1-THRU,,tap,T4-14,P3-500,150,2\n"
            "B1,SP1-TAP1,SP1,tap,T4-17,P3-500,180,3\n")
        self.assertEqual(len(net.locations), 5)
        self.assertEqual(net.validate(), [])
        legs = {l.display(): len(l.locations) for l in net.legs()}
        self.assertEqual(len(legs), 3, legs)
        by_label = {l.label: l.id for l in net.locations.values()}
        self.assertEqual(net.parent_of(by_label["B1"]), by_label["SP1"])
        self.assertEqual(net.parent_of(by_label["A2"]), by_label["A1"])

    def test_a_flat_chart_says_so_rather_than_inventing_branches(self):
        net, report = self._chart(
            "Loc,Device,Length,Units\nND1,ND-750,0,0\nA1,T4-17,250,2\n")
        self.assertTrue(any("no leg or branch column" in n for n in report.notes))

    def test_a_bare_tap_value_resolves_through_the_spec_set(self):
        """Designers print tap values, not part numbers."""
        specs = generic750()
        net, _ = self._chart(
            "Loc,Type,Device,Length,Units\n"
            "ND1,source,ND-750,0,0\n"
            "A1,tap,17,250,3\n", specs=specs)
        tap = net.ordered()[1]
        self.assertEqual(tap.device, "T4-17")

    def test_an_unrecognisable_file_is_reported_not_guessed(self):
        net, report = self._chart("this is not a design chart\njust prose\n")
        self.assertEqual(len(net.locations), 0)
        self.assertTrue(any("no recognisable heading" in n for n in report.notes))

    def test_round_trip_through_our_own_export_is_lossless(self):
        from lode.engine.levels import LevelEngine
        from lode.examples import build_example_network
        from lode.reports import ReportBuilder

        specs = generic750()
        original = build_example_network()
        from lode.engine.autodesign import AutoDesigner
        AutoDesigner(specs, original).full_design()
        solution = LevelEngine(specs, original).solve()
        chart = ReportBuilder(specs, original, solution).design_chart()

        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "chart.csv")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(chart.to_csv())
            from lode.importers import read_design_chart
            rebuilt, _ = read_design_chart(path, name="rt", specs=specs)

        self.assertEqual(len(rebuilt.locations), len(original.locations))
        self.assertEqual(rebuilt.stats()["footage"], original.stats()["footage"])
        self.assertEqual(rebuilt.stats()["units"], original.stats()["units"])
        # and it must solve to the same levels, not merely look similar
        after = LevelEngine(specs, rebuilt).solve()
        before = {r.label: round(r.fwd_tap.get("F1", 0), 3)
                  for r in solution.taps()}
        now = {r.label: round(r.fwd_tap.get("F1", 0), 3) for r in after.taps()}
        self.assertEqual(before, now)
