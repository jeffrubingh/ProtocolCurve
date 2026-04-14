import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from curveprotocol.book import BookError, ancestry, build_book, find_origins, find_terminals, reachable
from curveprotocol.model import Flow, Reserve


def simple():
    reserves = [Reserve(id="a"), Reserve(id="b"), Reserve(id="c")]
    flows = [Flow(id="f1", op="deposit", inputs=["a"], outputs=["b"]), Flow(id="f2", op="deposit", inputs=["b"], outputs=["c"])]
    return reserves, flows


class BuildTests(unittest.TestCase):
    def test_adjacency_is_populated(self):
        book = build_book(*simple())
        self.assertEqual(book.sinks("a"), ("b",))
        self.assertEqual(book.sources("c"), ("b",))

    def test_duplicate_reserve_rejected(self):
        with self.assertRaises(BookError):
            build_book([Reserve(id="a"), Reserve(id="a")], [])

    def test_duplicate_flow_rejected(self):
        reserves, flows = simple()
        with self.assertRaises(BookError):
            build_book(reserves, flows + flows[:1])

    def test_unknown_reference_is_fatal_in_strict_mode(self):
        with self.assertRaises(BookError):
            build_book([Reserve(id="a")], [Flow(id="f", inputs=["a"], outputs=["ghost"])])

    def test_unknown_reference_is_synthesised_in_lenient_mode(self):
        book = build_book([Reserve(id="a")], [Flow(id="f", inputs=["a"], outputs=["ghost"])], strict=False)
        self.assertIn("ghost", book.reserves)
        self.assertEqual(book.reserves["ghost"].band, "core")

    def test_flow_that_credits_nothing_rejected(self):
        with self.assertRaises(BookError):
            build_book([Reserve(id="a")], [Flow(id="f", inputs=["a"], outputs=[])])

    def test_cycle_rejected(self):
        reserves = [Reserve(id="a"), Reserve(id="b")]
        flows = [Flow(id="f1", inputs=["a"], outputs=["b"]), Flow(id="f2", inputs=["b"], outputs=["a"])]
        with self.assertRaises(BookError):
            build_book(reserves, flows)


class TraversalTests(unittest.TestCase):
    def test_origins_and_terminals(self):
        book = build_book(*simple())
        self.assertEqual(find_origins(book), ("a",))
        self.assertEqual(find_terminals(book), ("c",))

    def test_seed_flow_keeps_its_output_an_origin(self):
        book = build_book([Reserve(id="a")], [Flow(id="f", op="seed", outputs=["a"])])
        self.assertEqual(find_origins(book), ("a",))

    def test_ancestry_is_ordered(self):
        book = build_book(*simple())
        self.assertEqual(ancestry(book, "c"), ("a", "b"))

    def test_reachable_from_origin(self):
        book = build_book(*simple())
        self.assertEqual(reachable(book, "a"), ("b", "c"))

    def test_unknown_reserve(self):
        book = build_book(*simple())
        with self.assertRaises(BookError):
            ancestry(book, "zzz")


if __name__ == "__main__":
    unittest.main()
