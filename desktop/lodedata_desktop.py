"""The Design Assistant as a Windows program (LodeData.exe).

The same app, in a window of its own instead of a browser: the engine runs
inside the program, on this PC only (127.0.0.1, never on the network), and
the page talks to it there. Nothing is needed from a server or the internet.

* The networks opened are kept for this Windows user in
  %LOCALAPPDATA%\\LodeData (designs.db), as the server keeps them in
  data/designs.db.
* File > Open and Save Network use Windows' own dialogs, and Save writes
  straight back into the .ntw, as Lode Data does (the page reaches them
  through ``Files`` below).

    LodeData.exe            the program
    LodeData.exe --check    start the engine, open and save a network
                            through it, exit 0 if all went well (the build's
                            own check)
"""
import base64
import os
import socket
import sys
import tempfile
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for p in (ROOT / "app", ROOT / "tools"):         # running from a checkout
    if p.is_dir() and str(p) not in sys.path:
        sys.path.insert(0, str(p))

PORT = 17170          # a fixed port keeps the page's own settings from one start to the next


def data_dir() -> Path:
    d = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "LodeData"
    d.mkdir(parents=True, exist_ok=True)
    return d


def free_port() -> int:
    for port in (PORT, 0):
        with socket.socket() as s:
            try:
                s.bind(("127.0.0.1", port))
                return s.getsockname()[1]
            except OSError:
                continue
    raise RuntimeError("no free port")


def start_engine(port: int):
    """The app's server, on this PC only, in a thread of this program."""
    import uvicorn
    from api import app
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port,
                                           log_config=None, log_level="warning"))
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(200):
        if server.started:
            return server
        time.sleep(0.05)
    raise RuntimeError("the engine did not start")


class Files:
    """Windows' Open and Save dialogs for .ntw files, for the page."""
    TYPES = ("Lode Data network (*.ntw)", "All files (*.*)")

    def __init__(self):
        self._window = None

    def open_ntw(self):
        import webview
        kind = getattr(getattr(webview, "FileDialog", None), "OPEN", None) or webview.OPEN_DIALOG
        r = self._window.create_file_dialog(kind, file_types=self.TYPES)
        return r[0] if r else None

    def save_ntw(self, name):
        import webview
        kind = getattr(getattr(webview, "FileDialog", None), "SAVE", None) or webview.SAVE_DIALOG
        r = self._window.create_file_dialog(kind, save_filename=name or "network.ntw",
                                            file_types=self.TYPES)
        if not r:
            return None
        path = r if isinstance(r, str) else r[0]
        return path if path.lower().endswith(".ntw") else path + ".ntw"

    def read_file(self, path):
        return base64.b64encode(Path(path).read_bytes()).decode("ascii")

    def write_file(self, path, data):
        Path(path).write_bytes(base64.b64decode(data))
        return True


def check(port: int) -> int:
    """Open and save a network through the engine, as the page does."""
    import json
    import urllib.request
    base = f"http://127.0.0.1:{port}"

    def call(method, path, body=None, raw=False):
        req = urllib.request.Request(base + path, method=method,
                                     data=json.dumps(body).encode() if body is not None else None,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = r.read()
        return data if raw else json.loads(data)

    page = call("GET", "/", raw=True)
    assert b"app.js" in page, "the page is missing"
    assert call("GET", "/app.js", raw=True), "app.js is missing"
    net = call("POST", "/api/networks", {"name": "CHECK"})
    ntw = call("POST", f"/api/networks/{net['id']}/ntw?filename=CHECK.ntw", raw=True)
    assert ntw[:22] == b"Lode Data Network File", "the saved file is not a .ntw"
    call("DELETE", f"/api/networks/{net['id']}")
    if sys.platform == "win32":
        # the window's parts (Edge WebView2 through .NET) are in the program
        from webview.platforms import edgechromium  # noqa: F401
    return 0


def main() -> int:
    checking = "--check" in sys.argv
    data = Path(tempfile.mkdtemp()) if checking else data_dir()
    if sys.stdout is None:                       # no console: keep what it says
        log = Path("lodedata-check.log") if checking else data / "lodedata.log"
        sys.stdout = sys.stderr = open(log, "a", encoding="utf-8")
    os.environ.setdefault("LODEDATA_DB", str(data / "designs.db"))
    port = free_port()
    server = start_engine(port)
    if checking:
        try:
            return check(port)
        except Exception:
            import traceback
            print("check failed:\n" + traceback.format_exc())
            return 1
        finally:
            server.should_exit = True

    import webview
    files = Files()
    window = webview.create_window("Design Assistant", f"http://127.0.0.1:{port}/",
                                   js_api=files, maximized=True, min_size=(1000, 650))
    files._window = window
    if hasattr(webview, "settings"):
        webview.settings["ALLOW_DOWNLOADS"] = True       # the reports' CSV files
    webview.start(private_mode=False, storage_path=str(data / "window"))
    server.should_exit = True
    return 0


if __name__ == "__main__":
    sys.exit(main())
