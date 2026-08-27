"""A generic 750 MHz equipment library.

The figures here are representative of a 750 MHz / 42 MHz split hybrid
fibre-coax plant built with 75 ohm hardline: close enough to real hardware for
designs to come out realistic, but not any manufacturer's published data.
Load your own spec files for real work -- that is what the loader is for.

``generic750()`` returns a complete :class:`~lode.specs.SpecSet`.
"""

from __future__ import annotations

from .specs import (Active, ActivesSpec, Cable, CablesSpec, Coupler,
                        CouplersSpec, Frequency, HomesToPorts, ParametersSpec,
                        PerformanceSpec, PriceItem, PricingSpec, SpecSet, Tap,
                        TapsSpec)
from .specs.actives import Distortion, Equalizer, OutputPort

F1, F2, R1, R2 = "F1", "F2", "R1", "R2"


# ---------------------------------------------------------------------------
# parameters
# ---------------------------------------------------------------------------
def parameters() -> ParametersSpec:
    return ParametersSpec(
        name="generic750",
        description="750 MHz forward / 42 MHz return, feet, dBmV",
        system_name="Generic 750 MHz System",
        distance_units="feet",
        signal_display="dBmV",
        frequencies=[
            Frequency(F1, "750", 750.0, True),
            Frequency(F2, "55", 55.0, True),
            Frequency(R1, "42", 42.0, True),
            Frequency(R2, "5", 5.0, True),
        ],
        fwd_eq_high=F1, fwd_eq_low=F2, rtn_eq_high=R1, rtn_eq_low=R2,
        min_tap_output={F1: 16.0, F2: 12.0},
        tap_window=10.0,
        enforce_tap_window=False,
        max_return_tap_input={R1: 40.0, R2: 40.0},
        return_window=12.0,
        set_margin=1.0,
        max_crossover=3.0,
        allow_over_equalization=True,
        default_housing_offset=3.0,
        homes_to_ports=[
            HomesToPorts(1, 2), HomesToPorts(2, 2),
            HomesToPorts(4, 4), HomesToPorts(99, 8),
        ],
        default_tsg=1,
        default_cable="P3-500",
        default_trunk_cable="P3-750",
        default_active="LE-750",
        default_coupler="SP2",
        cable_loss_factor=1.0,
        connector_loss=0.0,
    )


# ---------------------------------------------------------------------------
# cables
# ---------------------------------------------------------------------------
CABLE_DATA = [
    # id, description, 750, 55, 42, 5, loop ohms/1000ft, $/ft
    ("P3-412", '0.412" semi-flexible hardline', 1.72, 0.46, 0.40, 0.15, 1.65, 0.42),
    ("P3-500", '0.500" semi-flexible hardline', 1.42, 0.38, 0.33, 0.13, 1.10, 0.55),
    ("P3-625", '0.625" semi-flexible hardline', 1.14, 0.30, 0.26, 0.10, 0.75, 0.78),
    ("P3-750", '0.750" semi-flexible hardline', 0.95, 0.25, 0.22, 0.09, 0.55, 0.98),
    ("P3-875", '0.875" semi-flexible hardline', 0.83, 0.22, 0.19, 0.08, 0.41, 1.30),
    ("RG-6",   'RG-6 subscriber drop', 5.65, 1.55, 1.35, 0.55, 15.0, 0.11),
    ("RG-11",  'RG-11 long drop', 3.65, 1.00, 0.87, 0.35, 6.5, 0.26),
]


def cables() -> CablesSpec:
    rows = []
    for cid, desc, a750, a55, a42, a5, res, price in CABLE_DATA:
        rows.append(Cable(
            id=cid, description=desc, part_number=cid,
            atten={F1: a750, F2: a55, R1: a42, R2: a5},
            loop_res=res, size=desc.split('"')[0] + '"' if '"' in desc else "",
            price=price, connector_price=6.50, labor=0.35,
        ))
    return CablesSpec(name="generic750", description="hardline and drop cable",
                      rows=rows)


# ---------------------------------------------------------------------------
# taps
# ---------------------------------------------------------------------------
#: through (insertion) loss at 750 MHz for a four-port tap, by tap value
INSERTION_4 = {4: 3.6, 8: 1.8, 11: 1.3, 14: 1.0, 17: 0.9, 20: 0.8,
               23: 0.7, 26: 0.6, 29: 0.6, 32: 0.5, 35: 0.5}
PORT_FACTOR = {2: 0.80, 4: 1.00, 8: 1.45}
VALUES = {
    2: [4, 8, 11, 14, 17, 20, 23, 26, 29, 32, 35],
    4: [4, 8, 11, 14, 17, 20, 23, 26, 29, 32],
    8: [8, 11, 14, 17, 20, 23, 26, 29, 32],
}


def taps() -> TapsSpec:
    rows = []
    for ports in (2, 4, 8):
        for value in VALUES[ports]:
            ins750 = round(INSERTION_4[value] * PORT_FACTOR[ports], 1)
            rows.append(Tap(
                id=f"T{ports}-{value}",
                description=f"{ports}-port {value} dB tap",
                part_number=f"TAP{ports}{value:02d}",
                tsg=1, value=float(value), ports=ports,
                tap_loss={
                    F1: value + 0.5, F2: max(0.5, value - 0.5),
                    R1: max(0.5, value - 0.7), R2: max(0.5, value - 1.0),
                },
                insertion_loss={
                    F1: ins750,
                    F2: max(0.2, round(ins750 * 0.45, 1)),
                    R1: max(0.2, round(ins750 * 0.40, 1)),
                    R2: max(0.2, round(ins750 * 0.30, 1)),
                },
                self_terminating=False,
                max_amps=15.0, resistance=0.06, power_passing=True,
                price=18.0 + ports * 1.5, labor=12.0,
            ))
    # end-of-line, self terminating variants of the high-value taps
    for ports in (2, 4, 8):
        for value in (8, 11, 14, 17, 20, 23, 26, 29):
            if value not in VALUES[ports]:
                continue
            rows.append(Tap(
                id=f"T{ports}-{value}T",
                description=f"{ports}-port {value} dB self-terminating tap",
                part_number=f"TAP{ports}{value:02d}T",
                tsg=1, value=float(value), ports=ports,
                tap_loss={
                    F1: value + 0.5, F2: max(0.5, value - 0.5),
                    R1: max(0.5, value - 0.7), R2: max(0.5, value - 1.0),
                },
                insertion_loss={}, self_terminating=True,
                max_amps=15.0, resistance=0.06, power_passing=False,
                price=18.0 + ports * 1.5, labor=12.0,
            ))
    return TapsSpec(name="generic750",
                    description="single tap selection group, 2/4/8 port",
                    rows=rows)


# ---------------------------------------------------------------------------
# couplers
# ---------------------------------------------------------------------------
COUPLER_DATA = [
    # id, description, kind, thru750, thru55, thru42, thru5, legs,
    #                        tap750, tap55, tap42, tap5, price
    ("SP2", "2-way splitter", "splitter", 3.9, 3.5, 3.4, 3.3, 1, 3.9, 3.5, 3.4, 3.3, 24.0),
    ("SP3", "3-way splitter (balanced leg + thru)", "splitter", 3.9, 3.5, 3.4, 3.3, 2, 7.4, 7.0, 6.9, 6.8, 29.0),
    ("SP4", "4-way splitter", "splitter", 7.6, 7.1, 7.0, 6.9, 3, 7.6, 7.1, 7.0, 6.9, 32.0),
    ("DC9", "9 dB directional coupler", "dc", 1.6, 1.2, 1.1, 1.0, 1, 9.6, 9.0, 8.8, 8.6, 26.0),
    ("DC12", "12 dB directional coupler", "dc", 1.1, 0.8, 0.7, 0.6, 1, 12.6, 12.0, 11.8, 11.6, 26.0),
    ("DC16", "16 dB directional coupler", "dc", 0.8, 0.5, 0.5, 0.4, 1, 16.6, 16.0, 15.8, 15.6, 26.0),
    ("PI", "power inserter", "power_inserter", 0.6, 0.3, 0.3, 0.2, 0, 0, 0, 0, 0, 41.0),
    ("SPL", "splice / in-line connector", "passive", 0.2, 0.1, 0.1, 0.1, 0, 0, 0, 0, 0, 7.0),
]


def couplers() -> CouplersSpec:
    rows = []
    for (cid, desc, kind, t750, t55, t42, t5, legs,
         p750, p55, p42, p5, price) in COUPLER_DATA:
        rows.append(Coupler(
            id=cid, description=desc, part_number=cid, kind=kind,
            thru_loss={F1: t750, F2: t55, R1: t42, R2: t5},
            tap_legs=legs,
            tap_loss=({F1: p750, F2: p55, R1: p42, R2: p5} if legs else {}),
            max_amps=15.0, resistance=0.05,
            power_passing=True, power_block=False,
            price=price, labor=9.0,
        ))
    # a power blocking coupler used to bound a powering area
    rows.append(Coupler(
        id="PB", description="AC power block", part_number="PB", kind="passive",
        thru_loss={F1: 0.4, F2: 0.2, R1: 0.2, R2: 0.2}, tap_legs=0,
        max_amps=15.0, resistance=0.0, power_passing=False, power_block=True,
        price=19.0, labor=9.0,
    ))
    return CouplersSpec(name="generic750",
                        description="splitters, directional couplers, passives",
                        rows=rows)


# ---------------------------------------------------------------------------
# actives
# ---------------------------------------------------------------------------
def cable_equalizers(values=(0, 3, 6, 9, 12, 15, 18, 21, 24), flat=0.5):
    """Plug-in cable equalizers: flat insertion loss plus *value* dB of slope."""
    out = []
    for v in values:
        out.append(Equalizer(
            value=float(v),
            loss={F1: flat, F2: flat + v, R1: flat, R2: flat},
            part_number=f"EQ{v:02d}",
        ))
    return out


def return_equalizers(values=(0, 3, 6, 9), flat=0.5):
    out = []
    for v in values:
        out.append(Equalizer(
            value=float(v),
            loss={R1: flat, R2: flat + v, F1: flat, F2: flat},
            part_number=f"REQ{v:02d}",
        ))
    return out


PADS = [0, 1, 2, 3, 4, 5, 6, 8, 10, 12, 14, 16, 18, 21]


def actives() -> ActivesSpec:
    rows = [
        Active(
            id="ND-750", description="1 GHz optical node, 2 RF outputs",
            part_number="ND750-2X", category="node",
            gain={}, design_output={F1: 50.0, F2: 39.0},
            module_input={F1: 0.0, F2: 0.0}, housing_offset=0.0,
            noise_figure={}, 
            distortions={
                "CN": Distortion(base=51.0), "CTB": Distortion(base=65.0),
                "CSO": Distortion(base=62.0), "XMOD": Distortion(base=65.0),
            },
            pads=list(PADS), equalizers=cable_equalizers(),
            outputs=[OutputPort("OUT1", {F1: 3.9, F2: 3.5, R1: 3.4, R2: 3.3}),
                     OutputPort("OUT2", {F1: 3.9, F2: 3.5, R1: 3.4, R2: 3.3})],
            return_capable=True,
            rtn_gain={R1: 0.0, R2: 0.0},
            rtn_design_output={R1: 0.0, R2: 0.0},
            rtn_module_input={R1: 16.0, R2: 16.0},
            rtn_noise_figure={R1: 8.0, R2: 8.0},
            rtn_distortions={"RCN": Distortion(base=48.0)},
            rtn_pads=list(PADS), rtn_equalizers=return_equalizers(),
            va_pairs=[[40, 2.60], [60, 1.75], [75, 1.42], [90, 1.20]],
            max_amps=15.0, power_passing=True, min_voltage=40.0,
            price=2450.0, labor=180.0,
        ),
        Active(
            id="TA-750", description="750 MHz trunk amplifier",
            part_number="TA750", category="trunk",
            gain={F1: 30.0, F2: 28.0},
            design_output={F1: 34.0, F2: 25.0},
            module_input={F1: 12.0, F2: 0.0}, housing_offset=3.0,
            noise_figure={F1: 7.5, F2: 7.5},
            distortions={
                "CTB": Distortion(base=79.0, ref_level=34.0),
                "CSO": Distortion(base=76.0, ref_level=34.0),
                "XMOD": Distortion(base=77.0, ref_level=34.0),
            },
            pads=list(PADS), equalizers=cable_equalizers(),
            outputs=[OutputPort("OUT", {})],
            return_capable=True,
            rtn_gain={R1: 18.0, R2: 18.0},
            rtn_design_output={R1: 32.0, R2: 32.0},
            rtn_module_input={R1: 14.0, R2: 14.0},
            rtn_noise_figure={R1: 8.0, R2: 8.0},
            rtn_distortions={"RCN": Distortion(base=60.0, ref_level=14.0)},
            rtn_pads=list(PADS), rtn_equalizers=return_equalizers(),
            va_pairs=[[40, 1.35], [60, 0.92], [75, 0.75], [90, 0.63]],
            max_amps=15.0, power_passing=True, min_voltage=40.0,
            price=1180.0, labor=95.0,
        ),
        Active(
            id="BR-750", description="750 MHz bridger, 4 distribution outputs",
            part_number="BR750-4X", category="bridger",
            gain={F1: 34.0, F2: 32.0},
            design_output={F1: 50.0, F2: 41.0},
            module_input={F1: 16.5, F2: 16.5}, housing_offset=3.0,
            noise_figure={F1: 9.0, F2: 9.0},
            distortions={
                "CTB": Distortion(base=71.0, ref_level=50.0),
                "CSO": Distortion(base=68.0, ref_level=50.0),
                "XMOD": Distortion(base=70.0, ref_level=50.0),
            },
            pads=list(PADS), equalizers=cable_equalizers(),
            outputs=[OutputPort("OUT1", {F1: 7.6, F2: 7.1, R1: 7.0, R2: 6.9}),
                     OutputPort("OUT2", {F1: 7.6, F2: 7.1, R1: 7.0, R2: 6.9}),
                     OutputPort("OUT3", {F1: 7.6, F2: 7.1, R1: 7.0, R2: 6.9}),
                     OutputPort("OUT4", {F1: 7.6, F2: 7.1, R1: 7.0, R2: 6.9})],
            return_capable=True,
            rtn_gain={R1: 20.0, R2: 20.0},
            rtn_design_output={R1: 34.0, R2: 34.0},
            rtn_module_input={R1: 14.0, R2: 14.0},
            rtn_noise_figure={R1: 8.5, R2: 8.5},
            rtn_distortions={"RCN": Distortion(base=58.0, ref_level=14.0)},
            rtn_pads=list(PADS), rtn_equalizers=return_equalizers(),
            va_pairs=[[40, 1.65], [60, 1.12], [75, 0.90], [90, 0.76]],
            max_amps=15.0, power_passing=True, min_voltage=40.0,
            price=1420.0, labor=110.0,
        ),
        Active(
            id="LE-750", description="750 MHz line extender",
            part_number="LE750", category="line_extender",
            gain={F1: 34.0, F2: 32.0},
            design_output={F1: 46.0, F2: 37.0},
            module_input={F1: 16.5, F2: 16.5}, housing_offset=3.0,
            noise_figure={F1: 9.0, F2: 9.0},
            distortions={
                "CTB": Distortion(base=73.0, ref_level=46.0),
                "CSO": Distortion(base=70.0, ref_level=46.0),
                "XMOD": Distortion(base=72.0, ref_level=46.0),
            },
            pads=list(PADS), equalizers=cable_equalizers(),
            outputs=[OutputPort("OUT", {})],
            return_capable=True,
            rtn_gain={R1: 20.0, R2: 20.0},
            rtn_design_output={R1: 32.0, R2: 32.0},
            rtn_module_input={R1: 12.0, R2: 12.0},
            rtn_noise_figure={R1: 9.0, R2: 9.0},
            rtn_distortions={"RCN": Distortion(base=57.0, ref_level=12.0)},
            rtn_pads=list(PADS), rtn_equalizers=return_equalizers(),
            va_pairs=[[40, 0.95], [60, 0.65], [75, 0.53], [90, 0.45]],
            max_amps=15.0, power_passing=True, min_voltage=40.0,
            price=760.0, labor=85.0,
        ),
    ]
    return ActivesSpec(name="generic750",
                       description="node, trunk, bridger and line extender",
                       rows=rows)


# ---------------------------------------------------------------------------
# performance and pricing
# ---------------------------------------------------------------------------
def performance() -> PerformanceSpec:
    spec = PerformanceSpec.default()
    spec.name = "generic750"
    spec.description = "carrier/noise, CTB, CSO, cross-modulation, return C/N"
    return spec


def pricing() -> PricingSpec:
    rows = [
        PriceItem(id="PS-90-15", part_number="PS9015", category="power",
                  description="90 V 15 A ferroresonant power supply",
                  material=1850.0, labor=240.0),
        PriceItem(id="PED", part_number="PED24", category="construction",
                  description="24 inch pedestal", material=64.0, labor=45.0),
        PriceItem(id="STRAND", part_number="STR", category="construction",
                  description="messenger strand", unit="foot",
                  material=0.18, labor=0.42),
    ]
    return PricingSpec(name="generic750", description="material and labour",
                       rows=rows)




def generic750() -> SpecSet:
    """The complete generic spec set."""
    return SpecSet(
        parameters=parameters(), cables=cables(), taps=taps(),
        couplers=couplers(), actives=actives(), performance=performance(),
        pricing=pricing(), name="generic750",
    )
