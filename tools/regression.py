"""Every network x every spec set, before and after a change.

A change made for one file must not change any file that already reads
right.  Take a snapshot before the change and one after, then compare:

    python tools/regression.py snapshot before.json     # on the old code
    python tools/regression.py snapshot after.json      # on the new code
    python tools/regression.py diff before.json after.json

A snapshot opens every .ntw under samples/ (or LODEDATA_SAMPLES) with no
spec set and with every spec set found there, and records every screen
row, the Test list, the branch list and the bytes a save would write.
The diff names each network x spec set that changed and which fields.
"""
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "app"), str(ROOT / "tools")]
SAMPLES = Path(os.environ.get("LODEDATA_SAMPLES", ROOT / "samples"))


def _inputs():
    ntws = sorted(SAMPLES.rglob("*.ntw"))
    specs = sorted({p.with_suffix("") for p in SAMPLES.rglob("*.par")
                    if all(p.with_suffix(e).exists() for e in (".atv", ".tap", ".cpr", ".cbl"))})
    # the Parameters save chains are one spec set's .par only
    specs = [s for s in specs if "partest" not in s.parts]
    return ntws, [None] + specs


def snapshot(out: str) -> None:
    from hfc.importer import design_from_ntw
    from hfc.exporter import export_ntw
    from hfc import screen

    ntws, specs = _inputs()
    shots = {}
    for n in ntws:
        src = n.read_bytes()
        for sp in specs:
            tag = f"{n.relative_to(SAMPLES)} + {sp.name if sp else 'no spec'}"
            try:
                d, rep = design_from_ntw(src, str(sp) if sp else None)
                scr = screen.build(d)
                data, report = export_ntw(d, src)
                shots[tag] = {"rows": [r.as_dict() for r in scr.rows], "tests": scr.tests,
                              "branches": scr.branches, "saved": hashlib.sha1(data).hexdigest(),
                              "same_as_file": data == src, "unresolved": rep["unresolved"],
                              "not_written": report["not_written"]}
            except Exception as e:          # an error is a result too
                shots[tag] = {"error": repr(e)}
    Path(out).write_text(json.dumps(shots, default=str))
    print(f"{len(shots)} network x spec set snapshots ({len(ntws)} networks, {len(specs) - 1} spec sets)")


def diff(before: str, after: str) -> int:
    a, b = json.loads(Path(before).read_text()), json.loads(Path(after).read_text())
    changed = 0
    for tag in sorted(set(a) | set(b)):
        x, y = a.get(tag), b.get(tag)
        if x is None or y is None:
            print(f"{tag}: only in {'after' if x is None else 'before'}")
            changed += 1
            continue
        if "error" in x or "error" in y:
            if x.get("error") != y.get("error"):
                print(f"{tag}: error {x.get('error')} -> {y.get('error')}")
                changed += 1
            continue
        fields = [k for k in ("tests", "branches", "saved", "same_as_file", "unresolved", "not_written")
                  if x[k] != y[k]]
        if len(x["rows"]) != len(y["rows"]):
            fields.append(f"row count {len(x['rows'])} -> {len(y['rows'])}")
        rows = [(f"{ra['branch']}.{ra['node']}{'e' if ra['end'] else ''}",
                 sorted(k for k in ra if k in rb and ra[k] != rb[k]))
                for ra, rb in zip(x["rows"], y["rows"])]
        rows = [r for r in rows if r[1]]
        if fields or rows:
            changed += 1
            print(f"{tag}: {fields} rows changed {len(rows)} e.g. {rows[:4]}")
    print(f"{changed} of {len(set(a) | set(b))} changed")
    return changed


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "snapshot":
        snapshot(sys.argv[2])
    elif len(sys.argv) == 4 and sys.argv[1] == "diff":
        sys.exit(1 if diff(sys.argv[2], sys.argv[3]) else 0)
    else:
        print(__doc__)
        sys.exit(2)
