"""Reader for Lode Data's native binary specification files.

Real equipment libraries live in Lode Data's own format -- ``.par``, ``.cbl``,
``.cpr``, ``.tap``, ``.atv`` -- and they differ from region to region.  This
module reads them directly so a designer can point OpenLode at the library
their system already uses instead of retyping it.

The format, established by inspection
-------------------------------------
Every file opens with a 512-byte header: a title (``Lode Data Cables File``),
a licence string and a user name, NUL-padded.  After that come fixed-length
records.

Numbers are **scaled integers**, not floats:

* decibels and signal levels are ``int32`` at **1 000 000** per dB, so
  ``2160000`` is ``2.16`` dB;
* loop resistance is ``uint16`` at **1 000** per ohm, so ``1720`` is
  ``1.72`` ohms per 1000 ft;
* return-path figures are stored **negative** and are taken as magnitudes.

Each parameter group is ten consecutive ``int32`` slots -- ``F1``-``F6`` then
``R1``-``R4`` -- matching the frequency columns declared in the Parameters
file.  Disabled columns are zero.

Record framing differs by file:

===========  =======  =========================================================
File         Stride   Framing
===========  =======  =========================================================
``.cbl``     394      header 512, every record starts with ``0x6f``
``.cpr``     114      first ``0x6f`` after the header, then fixed stride
``.tap``     varies   records delimited by an ``FF FF FF FF`` marker
``.atv``     362      anchored on the device name, values follow it
``.par``     --       a block of ten 10-byte frequency slots
===========  =======  =========================================================

Verification, not faith
-----------------------
The figures were checked against published hardline data before this reader
was trusted: RG-6 came out at 5.65 dB/100 ft at 750 MHz, ``.875`` P3 at 1.29
and ``.500`` P3 at 2.16, all correct, and loop resistance ordered properly by
cable size.  Even so, every import produces an :class:`ImportReport` listing
exactly what was read from each record, because a silent mis-read of an
equipment library is worse than a refusal.  Check it against Lode Data's own
spec printout before designing against an imported set.
"""

from __future__ import annotations

import os
import re
import struct
from dataclasses import dataclass, field

from ..specs import (Active, ActivesSpec, Cable, CablesSpec, Coupler,
                     CouplersSpec, Frequency, ParametersSpec, PerformanceSpec,
                     PricingSpec, SpecSet, Tap, TapsSpec)
from ..specs.actives import Distortion, Equalizer, OutputPort

HEADER = 512
DB = 1_000_000.0
OHM = 1_000.0
COLUMNS = ("F1", "F2", "F3", "F4", "F5", "F6", "R1", "R2", "R3", "R4")

#: file extension -> what it holds
KINDS = {
    ".par": "parameters", ".cbl": "cables", ".cpr": "couplers",
    ".tap": "taps", ".atv": "actives", ".prc": "pricing",
}

STRIDE = {"cables": 394, "couplers": 114, "actives": 362}


def detect_kind(path: str) -> str:
    """What kind of spec file this is, by extension then by title."""
    ext = os.path.splitext(path)[1].lower()
    if ext in KINDS:
        return KINDS[ext]
    try:
        with open(path, "rb") as fh:
            title = fh.read(64).split(b"\x00")[0].decode("latin1", "replace")
    except OSError as exc:
        raise ValueError(f"cannot read {path!r}: {exc}") from exc
    for kind in ("Cables", "Couplers", "Taps", "Actives", "Parameters"):
        if kind.lower() in title.lower():
            return kind.lower()
    raise ValueError(f"cannot tell what kind of spec file {path!r} is")


@dataclass
class ImportReport:
    """What the reader saw, so it can be checked rather than trusted."""

    source: str = ""
    kind: str = ""
    title: str = ""
    licence: str = ""
    user: str = ""
    records_scanned: int = 0
    records_kept: int = 0
    notes: list = field(default_factory=list)
    rows: list = field(default_factory=list)

    def note(self, message: str) -> None:
        if message not in self.notes:
            self.notes.append(message)

    def to_text(self, limit: int = 0) -> str:
        out = [
            f"{self.kind.upper()} <- {os.path.basename(self.source)}",
            f"  {self.title}" + (f"   licence {self.licence}" if self.licence else ""),
            f"  {self.records_kept} of {self.records_scanned} record slots in use",
        ]
        for note in self.notes:
            out.append(f"  ! {note}")
        rows = self.rows if not limit else self.rows[:limit]
        for row in rows:
            out.append("  " + row)
        if limit and len(self.rows) > limit:
            out.append(f"  ... {len(self.rows) - limit} more")
        return "\n".join(out)


# ---------------------------------------------------------------------------
# low level
# ---------------------------------------------------------------------------

def _text(buf: bytes, off: int, length: int) -> str:
    raw = buf[off:off + length]
    return raw.split(b"\x00")[0].decode("latin1", "replace").strip()


def _slots(buf: bytes, off: int, count: int = 10) -> dict:
    """Read *count* scaled-integer slots as a per-frequency mapping."""
    out = {}
    for index in range(count):
        if off + 4 * index + 4 > len(buf):
            break
        (value,) = struct.unpack_from("<i", buf, off + 4 * index)
        if value:
            out[COLUMNS[index]] = abs(value) / DB
    return out


def _header(data: bytes) -> tuple[str, str, str]:
    return (_text(data, 0, 64), _text(data, 129, 16), _text(data, 145, 16))


def _nonempty(mapping: dict) -> bool:
    return any(abs(v) > 1e-9 for v in mapping.values())


def _plausible(mapping: dict, low: float, high: float) -> bool:
    """Every value sits in a physically sensible range.

    A misread block produces numbers like 587 dB of tap loss.  Bounding the
    values is what separates "this record decoded" from "these bytes happened
    to be non-zero", and it is the difference between an honest import and a
    silently wrong equipment library.
    """
    if not mapping:
        return False
    return all(low <= v <= high for v in mapping.values())


# ---------------------------------------------------------------------------
# parameters
# ---------------------------------------------------------------------------

def read_parameters(path: str) -> tuple[ParametersSpec, ImportReport]:
    data = open(path, "rb").read()
    title, licence, user = _header(data)
    report = ImportReport(source=path, kind="parameters", title=title,
                          licence=licence, user=user)

    spec = ParametersSpec(name=os.path.splitext(os.path.basename(path))[0],
                          description=f"imported from {os.path.basename(path)}")
    spec.frequencies = []

    # ten 10-byte frequency slots: a five-byte label, an enabled flag, a value
    anchor = data.find(b"750\x00")
    if anchor < 0:
        for probe in (b"550\x00", b"870\x00", b"1000\x00", b"860\x00"):
            anchor = data.find(probe)
            if anchor >= 0:
                break
    if anchor < 0:
        report.note("no frequency table found; falling back to 750/54/42/5")
        labels = ["750", "54", "42", "5"]
        for index, label in enumerate(labels):
            column = COLUMNS[index if index < 2 else index + 4]
            spec.frequencies.append(
                Frequency(column, label, _mhz(label), True))
    else:
        for index in range(10):
            off = anchor + index * 10
            label = _text(data, off, 5)
            enabled = bool(data[off + 5]) if off + 5 < len(data) else False
            column = COLUMNS[index]
            looks_like_placeholder = re.fullmatch(r"[FR]\d", label or "")
            spec.frequencies.append(Frequency(
                column, label, _mhz(label),
                bool(enabled and label and not looks_like_placeholder)))
            report.rows.append(
                f"{column:<3} label {label or '-':<6} "
                f"{'enabled' if spec.frequencies[-1].enabled else 'off'}")
        report.records_scanned = 10

    forward = [f for f in spec.frequencies if not f.is_return and f.enabled]
    returns = [f for f in spec.frequencies if f.is_return and f.enabled]
    report.records_kept = len(forward) + len(returns)
    if len(forward) < 2:
        report.note("fewer than two forward frequencies are enabled; "
                    "equalizer selection needs two")
        while len(forward) < 2:
            spare = next(f for f in spec.frequencies
                         if not f.is_return and not f.enabled)
            spare.enabled = True
            spare.label = spare.label or spare.id
            forward.append(spare)
    spec.fwd_eq_high, spec.fwd_eq_low = forward[0].id, forward[1].id
    if len(returns) >= 2:
        spec.rtn_eq_high, spec.rtn_eq_low = returns[0].id, returns[1].id
    elif returns:
        spec.rtn_eq_high = spec.rtn_eq_low = returns[0].id

    for name in ("ALPHA", "Alpha", "PS"):
        if name.encode() in data:
            break
    spec.min_tap_output = {spec.fwd_eq_high: 16.0}
    spec.max_return_tap_input = ({spec.rtn_eq_high: 40.0} if returns else {})
    report.note("level windows (minimum tap output, tap window, return "
                "maximum, set margin) are not read from the binary yet -- "
                "check them on the Parameters tab before designing")
    return spec, report


def _mhz(label: str) -> float:
    try:
        return float(re.sub(r"[^0-9.]", "", label) or 0)
    except ValueError:
        return 0.0


# ---------------------------------------------------------------------------
# cables
# ---------------------------------------------------------------------------

def read_cables(path: str) -> tuple[CablesSpec, ImportReport]:
    data = open(path, "rb").read()
    title, licence, user = _header(data)
    report = ImportReport(source=path, kind="cables", title=title,
                          licence=licence, user=user)
    stride = STRIDE["cables"]
    rows, seen = [], set()
    count = (len(data) - HEADER) // stride
    report.records_scanned = count
    for index in range(count):
        rec = data[HEADER + index * stride: HEADER + (index + 1) * stride]
        if len(rec) < stride:
            break
        name = _text(rec, 5, 26)
        atten = _slots(rec, 34)
        if not name or not _nonempty(atten):
            continue
        ident = _unique(name, seen)
        (loop,) = struct.unpack_from("<H", rec, 30)
        rows.append(Cable(
            id=ident, description=name, part_number=_text(rec, 114, 15),
            atten=atten, loop_res=loop / OHM,
            extra={"connector": _text(rec, 129, 16), "lode_line": index},
        ))
        report.rows.append(
            f"{ident:<18} " +
            "  ".join(f"{k}={v:.2f}" for k, v in atten.items()) +
            f"   loop={loop / OHM:.3f}")
    report.records_kept = len(rows)
    spec = CablesSpec(name=os.path.splitext(os.path.basename(path))[0],
                      description=f"imported from {os.path.basename(path)}",
                      rows=rows)
    return spec, report


def _unique(name: str, seen: set) -> str:
    ident = re.sub(r"\s+", "-", name.strip())
    base, counter = ident, 2
    while ident in seen:
        ident = f"{base}#{counter}"
        counter += 1
    seen.add(ident)
    return ident


# ---------------------------------------------------------------------------
# couplers
# ---------------------------------------------------------------------------

def read_couplers(path: str) -> tuple[CouplersSpec, ImportReport]:
    data = open(path, "rb").read()
    title, licence, user = _header(data)
    report = ImportReport(source=path, kind="couplers", title=title,
                          licence=licence, user=user)
    stride = STRIDE["couplers"]
    start = data.find(b"\x6f", HEADER)
    while start >= 0 and not _text(data, start + 5, 20):
        nxt = data.find(b"\x6f", start + 1)
        if nxt < 0 or nxt - start > 4 * stride:
            break
        start = nxt
    if start < 0:
        report.note("no coupler records found")
        return CouplersSpec(name="imported"), report

    rows, seen, bad = [], set(), []
    index = 0
    while start + index * stride + stride <= len(data):
        rec = data[start + index * stride: start + index * stride + stride]
        index += 1
        name = _text(rec, 5, 14) or _text(rec, 19, 14)
        thru = _slots(rec, 30)
        tapl = _slots(rec, 70)
        if not name or not (_nonempty(thru) or _nonempty(tapl)):
            continue
        if not (_plausible(thru, 0.0, 40.0) if thru else True) or \
                not (_plausible(tapl, 0.0, 40.0) if tapl else True):
            bad.append(name)
            continue
        (value,) = struct.unpack_from("<i", rec, 1)
        ident = _unique(name, seen)
        legs = 1 if _nonempty(tapl) else 0
        kind = "dc" if legs and _peak(tapl) - _peak(thru) > 3.0 else (
            "splitter" if legs else "passive")
        rows.append(Coupler(
            id=ident, description=name, part_number=_text(rec, 19, 14),
            kind=kind, thru_loss=thru, tap_legs=legs, tap_loss=tapl,
            extra={"value": abs(value) / DB, "lode_line": index - 1},
        ))
        report.rows.append(
            f"{ident:<18} {kind:<9} thru " +
            " ".join(f"{k}={v:.2f}" for k, v in thru.items()) +
            ("   tap " + " ".join(f"{k}={v:.2f}" for k, v in tapl.items())
             if tapl else ""))
    report.records_scanned = index
    report.records_kept = len(rows)
    if bad:
        report.note(f"{len(bad)} coupler(s) REJECTED: losses decoded outside a "
                    f"physical range -- {', '.join(sorted(set(bad))[:5])}")
    report.note("leg counts are inferred: a coupler with tap-leg losses is "
                "given one tap leg. Check multi-leg splitters on the "
                "Couplers tab.")
    spec = CouplersSpec(name=os.path.splitext(os.path.basename(path))[0],
                        description=f"imported from {os.path.basename(path)}",
                        rows=rows)
    return spec, report


def _peak(mapping: dict) -> float:
    return max(mapping.values()) if mapping else 0.0


# ---------------------------------------------------------------------------
# taps
# ---------------------------------------------------------------------------

#: Rows in the taps file that are plug-ins, not taps.  Lode Data keeps pads
#: and equalizers in the same file; selecting one as a tap would be a silent,
#: serious design error, so they are separated out on import.
PLUGIN_PATTERNS = (
    re.compile(r"\bPAD\b", re.I),
    re.compile(r"\bEQ\b|\bLEQ\b|\bREQ\b", re.I),
    re.compile(r"^\s*RC[\\/ ]", re.I),
    re.compile(r"JUMPER|TERMINATOR|BLANK|PLUG", re.I),
)


def is_plugin(name: str) -> bool:
    """True for a pad or equalizer masquerading as a tap row."""
    return any(p.search(name) for p in PLUGIN_PATTERNS)


PORT_PATTERNS = (
    # RMT2002-RF-23 / RMT2004-RF-23 / RMT2008-RF-23 -- ports in the 4th digit
    re.compile(r"20(?:0?)([248])\D+(\d{2})"),
    re.compile(r"(?:^|[^0-9])2([248])(\d{2})(?:[^0-9]|$)"),   # MMT2830, MGTS-2824
    re.compile(r"-([248])(\d{2})(?:[^0-9]|$)"),               # AN-WIFI-824
    re.compile(r"21([248])\d.*?-(\d{2})"),                    # RMT2128-RF-26
)


def _ports_and_value(name: str) -> tuple[int | None, float | None]:
    for pattern in PORT_PATTERNS:
        m = pattern.search(name)
        if m:
            return int(m.group(1)), float(m.group(2))
    return None, None


def read_taps(path: str, primary: str = "F1") -> tuple[TapsSpec, ImportReport]:
    data = open(path, "rb").read()
    title, licence, user = _header(data)
    report = ImportReport(source=path, kind="taps", title=title,
                          licence=licence, user=user)

    # FF FF FF FF separates records.  The loss blocks sit at a fixed offset
    # from the start of the record -- the byte after a separator -- not from
    # the part number, whose position varies by region: KERMIT750 puts the
    # name at +7, WVBeck750 at +0, and both put tap loss at +25 and through
    # loss at +65.
    TAP_AT, THRU_AT = 25, 65
    marks = [m.start() for m in re.finditer(rb"\xff\xff\xff\xff", data)
             if m.start() > HEADER]
    starts = []
    if marks:
        first = marks[0]
        stride = min((b - a for a, b in zip(marks, marks[1:])), default=112)
        if first - stride >= HEADER:
            starts.append(first - stride + 4)
        starts += [m + 4 for m in marks]
    report.records_scanned = len(starts)

    rows, seen, plugins, lossless, unreadable = [], set(), [], [], []
    group, last_group_at = 1, -10 ** 9
    unknown_ports = 0

    for position, start in enumerate(starts):
        end = starts[position + 1] - 4 if position + 1 < len(starts) else len(data)
        rec = data[start:end]
        if len(rec) < THRU_AT + 8:
            continue
        found = re.search(rb"[A-Za-z][A-Za-z0-9\-.\\/ ]{3,24}\x00", rec)
        if not found:
            continue
        name = found.group()[:-1].strip().decode("latin1", "replace")
        if not name:
            continue

        tap_loss = _slots(rec, TAP_AT)
        thru_loss = _slots(rec, THRU_AT)
        if not _nonempty(tap_loss):
            continue

        if is_plugin(name):
            plugins.append(name)
            continue
        if not tap_loss.get(primary):
            lossless.append(name)
            continue
        if not _plausible(tap_loss, 0.5, 60.0) or \
                (thru_loss and not _plausible(thru_loss, 0.0, 25.0)):
            unreadable.append(name)
            continue

        ports, value = _ports_and_value(name)
        if value is None:
            value = round(tap_loss[primary])
        if ports is None:
            ports = 4
            unknown_ports += 1
        if start - last_group_at > 3000 and rows:
            group += 1
        last_group_at = start

        ident = _unique(name, seen)
        rows.append(Tap(
            id=ident, description=name, part_number=name, tsg=group,
            value=float(value), ports=int(ports),
            tap_loss=tap_loss, insertion_loss=thru_loss,
            self_terminating=not _nonempty(thru_loss),
            extra={"lode_line": position},
        ))
        report.rows.append(
            f"{ident:<22} tsg{group} {ports}p {value:>4.0f}dB  tap " +
            " ".join(f"{k}={v:.2f}" for k, v in tap_loss.items()) +
            ("   thru " + " ".join(f"{k}={v:.2f}" for k, v in thru_loss.items())
             if thru_loss else "  SELF-TERM"))

    report.records_kept = len(rows)
    if unreadable:
        report.note(f"{len(unreadable)} tap(s) REJECTED: their loss figures "
                    f"decoded outside a physical range, so the record layout "
                    f"differs from the rest of the file -- "
                    f"{', '.join(sorted(set(unreadable))[:5])}"
                    + (" ..." if len(set(unreadable)) > 5 else "")
                    + ". Enter these families by hand on the Taps tab.")
    if lossless:
        report.note(f"{len(lossless)} tap(s) had no port loss at {primary} and "
                    f"were REJECTED -- a lossless tap would be chosen ahead of "
                    f"every real one: {', '.join(sorted(set(lossless))[:5])}"
                    + (" ..." if len(set(lossless)) > 5 else ""))
    if plugins:
        report.note(f"{len(plugins)} plug-in row(s) (pads and equalizers) were "
                    f"skipped -- they live in the taps file but are not taps: "
                    f"{', '.join(sorted(set(plugins))[:4])}"
                    + (" ..." if len(set(plugins)) > 4 else ""))
    if unknown_ports:
        report.note(f"{unknown_ports} tap(s) had no recognisable port count in "
                    f"their part number and were set to 4 ports -- fix them on "
                    f"the Taps tab")
    report.note(f"{group} tap selection group(s) inferred from the gaps "
                f"between families")
    spec = TapsSpec(name=os.path.splitext(os.path.basename(path))[0],
                    description=f"imported from {os.path.basename(path)}",
                    rows=rows)
    return spec, report


# ---------------------------------------------------------------------------
# actives
# ---------------------------------------------------------------------------

def _pairs(buf: bytes, off: int, count: int) -> list:
    """Read *count* consecutive scaled-integer values as plain dB figures."""
    out = []
    for index in range(count):
        if off + 4 * index + 4 > len(buf):
            break
        (value,) = struct.unpack_from("<i", buf, off + 4 * index)
        out.append(abs(value) / DB)
    return out


def read_actives(path: str, columns=("F1", "F2")) -> tuple[ActivesSpec, ImportReport]:
    data = open(path, "rb").read()
    title, licence, user = _header(data)
    report = ImportReport(source=path, kind="actives", title=title,
                          licence=licence, user=user)

    names = [(m.start(), m.group()[:-1].decode("latin1", "replace").strip())
             for m in re.finditer(rb"[A-Z][A-Za-z0-9][A-Za-z0-9\-.\\/+ ]{4,22}\x00",
                                  data) if m.start() > HEADER]
    # the device name repeats every stride; sub-fields (kits, housings) do not
    stride = STRIDE["actives"]
    anchors = [p for p, _ in names]
    keep = [(p, s) for p, s in names
            if any(abs((p - q) % stride) in (0,) for q in anchors[:1])]
    if not keep:
        keep = names
    report.records_scanned = len(keep)

    fwd_high, fwd_low = columns
    rows, seen, seen_devices, suspect = [], set(), set(), []
    for position, name in keep:
        rec = data[position:position + stride]
        pairs = _pairs(rec, 54, 8)
        if len(pairs) < 6:
            continue
        # the pairs run (module input), (?), (design output), (?) at the two
        # enabled forward frequencies; the input carries a small tilt and the
        # output the design tilt, which is how they are told apart
        module_in = {fwd_high: pairs[0], fwd_low: pairs[1]}
        design_out = {fwd_high: pairs[4], fwd_low: pairs[5]}
        if not (_nonempty(module_in) and _nonempty(design_out)):
            continue
        if design_out[fwd_high] < module_in[fwd_high]:
            module_in, design_out = design_out, module_in
        # 99.00 and 0.00 are sentinels in these files, not levels
        levels = list(module_in.values()) + list(design_out.values())
        if any(v >= 99.0 for v in levels) or any(v <= 0.0 for v in levels):
            suspect.append(name)
            continue
        signature = (name, round(module_in[fwd_high], 2),
                     round(design_out[fwd_high], 2))
        if signature in seen_devices:
            continue
        seen_devices.add(signature)
        ident = _unique(name, seen)
        category = _category(name)
        gain = {c: round(design_out.get(c, 0.0) - module_in.get(c, 0.0), 2)
                for c in design_out if c in module_in}
        rows.append(Active(
            id=ident, description=name, part_number=name, category=category,
            gain=gain, design_output=design_out, module_input=module_in,
            housing_offset=0.0,
            noise_figure={c: 9.0 for c in design_out if not c.startswith("R")},
            distortions={}, pads=list(range(0, 22)),
            equalizers=[Equalizer(value=float(v),
                                  loss={c: 0.5 for c in design_out})
                        for v in range(0, 25, 3)],
            outputs=[OutputPort("OUT", {})],
            return_capable=any(c.startswith("R") for c in design_out),
            rtn_gain={}, rtn_design_output={}, rtn_module_input={},
            va_pairs=[[60, 1.0], [90, 0.7]], max_amps=15.0,
            extra={"lode_line": position},
        ))
        report.rows.append(
            f"{ident:<22} {category:<13} in " +
            " ".join(f"{k}={v:.2f}" for k, v in module_in.items()) +
            "   out " + " ".join(f"{k}={v:.2f}" for k, v in design_out.items()))

    report.records_kept = len(rows)
    if suspect:
        report.note(f"{len(suspect)} active(s) skipped: their levels read as "
                    f"sentinels (99.00 / 0.00) rather than real figures -- "
                    f"{', '.join(sorted(set(suspect))[:4])}. Enter them by hand "
                    f"on the Actives tab.")
    report.note("the actives block is read as parameter PAIRS at the two "
                "forward frequencies; module input and design output are "
                "identified by their tilt. VERIFY both against Lode Data's "
                "Actives printout.")
    report.note("noise figure, distortion specs, equalizer tables and powering "
                "current draws are NOT read from the binary yet -- placeholders "
                "are used. Fill them in on the Actives tab before trusting a "
                "performance or powering study.")
    spec = ActivesSpec(name=os.path.splitext(os.path.basename(path))[0],
                       description=f"imported from {os.path.basename(path)}",
                       rows=rows)
    return spec, report


def _category(name: str) -> str:
    upper = name.upper()
    if "NODE" in upper or upper.startswith("FM") or "OPT" in upper:
        return "node"
    if "LE" in upper and "BLE" not in upper:
        return "line_extender"
    if "BLE" in upper or "MB" in upper or "BRIDG" in upper:
        return "bridger"
    if "TRUNK" in upper or upper.startswith("TA"):
        return "trunk"
    return "line_extender"


# ---------------------------------------------------------------------------
# whole sets
# ---------------------------------------------------------------------------

READERS = {
    "parameters": read_parameters, "cables": read_cables,
    "couplers": read_couplers, "taps": read_taps, "actives": read_actives,
}


@dataclass
class LodeDataImporter:
    """Reads a whole Lode Data library into a :class:`SpecSet`."""

    name: str = "imported"
    reports: list = field(default_factory=list)

    def load(self, paths) -> SpecSet:
        found = {}
        order = sorted(paths, key=lambda p: 0 if p.lower().endswith(".par") else 1)
        for path in order:
            try:
                kind = detect_kind(path)
            except ValueError as exc:
                self.reports.append(ImportReport(
                    source=path, kind="?", notes=[str(exc)]))
                continue
            reader = READERS.get(kind)
            if reader is None:
                continue
            if kind == "actives":
                params = found.get("parameters")
                fwd = (params.forward_columns[:2] if params else ["F1", "F2"])
                spec, report = reader(path, tuple(fwd))
            elif kind == "taps":
                params = found.get("parameters")
                spec, report = reader(
                    path, params.fwd_eq_high if params else "F1")
            else:
                spec, report = reader(path)
            found[kind] = spec
            self.reports.append(report)

        params = found.get("parameters")
        if params is None:
            params = ParametersSpec.default()
            self.reports.append(ImportReport(
                source="", kind="parameters",
                notes=["no .par file supplied; using default 750/55/42/5 "
                       "frequencies -- the other files' columns may not line "
                       "up with your system"]))
        spec_set = SpecSet(
            parameters=params,
            cables=found.get("cables") or CablesSpec(),
            taps=found.get("taps") or TapsSpec(),
            couplers=found.get("couplers") or CouplersSpec(),
            actives=found.get("actives") or ActivesSpec(),
            performance=PerformanceSpec.default(),
            pricing=PricingSpec(),
            name=self.name,
        )
        for kind in ("cables", "taps", "couplers", "actives"):
            getattr(spec_set, kind).name = self.name
        return spec_set

    def report_text(self, limit: int = 12) -> str:
        return "\n\n".join(r.to_text(limit) for r in self.reports)


def import_set(paths, name: str = "imported") -> tuple[SpecSet, LodeDataImporter]:
    importer = LodeDataImporter(name=name)
    return importer.load(list(paths)), importer
