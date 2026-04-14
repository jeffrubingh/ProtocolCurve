import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from curveprotocol import curve
from curveprotocol.model import MICRO


class CompoundTests(unittest.TestCase):
    def test_grows_by_rate(self):
        self.assertEqual(curve.compound(1000 * MICRO, 500, 0), 1050 * MICRO)

    def test_clamped_by_ceiling(self):
        self.assertEqual(curve.compound(1000 * MICRO, 5000, 1100 * MICRO), 1100 * MICRO)

    def test_empty_balance_stays_empty(self):
        self.assertEqual(curve.compound(0, 500, 0), 0)

    def test_negative_rate_is_flat(self):
        self.assertEqual(curve.compound(700, -100, 0), 700)


class ProjectTests(unittest.TestCase):
    def test_series_starts_at_seed_and_is_monotone(self):
        series = curve.project(100 * MICRO, 1000, 0, 5)
        self.assertEqual(len(series), 6)
        self.assertEqual(series[0], 100 * MICRO)
        self.assertEqual(series, sorted(series))

    def test_epochs_are_capped(self):
        self.assertEqual(len(curve.project(10, 1, 0, curve.MAX_ROUNDS + 50)), curve.MAX_ROUNDS + 1)

    def test_epochs_to_ceiling(self):
        self.assertEqual(curve.epochs_to_ceiling(100 * MICRO, 10_000, 200 * MICRO), 1)
        self.assertEqual(curve.epochs_to_ceiling(100 * MICRO, 0, 200 * MICRO), -1)


class BandTests(unittest.TestCase):
    def test_parts_add_up(self):
        parts = curve.split_bands(1000, [0.5, 0.3, 0.2])
        self.assertEqual(sum(parts), 1000)
        self.assertEqual(parts[0], 500)

    def test_zero_weights_split_evenly(self):
        self.assertEqual(sum(curve.split_bands(9, [0, 0, 0])), 9)

    def test_band_weights_normalise(self):
        self.assertEqual(curve.band_weights([50, 100]), (0.5, 1.0))


class FingerprintTests(unittest.TestCase):
    def test_stable_and_order_sensitive(self):
        self.assertEqual(curve.fingerprint(["a", 1]), curve.fingerprint(["a", 1]))
        self.assertNotEqual(curve.fingerprint(["a", 1]), curve.fingerprint(["a", 2]))

    def test_hex_width(self):
        self.assertEqual(len(curve.fingerprint(["x"])), 16)


if __name__ == "__main__":
    unittest.main()
