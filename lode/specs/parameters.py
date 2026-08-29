"""PARAMETERS spec file (``.par``).

"The Parameters file contains six separate pages or tabs of general
information such as maximum crossover, maximum tap outputs, pedestal sizing,
and power supply information."

The Parameters file is the master file of a spec set: it declares the design
frequencies that every other spec file is indexed by, the unit system, the
level windows that drive the red/yellow/green flagging in Design Mode, and the
defaults used by the automatic design tools.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar

from .base import SpecError, SpecFile

FORWARD_COLUMNS = ("F1", "F2", "F3", "F4", "F5", "F6")
RETURN_COLUMNS = ("R1", "R2", "R3", "R4")


@dataclass
class Frequency:
    """One design frequency column.

    ``F1`` is by convention the *forward high* channel and ``F2`` the
    *forward low*; ``R1`` is *return high* and ``R2`` *return low*.  The
    Design Assistant supports up to six forward and four return columns, and
    "the column headings can be customized in the Frequencies page".
    """

    id: str = "F1"
    label: str = ""
    mhz: float = 0.0
    enabled: bool = True

    @property
    def is_return(self) -> bool:
        return self.id.upper().startswith("R")

    def display(self) -> str:
        return self.label or (f"{self.mhz:g}" if self.mhz else self.id)


@dataclass
class HomesToPorts:
    """Row of the Homes / Number of Ports table used by automatic tap sizing."""

    homes_max: int = 2
    ports: int = 2


@dataclass
class PoweringDefaults:
    supply_voltage: float = 90.0
    supply_max_amps: float = 15.0
    #: minimum voltage that must still be present at any active
    min_device_voltage: float = 42.0
    #: below this many volts of headroom a device is flagged yellow
    voltage_margin: float = 3.0
    #: ``stair`` reproduces the classic step table, ``linear`` interpolates
    #: "the actual current draws for the active devices at the true voltage"
    interpolation: str = "linear"
    #: fraction of homes assumed powered/off-hook in a worst-case study
    penetration_pct: float = 100.0


@dataclass
class ParametersSpec(SpecFile):
    KIND: ClassVar[str] = "parameters"
    EXT: ClassVar[str] = ".par"

    # -- page 1: general -------------------------------------------------
    distance_units: str = "feet"
    signal_display: str = "dBmV"
    system_name: str = ""

    # -- page 2: frequencies ---------------------------------------------
    frequencies: list[Frequency] = field(default_factory=list)
    #: which two forward columns select pads and equalizers
    fwd_eq_high: str = "F1"
    fwd_eq_low: str = "F2"
    rtn_eq_high: str = "R1"
    rtn_eq_low: str = "R2"

    # -- page 3: design levels -------------------------------------------
    #: minimum acceptable forward level at a tap port, per column
    min_tap_output: dict = field(default_factory=lambda: {"F1": 16.0})
    #: "if you have a minimum tap output specification of 16 dB and are not
    #: allowed to exceed 26 dB from that tap port, you would enter a 10.00"
    tap_window: float = 10.0
    enforce_tap_window: bool = False
    #: maximum acceptable return level a subscriber must transmit into a tap
    max_return_tap_input: dict = field(default_factory=lambda: {"R1": 40.0})
    return_window: float = 10.0
    #: "how far a tap has to be out of spec before being displayed red"
    set_margin: float = 1.0
    #: "the maximum that the forward low signal may exceed the forward high
    #: signal before an in-line equalizer is placed"
    max_crossover: float = 3.0
    allow_over_equalization: bool = True
    #: dB added to a module input level to obtain the housing input minimum
    default_housing_offset: float = 3.0

    # -- page 4: taps ----------------------------------------------------
    homes_to_ports: list[HomesToPorts] = field(default_factory=list)
    default_tsg: int = 1
    #: prefer the highest tap value that still meets the minimum port output
    tap_selection: str = "highest_value"
    #: "Maximum LE Cascade" -- how many line extenders may follow one another
    #: before the design is flagged (0 disables the check)
    max_le_cascade: int = 3
    #: flag a tap whose ports cannot serve the units at that location
    check_tap_ports: bool = True

    # -- page 5: powering ------------------------------------------------
    powering: PoweringDefaults = field(default_factory=PoweringDefaults)

    # -- page 6: defaults / misc -----------------------------------------
    default_cable: str = ""
    default_trunk_cable: str = ""
    default_active: str = ""
    default_coupler: str = ""
    #: cable attenuation multiplier for design temperature (1.0 = as specified)
    cable_loss_factor: float = 1.0
    #: dB of loss added for each connector pair on a span
    connector_loss: float = 0.0
    extra: dict = field(default_factory=dict)

    # ------------------------------------------------------------------
    def _payload(self) -> dict:
        from .base import _encode

        payload = {
            "distance_units": self.distance_units,
            "signal_display": self.signal_display,
            "system_name": self.system_name,
            "frequencies": _encode(self.frequencies),
            "fwd_eq_high": self.fwd_eq_high,
            "fwd_eq_low": self.fwd_eq_low,
            "rtn_eq_high": self.rtn_eq_high,
            "rtn_eq_low": self.rtn_eq_low,
            "min_tap_output": self.min_tap_output,
            "tap_window": self.tap_window,
            "enforce_tap_window": self.enforce_tap_window,
            "max_return_tap_input": self.max_return_tap_input,
            "return_window": self.return_window,
            "set_margin": self.set_margin,
            "max_crossover": self.max_crossover,
            "allow_over_equalization": self.allow_over_equalization,
            "default_housing_offset": self.default_housing_offset,
            "homes_to_ports": _encode(self.homes_to_ports),
            "default_tsg": self.default_tsg,
            "tap_selection": self.tap_selection,
            "powering": _encode(self.powering),
            "default_cable": self.default_cable,
            "default_trunk_cable": self.default_trunk_cable,
            "default_active": self.default_active,
            "default_coupler": self.default_coupler,
            "cable_loss_factor": self.cable_loss_factor,
            "connector_loss": self.connector_loss,
            "extra": self.extra,
        }
        return payload

    def _load_payload(self, data: dict) -> None:
        from .base import _decode

        simple = (
            "distance_units", "signal_display", "system_name",
            "fwd_eq_high", "fwd_eq_low", "rtn_eq_high", "rtn_eq_low",
            "min_tap_output", "tap_window", "enforce_tap_window",
            "max_return_tap_input", "return_window", "set_margin",
            "max_crossover", "allow_over_equalization",
            "default_housing_offset", "default_tsg", "tap_selection",
            "default_cable", "default_trunk_cable", "default_active",
            "default_coupler", "cable_loss_factor", "connector_loss", "extra",
        )
        for key in simple:
            if key in data:
                setattr(self, key, data[key])
        self.frequencies = [_decode(Frequency, f) for f in data.get("frequencies", [])]
        self.homes_to_ports = [
            _decode(HomesToPorts, h) for h in data.get("homes_to_ports", [])
        ]
        if "powering" in data:
            self.powering = _decode(PoweringDefaults, data["powering"])

    # ------------------------------------------------------------------
    def validate(self) -> None:
        if self.distance_units not in ("feet", "meters", "decimeters"):
            raise SpecError(f"bad distance_units {self.distance_units!r}")
        if self.signal_display.lower() not in ("dbmv", "dbuv"):
            raise SpecError(f"bad signal_display {self.signal_display!r}")
        ids = [f.id.upper() for f in self.frequencies]
        if len(set(ids)) != len(ids):
            raise SpecError("duplicate frequency column ids")
        for fid in ids:
            if fid not in FORWARD_COLUMNS + RETURN_COLUMNS:
                raise SpecError(
                    f"unknown frequency column {fid!r}; expected one of "
                    f"{FORWARD_COLUMNS + RETURN_COLUMNS}"
                )
        if len(self.forward_columns) < 2:
            raise SpecError(
                "two forward frequencies are required for the Design Assistant "
                "to select forward equalizer values correctly"
            )
        for attr in ("fwd_eq_high", "fwd_eq_low"):
            if getattr(self, attr) not in self.forward_columns:
                raise SpecError(f"{attr} must name an enabled forward column")
        if self.return_columns:
            for attr in ("rtn_eq_high", "rtn_eq_low"):
                if getattr(self, attr) not in self.return_columns:
                    raise SpecError(f"{attr} must name an enabled return column")

    # ------------------------------------------------------------------
    # frequency helpers
    # ------------------------------------------------------------------
    @property
    def enabled_frequencies(self) -> list[Frequency]:
        return [f for f in self.frequencies if f.enabled]

    @property
    def forward_columns(self) -> list[str]:
        return [f.id.upper() for f in self.enabled_frequencies if not f.is_return]

    @property
    def return_columns(self) -> list[str]:
        return [f.id.upper() for f in self.enabled_frequencies if f.is_return]

    @property
    def all_columns(self) -> list[str]:
        return self.forward_columns + self.return_columns

    def frequency(self, column: str) -> Frequency | None:
        for f in self.frequencies:
            if f.id.upper() == column.upper():
                return f
        return None

    def label(self, column: str) -> str:
        f = self.frequency(column)
        return f.display() if f else column

    def is_return(self, column: str) -> bool:
        return column.upper().startswith("R")

    # ------------------------------------------------------------------
    # design windows
    # ------------------------------------------------------------------
    def min_tap_level(self, column: str) -> float | None:
        """Minimum acceptable forward tap-port output for *column*."""
        if column in self.min_tap_output:
            return float(self.min_tap_output[column])
        return None

    def max_tap_level(self, column: str) -> float | None:
        """Maximum acceptable forward tap-port output (minimum + tap window)."""
        low = self.min_tap_level(column)
        if low is None or not self.tap_window:
            return None
        return low + float(self.tap_window)

    def max_return_level(self, column: str) -> float | None:
        if column in self.max_return_tap_input:
            return float(self.max_return_tap_input[column])
        return None

    def min_return_level(self, column: str) -> float | None:
        high = self.max_return_level(column)
        if high is None or not self.return_window:
            return None
        return high - float(self.return_window)

    def ports_for_homes(self, homes: int) -> int:
        """"How many tap ports are needed to feed a certain house count"."""
        table = sorted(self.homes_to_ports, key=lambda h: h.homes_max)
        for row in table:
            if homes <= row.homes_max:
                return row.ports
        return table[-1].ports if table else 8

    @classmethod
    def default(cls) -> "ParametersSpec":
        """A sensible 1 GHz / 42 MHz split starting point."""
        return cls(
            name="default",
            description="750 MHz forward, 42 MHz return starting parameters",
            frequencies=[
                Frequency("F1", "750", 750.0, True),
                Frequency("F2", "55", 55.0, True),
                Frequency("R1", "42", 42.0, True),
                Frequency("R2", "5", 5.0, True),
            ],
            homes_to_ports=[
                HomesToPorts(1, 2), HomesToPorts(2, 2),
                HomesToPorts(4, 4), HomesToPorts(8, 8),
            ],
        )
