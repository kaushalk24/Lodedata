"""COUPLERS spec file (``.cpl``).

"The four columns to the right of that labeled Thru are used to enter the thru
leg losses at the forward high, forward low, return high, and return low
frequencies, respectively.  In the next column, labeled Tap Legs, enter the
number of tap legs available for the coupler."

A balanced two-way splitter is a coupler with one tap leg whose tap loss
equals its thru loss; a directional coupler has a low-loss thru leg and a
high-loss tap leg.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar

from .base import SpecError, SpecFile, lookup


@dataclass
class Coupler:
    id: str = ""
    description: str = ""
    part_number: str = ""
    #: ``splitter``, ``dc`` (directional coupler), ``power_inserter`` or
    #: ``passive`` (a plain in-line device such as a splice or equaliser)
    kind: str = "splitter"
    #: loss on the through leg, per frequency column
    thru_loss: dict = field(default_factory=dict)
    #: number of tap legs available
    tap_legs: int = 1
    #: loss on each tap leg, per frequency column
    tap_loss: dict = field(default_factory=dict)
    #: powering
    max_amps: float = 15.0
    resistance: float = 0.0
    power_passing: bool = True
    #: a power block stops AC at this point (used for powering areas)
    power_block: bool = False
    price: float = 0.0
    labor: float = 0.0
    extra: dict = field(default_factory=dict)

    @property
    def legs(self) -> int:
        """Total number of outputs (thru leg plus tap legs)."""
        return 1 + int(self.tap_legs)

    def leg_loss(self, column: str, leg: int) -> float:
        """Loss to output *leg*; leg 0 is the thru leg."""
        if leg <= 0:
            return lookup(self.thru_loss, column)
        return lookup(self.tap_loss, column)

    def leg_name(self, leg: int) -> str:
        return "THRU" if leg <= 0 else f"TAP{leg}"


class CouplersSpec(SpecFile):
    KIND: ClassVar[str] = "couplers"
    EXT: ClassVar[str] = ".cpl"
    ROW: ClassVar[type] = Coupler

    def validate(self) -> None:
        seen = set()
        for row in self.rows:
            if not row.id:
                raise SpecError("coupler rows require an id")
            if row.id in seen:
                raise SpecError(f"duplicate coupler id {row.id!r}")
            seen.add(row.id)
            if row.tap_legs < 0:
                raise SpecError(f"coupler {row.id!r} has a negative tap leg count")
