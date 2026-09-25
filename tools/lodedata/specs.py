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
# parameters: only the power supply table is mapped so far
# --------------------------------------------------------------------------
@dataclass
class SupplySpec:
    type_id: int          # the number a design stores with each placed supply
    name: str
    volts: float
    amps: float
    rating: float         # third column, 85 or 90 in every sample (efficiency %?)


PAR_SUPPLY_NAMES, PAR_SUPPLY_NAME_STRIDE = 1567, 25
PAR_SUPPLY_TABLE, PAR_SUPPLY_STRIDE = 2212, 20
PAR_SUPPLY_SLOTS = 8


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
    """Power supply types 1-8: name, output volts and rated amps."""
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
    frequencies: dict = field(default_factory=dict)
    levels: list = field(default_factory=list)
    tap_margin: float = 0.0
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
        else:
            setattr(spec, {"cbl": "cables", "cpr": "couplers",
                           "atv": "actives", "tap": "taps"}[ext],
                    READERS[ext](data))
    return spec
