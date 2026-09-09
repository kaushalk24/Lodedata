"""Domain model: the equipment library and the network itself.

Kept deliberately plain -- dataclasses plus dict round-tripping, no ORM.
A project is stored as one JSON document.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any
import math
import uuid


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


# ==========================================================================
# frequency-dependent value: a list of (MHz, dB) points
# ==========================================================================
def interpolate_sqrt(points: list[tuple[float, float]], mhz: float) -> float:
    """Value at `mhz`, interpolating on sqrt(f) -- how coax actually behaves.

    With one point, scales it as sqrt(f).  With none, returns 0.
    """
    if not points:
        return 0.0
    pts = sorted(points)
    if len(pts) == 1:
        f0, v0 = pts[0]
        if f0 <= 0:
            return v0
        return v0 * math.sqrt(max(mhz, 0.0) / f0)
    if mhz <= pts[0][0]:
        lo, hi = pts[0], pts[1]
    elif mhz >= pts[-1][0]:
        lo, hi = pts[-2], pts[-1]
    else:
        for i in range(len(pts) - 1):
            if pts[i][0] <= mhz <= pts[i + 1][0]:
                lo, hi = pts[i], pts[i + 1]
                break
    x0, x1 = math.sqrt(lo[0]), math.sqrt(hi[0])
    if x1 == x0:
        return lo[1]
    t = (math.sqrt(max(mhz, 0.0)) - x0) / (x1 - x0)
    return lo[1] + t * (hi[1] - lo[1])


# ==========================================================================
# library parts
# ==========================================================================
@dataclass
class CableType:
    id: str
    name: str
    kind: str = "hardline"                     # hardline | drop
    loop_resistance_ohm_per_1000ft: float = 1.0
    attenuation: list = field(default_factory=list)   # [(MHz, dB per 100 ft)]
    velocity_pct: float = 87.0
    notes: str = ""
    source: str = "manual"

    def loss_db(self, mhz: float, feet: float) -> float:
        return interpolate_sqrt([tuple(p) for p in self.attenuation], mhz) * feet / 100.0

    def resistance_ohms(self, feet: float) -> float:
        return self.loop_resistance_ohm_per_1000ft * feet / 1000.0


@dataclass
class TapType:
    """A tap of one port count.

    Lode Data calls the two loss sets "Tap Value" -- the loss toward the tap
    ports -- and "Tap Losses", the insertion loss from hard cable in to hard
    cable out.  Both are given at each design frequency, so both are stored
    as frequency tables rather than single numbers.
    """
    id: str
    name: str
    ports: int = 4
    tap_value_db: float = 26.0                            # nominal, for display
    tap_value: list = field(default_factory=list)         # [(MHz, dB)] toward the ports
    through_loss: list = field(default_factory=list)      # [(MHz, dB)] insertion
    return_through_loss: list = field(default_factory=list)
    current_draw_a: float = 0.0
    power_passing: bool = True
    self_terminating: bool = False
    source: str = "manual"

    def through_db(self, mhz: float, reverse: bool = False) -> float:
        pts = self.return_through_loss if (reverse and self.return_through_loss) else self.through_loss
        return interpolate_sqrt([tuple(p) for p in pts], mhz)

    def tap_db(self, mhz: float) -> float:
        if self.tap_value:
            return interpolate_sqrt([tuple(p) for p in self.tap_value], mhz)
        return self.tap_value_db


@dataclass
class PassiveType:
    """Splitter, directional coupler or power inserter."""
    id: str
    name: str
    kind: str = "splitter"                     # splitter | coupler | power_inserter
    port_losses: list = field(default_factory=list)   # dB per output port, in port order
    power_passing: list = field(default_factory=list) # bool per output port
    source: str = "manual"

    @property
    def ports(self) -> int:
        return len(self.port_losses)

    def port_db(self, port: int) -> float:
        if 0 <= port < len(self.port_losses):
            return float(self.port_losses[port])
        return 0.0

    def port_powers(self, port: int) -> bool:
        if 0 <= port < len(self.power_passing):
            return bool(self.power_passing[port])
        return True


# An input requirement of 99 means "no RF input needed" -- what an optical node
# carries, since it is fed by fibre. Same sentinel convention as cable loop 99.
NO_RF_INPUT = 99.0


@dataclass
class ActiveType:
    """Amplifier, line extender or optical node.

    The four In and four Out levels mirror the Lode Data actives file: the
    level required at, and produced by, the active at each of the four design
    frequencies.
    """
    id: str
    name: str
    kind: str = "line_extender"                # node | trunk | bridger | line_extender
    outputs: int = 1
    # required input levels (dBmV)
    in_forward_high: float = 13.0
    in_forward_low: float = 9.0
    in_return_high: float = 21.0
    in_return_low: float = 21.0
    # produced output levels (dBmV)
    out_forward_high: float = 48.0
    out_forward_low: float = 39.0
    out_return_high: float = 40.0
    out_return_low: float = 40.0
    noise_figure_db: float = 7.0
    # powering: current draw against applied voltage, [[volts, amps], ...].
    # Actives are constant-power, so draw rises as the voltage sags -- which is
    # why the real spec file carries a table rather than one number.
    power_draw: list = field(default_factory=list)
    current_draw_a: float = 1.0                # used when no table is present
    min_operating_voltage: float = 42.0
    source: str = "manual"

    @property
    def forward_max_gain_db(self) -> float:
        if self.in_forward_high >= NO_RF_INPUT:
            return 0.0
        return self.out_forward_high - self.in_forward_high

    @property
    def forward_default_output_dbmv(self) -> float:
        return self.out_forward_high

    @property
    def forward_default_tilt_db(self) -> float:
        return self.out_forward_high - self.out_forward_low

    @property
    def return_max_gain_db(self) -> float:
        if not self.out_return_high:
            return 0.0
        return self.out_return_high - self.in_return_high

    @property
    def needs_rf_input(self) -> bool:
        return self.in_forward_high < NO_RF_INPUT

    def current_at(self, volts: float) -> float:
        """Current drawn at an applied voltage.

        The manual defines these as *power steps*, not a curve to interpolate:
        "from Vmin to V2, it uses A1 amperes; from V2 to V3, A2 amperes are
        used".  So each entry gives the draw from its own voltage up to the
        next one.
        """
        if not self.power_draw:
            return self.current_draw_a
        pts = sorted((float(v), float(a)) for v, a in self.power_draw)
        if volts < pts[0][0]:
            return pts[0][1]              # below Vmin: the worst-case draw
        current = pts[0][1]
        for v, a in pts:
            if volts >= v:
                current = a
            else:
                break
        return current

    @property
    def min_voltage(self) -> float:
        """Vmin: the lowest voltage at which the active will operate."""
        if self.power_draw:
            return min(float(v) for v, _ in self.power_draw)
        return self.min_operating_voltage


@dataclass
class PowerSupplyType:
    id: str
    name: str
    volts: float = 90.0
    amps: float = 15.0
    source: str = "manual"


@dataclass
class Library:
    name: str = "New library"
    cables: dict = field(default_factory=dict)
    taps: dict = field(default_factory=dict)
    passives: dict = field(default_factory=dict)
    actives: dict = field(default_factory=dict)
    power_supplies: dict = field(default_factory=dict)
    imported_from: str = ""

    _TABLES = {
        "cables": CableType, "taps": TapType, "passives": PassiveType,
        "actives": ActiveType, "power_supplies": PowerSupplyType,
    }

    def add(self, part) -> Any:
        for attr, cls in self._TABLES.items():
            if isinstance(part, cls):
                getattr(self, attr)[part.id] = part
                return part
        raise TypeError(f"not a library part: {type(part).__name__}")

    def to_dict(self) -> dict:
        d = {"name": self.name, "imported_from": self.imported_from}
        for attr in self._TABLES:
            d[attr] = {k: asdict(v) for k, v in getattr(self, attr).items()}
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Library":
        lib = cls(name=d.get("name", "New library"),
                  imported_from=d.get("imported_from", ""))
        for attr, klass in cls._TABLES.items():
            for k, v in (d.get(attr) or {}).items():
                getattr(lib, attr)[k] = klass(**v)
        return lib


# ==========================================================================
# design parameters
# ==========================================================================
@dataclass
class DesignParameters:
    forward_low_mhz: float = 54.0
    forward_high_mhz: float = 750.0
    return_low_mhz: float = 5.0
    return_high_mhz: float = 42.0
    # levels the design is checked against
    min_tap_port_dbmv: float = 0.0
    max_tap_port_dbmv: float = 15.0
    min_amp_input_dbmv: float = 10.0
    return_transmit_dbmv: float = 45.0     # CPE upstream transmit level
    return_target_at_node_dbmv: float = 15.0
    # powering
    supply_volts: float = 90.0
    min_device_volts: float = 42.0
    temperature_f: float = 68.0

    @property
    def forward_freqs(self) -> tuple[float, float]:
        return (self.forward_low_mhz, self.forward_high_mhz)

    @property
    def return_freqs(self) -> tuple[float, float]:
        return (self.return_low_mhz, self.return_high_mhz)


# ==========================================================================
# the network
# ==========================================================================
ELEMENT_TYPES = (
    "node",            # signal source: optical node or headend feed
    "amplifier",       # line extender / bridger / trunk amp
    "tap",
    "splitter",        # any passive with output ports (splitter / coupler)
    "power_inserter",
    "power_supply",
    "terminator",
    "subscriber",      # a drop / service location
)


@dataclass
class Element:
    id: str
    type: str
    label: str = ""
    parent_id: str | None = None
    parent_port: int = 0               # which output port of the parent feeds this
    cable_id: str | None = None        # cable type on the span from parent
    length_ft: float = 0.0
    part_id: str | None = None         # library part for this element
    houses: int = 0                    # homes passed / units served at a tap
    # per-element overrides, all optional
    output_dbmv: float | None = None   # amplifier operational output at high freq
    tilt_db: float | None = None       # amplifier output tilt
    source_dbmv: float | None = None   # node/headend launch level at high freq
    source_tilt_db: float | None = None
    supply_volts: float | None = None  # power supply output
    notes: str = ""
    x: float = 0.0
    y: float = 0.0


@dataclass
class Network:
    id: str = ""
    name: str = "New design"
    parameters: DesignParameters = field(default_factory=DesignParameters)
    library: Library = field(default_factory=Library)
    elements: dict = field(default_factory=dict)   # id -> Element
    imported_from: str = ""

    # -- structure helpers ------------------------------------------------
    def children(self, parent_id: str | None) -> list:
        kids = [e for e in self.elements.values() if e.parent_id == parent_id]
        kids.sort(key=lambda e: (e.parent_port, e.label))
        return kids

    def roots(self) -> list:
        return [e for e in self.elements.values() if not e.parent_id]

    def add(self, el: Element) -> Element:
        self.elements[el.id] = el
        return el

    def remove(self, element_id: str) -> list:
        """Delete an element and everything fed from it. Returns removed ids."""
        removed = []
        stack = [element_id]
        while stack:
            eid = stack.pop()
            if eid not in self.elements:
                continue
            removed.append(eid)
            stack.extend(c.id for c in self.children(eid))
            del self.elements[eid]
        return removed

    @property
    def has_specs(self) -> bool:
        """A design cannot be calculated until a spec set is attached."""
        lib = self.library
        return bool(lib.cables or lib.taps or lib.actives or lib.passives)

    def validate(self) -> list:
        """Structural problems, as a list of human-readable strings."""
        problems = []
        if not self.has_specs:
            problems.append(
                "no spec set attached: every level, loss and part comes from "
                "the spec files, so attach one before designing")
        for e in self.elements.values():
            if e.parent_id and e.parent_id not in self.elements:
                problems.append(f"{e.label or e.id}: parent no longer exists")
            if e.cable_id and e.cable_id not in self.library.cables:
                problems.append(f"{e.label or e.id}: cable type is not in the library")
            if e.length_ft < 0:
                problems.append(f"{e.label or e.id}: negative span length")
        # cycle check
        seen, stack = set(), []
        for e in self.elements.values():
            chain, cur = set(), e
            while cur and cur.parent_id:
                if cur.id in chain:
                    problems.append(f"{e.label or e.id}: loop in the topology")
                    break
                chain.add(cur.id)
                cur = self.elements.get(cur.parent_id)
        if not self.roots() and self.elements:
            problems.append("no signal source: give one element type 'node' with no parent")
        return problems

    # -- serialisation ----------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "imported_from": self.imported_from,
            "parameters": asdict(self.parameters),
            "library": self.library.to_dict(),
            "elements": {k: asdict(v) for k, v in self.elements.items()},
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Network":
        net = cls(
            id=d.get("id", ""),
            name=d.get("name", "New design"),
            imported_from=d.get("imported_from", ""),
            parameters=DesignParameters(**(d.get("parameters") or {})),
            library=Library.from_dict(d.get("library") or {}),
        )
        for k, v in (d.get("elements") or {}).items():
            net.elements[k] = Element(**v)
        return net
