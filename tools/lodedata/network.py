"""Reading the network itself out of a decoded .ntw design file.

The payload is a sequence of branches, in branch-number order.  Each is

    branch record   1966 bytes
    node records    one per screen line: 1970 bytes, or 2504 when the node
                    carries an active (amplifier, node, power supply)
    end record      44 bytes, starting 4 bytes past the last node record

Records are linked as well as sequential: every node starts with its own id,
the previous node's id (the branch number, for the first node) and the next
node's id.  Offsets below are relative to that id field.

Mapped against the AL004 design and its Design and Power screens -- every
footage, house count, cable, tap, coupler, amplifier, label and power supply
on branch 4 reads back as the screen shows it.  See docs/file-formats.md.

Equipment is stored by position in the spec files, not by name:

* taps      (row, port code) -- the tap file row, and 0/1/2/3 for 2/4/6/8 ports
* couplers  the coupler file record number plus one, on the branch it starts
* actives   the actives table index (record - 6); the Active ID is looked up
* cables    the displayed cable ID, series * 100 + cable file index

so a design only reads correctly against the spec set it was saved with.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass, field

from .obfuscation import PAYLOAD_START

BRANCH_RECORD = 1966
NODE_RECORD = 1970
ACTIVE_NODE_RECORD = 2504
END_GAP = 4
END_RECORD = 44

# node record fields, relative to the node's id
N_PREV, N_NEXT, N_FTG = 4, 8, 12
N_TAPS, TAP_SLOT, TAP_SLOTS = 14, 21, 4
N_BRANCH_A, N_BRANCH_B = 98, 102
N_AMP_INDEX, N_AMP_INDEX2 = 106, 107
N_PADS = 112                 # four (flag, value, 0) triples
N_PS_TYPE = 135
N_POWER_STOP = 133
N_HC, N_CABLE, N_LV = 129, 130, 132
N_HAS_ACTIVE = 701
N_PS_NAME = 726
N_LABEL = 981

# branch record fields, relative to its id
B_HEAD, B_COUNT = 4, 8
B_COUPLER = 126              # coupler file record + 1, 0 = none yet
B_THROUGH = 131              # non-zero: this branch takes the through leg

PORTS_BY_CODE = {0: 2, 1: 4, 2: 6, 3: 8}


@dataclass
class NtwTap:
    row: int
    ports: int


@dataclass
class NtwNode:
    id: int
    ftg: int = 0
    hc: int = 0
    cable: int = 0
    lv: int = 0
    taps: list = field(default_factory=list)          # NtwTap
    branches: list = field(default_factory=list)      # branch numbers started here
    active_index: int = 0     # actives table index, 0 = none
    inline_index: int = 0     # a non-active device in the amp column (EQ / Q)
    label: str = ""           # Amplifier Definition name
    pads: list = field(default_factory=list)          # fwd pad, ret pad, fwd EQ, ret EQ
    supply: str = ""          # power supply label, "" = none
    supply_type: int = 0
    power_stop: bool = False
    offset: int = 0           # file offset of the id field, for diagnostics


@dataclass
class NtwBranch:
    number: int
    coupler_record: int = 0   # coupler file record + 1, 0 = none
    through: bool = False
    nodes: list = field(default_factory=list)
    parent: tuple = (0, 0)    # (branch, node) carrying its coupler
    offset: int = 0


@dataclass
class NtwNetwork:
    name: str = ""
    spec_names: list = field(default_factory=list)
    branches: dict = field(default_factory=dict)      # number -> NtwBranch

    @property
    def node_count(self) -> int:
        return sum(len(b.nodes) for b in self.branches.values())


def _text(buf: bytes) -> str:
    return buf.split(b"\0", 1)[0].decode("latin-1").strip()


class _Reader:
    def __init__(self, data: bytes):
        self.d = data

    def u8(self, o): return self.d[o]
    def u16(self, o): return struct.unpack_from("<H", self.d, o)[0]
    def u32(self, o): return struct.unpack_from("<I", self.d, o)[0]
    def i32(self, o): return struct.unpack_from("<i", self.d, o)[0]


def _looks_like_branch(r: _Reader, b: int, number: int | None = None) -> bool:
    head = b + BRANCH_RECORD
    if head + NODE_RECORD > len(r.d) or b < 0:
        return False
    count = r.u16(b + B_COUNT)
    if not 0 < count < 5000:
        return False
    if r.u32(b + B_HEAD) != r.u32(head):
        return False
    if number is not None and r.u32(head + N_PREV) != number:
        return False
    return 0 < r.u32(head + N_PREV) < 100000


def _first_branch(r: _Reader) -> int:
    for b in range(PAYLOAD_START, len(r.d) - BRANCH_RECORD - NODE_RECORD):
        if r.u32(b + BRANCH_RECORD + N_PREV) == 1 and _looks_like_branch(r, b, 1):
            return b
    raise ValueError("no branch 1 found: not a design file this reader knows")


def _node(r: _Reader, p: int) -> NtwNode:
    n = NtwNode(id=r.u32(p), offset=p)
    n.ftg = r.u16(p + N_FTG)
    n.hc = r.u8(p + N_HC)
    n.cable = r.u16(p + N_CABLE)
    n.lv = r.u8(p + N_LV)
    for k in range(TAP_SLOTS):
        s = p + N_TAPS + k * TAP_SLOT
        row = r.i32(s)
        if row >= 0:
            n.taps.append(NtwTap(row=row, ports=PORTS_BY_CODE.get(r.u8(s + 4), 4)))
    n.branches = [b for b in (r.u32(p + N_BRANCH_A), r.u32(p + N_BRANCH_B)) if b]
    n.power_stop = bool(r.u8(p + N_POWER_STOP))
    idx = r.u8(p + N_AMP_INDEX)
    if r.u8(p + N_HAS_ACTIVE):
        n.active_index = idx
        n.label = _text(r.d[p + N_LABEL:p + N_LABEL + 16])
        n.pads = [r.u8(p + N_PADS + 3 * k + 1) for k in range(4)]
        if r.u8(p + N_PS_NAME):
            n.supply = _text(r.d[p + N_PS_NAME:p + N_PS_NAME + 1]) or "PS"
            n.supply_type = r.u8(p + N_PS_TYPE)
    elif idx:
        n.inline_index = idx
    return n


def read_network(plain: bytes) -> NtwNetwork:
    """Parse a whole decoded file (header included) into branches of nodes."""
    r = _Reader(plain)
    net = NtwNetwork()
    net.spec_names = [_text(plain[PAYLOAD_START + 261 * k:PAYLOAD_START + 261 * k + 40])
                      for k in range(5)]

    b = _first_branch(r)
    number = 1
    while _looks_like_branch(r, b):
        count = r.u16(b + B_COUNT)
        branch = NtwBranch(number=r.u32(b + BRANCH_RECORD + N_PREV), offset=b,
                           coupler_record=r.u8(b + B_COUPLER),
                           through=bool(r.u8(b + B_THROUGH)))
        p = b + BRANCH_RECORD
        for _ in range(count):
            node = _node(r, p)
            branch.nodes.append(node)
            p += ACTIVE_NODE_RECORD if r.u8(p + N_HAS_ACTIVE) else NODE_RECORD
        net.branches[branch.number] = branch
        number += 1
        b = p + END_GAP + END_RECORD

    for br in net.branches.values():
        for i, node in enumerate(br.nodes, start=1):
            for child in node.branches:
                if child in net.branches:
                    net.branches[child].parent = (br.number, i)

    feeder = net.branches.get(1)
    if feeder and feeder.nodes and feeder.nodes[0].label:
        net.name = feeder.nodes[0].label
    return net
