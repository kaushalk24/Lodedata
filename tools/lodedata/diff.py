"""Compare two .ntw design files byte by byte, after deobfuscation.

The point of this is differential analysis.  A design file holds no text at
all -- every part is an index into the spec files -- so the only way to learn
which bytes mean what is to change one known thing and see what moves.

    python -m lodedata diff before.ntw after.ntw

What each kind of pair buys you:

* two saves differing by ONE edit (one footage, one tap, one amp) -- pinpoints
  that single field exactly.  This is the cheapest and by far the most useful.
* a before/after rebuild pair -- partitions the file: bytes that stay the same
  are topology (nodes, branches, footages, house counts), bytes that change are
  equipment.  Coarser, but it halves the search space.
* two unrelated designs -- tells you little; almost everything differs.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .header import read_header
from .obfuscation import deobfuscate, PAYLOAD_START

# runs closer than this are reported as one region
GAP = 24


@dataclass
class Region:
    start: int           # offset in the file, header included
    end: int
    before: bytes
    after: bytes

    @property
    def length(self) -> int:
        return self.end - self.start + 1

    def describe(self) -> str:
        def show(b: bytes) -> str:
            return b[:16].hex(" ") + ("…" if len(b) > 16 else "")
        return (f"+{self.start:<8} {self.length:>4} bytes\n"
                f"    before  {show(self.before)}\n"
                f"    after   {show(self.after)}")


def compare(path_a, path_b) -> dict:
    a, b = Path(path_a).read_bytes(), Path(path_b).read_bytes()
    ha, hb = read_header(a), read_header(b)
    pa = deobfuscate(a[PAYLOAD_START:])
    pb = deobfuscate(b[PAYLOAD_START:])
    n = min(len(pa), len(pb))

    diffs = [i for i in range(n) if pa[i] != pb[i]]
    regions = []
    if diffs:
        start = prev = diffs[0]
        for i in diffs[1:]:
            if i - prev > GAP:
                regions.append(Region(start + PAYLOAD_START, prev + PAYLOAD_START,
                                      pa[start:prev + 1], pb[start:prev + 1]))
                start = i
            prev = i
        regions.append(Region(start + PAYLOAD_START, prev + PAYLOAD_START,
                              pa[start:prev + 1], pb[start:prev + 1]))

    live_a = sum(1 for x in pa if x)
    live_b = sum(1 for x in pb if x)
    return {
        "a": {"file": Path(path_a).name, "size": len(a), "live": live_a,
              "app": ha.app_version, "licence": ha.license_id, "user": ha.user_id},
        "b": {"file": Path(path_b).name, "size": len(b), "live": live_b,
              "app": hb.app_version, "licence": hb.license_id, "user": hb.user_id},
        "payload_compared": n,
        "size_differs_by": len(a) - len(b),
        "bytes_changed": len(diffs),
        "regions": regions,
    }


def report(path_a, path_b, limit: int = 40) -> str:
    r = compare(path_a, path_b)
    out = []
    for key in ("a", "b"):
        s = r[key]
        out.append(f"{key}: {s['file']}  {s['size']} bytes, {s['live']} live"
                   f"  [{s['app'] or '?'} / {s['licence']} / {s['user']}]")
    out.append("")
    pct = 100 * r["bytes_changed"] / max(1, r["payload_compared"])
    out.append(f"{r['bytes_changed']} of {r['payload_compared']} payload bytes differ"
               f" ({pct:.2f}%), in {len(r['regions'])} regions")
    if r["size_differs_by"]:
        out.append(f"the files differ in length by {r['size_differs_by']} bytes,"
                   f" so the table capacity changed too")
    out.append("")
    for region in r["regions"][:limit]:
        out.append(region.describe())
    if len(r["regions"]) > limit:
        out.append(f"… and {len(r['regions']) - limit} more regions")
    return "\n".join(out)
