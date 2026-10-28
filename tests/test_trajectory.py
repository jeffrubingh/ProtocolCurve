import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from curveprotocol.book import build_book
from curveprotocol.model import Flow, Reserve
from curveprotocol.trajectory import build_trajectory, render


def fixture():
    reserves = [
        Reserve(id="r-seed", band="seed", balance=1000 * 10**6),
        Reserve(id="r-core", band="core", balance=600 * 10**6),
        Reserve(id="r-sink", band="sink", balance=40 * 10**6),
    ]
    flows = [
        Flow(id="f1", op="seed", outputs=["r-seed"]),
        Flow(id="f2", op="deposit", inputs=["r-seed"], outputs=["r-core"]),
        Flow(id="f3", op="harvest", inputs=["r-core"], outputs=["r-sink"]),
    ]
    return build_book(reserves, flows)


class TrajectoryTests(unittest.TestCase):
    def test_digest_and_fingerprint_present(self):
        report = build_trajectory(fixture())
        self.assertEqual(len(report.book_digest), 64)
        self.assertEqual(len(report.curve_fingerprint), 16)

    def test_paths_end_at_terminal(self):
        book = fixture()
        report = build_trajectory(book)
        for terminal in report.terminals:
            self.assertNotIn(terminal, report.paths[terminal])

    def test_render_is_deterministic(self):
        book = fixture()
        first = render(build_trajectory(book), book)
        second = render(build_trajectory(book), book)
        self.assertEqual(first, second)

    def test_render_has_no_timestamp(self):
        book = fixture()
        self.assertNotRegex(render(build_trajectory(book), book), r"\d{4}-\d{2}-\d{2}")

    def test_json_roundtrip(self):
        book = fixture()
        payload = json.loads(render(build_trajectory(book), book, fmt="json"))
        self.assertIn("depth", payload)
        self.assertIn("op_histogram", payload)

    def test_unknown_format(self):
        book = fixture()
        with self.assertRaises(ValueError):
            render(build_trajectory(book), book, fmt="yaml")


if __name__ == "__main__":
    unittest.main()
