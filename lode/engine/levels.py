"""Forward and return signal level cascade.

This is the calculation the Design Assistant runs every time anything in the
network changes ("instant recalculations of what-if scenarios").

Forward path
------------
Levels march away from the source.  Cable subtracts ``atten x length / 100``
at every column, passives subtract their tabulated losses, and each active
re-establishes its design output level by way of a plug-in **pad** and
**equalizer** chosen by the engine.

Because a pad is flat and an equalizer is sloped, two frequencies are enough
to solve for both -- which is exactly why "two forward and two return
frequencies are required for the Design Assistant to select forward and return
equalizer values correctly".  With module input levels ``i``, module gain
``g``, pad ``p`` and equalizer loss ``e`` at the high (``h``) and low (``l``)
design frequencies, the module output is::

    o_h = i_h + g_h - p - e_h
    o_l = i_l + g_l - p - e_l

Subtracting removes the pad and leaves a single equation in the equalizer::

    e_h - e_l = (i_h - i_l) + (g_h - g_l) - (o_h - o_l)

The engine picks the stocked equalizer closest to that slope -- honouring
"Allow Over Equalization", which decides whether an equalizer that overshoots
the required slope may be used -- then back-substitutes for the pad.

Return path
-----------
The return is designed against each active's *fixed* module input
requirement.  Working outward from every active, the engine accumulates the
return losses down to each tap and reports the level a subscriber device must
transmit into that tap port for the amplifier to see its required input.  That
number has a **maximum** (a modem can only shout so loud), which is why "the
return input to a tap can rise above the maximum before it is flagged as red".

Between actives the reverse is true: the downstream amplifier's return output
is fixed, so the surplus arriving at the upstream amplifier is taken up by a
return pad.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from ..network import Network
from ..specs import SpecSet, lookup
from ..specs.actives import Active, Equalizer

OK, WARN, ERROR = "ok", "warn", "error"


# ---------------------------------------------------------------------------
# results
# ---------------------------------------------------------------------------

@dataclass
class Flag:
    """A design violation, mirroring the red / yellow colouring on screen."""

    severity: str = WARN
    code: str = ""
    location: str = ""
    label: str = ""
    column: str = ""
    message: str = ""
    value: float | None = None
    limit: float | None = None

    def to_dict(self) -> dict:
        return {
            "severity": self.severity, "code": self.code,
            "location": self.location, "label": self.label,
            "column": self.column, "message": self.message,
            "value": None if self.value is None else round(self.value, 2),
            "limit": None if self.limit is None else round(self.limit, 2),
        }


@dataclass
class LocationResult:
    """Everything the engine knows about one location."""

    id: str = ""
    label: str = ""
    kind: str = "point"
    device: str = ""
    #: forward level arriving at the location (end of the incoming cable --
    #: the *housing* level for an active)
    fwd_in: dict = field(default_factory=dict)
    #: forward level leaving each output port
    fwd_ports: dict = field(default_factory=dict)
    #: return level required at each output port (looking downstream)
    rtn_ports: dict = field(default_factory=dict)
    #: forward level at each subscriber tap port
    fwd_tap: dict = field(default_factory=dict)
    #: return level that must arrive at this location's upstream side
    rtn_req: dict = field(default_factory=dict)
    #: return level a subscriber must transmit into a tap port
    rtn_tap: dict = field(default_factory=dict)
    #: selected plug-ins
    pad: float | None = None
    eq: float | None = None
    eq_loss: dict = field(default_factory=dict)
    rtn_pad: float | None = None
    rtn_eq: float | None = None
    #: module levels for an active
    module_in: dict = field(default_factory=dict)
    module_out: dict = field(default_factory=dict)
    rtn_module_in: dict = field(default_factory=dict)
    rtn_out_housing: dict = field(default_factory=dict)
    #: return surplus over the upstream amplifier's requirement (pad material)
    rtn_surplus: dict = field(default_factory=dict)
    #: span feeding this location
    span_loss: dict = field(default_factory=dict)
    cable: str = ""
    length: float = 0.0
    units: int = 0
    #: worst status of any flag raised here
    status: str = OK
    flags: list = field(default_factory=list)
    #: cascade position, counted in actives from the source
    cascade: int = 0

    def to_dict(self) -> dict:
        def r(d):
            return {k: round(v, 2) for k, v in d.items()}
        return {
            "id": self.id, "label": self.label, "kind": self.kind,
            "device": self.device, "fwd_in": r(self.fwd_in),
            "fwd_ports": {p: r(v) for p, v in self.fwd_ports.items()},
            "fwd_tap": r(self.fwd_tap), "rtn_req": r(self.rtn_req),
            "rtn_tap": r(self.rtn_tap), "pad": self.pad, "eq": self.eq,
            "rtn_pad": self.rtn_pad, "rtn_eq": self.rtn_eq,
            "module_in": r(self.module_in), "module_out": r(self.module_out),
            "rtn_module_in": r(self.rtn_module_in),
            "rtn_surplus": r(self.rtn_surplus),
            "span_loss": r(self.span_loss), "cable": self.cable,
            "length": self.length, "units": self.units,
            "status": self.status, "cascade": self.cascade,
            "flags": [f.to_dict() for f in self.flags],
        }


@dataclass
class Solution:
    """The calculated state of a whole network."""

    results: dict = field(default_factory=dict)
    flags: list = field(default_factory=list)
    order: list = field(default_factory=list)
    forward_columns: list = field(default_factory=list)
    return_columns: list = field(default_factory=list)

    def __getitem__(self, loc_id: str) -> LocationResult:
        return self.results[loc_id]

    def get(self, loc_id: str) -> LocationResult | None:
        return self.results.get(loc_id)

    @property
    def errors(self) -> list:
        return [f for f in self.flags if f.severity == ERROR]

    @property
    def warnings(self) -> list:
        return [f for f in self.flags if f.severity == WARN]

    @property
    def status(self) -> str:
        if self.errors:
            return ERROR
        if self.warnings:
            return WARN
        return OK

    def taps(self) -> list:
        return [self.results[i] for i in self.order
                if self.results[i].kind == "tap"]

    def actives(self) -> list:
        return [self.results[i] for i in self.order
                if self.results[i].kind in ("active", "source")]

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "order": self.order,
            "forward_columns": self.forward_columns,
            "return_columns": self.return_columns,
            "results": {k: v.to_dict() for k, v in self.results.items()},
            "flags": [f.to_dict() for f in self.flags],
        }


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def classify(value: float, low: float | None, high: float | None,
             margin: float) -> str:
    """Green / yellow / red, using the Parameters file's *Set Margin*.

    "Sets how far a tap has to be out of spec before being displayed red.  If
    a tap is less than the margin value out of spec, it will be displayed in
    yellow."
    """
    if low is not None and value < low:
        return WARN if (low - value) < margin else ERROR
    if high is not None and value > high:
        return WARN if (value - high) < margin else ERROR
    return OK


def select_pad_eq(active: Active, module_in: dict, params, direction: str = "forward",
                  pad_override: float | None = None,
                  eq_override: float | None = None) -> tuple[float, Equalizer, dict]:
    """Choose the plug-in pad and equalizer for one amplifier module.

    Returns ``(pad, equalizer, diagnostics)``.  See the module docstring for
    the two-frequency solve this implements.
    """
    if direction == "return":
        col_h, col_l = params.rtn_eq_high, params.rtn_eq_low
    else:
        col_h, col_l = params.fwd_eq_high, params.fwd_eq_low

    gain = active.gains(direction)
    target = active.targets(direction)
    pads = active.pad_values(direction)
    eqs = active.eq_list(direction)

    in_h = module_in.get(col_h, 0.0)
    in_l = module_in.get(col_l, 0.0)
    g_h, g_l = lookup(gain, col_h), lookup(gain, col_l)
    t_h, t_l = lookup(target, col_h), lookup(target, col_l)

    required = (in_h - in_l) + (g_h - g_l) - (t_h - t_l)

    if eq_override is not None:
        chosen = min(eqs, key=lambda e: abs(e.value - eq_override))
    else:
        candidates = eqs
        if not params.allow_over_equalization:
            # an equalizer that slopes harder than required over-equalizes
            under = [e for e in eqs if (e.at(col_h) - e.at(col_l)) >= required]
            candidates = under or eqs
        chosen = min(
            candidates,
            key=lambda e: (abs((e.at(col_h) - e.at(col_l)) - required), e.value),
        )

    eq_h = chosen.at(col_h)
    raw_pad = in_h + g_h - eq_h - t_h
    if pad_override is not None:
        pad = min(pads, key=lambda p: abs(p - pad_override))
    else:
        pad = min(pads, key=lambda p: (abs(p - raw_pad), p))

    diagnostics = {
        "required_slope": required,
        "actual_slope": eq_h - chosen.at(col_l),
        "raw_pad": raw_pad,
        "pad_error": pad - raw_pad,
        "pad_floor": raw_pad < min(pads) - 1e-9,
        "pad_ceiling": raw_pad > max(pads) + 1e-9,
    }
    return pad, chosen, diagnostics


# ---------------------------------------------------------------------------
# engine
# ---------------------------------------------------------------------------

class LevelEngine:
    """Calculates forward and return levels for a network against a spec set."""

    def __init__(self, specs: SpecSet, network: Network):
        self.specs = specs
        self.network = network
        self.params = specs.parameters

    # -- lookups ---------------------------------------------------------
    def cable(self, ident: str):
        row = self.specs.cables.by_id(ident)
        if row is None and ident:
            raise KeyError(f"cable {ident!r} is not in the cables spec file")
        return row

    def device_of(self, loc):
        if loc.kind == "tap":
            return self.specs.taps.by_id(loc.device)
        if loc.kind == "coupler":
            return self.specs.couplers.by_id(loc.device)
        if loc.kind in ("active", "source"):
            return self.specs.actives.by_id(loc.device)
        return None

    # -- span loss -------------------------------------------------------
    def span_loss(self, span) -> dict:
        cable = self.cable(span.cable) if span.cable else None
        factor = self.params.cable_loss_factor
        conn = self.params.connector_loss * max(0, span.connectors)
        out = {}
        for col in self.params.all_columns:
            base = cable.loss(col, span.length, factor) if cable else 0.0
            out[col] = base + span.extra_loss + conn
        return out

    # -- main ------------------------------------------------------------
    def solve(self) -> Solution:
        params = self.params
        net = self.network
        sol = Solution(
            forward_columns=list(params.forward_columns),
            return_columns=list(params.return_columns),
        )

        source_id = net.source_id
        if not source_id:
            sol.flags.append(Flag(ERROR, "no-source", "", "", "",
                                  "the network has no source"))
            return sol

        # required return input at each active, keyed by location id
        rtn_required: dict[str, dict] = {}

        for loc, span in net.walk():
            res = LocationResult(
                id=loc.id, label=loc.display(), kind=loc.kind,
                device=loc.device, units=loc.units,
            )
            sol.results[loc.id] = res
            sol.order.append(loc.id)

            # ---------------- incoming span --------------------------
            if span is None:
                parent_res = None
                res.fwd_in = {}
                res.rtn_req = {}
                res.cascade = 0
            else:
                parent_res = sol.results[span.parent]
                res.cascade = parent_res.cascade
                res.cable = span.cable
                res.length = span.length
                loss = self.span_loss(span)
                res.span_loss = loss
                port_levels = parent_res.fwd_ports.get(span.port)
                if port_levels is None:
                    port_levels = (
                        next(iter(parent_res.fwd_ports.values()), {})
                        if parent_res.fwd_ports else {}
                    )
                res.fwd_in = {
                    col: port_levels.get(col, 0.0) - loss.get(col, 0.0)
                    for col in params.forward_columns
                }
                parent_rtn = parent_res.rtn_ports.get(
                    span.port,
                    next(iter(parent_res.rtn_ports.values()), parent_res.rtn_req),
                )
                res.rtn_req = {
                    col: parent_rtn.get(col, 0.0) + loss.get(col, 0.0)
                    for col in params.return_columns
                }

            self._apply_device(loc, res, sol, rtn_required)
            self._check_location(loc, res, sol)

        return sol

    # ------------------------------------------------------------------
    def _apply_device(self, loc, res: LocationResult, sol: Solution,
                      rtn_required: dict) -> None:
        params = self.params
        fwd_cols = params.forward_columns
        rtn_cols = params.return_columns
        device = self.device_of(loc)
        res.rtn_ports = {}

        if loc.kind in ("active", "source"):
            if device is None:
                sol.flags.append(Flag(
                    ERROR, "missing-active", loc.id, loc.display(), "",
                    f"active {loc.device!r} is not in the actives spec file"))
                res.fwd_ports = {"OUT": dict(res.fwd_in)}
                res.status = ERROR
                return
            self._apply_active(loc, res, sol, device, rtn_required)
            res.cascade += 1
            return

        if loc.kind == "tap":
            if device is None:
                sol.flags.append(Flag(
                    ERROR, "missing-tap", loc.id, loc.display(), "",
                    f"tap {loc.device!r} is not in the taps spec file"))
                res.fwd_ports = {"THRU": dict(res.fwd_in)}
                res.status = ERROR
                return
            res.fwd_tap = {
                col: res.fwd_in.get(col, 0.0) - device.port_loss(col)
                for col in fwd_cols
            }
            res.rtn_tap = {
                col: res.rtn_req.get(col, 0.0) + device.port_loss(col)
                for col in rtn_cols
            }
            if not device.self_terminating:
                res.fwd_ports = {"THRU": {
                    col: res.fwd_in.get(col, 0.0) - device.thru_loss(col)
                    for col in fwd_cols
                }}
                res.rtn_ports = {"THRU": {
                    col: res.rtn_req.get(col, 0.0) + device.thru_loss(col)
                    for col in rtn_cols
                }}
            else:
                res.fwd_ports = {}
            return

        if loc.kind == "coupler":
            if device is None:
                sol.flags.append(Flag(
                    ERROR, "missing-coupler", loc.id, loc.display(), "",
                    f"coupler {loc.device!r} is not in the couplers spec file"))
                res.fwd_ports = {"THRU": dict(res.fwd_in)}
                res.status = ERROR
                return
            for leg in range(device.legs):
                name = device.leg_name(leg)
                res.fwd_ports[name] = {
                    col: res.fwd_in.get(col, 0.0) - device.leg_loss(col, leg)
                    for col in fwd_cols
                }
                res.rtn_ports[name] = {
                    col: res.rtn_req.get(col, 0.0) + device.leg_loss(col, leg)
                    for col in rtn_cols
                }
            return

        # point, end, power supply: signal passes straight through
        res.fwd_ports = {"THRU": dict(res.fwd_in)}
        res.rtn_ports = {"THRU": dict(res.rtn_req)}

    # ------------------------------------------------------------------
    def _apply_active(self, loc, res: LocationResult, sol: Solution,
                      device: Active, rtn_required: dict) -> None:
        params = self.params
        fwd_cols = params.forward_columns
        rtn_cols = params.return_columns
        offset = float(device.housing_offset)

        # ---- forward -----------------------------------------------
        if loc.kind == "source" or not res.fwd_in:
            # a source simply launches its design output
            res.module_in = {col: lookup(device.module_input, col) for col in fwd_cols}
            res.module_out = {col: lookup(device.design_output, col) for col in fwd_cols}
            res.pad = None
            res.eq = None
        else:
            res.module_in = {
                col: res.fwd_in.get(col, 0.0) - offset for col in fwd_cols
            }
            pad, eq, diag = select_pad_eq(
                device, res.module_in, params, "forward",
                pad_override=loc.pad, eq_override=loc.eq,
            )
            res.pad = pad
            res.eq = eq.value
            res.eq_loss = {col: eq.at(col) for col in fwd_cols}
            res.module_out = {
                col: res.module_in.get(col, 0.0) + lookup(device.gain, col)
                     - pad - eq.at(col)
                for col in fwd_cols
            }
            self._flag_pad(loc, res, sol, device, diag, "forward")

        for port in device.outputs:
            res.fwd_ports[port.name] = {
                col: res.module_out.get(col, 0.0) - port.at(col)
                for col in fwd_cols
            }

        # ---- return -------------------------------------------------
        if rtn_cols and device.return_capable:
            required_module_in = {
                col: lookup(device.rtn_module_input, col) for col in rtn_cols
            }
            res.rtn_module_in = required_module_in
            required_housing = {
                col: required_module_in.get(col, 0.0) + offset for col in rtn_cols
            }
            rtn_required[loc.id] = required_housing

            # the level this amplifier delivers upstream, at its housing port
            res.rtn_out_housing = {
                col: lookup(device.rtn_design_output, col) - offset
                for col in rtn_cols
            }
            # what the upstream amplifier asked for is already in res.rtn_req
            if res.rtn_req:
                res.rtn_surplus = {
                    col: res.rtn_out_housing.get(col, 0.0) - res.rtn_req.get(col, 0.0)
                    for col in rtn_cols
                }
                pads = device.pad_values("return")
                col_h = params.rtn_eq_high
                surplus = res.rtn_surplus.get(col_h, 0.0)
                if loc.rtn_pad is not None:
                    res.rtn_pad = min(pads, key=lambda p: abs(p - loc.rtn_pad))
                else:
                    res.rtn_pad = min(pads, key=lambda p: (abs(p - surplus), p))
            # every downstream port starts a fresh return requirement
            for port in device.outputs:
                res.rtn_ports[port.name] = {
                    col: required_housing.get(col, 0.0) + port.at(col)
                    for col in rtn_cols
                }
            _, rtn_eq, rtn_diag = select_pad_eq(
                device, required_module_in, params, "return",
                eq_override=loc.rtn_eq,
            )
            res.rtn_eq = rtn_eq.value
        else:
            for port in device.outputs:
                res.rtn_ports[port.name] = dict(res.rtn_req)

    # ------------------------------------------------------------------
    def _flag_pad(self, loc, res, sol, device, diag, direction) -> None:
        params = self.params
        if diag["pad_floor"]:
            self._flag(sol, res, Flag(
                ERROR, "under-driven", loc.id, loc.display(),
                params.fwd_eq_high,
                f"{loc.display()}: input is {abs(diag['raw_pad']):.1f} dB short of "
                f"the drive needed for the design output "
                f"(minimum pad {min(device.pad_values(direction)):g} dB)",
                value=diag["raw_pad"]))
        elif diag["pad_ceiling"]:
            self._flag(sol, res, Flag(
                WARN, "over-driven", loc.id, loc.display(), params.fwd_eq_high,
                f"{loc.display()}: input is {diag['raw_pad'] - max(device.pad_values(direction)):.1f} dB "
                f"hotter than the largest stocked pad",
                value=diag["raw_pad"]))
        slope_err = abs(diag["actual_slope"] - diag["required_slope"])
        if slope_err > 2.0:
            self._flag(sol, res, Flag(
                WARN, "equalization", loc.id, loc.display(), "",
                f"{loc.display()}: no stocked equalizer matches the required "
                f"slope (off by {slope_err:.1f} dB)",
                value=diag["actual_slope"], limit=diag["required_slope"]))

    # ------------------------------------------------------------------
    def _check_location(self, loc, res: LocationResult, sol: Solution) -> None:
        params = self.params
        margin = params.set_margin

        # -- tap sizing and termination, as the Design Assistant tests them --
        if loc.kind == "tap":
            tap = self.specs.taps.by_id(loc.device)
            children = self.network.children(loc.id)
            if tap is not None:
                if params.check_tap_ports and loc.units > tap.ports:
                    self._flag(sol, res, Flag(
                        ERROR, "not-enough-taps", loc.id, loc.display(), "",
                        f"tap {loc.display()}: {loc.units} unit(s) on a "
                        f"{tap.ports}-port tap -- {loc.units - tap.ports} "
                        f"drop(s) cannot be served",
                        value=loc.units, limit=tap.ports))
                # "Invalid terminating tap used"
                if tap.self_terminating and children:
                    self._flag(sol, res, Flag(
                        ERROR, "invalid-terminating-tap", loc.id, loc.display(),
                        "",
                        f"tap {loc.display()}: {tap.id} is self-terminating "
                        f"but the line continues past it",
                        value=len(children)))
                elif not tap.self_terminating and not children:
                    self._flag(sol, res, Flag(
                        WARN, "unterminated", loc.id, loc.display(), "",
                        f"tap {loc.display()}: end of line on a through tap -- "
                        f"a terminator or a self-terminating tap is needed"))

        # forward crossover -- flagged only where the limit is first crossed,
        # which is where an in-line equalizer belongs
        if len(params.forward_columns) >= 2 and res.fwd_in:
            high = res.fwd_in.get(params.fwd_eq_high)
            low = res.fwd_in.get(params.fwd_eq_low)
            if high is not None and low is not None:
                crossover = low - high
                parent_id = self.network.parent_of(loc.id)
                parent_res = sol.results.get(parent_id) if parent_id else None
                parent_crossover = -1e9
                if parent_res is not None and parent_res.fwd_in:
                    parent_crossover = (
                        parent_res.fwd_in.get(params.fwd_eq_low, 0.0)
                        - parent_res.fwd_in.get(params.fwd_eq_high, 0.0)
                    )
                already = parent_crossover > params.max_crossover
                if crossover > params.max_crossover and not already:
                    self._flag(sol, res, Flag(
                        WARN, "crossover", loc.id, loc.display(), "",
                        f"{loc.display()}: forward low exceeds forward high by "
                        f"{crossover:.1f} dB -- an in-line equalizer is called for",
                        value=crossover, limit=params.max_crossover))

        if loc.kind == "tap" and res.fwd_tap:
            for col in params.forward_columns:
                low = params.min_tap_level(col)
                if low is None:
                    continue
                high = params.max_tap_level(col) if params.enforce_tap_window else None
                value = res.fwd_tap[col]
                status = classify(value, low, high, margin)
                if status != OK:
                    limit = low if value < low else high
                    self._flag(sol, res, Flag(
                        status, "tap-level", loc.id, loc.display(), col,
                        f"tap {loc.display()} port level {value:.1f} dBmV at "
                        f"{params.label(col)} is outside the "
                        f"{low:.1f}"
                        + (f"..{high:.1f}" if high is not None else "+")
                        + " dBmV window",
                        value=value, limit=limit))

        if loc.kind == "tap" and res.rtn_tap:
            for col in params.return_columns:
                high = params.max_return_level(col)
                if high is None:
                    continue
                value = res.rtn_tap[col]
                status = classify(value, None, high, margin)
                if status != OK:
                    self._flag(sol, res, Flag(
                        status, "return-tap-level", loc.id, loc.display(), col,
                        f"tap {loc.display()} needs {value:.1f} dBmV of return "
                        f"drive at {params.label(col)}, above the {high:.1f} dBmV "
                        f"maximum",
                        value=value, limit=high))

        # "LE X/N before/M after" -- the maximum line extender cascade
        if loc.kind == "active" and params.max_le_cascade:
            device = self.device_of(loc)
            if device is not None and device.category == "line_extender":
                run = 0
                for ident in reversed(self.network.path_to(loc.id)):
                    other = self.network.locations[ident]
                    if not other.is_active:
                        continue
                    spec = self.specs.actives.by_id(other.device)
                    if spec is None or spec.category != "line_extender":
                        break
                    run += 1
                if run > params.max_le_cascade:
                    self._flag(sol, res, Flag(
                        ERROR, "le-cascade", loc.id, loc.display(), "",
                        f"{loc.display()}: {run} line extenders in cascade, "
                        f"above the maximum of {params.max_le_cascade}",
                        value=run, limit=params.max_le_cascade))

        # "Unused LE placed" -- an amplifier that feeds nothing
        if loc.kind == "active" and not self.network.children(loc.id):
            self._flag(sol, res, Flag(
                WARN, "unused-active", loc.id, loc.display(), "",
                f"{loc.display()}: amplifier placed but nothing is fed from it"))

        if loc.kind == "active" and res.fwd_in:
            device = self.device_of(loc)
            if device is not None:
                for col in (params.fwd_eq_high,):
                    need = device.housing_input_min(col)
                    value = res.fwd_in.get(col, 0.0)
                    if value < need:
                        status = WARN if (need - value) < margin else ERROR
                        self._flag(sol, res, Flag(
                            status, "housing-input", loc.id, loc.display(), col,
                            f"{loc.display()}: housing input {value:.1f} dBmV is "
                            f"below the {need:.1f} dBmV minimum for {device.id}",
                            value=value, limit=need))
                if res.rtn_surplus:
                    col = params.rtn_eq_high
                    surplus = res.rtn_surplus.get(col, 0.0)
                    if surplus < -margin:
                        self._flag(sol, res, Flag(
                            ERROR, "return-short", loc.id, loc.display(), col,
                            f"{loc.display()}: return output arrives "
                            f"{abs(surplus):.1f} dB below what the upstream "
                            f"amplifier requires",
                            value=surplus, limit=0.0))

    # ------------------------------------------------------------------
    @staticmethod
    def _flag(sol: Solution, res: LocationResult, flag: Flag) -> None:
        sol.flags.append(flag)
        res.flags.append(flag)
        if flag.severity == ERROR or (flag.severity == WARN and res.status == OK):
            res.status = flag.severity
