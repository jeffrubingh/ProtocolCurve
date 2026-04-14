import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from curveprotocol.book import build_book
from curveprotocol.depth import DEPTH_FLOOR, compute_depth, grade, shortfalls
from curveprotocol.model import MICRO, Flow, Reserve


def book_of(reserves):
    return build_book(reserves, [Flow(id="f", inputs=[], outputs=[r.id for r in reserves])])


class DepthTests(unittest.TestCase):
    def test_core_book_scores_high(self):
        book = book_of([Reserve(id="a", band="core", balance=1000 * MICRO), Reserve(id="b", band="core", balance=1000 * MICRO)])
        self.assertGreater(compute_depth(book).depth_score, 0.9)

    def test_edge_book_scores_low(self):
        book = book_of([Reserve(id="a", band="edge", balance=1000 * MICRO)])
        self.assertLess(compute_depth(book).depth_score, 0.6)

    def test_thin_tranche_reported(self):
        book = book_of([Reserve(id="a", band="core", balance=DEPTH_FLOOR - 1)])
        self.assertEqual(compute_depth(book).thin_ids, ("a",))

    def test_dry_tranche_without_producer(self):
        book = build_book([Reserve(id="dry")], [])
        self.assertEqual(compute_depth(book).dry_ids, ("dry",))

    def test_score_is_bounded(self):
        book = book_of([Reserve(id="a", band="sink", balance=1), Reserve(id="b", band="seed", balance=10**9)])
        score = compute_depth(book).depth_score
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)

    def test_band_balances_are_integer(self):
        book = book_of([Reserve(id="a", band="core", balance=7)])
        self.assertEqual(compute_depth(book).band_balances["core"], 7)

    def test_shortfalls_are_thinnest_first(self):
        book = book_of([Reserve(id="a", band="core", balance=900 * MICRO)])
        gaps = shortfalls(compute_depth(book), 1000 * MICRO)
        self.assertEqual(gaps[-1][0], "core")

    def test_grades_descend(self):
        self.assertEqual(grade(0.9), "A")
        self.assertEqual(grade(0.0), "E")


if __name__ == "__main__":
    unittest.main()
