"""The plant model: locations, spans and the devices that sit on them.

A Design Assistant network is a tree.  Signal leaves a source (a fibre node or
a headend launch amplifier), travels along **spans** of cable between
**locations** -- "the distance, usually between poles or pedestals" -- and at
each location may pass through a device: a tap, a coupler, or an active.  Taps
and couplers with more than one output, and actives with distribution ports,
start new **legs**.

The model here is deliberately explicit: locations own devices, spans own
cable, and every span records *which output port* of its upstream device feeds
it.  That is what makes level, powering and bill-of-material calculations
unambiguous.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Iterator

#: What can sit at a location.
LOCATION_KINDS = (
    "source",         # fibre node / headend launch point
    "active",         # amplifier
    "tap",            # subscriber tap
    "coupler",        # splitter / directional coupler / in-line passive
    "power_supply",   # AC power supply
    "point",          # a bare pole or pedestal: cable passes through
    "end",            # end of line (terminator)
)


class NetworkError(Exception):
    """Raised for structurally invalid plant."""


@dataclass
class PowerSupply:
    """An AC power supply feeding a powering area."""

    id: str = ""
    volts: float = 90.0
    max_amps: float = 15.0
    #: which directions it feeds; empty means every leg at this location
    feeds: list = field(default_factory=list)
    description: str = ""
    price: float = 0.0

    def capacity_watts(self) -> float:
        return self.volts * self.max_amps


@dataclass
class Location:
    """A pole or pedestal, and whatever is mounted on it."""

    id: str = ""
    #: map reference shown on screen and in reports
    label: str = ""
    kind: str = "point"
    #: id of the row in the corresponding spec file (tap id, active id, ...)
    device: str = ""
    #: "the number of units to feed from that span location"
    units: int = 0
    #: tap selection group override (0 = use the parameters default)
    tsg: int = 0
    #: force a port count instead of deriving it from the homes table
    tap_ports: int = 0
    #: a locked device is never changed by the automatic design tools
    locked: bool = False
    #: manual pad / equaliser override for an active
    pad: float | None = None
    eq: float | None = None
    rtn_pad: float | None = None
    rtn_eq: float | None = None
    #: power supply mounted here
    power_supply: PowerSupply | None = None
    #: an AC block stops powering at this point
    power_block: bool = False
    #: "the Sticky Note function allows entry of a text note at any node"
    note: str = ""
    #: canvas position
    x: float = 0.0
    y: float = 0.0
    extra: dict = field(default_factory=dict)

    @property
    def is_active(self) -> bool:
        return self.kind in ("active", "source")

    @property
    def is_tap(self) -> bool:
        return self.kind == "tap"

    def display(self) -> str:
        return self.label or self.id


@dataclass
class Span:
    """A length of cable between two locations."""

    id: str = ""
    parent: str = ""
    child: str = ""
    cable: str = ""
    #: length in the distance units declared by the Parameters file
    length: float = 0.0
    #: output port of the parent device that feeds this span
    port: str = ""
    #: extra fixed loss on this span (jumpers, splices, connectors)
    extra_loss: float = 0.0
    #: number of connector pairs, costed by the parameters' connector loss
    connectors: int = 2
    label: str = ""
    #: name of the leg this span begins, when it begins one ("MAPLE ST", "FL1")
    leg_name: str = ""
    extra: dict = field(default_factory=dict)


@dataclass
class Leg:
    """One linear run of the plant, the unit Design Mode works in."""

    id: str = ""
    #: designer's name for the leg ("MAPLE ST", "FL1")
    name: str = ""
    #: the branching device this leg hangs off ("" for the trunk)
    origin: str = ""
    #: which port of that device
    port: str = ""
    #: the leg containing the origin
    parent_leg: str = ""
    #: the span that begins this leg
    first_span: str = ""
    #: ordered location ids
    locations: list = field(default_factory=list)

    def display(self) -> str:
        return self.name or (f"{self.port}" if self.port else "TRUNK")

    def to_dict(self) -> dict:
        return {
            "id": self.id, "name": self.name, "origin": self.origin,
            "port": self.port, "parent_leg": self.parent_leg,
            "first_span": self.first_span, "locations": self.locations,
            "display": self.display(),
        }


@dataclass
class Network:
    """A complete design: the tree plus its metadata."""

    name: str = "untitled"
    description: str = ""
    #: spec set this network was designed against (informational)
    spec_set: str = ""
    locations: dict = field(default_factory=dict)
    spans: dict = field(default_factory=dict)
    source: str = ""
    _seq: int = 0

    # ------------------------------------------------------------------
    # construction
    # ------------------------------------------------------------------
    def new_id(self, prefix: str) -> str:
        while True:
            self._seq += 1
            candidate = f"{prefix}{self._seq}"
            if candidate not in self.locations and candidate not in self.spans:
                return candidate

    def add_location(self, **kwargs) -> Location:
        loc = Location(**kwargs)
        if not loc.id:
            loc.id = self.new_id("L")
        if loc.id in self.locations:
            raise NetworkError(f"duplicate location id {loc.id!r}")
        if loc.kind not in LOCATION_KINDS:
            raise NetworkError(f"unknown location kind {loc.kind!r}")
        self.locations[loc.id] = loc
        return loc

    def add_span(self, parent: str, child: str, **kwargs) -> Span:
        span = Span(parent=parent, child=child, **kwargs)
        if not span.id:
            span.id = self.new_id("S")
        for end in (parent, child):
            if end not in self.locations:
                raise NetworkError(f"span references unknown location {end!r}")
        if self.feed_span(child) is not None:
            raise NetworkError(
                f"location {child!r} already has a feed; the plant must be a tree"
            )
        self.spans[span.id] = span
        return span

    def insert_before(self, child_id: str, jumper: float = 0.0,
                      out_port: str = "OUT", cable: str = "",
                      **kwargs) -> Location:
        """Insert a new location into the span that feeds *child_id*.

        The new location is fed by a short jumper from the existing parent --
        which is how an amplifier is actually hung, on the pole it is fed
        from -- and the original span then runs from the new location to the
        original child.
        """
        span = self.feed_span(child_id)
        if span is None:
            raise NetworkError(f"location {child_id!r} has no feed to insert into")
        loc = self.add_location(**kwargs)
        jumper_span = Span(
            id=self.new_id("S"), parent=span.parent, child=loc.id,
            cable=cable or span.cable, length=jumper, port=span.port,
            connectors=2, label="jumper" if not jumper else "",
        )
        self.spans[jumper_span.id] = jumper_span
        span.parent = loc.id
        span.port = out_port
        return loc

    def remove_location(self, loc_id: str) -> None:
        """Delete a location and everything downstream of it."""
        for child in list(self.children(loc_id)):
            self.remove_location(child.child)
        for span_id, span in list(self.spans.items()):
            if span.child == loc_id or span.parent == loc_id:
                del self.spans[span_id]
        self.locations.pop(loc_id, None)

    # ------------------------------------------------------------------
    # topology
    # ------------------------------------------------------------------
    @property
    def source_id(self) -> str:
        for loc in self.locations.values():
            if loc.kind == "source":
                return loc.id
        roots = [
            loc.id for loc in self.locations.values()
            if self.feed_span(loc.id) is None
        ]
        return roots[0] if roots else ""

    def feed_span(self, loc_id: str) -> Span | None:
        for span in self.spans.values():
            if span.child == loc_id:
                return span
        return None

    def parent_of(self, loc_id: str) -> str | None:
        span = self.feed_span(loc_id)
        return span.parent if span else None

    def children(self, loc_id: str) -> list[Span]:
        out = [s for s in self.spans.values() if s.parent == loc_id]
        out.sort(key=lambda s: (s.port, s.id))
        return out

    def walk(self, start: str = "") -> Iterator[tuple[Location, Span | None]]:
        """Depth-first walk from the source, yielding ``(location, feed span)``."""
        start = start or self.source_id
        if not start:
            return
        stack = [(start, None)]
        seen: set[str] = set()
        while stack:
            loc_id, span = stack.pop()
            if loc_id in seen:
                raise NetworkError(f"cycle detected at location {loc_id!r}")
            seen.add(loc_id)
            yield self.locations[loc_id], span
            for child in reversed(self.children(loc_id)):
                stack.append((child.child, child))

    def ordered(self, start: str = "") -> list[Location]:
        return [loc for loc, _ in self.walk(start)]

    def path_to(self, loc_id: str) -> list[str]:
        """Location ids from the source down to *loc_id* inclusive."""
        chain = [loc_id]
        guard = 0
        while True:
            parent = self.parent_of(chain[-1])
            if parent is None:
                break
            chain.append(parent)
            guard += 1
            if guard > len(self.locations) + 1:
                raise NetworkError("cycle detected while tracing to the source")
        return list(reversed(chain))

    def upstream_active(self, loc_id: str) -> str | None:
        """Nearest active (or source) at or above *loc_id*."""
        for ident in reversed(self.path_to(loc_id)[:-1]):
            if self.locations[ident].is_active:
                return ident
        return None

    def legs(self) -> list["Leg"]:
        """Index the plant as a set of legs.

        A **leg** is one linear run: it starts at an output port of a
        branching device and continues until the line ends or the next
        branch point is reached.  A run continues straight through an
        in-line amplifier -- a designer walking a street does not start a
        new leg at every line extender -- so legs are delimited where the
        plant actually branches.

        Naming a span also starts a leg there, even where nothing branches.
        That is what naming is for: it lets a designer split a long run into
        the legs they actually think in ("MAPLE ST", then "OAK AVE" beyond
        the amplifier) rather than being held to the topology alone.

        This is the unit the Design Assistant works in: you design a trunk
        line or a feeder leg at a time and "move to" the others.
        """
        out: list[Leg] = []
        start = self.source_id
        if not start:
            return out

        pending = [(Leg(id="TRUNK", name="", origin="", port="",
                        parent_leg=""), start)]
        seen: set[str] = set()
        while pending:
            leg, head = pending.pop(0)
            if head in seen:
                continue
            seen.add(head)
            chain = [head]
            cursor = head
            while True:
                kids = self.children(cursor)
                if len(kids) != 1 or kids[0].leg_name:
                    break
                cursor = kids[0].child
                if cursor in seen:
                    break
                seen.add(cursor)
                chain.append(cursor)
            leg.locations = chain
            out.append(leg)
            # only the tail of a chain can branch: every interior location
            # has exactly one child by construction
            tail = chain[-1]
            for span in self.children(tail):
                pending.append((
                    Leg(id=f"{tail}:{span.port}", name=span.leg_name,
                        origin=tail, port=span.port, parent_leg=leg.id,
                        first_span=span.id),
                    span.child,
                ))
        return out

    def leg_index(self) -> dict:
        return {leg.id: leg for leg in self.legs()}

    def leg_of(self, loc_id: str) -> "Leg | None":
        for leg in self.legs():
            if loc_id in leg.locations:
                return leg
        return None

    # ------------------------------------------------------------------
    # structural editing
    # ------------------------------------------------------------------
    def insert_after(self, loc_id: str, port: str = "", jumper: float = 0.0,
                     cable: str = "", **kwargs) -> Location:
        """Insert a new location immediately after *loc_id*.

        If something already hangs on *port*, the new location is spliced
        into that span: the existing child keeps its footage and the new
        location is fed by a jumper, which is how a device is added to a run
        without moving every pole below it.
        """
        existing = None
        for span in self.children(loc_id):
            if not port or span.port == port:
                existing = span
                break
        if existing is not None:
            return self.insert_before(existing.child, jumper=jumper,
                                      cable=cable, **kwargs)
        loc = self.add_location(**kwargs)
        self.add_span(loc_id, loc.id, cable=cable, length=jumper,
                      port=port or self._default_port(loc_id))
        return loc

    def _default_port(self, loc_id: str) -> str:
        used = {s.port for s in self.children(loc_id)}
        loc = self.locations[loc_id]
        if loc.is_active:
            return "OUT" if "OUT" not in used else f"OUT{len(used) + 1}"
        return "THRU" if "THRU" not in used else f"TAP{len(used)}"

    def splice_out(self, loc_id: str) -> None:
        """Remove one location and heal the run around it.

        The location's single child is reconnected to its parent and the two
        footages are added together, so deleting a pole from the middle of a
        leg leaves the geography of the rest of the leg untouched.  A
        location with more than one child cannot be spliced -- use
        :meth:`remove_location`.
        """
        feed = self.feed_span(loc_id)
        kids = self.children(loc_id)
        if feed is None:
            raise NetworkError("the source cannot be spliced out")
        if len(kids) > 1:
            raise NetworkError(
                f"{self.locations[loc_id].display()!r} branches into "
                f"{len(kids)} legs; delete it instead of splicing it"
            )
        if kids:
            child = kids[0]
            child.parent = feed.parent
            child.port = feed.port
            child.length = (child.length or 0) + (feed.length or 0)
            if not child.leg_name:
                child.leg_name = feed.leg_name
        del self.spans[feed.id]
        del self.locations[loc_id]

    def swap_ports(self, loc_id: str, port_a: str, port_b: str) -> None:
        """Swap the legs hanging on two ports of one device.

        Moving a leg from the tap leg of a coupler to its through leg (or
        between an amplifier's outputs) is a routine balancing move: it
        changes which branch gets the stronger signal without redrawing
        anything.
        """
        if loc_id not in self.locations:
            raise NetworkError(f"unknown location {loc_id!r}")
        spans = {s.port: s for s in self.children(loc_id)}
        a, b = spans.get(port_a), spans.get(port_b)
        if a is None and b is None:
            raise NetworkError(
                f"neither {port_a!r} nor {port_b!r} feeds anything"
            )
        if a is not None:
            a.port = port_b
        if b is not None:
            b.port = port_a

    def move_leg(self, span_id: str, new_parent: str, new_port: str) -> None:
        """Re-hang a whole leg on a different device or port."""
        span = self.spans.get(span_id)
        if span is None:
            raise NetworkError(f"unknown span {span_id!r}")
        if new_parent not in self.locations:
            raise NetworkError(f"unknown location {new_parent!r}")
        if new_parent == span.child or new_parent in self._descendants(span.child):
            raise NetworkError("a leg cannot be moved beneath itself")
        for other in self.children(new_parent):
            if other.port == new_port and other.id != span_id:
                raise NetworkError(
                    f"port {new_port} of "
                    f"{self.locations[new_parent].display()} is already fed"
                )
        span.parent = new_parent
        span.port = new_port

    def _descendants(self, loc_id: str) -> set:
        out = set()
        stack = [loc_id]
        while stack:
            current = stack.pop()
            for span in self.children(current):
                out.add(span.child)
                stack.append(span.child)
        return out

    def name_leg(self, span_id: str, name: str) -> None:
        span = self.spans.get(span_id)
        if span is None:
            raise NetworkError(f"unknown span {span_id!r}")
        span.leg_name = name

    # ------------------------------------------------------------------
    # validation and statistics
    # ------------------------------------------------------------------
    def validate(self) -> list[str]:
        problems: list[str] = []
        if not self.locations:
            return ["the network is empty"]
        roots = [
            loc.id for loc in self.locations.values()
            if self.feed_span(loc.id) is None
        ]
        if len(roots) > 1:
            problems.append(
                "more than one unfed location: " + ", ".join(sorted(roots))
            )
        if not any(loc.kind == "source" for loc in self.locations.values()):
            problems.append("the network has no source (node or launch amplifier)")
        try:
            reached = {loc.id for loc, _ in self.walk()}
        except NetworkError as exc:
            problems.append(str(exc))
            reached = set()
        orphans = set(self.locations) - reached
        if orphans:
            problems.append(
                "unreachable locations: " + ", ".join(sorted(orphans))
            )
        for span in self.spans.values():
            if span.length < 0:
                problems.append(f"span {span.id!r} has a negative length")
            if not span.cable:
                problems.append(f"span {span.id!r} has no cable type")
        for loc in self.locations.values():
            if loc.kind in ("tap", "coupler", "active") and not loc.device:
                problems.append(
                    f"location {loc.display()!r} is a {loc.kind} with no device"
                )
        return problems

    def stats(self) -> dict:
        taps = [l for l in self.locations.values() if l.is_tap]
        actives = [l for l in self.locations.values() if l.kind == "active"]
        return {
            "locations": len(self.locations),
            "spans": len(self.spans),
            "taps": len(taps),
            "actives": len(actives),
            "couplers": sum(1 for l in self.locations.values() if l.kind == "coupler"),
            "power_supplies": sum(
                1 for l in self.locations.values() if l.power_supply is not None
            ),
            "units": sum(l.units for l in self.locations.values()),
            "footage": round(sum(s.length for s in self.spans.values()), 1),
        }

    # ------------------------------------------------------------------
    # serialisation (.dsn)
    # ------------------------------------------------------------------
    def to_dict(self) -> dict:
        def enc_loc(loc: Location) -> dict:
            data = {
                "id": loc.id, "label": loc.label, "kind": loc.kind,
                "device": loc.device, "units": loc.units, "tsg": loc.tsg,
                "tap_ports": loc.tap_ports, "locked": loc.locked,
                "pad": loc.pad, "eq": loc.eq,
                "rtn_pad": loc.rtn_pad, "rtn_eq": loc.rtn_eq,
                "power_block": loc.power_block, "note": loc.note,
                "x": loc.x, "y": loc.y, "extra": loc.extra,
            }
            if loc.power_supply is not None:
                ps = loc.power_supply
                data["power_supply"] = {
                    "id": ps.id, "volts": ps.volts, "max_amps": ps.max_amps,
                    "feeds": ps.feeds, "description": ps.description,
                    "price": ps.price,
                }
            return data

        return {
            "kind": "network",
            "name": self.name,
            "description": self.description,
            "spec_set": self.spec_set,
            "locations": [enc_loc(l) for l in self.locations.values()],
            "spans": [
                {
                    "id": s.id, "parent": s.parent, "child": s.child,
                    "cable": s.cable, "length": s.length, "port": s.port,
                    "extra_loss": s.extra_loss, "connectors": s.connectors,
                    "label": s.label, "leg_name": s.leg_name, "extra": s.extra,
                }
                for s in self.spans.values()
            ],
        }

    @classmethod
    def from_dict(cls, data: dict, source: str = "") -> "Network":
        net = cls(
            name=data.get("name", "untitled"),
            description=data.get("description", ""),
            spec_set=data.get("spec_set", ""),
            source=source,
        )
        for raw in data.get("locations", []):
            ps_raw = raw.pop("power_supply", None)
            known = {f for f in Location.__dataclass_fields__}
            loc = Location(**{k: v for k, v in raw.items() if k in known})
            if ps_raw:
                loc.power_supply = PowerSupply(
                    **{k: v for k, v in ps_raw.items()
                       if k in PowerSupply.__dataclass_fields__}
                )
            net.locations[loc.id] = loc
        for raw in data.get("spans", []):
            known = {f for f in Span.__dataclass_fields__}
            span = Span(**{k: v for k, v in raw.items() if k in known})
            net.spans[span.id] = span
        digits = [
            int(x[1:]) for x in list(net.locations) + list(net.spans)
            if len(x) > 1 and x[0] in "LS" and x[1:].isdigit()
        ]
        net._seq = max(digits) if digits else 0
        return net

    @classmethod
    def load(cls, path: str) -> "Network":
        with open(path, "r", encoding="utf-8") as fh:
            return cls.from_dict(json.load(fh), source=os.path.abspath(path))

    def save(self, path: str) -> str:
        tmp = f"{path}.tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(self.to_dict(), fh, indent=2)
            fh.write("\n")
        os.replace(tmp, path)
        self.source = os.path.abspath(path)
        return self.source
