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
    # lv is the last: "." keeps it and goes no further
    _goto(page, 34, 3, "ftg")
    _type(page, "0...2.")
    page.wait_for_timeout(1200)
    assert page.evaluate("curCol().key") == "lv"
    assert page.evaluate("S.buffer") is None
    r = _row(page, 34, 3)
    assert (r["ftg"], r["cab"], r["lv"]) == (338, 406, 2)
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
    # 34.3's name, in any case: the window closes and "Amp Exists" says where
    page.fill("#adName", "al00410")
    page.click("#adOk")
    page.wait_for_timeout(400)
    assert page.inner_text(".msgbox .mbtitle") == "Amp Exists"
    assert page.inner_text(".msgbox .mbbody span:last-child") == "Amplifier al00410 already exists at 34.3."
    page.click("#mbOk")
    assert page.evaluate("document.getElementById('modal').hidden")
    assert _row(page, 34, 6)["amp_label"] == "AL00411"
    _type(page, ".+")
    page.wait_for_timeout(300)
    assert page.input_value("#adName") == "AL00411"
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
    assert [r["cab"] for r in rows[3:7]] == [410, 410, 410, 410]
    assert rows[5]["couplers"] == ["12<6>"]
    # the cursor stayed on the coupler's line
    assert page.evaluate("curRow().node") == 6
    # branch 6 still hangs from it, and nothing downstream moved
    assert page.evaluate("S.scr.branches.find(b => b.number === 6).parent_node") == 6
    assert _row(page, 6, 9)["block"] == block
    # a new line takes the cable of the line above it: 22.2 is 505, 22.3 405
    _goto(page, 22, 3, "ftg")
    page.keyboard.press("Insert")
    page.wait_for_timeout(800)
    _type(page, ".")
    page.keyboard.press("Insert")
    page.wait_for_timeout(800)
    rows = page.evaluate("S.scr.rows.filter(r => r.branch === 22 && !r.end)")
    assert [(r["ftg"], r["cab"]) for r in rows[1:5]] == [(25, 505), (0, 505), (360, 405), (0, 405)]
    assert not page.errors


def test_the_next_amplifier_is_offered_the_last_name_and_steps_it(page):
    """An amplifier not yet named is offered the last name given; + and -
    in the field step its number."""
    _open_al004(page)
    _goto(page, 34, 6, "amp")
    _type(page, ".+")
    page.wait_for_timeout(300)
    page.fill("#adName", "AL00500")
    page.keyboard.press("Enter")
    page.wait_for_timeout(1000)
    _goto(page, 34, 7, "amp")                     # place a 21 there
    _type(page, "021")
    page.keyboard.press("Enter")
    page.wait_for_timeout(1200)
    _goto(page, 34, 7, "amp")
    _type(page, ".+")
    page.wait_for_timeout(300)
    assert page.input_value("#adName") == "AL00500"
    page.keyboard.press("+")
    assert page.input_value("#adName") == "AL00501"
    page.keyboard.press("Enter")
    page.wait_for_timeout(1000)
    assert _row(page, 34, 7)["amp_label"] == "AL00501"
    _goto(page, 34, 5, "amp")
    _type(page, "021")
    page.keyboard.press("Enter")
    page.wait_for_timeout(1200)
    _goto(page, 34, 5, "amp")
    _type(page, ".+")
    page.wait_for_timeout(300)
    assert page.input_value("#adName") == "AL00501"
    page.keyboard.press("-")
    page.keyboard.press("-")
    assert page.input_value("#adName") == "AL00499"
    page.keyboard.press("+")
    page.keyboard.press("Enter")
    page.wait_for_timeout(400)
    assert page.inner_text(".msgbox .mbbody span:last-child") == "Amplifier AL00500 already exists at 34.6."
    assert not page.errors


def test_double_clicking_a_coupler_enters_its_branch_and_show_tips_hides_the_box(page):
    """The coupler's tip reads "<double-click or [.][LT] or [.][RT] to enter
    branch>".  On 4.14's 3-[11]<12> the program's box previews branch 11
    only.  View > Show Tips turns the box off and on."""
    _open_al004(page)
    _goto(page, 4, 14, "cplr0")
    box = page.inner_text("#info")
    assert "Feeds Branch: 11" in box and "Feeds Branch: 12" not in box
    # the preview draws 2/4/8-port taps (17) [8] {15}, as the program's box
    assert "(17)" in box and "{15}" in box and "[8]" in box
    assert box.rstrip().endswith("<double-click or [.][LT] or [.][RT] to enter branch>")
    i = page.evaluate("pageRows().findIndex(r => r.node === 14 && !r.end)")
    j = page.evaluate("columns().findIndex(c => c.key === 'cplr0')")
    page.dblclick(f'#grid td[data-r="{i}"][data-c="{j}"]')
    page.wait_for_timeout(400)
    assert page.evaluate("S.branch") == 11

    def show_tips():
        page.click('.mi[data-menu="view"]')
        page.wait_for_timeout(200)
        item = page.locator('.dropdown .di:has-text("Show Tips")')
        checked = item.locator(".chk").inner_text()
        item.click()
        page.wait_for_timeout(200)
        return checked

    assert show_tips() == "✓"
    assert page.evaluate("document.getElementById('info').hidden")
    assert show_tips() == ""
    assert not page.evaluate("document.getElementById('info').hidden")
    assert not page.errors


def _ntw_lines(data: bytes):
    sys.path.insert(0, str(ROOT / "tools"))
    from lodedata.obfuscation import deobfuscate
    from lodedata.network import read_network
    return read_network(data[:512] + deobfuscate(data[512:]))


def test_save_network_writes_the_edited_ntw_to_the_chosen_file(page):
    """File > Save Network asks where the first time, then writes there;
    the file carries the edit and reads back as a Lode Data network."""
    _open_al004(page)
    page.evaluate("""() => {
      window.__saved = [];
      window.showSaveFilePicker = async (opts) => ({
        name: opts.suggestedName,
        createWritable: async () => { const parts = [];
          return { write: async b => parts.push(new Uint8Array(await b.arrayBuffer())),
                   close: async () => { let t = '';
                     for (const b of parts[0]) t += String.fromCharCode(b);
                     window.__saved.push(btoa(t)); } }; } });
    }""")
    _goto(page, 4, 1, "ftg")
    _type(page, "0")
    _type(page, "500")
    page.keyboard.press("Enter")
    page.wait_for_timeout(800)
    page.click('.mi[data-menu="file"]')
    page.wait_for_timeout(200)
    page.click('.dropdown .di:has-text("Save Network"):not(:has-text("As"))')
    page.wait_for_timeout(2000)
    assert "saved AL004.ntw" in page.inner_text("#stMsg")
    saved = page.evaluate("window.__saved")
    assert len(saved) == 1
    import base64
    net = _ntw_lines(base64.b64decode(saved[0]))
    assert net.branches[4].nodes[0].ftg == 500 and len(net.branches) == 45
    assert not page.errors


def test_save_network_as_downloads_without_a_file_picker(page):
    """A browser with no file picker (Firefox) gets the .ntw as a download."""
    _open_al004(page)
    page.evaluate("delete window.showSaveFilePicker; window.showSaveFilePicker = undefined")
    page.click('.mi[data-menu="file"]')
    page.wait_for_timeout(200)
    with page.expect_download() as info:
        page.click('.dropdown .di:has-text("Save Network As")')
    download = info.value
    assert download.suggested_filename == "AL004.ntw"
    data = Path(download.path()).read_bytes()
    assert data == (SAMPLES / "AL004-WV750" / "AL004.ntw").read_bytes()
    assert not page.errors


def test_keying_a_cable_id_uses_that_cable(page):
    """406 is series 4, cable file index 6 (EX TX10 700 A): its loss applies."""
    _open_al004(page)
    before = _row(page, 4, 2)
    _goto(page, 4, 2, "cab")
    _type(page, "0")
    _type(page, "406")
    page.keyboard.press("Enter")
    page.wait_for_timeout(1000)
    after = _row(page, 4, 2)
    assert after["cab"] == 406 and after["cab_name"] == "EX TX10 700 A"
    assert after["levels"] != before["levels"]
    assert "not in the spec set" not in page.inner_text("#stMsg")
    assert not page.errors


def test_clearing_and_retyping_a_coupler(page):
    """0 on a coupler clears it and its branch; typing over one replaces it.
    Either used to fail: the coupler was taken off the line twice."""
    _open_al004(page)
    _goto(page, 20, 17, "cplr0")
    _type(page, "0")
    _type(page, "0")
    page.keyboard.press("Enter")
    page.wait_for_timeout(1000)
    assert _row(page, 20, 17)["couplers"] == []
    # the branches after 44 move up: 45 (from 5.9) is now 44
    branches = page.evaluate("S.scr.branches.map(b => [b.number, b.parent_branch, b.parent_node])")
    assert [b[0] for b in branches] == list(range(1, 45)) and branches[-1] == [44, 5, 9]
    assert _row(page, 5, 9)["couplers"] == ["1<44>"]
    _goto(page, 4, 26, "cplr0")                   # 8[22] (and 23 under it): a DC-12 over it
    _type(page, "0")
    _type(page, "12")
    page.keyboard.press("Enter")
    page.wait_for_timeout(1000)
    cell = _row(page, 4, 26)["couplers"]
    assert len(cell) == 1 and cell[0].startswith("12"), cell
    numbers = page.evaluate("S.scr.branches.map(b => b.number)")
    assert numbers == list(range(1, 44))          # 44 - 22 - 23 + the new one
    assert not page.errors


def _open_al004_with_file_access(page):
    """Open AL004 the way Chrome and Edge do: through the browser's file
    access, which hands back the file itself to save into."""
    import base64
    data = base64.b64encode((SAMPLES / "AL004-WV750" / "AL004.ntw").read_bytes()).decode()
    page.evaluate("""(data) => {
      const bytes = Uint8Array.from(atob(data), c => c.charCodeAt(0));
      window.__written = []; window.__asked = 0;
      const handle = (name, contents) => ({
        name, getFile: async () => new File([contents], name),
        createWritable: async () => { const parts = [];
          return { write: async b => parts.push(new Uint8Array(await b.arrayBuffer())),
                   close: async () => { let t = '';
                     for (const b of parts[0]) t += String.fromCharCode(b);
                     window.__written.push([name, btoa(t)]); } }; } });
      window.showOpenFilePicker = async () => [handle('AL004.ntw', bytes)];
      window.showSaveFilePicker = async (o) => { window.__asked += 1; return handle('AL004_B.ntw', new Uint8Array()); };
    }""", data)
    page.evaluate("importNtw()")
    page.wait_for_timeout(200)
    page.click("#ntwFile")
    page.wait_for_timeout(300)
    pair = SAMPLES / "AL004-WV750"
    page.set_input_files("#ntwSpecs", [str(f) for f in sorted(pair.glob("WV750-2026.*"))])
    page.click("#ntwGo")
    page.wait_for_timeout(2500)


def _file_menu(page, item):
    page.click('.mi[data-menu="file"]')
    page.wait_for_timeout(200)
    page.click(f'.dropdown .di:has(span:text-is("{item}"))')
    page.wait_for_timeout(2000)


def test_save_network_writes_back_into_the_opened_file(page):
    """Open AL004, change it, File > Save Network: the changes go into
    AL004.ntw itself, with no file dialog."""
    if not (SAMPLES / "AL004-WV750" / "AL004.ntw").exists():
        pytest.skip("AL004 not in samples")
    import base64
    _open_al004_with_file_access(page)
    _goto(page, 4, 1, "ftg")
    _type(page, "0")
    _type(page, "500")
    page.keyboard.press("Enter")
    page.wait_for_timeout(800)
    _file_menu(page, "Save Network")
    assert "saved AL004.ntw" in page.inner_text("#stMsg")
    assert page.evaluate("window.__asked") == 0
    written = page.evaluate("window.__written")
    assert [w[0] for w in written] == ["AL004.ntw"]
    net = _ntw_lines(base64.b64decode(written[0][1]))
    assert net.branches[4].nodes[0].ftg == 500 and net.name == "AL004"
    assert not page.errors


def test_save_network_as_takes_the_new_name(page):
    """Save Network As... asks for a file; the file keeps that name, so the
    program does not warn "Filename AL004 has changed to ..." on opening it,
    and the network carries the name from then on."""
    if not (SAMPLES / "AL004-WV750" / "AL004.ntw").exists():
        pytest.skip("AL004 not in samples")
    import base64
    sys.path.insert(0, str(ROOT / "tools"))
    from lodedata.obfuscation import deobfuscate
    from lodedata.writer import _stored_name
    _open_al004_with_file_access(page)
    _file_menu(page, "Save Network As...")
    assert page.evaluate("window.__asked") == 1
    name, data = page.evaluate("window.__written")[0]
    data = base64.b64decode(data)
    assert name == "AL004_B.ntw" and _stored_name(data[:512] + deobfuscate(data[512:])) == "AL004_B"
    assert "AL004_B" in page.inner_text("#title")
    _file_menu(page, "Save Network")                # then saves go to AL004_B.ntw
    assert page.evaluate("window.__asked") == 1
    assert [w[0] for w in page.evaluate("window.__written")] == ["AL004_B.ntw", "AL004_B.ntw"]
    assert not page.errors


def test_other_spec_files_bring_up_the_spec_file_mismatch_box(page, tmp_path):
    """Opened with a spec set of another name, the network still opens and
    the box says which set it was saved with (the user: a node upgrade uses
    another set on purpose)."""
    import shutil
    pair = SAMPLES / "AL004-WV750"
    if not (pair / "AL004.ntw").exists():
        pytest.skip("AL004 not in samples")
    specs = []
    for f in sorted(pair.glob("WV750-2026.*")):
        specs.append(tmp_path / f"UPGRADE{f.suffix}")
        shutil.copy(f, specs[-1])
    page.evaluate("importNtw()")
    page.wait_for_timeout(200)
    page.set_input_files("#ntwFile", str(pair / "AL004.ntw"))
    page.set_input_files("#ntwSpecs", [str(f) for f in specs])
    page.click("#ntwGo")
    page.wait_for_timeout(2500)
    assert page.inner_text(".msgbox .mbtitle") == "Spec File Mismatch"
    rows = page.eval_on_selector_all(".msgbox table.mismatch tr",
                                     "trs => trs.map(t => t.innerText.replace(/\\s+/g, ' ').trim())")
    assert rows[0] == "Parameters: Project spec file loaded does not match spec file 'WV750-2026' saved with"
    assert rows[5:] == ["Prices: Loaded.", "Performance: Loaded.", "Map Grid: Loaded."]
    page.click("#mbOk")
    assert page.evaluate("S.scr.rows.length") > 0 and "AL004" in page.inner_text("#title")
    assert not page.errors


def test_a_network_keyed_from_scratch_saves_as_ntw(server):
    """File > New, a spec set, a few lines; Save Network writes a .ntw as the
    program writes a new network (the header's licence and user fields from
    the last .ntw opened), and it reads back."""
    import requests
    pair = SAMPLES / "AL004-WV750"
    if not (pair / "AL004.ntw").exists():
        pytest.skip("AL004 not in samples")
    specs = [("specs", (f.name, f.read_bytes())) for f in sorted(pair.glob("WV750-2026.*"))]
    r = requests.post(f"{server}/api/import/ntw",
                      files=[("file", ("AL004.ntw", (pair / "AL004.ntw").read_bytes()))] + specs)
    assert r.json()["imported"]
    nid = requests.post(f"{server}/api/networks", json={"name": "Untitled"}).json()["id"]
    requests.post(f"{server}/api/networks/{nid}/library/spec",
                  files=[("files", s[1]) for s in specs]).raise_for_status()
    base = f"{server}/api/networks/{nid}"
    requests.patch(f"{base}/nodes/1/1", json={"amp_code": "70"}).raise_for_status()
    requests.patch(f"{base}/nodes/1/1", json={"amp_label": "AL004", "cab": 2}).raise_for_status()
    requests.post(f"{base}/branches/1/nodes", json={"after": 1, "cable_from_previous": True}).raise_for_status()
    requests.put(f"{base}/nodes/1/2/coupler", json={"slot": 0, "code": "100"}).raise_for_status()
    requests.patch(f"{base}/nodes/2/1", json={"ftg": 120, "hc": 2}).raise_for_status()
    requests.put(f"{base}/nodes/2/1/tap", json={"slot": 0, "code": "2.23"}).raise_for_status()
    r = requests.post(f"{base}/ntw", params={"filename": "SCRATCH.ntw"})
    assert r.status_code == 200, r.text
    net = _ntw_lines(r.content)
    assert [len(b.nodes) for b in net.branches.values()] == [2, 1]
    first = net.branches[2].nodes[0]
    assert (first.ftg, first.hc, first.cable) == (120, 2, 2)      # the coupler line's cable
    assert net.branches[1].nodes[0].label == "AL004"
    assert requests.get(base).json()["name"] == "SCRATCH"
    assert r.content[:512] == (pair / "AL004.ntw").read_bytes()[:512]
