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
    cable_index: int = -1                      # 0-99 in the spec file; the screen shows series*100 + this

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
    tap_id: int = 0                                       # what the screen shows
    row: int = -1                                         # tap file row, as a design file refers to it
    tap_value_db: float = 26.0                            # measured, for BOM
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
    coupler_id: int = 0                        # the ID entered when placing it
    port_losses: list = field(default_factory=list)   # dB per output port, in port order
    power_passing: list = field(default_factory=list) # bool per output port
    source: str = "manual"
    # Per-frequency losses, one [(MHz, dB)] table per leg: leg 0 is the
    # through leg, then the tap legs.  Spec-file couplers carry these; parts
    # keyed in by hand fall back to port_losses.
    leg_losses: list = field(default_factory=list)
    record: int = -1                           # coupler file record, as a design refers to it
    internal: bool = False                     # an amplifier's own output split

    @property
    def ports(self) -> int:
        return len(self.port_losses)

    def port_db(self, port: int, mhz: float | None = None) -> float:
        if mhz is not None and self.leg_losses:
            legs = self.leg_losses
            table = legs[min(port, len(legs) - 1)] if port > 0 else legs[0]
            return interpolate_sqrt([tuple(p) for p in table], mhz)
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
    # The Active ID typed at the amp column -- text, since the Configuration
    # Table allows "11H" as readily as "61".
    active_id: str = ""
    index: int = -1                            # actives table index, as a design refers to it
    fibre_fed: bool = False                    # no RF input: an optical node
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
        return not self.fibre_fed and self.in_forward_high < NO_RF_INPUT

    def current_at(self, volts: float, mode: str = "constant_wattage") -> float:
        """Current drawn at an applied voltage.

        ``mode`` is the Parameters file's Power interpolation setting.  In
        "constant_wattage" actives are constant-power loads: the power steps give the draw at a
        few voltages, and between them the *power* (volts x amps) is
        interpolated, then divided by the voltage.  Checked against the AL004
        Power screen, where this reproduces all 29 currents on branch 4 --
        e.g. the Ripple node at 85.6 V draws 1.74 A and a Bridger at 86.8 V
        0.79 A.  Holding the step value instead would show 1.86 and 0.81.
        Below the lowest step the lowest-voltage draw holds; above the highest,
        its power does.
        """
        if not self.power_draw:
            return self.current_draw_a
        pts = sorted((float(v), float(a)) for v, a in self.power_draw)
        if volts <= pts[0][0]:
            return pts[0][1]
        if mode == "step":
            # "from Vmin to V2 the current from A1 is used", and so on
            current = pts[0][1]
            for v, a in pts:
                if volts >= v:
                    current = a
            return current
        if mode == "linear":
            if volts >= pts[-1][0]:
                return pts[-1][1]
            for (v0, a0), (v1, a1) in zip(pts, pts[1:]):
                if v0 <= volts <= v1 and v1 > v0:
                    return a0 + (a1 - a0) * (volts - v0) / (v1 - v0)
            return pts[-1][1]
        if volts >= pts[-1][0]:
            return pts[-1][0] * pts[-1][1] / volts
        for (v0, a0), (v1, a1) in zip(pts, pts[1:]):
            if v0 <= volts <= v1 and v1 > v0:
                watts = v0 * a0 + (v1 * a1 - v0 * a0) * (volts - v0) / (v1 - v0)
                return watts / volts
        return pts[-1][1]

    @property
    def min_voltage(self) -> float:
        """Vmin: the lowest voltage at which the active will operate."""
        if self.power_draw:
            return min(float(v) for v, _ in self.power_draw)
        return self.min_operating_voltage


@dataclass
class InlineType:
    """An in-line device placed in the amp column as Qn: an equalizer, a pad,
    or a zero-loss marker such as EXIST SPLICE.  Losses at each frequency."""
    id: str
    name: str
    number: int = 0                            # the n of Qn
    losses: list = field(default_factory=list)  # [(MHz, dB)]
    source: str = "manual"

    def loss_db(self, mhz: float) -> float:
        for f, v in self.losses:
            if abs(f - mhz) < 1e-6:
                return float(v)
        return 0.0


@dataclass
class PowerSupplyType:
    id: str
    name: str
    volts: float = 90.0
    amps: float = 15.0
    source: str = "manual"
    type_id: int = 0                           # the supply type number in the Parameters file


@dataclass
class Library:
    name: str = "New library"
    cables: dict = field(default_factory=dict)
    taps: dict = field(default_factory=dict)
    passives: dict = field(default_factory=dict)
    actives: dict = field(default_factory=dict)
    power_supplies: dict = field(default_factory=dict)
    inline: dict = field(default_factory=dict)
    imported_from: str = ""

    _TABLES = {
        "cables": CableType, "taps": TapType, "passives": PassiveType,
        "actives": ActiveType, "power_supplies": PowerSupplyType,
        "inline": InlineType,
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
                if attr == "actives" and not isinstance(v.get("active_id", ""), str):
                    v = dict(v, active_id=str(v["active_id"] or ""))
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
    # System Levels: per lv 0-15, [min forward high, min forward low,
    # max return high, max return low] at the tap ports.  A tap outside by
    # less than the tap margin is marginal (yellow), beyond it red.
    levels: list = field(default_factory=lambda: [[15.0, 9.0, 45.0, 45.0]])
    tap_margin_db: float = 0.5
    # cable series (the hundreds of a cable ID) not counted as mileage: the
    # ones not ticked under the Parameters file's Strand/Trench Types
    # (WV750: 000 200 300 400 ticked, so 1xx and 5xx-9xx are not mileage)
    non_mileage_series: list = field(default_factory=lambda: [1])
    # how an active's power steps are read: "step", "linear" or
    # "constant_wattage" -- the Parameters file's Power interpolation setting
    power_interpolation: str = "constant_wattage"
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
