"""Powering Mode: AC distribution over the coax.

Actives are powered through the same cable that carries the RF.  A power
supply injects quasi-square-wave AC at one location; current flows outward in
*both* directions along the plant (the RF tree is directed, the AC network is
not), losing voltage across the loop resistance of every span and the series
resistance of every passive it passes through.

Two things make this non-trivial and both come straight from the manual:

* current draw depends on the voltage that actually arrives -- "Powering data
  are entered in voltage-current pairs in ascending order of voltage for each
  device", and with linear interpolation the engine will "interpolate the
  actual current draws for the active devices at the true voltage thereby
  eliminating the jumps that occur in the stair step method";
* the loop is circular -- voltage depends on current, current depends on
  voltage -- so it is solved by fixed-point iteration to convergence.

The engine also supports a peak-usage study: "the worst-case analysis allows
you to specify a different penetration percentage than is set in the spec
files", modelled here as a load multiplier plus per-location extra load.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..network import Network
from ..specs import SpecSet
from .levels import ERROR, OK, WARN, Flag


@dataclass
class NodePower:
    location: str = ""
    label: str = ""
    device: str = ""
    kind: str = ""
    volts: float = 0.0
    #: current this device itself draws
    draw: float = 0.0
    #: total current flowing through this device (its own draw plus everything
    #: it feeds)
    through: float = 0.0
    max_amps: float = 0.0
    watts: float = 0.0
    status: str = OK

    def to_dict(self) -> dict:
        return {
            "location": self.location, "label": self.label,
            "device": self.device, "kind": self.kind,
            "volts": round(self.volts, 2), "draw": round(self.draw, 3),
            "through": round(self.through, 3),
            "max_amps": self.max_amps, "watts": round(self.watts, 1),
            "status": self.status,
        }


@dataclass
class SpanPower:
    span: str = ""
    label: str = ""
    cable: str = ""
    length: float = 0.0
    resistance: float = 0.0
    current: float = 0.0
    drop: float = 0.0

    def to_dict(self) -> dict:
        return {
            "span": self.span, "label": self.label, "cable": self.cable,
            "length": self.length, "resistance": round(self.resistance, 3),
            "current": round(self.current, 3), "drop": round(self.drop, 2),
        }


@dataclass
class PoweringArea:
    """One power supply and everything it feeds."""

    supply_location: str = ""
    supply_id: str = ""
    label: str = ""
    volts: float = 0.0
    max_amps: float = 0.0
    total_current: float = 0.0
    total_watts: float = 0.0
    utilisation: float = 0.0
    iterations: int = 0
    converged: bool = True
    nodes: dict = field(default_factory=dict)
    spans: dict = field(default_factory=dict)
    flags: list = field(default_factory=list)

    @property
    def min_voltage(self) -> float:
        return min((n.volts for n in self.nodes.values()), default=0.0)

    def to_dict(self) -> dict:
        return {
            "supply_location": self.supply_location,
            "supply_id": self.supply_id, "label": self.label,
            "volts": self.volts, "max_amps": self.max_amps,
            "total_current": round(self.total_current, 3),
            "total_watts": round(self.total_watts, 1),
            "utilisation": round(self.utilisation, 1),
            "min_voltage": round(self.min_voltage, 2),
            "iterations": self.iterations, "converged": self.converged,
            "nodes": {k: v.to_dict() for k, v in self.nodes.items()},
            "spans": {k: v.to_dict() for k, v in self.spans.items()},
            "flags": [f.to_dict() for f in self.flags],
        }


class PoweringEngine:
    """Solves every powering area in a network."""

    def __init__(self, specs: SpecSet, network: Network,
                 load_factor: float = 1.0, extra_load: dict | None = None):
        self.specs = specs
        self.network = network
        self.params = specs.parameters
        self.load_factor = load_factor
        self.extra_load = extra_load or {}

    # -- device facts ----------------------------------------------------
    def _device(self, loc):
        if loc.kind in ("active", "source"):
            return self.specs.actives.by_id(loc.device)
        if loc.kind == "tap":
            return self.specs.taps.by_id(loc.device)
        if loc.kind == "coupler":
            return self.specs.couplers.by_id(loc.device)
        return None

    def _series_resistance(self, loc) -> float:
        device = self._device(loc)
        return float(getattr(device, "resistance", 0.0) or 0.0)

    def _max_amps(self, loc) -> float:
        device = self._device(loc)
        return float(getattr(device, "max_amps", 0.0) or 0.0)

    def _passes_power(self, loc) -> bool:
        if loc.power_block:
            return False
        device = self._device(loc)
        if device is None:
            return True
        if getattr(device, "power_block", False):
            return False
        return bool(getattr(device, "power_passing", True))

    def _draw(self, loc, volts: float) -> float:
        device = self._device(loc)
        base = 0.0
        if loc.kind in ("active", "source") and device is not None:
            base = device.current_at(volts, self.params.powering.interpolation)
        base *= self.load_factor
        return base + float(self.extra_load.get(loc.id, 0.0))

    def _span_resistance(self, span) -> float:
        cable = self.specs.cables.by_id(span.cable)
        return cable.resistance(span.length) if cable else 0.0

    # ------------------------------------------------------------------
    def areas(self) -> list:
        """Find every power supply and the tree of plant it can reach."""
        net = self.network
        supplies = [
            loc for loc in net.locations.values() if loc.power_supply is not None
        ]
        blocked_by_supply = {s.id for s in supplies}

        found = []
        for supply in supplies:
            adjacency: dict[str, list] = {}
            for span in net.spans.values():
                adjacency.setdefault(span.parent, []).append((span.child, span))
                adjacency.setdefault(span.child, []).append((span.parent, span))

            parent: dict[str, tuple[str, object] | None] = {supply.id: None}
            order = [supply.id]
            stack = [supply.id]
            seen = {supply.id}
            while stack:
                current = stack.pop()
                loc = net.locations[current]
                if current != supply.id and not self._passes_power(loc):
                    continue  # AC stops here; the device itself is still fed
                for neighbour, span in adjacency.get(current, []):
                    if neighbour in seen:
                        continue
                    if neighbour in blocked_by_supply:
                        continue  # a neighbouring supply bounds this area
                    seen.add(neighbour)
                    parent[neighbour] = (current, span)
                    order.append(neighbour)
                    stack.append(neighbour)
            found.append((supply, parent, order))
        return found

    # ------------------------------------------------------------------
    def solve(self, tolerance: float = 0.005, max_iterations: int = 200) -> list:
        results = []
        net = self.network
        for supply_loc, parent, order in self.areas():
            ps = supply_loc.power_supply
            area = PoweringArea(
                supply_location=supply_loc.id,
                supply_id=ps.id or "PS",
                label=supply_loc.display(),
                volts=ps.volts, max_amps=ps.max_amps,
            )
            volts = {loc_id: ps.volts for loc_id in order}
            draw: dict[str, float] = {}
            through: dict[str, float] = {}

            for iteration in range(1, max_iterations + 1):
                for loc_id in order:
                    draw[loc_id] = self._draw(net.locations[loc_id], volts[loc_id])
                # accumulate subtree currents from the leaves back to the supply
                through = dict(draw)
                for loc_id in reversed(order[1:]):
                    up = parent[loc_id]
                    if up is None:
                        continue
                    through[up[0]] = through.get(up[0], 0.0) + through[loc_id]
                # push voltages back out
                delta = 0.0
                for loc_id in order[1:]:
                    up_id, span = parent[loc_id]
                    resistance = (
                        self._span_resistance(span)
                        + (0.0 if up_id == supply_loc.id
                           else self._series_resistance(net.locations[up_id]))
                    )
                    new_v = volts[up_id] - through[loc_id] * resistance
                    delta = max(delta, abs(new_v - volts[loc_id]))
                    volts[loc_id] = new_v
                area.iterations = iteration
                if delta < tolerance:
                    break
            else:
                area.converged = False

            self._collect(area, net, parent, order, volts, draw, through)
            results.append(area)
        return results

    # ------------------------------------------------------------------
    def _collect(self, area, net, parent, order, volts, draw, through) -> None:
        params = self.params.powering
        for loc_id in order:
            loc = net.locations[loc_id]
            node = NodePower(
                location=loc_id, label=loc.display(), device=loc.device,
                kind=loc.kind, volts=volts[loc_id], draw=draw.get(loc_id, 0.0),
                through=through.get(loc_id, 0.0), max_amps=self._max_amps(loc),
            )
            node.watts = node.volts * node.draw
            device = self._device(loc)
            floor = float(getattr(device, "min_voltage", 0.0) or
                          params.min_device_voltage)
            if loc.kind in ("active", "source"):
                if node.volts < floor:
                    node.status = ERROR
                    area.flags.append(Flag(
                        ERROR, "under-voltage", loc_id, loc.display(), "",
                        f"{loc.display()}: {node.volts:.1f} V at the {loc.device} "
                        f"is below its {floor:.0f} V minimum",
                        value=node.volts, limit=floor))
                elif node.volts < floor + params.voltage_margin:
                    node.status = WARN
                    area.flags.append(Flag(
                        WARN, "low-voltage", loc_id, loc.display(), "",
                        f"{loc.display()}: {node.volts:.1f} V leaves less than "
                        f"{params.voltage_margin:.0f} V of headroom over the "
                        f"{floor:.0f} V minimum",
                        value=node.volts, limit=floor))
            if node.max_amps and node.through > node.max_amps:
                node.status = ERROR
                area.flags.append(Flag(
                    ERROR, "over-current", loc_id, loc.display(), "",
                    f"{loc.display()}: {node.through:.2f} A through the "
                    f"{loc.device or loc.kind} exceeds its {node.max_amps:.1f} A "
                    f"rating",
                    value=node.through, limit=node.max_amps))
            area.nodes[loc_id] = node

        for loc_id in order[1:]:
            up_id, span = parent[loc_id]
            resistance = (
                self._span_resistance(span)
                + (0.0 if up_id == area.supply_location
                   else self._series_resistance(net.locations[up_id]))
            )
            current = through.get(loc_id, 0.0)
            area.spans[span.id] = SpanPower(
                span=span.id,
                label=f"{net.locations[up_id].display()} - "
                      f"{net.locations[loc_id].display()}",
                cable=span.cable, length=span.length, resistance=resistance,
                current=current, drop=current * resistance,
            )

        area.total_current = through.get(area.supply_location, 0.0)
        area.total_watts = area.volts * area.total_current
        area.utilisation = (
            100.0 * area.total_current / area.max_amps if area.max_amps else 0.0
        )
        if area.max_amps and area.total_current > area.max_amps:
            area.flags.append(Flag(
                ERROR, "supply-overload", area.supply_location, area.label, "",
                f"power supply {area.label}: {area.total_current:.2f} A load "
                f"exceeds its {area.max_amps:.1f} A rating",
                value=area.total_current, limit=area.max_amps))
        elif area.max_amps and area.utilisation > 80.0:
            area.flags.append(Flag(
                WARN, "supply-loading", area.supply_location, area.label, "",
                f"power supply {area.label} is at {area.utilisation:.0f}% of "
                f"its {area.max_amps:.1f} A rating",
                value=area.total_current, limit=area.max_amps))
        if not area.converged:
            area.flags.append(Flag(
                WARN, "no-convergence", area.supply_location, area.label, "",
                "the powering solution did not converge -- check for an "
                "overloaded supply or an unrealistic load"))
