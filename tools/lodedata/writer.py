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
P_FTG = 1817                            # u32 feet aerial, underground
P_FTG_CABLE = 1825                      # u32 [100 cable index][10 series]
P_HOMES = 5825                          # u32 homes a/u, tap ports a/u, homes a/u
P_ACTIVES = 22377                       # (u16 aerial, u16 UG) at +4 x actives index
P_INLINE = 23381                        # the same at +4 x n for Qn
P_TAPS = 23513                          # (u16, u16) [512 tap rows][4 port codes]
P_TAP_PORTS = 31705                     # (u16, u16) [4 port codes]
P_COUPLERS = 31721                      # (u16, u16) at +4 x coupler record
P_BRANCHES = 41405                      # u32 number of branches
P_NEXT_ID = 41409                       # u32 next free id, counting down


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
        p = br.offset + N.BRANCH_RECORD
        nodes = []
        for nd in br.nodes:
            size = N.ACTIVE_NODE_RECORD if plain[nd.offset + N.N_HAS_ACTIVE] else N.NODE_RECORD
            nodes.append((nd.id, plain[p:p + size]))
            p += size
        raw.branches.append(RawBranch(head=plain[br.offset:br.offset + N.BRANCH_RECORD],
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


@dataclass
class BranchOut:
    nodes: list                  # NodeOut
    end_rec: int = 0             # its end line's id in the file it came from; 0 = new
    coupler_record: int = 0      # the coupler that starts it (file record + 1); -1 = as in the file
    through: bool = False        # takes the coupler's through leg
    parent: tuple = (0, 0)       # (branch number, node number) carrying its coupler


class WriteError(ValueError):
    pass


def _text_into(rec: bytearray, at: int, text: str, width: int = 16) -> None:
    """The program writes names C-style: the text and a NUL, the rest left."""
    data = text.encode("latin-1", "replace")[:width - 1] + b"\0"
    rec[at:at + len(data)] = data


def _new_node() -> bytearray:
    """A line as the program starts one: empty tap slots, and the house list
    filled in (1 per home, 4 for the rest) as on AL004's newest lines."""
    rec = bytearray(N.NODE_RECORD)
    for k in range(N.TAP_SLOTS):
        s = N.N_TAPS + k * N.TAP_SLOT
        rec[s:s + 17] = EMPTY_TAP + b"\xff\xff\x00" * 4
    struct.pack_into("<32I", rec, TAIL_HOMES, *([4] * 32))
    return rec


def _tail(extended: bool) -> int:
    return EXT_SIZE if extended else 0


def build(source: RawNetwork, branches: list) -> tuple[bytes, dict]:
    """Write ``branches`` (BranchOut, branch 1 first) over ``source``.

    Returns the decoded file and the ids handed out: ``{"nodes": [[id per
    node] per branch], "ends": [end id per branch]}`` so the caller can keep
    them for the next save.
    """
    if not branches or not branches[0].nodes:
        raise WriteError("a network needs branch 1 with at least one line")
    if len(source.header) + len(source.preamble) != PREAMBLE_END:
        raise WriteError("the file this network came from is not laid out as "
                         "a Design 12.11 file: nothing written")
    records = source.records()
    heads = {b.end_id: b for b in source.branches}
    pre = bytearray(source.header + source.preamble)
    next_id = _u32(pre, P_NEXT_ID)

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

    for br in branches:
        ends.append(own(br.end_rec, heads))
        ids.append([own(nd.rec, records) for nd in br.nodes])
    number = {k + 1: k for k in range(len(branches))}

    out = bytearray(pre)
    template_head = next((b.head for b in source.branches[1:]), None) or source.branches[0].head
    for k, br in enumerate(branches):
        if not br.nodes:
            raise WriteError(f"branch {k + 1} has no lines")
        src = heads.get(br.end_rec) if ends[k] == br.end_rec else None
        head = bytearray(src.head if src else template_head)
        if k == 0:
            parent_id = 0
        else:
            pb, pn = br.parent
            if pb not in number or not 0 < pn <= len(branches[number[pb]].nodes):
                raise WriteError(f"branch {k + 1}: its coupler's line {pb}.{pn} is not there")
            parent_id = ids[number[pb]][pn - 1]
        struct.pack_into("<IIH", head, B_PARENT, parent_id, ids[k][0], len(br.nodes))
        if br.coupler_record >= 0:
            head[N.B_COUPLER] = br.coupler_record & 0xFF
        head[N.B_THROUGH] = THROUGH_VALUE if br.through else 0
        out += head

        for i, nd in enumerate(br.nodes):
            out += _node_record(nd, records.get(nd.rec) if ids[k][i] == nd.rec else None, ids[k][i],
                                prev=ids[k][i - 1] if i else k + 1,
                                nxt=ids[k][i + 1] if i + 1 < len(br.nodes) else ends[k],
                                take=take)
        out += bytes(N.END_GAP) + struct.pack("<II", ends[k], ids[k][-1]) + bytes(N.END_RECORD - 8)

    struct.pack_into("<I", out, P_BRANCHES, len(branches))
    struct.pack_into("<I", out, P_NEXT_ID, next_id)
    _totals(out, _counts(outs_from_plain(join(source))), _counts(branches))
    return bytes(out), {"nodes": ids, "ends": ends}


def _node_record(nd: NodeOut, src: bytes | None, own: int, prev: int, nxt: int,
                 take) -> bytes:
    rec = bytearray(src) if src is not None else _new_node()
    extended = bool(rec[N.N_HAS_ACTIVE])
    keep_active = nd.active_index == -1 and src is not None
    has_active = bool(rec[N.N_AMP_INDEX]) and not rec[N_INLINE_FLAG] if keep_active else nd.active_index > 0
    want = bool(has_active or nd.supply)
    if want and not extended:
        # an active or a supply takes the longer record: the program's block
        # goes in ahead of the house list, and the active gets an id
        rec[EXT_AT:EXT_AT] = bytes(EXT_SIZE)
        rec[N.N_HAS_ACTIVE] = 1
        struct.pack_into("<I", rec, N_OBJECT, take())
        if has_active:
            # every AL004 record holding an active has this list all 4
            struct.pack_into("<32I", rec, TAIL_A + EXT_SIZE, *([4] * 32))
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
        rec[N.N_AMP_INDEX] = rec[N.N_AMP_INDEX2] = nd.active_index & 0xFF
        rec[N_INLINE_FLAG] = 0
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
        if not rec[N.N_PS_NAME]:
            raise WriteError(f"line id {own}: a power supply placed here is not "
                             "written yet -- its record layout is still being checked")
        _text_into(rec, N.N_PS_NAME, nd.supply)
        if nd.supply_type >= 0:
            rec[N.N_PS_TYPE] = nd.supply_type & 0xFF
    elif rec[N.N_PS_NAME]:
        rec[N.N_PS_NAME] = 0
        rec[N.N_PS_TYPE] = 0

    tail = _tail(extended)
    rec[TAIL_HC + tail] = nd.hc & 0xFF
    homes = TAIL_HOMES + tail
    if any(rec[homes:homes + 128]):
        # filled in: a 1 for each home, 4 for the rest
        for k in range(32):
            struct.pack_into("<I", rec, homes + 4 * k, 1 if k < nd.hc else 4)
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
