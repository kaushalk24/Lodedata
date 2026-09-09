"""Sample specs, for learning the tool -- not for real design.

Lode Data ships sample specification files in a SPECS subdirectory and says
they "are intended to be samples only and, therefore, should not be used for
actual design".  This is the same idea: something to key a design against
while you are finding your way around, clearly labelled so nobody mistakes it
for a real spec set.

Attenuation figures are the published values for the common P3/QR hardline and
RG-6/RG-11 drop, given at 750 MHz and 55 MHz so the sqrt(f) interpolation has
two real points to work between.  Tap and passive losses are the usual values
for standard 750 MHz plant.  Everything here is editable in the app -- it is a
starting point, not a specification.
"""
from .model import (Library, CableType, TapType, PassiveType, ActiveType,
                    PowerSupplyType)

# name, loop resistance ohm/1000ft, dB/100ft @55, @750
_CABLES = [
    (".412 P3", 2.60, 0.44, 1.73, "hardline"),
    (".500 P3", 1.72, 0.38, 1.42, "hardline"),
    (".565 P3", 1.30, 0.34, 1.28, "hardline"),
    (".625 P3", 1.07, 0.30, 1.13, "hardline"),
    (".750 P3", 0.76, 0.26, 0.99, "hardline"),
    (".875 P3", 0.55, 0.23, 0.86, "hardline"),
    ("1.000 P3", 0.42, 0.20, 0.77, "hardline"),
    ("540 QR", 1.61, 0.35, 1.32, "hardline"),
    ("715 QR", 0.95, 0.28, 1.05, "hardline"),
    ("860 QR", 0.72, 0.23, 0.88, "hardline"),
    ("RG-6 drop", 36.0, 1.55, 5.65, "drop"),
    ("RG-11 drop", 15.0, 1.00, 3.60, "drop"),
]

# tap value -> through loss at 55 / 750 MHz, for 2 / 4 / 8 port taps
_TAP_THROUGH = {
    4:  (2.9, 3.6), 7: (1.6, 2.3), 8: (1.4, 2.1), 11: (1.0, 1.5),
    14: (0.7, 1.2), 17: (0.6, 1.0), 20: (0.5, 0.9), 23: (0.4, 0.8),
    26: (0.4, 0.8), 29: (0.4, 0.8), 32: (0.4, 0.8), 35: (0.4, 0.8),
}

_PASSIVES = [
    ("2-way splitter", "splitter", [3.5, 3.5], [True, True]),
    ("3-way splitter", "splitter", [5.5, 5.5, 5.5], [True, True, True]),
    ("4-way splitter", "splitter", [7.0, 7.0, 7.0, 7.0], [True] * 4),
    ("DC-8 coupler", "coupler", [1.4, 8.5], [True, True]),
    ("DC-12 coupler", "coupler", [0.9, 12.5], [True, True]),
    ("DC-16 coupler", "coupler", [0.6, 16.5], [True, True]),
    ("Power inserter", "power_inserter", [0.5], [True]),
]

# name, kind, outputs, In(fwd hi, fwd lo, ret hi, ret lo),
#                        Out(fwd hi, fwd lo, ret hi, ret lo), NF, watts
# In forward high of 99 marks an optical node: fibre fed, no RF input.
_ACTIVES = [
    ("Optical node (4 out)", "node", 4, (99.0, 0.0, 27.0, 27.0),
     (50.0, 40.0, 0.0, 0.0), 6.0, 70.0),
    ("Optical node (2 out)", "node", 2, (99.0, 0.0, 27.0, 27.0),
     (50.0, 40.0, 0.0, 0.0), 6.0, 60.0),
    ("System amplifier", "bridger", 4, (17.0, 13.0, 21.0, 21.0),
     (50.0, 40.0, 43.0, 43.0), 7.0, 55.0),
    ("Line extender", "line_extender", 1, (19.0, 15.0, 21.0, 21.0),
     (48.0, 39.0, 40.0, 40.0), 8.0, 30.0),
    ("Mini bridger", "bridger", 2, (12.0, 11.0, 21.0, 21.0),
     (49.0, 38.0, 40.0, 40.0), 7.5, 43.0),
]

# Actives are constant-power devices, so the draw is derived from the wattage
# across the usual operating range rather than stated as a single number.
_POWER_VOLTAGES = (38.0, 45.0, 52.0, 60.0, 70.0, 80.0, 90.0)


def _power_table(watts: float) -> list:
    return [[v, round(watts / v, 2)] for v in _POWER_VOLTAGES]

_SUPPLIES = [
    ("90 V / 15 A supply", 90.0, 15.0),
    ("90 V / 18 A supply", 90.0, 18.0),
    ("60 V / 15 A supply", 60.0, 15.0),
]


def starter_library() -> Library:
    lib = Library(name="Sample specs (not for real design)")
    for name, r, a55, a750, kind in _CABLES:
        lib.add(CableType(
            id=f"cbl_{name.replace(' ', '_').replace('.', 'p')}",
            name=name, kind=kind,
            loop_resistance_ohm_per_1000ft=r,
            attenuation=[[55.0, a55], [750.0, a750]],
            source="starter",
        ))
    for value, (t55, t750) in sorted(_TAP_THROUGH.items()):
        for ports in (2, 4, 8):
            lib.add(TapType(
                id=f"tap_{ports}x{value}",
                name=f"{ports}-port {value} dB tap",
                ports=ports, tap_value_db=float(value),
                through_loss=[[55.0, t55], [750.0, t750]],
                return_through_loss=[[5.0, t55], [42.0, t55]],
                current_draw_a=0.0, power_passing=True,
                source="starter",
            ))
    for name, kind, losses, powers in _PASSIVES:
        lib.add(PassiveType(
            id=f"psv_{name.replace(' ', '_').replace('-', '_')}",
            name=name, kind=kind,
            port_losses=losses, power_passing=powers, source="starter",
        ))
    for name, kind, outs, ins, outs_lv, nf, watts in _ACTIVES:
        lib.add(ActiveType(
            id=f"act_{name.replace(' ', '_').replace('(', '').replace(')', '')}",
            name=name, kind=kind, outputs=outs,
            in_forward_high=ins[0], in_forward_low=ins[1],
            in_return_high=ins[2], in_return_low=ins[3],
            out_forward_high=outs_lv[0], out_forward_low=outs_lv[1],
            out_return_high=outs_lv[2], out_return_low=outs_lv[3],
            noise_figure_db=nf,
            power_draw=_power_table(watts),
            current_draw_a=round(watts / 60.0, 2),
            source="starter",
        ))
    for name, v, a in _SUPPLIES:
        lib.add(PowerSupplyType(id=f"ps_{int(v)}_{int(a)}", name=name,
                                volts=v, amps=a, source="starter"))
    return lib
