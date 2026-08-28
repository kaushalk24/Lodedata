"""The Lode Data binary importer.

No customer library is committed here, so the fixtures are synthesised in the
same format the real files use -- which also documents that format precisely.
"""

import os
import struct
import tempfile
import unittest

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
