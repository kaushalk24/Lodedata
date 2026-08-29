"""PRICING spec file (``.prc``).

Optional file that puts material and labour costs against every part number so
that the Bill of Materials report can be costed.  Entries are matched to a
device by ``id`` first and by ``part_number`` second, so a single pricing file
can be shared across equipment libraries.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar

from .base import SpecError, SpecFile


@dataclass
class PriceItem:
    id: str = ""
    part_number: str = ""
    description: str = ""
    category: str = ""
    unit: str = "each"
    material: float = 0.0
    labor: float = 0.0
    extra: dict = field(default_factory=dict)

    @property
    def total(self) -> float:
        return self.material + self.labor


class PricingSpec(SpecFile):
    KIND: ClassVar[str] = "pricing"
    EXT: ClassVar[str] = ".prc"
    ROW: ClassVar[type] = PriceItem

    def validate(self) -> None:
        for row in self.rows:
            if not row.id and not row.part_number:
                raise SpecError("pricing rows require an id or a part number")

    def price_for(self, ident: str, part_number: str = "") -> PriceItem | None:
        for row in self.rows:
            if ident and row.id == ident:
                return row
        for row in self.rows:
            if part_number and row.part_number == part_number:
                return row
        return None
