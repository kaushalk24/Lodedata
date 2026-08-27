"""ACTIVES spec file (``.act``).

"The forward inputs and return outputs on the Actives tab of the actives spec
file should be viewed as module level figures.  Actual module input levels are
best determined by the amplifier manufacturer, as they will take into account
all of the actual losses associated with the internal components."

Housing versus module levels
----------------------------
"Housing levels are determined for the forward-high and return-high channels
by these values to the module level for that device.  For example, assume you
have a forward-high-channel module input of 16.50 dB.  In this case, your
forward-high-channel housing input minimum is 19.50 dB and the Design
Assistant would show an error on an amplifier where the forward-high-channel
level at the end of the incoming piece of cable is less than 19.50 dB."

That is, ``housing_input_min = module_input + housing_offset`` (3.00 dB in the
worked example above), because the level is quoted at the end of the incoming
cable, before the housing's internal losses.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar

from .base import SpecError, SpecFile, lookup

#: Broad equipment classes; used for reports, defaults and auto-design.
CATEGORIES = (
    "node",           # fibre optic node / signal source
    "trunk",          # trunk amplifier
    "bridger",        # trunk amplifier with distribution outputs
    "line_extender",  # feeder-only amplifier
    "launch",         # headend launch amplifier
)


@dataclass
class Equalizer:
    """A plug-in equaliser: a value plus its loss at every frequency column."""

    value: float = 0.0
    loss: dict = field(default_factory=dict)
    part_number: str = ""

    def at(self, column: str) -> float:
        return lookup(self.loss, column)


@dataclass
class OutputPort:
    """One RF output of an active (a bridger typically has two or four)."""

    name: str = "OUT"
    #: additional loss from the module output to this port (internal splitter)
    loss: dict = field(default_factory=dict)

    def at(self, column: str) -> float:
        return lookup(self.loss, column)


@dataclass
class Distortion:
    """A single-unit distortion specification.

    ``base`` is the spec, in dB below carrier, measured with the module
    operating at ``ref_level``.  Whether ``ref_level`` is an input or an output
    level is decided by the sign of the derate factor in the Performance file.
    A ``ref_level`` of ``None`` means the figure does not derate with level --
    used for fixed contributions such as an optical link budget.
    """

    base: float = 0.0
    ref_level: float | None = None


@dataclass
class Active:
    id: str = ""
    description: str = ""
    part_number: str = ""
    category: str = "line_extender"

    # -- forward path ---------------------------------------------------
    #: full module gain, per frequency column
    gain: dict = field(default_factory=dict)
    #: design (operating) output level at the module, per frequency column
    design_output: dict = field(default_factory=dict)
    #: nominal / minimum module input level, per frequency column
    module_input: dict = field(default_factory=dict)
    #: dB added to a module input to obtain the housing input minimum
    housing_offset: float = 3.0
    noise_figure: dict = field(default_factory=dict)
    #: distortion id -> :class:`Distortion`
    distortions: dict = field(default_factory=dict)
    #: available plug-in pad values, dB (flat attenuation)
    pads: list = field(default_factory=list)
    #: available plug-in equalisers
    equalizers: list = field(default_factory=list)
    #: RF outputs
    outputs: list = field(default_factory=list)

    # -- return path ----------------------------------------------------
    return_capable: bool = True
    rtn_gain: dict = field(default_factory=dict)
    rtn_design_output: dict = field(default_factory=dict)
    rtn_module_input: dict = field(default_factory=dict)
    rtn_noise_figure: dict = field(default_factory=dict)
    rtn_distortions: dict = field(default_factory=dict)
    rtn_pads: list = field(default_factory=list)
    rtn_equalizers: list = field(default_factory=list)

    # -- powering -------------------------------------------------------
    #: "Powering data are entered in voltage-current pairs in ascending order
    #: of voltage for each device.  That is, for a given device, from Vmin to
    #: V2, it uses A1 amperes; from V2 to V3, A2 amperes are used."
    va_pairs: list = field(default_factory=list)
    max_amps: float = 15.0
    power_passing: bool = True
    #: minimum voltage the module will operate at
    min_voltage: float = 40.0

    price: float = 0.0
    labor: float = 0.0
    extra: dict = field(default_factory=dict)

    # ------------------------------------------------------------------
    def __post_init__(self) -> None:
        self.equalizers = [self._as_eq(e) for e in self.equalizers]
        self.rtn_equalizers = [self._as_eq(e) for e in self.rtn_equalizers]
        self.outputs = [self._as_port(p) for p in self.outputs]
        self.distortions = {
            k: self._as_dist(v) for k, v in (self.distortions or {}).items()
        }
        self.rtn_distortions = {
            k: self._as_dist(v) for k, v in (self.rtn_distortions or {}).items()
        }
        if not self.outputs:
            self.outputs = [OutputPort(name="OUT", loss={})]

    @staticmethod
    def _as_eq(raw) -> Equalizer:
        if isinstance(raw, Equalizer):
            return raw
        return Equalizer(
            value=float(raw.get("value", 0.0)),
            loss={str(k).upper(): float(v) for k, v in (raw.get("loss") or {}).items()},
            part_number=raw.get("part_number", ""),
        )

    @staticmethod
    def _as_port(raw) -> OutputPort:
        if isinstance(raw, OutputPort):
            return raw
        return OutputPort(
            name=raw.get("name", "OUT"),
            loss={str(k).upper(): float(v) for k, v in (raw.get("loss") or {}).items()},
        )

    @staticmethod
    def _as_dist(raw) -> Distortion:
        if isinstance(raw, Distortion):
            return raw
        if isinstance(raw, (int, float)):
            return Distortion(base=float(raw))
        ref = raw.get("ref_level")
        return Distortion(
            base=float(raw.get("base", 0.0)),
            ref_level=None if ref is None else float(ref),
        )

    # ------------------------------------------------------------------
    def housing_input_min(self, column: str) -> float:
        """Minimum level required at the end of the incoming cable."""
        return lookup(self.module_input, column) + float(self.housing_offset)

    def pad_values(self, direction: str = "forward") -> list[float]:
        pads = self.rtn_pads if direction == "return" else self.pads
        return sorted(float(p) for p in pads) or [0.0]

    def eq_list(self, direction: str = "forward") -> list[Equalizer]:
        eqs = self.rtn_equalizers if direction == "return" else self.equalizers
        return list(eqs) or [Equalizer(value=0.0, loss={})]

    def gains(self, direction: str = "forward") -> dict:
        return self.rtn_gain if direction == "return" else self.gain

    def targets(self, direction: str = "forward") -> dict:
        return (
            self.rtn_design_output if direction == "return" else self.design_output
        )

    def inputs(self, direction: str = "forward") -> dict:
        return (
            self.rtn_module_input if direction == "return" else self.module_input
        )

    # -- powering -------------------------------------------------------
    def current_at(self, volts: float, interpolation: str = "linear") -> float:
        """Current drawn at *volts*.

        With ``stair`` the classic step table is reproduced: from ``Vmin`` to
        ``V2`` the device draws ``A1``.  With ``linear`` the draw is
        interpolated, "eliminating the jumps that occur in the stair step
        method".  Outside the tabulated range the nearest entry is held.
        """
        pairs = sorted(
            ((float(v), float(a)) for v, a in self.va_pairs), key=lambda p: p[0]
        )
        if not pairs:
            return 0.0
        if len(pairs) == 1 or volts <= pairs[0][0]:
            return pairs[0][1]
        if volts >= pairs[-1][0]:
            return pairs[-1][1]
        for i in range(len(pairs) - 1):
            v0, a0 = pairs[i]
            v1, a1 = pairs[i + 1]
            if v0 <= volts <= v1:
                if interpolation == "stair":
                    return a0
                if v1 == v0:
                    return a0
                return a0 + (a1 - a0) * (volts - v0) / (v1 - v0)
        return pairs[-1][1]

    @property
    def watts_nominal(self) -> float:
        if not self.va_pairs:
            return 0.0
        v, a = max(self.va_pairs, key=lambda p: float(p[0]))
        return float(v) * float(a)


class ActivesSpec(SpecFile):
    KIND: ClassVar[str] = "actives"
    EXT: ClassVar[str] = ".act"
    ROW: ClassVar[type] = Active

    def validate(self) -> None:
        seen = set()
        for row in self.rows:
            if not row.id:
                raise SpecError("active rows require an id")
            if row.id in seen:
                raise SpecError(f"duplicate active id {row.id!r}")
            seen.add(row.id)
            if row.category not in CATEGORIES:
                raise SpecError(
                    f"active {row.id!r}: unknown category {row.category!r}; "
                    f"expected one of {CATEGORIES}"
                )
            if not row.gain and row.category != "node":
                raise SpecError(f"active {row.id!r} has no forward gain figures")

    def by_category(self, category: str) -> list[Active]:
        return [r for r in self.rows if r.category == category]
