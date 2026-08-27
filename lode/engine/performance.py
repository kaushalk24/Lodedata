"""Distortion and noise cascade.

Every active in the path from the source to a point in the plant contributes
noise and distortion.  The Performance spec file says how each contribution
scales with operating level (the *derate factor*) and how contributions add
(the *addition factor*).  This module applies both and reports the result at
every tap -- the Design Assistant's Performance Distribution report, which
"provides a breakdown of the expected performance for each type of distortion
(c/n, ctb, etc) at every tap in the currently loaded network".

Carrier to noise
----------------
For an amplifier the single-unit figure is derived from the noise figure
rather than tabulated:  "the formula to calculate the single unit base
distortion level of carrier-to-noise for an amplifier that has an input of 11
and a noise figure of 9 is: C/N[1] = 59 + input - noise figure = 59 + 11 - 9 =
61".  Because the actual operating input is already in that expression, no
further derating is applied.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from ..network import Network
from ..specs import SpecSet, lookup
from ..units import log_combine
from .levels import ERROR, OK, WARN, Flag, Solution


@dataclass
class Contribution:
    """One active's contribution to one impairment."""

    location: str = ""
    label: str = ""
    device: str = ""
    impairment: str = ""
    base: float = 0.0
    derated: float = 0.0
    input_level: float = 0.0
    output_level: float = 0.0

    def to_dict(self) -> dict:
        return {
            "location": self.location, "label": self.label,
            "device": self.device, "impairment": self.impairment,
            "base": round(self.base, 2), "derated": round(self.derated, 2),
            "input_level": round(self.input_level, 2),
            "output_level": round(self.output_level, 2),
        }


@dataclass
class PerformanceResult:
    """Cascaded performance at one location."""

    location: str = ""
    label: str = ""
    kind: str = ""
    cascade: int = 0
    #: impairment id -> cascaded value in dB
    values: dict = field(default_factory=dict)
    #: impairment id -> margin against the design objective
    margins: dict = field(default_factory=dict)
    contributions: list = field(default_factory=list)
    status: str = OK

    def to_dict(self) -> dict:
        return {
            "location": self.location, "label": self.label, "kind": self.kind,
            "cascade": self.cascade,
            "values": {k: (None if math.isinf(v) else round(v, 2))
                       for k, v in self.values.items()},
            "margins": {k: round(v, 2) for k, v in self.margins.items()},
            "status": self.status,
            "contributions": [c.to_dict() for c in self.contributions],
        }


class PerformanceEngine:
    """Cascades the Performance file's impairments through a solved network."""

    def __init__(self, specs: SpecSet, network: Network, solution: Solution):
        self.specs = specs
        self.network = network
        self.solution = solution
        self.params = specs.parameters

    # ------------------------------------------------------------------
    def _single_unit(self, imp, device, res, direction: str) -> float | None:
        """The single-unit spec for *device*, derated to its operating levels."""
        if direction == "return":
            column = self.params.rtn_eq_high
            in_level = res.rtn_module_in.get(column)
            out_level = lookup(device.rtn_design_output, column)
            table = device.rtn_distortions
            noise_figure = lookup(device.rtn_noise_figure, column)
        else:
            column = self.params.fwd_eq_high
            in_level = res.module_in.get(column)
            out_level = res.module_out.get(column)
            table = device.distortions
            noise_figure = lookup(device.noise_figure, column)

        if in_level is None or out_level is None:
            return None

        entry = table.get(imp.id)
        if imp.from_noise_figure and entry is None:
            if not noise_figure:
                return None
            # C/N[1] = k + input - noise figure
            return imp.noise_constant + in_level - noise_figure
        if entry is None:
            return None
        imp.reference_level = entry.ref_level
        return imp.derate_spec(entry.base, in_level, out_level)

    # ------------------------------------------------------------------
    def solve(self, directions=("forward", "return")) -> dict:
        """Return ``{location_id: PerformanceResult}`` for the whole network."""
        out: dict[str, PerformanceResult] = {}
        net = self.network
        sol = self.solution

        # cache each active's contribution once
        cache: dict[tuple[str, str], Contribution] = {}
        for loc_id in sol.order:
            res = sol.results[loc_id]
            if res.kind not in ("active", "source"):
                continue
            device = self.specs.actives.by_id(res.device)
            if device is None:
                continue
            for direction in directions:
                for imp in self.specs.performance.enabled_rows(direction):
                    value = self._single_unit(imp, device, res, direction)
                    if value is None:
                        continue
                    column = (self.params.rtn_eq_high if direction == "return"
                              else self.params.fwd_eq_high)
                    entry = (device.rtn_distortions if direction == "return"
                             else device.distortions).get(imp.id)
                    cache[(loc_id, imp.id)] = Contribution(
                        location=loc_id, label=res.label, device=res.device,
                        impairment=imp.id,
                        base=entry.base if entry else value,
                        derated=value,
                        input_level=(res.rtn_module_in if direction == "return"
                                     else res.module_in).get(column, 0.0),
                        output_level=(lookup(device.rtn_design_output, column)
                                      if direction == "return"
                                      else res.module_out.get(column, 0.0)),
                    )

        impairments = []
        for direction in directions:
            impairments.extend(self.specs.performance.enabled_rows(direction))

        for loc_id in sol.order:
            res = sol.results[loc_id]
            chain = [
                ident for ident in net.path_to(loc_id)
                if sol.results[ident].kind in ("active", "source")
            ]
            entry = PerformanceResult(
                location=loc_id, label=res.label, kind=res.kind,
                cascade=len(chain),
            )
            for imp in impairments:
                parts = [cache[(a, imp.id)] for a in chain if (a, imp.id) in cache]
                if not parts:
                    continue
                total = log_combine((p.derated for p in parts),
                                    imp.addition_factor)
                entry.values[imp.id] = total
                if imp.objective:
                    entry.margins[imp.id] = total - imp.objective
                entry.contributions.extend(parts)
            out[loc_id] = entry
        return out

    # ------------------------------------------------------------------
    def flags(self, results: dict) -> list:
        """Raise a flag wherever a tap misses a design objective."""
        found = []
        margin = self.params.set_margin
        for loc_id, entry in results.items():
            if entry.kind != "tap":
                continue
            worst = OK
            for imp in self.specs.performance.rows:
                if not imp.enabled or not imp.objective:
                    continue
                value = entry.values.get(imp.id)
                if value is None or math.isinf(value):
                    continue
                if value < imp.objective:
                    severity = (WARN if (imp.objective - value) < margin
                                else ERROR)
                    worst = ERROR if severity == ERROR else (worst or WARN)
                    found.append(Flag(
                        severity, "performance", loc_id, entry.label, "",
                        f"tap {entry.label}: {imp.name or imp.id} is "
                        f"{value:.1f} dB against a {imp.objective:.1f} dB "
                        f"objective ({len(entry.contributions)} contributors, "
                        f"cascade of {entry.cascade})",
                        value=value, limit=imp.objective))
            entry.status = worst
        return found
