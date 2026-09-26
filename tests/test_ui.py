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
    """The bug this file exists for: fields must not race each other.  Strand
    data is keyed in Entry mode, "1 0 7 . 2 . 0 ENTER" as the manual has it."""
    page.select_option("#selMode", "entry")
    page.wait_for_timeout(200)
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
    page.select_option("#selMode", "design")


def test_typing_a_tap_code_places_it_in_the_right_bracket(page):
    tap1 = _col(page, "tap1")
    page.click(f'#grid tbody tr:nth-child(1) td[data-c="{tap1}"]')
    page.wait_for_timeout(150)
    _type(page, "0")                       # Alter
    assert "Enter desired tap {# of ports}.{ID #}:" in page.inner_text("#stMsg")
    _type(page, "4.23")
    page.keyboard.press("Enter")
    page.wait_for_timeout(900)
    cell = page.inner_text(f'#grid tbody tr:nth-child(1) td[data-c="{tap1}"]')
    assert cell.strip() == "[23]"          # four-port brackets

    page.click(f'#grid tbody tr:nth-child(1) td[data-c="{tap1 + 1}"]')
    _type(page, "08.21")
    page.keyboard.press("Enter")
    page.wait_for_timeout(900)
    cell = page.inner_text(f'#grid tbody tr:nth-child(1) td[data-c="{tap1 + 1}"]')
    assert cell.strip() == "<21>"          # eight-port brackets
    assert not page.errors


def test_an_unknown_tap_is_refused_with_what_the_spec_has(page):
    tap1 = _col(page, "tap1")
    page.click(f'#grid tbody tr:nth-child(1) td[data-c="{tap1 + 2}"]')
    _type(page, "04.99")
    page.keyboard.press("Enter")
    page.wait_for_timeout(900)
    assert "no 4-port 99 tap" in page.inner_text("#stMsg")
    assert page.inner_text(f'#grid tbody tr:nth-child(1) td[data-c="{tap1 + 2}"]').strip() == ""


def test_typing_a_negative_coupler_swaps_the_legs_and_makes_a_branch(page):
    cplr = _col(page, "cplr[branch]")
    page.click(f'#grid tbody tr:nth-child(1) td[data-c="{cplr}"]')
    _type(page, "0-8")
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


def test_design_keys_are_the_screen_menu(page):
    # 5 Test opens the Test Results window, Esc closes it; / toggles the
    # expanded display; 0 then Home on a tap opens Select Tap
    tap1 = _col(page, "tap1")
    page.click(f'#grid tbody tr:nth-child(1) td[data-c="{tap1}"]')
    _type(page, "5")
    page.wait_for_timeout(300)
    assert "Design Assistant Test Results -" in page.inner_text(".testres .trtitle")
    page.keyboard.press("Escape")
    assert page.evaluate("document.getElementById('modal').hidden")
    _type(page, "/")
    page.wait_for_timeout(200)
    assert page.eval_on_selector_all("#grid tbody tr.xline", "els => els.length") >= 6
    _type(page, "/")
    page.wait_for_timeout(200)
    assert page.eval_on_selector_all("#grid tbody tr.xline", "els => els.length") == 0
    page.click(f'#grid tbody tr:nth-child(1) td[data-c="{tap1}"]')
    _type(page, "0")
    page.keyboard.press("Home")
    page.wait_for_timeout(600)
    assert page.inner_text(".seltap .sttitle") == "Select Tap"
    tabs = page.eval_on_selector_all(".sttab", "els => els.map(e => e.textContent)")
    assert tabs == ["2 Port", "4 Port", "6 Port", "8 Port"]
    assert page.eval_on_selector_all(".stitem", "els => els.length") > 0
    page.keyboard.press("Escape")
    assert not page.errors



def test_expanded_display_draws_the_amplifier_and_its_block(page):
    """AL004 22.3 with "/" on, as the program draws it."""
    pair = SAMPLES / "AL004-WV750"
    if not (pair / "AL004.ntw").exists():
        pytest.skip("AL004 not in samples")
    page.evaluate("importNtw()")
    page.wait_for_timeout(200)
    page.set_input_files("#ntwFile", str(pair / "AL004.ntw"))
    page.set_input_files("#ntwSpecs", [str(f) for f in sorted(pair.glob("WV750-2026.*"))])
    page.click("#ntwGo")
    page.wait_for_timeout(2500)
    page.evaluate("gotoBranch(22, 3)")
    page.wait_for_timeout(300)
    _type(page, "/")
    page.wait_for_timeout(300)
    text = page.eval_on_selector_all("#grid tbody td.xtext", "els => els.map(e => e.textContent)")
    assert "[           AL00429]  <      SPB-2   \u00a6  SEQ-750-5   >" in text
    assert "<                 A>  <      SPB-1   \u00a6   MEQ-42-2   >" in text
    assert "      [   74  2994  385  459  3379  6.85  8.45 51.67]" in text
    assert "       2-1-0 0-1-0   16 385" in text
    marks = page.eval_on_selector_all("#grid tbody td.xhousing", "els => els.map(e => e.textContent)")
    assert marks == ["(3)", "(1)"]
    page.evaluate("gotoBranch(4, 4)")
    page.wait_for_timeout(300)
    text = page.eval_on_selector_all("#grid tbody td.xtext", "els => els.map(e => e.textContent)")
    assert "       0-0-0 8-7-0   127886" in text
    assert not page.errors


def test_double_clicking_a_tap_in_select_tap_replaces_the_slots_tap(page):
    """A double-click in Select Tap places that tap in the cursor's slot,
    replacing the one there (the user: "gets placed or replaced when we
    double click on the tap").  AL004 6.8 holds {43}; take {44}."""
    pair = SAMPLES / "AL004-WV750"
    if not (pair / "AL004.ntw").exists():
        pytest.skip("AL004 not in samples")
    page.evaluate("importNtw()")
    page.wait_for_timeout(200)
    page.set_input_files("#ntwFile", str(pair / "AL004.ntw"))
    page.set_input_files("#ntwSpecs", [str(f) for f in sorted(pair.glob("WV750-2026.*"))])
    page.click("#ntwGo")
    page.wait_for_timeout(2500)
    page.evaluate("gotoBranch(6, 8); S.col = columns().findIndex(c => c.key === 'tap0'); renderGrid();")
    page.wait_for_timeout(300)
    _type(page, "0")
    page.keyboard.press("Home")
    page.wait_for_timeout(600)
    # the tab follows the tap in the slot: {43} is a 6-port
    assert page.inner_text(".sttab.on") == "6 Port"
    assert page.inner_text(".stitem.sel") == "{43}"
    page.dblclick('.stitem:text-is("{44}")')
    page.wait_for_timeout(800)
    assert page.evaluate("document.getElementById('modal').hidden")
    row = page.evaluate("S.scr.rows.find(r => r.branch === 6 && r.node === 8)")
    assert row["taps"] == ["<44>"]
    assert not page.errors


def _open_al004(page):
    pair = SAMPLES / "AL004-WV750"
    if not (pair / "AL004.ntw").exists():
        pytest.skip("AL004 not in samples")
    page.evaluate("importNtw()")
    page.wait_for_timeout(200)
    page.set_input_files("#ntwFile", str(pair / "AL004.ntw"))
    page.set_input_files("#ntwSpecs", [str(f) for f in sorted(pair.glob("WV750-2026.*"))])
    page.click("#ntwGo")
    page.wait_for_timeout(2500)


def _goto(page, branch, node, col):
    page.evaluate(f"gotoBranch({branch}, {node}); S.col = columns().findIndex(c => c.key === '{col}'); renderGrid();")
    page.wait_for_timeout(300)


def _row(page, branch, node):
    return page.evaluate(f"S.scr.rows.find(r => r.branch === {branch} && r.node === {node} && !r.end)")


def test_design_alter_keys_ftg_hc_cab_lv_as_one(page):
    """0 on ftg starts keying; "." moves on to hc, cab, lv still keying."""
    _open_al004(page)
    _goto(page, 34, 2, "ftg")
    _type(page, "0150.2.401")
    page.keyboard.press("Enter")
    page.wait_for_timeout(1200)
    r = _row(page, 34, 2)
    assert (r["ftg"], r["hc"], r["cab"]) == (150, 2, 401)
    # a field left empty keeps its value
    _goto(page, 34, 5, "ftg")
    _type(page, "0.3")
    page.keyboard.press("Enter")
    page.wait_for_timeout(1200)
    r = _row(page, 34, 5)
    assert (r["ftg"], r["hc"]) == (273, 3)
    assert not page.errors


def test_amplifier_definition_names_the_amplifier(page):
    """". +" on an amplifier's amp column: the name shows in tap1, a name
    another amplifier has is refused with a warning, and a tap placed in
    tap1 hides the name without taking it from the amplifier."""
    _open_al004(page)
    _goto(page, 34, 6, "amp")
    _type(page, ".+")
    page.wait_for_timeout(300)
    assert page.inner_text(".ampdef .adtitle") == "Amplifier Definition"
    assert "B" in page.inner_text(".ampdef .adrow")
    assert page.input_value("#adName") == "AL00411"
    assert page.inner_text(".ampdef .adstatus") == "Enter Amplifier name."
    warnings = []
    page.once("dialog", lambda d: (warnings.append(d.message), d.accept()))
    page.fill("#adName", "AL00410")               # 34.3's
    page.click("#adOk")
    page.wait_for_timeout(500)
    assert warnings and "AL00410" in warnings[0]
    assert not page.evaluate("document.getElementById('modal').hidden")
    assert _row(page, 34, 6)["amp_label"] == "AL00411"
    page.fill("#adName", "A-1/b#2")
    page.keyboard.press("Enter")
    page.wait_for_timeout(1000)
    assert page.evaluate("document.getElementById('modal').hidden")
    assert _row(page, 34, 6)["amp_label"] == "A-1/b#2"
    tap1 = _col(page, "tap1")
    cell = lambda: page.evaluate(
        f"Array.from(document.querySelectorAll('#grid tbody tr')).find(tr => tr.children[1]"
        f" && tr.children[1].textContent.trim() === '6').children[{tap1} + 1].textContent.trim()")
    assert cell() == "A-1/b#2"
    # a 2-port 4 tap keyed into tap1: "0 2 . 4"
    _goto(page, 34, 6, "tap0")
    _type(page, "02.4")
    page.keyboard.press("Enter")
    page.wait_for_timeout(1200)
    r = _row(page, 34, 6)
    assert r["taps"] == ["/ 4/"]
    assert cell() == "/ 4/"
    assert r["amp_label"] == "A-1/b#2" and r["amp_info"]["name"] == "A-1/b#2"
    assert not page.errors


def test_insert_adds_zero_footage_lines_above_and_below(page):
    """Insert adds a line above the cursor's, ". Insert" one below; each
    press adds another.  4.4 carries branch 6's coupler."""
    _open_al004(page)
    before = page.evaluate("S.scr.rows.filter(r => r.branch === 4 && !r.end).length")
    block = _row(page, 6, 9)["block"]
    _goto(page, 4, 4, "ftg")
    page.keyboard.press("Insert")
    page.wait_for_timeout(800)
    page.keyboard.press("Insert")
    page.wait_for_timeout(800)
    _type(page, ".")
    page.keyboard.press("Insert")
    page.wait_for_timeout(800)
    rows = page.evaluate("S.scr.rows.filter(r => r.branch === 4 && !r.end)")
    assert len(rows) == before + 3
    assert [r["ftg"] for r in rows[:8]] == [476, 155, 134, 0, 0, 121, 0, 156]
    assert rows[5]["couplers"] == ["12<6>"]
    # the cursor stayed on the coupler's line
    assert page.evaluate("curRow().node") == 6
    # branch 6 still hangs from it, and nothing downstream moved
    assert page.evaluate("S.scr.branches.find(b => b.number === 6).parent_node") == 6
    assert _row(page, 6, 9)["block"] == block
    assert not page.errors
