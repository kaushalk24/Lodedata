"""HTTP API and static hosting.

Run with:  ./run.sh   (python -m uvicorn api:app --app-dir app)
"""
from __future__ import annotations

import json
import os
import sqlite3
import tempfile
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile, File, Response
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from hfc.model import Library, DesignParameters, new_id
from hfc.plant import (Design, Branch, Node, TapPlacement, CouplerPlacement,
                       BRANCH_NORMAL)
from hfc.screen import build, tap_candidates
from hfc.entry import resolve_tap, resolve_coupler, resolve_active, EntryError
from hfc.starter import starter_library
from hfc.reports import level_report, bill_of_materials, powering_report, to_csv
from hfc.importer import (library_from_spec_set, inspect_ntw, relink_library,
                          design_from_ntw)

WEB = Path(__file__).parent / "web"
DB_PATH = Path(os.environ.get("LODEDATA_DB",
                              Path(__file__).parent.parent / "data" / "designs.db"))

app = FastAPI(title="Design Assistant")


# --------------------------------------------------------------------------
def db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.execute("CREATE TABLE IF NOT EXISTS designs ("
                "id TEXT PRIMARY KEY, name TEXT, updated TEXT, doc TEXT)")
    return con


def load(design_id: str) -> Design:
    con = db()
    row = con.execute("SELECT doc FROM designs WHERE id=?", (design_id,)).fetchone()
    con.close()
    if not row:
        raise HTTPException(404, "network not found")
    return Design.from_dict(json.loads(row[0]))


def save(d: Design) -> Design:
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
    return d.to_dict()


@app.get("/api/networks/{nid}")
def get_network(nid: str):
    return load(nid).to_dict()


@app.delete("/api/networks/{nid}")
def delete_network(nid: str):
    con = db()
    con.execute("DELETE FROM designs WHERE id=?", (nid,))
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
    d = load(nid)
    n = _node(d, branch, node)
    if body.clear_amp:
        n.amp, n.amp_part, n.amp_label = "", None, ""
    if body.amp_code is not None:
        try:
            part = resolve_active(d.library, body.amp_code)
        except EntryError as e:
            raise HTTPException(400, str(e))
        if part is None:
            n.amp, n.amp_part = "", None
        else:
            n.amp, n.amp_part = part.active_id or "", part.id
    for f, v in body.model_dump(exclude_none=True).items():
        if f in ("clear_amp", "amp_code"):
            continue
        setattr(n, f, v)
    save(d)
    return n.to_dict()


class InsertNode(BaseModel):
    after: int = 0          # node seq to insert after; 0 appends


@app.post("/api/networks/{nid}/branches/{branch}/nodes")
def insert_node(nid: str, branch: int, body: InsertNode):
    d = load(nid)
    b = d.branch(branch)
    if not b:
        raise HTTPException(404, "branch not found")
    at = len(b.nodes) if not body.after else body.after
    b.nodes.insert(at, Node())
    d.renumber(b)
    save(d)
    return {"branch": branch, "node": at + 1}


@app.delete("/api/networks/{nid}/branches/{branch}/nodes/{node}")
def delete_node(nid: str, branch: int, branch_node: int = 0, node: int = 0):
    d = load(nid)
    b = d.branch(branch)
    if not b:
        raise HTTPException(404, "branch not found")
    b.nodes = [n for n in b.nodes if n.seq != node]
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
    d = load(nid)
    n = _node(d, branch, node)
    if body.code is not None:
        try:
            part = resolve_tap(d.library, body.code, n.hc)
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
    if part is None:
        n.taps.pop(body.slot)
    else:
        n.taps[body.slot] = TapPlacement(part_id=part.id, ports=part.ports,
                                         value_db=part.tap_value_db)
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
    d = load(nid)
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
            d.remove_branch(n.couplers[body.slot].branch)
            n.couplers.pop(body.slot)
            if not n.couplers:
                n.through_leg = 0
        save(d)
        return {"node": n.to_dict(), "placed": None}

    # re-typing over an existing coupler replaces it rather than stacking
    if body.slot < len(n.couplers):
        d.remove_branch(n.couplers[body.slot].branch)
        n.couplers.pop(body.slot)
    if len(n.couplers) >= 2:
        raise HTTPException(400, "a node can carry at most two couplers")

    child = d.add_branch(branch, node, body.style)
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
    d = load(nid)
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


@app.post("/api/networks/{nid}/library/spec")
async def attach_spec(nid: str, files: list[UploadFile] = File(...)):
    d = load(nid)
    with tempfile.TemporaryDirectory() as tmp:
        base = None
        for f in files:
            name = Path(f.filename).name
            (Path(tmp) / name).write_bytes(await f.read())
            base = Path(tmp) / Path(name).stem
        if base is None:
            raise HTTPException(400, "no files uploaded")
        lib = library_from_spec_set(base, d.parameters)
    report = relink_library(d, lib)
    save(d)
    return {"library": lib.to_dict(), "matched": report["matched"],
            "unmatched": report["unmatched"][:40]}


SPEC_EXTS = {".par", ".atv", ".tap", ".cpr", ".cbl", ".prc", ".per"}


@app.post("/api/import/ntw")
async def import_ntw(file: UploadFile = File(...),
                     specs: list[UploadFile] = File(default=[])):
    """Open a Lode Data design as a new network.

    A .ntw refers to equipment by its position in the spec files, so it reads
    right only against the spec set it was saved with; that set's name is in
    the file.  Without spec files this just says what the file is and which
    set it needs.
    """
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / Path(file.filename).name
        p.write_bytes(await file.read())
        info = inspect_ntw(p)
        base = None
        for f in specs:
            name = Path(f.filename).name
            if Path(name).suffix.lower() not in SPEC_EXTS:
                continue
            (Path(tmp) / name).write_bytes(await f.read())
            base = Path(tmp) / Path(name).stem
        if base is None:
            return {"imported": False, **info}
        try:
            d, report = design_from_ntw(p, base)
        except ValueError as e:
            raise HTTPException(400, str(e))
    d.id = new_id("ntw")
    save(d)
    return {"imported": True, "id": d.id, "name": d.name, "report": report, **info}


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
