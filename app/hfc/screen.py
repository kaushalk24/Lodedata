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
from decimal import Decimal, ROUND_HALF_UP

from .plant import (Design, Branch, Node, TAP_BRACKETS, BRANCH_BRACKETS, BRANCH_NORMAL,
                    THROUGH_MARK, THROUGH_DOWNSTREAM, bracket)

POWERING_PASSES = 4


def as_shown(v: float) -> float:
    """A level as the screen prints it: to the hundredth, halves up.

    AL004 34.7 shows 21.115 as 21.12 and 37.865 as 37.87 -- round-half-even
    would give 37.86, and the binary 21.115 sits just below the half.  A
    half the arithmetic leaves a hair under goes up too: the older AL004's
    9.17 port at 54 MHz, 3.445 computed as 3.4449999999999985, is 3.45 to
    Lode ("Tap(54) 6.55 below min").
    """
    return float(Decimal(repr(round(v, 9))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def as_tested(v: float) -> float:
    """A port level as the Test reads it: a half added and the rest of the
    hundredths dropped, which takes a level under zero up, not down.  The
    older AL004's 15.4 port at 870 MHz, -4.191, is -4.19 on the screen and
    in its tap box but -4.18 to the Test: "Tap(870) 23.18 below min", and
    at 550 -1.993 gives 16.98, its crossover 3.88 + 4.18 = 8.06 (Lode's list,
    1 and 2 Oct).  At or above zero it is the screen's figure."""
    if v >= 0:
        return as_shown(v)
    return int(Decimal(repr(round(v * 100 + 0.5, 6)))) / 100


@dataclass
class Row:
    branch: int
    node: int
    depth: int = 0              # branch nesting, for the left gutter
    gutter: str = " "           # line art: the branch bracket characters
    # levels at the input to this node, one per design frequency
    levels: dict = field(default_factory=dict)     # MHz -> dBmV
    freq_order: list = field(default_factory=list)  # the column order
    extra_order: list = field(default_factory=list)  # F3: its column after cplr[branch]
    ftg: float = 0.0
    hc: int = 0
    cab: int = 0
    cab_name: str = ""
    # the cable number's colour and the series' name, from the cable file
    cab_color: str = ""
    cab_series: str = ""
    lv: int = 0
    tsg: int = 0
    amp: str = ""
    fixed: bool = False
    amp_name: str = ""
    amp_label: str = ""
    taps: list = field(default_factory=list)       # rendered strings, e.g. "[26]"
    tap_severity: list = field(default_factory=list)  # "", "yellow" or "red" per tap
    # "red" when the homes passed are more than the ports of the line's taps
    # together (3 homes on a 2-port tap, or on no tap); a 4- or 8-port tap
    # takes it back to green (the user, recording 2's 2.2)
    hc_severity: str = ""
    tap_levels: list = field(default_factory=list)    # each tap's port levels, per frequency
    power_stop: bool = False
    end: bool = False           # the line under a branch's last node
    port_levels: list = field(default_factory=list)   # that line: last tap's port output
    port_severity: list = field(default_factory=list)
    tap_notes: list = field(default_factory=list)  # (severity, message) about taps
    slope_notes: list = field(default_factory=list)  # the active's, listed ahead of its taps
    active_notes: list = field(default_factory=list)  # its inputs, outputs and cascade, ahead of those
    level_severity: dict = field(default_factory=dict)  # MHz -> "red": an input or output the active misses
    tap_port_severity: list = field(default_factory=list)  # per tap, per column
    tap_inputs: list = field(default_factory=list)  # level entering each tap slot (not sent)
    after_taps: dict = field(default_factory=dict)  # level after the last tap (not sent)
    out_levels: dict = field(default_factory=dict)  # level carried on to the next node
    tap_ports: list = field(default_factory=list)
    tap_parts: list = field(default_factory=list)  # part numbers, for the panel
    tap_branches: list = field(default_factory=list)  # per tap, the branch its port feeds, 0 = none
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
    block: dict = field(default_factory=dict)      # the expanded display's cyan block
    housing: int = 0            # underground housing number, 0 = none
    note: str = ""              # the line's Notes; Lode marks the line with a yellow ♪
    inline: int = 0             # the in-line device in the amp column, 0 = none
    node_box: bool = False      # a line with no active whose node box has the distances
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
            "levels": [as_shown(self.levels.get(f, 0.0)) for f in self.freq_order],
            # as computed: the preview box prints these (SN001_MID 2.5's
            # 32.055 as 32.05, where the Design screen shows 32.06)
            "raw_levels": [self.levels.get(f, 0.0) for f in self.freq_order],
            "extra_levels": [as_shown(self.levels.get(f, 0.0)) for f in self.extra_order],
            "level_severity": [self.level_severity.get(f, "") for f in self.freq_order],
            "extra_severity": [self.level_severity.get(f, "") for f in self.extra_order],
            # an input or output it misses; not its cascade (23.17's 11 stays green)
            "amp_severity": "red" if self.level_severity else "",
            "inline": self.inline, "node_box": self.node_box,
            "ftg": round(self.ftg, 0), "hc": self.hc, "cab": self.cab,
            "cab_name": self.cab_name, "cab_color": self.cab_color,
            "cab_series": self.cab_series, "lv": self.lv, "tsg": self.tsg,
            "amp": self.amp, "amp_name": self.amp_name, "fixed": self.fixed,
            "amp_label": self.amp_label,
            "taps": self.taps, "tap_ports": self.tap_ports, "couplers": self.couplers,
            "tap_severity": self.tap_severity, "hc_severity": self.hc_severity,
            "end": self.end,
            "tap_port_severity": self.tap_port_severity,
            "out_levels": [as_shown(self.out_levels[f]) for f in self.freq_order]
                          if self.out_levels else [],
            "tap_levels": [[as_shown(v) for v in t] for t in self.tap_levels],
            "power_stop": self.power_stop,
            "port_levels": [as_shown(v) for v in self.port_levels],
            "port_severity": self.port_severity,
            "tap_parts": self.tap_parts, "tap_branches": self.tap_branches,
            "coupler_parts": self.coupler_parts,
            "cumulative_ft": round(self.cumulative_ft, 0),
            "volts": None if self.volts is None else round(self.volts, 2),
            "current": round(self.current, 2),
            "supply": self.supply,
            "supply_label": self.supply_label, "supply_type": self.supply_type,
            "supply_name": self.supply_name, "powered_by": self.powered_by,
            "amp_info": self.amp_info, "block": self.block, "housing": self.housing,
            "note": self.note,
            "supply_pct": self.supply_pct,
            "flags": [{"severity": s, "message": m} for s, m in self.flags + self.tap_notes],
            "severity": self.severity,
        }


@dataclass
class Screen:
    rows: list = field(default_factory=list)
    frequencies: list = field(default_factory=list)   # column order
    extra_frequencies: list = field(default_factory=list)  # F3, drawn after cplr[branch]
    # the level column heads: the frequencies, or with no spec set the
    # program's own "high low Rh Rl"
    labels: list = field(default_factory=list)
    branches: list = field(default_factory=list)      # paging metadata
    problems: list = field(default_factory=list)
    totals: dict = field(default_factory=dict)
    tests: list = field(default_factory=list)         # (severity, message): Test Results

    def as_dict(self) -> dict:
        return {"rows": [r.as_dict() for r in self.rows],
                "frequencies": self.frequencies,
                "extra_frequencies": self.extra_frequencies,
                "labels": self.labels or [f"{f:g}" for f in self.frequencies],
                "branches": self.branches,
                "problems": self.problems, "totals": self.totals,
                "tests": [{"severity": v, "message": m} for v, m in self.tests]}


# The program's own actives table, the one it uses with no spec set (Spec
# Edit > Actives, Unnamed): the Active ID of each index.  The user's
# screenshots: 1-12 the line extenders 11 ... 33H, 13-41 61-89, 42-50 41-49,
# then ###.
_DEFAULT_IDS = (["11", "21", "22", "31", "32", "33", "11H", "21H", "22H", "31H", "32H", "33H"]
                + [str(i) for i in range(61, 90)] + [str(i) for i in range(41, 50)])


def default_active_id(index: int) -> str:
    return _DEFAULT_IDS[index - 1] if 0 < index <= len(_DEFAULT_IDS) else "###"


def _freqs(p) -> list:
    """Column order as the real screen shows it: forward high to return low."""
    return [p.forward_high_mhz, p.forward_low_mhz,
            p.return_high_mhz, p.return_low_mhz]


def _extra_freqs(p) -> list:
    """The third forward frequency when the Parameters have it on: Lode draws
    its column after the two cplr[branch] columns (WVEXT862's 550 on the older
    AL004: 35.20 at 4.1, 19.55 at 44.1, 0.00 on the line under it)."""
    return [p.f3_mhz] if getattr(p, "f3_mhz", 0.0) else []


def _all_freqs(p) -> list:
    """Every frequency the levels are carried at, in the Parameters' order --
    the order the Test list checks a tap's ports in: 870, 54, 550, 40, 5."""
    return [p.forward_high_mhz, p.forward_low_mhz, *_extra_freqs(p),
            p.return_high_mhz, p.return_low_mhz]


def _is_forward(p, mhz: float) -> bool:
    return mhz >= p.forward_low_mhz


# --------------------------------------------------------------------------
def build(design: Design) -> Screen:
    p = design.parameters
    freqs = _freqs(p)
    extra, allf = _extra_freqs(p), _all_freqs(p)
    scr = Screen(frequencies=freqs, extra_frequencies=extra, problems=design.validate())
    lib = design.library
    if not design.has_specs:
        scr.labels = ["high", "low", "Rh", "Rl"]
    if not design.branches:
        return scr

    def cable_loss(node: Node, mhz: float) -> float:
        cable = lib.cables.get(node.cab_part)
        return cable.loss_db(mhz, node.ftg) if cable and node.ftg else 0.0

    starts, feeders = {}, {}      # per branch: levels out of its coupler, coupler name

    # Nothing in the file marks a branch <n> or [n]; the program works it out
    # from the spans.  A branch is drawn <n> when it has no footage, or when
    # its first span is as long as the parent branch's nearest span behind or
    # ahead of the coupler -- the span BkFeed (.2) or FwdFd (..2) copies.
    # The walk to that span takes each line's own span, the coupler's line
    # first going back, and ends at the first line that has one or at a line
    # with a power stop -- but not at the coupler's own line's stop going
    # back: the older AL004's 16.4 is 8<17> (17 runs 169 ft, 16.3's span,
    # past 16.4's stop; set A 5a).  The cable does not matter: its 9.14 is
    # 2<14> on 404, mileage (5b).  All 85 seen fit (AL004, the older AL004,
    # SN001_MID):
    #   AL004 4.4 12<6> starts on 4's 121 behind, 4.14 3-<11><12> on the 99
    #   behind and the 105 ahead, past 4.15's coupler (0 ft); 11.1 made 106
    #   ft turns it 3-[11]<12> (the user, in Lode Data);
    #   AL004 9.1 108[10]: 9.2 (0 ft) holds a power stop before 9.3's 300 --
    #   taken off, Lode Data reads 108<10> (the user's test);
    #   SN001 1.15 63<15> on 1.14's 550, a power stop on the line whose span
    #   it is; 5.3 212[8] and 28.1 102[34] match nothing;
    #   only the parent counts: AL004's 7 runs along 4's 156 from 6.1 (0 ft
    #   at 4.4), yet it is 100[7] -- 6's own span is 121.
    def fed(b: Branch) -> bool:
        first = next((n for n in b.nodes if n.ftg), None)
        if first is None:
            return True
        parent = design.branch(b.parent_branch)
        if parent is None:
            return False

        def nearest(lines, own=None) -> float:
            for n in lines:
                if n.ftg:
                    return n.ftg
                if n.power_stop and n is not own:
                    return 0.0
            return 0.0
        k = b.parent_node               # parent.nodes[:k] runs up to the coupler's line
        behind = list(reversed(parent.nodes[:k]))
        return first.ftg in (nearest(behind, behind[0] if behind else None),
                             nearest(parent.nodes[k:]))

    def branch_style(cp) -> str:
        if cp.style != BRANCH_NORMAL:
            return BRANCH_BRACKETS.get(cp.style, "[]")
        b = design.branch(cp.branch)
        if b is None:
            return "<>"
        return "<>" if fed(b) else "[]"

    def walk(branch: Branch, incoming: dict, depth: int, cum_ft: float,
             gutter_open: bool):
        starts[branch.number] = [as_shown(incoming.get(f, 0.0)) for f in freqs]
        levels = dict(incoming)
        last_tap = None
        for idx, node in enumerate(branch.nodes):
            last_tap = None
            fed_from_taps = []      # (tap, branch, port levels): drawn after this line
            amp = node.amp
            if not amp and node.kept_active and not design.has_specs:
                # no spec set: the Active ID of the program's own (Unnamed)
                # actives table -- AL004's Ripple, index 22, reads 70 and
                # AL00416, index 13, 61 (the user's screenshots)
                amp = default_active_id(node.kept_active)
            row = Row(freq_order=freqs, extra_order=extra, branch=branch.number, node=node.seq or idx + 1,
                      depth=depth, ftg=node.ftg, hc=node.hc, cab=node.cab,
                      lv=node.lv, tsg=node.tsg, amp=amp, fixed=node.fixed,
                      power_stop=node.power_stop,
                      amp_label=node.amp_label, supply=node.supply_volts,
                      note=node.note)
            ports = sum(lib.taps[s.part_id].ports if s.part_id in lib.taps else s.file_ports
                        for s in node.taps)
            if node.hc > ports:
                row.hc_severity = "red"
            cable = lib.cables.get(node.cab_part)
            row.cab_name = cable.name if cable else ""
            # the number in its series' colour, the series named in the info
            # box: the older AL004's 505 red, "EX P3 625 U    Dual New Build"
            # (series 5 of cable 5), 438 red (series 4 of cable 38) where 405
            # and 410 are 0,200,0; SN001's 10 0,200,0 by its 40 at 0,255,0
            if cable and len(cable.series) == 10:
                row.cab_color, row.cab_series = cable.series[node.cab // 100 % 10]
            cum_ft += node.ftg
            row.cumulative_ft = cum_ft

            # the span into this node
            for f in allf:
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
                if part and len(part.pad_eq) == 4:
                    # its Pads/EQs bank has no forward (return) EQ to pick:
                    # SN001_MID's Ripple-2 on 1.1 (bank 4, empty) and the
                    # older AL004's WIFI OMNIs on 43.1 and 44.1 (bank 3, pads
                    # only); AL004's Ripple (bank 4, a row in each) has none
                    at = f"{branch.number}.{row.node}."
                    if not part.pad_eq[2][1]:
                        row.slope_notes.append(("yellow", f"Fslope too low to equalize at {at}"))
                    if not part.pad_eq[3][1]:
                        row.slope_notes.append(("yellow", f"Rslope too low to equalize at {at}"))
                if part:
                    if not part.needs_rf_input:
                        # fibre fed: there is no RF input to show on this line
                        row.levels = {f: 0.0 for f in allf}
                    else:
                        _active_checks(p, part, node.pads, row, f"{branch.number}.{row.node}.")
                    levels[p.forward_high_mhz] = part.out_forward_high
                    levels[p.forward_low_mhz] = part.out_forward_low
                    levels[p.return_high_mhz] = part.in_return_high
                    levels[p.return_low_mhz] = part.in_return_low
                    for f in extra:
                        levels[f] = part.out_f3

            # an in-line device in the amp column (Qn) comes before the taps.
            # The first is the in-line equaliser, drawn "EQ": SN001_MID's
            # Q1 at 5.12, 8.7 and 15.26, while 5.5 reads Q8, 5.6 Q6 and
            # AL004 6.8 Q2 (the manual: "in-line equalisers and Q numbers")
            if node.inline:
                q = lib.inline.get(node.inline_part)
                row.amp = "EQ" if node.inline == 1 else f"Q{node.inline}"
                row.inline = node.inline
                if q:
                    row.amp_name = q.name
                    for f in allf:
                        loss = q.loss_db(f)
                        levels[f] = levels[f] - loss if _is_forward(p, f) else levels[f] + loss

            if not design.has_specs:
                # no spec set: each tap is drawn with ID 0 in its port
                # count's brackets, "[ 0]" "/ 0/" (AL004 4.27 - 4.29), and
                # the line under the branch reads 0.00 below them
                for slot in node.taps:
                    if slot.file_ports:
                        row.taps.append(bracket(f"{0:>2}", TAP_BRACKETS.get(slot.file_ports, "[]")))
                        row.tap_ports.append(slot.file_ports)
                        row.tap_branches.append(slot.branch)
                        last_tap = ("file", {f: 0.0 for f in allf}, [""] * len(freqs))

            # taps: the through loss applies to everything downstream
            for slot in node.taps:
                tap = lib.taps.get(slot.part_id)
                if not tap:
                    continue
                row.tap_inputs.append(dict(levels))
                style = TAP_BRACKETS.get(tap.ports, "[]")
                # the Design screen shows the Tap ID, integer part only
                shown = tap.tap_id or int(round(tap.tap_value_db))
                # a tap feeding a branch from its port: "117+" (the old
                # AL004's 11.16; "104+" at 11.18, a 2-port)
                # The column is four wide: a 3-digit tap loses its opening
                # bracket, "117]" (SN001_MID 5.11, 18.12, 28.11)
                row.taps.append(f"{shown}+" if slot.branch else bracket(f"{shown:>2}", style)[-4:])
                row.tap_ports.append(tap.ports)
                row.tap_parts.append(
                    f"{tap.name} ({tap.ports} port, {tap.tap_value_db:g} dB)")
                row.tap_branches.append(slot.branch)
                # a tap sees the level after whatever precedes it on the line:
                # the amplifier, an in-line Q device, an earlier tap
                ports = _tap_ports(p, allf, levels, tap)
                per_all, errors = _tap_checks(p, node.lv, allf, ports)
                # a tap is drawn in its worst colour, 550 included; each port
                # value under the four level columns in its own
                sev = _worst(per_all)
                per_port = [per_all[allf.index(f)] for f in freqs]
                row.tap_severity.append(sev)
                row.tap_levels.append([ports[f] for f in freqs])
                row.tap_port_severity.append(per_port)
                for e_sev, e_msg in errors:
                    row.tap_notes.append((e_sev, f"{e_msg} at {branch.number}.{row.node}."))
                last_tap = (tap, ports, per_port)
                if slot.branch and design.branch(slot.branch):
                    fed_from_taps.append((tap, design.branch(slot.branch), dict(ports)))
                if tap.self_terminating:
                    levels = {f: 0.0 for f in allf}
                    continue
                for f in allf:
                    thru = tap.through_db(f, reverse=not _is_forward(p, f))
                    levels[f] = levels[f] - thru if _is_forward(p, f) else levels[f] + thru

            row.after_taps = dict(levels)
            scr.rows.append(row)

            # a tap the spec set cannot name (or no spec set) still has its
            # branch, drawn from 0.00 as the rest of such a screen is
            walked = {child.number for _, child, _ in fed_from_taps}
            for slot in node.taps:
                child = design.branch(slot.branch) if slot.branch else None
                if child is not None and child.number not in walked:
                    fed_from_taps.append((None, child, {f: 0.0 for f in allf}))
            for tap, child, ports in fed_from_taps:
                feeders[child.number] = tap.name if tap else ""
                walk(child, ports, depth + 1, cum_ft, True)

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
                    if cp.removed:
                        # its coupler taken off with "0", the branch kept: "- [55]"
                        row.couplers.append(f"- {bracket(str(cp.branch), style)}")
                        continue
                    own = lib.passives.get(cp.part_id) or passive
                    cid = cp.coupler_id or (own.coupler_id if own else 0)
                    text = bracket(str(cp.branch), style)
                    # with no spec set the program shows every coupler's ID
                    # as 0: AL004's 1.2 - 1.5 read 0<2> 0[3] 0[4] 0[5]
                    shown = cid or ("0" if not design.has_specs else "")
                    if i == 0 or not shared:
                        row.couplers.append(f"{shown}{mark if i == 0 else ''}{text}")
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
                                else levels[f] + leg(i, f)) for f in allf}
                    if cp.removed:
                        # nothing feeds it: it starts at 0.00 (AL002 55.1,
                        # the user's recording: 112 ft of cable 0 below it
                        # reads -2.42 -0.60 0.52 0.18)
                        down = {f: 0.0 for f in allf}
                    own = lib.passives.get(cp.part_id) or passive
                    feeders[child.number] = own.name if own else ""
                    walk(child, down, depth + 1, cum_ft, True)
                for f in allf:
                    loss = leg(THROUGH_DOWNSTREAM, f)
                    levels[f] = (levels[f] - loss if _is_forward(p, f)
                                 else levels[f] + loss)
            row.out_levels = dict(levels)

        # the line under the last node: what continues through the last tap,
        # and under the tap columns that tap's port output
        end = Row(freq_order=freqs, extra_order=extra, branch=branch.number, node=len(branch.nodes) + 1,
                  depth=depth, end=True)
        end.levels = dict(levels)
        if last_tap:
            _, ports, per_port = last_tap
            end.port_levels = [ports[f] for f in freqs]
            end.port_severity = list(per_port)
        scr.rows.append(end)

    feeder = design.branches.get(1)
    if feeder:
        start = {}
        hi, lo = p.forward_high_mhz, p.forward_low_mhz
        start[hi] = design.source_dbmv
        start[lo] = design.source_dbmv - design.source_tilt_db
        start[p.return_high_mhz] = p.return_target_at_node_dbmv
        start[p.return_low_mhz] = p.return_target_at_node_dbmv
        if not design.has_specs:
            # nothing to compute from: the program shows 0.00 throughout
            start = {f: 0.0 for f in freqs}
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
    _housings(design, scr)
    # the Test Results list runs in branch, then node order
    for r in sorted((r for r in scr.rows if not r.end), key=lambda r: (r.branch, r.node)):
        scr.tests.extend(r.active_notes + r.slope_notes + r.tap_notes)
    return scr


def _active_checks(p, part, pads, row: Row, at: str) -> None:
    """Lode's Test of an active's levels, with the pads and EQs it holds.

    Forward, the line's input less the forward pad and the EQ's loss must
    reach the active's In at each frequency ("870 input 10.97 to LE at
    4.13.": AL00416 holds pad 0, EQ 15 -- 0.00 at 870, 13.50 at 54 -- and
    In is 11.50 / 11.70).  Return, its Out less the return pad and EQ must
    reach the level the line needs there ("40 output 36.64 from LE at
    25.3.": 39 less pad 8 is 31.00).  All 12 such lines of the older AL004
    and none on AL004 or SN001_MID; the levels are compared as shown, the
    failing ones drawn red.  "LE" is Lode's word for any active here (4.13
    is a bridger).
    """
    def loss(c: int, i: int) -> float:
        column = part.pad_eq[c] if len(part.pad_eq) == 4 else None
        v = pads[c] if c < len(pads) else 0
        if not column or v == 255 or v >= len(column[2]):
            return 0.0
        values = column[2][v]
        return values[i] if i < len(values) else 0.0

    forward = [(p.forward_high_mhz, part.in_forward_high, 0),
               (p.forward_low_mhz, part.in_forward_low, 1)]
    forward += [(f, part.in_f3, 2) for f in _extra_freqs(p)]
    for f, need, i in forward:
        have = as_shown(row.levels.get(f, 0.0))
        if need - (have - loss(0, 0) - loss(2, i)) > 0.005:
            row.level_severity[f] = "red"
            row.active_notes.append(("red", f"{f:g} input {have:7.2f} to LE at {at}"))
    for f, out, i in ((p.return_high_mhz, part.out_return_high, 0),
                      (p.return_low_mhz, part.out_return_low, 1)):
        needed = as_shown(row.levels.get(f, 0.0))
        if needed - (out - loss(1, 0) - loss(3, i)) > 0.005:
            row.level_severity[f] = "red"
            row.active_notes.append(("red", f"{f:g} output {needed:7.2f} from LE at {at}"))


def _active_kind(part) -> str:
    """Amplifier or line extender, as the program counts them.

    Nothing in an active's record says which it is: the program goes by its
    place in the Actives table.  Items 1-12 are the line extenders (its own
    table gives them the LE IDs 11 ... 33H); everything after is an
    amplifier.  The user placed WV750's item 40, "FML1G7J ALC LE", on AL004
    4.2: the expanded display counted it an amplifier, 1-0-0.  A fibre-fed
    node counts as neither there.  (A library not read from a spec set has
    no items; its parts go by name.)
    """
    if part is None:
        return ""
    if part.index > 0:
        if part.index <= 12:
            return "line_extender"
        return "" if part.fibre_fed else "amplifier"
    name = part.name.upper()
    if "BRIDGER" in name:
        return "amplifier"
    if name.startswith("LE") or " LE" in name:
        return "line_extender"
    return ""


def choose_pads_eqs(part, levels: dict, p) -> list:
    """The pads and EQs the program picks for an active, as stored values:
    forward pad, return pad, forward EQ, return EQ.

    The EQ is the bank row whose tilt is nearest the one needed -- forward,
    the active's In tilt less the tilt arriving; return, the tilt the level
    needed here asks for.  The pad is then the largest that still leaves,
    after it and the EQ's loss, the input at the active's In levels
    (forward) and its Out at the levels needed here (return), at both
    frequencies.  Reproduces all 27 amplifiers of AL004, 108 values.
    """
    (_, _, fpad), (_, _, rpad), (_, _, feq), (_, _, req) = [
        (c + [[], [], []])[:3] for c in part.pad_eq]
    hi, lo = levels[p.forward_high_mhz], levels[p.forward_low_mhz]
    rh, rl = levels[p.return_high_mhz], levels[p.return_low_mhz]
    slack = 1e-9

    def nearest(eqs, tilt):
        return min(range(len(eqs)), key=lambda v: abs((eqs[v][1] - eqs[v][0]) - tilt), default=0)

    def largest(pads, fits):
        return max((v for v in range(len(pads)) if fits(pads[v][0])), default=0)

    fe = nearest(feq, (part.in_forward_high - part.in_forward_low) - (hi - lo))
    re_ = nearest(req, rh - rl)
    f_loss = feq[fe] if feq else [0.0, 0.0]
    r_loss = req[re_] if req else [0.0, 0.0]
    fp = largest(fpad, lambda db: hi - db - f_loss[0] >= part.in_forward_high - slack
                 and lo - db - f_loss[1] >= part.in_forward_low - slack)
    rp = largest(rpad, lambda db: part.out_return_high - db - r_loss[0] >= rh - slack
                 and part.out_return_low - db - r_loss[1] >= rl - slack)
    return [fp, rp, fe, re_]


def _amp_info(design: Design, scr: Screen) -> None:
    """What the info box shows with the cursor on an amplifier, and the cyan
    block the expanded display (`/`) draws under a node.

    Checked on AL004's AL00416: 2027 ft to the node and to the start of the
    network, 1141 ft to the previous active or split (the DC-12 at 4.4),
    cascade position 1, supply A, 120 homes downstream.  The block, on 6.9,
    4.24-4.26 and 22.1-22.5, every figure: the same five distances, cable
    loss at the first design frequency over three of them, bridgers and
    line extenders from the start down to the node and from the node on
    (itself included both ways), homes from the node on, and footage on
    the node's own cable back to the previous active or split.
    """
    lib = design.library
    rows = {(r.branch, r.node): r for r in scr.rows if not r.end}
    mhz = scr.frequencies[0] if scr.frequencies else 0.0

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

    def loss(nd) -> float:
        cable = lib.cables.get(nd.cab_part)
        return cable.loss_db(mhz, nd.ftg) if cable and nd.ftg else 0.0

    def has_amp(nd) -> bool:
        # with no spec set an active is still there, by its index
        return bool(nd.amp or nd.kept_active)

    def kinds(nodes) -> list:
        found = [_active_kind(lib.actives.get(nd.amp_part)) for nd in nodes if nd.amp]
        # the third count is 0 on every node seen so far; what it counts is not known
        return [found.count("amplifier"), found.count("line_extender"), 0]

    def downstream(b: int, n: int) -> list:
        out, stack = [], [(b, n)]
        while stack:
            bb, first = stack.pop()
            for nd in design.branch(bb).nodes[first - 1:]:
                out.append(nd)
                stack += [(c.branch, 1) for c in nd.couplers + nd.taps
                          if c.branch and design.branch(c.branch)]
        return out

    def splits(nd) -> bool:
        # a coupler, or a tap feeding a branch from its port: the old AL004's
        # 44.1 is 6 ft from its split, the tap at 11.18 (Lode's info box)
        return bool(nd.couplers or any(t.branch for t in nd.taps))

    def cascading(nd) -> int:
        part = lib.actives.get(nd.amp_part)
        return part.cascading if part else 0

    def counted(nd) -> bool:
        # Custom Cascading's Exclude: WV750's and SHINSTON's Ripple nodes
        return not cascading(nd) >> 1 & 1

    def children(nd) -> list:
        return [c.branch for c in nd.couplers + nd.taps
                if c.branch and not getattr(c, "removed", False) and design.branch(c.branch)]

    def chain_from(bb: int, first: int) -> int:
        """the most actives one after another from line `first` of a branch on"""
        nodes = design.branch(bb).nodes
        best = run = 0
        for k in range(first, len(nodes) + 1):
            here = nodes[k - 1]
            run += 1 if has_amp(here) else 0
            best = max([best] + [run + chain_from(c, 1) for c in children(here)])
        return max(best, run)

    def chain_below(bb: int, k: int) -> int:
        # branches off the active's own line leave after it
        return max([chain_from(bb, k + 1)] + [chain_from(c, 1) for c in children(node(bb, k))])

    for (b, n), r in rows.items():
        nd = node(b, n)
        last = n == len(design.branch(b).nodes)
        # a branch's first node shows it at 22.1 (0 ft); whether that is for
        # being first or for the 0 ft is not yet known, so only both
        block = bool(has_amp(nd) or splits(nd) or last or (n == 1 and not nd.ftg))
        if not (has_amp(nd) or block):
            continue
        d = dict.fromkeys(("aerial_prev", "aerial_start", "total_split",
                           "total_prev", "total_start"), 0)
        lost = dict.fromkeys(("split", "prev", "start"), 0.0)
        same_cable = 0
        found_active = found_split = False
        first = True
        for bb, k in upstream(b, n):
            here = node(bb, k)
            if not first:
                if has_amp(here):
                    found_active = True
                if has_amp(here) or splits(here):
                    found_split = True
            ft, db = here.ftg, loss(here)
            d["total_start"] += ft
            d["aerial_start"] += ft if aerial(here) else 0
            lost["start"] += db
            if not found_active:
                d["total_prev"] += ft
                d["aerial_prev"] += ft if aerial(here) else 0
                lost["prev"] += db
            if not found_split:
                d["total_split"] += ft
                lost["split"] += db
                # the cable, not the code: 22.2's 505 counts for 22.3's 405
                same_cable += ft if here.cab_part == nd.cab_part else 0
            first = False
        below = downstream(b, n)
        homes = sum(x.hc for x in below)
        # the node box lists the distances and homes wherever the block is
        # drawn: a coupler line (SN001_MID's 1.2: all 0, 227 homes; AL004's
        # 9.1), a branch's last line (28.16: 739 9856 739 739 9856, 2 homes)
        # and its 0-ft first line (4.1), not 8.1 (334 ft, bare)
        r.node_box = block
        if block:
            r.block = {
                "distances": [d[k] for k in ("aerial_prev", "aerial_start", "total_split",
                                             "total_prev", "total_start")],
                "losses": [as_shown(lost["split"]), as_shown(lost["prev"]), as_shown(lost["start"])],
                "above": kinds(node(bb, k) for bb, k in upstream(b, n)),
                "below": kinds(below),
                "homes": homes, "same_cable": same_cable,
            }
        if not has_amp(nd):
            continue
        part = lib.actives.get(nd.amp_part)
        fibre = part is not None and part.fibre_fed
        # the stored values index the active's Pads/EQs Banks: the info box
        # shows the label, the expanded display the prefix and label
        # (AL00416: forward EQ 16 -> "12", SEQ-750-12)
        # an active just placed holds 0 in all four: the program does not pick
        # them then (88 on AL004 4.2: NPB-0, SEQ-750-SCS6, NPB-0, MEQ-42-0)
        stored = list(nd.pads[:4])
        shown_as = []
        for c, v in enumerate((stored + [0, 0, 0, 0])[:4]):
            column = part.pad_eq[c] if part and len(part.pad_eq) == 4 else ["", []]
            prefix, labels = column[:2]
            # 255 is row 0, "VOID" (the older AL004's WIFI OMNIs, both EQs)
            if v == 255 and len(column) > 3 and column[3]:
                label = column[3]
            elif part and len(part.pad_eq) == 4 and not labels:
                # the bank has nothing in that column: Lode leaves it blank
                # (SN001's Ripple-2 on 1.1, bank 4, Forward and Return Pad)
                label = ""
            else:
                label = labels[v].strip() if 0 <= v < len(labels) else str(v)
            shown_as.append((label, prefix + label))
        (fp, fp_part), (rp, rp_part), (fe, fe_part), (re_, re_part) = shown_as
        # Cascade Position: the actives from the network's start down to this
        # one, itself included, but those Custom Cascading excludes: WV750's
        # and SHINSTON's Ripple nodes (Exclude) are 0 and the first amplifier
        # after one is 1; WVEXT862's NC4000 and HLN 3842 NODE (Include) are 1,
        # so AL00416 reads 2 there, 1 on AL004.  An excluded fibre-fed node
        # reads 0 wherever it is
        chain = [node(bb, k) for bb, k in upstream(b, n) if has_amp(node(bb, k))][::-1]
        position = sum(counted(x) for x in chain)
        if fibre and not counted(nd):
            position = 0
        if cascading(nd) & 1 and position and not cascading(nd) >> (position + 1) & 1:
            # Cust. Casc. Yes and Casc. <position> Invalid: 23.17's "11"
            # (Casc. 1-5) at 6, "LE  11/5 before/0 after at 23.17."
            r.active_notes.append(("red", f"LE {r.amp:>3}/{len(chain) - 1} before/"
                                          f"{chain_below(b, n)} after at {b}.{n}."))
        if not design.has_specs:
            # no spec set: no type, no pads or EQs, cascade position 0
            # (AL004's AL00416, the user's screenshot)
            fp = rp = fe = re_ = ""
            position = 0
        r.amp_info = {
            "name": nd.amp_label, "type": part.name if part else "",
            "fwd_pad": fp, "ret_pad": rp, "fwd_eq": fe, "ret_eq": re_,
            "parts": [fp_part, rp_part, fe_part, re_part],
            **d,
            "cascade": position,
            "supply": r.powered_by, "homes_down": homes,
        }


def _housings(design: Design, scr: Screen) -> None:
    """The white (n) the expanded display puts under an underground node's
    number: the Underground Housings size the equipment there needs.

    Nodes 0 ft apart are one location.  Its points -- Parameters: amplifier,
    line extender, tap, 8-port tap, coupler, power supply -- pick the largest
    housing whose Minimum Size they reach, shown on the location's first
    node.  AL004: (3) at 22.3 (LE 11 + 22.4's coupler 5 = 16, TV-104 from
    11), (1) at 22.5, 34.8 and 34.9 (a tap, 5 -- TV-60 from 4; "the smallest
    that holds them" would make these a 2); none on aerial cable.
    """
    p = design.parameters
    pts, sizes = p.equipment_points, p.housings
    if not pts or not sizes:
        return
    lib = design.library
    rows = {(r.branch, r.node): r for r in scr.rows if not r.end}

    def points(nd) -> int:
        n = 0
        if nd.amp:
            kind = _active_kind(lib.actives.get(nd.amp_part))
            n += pts["line_extender"] if kind == "line_extender" else pts["amplifier"]
        n += sum(pts["tap_8_port"] if t.ports == 8 else pts["tap"] for t in nd.taps if t.part_id)
        n += pts["coupler"] * len(nd.couplers)
        n += pts["power_supply"] if nd.supply_volts else 0
        return n

    for branch in design.branches.values():
        groups = []
        for k, nd in enumerate(branch.nodes, start=1):
            if k == 1 or nd.ftg:
                groups.append([])
            groups[-1].append((k, nd))
        for group in groups:
            k, first = group[0]
            cable = lib.cables.get(first.cab_part)
            index = cable.cable_index if cable and cable.cable_index >= 0 else first.cab % 100
            if index % 2 == 0:
                continue
            total = sum(points(nd) for _, nd in group)
            fits = [number for number, least in sizes if total and least <= total]
            if fits and (branch.number, k) in rows:
                rows[(branch.number, k)].housing = fits[-1]


def _tap_ports(p, freqs, levels: dict, tap) -> dict:
    """Level at the tap's ports: forward the line level less the tap value,
    return the level the drop must deliver, i.e. the line level plus it."""
    return {f: (levels[f] - tap.tap_db(f)) if _is_forward(p, f) else (levels[f] + tap.tap_db(f))
            for f in freqs}


def _limits(p, lv: int) -> tuple:
    """System Levels for the node's lv and the tap windows, by frequency.
    F3's Min is a column of its own on the System Levels tab (WVEXT862: 15
    on level 0, 18 on level 1), its window in the frequency table (12)."""
    rows = p.levels or [[0.0, 0.0, 99.0, 99.0]]
    k = lv if 0 <= lv < len(rows) and any(rows[lv]) else 0
    four = _freqs(p)
    lim = dict(zip(four, rows[k]))
    windows = dict(zip(four, getattr(p, "tap_windows", None) or []))
    for f in _extra_freqs(p):
        lim[f] = p.f3_levels[k] if k < len(p.f3_levels) else 0.0
        windows[f] = p.f3_tap_window
    return lim, windows


def _worst(severities) -> str:
    return "red" if "red" in severities else ("yellow" if "yellow" in severities else "")


def _tap_checks(p, lv: int, freqs, ports: dict) -> tuple:
    """Lode Data's tap test, as its Test Results window words it.  Checked
    against all 37 lines of AL004's list:

      Tap(750) 6.16 below min   a forward port under the System Levels minimum
                                for the node's lv (a return port over the
                                maximum is "above max"): yellow within the tap
                                margin, red beyond it
      Tap(54) 0.82 over window  a forward port above its minimum plus the tap
                                window (Parameters, System Levels): yellow
      Tap(5) 0.29 below window  a return port below its maximum less the tap
                                window: yellow
      Crossover of 3.18         the forward low port above the forward high by
                                more than Max. Crossover: yellow, on both

    Levels are compared as shown, to the hundredth (16.63 - 12.84 is a 3.79
    crossover at 3.5, not the 3.80 the unrounded levels give).  With the 5 MHz
    return window at 15.50 and Max. Crossover at 3.50 the program adds
    "Tap(5) 0.29 below window at 3.6" and drops the 3.18, 3.34 and 3.40
    crossovers: both are the Parameters settings.  Returns the
    colour of each column's port value and the messages, in the list's order.
    """
    lim, windows = _limits(p, lv)
    seen = {f: as_tested(ports[f]) for f in freqs}
    per = [""] * len(freqs)
    errors = []

    def mark(i, sev):
        if sev == "red" or not per[i]:
            per[i] = sev

    for i, f in enumerate(freqs):
        limit = lim.get(f, 0.0)
        out = limit - seen[f] if _is_forward(p, f) else seen[f] - limit
        if out > 0.005:
            sev = "red" if out > p.tap_margin_db + 0.005 else "yellow"
            mark(i, sev)
            side = "below min" if _is_forward(p, f) else "above max"
            errors.append((sev, f"Tap({f:g}) {out:5.2f} {side}"))
    for i, f in enumerate(freqs):
        if not windows.get(f):
            continue
        if _is_forward(p, f):
            out, side = seen[f] - (lim[f] + windows[f]), "over window"
        else:
            out, side = (lim[f] - windows[f]) - seen[f], "below window"
        if out > 0.005:
            mark(i, "yellow")
            errors.append(("yellow", f"Tap({f:g}) {out:5.2f} {side}"))
    # Max. Crossover 0.00 is a limit like any other: WVEXT862 holds 0 and
    # Lode lists all five crossovers of the older AL004 (2.01 at 5.29 up)
    hi, lo = freqs.index(p.forward_high_mhz), freqs.index(p.forward_low_mhz)
    cross = seen[freqs[lo]] - seen[freqs[hi]]
    if cross > p.max_crossover_db + 0.005:
        mark(hi, "yellow")
        mark(lo, "yellow")
        errors.append(("yellow", f"Crossover of {cross:5.2f}"))
    return per, errors


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
        # a supply the spec set cannot name still has its area (AL004 with
        # no spec set: AL00416's box says Power Supply A)
        if not (n.supply_volts or n.supply_label) or key in seen:
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
        others = [k for k in order if k != key and (nodes[k].supply_volts or nodes[k].supply_label)]
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


def tap_candidates(design: Design, branch: int, node: int, slot: int) -> dict:
    """Every tap in the spec set, tested as if placed in this slot -- what the
    Select Tap window colours (AL004 6.8: /11/ [11] / 8/ [ 8] green, / 4/ and
    the LEQ pads yellow).  The slot's input is the level after whatever
    precedes it on the line.  The window colours by the level checks only:
    [11] and / 8/ are crossed over there (3.08, 3.18) yet shown green."""
    scr = build(design)
    p = design.parameters
    freqs = _all_freqs(p)
    row = next((r for r in scr.rows if (r.branch, r.node) == (branch, node) and not r.end), None)
    if row is None:
        return {"candidates": [], "current": None}
    levels = row.tap_inputs[slot] if slot < len(row.tap_inputs) else row.after_taps
    b = design.branch(branch)
    current = b.nodes[node - 1].taps[slot].part_id \
        if b and slot < len(b.nodes[node - 1].taps) else None
    out = []
    for tap in sorted(design.library.taps.values(), key=lambda t: (t.row, t.ports)):
        ports = _tap_ports(p, freqs, levels, tap)
        _, errors = _tap_checks(p, row.lv, freqs, ports)
        sev = _worst([v for v, m in errors if not m.startswith("Crossover")])
        out.append({"id": tap.id, "row": tap.row, "ports": tap.ports,
                    "tap_id": tap.tap_id, "name": tap.name, "severity": sev})
    return {"candidates": out, "current": current}

