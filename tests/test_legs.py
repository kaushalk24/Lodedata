"""Legs and structural editing -- the Design Mode entry model.

The Design Assistant is worked one leg at a time: you design a trunk line or
a feeder leg, typing footage and house counts into a grid, and "move to" the
other legs.  These tests cover the model that makes that possible.
"""

import unittest

from lode.engine.levels import LevelEngine
from lode.library import generic750
from lode.network import Network, NetworkError
from lode.web.server import Handler


def run(spans, device="T4-17", units=2):
    """A straight run of taps off a node."""
    net = Network(name="run")
    cursor = net.add_location(kind="source", label="ND1", device="ND-750").id
    port = "OUT1"
    ids = []
    for index, length in enumerate(spans, start=1):
        loc = net.add_location(kind="tap", label=f"T{index}", device=device,
                               units=units)
        net.add_span(cursor, loc.id, cable="P3-500", length=length, port=port)
        ids.append(loc.id)
        cursor, port = loc.id, "THRU"
    return net, ids


class TestLegIndex(unittest.TestCase):
    def test_a_straight_run_is_one_leg(self):
        net, ids = run([100, 100, 100])
        legs = net.legs()
        self.assertEqual(len(legs), 1)
        self.assertEqual(legs[0].id, "TRUNK")
        self.assertEqual(len(legs[0].locations), 4)   # the source counts

    def test_a_run_continues_straight_through_an_amplifier(self):
        """A designer walking a street does not start a new leg at every LE."""
        net, ids = run([100, 100])
        amp = net.add_location(kind="active", label="LE1", device="LE-750")
        net.add_span(ids[-1], amp.id, cable="P3-500", length=100, port="THRU")
        tail = net.add_location(kind="tap", label="T9", device="T4-17")
        net.add_span(amp.id, tail.id, cable="P3-500", length=100, port="OUT")
        legs = net.legs()
        self.assertEqual(len(legs), 1)
        self.assertIn(amp.id, legs[0].locations)
        self.assertIn(tail.id, legs[0].locations)

    def test_a_branch_starts_new_legs(self):
        net, ids = run([100, 100])
        coupler = net.add_location(kind="coupler", label="SP1", device="SP2")
        net.add_span(ids[-1], coupler.id, cable="P3-500", length=50, port="THRU")
        left = net.add_location(kind="tap", label="L1", device="T4-17")
        right = net.add_location(kind="tap", label="R1", device="T4-17")
        net.add_span(coupler.id, left.id, cable="P3-500", length=60, port="THRU")
        net.add_span(coupler.id, right.id, cable="P3-500", length=70, port="TAP1")

        legs = {leg.id: leg for leg in net.legs()}
        self.assertEqual(len(legs), 3)
        trunk = legs["TRUNK"]
        self.assertEqual(trunk.locations[-1], coupler.id)
        for leg in legs.values():
            if leg.id == "TRUNK":
                continue
            self.assertEqual(leg.origin, coupler.id)
            self.assertEqual(leg.parent_leg, "TRUNK")
        self.assertEqual({legs[f"{coupler.id}:THRU"].locations[0],
                          legs[f"{coupler.id}:TAP1"].locations[0]},
                         {left.id, right.id})

    def test_every_location_belongs_to_exactly_one_leg(self):
        net = Network.load("networks/example.dsn")
        seen = []
        for leg in net.legs():
            seen.extend(leg.locations)
        self.assertEqual(sorted(seen), sorted(net.locations))
        self.assertEqual(len(seen), len(set(seen)), "a location was listed twice")

    def test_leg_names_ride_on_the_span_that_starts_them(self):
        net, ids = run([100, 100])
        coupler = net.add_location(kind="coupler", label="SP1", device="SP2")
        net.add_span(ids[-1], coupler.id, cable="P3-500", length=50, port="THRU")
        a = net.add_location(kind="tap", label="A", device="T4-17")
        span = net.add_span(coupler.id, a.id, cable="P3-500", length=60,
                            port="TAP1")
        net.name_leg(span.id, "MAPLE ST")
        leg = next(l for l in net.legs() if l.origin == coupler.id
                   and l.port == "TAP1")
        self.assertEqual(leg.name, "MAPLE ST")
        self.assertEqual(leg.display(), "MAPLE ST")
        # and it survives a save/load round trip
        again = Network.from_dict(net.to_dict())
        self.assertEqual(again.spans[span.id].leg_name, "MAPLE ST")

    def test_naming_a_span_splits_a_run_into_named_legs(self):
        """Naming imposes the designer's own leg structure on a straight run."""
        net, ids = run([100, 100, 100, 100])
        self.assertEqual(len(net.legs()), 1)
        net.name_leg(net.feed_span(ids[2]).id, "OAK AVE")
        legs = net.legs()
        self.assertEqual(len(legs), 2)
        named = next(l for l in legs if l.name == "OAK AVE")
        self.assertEqual(named.locations[0], ids[2])
        self.assertEqual(named.parent_leg, "TRUNK")
        self.assertEqual(named.origin, ids[1])
        # clearing the name merges the run back together
        net.name_leg(net.feed_span(ids[2]).id, "")
        self.assertEqual(len(net.legs()), 1)

    def test_leg_of_finds_the_containing_leg(self):
        net = Network.load("networks/example.dsn")
        for leg in net.legs():
            for loc_id in leg.locations:
                self.assertEqual(net.leg_of(loc_id).id, leg.id)


class TestSpliceOut(unittest.TestCase):
    def test_footage_is_conserved(self):
        """Deleting a pole must not move every pole below it."""
        net, ids = run([100, 200, 300, 400])
        before = sum(s.length for s in net.spans.values())
        net.splice_out(ids[1])
        after = sum(s.length for s in net.spans.values())
        self.assertEqual(before, after)
        self.assertEqual(net.feed_span(ids[2]).length, 500)
        self.assertEqual(net.validate(), [])

    def test_levels_below_are_unchanged(self):
        specs = generic750()
        net, ids = run([100, 200, 300, 400], device="T4-11")
        # a zero-value pole in the middle: splicing it must not move the rest
        net.locations[ids[1]].kind = "point"
        net.locations[ids[1]].device = ""
        before = LevelEngine(specs, net).solve()[ids[3]].fwd_in["F1"]
        net.splice_out(ids[1])
        after = LevelEngine(specs, net).solve()[ids[3]].fwd_in["F1"]
        self.assertAlmostEqual(before, after, places=6)

    def test_the_source_cannot_be_spliced(self):
        net, ids = run([100])
        with self.assertRaises(NetworkError):
            net.splice_out(net.source_id)

    def test_a_branch_point_cannot_be_spliced(self):
        net, ids = run([100])
        for port in ("THRU", "TAP1"):
            loc = net.add_location(kind="tap", label=port, device="T4-17")
            net.add_span(ids[0], loc.id, cable="P3-500", length=10, port=port)
        with self.assertRaises(NetworkError) as ctx:
            net.splice_out(ids[0])
        self.assertIn("branches", str(ctx.exception))

    def test_splicing_the_last_pole_just_removes_it(self):
        net, ids = run([100, 200])
        net.splice_out(ids[-1])
        self.assertNotIn(ids[-1], net.locations)
        self.assertEqual(net.validate(), [])


class TestSwapAndMove(unittest.TestCase):
    def _coupler(self):
        net, ids = run([100])
        coupler = net.add_location(kind="coupler", label="SP1", device="SP2")
        net.add_span(ids[0], coupler.id, cable="P3-500", length=50, port="THRU")
        left = net.add_location(kind="tap", label="L", device="T4-17")
        right = net.add_location(kind="tap", label="R", device="T4-17")
        net.add_span(coupler.id, left.id, cable="P3-500", length=60, port="THRU")
        net.add_span(coupler.id, right.id, cable="P3-500", length=70, port="TAP1")
        return net, coupler.id, left.id, right.id

    def test_swap_exchanges_the_two_legs(self):
        net, coupler, left, right = self._coupler()
        net.swap_ports(coupler, "THRU", "TAP1")
        ports = {s.port: s.child for s in net.children(coupler)}
        self.assertEqual(ports["THRU"], right)
        self.assertEqual(ports["TAP1"], left)
        self.assertEqual(net.validate(), [])

    def test_swapping_changes_which_leg_gets_the_signal(self):
        specs = generic750()
        net, coupler, left, right = self._coupler()
        # a directional coupler is deliberately lopsided
        net.locations[coupler].device = "DC12"
        before = LevelEngine(specs, net).solve()
        net.swap_ports(coupler, "THRU", "TAP1")
        after = LevelEngine(specs, net).solve()
        self.assertGreater(before[left].fwd_in["F1"], before[right].fwd_in["F1"])
        self.assertLess(after[left].fwd_in["F1"], after[right].fwd_in["F1"])

    def test_swapping_an_empty_port_moves_the_leg(self):
        net, coupler, left, right = self._coupler()
        for span in list(net.children(coupler)):
            if span.port == "TAP1":
                del net.spans[span.id]
                net.locations.pop(right)
        net.swap_ports(coupler, "THRU", "TAP1")
        self.assertEqual([s.port for s in net.children(coupler)], ["TAP1"])

    def test_unknown_ports_are_refused(self):
        net, coupler, left, right = self._coupler()
        with self.assertRaises(NetworkError):
            net.swap_ports(coupler, "NOPE", "ALSO-NOPE")

    def test_move_leg_rehangs_a_whole_branch(self):
        net, coupler, left, right = self._coupler()
        span = net.feed_span(right)
        target = net.locations[left]
        net.move_leg(span.id, target.id, "THRU")
        self.assertEqual(net.parent_of(right), left)
        self.assertEqual(net.validate(), [])

    def test_a_leg_cannot_be_moved_beneath_itself(self):
        net, coupler, left, right = self._coupler()
        span = net.feed_span(left)
        with self.assertRaises(NetworkError):
            net.move_leg(span.id, left, "THRU")

    def test_a_taken_port_is_refused(self):
        net, coupler, left, right = self._coupler()
        span = net.feed_span(right)
        with self.assertRaises(NetworkError) as ctx:
            net.move_leg(span.id, coupler, "THRU")
        self.assertIn("already fed", str(ctx.exception))


class TestInsertAfter(unittest.TestCase):
    def test_insert_splices_into_an_existing_span(self):
        net, ids = run([100, 200])
        amp = net.insert_after(ids[0], port="THRU", kind="active",
                               device="LE-750", label="LE1")
        # the pole below keeps its own footage; the new device rides a jumper
        self.assertEqual(net.feed_span(amp.id).length, 0)
        self.assertEqual(net.feed_span(ids[1]).length, 200)
        self.assertEqual(net.parent_of(ids[1]), amp.id)
        self.assertEqual(net.validate(), [])

    def test_insert_at_the_end_appends(self):
        net, ids = run([100])
        loc = net.insert_after(ids[0], port="THRU", jumper=250,
                               cable="P3-500", kind="tap", device="T4-11")
        self.assertEqual(net.parent_of(loc.id), ids[0])
        self.assertEqual(net.feed_span(loc.id).length, 250)


class TestTapByValue(unittest.TestCase):
    """Designers type a tap value, not a part number."""

    def setUp(self):
        self.specs = generic750()

    def test_exact_and_nearest_values(self):
        self.assertEqual(self.specs.taps.find_value(17, 4).id, "T4-17")
        self.assertEqual(self.specs.taps.find_value(17, 8).id, "T8-17")
        self.assertEqual(self.specs.taps.find_value(18, 4).id, "T4-17")
        self.assertEqual(self.specs.taps.find_value(999, 4).id, "T4-32")

    def test_self_terminating_is_honoured(self):
        tap = self.specs.taps.find_value(17, 4, self_terminating=True)
        self.assertTrue(tap.self_terminating)
        self.assertEqual(tap.id, "T4-17T")

    def test_values_lists_the_group(self):
        self.assertEqual(self.specs.taps.values(1, 2)[0], 4.0)
        self.assertIn(17.0, self.specs.taps.values(1, 4))


class TestEditEndpoint(unittest.TestCase):
    """The structural edits the grid drives, exercised through the API layer."""

    def setUp(self):
        self.specs = generic750()

    def apply(self, net, op, args):
        Handler._apply_edit(net, self.specs, op, args)

    def test_set_tap_value(self):
        net, ids = run([100], device="T4-8")
        self.apply(net, "set_tap_value", {"location": ids[0], "value": 20,
                                          "ports": 4})
        self.assertEqual(net.locations[ids[0]].device, "T4-20")

    def test_set_tap_value_respects_the_port_count(self):
        net, ids = run([100], device="T4-8")
        self.apply(net, "set_tap_value", {"location": ids[0], "value": 20,
                                          "ports": 8})
        self.assertEqual(net.locations[ids[0]].device, "T8-20")

    def test_splice_and_swap_through_the_api(self):
        net, ids = run([100, 200, 300])
        self.apply(net, "splice_out", {"location": ids[1]})
        self.assertNotIn(ids[1], net.locations)
        self.assertEqual(net.feed_span(ids[2]).length, 500)

    def test_name_leg_through_the_api(self):
        net, ids = run([100, 100])
        span = net.feed_span(ids[1])
        self.apply(net, "name_leg", {"span": span.id, "name": "OAK AVE"})
        self.assertEqual(net.spans[span.id].leg_name, "OAK AVE")

    def test_unknown_location_is_reported(self):
        net, ids = run([100])
        with self.assertRaises(Exception):
            self.apply(net, "splice_out", {"location": "nope"})


if __name__ == "__main__":
    unittest.main()
