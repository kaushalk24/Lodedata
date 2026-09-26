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

from .plant import (Design, Branch, Node, TAP_BRACKETS, BRANCH_BRACKETS, BRANCH_NORMAL,
                    THROUGH_MARK, THROUGH_DOWNSTREAM, bracket)

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
    amp: str = ""
    fixed: bool = False
    amp_name: str = ""
    amp_label: str = ""
    taps: list = field(default_factory=list)       # rendered strings, e.g. "[26]"
    tap_severity: list = field(default_factory=list)  # "", "yellow" or "red" per tap
    tap_levels: list = field(default_factory=list)    # each tap's port levels, per frequency
    power_stop: bool = False
    end: bool = False           # the line under a branch's last node
    port_levels: list = field(default_factory=list)   # that line: last tap's port output
    port_severity: list = field(default_factory=list)
    tap_notes: list = field(default_factory=list)  # (severity, message) about taps
    tap_ports: list = field(default_factory=list)
    tap_parts: list = field(default_factory=list)  # part numbers, for the panel
    couplers: list = field(default_factory=list)   # e.g. "200[2]"
    coupler_parts: list = field(default_factory=list)
    cumulative_ft: float = 0.0
    # powering
    volts: float | None = None
    current: float = 0.0
    supply: float = 0.0
    supply_label: str = ""
    supply_type: int = 0
    supply_name: str = ""
    supply_pct: int | None = None
    powered_by: str = ""        # label of the supply whose area this node is in
    amp_info: dict = field(default_factory=dict)
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
            "amp": self.amp, "amp_name": self.amp_name, "fixed": self.fixed,
            "amp_label": self.amp_label,
            "taps": self.taps, "couplers": self.couplers,
            "tap_severity": self.tap_severity, "end": self.end,
            "tap_levels": [[round(v, 2) for v in t] for t in self.tap_levels],
            "power_stop": self.power_stop,
            "port_levels": [round(v, 2) for v in self.port_levels],
            "port_severity": self.port_severity,
            "tap_parts": self.tap_parts, "coupler_parts": self.coupler_parts,
            "cumulative_ft": round(self.cumulative_ft, 0),
            "volts": None if self.volts is None else round(self.volts, 2),
            "current": round(self.current, 2),
            "supply": self.supply,
            "supply_label": self.supply_label, "supply_type": self.supply_type,
            "supply_name": self.supply_name, "powered_by": self.powered_by,
            "amp_info": self.amp_info,
            "supply_pct": self.supply_pct,
            "flags": [{"severity": s, "message": m} for s, m in self.flags + self.tap_notes],
            "severity": self.severity,
        }


@dataclass
class Screen:
    rows: list = field(default_factory=list)
    frequencies: list = field(default_factory=list)   # column order
    branches: list = field(default_factory=list)      # paging metadata
    problems: list = field(default_factory=list)
    totals: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {"rows": [r.as_dict() for r in self.rows],
                "frequencies": self.frequencies,
                "branches": self.branches,
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

    starts, feeders = {}, {}      # per branch: levels out of its coupler, coupler name

    # Nothing in the file marks a branch <n> or [n].  What fits all seventeen
    # seen on AL004's screens (branch 1: 570<2> 570[3] 570[4] 570[5];
    # branch 4: 12<6> 100[9] 3-<11><12> 2[17] 1<18> 16<19> 100[20]
    # 3[21]<24> 8[22]; branch 6: 100[7]; branch 9: 108[10]): a branch is
    # drawn <n> when it adds no mileage -- no footage, or only 1xx cable --
    # and its first span matches the nearest span behind or ahead of the
    # coupler on the parent branch, the span BkFeed or FwdFd copies (6
    # starts on 4's 121 backward, 11 on its 105 forward, 12 on its 99
    # backward).  Branch 3 is all 1xx
    # too, but branch 1 has no spans, so it is [3].  Confirmed in Lode Data:
    # 11.1 changed from 105 to 106 ft turns 4.14 into 3-[11]<12>.  Only the
    # parent branch counts: 6.1 is a 0-ft branch start at 4.4, and 7 runs
    # along 4's 156 from there, yet it is 100[7] -- 6's own span is 121.
    def mileage(b: Branch) -> float:
        return sum(n.ftg for n in b.nodes if n.cab // 100 not in p.non_mileage_series)

    def fed(b: Branch) -> bool:
        first = next((n.ftg for n in b.nodes if n.ftg), 0)
        parent = design.branch(b.parent_branch)
        if not first or parent is None:
            return not first
        spans = [n.ftg for n in parent.nodes]
        k = b.parent_node               # spans[:k] runs up to the coupler's node
        back = next((f for f in reversed(spans[:k]) if f), 0)
        ahead = next((f for f in spans[k:] if f), 0)
        return first in (back, ahead)

    def branch_style(cp) -> str:
        if cp.style != BRANCH_NORMAL:
            return BRANCH_BRACKETS.get(cp.style, "[]")
        b = design.branch(cp.branch)
        if b is None:
            return "<>"
        return "<>" if mileage(b) == 0 and fed(b) else "[]"

    def walk(branch: Branch, incoming: dict, depth: int, cum_ft: float,
             gutter_open: bool):
        starts[branch.number] = [round(incoming.get(f, 0.0), 2) for f in freqs]
        levels = dict(incoming)
        last_tap = None
        for idx, node in enumerate(branch.nodes):
            last_tap = None
            row = Row(freq_order=freqs, branch=branch.number, node=node.seq or idx + 1,
                      depth=depth, ftg=node.ftg, hc=node.hc, cab=node.cab,
                      lv=node.lv, tsg=node.tsg, amp=node.amp, fixed=node.fixed,
                      power_stop=node.power_stop,
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

            # an in-line device in the amp column (Qn) comes before the taps
            if node.inline:
                q = lib.inline.get(node.inline_part)
                row.amp = f"Q{node.inline}"
                if q:
                    row.amp_name = q.name
                    for f in freqs:
                        loss = q.loss_db(f)
                        levels[f] = levels[f] - loss if _is_forward(p, f) else levels[f] + loss

            # taps: the through loss applies to everything downstream
            for slot in node.taps:
                tap = lib.taps.get(slot.part_id)
                if not tap:
                    continue
                style = TAP_BRACKETS.get(tap.ports, "[]")
                # the Design screen shows the Tap ID, integer part only
                shown = tap.tap_id or int(round(tap.tap_value_db))
                row.taps.append(bracket(f"{shown:>2}", style))
                row.tap_ports.append(tap.ports)
                row.tap_parts.append(
                    f"{tap.name} ({tap.ports} port, {tap.tap_value_db:g} dB)")
                # a tap sees the level after whatever precedes it on the line:
                # the amplifier, an in-line Q device, an earlier tap
                ports = _tap_ports(p, freqs, levels, tap)
                sev, why = _check_tap(p, node.lv, freqs, ports)
                row.tap_severity.append(sev)
                row.tap_levels.append([ports[f] for f in freqs])
                if why:
                    row.tap_notes.append((sev, f"{shown}: {why}"))
                last_tap = (tap, ports)
                if tap.self_terminating:
                    levels = {f: 0.0 for f in freqs}
                    continue
                for f in freqs:
                    thru = tap.through_db(f, reverse=not _is_forward(p, f))
                    levels[f] = levels[f] - thru if _is_forward(p, f) else levels[f] + thru

            scr.rows.append(row)

            # couplers start branches, walked where their coupler sits.
            # The through (low-loss) leg goes downstream unless the node says
            # otherwise -- that is what the "-" and "=" designations mean.
            if node.couplers:
                passive = next((lib.passives.get(c.part_id)
                                for c in node.couplers if c.part_id), None)
                mark = THROUGH_MARK.get(node.through_leg, "")
                # one splitter feeding both branches is drawn in one column,
                # "3-<11><12>"; two separate couplers take a column each
                shared = (len(node.couplers) == 2 and passive is not None
                          and node.couplers[0].part_id == node.couplers[1].part_id
                          and len(passive.port_losses) > 2)
                for i, cp in enumerate(node.couplers):
                    style = branch_style(cp)
                    own = lib.passives.get(cp.part_id) or passive
                    cid = cp.coupler_id or (own.coupler_id if own else 0)
                    text = bracket(str(cp.branch), style)
                    if i == 0 or not shared:
                        row.couplers.append(f"{cid or ''}{mark if i == 0 else ''}{text}")
                    else:
                        row.couplers[0] += text
                    if passive and i == 0:
                        row.coupler_parts.append(
                            f"{passive.name} legs {' / '.join(str(v) for v in passive.port_losses)} dB")

                def leg(which: int, f: float) -> float:
                    """Loss on one output: 0 downstream, then each branch column.

                    The through (low-loss) leg goes downstream unless the node
                    says otherwise -- that is what "-" and "=" mean; every other
                    output takes a tap leg."""
                    if not passive:
                        return 0.0
                    return passive.port_db(0 if which == node.through_leg else 1, f)

                for i, cp in enumerate(node.couplers, start=1):
                    child = design.branch(cp.branch)
                    if not child:
                        continue
                    down = {f: (levels[f] - leg(i, f) if _is_forward(p, f)
                                else levels[f] + leg(i, f)) for f in freqs}
                    own = lib.passives.get(cp.part_id) or passive
                    feeders[child.number] = own.name if own else ""
                    walk(child, down, depth + 1, cum_ft, True)
                for f in freqs:
                    loss = leg(THROUGH_DOWNSTREAM, f)
                    levels[f] = (levels[f] - loss if _is_forward(p, f)
                                 else levels[f] + loss)

        # the line under the last node: what continues through the last tap,
        # and under the tap columns that tap's port output
        end = Row(freq_order=freqs, branch=branch.number, node=len(branch.nodes) + 1,
                  depth=depth, end=True)
        end.levels = dict(levels)
        if last_tap:
            ports = last_tap[1]
            end.port_levels = [ports[f] for f in freqs]
            end.port_severity = [_port_severity(p, branch.nodes[-1].lv, freqs, ports, f)
                                 for f in freqs]
        scr.rows.append(end)

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
    order = []
    for r in scr.rows:
        if r.branch not in order:
            order.append(r.branch)
    scr.branches = [{
        "number": b.number, "parent_branch": b.parent_branch,
        "parent_node": b.parent_node, "style": b.style, "label": b.label,
        "nodes": len(b.nodes),
        "position": order.index(b.number) + 1 if b.number in order else 0,
        "start": starts.get(b.number, []),
        "coupler": feeders.get(b.number, ""),
    } for b in sorted(design.branches.values(), key=lambda x: x.number)]
    _amp_info(design, scr)
    return scr


def _amp_info(design: Design, scr: Screen) -> None:
    """What the info box shows with the cursor on an amplifier.

    Checked on AL004's AL00416: 2027 ft to the node and to the start of the
    network, 1141 ft to the previous active or split (the DC-12 at 4.4),
    cascade position 1, supply A, 120 homes downstream.
    """
    lib = design.library
    rows = {(r.branch, r.node): r for r in scr.rows if not r.end}

    def upstream(b: int, n: int):
        """(branch, node) pairs from this node back to the start, nearest first."""
        while b:
            br = design.branch(b)
            for k in range(n, 0, -1):
                yield b, k
            n, b = br.parent_node, br.parent_branch

    def node(b, n):
        return design.branch(b).nodes[n - 1]

    def aerial(nd) -> bool:
        cable = lib.cables.get(nd.cab_part)
        return (cable.cable_index if cable and cable.cable_index >= 0 else nd.cab % 100) % 2 == 0

    def downstream_homes(b: int, n: int) -> int:
        total, stack = 0, [(b, n)]
        while stack:
            bb, first = stack.pop()
            br = design.branch(bb)
            for nd in br.nodes[first - 1:]:
                total += nd.hc
                stack += [(c.branch, 1) for c in nd.couplers if design.branch(c.branch)]
        return total

    for (b, n), r in rows.items():
        nd = node(b, n)
        if not nd.amp:
            continue
        part = lib.actives.get(nd.amp_part)
        d = dict.fromkeys(("aerial_prev", "aerial_start", "total_split",
                           "total_prev", "total_start"), 0)
        found_active = found_split = False
        cascade = 0
        first = True
        for bb, k in upstream(b, n):
            here = node(bb, k)
            if not first:
                if here.amp and not found_active:
                    found_active = True
                    cascade += 0
                if here.amp:
                    cascade += 1
                if (here.amp or here.couplers) and not found_split:
                    found_split = True
            ft = here.ftg
            d["total_start"] += ft
            d["aerial_start"] += ft if aerial(here) else 0
            if not found_active:
                d["total_prev"] += ft
                d["aerial_prev"] += ft if aerial(here) else 0
            if not found_split:
                d["total_split"] += ft
            first = False
        fibre = part is not None and part.fibre_fed
        pads = (nd.pads + [0, 0, 0, 0])[:4]
        r.amp_info = {
            "name": nd.amp_label, "type": part.name if part else "",
            "fwd_pad": pads[0], "ret_pad": pads[1], "fwd_eq": pads[2], "ret_eq": pads[3],
            **d,
            # the node itself is position 0; each active upstream adds one
            "cascade": 0 if fibre else max(cascade, 1),
            "supply": r.powered_by, "homes_down": downstream_homes(b, n),
        }


def _tap_ports(p, freqs, levels: dict, tap) -> dict:
    """Level at the tap's ports: forward the line level less the tap value,
    return the level the drop must deliver, i.e. the line level plus it."""
    return {f: (levels[f] - tap.tap_db(f)) if _is_forward(p, f) else (levels[f] + tap.tap_db(f))
            for f in freqs}


def _level_row(p, lv: int) -> list:
    rows = p.levels or [[0.0, 0.0, 99.0, 99.0]]
    return rows[lv] if 0 <= lv < len(rows) and any(rows[lv]) else rows[0]


def _port_severity(p, lv: int, freqs, ports: dict, f: float) -> str:
    """Against the System Levels for this node's lv: forward outputs must reach
    the minimum, return inputs stay under the maximum.  Out by less than the
    tap margin is marginal."""
    mins = _level_row(p, lv)
    i = freqs.index(f)
    limit = mins[i] if i < len(mins) else 0.0
    if _is_forward(p, f):
        short = limit - ports[f]
    else:
        short = ports[f] - limit
    if short <= 1e-9:
        return ""
    return "yellow" if short <= p.tap_margin_db else "red"


def _check_tap(p, lv: int, freqs, ports: dict) -> tuple:
    worst, why = "", ""
    for f in freqs:
        sev = _port_severity(p, lv, freqs, ports, f)
        if sev and (not worst or sev == "red"):
            worst = sev
            limit = _level_row(p, lv)[freqs.index(f)]
            side = "below the minimum" if _is_forward(p, f) else "above the maximum"
            why = f"port {ports[f]:.2f} dBmV at {f:g} is {side} {limit:g} (lv {lv})"
    return worst, why


def _gutter(scr: Screen) -> None:
    """The line art down the left edge that shows where branches run."""
    spans: dict = {}
    for i, r in enumerate(scr.rows):
        if r.end:
            continue
        spans.setdefault((r.branch, r.depth), [i, i])[1] = i
    for (branch, depth), (first, last) in spans.items():
        if depth == 0 or first == last:
            continue
        for i in range(first, last + 1):
            ch = "┌" if i == first else ("└" if i == last else "│")
            scr.rows[i].gutter = ch


# --------------------------------------------------------------------------
def _powering(design: Design, scr: Screen) -> None:
    """Voltage and current on every node, the way the Power screen shows them.

    The plant is a tree of spans.  A node's footage and cable are the span
    back to the node before it -- or, for the first node of a branch, back to
    the node carrying its coupler.  A power stop on a node cuts that span.
    Each power supply feeds whatever it can reach without crossing a stop.

    Actives draw the current their power steps give at the voltage they see,
    so the solution is iterated: voltages from the supply outward, currents
    back from the loads.  The drop along a span is its current times its
    resistance: feet times the cable's loop resistance, truncated to whole
    milliohms.

    Shown per node, as checked against the AL004 Power screen:
      volt     the voltage at the node
      current  the current in the span on the supply side of the node --
               everything powered through it
    """
    lib = design.library
    rows = {(r.branch, r.node): r for r in scr.rows}
    nodes = {}
    for b in design.branches.values():
        for i, n in enumerate(b.nodes, start=1):
            nodes[(b.number, n.seq or i)] = n

    # span edges: child key -> (parent key, ohms)
    edges = {}
    for b in design.branches.values():
        prev = (b.parent_branch, b.parent_node) if b.parent_branch else None
        for i, n in enumerate(b.nodes, start=1):
            key = (b.number, n.seq or i)
            if prev is not None and prev in nodes and not n.power_stop:
                cable = lib.cables.get(n.cab_part)
                loop = cable.loop_resistance_ohm_per_1000ft if cable else 0.0
                if loop >= 99.0:           # "never power this" cable
                    prev = key
                    continue
                # A span's resistance is whole milliohms, truncated: feet times
                # the cable file's micro-ohms per foot, integer-divided by 1000
                # (136 ft of 760 uohm/ft is 0.103 ohm, not 0.10336).  With
                # that every volt on AL004's branch 4 Power screen matches;
                # without it the drop runs ~0.5 % high.
                milliohms = int(round(n.ftg)) * int(round(loop * 1000)) // 1000
                edges[key] = (prev, milliohms / 1000.0)
            prev = key
    adj = {k: [] for k in nodes}
    for child, (parent, ohms) in edges.items():
        adj[child].append((parent, ohms, child))
        adj[parent].append((child, ohms, child))

    def draw(key, volts: float) -> float:
        n = nodes[key]
        if n.amp:
            part = lib.actives.get(n.amp_part)
            if part:
                return part.current_at(volts, design.parameters.power_interpolation)
        return 0.0

    seen = set()
    for key, n in nodes.items():
        if not n.supply_volts or key in seen:
            continue
        # the area this supply reaches, as a tree rooted at the supply
        parent, span_ohms, order = {key: None}, {key: 0.0}, [key]
        i = 0
        while i < len(order):
            here = order[i]
            i += 1
            for there, ohms, _ in adj[here]:
                if there not in parent:
                    parent[there] = here
                    span_ohms[there] = ohms
                    order.append(there)
        seen.update(order)
        others = [k for k in order if k != key and nodes[k].supply_volts]
        if others:
            rows[key].flags.append(("red", "bucking power: another supply in this "
                                           "area without a power stop between"))
        volts = {k: n.supply_volts for k in order}
        current = {}
        for _ in range(30):
            current = {k: draw(k, volts[k]) for k in order}
            for k in reversed(order[1:]):
                current[parent[k]] += current[k]
            new = {key: n.supply_volts}
            for k in order[1:]:
                new[k] = new[parent[k]] - current[k] * span_ohms[k]
            done = max(abs(new[k] - volts[k]) for k in order) < 1e-6
            volts = new
            if done:
                break
        sup = lib.power_supplies.get(n.supply_part)
        for k in order:
            r = rows.get(k)
            if r is None:
                continue
            r.volts = volts[k]
            r.current = current[k]
            r.powered_by = n.supply_label
            node = nodes[k]
            if node.amp:
                part = lib.actives.get(node.amp_part)
                if part and volts[k] < part.min_voltage:
                    r.flags.append(("red", f"{volts[k]:.1f} V is below the "
                                           f"{part.min_voltage:.0f} V minimum "
                                           f"for {part.name}"))
        r = rows.get(key)
        if r is not None:
            r.supply = n.supply_volts
            r.supply_label = n.supply_label
            if sup:
                r.supply_type, r.supply_name = sup.type_id, sup.name
            if sup and sup.amps:
                r.supply_pct = round(100 * current[key] / sup.amps)
                if current[key] > sup.amps:
                    r.flags.append(("red", f"excess current draw: {current[key]:.2f} A "
                                           f"on a {sup.amps:g} A supply"))


def _totals(design: Design, scr: Screen) -> None:
    rows = [r for r in scr.rows if not r.end]
    taps = sum(len(r.taps) for r in rows)
    scr.totals = {
        "branches": len(design.branches),
        "nodes": len(rows),
        "taps": taps,
        "actives": sum(1 for r in rows if r.amp),
        "homes": sum(r.hc for r in rows),
        "footage": round(sum(r.ftg for r in rows)),
        "errors": sum(1 for r in rows if r.severity == "red"),
        "warnings": sum(1 for r in rows if r.severity == "yellow"),
    }
