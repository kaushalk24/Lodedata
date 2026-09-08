"""Command line front end:  python -m lodedata <command> ..."""
import argparse
import json
import sys
from pathlib import Path

from .header import read_header
from .obfuscation import deobfuscate, recover_key, NTW_KEY, PAYLOAD_START
from .specs import load_spec_set


def cmd_info(args):
    for p in args.files:
        data = Path(p).read_bytes()
        h = read_header(data)
        print(f"{p}")
        print(f"  magic       : {h.magic}  ({h.description})")
        print(f"  format ver  : {h.format_version}")
        if h.app_version:
            print(f"  written by  : {h.app_version}")
        print(f"  licence id  : {h.license_id}")
        print(f"  user id     : {h.user_id}")
        print(f"  size        : {len(data)} bytes ({len(data)-512} of payload)")
        if h.kind == "ntw":
            key = recover_key(data[PAYLOAD_START:])
            print(f"  keystream   : {'matches the known key' if key == NTW_KEY else 'DIFFERENT: ' + key.hex()}")


def cmd_decode(args):
    data = Path(args.file).read_bytes()
    out = data[:PAYLOAD_START] + deobfuscate(data[PAYLOAD_START:])
    Path(args.out).write_bytes(out)
    nz = sum(1 for b in out[PAYLOAD_START:] if b)
    print(f"wrote {args.out}: {len(out)} bytes, "
          f"{nz} non-zero payload bytes ({100*nz/(len(out)-PAYLOAD_START):.1f}% used)")


def cmd_spec(args):
    spec = load_spec_set(args.base)
    if args.json:
        print(json.dumps(spec.to_dict(), indent=2))
        return
    print(f"spec set: {spec.name}")
    for ext, h in spec.headers.items():
        print(f"  .{ext}: {h.description}, licence {h.license_id}, user {h.user_id}")
    print(f"  cables   : {len(spec.cables)}")
    for c in spec.cables:
        print(f"     {c.name:<18} loop {c.loop_resistance_ohm_per_ft*1000:6.2f} ohm/1000ft"
              f"  coeffs {c.forward_coeffs[:3]}  {c.footage_part}/{c.connector_part}")
    print(f"  couplers : {len(spec.couplers)}")
    for c in spec.couplers[:40]:
        print(f"     {c.name:<18} code {c.code:8.2f}")
    print(f"  actives  : {len(spec.actives)}")
    for a in spec.actives:
        print(f"     {a.name:<18} {' '.join(a.option_parts)}")
    print(f"  taps     : {len(spec.taps)}")
    for t in spec.taps:
        print(f"     {t.parts}")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="lodedata")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("info", help="show the header of any Lode Data file")
    p.add_argument("files", nargs="+")
    p.set_defaults(func=cmd_info)

    p = sub.add_parser("decode", help="write a deobfuscated copy of a .ntw file")
    p.add_argument("file")
    p.add_argument("out")
    p.set_defaults(func=cmd_decode)

    p = sub.add_parser("spec", help="parse a spec set given its base path (no extension)")
    p.add_argument("base")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_spec)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
