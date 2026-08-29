"""Rebuild a network from a Lode Data report export.

The ``.ntw`` design format is obfuscated and not yet decoded.  But the Design
Assistant will *print* any network -- "printing to a .XLS file allows for
customized spreadsheets" -- and a printed design chart contains everything
needed to rebuild the plant: the location, the footage of the span feeding it,
the house count, and the device.

So this reads the report instead of the file.  It is not a workaround; for
getting existing designs in it is the more reliable path, because it reads the
same numbers the designer sees on screen rather than an inferred byte layout.

Export from Lode Data as CSV, tab-separated or fixed-width text, then::

    lode import-design MYPLANT.csv --specs KERMIT750

Columns are matched by name, not position, so column order and extra columns
do not matter.  Anything the exporter calls a footage (``Ft``, ``Footage``,
``Distance``, ``Span``) is found, and likewise for the rest.

Branching
---------
A printed chart is linear, so branches are carried in whatever way the report
marks them.  Two conventions are understood:

* an explicit ``Leg`` / ``Branch`` column -- rows sharing a value form one leg,
  and a leg is attached to the location named in ``From`` / ``Parent`` if that
  column exists;
* indentation in the location column, which is how a printed chart usually
  shows a feeder hanging off a trunk.

When neither is present the chart is read as a single run, and the importer
says so rather than inventing a topology.
"""

from __future__ import annotations

import csv
import io
import os
import re
from dataclasses import dataclass, field

from ..network import Network

#: report heading -> what we need.  Matching is case- and space-insensitive.
COLUMNS = {
    "label": ("loc", "location", "node", "pole", "id", "ref", "map"),
    "footage": ("ft", "feet", "footage", "distance", "dist", "span", "length",
                "meters", "metres"),
    "units": ("units", "homes", "hh", "houses", "house count", "hc", "passings"),
    "device": ("device", "tap", "equipment", "part", "item", "model",
               "tap value", "value"),
    "kind": ("type", "kind", "class"),
    "cable": ("cable", "cable type", "coax"),
    "leg": ("leg", "branch", "feeder", "line"),
    "parent": ("from", "parent", "origin", "attaches to", "off"),
    "note": ("note", "notes", "comment", "remarks"),
}

ACTIVE_WORDS = ("amp", "le-", "ble", "bridg", "trunk", "node", "extender",
                "active", "mb-", "fm9")
COUPLER_WORDS = ("split", "coupler", "dc-", "dc", "sp-", "pi", "power inserter",
                 "block", "splice")


@dataclass
class ChartReport:
    source: str = ""
    rows_read: int = 0
    rows_used: int = 0
    columns: dict = field(default_factory=dict)
    notes: list = field(default_factory=list)

    def note(self, message: str) -> None:
        if message not in self.notes:
            self.notes.append(message)

    def to_text(self) -> str:
        found = ", ".join(f"{k}={v!r}" for k, v in sorted(self.columns.items()))
        out = [
            f"design chart <- {os.path.basename(self.source)}",
            f"  {self.rows_used} of {self.rows_read} rows used",
            f"  columns: {found or '(none matched)'}",
        ]
        for note in self.notes:
            out.append(f"  ! {note}")
        return "\n".join(out)


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", str(text).strip().lower()).strip()


def _match_columns(header) -> dict:
    """Map our field names onto whatever the report calls them."""
    found = {}
    for index, cell in enumerate(header):
        name = _norm(cell)
        if not name:
            continue
        for field_name, aliases in COLUMNS.items():
            if field_name in found:
                continue
            if name in aliases or any(name == _norm(a) for a in aliases):
                found[field_name] = (index, str(cell).strip())
                break
    return found


def _number(cell, default=0.0) -> float:
    if cell is None:
        return default
    text = re.sub(r"[^0-9.\-]", "", str(cell))
    if text in ("", "-", ".", "-."):
        return default
    try:
        return float(text)
    except ValueError:
        return default


def _sniff(text: str):
    """Read CSV, TSV or whitespace-aligned text into rows."""
    sample = text[:4096]
    if "\t" in sample:
        return [line.split("\t") for line in text.splitlines() if line.strip()]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;|\t")
        return [r for r in csv.reader(io.StringIO(text), dialect) if any(r)]
    except csv.Error:
        pass
    if "," in sample:
        return [r for r in csv.reader(io.StringIO(text)) if any(r)]
    return [re.split(r"\s{2,}", line.strip())
            for line in text.splitlines() if line.strip()]


def _kind_of(device: str, declared: str) -> str:
    text = f"{declared} {device}".lower()
    if any(w in text for w in ("source", "headend", "hub")):
        return "source"
    if any(w in text for w in ACTIVE_WORDS):
        return "active"
    if any(w in text for w in COUPLER_WORDS):
        return "coupler"
    if device:
        return "tap"
    return "point"


def read_design_chart(path: str, name: str = "", specs=None):
    """Rebuild a :class:`Network` from an exported design chart."""
    with open(path, "r", encoding="utf-8-sig", errors="replace") as fh:
        rows = _sniff(fh.read())
    report = ChartReport(source=os.path.abspath(path))
    if not rows:
        report.note("the file is empty")
        return Network(name=name or "imported"), report

    header_at, columns = None, {}
    for index, row in enumerate(rows[:25]):
        candidate = _match_columns(row)
        if "footage" in candidate or ("label" in candidate and "device" in candidate):
            header_at, columns = index, candidate
            break
    if header_at is None:
        report.note("no recognisable heading row: expected a column named "
                    "Loc/Location and one named Ft/Footage/Distance")
        return Network(name=name or "imported"), report

    report.columns = {k: v[1] for k, v in columns.items()}
    body = rows[header_at + 1:]
    report.rows_read = len(body)

    def cell(row, field_name, default=""):
        spot = columns.get(field_name)
        if spot is None or spot[0] >= len(row):
            return default
        return str(row[spot[0]]).strip()

    net = Network(name=name or os.path.splitext(os.path.basename(path))[0])
    legs, order = {}, []
    x = 0.0

    for row in body:
        if not any(str(c).strip() for c in row):
            continue
        label = cell(row, "label")
        device = cell(row, "device")
        if not label and not device:
            continue
        if _norm(label) in ("loc", "location", "total", "totals"):
            continue

        indent = len(str(row[columns["label"][0]])) - \
            len(str(row[columns["label"][0]]).lstrip()) if "label" in columns else 0
        leg_key = cell(row, "leg") or (f"indent{indent}" if indent else "TRUNK")
        footage = _number(cell(row, "footage"))
        units = int(_number(cell(row, "units")))
        kind = _kind_of(device, cell(row, "kind"))
        cable = cell(row, "cable")

        # a bare tap value ("17") becomes a device id via the spec set
        if specs is not None and device and re.fullmatch(r"\d+(\.\d+)?", device):
            ports = specs.parameters.ports_for_homes(units) or 4
            tap = specs.taps.find_value(float(device), ports,
                                        specs.parameters.default_tsg)
            if tap is not None:
                device = tap.id

        loc = net.add_location(
            label=label or f"{len(net.locations) + 1}", kind=kind,
            device=device, units=units, note=cell(row, "note"),
            x=x, y=len(legs) * 220.0,
        )
        x += max(60.0, footage)
        previous = legs.get(leg_key)
        if previous is None:
            parent_label = cell(row, "parent")
            anchor = None
            if parent_label:
                anchor = next((l.id for l in net.locations.values()
                               if l.label == parent_label), None)
            if anchor is None and order:
                anchor = legs[order[0]] if leg_key != "TRUNK" else None
            if anchor is not None:
                net.add_span(anchor, loc.id, cable=cable, length=footage,
                             port=net._default_port(anchor))
            order.append(leg_key)
        else:
            net.add_span(previous, loc.id, cable=cable, length=footage,
                         port=net._default_port(previous))
        legs[leg_key] = loc.id
        report.rows_used += 1

    if net.locations:
        first = net.ordered()[0] if net.source_id else None
        if first is not None and first.kind not in ("source", "active"):
            first.kind = "source"
            report.note(f"the first row ({first.display()}) was taken as the "
                        f"source; set its device on the Properties panel")
    if len(order) <= 1:
        report.note("no leg or branch column was found, so the chart was read "
                    "as one run -- add a Leg column to the export to carry "
                    "branches")
    problems = net.validate()
    for problem in problems:
        report.note(problem)
    return net, report
