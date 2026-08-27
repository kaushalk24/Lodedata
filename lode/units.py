"""Units, dB arithmetic and display helpers.

The Design Assistant works in dBmV internally.  The Parameters spec file
decides whether levels are *displayed* in dBmV or dBuV, and whether distances
are expressed in feet, meters or decimeters.
"""

from __future__ import annotations

import math
from typing import Iterable

# ---------------------------------------------------------------------------
# distance
# ---------------------------------------------------------------------------

#: Multiplier that converts a stored distance into the "per 100 units" basis
#: used by the cable attenuation factors.  Attenuation is always quoted per
#: 100 distance-units, matching the Cables spec file ("per 100ft", or "per
#: 100 meters if meters had been specified in the Parameters").
DISTANCE_UNITS = ("feet", "meters", "decimeters")

FEET_PER_METER = 3.280839895013123


def to_feet(value: float, units: str) -> float:
    """Convert *value* expressed in *units* into feet."""
    if units == "feet":
        return value
    if units == "meters":
        return value * FEET_PER_METER
    if units == "decimeters":
        return value * FEET_PER_METER / 10.0
    raise ValueError(f"unknown distance unit: {units!r}")


def from_feet(value_ft: float, units: str) -> float:
    """Convert *value_ft* (feet) into *units*."""
    if units == "feet":
        return value_ft
    if units == "meters":
        return value_ft / FEET_PER_METER
    if units == "decimeters":
        return value_ft / FEET_PER_METER * 10.0
    raise ValueError(f"unknown distance unit: {units!r}")


# ---------------------------------------------------------------------------
# signal display
# ---------------------------------------------------------------------------

#: dBuV = dBmV + 60
DBUV_OFFSET = 60.0


def display_level(dbmv: float, signal_display: str) -> float:
    """Return *dbmv* converted for display (``dBmV`` or ``dBuV``)."""
    if signal_display.lower() in ("dbmv", "dbmV".lower()):
        return dbmv
    if signal_display.lower() == "dbuv":
        return dbmv + DBUV_OFFSET
    raise ValueError(f"unknown signal display: {signal_display!r}")


def store_level(displayed: float, signal_display: str) -> float:
    """Inverse of :func:`display_level`."""
    if signal_display.lower() == "dbmv":
        return displayed
    if signal_display.lower() == "dbuv":
        return displayed - DBUV_OFFSET
    raise ValueError(f"unknown signal display: {signal_display!r}")


# ---------------------------------------------------------------------------
# dB arithmetic
# ---------------------------------------------------------------------------

def log_combine(values: Iterable[float], addition_factor: float) -> float:
    """Combine impairment specs that are quoted *below carrier*.

    This is the core cascade rule of the Design Assistant's Performance file.
    Each impairment type carries an *addition factor* -- the "log rule" used
    when several contributors are summed:

    * carrier-to-noise adds on a **10 log** basis (power addition),
    * composite triple beat adds on a **20 log** basis (voltage addition),
    * composite second order is commonly **15 log** (partially coherent).

    For specs quoted as a positive "dB below carrier" figure (bigger is
    better) the combination of *n* contributors is::

        total = -X * log10( sum( 10 ** (-s_i / X) ) )

    A single contributor returns its own value; an empty cascade returns
    ``inf`` (perfect).
    """
    factor = float(addition_factor)
    if factor <= 0:
        raise ValueError("addition factor must be positive")
    acc = 0.0
    seen = False
    for spec in values:
        if spec is None or math.isinf(spec):
            continue
        seen = True
        acc += 10.0 ** (-float(spec) / factor)
    if not seen or acc <= 0.0:
        return math.inf
    return -factor * math.log10(acc)


def power_sum_db(values: Iterable[float]) -> float:
    """Sum absolute levels (dBmV) on a power basis."""
    acc = 0.0
    seen = False
    for v in values:
        if v is None:
            continue
        seen = True
        acc += 10.0 ** (float(v) / 10.0)
    if not seen or acc <= 0.0:
        return -math.inf
    return 10.0 * math.log10(acc)


def round_half_up(value: float, digits: int = 2) -> float:
    """Round like an engineer (0.005 -> 0.01), not like IEEE-754."""
    factor = 10.0 ** digits
    return math.floor(abs(value) * factor + 0.5) / factor * (1 if value >= 0 else -1)
