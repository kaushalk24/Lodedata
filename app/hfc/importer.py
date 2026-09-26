"""Bringing Lode Data files in.

Two operations:

* ``library_from_spec_set``  -- read a .cbl/.cpr/.atv/.tap set into a Library.
* ``inspect_ntw``           -- what a .ntw design file is, and which spec set
  it needs.
* ``design_from_ntw``       -- a .ntw read into a Design, against its spec set.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

_TOOLS = Path(__file__).resolve().parents[2] / "tools"
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

from lodedata.header import read_header                    # noqa: E402
from lodedata.obfuscation import deobfuscate, recover_key, NTW_KEY, PAYLOAD_START  # noqa: E402
from lodedata import specs as ld_specs                     # noqa: E402

from dataclasses import asdict

from lodedata.network import read_network                  # noqa: E402

from .model import (Library, CableType, TapType, PassiveType, ActiveType,
                    PowerSupplyType, InlineType, DesignParameters, new_id)
from .plant import (Design, Branch, Node, TapPlacement, CouplerPlacement,
                    THROUGH_FIRST, THROUGH_SECOND)

# A loss block is ten int32 fixed-point values, laid out the same way in the
# cable and coupler files (docs/lode-data-manual-notes.md):
#   0     loss at the forward HIGH frequency
#   1     loss at the forward LOW frequency
#   2-5   the four optional extra forward frequencies
#   6     loss at the return HIGH frequency (Rh, default 42 MHz)
#   7     loss at the return LOW frequency  (Rl, default 5 MHz)
#   8-9   the two optional extra return frequencies
# The frequencies themselves live in the Parameters file, which is why import
# takes the design's own parameters rather than assuming a frequency plan.
BLOCK_HIGH, BLOCK_LOW, BLOCK_RH, BLOCK_RL = 0, 1, 6, 7

# Loop resistance 99 means "never power this" -- the convention for fibre and
# anything else not meant to carry power.
NON_POWERING_LOOP_RESISTANCE = 99.0


def _four_points(four: list, params: DesignParameters) -> list:
    """[High, Low, Rh, Rl] -> [(MHz, dB)] against the design's frequency plan."""
    if not four or len(four) < 4:
        return []
    pairs = [
        (params.return_low_mhz, abs(four[3])),
        (params.return_high_mhz, abs(four[2])),
        (params.forward_low_mhz, abs(four[1])),
        (params.forward_high_mhz, abs(four[0])),
    ]
    return [[f, round(v, 4)] for f, v in pairs if v]


def _loss_points(block, params: DesignParameters) -> list:
    """A loss block -> [(MHz, dB per 100 ft)] the engine can interpolate."""
    pairs = [
        (params.return_low_mhz,   abs(block[BLOCK_RL])),
        (params.return_high_mhz,  abs(block[BLOCK_RH])),
        (params.forward_low_mhz,  abs(block[BLOCK_LOW])),
        (params.forward_high_mhz, abs(block[BLOCK_HIGH])),
    ]
    return [[f, round(v, 4)] for f, v in pairs if v]


def _tap_value_from_part(part: str) -> float | None:
    """`MMT2830` -> 30.0.  Tap part numbers end in the tap value."""
    digits = ""
    for ch in reversed(part):
        if ch.isdigit():
            digits = ch + digits
        else:
            break
    if len(digits) >= 2:
        return float(digits[-2:])
    return None


def parameters_from_spec_set(base: str | Path,
                             params: DesignParameters | None = None) -> DesignParameters:
    """The design frequencies named in the Parameters file, over ``params``."""
    params = DesignParameters(**asdict(params)) if params else DesignParameters()
    spec = ld_specs.load_spec_set(Path(base))
    f = spec.frequencies

    def num(key, default):
        try:
            return float(f[key])
        except (KeyError, ValueError):
            return default
    params.forward_high_mhz = num("F1", params.forward_high_mhz)
    params.forward_low_mhz = num("F2", params.forward_low_mhz)
    params.return_high_mhz = num("R1", params.return_high_mhz)
    params.return_low_mhz = num("R2", params.return_low_mhz)
    if spec.levels and any(any(r) for r in spec.levels):
        params.levels = spec.levels
        params.tap_margin_db = spec.tap_margin
    par = spec.parameters
    if par:
        # General Parameters -> Strand/Trench Types: a series left unticked
        # (WV750: 100, 500-900) is not mileage
        params.non_mileage_series = [n for n in range(10) if n not in par["strand_series"]]
        params.power_interpolation = par["power_interpolation"]
        w = par["tap_windows"]
        params.tap_windows = [w["F1"], w["F2"], w["R1"], w["R2"]]
        params.max_crossover_db = par["max_crossover"]
        params.housings = [[h["number"], h["min_points"]] for h in par["housings"]]
        params.equipment_points = dict(par["points"])
    return params


def library_from_spec_set(base: str | Path,
                         params: DesignParameters | None = None) -> Library:
    """Load ``<base>.cbl/.cpr/.atv/.tap/.par`` into a Library.

    ``params`` supplies the four design frequencies the spec file's loss
    columns were entered against; they live in the Parameters file, so pass
    the design's own rather than guessing.
    """
    base = Path(base)
    params = params or DesignParameters()
    spec = ld_specs.load_spec_set(base)
    lib = Library(name=base.name, imported_from=str(base.name))

    for c in spec.cables:
        loop = round(c.loop_resistance_ohm_per_ft * 1000, 3)
        notes = []
        if abs(loop - NON_POWERING_LOOP_RESISTANCE) < 0.01:
            notes.append("loop resistance 99: not to be powered (fibre or similar)")
        if c.connector_part:
            notes.append(f"connector {c.connector_part}")
        lib.add(CableType(
            id=new_id("cbl"),
            name=c.name,
            kind="drop" if "RG" in c.name.upper() else "hardline",
            loop_resistance_ohm_per_1000ft=loop,
            attenuation=_loss_points(c.forward_coeffs, params),
            cable_index=c.index,
            notes="; ".join(
                [f"cable ID {c.index} ({'aerial' if c.index % 2 == 0 else 'underground'})"]
                + notes),
            source=f"lodedata:{base.name}.cbl",
        ))

    for t in spec.taps:
        for ports, port in sorted(t.ports.items()):
            # tap value and insertion loss are both given at the four design
            # frequencies, in the same [High, Low, Rh, Rl] order as cables
            value_pts = _four_points(port.tap_value, params)
            loss_pts = _four_points(port.insertion, params)
            nominal = port.tap_value[0] if port.tap_value else (
                _tap_value_from_part(port.part) or 0.0)
            lib.add(TapType(
                id=new_id("tap"),
                name=port.part,
                ports=ports,
                tap_id=t.tap_id or int(round(nominal)),
                row=t.slot,
                tap_value_db=round(nominal, 2),
                tap_value=value_pts,
                through_loss=[p for p in loss_pts
                              if p[0] >= params.forward_low_mhz],
                return_through_loss=[p for p in loss_pts
                                     if p[0] <= params.return_high_mhz],
                # a zero insertion loss marks a terminating tap: nothing
                # continues past it (the screen shows 0.00 on the next line)
                self_terminating=not any(abs(v) for v in port.insertion),
                source=f"lodedata:{base.name}.tap",
            ))

    for p in spec.couplers:
        # "the Tap leg columns come first, then the Thru leg columns"
        tap_leg, thru_leg = p.values[0:10], p.values[10:20]
        legs = max(1, p.tap_legs)
        thru_pts = _loss_points(thru_leg, params)
        tap_pts = _loss_points(tap_leg, params)
        lib.add(PassiveType(
            id=new_id("psv"),
            name=p.name,
            kind=("power_inserter" if abs(tap_leg[BLOCK_HIGH]) >= 99
                  else "coupler" if abs(tap_leg[BLOCK_HIGH]) != abs(thru_leg[BLOCK_HIGH])
                  else "splitter"),
            coupler_id=int(p.code) if 0 < p.code < 100000 else 0,
            port_losses=[round(abs(thru_leg[BLOCK_HIGH]), 2)]
                        + [round(abs(tap_leg[BLOCK_HIGH]), 2)] * legs,
            power_passing=[True] * (legs + 1),
            leg_losses=[thru_pts] + [tap_pts] * legs,
            record=p.slot + 1,
            internal=p.internal,
            source=f"lodedata:{base.name}.cpr",
        ))

    for a in spec.actives:
        ins = a.input_levels or [0, 0, 0, 0]
        outs = a.output_levels or [0, 0, 0, 0]
        # no forward input requirement -- 99, or zero on both forward columns
        # as the WV750 "Ripple" node has -- marks a fibre-fed device
        fibre_fed = ins[0] >= 99.0 or (ins[0] == 0 and ins[1] == 0)
        lib.add(ActiveType(
            id=new_id("act"),
            name=a.name,
            active_id=a.active_id or str(a.slot),
            index=a.index,
            kind="node" if (fibre_fed or "NODE" in a.name.upper()) else "line_extender",
            fibre_fed=fibre_fed,
            in_forward_high=ins[0], in_forward_low=ins[1],
            in_return_high=ins[2], in_return_low=ins[3],
            out_forward_high=outs[0], out_forward_low=outs[1],
            out_return_high=outs[2], out_return_low=outs[3],
            power_draw=a.power_draw,
            current_draw_a=next((amps for v, amps in a.power_draw
                                 if abs(v - 60.0) < 6), 0.0),
            source=f"lodedata:{base.name}.atv",
        ))

    for q in spec.inline:
        lib.add(InlineType(
            id=new_id("inl"), name=q.name, number=q.number,
            losses=[[params.forward_high_mhz, q.losses[0]], [params.forward_low_mhz, q.losses[1]],
                    [params.return_high_mhz, q.losses[2]], [params.return_low_mhz, q.losses[3]]],
            source=f"lodedata:{base.name}.atv"))

    for sup in spec.supplies:
        lib.add(PowerSupplyType(
            id=new_id("psu"), name=sup.name, volts=sup.volts, amps=sup.amps,
            type_id=sup.type_id, source=f"lodedata:{base.name}.par"))

    return lib


def design_from_ntw(ntw: str | Path | bytes, spec_base: str | Path,
                    name: str | None = None) -> tuple:
    """Read a Lode Data design against the spec set it was saved with.

    A design refers to equipment by its position in the spec files -- tap
    row, coupler record, actives index -- so it only reads right against its
    own spec set.  Returns ``(design, report)``; the report lists anything the
    spec set could not resolve rather than guessing.
    """
    data = Path(ntw).read_bytes() if not isinstance(ntw, (bytes, bytearray)) else bytes(ntw)
    plain = data[:PAYLOAD_START] + deobfuscate(data[PAYLOAD_START:])
    net = read_network(plain)

    params = parameters_from_spec_set(spec_base)
    lib = library_from_spec_set(spec_base, params)
    taps = {(t.row, t.ports): t for t in lib.taps.values()}
    passives = {p.record: p for p in lib.passives.values()}
    actives = {a.index: a for a in lib.actives.values()}
    cables = {c.cable_index: c for c in lib.cables.values()}
    supplies = {s.type_id: s for s in lib.power_supplies.values()}
    inline = {q.number: q for q in lib.inline.values()}

    report = {"network": net.name, "saved_with": net.spec_names[0] if net.spec_names else "",
              "spec_set": Path(spec_base).name, "branches": len(net.branches),
              "nodes": net.node_count, "unresolved": []}
    if report["saved_with"] and report["saved_with"] != report["spec_set"]:
        report["unresolved"].append(
            f"the design was saved with spec set {report['saved_with']}, "
            f"not {report['spec_set']}: parts are looked up by position")

    def miss(what: str):
        if len(report["unresolved"]) < 200:
            report["unresolved"].append(what)

    design = Design(name=name or net.name or "imported", parameters=params,
                    library=lib, imported_from=f"{net.name}.ntw")
    for number, nb in sorted(net.branches.items()):
        pb, pn = nb.parent
        br = Branch(number=number, parent_branch=pb, parent_node=pn)
        for i, nn in enumerate(nb.nodes, start=1):
            node = Node(seq=i, ftg=float(nn.ftg), hc=nn.hc, cab=nn.cable, lv=nn.lv,
                        power_stop=nn.power_stop, amp_label=nn.label, pads=list(nn.pads),
                        fixed=nn.fixed)
            if nn.inline:
                q = inline.get(nn.inline)
                node.inline = nn.inline
                if q:
                    node.inline_part = q.id
                else:
                    miss(f"{number}.{i}: in-line device Q{nn.inline}")
            # cable 0 is a real cable, index 0: on AL004 1.1 (cab 0) shows
            # EX P3 500 A in its info box, as 11.1 (cab 100) does
            cable = cables.get(nn.cable % 100)
            if cable:
                node.cab_part = cable.id
            elif nn.cable:
                miss(f"{number}.{i}: cable {nn.cable}")
            for t in nn.taps:
                tap = taps.get((t.row, t.ports))
                if tap:
                    node.taps.append(TapPlacement(part_id=tap.id, ports=tap.ports,
                                                  value_db=tap.tap_value_db))
                else:
                    miss(f"{number}.{i}: tap row {t.row} ({t.ports}-port)")
            if nn.active_index:
                act = actives.get(nn.active_index)
                if act:
                    node.amp, node.amp_part = act.active_id, act.id
                else:
                    miss(f"{number}.{i}: active index {nn.active_index}")
            if nn.supply:
                node.supply_label = nn.supply
                sup = supplies.get(nn.supply_type)
                if sup:
                    node.supply_part, node.supply_volts = sup.id, sup.volts
                else:
                    miss(f"{number}.{i}: power supply type {nn.supply_type}")
            for child in nn.branches:
                cb = net.branches.get(child)
                part = passives.get(cb.coupler_record) if cb else None
                node.couplers.append(CouplerPlacement(
                    part_id=part.id if part else None,
                    coupler_id=part.coupler_id if part else 0,
                    branch=child))
                if cb and cb.coupler_record and not part:
                    miss(f"{number}.{i}: coupler record {cb.coupler_record}")
            # "-" puts the through leg on the left-hand branch, "=" on the right
            for k, child in enumerate(nn.branches, start=1):
                cb = net.branches.get(child)
                if cb and cb.through:
                    node.through_leg = THROUGH_FIRST if k == 1 else THROUGH_SECOND
            br.nodes.append(node)
        design.branches[number] = br
    return design, report


def inspect_ntw(path: str | Path) -> dict:
    """Header plus payload statistics for a .ntw design file."""
    path = Path(path)
    data = path.read_bytes()
    h = read_header(data)
    payload = data[PAYLOAD_START:]
    plain = deobfuscate(payload)
    nonzero = sum(1 for b in plain if b)
    try:
        key_ok = recover_key(payload) == NTW_KEY
    except ValueError:
        key_ok = False
    return {
        "file": path.name,
        "magic": h.magic,
        "kind": h.kind,
        "format_version": h.format_version,
        "app_version": h.app_version,
        "license_id": h.license_id,
        "user_id": h.user_id,
        "size_bytes": len(data),
        "payload_bytes": len(payload),
        "live_bytes": nonzero,
        "live_percent": round(100 * nonzero / max(1, len(payload)), 2),
        "keystream_matches_known_key": key_ok,
        **_network_summary(data[:PAYLOAD_START] + plain),
    }


def _network_summary(plain: bytes) -> dict:
    try:
        net = read_network(plain)
    except ValueError as e:
        return {"network_error": str(e)}
    return {"network": net.name, "spec_set_needed": net.spec_names[0] if net.spec_names else "",
            "branches": len(net.branches), "nodes": net.node_count}


def _tokens(name: str) -> frozenset:
    """`EX .625P3 AER` -> {EX, 625P3, AER}. Punctuation is noise in part numbers."""
    return frozenset(t for t in re.split(r"[^A-Z0-9]+", name.upper()) if t)


FUZZY_THRESHOLD = 0.6


def relink_library(design, new_lib: Library, threshold: float = FUZZY_THRESHOLD) -> dict:
    """Attach a different spec set to an existing design.

    Parts are re-matched by part number, which is how a spec upgrade actually
    behaves: the design keeps its topology and every device that still exists
    in the new library keeps working, now with the new numbers.

    Matching is exact on the normalised part number first, then falls back to
    a token overlap so that `EX .625P3 AER` finds `625P3 AER EXT` across two
    revisions of a spec set.  Every decision is reported so it can be checked.
    """
    old = design.library
    report = {"library": new_lib.name, "matched": 0,
              "exact": [], "fuzzy": [], "unmatched": []}

    tables = {
        "cables": (old.cables, new_lib.cables),
        "taps": (old.taps, new_lib.taps),
        "passives": (old.passives, new_lib.passives),
        "actives": (old.actives, new_lib.actives),
    }
    translate: dict = {}
    for table, (old_table, new_table) in tables.items():
        by_tokens = {}
        for part in new_table.values():
            by_tokens.setdefault(_tokens(part.name), part.id)
        for old_id, part in old_table.items():
            want = _tokens(part.name)
            hit = by_tokens.get(want)
            if hit:
                translate[old_id] = hit
                report["matched"] += 1
                report["exact"].append(f"{table}: {part.name}")
                continue
            want_digits = {t for t in want if any(c.isdigit() for c in t)}
            best, best_score = None, 0.0
            for tokens, pid in by_tokens.items():
                shared = want & tokens
                if not shared:
                    continue
                # a part number's digit-bearing tokens are what identify it;
                # never match across them (".625P3 AER" must not find ".875P3 AER")
                other_digits = {t for t in tokens if any(c.isdigit() for c in t)}
                if (want_digits or other_digits) and not (shared & want_digits):
                    continue
                if want_digits and other_digits and want_digits != (shared & want_digits):
                    continue
                score = len(shared) / min(len(want), len(tokens))
                if score > best_score:
                    best, best_score = pid, score
            if best and best_score >= threshold:
                translate[old_id] = best
                report["matched"] += 1
                new_name = new_table[best].name
                report["fuzzy"].append(
                    f"{table}: {part.name} -> {new_name} ({best_score:.0%})")
            else:
                report["unmatched"].append(f"{table}: {part.name}")

    for branch in design.branches.values():
        for node in branch.nodes:
            node.cab_part = translate.get(node.cab_part, node.cab_part)
            node.amp_part = translate.get(node.amp_part, node.amp_part)
            for t in node.taps:
                t.part_id = translate.get(t.part_id, t.part_id)
            for c in node.couplers:
                c.part_id = translate.get(c.part_id, c.part_id)
    design.library = new_lib
    design.imported_from = new_lib.imported_from
    return report
