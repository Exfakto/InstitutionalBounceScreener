import unittest

import pandas as pd

from analysis.trend_strength import TrendStrengthCalculator


class TrendStrengthCalculatorTest(unittest.TestCase):

    def setUp(self):
        self.calculator = TrendStrengthCalculator()

    def build_history(self, closes):
        return pd.DataFrame(
            {"Close": closes},
            index=pd.date_range("2026-01-01", periods=len(closes), freq="B"),
        )

    def test_strong_bullish_trend_scores_high(self):
        result = self.calculator.calculate(
            self.build_history([120]),
            {
                "sma20": 110,
                "sma50": 100,
                "sma200": 90,
            },
        )

        self.assertTrue(result.price_above_sma20)
        self.assertTrue(result.price_above_sma50)
        self.assertTrue(result.price_above_sma200)
        self.assertTrue(result.sma20_above_sma50)
        self.assertTrue(result.sma50_above_sma200)
        self.assertGreaterEqual(result.trend_score, 90.0)

    def test_neutral_mixed_trend_scores_medium(self):
        result = self.calculator.calculate(
            self.build_history([100]),
            {
                "sma20": 101,
                "sma50": 99,
                "sma200": 100,
            },
        )

        self.assertGreater(result.trend_score, 30.0)
        self.assertLess(result.trend_score, 70.0)

    def test_bearish_trend_scores_low(self):
        result = self.calculator.calculate(
            self.build_history([80]),
            {
                "sma20": 90,
                "sma50": 100,
                "sma200": 110,
            },
        )

        self.assertFalse(result.price_above_sma20)
        self.assertFalse(result.sma20_above_sma50)
        self.assertLess(result.trend_score, 20.0)

    def test_calculates_distance_from_moving_averages(self):
        result = self.calculator.calculate(
            self.build_history([110]),
            {
                "sma20": 100,
                "sma50": 100,
                "sma200": 100,
            },
        )

        self.assertAlmostEqual(result.price_vs_sma20_pct, 10.0)
        self.assertAlmostEqual(result.price_vs_sma50_pct, 10.0)
        self.assertAlmostEqual(result.price_vs_sma200_pct, 10.0)

    def test_missing_sma_values_return_warnings(self):
        result = self.calculator.calculate(
            self.build_history([100]),
            {},
        )

        self.assertEqual(result.trend_score, 0.0)
        self.assertIn("Missing sma20", result.warnings)
        self.assertIn("Missing sma50", result.warnings)
        self.assertIn("Missing sma200", result.warnings)

    def test_missing_price_history_is_safe(self):
        result = self.calculator.calculate(pd.DataFrame(), {"sma20": 1})

        self.assertIsNone(result.close_price)
        self.assertEqual(result.trend_score, 0.0)
        self.assertIn("Missing price history", result.warnings)

    def test_missing_close_column_is_safe(self):
        result = self.calculator.calculate(
            pd.DataFrame({"Open": [1]}),
            {
                "sma20": 1,
                "sma50": 1,
                "sma200": 1,
            },
        )

        self.assertIsNone(result.close_price)
        self.assertIn("Missing required columns: Close", result.warnings)

    def test_score_is_clamped(self):
        high = self.calculator.score(
            price_above_sma20=True,
            price_above_sma50=True,
            price_above_sma200=True,
            sma20_above_sma50=True,
            sma50_above_sma200=True,
            distances=[500, 500, 500],
        )
        low = self.calculator.score(
            price_above_sma20=False,
            price_above_sma50=False,
            price_above_sma200=False,
            sma20_above_sma50=False,
            sma50_above_sma200=False,
            distances=[-500, -500, -500],
        )

        self.assertEqual(high, 100.0)
        self.assertEqual(low, 0.0)


if __name__ == "__main__":
    unittest.main()
