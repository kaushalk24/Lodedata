"""PERFORMANCE spec file (``.prf``).

This file defines how every impairment is *derated* with operating level and
how contributors are *combined* down a cascade.  Straight from the manual:

* "The addition factor for carrier to noise is 10 because it is calculated
  using a 10 log rule.  The addition factor for composite triple beat is 20
  because it is calculated using a 20 log rule."
* "The derate factor represents the amount of degradation that occurs with a
  1 dB change in signal level.  A positive number will cause the Design
  Assistant to key off the input level for that particular distortion type,
  whereas a negative number will cause it to key off the output level."
* "Carrier to noise gets 1 dB worse for every 1 dB decrease in input level, so
  you would enter a positive 1 here for carrier to noise.  Composite triple
  beat gets 2 dB worse for every 1 dB increase in output level, so you would
  enter a negative 2 for composite triple beat."

Both statements collapse into one rule, implemented in
:meth:`Impairment.derate_spec`::

    spec_actual = spec_base + derate * (level_key - level_ref)

where ``level_key`` is the device's operating *input* level when the derate
factor is positive and its *output* level when it is negative.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar

from .base import SpecError, SpecFile


@dataclass
class Impairment:
    #: short key, matched against the ``distortions`` map of an active
    id: str = ""
    name: str = ""
    #: log rule used to add contributors: 10, 15 or 20
    addition_factor: float = 20.0
    #: dB of degradation per dB of level change (sign selects input/output)
    derate: float = -2.0
    #: design objective, in dB below carrier, used for pass/fail reporting
    objective: float = 0.0
    #: carrier-to-noise is computed from the noise figure rather than a
    #: tabulated single-unit spec:  C/N[1] = k + input - noise figure
    from_noise_figure: bool = False
    #: the constant ``k`` above (59 in the manual's worked example)
    noise_constant: float = 59.0
    #: ``forward`` or ``return``
    direction: str = "forward"
    enabled: bool = True
    extra: dict = field(default_factory=dict)

    @property
    def keys_off_input(self) -> bool:
        """True when the derate factor keys off the device input level."""
        return self.derate >= 0

    def derate_spec(self, base: float, input_level: float, output_level: float) -> float:
        """Apply the derate rule to a single-unit *base* spec."""
        key = input_level if self.keys_off_input else output_level
        ref = self.reference_level
        if ref is None:
            return base
        return base + self.derate * (key - ref)

    #: filled in per-device at calculation time
    reference_level: float | None = None


class PerformanceSpec(SpecFile):
    KIND: ClassVar[str] = "performance"
    EXT: ClassVar[str] = ".prf"
    ROW: ClassVar[type] = Impairment

    def validate(self) -> None:
        seen = set()
        for row in self.rows:
            if not row.id:
                raise SpecError("impairment rows require an id")
            if row.id in seen:
                raise SpecError(f"duplicate impairment id {row.id!r}")
            seen.add(row.id)
            if row.addition_factor <= 0:
                raise SpecError(
                    f"impairment {row.id!r}: addition factor must be positive"
                )

    def enabled_rows(self, direction: str = "forward") -> list[Impairment]:
        return [
            r for r in self.rows
            if r.enabled and r.direction in (direction, "both")
        ]

    @classmethod
    def default(cls) -> "PerformanceSpec":
        """The classic four-impairment table."""
        return cls(
            name="default",
            description="carrier-to-noise, CTB, CSO and cross-modulation",
            rows=[
                Impairment("CN", "Carrier / Noise", 10.0, 1.0, 49.0,
                           from_noise_figure=True),
                Impairment("CTB", "Composite Triple Beat", 20.0, -2.0, 53.0),
                Impairment("CSO", "Composite Second Order", 15.0, -1.0, 53.0),
                Impairment("XMOD", "Cross Modulation", 20.0, -2.0, 51.0),
                Impairment("RCN", "Return Carrier / Noise", 10.0, 1.0, 43.0,
                           from_noise_figure=True, direction="return"),
            ],
        )
