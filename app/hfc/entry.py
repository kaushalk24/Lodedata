"""Resolving what you type in a tap, coupler or amp column against the spec set.

This is how equipment actually goes into a design: you type at the cell rather
than pick from a list.

    tap column       2.23   a 2-port 23 tap
                     4.23   a 4-port 23
                     8.20   an 8-port 20
                     23     a 23 tap, port count chosen from the house count
                     0      clear the cell

    coupler column   2      the coupler whose ID is 2, e.g. a 2-way splitter
                     3      a 3-way splitter
                     8      a DC-8
                     -8     the same DC with its legs swapped: the through
                            (low loss) leg goes to the branch and the tap
                            (high loss) leg carries on downstream
                     --3    or "=3": through leg to the right-most branch
                     0      clear the cell, removing the branch it created

    amp column       the Active ID from the spec set; 0 clears it
"""
from __future__ import annotations

import re

from .model import Library, TapType, PassiveType, ActiveType
from .plant import THROUGH_DOWNSTREAM, THROUGH_FIRST, THROUGH_SECOND

TAP_PORT_COUNTS = (2, 4, 6, 8)


class EntryError(ValueError):
    """What you typed does not name anything in the attached spec set."""


# --------------------------------------------------------------------------
def _ports_for_houses(houses: int) -> list:
    """Port counts worth trying for a house count, closest fit first.

    "Typically, you need 1 port for 1 house count, 2 ports for a 2 house
    count, and so on."
    """
    if houses <= 0:
        return [4, 2, 8, 6]
    fits = [p for p in TAP_PORT_COUNTS if p >= houses]
    return fits + [p for p in reversed(TAP_PORT_COUNTS) if p not in fits]


def resolve_tap(lib: Library, code: str, houses: int = 0) -> TapType | None:
    """`2.23` -> the 2-port 23 tap.  Returns None for a clear."""
    code = (code or "").strip()
    if code in ("", "0"):
        return None

    m = re.fullmatch(r"(\d+)\s*[.\-/]\s*(\d+(?:\.\d+)?)", code)
    if m:
        ports, value = int(m.group(1)), float(m.group(2))
        if ports not in TAP_PORT_COUNTS:
            raise EntryError(f"{ports} is not a tap port count — use 2, 4, 6 or 8")
        wanted = [ports]
    else:
        if not re.fullmatch(r"\d+(?:\.\d+)?", code):
            raise EntryError(f"'{code}' is not a tap: type ports.value, like 4.23")
        value = float(code)
        wanted = _ports_for_houses(houses)

    for ports in wanted:
        for tap in lib.taps.values():
            if tap.ports == ports and _same_value(tap, value):
                return tap
    have = sorted({int(t.tap_id or t.tap_value_db) for t in lib.taps.values()
                   if t.ports == wanted[0]})
    raise EntryError(
        f"no {wanted[0]}-port {value:g} tap in the spec set"
        + (f" — it has {', '.join(str(v) for v in have)}" if have else ""))


def _same_value(tap: TapType, value: float) -> bool:
    if tap.tap_id and abs(tap.tap_id - value) < 0.001:
        return True
    # a tap value entered as 15.5 shows as 15 on screen, so match either
    return abs(tap.tap_value_db - value) < 0.5


# --------------------------------------------------------------------------
def resolve_coupler(lib: Library, code: str) -> tuple:
    """`-8` -> (the DC-8, THROUGH_FIRST).  Returns (None, _) for a clear."""
    code = (code or "").strip()
    if code in ("", "0"):
        return None, THROUGH_DOWNSTREAM

    through = THROUGH_DOWNSTREAM
    if code.startswith("--") or code.startswith("="):
        through = THROUGH_SECOND
        code = code.lstrip("-=").strip()
    elif code.startswith("-"):
        through = THROUGH_FIRST
        code = code[1:].strip()

    if not re.fullmatch(r"\d+(?:\.\d+)?", code):
        raise EntryError(f"'{code}' is not a coupler ID")
    wanted = float(code)

    for part in lib.passives.values():
        if part.coupler_id and abs(part.coupler_id - wanted) < 0.001:
            return part, through
    have = sorted({p.coupler_id for p in lib.passives.values() if p.coupler_id})
    raise EntryError(
        f"no coupler with ID {wanted:g} in the spec set"
        + (f" — it has {', '.join(str(v) for v in have)}" if have else ""))


# --------------------------------------------------------------------------
def resolve_active(lib: Library, code: str) -> ActiveType | None:
    """An Active ID from the spec set.  Returns None for a clear."""
    code = (code or "").strip()
    if code in ("", "0"):
        return None
    if not re.fullmatch(r"\d+", code):
        raise EntryError(f"'{code}' is not an Active ID")
    wanted = int(code)
    for part in lib.actives.values():
        if part.active_id == wanted:
            return part
    have = sorted(p.active_id for p in lib.actives.values() if p.active_id)
    raise EntryError(
        f"no active with ID {wanted} in the spec set"
        + (f" — it has {', '.join(str(v) for v in have[:20])}" if have else ""))
