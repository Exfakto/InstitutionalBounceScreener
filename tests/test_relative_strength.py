import unittest

import pandas as pd

from analysis.relative_strength import RelativeStrengthCalculator


class RelativeStrengthCalculatorTest(unittest.TestCase):

    def setUp(self):
        self.calculator = RelativeStrengthCalculator()

    def build_history(self, start_price, daily_step, periods):
        closes = [start_price + (daily_step * index) for index in range(periods)]
        return pd.DataFrame(
            {"Close": closes},
            index=pd.date_range("2025-01-01", periods=periods, freq="B"),
        )

    def test_calculates_relative_strength_for_all_periods(self):
        stock = self.build_history(100, 1.0, 260)
        benchmark = self.build_history(100, 0.5, 260)

        result = self.calculator.calculate(stock, benchmark)

        self.assertIsNotNone(result.rs_3m)
        self.assertIsNotNone(result.rs_6m)
        self.assertIsNotNone(result.rs_12m)
        self.assertGreater(result.rs_3m, 0.0)
        self.assertGreater(result.rs_6m, 0.0)
        self.assertGreater(result.rs_12m, 0.0)
        self.assertGreater(result.rs_score, 50.0)
        self.assertEqual(result.warnings, [])

    def test_market_like_performance_scores_near_neutral(self):
        stock = self.build_history(100, 0.5, 260)
        benchmark = self.build_history(100, 0.5, 260)

        result = self.calculator.calculate(stock, benchmark)

        self.assertAlmostEqual(result.rs_3m, 0.0, places=6)
        self.assertAlmostEqual(result.rs_6m, 0.0, places=6)
        self.assertAlmostEqual(result.rs_12m, 0.0, places=6)
        self.assertAlmostEqual(result.rs_score, 50.0, places=6)

    def test_missing_history_returns_safe_result(self):
        benchmark = self.build_history(100, 0.5, 260)

        result = self.calculator.calculate(pd.DataFrame(), benchmark)

        self.assertIsNone(result.rs_3m)
        self.assertIsNone(result.rs_6m)
        self.assertIsNone(result.rs_12m)
        self.assertEqual(result.rs_score, 0.0)
        self.assertIn("Missing stock price history", result.warnings)

    def test_insufficient_history_returns_partial_safe_result(self):
        stock = self.build_history(100, 1.0, 120)
        benchmark = self.build_history(100, 0.5, 120)

        result = self.calculator.calculate(stock, benchmark)

        self.assertIsNotNone(result.rs_3m)
        self.assertIsNone(result.rs_6m)
        self.assertIsNone(result.rs_12m)
        self.assertGreater(result.rs_score, 50.0)
        self.assertIn("Insufficient overlapping history for rs_6m", result.warnings)
        self.assertIn("Insufficient overlapping history for rs_12m", result.warnings)

    def test_score_is_clamped_to_zero_and_hundred(self):
        strong_stock = self.build_history(100, 5.0, 260)
        weak_benchmark = self.build_history(100, 0.1, 260)

        strong_result = self.calculator.calculate(strong_stock, weak_benchmark)

        self.assertEqual(strong_result.rs_score, 100.0)

        weak_stock = self.build_history(100, 0.1, 260)
        strong_benchmark = self.build_history(100, 5.0, 260)

        weak_result = self.calculator.calculate(weak_stock, strong_benchmark)

        self.assertEqual(weak_result.rs_score, 0.0)


if __name__ == "__main__":
    unittest.main()
