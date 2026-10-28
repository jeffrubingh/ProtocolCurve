import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from curveprotocol import parity

BOOK = "R|a|seed|1000000\nR|b|core|500000\nF|f|deposit|a|b\n"


class ParityTests(unittest.TestCase):
    def test_parses_and_fingerprints(self):
        reserves, flows = parity.parse(BOOK)
        self.assertEqual(len(reserves), 2)
        self.assertEqual(len(parity.fingerprint(reserves, flows)), 16)

    def test_rejects_unknown_reference(self):
        with self.assertRaises(parity.ParityError):
            parity.parse("R|a|core|1\nF|f|deposit|a|ghost\n")

    def test_rejects_empty_outputs(self):
        with self.assertRaises(parity.ParityError):
            parity.parse("R|a|core|1\nF|f|deposit|a|\n")

    def test_rejects_duplicate_reserve(self):
        with self.assertRaises(parity.ParityError):
            parity.parse("R|a|core|1\nR|a|core|2\n")

    def test_unknown_band_folds_to_core(self):
        reserves, _ = parity.parse("R|a|moon|1\n")
        self.assertEqual(reserves[0].band, "core")

    def test_fingerprint_is_sorted_stable(self):
        first = parity.fingerprint(*parity.parse(BOOK))
        second = parity.fingerprint(*parity.parse("R|b|core|500000\nR|a|seed|1000000\nF|f|deposit|a|b\n"))
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
