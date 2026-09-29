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
# the active's Configuration Table slot: 0 (the base ID) on every active of
# AL002 - AL005, 2 on SN001_MID's, which Lode shows as 63U and 11U (FM902B:
# 63 63N 63U ...; FML332: 11 11N 11U ...), 3 on its 5.8 (11M)
N_CONFIG = 111
# The amp column holds either an active -- both bytes the actives index -- or
# an in-line device from the Actives file's Bridgers/Feedermakers/Inline Eqs
# page, shown as Q1, Q2 ...: then the first byte is 80 - n and the second
# 24 - n.  Seen in all five sample designs (Q1 = 79/23, Q2 = 78/22,
# Q5 = 75/19); on AL004 Q2 costs exactly LEQ-PEA-0's losses.
INLINE_BASE, INLINE_BASE2 = 80, 24
N_FIXED = 128                # the node is fixed (locked): drawn as an arrow
N_PADS = 112                 # four (flag, value, 0) triples
N_PS_TYPE = 135
N_POWER_STOP = 133
N_HC, N_CABLE, N_LV = 129, 130, 132
N_HAS_ACTIVE = 701
N_PS_NAME = 726
N_LABEL = 981
# A line's text: C-style at +698, empty (one NUL) in every design but
# SN001_MID, whose 1.1 holds 63 characters (SHIN1 - 4953 - P-003938~0POWERED
# BY PS "PS1A"~0DATE :02/20/26~0).  The record grows by the text's length and
# every field after it moves with it -- 1.1's active flag is at +764 and its
# own id at +781, and 1.2 starts 2504 + 63 bytes on.  The offsets above
# 698 are as in an empty-text record; add text_len(...) to them.
N_TEXT = 698
B_TEXT = N_TEXT - 4          # the same field in a branch head (empty in every file)


def text_len(data: bytes, at: int) -> int:
    """Length of the C string at ``at`` (the NUL not counted)."""
    return data.index(b"\0", at) - at

# branch record fields, relative to its id
B_HEAD, B_COUNT = 4, 8
B_COUPLER = 126              # coupler file record + 1, 0 = none yet
B_THROUGH = 131              # non-zero: this branch takes the through leg

PORTS_BY_CODE = {0: 2, 1: 4, 2: 6, 3: 8}
TAP_CODES = {v: k for k, v in PORTS_BY_CODE.items()}


@dataclass
class NtwTap:
    row: int
    ports: int
    slot: int = 0             # which of the four tap columns


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
    config: int = 0           # the active's Configuration Table slot
    inline: int = 0           # in-line device Qn in the amp column, 0 = none
    fixed: bool = False       # locked against the semi-automatic design commands
    label: str = ""           # Amplifier Definition name
    pads: list = field(default_factory=list)          # fwd pad, ret pad, fwd EQ, ret EQ
    supply: str = ""          # power supply label, "" = none
    supply_type: int = 0
    power_stop: bool = False
    text: bytes = b""         # the line's text (N_TEXT), as stored
    offset: int = 0           # file offset of the id field, for diagnostics
    size: int = NODE_RECORD   # the record's length in the file


@dataclass
class NtwBranch:
    number: int
    coupler_record: int = 0   # coupler file record + 1, 0 = none
    through: bool = False
    nodes: list = field(default_factory=list)
    parent: tuple = (0, 0)    # (branch, node) carrying its coupler
    offset: int = 0
    end_id: int = 0           # the id of its end line (the last node's next)
    tap_port: bool = False    # hangs from a line no coupler of which starts it
    head_size: int = BRANCH_RECORD


# The files it was saved with, as the program's "Spec File Mismatch" box
# lists them: Parameters, Actives, Taps, Couplers, Cables, Prices,
# Performance, Map Grid -- 8 x char[261] (AL004: WV750-2026 five times, then
# Untitled three times).
SAVED_WITH = 42366
SAVED_WITH_FILES = ("Parameters", "Actives", "Taps", "Couplers", "Cables",
                    "Prices", "Performance", "Map Grid")


@dataclass
class NtwNetwork:
    name: str = ""
    spec_names: list = field(default_factory=list)
    saved_with: list = field(default_factory=list)    # the 8 file names, in SAVED_WITH_FILES order
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
    if b < 0 or b + BRANCH_RECORD + NODE_RECORD > len(r.d):
        return False
    head = b + BRANCH_RECORD + text_len(r.d, b + B_TEXT)
    if head + NODE_RECORD > len(r.d):
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
        first = b + BRANCH_RECORD + (text_len(r.d, b + B_TEXT) if r.d[b + B_TEXT] else 0)
        if r.u32(first + N_PREV) == 1 and _looks_like_branch(r, b, 1):
            return b
    raise ValueError("no branch 1 found: not a design file this reader knows")


def _node(r: _Reader, p: int) -> NtwNode:
    t = text_len(r.d, p + N_TEXT)
    n = NtwNode(id=r.u32(p), offset=p, text=bytes(r.d[p + N_TEXT:p + N_TEXT + t]))
    n.ftg = r.u16(p + N_FTG)
    n.hc = r.u8(p + N_HC)
    n.cable = r.u16(p + N_CABLE)
    n.lv = r.u8(p + N_LV)
    for k in range(TAP_SLOTS):
        s = p + N_TAPS + k * TAP_SLOT
        row = r.i32(s)
        if row >= 0:
            n.taps.append(NtwTap(row=row, ports=PORTS_BY_CODE.get(r.u8(s + 4), 4), slot=k))
    n.branches = [b for b in (r.u32(p + N_BRANCH_A), r.u32(p + N_BRANCH_B)) if b]
    n.power_stop = bool(r.u8(p + N_POWER_STOP))
    n.fixed = bool(r.u8(p + N_FIXED))
    idx, idx2 = r.u8(p + N_AMP_INDEX), r.u8(p + N_AMP_INDEX2)
    if idx and idx2 == idx - (INLINE_BASE - INLINE_BASE2):
        n.inline = INLINE_BASE - idx
    elif idx:
        n.active_index = idx
        n.config = r.u8(p + N_CONFIG)
        n.pads = [r.u8(p + N_PADS + 3 * k + 1) for k in range(4)]
    if r.u8(p + t + N_HAS_ACTIVE):
        n.label = _text(r.d[p + t + N_LABEL:p + t + N_LABEL + 16])
        if r.u8(p + t + N_PS_NAME):
            # char[16], C-style: SN001_MID's read 1A, 1B, 1C (its 1.1 notes
            # "POWERED BY PS "PS1A"")
            n.supply = _text(r.d[p + t + N_PS_NAME:p + t + N_PS_NAME + 16]) or "PS"
            n.supply_type = r.u8(p + N_PS_TYPE)
        n.size = ACTIVE_NODE_RECORD + t
    else:
        n.size = NODE_RECORD + t
    return n


def read_network(plain: bytes) -> NtwNetwork:
    """Parse a whole decoded file (header included) into branches of nodes."""
    r = _Reader(plain)
    net = NtwNetwork()
    net.spec_names = [_text(plain[PAYLOAD_START + 261 * k:PAYLOAD_START + 261 * k + 40])
                      for k in range(5)]
    if len(plain) > SAVED_WITH + 261 * 8:
        net.saved_with = [_text(plain[SAVED_WITH + 261 * k:SAVED_WITH + 261 * (k + 1)])
                          for k in range(8)]

    b = _first_branch(r)
    number = 1
    while _looks_like_branch(r, b):
        count = r.u16(b + B_COUNT)
        head_size = BRANCH_RECORD + text_len(plain, b + B_TEXT)
        branch = NtwBranch(number=r.u32(b + head_size + N_PREV), offset=b,
                           coupler_record=r.u8(b + B_COUPLER),
                           through=bool(r.u8(b + B_THROUGH)), head_size=head_size)
        p = b + head_size
        for _ in range(count):
            node = _node(r, p)
            branch.nodes.append(node)
            p += node.size
        branch.end_id = r.u32(p + END_GAP)
        net.branches[branch.number] = branch
        number += 1
        b = p + END_GAP + END_RECORD
    if b != len(plain):
        # every design ends with its last branch's end record: stopping short
        # means a record was misread (SN001_MID's text did this, as 1 branch
        # of garbage), so say so rather than show part of a network
        raise ValueError(f"the network could not be read past branch {number - 1}: "
                         f"{len(plain) - b} of {len(plain)} bytes left over, "
                         "a record layout this reader does not know yet")

    for br in net.branches.values():
        for i, node in enumerate(br.nodes, start=1):
            for child in node.branches:
                if child in net.branches:
                    net.branches[child].parent = (br.number, i)
    # A branch no coupler starts still names the line it hangs from, in its
    # head's first field: the old AL004 has two, 43 and 44, from the taps at
    # 11.16 and 11.18 (coupler 0; their lines list no branch)
    at = {n.id: (br.number, i) for br in net.branches.values()
          for i, n in enumerate(br.nodes, start=1)}
    for br in net.branches.values():
        if br.number != 1 and br.parent == (0, 0):
            parent = at.get(r.u32(br.offset))
            if parent is not None:
                br.parent, br.tap_port = parent, True

    feeder = net.branches.get(1)
    if feeder and feeder.nodes and feeder.nodes[0].label:
        net.name = feeder.nodes[0].label
    return net
