"""HTTP API and static hosting for the design tool.

Run with:  python -m uvicorn api:app --reload --app-dir app
"""
from __future__ import annotations

import json
import sqlite3
import tempfile
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile, File, Response
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from hfc.model import Network, Element, DesignParameters, Library, new_id
from hfc.starter import starter_library
from hfc.engine import calculate
from hfc.reports import level_report, bill_of_materials, powering_report, to_csv
from hfc.importer import library_from_spec_set, inspect_ntw, relink_library

WEB = Path(__file__).parent / "web"
DB_PATH = Path(__file__).parent.parent / "data" / "designs.db"

app = FastAPI(title="HFC Design")


# --------------------------------------------------------------------------
# storage: one JSON document per design
# --------------------------------------------------------------------------
def db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.execute("CREATE TABLE IF NOT EXISTS designs ("
                "id TEXT PRIMARY KEY, name TEXT, updated TEXT, doc TEXT)")
    return con


def load(design_id: str) -> Network:
    con = db()
    row = con.execute("SELECT doc FROM designs WHERE id=?", (design_id,)).fetchone()
    con.close()
    if not row:
        raise HTTPException(404, "design not found")
    return Network.from_dict(json.loads(row[0]))


def save(net: Network) -> Network:
    con = db()
    con.execute(
        "INSERT INTO designs(id,name,updated,doc) VALUES(?,?,datetime('now'),?) "
        "ON CONFLICT(id) DO UPDATE SET name=excluded.name, "
        "updated=excluded.updated, doc=excluded.doc",
        (net.id, net.name, json.dumps(net.to_dict())))
    con.commit()
    con.close()
    return net


# --------------------------------------------------------------------------
# designs
# --------------------------------------------------------------------------
class NewDesign(BaseModel):
    name: str = "New design"


@app.get("/api/designs")
def list_designs():
    con = db()
    rows = con.execute("SELECT id,name,updated FROM designs ORDER BY updated DESC").fetchall()
    con.close()
    return [{"id": r[0], "name": r[1], "updated": r[2]} for r in rows]


@app.post("/api/designs")
def create_design(body: NewDesign):
    net = Network(id=new_id("dsn"), name=body.name, library=starter_library())
    net.add(Element(id=new_id("el"), type="node", label="Node 1",
                    part_id="act_Optical_node_4_out",
                    source_dbmv=50.0, source_tilt_db=10.0))
    save(net)
    return net.to_dict()


@app.get("/api/designs/{design_id}")
def get_design(design_id: str):
    return load(design_id).to_dict()


@app.delete("/api/designs/{design_id}")
def delete_design(design_id: str):
    con = db()
    con.execute("DELETE FROM designs WHERE id=?", (design_id,))
    con.commit()
    con.close()
    return {"deleted": design_id}


class DesignPatch(BaseModel):
    name: str | None = None
    parameters: dict | None = None


@app.patch("/api/designs/{design_id}")
def patch_design(design_id: str, body: DesignPatch):
    net = load(design_id)
    if body.name is not None:
        net.name = body.name
    if body.parameters is not None:
        current = net.parameters.__dict__ | body.parameters
        net.parameters = DesignParameters(**current)
    save(net)
    return net.to_dict()


# --------------------------------------------------------------------------
# elements
# --------------------------------------------------------------------------
class ElementBody(BaseModel):
    type: str = "tap"
    label: str = ""
    parent_id: str | None = None
    parent_port: int = 0
    cable_id: str | None = None
    length_ft: float = 0.0
    part_id: str | None = None
    houses: int = 0
    output_dbmv: float | None = None
    tilt_db: float | None = None
    source_dbmv: float | None = None
    source_tilt_db: float | None = None
    supply_volts: float | None = None
    notes: str = ""


@app.post("/api/designs/{design_id}/elements")
def add_element(design_id: str, body: ElementBody):
    net = load(design_id)
    el = Element(id=new_id("el"), **body.model_dump())
    if not el.label:
        n = sum(1 for e in net.elements.values() if e.type == el.type) + 1
        el.label = f"{el.type.replace('_', ' ').title()} {n}"
    net.add(el)
    save(net)
    return el.__dict__


@app.put("/api/designs/{design_id}/elements/{element_id}")
def update_element(design_id: str, element_id: str, body: ElementBody):
    net = load(design_id)
    el = net.elements.get(element_id)
    if not el:
        raise HTTPException(404, "element not found")
    for k, v in body.model_dump().items():
        setattr(el, k, v)
    save(net)
    return el.__dict__


@app.delete("/api/designs/{design_id}/elements/{element_id}")
def delete_element(design_id: str, element_id: str):
    net = load(design_id)
    removed = net.remove(element_id)
    save(net)
    return {"removed": removed}


# --------------------------------------------------------------------------
# results and reports
# --------------------------------------------------------------------------
@app.get("/api/designs/{design_id}/results")
def results(design_id: str):
    return calculate(load(design_id)).as_dict()


_REPORTS = {"levels": level_report, "bom": bill_of_materials,
            "powering": powering_report}


@app.get("/api/designs/{design_id}/reports/{kind}")
def report(design_id: str, kind: str, format: str = "json"):
    if kind not in _REPORTS:
        raise HTTPException(404, f"no such report: {kind}")
    rows = _REPORTS[kind](load(design_id))
    if format == "csv":
        return PlainTextResponse(
            to_csv(rows), media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{kind}.csv"'})
    return rows


# --------------------------------------------------------------------------
# library
# --------------------------------------------------------------------------
@app.get("/api/designs/{design_id}/library")
def get_library(design_id: str):
    return load(design_id).library.to_dict()


@app.put("/api/designs/{design_id}/library")
def put_library(design_id: str, body: dict):
    net = load(design_id)
    net.library = Library.from_dict(body)
    save(net)
    return net.library.to_dict()


@app.post("/api/designs/{design_id}/library/spec")
async def attach_spec_set(design_id: str, files: list[UploadFile] = File(...)):
    """Upload a Lode Data spec set (.cbl/.cpr/.atv/.tap/.par) and attach it.

    Existing devices are re-matched to the new library by part name, so the
    topology survives the upgrade.
    """
    net = load(design_id)
    with tempfile.TemporaryDirectory() as tmp:
        base = None
        for f in files:
            name = Path(f.filename).name
            (Path(tmp) / name).write_bytes(await f.read())
            base = Path(tmp) / Path(name).stem
        if base is None:
            raise HTTPException(400, "no files uploaded")
        lib = library_from_spec_set(base)
    report_ = relink_library(net, lib)
    save(net)
    return {"library": lib.to_dict(), "relink": report_}


@app.post("/api/import/ntw")
async def import_ntw(file: UploadFile = File(...)):
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / Path(file.filename).name
        p.write_bytes(await file.read())
        return inspect_ntw(p)


# --------------------------------------------------------------------------
# static site
# --------------------------------------------------------------------------
@app.get("/favicon.ico")
def favicon():
    # a 1x1 transparent gif, enough to stop the browser asking
    import base64
    return Response(base64.b64decode(
        "R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"),
        media_type="image/gif")


@app.get("/")
def index():
    return FileResponse(WEB / "index.html")


app.mount("/", StaticFiles(directory=WEB), name="web")
