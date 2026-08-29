"""The report suite.

The Design Assistant's value is as much in what it prints as in what it
calculates: "a full suite of reporting tools".  This module reproduces the
reports designers actually use --

``design_chart``              the Design Mode level chart, as a printout
``active_report``             every amplifier with its inputs, plug-ins and outputs
``tap_distribution``          how many of each tap value and port count
``performance_distribution``  "a breakdown of the expected performance for each
                              type of distortion (c/n, ctb, etc) at every tap"
``power_supply_report``       load, utilisation and voltage in every powering area
``bill_of_materials``         counts and costs, ready for the estimator
``network_notes``             the sticky notes left around the design
``flag_report``               everything out of spec

-- and renders each one as plain text, CSV, JSON or a real ``.xlsx`` workbook
("Printing to a .XLS file allows for customized spreadsheets containing Bill
of Materials or Active Report information").
"""

from __future__ import annotations

import csv
import io
import math
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from xml.sax.saxutils import escape

from .engine.levels import ERROR, OK, WARN
from .network import Network
from .specs import SpecSet


def _fmt(value, digits: int = 1) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        if math.isinf(value):
            return "-"
        if math.isnan(value):
            return ""
        return f"{value:.{digits}f}"
    return str(value)


@dataclass
class Report:
    """A titled table plus optional summary lines."""

    title: str = ""
    columns: list = field(default_factory=list)
    rows: list = field(default_factory=list)
    summary: list = field(default_factory=list)
    meta: dict = field(default_factory=dict)
    #: per-column rounding for numeric values
    digits: dict = field(default_factory=dict)

    # -- rendering -------------------------------------------------------
    def to_text(self, width_limit: int = 200) -> str:
        widths = {}
        for col in self.columns:
            widths[col] = len(str(col))
        cells = []
        for row in self.rows:
            line = {}
            for col in self.columns:
                text = _fmt(row.get(col), self.digits.get(col, 1))
                line[col] = text
                widths[col] = max(widths[col], len(text))
            cells.append(line)

        out = [self.title, "=" * min(len(self.title), width_limit)]
        for key, value in self.meta.items():
            out.append(f"{key}: {value}")
        if self.meta:
            out.append("")
        header = "  ".join(str(c).rjust(widths[c]) for c in self.columns)
        out.append(header)
        out.append("-" * len(header))
        for line in cells:
            out.append("  ".join(line[c].rjust(widths[c]) for c in self.columns))
        if self.summary:
            out.append("-" * len(header))
            out.extend(self.summary)
        return "\n".join(out)

    def to_csv(self) -> str:
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=self.columns, extrasaction="ignore")
        writer.writeheader()
        for row in self.rows:
            writer.writerow({
                c: _fmt(row.get(c), self.digits.get(c, 1)) for c in self.columns
            })
        return buf.getvalue()

    def to_dict(self) -> dict:
        return {
            "title": self.title, "columns": self.columns, "rows": self.rows,
            "summary": self.summary, "meta": self.meta,
        }


# ---------------------------------------------------------------------------
# minimal .xlsx writer (no third-party dependencies)
# ---------------------------------------------------------------------------

def _col_ref(index: int) -> str:
    ref = ""
    index += 1
    while index:
        index, rem = divmod(index - 1, 26)
        ref = chr(65 + rem) + ref
    return ref


def write_workbook(path: str, reports: list) -> str:
    """Write *reports* into a real Excel workbook, one sheet per report."""
    sheets = []
    used_names = set()
    for report in reports:
        name = (report.title or "Sheet")[:31]
        for bad in "[]:*?/\\":
            name = name.replace(bad, "-")
        base, counter = name, 2
        while name in used_names:
            name = f"{base[:28]}_{counter}"
            counter += 1
        used_names.add(name)
        sheets.append((name, report))

    def sheet_xml(report: Report) -> str:
        lines = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
                 '<worksheet xmlns="http://schemas.openxmlformats.org/'
                 'spreadsheetml/2006/main"><sheetData>']
        rows = [[str(c) for c in report.columns]]
        for row in report.rows:
            rows.append([
                _fmt(row.get(c), report.digits.get(c, 1)) for c in report.columns
            ])
        for line in report.summary:
            rows.append([line])
        for r_index, row in enumerate(rows, start=1):
            cells = []
            for c_index, value in enumerate(row):
                ref = f"{_col_ref(c_index)}{r_index}"
                try:
                    number = float(value)
                    if value.strip() == "":
                        raise ValueError
                    cells.append(f'<c r="{ref}"><v>{number}</v></c>')
                except (TypeError, ValueError):
                    cells.append(
                        f'<c r="{ref}" t="inlineStr"><is><t>'
                        f'{escape(str(value))}</t></is></c>'
                    )
            lines.append(f'<row r="{r_index}">{"".join(cells)}</row>')
        lines.append("</sheetData></worksheet>")
        return "".join(lines)

    content_types = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/'
        'content-types">',
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats'
        '-package.relationships+xml"/>',
        '<Default Extension="xml" ContentType="application/xml"/>',
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.'
        'openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>',
    ]
    for index in range(1, len(sheets) + 1):
        content_types.append(
            f'<Override PartName="/xl/worksheets/sheet{index}.xml" '
            f'ContentType="application/vnd.openxmlformats-officedocument.'
            f'spreadsheetml.worksheet+xml"/>'
        )
    content_types.append("</Types>")

    workbook = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/'
        '2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/'
        '2006/relationships"><sheets>',
    ]
    rels = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/'
        'relationships">',
    ]
    for index, (name, _) in enumerate(sheets, start=1):
        workbook.append(
            f'<sheet name="{escape(name)}" sheetId="{index}" r:id="rId{index}"/>'
        )
        rels.append(
            f'<Relationship Id="rId{index}" Type="http://schemas.openxmlformats'
            f'.org/officeDocument/2006/relationships/worksheet" '
            f'Target="worksheets/sheet{index}.xml"/>'
        )
    workbook.append("</sheets></workbook>")
    rels.append("</Relationships>")

    root_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/'
        'relationships"><Relationship Id="rId1" Type="http://schemas.'
        'openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/></Relationships>'
    )

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", "".join(content_types))
        zf.writestr("_rels/.rels", root_rels)
        zf.writestr("xl/workbook.xml", "".join(workbook))
        zf.writestr("xl/_rels/workbook.xml.rels", "".join(rels))
        for index, (_, report) in enumerate(sheets, start=1):
            zf.writestr(f"xl/worksheets/sheet{index}.xml", sheet_xml(report))
    return path


# ---------------------------------------------------------------------------
# the reports themselves
# ---------------------------------------------------------------------------

class ReportBuilder:
    def __init__(self, specs: SpecSet, network: Network, solution,
                 performance: dict | None = None, powering: list | None = None):
        self.specs = specs
        self.network = network
        self.solution = solution
        self.performance = performance or {}
        self.powering = powering or []
        self.params = specs.parameters

    def _meta(self) -> dict:
        return {
            "Network": self.network.name,
            "Spec set": self.specs.name,
            "Units": self.params.distance_units,
            "Levels": self.params.signal_display,
            "Printed": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        }

    # ------------------------------------------------------------------
    def design_chart(self) -> Report:
        """The Design Mode screen, as a printout."""
        params = self.params
        fwd = params.forward_columns
        rtn = params.return_columns
        columns = ["Loc", "Leg", "From", "Type", "Device", "Cable", "Length",
                   "Units"]
        columns += [f"In {params.label(c)}" for c in fwd]
        columns += [f"Tap {params.label(c)}" for c in fwd]
        columns += [f"Rtn {params.label(c)}" for c in rtn]
        columns += ["Pad", "EQ", "Status"]
        # the leg each row belongs to, and where that leg hangs from, so an
        # exported chart carries the topology and can be read back in
        leg_of, leg_from = {}, {}
        for leg in self.network.legs():
            origin = self.network.locations.get(leg.origin)
            name = leg.name or (
                f"{origin.display()}-{leg.port}" if origin else "TRUNK")
            for index, loc_id in enumerate(leg.locations):
                leg_of[loc_id] = name
                # only the first row of a leg names where the leg attaches
                leg_from[loc_id] = (origin.display()
                                    if origin and index == 0 else "")

        rows = []
        for loc_id in self.solution.order:
            res = self.solution.results[loc_id]
            row = {
                "Loc": res.label,
                "Leg": leg_of.get(loc_id, ""),
                "From": leg_from.get(loc_id, ""),
                "Type": res.kind, "Device": res.device,
                "Cable": res.cable, "Length": res.length or "",
                "Units": res.units or "",
                "Pad": res.pad if res.pad is not None else "",
                "EQ": res.eq if res.eq is not None else "",
                "Status": res.status,
            }
            for col in fwd:
                row[f"In {params.label(col)}"] = res.fwd_in.get(col)
                row[f"Tap {params.label(col)}"] = res.fwd_tap.get(col)
            for col in rtn:
                row[f"Rtn {params.label(col)}"] = res.rtn_tap.get(col)
            rows.append(row)
        stats = self.network.stats()
        return Report(
            title="Design Chart", columns=columns, rows=rows,
            meta=self._meta(),
            summary=[
                f"{stats['locations']} locations, {stats['taps']} taps, "
                f"{stats['actives']} actives, {stats['units']} units, "
                f"{stats['footage']:,.0f} {self.params.distance_units}",
                f"{len(self.solution.errors)} error(s), "
                f"{len(self.solution.warnings)} warning(s)",
            ],
        )

    # ------------------------------------------------------------------
    def active_report(self) -> Report:
        params = self.params
        fwd = params.forward_columns
        rtn = params.return_columns
        columns = ["Loc", "Device", "Cascade"]
        columns += [f"Hsg In {params.label(c)}" for c in fwd]
        columns += ["Pad", "EQ"]
        columns += [f"Out {params.label(c)}" for c in fwd]
        columns += [f"Rtn In {params.label(c)}" for c in rtn]
        columns += ["Rtn Pad", "Rtn EQ", "Status"]
        rows = []
        for res in self.solution.actives():
            row = {
                "Loc": res.label, "Device": res.device, "Cascade": res.cascade,
                "Pad": res.pad if res.pad is not None else "",
                "EQ": res.eq if res.eq is not None else "",
                "Rtn Pad": res.rtn_pad if res.rtn_pad is not None else "",
                "Rtn EQ": res.rtn_eq if res.rtn_eq is not None else "",
                "Status": res.status,
            }
            for col in fwd:
                row[f"Hsg In {params.label(col)}"] = res.fwd_in.get(col)
                row[f"Out {params.label(col)}"] = res.module_out.get(col)
            for col in rtn:
                row[f"Rtn In {params.label(col)}"] = res.rtn_module_in.get(col)
            rows.append(row)
        return Report(title="Active Report", columns=columns, rows=rows,
                      meta=self._meta(),
                      summary=[f"{len(rows)} active device(s)"])

    # ------------------------------------------------------------------
    def tap_distribution(self) -> Report:
        counts: dict[str, dict] = {}
        for res in self.solution.taps():
            entry = counts.setdefault(res.device, {
                "Tap": res.device, "Value": "", "Ports": "", "Count": 0,
                "Units": 0,
            })
            entry["Count"] += 1
            entry["Units"] += res.units
        for device, entry in counts.items():
            tap = self.specs.taps.by_id(device)
            if tap is not None:
                entry["Value"] = tap.value
                entry["Ports"] = tap.ports
                entry["Spare"] = max(0, tap.ports * entry["Count"] - entry["Units"])
        rows = sorted(counts.values(),
                      key=lambda r: (r["Ports"] or 0, r["Value"] or 0))
        total_taps = sum(r["Count"] for r in rows)
        total_units = sum(r["Units"] for r in rows)
        total_ports = sum((r["Ports"] or 0) * r["Count"] for r in rows)
        return Report(
            title="Tap Distribution",
            columns=["Tap", "Value", "Ports", "Count", "Units", "Spare"],
            rows=rows, meta=self._meta(),
            digits={"Value": 0},
            summary=[
                f"{total_taps} taps, {total_ports} ports, {total_units} units, "
                f"{total_ports - total_units} spare ports",
            ],
        )

    # ------------------------------------------------------------------
    def performance_distribution(self) -> Report:
        impairments = [i for i in self.specs.performance.rows if i.enabled]
        columns = ["Loc", "Cascade"] + [i.id for i in impairments] + ["Status"]
        rows = []
        worst = {i.id: math.inf for i in impairments}
        for res in self.solution.taps():
            entry = self.performance.get(res.id)
            if entry is None:
                continue
            row = {"Loc": res.label, "Cascade": entry.cascade,
                   "Status": entry.status}
            for imp in impairments:
                value = entry.values.get(imp.id)
                row[imp.id] = value
                if value is not None and value < worst[imp.id]:
                    worst[imp.id] = value
            rows.append(row)
        summary = []
        for imp in impairments:
            if math.isinf(worst[imp.id]):
                continue
            objective = f" (objective {imp.objective:.1f})" if imp.objective else ""
            summary.append(
                f"worst {imp.id}: {worst[imp.id]:.1f} dB{objective}"
            )
        return Report(title="Performance Distribution", columns=columns,
                      rows=rows, meta=self._meta(), summary=summary)

    # ------------------------------------------------------------------
    def power_supply_report(self) -> Report:
        columns = ["Supply", "Location", "Volts", "Rating A", "Load A",
                   "Load %", "Watts", "Min V", "Devices", "Status"]
        rows = []
        for area in self.powering:
            actives = sum(1 for n in area.nodes.values()
                          if n.kind in ("active", "source"))
            status = ERROR if any(f.severity == ERROR for f in area.flags) else (
                WARN if area.flags else OK)
            rows.append({
                "Supply": area.supply_id, "Location": area.label,
                "Volts": area.volts, "Rating A": area.max_amps,
                "Load A": area.total_current, "Load %": area.utilisation,
                "Watts": area.total_watts, "Min V": area.min_voltage,
                "Devices": actives, "Status": status,
            })
        return Report(
            title="Power Supply Report", columns=columns, rows=rows,
            meta=self._meta(), digits={"Load A": 2, "Load %": 0, "Watts": 0},
            summary=[f"{len(rows)} powering area(s)"],
        )

    def powering_detail(self) -> Report:
        columns = ["Supply", "Loc", "Type", "Device", "Volts", "Draw A",
                   "Through A", "Max A", "Status"]
        rows = []
        for area in self.powering:
            for node in area.nodes.values():
                if node.kind not in ("active", "source") and node.through < 0.001:
                    continue
                rows.append({
                    "Supply": area.supply_id, "Loc": node.label,
                    "Type": node.kind, "Device": node.device,
                    "Volts": node.volts, "Draw A": node.draw,
                    "Through A": node.through, "Max A": node.max_amps,
                    "Status": node.status,
                })
        return Report(title="Powering Detail", columns=columns, rows=rows,
                      meta=self._meta(),
                      digits={"Draw A": 3, "Through A": 3, "Volts": 1})

    # ------------------------------------------------------------------
    def bill_of_materials(self, exclude_zero: bool = True) -> Report:
        """Counts and costs every part in the design."""
        items: dict[tuple, dict] = {}

        def add(category: str, ident: str, description: str, part: str,
                quantity: float, unit: str, material: float, labor: float):
            key = (category, ident)
            entry = items.setdefault(key, {
                "Category": category, "Item": ident, "Part": part,
                "Description": description, "Unit": unit, "Quantity": 0.0,
                "Material": 0.0, "Labor": 0.0, "Total": 0.0,
            })
            entry["Quantity"] += quantity
            entry["Material"] += material * quantity
            entry["Labor"] += labor * quantity
            entry["Total"] = entry["Material"] + entry["Labor"]

        def priced(ident: str, part: str, fallback_material: float,
                   fallback_labor: float) -> tuple[float, float]:
            row = self.specs.pricing.price_for(ident, part)
            if row is None:
                return fallback_material, fallback_labor
            return row.material, row.labor

        for loc in self.network.locations.values():
            if loc.kind == "tap":
                tap = self.specs.taps.by_id(loc.device)
                if tap:
                    material, labor = priced(tap.id, tap.part_number,
                                             tap.price, tap.labor)
                    add("Taps", tap.id, tap.description, tap.part_number,
                        1, "each", material, labor)
            elif loc.kind == "coupler":
                cpl = self.specs.couplers.by_id(loc.device)
                if cpl:
                    material, labor = priced(cpl.id, cpl.part_number,
                                             cpl.price, cpl.labor)
                    add("Passives", cpl.id, cpl.description, cpl.part_number,
                        1, "each", material, labor)
            elif loc.kind in ("active", "source"):
                act = self.specs.actives.by_id(loc.device)
                if act:
                    material, labor = priced(act.id, act.part_number,
                                             act.price, act.labor)
                    add("Actives", act.id, act.description, act.part_number,
                        1, "each", material, labor)
                    res = self.solution.get(loc.id)
                    if res is not None and res.pad is not None:
                        add("Plug-ins", f"PAD-{res.pad:g}",
                            f"{res.pad:g} dB forward pad", "", 1, "each", 12.0, 0.0)
                    if res is not None and res.eq is not None:
                        add("Plug-ins", f"EQ-{res.eq:g}",
                            f"{res.eq:g} dB forward equalizer", "", 1, "each",
                            18.0, 0.0)
                    if res is not None and res.rtn_pad is not None:
                        add("Plug-ins", f"RPAD-{res.rtn_pad:g}",
                            f"{res.rtn_pad:g} dB return pad", "", 1, "each",
                            12.0, 0.0)
            if loc.power_supply is not None:
                ps = loc.power_supply
                ident = ps.id or "PS"
                material, labor = priced(ident, "", ps.price or 1850.0, 240.0)
                add("Power", ident,
                    f"{ps.volts:g} V {ps.max_amps:g} A power supply", "",
                    1, "each", material, labor)

        for span in self.network.spans.values():
            cable = self.specs.cables.by_id(span.cable)
            if cable is None:
                continue
            material, labor = priced(cable.id, cable.part_number,
                                     cable.price, cable.labor)
            add("Cable", cable.id, cable.description, cable.part_number,
                span.length, self.params.distance_units, material, labor)
            if span.connectors:
                add("Connectors", f"CONN-{cable.id}",
                    f"connectors for {cable.id}", "", span.connectors, "each",
                    cable.connector_price, 3.0)

        rows = [r for r in items.values()
                if not (exclude_zero and r["Quantity"] == 0)]
        rows.sort(key=lambda r: (r["Category"], r["Item"]))
        material_total = sum(r["Material"] for r in rows)
        labor_total = sum(r["Labor"] for r in rows)
        return Report(
            title="Bill of Materials",
            columns=["Category", "Item", "Part", "Description", "Quantity",
                     "Unit", "Material", "Labor", "Total"],
            rows=rows, meta=self._meta(),
            digits={"Quantity": 0, "Material": 2, "Labor": 2, "Total": 2},
            summary=[
                f"material {material_total:,.2f}",
                f"labor    {labor_total:,.2f}",
                f"total    {material_total + labor_total:,.2f}",
            ],
        )

    # ------------------------------------------------------------------
    def network_notes(self) -> Report:
        rows = []
        for loc in self.network.locations.values():
            if loc.note:
                rows.append({"Loc": loc.display(), "Type": loc.kind,
                             "Device": loc.device, "Note": loc.note})
        return Report(title="Network Notes",
                      columns=["Loc", "Type", "Device", "Note"], rows=rows,
                      meta=self._meta(),
                      summary=[f"{len(rows)} note(s)"])

    def mdu_report(self, threshold: int = 5) -> Report:
        """Locations feeding a unit count large enough to be an MDU."""
        rows = []
        for res in self.solution.taps():
            if res.units < threshold:
                continue
            tap = self.specs.taps.by_id(res.device)
            rows.append({
                "Loc": res.label, "Units": res.units, "Tap": res.device,
                "Ports": tap.ports if tap else "",
                "Level": res.fwd_tap.get(self.params.fwd_eq_high),
                "Shortfall": (res.units - (tap.ports if tap else 0)),
            })
        rows.sort(key=lambda r: -r["Units"])
        return Report(title="MDU Report",
                      columns=["Loc", "Units", "Tap", "Ports", "Level",
                               "Shortfall"],
                      rows=rows, meta=self._meta(),
                      summary=[f"{len(rows)} location(s) at or above "
                               f"{threshold} units"])

    # ------------------------------------------------------------------
    def flag_report(self) -> Report:
        rows = []
        flags = list(self.solution.flags)
        for area in self.powering:
            flags.extend(area.flags)
        order = {ERROR: 0, WARN: 1, OK: 2}
        for flag in sorted(flags, key=lambda f: (order.get(f.severity, 3),
                                                 f.label)):
            rows.append({
                "Severity": flag.severity.upper(), "Code": flag.code,
                "Loc": flag.label, "Column": flag.column,
                "Value": flag.value, "Limit": flag.limit,
                "Message": flag.message,
            })
        errors = sum(1 for r in rows if r["Severity"] == "ERROR")
        warnings = sum(1 for r in rows if r["Severity"] == "WARN")
        return Report(
            title="Design Flags",
            columns=["Severity", "Code", "Loc", "Column", "Value", "Limit",
                     "Message"],
            rows=rows, meta=self._meta(),
            summary=[f"{errors} error(s), {warnings} warning(s)"],
        )

    # ------------------------------------------------------------------
    def all_reports(self) -> list:
        return [
            self.design_chart(),
            self.active_report(),
            self.tap_distribution(),
            self.performance_distribution(),
            self.power_supply_report(),
            self.powering_detail(),
            self.bill_of_materials(),
            self.mdu_report(),
            self.network_notes(),
            self.flag_report(),
        ]


REPORTS = {
    "design": "design_chart",
    "actives": "active_report",
    "taps": "tap_distribution",
    "performance": "performance_distribution",
    "power": "power_supply_report",
    "powering-detail": "powering_detail",
    "bom": "bill_of_materials",
    "mdu": "mdu_report",
    "notes": "network_notes",
    "flags": "flag_report",
}
