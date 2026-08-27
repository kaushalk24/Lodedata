"""The design optimisation tools.

"The Design mode/menu contains many powerful design optimization tools."
These are the ones that do the real work:

``auto_ports``      size every tap from the house count using the Parameters
                    file's Homes / Number of Ports table
``auto_taps``       choose the tap *value* at every location -- the highest
                    value in the tap selection group that still meets the
                    minimum tap output, which is what leaves the most signal
                    for the rest of the line
``self_terminate``  swap the last tap on each leg for its self-terminating
                    equivalent
``rebalance``       drop manual pad and equalizer overrides so every active is
                    re-balanced by the engine
``suggest_actives`` report where the line runs out of signal and an amplifier
                    is called for

Tap selection is iterative: changing a tap changes the level reaching every
tap below it.  Choosing the highest feasible value only ever *raises* the
downstream level (a higher tap value has a lower insertion loss), so the
process is monotone and settles in a handful of passes.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..network import Network
from ..specs import SpecSet
from .levels import LevelEngine, Solution


@dataclass
class Change:
    location: str = ""
    label: str = ""
    field: str = ""
    old: object = None
    new: object = None
    reason: str = ""

    def to_dict(self) -> dict:
        return {
            "location": self.location, "label": self.label,
            "field": self.field, "old": self.old, "new": self.new,
            "reason": self.reason,
        }


@dataclass
class DesignRun:
    changes: list = field(default_factory=list)
    passes: int = 0
    solution: Solution | None = None
    notes: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "changes": [c.to_dict() for c in self.changes],
            "passes": self.passes,
            "notes": self.notes,
        }


class AutoDesigner:
    def __init__(self, specs: SpecSet, network: Network):
        self.specs = specs
        self.network = network
        self.params = specs.parameters

    def solve(self) -> Solution:
        return LevelEngine(self.specs, self.network).solve()

    # ------------------------------------------------------------------
    def auto_ports(self) -> list:
        """Size every tap from its house count."""
        changes = []
        for loc in self.network.locations.values():
            if loc.kind != "tap" or loc.locked:
                continue
            wanted = loc.tap_ports or self.params.ports_for_homes(loc.units)
            tap = self.specs.taps.by_id(loc.device)
            if tap is None:
                continue
            if tap.ports == wanted:
                continue
            tsg = loc.tsg or self.params.default_tsg
            available = self.specs.taps.port_counts(tsg)
            if not available:
                continue
            target = min(available, key=lambda p: (abs(p - wanted), -p))
            replacement = self._same_value_other_ports(tap, tsg, target)
            if replacement is None or replacement.id == loc.device:
                continue
            changes.append(Change(
                loc.id, loc.display(), "device", loc.device, replacement.id,
                f"{loc.units} unit(s) call for a {target}-port tap",
            ))
            loc.device = replacement.id
        return changes

    def _same_value_other_ports(self, tap, tsg: int, ports: int):
        group = self.specs.taps.group(tsg, ports)
        group = [t for t in group if t.self_terminating == tap.self_terminating]
        if not group:
            group = self.specs.taps.group(tsg, ports)
        if not group:
            return None
        return min(group, key=lambda t: abs(t.value - tap.value))

    # ------------------------------------------------------------------
    def auto_taps(self, max_passes: int = 12) -> DesignRun:
        """Choose the tap value at every unlocked tap location."""
        run = DesignRun()
        params = self.params
        columns = [c for c in params.forward_columns
                   if params.min_tap_level(c) is not None]
        if not columns:
            run.notes.append(
                "no minimum tap output is set in the Parameters file, so tap "
                "values cannot be selected automatically"
            )
            run.solution = self.solve()
            return run

        for attempt in range(1, max_passes + 1):
            solution = self.solve()
            run.solution = solution
            run.passes = attempt
            touched = False
            for loc_id in solution.order:
                loc = self.network.locations[loc_id]
                if loc.kind != "tap" or loc.locked:
                    continue
                res = solution.results[loc_id]
                current = self.specs.taps.by_id(loc.device)
                if current is None:
                    continue
                choice = self.choose_tap(
                    res.fwd_in, res.rtn_req,
                    ports=current.ports,
                    tsg=loc.tsg or params.default_tsg,
                    self_terminating=current.self_terminating,
                )
                if choice is not None and choice.id != loc.device:
                    run.changes.append(Change(
                        loc.id, loc.display(), "device", loc.device, choice.id,
                        f"highest value meeting the "
                        f"{params.min_tap_level(columns[0]):.1f} dBmV minimum "
                        f"port output",
                    ))
                    loc.device = choice.id
                    touched = True
            if not touched:
                break
        run.solution = self.solve()
        return run

    # ------------------------------------------------------------------
    def choose_tap(self, fwd_in: dict, rtn_req: dict | None = None,
                   ports: int = 4, tsg: int = 1,
                   self_terminating: bool = False):
        """The tap-selection rule itself.

        Prefers the **highest** tap value whose port output still clears the
        minimum, because a higher value costs less through loss and so leaves
        more signal for the rest of the leg.  When nothing clears the minimum
        the lowest value is returned -- the best that can be done -- and the
        level engine raises the out-of-spec flag.
        """
        params = self.params
        group = [
            t for t in self.specs.taps.group(tsg, ports)
            if t.self_terminating == self_terminating
        ]
        if not group:
            group = self.specs.taps.group(tsg, ports)
        if not group:
            return None

        feasible = []
        for tap in group:
            ok = True
            for col in params.forward_columns:
                low = params.min_tap_level(col)
                if low is None:
                    continue
                level = fwd_in.get(col, 0.0) - tap.port_loss(col)
                if level < low:
                    ok = False
                    break
                if params.enforce_tap_window:
                    high = params.max_tap_level(col)
                    if high is not None and level > high:
                        ok = False
                        break
            if ok and rtn_req:
                for col in params.return_columns:
                    high = params.max_return_level(col)
                    if high is None:
                        continue
                    needed = rtn_req.get(col, 0.0) + tap.port_loss(col)
                    if needed > high:
                        ok = False
                        break
            if ok:
                feasible.append(tap)

        if feasible:
            if params.tap_selection == "lowest_value":
                return min(feasible, key=lambda t: t.value)
            return max(feasible, key=lambda t: t.value)

        # nothing fits: fall back to the gentlest tap available
        return min(group, key=lambda t: t.value)

    # ------------------------------------------------------------------
    def self_terminate(self) -> list:
        """Swap the last tap on each leg for a self-terminating equivalent."""
        changes = []
        net = self.network
        for loc in net.locations.values():
            if loc.kind != "tap" or loc.locked:
                continue
            if net.children(loc.id):
                continue
            tap = self.specs.taps.by_id(loc.device)
            if tap is None or tap.self_terminating:
                continue
            tsg = loc.tsg or self.params.default_tsg
            candidates = [
                t for t in self.specs.taps.group(tsg, tap.ports)
                if t.self_terminating and t.value == tap.value
            ]
            if not candidates:
                continue
            changes.append(Change(
                loc.id, loc.display(), "device", loc.device, candidates[0].id,
                "end of leg -- a self-terminating tap saves a terminator",
            ))
            loc.device = candidates[0].id
        return changes

    # ------------------------------------------------------------------
    def rebalance(self) -> list:
        """Clear manual pad / equalizer overrides so actives re-balance."""
        changes = []
        for loc in self.network.locations.values():
            if loc.kind not in ("active", "source") or loc.locked:
                continue
            for attr in ("pad", "eq", "rtn_pad", "rtn_eq"):
                if getattr(loc, attr) is not None:
                    changes.append(Change(
                        loc.id, loc.display(), attr, getattr(loc, attr), None,
                        "re-balanced by the engine",
                    ))
                    setattr(loc, attr, None)
        return changes

    # ------------------------------------------------------------------
    def suggest_actives(self, solution: Solution | None = None) -> list:
        """Report where the plant runs out of signal.

        "Since you are out of signal, the most logical step is to place an
        amplifier."
        """
        solution = solution or self.solve()
        params = self.params
        column = params.fwd_eq_high
        floor = params.min_tap_level(column)
        suggestions = []
        cheapest = None
        for tap in self.specs.taps.rows:
            if cheapest is None or tap.port_loss(column) < cheapest.port_loss(column):
                cheapest = tap
        gentle_loss = cheapest.port_loss(column) if cheapest else 0.0

        for loc_id in solution.order:
            res = solution.results[loc_id]
            loc = self.network.locations[loc_id]
            if not res.fwd_in:
                continue
            level = res.fwd_in.get(column, 0.0)
            if loc.kind == "active":
                device = self.specs.actives.by_id(loc.device)
                if device and level < device.housing_input_min(column):
                    suggestions.append({
                        "location": loc_id, "label": res.label,
                        "kind": "amplifier-input",
                        "message": (
                            f"{res.label}: {level:.1f} dBmV reaches the "
                            f"{loc.device} housing, {device.housing_input_min(column) - level:.1f} dB "
                            f"short of its minimum -- shorten the span, use a "
                            f"larger cable, or add an amplifier ahead of it"
                        ),
                    })
                continue
            if loc.kind == "tap" and floor is not None:
                if level - gentle_loss < floor:
                    parent = self.network.parent_of(loc_id)
                    parent_label = (
                        solution.results[parent].label if parent else ""
                    )
                    suggestions.append({
                        "location": loc_id, "label": res.label,
                        "kind": "out-of-signal",
                        "message": (
                            f"{res.label}: {level:.1f} dBmV cannot feed any tap "
                            f"in the group and still make {floor:.1f} dBmV -- "
                            f"place a line extender at or before {parent_label or res.label}"
                        ),
                    })
        return suggestions

    # ------------------------------------------------------------------
    def auto_actives(self, device: str = "", max_inserts: int = 40,
                     jumper: float = 0.0) -> list:
        """Place amplifiers wherever the plant runs out of signal.

        Working down the plant, the first tap that cannot make the minimum
        port output with *any* tap in its group means the line is out of
        signal.  The amplifier then goes at the **last** pole above it where
        the level still clears the amplifier's housing input minimum -- put it
        any further along and the amplifier itself is starved.
        """
        params = self.params
        column = params.fwd_eq_high
        floor = params.min_tap_level(column)
        if floor is None:
            return []
        device = device or params.default_active
        spec = self.specs.actives.by_id(device)
        if spec is None:
            candidates = self.specs.actives.by_category("line_extender")
            if not candidates:
                return []
            spec = candidates[0]
            device = spec.id
        needed_input = spec.housing_input_min(column)

        changes = []
        counter = 0
        for _ in range(max_inserts):
            solution = self.solve()
            target = self._first_starved_tap(solution, floor, column)
            if target is None:
                break
            host = self._amplifier_host(solution, target, needed_input, column)
            if host is None:
                break
            counter += 1
            child = self.network.locations[host]
            parent_loc = self.network.locations[
                self.network.parent_of(host) or host
            ]
            new_loc = self.network.insert_before(
                host, jumper=jumper, out_port=spec.outputs[0].name,
                kind="active", device=device,
                label=self._amplifier_label(counter),
                x=(child.x + parent_loc.x) / 2.0,
                y=(child.y + parent_loc.y) / 2.0,
            )
            changes.append(Change(
                new_loc.id, new_loc.display(), "insert", None, device,
                f"line was out of signal at {solution.results[target].label}",
            ))
            # re-select taps now that the levels downstream have changed
            self.auto_taps(max_passes=6)
        return changes

    def _amplifier_label(self, counter: int) -> str:
        used = {loc.label for loc in self.network.locations.values()}
        while True:
            label = f"LE{counter}"
            if label not in used:
                return label
            counter += 1

    def _first_starved_tap(self, solution, floor: float, column: str):
        """The first tap no tap value in its group can serve."""
        params = self.params
        for loc_id in solution.order:
            loc = self.network.locations[loc_id]
            res = solution.results[loc_id]
            if loc.kind == "active":
                spec = self.specs.actives.by_id(loc.device)
                if spec and res.fwd_in.get(column, 0.0) < spec.housing_input_min(column):
                    return loc_id
                continue
            if loc.kind != "tap" or not res.fwd_in:
                continue
            tsg = loc.tsg or params.default_tsg
            tap = self.specs.taps.by_id(loc.device)
            ports = tap.ports if tap else 4
            group = self.specs.taps.group(tsg, ports) or self.specs.taps.group(tsg)
            if not group:
                continue
            gentlest = min(t.port_loss(column) for t in group)
            if res.fwd_in.get(column, 0.0) - gentlest < floor:
                return loc_id
        return None

    def _amplifier_host(self, solution, starved_id: str, needed_input: float,
                        column: str):
        """The location the new amplifier should be inserted in front of."""
        path = self.network.path_to(starved_id)
        # walk back from the starved location looking for the last pole whose
        # incoming level can still drive an amplifier
        for loc_id in reversed(path):
            res = solution.results.get(loc_id)
            if res is None or not res.fwd_in:
                continue
            if self.network.locations[loc_id].kind in ("active", "source"):
                break
            if res.fwd_in.get(column, 0.0) >= needed_input:
                return loc_id
        return None

    # ------------------------------------------------------------------
    def full_design(self, place_actives: bool = True) -> DesignRun:
        """Size, select, terminate and balance in one go."""
        run = DesignRun()
        run.changes.extend(self.rebalance())
        run.changes.extend(self.auto_ports())
        tap_run = self.auto_taps()
        if place_actives:
            run.changes.extend(self.auto_actives())
        run.changes.extend(tap_run.changes)
        run.passes = tap_run.passes
        run.changes.extend(self.self_terminate())
        run.solution = self.solve()
        run.notes.extend(tap_run.notes)
        for hint in self.suggest_actives(run.solution):
            run.notes.append(hint["message"])
        return run
