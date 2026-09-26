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


def _records(data: bytes, kind: str):
    start, stride, _ = LAYOUT[kind]
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


def read_cables(data: bytes) -> list:
    out = []
    mark = _record_mark(data)
    for slot, off, seg in _records(data, "cbl"):
        if seg[0] != mark:
            continue
        name = _name(seg[5:30])
        if not name:
            continue
        out.append(CableSpec(
            slot=slot,
            name=name,
            index=struct.unpack_from("<H", seg, 1)[0],
            loop_resistance_ohm_per_ft=_fx(struct.unpack_from("<i", seg, 30)[0]),
            forward_coeffs=[_fx(v) for v in struct.unpack_from("<10i", seg, 34)],
            return_coeffs=[_fx(v) for v in struct.unpack_from("<10i", seg, 74)],
            footage_part=_name(seg[114:129]),
            connector_part=_name(seg[129:144]),
            trailing=list(struct.unpack_from("<5i", seg, 144)),
        ))
    return out


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
    for slot, off, seg in _records(data, "cpr"):
        if seg[0] != mark:
            continue
        name = _name(seg[5:30])
        if not name:
            continue
        out.append(CouplerSpec(
            slot=slot,
            name=name,
            alt_name=_name(seg[13:30]),
            code=_fx(struct.unpack_from("<i", seg, 1)[0]),
            tap_legs=seg[110] + 1,
            internal=bool(seg[113]),
            values=[_fx(v) for v in struct.unpack_from("<20i", seg, 30)],
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
    housing: str = ""
    option_parts: list = field(default_factory=list)
    # levels required at, and produced by, the active at the four design
    # frequencies: forward high, forward low, return high, return low
    input_levels: list = field(default_factory=list)
    output_levels: list = field(default_factory=list)
    # [[volts, amps], ...] -- actives are constant-power, so the draw is a curve
    power_draw: list = field(default_factory=list)
    values: list = field(default_factory=list)


# The .atv file holds more than the Actives table -- the manual describes
# Reserve Gain, Power Steps, Pads/EQ banks 1-8 and a Configuration Table as
# further pages.  Where the Actives table ends is not mapped, so records are
# checked for plausibility instead of assumed: past the end, the fixed stride
# reads into another page and produces levels like 538.97 dB.
LEVEL_RANGE = (-40.0, 120.0)
VOLTAGE_RANGE = (20.0, 150.0)
MAX_AMPS = 30.0


def _plausible_active(name: str, levels: list, table: list) -> bool:
    if len(name) < 2 or not all(32 <= ord(c) < 127 for c in name):
        return False
    if not all(LEVEL_RANGE[0] <= v <= LEVEL_RANGE[1] for v in levels):
        return False
    for volts, amps in table:
        if not (VOLTAGE_RANGE[0] <= volts <= VOLTAGE_RANGE[1]):
            return False
        if not (0 < amps <= MAX_AMPS):
            return False
    return True


def read_actives(data: bytes) -> list:
    out = []
    for slot, off, seg in _records(data, "atv"):
        name = _name(seg[5:30])
        if not name:
            continue
        parts = [x for x in (_name(seg[30:40]), _name(seg[40:45])) if x]
        nums = [_fx(v) for v in struct.unpack_from("<24i", seg, 59)]
        # +99 onward is a (volts, amps) table, terminated by a zero volts entry
        table = []
        for i in range(8, 24, 2):
            volts, amps = nums[i], nums[i + 1]
            if volts > 0 and amps > 0:
                table.append([round(volts, 1), round(amps, 3)])
        levels = [round(v, 2) for v in nums[0:8]]
        if not _plausible_active(name, levels, table):
            continue
        ids = [_name(seg[o + 5:o + 10]) for o in range(
            ATV_CONFIG_BASE, ATV_CONFIG_BASE + ATV_CONFIG_STRIDE * ATV_CONFIG_SLOTS,
            ATV_CONFIG_STRIDE)]
        out.append(ActiveSpec(
            slot=slot,
            name=name,
            index=slot - ATV_INDEX_BASE,
            active_id=ids[0],
            config_ids=[i for i in ids if i],
            housing=_name(seg[18:20]),
            option_parts=parts,
            input_levels=levels[0:4],
            output_levels=levels[4:8],
            power_draw=table,
            values=nums,
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


def read_taps(data: bytes) -> list:
    out = []
    for slot, off, seg in _records(data, "tap"):
        ports = {}
        for count, o in TAP_PORT_SLOTS.items():
            part = _name(seg[o:o + 20])
            if not part:
                continue
            ports[count] = TapPort(
                ports=count,
                part=part,
                tap_value=_loss4(seg, o + TAP_VALUE_BLOCK),
                insertion=_loss4(seg, o + TAP_INSERTION_BLOCK),
            )
        if not ports:
            continue
        tap_id = round(_fx(struct.unpack_from("<i", seg, TAP_ID_OFFSET)[0]))
        out.append(TapSpec(slot=slot, tap_id=tap_id, ports=ports,
                           parts={str(k): v.part for k, v in ports.items()}))
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


def read_frequencies(data: bytes) -> dict:
    """Column labels of the design frequencies, e.g. {"F1": "750", "R1": "40"}.

    Only enabled columns are returned.  The labels are what the screen heads
    its level columns with; the manual is clear they are labels, and that the
    spec files hold a loss per column rather than per MHz."""
    out = {}
    for k, key in enumerate(PAR_FREQUENCY_NAMES):
        o = PAR_FREQUENCIES + PAR_FREQUENCY_STRIDE * k
        if o + 6 > len(data):
            break
        if data[o + 5]:
            out[key] = _name(data[o:o + 5])
    return out


# In-line devices (the Actives file's "Inline Eqs"): Q1, Q2 ... placed in a
# node's amp column.  69-byte records from a fixed offset (the .atv is a
# fixed-size file); name, then losses at the four design columns
# [F1, F2, R1, R2].  WV750: Q2 LEQ-PEA-0 = 1.2 / 1.0 / 1.2 / 0.7, exactly what
# it costs on AL004's Design screen at 6.8.
ATV_INLINE, ATV_INLINE_STRIDE, ATV_INLINE_SLOTS = 169372, 69, 40
ATV_INLINE_LOSS = 29


@dataclass
class InlineSpec:
    number: int          # the n of Qn
    name: str
    losses: list         # dB at F1, F2, R1, R2


def read_inline(data: bytes) -> list:
    out = []
    for k in range(1, ATV_INLINE_SLOTS):
        o = ATV_INLINE + ATV_INLINE_STRIDE * k
        if o + ATV_INLINE_LOSS + 16 > len(data):
            break
        name = _name(data[o:o + 20])
        losses = [round(_fx(v), 3) for v in struct.unpack_from("<4i", data, o + ATV_INLINE_LOSS)]
        if name and all(abs(v) < 60 for v in losses):
            out.append(InlineSpec(number=k, name=name, losses=losses))
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
        o = PAR_LEVELS + PAR_LEVEL_STRIDE * k
        if o + 16 > len(data):
            break
        levels.append([round(_fx(v), 2) for v in struct.unpack_from("<4i", data, o)])
    margin = _fx(struct.unpack_from("<i", data, PAR_TAP_MARGIN)[0]) \
        if PAR_TAP_MARGIN + 4 <= len(data) else 0.0
    return {"levels": levels, "tap_margin": round(margin, 2)}


def read_supplies(data: bytes) -> list:
    """Power supply types 1-25: name, voltage rating, current rating and
    % capacity -- the Powering tab's table."""
    out = []
    for k in range(PAR_SUPPLY_SLOTS):
        o = PAR_SUPPLY_TABLE + PAR_SUPPLY_STRIDE * k
        if o + 12 > len(data):
            break
        volts, amps, rating = (_fx(v) for v in struct.unpack_from("<3i", data, o))
        if volts <= 0:
            continue
        n = PAR_SUPPLY_NAMES + PAR_SUPPLY_NAME_STRIDE * k
        out.append(SupplySpec(type_id=k + 1, name=_name(data[n:n + 23]),
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
    if len(data) < PAR_TILTS + PAR_TILT_STRIDE * 16:
        return {}
    fx = lambda o: round(_fx(struct.unpack_from("<i", data, o)[0]), 3)
    mask = data[PAR_STRAND_SERIES] & 0x3F
    strand = [n for n in range(6) if mask >> n & 1] + \
        [6 + k for k in range(4) if data[PAR_STRAND_600 + k]]
    label = [_name(data[PAR_FREQUENCIES + PAR_FREQUENCY_STRIDE * k:
                        PAR_FREQUENCIES + PAR_FREQUENCY_STRIDE * k + 5]) for k in range(10)]
    fwd, ret = label[:6], label[6:]
    eq_sel = struct.unpack_from("<4H", data, PAR_EQ_SELECTION)
    windows = {}
    for k, key in enumerate(PAR_FREQUENCY_NAMES):
        windows[key] = fx(PAR_FREQUENCIES + PAR_FREQUENCY_STRIDE * k + 6)
    housings = []
    for k in range(PAR_HOUSINGS):
        name = _name(data[PAR_HOUSING_PARTS + 25 * k:PAR_HOUSING_PARTS + 25 * k + 25])
        if name:
            housings.append({"number": k + 1, "part": name,
                             "min_points": data[PAR_HOUSING_SIZE + k]})
    return {
        "strand_series": strand,
        "distance_units": {0: "Ftg", 1: "m", 2: "dM"}.get(int(fx(PAR_DISTANCE_UNITS)), fx(PAR_DISTANCE_UNITS)),
        "signal_display": {0: "dBmV", 1: "dBuV"}.get(int(fx(PAR_SIGNAL_DISPLAY)), fx(PAR_SIGNAL_DISPLAY)),
        "show_count_types": bool(data[PAR_SHOW_COUNT_TYPES]),
        "eq_placement": {0: "EQ-", 1: "EQ+", 2: "EQe"}.get(int(fx(PAR_EQ_PLACEMENT)), fx(PAR_EQ_PLACEMENT)),
        "optimization": {0: "OP-", 1: "OFf", 2: "OP+"}.get(int(fx(PAR_OPTIMIZATION)), fx(PAR_OPTIMIZATION)),
        "enforce_tap_window": bool(data[PAR_ENFORCE_TAP_WINDOW]),
        "enforce_tap_tilt": bool(data[PAR_ENFORCE_TAP_TILT]),
        "pre_load": len(data) > PAR_PRE_LOAD and bool(data[PAR_PRE_LOAD]),
        "eq_selection": {"fwd_high": fwd[eq_sel[0] % 6], "fwd_low": fwd[eq_sel[1] % 6],
                         "ret_high": ret[eq_sel[2] % 4], "ret_low": ret[eq_sel[3] % 4]},
        "transformers": [t for t in (
            {"id": k + 1,
             "part": _name(data[PAR_TRANSFORMERS + PAR_TRANSFORMER_STRIDE * k + (k == 0):
                                PAR_TRANSFORMERS + PAR_TRANSFORMER_STRIDE * k + PAR_TRANSFORMER_VOLTS]),
             "volts": fx(PAR_TRANSFORMERS + PAR_TRANSFORMER_STRIDE * k + PAR_TRANSFORMER_VOLTS)}
            for k in range(8)) if t["part"] or t["volts"]],
        "flag_hi_lo_tilt": bool(data[PAR_FLAG_TILT]),
        "power_interpolation": INTERPOLATION.get(data[PAR_INTERPOLATION], "constant_wattage"),
        "max_amps_through": {k: fx(PAR_MAX_AMPS + 4 * i) for i, k in enumerate(MAX_AMPS_THROUGH)},
        "tap_type_by_ports": {n: (2, 4, 6, 8)[data[PAR_TAP_TYPE_BY_PORTS + n] & 3]
                              for n in range(1, 33)},
        "ports_by_homes": {n: data[PAR_PORTS_BY_HOMES + n] for n in range(1, 33)},
        "misc_parts": {k: _name(data[PAR_MISC_PARTS + 25 * i:PAR_MISC_PARTS + 25 * i + 25])
                       for i, k in enumerate(("hth_connectors", "splices", "terminators"))},
        "housings": housings,
        "points": {k: data[o] for k, o in PAR_POINTS.items()},
        "niu": {k: fx(PAR_NIU + 4 * i) for i, k in enumerate(NIU_FIELDS)},
        "max_crossover": fx(PAR_CROSSOVER),
        "max_return_crossover": fx(PAR_RETURN_CROSSOVER),
        "max_le_cascade": int(fx(PAR_MAX_LE_CASCADE)),
        "max_tap_cascade": data[PAR_MAX_TAP_CASCADE],
        "lines_per_form": int(fx(PAR_LINES_PER_FORM)),
        "replacement_cables": {"backfeed": int(fx(PAR_BACKFEED_CABLE)),
                               "fwd_feed": int(fx(PAR_FWDFEED_CABLE))},
        "allow_over_equalization": bool(data[PAR_OVER_EQUALIZATION]),
        "overvoltage_check": bool(data[PAR_OVERVOLTAGE]),
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
    return spec
