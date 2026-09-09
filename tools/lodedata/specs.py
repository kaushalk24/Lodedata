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

# tap part-number slots, keyed by the port count they belong to
TAP_NAME_SLOTS = {8: 16, 2: 134, 4: 246, "aux1": 588, "aux2": 700}


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
        out.append(ActiveSpec(
            slot=slot,
            name=name,
            housing=_name(seg[18:20]),
            option_parts=parts,
            input_levels=[round(v, 2) for v in nums[0:4]],
            output_levels=[round(v, 2) for v in nums[4:8]],
            power_draw=table,
            values=nums,
        ))
    return out


# --------------------------------------------------------------------------
# taps
# --------------------------------------------------------------------------
@dataclass
class TapSpec:
    slot: int
    parts: dict              # port count / slot label -> part number
    values: list


def read_taps(data: bytes) -> list:
    out = []
    for slot, off, seg in _records(data, "tap"):
        parts = {}
        for key, o in TAP_NAME_SLOTS.items():
            p = _name(seg[o:o + 16])
            if p:
                parts[str(key)] = p
        if not parts:
            continue
        out.append(TapSpec(
            slot=slot,
            parts=parts,
            values=[_fx(v) for v in struct.unpack_from("<8i", seg, 32)],
        ))
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
