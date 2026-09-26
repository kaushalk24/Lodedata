"""Keying at the grid, driven through a real browser.

The only thing that catches timing bugs in the entry path: typing "300 . 4 . 2"
faster than the round trip used to land the wrong values in the wrong columns.

Skipped unless Playwright and a Chromium build are both present.
"""
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = Path(os.environ.get("LODEDATA_SAMPLES", ROOT / "samples"))

playwright = pytest.importorskip("playwright.sync_api",
                                 reason="playwright is not installed")
CHROMIUM = os.environ.get("CHROMIUM_PATH", "/opt/pw-browsers/chromium")

pytestmark = pytest.mark.skipif(
    not Path(CHROMIUM).exists() or not SAMPLES.is_dir(),
    reason="needs a Chromium build and a sample spec set")


def _spec_files():
    # The keying tests type KERMIT750 tap codes (4.23, 8.21); prefer that set.
    cbls = sorted(SAMPLES.rglob("*.cbl"), key=lambda p: "KERMIT" not in p.name)
    cbl = next(iter(cbls), None)
    if not cbl:
        return []
    return [str(cbl.with_suffix("." + e)) for e in ("par", "atv", "tap", "cpr", "cbl")
            if cbl.with_suffix("." + e).exists()]


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def server(tmp_path_factory):
    port = _free_port()
    env = dict(os.environ, LODEDATA_DB=str(tmp_path_factory.mktemp("db") / "t.db"))
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "api:app", "--app-dir", "app",
         "--port", str(port), "--log-level", "warning"],
        cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    url = f"http://127.0.0.1:{port}"
    for _ in range(80):
        time.sleep(0.25)
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                break
        except OSError:
            continue
    else:
        proc.kill()
        pytest.skip("the server did not start")
    yield url
    proc.terminate()
    proc.wait(timeout=10)


@pytest.fixture
def page(server):
    from playwright.sync_api import sync_playwright
    files = _spec_files()
    if len(files) < 5:
        pytest.skip("a full five-file spec set is needed")
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=CHROMIUM)
        pg = browser.new_page(viewport={"width": 1240, "height": 700})
        errors = []
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.goto(server, wait_until="networkidle")
        pg.wait_for_timeout(600)
        # attach the spec set as Lode Data does it:
        # File -> Project Settings... -> Set All Files
        pg.click('.mi[data-menu="file"]')
        pg.wait_for_timeout(250)
        pg.click('.dropdown .di:has-text("Project Settings")')
        pg.wait_for_timeout(300)
        pg.set_input_files("#psFiles", files)
        pg.wait_for_timeout(1800)
        pg.errors = errors
        yield pg
        browser.close()


def _col(page, key):
    return page.evaluate(
        "k => Array.from(document.querySelectorAll('#grid thead th'))"
        "  .findIndex(th => th.textContent.trim() === k) - 1", key)


def _type(page, text):
    for ch in text:
        page.keyboard.press(ch)


def test_typing_footage_house_count_and_cable_lands_in_the_right_columns(page):
    """The bug this file exists for: fields must not race each other."""
    page.click(f'#grid tbody tr:nth-child(1) td[data-c="{_col(page, "ftg")}"]')
    page.wait_for_timeout(150)
    _type(page, "300.4.2")
    page.keyboard.press("Enter")
    page.wait_for_timeout(900)

    row = page.evaluate("""() => {
      const t = document.querySelectorAll('#grid tbody tr')[0]
        .querySelectorAll('td[data-c]');
      const head = Array.from(document.querySelectorAll('#grid thead th'))
        .slice(1).map(h => h.textContent.trim());
      const out = {};
      head.forEach((h, i) => { out[h] = t[i] ? t[i].textContent.trim() : ''; });
      return out;
    }""")
    assert row["ftg"] == "300"
    assert row["hc"] == "4"
    assert row["cab"] == "2"
    assert not page.errors


def test_typing_a_tap_code_places_it_in_the_right_bracket(page):
    tap1 = _col(page, "tap1")
    page.click(f'#grid tbody tr:nth-child(1) td[data-c="{tap1}"]')
    page.wait_for_timeout(150)
    _type(page, "4.23")
    page.keyboard.press("Enter")
    page.wait_for_timeout(900)
    cell = page.inner_text(f'#grid tbody tr:nth-child(1) td[data-c="{tap1}"]')
    assert cell.strip() == "[23]"          # four-port brackets

    page.click(f'#grid tbody tr:nth-child(1) td[data-c="{tap1 + 1}"]')
    _type(page, "8.21")
    page.keyboard.press("Enter")
    page.wait_for_timeout(900)
    cell = page.inner_text(f'#grid tbody tr:nth-child(1) td[data-c="{tap1 + 1}"]')
    assert cell.strip() == "<21>"          # eight-port brackets
    assert not page.errors


def test_an_unknown_tap_is_refused_with_what_the_spec_has(page):
    tap1 = _col(page, "tap1")
    page.click(f'#grid tbody tr:nth-child(1) td[data-c="{tap1 + 2}"]')
    _type(page, "4.99")
    page.keyboard.press("Enter")
    page.wait_for_timeout(900)
    assert "no 4-port 99 tap" in page.inner_text("#stMsg")
    assert page.inner_text(f'#grid tbody tr:nth-child(1) td[data-c="{tap1 + 2}"]').strip() == ""


def test_typing_a_negative_coupler_swaps_the_legs_and_makes_a_branch(page):
    cplr = _col(page, "cplr[branch]")
    page.click(f'#grid tbody tr:nth-child(1) td[data-c="{cplr}"]')
    _type(page, "-8")
    page.keyboard.press("Enter")
    page.wait_for_timeout(1000)
    cell = page.inner_text(f'#grid tbody tr:nth-child(1) td[data-c="{cplr}"]').strip()
    assert cell.startswith("8-<"), cell      # a new branch has no footage yet
    assert "Branch 1 of 2" in page.inner_text("#stBranch")
    assert "through leg to this branch" in page.inner_text("#stMsg")
    assert not page.errors


def test_the_menu_bar_matches_the_program(page):
    names = page.eval_on_selector_all(".menubar .mi", "els => els.map(e => e.textContent)")
    assert names == ["File", "Edit", "Mode", "Tools", "Global Change", "Spec Edit",
                     "Test", "Misc", "Reports", "View", "Help"]
    page.click('.mi[data-menu="file"]')
    page.wait_for_timeout(200)
    items = page.eval_on_selector_all(".dropdown .di span:first-child",
                                      "els => els.map(e => e.textContent)")
    assert items == ["New", "Open", "Unload", "Save Specs", "Save Network",
                     "Save Network As...", "Project Settings...", "Print", "Exit"]
    assert not page.errors

