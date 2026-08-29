"""Command line front end.

    lode init                     create a starter workspace here
    lode import <files>           read a Lode Data binary library (.par .cbl
                                  .cpr .tap .atv) into a named spec set
    lode import-design <chart.csv>  rebuild a network from an exported
                                  Lode Data design chart
    lode inspect-network <f.ntw>  deobfuscate a Lode Data design file
    lode specs [name]             summarise and validate a spec set
    lode calc <network>           solve and print the design chart
    lode design <network>         run the automatic design tools and save
    lode report <name> <network>  print any report (--csv / --xlsx to export)
    lode power <network>          powering analysis
    lode serve                    start the browser front end
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from .reports import REPORTS, write_workbook
from .specs import SpecError
from .workspace import Workspace


def _workspace(args) -> Workspace:
    return Workspace(args.workspace)


def _load(args, workspace: Workspace):
    specs = workspace.load_specs(args.specs)
    network = workspace.load_network(args.network)
    return specs, network


# ---------------------------------------------------------------------------
def cmd_init(args) -> int:
    from .examples import build_example_workspace

    workspace = _workspace(args)
    created = build_example_workspace(workspace)
    print(f"workspace ready at {workspace.root}")
    for line in created:
        print(f"  {line}")
    print("\nnext:  lode calc example    or    lode serve")
    return 0


def cmd_import(args) -> int:
    """Read a Lode Data binary library into a workspace spec set."""
    from .importers import import_set

    workspace = _workspace(args)
    workspace.ensure()
    paths = []
    for entry in args.paths:
        if os.path.isdir(entry):
            paths.extend(os.path.join(entry, f) for f in sorted(os.listdir(entry)))
        else:
            paths.append(entry)
    paths = [p for p in paths
             if os.path.splitext(p)[1].lower() in
             (".par", ".cbl", ".cpr", ".tap", ".atv", ".prc")]
    if not paths:
        print("lode: no Lode Data spec files (.par .cbl .cpr .tap .atv) found",
              file=sys.stderr)
        return 2

    name = args.name or os.path.splitext(os.path.basename(paths[0]))[0]
    spec_set, importer = import_set(paths, name=name)
    print(importer.report_text(limit=args.rows))

    warnings = spec_set.validate()
    target = os.path.join(workspace.spec_root, name)
    if not args.dry_run:
        spec_set.save_dir(target)
        print(f"\nwrote {target}")
    print(f"\n{len(spec_set.cables)} cables, {len(spec_set.taps)} taps, "
          f"{len(spec_set.couplers)} couplers, {len(spec_set.actives)} actives")
    if warnings:
        print(f"{len(warnings)} cross-file warning(s); first few:")
        for warning in warnings[:8]:
            print(f"  - {warning}")
    print("\nCHECK THE IMPORT REPORT against your Lode Data spec printout "
          "before designing against this set.")
    return 0


def cmd_import_design(args) -> int:
    """Rebuild a network from an exported Lode Data design chart."""
    from .importers import read_design_chart

    workspace = _workspace(args)
    workspace.ensure()
    try:
        specs = workspace.load_specs(args.specs)
    except Exception:
        specs = None
    name = args.name or os.path.splitext(os.path.basename(args.path))[0]
    network, report = read_design_chart(args.path, name=name, specs=specs)
    print(report.to_text())
    if not network.locations:
        print("\nnothing was imported", file=sys.stderr)
        return 2
    print(f"\n{network.stats()}")
    if specs is not None:
        analysis = workspace.analyse(specs, network)
        errors = [f for f in analysis.all_flags if f.severity == "error"]
        print(f"solves with {len(errors)} error(s), "
              f"{len(analysis.all_flags) - len(errors)} warning(s)")
    if not args.dry_run:
        path = workspace.save_network(network, name)
        print(f"\nsaved {path}")
    return 0


def cmd_inspect_network(args) -> int:
    """Deobfuscate a Lode Data .ntw file and report what is in it."""
    from .importers import compare, read_network

    if len(args.paths) > 1:
        print("keystream comparison")
        print(compare(args.paths))
        print()
    for path in args.paths:
        net = read_network(path)
        print(net.summary())
        if args.dump:
            print(net.dump(limit=args.dump))
        print()
    return 0


def cmd_specs(args) -> int:
    workspace = _workspace(args)
    names = workspace.spec_sets()
    if args.specs or names:
        specs = workspace.load_specs(args.specs)
        summary = specs.summary()
        print(f"spec set: {summary['name']}   ({summary['directory']})")
        print(f"  parameters : {specs.parameters.name} -- "
              f"{specs.parameters.description}")
        print(f"  frequencies: forward "
              f"{', '.join(specs.parameters.label(c) for c in summary['forward_columns'])}"
              f"   return "
              f"{', '.join(specs.parameters.label(c) for c in summary['return_columns'])}")
        for kind, count in summary["counts"].items():
            print(f"  {kind:<11}: {count}")
        warnings = specs.validate()
        if warnings:
            print(f"\n{len(warnings)} warning(s):")
            for warning in warnings:
                print(f"  - {warning}")
        else:
            print("\nspec set validates cleanly")
    if names:
        print(f"\navailable spec sets: {', '.join(names)}")
    return 0


def cmd_calc(args) -> int:
    workspace = _workspace(args)
    specs, network = _load(args, workspace)
    analysis = workspace.analyse(specs, network)
    report = workspace.report(specs, network, analysis, args.report)
    print(report.to_text())
    errors = len([f for f in analysis.all_flags if f.severity == "error"])
    return 1 if (errors and args.strict) else 0


def cmd_design(args) -> int:
    workspace = _workspace(args)
    specs, network = _load(args, workspace)
    run = workspace.design(specs, network)
    print(f"automatic design: {len(run.changes)} change(s) in {run.passes} pass(es)")
    for change in run.changes:
        print(f"  {change.label:<8} {change.field}: {change.old} -> {change.new}"
              f"   ({change.reason})")
    for note in run.notes:
        print(f"  note: {note}")
    if not args.dry_run:
        path = workspace.save_network(network, args.network)
        print(f"\nsaved {path}")
    analysis = workspace.analyse(specs, network)
    flags = analysis.all_flags
    errors = [f for f in flags if f.severity == "error"]
    print(f"{len(errors)} error(s), {len(flags) - len(errors)} warning(s)")
    return 1 if (errors and args.strict) else 0


def cmd_report(args) -> int:
    workspace = _workspace(args)
    specs, network = _load(args, workspace)
    analysis = workspace.analyse(specs, network)
    builder = workspace.reports(specs, network, analysis)

    if args.name == "all":
        reports = builder.all_reports()
    else:
        reports = [workspace.report(specs, network, analysis, args.name)]

    if args.xlsx:
        os.makedirs(os.path.dirname(os.path.abspath(args.xlsx)), exist_ok=True)
        write_workbook(args.xlsx, reports)
        print(f"wrote {args.xlsx} ({len(reports)} sheet(s))")
        return 0
    for index, report in enumerate(reports):
        if index:
            print("\n")
        if args.csv:
            print(report.to_csv(), end="")
        elif args.json:
            print(json.dumps(report.to_dict(), indent=2))
        else:
            print(report.to_text())
    return 0


def cmd_power(args) -> int:
    workspace = _workspace(args)
    specs, network = _load(args, workspace)
    analysis = workspace.analyse(specs, network, load_factor=args.load_factor)
    print(workspace.report(specs, network, analysis, "power").to_text())
    print()
    print(workspace.report(specs, network, analysis, "powering-detail").to_text())
    return 0


def cmd_serve(args) -> int:
    from .web.server import serve

    serve(Workspace(args.workspace), host=args.host, port=args.port,
          open_browser=not args.no_browser)
    return 0


# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lode",
        description="OpenLode Design Assistant -- broadband plant design",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("-w", "--workspace", default=".",
                        help="workspace directory (default: current)")
    parser.add_argument("-s", "--specs", default="",
                        help="spec set name (default: the first one found)")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init", help="create a starter workspace")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("import", help="read Lode Data binary spec files")
    p.add_argument("paths", nargs="+",
                   help="spec files or a directory holding them")
    p.add_argument("--name", default="", help="name for the imported set")
    p.add_argument("--rows", type=int, default=12,
                   help="records to show per file in the report (0 = all)")
    p.add_argument("-n", "--dry-run", action="store_true",
                   help="report without writing the spec set")
    p.set_defaults(func=cmd_import)

    p = sub.add_parser("import-design",
                       help="rebuild a network from an exported design chart")
    p.add_argument("path", help="CSV, TSV or text export of a design chart")
    p.add_argument("--name", default="", help="name for the imported network")
    p.add_argument("-n", "--dry-run", action="store_true")
    p.set_defaults(func=cmd_import_design)

    p = sub.add_parser("inspect-network",
                       help="deobfuscate and report on a Lode Data .ntw file")
    p.add_argument("paths", nargs="+")
    p.add_argument("--dump", type=int, default=0, metavar="N",
                   help="hex-dump the N largest data clusters")
    p.set_defaults(func=cmd_inspect_network)

    p = sub.add_parser("specs", help="summarise and validate a spec set")
    p.set_defaults(func=cmd_specs)

    p = sub.add_parser("calc", help="solve a network and print a report")
    p.add_argument("network")
    p.add_argument("-r", "--report", default="design",
                   choices=sorted(REPORTS), help="which report to print")
    p.add_argument("--strict", action="store_true",
                   help="exit non-zero when the design has errors")
    p.set_defaults(func=cmd_calc)

    p = sub.add_parser("design", help="run the automatic design tools")
    p.add_argument("network")
    p.add_argument("-n", "--dry-run", action="store_true",
                   help="show the changes without saving")
    p.add_argument("--strict", action="store_true")
    p.set_defaults(func=cmd_design)

    p = sub.add_parser("report", help="print or export a report")
    p.add_argument("name", choices=sorted(REPORTS) + ["all"])
    p.add_argument("network")
    p.add_argument("--csv", action="store_true")
    p.add_argument("--json", action="store_true")
    p.add_argument("--xlsx", default="", metavar="PATH",
                   help="write an Excel workbook instead of printing")
    p.set_defaults(func=cmd_report)

    p = sub.add_parser("power", help="powering analysis")
    p.add_argument("network")
    p.add_argument("--load-factor", type=float, default=1.0,
                   help="multiply every current draw (peak usage study)")
    p.set_defaults(func=cmd_power)

    p = sub.add_parser("serve", help="start the browser front end")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--no-browser", action="store_true")
    p.set_defaults(func=cmd_serve)

    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (SpecError, FileNotFoundError, KeyError) as exc:
        print(f"lode: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
