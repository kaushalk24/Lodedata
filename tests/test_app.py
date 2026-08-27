"""Reports, the workspace, the command line and the HTTP API."""

import io
import json
import os
import tempfile
import unittest
import zipfile
from contextlib import redirect_stdout

from lode import cli
from lode.examples import build_example_network, build_example_workspace
from lode.library import generic750
from lode.reports import ReportBuilder, write_workbook
from lode.workspace import Workspace


class WorkspaceCase(unittest.TestCase):
    """A throwaway workspace with the example design already in it."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = self._tmp.name
        self.ws = Workspace(self.root)
        build_example_workspace(self.ws)
        self.specs = self.ws.load_specs("generic")
        self.net = self.ws.load_network("example")

    def tearDown(self):
        self._tmp.cleanup()


class TestReports(WorkspaceCase):
    def setUp(self):
        super().setUp()
        self.analysis = self.ws.analyse(self.specs, self.net)
        self.builder = ReportBuilder(self.specs, self.net,
                                     self.analysis.solution,
                                     self.analysis.performance,
                                     self.analysis.powering)

    def test_every_report_builds_and_renders(self):
        for report in self.builder.all_reports():
            self.assertTrue(report.title)
            self.assertTrue(report.columns, msg=report.title)
            text = report.to_text()
            self.assertIn(report.title, text)
            self.assertIn(report.columns[0], report.to_csv())
            json.dumps(report.to_dict())   # must be serialisable

    def test_design_chart_covers_every_location(self):
        chart = self.builder.design_chart()
        self.assertEqual(len(chart.rows), len(self.net.locations))

    def test_tap_distribution_counts_add_up(self):
        report = self.builder.tap_distribution()
        counted = sum(row["Count"] for row in report.rows)
        taps = sum(1 for l in self.net.locations.values() if l.kind == "tap")
        self.assertEqual(counted, taps)
        units = sum(row["Units"] for row in report.rows)
        self.assertEqual(units, sum(l.units for l in self.net.locations.values()))

    def test_bill_of_materials_prices_the_design(self):
        report = self.builder.bill_of_materials()
        cable = [r for r in report.rows if r["Category"] == "Cable"]
        self.assertTrue(cable)
        footage = sum(r["Quantity"] for r in cable)
        self.assertAlmostEqual(footage, self.net.stats()["footage"], places=4)
        self.assertGreater(sum(r["Total"] for r in report.rows), 0)

    def test_workbook_is_a_valid_xlsx(self):
        path = os.path.join(self.root, "reports.xlsx")
        write_workbook(path, self.builder.all_reports())
        with zipfile.ZipFile(path) as zf:
            names = zf.namelist()
            self.assertIn("[Content_Types].xml", names)
            self.assertIn("xl/workbook.xml", names)
            self.assertIn("xl/worksheets/sheet1.xml", names)
            self.assertIsNone(zf.testzip())
            book = zf.read("xl/workbook.xml").decode()
        self.assertIn("Design Chart", book)


class TestExampleDesign(WorkspaceCase):
    def test_the_shipped_example_is_in_spec(self):
        analysis = self.ws.analyse(self.specs, self.net)
        errors = [f.message for f in analysis.all_flags if f.severity == "error"]
        self.assertEqual(errors, [])

    def test_the_example_network_is_structurally_sound(self):
        self.assertEqual(self.net.validate(), [])
        self.assertEqual(build_example_network().validate(), [])

    def test_saving_and_reloading_preserves_the_design(self):
        before = self.ws.analyse(self.specs, self.net).solution
        path = self.ws.save_network(self.net, "roundtrip")
        again = self.ws.load_network("roundtrip")
        after = self.ws.analyse(self.specs, again).solution
        self.assertEqual(before.order, after.order)
        for loc_id in before.order:
            self.assertEqual(before[loc_id].fwd_tap, after[loc_id].fwd_tap)
        self.assertTrue(os.path.exists(path))


class TestCommandLine(WorkspaceCase):
    def _run(self, *args):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = cli.main(["-w", self.root, *args])
        return code, buffer.getvalue()

    def test_specs_command_reports_a_clean_set(self):
        code, out = self._run("specs")
        self.assertEqual(code, 0)
        self.assertIn("validates cleanly", out)

    def test_calc_prints_the_design_chart(self):
        code, out = self._run("calc", "example")
        self.assertEqual(code, 0)
        self.assertIn("Design Chart", out)
        self.assertIn("ND1", out)

    def test_every_report_is_reachable_from_the_command_line(self):
        for name in ("design", "actives", "taps", "performance", "power",
                     "bom", "flags", "mdu", "notes", "powering-detail"):
            code, out = self._run("report", name, "example")
            self.assertEqual(code, 0, msg=name)
            self.assertTrue(out.strip(), msg=name)

    def test_report_exports_a_workbook(self):
        target = os.path.join(self.root, "out", "all.xlsx")
        code, out = self._run("report", "all", "example", "--xlsx", target)
        self.assertEqual(code, 0)
        self.assertTrue(os.path.exists(target))
        with zipfile.ZipFile(target) as zf:
            self.assertIsNone(zf.testzip())

    def test_design_is_idempotent_on_a_finished_design(self):
        code, first = self._run("design", "example")
        self.assertEqual(code, 0)
        code, second = self._run("design", "example")
        self.assertEqual(code, 0)
        self.assertIn("0 change(s)", second)

    def test_dry_run_leaves_the_file_alone(self):
        path = self.ws.network_path("example")
        with open(path, "rb") as fh:
            before = fh.read()
        self._run("design", "example", "--dry-run")
        with open(path, "rb") as fh:
            self.assertEqual(before, fh.read())

    def test_unknown_report_is_a_clean_error(self):
        with self.assertRaises(SystemExit):
            cli.main(["-w", self.root, "report", "nope", "example"])


class TestHttpApi(WorkspaceCase):
    """Drive the request handler directly, without opening a socket."""

    def _call(self, method, path, body=None):
        from lode.web.server import Handler

        class FakeHandler(Handler):
            def __init__(self, outer):
                self.outer = outer
                self.status = None
                self.payload = None
                self.headers = {"Content-Length": str(len(body or ""))}
                self.rfile = io.BytesIO((body or "").encode())
                self.command = method
                self.path = path

            def _send(self, status, data, content_type, extra=None):
                self.status = status
                self.content_type = content_type
                self.payload = data

            def log_message(self, *a):
                pass

        Handler.workspace = self.ws
        handler = FakeHandler(self)
        handler._dispatch(method)
        data = handler.payload
        if "json" in getattr(handler, "content_type", ""):
            data = json.loads(data.decode())
        return handler.status, data

    def test_workspace_endpoint(self):
        status, data = self._call("GET", "/api/workspace")
        self.assertEqual(status, 200)
        self.assertIn("generic", data["spec_sets"])
        self.assertIn("example", data["networks"])

    def test_specs_endpoint_returns_every_file(self):
        status, data = self._call("GET", "/api/specs/generic")
        self.assertEqual(status, 200)
        for kind in ("parameters", "actives", "taps", "couplers", "cables",
                     "performance", "pricing"):
            self.assertIn(kind, data["files"])
        self.assertEqual(data["warnings"], [])

    def test_analyse_endpoint_solves_a_posted_network(self):
        payload = json.dumps({"network": self.net.to_dict(), "spec": "generic"})
        status, data = self._call("POST", "/api/analyse", payload)
        self.assertEqual(status, 200)
        self.assertEqual(data["analysis"]["solution"]["status"], "warn")
        self.assertEqual(data["problems"], [])
        self.assertEqual(data["stats"]["taps"], 19)

    def test_design_endpoint_returns_a_changed_network(self):
        for loc in self.net.locations.values():
            if loc.kind == "tap":
                loc.device = "T4-4"
        payload = json.dumps({"network": self.net.to_dict(), "spec": "generic",
                              "action": "taps"})
        status, data = self._call("POST", "/api/design", payload)
        self.assertEqual(status, 200)
        self.assertTrue(data["run"]["changes"])
        devices = {l["device"] for l in data["network"]["locations"]
                   if l["kind"] == "tap"}
        self.assertGreater(len(devices), 1)

    def test_report_endpoint_serves_json_and_csv(self):
        payload = json.dumps({"network": self.net.to_dict(), "spec": "generic"})
        status, data = self._call("POST", "/api/report/bom?format=json", payload)
        self.assertEqual(status, 200)
        self.assertEqual(data["reports"][0]["title"], "Bill of Materials")
        status, raw = self._call("POST", "/api/report/taps?format=csv", payload)
        self.assertEqual(status, 200)
        self.assertIn(b"Tap,Value,Ports", raw)

    def test_saving_a_network_through_the_api(self):
        network = self.net.to_dict()
        network["name"] = "via-api"
        payload = json.dumps({"network": network, "name": "via-api"})
        status, data = self._call("POST", "/api/network/via-api", payload)
        self.assertEqual(status, 200)
        self.assertIn("via-api", data["networks"])

    def test_unknown_route_is_404(self):
        status, data = self._call("GET", "/api/nonsense")
        self.assertEqual(status, 404)
        self.assertIn("no api route", data["error"])

    def test_static_files_are_served(self):
        status, data = self._call("GET", "/index.html")
        self.assertEqual(status, 200)
        self.assertIn(b"OpenLode", data)

    def test_directory_traversal_is_refused(self):
        status, _ = self._call("GET", "/../../etc/passwd")
        self.assertEqual(status, 404)


if __name__ == "__main__":
    unittest.main()
