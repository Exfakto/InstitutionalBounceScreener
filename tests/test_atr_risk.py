import unittest

import pandas as pd

from analysis.atr_risk import ATRRiskCalculator


class ATRRiskCalculatorTest(unittest.TestCase):

    def setUp(self):
        self.calculator = ATRRiskCalculator()

    def build_history(self, highs, lows, closes):
        return pd.DataFrame(
            {
                "High": highs,
                "Low": lows,
                "Close": closes,
            },
            index=pd.date_range("2026-01-01", periods=len(closes), freq="B"),
        )

    def test_calculates_atr14_correctly(self):
        history = self.build_history(
            highs=[12.0] * 15,
            lows=[10.0] * 15,
            closes=[11.0] * 15,
        )

        result = self.calculator.calculate(history)

        self.assertAlmostEqual(result.atr14, 2.0)
        self.assertAlmostEqual(result.atr_pct, (2.0 / 11.0) * 100.0)
        self.assertAlmostEqual(result.expected_daily_move_pct, result.atr_pct)
        self.assertAlmostEqual(result.suggested_stop_pct, result.atr_pct * 1.75)
        self.assertEqual(result.warnings, [])

    def test_true_range_uses_previous_close_gaps(self):
        history = self.build_history(
            highs=[10.0, 15.0] + [15.0] * 13,
            lows=[9.0, 14.0] + [14.0] * 13,
            closes=[9.5, 14.5] + [14.5] * 13,
        )

        true_range = self.calculator.true_range(history)

        self.assertAlmostEqual(true_range.iloc[1], 5.5)

    def test_moderate_volatility_scores_best(self):
        moderate = self.calculator.risk_score(2.0)
        low = self.calculator.risk_score(0.2)
        high = self.calculator.risk_score(7.0)

        self.assertGreater(moderate, low)
        self.assertGreater(moderate, high)

    def test_high_volatility_increases_volatility_score_and_penalizes_risk(self):
        low_volatility = self.calculator.volatility_score(1.0)
        high_volatility = self.calculator.volatility_score(8.0)

        self.assertGreater(high_volatility, low_volatility)
        self.assertLess(self.calculator.risk_score(8.0), self.calculator.risk_score(2.0))

    def test_extremely_low_volatility_is_not_perfect(self):
        self.assertLess(self.calculator.risk_score(0.1), 100.0)

    def test_missing_columns_are_safe(self):
        result = self.calculator.calculate(
            pd.DataFrame(
                {"High": [10.0], "Close": [9.0]},
                index=pd.date_range("2026-01-01", periods=1),
            )
        )

        self.assertEqual(result.risk_score, 0.0)
        self.assertIn("Missing required columns: Low", result.warnings)

    def test_insufficient_rows_are_safe(self):
        result = self.calculator.calculate(
            self.build_history(
                highs=[12.0] * 10,
                lows=[10.0] * 10,
                closes=[11.0] * 10,
            )
        )

        self.assertIsNone(result.atr14)
        self.assertEqual(result.risk_score, 0.0)
        self.assertIn("Insufficient history for ATR14", result.warnings)

    def test_missing_history_is_safe(self):
        result = self.calculator.calculate(pd.DataFrame())

        self.assertIsNone(result.atr14)
        self.assertEqual(result.risk_score, 0.0)
        self.assertIn("Missing price history", result.warnings)

    def test_scores_are_clamped(self):
        self.assertEqual(self.calculator.volatility_score(50.0), 100.0)
        self.assertEqual(self.calculator.risk_score(20.0), 0.0)


if __name__ == "__main__":
    unittest.main()
