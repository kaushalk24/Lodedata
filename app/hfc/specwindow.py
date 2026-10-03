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
    """``cols``: (head, width) or (head, width, cell style) -- "group" the
    grey of Tap Selection Group, "id" the light grey of a column Lode does
    not let you edit."""
    return {"cols": [{"head": c[0], "w": c[1], **({"cls": c[2]} if len(c) > 2 else {})}
                     for c in cols], "rows": rows}


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

    # Actives: In/Out at the four, the banks, then In at F3-F6, R3, R4 and
    # Out at F3-F6, R3, R4, each Out with its Out/Loss (the user's Q11
    # recording, scrolled to the end): In from +171 and Out from +195, six
    # each -- no file has a figure at R3 or R4 yet (+187 to +218 empty in all)
    cols = [("It...", _w(31)), ("Active ID", _w(93)), ("Part Number", _w(214))]
    cols += [(f"In - {L[k]}", _fw(57, L[k])) for k in ("F1", "F2", "R1", "R2")]
    for k in ("F1", "F2", "R1", "R2"):
        cols += [(f"Out - {L[k]}", _fw(67, L[k])), ("Out/Loss", _w(93))]
    cols += [("Fwd Pad", _w(88)), ("Ret Pad", _w(83)), ("Fwd EQ", _w(80)), ("Ret EQ", _w(74))]
    extra = ("F3", "F4", "F5", "F6", "R3", "R4")
    cols += [(f"In - {L[k]}", _fw(57, L[k])) for k in extra]
    for k in extra:
        cols += [(f"Out - {L[k]}", _fw(67, L[k])), ("Out/Loss", _w(93))]
    rows = []
    for i, seg in recs:
        ins = struct.unpack_from("<4i", seg, levels_at)
        outs = struct.unpack_from("<4i", seg, levels_at + 16)
        row = [str(i), ident(seg), part(seg)] + [_f2(v / S.SCALE) for v in ins]
        for v in outs:
            row += [_f2(v / S.SCALE), "0 Out"]
        row += [str(seg[S.ATV_PAD_BANKS] + 1), str(seg[S.ATV_PAD_BANKS + 1] + 1),
                str(seg[S.ATV_EQ_BANKS] + 1), str(seg[S.ATV_EQ_BANKS + 1] + 1)]
        row += [_f2(_fx(seg, in_at + 4 * k)) for k in range(6)]
        for k in range(6):
            row += [_f2(_fx(seg, out_at + 4 * k)), "0 Out"]
        rows.append(row)
    tabs.append({"name": "Actives", "grid": _grid(cols, rows),
                 "note": "Out/Loss: set to Loss on row 1's Out - F1 it is byte 518 of "
                         "the file (TEST_OL.atv); where the other rows and columns keep "
                         "it is not known yet, so every row reads 0 Out."})

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
            # Quantity: 1 beside every plug-in named, 0 beside none -- every
            # row of the user's 13c-13h (WV750's 68N-68B, 69N-69M); the
            # slot holds no 1, so where a larger one would be kept is not known
            for p in plugs:
                row += [str(p), "1" if p else "0"]
            rows.append(row)
    tabs.append({"name": "Configuration Table", "grid": _grid(cols, rows),
                 "note": "Plugin 2-8: no file names one yet."})

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
    tabs = [{"name": "Cables", "grid": _grid(cols, rows)}]
    # Connectors (the user's 16a, the older WVEXT862): the Feed-Thru and
    # Pin-Type part numbers, then for Line Extender, Amplifier, Equalizer,
    # Tap and Coupler 1 Pin-Type or 0 Feed-Thru (every named cable 1, the
    # empty ones 0)
    cols = [("It...", _w(37)), ("Cable ID", _w(87)), ("Part Number", _w(213)),
            ("Feed-Thru Part #", _w(229)), ("Pin-Type Part #", _w(219))]
    cols += [(h, _w(138)) for h in ("Line Extender", "Amplifier", "Equalizer", "Tap", "Coupler")]
    conn, series, colors = [], [], []
    for r in range(100):
        seg = cbl[start + stride * r:start + stride * (r + 1)]
        if len(seg) < stride:
            seg = bytes(stride)
        flags = struct.unpack_from("<5i", seg, 119 + n)
        conn.append([str(r + 1), str(r), S._name(seg[5:5 + n]), S._name(seg[89 + n:104 + n]),
                     S._name(seg[104 + n:119 + n])]
                    + ["1 - Pin-Type" if v else "0 - Feed-Thru" for v in flags])
        # Series/Colors (16c): each series' name in its colour, on black
        slots = [S._series(seg, 139 + n + 23 * k) for k in range(10)]
        series.append([str(r + 1), str(r), S._name(seg[5:5 + n])] + [name for _, name in slots])
        colors.append(["", "", ""] + [color for color, _ in slots])
    tabs.append({"name": "Connectors", "grid": _grid(cols, conn)})
    cols = [("It...", _w(37)), ("Cable ID", _w(87)), ("Part Number", _w(213))]
    cols += [(f"{k}00 Series" if k else "000 Series", _w(106), "series") for k in range(10)]
    grid = _grid(cols, series)
    grid["colors"] = colors
    tabs.append({"name": "Series/Colors", "grid": grid})
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


# --------------------------------------------------------------------------
# the Taps window: eleven tabs (the user's Q14 recording of BH1GHzMid.tap)
# --------------------------------------------------------------------------
# The 128 bytes before the rows: Active Taps, four rows (2/4/6/8 Port Taps)
# of Min. Voltage, Amperage 1, Voltage 2 ... Amperage 4 (all 0.00 there).
# In each port slot, after its Values (+25) and Losses (+65): the Swap
# Opt. as a port code (2 Port 0 ... 8 Port 3), Active, Self-Term., then the
# F-Pad, R-Pad, F-EQ and R-EQ banks less one (FF: 0)
TAP_ACTIVE, TAP_GROUP = S.TAP_ACTIVE_TABLE, S.TAP_GROUP
TAP_SWAP, TAP_ACTIVE_FLAG, TAP_SELF_TERM, TAP_BANKS = S.TAP_SWAP, S.TAP_ACTIVE, S.TAP_SELF_TERM, S.TAP_BANKS
# the order of a Values or Losses block, and the order Lode's columns take
TAP_BLOCK = ("F1", "F2", "F3", "F4", "F5", "F6", "R1", "R2", "R3", "R4")
TAP_SHOWN = ("F1", "F2", "R1", "R2", "F3", "F4", "F5", "F6", "R3", "R4")


def taps_window(tap: bytes, par: bytes | None, name: str) -> dict:
    """Every row of the tap file (512), as the program's Tap Specs window
    shows it: BH1GHzMid's 30 (8 Port 9830 only), 29 (9229, 9429) ... 4
    (9204), its groups 1 and 2 (129 RMT2122-29 ... 104 RMT2122-04), Values
    and Losses row by row (30's 8 Port: 30.00 at every frequency on, Loss
    1.10 0.40 0.40 0.30, 550 0.60, 860 1.00)."""
    L = freq_labels(par)
    classic = S._classic(tap)
    start, stride, _ = (S.CLASSIC_LAYOUT if classic else S.LAYOUT)["tap"]
    slots = S.CLASSIC_TAP_PORT_SLOTS if classic else S.TAP_PORT_SLOTS
    width = S.CLASSIC_NAME if classic else 25
    rows = []
    for r in range(512):
        seg = tap[start + stride * r:start + stride * (r + 1)]
        rows.append(seg if len(seg) == stride else bytes(stride))

    def tap_id(seg) -> float:
        return _fx(seg, S.TAP_ID_OFFSET)

    def shown_id(seg) -> str:
        v = tap_id(seg)
        return "" if not v else (str(int(v)) if v == int(v) else _f2(v))

    def part(seg, n) -> str:
        o = slots[n]
        return S._name(seg[o:o + min(width, 20)])

    def block(seg, n, at) -> dict:
        o = slots[n] + width + at - 25
        return dict(zip(TAP_BLOCK, (v / S.SCALE for v in struct.unpack_from("<10i", seg, o))))

    def tail(seg, n, k) -> int:
        o = slots[n] + width + k - 25
        return seg[o] if o < len(seg) else 0

    def yes(v) -> str:
        return "1 - Yes" if v else "0 - No"

    tabs = []
    cols = [("It...", _w(35)), ("Tap ID", _w(70))]
    cols += [(f"{n} Port Part Number", _w(191)) for n in (2, 4, 6, 8)]
    cols += [("Tap Selection Group", _w(206), "group")]
    tabs.append({"name": "Tap IDs/PartNumbers", "grid": _grid(cols, [
        [str(r + 1), shown_id(seg)] + [part(seg, n) for n in (2, 4, 6, 8)] + [str(seg[TAP_GROUP] + 1)]
        for r, seg in enumerate(rows)])})
    for n in (2, 4, 6, 8):
        cols = [("It...", _w(38)), ("Tap ID", _w(61)), ("Part Number", _w(189)),
                ("Active", _w(56)), ("Self-Term.", _w(90))]
        cols += [(f"Value - {L[f]}", _fw(87, L[f], 13)) for f in TAP_SHOWN]
        cols += [(f"Loss - {L[f]}", _fw(78, L[f], 13)) for f in TAP_SHOWN]
        grid = []
        for r, seg in enumerate(rows):
            value, loss = block(seg, n, S.TAP_VALUE_BLOCK), block(seg, n, S.TAP_INSERTION_BLOCK)
            grid.append([str(r + 1), shown_id(seg), part(seg, n),
                         yes(tail(seg, n, TAP_ACTIVE_FLAG)), yes(tail(seg, n, TAP_SELF_TERM))]
                        + [_f2(value[f]) for f in TAP_SHOWN] + [_f2(loss[f]) for f in TAP_SHOWN])
        tabs.append({"name": f"{n} Port Taps", "grid": _grid(cols, grid)})
    cols = [("It...", _w(37)), ("Tap Type", _w(86)), ("Min. Voltage", _w(110)), ("Amperage 1", _w(120))]
    for k in (2, 3, 4):
        cols += [(f"Voltage {k}", _w(95)), (f"Amperage {k}", _w(120))]
    grid = []
    for k, n in enumerate((2, 4, 6, 8)):
        vals = [] if classic else struct.unpack_from("<8i", tap, TAP_ACTIVE + 32 * k)
        grid.append([str(k + 1), f"{n} Port Taps"] + [_f2(v / S.SCALE) for v in vals or [0] * 8])
    tabs.append({"name": "Active Taps", "grid": _grid(cols, grid)})
    cols = []
    for n in (2, 4, 6, 8):
        cols += [(f"{n} Port ID", _w(88), "id"), (f"{n} Port Swap Opt.", _w(172))]
    tabs.append({"name": "Tap Swap Options", "plain": True, "grid": _grid(cols, [
        sum(([_f2(tap_id(seg)), str(2 * (tail(seg, n, TAP_SWAP) + 1))] for n in (2, 4, 6, 8)), [])
        for seg in rows])})
    for n in (2, 4, 6, 8):
        cols = [("It...", _w(37)), (f"{n} Port Part Num.", _w(164)), (f"{n} Port F-Pad", _w(125)),
                (f"{n} Port R-Pad", _w(129)), (f"{n} Port F-EQ", _w(116)), (f"{n} Port R-EQ", _w(120))]
        tabs.append({"name": f"{n} Port Pad/EQ Banks", "grid": _grid(cols, [
            [str(r + 1), part(seg, n)] + [str((tail(seg, n, TAP_BANKS + k) + 1) & 0xFF) for k in range(4)]
            for r, seg in enumerate(rows)])})
    return {"kind": "tap", "title": f"Design Assistant Tap Specs - {name}",
            "menus": ["File", "Edit"], "tabs": tabs}


# --------------------------------------------------------------------------
# the Couplers window (the user's Q15 recording of HUMB1GHzMid.cpr)
# --------------------------------------------------------------------------
COUPLER_RECORDS = 998      # the NIU tables follow; a PCD's record (998) is past them
NIU_NOTE = ("Every row Lode showed for HUMB1GHzMid is empty; where the file keeps "
            "these, and how many rows there are, is not known yet.")


def couplers_window(cpr: bytes, par: bytes | None, name: str) -> dict:
    """Every coupler record, as the Coupler Specs window's Couplers tab shows
    it: HUMB1GHzMid's 1 SSP-3N (2) Tap 5.30 3.60 3.60 3.90, Thru 5.30 3.60
    3.60 3.90, legs 1, Tap 550 4.40 870 4.90; 9 FMT Split (62), Internal,
    Tap -9.00 at 1002, 102, 550 and 870; 11 no part, 92, Internal, Tap 1002
    99.00.  A block is F1 F2 F3-F6 R1 R2 R3 R4; Lode shows F1 F2 R1 R2 first."""
    L = freq_labels(par)
    classic = S._classic(cpr)
    start, stride, _ = (S.CLASSIC_LAYOUT if classic else S.LAYOUT)["cpr"]
    n = S.CLASSIC_NAME if classic else 25
    first4, rest = ("F1", "F2", "R1", "R2"), ("F3", "F4", "F5", "F6", "R3", "R4")

    def head(word, f, base):
        return (f"{word} {L[f]}", _fw(base, L[f], 13))

    cols = [("It...", _w(35)), ("Part Number", _w(215)), ("Coupler ID", _w(105)),
            ("Optical", _w(72)), ("Internal", _w(73))]
    cols += [head("Tap", f, 57) for f in first4] + [head("Thru", f, 67) for f in first4]
    cols += [("Tap Legs", _w(94))]
    cols += [head("Tap", f, 57) for f in rest] + [head("Thru", f, 67) for f in rest]
    rows = []
    for r in range(COUPLER_RECORDS):
        seg = cpr[start + stride * r:start + stride * (r + 1)]
        if len(seg) < stride:
            break
        code = _fx(seg, 1)
        # the Tap leg block, then the Thru leg block
        keys = [f"t{f}" for f in TAP_BLOCK] + [f"h{f}" for f in TAP_BLOCK]
        values = dict(zip(keys, (v / S.SCALE for v in struct.unpack_from("<20i", seg, 5 + n))))
        rows.append([str(r + 1), S._name(seg[5:5 + n]),
                     str(int(code)) if code == int(code) else _f2(code),
                     "0 - No", "1 - Yes" if seg[88 + n] else "0 - No"]
                    + [_f2(values[f"t{f}"]) for f in first4] + [_f2(values[f"h{f}"]) for f in first4]
                    + [str(seg[85 + n] + 1)]
                    + [_f2(values[f"t{f}"]) for f in rest] + [_f2(values[f"h{f}"]) for f in rest])
    tabs = [{"name": "Couplers", "grid": _grid(cols, rows),
             "note": "Optical: no file seen sets it; every row reads 0 - No."}]
    blank = [""] * 30
    cols = [("It...", _w(38)), ("Part Number", _w(213)), ("NIU ID#", _w(82)), ("Phone Ports", _w(123)),
            ("Video Ports", _w(115)), ("Min. Ports", _w(102)), ("Homes", _w(68))]
    cols += [(f"{'Min.' if f[0] == 'F' else 'Max.'} {L[f]}", _fw(67, L[f], 12))
             for f in ("F1", "F2", "R1", "R2", "F3", "F4", "F5", "F6", "R3", "R4")]
    tabs.append({"name": "Base NIUs", "note": NIU_NOTE, "grid": _grid(cols, [
        [str(k + 1), ""] + ["0"] * 5 + ["0.00"] * 10 for k, _ in enumerate(blank)])})
    cols = [("It...", _w(38)), ("Part Number", _w(213)), ("Coupler ID", _w(104)), ("Idle Power", _w(108)),
            ("1 Line Active", _w(130)), ("2+ Lines Active", _w(155)), ("Add1 Ring", _w(100)),
            ("Min. Voltage", _w(127)), ("Max. Voltage", _w(130))]
    tabs.append({"name": "NIU Power Requirements", "note": NIU_NOTE, "grid": _grid(cols, [
        [str(k + 1), "", "0"] + ["0.00"] * 6 for k, _ in enumerate(blank)])})
    cols = [("It...", _w(38)), ("Array Code", _w(108)), ("Drop Coupler", _w(132))]
    cols += [c for _ in range(8) for c in (("NIU ID#", _w(85)), ("Quantity", _w(82)))]
    tabs.append({"name": "NIU Arrays", "note": NIU_NOTE, "grid": _grid(cols, [
        [str(k + 1), "", "0"] + ["0"] * 16 for k, _ in enumerate(blank)])})
    cols = [("It...", _w(38)), ("Cumulative Prob.", _w(168)), ("Percent", _w(82)), ("Array Code", _w(105)),
            ("Add1 Lines", _w(110)), ("Base Offhook", _w(138)), ("Base Ringing", _w(132)),
            ("Extra Offhook", _w(135)), ("Extra Ringing", _w(135))]
    tabs.append({"name": "Meta NIUs", "note": NIU_NOTE, "grid": _grid(cols, [
        [str(k + 1), "0.00", "0.00", ""] + ["0.00"] * 5 for k, _ in enumerate(blank)])})
    return {"kind": "cpr", "title": f"Design Assistant Coupler Specs - {name}",
            "menus": ["File", "Edit"], "tabs": tabs}


WINDOWS = {".atv": "Actives", ".cbl": "Cables", ".par": "Parameters", ".tap": "Taps",
           ".cpr": "Couplers"}


def window(ext: str, data: bytes, par: bytes | None, name: str) -> dict:
    if ext == ".atv":
        return actives_window(data, par, name)
    if ext == ".cbl":
        return cables_window(data, par, name)
    if ext == ".par":
        return parameters_window(data, name)
    if ext == ".tap":
        return taps_window(data, par, name)
    if ext == ".cpr":
        return couplers_window(data, par, name)
    raise ValueError(ext)
