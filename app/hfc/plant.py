"""The network as Lode Data models it: branches of nodes.

From the manual's glossary:

  Node    "A logical (as opposed to physical) unit that corresponds to one line
           of the Entry, Power or Design screens... it can represent a pole for
           aerial plant, or a pedestal for underground plant.  Several nodes can
           be located at the same pole or pedestal."
  Branch  "one page on the display that begins from a coupler."

So a design is a list of branches, each a list of node lines, and a node
carrying a coupler starts a new branch.  Every screen -- Entry, Design and
Powering -- is that same list with different columns.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict

from .model import Library, DesignParameters, new_id

# how a branch number is drawn, which is also what it means
BRANCH_NORMAL = "normal"        # [n]
BRANCH_NO_FOOTAGE = "nofootage"  # (n)
BRANCH_BACKFEED = "backfeed"    # {n}
BRANCH_FORWARDFEED = "forwardfeed"  # <n>

BRANCH_BRACKETS = {
    BRANCH_NORMAL: "[]",
    BRANCH_NO_FOOTAGE: "()",
    BRANCH_BACKFEED: "{}",
    BRANCH_FORWARDFEED: "<>",
}

# a tap is drawn in the bracket style of its port count
TAP_BRACKETS = {2: "//", 4: "[]", 6: "{}", 8: "<>"}


def bracket(text: str, style: str) -> str:
    return f"{style[0]}{text}{style[1]}"


@dataclass
class TapPlacement:
    """One of the four tap slots on a node line."""
    part_id: str | None = None
    ports: int = 4
    value_db: float = 0.0


@dataclass
class CouplerPlacement:
    """A coupler on a node line, and the branch it creates."""
    part_id: str | None = None
    coupler_id: int = 0
    branch: int = 0
    style: str = BRANCH_NORMAL


# Which leg of a coupler carries the through (low-loss) path.  From the manual:
# "8[2]" sends the through leg downstream; "8 -[2]" a single minus sends it to
# the branch in the left-most coupler column; "3 =[2][3]" a double minus, which
# looks like an equals sign, sends it to the right-most.
THROUGH_DOWNSTREAM = 0
THROUGH_FIRST = 1
THROUGH_SECOND = 2
THROUGH_MARK = {THROUGH_DOWNSTREAM: "", THROUGH_FIRST: "-", THROUGH_SECOND: "="}


@dataclass
class Node:
    """One line of the screen."""
    seq: int = 0
    ftg: float = 0.0            # footage from the previous node
    hc: int = 0                 # house count
    cab: int = 0                # cable ID; even aerial, odd underground
    cab_part: str | None = None  # library id of the cable
    lv: int = 0                 # which System Levels set applies here
    tsg: int = 0                # tap selection group, 0 = the file default
    amp: str = ""               # Active ID placed here, "" = none
    amp_part: str | None = None
    amp_label: str = ""         # from the Amplifier Definition window
    pads: list = field(default_factory=list)   # fwd pad, ret pad, fwd EQ, ret EQ as stored
    taps: list = field(default_factory=list)      # up to 4 TapPlacement
    couplers: list = field(default_factory=list)  # up to 2 CouplerPlacement
    through_leg: int = THROUGH_DOWNSTREAM
    map: str = ""
    loc: str = ""
    address: str = ""
    note: str = ""
    supply_volts: float = 0.0   # a power supply placed on this node
    supply_label: str = ""      # its name, e.g. "A"
    supply_part: str | None = None
    power_stop: bool = False    # stops power in the span leading to this node

    def to_dict(self) -> dict:
        d = asdict(self)
        d["taps"] = [asdict(t) for t in self.taps]
        d["couplers"] = [asdict(c) for c in self.couplers]
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Node":
        d = dict(d)
        if not isinstance(d.get("amp", ""), str):
            d["amp"] = str(d["amp"]) if d["amp"] else ""
        d["taps"] = [TapPlacement(**t) for t in d.get("taps") or []]
        d["couplers"] = [CouplerPlacement(**c) for c in d.get("couplers") or []]
        return cls(**d)


@dataclass
class Branch:
    """A run of nodes beginning at a coupler."""
    number: int = 1
    parent_branch: int = 0      # 0 for the feeder
    parent_node: int = 0        # node index in the parent that carries the coupler
    style: str = BRANCH_NORMAL
    label: str = ""
    nodes: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"number": self.number, "parent_branch": self.parent_branch,
                "parent_node": self.parent_node, "style": self.style,
                "label": self.label, "nodes": [n.to_dict() for n in self.nodes]}

    @classmethod
    def from_dict(cls, d: dict) -> "Branch":
        b = cls(number=d.get("number", 1), parent_branch=d.get("parent_branch", 0),
                parent_node=d.get("parent_node", 0),
                style=d.get("style", BRANCH_NORMAL), label=d.get("label", ""))
        b.nodes = [Node.from_dict(n) for n in d.get("nodes") or []]
        return b


def _parameters(d: dict) -> DesignParameters:
    """Stored parameters, ignoring settings this version no longer has."""
    known = DesignParameters.__dataclass_fields__
    return DesignParameters(**{k: v for k, v in d.items() if k in known})


@dataclass
class Design:
    """A whole network file."""
    id: str = ""
    name: str = "lode-1"
    parameters: DesignParameters = field(default_factory=DesignParameters)
    library: Library = field(default_factory=Library)
    branches: dict = field(default_factory=dict)     # number -> Branch
    source_dbmv: float = 46.0        # launch level at the forward high frequency
    source_tilt_db: float = 10.0
    supply_volts: float = 60.0
    imported_from: str = ""

    # ------------------------------------------------------------------
    @property
    def has_specs(self) -> bool:
        lib = self.library
        return bool(lib.cables or lib.taps or lib.actives or lib.passives)

    def branch(self, number: int) -> Branch | None:
        return self.branches.get(number)

    def next_branch_number(self) -> int:
        return (max(self.branches) + 1) if self.branches else 1

    def ensure_feeder(self) -> Branch:
        if 1 not in self.branches:
            self.branches[1] = Branch(number=1, nodes=[Node(seq=1)])
        return self.branches[1]

    def add_branch(self, parent_branch: int, parent_node: int,
                   style: str = BRANCH_NORMAL) -> Branch:
        n = self.next_branch_number()
        b = Branch(number=n, parent_branch=parent_branch,
                   parent_node=parent_node, style=style, nodes=[Node(seq=1)])
        self.branches[n] = b
        return b

    def remove_branch(self, number: int) -> list:
        """Delete a branch and everything hanging off it."""
        if number == 1:
            return []
        gone = []
        stack = [number]
        while stack:
            n = stack.pop()
            if n not in self.branches:
                continue
            gone.append(n)
            stack += [b.number for b in self.branches.values()
                      if b.parent_branch == n]
            del self.branches[n]
        for b in self.branches.values():
            for node in b.nodes:
                node.couplers = [c for c in node.couplers if c.branch not in gone]
        return gone

    def renumber(self, branch: Branch) -> None:
        for i, node in enumerate(branch.nodes, start=1):
            node.seq = i

    # ------------------------------------------------------------------
    def validate(self) -> list:
        problems = []
        if not self.has_specs:
            problems.append("no spec set attached: every level, loss and part "
                            "comes from the spec files")
        for b in self.branches.values():
            if b.parent_branch and b.parent_branch not in self.branches:
                problems.append(f"branch {b.number}: its parent branch is gone")
            if not b.nodes:
                problems.append(f"branch {b.number} is empty: place at least a "
                                f"single zero node or delete the branch")
        return problems

    def to_dict(self) -> dict:
        return {
            "id": self.id, "name": self.name,
            "imported_from": self.imported_from,
            "parameters": asdict(self.parameters),
            "library": self.library.to_dict(),
            "branches": {str(k): v.to_dict() for k, v in self.branches.items()},
            "source_dbmv": self.source_dbmv,
            "source_tilt_db": self.source_tilt_db,
            "supply_volts": self.supply_volts,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Design":
        g = cls(id=d.get("id", ""), name=d.get("name", "lode-1"),
                imported_from=d.get("imported_from", ""),
                parameters=_parameters(d.get("parameters") or {}),
                library=Library.from_dict(d.get("library") or {}),
                source_dbmv=d.get("source_dbmv", 46.0),
                source_tilt_db=d.get("source_tilt_db", 10.0),
                supply_volts=d.get("supply_volts", 60.0))
        for k, v in (d.get("branches") or {}).items():
            g.branches[int(k)] = Branch.from_dict(v)
        return g
