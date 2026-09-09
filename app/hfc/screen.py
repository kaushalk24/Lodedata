"""Computes what the Design, Entry and Powering screens display.

One row per node, in the same order the real program walks the plant: down the
feeder, and into each branch where its coupler sits.

Levels shown on a row are the input to the first piece of equipment on that
line -- so the value falls going downstream on the forward frequencies as cable
and insertion loss accumulate.  The return columns instead rise downstream:
they are the level a transmitter at that point has to produce for the signal to
arrive back at the node at the target level.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .plant import Design, Branch, Node, TAP_BRACKETS, BRANCH_BRACKETS, bracket

POWERING_PASSES = 4


@dataclass
class Row:
    branch: int
    node: int
    depth: int = 0              # branch nesting, for the left gutter
    gutter: str = " "           # line art: the branch bracket characters
    # levels at the input to this node, one per design frequency
    levels: dict = field(default_factory=dict)     # MHz -> dBmV
    freq_order: list = field(default_factory=list)  # the column order
    ftg: float = 0.0
    hc: int = 0
    cab: int = 0
    cab_name: str = ""
    lv: int = 0
    tsg: int = 0
    amp: int = 0
    amp_name: str = ""
    amp_label: str = ""
    taps: list = field(default_factory=list)       # rendered strings, e.g. "[26]"
    tap_ports: list = field(default_factory=list)
    couplers: list = field(default_factory=list)   # e.g. "200[2]"
    cumulative_ft: float = 0.0
    # powering
    volts: float | None = None
    current: float = 0.0
    supply: float = 0.0
    # checks
    flags: list = field(default_factory=list)      # (severity, message)

    @property
    def severity(self) -> str:
        if any(s == "red" for s, _ in self.flags):
            return "red"
        if any(s == "yellow" for s, _ in self.flags):
            return "yellow"
        return ""

    def as_dict(self) -> dict:
        return {
            "branch": self.branch, "node": self.node, "depth": self.depth,
            "gutter": self.gutter,
            "levels": [round(self.levels.get(f, 0.0), 2) for f in self.freq_order],
            "ftg": round(self.ftg, 0), "hc": self.hc, "cab": self.cab,
            "cab_name": self.cab_name, "lv": self.lv, "tsg": self.tsg,
            "amp": self.amp, "amp_name": self.amp_name,
            "amp_label": self.amp_label,
            "taps": self.taps, "couplers": self.couplers,
            "cumulative_ft": round(self.cumulative_ft, 0),
            "volts": None if self.volts is None else round(self.volts, 2),
            "current": round(self.current, 2),
            "supply": self.supply,
            "flags": [{"severity": s, "message": m} for s, m in self.flags],
            "severity": self.severity,
        }


@dataclass
class Screen:
    rows: list = field(default_factory=list)
    frequencies: list = field(default_factory=list)   # column order
    problems: list = field(default_factory=list)
    totals: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {"rows": [r.as_dict() for r in self.rows],
                "frequencies": self.frequencies,
                "problems": self.problems, "totals": self.totals}


def _freqs(p) -> list:
    """Column order as the real screen shows it: forward high to return low."""
    return [p.forward_high_mhz, p.forward_low_mhz,
            p.return_high_mhz, p.return_low_mhz]


def _is_forward(p, mhz: float) -> bool:
    return mhz >= p.forward_low_mhz


# --------------------------------------------------------------------------
def build(design: Design) -> Screen:
    p = design.parameters
    freqs = _freqs(p)
    scr = Screen(frequencies=freqs, problems=design.validate())
    lib = design.library
    if not design.branches:
        return scr

    def cable_loss(node: Node, mhz: float) -> float:
        cable = lib.cables.get(node.cab_part)
        return cable.loss_db(mhz, node.ftg) if cable and node.ftg else 0.0

    def walk(branch: Branch, incoming: dict, depth: int, cum_ft: float,
             gutter_open: bool):
        levels = dict(incoming)
        for idx, node in enumerate(branch.nodes):
            row = Row(freq_order=freqs, branch=branch.number, node=node.seq or idx + 1,
                      depth=depth, ftg=node.ftg, hc=node.hc, cab=node.cab,
                      lv=node.lv, tsg=node.tsg, amp=node.amp,
                      amp_label=node.amp_label, supply=node.supply_volts)
            cable = lib.cables.get(node.cab_part)
            row.cab_name = cable.name if cable else ""
            cum_ft += node.ftg
            row.cumulative_ft = cum_ft

            # the span into this node
            for f in freqs:
                loss = cable_loss(node, f)
                if _is_forward(p, f):
                    levels[f] = levels.get(f, 0.0) - loss
                else:
                    levels[f] = levels.get(f, 0.0) + loss
            row.levels = dict(levels)

            # an active replaces the level with its own output
            if node.amp:
                part = lib.actives.get(node.amp_part)
                row.amp_name = part.name if part else str(node.amp)
                if part:
                    if not part.needs_rf_input:
                        # fibre fed: there is no RF input to show on this line
                        row.levels = {f: 0.0 for f in freqs}
                    if part.needs_rf_input:
                        need = part.in_forward_high
                        have = row.levels.get(p.forward_high_mhz, 0.0)
                        if have < need:
                            row.flags.append(("red",
                                f"input {have:.2f} below the {need:.2f} dBmV "
                                f"module input for {part.name}"))
                    levels[p.forward_high_mhz] = part.out_forward_high
                    levels[p.forward_low_mhz] = part.out_forward_low
                    levels[p.return_high_mhz] = part.in_return_high
                    levels[p.return_low_mhz] = part.in_return_low

            # taps: the through loss applies to everything downstream
            for slot in node.taps:
                tap = lib.taps.get(slot.part_id)
                if not tap:
                    continue
                style = TAP_BRACKETS.get(tap.ports, "[]")
                # the Design screen shows the Tap ID, integer part only
                shown = tap.tap_id or int(round(tap.tap_value_db))
                row.taps.append(bracket(str(shown), style))
                row.tap_ports.append(tap.ports)
                port_hi = row.levels[p.forward_high_mhz] - tap.tap_db(p.forward_high_mhz)
                _check_tap(p, row, port_hi)
                for f in freqs:
                    thru = tap.through_db(f, reverse=not _is_forward(p, f))
                    levels[f] = levels[f] - thru if _is_forward(p, f) else levels[f] + thru

            scr.rows.append(row)

            # couplers start branches, walked where they sit
            for cp in node.couplers:
                passive = lib.passives.get(cp.part_id)
                child = design.branch(cp.branch)
                style = BRANCH_BRACKETS.get(cp.style, "[]")
                cid = cp.coupler_id or (passive.coupler_id if passive else 0)
                row.couplers.append(f"{cid or ''}{bracket(str(cp.branch), style)}")
                if not child:
                    continue
                # port 0 is the through leg, the tap legs follow
                tap_leg = passive.port_db(1) if passive else 0.0
                down = {f: (levels[f] - tap_leg if _is_forward(p, f)
                            else levels[f] + tap_leg) for f in freqs}
                walk(child, down, depth + 1, cum_ft, True)
                if passive:
                    thru = passive.port_db(0)
                    for f in freqs:
                        levels[f] = (levels[f] - thru if _is_forward(p, f)
                                     else levels[f] + thru)

    feeder = design.branches.get(1)
    if feeder:
        start = {}
        hi, lo = p.forward_high_mhz, p.forward_low_mhz
        start[hi] = design.source_dbmv
        start[lo] = design.source_dbmv - design.source_tilt_db
        start[p.return_high_mhz] = p.return_target_at_node_dbmv
        start[p.return_low_mhz] = p.return_target_at_node_dbmv
        walk(feeder, start, 0, 0.0, False)

    _gutter(scr)
    _powering(design, scr)
    _totals(design, scr)
    return scr


def _check_tap(p, row: Row, port_hi: float) -> None:
    """Tap port level against the System Levels window, with the tap margin."""
    lo, hi = p.min_tap_port_dbmv, p.max_tap_port_dbmv
    margin = getattr(p, "tap_margin_db", 1.0)
    if port_hi > hi + margin or port_hi < lo - margin:
        row.flags.append(("red", f"tap port {port_hi:.2f} dBmV outside "
                                 f"{lo:g}..{hi:g} dBmV"))
    elif port_hi > hi or port_hi < lo:
        row.flags.append(("yellow", f"tap port {port_hi:.2f} dBmV is within the "
                                    f"tap margin of the {lo:g}..{hi:g} window"))


def _gutter(scr: Screen) -> None:
    """The line art down the left edge that shows where branches run."""
    spans: dict = {}
    for i, r in enumerate(scr.rows):
        spans.setdefault((r.branch, r.depth), [i, i])[1] = i
    for (branch, depth), (first, last) in spans.items():
        if depth == 0 or first == last:
            continue
        for i in range(first, last + 1):
            ch = "┌" if i == first else ("└" if i == last else "│")
            scr.rows[i].gutter = ch


# --------------------------------------------------------------------------
def _powering(design: Design, scr: Screen) -> None:
    lib = design.library
    by_key = {(r.branch, r.node): r for r in scr.rows}
    supply = next((n.supply_volts for b in design.branches.values()
                   for n in b.nodes if n.supply_volts), design.supply_volts)
    volts = {k: supply for k in by_key}

    def draw(node: Node, v: float) -> float:
        if node.amp:
            part = lib.actives.get(node.amp_part)
            if part:
                return part.current_at(v)
        return 0.0

    def accumulate(branch: Branch) -> float:
        total = 0.0
        for node in branch.nodes:
            key = (branch.number, node.seq)
            row = by_key.get(key)
            own = draw(node, volts.get(key, supply))
            sub = 0.0
            for cp in node.couplers:
                child = design.branch(cp.branch)
                if child and not node.power_stop:
                    sub += accumulate(child)
            if row is not None:
                row.current = own + sub
            total += own + sub
        # a node's current column carries everything from it downstream
        running = 0.0
        for node in reversed(branch.nodes):
            row = by_key.get((branch.number, node.seq))
            if row is None:
                continue
            running += row.current
            row.current = running
        return total

    def distribute(branch: Branch, v: float):
        for node in branch.nodes:
            key = (branch.number, node.seq)
            row = by_key.get(key)
            if row is None:
                continue
            if node.supply_volts:
                v = node.supply_volts
            cable = lib.cables.get(node.cab_part)
            if cable and node.ftg:
                v -= row.current * cable.resistance_ohms(node.ftg)
            volts[key] = v
            row.volts = v
            if node.amp:
                part = lib.actives.get(node.amp_part)
                if part and v < part.min_voltage:
                    row.flags.append(("red", f"{v:.1f} V is below the "
                                             f"{part.min_voltage:.0f} V minimum "
                                             f"for {part.name}"))
            for cp in node.couplers:
                child = design.branch(cp.branch)
                if child and not node.power_stop:
                    distribute(child, v)

    feeder = design.branches.get(1)
    if not feeder:
        return
    for _ in range(POWERING_PASSES):
        accumulate(feeder)
        distribute(feeder, supply)


def _totals(design: Design, scr: Screen) -> None:
    taps = sum(len(r.taps) for r in scr.rows)
    scr.totals = {
        "branches": len(design.branches),
        "nodes": len(scr.rows),
        "taps": taps,
        "actives": sum(1 for r in scr.rows if r.amp),
        "homes": sum(r.hc for r in scr.rows),
        "footage": round(sum(r.ftg for r in scr.rows)),
        "errors": sum(1 for r in scr.rows if r.severity == "red"),
        "warnings": sum(1 for r in scr.rows if r.severity == "yellow"),
    }
