"""Signal level, return path and powering calculations.

The distribution plant below a node is a tree, so everything here is a walk
over that tree.  Forward levels accumulate downstream from the source; return
levels accumulate upstream from each tap port; powering accumulates current
upstream to the supply and voltage downstream from it.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict

from .model import Network, Element, DesignParameters


@dataclass
class Levels:
    """A signal level pair: the two design frequencies."""
    low: float = 0.0
    high: float = 0.0

    @property
    def tilt(self) -> float:
        return self.high - self.low

    def minus(self, low_db: float, high_db: float) -> "Levels":
        return Levels(self.low - low_db, self.high - high_db)

    def as_dict(self) -> dict:
        return {"low": round(self.low, 2), "high": round(self.high, 2),
                "tilt": round(self.tilt, 2)}


@dataclass
class ElementResult:
    element_id: str
    label: str
    type: str
    depth: int = 0
    parent_id: str | None = None
    # forward
    span_loss_low: float = 0.0
    span_loss_high: float = 0.0
    input: Levels = field(default_factory=Levels)
    output: Levels = field(default_factory=Levels)
    tap_port: Levels | None = None
    gain_high: float | None = None
    # geometry / counts
    cable_name: str = ""
    length_ft: float = 0.0
    cumulative_ft: float = 0.0
    houses: int = 0
    # return
    return_at_node: Levels | None = None
    # powering
    volts: float | None = None
    current_a: float = 0.0
    segment_current_a: float = 0.0
    # checks
    warnings: list = field(default_factory=list)

    def as_dict(self) -> dict:
        d = asdict(self)
        for k in ("input", "output", "tap_port", "return_at_node"):
            v = getattr(self, k)
            d[k] = v.as_dict() if isinstance(v, Levels) else None
        for k in ("span_loss_low", "span_loss_high", "length_ft", "cumulative_ft"):
            d[k] = round(d[k], 2)
        if self.gain_high is not None:
            d["gain_high"] = round(self.gain_high, 2)
        if self.volts is not None:
            d["volts"] = round(self.volts, 1)
        d["current_a"] = round(self.current_a, 2)
        d["segment_current_a"] = round(self.segment_current_a, 2)
        return d


@dataclass
class Results:
    rows: dict = field(default_factory=dict)          # element_id -> ElementResult
    order: list = field(default_factory=list)         # element ids, tree order
    problems: list = field(default_factory=list)
    totals: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "order": self.order,
            "rows": {k: v.as_dict() for k, v in self.rows.items()},
            "problems": self.problems,
            "totals": self.totals,
        }


# --------------------------------------------------------------------------
# per-element behaviour
# --------------------------------------------------------------------------
def _span_loss(net: Network, el: Element, mhz: float) -> float:
    if not el.cable_id or not el.length_ft:
        return 0.0
    cable = net.library.cables.get(el.cable_id)
    if not cable:
        return 0.0
    return cable.loss_db(mhz, el.length_ft)


def _device_loss(net: Network, el: Element, mhz: float, port: int,
                 reverse: bool = False) -> float:
    """Insertion loss seen by a signal passing *through* this element to `port`."""
    if el.type == "tap":
        tap = net.library.taps.get(el.part_id)
        return tap.through_db(mhz, reverse) if tap else 0.0
    if el.type in ("splitter", "power_inserter"):
        p = net.library.passives.get(el.part_id)
        return p.port_db(port) if p else 0.0
    return 0.0


def _tap_port_loss(net: Network, el: Element, mhz: float) -> float:
    tap = net.library.taps.get(el.part_id)
    return tap.tap_db(mhz) if tap else 0.0


# --------------------------------------------------------------------------
# forward
# --------------------------------------------------------------------------
def _forward(net: Network, res: Results) -> None:
    p = net.parameters
    f_lo, f_hi = p.forward_freqs

    def walk(el: Element, incoming: Levels | None, depth: int, cum_ft: float):
        row = ElementResult(element_id=el.id, label=el.label or el.id,
                            type=el.type, depth=depth, parent_id=el.parent_id,
                            houses=el.houses, length_ft=el.length_ft)
        cable = net.library.cables.get(el.cable_id) if el.cable_id else None
        row.cable_name = cable.name if cable else ""
        row.span_loss_low = _span_loss(net, el, f_lo)
        row.span_loss_high = _span_loss(net, el, f_hi)
        cum_ft += el.length_ft
        row.cumulative_ft = cum_ft

        if el.type == "node" or incoming is None:
            hi = el.source_dbmv if el.source_dbmv is not None else 48.0
            tilt = el.source_tilt_db if el.source_tilt_db is not None else 9.0
            row.input = Levels(hi - tilt, hi)
            row.output = Levels(hi - tilt, hi)
        else:
            row.input = incoming.minus(row.span_loss_low, row.span_loss_high)
            if el.type == "amplifier":
                part = net.library.actives.get(el.part_id)
                hi = el.output_dbmv
                if hi is None:
                    hi = part.forward_default_output_dbmv if part else 48.0
                tilt = el.tilt_db
                if tilt is None:
                    tilt = part.forward_default_tilt_db if part else 9.0
                row.output = Levels(hi - tilt, hi)
                row.gain_high = row.output.high - row.input.high
                if part and row.gain_high > part.forward_max_gain_db + 0.01:
                    row.warnings.append(
                        f"needs {row.gain_high:.1f} dB but {part.name} tops out at "
                        f"{part.forward_max_gain_db:.1f} dB")
                if row.input.high < p.min_amp_input_dbmv:
                    row.warnings.append(
                        f"input {row.input.high:.1f} dBmV is below the "
                        f"{p.min_amp_input_dbmv:.1f} dBmV minimum")
            else:
                row.output = row.input

            if el.type == "tap":
                tl = _tap_port_loss(net, el, f_hi)
                row.tap_port = Levels(row.input.low - _tap_port_loss(net, el, f_lo),
                                      row.input.high - tl)
                if row.tap_port.high > p.max_tap_port_dbmv:
                    row.warnings.append(
                        f"tap port {row.tap_port.high:.1f} dBmV is above the "
                        f"{p.max_tap_port_dbmv:.1f} dBmV maximum")
                elif row.tap_port.high < p.min_tap_port_dbmv:
                    row.warnings.append(
                        f"tap port {row.tap_port.high:.1f} dBmV is below the "
                        f"{p.min_tap_port_dbmv:.1f} dBmV minimum")

        res.rows[el.id] = row
        res.order.append(el.id)

        for child in net.children(el.id):
            out = Levels(
                row.output.low - _device_loss(net, el, f_lo, child.parent_port),
                row.output.high - _device_loss(net, el, f_hi, child.parent_port),
            )
            walk(child, out, depth + 1, cum_ft)

    for root in net.roots():
        walk(root, None, 0, 0.0)


# --------------------------------------------------------------------------
# return path
# --------------------------------------------------------------------------
def _return(net: Network, res: Results) -> None:
    """Upstream level arriving at the node from each element's tap port.

    Walks down accumulating loss, so every row knows what a CPE transmitting at
    the configured level would land at the node with.
    """
    p = net.parameters
    r_lo, r_hi = p.return_freqs
    tx = p.return_transmit_dbmv

    def walk(el: Element, loss_lo: float, loss_hi: float):
        row = res.rows.get(el.id)
        loss_lo += _span_loss(net, el, r_lo)
        loss_hi += _span_loss(net, el, r_hi)

        if el.type == "amplifier":
            part = net.library.actives.get(el.part_id)
            gain = part.return_max_gain_db if part else 0.0
            loss_lo -= gain
            loss_hi -= gain

        if row is not None and el.type == "tap":
            port_lo = _tap_port_loss(net, el, r_lo)
            port_hi = _tap_port_loss(net, el, r_hi)
            row.return_at_node = Levels(tx - loss_lo - port_lo, tx - loss_hi - port_hi)

        for child in net.children(el.id):
            walk(child,
                 loss_lo + _device_loss(net, el, r_lo, child.parent_port, reverse=True),
                 loss_hi + _device_loss(net, el, r_hi, child.parent_port, reverse=True))

    for root in net.roots():
        walk(root, 0.0, 0.0)


# --------------------------------------------------------------------------
# powering
# --------------------------------------------------------------------------
def _element_current(net: Network, el: Element) -> float:
    if el.type == "amplifier":
        part = net.library.actives.get(el.part_id)
        return part.current_draw_a if part else 0.0
    if el.type == "tap":
        part = net.library.taps.get(el.part_id)
        return part.current_draw_a if part else 0.0
    return 0.0


def _blocks_power(net: Network, el: Element, port: int) -> bool:
    if el.type == "tap":
        part = net.library.taps.get(el.part_id)
        return not (part.power_passing if part else True)
    if el.type in ("splitter", "power_inserter"):
        part = net.library.passives.get(el.part_id)
        return not (part.port_powers(port) if part else True)
    return False


def _powering(net: Network, res: Results) -> None:
    p = net.parameters

    def accumulate(el: Element) -> float:
        """Total current drawn by this element and everything it powers."""
        total = _element_current(net, el)
        for child in net.children(el.id):
            if _blocks_power(net, el, child.parent_port):
                continue
            total += accumulate(child)
        row = res.rows.get(el.id)
        if row is not None:
            row.current_a = _element_current(net, el)
            row.segment_current_a = total
        return total

    def distribute(el: Element, volts: float):
        row = res.rows.get(el.id)
        if row is None:
            return
        if el.length_ft and el.cable_id:
            cable = net.library.cables.get(el.cable_id)
            if cable:
                volts -= row.segment_current_a * cable.resistance_ohms(el.length_ft)
        row.volts = volts
        if volts < p.min_device_volts and _element_current(net, el) > 0:
            row.warnings.append(
                f"{volts:.0f} V at the device is under the "
                f"{p.min_device_volts:.0f} V minimum")
        for child in net.children(el.id):
            if _blocks_power(net, el, child.parent_port):
                continue
            distribute(child, volts)

    for root in net.roots():
        accumulate(root)
        supply = None
        for e in net.elements.values():
            if e.type == "power_supply" and e.supply_volts:
                supply = e.supply_volts
                break
        distribute(root, supply if supply is not None else p.supply_volts)


# --------------------------------------------------------------------------
def calculate(net: Network) -> Results:
    res = Results(problems=net.validate())
    if any("loop in the topology" in p for p in res.problems):
        return res
    _forward(net, res)
    _return(net, res)
    _powering(net, res)

    rows = list(res.rows.values())
    taps = [r for r in rows if r.type == "tap" and r.tap_port]
    res.totals = {
        "elements": len(rows),
        "taps": len(taps),
        "amplifiers": sum(1 for r in rows if r.type == "amplifier"),
        "homes_passed": sum(r.houses for r in rows),
        "footage": round(sum(r.length_ft for r in rows), 1),
        "max_cumulative_ft": round(max((r.cumulative_ft for r in rows), default=0), 1),
        "min_tap_port_dbmv": round(min((r.tap_port.high for r in taps), default=0), 2),
        "max_tap_port_dbmv": round(max((r.tap_port.high for r in taps), default=0), 2),
        "warnings": sum(len(r.warnings) for r in rows),
    }
    return res
