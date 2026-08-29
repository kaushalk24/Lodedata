"""Loading, holding and switching complete sets of specification files.

Three concepts from the Design Assistant are reproduced here:

**Spec set** -- "in order for the program to calculate a network properly you
must have a PARAMETERS, TAPS, ACTIVE, COUPLERS, and CABLES spec file"; PRICING
and PERFORMANCE are optional.  :class:`SpecSet` is that bundle, plus the
cross-file consistency checks the originals leave to the user.

**Project settings** (``.dap``, "Design Assistant Project") -- "Setting up
your project settings paths properly will ensure that the Design Assistant
will always be able to find the desired specification and network files."

**Xspec** (``.xsp``) -- "a file that stores up to ten different sets of
specification files for quick and easy access ... To load any set of specs
listed in the Xspec file press the corresponding line number 0 through 9."
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

from .actives import ActivesSpec
from .base import SpecError
from .cables import CablesSpec
from .couplers import CouplersSpec
from .parameters import ParametersSpec
from .performance import PerformanceSpec
from .pricing import PricingSpec
from .taps import TapsSpec

#: attribute name -> (spec class, required?)
SPEC_KINDS = {
    "parameters": (ParametersSpec, True),
    "actives": (ActivesSpec, True),
    "taps": (TapsSpec, True),
    "couplers": (CouplersSpec, True),
    "cables": (CablesSpec, True),
    "performance": (PerformanceSpec, False),
    "pricing": (PricingSpec, False),
}

EXT_TO_KIND = {cls.EXT: kind for kind, (cls, _) in SPEC_KINDS.items()}


@dataclass
class SpecSet:
    """One complete, loaded set of specification files."""

    parameters: ParametersSpec = field(default_factory=ParametersSpec.default)
    actives: ActivesSpec = field(default_factory=ActivesSpec)
    taps: TapsSpec = field(default_factory=TapsSpec)
    couplers: CouplersSpec = field(default_factory=CouplersSpec)
    cables: CablesSpec = field(default_factory=CablesSpec)
    performance: PerformanceSpec = field(default_factory=PerformanceSpec.default)
    pricing: PricingSpec = field(default_factory=PricingSpec)
    name: str = "untitled"
    directory: str = ""

    # ------------------------------------------------------------------
    # loading
    # ------------------------------------------------------------------
    @classmethod
    def load_dir(cls, directory: str, name: str = "") -> "SpecSet":
        """Load every spec file found in *directory* (by file extension)."""
        directory = os.path.abspath(directory)
        if not os.path.isdir(directory):
            raise SpecError(f"spec directory not found: {directory}")
        found: dict[str, str] = {}
        for entry in sorted(os.listdir(directory)):
            ext = os.path.splitext(entry)[1].lower()
            kind = EXT_TO_KIND.get(ext)
            if kind and kind not in found:
                found[kind] = os.path.join(directory, entry)
        return cls.load_files(found, name=name or os.path.basename(directory),
                              directory=directory)

    @classmethod
    def load_files(cls, paths: dict, name: str = "untitled",
                   directory: str = "") -> "SpecSet":
        """Load a spec set from an explicit ``{kind: path}`` mapping."""
        kwargs = {}
        missing = []
        for kind, (spec_cls, required) in SPEC_KINDS.items():
            path = paths.get(kind)
            if not path:
                if required:
                    missing.append(kind)
                continue
            if directory and not os.path.isabs(path):
                path = os.path.join(directory, path)
            kwargs[kind] = spec_cls.load(path)
        if missing:
            raise SpecError(
                "spec set is incomplete -- the Design Assistant needs a "
                + ", ".join(sorted(missing))
                + " spec file to calculate a network"
            )
        obj = cls(name=name, directory=directory, **kwargs)
        obj.validate()
        return obj

    def save_dir(self, directory: str) -> dict:
        """Write every loaded file into *directory*, named after the set."""
        os.makedirs(directory, exist_ok=True)
        written = {}
        for kind, (spec_cls, _) in SPEC_KINDS.items():
            spec = getattr(self, kind)
            if spec is None:
                continue
            path = os.path.join(directory, f"{self.name}{spec_cls.EXT}")
            spec.save(path)
            written[kind] = path
        self.directory = os.path.abspath(directory)
        return written

    # ------------------------------------------------------------------
    # cross-file validation
    # ------------------------------------------------------------------
    def validate(self) -> list[str]:
        """Cross-check the files against each other; returns warnings.

        Hard structural problems raise :class:`SpecError`; anything merely
        suspicious (a missing frequency column on one part, an unpriced item)
        is returned as a warning so the designer can decide.
        """
        for kind, (_, required) in SPEC_KINDS.items():
            spec = getattr(self, kind)
            if spec is None and required:
                raise SpecError(f"missing required {kind} spec file")
            if spec is not None:
                spec.validate()

        params = self.parameters
        columns = set(params.all_columns)
        warnings: list[str] = []

        def check(container, label: str, mapping: dict, needed=None) -> None:
            need = set(needed if needed is not None else columns)
            if not mapping:
                return
            if "*" in mapping:
                return
            gap = need - set(mapping)
            if gap:
                warnings.append(
                    f"{label} {container!r} has no value for "
                    f"{', '.join(sorted(gap))}"
                )

        for cable in self.cables:
            check(cable.id, "cable", cable.atten)
        for tap in self.taps:
            check(tap.id, "tap", tap.tap_loss)
            if not tap.self_terminating:
                check(tap.id, "tap", tap.insertion_loss)
        for cpl in self.couplers:
            check(cpl.id, "coupler", cpl.thru_loss)
            if cpl.tap_legs:
                check(cpl.id, "coupler", cpl.tap_loss)
        fwd = set(params.forward_columns)
        rtn = set(params.return_columns)
        for act in self.actives:
            if act.category != "node":
                check(act.id, "active", act.gain, fwd)
            check(act.id, "active", act.design_output, fwd)
            if act.return_capable and rtn:
                check(act.id, "active", act.rtn_design_output, rtn)
            for imp in self.performance.enabled_rows("forward"):
                if imp.from_noise_figure:
                    if act.category != "node" and not act.noise_figure:
                        warnings.append(
                            f"active {act.id!r} has no noise figure, so "
                            f"{imp.id} cannot be calculated"
                        )
                elif imp.id not in act.distortions and act.category != "node":
                    warnings.append(
                        f"active {act.id!r} has no {imp.id} specification"
                    )
        for ident in (params.default_cable, params.default_trunk_cable):
            if ident and self.cables.by_id(ident) is None:
                warnings.append(f"default cable {ident!r} is not in the cables file")
        if params.default_active and self.actives.by_id(params.default_active) is None:
            warnings.append(
                f"default active {params.default_active!r} is not in the actives file"
            )
        return warnings

    # ------------------------------------------------------------------
    def summary(self) -> dict:
        return {
            "name": self.name,
            "directory": self.directory,
            "parameters": self.parameters.name,
            "counts": {
                "actives": len(self.actives),
                "taps": len(self.taps),
                "couplers": len(self.couplers),
                "cables": len(self.cables),
                "impairments": len(self.performance),
                "prices": len(self.pricing),
            },
            "forward_columns": self.parameters.forward_columns,
            "return_columns": self.parameters.return_columns,
        }


# ---------------------------------------------------------------------------
# project settings (.dap)
# ---------------------------------------------------------------------------

@dataclass
class ProjectSettings:
    """"The Project Settings file has a file extension of .DAP"."""

    name: str = "untitled"
    spec_dir: str = "specs"
    network_dir: str = "networks"
    report_dir: str = "reports"
    spec_files: dict = field(default_factory=dict)
    notes: str = ""
    source: str = ""

    @classmethod
    def load(cls, path: str) -> "ProjectSettings":
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        obj = cls(
            name=data.get("name", "untitled"),
            spec_dir=data.get("spec_dir", "specs"),
            network_dir=data.get("network_dir", "networks"),
            report_dir=data.get("report_dir", "reports"),
            spec_files=data.get("spec_files", {}),
            notes=data.get("notes", ""),
            source=os.path.abspath(path),
        )
        return obj

    def save(self, path: str) -> str:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({
                "kind": "project",
                "name": self.name,
                "spec_dir": self.spec_dir,
                "network_dir": self.network_dir,
                "report_dir": self.report_dir,
                "spec_files": self.spec_files,
                "notes": self.notes,
            }, fh, indent=2)
            fh.write("\n")
        self.source = os.path.abspath(path)
        return self.source

    def resolve(self, base: str = "") -> str:
        base = base or (os.path.dirname(self.source) if self.source else os.getcwd())
        return os.path.normpath(os.path.join(base, self.spec_dir))

    def load_specs(self, base: str = "") -> SpecSet:
        """"SET ALL FILES" -- load the whole set this project points at."""
        if self.spec_files:
            directory = self.resolve(base)
            return SpecSet.load_files(self.spec_files, name=self.name,
                                      directory=directory)
        return SpecSet.load_dir(self.resolve(base), name=self.name)


# ---------------------------------------------------------------------------
# Xspec (.xsp)
# ---------------------------------------------------------------------------

@dataclass
class XspecEntry:
    line: int = 0
    name: str = ""
    directory: str = ""
    files: dict = field(default_factory=dict)


@dataclass
class Xspec:
    """Ten quick-access spec sets, addressed by line number 0-9."""

    entries: list = field(default_factory=list)
    source: str = ""

    @classmethod
    def load(cls, path: str) -> "Xspec":
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        entries = [
            XspecEntry(
                line=int(e.get("line", i)),
                name=e.get("name", ""),
                directory=e.get("directory", ""),
                files=e.get("files", {}),
            )
            for i, e in enumerate(data.get("entries", []))
        ]
        return cls(entries=entries, source=os.path.abspath(path))

    def save(self, path: str) -> str:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({
                "kind": "xspec",
                "entries": [
                    {"line": e.line, "name": e.name,
                     "directory": e.directory, "files": e.files}
                    for e in self.entries
                ],
            }, fh, indent=2)
            fh.write("\n")
        self.source = os.path.abspath(path)
        return self.source

    def entry(self, line: int) -> XspecEntry | None:
        for e in self.entries:
            if e.line == line:
                return e
        return None

    def load_line(self, line: int, base: str = "") -> SpecSet:
        entry = self.entry(line)
        if entry is None:
            raise SpecError(f"Xspec line {line} is empty")
        base = base or (os.path.dirname(self.source) if self.source else os.getcwd())
        directory = os.path.normpath(os.path.join(base, entry.directory))
        if entry.files:
            return SpecSet.load_files(entry.files, name=entry.name,
                                      directory=directory)
        return SpecSet.load_dir(directory, name=entry.name)
