"""A worked example: one node area, designed end to end.

The layout is a small residential node area -- an express feeder out of the
node, a splitter into two feeder legs, a line extender where the first leg
runs out of signal, and a power supply feeding the whole area.  It is small
enough to read on one screen and rich enough to exercise every engine.
"""

from __future__ import annotations

import os

from .library import generic750
from .network import Network, PowerSupply
from .workspace import Workspace

FT = 1.0  # coordinates are in feet, so the canvas is a scale drawing


def build_example_network() -> Network:
    net = Network(
        name="example",
        description="Maple Grove node area -- 1 node, 2 feeder legs, 1 line extender",
        spec_set="generic750",
    )

    node = net.add_location(
        kind="source", label="ND1", device="ND-750", x=0, y=0,
        note="Maple Grove node -- fed from Hub 3, fibre pair 12/13",
    )
    node.power_supply = PowerSupply(
        id="PS1", volts=90.0, max_amps=15.0,
        description="90 V standby supply, pedestal at Maple & 1st",
    )

    # -- express feeder out of the node ------------------------------
    pi = net.add_location(kind="coupler", label="PI1", device="PI",
                          x=350, y=0, note="power inserter")
    net.add_span(node.id, pi.id, cable="P3-750", length=350, port="OUT1")

    split = net.add_location(kind="coupler", label="SP1", device="SP2",
                             x=900, y=0)
    net.add_span(pi.id, split.id, cable="P3-750", length=550, port="THRU")

    # -- leg A: Maple Street, running east ---------------------------
    leg_a = [
        (260, 3), (240, 4), (280, 2), (300, 6), (260, 4),
        (240, 2), (300, 4), (280, 3),
    ]
    cursor, port = split.id, "THRU"
    x = 900
    for index, (length, homes) in enumerate(leg_a, start=1):
        x += length
        loc = net.add_location(kind="tap", label=f"A{index}", device="T4-17",
                               units=homes, x=x, y=0)
        net.add_span(cursor, loc.id, cable="P3-500", length=length, port=port)
        cursor, port = loc.id, "THRU"

    # the leg runs out of signal here, so a line extender goes in
    x += 300
    le = net.add_location(kind="active", label="LE1", device="LE-750", x=x, y=0,
                          note="line extender -- end of the first cascade")
    net.add_span(cursor, le.id, cable="P3-500", length=300, port=port)

    cursor, port = le.id, "OUT"
    for index, (length, homes) in enumerate(
            [(240, 4), (260, 3), (280, 4), (240, 2), (300, 3)], start=9):
        x += length
        loc = net.add_location(kind="tap", label=f"A{index}", device="T4-17",
                               units=homes, x=x, y=0)
        net.add_span(cursor, loc.id, cable="P3-500", length=length, port=port)
        cursor, port = loc.id, "THRU"

    # -- leg B: First Avenue, running north --------------------------
    cursor, port = split.id, "TAP1"
    y = 0
    for index, (length, homes) in enumerate(
            [(280, 4), (260, 8), (300, 4), (240, 2), (260, 4), (280, 3)],
            start=1):
        y -= length
        loc = net.add_location(kind="tap", label=f"B{index}", device="T4-17",
                               units=homes, x=900, y=y)
        net.add_span(cursor, loc.id, cable="P3-500", length=length, port=port)
        cursor, port = loc.id, "THRU"
    net.locations[cursor].note = "end of First Avenue -- future extension north"

    return net


def build_example_workspace(workspace: Workspace) -> list[str]:
    """Populate *workspace* with the generic spec set and the example design."""
    workspace.ensure()
    created = []

    spec_dir = os.path.join(workspace.spec_root, "generic")
    specs = generic750()
    specs.save_dir(spec_dir)
    created.append(f"specs/generic/       {len(specs.taps)} taps, "
                   f"{len(specs.actives)} actives, {len(specs.cables)} cables")

    net = build_example_network()
    from .engine.autodesign import AutoDesigner
    AutoDesigner(specs, net).full_design()
    path = workspace.save_network(net, "example")
    created.append(f"networks/example.dsn  {net.stats()['locations']} locations, "
                   f"{net.stats()['units']} units")

    settings = workspace.settings()
    settings.name = os.path.basename(workspace.root) or "lode"
    settings.notes = "created by 'lode init'"
    settings.save(os.path.join(workspace.root, "project.dap"))
    created.append("project.dap")

    from .specs import Xspec, XspecEntry
    xspec = Xspec(entries=[XspecEntry(line=0, name="generic750",
                                      directory="specs/generic")])
    xspec.save(os.path.join(workspace.root, "quick.xsp"))
    created.append("quick.xsp            Xspec quick-load list")
    return created
