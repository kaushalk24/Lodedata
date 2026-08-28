"""A dependency-free HTTP front end.

The server is deliberately stateless: the browser holds the network being
edited and posts it back for recalculation on every change, which is what
gives Design Mode its "instant recalculations of what-if scenarios".  Files
are only touched when the designer saves.
"""

from __future__ import annotations

import json
import mimetypes
import os
import posixpath
import threading
import traceback
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

from ..engine.autodesign import AutoDesigner
from ..network import Network, NetworkError
from ..reports import REPORTS, write_workbook
from ..specs import SPEC_KINDS, SpecError
from ..workspace import Workspace

STATIC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")


class ApiError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


class Handler(BaseHTTPRequestHandler):
    server_version = "OpenLode/1.0"
    workspace: Workspace = None  # type: ignore[assignment]

    # -- plumbing --------------------------------------------------------
    def log_message(self, fmt, *args) -> None:  # quieter console
        if self.path.startswith("/api/"):
            super().log_message(fmt, *args)

    def _send(self, status: int, body: bytes, content_type: str,
              extra: dict | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for key, value in (extra or {}).items():
            self.send_header(key, value)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _json(self, payload, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self._send(status, body, "application/json; charset=utf-8")

    def _text(self, text: str, content_type="text/plain; charset=utf-8",
              filename: str = "") -> None:
        extra = {}
        if filename:
            extra["Content-Disposition"] = f'attachment; filename="{filename}"'
        self._send(200, text.encode("utf-8"), content_type, extra)

    def _body(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        if not length:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ApiError(f"malformed request body: {exc}")

    # -- routing ---------------------------------------------------------
    def do_GET(self) -> None:
        self._dispatch("GET")

    def do_HEAD(self) -> None:
        self._dispatch("GET")

    def do_POST(self) -> None:
        self._dispatch("POST")

    def _dispatch(self, method: str) -> None:
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        query = parse_qs(parsed.query)
        try:
            if path.startswith("/api/"):
                self._api(method, path[5:].strip("/"), query)
            elif method == "GET":
                self._static(path)
            else:
                raise ApiError("not found", 404)
        except ApiError as exc:
            self._json({"error": str(exc)}, exc.status)
        except (SpecError, KeyError, ValueError) as exc:
            self._json({"error": str(exc)}, 400)
        except Exception as exc:  # pragma: no cover - surfaced to the browser
            traceback.print_exc()
            self._json({"error": f"{type(exc).__name__}: {exc}"}, 500)

    # -- static files ----------------------------------------------------
    def _static(self, path: str) -> None:
        if path in ("/", ""):
            path = "/index.html"
        safe = posixpath.normpath(path).lstrip("/")
        if safe.startswith(".."):
            raise ApiError("not found", 404)
        full = os.path.join(STATIC, safe)
        if not os.path.isfile(full):
            raise ApiError("not found", 404)
        ctype, _ = mimetypes.guess_type(full)
        with open(full, "rb") as fh:
            self._send(200, fh.read(), ctype or "application/octet-stream")

    # -- structural edits --------------------------------------------
    @staticmethod
    def _apply_edit(network: Network, specs, op: str, args: dict) -> None:
        """Apply one structural edit, in the model rather than the browser.

        Keeping these in Python means the grid, the command line and any
        script all go through the same, tested implementation.
        """
        if op == "insert_after":
            network.insert_after(
                args["location"], port=args.get("port", ""),
                jumper=float(args.get("jumper", 0.0) or 0.0),
                cable=args.get("cable", ""), **(args.get("fields") or {}))
        elif op == "insert_before":
            network.insert_before(
                args["location"], jumper=float(args.get("jumper", 0.0) or 0.0),
                out_port=args.get("out_port", "OUT"),
                cable=args.get("cable", ""), **(args.get("fields") or {}))
        elif op == "splice_out":
            network.splice_out(args["location"])
        elif op == "remove":
            network.remove_location(args["location"])
        elif op == "swap_ports":
            network.swap_ports(args["location"], args["port_a"], args["port_b"])
        elif op == "move_leg":
            network.move_leg(args["span"], args["parent"], args["port"])
        elif op == "name_leg":
            network.name_leg(args["span"], args.get("name", ""))
        elif op == "set_tap_value":
            loc = network.locations.get(args["location"])
            if loc is None:
                raise NetworkError(f"unknown location {args['location']!r}")
            current = specs.taps.by_id(loc.device)
            ports = int(args.get("ports") or (current.ports if current else 4))
            tsg = int(loc.tsg or specs.parameters.default_tsg)
            tap = specs.taps.find_value(
                float(args["value"]), ports, tsg,
                self_terminating=(current.self_terminating if current else False))
            if tap is None:
                raise NetworkError(
                    f"no tap of value {args['value']} in selection group {tsg}")
            loc.kind = "tap"
            loc.device = tap.id
        else:
            raise ApiError(f"unknown edit operation {op!r}", 400)

    # -- api -------------------------------------------------------------
    def _api(self, method: str, route: str, query: dict) -> None:
        ws = self.workspace
        parts = route.split("/") if route else []
        head = parts[0] if parts else ""

        def one(name: str, default: str = "") -> str:
            values = query.get(name)
            return values[0] if values else default

        if head == "workspace" and method == "GET":
            self._json({
                "root": ws.root,
                "spec_sets": ws.spec_sets(),
                "networks": ws.networks(),
                "reports": sorted(REPORTS),
            })
            return

        if head == "specs":
            name = parts[1] if len(parts) > 1 else one("spec")
            specs = ws.load_specs(name)
            if method == "GET" and len(parts) <= 2:
                payload = {
                    "summary": specs.summary(),
                    "warnings": specs.validate(),
                    "files": {
                        kind: getattr(specs, kind).to_dict()
                        for kind in SPEC_KINDS
                        if getattr(specs, kind) is not None
                    },
                }
                self._json(payload)
                return
            if method == "POST" and len(parts) == 3:
                kind = parts[2]
                if kind not in SPEC_KINDS:
                    raise ApiError(f"unknown spec kind {kind!r}", 404)
                spec_cls = SPEC_KINDS[kind][0]
                updated = spec_cls.from_dict(self._body())
                setattr(specs, kind, updated)
                warnings = specs.validate()
                target = os.path.join(ws.spec_root, name or ws.spec_sets()[0])
                path = os.path.join(target, f"{specs.name}{spec_cls.EXT}")
                updated.save(path)
                ws.load_specs(name, reload=True)
                self._json({"saved": path, "warnings": warnings})
                return
            raise ApiError("not found", 404)

        if head == "network":
            name = parts[1] if len(parts) > 1 else one("network")
            if method == "GET":
                network = ws.load_network(name)
                self._json({"network": network.to_dict()})
                return
            if method == "POST":
                body = self._body()
                network = Network.from_dict(body.get("network") or body)
                path = ws.save_network(network, body.get("name") or name)
                self._json({"saved": path, "networks": ws.networks()})
                return

        if head == "analyse" and method == "POST":
            body = self._body()
            specs = ws.load_specs(body.get("spec", ""))
            network = Network.from_dict(body["network"])
            analysis = ws.analyse(
                specs, network,
                load_factor=float(body.get("load_factor", 1.0) or 1.0),
                extra_load=body.get("extra_load") or {},
            )
            self._json({
                "analysis": analysis.to_dict(),
                "stats": network.stats(),
                "problems": network.validate(),
                "legs": [leg.to_dict() for leg in network.legs()],
            })
            return

        if head == "edit" and method == "POST":
            body = self._body()
            specs = ws.load_specs(body.get("spec", ""))
            network = Network.from_dict(body["network"])
            op = body.get("op", "")
            args = body.get("args") or {}
            try:
                self._apply_edit(network, specs, op, args)
            except NetworkError as exc:
                raise ApiError(str(exc), 409) from exc
            analysis = ws.analyse(specs, network)
            self._json({
                "network": network.to_dict(),
                "analysis": analysis.to_dict(),
                "stats": network.stats(),
                "problems": network.validate(),
                "legs": [leg.to_dict() for leg in network.legs()],
            })
            return

        if head == "design" and method == "POST":
            body = self._body()
            specs = ws.load_specs(body.get("spec", ""))
            network = Network.from_dict(body["network"])
            designer = AutoDesigner(specs, network)
            action = body.get("action", "full")
            if action == "taps":
                run = designer.auto_taps()
            elif action == "ports":
                run = designer.auto_taps(max_passes=1)
                run.changes = designer.auto_ports()
            elif action == "actives":
                changes = designer.auto_actives()
                run = designer.auto_taps()
                run.changes = changes + run.changes
            elif action == "rebalance":
                run = designer.auto_taps(max_passes=1)
                run.changes = designer.rebalance()
            else:
                run = designer.full_design()
            analysis = ws.analyse(specs, network)
            self._json({
                "network": network.to_dict(),
                "run": run.to_dict(),
                "analysis": analysis.to_dict(),
                "stats": network.stats(),
            })
            return

        if head == "report":
            body = self._body() if method == "POST" else {}
            name = parts[1] if len(parts) > 1 else one("name", "design")
            fmt = one("format", body.get("format", "text"))
            specs = ws.load_specs(body.get("spec", one("spec")))
            if body.get("network"):
                network = Network.from_dict(body["network"])
            else:
                network = ws.load_network(one("network"))
            analysis = ws.analyse(specs, network)
            builder = ws.reports(specs, network, analysis)
            if name == "all" or fmt == "xlsx":
                reports = (builder.all_reports() if name == "all"
                           else [ws.report(specs, network, analysis, name)])
            else:
                reports = [ws.report(specs, network, analysis, name)]
            if fmt == "xlsx":
                ws.ensure()
                path = os.path.join(ws.report_root, f"{network.name}-{name}.xlsx")
                write_workbook(path, reports)
                with open(path, "rb") as fh:
                    self._send(
                        200, fh.read(),
                        "application/vnd.openxmlformats-officedocument."
                        "spreadsheetml.sheet",
                        {"Content-Disposition":
                         f'attachment; filename="{os.path.basename(path)}"'})
                return
            if fmt == "csv":
                self._text("\n\n".join(r.to_csv() for r in reports),
                           "text/csv; charset=utf-8",
                           filename=f"{network.name}-{name}.csv")
                return
            if fmt == "json":
                self._json({"reports": [r.to_dict() for r in reports]})
                return
            self._text("\n\n\n".join(r.to_text() for r in reports))
            return

        raise ApiError(f"no api route for /{route}", 404)


def serve(workspace: Workspace, host: str = "127.0.0.1", port: int = 8765,
          open_browser: bool = True) -> None:
    workspace.ensure()
    Handler.workspace = workspace
    httpd = ThreadingHTTPServer((host, port), Handler)
    url = f"http://{host}:{port}/"
    print(f"OpenLode Design Assistant\n  workspace : {workspace.root}")
    print(f"  spec sets : {', '.join(workspace.spec_sets()) or '(none)'}")
    print(f"  networks  : {', '.join(workspace.networks()) or '(none)'}")
    print(f"\n  serving   : {url}\n  stop with Ctrl-C")
    if open_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        httpd.server_close()
