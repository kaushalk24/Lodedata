"""Bringing Lode Data files in.

Two operations:

* ``library_from_spec_set``  -- read a .cbl/.cpr/.atv/.tap set into a Library.
* ``inspect_ntw``           -- read what a .ntw design file will currently give
  up.  The obfuscation is solved so the payload is plaintext, but the record
  layout is not mapped yet, so this reports the header and payload statistics
  rather than pretending to import devices.  See docs/open-questions.md.
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

from .model import (Library, CableType, TapType, PassiveType, ActiveType,
                    DesignParameters, new_id)

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


def library_from_spec_set(base: str | Path,
                         params: DesignParameters | None = None) -> Library:
    """Load ``<base>.cbl/.cpr/.atv/.tap`` into a Library.

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
            # cable IDs are 0-99 and the parity is the construction type
            kind="drop" if "RG" in c.name.upper()
                 else ("hardline" if c.index % 2 == 0 else "hardline"),
            loop_resistance_ohm_per_1000ft=loop,
            attenuation=_loss_points(c.forward_coeffs, params),
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
                tap_value_db=round(nominal, 2),
                tap_value=value_pts,
                through_loss=[p for p in loss_pts
                              if p[0] >= params.forward_low_mhz],
                return_through_loss=[p for p in loss_pts
                                     if p[0] <= params.return_high_mhz],
                source=f"lodedata:{base.name}.tap",
            ))

    for p in spec.couplers:
        # a coupler record carries two loss blocks: the thru leg then the tap
        # leg, each in the same ten-value layout the cable file uses
        # the manual is explicit about the order: the Tap leg columns come
        # first, then the Thru leg columns
        tap_leg, thru_leg = p.values[0:10], p.values[10:20]
        losses, names = [], []
        if any(thru_leg):
            losses.append(round(abs(thru_leg[BLOCK_HIGH]), 2)); names.append("thru")
        for _ in range(max(1, p.tap_legs) if any(tap_leg) else 0):
            losses.append(round(abs(tap_leg[BLOCK_HIGH]), 2)); names.append("tap")
        lib.add(PassiveType(
            id=new_id("psv"),
            name=p.name,
            kind=("power_inserter" if "PI" in p.name.upper()
                  else "coupler" if len(set(losses)) > 1 else "splitter"),
            port_losses=losses or [0.0],
            power_passing=[True] * max(1, len(losses)),
            source=f"lodedata:{base.name}.cpr",
        ))

    for a in spec.actives:
        ins = a.input_levels or [0, 0, 0, 0]
        outs = a.output_levels or [0, 0, 0, 0]
        nominal = 60.0
        # an input requirement of 99 is the "no RF input" sentinel, i.e. the
        # device is fibre fed -- a more reliable marker than the part name
        fibre_fed = ins[0] >= 99.0
        lib.add(ActiveType(
            id=new_id("act"),
            name=a.name,
            kind="node" if (fibre_fed or "NODE" in a.name.upper()) else "line_extender",
            in_forward_high=ins[0], in_forward_low=ins[1],
            in_return_high=ins[2], in_return_low=ins[3],
            out_forward_high=outs[0], out_forward_low=outs[1],
            out_return_high=outs[2], out_return_low=outs[3],
            power_draw=a.power_draw,
            current_draw_a=next((amps for v, amps in a.power_draw
                                 if abs(v - nominal) < 6), 0.0),
            source=f"lodedata:{base.name}.atv",
        ))

    return lib


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
        "device_records_imported": 0,
        "note": ("The payload is readable but the record layout is not mapped "
                 "yet: .ntw files hold no text, only indices into the spec "
                 "files, so a known-content sample design is needed to "
                 "identify the tables. See docs/open-questions.md."),
    }


def _tokens(name: str) -> frozenset:
    """`EX .625P3 AER` -> {EX, 625P3, AER}. Punctuation is noise in part numbers."""
    return frozenset(t for t in re.split(r"[^A-Z0-9]+", name.upper()) if t)


FUZZY_THRESHOLD = 0.6


def relink_library(net, new_lib: Library, threshold: float = FUZZY_THRESHOLD) -> dict:
    """Attach a different spec set to an existing design.

    Parts are re-matched by part number, which is how a spec upgrade actually
    behaves: the design keeps its topology and every device that still exists
    in the new library keeps working, now with the new numbers.

    Matching is exact on the normalised part number first, then falls back to
    a token overlap so that `EX .625P3 AER` finds `625P3 AER EXT` across two
    revisions of a spec set.  Every decision is reported so it can be checked.
    """
    old = net.library
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

    for el in net.elements.values():
        if el.cable_id in translate:
            el.cable_id = translate[el.cable_id]
        if el.part_id in translate:
            el.part_id = translate[el.part_id]
    net.library = new_lib
    net.imported_from = new_lib.imported_from
    return report
