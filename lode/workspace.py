"""A workspace ties spec sets, networks and reports together.

This is the "Project Settings" idea made concrete: one directory holding
``specs/`` (one sub-directory per equipment library), ``networks/`` (``.dsn``
designs) and ``reports/``.  Both the command line and the web front end drive
the application through this class, so they always behave identically.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from .engine.autodesign import AutoDesigner
from .engine.levels import LevelEngine, Solution
from .engine.performance import PerformanceEngine
from .engine.powering import PoweringEngine
from .network import Network
from .reports import REPORTS, ReportBuilder
from .specs import ProjectSettings, SpecError, SpecSet


@dataclass
class Analysis:
    """Everything the engines produce for one network."""

    solution: Solution
    performance: dict = field(default_factory=dict)
    powering: list = field(default_factory=list)
    performance_flags: list = field(default_factory=list)

    @property
    def all_flags(self) -> list:
        flags = list(self.solution.flags) + list(self.performance_flags)
        for area in self.powering:
            flags.extend(area.flags)
        return flags

    def to_dict(self) -> dict:
        return {
            "solution": self.solution.to_dict(),
            "performance": {k: v.to_dict() for k, v in self.performance.items()},
            "powering": [a.to_dict() for a in self.powering],
            "flags": [f.to_dict() for f in self.all_flags],
        }


class Workspace:
    def __init__(self, root: str = "."):
        self.root = os.path.abspath(root)
        self.spec_root = os.path.join(self.root, "specs")
        self.network_root = os.path.join(self.root, "networks")
        self.report_root = os.path.join(self.root, "reports")
        self._specs: dict[str, SpecSet] = {}

    # ------------------------------------------------------------------
    def ensure(self) -> None:
        for path in (self.spec_root, self.network_root, self.report_root):
            os.makedirs(path, exist_ok=True)

    # -- spec sets -------------------------------------------------------
    def spec_sets(self) -> list[str]:
        if not os.path.isdir(self.spec_root):
            return []
        return sorted(
            name for name in os.listdir(self.spec_root)
            if os.path.isdir(os.path.join(self.spec_root, name))
        )

    def load_specs(self, name: str = "", reload: bool = False) -> SpecSet:
        available = self.spec_sets()
        if not name:
            if not available:
                raise SpecError(
                    f"no spec sets found in {self.spec_root}; run "
                    f"'lode init' to create a starter workspace"
                )
            name = available[0]
        if name in self._specs and not reload:
            return self._specs[name]
        path = os.path.join(self.spec_root, name)
        if not os.path.isdir(path):
            path = name  # allow an explicit directory
        spec_set = SpecSet.load_dir(path, name=os.path.basename(path.rstrip("/")))
        self._specs[name] = spec_set
        return spec_set

    # -- networks --------------------------------------------------------
    def networks(self) -> list[str]:
        if not os.path.isdir(self.network_root):
            return []
        return sorted(
            os.path.splitext(name)[0]
            for name in os.listdir(self.network_root)
            if name.endswith(".dsn")
        )

    def network_path(self, name: str) -> str:
        if os.path.sep in name or name.endswith(".dsn"):
            return os.path.abspath(name)
        return os.path.join(self.network_root, f"{name}.dsn")

    def load_network(self, name: str) -> Network:
        return Network.load(self.network_path(name))

    def save_network(self, network: Network, name: str = "") -> str:
        self.ensure()
        return network.save(self.network_path(name or network.name))

    # ------------------------------------------------------------------
    def analyse(self, specs: SpecSet, network: Network,
                load_factor: float = 1.0,
                extra_load: dict | None = None) -> Analysis:
        """Run every engine over *network*."""
        solution = LevelEngine(specs, network).solve()
        perf_engine = PerformanceEngine(specs, network, solution)
        performance = perf_engine.solve()
        perf_flags = perf_engine.flags(performance)
        powering = PoweringEngine(
            specs, network, load_factor=load_factor, extra_load=extra_load
        ).solve()
        return Analysis(solution=solution, performance=performance,
                        powering=powering, performance_flags=perf_flags)

    def design(self, specs: SpecSet, network: Network):
        return AutoDesigner(specs, network).full_design()

    def reports(self, specs: SpecSet, network: Network,
                analysis: Analysis) -> ReportBuilder:
        return ReportBuilder(specs, network, analysis.solution,
                             analysis.performance, analysis.powering)

    def report(self, specs: SpecSet, network: Network, analysis: Analysis,
               name: str):
        builder = self.reports(specs, network, analysis)
        method = REPORTS.get(name)
        if method is None:
            raise KeyError(
                f"unknown report {name!r}; choose from {', '.join(sorted(REPORTS))}"
            )
        return getattr(builder, method)()

    # ------------------------------------------------------------------
    def settings(self) -> ProjectSettings:
        return ProjectSettings(
            name=os.path.basename(self.root),
            spec_dir="specs", network_dir="networks", report_dir="reports",
        )
