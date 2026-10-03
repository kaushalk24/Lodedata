"""HTTP API and static hosting.

Run with:  ./run.sh   (python -m uvicorn api:app --app-dir app)
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import sqlite3
import struct
import tempfile
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile, File, Response
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from hfc.model import Library, DesignParameters, new_id
from hfc.plant import (Design, Branch, Node, TapPlacement, CouplerPlacement,
                       BRANCH_NORMAL)
from hfc.screen import build, tap_candidates, active_inputs, repick
from hfc.entry import resolve_tap, resolve_coupler, resolve_active, config_slot, EntryError
from hfc.starter import starter_library
from hfc.reports import level_report, bill_of_materials, powering_report, to_csv
from hfc.importer import (library_from_spec_set, inspect_ntw, relink_library,
                          design_from_ntw)
from hfc.exporter import export_ntw, ExportError
from hfc.specwindow import window, WINDOWS

WEB = Path(__file__).parent / "web"
DB_PATH = Path(os.environ.get("LODEDATA_DB",
                              Path(__file__).parent.parent / "data" / "designs.db"))

app = FastAPI(title="Design Assistant")

# Several people can use one server at once, each on their own network.  A
# change reads the whole network, changes it and writes it back, so two
# changes to the same network arriving together would lose one: they are
# taken one after the other -- within a server process by an asyncio lock,
# across processes (start-server.sh's WORKERS) by a lock file.  Different
# networks are not held up.
try:
    import fcntl
except ImportError:              # Windows: one process, the asyncio lock is enough
    fcntl = None
_NETWORK_PATH = re.compile(r"^/api/networks/([A-Za-z0-9_-]+)")
_network_locks: dict = {}


def _hold_lock_file(nid: str):
    folder = DB_PATH.parent / "locks"
    folder.mkdir(parents=True, exist_ok=True)
    f = open(folder / f"{nid}.lock", "a")
    fcntl.flock(f, fcntl.LOCK_EX)          # released when the file is closed
    return f


@app.middleware("http")
async def one_change_at_a_time(request, call_next):
    found = _NETWORK_PATH.match(request.url.path)
    if not found or request.method == "GET":
        return await call_next(request)
    nid = found.group(1)
    async with _network_locks.setdefault(nid, asyncio.Lock()):
        held = await asyncio.to_thread(_hold_lock_file, nid) if fcntl else None
        try:
            return await call_next(request)
        finally:
            if held:
                held.close()


# --------------------------------------------------------------------------
def db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    # several server processes share the file: wait for another's write
    # rather than fail, and let reads go on while one writes
    con = sqlite3.connect(DB_PATH, timeout=30)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("CREATE TABLE IF NOT EXISTS designs ("
                "id TEXT PRIMARY KEY, name TEXT, updated TEXT, doc TEXT)")
    # the .ntw a network was opened from, or last saved as: a save is built
    # over it, so everything the program wrote that this app does not model
    # is kept
    con.execute("CREATE TABLE IF NOT EXISTS ntw_files (id TEXT PRIMARY KEY, data BLOB)")
    return con


def layout_key(design_id: str) -> str:
    """Where a network keyed in from scratch keeps the header it is written
    with: the licence and user fields of the last .ntw opened in the browser
    that started it -- that person's, on a server several people use."""
    return f"layout:{design_id}"


def ntw_file(design_id: str) -> bytes | None:
    con = db()
    row = con.execute("SELECT data FROM ntw_files WHERE id=?", (design_id,)).fetchone()
    con.close()
    return bytes(row[0]) if row else None


def keep_ntw_file(design_id: str, data: bytes) -> None:
    con = db()
    con.execute("INSERT INTO ntw_files(id,data) VALUES(?,?) "
                "ON CONFLICT(id) DO UPDATE SET data=excluded.data", (design_id, data))
    con.commit()
    con.close()


def spec_key(design_id: str, ext: str) -> str:
    """Where a network keeps one of its spec files, as attached: the Spec
    Edit windows show the file itself, every record of it."""
    return f"spec:{design_id}{ext}"


def keep_spec_files(design_id: str, files: dict) -> None:
    """``files``: extension -> bytes, the set just attached (it replaces the
    one kept before)."""
    con = db()
    con.execute("DELETE FROM ntw_files WHERE id LIKE ?", (f"spec:{design_id}.%",))
    for ext, data in files.items():
        con.execute("INSERT INTO ntw_files(id,data) VALUES(?,?)", (spec_key(design_id, ext), data))
    con.commit()
    con.close()


def load(design_id: str) -> Design:
    con = db()
    row = con.execute("SELECT doc FROM designs WHERE id=?", (design_id,)).fetchone()
    con.close()
    if not row:
        raise HTTPException(404, "network not found")
    return Design.from_dict(json.loads(row[0]))


def load_for_edit(design_id: str) -> Design:
    """A network about to be edited: its actives' input levels are noted,
    so that saving it picks the pads and EQs again where they changed."""
    d = load(design_id)
    d._inputs_before = active_inputs(d)
    return d


def save(d: Design, keyed=()) -> Design:
    before = getattr(d, "_inputs_before", None)
    if before is not None:
        repick(d, before, keyed)
    con = db()
    con.execute("INSERT INTO designs(id,name,updated,doc) "
                "VALUES(?,?,datetime('now'),?) "
                "ON CONFLICT(id) DO UPDATE SET name=excluded.name, "
                "updated=excluded.updated, doc=excluded.doc",
                (d.id, d.name, json.dumps(d.to_dict())))
    con.commit()
    con.close()
    return d


# --------------------------------------------------------------------------
class NewNetwork(BaseModel):
    name: str = "lode-1"
    sample_specs: bool = False
    header_from: str | None = None     # the last network this browser opened from a .ntw


@app.get("/api/networks")
def list_networks():
    con = db()
    rows = con.execute("SELECT id,name,updated FROM designs "
                       "ORDER BY updated DESC").fetchall()
    con.close()
    return [{"id": r[0], "name": r[1], "updated": r[2]} for r in rows]


@app.post("/api/networks")
def new_network(body: NewNetwork):
    """A new network file starts empty and with no spec set attached."""
    d = Design(id=new_id("ntw"), name=body.name)
    d.ensure_feeder()
    if body.sample_specs:
        d.library = starter_library()
    save(d)
    opened = ntw_file(body.header_from) if body.header_from else None
    if opened:
        keep_ntw_file(layout_key(d.id), opened[:512])
    return d.to_dict()


@app.get("/api/networks/{nid}")
def get_network(nid: str):
    return load(nid).to_dict()


@app.delete("/api/networks/{nid}")
def delete_network(nid: str):
    con = db()
    con.execute("DELETE FROM designs WHERE id=?", (nid,))
    con.execute("DELETE FROM ntw_files WHERE id IN (?, ?)", (nid, layout_key(nid)))
    con.execute("DELETE FROM ntw_files WHERE id LIKE ?", (f"spec:{nid}.%",))
    con.commit()
    con.close()
    return {"deleted": nid}


class NetworkPatch(BaseModel):
    name: str | None = None
    parameters: dict | None = None
    source_dbmv: float | None = None
    source_tilt_db: float | None = None
    supply_volts: float | None = None


@app.patch("/api/networks/{nid}")
def patch_network(nid: str, body: NetworkPatch):
    d = load(nid)
    if body.name is not None:
        d.name = body.name
    if body.parameters is not None:
        d.parameters = DesignParameters(**(d.parameters.__dict__ | body.parameters))
    for f in ("source_dbmv", "source_tilt_db", "supply_volts"):
        v = getattr(body, f)
        if v is not None:
            setattr(d, f, v)
    save(d)
    return d.to_dict()


# --------------------------------------------------------------------------
# the screen
# --------------------------------------------------------------------------
@app.get("/api/networks/{nid}/screen")
def screen(nid: str):
    return build(load(nid)).as_dict()


class NodeEdit(BaseModel):
    ftg: float | None = None
    through_leg: int | None = None
    amp_code: str | None = None      # an Active ID typed at the amp column
    hc: int | None = None
    cab: int | None = None
    cab_part: str | None = None
    lv: int | None = None
    tsg: int | None = None
    amp: str | None = None
    amp_part: str | None = None
    amp_label: str | None = None
    map: str | None = None
    loc: str | None = None
    address: str | None = None
    note: str | None = None
    supply_volts: float | None = None
    power_stop: bool | None = None
    clear_amp: bool = False


def _node(d: Design, branch: int, node: int) -> Node:
    b = d.branch(branch)
    if not b:
        raise HTTPException(404, f"branch {branch} not found")
    for n in b.nodes:
        if n.seq == node:
            return n
    raise HTTPException(404, f"node {branch}.{node} not found")


@app.patch("/api/networks/{nid}/nodes/{branch}/{node}")
def edit_node(nid: str, branch: int, node: int, body: NodeEdit):
    d = load_for_edit(nid)
    n = _node(d, branch, node)
    if body.clear_amp:
        n.amp, n.amp_part, n.amp_label = "", None, ""
        n.pads, n.kept_active, n.amp_config = [], 0, 0
    if body.amp_code is not None:
        n.kept_active = 0
        # the program picks its pads and EQs as it is keyed (saving below);
        # a fibre-fed one holds 0 in all four
        n.pads = [0, 0, 0, 0]
        try:
            part = resolve_active(d.library, body.amp_code)
        except EntryError as e:
            raise HTTPException(400, str(e))
        if part is None:
            n.amp, n.amp_part, n.amp_config = "", None, 0
        else:
            n.amp_config = config_slot(part, body.amp_code)
            n.amp = part.config_ids[n.amp_config] if n.amp_config else (part.active_id or "")
            n.amp_part = part.id
    for f, v in body.model_dump(exclude_none=True).items():
        if f in ("clear_amp", "amp_code"):
            continue
        setattr(n, f, v)
    if body.cab is not None and body.cab_part is None:
        # the cable ID is series * 100 + the cable file index; the index
        # names the cable, as when a .ntw is read
        n.cab_part = next((c.id for c in d.library.cables.values()
                           if c.cable_index == body.cab % 100), None)
    save(d, keyed={id(n)} if body.amp_code is not None and n.amp else ())
    return n.to_dict()


class InsertNode(BaseModel):
    after: int = 0          # node seq to insert after; 0 appends
    before: int = 0         # or the node seq to insert above
    cable_from_previous: bool = False   # Design's Insert: the line above's cable


@app.post("/api/networks/{nid}/branches/{branch}/nodes")
def insert_node(nid: str, branch: int, body: InsertNode):
    d = load_for_edit(nid)
    b = d.branch(branch)
    if not b:
        raise HTTPException(404, "branch not found")
    if body.before:
        at = max(0, min(body.before - 1, len(b.nodes)))
    else:
        at = len(b.nodes) if not body.after else body.after
    new = Node()
    if body.cable_from_previous:
        # the line above; above a branch's first line, the coupler's line
        parent = d.branch(b.parent_branch) if b.parent_branch else None
        prev = (b.nodes[at - 1] if at > 0
                else parent.nodes[b.parent_node - 1] if parent and 0 < b.parent_node <= len(parent.nodes)
                else b.nodes[0] if b.nodes else None)
        if prev is not None:
            new.cab, new.cab_part = prev.cab, prev.cab_part
    if new.cab_part is None:
        # cab 0 is cable 0 of the spec set, a real cable, as when a .ntw is
        # read: the user's BH1GHzMid lines keyed with the cab column blank
        # lose 2.54 dB per 100 ft at 1002, cable 0's (190 ft: 52.00 -> 47.17)
        new.cab_part = next((c.id for c in d.library.cables.values()
                             if c.cable_index == new.cab % 100), None)
    b.nodes.insert(at, new)
    d.renumber(b)
    save(d)
    return {"branch": branch, "node": at + 1}


@app.delete("/api/networks/{nid}/branches/{branch}/nodes/{node}")
def delete_node(nid: str, branch: int, branch_node: int = 0, node: int = 0,
                confirm: bool = False):
    """The Delete key.  As the program does it (the user's recording): a
    line with a power stop is not deleted; one a branch begins at is
    deleted with that branch and everything down it, once the "Delete
    Branch(es)?" box has been answered OK (``confirm``)."""
    d = load_for_edit(nid)
    b = d.branch(branch)
    if not b:
        raise HTTPException(404, "branch not found")
    n = next((x for x in b.nodes if x.seq == node), None)
    if n is not None and n.power_stop:
        raise HTTPException(409, detail={"error": "Cannot delete a line with a power stop."})
    starts = [c.branch for c in (n.couplers + n.taps if n else [])
              if c.branch and d.branch(c.branch)]
    if starts and not confirm:
        raise HTTPException(409, detail={"branches": starts})
    # removing a branch takes its coupler off the line and closes the
    # numbers up, so go by what is left on the line
    while n is not None and n.couplers:
        before = len(n.couplers)
        d.remove_branch(n.couplers[0].branch)
        if len(n.couplers) == before:
            n.couplers.pop(0)
    for t in (n.taps if n else []):
        if t.branch and d.branch(t.branch):
            d.remove_branch(t.branch)
        t.branch = 0
    b.nodes = [x for x in b.nodes if x is not n]
    if not b.nodes:
        b.nodes = [Node(seq=1)]
    d.renumber(b)
    save(d)
    return {"ok": True}


class TapEdit(BaseModel):
    slot: int = 0
    part_id: str | None = None
    code: str | None = None      # what was typed, e.g. "4.23"


@app.get("/api/networks/{nid}/nodes/{branch}/{node}/tap/{slot}/candidates")
def tap_choices(nid: str, branch: int, node: int, slot: int):
    """The Select Tap window: every tap, tested in this slot."""
    return tap_candidates(load(nid), branch, node, slot)


@app.put("/api/networks/{nid}/nodes/{branch}/{node}/tap")
def set_tap(nid: str, branch: int, node: int, body: TapEdit):
    d = load_for_edit(nid)
    n = _node(d, branch, node)
    if body.code is not None:
        try:
            part = resolve_tap(d.library, body.code, n.hc, d.parameters.tap_types)
        except EntryError as e:
            raise HTTPException(400, str(e))
    elif body.part_id is None:
        part = None
    else:
        part = d.library.taps.get(body.part_id)
        if not part:
            raise HTTPException(400, "no such tap in the spec set")

    while len(n.taps) <= body.slot:
        n.taps.append(TapPlacement())
    fed = n.taps[body.slot].branch
    if part is None:
        n.taps.pop(body.slot)
        if fed and d.branch(fed):
            # the branch its port fed stays, hanging from the line with
            # nothing feeding it -- as the file keeps such a branch
            n.couplers.append(CouplerPlacement(branch=fed, removed=True))
    else:
        # typed over, the tap keeps the branch its port feeds
        n.taps[body.slot] = TapPlacement(part_id=part.id, ports=part.ports,
                                         value_db=part.tap_value_db, branch=fed)
    save(d)
    return {"node": n.to_dict(),
            "placed": None if part is None else
                      {"name": part.name, "ports": part.ports,
                       "tap_id": part.tap_id, "value_db": part.tap_value_db}}


class CouplerEdit(BaseModel):
    slot: int = 0
    part_id: str | None = None
    code: str | None = None      # what was typed, e.g. "8" or "-8"
    style: str = BRANCH_NORMAL


@app.put("/api/networks/{nid}/nodes/{branch}/{node}/coupler")
def set_coupler(nid: str, branch: int, node: int, body: CouplerEdit):
    """Placing a coupler creates the branch it feeds.

    A leading "-" swaps the legs: the through (low loss) leg goes to the
    branch and the tap (high loss) leg carries on downstream.
    """
    d = load_for_edit(nid)
    n = _node(d, branch, node)
    through = n.through_leg
    if body.code is not None:
        try:
            part, through = resolve_coupler(d.library, body.code)
        except EntryError as e:
            raise HTTPException(400, str(e))
    elif body.part_id is None:
        part = None
    else:
        part = d.library.passives.get(body.part_id)
        if not part:
            raise HTTPException(400, "no such coupler in the spec set")

    if part is None:
        if body.slot < len(n.couplers):
            cp = n.couplers[body.slot]
            # one splitter feeding both branches comes off both: AL004 4.14's
            # 3-<11><12> becomes - <11>  - <12> (the user)
            one = d.library.passives.get(cp.part_id) if cp.part_id else None
            shared = (len(n.couplers) == 2 and one is not None
                      and n.couplers[0].part_id == n.couplers[1].part_id
                      and len(one.port_losses) > 2)
            for c in (list(n.couplers) if shared else [cp]):
                if d.branch_is_empty(c.branch):
                    # nothing on the branch: it goes, and its coupler with it
                    d.remove_branch(c.branch)
                else:
                    # lines on it: the program takes the coupler off and
                    # keeps the branch, "- [55]"; a second 0 leaves it so
                    # (the user's recording, AL002 53.5)
                    c.part_id, c.coupler_id, c.removed = None, 0, True
            if all(c.removed for c in n.couplers):
                n.through_leg = 0
        save(d)
        return {"node": n.to_dict(), "placed": None}

    # re-typing over a coupler changes the coupler; its branch stays
    if body.slot < len(n.couplers):
        cp = n.couplers[body.slot]
        cp.part_id, cp.coupler_id, cp.removed = part.id, int(part.coupler_id or 0), False
        n.through_leg = through
        save(d)
        return {"node": n.to_dict(),
                "placed": {"name": part.name, "coupler_id": part.coupler_id,
                           "legs": part.port_losses, "through_leg": through,
                           "branch": cp.branch}}
    if len(n.couplers) >= 2:
        raise HTTPException(400, "a node can carry at most two couplers")

    # a branch taken away above may have moved this line's branch up
    child = d.add_branch(d.branch_of(n).number, node, body.style)
    n.couplers.insert(min(body.slot, len(n.couplers)),
                      CouplerPlacement(part_id=part.id,
                                       coupler_id=int(part.coupler_id or 0),
                                       branch=child.number, style=body.style))
    n.through_leg = through
    save(d)
    return {"node": n.to_dict(),
            "placed": {"name": part.name, "coupler_id": part.coupler_id,
                       "legs": part.port_losses, "through_leg": through,
                       "branch": child.number}}


@app.delete("/api/networks/{nid}/branches/{branch}")
def delete_branch(nid: str, branch: int):
    d = load_for_edit(nid)
    gone = d.remove_branch(branch)
    save(d)
    return {"removed": gone}


# --------------------------------------------------------------------------
# library, reports, import
# --------------------------------------------------------------------------
@app.get("/api/networks/{nid}/library")
def get_library(nid: str):
    return load(nid).library.to_dict()


@app.post("/api/networks/{nid}/library/sample")
def load_sample(nid: str):
    d = load(nid)
    d.library = starter_library()
    save(d)
    return d.library.to_dict()


# Project Settings' spec files, as its "Errors Loading Project" box names them
PROJECT_FILES = (("Parameters", ".par"), ("Actives", ".atv"), ("Taps", ".tap"),
                 ("Couplers", ".cpr"), ("Cables", ".cbl"), ("Pricing", None),
                 ("Performance", None), ("Map Grid", None))


@app.post("/api/networks/{nid}/library/spec")
async def attach_spec(nid: str, files: list[UploadFile] = File(...)):
    """Project Settings > Set All Files > OK: load a spec set for the network.

    A network read from a .ntw (or with no spec set yet) is read again
    against the new set by position, as the program does -- tap row, coupler
    record, actives index -- keeping every edit; the program's "Errors
    Loading Project" lines come back with it.  Pricing, Performance and Map
    Grid files are not read here, so those keep Untitled.
    """
    d = load(nid)
    was = d.library.name or "Untitled"
    uploaded = {}
    with tempfile.TemporaryDirectory() as tmp:
        base, have = None, set()
        for f in files:
            name = Path(f.filename).name
            data = await f.read()
            (Path(tmp) / name).write_bytes(data)
            base = Path(tmp) / Path(name).stem
            have.add(Path(name).suffix.lower())
            uploaded[Path(name).suffix.lower()] = data
        if base is None:
            raise HTTPException(400, "no files uploaded")
        whole = all(ext in have for _, ext in PROJECT_FILES if ext)
        errors = []
        for what, ext in PROJECT_FILES:
            if ext and whole:
                errors.append(f"{what} file [{base.name}] Loaded..")
            else:
                kept = was if ext else "Untitled"
                errors.append(f"{what} file [{base.name}] Not found or Invalid.. File {kept} retained.")
        if not whole:
            return {"library": d.library.to_dict(), "errors": errors, "loaded": False}
        feeder = d.branches.get(1)
        by_position = bool(feeder and feeder.nodes) and (
            ntw_file(nid) is not None or not d.has_specs or
            any(p.source.startswith("lodedata:") for p in d.library.actives.values()))
        if by_position:
            try:
                d = _read_again(nid, d, base)
            except (ExportError, ValueError) as e:
                raise HTTPException(400, str(e))
        else:
            relink_library(d, library_from_spec_set(base, d.parameters))
    save(d)
    keep_spec_files(nid, uploaded)
    return {"library": d.library.to_dict(), "errors": errors, "loaded": True}


def _read_again(nid: str, d: Design, base: Path) -> Design:
    """The network written as a .ntw as it stands, and read back against
    the spec set at ``base``: what the file holds by position is what the
    network is under the new set.  What a .ntw does not hold yet (TSG, map,
    location, address, notes) is carried across line by line."""
    source = ntw_file(nid)
    layout = ntw_file(layout_key(nid))
    data, _ = export_ntw(d, source, name=d.name,
                         header=layout[:512] if source is None and layout else None)
    new, _ = design_from_ntw(data, base, name=d.name)
    new.id = d.id
    for b, old in d.branches.items():
        nb = new.branches.get(b)
        for on, nn in zip(old.nodes, nb.nodes if nb else []):
            nn.tsg, nn.map, nn.loc, nn.address, nn.note = on.tsg, on.map, on.loc, on.address, on.note
        if nb:
            nb.style, nb.label = old.style, old.label
    keep_ntw_file(nid, data)
    return new


SPEC_EXTS = {".par", ".atv", ".tap", ".cpr", ".cbl", ".prc", ".per"}


@app.post("/api/import/ntw")
async def import_ntw(file: UploadFile = File(...),
                     specs: list[UploadFile] = File(default=[])):
    """Open a Lode Data design as a new network.

    A .ntw refers to equipment by its position in the spec files, so it reads
    right only against the spec set it was saved with; that set's name is in
    the file.  Without spec files it opens with none, as the program does,
    and the set is attached later through Project Settings.
    """
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / Path(file.filename).name
        data = await file.read()
        p.write_bytes(data)
        info = inspect_ntw(p)
        base = None
        kept = {}
        for f in specs:
            name = Path(f.filename).name
            if Path(name).suffix.lower() not in SPEC_EXTS:
                continue
            spec = await f.read()
            (Path(tmp) / name).write_bytes(spec)
            base = Path(tmp) / Path(name).stem
            kept[Path(name).suffix.lower()] = spec
        try:
            # with no spec files it opens as the program opens it: levels
            # 0.00 and the Spec File Mismatch box naming the set it needs
            d, report = design_from_ntw(p, base)
        except ValueError as e:
            raise HTTPException(400, str(e))
    d.id = new_id("ntw")
    save(d)
    keep_ntw_file(d.id, data)
    if base is not None:
        keep_spec_files(d.id, kept)
    return {"imported": True, "id": d.id, "name": d.name, "report": report, **info}


@app.post("/api/networks/{nid}/ntw")
def save_ntw(nid: str, filename: str | None = None):
    """File > Save Network: the network as a Lode Data .ntw.

    Built over the .ntw it was opened from (or last saved as), which then
    becomes the file the next save builds on.  ``filename`` is the name it is
    saved under: the file keeps it, and the network takes it, as the
    program's Save Network As does.  Anything the file cannot hold yet is
    listed in the X-Not-Written header rather than dropped silently.
    """
    d = load(nid)
    stem = Path(filename).stem if filename else None
    source = ntw_file(nid)
    header = None
    if source is None:
        # keyed in from scratch: written as the program writes a new network,
        # with the licence and user fields of the last .ntw its person opened
        # (blank if none -- Lode Data opens that too)
        layout = ntw_file(layout_key(nid))
        header = layout[:512] if layout else None
    try:
        data, report = export_ntw(d, source, name=stem or d.name, header=header)
    except ExportError as e:
        raise HTTPException(400, str(e))
    if stem:
        d.name = stem
    save(d)
    keep_ntw_file(nid, data)
    name = (d.name or "network").replace('"', "")
    return Response(content=data, media_type="application/octet-stream", headers={
        "Content-Disposition": f'attachment; filename="{name}.ntw"',
        "X-Not-Written": json.dumps(report["not_written"])})


@app.get("/api/networks/{nid}/specs/{ext}")
def spec_window(nid: str, ext: str):
    """Spec Edit > Actives / Cables / Parameters: the window for the file of
    the network's spec set, every tab as Lode shows it."""
    ext = "." + ext.lower().lstrip(".")
    if ext not in WINDOWS:
        raise HTTPException(404, f"no Spec Edit window for {ext} files yet")
    data = ntw_file(spec_key(nid, ext))
    if data is None:
        raise HTTPException(404, "This network's spec files were attached before the app kept "
                                 "them: attach the set again (File > Project Settings > Set All Files).")
    d = load(nid)
    par = ntw_file(spec_key(nid, ".par"))
    try:
        return window(ext, data, par, f"{d.library.name or 'Untitled'}{ext}")
    except (ValueError, struct.error) as e:
        raise HTTPException(400, f"cannot read this {ext} file: {e}")


_REPORTS = {"levels": level_report, "bom": bill_of_materials,
            "powering": powering_report}


@app.get("/api/networks/{nid}/reports/{kind}")
def report(nid: str, kind: str, format: str = "json"):
    if kind not in _REPORTS:
        raise HTTPException(404, f"no such report: {kind}")
    rows = _REPORTS[kind](load(nid))
    if format == "csv":
        return PlainTextResponse(
            to_csv(rows), media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{kind}.csv"'})
    return rows


@app.get("/favicon.ico")
def favicon():
    import base64
    return Response(base64.b64decode(
        "R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"),
        media_type="image/gif")


@app.get("/")
def index():
    return FileResponse(WEB / "index.html")


app.mount("/", StaticFiles(directory=WEB), name="web")
