"""CABLES spec file (``.cab``).

"The High, Low, Rh, Rl per 100ft columns contain attenuation factors for each
specific cable type, where High refers to the forward high frequency; Low, the
forward low; Rh, the return high; and Rl the return low frequency."  ...
"Loop Res./1000 refers to electrical loop resistance in Ohms per 1000 feet, or
per 1000 meters if meters had been specified in the Parameters."
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar

from .base import SpecError, SpecFile, lookup


@dataclass
class Cable:
    id: str = ""
    description: str = ""
    part_number: str = ""
    #: attenuation in dB per 100 distance-units, keyed by frequency column
    atten: dict = field(default_factory=dict)
    #: loop resistance in ohms per 1000 distance-units (powering)
    loop_res: float = 0.0
    #: nominal diameter, informational
    size: str = ""
    #: velocity of propagation, informational
    vop: float = 87.0
    price: float = 0.0
    connector_price: float = 0.0
    labor: float = 0.0
    extra: dict = field(default_factory=dict)

    def loss(self, column: str, length: float, factor: float = 1.0) -> float:
        """dB of loss for *length* distance-units at *column*."""
        return lookup(self.atten, column) * (length / 100.0) * factor

    def resistance(self, length: float) -> float:
        """Loop resistance in ohms for *length* distance-units."""
        return self.loop_res * (length / 1000.0)


class CablesSpec(SpecFile):
    KIND: ClassVar[str] = "cables"
    EXT: ClassVar[str] = ".cab"
    ROW: ClassVar[type] = Cable

    def validate(self) -> None:
        seen = set()
        for row in self.rows:
            if not row.id:
                raise SpecError("cable rows require an id")
            if row.id in seen:
                raise SpecError(f"duplicate cable id {row.id!r}")
            seen.add(row.id)
            if not row.atten:
                raise SpecError(f"cable {row.id!r} has no attenuation factors")
