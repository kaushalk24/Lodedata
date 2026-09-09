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
RECORD_MARK = 0x6F           # first byte of a live .cbl / .cpr record


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
    "tap": (512, 908, 16),
}

# Tap records hold one row per tap value, with a sub-block for each port
# count.  Slot offsets confirmed against two independent vendors' spec sets:
# RMT2008-RF-20 sits at +16 and decodes to exactly 20.0 dB, RMT2002-RF-23 at
# +134 to 23.0 dB, and so on.
TAP_PORT_SLOTS = {8: 16, 2: 134, 4: 246, 6: 358}
# within a slot, relative to the part-number field
TAP_VALUE_BLOCK = 25        # losses toward the tap ports
TAP_INSERTION_BLOCK = 65    # hard cable in to hard cable out
TAP_NAME_SLOTS = TAP_PORT_SLOTS      # kept for older callers


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
    for slot, off, seg in _records(data, "cbl"):
        if seg[0] != RECORD_MARK:
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
    for slot, off, seg in _records(data, "cpr"):
        if seg[0] != RECORD_MARK:
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
    housing: str
    option_parts: list
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
        out.append(ActiveSpec(
            slot=slot,
            name=name,
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
    slot: int
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
            part = _name(seg[o:o + 16])
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
        out.append(TapSpec(slot=slot, ports=ports,
                           parts={str(k): v.part for k, v in ports.items()}))
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
        else:
            setattr(spec, {"cbl": "cables", "cpr": "couplers",
                           "atv": "actives", "tap": "taps"}[ext],
                    READERS[ext](data))
    return spec
