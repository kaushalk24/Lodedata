"""A design written out as a Lode Data .ntw.

The file is built over the .ntw the design was opened from, so every byte
the program wrote and this package does not model stays as it was; only the
lines, branches and totals the design holds are written (see
tools/lodedata/writer.py).  Parts go back in by their position in the spec
set -- tap row and port code, actives index, coupler record, cable ID -- the
way the program refers to them.
"""
from __future__ import annotations

import sys
from pathlib import Path

_TOOLS = Path(__file__).resolve().parents[2] / "tools"
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

from lodedata import writer as W                              # noqa: E402
from lodedata.network import TAP_CODES                         # noqa: E402
from lodedata.obfuscation import PAYLOAD_START, deobfuscate    # noqa: E402

from .plant import Design, THROUGH_FIRST, THROUGH_SECOND       # noqa: E402
from .screen import _active_kind                               # noqa: E402


class ExportError(ValueError):
    pass


def export_ntw(design: Design, source: bytes | None, name: str | None = None,
               fresh: bool = False, header: bytes | None = None) -> tuple[bytes, dict]:
    """The design as a .ntw file, built over ``source`` (the .ntw it came
    from, as read from disk), to be saved as ``name``.ntw.  Returns the file
    and a report; the design's
    lines and branches are given the ids they now have in the file, so the
    next save carries on from this one.

    ``fresh`` (a network keyed in from scratch, ``source`` None) writes it
    as the program writes a new network: over its empty file, with the
    licence and user fields of ``header`` when one is given."""
    if source is None:
        raw, fresh = W.blank(header), True
    else:
        plain = source[:PAYLOAD_START] + deobfuscate(source[PAYLOAD_START:])
        try:
            raw = W.split(plain)
        except ValueError as e:
            raise ExportError(f"the file this network was opened from cannot be read back: {e}")
    lib = design.library
    report = {"not_written": []}

    def note(text: str):
        if len(report["not_written"]) < 200:
            report["not_written"].append(text)

    # branch numbers run 1..n in the file, in the design's order
    numbers = sorted(design.branches)
    number = {b: k + 1 for k, b in enumerate(numbers)}

    outs = []
    for b in numbers:
        br = design.branches[b]
        nodes = []
        for i, n in enumerate(br.nodes, start=1):
            where = f"{b}.{i}"
            taps = []
            for t in n.taps:
                part = lib.taps.get(t.part_id) if t.part_id else None
                if part is not None and part.row >= 0 and part.ports in TAP_CODES:
                    taps.append((part.row, TAP_CODES[part.ports]))
                else:
                    # an empty column ahead of a tap, or a tap the spec set
                    # could not name: the file keeps what it had there
                    taps.append(W.KEEP if n.rec else None)
            active, pads, pad_banks, config = 0, None, None, None
            if n.amp:
                part = lib.actives.get(n.amp_part) if n.amp_part else None
                if part is not None and part.index > 0:
                    active = part.index
                    config = n.amp_config
                    if len(part.banks) == 4:
                        pad_banks = [b - 1 for b in part.banks]
                    if n.pads:
                        pads = list(n.pads)
                elif n.rec:
                    active = -1
                else:
                    note(f"{where}: active {n.amp} is not in the spec set")
            elif n.kept_active and n.rec:
                active = -1
            supply, supply_type = "", 0
            if n.supply_label:
                supply = n.supply_label
                ps = lib.power_supplies.get(n.supply_part) if n.supply_part else None
                supply_type = ps.type_id if ps is not None else -1
            elif n.supply_volts:
                note(f"{where}: a power supply given only a voltage is not written")
            if n.tsg:
                note(f"{where}: TSG {n.tsg} is not written (where the file keeps it is not known yet)")
            for field, text in (("map", n.map), ("loc", n.loc), ("address", n.address)):
                if text:
                    note(f"{where}: {field} is not written (where the file keeps it is not known yet)")
            # the line's Notes, C-style at +698 with each row followed by
            # "~0" (SN001's 1.1); a note left as the file had it is not touched
            text = n.note.encode("latin-1", "replace") if n.note != n.note_file else None
            nodes.append(W.NodeOut(
                rec=n.rec, ftg=int(round(n.ftg)), hc=n.hc, cable=n.cab, lv=n.lv,
                # a branch whose coupler was taken off is listed on no line
                taps=taps, branches=[number[c.branch] for c in n.couplers
                                     if c.branch in number and not c.removed],
                active_index=active, inline=n.inline, pads=pads, fixed=n.fixed,
                power_stop=n.power_stop, label=n.amp_label if (n.amp or n.rec) else None,
                supply=supply, supply_type=supply_type, pad_banks=pad_banks, config=config,
                text=text))

        coupler, through = 0, False
        if br.parent_branch in design.branches:
            parent = design.branches[br.parent_branch]
            if 0 < br.parent_node <= len(parent.nodes):
                pnode = parent.nodes[br.parent_node - 1]
                for k, cp in enumerate(pnode.couplers, start=1):
                    if cp.branch != b:
                        continue
                    if cp.removed:
                        coupler = 0
                        continue
                    part = lib.passives.get(cp.part_id) if cp.part_id else None
                    coupler = part.record if part is not None and part.record > 0 else -1
                    through = ((pnode.through_leg == THROUGH_FIRST and k == 1)
                               or (pnode.through_leg == THROUGH_SECOND and k == 2))
        outs.append(W.BranchOut(
            nodes=nodes, end_rec=br.end_rec, coupler_record=coupler if b != numbers[0] else 0,
            through=through,
            parent=(number.get(br.parent_branch, 0), br.parent_node) if b != numbers[0] else (0, 0)))

    info = None
    if lib.actives:
        p = design.parameters
        info = W.SpecInfo(
            line_extenders={a.index for a in lib.actives.values()
                            if a.index > 0 and _active_kind(a) == "line_extender"},
            points=dict(p.equipment_points or {}),
            housings=[tuple(h) for h in (p.housings or [])])
    try:
        plain_out, ids = W.build(raw, outs, name=name, spec=lib.name or None, fresh=fresh,
                                 info=info)
    except W.WriteError as e:
        raise ExportError(str(e))
    for b, node_ids, end in zip(numbers, ids["nodes"], ids["ends"]):
        br = design.branches[b]
        br.end_rec = end
        for n, rec in zip(br.nodes, node_ids):
            n.rec = rec
    report["branches"] = len(outs)
    report["nodes"] = sum(len(o.nodes) for o in outs)
    return W.encode(plain_out), report
