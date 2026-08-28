"""TAPS spec file (``.tap``).

"In the Taps spec file, you will input loss values, insertion losses,
self-term, etc.  The taps will display the tap value within one of four
different types of brackets that identify the number of tap ports."

Taps are organised into **Tap Selection Groups**: "Tap Selection Group is a
1-99 value to specify the group to be used for tap selection as defined in the
Tap specs.  You can create a group by leaving a blank line between the tap
groups."  Here the grouping is explicit (a ``tsg`` field) rather than
positional, which is the same idea without the fragile blank-line encoding.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar

from .base import SpecError, SpecFile, lookup

#: Bracket styles the Design Assistant uses to show port count on screen.
PORT_BRACKETS = {2: ("[", "]"), 4: ("(", ")"), 8: ("{", "}"), 1: ("<", ">")}


@dataclass
class Tap:
    id: str = ""
    description: str = ""
    part_number: str = ""
    #: tap selection group (1-99)
    tsg: int = 1
    #: nominal tap value in dB -- the number printed on the map
    value: float = 0.0
    #: number of tap (subscriber) ports
    ports: int = 4
    #: loss from input to a tap port, per frequency column
    tap_loss: dict = field(default_factory=dict)
    #: through (insertion) loss input to output, per frequency column
    insertion_loss: dict = field(default_factory=dict)
    #: a self-terminating tap has no through port -- it ends the line
    self_terminating: bool = False
    #: powering
    max_amps: float = 15.0
    resistance: float = 0.0
    power_passing: bool = True
    price: float = 0.0
    labor: float = 0.0
    extra: dict = field(default_factory=dict)

    def port_loss(self, column: str) -> float:
        return lookup(self.tap_loss, column)

    def thru_loss(self, column: str) -> float:
        return lookup(self.insertion_loss, column)

    def bracket(self) -> tuple[str, str]:
        return PORT_BRACKETS.get(self.ports, ("[", "]"))

    def display(self) -> str:
        left, right = self.bracket()
        return f"{left}{self.value:g}{right}"


class TapsSpec(SpecFile):
    KIND: ClassVar[str] = "taps"
    EXT: ClassVar[str] = ".tap"
    ROW: ClassVar[type] = Tap

    def validate(self) -> None:
        seen = set()
        for row in self.rows:
            if not row.id:
                raise SpecError("tap rows require an id")
            if row.id in seen:
                raise SpecError(f"duplicate tap id {row.id!r}")
            seen.add(row.id)
            if row.ports <= 0:
                raise SpecError(f"tap {row.id!r} must have at least one port")

    # -- tap selection groups -------------------------------------------
    def groups(self) -> dict[int, list[Tap]]:
        out: dict[int, list[Tap]] = {}
        for row in self.rows:
            out.setdefault(int(row.tsg), []).append(row)
        return out

    def group(self, tsg: int, ports: int | None = None) -> list[Tap]:
        """Taps in *tsg*, optionally filtered to a port count.

        Returned in ascending tap value, which is the order the ``+`` key
        walks through in Design Mode ("pressing the + key will change it to
        the next higher value tap").
        """
        rows = [r for r in self.rows if int(r.tsg) == int(tsg)]
        if ports is not None:
            rows = [r for r in rows if r.ports == ports]
        return sorted(rows, key=lambda r: (r.value, r.ports))

    def port_counts(self, tsg: int) -> list[int]:
        return sorted({r.ports for r in self.rows if int(r.tsg) == int(tsg)})

    def find_value(self, value: float, ports: int, tsg: int = 1,
                   self_terminating: bool | None = None) -> Tap | None:
        """The tap of a given *value* -- what a designer actually types.

        Designers work in tap values ("put a 17 there"), not part numbers.
        Falls back to the nearest stocked value in the group, and to any port
        count in the group if that exact one is not carried.
        """
        group = self.group(tsg, ports)
        if self_terminating is not None:
            filtered = [t for t in group if t.self_terminating == self_terminating]
            group = filtered or group
        if not group:
            group = self.group(tsg)
            if self_terminating is not None:
                filtered = [t for t in group
                            if t.self_terminating == self_terminating]
                group = filtered or group
        if not group:
            return None
        return min(group, key=lambda t: (abs(t.value - float(value)),
                                         abs(t.ports - ports)))

    def values(self, tsg: int = 1, ports: int | None = None) -> list[float]:
        """The stocked tap values in a group, ascending."""
        rows = self.group(tsg, ports)
        return sorted({t.value for t in rows})
