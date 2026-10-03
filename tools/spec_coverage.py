"""How much of each spec file the readers understand, byte by byte.

    python tools/spec_coverage.py [spec base ...]

With no arguments every spec set under samples/ (or LODEDATA_SAMPLES) is
checked.  For each of the five files it maps every byte the readers in
lodedata.specs take a meaning from, then lists the bytes no reader explains
that hold something other than zero: inside a record table by the offset in
the record (and how many records use it), elsewhere by file offset.  A file
whose version or size has not been seen is said so first: its layout is a
guess until it is checked against Lode.
"""
import os
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from lodedata import specs as S                                      # noqa: E402

SAMPLES = Path(os.environ.get("LODEDATA_SAMPLES", ROOT / "samples"))

# (format version, file size) of every spec file checked against Lode so far
SEEN = {
    "cbl": {((5, 1), 38912), ((11, 1), 39912), ((12, 1), 39912)},
    "cpr": {((5, 1), 111823), ((11, 1), 121813), ((12, 1), 121813)},
    "atv": {((6, 0), 104922), ((11, 1), 262136), ((12, 1), 273200)},
    "tap": {((3, 0), 26723), ((11, 1), 233089)},
    "par": {((2, 10), 3102), ((11, 1), 6515), ((12, 1), 6516)},
}
# Other versions met in the user's regions' spec sets (2 Oct, 168 sets): the
# same layout as one above -- every value reads sensibly and the same share of
# each file is explained -- but not yet checked against Lode's screens.  The
# Parameters files of 3095-5190 bytes are the 3102-byte layout with fields
# added at the end; taps 10.0 are the older rows, 256 of them.
SAME_LAYOUT = {
    "cbl": {((10, 0), 38912)},
    "cpr": {((10, 0), 111823), ((10, 6), 111823)},
    "atv": {((10, 0), 104922), ((12, 2), 273200)},
    "tap": {((2, 10), 26723), ((10, 0), 106625), ((12, 1), 233089)},
    "par": {((2, 10), 3095), ((5, 1), 3106), ((7, 0), 5186), ((10, 0), 5190), ((10, 2), 5190)},
}
# Older still, and not readable yet: the actives 2.20, 3.0 and 5.0, cables and
# couplers 2.10, Parameters 2.10 of 2162 bytes (the regions' "old spec" sets)


def _table(start, stride, count, fields):
    """A record table: fields are (offset in record, length, label)."""
    return {"start": start, "stride": stride, "count": count, "fields": fields}


def layout(kind: str, data: bytes) -> tuple:
    """(record tables, other mapped ranges) for one file, from the readers'
    own constants."""
    classic = S._classic(data)
    n = S.CLASSIC_NAME if classic else 25
    other = [(0, 512, "header")]
    tables = []
    if kind == "cbl":
        start, stride, _ = (S.CLASSIC_LAYOUT if classic else S.LAYOUT)["cbl"]
        f = [(0, 1, "mark"), (1, 2, "cable ID"), (5, n, "name"), (5 + n, 4, "loop resistance"),
             (9 + n, 40, "loss block"), (49 + n, 40, "second loss block"),
             (89 + n, 15, "footage part"), (104 + n, 15, "connector part"), (119 + n, 20, "flags")]
        f += [(139 + n + 23 * k, 23, f"series {k}") for k in range(10)]
        tables.append(_table(start, stride, 100, f))
    elif kind == "cpr":
        start, stride, _ = (S.CLASSIC_LAYOUT if classic else S.LAYOUT)["cpr"]
        count = (len(data) - start) // stride
        f = [(0, 1, "mark"), (1, 4, "code"), (5, n, "name"), (5 + n, 40, "tap leg block"),
             (45 + n, 40, "thru leg block"), (85 + n, 1, "tap legs - 1"), (88 + n, 1, "internal")]
        tables.append(_table(start, stride, count, f))
    elif kind == "atv":
        if classic:
            start, stride, count, levels, config = 1021, 318, S.CLASSIC_ATV_RECORDS, 39, 170
            f = [(1, 4, "banks"), (5, 15, "name"), (20, 15, "Ret. Mod. Part Number"),
                 (35, 4, "custom cascading"), (levels, 32, "in/out levels")]
            banks, nbanks = S.CLASSIC_BANKS, S.CLASSIC_BANK_COUNT
            inline, istride, islots, iat = S.CLASSIC_INLINE
        else:
            start, stride, count, levels, config = 849 + 362 * S.ATV_INDEX_BASE, 362, 251, 59, 214
            f = [(1, 4, "banks"), (5, 25, "name"), (30, 25, "Ret. Mod. Part Number"),
                 (55, 4, "custom cascading"), (levels, 32, "in/out levels"),
                 (S.ATV_RESERVE_GAIN[0], 8, "reserve gain")]
            banks, nbanks = S.ATV_BANKS, S.ATV_BANK_COUNT
            inline, istride, islots, iat = (S.ATV_INLINE, S.ATV_INLINE_STRIDE,
                                            S.ATV_INLINE_SLOTS, S.ATV_INLINE_LOSS)
        (steps_at, steps), f3 = (S.CLASSIC_ATV_STEPS, S.CLASSIC_ATV_F3) if classic else (S.ATV_STEPS, S.ATV_F3)
        f += [(steps_at, 8 * steps, "power steps"), (f3[0], 16, "in F3-F6"), (f3[1], 16, "out F3-F6")]
        f += [(config + S.ATV_CONFIG_STRIDE * k + 5, 5, f"config ID {k}")
              for k in range(S.ATV_CONFIG_SLOTS)]
        tables.append(_table(start, stride, count, f))
        rows = [(o, 5, "label") for o in S.ATV_BANK_LABELS] + [(10, 48, "values")]
        for k in range(nbanks):
            b = banks + S.ATV_BANK_STRIDE * k
            tables.append(_table(b, S.ATV_BANK_ROW, S.ATV_BANK_ROWS, rows))
            other.append((b + S.ATV_BANK_ROW * S.ATV_BANK_ROWS, 44, f"bank {k + 1} prefixes"))
        tables.append(_table(inline, istride, islots, [(0, min(iat, 20), "name"), (iat, 40, "losses")]))
    elif kind == "tap":
        start, stride, _ = (S.CLASSIC_LAYOUT if classic else S.LAYOUT)["tap"]
        slots = S.CLASSIC_TAP_PORT_SLOTS if classic else S.TAP_PORT_SLOTS
        count = (len(data) - start) // stride
        f = [(0, 4, "tap ID")]
        for ports, o in slots.items():
            f += [(o, n, f"{ports}-port part"), (o + n, 40, f"{ports}-port tap value"),
                  (o + n + 40, 40, f"{ports}-port insertion")]
        tables.append(_table(start, stride, count, f))
    elif kind == "par":
        other += _par_fields(data)
    return tables, other


def _par_fields(data: bytes) -> list:
    """The Parameters fields read_parameters and its helpers use."""
    classic = S._classic(data)
    out = []

    def at(o, length, label):
        a = S._par_at(data, o)
        if a is not None:
            out.append((a, length, label))

    at(S.PAR_TAP_TYPE_BY_PORTS, 33, "tap type by ports")
    at(S.PAR_PORTS_BY_HOMES, 33, "ports by homes")
    width = S.CLASSIC_NAME if classic else 25
    misc, parts = (S.CLASSIC_PAR_MISC, S.CLASSIC_PAR_HOUSING_PARTS) if classic else (
        S.PAR_MISC_PARTS, S.PAR_HOUSING_PARTS)
    out.append((misc, width * 3, "misc parts"))
    out.append((parts, width * S.PAR_HOUSINGS, "housing parts"))
    at(S.PAR_STRAND_SERIES, 1, "strand series")
    for k, o in S.PAR_POINTS.items():
        at(o, 1, f"points {k}")
    at(S.PAR_HOUSING_SIZE, S.PAR_HOUSINGS, "housing sizes")
    at(S.PAR_NIU, 20, "NIU")
    for o, label in ((S.PAR_CROSSOVER, "max crossover"), (S.PAR_RETURN_CROSSOVER, "max return crossover"),
                     (S.PAR_MAX_LE_CASCADE, "max LE cascade"), (S.PAR_LINES_PER_FORM, "lines per form"),
                     (S.PAR_TAP_MARGIN, "tap margin"), (S.PAR_SIGNAL_DISPLAY, "signal display"),
                     (S.PAR_DISTANCE_UNITS, "distance units"), (S.PAR_BACKFEED_CABLE, "backfeed cable"),
                     (S.PAR_FWDFEED_CABLE, "fwd feed cable"), (S.PAR_INTERPOLATION, "interpolation"),
                     (S.PAR_OVERVOLTAGE, "overvoltage"), (S.PAR_OPTIMIZATION, "optimization"),
                     (S.PAR_EQ_PLACEMENT, "EQ placement")):
        at(o, 4, label)
    at(S.PAR_LEVELS, S.PAR_LEVEL_STRIDE * S.PAR_LEVEL_COUNT, "system levels")
    at(S.PAR_MAX_AMPS, 24, "max amps through")
    if classic:
        names, table, slots = S.CLASSIC_PAR_SUPPLY_NAMES, S.CLASSIC_PAR_SUPPLY_TABLE, S.CLASSIC_PAR_SUPPLY_SLOTS
        out += [(names, S.CLASSIC_NAME * slots, "supply names"), (table, S.PAR_SUPPLY_STRIDE * slots, "supplies")]
    else:
        out += [(S.PAR_SUPPLY_NAMES, S.PAR_SUPPLY_NAME_STRIDE * S.PAR_SUPPLY_SLOTS, "supply names"),
                (S.PAR_SUPPLY_TABLE, S.PAR_SUPPLY_STRIDE * S.PAR_SUPPLY_SLOTS, "supplies")]
    at(S.PAR_EXTRA_LEVELS, S.PAR_EXTRA_LEVEL_STRIDE * 16, "extra levels")
    at(S.PAR_FREQUENCIES, S.PAR_FREQUENCY_STRIDE * 10, "frequencies")
    at(S.PAR_EQ_SELECTION, 8, "EQ selection")
    for o, label in ((S.PAR_ENFORCE_TAP_WINDOW, "enforce tap window"), (S.PAR_MAX_TAP_CASCADE, "max tap cascade"),
                     (S.PAR_OVER_EQUALIZATION, "over equalization")):
        at(o, 1, label)
    if not classic:
        out += [(S.PAR_STRAND_600, 3, "600-800 series"), (S.PAR_TRANSFORMERS, 260 * 8, "transformers"),
                (S.PAR_ENFORCE_TAP_TILT, 1, "enforce tap tilt"), (S.PAR_FLAG_TILT, 1, "flag tilt"),
                (S.PAR_TILTS, S.PAR_TILT_STRIDE * 16, "tilts"), (S.PAR_SHOW_COUNT_TYPES, 1, "count types"),
                (S.PAR_PRE_LOAD, 1, "pre load")]
    return out


def audit(path: Path) -> dict:
    data = path.read_bytes()
    kind = path.suffix[1:]
    tables, other = layout(kind, data)
    known = bytearray(len(data))
    for a, length, _ in other:
        known[a:a + length] = b"\1" * len(known[a:a + length])
    in_table = bytearray(len(data))
    for t in tables:
        for r in range(t["count"]):
            base = t["start"] + t["stride"] * r
            if base + t["stride"] > len(data):
                break
            in_table[base:base + t["stride"]] = b"\1" * t["stride"]
            for o, length, _ in t["fields"]:
                known[base + o:base + o + length] = b"\1" * length
    # spaces are counted apart: a field holding only spaces is an empty text
    # field, whatever it is for
    used = sum(1 for b in data if b and b != 0x20)
    unexplained = [i for i, b in enumerate(data) if b and not known[i]]
    a_blank = sum(1 for i in unexplained if data[i] == 0x20)
    # inside a table: by offset in the record; elsewhere: runs of file offsets
    by_field = defaultdict(set)
    loose = []
    for i in unexplained:
        for k, t in enumerate(tables):
            if t["start"] <= i < t["start"] + t["stride"] * t["count"]:
                r, o = divmod(i - t["start"], t["stride"])
                by_field[(k, o)].add(r)
                break
        else:
            loose.append(i)
    runs = []
    for i in loose:
        if runs and i - runs[-1][1] <= 16:
            runs[-1][1] = i
        else:
            runs.append([i, i])
    version = (data[26], data[27])
    return {"kind": kind, "size": len(data), "version": version,
            "seen": (version, len(data)) in SEEN.get(kind, set()),
            "same_layout": (version, len(data)) in SAME_LAYOUT.get(kind, set()),
            "used": used, "unexplained": len(unexplained) - a_blank, "tables": tables,
            "by_field": by_field, "runs": runs, "data": data}


def report(base: Path) -> None:
    print(f"== {base.name}")
    for ext in ("cbl", "cpr", "atv", "tap", "par"):
        p = base.with_suffix("." + ext)
        if not p.exists():
            print(f"  .{ext}: missing")
            continue
        a = audit(p)
        share = 100 * (a["used"] - a["unexplained"]) / max(a["used"], 1)
        note = "" if a["seen"] else (
            "  (a layout already read, this version not yet checked against Lode)" if a["same_layout"]
            else "  ** version/size not seen before: layout unchecked **")
        print(f"  .{ext} {a['version'][0]}.{a['version'][1]} {a['size']} bytes: "
              f"{share:.1f}% of {a['used']} bytes in use explained (spaces aside){note}")
        for (k, o), recs in sorted(a["by_field"].items()):
            t = a["tables"][k]
            if o and (k, o - 1) in a["by_field"]:
                continue            # printed with the run it starts
            end = o
            while (k, end + 1) in a["by_field"]:
                end += 1
            recs = set().union(*(a["by_field"][(k, x)] for x in range(o, end + 1)))
            at0 = [t["start"] + t["stride"] * r for r in recs]
            if all(set(a["data"][x + o:x + end + 1]) <= {0, 0x20} for x in at0):
                continue            # empty text fields
            seen = defaultdict(int)
            for r in recs:
                at = t["start"] + t["stride"] * r
                seen[a["data"][at + o:at + end + 1].hex(" ")] += 1
            top = ", ".join(f"{v} x{c}" for v, c in sorted(seen.items(), key=lambda x: -x[1])[:3])
            print(f"    table @{t['start']} +{o}..+{end}: set in {len(recs)} of {t['count']} records"
                  f" ({len(seen)} values: {top})")
        a["runs"] = [r for r in a["runs"] if not set(a["data"][r[0]:r[1] + 1]) <= {0, 0x20}]
        for lo, hi in a["runs"][:12]:
            print(f"    file {lo}..{hi} ({hi - lo + 1} bytes): {a['data'][lo:min(hi + 1, lo + 24)].hex(' ')}")
        if len(a["runs"]) > 12:
            print(f"    ... {len(a['runs']) - 12} more runs to {a['runs'][-1][1]}")


def main(argv) -> None:
    bases = [Path(x) for x in argv] or sorted(
        {p.with_suffix("") for p in SAMPLES.rglob("*.par")
         if "partest" not in p.parts and p.with_suffix(".atv").exists()})
    for b in bases:
        report(b)


if __name__ == "__main__":
    main(sys.argv[1:])
