"""Common machinery for the seven Design Assistant specification files.

Lode Data's Design Assistant is driven by *spec files*: "Spec files are the
backbone of The Design Assistant, and in order for the program to calculate a
network properly you must have a PARAMETERS, TAPS, ACTIVE, COUPLERS, and
CABLES spec file."  Two further optional files -- PRICING and PERFORMANCE --
complete the set of seven.

Every spec file in this implementation is a small, human-readable JSON
document with a header block and a list of rows.  Each file type also has a
lossless CSV projection so the tables can be edited in a spreadsheet, which is
how most designers actually maintain equipment libraries.

File extensions mirror the originals::

    .par  Parameters      .act  Actives     .tap  Taps
    .cpl  Couplers        .cab  Cables      .prc  Pricing
    .prf  Performance     .xsp  Xspec       .dap  Project settings
    .dsn  Network (design)
"""

from __future__ import annotations

import csv
import dataclasses
import io
import json
import os
from dataclasses import dataclass, field, fields, is_dataclass
from typing import Any, ClassVar, Iterator, Sequence


class SpecError(Exception):
    """Raised when a spec file is malformed or internally inconsistent."""


# ---------------------------------------------------------------------------
# (de)serialisation helpers
# ---------------------------------------------------------------------------

def _encode(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return {f.name: _encode(getattr(value, f.name)) for f in fields(value)}
    if isinstance(value, dict):
        return {str(k): _encode(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_encode(v) for v in value]
    return value


def _decode(cls: type, value: Any) -> Any:
    """Rebuild dataclass *cls* from plain JSON *value*, tolerating extra keys."""
    if not is_dataclass(cls):
        return value
    known = {f.name: f for f in fields(cls)}
    kwargs: dict[str, Any] = {}
    for name, f in known.items():
        if name not in value:
            continue
        raw = value[name]
        ftype = f.type
        # dataclass-typed members are declared by class, not by string, in the
        # spec modules, so a direct issubclass check is enough.
        if isinstance(ftype, type) and is_dataclass(ftype):
            kwargs[name] = _decode(ftype, raw)
        else:
            kwargs[name] = raw
    unknown = set(value) - set(known)
    if unknown and "extra" in known:
        kwargs.setdefault("extra", {}).update({k: value[k] for k in unknown})
    return cls(**kwargs)


@dataclass
class SpecFile:
    """Base class for a loaded specification file."""

    #: short kind name, e.g. ``"taps"``
    KIND: ClassVar[str] = "spec"
    #: canonical file extension, e.g. ``".tap"``
    EXT: ClassVar[str] = ".spec"
    #: dataclass used for each row (``None`` for single-record files)
    ROW: ClassVar[type | None] = None

    name: str = "untitled"
    description: str = ""
    version: str = "1.0"
    source: str = ""  # path this file was loaded from
    rows: list = field(default_factory=list)

    # -- dict/JSON -------------------------------------------------------
    def to_dict(self) -> dict:
        data = {
            "kind": self.KIND,
            "name": self.name,
            "description": self.description,
            "version": self.version,
        }
        payload = self._payload()
        data.update(payload)
        return data

    def _payload(self) -> dict:
        return {"rows": [_encode(r) for r in self.rows]}

    @classmethod
    def from_dict(cls, data: dict, source: str = "") -> "SpecFile":
        kind = data.get("kind")
        if kind and kind != cls.KIND:
            raise SpecError(
                f"expected a {cls.KIND!r} spec file but found {kind!r}"
            )
        obj = cls(
            name=data.get("name", "untitled"),
            description=data.get("description", ""),
            version=data.get("version", "1.0"),
            source=source,
        )
        obj._load_payload(data)
        obj.validate()
        return obj

    def _load_payload(self, data: dict) -> None:
        row_cls = self.ROW
        if row_cls is None:
            return
        self.rows = [_decode(row_cls, r) for r in data.get("rows", [])]

    # -- files -----------------------------------------------------------
    @classmethod
    def load(cls, path: str) -> "SpecFile":
        with open(path, "r", encoding="utf-8") as fh:
            try:
                data = json.load(fh)
            except json.JSONDecodeError as exc:
                raise SpecError(f"{path}: not valid JSON ({exc})") from exc
        return cls.from_dict(data, source=os.path.abspath(path))

    def save(self, path: str) -> str:
        tmp = f"{path}.tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(self.to_dict(), fh, indent=2)
            fh.write("\n")
        os.replace(tmp, path)
        self.source = os.path.abspath(path)
        return self.source

    # -- CSV projection --------------------------------------------------
    CSV_COLUMNS: ClassVar[Sequence[str]] = ()

    def to_csv(self) -> str:
        """Flatten rows to CSV (the spreadsheet view of the grid)."""
        buf = io.StringIO()
        cols = list(self.csv_columns())
        writer = csv.DictWriter(buf, fieldnames=cols, extrasaction="ignore")
        writer.writeheader()
        for row in self.rows:
            writer.writerow(self.csv_row(row))
        return buf.getvalue()

    def csv_columns(self) -> Sequence[str]:
        if self.CSV_COLUMNS:
            return self.CSV_COLUMNS
        if self.rows and is_dataclass(self.rows[0]):
            return [f.name for f in fields(self.rows[0])]
        return []

    def csv_row(self, row) -> dict:
        out = {}
        for k, v in _encode(row).items():
            out[k] = json.dumps(v) if isinstance(v, (dict, list)) else v
        return out

    # -- validation ------------------------------------------------------
    def validate(self) -> None:
        """Raise :class:`SpecError` if the file is unusable."""

    # -- convenience -----------------------------------------------------
    def __iter__(self) -> Iterator:
        return iter(self.rows)

    def __len__(self) -> int:
        return len(self.rows)

    def by_id(self, ident: str):
        for row in self.rows:
            if getattr(row, "id", None) == ident:
                return row
        return None

    def require(self, ident: str):
        row = self.by_id(ident)
        if row is None:
            raise SpecError(
                f"{self.KIND} spec {self.name!r} has no entry with id {ident!r}"
            )
        return row

    @property
    def ids(self) -> list[str]:
        return [getattr(r, "id", "") for r in self.rows]


def freq_map(raw: Any, default: float = 0.0) -> dict[str, float]:
    """Normalise a per-frequency mapping such as ``{"F1": 1.2, "F2": 0.6}``."""
    if raw is None:
        return {}
    if isinstance(raw, (int, float)):
        return {"*": float(raw)}
    if isinstance(raw, dict):
        return {str(k).upper(): float(v) for k, v in raw.items()}
    raise SpecError(f"expected a per-frequency mapping, got {raw!r}")


def lookup(mapping: dict[str, float], column: str, default: float = 0.0) -> float:
    """Fetch *column* from a per-frequency mapping, honouring a ``"*"`` wildcard."""
    if not mapping:
        return default
    if column in mapping:
        return mapping[column]
    if "*" in mapping:
        return mapping["*"]
    return default
