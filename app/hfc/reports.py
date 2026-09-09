"""Design reports: the level sheet, bill of materials and powering."""
from __future__ import annotations

import csv
import io

from .plant import Design
from .screen import build, Screen


def level_report(design: Design, scr: Screen | None = None) -> list:
    scr = scr or build(design)
    freqs = scr.frequencies
    out = []
    for r in scr.rows:
        row = {"branch": r.branch, "node": r.node}
        for f in freqs:
            row[f"{f:g} MHz"] = round(r.levels.get(f, 0.0), 2)  # noqa: keeps MHz labels
        row.update({
            "ftg": round(r.ftg), "hc": r.hc, "cab": r.cab_name, "lv": r.lv,
            "amp": r.amp_name, "taps": " ".join(r.taps),
            "couplers": " ".join(r.couplers),
            "cumulative ft": round(r.cumulative_ft),
            "volts": "" if r.volts is None else round(r.volts, 1),
            "amps": round(r.current, 2),
            "flags": "; ".join(m for _, m in r.flags),
        })
        out.append(row)
    return out


def bill_of_materials(design: Design) -> list:
    lib = design.library
    counts: dict = {}
    footage: dict = {}

    def bump(category: str, name: str, n: int = 1):
        counts[(category, name)] = counts.get((category, name), 0) + n

    for b in design.branches.values():
        for n in b.nodes:
            if n.amp_part and n.amp_part in lib.actives:
                bump("Active", lib.actives[n.amp_part].name)
            for t in n.taps:
                if t.part_id in lib.taps:
                    bump("Tap", lib.taps[t.part_id].name)
            for c in n.couplers:
                if c.part_id in lib.passives:
                    bump("Coupler", lib.passives[c.part_id].name)
            if n.supply_volts:
                bump("Power supply", f"{n.supply_volts:g} V")
            cable = lib.cables.get(n.cab_part)
            if cable and n.ftg:
                footage[cable.name] = footage.get(cable.name, 0.0) + n.ftg

    rows = [{"category": c, "item": i, "quantity": q, "unit": "ea"}
            for (c, i), q in sorted(counts.items())]
    rows += [{"category": "Cable", "item": name, "quantity": round(ft),
              "unit": "ft"} for name, ft in sorted(footage.items())]
    return rows


def powering_report(design: Design, scr: Screen | None = None) -> list:
    scr = scr or build(design)
    rows = []
    for r in scr.rows:
        if not (r.amp or r.supply or r.current):
            continue
        rows.append({
            "branch": r.branch, "node": r.node,
            "device": r.amp_name or ("power supply" if r.supply else ""),
            "supply V": r.supply or "",
            "volts": "" if r.volts is None else round(r.volts, 1),
            "amps carried": round(r.current, 2),
            "flags": "; ".join(m for s, m in r.flags if "V" in m),
        })
    return rows


def to_csv(rows: list) -> str:
    if not rows:
        return ""
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()
