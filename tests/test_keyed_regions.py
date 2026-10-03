"""Networks keyed in Lode Data on the regions' spec sets, against the user's
screenshots of them (2 Oct): BH1GHzMid and HUMB1GHzMid, the 7-29-2025 sets.

    1.1  amp 71 (NC4000 1x1)
    1.2-1.4  coupler 99 (BH: Node Split) / 92 (HUMB: no part number) to
             branches 2, 3 and 4
    1.5  190 ft, hc 2, tap 26        1.6  189 ft, hc 5, tap 21
    1.7  amp 11 (FM332)

keyed through the program's own API, as the screen's keys do.  Skipped
unless the two spec sets are under samples/ (the user's files: never
committed).
"""
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
import uuid
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = Path(os.environ.get("LODEDATA_SAMPLES", ROOT / "samples"))


def _set(name):
    base = next((p.with_suffix("") for p in SAMPLES.rglob(f"{name}.par")), None) \
        if SAMPLES.is_dir() else None
    if base is None:
        pytest.skip(f"{name} not in samples")
    return base


@pytest.fixture(scope="module")
def server(tmp_path_factory):
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    env = dict(os.environ, LODEDATA_DB=str(tmp_path_factory.mktemp("db") / "t.db"))
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "api:app", "--app-dir", "app",
         "--port", str(port), "--log-level", "warning"],
        cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    url = f"http://127.0.0.1:{port}"
    for _ in range(120):
        try:
            _call(url, "GET", "/api/networks")
            break
        except OSError:
            time.sleep(0.25)
    yield url
    proc.terminate()
    proc.wait(timeout=10)


def _call(url, method, path, body=None, files=None):
    headers = {}
    data = None
    if files is not None:
        bound = uuid.uuid4().hex
        parts = []
        for name, content in files:
            parts.append(f'--{bound}\r\nContent-Disposition: form-data; name="files"; '
                         f'filename="{name}"\r\nContent-Type: application/octet-stream\r\n\r\n'
                         .encode() + content + b"\r\n")
        data = b"".join(parts) + f"--{bound}--\r\n".encode()
        headers["Content-Type"] = f"multipart/form-data; boundary={bound}"
    elif body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url + path, data=data, method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read() or b"null")


def _keyed(url, name, coupler):
    base = _set(name)
    nid = _call(url, "POST", "/api/networks", {"name": "Untitled"})["id"]
    files = [(base.name + ext, (base.parent / (base.name + ext)).read_bytes())
             for ext in (".par", ".atv", ".tap", ".cpr", ".cbl")]
    assert _call(url, "POST", f"/api/networks/{nid}/library/spec", files=files)["loaded"]

    def line():
        _call(url, "POST", f"/api/networks/{nid}/branches/1/nodes", {"after": 0})

    def node(n, **edit):
        _call(url, "PATCH", f"/api/networks/{nid}/nodes/1/{n}", edit)

    node(1, amp_code="71")
    for n in (2, 3, 4):
        line()
        _call(url, "PUT", f"/api/networks/{nid}/nodes/1/{n}/coupler", {"code": coupler})
    for n, ftg, hc, tap in ((5, 190, 2, "26"), (6, 189, 5, "21")):
        line()
        node(n, ftg=ftg, hc=hc)
        _call(url, "PUT", f"/api/networks/{nid}/nodes/1/{n}/tap", {"code": tap})
    line()
    node(7, amp_code="11")
    return _call(url, "GET", f"/api/networks/{nid}/screen")


def _lines(screen):
    """Each line of branch 1 as the screen shows it: the four level columns,
    then the extra ones after the cplr[branch] columns."""
    return [([f"{v:.2f}" for v in r["levels"]], [f"{v:.2f}" for v in r["extra_levels"]])
            for r in screen["rows"] if r["branch"] == 1]


BH = [  # the user's screenshot 1, every number
    (["0.00", "0.00", "0.00", "0.00"], ["0.00", "0.00"]),
    (["52.00", "38.00", "11.00", "11.00"], ["45.00", "50.00"]),
    (["52.00", "38.00", "11.00", "11.00"], ["45.00", "50.00"]),
    (["52.00", "38.00", "11.00", "11.00"], ["45.00", "50.00"]),
    (["47.17", "36.59", "12.29", "11.30"], ["41.54", "45.55"]),
    (["41.37", "34.70", "14.08", "11.91"], ["37.50", "40.23"]),
    (["39.67", "33.70", "15.08", "13.01"], ["36.40", "38.73"]),
    (["52.00", "38.00", "11.00", "11.00"], ["45.00", "50.00"]),
]
HUMB = [  # screenshot 2
    (["0.00", "0.00", "0.00", "0.00"], ["0.00", "0.00"]),
    (["51.00", "37.00", "11.00", "11.00"], ["44.50", "49.00"]),
    (["51.00", "37.00", "11.00", "11.00"], ["44.50", "49.00"]),
    (["51.00", "37.00", "11.00", "11.00"], ["44.50", "49.00"]),
    (["46.17", "35.59", "12.29", "11.30"], ["41.04", "44.55"]),
    (["39.57", "33.90", "13.88", "11.91"], ["36.70", "38.73"]),
    (["39.57", "33.90", "13.88", "11.91"], ["36.70", "38.73"]),
    (["51.00", "37.00", "11.00", "11.00"], ["44.00", "49.00"]),
]


def test_bh1ghzmid_keyed_as_on_the_screenshot(server):
    s = _keyed(server, "BH1GHzMid", "99")
    assert s["labels"] == ["1002", "102", "85", "5"] and s["extra_labels"] == ["550", "860"]
    assert _lines(s) == BH
    rows = [r for r in s["rows"] if r["branch"] == 1 and not r["end"]]
    assert [r["couplers"] for r in rows[1:4]] == [["99<2>"], ["99<3>"], ["99<4>"]]
    assert [(r["taps"], r["tap_severity"]) for r in rows[4:6]] == [(["/26/"], [""]), (["<21>"], [""])]
    box = rows[6]["amp_info"]
    assert (box["type"], box["cascade"], box["homes_down"]) == ("FM332", 1, 0)
    assert [box[k] for k in ("aerial_prev", "aerial_start", "total_split", "total_prev",
                             "total_start")] == [379.0] * 5


def test_humb1ghzmid_keyed_as_on_the_screenshot(server):
    # coupler 92 has no part number and tap row 21 no part at all: Lode draws
    # both, 92<2> green and <21> yellow, and the levels go on through them
    s = _keyed(server, "HUMB1GHzMid", "92")
    assert s["labels"] == ["1002", "102", "85", "5"] and s["extra_labels"] == ["550", "870"]
    assert _lines(s) == HUMB
    rows = [r for r in s["rows"] if r["branch"] == 1 and not r["end"]]
    assert [r["couplers"] for r in rows[1:4]] == [["92<2>"], ["92<3>"], ["92<4>"]]
    assert [(r["taps"], r["tap_severity"]) for r in rows[4:6]] == [(["/26/"], [""]),
                                                                   (["<21>"], ["yellow"])]


def test_the_pads_and_eqs_lode_picked_at_1_7():
    """Forward Pad Flag, Forward Eq CS2 (HUMB: CS1), Return Pad Flag, Return
    Eq 3 in both boxes: the largest pad that fits is the bank's Flag row
    (21 dB), and with Allow Over Equalization unticked the forward EQ leaves
    no more tilt than the FM332's own."""
    sys.path[:0] = [str(ROOT / "app"), str(ROOT / "tools")]
    from hfc.importer import library_from_spec_set, parameters_from_spec_set
    from hfc.screen import choose_pads_eqs
    for name, levels, want in (
            ("BH1GHzMid", (39.6734, 33.6954, 15.08, 13.01), ["Flag", "Flag", "CS2", "3"]),
            ("HUMB1GHzMid", (39.5734, 33.8954, 13.88, 11.91), ["Flag", "Flag", "CS1", "3"])):
        base = _set(name)
        params = parameters_from_spec_set(base)
        assert params.allow_over_equalization is False
        lib = library_from_spec_set(base, params)
        fm332 = next(a for a in lib.actives.values() if a.active_id == "11")
        at = dict(zip((params.forward_high_mhz, params.forward_low_mhz,
                       params.return_high_mhz, params.return_low_mhz), levels))
        picked = choose_pads_eqs(fm332, at, params)
        assert [fm332.pad_eq[c][1][v].strip() for c, v in enumerate(picked)] == want, name


def _new(url, name):
    base = _set(name)
    nid = _call(url, "POST", "/api/networks", {"name": "Untitled"})["id"]
    files = [(base.name + ext, (base.parent / (base.name + ext)).read_bytes())
             for ext in (".par", ".atv", ".tap", ".cpr", ".cbl")]
    assert _call(url, "POST", f"/api/networks/{nid}/library/spec", files=files)["loaded"]
    return nid


def _row(screen, branch, node):
    return next(r for r in screen["rows"] if r["branch"] == branch and r["node"] == node and not r["end"])


def _levels(row):
    return [f"{v:.2f}" for v in row["levels"]] + [f"{v:.2f}" for v in row["extra_levels"]]


def test_pads_and_eqs_are_picked_as_the_amp_is_keyed_and_again_when_its_input_changes(server):
    """The user's 1a and 1b (3 Oct): BH1GHzMid, 1.1 amp 71, 1.2 190 ft hc 2,
    1.3 amp 11.  Keyed, the FM332's box reads Forward Pad Flag, Forward Eq
    CS8, Return Pad Flag, Return Eq 2; 1.3's ftg 0 -> 900 and it reads 060
    / 13 / 190 / 6 (Recalc changes nothing)."""
    nid = _new(server, "BH1GHzMid")

    def edit(n, **body):
        _call(server, "PATCH", f"/api/networks/{nid}/nodes/1/{n}", body)
    edit(1, amp_code="71")
    _call(server, "POST", f"/api/networks/{nid}/branches/1/nodes", {"after": 0})
    edit(2, ftg=190, hc=2)
    _call(server, "POST", f"/api/networks/{nid}/branches/1/nodes", {"after": 0})
    edit(3, amp_code="11")
    s = _call(server, "GET", f"/api/networks/{nid}/screen")
    r = _row(s, 1, 3)
    assert _levels(r) == ["47.17", "36.59", "12.29", "11.30", "41.54", "45.55"]
    box = r["amp_info"]
    assert [box[k] for k in ("fwd_pad", "fwd_eq", "ret_pad", "ret_eq")] == ["Flag", "CS8", "Flag", "2"]
    edit(3, ftg=900)
    s = _call(server, "GET", f"/api/networks/{nid}/screen")
    r = _row(s, 1, 3)
    assert _levels(r) == ["24.31", "29.93", "18.41", "12.74", "25.16", "24.49"]
    box = r["amp_info"]
    assert [box[k] for k in ("fwd_pad", "fwd_eq", "ret_pad", "ret_eq")] == ["060", "13", "190", "6"]
    assert [box[k] for k in ("aerial_prev", "total_start", "cascade")] == [1090.0, 1090.0, 1]


def test_humb_keyed_on_its_own_spec(server):
    """The user's 3a, 4a and 5 (3 Oct), keyed on HUMB1GHzMid itself: 1.5 a
    0-ft line, 1.6 190 ft hc 2 /26/, 1.7 189 ft hc 5 <20> (FFT8-20 P, green),
    1.8 100 ft hc 5 /12/ (FFT2-12P, the 2-port: HUMB has 12 only so; 5 homes
    on 2 ports red), 1.9 amp 11.  Branch 2 behind 92: a 0 in a spec column is
    0 dB, -48.00 37.00 11.00 11.00 | 44.50 49.00."""
    nid = _new(server, "HUMB1GHzMid")

    def edit(n, **body):
        _call(server, "PATCH", f"/api/networks/{nid}/nodes/1/{n}", body)

    def line():
        _call(server, "POST", f"/api/networks/{nid}/branches/1/nodes", {"after": 0})
    edit(1, amp_code="71")
    for n in (2, 3, 4):
        line()
        _call(server, "PUT", f"/api/networks/{nid}/nodes/1/{n}/coupler", {"code": "92"})
    line()
    for n, ftg, hc, tap in ((6, 190, 2, "26"), (7, 189, 5, "20"), (8, 100, 5, "12")):
        line()
        edit(n, ftg=ftg, hc=hc)
        _call(server, "PUT", f"/api/networks/{nid}/nodes/1/{n}/tap", {"code": tap})
    line()
    edit(9, amp_code="11")
    s = _call(server, "GET", f"/api/networks/{nid}/screen")
    want = {5: ["51.00", "37.00", "11.00", "11.00", "44.50", "49.00"],
            6: ["46.17", "35.59", "12.29", "11.30", "41.04", "44.55"],
            7: ["39.57", "33.90", "13.88", "11.91", "36.70", "38.73"],
            8: ["34.43", "32.36", "15.36", "13.27", "33.68", "34.29"],
            9: ["31.73", "31.36", "16.46", "14.67", "32.08", "31.89"]}
    for n, lv in want.items():
        assert _levels(_row(s, 1, n)) == lv, n
    r7, r8 = _row(s, 1, 7), _row(s, 1, 8)
    assert (r7["taps"], r7["tap_severity"]) == (["<20>"], [""])
    assert [f"{v:.2f}" for v in r7["tap_levels"][0]] == ["19.57", "13.90", "33.88", "31.91"]
    # the cursor on it is yellow: 22.43 at 1002 is over its window
    assert (r8["taps"], r8["tap_severity"], r8["hc_severity"]) == (["/12/"], ["yellow"], "red")
    assert [f"{v:.2f}" for v in r8["tap_levels"][0]] == ["22.43", "20.36", "27.36", "25.27"]
    assert _levels(_row(s, 2, 1)) == ["-48.00", "37.00", "11.00", "11.00", "44.50", "49.00"]
