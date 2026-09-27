"""Existing acceptance tests for the crdtmerge library.

Every test in this module is expected to fail with ``NotImplementedError``
until the library is implemented.
"""

import unittest

from crdtmerge import LWWRegister, ORSet, load, merge, state
from crdtmerge.errors import CorruptState


class ORSetTests(unittest.TestCase):
    def test_add_and_elements(self):
        s = ORSet("A")
        s.add("x")
        s.add("y")
        self.assertEqual(s.elements(), frozenset({"x", "y"}))

    def test_remove_observed_tag(self):
        s = ORSet("A")
        s.add("x")
        s.remove("x")
        self.assertEqual(s.elements(), frozenset())

    def test_add_wins_concurrent(self):
        a = ORSet("A")
        a.add("x")
        b = merge(ORSet("B"), a)
        b.add("x")
        a = merge(a, ORSet("A"))
        a.remove("x")
        c = merge(a, b)
        self.assertIn("x", c.elements())

    def test_global_counter_across_elements(self):
        s = ORSet("A")
        s.add("x")
        s.add("y")
        s.remove("x")
        self.assertEqual(s.elements(), frozenset({"y"}))

    def test_empty_replica_rejected(self):
        with self.assertRaises(ValueError):
            ORSet("")


class LWWTests(unittest.TestCase):
    def test_basic_set_and_value(self):
        r = LWWRegister("A")
        r.set("v1", 1)
        self.assertEqual(r.value(), "v1")
        r.set("v2", 2)
        self.assertEqual(r.value(), "v2")

    def test_ts_then_replica_tiebreak(self):
        a = LWWRegister("A")
        a.set("va", 5)
        b = LWWRegister("B")
        b.set("vb", 5)
        self.assertEqual(merge(a, b).value(), "vb")
        self.assertEqual(merge(b, a).value(), "vb")
        hi = LWWRegister("A")
        hi.set("high", 9)
        lo = LWWRegister("B")
        lo.set("low", 1)
        self.assertEqual(merge(hi, lo).value(), "high")

    def test_same_ts_deterministic(self):
        r = LWWRegister("A")
        r.set("first", 7)
        r.set("second", 7)
        self.assertIn(r.value(), ("first", "second"))
        a = LWWRegister("A")
        a.set("p", 3)
        b = LWWRegister("A")
        b.set("q", 3)
        self.assertEqual(merge(a, b).value(), merge(b, a).value())

    def test_empty_replica_rejected(self):
        with self.assertRaises(ValueError):
            LWWRegister("")


class MergeTests(unittest.TestCase):
    def test_merge_pure(self):
        a = ORSet("A")
        a.add("x")
        b = ORSet("B")
        b.add("y")
        before_a = state(a)
        before_b = state(b)
        c = merge(a, b)
        self.assertIsNot(c, a)
        self.assertIsNot(c, b)
        self.assertEqual(state(a), before_a)
        self.assertEqual(state(b), before_b)
        self.assertEqual(c.elements(), frozenset({"x", "y"}))

    def test_algebraic_laws(self):
        a = ORSet("A")
        a.add("x")
        b = ORSet("B")
        b.add("x")
        b.add("y")
        c = ORSet("C")
        c.add("y")
        c.remove("y")
        c.add("z")
        self.assertEqual(state(merge(a, b)), state(merge(b, a)))
        self.assertEqual(
            state(merge(merge(a, b), c)),
            state(merge(a, merge(b, c))),
        )
        self.assertEqual(state(merge(a, a)), state(a))


class CodecTests(unittest.TestCase):
    def test_roundtrip_and_corrupt(self):
        s = ORSet("A")
        s.add("x")
        s.add("y")
        s.remove("x")
        blob = state(s)
        self.assertIsInstance(blob, bytes)
        self.assertEqual(state(load(blob)), blob)
        bad_blobs = (b"", blob[:-1], blob[: len(blob) // 2], b"\xff" * len(blob))
        for bad in bad_blobs:
            with self.assertRaises(CorruptState):
                load(bad)


if __name__ == "__main__":
    unittest.main()
