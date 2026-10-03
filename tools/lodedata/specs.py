"""Readers for the five Lode Data equipment-library ("spec") files.

All five share the 512-byte header from :mod:`lodedata.header` and then hold
fixed-capacity, fixed-stride record tables.  The tables are pre-allocated at a
constant size, which is why two different spec sets are byte-for-byte the same
length; unused slots are simply zero-filled.

Numeric fields are signed 32-bit little-endian integers holding the real value
multiplied by 1e6 (see docs/file-formats.md).
"""
from dataclasses import dataclass, field, asdict
from pathlib import Path
import struct

from .header import read_header, HEADER_SIZE, LodeHeader

SCALE = 1_000_000            # int32 fixed-point scale used throughout
RECORD_MARK = 0x6F           # first byte of a live 11.1-format .cbl / .cpr record


def _record_mark(data: bytes) -> int:
    """A live record starts with the file's format version, major*10 + minor:
    0x6F (111) in an 11.1 file, 0x79 (121) in a 12.1 one."""
    major, minor = data[26], data[27]
    return major * 10 + minor if 0 < major < 25 and minor < 10 else RECORD_MARK


def _name(buf: bytes) -> str:
    return buf.split(b"\0", 1)[0].strip().decode("latin-1")


def _fx(raw: int) -> float:
    """Fixed-point int32 -> float."""
    return raw / SCALE


# --------------------------------------------------------------------------
# layout table: (data_start, record_stride, name_offset)
# --------------------------------------------------------------------------
LAYOUT = {
    "cbl": (512, 394, 5),
    "cpr": (626, 114, 5),
    "atv": (849, 362, 5),
    "tap": (641, 454, 5),
}

# A tap file is a 129-byte prefix after the header, then 512 rows of 454
# bytes.  A row is one Tap ID -- the number the screen shows and the number
# typed after the port count ("4.23") -- with a part for each port count:
#   +0    Tap ID, int32 fixed point
#   +5    2-port part      +117  4-port part
#   +229  6-port part      +341  8-port part
# Each part slot is 112 bytes: the part number, then the Tap Value block at
# +25 and the Tap Losses (insertion) block at +65.  A design file refers to a
# tap by (row, port code), port code 0/1/2/3 = 2/4/6/8 ports, so the row
# number matters as much as the ID.  Confirmed on the AL004 design: rows 3, 5,
# 9 and 11 of WV750-2026 are Tap IDs 20, 17, 11 and 4, exactly as its Design
# screen shows them.
TAP_PORT_SLOTS = {2: 5, 4: 117, 6: 229, 8: 341}
TAP_PORT_CODES = {2: 0, 4: 1, 6: 2, 8: 3}
# within a slot, relative to the part-number field
TAP_VALUE_BLOCK = 25        # losses toward the tap ports
TAP_INSERTION_BLOCK = 65    # hard cable in to hard cable out
TAP_ID_OFFSET = 0
TAP_NAME_SLOTS = TAP_PORT_SLOTS      # kept for older callers

# The actives table starts six records into the .atv record area: a design
# file's active index i is record i + 6.  Each record carries eight
# Configuration Table slots of 18 bytes from +214; the Active ID -- text, so
# "11H" is as valid as "61" -- sits 5 bytes into each slot.  Slot 0 is the
# base unit, the rest are plug-in variants ("68N", "68U", ...).
ATV_INDEX_BASE = 6
ATV_CONFIG_BASE = 214
ATV_CONFIG_STRIDE = 18
ATV_CONFIG_SLOTS = 8
# Before the name, the banks the Actives tab's Fwd Pad / Ret Pad / Fwd EQ /
# Ret EQ columns name, one byte each, less one: forward and return EQ at
# +1, +2, forward and return pad at +3, +4.  WV750: FM901e-B shows pads 2 2,
# EQs 1 1 and stores 0 0 1 1; setting BRIDGER 61's Ret Pad to 2 moved +4
# alone.  The EQ pair is taken to run the same way.
ATV_EQ_BANKS, ATV_PAD_BANKS = 1, 3


# Older spec files -- WVEXT862, saved by Lode 4 ("Design 4.22" in its .par):
# .cbl and .cpr 5.1, .atv 6.0, .tap 3.0, .par 2.10 -- hold the same fields
# with 15-character part names where the current files have 25, fewer slots
# (51 actives, 4 Pads/EQs banks, 25 in-line devices, 63 tap rows, 15 power
# supplies) and none of the later Parameters pages (transformers, tilts, the
# 600-900 series).  Lode 12 reads them as they are; so do these readers.
CLASSIC_NAME = 15
CLASSIC_LAYOUT = {
    "cbl": (512, 384, 5),
    "cpr": (616, 104, 5),
    "atv": (1021, 318, 5),       # record 0 is active index 0
    "tap": (641, 414, 5),
}
CLASSIC_ATV_RECORDS = 51
# The actives table is 251 records in the current file, 51 in the older:
# the Pads/EQs banks start one byte after the last (93884 = 3021 + 251 x 362
# + 1; 17240 = 1021 + 51 x 318 + 1).  Records are read by that count, not
# by whether their figures look likely.
ATV_RECORDS = 251
# Power Steps, (volts, amps) pairs: the older record six from +79 up to In
# F3 at +127 (WVEXT862's LEs 42 V ... 90 V); the current one eight from +99,
# as the Actives window's Power Steps tab has them: "Min. Voltage",
# "Amperage 1" ... "Voltage 8", "Amperage 8" (NBERN1GHz's FM332 45 V 0.73 A
# ... 90 V 0.32 A, the user's recording; KERMIT's MB-750D-H uses seven).
CLASSIC_ATV_STEPS, ATV_STEPS = (79, 6), (99, 8)
# The Reserve Gain tab: "Ret. Mod. Part Number", the only text after the
# part number (Buckhannon's item 42 "RA-KIT-40L", KERMIT's "RA-KIT\40";
# NUL-ended, what follows the NUL is left from an older entry), and "Fwd
# Reserve Gain", "Ret Reserve Gain" (BH1GHzMid's FM332s 2.00 forward)
ATV_RETURN_MODULE, ATV_RESERVE_GAIN = (30, 55), (91, 95)
# In and Out at the extra forward frequencies F3-F6, four of each: the
# current record's from +171 and +195, the older record's from +127 and
# +151.  WV750's bridger 41 holds 10.1 / 43.0 at F3, as WVEXT862's FNB99 41
# does in the older record; BH1GHzMid's FM332 12.2 / 45.0 at 550 (F3) and
# 12.9 / 50.0 at 860 (F4) -- 45.00 and 50.00 under the user's screenshot's
# 550 and 860 at 1.2-1.4; NBERN1GHz's 13.90 is its Actives tab's "In - 750"
ATV_F3 = (171, 195)
CLASSIC_ATV_F3 = (127, 151)
EXTRA_FORWARD = 4                # F3, F4, F5, F6
CLASSIC_TAP_PORT_SLOTS = {2: 5, 4: 107, 6: 209, 8: 311}


def _classic(data: bytes) -> bool:
    """A file in the older layout: its format version (bytes 26-27) is below
    the 11.1 / 12.1 the current files carry."""
    return 0 < data[26] < 11


def _records(data: bytes, kind: str):
    start, stride, _ = (CLASSIC_LAYOUT if _classic(data) else LAYOUT)[kind]
    n = (len(data) - start) // stride
    for i in range(n):
        off = start + i * stride
        yield i, off, data[off:off + stride]


# --------------------------------------------------------------------------
# cables
# --------------------------------------------------------------------------
@dataclass
class CableSpec:
    slot: int
    name: str
    index: int
    loop_resistance_ohm_per_ft: float   # int32 * 1e-6, i.e. 1070 -> 1.07 ohm/1000ft
    forward_coeffs: list                # 10 fixed-point values, forward path
    return_coeffs: list                 # 10 fixed-point values, return path
    footage_part: str                   # "FT-625" style footage/marker part
    connector_part: str                 # "PT-625" style connector part
    trailing: list
    # the Series/Colors tab: for series 0-9 (the hundreds of the cable number
    # on the Design screen) the colour that number is drawn in, "#rrggbb",
    # and the series' name, which the line's info box adds after the cable
    series: list = field(default_factory=list)


def read_cables(data: bytes) -> list:
    out = []
    mark = _record_mark(data)
    n = CLASSIC_NAME if _classic(data) else 25     # every field after the name moves
    for slot, off, seg in _records(data, "cbl"):
        if seg[0] != mark:
            continue
        name = _name(seg[5:5 + n])
        if not name:
            continue
        out.append(CableSpec(
            slot=slot,
            name=name,
            index=struct.unpack_from("<H", seg, 1)[0],
            loop_resistance_ohm_per_ft=_fx(struct.unpack_from("<i", seg, 5 + n)[0]),
            forward_coeffs=[_fx(v) for v in struct.unpack_from("<10i", seg, 9 + n)],
            return_coeffs=[_fx(v) for v in struct.unpack_from("<10i", seg, 49 + n)],
            footage_part=_name(seg[89 + n:104 + n]),
            connector_part=_name(seg[104 + n:119 + n]),
            trailing=list(struct.unpack_from("<5i", seg, 119 + n)),
            series=[_series(seg, 139 + n + 23 * k) for k in range(10)],
        ))
    return out


def _series(seg: bytes, o: int) -> list:
    """One series slot, 23 bytes: a Windows colour (0x00BBGGRR), four bytes
    no file sets, the name (15).  WVEXT862 holds red 255,0,0 and green 0,200,0
    with names (4 Upgrade, 5 Dual New Build); untouched slots are 0,255,0."""
    c = struct.unpack_from("<I", seg, o)[0]
    return [f"#{c & 0xFF:02x}{c >> 8 & 0xFF:02x}{c >> 16 & 0xFF:02x}", _name(seg[o + 8:o + 23])]


# --------------------------------------------------------------------------
# couplers / splitters / power inserters
# --------------------------------------------------------------------------
@dataclass
class CouplerSpec:
    slot: int
    name: str
    alt_name: str
    code: float              # packed family/value code; for the plain SSP-nK parts
                             # it is exactly the dB in the part number (SSP-7K -> 7.0),
                             # for others it looks like family*100 + value
                             # (RLDC12-8 -> 408).  Needs ground truth to split.
    values: list             # remaining fixed-point fields, still being mapped
    tap_legs: int = 1        # branches this coupler creates (stored as count-1)
    internal: bool = False   # an internal coupler: no fittings BOMed, must sit
                             # at the same location as an amplifier


def read_couplers(data: bytes) -> list:
    out = []
    mark = _record_mark(data)
    n = CLASSIC_NAME if _classic(data) else 25
    for slot, off, seg in _records(data, "cpr"):
        if seg[0] != mark:
            continue
        name = _name(seg[5:5 + n])
        code = _fx(struct.unpack_from("<i", seg, 1)[0])
        # a record with an ID and no part number is still a coupler:
        # HUMB1GHzMid's 92 (record 10, every loss 0 but the tap leg's 99 at
        # 1002) is drawn 92<2> in green on the user's screenshot, the levels
        # going on through it unchanged
        if not name and not code:
            continue
        out.append(CouplerSpec(
            slot=slot,
            name=name,
            alt_name=_name(seg[13:5 + n]),
            code=code,
            tap_legs=seg[85 + n] + 1,
            internal=bool(seg[88 + n]),
            values=[_fx(v) for v in struct.unpack_from("<20i", seg, 5 + n)],
        ))
    return out


# --------------------------------------------------------------------------
# actives (amplifiers, line extenders, nodes)
# --------------------------------------------------------------------------
@dataclass
class ActiveSpec:
    slot: int
    name: str
    index: int = 0                  # how a design file refers to it
    active_id: str = ""             # what the amp column shows
    config_ids: list = field(default_factory=list)   # base + plug-in variants
    config_slots: list = field(default_factory=list)  # the same by slot, "" for an empty one
    # the Reserve Gain tab: Ret. Mod. Part Number, [Fwd, Ret] Reserve Gain
    return_module: str = ""
    reserve_gain: list = field(default_factory=lambda: [0.0, 0.0])
    # levels required at, and produced by, the active at the four design
    # frequencies: forward high, forward low, return high, return low
    input_levels: list = field(default_factory=list)
    output_levels: list = field(default_factory=list)
    # [[volts, amps], ...] -- actives are constant-power, so the draw is a curve
    power_draw: list = field(default_factory=list)
    values: list = field(default_factory=list)
    # Pads/EQs Bank used for forward pad, return pad, forward EQ, return EQ
    banks: list = field(default_factory=lambda: [1, 1, 1, 1])
    # in and out at the extra forward frequencies F3-F6 (ATV_F3): the older
    # record's In from +127 (after the six power steps) and Out from +151 --
    # WVEXT862's LEs need 14.1 in and put out 43.0 at F3, the FNB99s 10.1 and
    # 43.0, NC4000 0 and 41.1, HLN 3842 NODE 0 and 43.5, the WIFI OMNI 0 and 0
    # (43.1's end line reads 0.00 at 550; Lode's "550 input 20.98 to LE at
    # 25.3." is 20.98 less its 10 pad under 14.1)
    extra_in: list = field(default_factory=lambda: [0.0] * EXTRA_FORWARD)
    extra_out: list = field(default_factory=lambda: [0.0] * EXTRA_FORWARD)
    # [in, out] at F3 alone
    f3_levels: list = field(default_factory=lambda: [0.0, 0.0])
    # the Actives window's Custom Cascading tab, one row per active: bit 0
    # "Cust. Casc." (1 Yes), bit 1 "Exclude" (left out of the count), bit k + 1
    # "Casc. k" Valid, k = 1-19: the four bytes before the levels (KERMIT's
    # actives Valid at 1-14 hold Casc. 15 too, in the third).  WV750's and SHINSTON's Ripple
    # nodes are Yes, Exclude, Casc. 1 (0x0007), so they count 0 and the first
    # amplifier after one is 1; WVEXT862's HLN 3842 NODE is Yes, Include,
    # Casc. 1 (0x0005) and its NC4000 No (0), so either is 1 and AL00416 2
    # (Lode's boxes).  Its "11" line extenders are Casc. 1-5: at 23.17,
    # position 6, Lode's Test list says "LE  11/5 before/0 after".  Every row
    # of WVEXT862's and WVBeck750's tabs (the user's set A2) reads so.  u32 at
    # +55, +35 in the older record
    cascading: int = 0


def read_actives(data: bytes) -> list:
    out = []
    classic = _classic(data)
    # the older record: name char[15], then the Ret. Mod. Part Number's 15
    # bytes (blank in WVEXT862), levels at +39 (current +59), the
    # Configuration Table at +170 (current +214); record 0 is index 0
    levels_at, config_at = (39, 170) if classic else (59, ATV_CONFIG_BASE)
    (steps_at, steps), (in_at, out_at) = (CLASSIC_ATV_STEPS, CLASSIC_ATV_F3) if classic else (ATV_STEPS, ATV_F3)
    module = (20, 35) if classic else ATV_RETURN_MODULE
    first, count = (0, CLASSIC_ATV_RECORDS) if classic else (ATV_INDEX_BASE, ATV_RECORDS)
    for slot, off, seg in _records(data, "atv"):
        index = slot - first
        if index >= count:
            break
        if index < 1:
            # a design stores 0 for no active, so record 0 is never placed
            # (SHINSTON's holds "BRIDGER" with every level 0)
            continue
        name = _name(seg[5:20] if classic else seg[5:30])
        if not name:
            continue
        levels = [round(_fx(v), 2) for v in struct.unpack_from("<8i", seg, levels_at)]
        table = []
        for volts, amps in zip(*[iter(struct.unpack_from(f"<{2 * steps}i", seg, steps_at))] * 2):
            if volts > 0 and amps > 0:
                table.append([round(_fx(volts), 1), round(_fx(amps), 3)])
        ids = [_name(seg[o + 5:o + 10]) for o in range(
            config_at, config_at + ATV_CONFIG_STRIDE * ATV_CONFIG_SLOTS,
            ATV_CONFIG_STRIDE)]
        extra_in, extra_out = ([round(_fx(v), 2) for v in struct.unpack_from(f"<{EXTRA_FORWARD}i", seg, o)]
                               for o in (in_at, out_at))
        gains = [] if classic else [round(_fx(struct.unpack_from("<i", seg, o)[0]), 2)
                                    for o in ATV_RESERVE_GAIN]
        # the four bytes before the levels: Cust. Casc., Exclude, Casc. 1-19
        cascading = struct.unpack_from("<I", seg, levels_at - 4)[0]
        out.append(ActiveSpec(
            slot=slot,
            name=name,
            index=index,
            active_id=ids[0],
            config_ids=[i for i in ids if i],
            config_slots=ids,
            return_module=_name(seg[module[0]:module[1]]),
            reserve_gain=gains or [0.0, 0.0],
            input_levels=levels[0:4],
            output_levels=levels[4:8],
            power_draw=table,
            values=[_fx(v) for v in struct.unpack_from("<24i", seg, levels_at)],
            banks=[seg[ATV_PAD_BANKS] + 1, seg[ATV_PAD_BANKS + 1] + 1,
                   seg[ATV_EQ_BANKS] + 1, seg[ATV_EQ_BANKS + 1] + 1],
            extra_in=extra_in,
            extra_out=extra_out,
            f3_levels=[extra_in[0], extra_out[0]],
            cascading=cascading,
        ))
    return out


# --------------------------------------------------------------------------
# taps
# --------------------------------------------------------------------------
@dataclass
class TapPort:
    """One port-count variant of a tap value."""
    ports: int
    part: str
    tap_value: list = field(default_factory=list)   # [High, Low, Rh, Rl] dB
    insertion: list = field(default_factory=list)   # [High, Low, Rh, Rl] dB
    # the same two at F3-F6 (slots 2-5 of each block): [[value, insertion], ...]
    extra: list = field(default_factory=list)
    # at F3 alone
    f3: list = field(default_factory=lambda: [0.0, 0.0])


@dataclass
class TapSpec:
    slot: int                                   # row number, as a design refers to it
    tap_id: int = 0                             # the row's identifying value
    ports: dict = field(default_factory=dict)   # port count -> TapPort
    parts: dict = field(default_factory=dict)   # port count -> part number

    @property
    def tap_value_db(self) -> float:
        """Nominal value of the row: the forward-high figure of any variant."""
        for n in (2, 4, 8, 6):
            p = self.ports.get(n)
            if p and p.tap_value:
                return p.tap_value[0]
        return 0.0


def _loss4(seg: bytes, base: int) -> list:
    """Read the four required frequencies out of a ten-slot loss block."""
    return [round(_fx(struct.unpack_from("<i", seg, base + 4 * i)[0]), 3)
            for i in (0, 1, 6, 7)]


def _loss_extra(seg: bytes, base: int) -> list:
    """Slots 2-5 of a ten-slot loss block: the extra forward frequencies
    F3-F6."""
    return [round(_fx(v), 3) for v in struct.unpack_from(f"<{EXTRA_FORWARD}i", seg, base + 8)]


def read_taps(data: bytes) -> list:
    out = []
    # the older row: 102-byte part slots, part char[15], the two loss blocks
    # at +15 and +55
    classic = _classic(data)
    slots, width = (CLASSIC_TAP_PORT_SLOTS, CLASSIC_NAME) if classic else (TAP_PORT_SLOTS, 25)
    for slot, off, seg in _records(data, "tap"):
        ports = {}
        for count, o in slots.items():
            part = _name(seg[o:o + min(width, 20)])
            if not part:
                continue
            value, insertion = o + TAP_VALUE_BLOCK - 25 + width, o + TAP_INSERTION_BLOCK - 25 + width
            extra = [list(x) for x in zip(_loss_extra(seg, value), _loss_extra(seg, insertion))]
            ports[count] = TapPort(
                ports=count,
                part=part,
                tap_value=_loss4(seg, value),
                insertion=_loss4(seg, insertion),
                extra=extra,
                f3=extra[0],
            )
        if not ports:
            continue
        tap_id = round(_fx(struct.unpack_from("<i", seg, TAP_ID_OFFSET)[0]))
        out.append(TapSpec(slot=slot, tap_id=tap_id, ports=ports,
                           parts={str(k): v.part for k, v in ports.items()}))
    return out


def read_tap_ids(data: bytes) -> dict:
    """Row -> Tap ID for every row that has one, whether or not it has a part
    for any port count.  HUMB1GHzMid's row 6 is Tap ID 21 with every part
    empty; the user keyed an 8-port 21 there (1.6 on the screenshot) and
    Lode drew it <21>, the levels going on through it unchanged (1.7 = 1.6)."""
    out = {}
    for slot, off, seg in _records(data, "tap"):
        tap_id = round(_fx(struct.unpack_from("<i", seg, TAP_ID_OFFSET)[0]))
        if tap_id:
            out[slot] = tap_id
    return out


# --------------------------------------------------------------------------
# parameters (Spec Edit -> Parameters).  Every offset below was checked
# against screenshots of all six tabs of WV750-2026.par; see
# docs/file-formats.md 3.5 for what is proven and what is not.
# --------------------------------------------------------------------------
@dataclass
class SupplySpec:
    type_id: int          # the number a design stores with each placed supply
    name: str
    volts: float
    amps: float
    rating: float         # the Powering tab's "% Capacity" column


PAR_SUPPLY_NAMES, PAR_SUPPLY_NAME_STRIDE = 1567, 25
PAR_SUPPLY_TABLE, PAR_SUPPLY_STRIDE = 2212, 20
PAR_SUPPLY_SLOTS = 25          # the Powering tab lists ID 1-25


PAR_FREQUENCIES, PAR_FREQUENCY_STRIDE = 3792, 10
PAR_FREQUENCY_NAMES = ("F1", "F2", "F3", "F4", "F5", "F6", "R1", "R2", "R3", "R4")

# The older .par (2.10, 3102 bytes: WVEXT862, "Design 4.22") holds the same
# fields.  Its part names are char[15] -- the miscellaneous parts from 578,
# the housings from 668, the supplies from 1357 -- it has 15 power supplies
# (table from 1602) and ends where the current file's 600 Series flag
# starts.  Everything else sits at a fixed shift from the current offset:
# (first current offset, end, shift).  Checked field by field against
# WV750-2026: the tap-type and ports tables, strand types 000/200/300/400,
# the points, the housing sizes, levels 0-1, the max amperage row, the
# frequency table (870 54 550 / 40 5) and the EQ selection all line up.
CLASSIC_PAR_SIZE = 3102
CLASSIC_PAR_SHIFTS = ((512, 578, 0), (1053, 1072, -190), (1082, 1514, -200),
                      (2712, 3912, -810))
CLASSIC_PAR_MISC, CLASSIC_PAR_HOUSING_PARTS = 578, 668
CLASSIC_PAR_SUPPLY_NAMES, CLASSIC_PAR_SUPPLY_TABLE, CLASSIC_PAR_SUPPLY_SLOTS = 1357, 1602, 15


def _par_at(data: bytes, offset: int):
    """Where ``data`` holds the Parameters field the current layout keeps at
    ``offset``; None when the older layout has no such field."""
    if not _classic(data):
        return offset
    for lo, hi, shift in CLASSIC_PAR_SHIFTS:
        if lo <= offset < hi:
            return offset + shift
    return None


def read_frequencies(data: bytes) -> dict:
    """Column labels of the design frequencies, e.g. {"F1": "750", "R1": "40"}.

    Only enabled columns are returned.  The labels are what the screen heads
    its level columns with; the manual is clear they are labels, and that the
    spec files hold a loss per column rather than per MHz."""
    out = {}
    for k, key in enumerate(PAR_FREQUENCY_NAMES):
        o = _par_at(data, PAR_FREQUENCIES + PAR_FREQUENCY_STRIDE * k)
        if o is None or o + 6 > len(data):
            break
        if data[o + 5]:
            out[key] = _name(data[o:o + 5])
    return out


# In-line devices (the Actives file's "Inline Eqs"): Q1, Q2 ... placed in a
# node's amp column.  69-byte records from a fixed offset (the .atv is a
# fixed-size file); name, then losses at the four design columns
# [F1, F2, R1, R2].  WV750: Q2 LEQ-PEA-0 = 1.2 / 1.0 / 1.2 / 0.7, exactly what
# it costs on AL004's Design screen at 6.8.  The fifth is F3, unlike the
# cable and coupler blocks: WVEXT862's LEQ-PEA-8 (1.8 8.3 1.2 0.7 3.1) takes
# 3.1 at 550 on the older AL004's 6.9 and 7.6.  The Actives window's Inline
# EQs tab lists 24 -- "EQ", then Q2-Q24 (the user's recording of NBERN1GHz)
# -- with ten Loss columns in the order stored: F1, F2, R1, R2, F3-F6, R3,
# R4.  What follows the 24th record is another table.
ATV_INLINE, ATV_INLINE_STRIDE, ATV_INLINE_SLOTS = 169372, 69, 25
ATV_INLINE_LOSS = 29


@dataclass
class InlineSpec:
    number: int          # the n of Qn
    name: str
    losses: list         # dB at F1, F2, R1, R2
    f3: float = 0.0      # dB at F3
    extra: list = field(default_factory=list)   # dB at F3-F6


# the older .atv: 25 records of 59 bytes from 57464, name char[15], losses at +19
CLASSIC_INLINE = (57464, 59, 25, 19)


def read_inline(data: bytes) -> list:
    out = []
    base, stride, slots, at = CLASSIC_INLINE if _classic(data) else (
        ATV_INLINE, ATV_INLINE_STRIDE, ATV_INLINE_SLOTS, ATV_INLINE_LOSS)
    for k in range(1, slots):
        o = base + stride * k
        if o + at + 40 > len(data):
            break
        name = _name(data[o:o + min(at, 20)])
        losses = [round(_fx(v), 3) for v in struct.unpack_from("<10i", data, o + at)]
        if name:
            out.append(InlineSpec(number=k, name=name, losses=losses[:4], f3=losses[4],
                                  extra=losses[4:8]))
    return out


# Pads/EQs Banks 1-8, the Actives window's tabs: 129 rows of 68 bytes each,
# then the four part-number prefixes, char[11] each -- forward pad, return
# pad, forward EQ, return EQ (WV750 bank 1: SPB- SPB- SEQ-750- MEQ-42-; bank
# 4, the nodes': NODE-; bank 5, the FM902s': NPB- NPB- CE-120- MEQ-85-).
# A row is its four labels, char[5] each and right-aligned as stored
# ("   8"), at +0, +5 (pads) and +58, +63 (EQs), and between them the
# bank tabs' twelve numbers: forward pad dB Loss; forward EQ Loss at F1, F2,
# F3-F6 (750, 54, 550, ...); return pad dB Loss; return EQ Loss at R1-R4
# (40, 5, ...).  A column ends at its row labelled FLAG ("Flag" in BH1GHzMid),
# and that row is a choice like any other: the pad there is 21 dB, one past
# the largest, and Lode picks it when no pad is large enough -- "Forward Pad:
# Flag", "Return Pad: Flag" on 1.7 of the user's BH1GHzMid and HUMB1GHzMid
# screenshots.  Row 0 is VOID; a design stores row - 1, so AL004's AL00416,
# forward EQ 16, is row 17, "  12" -- what its info box shows.
ATV_BANKS, ATV_BANK_COUNT, ATV_BANK_STRIDE = 93884, 8, 8816
ATV_BANK_ROW, ATV_BANK_ROWS = 68, 129
ATV_BANK_LABELS = (0, 5, 58, 63)


@dataclass
class PadEqBank:
    number: int
    prefixes: list       # forward pad, return pad, forward EQ, return EQ
    labels: list         # per column, the labels by stored value (row 1 on)
    values: list         # per row from row 1: fwd pad, fwd EQ F1-F6, ret pad, ret EQ R1-R4
    # row 0's four labels ("VOID"): a design stores row - 1, so 255 is row 0
    # (the older AL004's WIFI OMNIs hold 255 for both EQs; Lode shows VOID)
    void: list = field(default_factory=list)


def _label(raw: bytes) -> str:
    return raw.split(b"\0")[0].decode("latin-1")


CLASSIC_BANKS, CLASSIC_BANK_COUNT = 17240, 4     # the older .atv's banks 1-4


def read_pad_eq_banks(data: bytes) -> list:
    out = []
    first, count = (CLASSIC_BANKS, CLASSIC_BANK_COUNT) if _classic(data) else (
        ATV_BANKS, ATV_BANK_COUNT)
    for k in range(count):
        base = first + ATV_BANK_STRIDE * k
        end = base + ATV_BANK_ROW * ATV_BANK_ROWS
        if end + 44 > len(data):
            break
        rows = [data[base + ATV_BANK_ROW * r:base + ATV_BANK_ROW * (r + 1)]
                for r in range(1, ATV_BANK_ROWS)]
        labels = []
        for o in ATV_BANK_LABELS:       # each column ends at its FLAG row
            column = [_label(row[o:o + 5]) for row in rows]
            flag = next((i for i, x in enumerate(column) if x.strip().upper() == "FLAG"), None)
            labels.append(column[:flag + 1] if flag is not None else
                          [x for x in column if x.strip()])
        out.append(PadEqBank(
            number=k + 1,
            prefixes=[_label(data[end + 11 * i:end + 11 * i + 11]) for i in range(4)],
            labels=labels,
            values=[[round(_fx(v), 3) for v in struct.unpack_from("<12i", row, 10)]
                    for row in rows],
            void=[_label(data[base + o:base + o + 5]).strip() for o in ATV_BANK_LABELS]))
    return out


PAR_LEVELS, PAR_LEVEL_STRIDE, PAR_LEVEL_COUNT = 1154, 20, 16
PAR_TAP_MARGIN = 1134


def read_levels(data: bytes) -> dict:
    """System Levels 0-15 and the tap margin.

    Each level is [min forward high, min forward low, max return high, max
    return low] at the tap ports -- the lv column picks one per node.  Checked
    on AL004: with WV750-2026's level 0 (17 / 10 / 45 / 45) and level 1
    (19 / 12 / 45 / 45) exactly the taps its Design screen shows red come out
    red.  An unused level is all zeros.
    """
    levels = []
    for k in range(PAR_LEVEL_COUNT):
        o = _par_at(data, PAR_LEVELS + PAR_LEVEL_STRIDE * k)
        if o is None or o + 16 > len(data):
            break
        levels.append([round(_fx(v), 2) for v in struct.unpack_from("<4i", data, o)])
    at = _par_at(data, PAR_TAP_MARGIN)
    margin = _fx(struct.unpack_from("<i", data, at)[0]) \
        if at is not None and at + 4 <= len(data) else 0.0
    return {"levels": levels, "tap_margin": round(margin, 2)}


def read_supplies(data: bytes) -> list:
    """Power supply types 1-25: name, voltage rating, current rating and
    % capacity -- the Powering tab's table."""
    out = []
    if _classic(data):
        names, stride, width, table, slots = (CLASSIC_PAR_SUPPLY_NAMES, CLASSIC_NAME, CLASSIC_NAME,
                                              CLASSIC_PAR_SUPPLY_TABLE, CLASSIC_PAR_SUPPLY_SLOTS)
    else:
        names, stride, width, table, slots = (PAR_SUPPLY_NAMES, PAR_SUPPLY_NAME_STRIDE, 23,
                                              PAR_SUPPLY_TABLE, PAR_SUPPLY_SLOTS)
    for k in range(slots):
        o = table + PAR_SUPPLY_STRIDE * k
        if o + 12 > len(data):
            break
        volts, amps, rating = (_fx(v) for v in struct.unpack_from("<3i", data, o))
        if volts <= 0:
            continue
        n = names + stride * k
        out.append(SupplySpec(type_id=k + 1, name=_name(data[n:n + width]),
                              volts=round(volts, 2), amps=round(amps, 2),
                              rating=round(rating, 2)))
    return out


PAR_TAP_TYPE_BY_PORTS = 512     # u8[33]: ports 0-32 -> tap port code (0/1/2/3 = 2/4/6/8)
PAR_PORTS_BY_HOMES = 545        # u8[33]: homes 0-32 -> number of ports
PAR_MISC_PARTS = 578            # char[25] x3: HTH connectors, splices, terminators
PAR_HOUSING_PARTS, PAR_HOUSINGS = 728, 13   # char[25] each; min size u8 at 1063 + k
PAR_HOUSING_SIZE = 1063
PAR_STRAND_SERIES = 1053        # bit n: series n00 (000-500) is a strand/trench type
PAR_STRAND_600 = 3912           # u8 each for 600, 700, 800, 900 Series
# Underground Housings points, u8 each
PAR_POINTS = {"equalizer": 1056, "amplifier": 1057, "line_extender": 1058, "tap": 1059,
              "tap_8_port": 1060, "coupler": 1061, "power_supply": 1062}
PAR_NIU = 1098                  # i32 x5 in the tab's order; whole numbers (1.11 saves as 1)
PAR_SIGNAL_DISPLAY, PAR_DISTANCE_UNITS = 1138, 1142   # 0 dBmV / 1 dBuV; 0 Ftg / 1 m / 2 dM
NIU_FIELDS = ("system_penetration", "offhook", "ring", "additional_line", "offhook_limit")
PAR_CROSSOVER, PAR_RETURN_CROSSOVER = 1118, 1122
PAR_MAX_LE_CASCADE, PAR_LINES_PER_FORM = 1126, 1130
PAR_BACKFEED_CABLE, PAR_FWDFEED_CABLE = 1146, 1470
PAR_INTERPOLATION = 1474        # 0 Step, 1 Linear, 2 Constant Wattage
PAR_OPTIMIZATION = 1482         # 0 OP-, 1 OFf, 2 OP+
PAR_OVERVOLTAGE = 1478          # u8, 1 = On
PAR_MAX_AMPS = 1486             # i32 x6 in the tab's order
PAR_EQ_PLACEMENT = 1510         # 0 EQ-, 1 EQ+, 2 EQe
# per level: Min F3, Min F4, Min F5, Min F6, Max R3, Max R4
PAR_EXTRA_LEVELS, PAR_EXTRA_LEVEL_STRIDE = 2976, 24
PAR_EQ_SELECTION = 3892         # u16 x4: Fwd High, Fwd Low (index into F1-F6), Ret High, Ret Low (R1-R4)
PAR_ENFORCE_TAP_WINDOW = 3904   # u8
PAR_MAX_TAP_CASCADE = 3909      # u8
PAR_OVER_EQUALIZATION = 3911    # u8, 1 = Allow Over Equalization ticked
# Transformers 1-8: 260-byte records, char[256] part number then i32 volts.
# Slot 1's name starts on 3915, the 900 Series flag's byte, so its first
# letter is lost when the file is saved (XFMR-T1 is stored as FMR-T1).
PAR_TRANSFORMERS, PAR_TRANSFORMER_STRIDE, PAR_TRANSFORMER_VOLTS = 3915, 260, 256
PAR_ENFORCE_TAP_TILT = 6000     # u8
PAR_FLAG_TILT = 6001            # u8 Flag Hi/Lo Tilt
PAR_TILTS, PAR_TILT_STRIDE = 6002, 16   # Max/Min Tilt Fwd, Max/Min Tilt Ret per level
PAR_SHOW_COUNT_TYPES = 6514     # u8
PAR_PRE_LOAD = 6515             # u8, only in the 6516-byte files version 12 writes
INTERPOLATION = {0: "step", 1: "linear", 2: "constant_wattage"}
MAX_AMPS_THROUGH = ("power_inserter", "amplifier", "bridger_port", "coupler",
                    "line_extender", "tap")


def read_parameters(data: bytes) -> dict:
    """The Parameters tabs, as far as they are proven.

    WV750-2026 reads back as its screens show it: strand/trench types 000,
    200, 300, 400; Power Interpolation Constant Wattage (2); maximum amperage
    through 16 / 15 / 15 / 15 / 15 / 12; ports 1-2 -> 2-port, 3-4 -> 4-port,
    5 and up -> 8-port; homes n -> n ports; HOUS TO HOUS / SGMC / GTRM;
    housings TV-60 4 ... TV-1024 27; points amplifier 16, line extender 11,
    power supply 30; max crossover 3.00, max return crossover 99.00; the tap
    windows 12 / 16 (750 / 54) and 16 / 16 (40 / 5), which sit in the
    frequency table; and Min 550 of 15 / 17 on levels 0 / 1.  A test copy
    saved with distinct values placed the rest: NIU, the cascades, lines per
    form, replacement cables, overvoltage, over-equalization, the tilts and
    the other points.
    """
    classic = _classic(data)
    if len(data) < (CLASSIC_PAR_SIZE if classic else PAR_TILTS + PAR_TILT_STRIDE * 16):
        return {}

    def fx(o):
        at = _par_at(data, o)
        return round(_fx(struct.unpack_from("<i", data, at)[0]), 3) if at is not None else 0.0

    def u8(o):
        at = _par_at(data, o)
        return data[at] if at is not None and at < len(data) else 0

    def text(o, width):
        at = _par_at(data, o)
        return _name(data[at:at + width]) if at is not None else ""

    mask = u8(PAR_STRAND_SERIES) & 0x3F
    strand = [n for n in range(6) if mask >> n & 1] + \
        [6 + k for k in range(4) if u8(PAR_STRAND_600 + k)]
    label = [text(PAR_FREQUENCIES + PAR_FREQUENCY_STRIDE * k, 5) for k in range(10)]
    fwd, ret = label[:6], label[6:]
    eq_sel = struct.unpack_from("<4H", data, _par_at(data, PAR_EQ_SELECTION))
    windows = {}
    for k, key in enumerate(PAR_FREQUENCY_NAMES):
        windows[key] = fx(PAR_FREQUENCIES + PAR_FREQUENCY_STRIDE * k + 6)
    width = CLASSIC_NAME if classic else 25
    parts, misc = (CLASSIC_PAR_HOUSING_PARTS, CLASSIC_PAR_MISC) if classic else (
        PAR_HOUSING_PARTS, PAR_MISC_PARTS)
    housings = []
    for k in range(PAR_HOUSINGS):
        name = _name(data[parts + width * k:parts + width * k + width])
        if name:
            housings.append({"number": k + 1, "part": name,
                             "min_points": u8(PAR_HOUSING_SIZE + k)})
    transformers = [] if classic else [t for t in (
        {"id": k + 1,
         "part": _name(data[PAR_TRANSFORMERS + PAR_TRANSFORMER_STRIDE * k + (k == 0):
                            PAR_TRANSFORMERS + PAR_TRANSFORMER_STRIDE * k + PAR_TRANSFORMER_VOLTS]),
         "volts": fx(PAR_TRANSFORMERS + PAR_TRANSFORMER_STRIDE * k + PAR_TRANSFORMER_VOLTS)}
        for k in range(8)) if t["part"] or t["volts"]]
    return {
        "strand_series": strand,
        "distance_units": {0: "Ftg", 1: "m", 2: "dM"}.get(int(fx(PAR_DISTANCE_UNITS)), fx(PAR_DISTANCE_UNITS)),
        "signal_display": {0: "dBmV", 1: "dBuV"}.get(int(fx(PAR_SIGNAL_DISPLAY)), fx(PAR_SIGNAL_DISPLAY)),
        "show_count_types": bool(u8(PAR_SHOW_COUNT_TYPES)),
        "eq_placement": {0: "EQ-", 1: "EQ+", 2: "EQe"}.get(int(fx(PAR_EQ_PLACEMENT)), fx(PAR_EQ_PLACEMENT)),
        "optimization": {0: "OP-", 1: "OFf", 2: "OP+"}.get(int(fx(PAR_OPTIMIZATION)), fx(PAR_OPTIMIZATION)),
        "enforce_tap_window": bool(u8(PAR_ENFORCE_TAP_WINDOW)),
        "enforce_tap_tilt": bool(u8(PAR_ENFORCE_TAP_TILT)),
        "pre_load": len(data) > PAR_PRE_LOAD and bool(u8(PAR_PRE_LOAD)),
        "eq_selection": {"fwd_high": fwd[eq_sel[0] % 6], "fwd_low": fwd[eq_sel[1] % 6],
                         "ret_high": ret[eq_sel[2] % 4], "ret_low": ret[eq_sel[3] % 4]},
        "transformers": transformers,
        "flag_hi_lo_tilt": bool(u8(PAR_FLAG_TILT)),
        "power_interpolation": INTERPOLATION.get(u8(PAR_INTERPOLATION), "constant_wattage"),
        "max_amps_through": {k: fx(PAR_MAX_AMPS + 4 * i) for i, k in enumerate(MAX_AMPS_THROUGH)},
        "tap_type_by_ports": {n: (2, 4, 6, 8)[u8(PAR_TAP_TYPE_BY_PORTS + n) & 3]
                              for n in range(1, 33)},
        "ports_by_homes": {n: u8(PAR_PORTS_BY_HOMES + n) for n in range(1, 33)},
        "misc_parts": {k: _name(data[misc + width * i:misc + width * i + width])
                       for i, k in enumerate(("hth_connectors", "splices", "terminators"))},
        "housings": housings,
        "points": {k: u8(o) for k, o in PAR_POINTS.items()},
        "niu": {k: fx(PAR_NIU + 4 * i) for i, k in enumerate(NIU_FIELDS)},
        "max_crossover": fx(PAR_CROSSOVER),
        "max_return_crossover": fx(PAR_RETURN_CROSSOVER),
        "max_le_cascade": int(fx(PAR_MAX_LE_CASCADE)),
        "max_tap_cascade": u8(PAR_MAX_TAP_CASCADE),
        "lines_per_form": int(fx(PAR_LINES_PER_FORM)),
        "replacement_cables": {"backfeed": int(fx(PAR_BACKFEED_CABLE)),
                               "fwd_feed": int(fx(PAR_FWDFEED_CABLE))},
        "allow_over_equalization": bool(u8(PAR_OVER_EQUALIZATION)),
        "overvoltage_check": bool(u8(PAR_OVERVOLTAGE)),
        "tilts": [[fx(PAR_TILTS + PAR_TILT_STRIDE * lv + 4 * j) for j in range(4)]
                  for lv in range(16)],
        "tap_windows": windows,
        "extra_levels": [[fx(PAR_EXTRA_LEVELS + PAR_EXTRA_LEVEL_STRIDE * lv + 4 * j) for j in range(6)]
                         for lv in range(16)],
    }


# --------------------------------------------------------------------------
# a whole spec set (the five files that share a base name)
# --------------------------------------------------------------------------
READERS = {
    "cbl": read_cables,
    "cpr": read_couplers,
    "atv": read_actives,
    "tap": read_taps,
}


@dataclass
class SpecSet:
    name: str
    headers: dict = field(default_factory=dict)
    cables: list = field(default_factory=list)
    couplers: list = field(default_factory=list)
    actives: list = field(default_factory=list)
    taps: list = field(default_factory=list)
    supplies: list = field(default_factory=list)
    inline: list = field(default_factory=list)
    banks: list = field(default_factory=list)
    frequencies: dict = field(default_factory=dict)
    levels: list = field(default_factory=list)
    tap_margin: float = 0.0
    parameters: dict = field(default_factory=dict)
    parameters_raw: bytes = b""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "headers": {k: {kk: vv for kk, vv in asdict(v).items() if kk != "raw"}
                        for k, v in self.headers.items()},
            "cables": [asdict(c) for c in self.cables],
            "couplers": [asdict(c) for c in self.couplers],
            "actives": [asdict(a) for a in self.actives],
            "taps": [asdict(t) for t in self.taps],
            "supplies": [asdict(x) for x in self.supplies],
        }


def load_spec_set(base: str | Path) -> SpecSet:
    """Load ``<base>.cbl/.cpr/.atv/.tap/.par`` as one equipment library."""
    base = Path(base)
    spec = SpecSet(name=base.name)
    for ext in ("cbl", "cpr", "atv", "tap", "par"):
        p = base.with_suffix("." + ext)
        if not p.exists():
            continue
        data = p.read_bytes()
        spec.headers[ext] = read_header(data)
        if ext == "par":
            spec.parameters_raw = data[HEADER_SIZE:]
            spec.supplies = read_supplies(data)
            spec.frequencies = read_frequencies(data)
            lv = read_levels(data)
            spec.levels, spec.tap_margin = lv["levels"], lv["tap_margin"]
            spec.parameters = read_parameters(data)
        else:
            setattr(spec, {"cbl": "cables", "cpr": "couplers",
                           "atv": "actives", "tap": "taps"}[ext],
                    READERS[ext](data))
            if ext == "atv":
                spec.inline = read_inline(data)
                spec.banks = read_pad_eq_banks(data)
    return spec
