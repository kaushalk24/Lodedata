"""Writing a .ntw design back out, in the program's own layout.

A design file is written by starting from the file it was read from and
changing only what changed: every record keeps the bytes the program wrote,
and only the fields this package understands are rewritten.  An unchanged
network therefore comes back byte for byte (``tests/test_ntw_writer.py``).

What a file is, decoded (offsets from the start of the file, header
included; see docs/file-formats.md 3.7 and 3.8):

    header        512 bytes, copied as it is
    preamble      the spec file names, totals the program keeps for its
                  reports, the branch count and the id counter
    branches      in branch-number order, each
                      head record   1966 bytes
                      node records  1970 bytes, or 2504 with an active or a
                                    power supply: the same record with a
                                    534-byte block put in at +1706
                      end           4 zero bytes, then the end line's id and
                                    the last node's id, 44 bytes in all

Every node, end line and active has an id, handed out counting down from
127999; the preamble keeps the next free one.
"""
from __future__ import annotations

import struct
from collections import Counter
from dataclasses import dataclass, field

from . import network as N
from .obfuscation import PAYLOAD_START, obfuscate

EXT_AT = 1706                           # where an active's block goes in
EXT_SIZE = N.ACTIVE_NODE_RECORD - N.NODE_RECORD     # 534
END_SIZE = N.END_GAP + N.END_RECORD                 # 48

# fields of a node record not in network.py, relative to its id
N_INLINE_FLAG = 108          # 1 on a node carrying an in-line device (Qn)
N_OBJECT = 137               # u32 id of the active or supply placed here
N_SELF = 718                 # u32 the node's own id, in an extended record
TAIL_HC = 1706               # u8 the house count again (+534 when extended)
TAIL_A = 1714                # 32 u32: 4 on every record that has held an active
TAIL_HOMES = 1842            # 32 u32: 1 per home, then 4 -- when filled in
# a supply's record, as the program starts one (AL004's 43.1 and 45.1,
# SN001_MID's 27.1 and 41.1, all three of AL002's, PS_B's new 46.1): four
# 21-byte groups at +808 (of the record without its text), and no house list
PS_BLOCK = 808
PS_BLOCK_NEW = bytes.fromhex("ffffffff00ffff00ffff00ffff00ffff0000000000") * 4
EMPTY_TAP = b"\xff\xff\xff\xff\x00"     # tap-file row -1, port code 0

# Where a design refers to a part the spec set could not resolve, the
# writer leaves what the file holds: a tap slot given as KEEP, an active
# index, coupler record or supply type of -1.
KEEP = "keep"

# branch head record fields
B_PARENT, B_FIRST = 0, 4                # u32 ids: the coupler's node, the first node
THROUGH_VALUE = 4                       # +131 on the branch taking the through leg

# the preamble of a 12.11 design (offsets from the start of the file)
PREAMBLE_END = 44807                    # where branch 1 starts
# A network joined to others by a PCD (Power Connecting Device) lists
# them before branch 1: the u32 at 44803 is non-zero and a table follows
# -- in Bullhead's H043A_MID and H043B_MID one byte, then per network its
# file name char[261] and two u32 (1, 1): H043A_MID, H043B_MID, branch 1
# 539 bytes on.  Kept as the file has it.
P_PCDS = 44803
P_FTG = 1817                            # u32 feet aerial, underground
P_FTG_CABLE = 1825                      # u32 [100 cable index][10 series]
P_HOMES = 5825                          # u32 homes a/u, tap ports a/u, homes a/u
P_ACTIVES = 22377                       # (u16 aerial, u16 UG) at +4 x actives index
P_INLINE = 23381                        # the same at +4 x n for Qn
P_TAPS = 23513                          # (u16, u16) [512 tap rows][4 port codes]
P_TAP_PORTS = 31705                     # (u16, u16) [4 port codes]
P_COUPLERS = 31721                      # (u16, u16) at +4 x coupler record
P_NAME = 44542                          # the network's file name, without .ntw
P_SPECS = (512, 42366)                  # twice, 5 x char[261]: the spec set it was saved with
P_BRANCHES = 41405                      # u32 number of branches
P_NEXT_ID = 41409                       # u32 next free id, counting down
P_FIRST_ID = 41413                      # u32 the id the count starts from (127999)
P_CURSOR = 41425                        # u32 branch, u32 line (AL005: 12, 25; else 1, 1)
FIRST_ID = 127999
# More totals, checked against all five sample designs (AL002-AL005 and
# AL004 as re-saved with WV750-2026): every value below is rebuilt exactly.
P_PAD_TALLY = 5869          # 4 x 1032 (u16 aerial, u16 UG): the actives' forward
PAD_TALLY_SIZE = 4128       # pad, return pad, forward EQ, return EQ, each at
                            # +4 x (bank x 129 + value) -- the (bank, value)
                            # the node record holds
P_POWER_STOPS = 23477       # u32 power stops
P_CONNECTORS = 35723        # u16 at +4 x cable index: a connector at each end of
                            # a span (a line with footage) that meets a device
P_HOUSINGS = 36141          # (u16 aerial, u16 UG) at +4 x housing number: the
                            # Underground Housing each underground location takes
HOUSING_SLOTS = range(1, 15)
P_PARTS = 36201             # (u16 aerial, u16 UG) at +4 x k:
PARTS_TAPS, PARTS_COUPLERS, PARTS_SPLITTERS, PARTS_INLINE = 0, 1, 2, 3
PARTS_LINE_EXTENDERS, PARTS_AMPLIFIERS = 4, 5
# 1 in every file the program wrote but H043A_MID, which has it at k = 6:
# not decoded, so kept as the file has it (an empty network's is 1)
PARTS_ONE = 12
PCD_RECORD = 999            # a branch head's coupler record for a PCD (ID 1000)
PARTS_SUPPLIES = 56         # + power supply type
SUPPLY_TYPES = range(0, 26)
# Not decoded yet, left as the file has them (0 in an empty network):
# 23481 and 23483 (AL004: 70, 81) and the three pairs at 36121 (AL004:
# 58/1, 0/1, 28/4).


def _u32(b, o):
    return struct.unpack_from("<I", b, o)[0]


# --------------------------------------------------------------------------
# the file as records
# --------------------------------------------------------------------------
@dataclass
class RawBranch:
    head: bytes
    nodes: list                  # [(id, record bytes)]
    end: bytes                   # the 4 gap bytes and the end record

    @property
    def end_id(self) -> int:
        return _u32(self.end, N.END_GAP)


@dataclass
class RawNetwork:
    header: bytes
    preamble: bytes
    branches: list = field(default_factory=list)     # RawBranch, branch 1 first

    def records(self) -> dict:
        """Every node record by id."""
        return {i: rec for b in self.branches for i, rec in b.nodes}


def split(plain: bytes) -> RawNetwork:
    """A decoded file (header included) cut into its records."""
    net = N.read_network(plain)
    order = sorted(net.branches.values(), key=lambda b: b.offset)
    first = order[0].offset
    raw = RawNetwork(header=plain[:PAYLOAD_START], preamble=plain[PAYLOAD_START:first])
    end = first
    for br in order:
        p = br.offset + br.head_size
        nodes = []
        for nd in br.nodes:
            nodes.append((nd.id, plain[p:p + nd.size]))
            p += nd.size
        raw.branches.append(RawBranch(head=plain[br.offset:br.offset + br.head_size],
                                      nodes=nodes, end=plain[p:p + END_SIZE]))
        end = p + END_SIZE
    if end != len(plain):
        raise ValueError(f"{len(plain) - end} bytes after the last branch: "
                         "not a layout this writer knows")
    return raw


def join(raw: RawNetwork) -> bytes:
    """The decoded file again."""
    out = bytearray(raw.header + raw.preamble)
    for b in raw.branches:
        out += b.head
        for _, rec in b.nodes:
            out += rec
        out += b.end
    return bytes(out)


def encode(plain: bytes) -> bytes:
    """A decoded file (header included) as it is written to disk."""
    return plain[:PAYLOAD_START] + obfuscate(plain[PAYLOAD_START:])


# --------------------------------------------------------------------------
# what to write
# --------------------------------------------------------------------------
@dataclass
class NodeOut:
    """One screen line in the file's own terms (spec positions, not names)."""
    rec: int = 0                 # its id in the file it came from; 0 = new
    ftg: int = 0
    hc: int = 0
    cable: int = 0               # as displayed: series * 100 + cable file index
    lv: int = 0
    taps: list = field(default_factory=list)       # per slot (row, port code), None or KEEP
    branches: list = field(default_factory=list)   # branch numbers started here (<= 2)
    active_index: int = 0        # actives table index, 0 = none, -1 = as in the file
    inline: int = 0              # Qn in the amp column, 0 = none
    pads: list | None = None     # four bank rows as stored; None = leave as they are
    fixed: bool = False
    power_stop: bool = False
    label: str | None = None     # Amplifier Definition name; None = leave it
    supply: str = ""             # power supply label, "" = none
    supply_type: int = 0         # -1 = as in the file
    pad_banks: list | None = None  # the active's Pads/EQs banks less one (fwd pad,
                                   # ret pad, fwd EQ, ret EQ); None = leave them
    text: bytes | None = None    # the line's text at N_TEXT; None = leave it
    config: int | None = None    # the active's Configuration Table slot; None = leave it


@dataclass
class BranchOut:
    nodes: list                  # NodeOut
    end_rec: int = 0             # its end line's id in the file it came from; 0 = new
    coupler_record: int = 0      # the coupler that starts it (file record + 1); -1 = as in the file
    through: bool = False        # takes the coupler's through leg
    parent: tuple = (0, 0)       # (branch number, node number) carrying its coupler


@dataclass
class SpecInfo:
    """What the totals need from the spec set the network uses."""
    line_extenders: set = field(default_factory=set)   # actives indices
    points: dict = field(default_factory=dict)         # Parameters: equipment points
    housings: list = field(default_factory=list)       # [(housing number, least points)]
    internal_couplers: set = field(default_factory=set)  # coupler records an amp holds


class WriteError(ValueError):
    pass


def _text_into(rec: bytearray, at: int, text: str, width: int = 16) -> None:
    """The program writes names C-style: the text and a NUL, the rest left."""
    data = text.encode("latin-1", "replace")[:width - 1] + b"\0"
    rec[at:at + len(data)] = data


def _new_node() -> bytearray:
    """A line as the program starts one: empty tap slots, and the house list
    filled in (1 per home, 4 for the rest) as on AL004's newest lines."""
    rec = _untouched_line()
    rec[N.N_PADS:N.N_PADS + 12] = bytes(12)
    struct.pack_into("<32I", rec, TAIL_HOMES, *([4] * 32))
    return rec


def _untouched_line() -> bytearray:
    """The one line of a new network, as the program saves it untouched:
    empty tap slots, pads (255, 255, 0) x 4, no house list."""
    rec = bytearray(N.NODE_RECORD)
    for k in range(N.TAP_SLOTS):
        s = N.N_TAPS + k * N.TAP_SLOT
        rec[s:s + 17] = EMPTY_TAP + b"\xff\xff\x00" * 4
    rec[N.N_PADS:N.N_PADS + 12] = b"\xff\xff\x00" * 4
    return rec


HEADER_MAGIC = b"Lode Data Network File"
HEADER_VERSION = b"Design 12.11"


def blank(header: bytes | None = None) -> RawNetwork:
    """An empty network as the program starts one and saves it (File > New,
    nothing keyed: Untitled spec files, branch 1 with one line), rebuilt from
    the program's own empty file byte for byte.  ``header`` is a .ntw header
    to take the licence and user fields from; without one they are blank."""
    if header is not None and len(header) == PAYLOAD_START:
        head = bytearray(header)
    else:
        head = bytearray(PAYLOAD_START)
        head[0:len(HEADER_MAGIC)] = HEADER_MAGIC
        head[26], head[27] = 12, 1
        head[28:28 + len(HEADER_VERSION)] = HEADER_VERSION
        head[402] = 0xE2
    pre = bytearray(PREAMBLE_END)
    for base in P_SPECS:
        for k in range(8 if base == P_SPECS[1] else 5):
            _text_into(pre, base + 261 * k, "Untitled", width=261)
    struct.pack_into("<HBB", pre, P_BRANCHES - 4, 41, 1, 1)
    struct.pack_into("<III", pre, P_BRANCHES, 1, FIRST_ID - 2, FIRST_ID)
    struct.pack_into("<IIB", pre, P_CURSOR, 1, 1, 1)
    struct.pack_into("<H", pre, P_PARTS + 4 * PARTS_ONE, 1)
    line = _untouched_line()
    struct.pack_into("<III", line, 0, FIRST_ID, 1, FIRST_ID - 1)
    branch_head = bytearray(N.BRANCH_RECORD)
    branch_head[:N.BRANCH_RECORD] = line[4:4 + N.BRANCH_RECORD]
    struct.pack_into("<IIH", branch_head, B_PARENT, 0, FIRST_ID, 1)
    end = bytes(N.END_GAP) + struct.pack("<II", FIRST_ID - 1, FIRST_ID) + bytes(N.END_RECORD - 8)
    return RawNetwork(header=bytes(head), preamble=bytes(pre[PAYLOAD_START:]),
                      branches=[RawBranch(head=bytes(branch_head), nodes=[(FIRST_ID, bytes(line))],
                                          end=end)])


def _tail(extended: bool) -> int:
    return EXT_SIZE if extended else 0


def build(source: RawNetwork, branches: list, name: str | None = None,
          spec: str | None = None, fresh: bool = False,
          info: SpecInfo | None = None) -> tuple[bytes, dict]:
    """Write ``branches`` (BranchOut, branch 1 first) over ``source``.

    ``name`` is the file name it is saved as, without .ntw.  The program
    keeps it in the file and, opening a file whose name differs, says
    "Filename AL004 has changed to ... Setting all PCDs to open."
    ``spec`` is the spec set the network now uses (its base name): the file
    keeps it, and the program warns when a file is opened with another set.
    ``fresh`` writes a network that did not come from ``source`` (one keyed
    in from scratch; ``source`` is then normally ``blank()``): only the
    file's layout is taken from it, every line is new and the ids start
    again from the first.  ``info`` is what the totals need from the spec
    set; without it the totals that depend on it are left as they are.

    Returns the decoded file and the ids handed out: ``{"nodes": [[id per
    node] per branch], "ends": [end id per branch]}`` so the caller can keep
    them for the next save.
    """
    if not branches or not branches[0].nodes:
        raise WriteError("a network needs branch 1 with at least one line")
    size = len(source.header) + len(source.preamble)
    if size != PREAMBLE_END and not (size > PREAMBLE_END and _u32(source.header + source.preamble, P_PCDS)):
        raise WriteError("the file this network came from is not laid out as "
                         "a Design 12.11 file: nothing written")
    records = {} if fresh else source.records()
    heads = {} if fresh else {b.end_id: b for b in source.branches}
    pre = bytearray(source.header + source.preamble)
    next_id = _u32(pre, P_FIRST_ID if fresh else P_NEXT_ID)

    def take() -> int:
        nonlocal next_id
        if next_id <= 0:
            raise WriteError("the file has run out of ids")
        next_id -= 1
        return next_id + 1

    # hand out ids first: every link needs them.  An id is used once: a
    # second line carrying the same id (a copy) gets a new one.
    ids, ends, used = [], [], set()

    def own(rec: int, known) -> int:
        got = rec if rec in known and rec not in used else take()
        used.add(got)
        return got

    for k, br in enumerate(branches):
        # A new network starts with branch 1's line and end line (127999,
        # 127998); lines keyed after take the next ids, and a branch placed
        # later takes its end line's id first (the user's S3: 1.2 127997,
        # 1.3 127996, branch 2's end 127995, 2.1 127994)
        if k == 0:
            first = own(br.nodes[0].rec, records)
            ends.append(own(br.end_rec, heads))
            ids.append([first] + [own(nd.rec, records) for nd in br.nodes[1:]])
        else:
            ends.append(own(br.end_rec, heads))
            ids.append([own(nd.rec, records) for nd in br.nodes])
    number = {k + 1: k for k in range(len(branches))}

    out = bytearray(pre)
    # a branch placed later: its head as the program starts one (S3's
    # branch 2), the head of a keyed line -- pads (0, 0, 0), no house list
    template_head = bytes(_new_node()[4:4 + N.BRANCH_RECORD])
    template_head = template_head[:TAIL_HOMES - 4] + bytes(N.BRANCH_RECORD - (TAIL_HOMES - 4))
    for k, br in enumerate(branches):
        if not br.nodes:
            raise WriteError(f"branch {k + 1} has no lines")
        src = heads.get(br.end_rec) if ends[k] == br.end_rec else None
        head = bytearray(src.head if src else
                         source.branches[0].head if k == 0 else template_head)
        if k == 0:
            parent_id = 0
        else:
            pb, pn = br.parent
            if pb not in number or not 0 < pn <= len(branches[number[pb]].nodes):
                raise WriteError(f"branch {k + 1}: its coupler's line {pb}.{pn} is not there")
            parent_id = ids[number[pb]][pn - 1]
        struct.pack_into("<IIH", head, B_PARENT, parent_id, ids[k][0], len(br.nodes))
        if br.coupler_record >= 0:
            struct.pack_into("<H", head, N.B_COUPLER, br.coupler_record)
        head[N.B_THROUGH] = THROUGH_VALUE if br.through else 0
        out += head

        for i, nd in enumerate(br.nodes):
            src = records.get(nd.rec) if ids[k][i] == nd.rec else None
            if fresh and k == 0 and i == 0:
                # the network's first line is the one it started with
                src = bytes(_untouched_line())
            out += _node_record(nd, src, ids[k][i],
                                prev=ids[k][i - 1] if i else k + 1,
                                nxt=ids[k][i + 1] if i + 1 < len(br.nodes) else ends[k],
                                take=take)
        out += bytes(N.END_GAP) + struct.pack("<II", ends[k], ids[k][-1]) + bytes(N.END_RECORD - 8)

    struct.pack_into("<I", out, P_BRANCHES, len(branches))
    struct.pack_into("<I", out, P_NEXT_ID, next_id)
    if name is not None and name != _stored_name(out):
        _text_into(out, P_NAME, name, width=261)
    if spec:
        for base in P_SPECS:
            for k in range(5):
                at = base + 261 * k
                if _stored_name(out, at) != spec:
                    _text_into(out, at, spec, width=261)
        # Set All Files names all eight; Prices, Performance and Map Grid
        # then keep Untitled over it, which leaves the name's tail behind
        # ("Untitled\0" then "6" of WV750-2026, on AL004 and S1 - S3)
        for k in range(5, 8):
            at = P_SPECS[1] + 261 * k
            kept = _stored_name(out, at)
            _text_into(out, at, spec, width=261)
            _text_into(out, at, kept or "Untitled", width=261)
    # counted from what was written: a tap or active the spec set in use
    # cannot name is kept in its line, and still counts
    _totals(out, _counts(outs_from_plain(join(source))), _counts(outs_from_plain(bytes(out))))
    _more_totals(out, info)
    cur_branch, cur_line = struct.unpack_from("<II", out, P_CURSOR)
    if not (0 < cur_branch <= len(branches) and 0 < cur_line <= len(branches[cur_branch - 1].nodes)):
        # where the program's cursor was, and it is no longer there
        struct.pack_into("<II", out, P_CURSOR, 1, 1)
    return bytes(out), {"nodes": ids, "ends": ends}


def _stored_name(plain, at: int = P_NAME) -> str:
    return bytes(plain[at:at + 261]).split(b"\0", 1)[0].decode("latin-1")


def _node_record(nd: NodeOut, src: bytes | None, own: int, prev: int, nxt: int,
                 take) -> bytes:
    rec = bytearray(src) if src is not None else _new_node()
    # the line's text moves every field after it (SN001_MID's 1.1): work on
    # the record without it, and put it back last
    t = N.text_len(rec, N.N_TEXT)
    text = bytes(rec[N.N_TEXT:N.N_TEXT + t]) if nd.text is None else nd.text.replace(b"\0", b"")
    del rec[N.N_TEXT:N.N_TEXT + t]
    old_hc = rec[N.N_HC] if src is not None else None
    extended = bool(rec[N.N_HAS_ACTIVE])
    keep_active = nd.active_index == -1 and src is not None
    has_active = bool(rec[N.N_AMP_INDEX]) and not rec[N_INLINE_FLAG] if keep_active else nd.active_index > 0
    named = nd.label if nd.label is not None else bytes(rec[N.N_LABEL:N.N_LABEL + 1]) != b"\0"
    want = bool(has_active or nd.supply)
    if nd.supply and has_active and not rec[N.N_PS_NAME]:
        raise WriteError(f"line id {own}: a power supply on a line with an active is "
                         "not written yet -- that record has not been seen")
    if want and not extended and not nd.supply and not named:
        # an active the program has not been given a name for stays on the
        # short record: the user's S1 Ripple, and 22 of AL002's actives
        want = False
    if want and not extended:
        # an active or a supply takes the longer record: the program's block
        # goes in ahead of the house list, and the active gets an id
        rec[EXT_AT:EXT_AT] = bytes(EXT_SIZE)
        rec[N.N_HAS_ACTIVE] = 1
        struct.pack_into("<I", rec, N_OBJECT, take())
        if has_active:
            # every AL004 record holding an active has this list all 4
            struct.pack_into("<32I", rec, TAIL_A + EXT_SIZE, *([4] * 32))
        else:
            rec[PS_BLOCK:PS_BLOCK + len(PS_BLOCK_NEW)] = PS_BLOCK_NEW
            rec[TAIL_HOMES + EXT_SIZE:TAIL_HOMES + EXT_SIZE + 128] = bytes(128)
    elif extended and not want:
        # taken away: back to the short record (AL004's 9.20 still holds the
        # pads of the amplifier moved to 9.21, so those are left)
        del rec[EXT_AT:EXT_AT + EXT_SIZE]
        rec[N.N_HAS_ACTIVE] = 0
        struct.pack_into("<I", rec, N_OBJECT, 0)
        struct.pack_into("<I", rec, N_SELF, 0)
    extended = want
    if extended:
        struct.pack_into("<I", rec, N_SELF, own)

    struct.pack_into("<III", rec, 0, own, prev, nxt)
    struct.pack_into("<H", rec, N.N_FTG, max(0, min(0xFFFF, int(round(nd.ftg)))))
    for k in range(N.TAP_SLOTS):
        s = N.N_TAPS + k * N.TAP_SLOT
        tap = nd.taps[k] if k < len(nd.taps) else None
        if tap == KEEP:
            if src is None:
                rec[s:s + 5] = EMPTY_TAP
        elif tap is None:
            rec[s:s + 5] = EMPTY_TAP
        else:
            row, code = tap
            struct.pack_into("<iB", rec, s, row, code)
    a, b = (list(nd.branches) + [0, 0])[:2]
    struct.pack_into("<II", rec, N.N_BRANCH_A, a, b)

    if keep_active:
        pass
    elif nd.active_index > 0:
        placed = rec[N.N_AMP_INDEX] != nd.active_index or rec[N_INLINE_FLAG]
        rec[N.N_AMP_INDEX] = rec[N.N_AMP_INDEX2] = nd.active_index & 0xFF
        rec[N_INLINE_FLAG] = 0
        if nd.config is not None:
            rec[N.N_CONFIG] = nd.config & 0xFF
        if nd.pad_banks is not None and placed:
            # each pad and EQ is (the bank it comes from, its value, 0): AL004's
            # Ripple node, banks 4, holds (3, 0, 0) four times
            for k, bank in enumerate(nd.pad_banks[:4]):
                rec[N.N_PADS + 3 * k] = bank & 0xFF
                if placed and nd.pads is None:
                    rec[N.N_PADS + 3 * k + 1] = 0
                rec[N.N_PADS + 3 * k + 2] = 0
    elif nd.inline:
        rec[N.N_AMP_INDEX] = N.INLINE_BASE - nd.inline
        rec[N.N_AMP_INDEX2] = N.INLINE_BASE2 - nd.inline
        rec[N_INLINE_FLAG] = 1
    else:
        rec[N.N_AMP_INDEX] = rec[N.N_AMP_INDEX2] = rec[N_INLINE_FLAG] = 0
    if nd.pads is not None:
        for k, v in enumerate(nd.pads[:4]):
            rec[N.N_PADS + 3 * k + 1] = int(v) & 0xFF

    rec[N.N_FIXED] = 1 if nd.fixed else 0
    rec[N.N_HC] = nd.hc & 0xFF
    struct.pack_into("<H", rec, N.N_CABLE, nd.cable & 0xFFFF)
    rec[N.N_LV] = nd.lv & 0xFF
    rec[N.N_POWER_STOP] = 1 if nd.power_stop else 0
    if nd.label is not None and (nd.label or rec[N.N_LABEL]):
        _text_into(rec, N.N_LABEL, nd.label)
    if nd.supply:
        if nd.supply != bytes(rec[N.N_PS_NAME:N.N_PS_NAME + 16]).split(b"\0", 1)[0].decode("latin-1"):
            # written C-style, the rest left: AL004's 18.1 holds "A\0004A",
            # the "A" written over "AL004A"; an unchanged label is left alone
            _text_into(rec, N.N_PS_NAME, nd.supply)
        if nd.supply_type >= 0:
            rec[N.N_PS_TYPE] = nd.supply_type & 0xFF
    elif rec[N.N_PS_NAME]:
        rec[N.N_PS_NAME] = 0
        rec[N.N_PS_TYPE] = 0

    tail = _tail(extended)
    rec[TAIL_HC + tail] = nd.hc & 0xFF
    homes = TAIL_HOMES + tail
    # filled in: a 1 for each home, 4 for the rest -- rewritten when the house
    # count changes to some homes, an empty list too (H_B's 2.1, 0 -> 2 homes:
    # 1 1 4 4 ...); SN001_MID's 8.3 holds 0 homes over a list still reading
    # 1 1 1, so a line left alone keeps its list
    if nd.hc and nd.hc != old_hc:
        for k in range(32):
            struct.pack_into("<I", rec, homes + 4 * k, 1 if k < nd.hc else 4)
    rec[N.N_TEXT:N.N_TEXT] = text
    return bytes(rec)


# --------------------------------------------------------------------------
# the totals the program keeps in the preamble
# --------------------------------------------------------------------------
def _counts(branches: list) -> dict:
    """Footage, homes, ports, taps, actives, in-line devices and couplers,
    aerial and underground (odd cable file index), as AL004 holds them."""
    c = {"ftg": [0, 0], "ftg_cable": {}, "homes": [0, 0], "ports": [0, 0],
         "actives": {}, "inline": {}, "couplers": {}, "taps": {}, "tap_ports": {}}
    ug_of = {}
    for k, br in enumerate(branches):
        for nd in br.nodes:
            ug = (nd.cable % 100) % 2
            c["ftg"][ug] += nd.ftg
            key = (nd.cable % 100, nd.cable // 100 % 10)
            c["ftg_cable"][key] = c["ftg_cable"].get(key, 0) + nd.ftg
            c["homes"][ug] += nd.hc
            for tap in nd.taps:
                if tap is None or tap == KEEP:
                    continue
                row, code = tap
                c["ports"][ug] += N.PORTS_BY_CODE.get(code, 4)
                c["taps"].setdefault((row, code), [0, 0])[ug] += 1
                c["tap_ports"].setdefault(code, [0, 0])[ug] += 1
            if nd.active_index > 0:
                c["actives"].setdefault(nd.active_index, [0, 0])[ug] += 1
            if nd.inline:
                c["inline"].setdefault(nd.inline, [0, 0])[ug] += 1
            for child in nd.branches:
                ug_of[child] = ug
    # a coupler feeding two branches is one coupler (AL004: the two 3-way
    # splitters at 4.14 and 4.25 count 2)
    seen = set()
    for k, br in enumerate(branches):
        where = (br.parent, br.coupler_record)
        if k == 0 or br.coupler_record <= 0 or where in seen:
            continue
        seen.add(where)
        c["couplers"].setdefault(br.coupler_record, [0, 0])[ug_of.get(k + 1, 0)] += 1
    return c


# (table, offset of key k, highest key + 1) for the (u16 aerial, u16 UG) tables
_PAIR_TABLES = {
    "actives": (lambda i: P_ACTIVES + 4 * i, 252),
    "inline": (lambda n: P_INLINE + 4 * n, 24),
    "taps": (lambda rc: P_TAPS + 16 * rc[0] + 4 * rc[1], None),
    "tap_ports": (lambda code: P_TAP_PORTS + 4 * code, 4),
    "couplers": (lambda r: P_COUPLERS + 4 * r, 252),
}


def _totals(out: bytearray, old: dict, new: dict) -> None:
    """Rewrite the totals for everything counted before or now; nothing
    else in the preamble is touched."""
    struct.pack_into("<II", out, P_FTG, *new["ftg"])
    for (index, series) in set(old["ftg_cable"]) | set(new["ftg_cable"]):
        if 0 <= index < 100:
            struct.pack_into("<I", out, P_FTG_CABLE + 40 * index + 4 * series,
                             new["ftg_cable"].get((index, series), 0))
    struct.pack_into("<6I", out, P_HOMES, new["homes"][0], new["homes"][1],
                     new["ports"][0], new["ports"][1], new["homes"][0], new["homes"][1])
    for name, (at, limit) in _PAIR_TABLES.items():
        for key in set(old[name]) | set(new[name]):
            if name == "taps":
                if not (0 <= key[0] < 512 and 0 <= key[1] < 4):
                    continue
            elif not 0 < key < limit and not (name == "tap_ports" and key == 0):
                continue
            a, u = new[name].get(key, (0, 0))
            struct.pack_into("<HH", out, at(key), a, u)


def _groups(nodes: list) -> list:
    """A branch's lines by location: a line with footage starts one, the
    lines 0 ft after it are at the same place."""
    out = []
    for i, nd in enumerate(nodes):
        if nd.ftg or not out:
            out.append([])
        out[-1].append(nd)
    return out


def _has_device(nd) -> bool:
    return bool(nd.taps or nd.branches or nd.active_index or nd.inline or nd.supply)


def tallies(plain, info: SpecInfo | None = None) -> dict:
    """The totals below ``_totals``'s, rebuilt from a decoded file:
    {offset: value}, u16 each but the power stops (u32).  The line
    extender / amplifier split and the housings need ``info``."""
    net = N.read_network(bytes(plain))
    t = Counter()
    ug = lambda nd: (nd.cable % 100) % 2          # noqa: E731
    for br in net.branches.values():
        for nd in br.nodes:
            u = ug(nd)
            if nd.power_stop:
                t[P_POWER_STOPS] += 1
            t[P_PARTS + 4 * PARTS_TAPS + 2 * u] += len(nd.taps)
            if nd.branches:
                # a PCD is no coupler: H043A_MID and H043B_MID count one
                # aerial coupler, their 1.1 PCDs left out
                recs = [net.branches[b].coupler_record for b in nd.branches
                        if b in net.branches and net.branches[b].coupler_record != PCD_RECORD]
                if len(recs) == 2 and recs[0] == recs[1]:
                    t[P_PARTS + 4 * PARTS_SPLITTERS + 2 * u] += 1
                else:
                    t[P_PARTS + 4 * PARTS_COUPLERS + 2 * u] += len(recs)
            if nd.inline:
                t[P_PARTS + 4 * PARTS_INLINE + 2 * u] += 1
            if nd.supply and nd.supply_type in SUPPLY_TYPES:
                t[P_PARTS + 4 * (PARTS_SUPPLIES + nd.supply_type) + 2 * u] += 1
            if nd.active_index:
                if info is not None:
                    kind = PARTS_LINE_EXTENDERS if nd.active_index in info.line_extenders else PARTS_AMPLIFIERS
                    t[P_PARTS + 4 * kind + 2 * u] += 1
                for k in range(4):
                    bank = plain[nd.offset + N.N_PADS + 3 * k]
                    value = struct.unpack_from("<b", plain, nd.offset + N.N_PADS + 3 * k + 1)[0]
                    slot = bank * 129 + value
                    if 0 <= slot < PAD_TALLY_SIZE // 4:
                        t[P_PAD_TALLY + PAD_TALLY_SIZE * k + 4 * slot + 2 * u] += 1

        # connectors: one at each end of a span that meets a device; a branch
        # starts at its coupler, and one starting 0 ft on is still there
        groups = _groups(br.nodes)

        def device_at(g: int) -> bool:
            if any(_has_device(nd) for nd in groups[g]):
                return True
            return g == 0 and br.number != 1 and not groups[0][0].ftg

        # a PCD's branch: one connector, counted on its line's cable (H043A_MID
        # and H043B_MID one more on cable 0, the PCD's line and 1.1 both on 0)
        if br.coupler_record == PCD_RECORD and br.nodes:
            t[P_CONNECTORS + 4 * (br.nodes[0].cable % 100)] += 1
        for g, lines in enumerate(groups):
            if not lines[0].ftg:
                continue
            ends = device_at(g) + (device_at(g - 1) if g else br.number != 1)
            t[P_CONNECTORS + 4 * (lines[0].cable % 100)] += ends

        if info is not None and info.points and info.housings:
            for lines in groups:
                total = _place_points(net, lines, info)
                fits = [number for number, least in info.housings if total and least <= total]
                if fits and fits[-1] in HOUSING_SLOTS:
                    t[P_HOUSINGS + 4 * fits[-1] + 2] += 1
    return t


def _place_points(net, lines: list, info: SpecInfo) -> int:
    """The Parameters points of the equipment at one place, 0 unless its
    first line is underground: its lines' -- an amplifier or a line
    extender, each tap, each coupler (a splitter's two legs one, an amp's
    internal one and a PCD none), an in-line equalizer, a supply -- and
    those of the 0-ft first lines of the branches started on them.  Every
    file's tally is every such place's housing, a branch's 0-ft start
    counted on its own as well (H043A_MID 179/23/8/7 of housings 1/3/4/5,
    H043B_MID 82/11/4/2: its 7.1 supply a (5) and 2.5's place, which holds
    it, another)."""
    if not (lines[0].cable % 100) % 2:
        return 0
    pts = info.points
    total = 0
    for nd in lines:
        if nd.active_index:
            total += pts.get("line_extender" if nd.active_index in info.line_extenders else "amplifier", 0)
        total += sum(pts.get("tap_8_port" if tp.ports == 8 else "tap", 0) for tp in nd.taps)
        recs = [net.branches[b].coupler_record for b in nd.branches if b in net.branches]
        devices = [r for r in recs if r and r != PCD_RECORD and r not in info.internal_couplers]
        total += pts.get("coupler", 0) * (1 if len(devices) == 2 and devices[0] == devices[1] else len(devices))
        if nd.inline:
            total += pts.get("equalizer", 0)
        if nd.supply:
            total += pts.get("power_supply", 0)
        for b in nd.branches:
            child = net.branches.get(b)
            if child is not None and child.coupler_record != PCD_RECORD and child.nodes and not child.nodes[0].ftg:
                total += _place_points(net, _groups(child.nodes)[0], info)
    return total


def _more_totals(out: bytearray, info: SpecInfo | None) -> None:
    """Rewrite the totals ``tallies`` rebuilds; the rest is left."""
    pairs = [PARTS_TAPS, PARTS_COUPLERS, PARTS_SPLITTERS, PARTS_INLINE]
    pairs += [PARTS_SUPPLIES + k for k in SUPPLY_TYPES]
    if info is not None:
        pairs += [PARTS_LINE_EXTENDERS, PARTS_AMPLIFIERS]
    clear = [P_PARTS + 4 * k + h for k in pairs for h in (0, 2)]
    clear += [P_CONNECTORS + 4 * k for k in range(100)]
    clear += [P_PAD_TALLY + 2 * k for k in range(4 * PAD_TALLY_SIZE // 2)]
    if info is not None and info.points and info.housings:
        clear += [P_HOUSINGS + 4 * n + h for n in HOUSING_SLOTS for h in (0, 2)]
    for at in clear:
        struct.pack_into("<H", out, at, 0)
    struct.pack_into("<I", out, P_POWER_STOPS, 0)
    for at, value in tallies(out, info).items():
        if at == P_POWER_STOPS:
            struct.pack_into("<I", out, at, value)
        else:
            struct.pack_into("<H", out, at, min(value, 0xFFFF))


def outs_from_plain(plain: bytes) -> list:
    """The network in a decoded file, as ``build`` takes it -- for writing a
    file back unchanged, and for the totals it held."""
    net = N.read_network(plain)
    branches = []
    for number in sorted(net.branches):
        nb = net.branches[number]
        nodes = []
        for nn in nb.nodes:
            taps = [None] * N.TAP_SLOTS
            for t in nn.taps:
                taps[t.slot] = (t.row, N.TAP_CODES[t.ports])
            nodes.append(NodeOut(rec=nn.id, ftg=nn.ftg, hc=nn.hc, cable=nn.cable, lv=nn.lv,
                                 taps=taps, branches=list(nn.branches),
                                 active_index=nn.active_index, inline=nn.inline,
                                 fixed=nn.fixed, power_stop=nn.power_stop,
                                 supply=nn.supply, supply_type=nn.supply_type))
        branches.append(BranchOut(nodes=nodes, end_rec=nb.end_id,
                                  coupler_record=nb.coupler_record, through=nb.through,
                                  parent=nb.parent))
    return branches
