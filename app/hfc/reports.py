"""Design reports: level/cascade sheet, bill of materials, powering."""
from __future__ import annotations

import csv
import io

from .model import Network
from .engine import calculate, Results


def level_report(net: Network, res: Results | None = None) -> list:
    res = res or calculate(net)
    out = []
    for eid in res.order:
        r = res.rows[eid]
        out.append({
            "depth": r.depth,
            "label": r.label,
            "type": r.type,
            "cable": r.cable_name,
            "length_ft": round(r.length_ft, 1),
            "cumulative_ft": round(r.cumulative_ft, 1),
            "span_loss_high": round(r.span_loss_high, 2),
            "in_low": round(r.input.low, 2),
            "in_high": round(r.input.high, 2),
            "out_low": round(r.output.low, 2),
            "out_high": round(r.output.high, 2),
            "tilt": round(r.output.tilt, 2),
            "gain_high": round(r.gain_high, 2) if r.gain_high is not None else "",
            "tap_low": round(r.tap_port.low, 2) if r.tap_port else "",
            "tap_high": round(r.tap_port.high, 2) if r.tap_port else "",
            "return_at_node_low": round(r.return_at_node.low, 2) if r.return_at_node else "",
            "return_at_node_high": round(r.return_at_node.high, 2) if r.return_at_node else "",
            "volts": round(r.volts, 1) if r.volts is not None else "",
            "current_a": round(r.segment_current_a, 2),
            "houses": r.houses,
            "warnings": "; ".join(r.warnings),
        })
    return out


def bill_of_materials(net: Network) -> list:
    counts: dict = {}
    footage: dict = {}
    for el in net.elements.values():
        part = None
        for table in (net.library.taps, net.library.passives,
                      net.library.actives, net.library.power_supplies):
            if el.part_id in table:
                part = table[el.part_id]
                break
        if part is not None:
            key = (type(part).__name__.replace("Type", ""), part.name)
            counts[key] = counts.get(key, 0) + 1
        if el.cable_id and el.length_ft:
            cable = net.library.cables.get(el.cable_id)
            if cable:
                footage[cable.name] = footage.get(cable.name, 0.0) + el.length_ft

    rows = [{"category": cat, "item": name, "quantity": n, "unit": "ea"}
            for (cat, name), n in sorted(counts.items())]
    rows += [{"category": "Cable", "item": name, "quantity": round(ft, 1),
              "unit": "ft"} for name, ft in sorted(footage.items())]
    return rows


def powering_report(net: Network, res: Results | None = None) -> list:
    res = res or calculate(net)
    rows = []
    for eid in res.order:
        r = res.rows[eid]
        if r.current_a == 0 and r.volts is None:
            continue
        rows.append({
            "label": r.label,
            "type": r.type,
            "draw_a": round(r.current_a, 2),
            "carried_a": round(r.segment_current_a, 2),
            "volts": round(r.volts, 1) if r.volts is not None else "",
            "warnings": "; ".join(w for w in r.warnings if "V at the device" in w),
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
