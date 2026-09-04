import math
import unittest

from src.core.numeric import bounded_float, bounded_int
from src.input.text_input import _normalize_double_input_options


class NumericStabilityTests(unittest.TestCase):
    def test_non_finite_float_uses_safe_default(self):
        for value in (math.nan, math.inf, -math.inf):
            with self.subTest(value=value):
                self.assertEqual(
                    bounded_float(value, default=1.0, minimum=0.2, maximum=5.0),
                    1.0,
                )

    def test_huge_integers_are_clamped(self):
        self.assertEqual(
            bounded_int(10**1000, default=10, minimum=1, maximum=100),
            100,
        )

    def test_double_input_options_are_ordered_finite_and_bounded(self):
        value, minimum, maximum, decimals, step = _normalize_double_input_options(
            math.nan,
            100,
            -100,
            10**100,
            -math.inf,
        )
        self.assertEqual((minimum, maximum), (-100.0, 100.0))
        self.assertTrue(math.isfinite(value))
        self.assertEqual(decimals, 12)
        self.assertGreater(step, 0)


if __name__ == "__main__":
    unittest.main()
