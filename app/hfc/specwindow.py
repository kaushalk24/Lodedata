"""Spec Edit windows: what Lode Data's Actives, Cables and Parameters windows
show for a spec file, tab by tab, read from the file itself.

Every record is listed, named or not, as Lode lists them: the user's
recording of NBERN1GHz's Actives window (2 Oct) shows rows 7-12 (11H ... 33H)
and 14, 16-22 with an Active ID and no Part Number.  The column heads and
their widths are the recording's (Actives) and the WVEXT862 Cables tab's
(set A2, 4c/4d), at the 100 % scale of the latter: the recording is at 125 %.

A tab whose place in the file is not known yet is drawn as Lode draws it
for NBERN1GHz, where it is empty, and says so (``note``).
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

_TOOLS = Path(__file__).resolve().parents[2] / "tools"
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

from lodedata import specs as S        # noqa: E402

# The recording is at 125 %: its widths times this are the 100 % ones
_SCALE = 0.8

FREQ_KEYS = ("F1", "F2", "F3", "F4", "F5", "F6", "R1", "R2", "R3", "R4")

NOT_READ = ("Not read from the file yet: drawn empty, as Lode draws it for "
            "NBERN1GHz.")
PLUG_NOTE = ("Part numbers read from the file; the other columns not yet: drawn "
             "empty, as Lode draws them for NBERN1GHz.")


def freq_labels(par: bytes | None) -> dict:
    """Every frequency's label, on or off ("550" for WV750's unticked Freq.
    3, "F4" for one never named), as the Parameters' Frequencies tab shows
    them; the column heads use them whether the frequency is on or not
    (WVEXT862's cables: 870/100 54/100 550/100 F4/100 ... R4/100)."""
    out = {k: k for k in FREQ_KEYS}
    if par:
        for k, key in enumerate(FREQ_KEYS):
            o = S._par_at(par, S.PAR_FREQUENCIES + S.PAR_FREQUENCY_STRIDE * k)
            if o is not None and o + 5 <= len(par):
                out[key] = S._name(par[o:o + 5]) or key
    return out


def _w(video_px: float) -> int:
    return round(video_px * _SCALE)


def _fw(base_one_char: float, label: str, per_char: float = 13) -> int:
    """A column headed "<text> - <label>": Lode widens it with the label, about
    13 px a character at 125 % ("In - 5" 57, "In - 85" 70, "In - 102" 82,
    "In - 1002" 95 on the recording)."""
    return _w(base_one_char + per_char * (max(len(label), 1) - 1))


def _f2(v: float) -> str:
    return f"{v:.2f}"


def _fx(seg: bytes, o: int) -> float:
    return struct.unpack_from("<i", seg, o)[0] / S.SCALE


def _grid(cols: list, rows: list) -> dict:
    return {"cols": [{"head": h, "w": w} for h, w in cols], "rows": rows}


# --------------------------------------------------------------------------
# the Actives window
# --------------------------------------------------------------------------
def actives_window(atv: bytes, par: bytes | None, name: str) -> dict:
    L = freq_labels(par)
    classic = S._classic(atv)
    tabs = []
    start, stride, count = (1021, 318, S.CLASSIC_ATV_RECORDS) if classic else (
        849 + 362 * S.ATV_INDEX_BASE, 362, S.ATV_RECORDS)
    width = S.CLASSIC_NAME if classic else 25
    levels_at, config_at = (39, 170) if classic else (59, S.ATV_CONFIG_BASE)
    (steps_at, steps), (in_at, out_at) = (S.CLASSIC_ATV_STEPS, S.CLASSIC_ATV_F3) if classic \
        else (S.ATV_STEPS, S.ATV_F3)
    module = (20, 35) if classic else S.ATV_RETURN_MODULE
    recs = []
    for i in range(1, count):
        o = start + stride * i
        seg = atv[o:o + stride]
        if len(seg) < stride:
            break
        recs.append((i, seg))

    def ident(seg, slot=0):
        o = config_at + S.ATV_CONFIG_STRIDE * slot
        return S._name(seg[o + 5:o + 10])

    def part(seg):
        return S._name(seg[5:5 + width])

    # Actives: In/Out at the four, the banks, then In at F3, F4, F5 (what the
    # recording shows before it scrolls)
    cols = [("It...", _w(31)), ("Active ID", _w(93)), ("Part Number", _w(214))]
    cols += [(f"In - {L[k]}", _fw(57, L[k])) for k in ("F1", "F2", "R1", "R2")]
    for k in ("F1", "F2", "R1", "R2"):
        cols += [(f"Out - {L[k]}", _fw(67, L[k])), ("Out/Loss", _w(93))]
    cols += [("Fwd Pad", _w(88)), ("Ret Pad", _w(83)), ("Fwd EQ", _w(80)), ("Ret EQ", _w(74))]
    cols += [(f"In - {L[k]}", _fw(57, L[k])) for k in ("F3", "F4", "F5")]
    rows = []
    for i, seg in recs:
        ins = struct.unpack_from("<4i", seg, levels_at)
        outs = struct.unpack_from("<4i", seg, levels_at + 16)
        row = [str(i), ident(seg), part(seg)] + [_f2(v / S.SCALE) for v in ins]
        for v in outs:
            row += [_f2(v / S.SCALE), "0 Out"]
        row += [str(seg[S.ATV_PAD_BANKS] + 1), str(seg[S.ATV_PAD_BANKS + 1] + 1),
                str(seg[S.ATV_EQ_BANKS] + 1), str(seg[S.ATV_EQ_BANKS + 1] + 1)]
        row += [_f2(_fx(seg, in_at + 4 * k)) for k in range(3)]
        rows.append(row)
    tabs.append({"name": "Actives", "grid": _grid(cols, rows),
                 "note": "Out/Loss: every row of the recording reads 0 Out; where the "
                         "file keeps it is not known yet."})

    # Reserve Gain
    cols = [("It...", _w(36)), ("Active ID", _w(93)), ("Ret. Mod. Part Number", _w(231)),
            ("Fwd Reserve Gain", _w(187)), ("Ret Reserve Gain", _w(180))]
    rows = []
    for i, seg in recs:
        gains = [0.0, 0.0] if classic else [_fx(seg, o) for o in S.ATV_RESERVE_GAIN]
        rows.append([str(i), ident(seg), S._name(seg[module[0]:module[1]])] + [_f2(g) for g in gains])
    tabs.append({"name": "Reserve Gain", "grid": _grid(cols, rows)})

    # Power Steps: eight (the older record has six)
    cols = [("It...", _w(36)), ("Active ID", _w(93)), ("Min. Voltage", _w(125)), ("Amperage 1", _w(120))]
    for k in range(2, 9):
        cols += [(f"Voltage {k}", _w(95)), (f"Amperage {k}", _w(120))]
    rows = []
    for i, seg in recs:
        pairs = list(struct.unpack_from(f"<{2 * steps}i", seg, steps_at)) + [0] * (16 - 2 * steps)
        rows.append([str(i), ident(seg)] + [_f2(v / S.SCALE) for v in pairs])
    tabs.append({"name": "Power Steps", "grid": _grid(cols, rows)})

    # Pads/EQs Bank 1-8
    first, nbanks = (S.CLASSIC_BANKS, S.CLASSIC_BANK_COUNT) if classic else (S.ATV_BANKS, S.ATV_BANK_COUNT)
    for k in range(8):
        base = first + S.ATV_BANK_STRIDE * k
        end = base + S.ATV_BANK_ROW * S.ATV_BANK_ROWS
        have = k < nbanks and end + 44 <= len(atv)
        bank_rows = [atv[base + S.ATV_BANK_ROW * r:base + S.ATV_BANK_ROW * (r + 1)] if have
                     else bytes(S.ATV_BANK_ROW) for r in range(1, S.ATV_BANK_ROWS)]
        prefixes = [S._label(atv[end + 11 * c:end + 11 * c + 11]) if have else "" for c in range(4)]

        def vals(row):
            return [v / S.SCALE for v in struct.unpack_from("<12i", row, 10)]

        def page(title, c, label_at, value_idx, heads):
            cols = [("It...", _w(37)), ("Part Number", _w(189))] + heads
            rows = []
            for r, row in enumerate(bank_rows, start=1):
                v = vals(row)
                rows.append([str(r), S._label(row[label_at:label_at + 5]).strip()]
                            + [_f2(v[j]) for j in value_idx])
            return {"name": title, "prefix": prefixes[c], "grid": _grid(cols, rows)}

        sub = [
            page("Forward Pad", 0, 0, [0], [("dB Loss", _w(71))]),
            page("Return Pad", 1, 5, [7], [("dB Loss", _w(71))]),
            page("Forward EQ", 2, 58, [1, 2, 3, 4, 5, 6],
                 [(f"Loss - {L[f]}", _fw(78, L[f])) for f in ("F1", "F2", "F3", "F4", "F5", "F6")]),
            page("Return EQ", 3, 63, [8, 9, 10, 11],
                 [(f"Loss - {L[f]}", _fw(78, L[f])) for f in ("R1", "R2", "R3", "R4")]),
        ]
        tabs.append({"name": f"Pads/EQs Bank {k + 1}", "sub": sub})

    # EQs Bank 9-16: 128 rows of 88 bytes each from 172024 -- the prefix
    # char[11] ("2&4 PORT" in NBERN1GHz's 9), the part from +11, the ten
    # losses at +48 in the loss block's order, F1-F6 then R1-R4
    loss_cols = [(f"Loss - {L[f]}", _fw(78, L[f])) for f in FREQ_KEYS]
    for m in range(8):
        base = EQ_BANKS + EQ_BANK_ROW * EQ_BANK_ROWS * m
        have = not classic and base + EQ_BANK_ROW * EQ_BANK_ROWS <= len(atv)
        rows, prefix = [], ""
        for r in range(EQ_BANK_ROWS):
            row = atv[base + EQ_BANK_ROW * r:base + EQ_BANK_ROW * (r + 1)] if have else bytes(EQ_BANK_ROW)
            if r == 0:
                prefix = S._label(row[:11])
            rows.append([str(r + 1), S._name(row[11:48])]
                        + [_f2(v / S.SCALE) for v in struct.unpack_from("<10i", row, 48)])
        tabs.append({"name": f"EQs Bank {m + 9}", "prefix": prefix,
                     "grid": _grid([("It...", _w(36)), ("Part Number", _w(189))] + loss_cols, rows)})

    # Plug-Ins and Plug-Ins Powering: 32 records of 155 bytes from 164412,
    # the name char[15] at +140 (WV750: 4 SWAP BR TO LE ... 17 SWAP FMB TO
    # FMT, the plug-ins its Configuration Table's variants name: 68N 8 NEW
    # FMB, 69T 17 SWAP FMB TO FMT, 78S 4 SWAP BR TO LE); record 0 is "no
    # plug-in".  The figures' places are not known (empty in every file)
    plug_names = [S._name(atv[PLUGINS + PLUGIN_STRIDE * j + 140:PLUGINS + PLUGIN_STRIDE * j + 155])
                  if not classic and PLUGINS + PLUGIN_STRIDE * (j + 1) <= len(atv) else ""
                  for j in range(1, PLUGIN_RECORDS)]
    order = ("F1", "F2", "R1", "R2", "F3", "F4", "F5", "F6", "R3", "R4")
    cols = [("It...", _w(36)), ("Plugin Module Part #", _w(186))]
    cols += [(f"Atten. - {L[f]}", _fw(92, L[f], 12)) for f in order] + [("AGC/Step Down", _w(150))]
    rows = [[str(j), n] + ["0.00"] * 10 + ["0 - No"] for j, n in enumerate(plug_names, start=1)]
    tabs.append({"name": "Plug-Ins", "grid": _grid(cols, rows),
                 "note": PLUG_NOTE})
    cols = [("It...", _w(36)), ("Plugin Module Part #", _w(186)), ("Min. Voltage", _w(125)),
            ("Amperage 1", _w(120))]
    for k in range(2, 9):
        cols += [(f"Voltage {k}", _w(95)), (f"Amperage {k}", _w(120))]
    rows = [[str(j), n] + ["0.00"] * 16 for j, n in enumerate(plug_names, start=1)]
    tabs.append({"name": "Plug-Ins Powering", "grid": _grid(cols, rows), "note": PLUG_NOTE})

    # Configuration Table: each active's eight slots, "1/0" ... "250/7"; the
    # slot's ID 5 bytes in, Plugin 1 at +10 (the Plug-Ins record)
    cols = [("It...", _w(36)), ("Act./Cfg.", _w(81)), ("Part Number", _w(188)), ("Active ID", _w(83))]
    for k in range(1, 9):
        cols += [(f"Plugin {k}", _w(80)), ("Quantity", _w(73))]
    rows = []
    n = 0
    for i, seg in recs:
        for slot in range(S.ATV_CONFIG_SLOTS):
            n += 1
            o = config_at + S.ATV_CONFIG_STRIDE * slot
            plugs = list(seg[o + 10:o + 18]) if o + 18 <= len(seg) else [0] * 8
            row = [str(n), f"{i}/{slot}", part(seg), ident(seg, slot)]
            for p in plugs:
                row += [str(p), "0"]
            rows.append(row)
    tabs.append({"name": "Configuration Table", "grid": _grid(cols, rows),
                 "note": "Quantity and Plugin 2-8: not read from the file yet."})

    # Bridgers, Feedermakers: places not known
    cols = [("It...", _w(36)), ("Bridger", _w(62)), (f"In - {L['R1']}", _fw(57, L["R1"])),
            (f"In - {L['R2']}", _fw(57, L["R2"])), (f"Out - {L['F1']}", _fw(67, L["F1"])),
            (f"Out - {L['F2']}", _fw(67, L["F2"])), (f"In - {L['R3']}", _fw(61, L["R3"])),
            (f"In - {L['R4']}", _fw(61, L["R4"]))]
    cols += [(f"Out - {L[f]}", _fw(67, L[f])) for f in ("F3", "F4", "F5", "F6")]
    tabs.append({"name": "Bridgers", "grid": _grid(cols, [[str(b), f"BR{b}"] + ["0.00"] * 10
                                                        for b in (1, 2)]),
                 "note": NOT_READ})
    cols = [("It...", _w(36)), ("Part Number", _w(189)), ("Ports", _w(45))]
    for prt in (1, 2):
        cols += [(f"Prt{prt} - {L[f]}", _fw(71, L[f])) for f in ("F1", "F2", "R1", "R2")]
    for prt in (1, 2):
        cols += [(f"Prt{prt} - {L[f]}", _fw(71, L[f])) for f in ("F3", "F4", "F5", "F6", "R3", "R4")]
    tabs.append({"name": "Feedermakers", "grid": _grid(cols, [[str(r), "", "1"] + ["0.00"] * 20
                                                            for r in range(1, 9)]),
                 "note": NOT_READ})

    # Inline EQs: 24, "EQ" then Q2-Q24, the losses in the order stored
    base, qstride, slots, at = S.CLASSIC_INLINE if classic else (
        S.ATV_INLINE, S.ATV_INLINE_STRIDE, S.ATV_INLINE_SLOTS, S.ATV_INLINE_LOSS)
    cols = [("It...", _w(36)), ("EQ ID", _w(55)), ("Part Number", _w(188))]
    cols += [(f"Loss - {L[f]}", _fw(78, L[f])) for f in order]
    rows = []
    for k in range(1, 25):
        o = base + qstride * k
        q = atv[o:o + qstride] if k < slots and o + qstride <= len(atv) else bytes(at + 40)
        rows.append([str(k), "EQ" if k == 1 else f"Q{k}", S._name(q[:min(at, 20)])]
                    + [_f2(v / S.SCALE) for v in struct.unpack_from("<10i", q, at)])
    tabs.append({"name": "Inline EQs", "grid": _grid(cols, rows)})

    # Custom Cascading: bit 0 Cust. Casc., bit 1 Exclude, bit k + 1 Casc. k
    cols = [("It...", _w(36)), ("Active ID", _w(83)), ("Part Number", _w(189)),
            ("Cust. Casc.", _w(101)), ("Exclude", _w(71))]
    cols += [(f"Casc. {k}", _w(76 if k < 10 else 89)) for k in range(1, 20)]
    rows = []
    for i, seg in recs:
        c = struct.unpack_from("<I", seg, levels_at - 4)[0]
        rows.append([str(i), ident(seg), part(seg), "1 - Yes" if c & 1 else "0 - No",
                     "1 - Exclude" if c & 2 else "0 - Include"]
                    + ["1 - Valid" if c >> (k + 1) & 1 else "0 - Invalid" for k in range(1, 20)])
    tabs.append({"name": "Custom Cascading", "grid": _grid(cols, rows)})

    # Boosters, Booster Powering: B1-B24 (the 12.1 file's last 24 x 461
    # bytes; empty in every file)
    cols = [("It...", _w(36)), ("Booster ID", _w(107)), ("Part Number", _w(214))]
    for f in ("F1", "F2", "R1", "R2"):
        cols += [(f"Range low - {L[f]}", _fw(140, L[f])), (f"Range high - {L[f]}", _fw(148, L[f]))]
    cols += [(f"Gain - {L[f]}", _fw(78, L[f])) for f in ("F1", "F2")]
    tabs.append({"name": "Boosters", "grid": _grid(cols, [[str(b), f"B{b}", ""] + ["0.00"] * 10
                                                        for b in range(1, 25)]),
                 "note": NOT_READ})
    cols = [("It...", _w(36)), ("Booster ID", _w(95)), ("Min. Voltage", _w(124)), ("Amperage 1", _w(120))]
    for k in range(2, 9):
        cols += [(f"Voltage {k}", _w(95)), (f"Amperage {k}", _w(120))]
    tabs.append({"name": "Booster Powering", "grid": _grid(cols, [[str(b), f"B{b}"] + ["0.00"] * 16
                                                                for b in range(1, 25)]),
                 "note": NOT_READ})

    # the tab control's order, as Lode wraps it
    by = {t["name"]: t for t in tabs}
    names = (["Actives", "Reserve Gain", "Power Steps"]
             + [f"Pads/EQs Bank {k}" for k in range(1, 9)]
             + [f"EQs Bank {k}" for k in range(9, 17)]
             + ["Plug-Ins", "Plug-Ins Powering", "Configuration Table", "Bridgers",
                "Feedermakers", "Inline EQs", "Custom Cascading", "Boosters", "Booster Powering"])
    return {"kind": "atv", "title": f"Design Assistant Actives Specs - {name}",
            "menus": ["File", "Edit"], "tabs": [by[n] for n in names]}


EQ_BANKS, EQ_BANK_ROW, EQ_BANK_ROWS = 172024, 88, 128
PLUGINS, PLUGIN_STRIDE, PLUGIN_RECORDS = 164412, 155, 32


# --------------------------------------------------------------------------
# the Cables window
# --------------------------------------------------------------------------
def cables_window(cbl: bytes, par: bytes | None, name: str) -> dict:
    """Cables, Connectors and Series/Colors (set A2's 4c/4d: WVEXT862's
    Cables tab, IDs 0-52 seen).  Every one of the 100 records is a row,
    Cable ID 0-99; the losses are the first loss block's ten, F1-F6 then
    R1-R4, to six places."""
    L = freq_labels(par)
    classic = S._classic(cbl)
    start, stride, _ = (S.CLASSIC_LAYOUT if classic else S.LAYOUT)["cbl"]
    n = S.CLASSIC_NAME if classic else 25
    cols = [("It...", 30), ("Cable ID", 69), ("Part Number", 171), ("Loop Res./1000", 132)]
    cols += [(f"{L[f]}/100", 49 + 10 * max(len(L[f]) - 1, 0)) for f in FREQ_KEYS]
    rows = []
    for r in range(100):
        o = start + stride * r
        seg = cbl[o:o + stride]
        if len(seg) < stride:
            seg = bytes(stride)
        rows.append([str(r + 1), str(r), S._name(seg[5:5 + n]), _f2(_fx(seg, 5 + n) * 1000)]
                    # the return columns are stored negative (-0.46, -0.16
                    # for EX P3 500 A); Lode shows them 0.460000, 0.160000
                    + [f"{abs(v) / S.SCALE:.6f}" for v in struct.unpack_from("<10i", seg, 9 + n)])
    tabs = [{"name": "Cables", "grid": _grid(cols, rows)},
            {"name": "Connectors", "unseen": True},
            {"name": "Series/Colors", "unseen": True}]
    return {"kind": "cbl", "title": f"Design Assistant Cable Specs - {name}",
            "menus": ["File", "Series", "Edit"], "tabs": tabs}


# --------------------------------------------------------------------------
# the Parameters window: six tabs of fields (WV750-2026's screenshots)
# --------------------------------------------------------------------------
def parameters_window(par: bytes, name: str) -> dict:
    p = S.read_parameters(par)
    L = freq_labels(par)
    on = S.read_frequencies(par)
    levels = S.read_levels(par)
    supplies = {s.type_id: s for s in S.read_supplies(par)} if hasattr(S, "read_supplies") else {}
    classic = S._classic(par)
    nsup = S.CLASSIC_PAR_SUPPLY_SLOTS if classic else S.PAR_SUPPLY_SLOTS
    lv = levels.get("levels") or []
    extra = p.get("extra_levels") or [[0.0] * 6] * 16
    tilts = p.get("tilts") or [[0.0] * 4] * 16
    level_rows = []
    for k in range(16):
        four = lv[k] if k < len(lv) else [0.0] * 4
        level_rows.append([str(k)] + [_f2(v) for v in four] + [_f2(v) for v in extra[k]]
                          + [_f2(v) for v in tilts[k]])
    level_cols = ["Level", f"Min. {L['F1']}", f"Min. {L['F2']}", f"Max. {L['R1']}", f"Max. {L['R2']}",
                  f"Min. {L['F3']}", f"Min. {L['F4']}", f"Min. {L['F5']}", f"Min. {L['F6']}",
                  f"Max. {L['R3']}", f"Max. {L['R4']}", "Max Tilt Fwd", "Min Tilt Fwd",
                  "Max Tilt Ret", "Min Tilt Ret"]
    w = p.get("tap_windows", {})
    transformers = {t["id"]: t for t in p.get("transformers", [])}
    return {
        "kind": "par", "title": f"Design Assistant Parameters Specs - {name}",
        "menus": ["File", "Edit"],
        "tabs": [{"name": t} for t in ("General Parameters", "System Levels", "Tap Selection",
                                        "Powering", "Underground Housings", "Frequencies")],
        "values": {
            "distance_units": p.get("distance_units"), "signal_display": p.get("signal_display"),
            "show_count_types": p.get("show_count_types"),
            "strand_series": p.get("strand_series", []),
            "niu": {k: _f2(v) for k, v in p.get("niu", {}).items()},
            "max_crossover": _f2(p.get("max_crossover", 0.0)),
            "max_return_crossover": _f2(p.get("max_return_crossover", 0.0)),
            "eq_placement": p.get("eq_placement"),
            "replacement_cables": p.get("replacement_cables", {}),
            "misc_parts": p.get("misc_parts", {}),
            "lines_per_form": p.get("lines_per_form", 0),
            "max_tap_cascade": p.get("max_tap_cascade", 0),
            "max_le_cascade": p.get("max_le_cascade", 0),
            "allow_over_equalization": p.get("allow_over_equalization"),
            "tap_margin": _f2(levels.get("tap_margin", 0.0)),
            "forward_windows": [[L[k], _f2(w.get(k, 0.0))] for k in ("F1", "F2", "F3", "F4", "F5", "F6")],
            "return_windows": [[L[k], _f2(w.get(k, 0.0))] for k in ("R1", "R2", "R3", "R4")],
            "level_cols": level_cols, "level_rows": level_rows,
            "optimization": p.get("optimization"),
            "enforce_tap_window": p.get("enforce_tap_window"),
            "enforce_tap_tilt": p.get("enforce_tap_tilt"),
            "flag_hi_lo_tilt": p.get("flag_hi_lo_tilt"),
            "ports_by_homes": [[h, p.get("ports_by_homes", {}).get(h, 0)] for h in range(1, 33)],
            "tap_type_by_ports": [[n, p.get("tap_type_by_ports", {}).get(n, 0)] for n in range(1, 33)],
            "power_interpolation": p.get("power_interpolation"),
            "overvoltage_check": p.get("overvoltage_check"),
            "pre_load": p.get("pre_load"),
            "max_amps_through": {k: _f2(v) for k, v in p.get("max_amps_through", {}).items()},
            "transformers": [[k, (transformers.get(k) or {}).get("part", ""),
                              _f2((transformers.get(k) or {}).get("volts", 0.0))] for k in range(1, 9)],
            "supplies": [[k, supplies[k].name if k in supplies else "",
                          _f2(supplies[k].volts if k in supplies else 0.0),
                          _f2(supplies[k].amps if k in supplies else 0.0),
                          _f2(supplies[k].rating if k in supplies else 0.0)] for k in range(1, nsup + 1)],
            "points": p.get("points", {}),
            "housings": [[h["number"], h["part"], h["min_points"]] for h in p.get("housings", [])],
            "forward": [[L[k], k in on] for k in ("F1", "F2", "F3", "F4", "F5", "F6")],
            "return": [[L[k], k in on] for k in ("R1", "R2", "R3", "R4")],
            "eq_selection": p.get("eq_selection", {}),
        },
    }


WINDOWS = {".atv": "Actives", ".cbl": "Cables", ".par": "Parameters"}


def window(ext: str, data: bytes, par: bytes | None, name: str) -> dict:
    if ext == ".atv":
        return actives_window(data, par, name)
    if ext == ".cbl":
        return cables_window(data, par, name)
    if ext == ".par":
        return parameters_window(data, name)
    raise ValueError(ext)
