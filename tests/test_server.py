"""The app as a shared server: several people, each on their own network,
changes arriving at once -- with one server process and with several.

Starts the real server on a free port with its own database; needs nothing
but the app's own packages.
"""
import concurrent.futures as cf
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))
sys.path.insert(0, str(ROOT / "tools"))


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module", params=[1, 3], ids=["one process", "three processes"])
def server(request, tmp_path_factory):
    port = _free_port()
    env = dict(os.environ, LODEDATA_DB=str(tmp_path_factory.mktemp("db") / "t.db"))
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "api:app", "--app-dir", "app",
         "--port", str(port), "--log-level", "warning", "--workers", str(request.param)],
        cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    url = f"http://127.0.0.1:{port}"
    for _ in range(80):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                break
        except OSError:
            time.sleep(0.25)
    for _ in range(80):          # every process ready to answer
        try:
            _call(url, "GET", "/api/networks")
            break
        except OSError:
            time.sleep(0.25)
    yield url
    proc.terminate()
    proc.wait(timeout=10)


def _call(url, method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url + path, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read() or b"null")


def _feeder(doc):
    branches = doc["branches"]
    return branches[0] if isinstance(branches, list) else next(iter(branches.values()))


def test_changes_to_one_network_at_the_same_moment_are_all_kept(server):
    # each change reads the network, changes it and writes it back whole;
    # without taking them one at a time, 28 of these 31 were lost
    nid = _call(server, "POST", "/api/networks", {"name": "shared", "sample_specs": True})["id"]
    for _ in range(30):
        _call(server, "POST", f"/api/networks/{nid}/branches/1/nodes", {})
    lines = len(_feeder(_call(server, "GET", f"/api/networks/{nid}"))["nodes"])
    with cf.ThreadPoolExecutor(lines) as pool:
        list(pool.map(lambda k: _call(server, "PATCH", f"/api/networks/{nid}/nodes/1/{k}",
                                      {"ftg": 100 + k}), range(1, lines + 1)))
    got = [n["ftg"] for n in _feeder(_call(server, "GET", f"/api/networks/{nid}"))["nodes"]]
    assert got == [100 + k for k in range(1, lines + 1)]


def test_people_on_different_networks_work_side_by_side(server):
    ids = [_call(server, "POST", "/api/networks", {"name": f"user {k}", "sample_specs": True})["id"]
           for k in range(4)]
    with cf.ThreadPoolExecutor(8) as pool:
        list(pool.map(lambda nid: _call(server, "PATCH", f"/api/networks/{nid}/nodes/1/1",
                                        {"ftg": 250}), ids * 2))
    for nid in ids:
        assert _feeder(_call(server, "GET", f"/api/networks/{nid}"))["nodes"][0]["ftg"] == 250


def _upload(url, name, data):
    boundary = "lodedata-test-boundary"
    body = (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{name}"\r\n'
            "Content-Type: application/octet-stream\r\n\r\n").encode() + data + \
        f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(url + "/api/import/ntw", data=body, method="POST",
                                 headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())["id"]


def _save(url, nid, name):
    req = urllib.request.Request(f"{url}/api/networks/{nid}/ntw?filename={name}.ntw", method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def test_a_new_network_takes_its_own_person_s_header(server):
    # A network keyed in from scratch is written with the licence and user
    # fields of the last .ntw its person opened -- never someone else's
    from hfc.exporter import export_ntw
    from hfc.plant import Design
    d = Design(id="x", name="PERSON_A")
    d.ensure_feeder()
    head = bytearray(export_ntw(d, None, name="PERSON_A")[0][:512])
    head[129:141] = b"LP-TEST0001\0"          # made-up licence and user fields
    head[145:152] = b"tester\0"
    opened = _upload(server, "PERSON_A.ntw", export_ntw(d, None, name="PERSON_A", header=bytes(head))[0])
    mine = _call(server, "POST", "/api/networks", {"name": "mine", "header_from": opened})["id"]
    theirs = _call(server, "POST", "/api/networks", {"name": "theirs"})["id"]
    assert _save(server, mine, "mine")[129:152] == bytes(head[129:152])
    assert _save(server, theirs, "theirs")[129:161] == bytes(32)
