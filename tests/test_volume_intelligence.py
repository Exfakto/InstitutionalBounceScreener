import unittest

import pandas as pd

from analysis.volume_intelligence import VolumeIntelligenceCalculator


class VolumeIntelligenceCalculatorTest(unittest.TestCase):

    def setUp(self):
        self.calculator = VolumeIntelligenceCalculator()

    def build_history(self, close=50.0, volumes=None):
        volumes = volumes or [1_000_000] * 60
        return pd.DataFrame(
            {
                "Close": [close] * len(volumes),
                "Volume": volumes,
            },
            index=pd.date_range("2026-01-01", periods=len(volumes), freq="B"),
        )

    def test_calculates_volume_metrics(self):
        volumes = [1_000_000] * 40 + [2_000_000] * 19 + [3_000_000]
        history = self.build_history(close=50.0, volumes=volumes)

        result = self.calculator.calculate(history)

        self.assertAlmostEqual(result.avg_volume_20, 2_050_000.0)
        self.assertAlmostEqual(result.avg_volume_50, 1_420_000.0)
        self.assertAlmostEqual(result.relative_volume, 3_000_000 / 2_050_000)
        self.assertAlmostEqual(result.dollar_volume, 150_000_000.0)
        self.assertGreater(result.volume_trend_score, 50.0)
        self.assertEqual(result.liquidity_score, 100.0)
        self.assertGreater(result.volume_score, 50.0)
        self.assertEqual(result.warnings, [])

    def test_relative_volume_near_one_is_neutralish(self):
        history = self.build_history(close=25.0, volumes=[1_000_000] * 60)

        result = self.calculator.calculate(history)

        self.assertAlmostEqual(result.relative_volume, 1.0)
        self.assertAlmostEqual(result.volume_trend_score, 50.0)
        self.assertGreater(result.volume_score, 40.0)
        self.assertLess(result.volume_score, 70.0)

    def test_low_relative_volume_lowers_score(self):
        volumes = [1_000_000] * 59 + [500_000]
        history = self.build_history(close=25.0, volumes=volumes)

        result = self.calculator.calculate(history)

        self.assertLess(result.relative_volume, 0.7)
        self.assertLess(result.volume_score, 50.0)

    def test_missing_price_history_returns_safe_result(self):
        result = self.calculator.calculate(pd.DataFrame())

        self.assertIsNone(result.avg_volume_20)
        self.assertIsNone(result.avg_volume_50)
        self.assertIsNone(result.relative_volume)
        self.assertIsNone(result.dollar_volume)
        self.assertEqual(result.volume_score, 0.0)
        self.assertIn("Missing price history", result.warnings)

    def test_missing_required_columns_returns_safe_result(self):
        result = self.calculator.calculate(
            pd.DataFrame(
                {"Close": [10, 11]},
                index=pd.date_range("2026-01-01", periods=2),
            )
        )

        self.assertEqual(result.volume_score, 0.0)
        self.assertIn("Missing required columns: Volume", result.warnings)

    def test_insufficient_data_keeps_safe_partial_result(self):
        history = self.build_history(close=10.0, volumes=[100_000] * 10)

        result = self.calculator.calculate(history)

        self.assertIsNone(result.avg_volume_20)
        self.assertIsNone(result.avg_volume_50)
        self.assertIsNone(result.relative_volume)
        self.assertEqual(result.dollar_volume, 1_000_000.0)
        self.assertEqual(result.volume_score, 0.0)
        self.assertIn("Insufficient history for avg_volume_20", result.warnings)
        self.assertIn("Insufficient history for avg_volume_50", result.warnings)

    def test_scores_are_clamped(self):
        high = self.calculator.calculate(
            self.build_history(close=500.0, volumes=[1_000_000] * 59 + [20_000_000])
        )

        self.assertLessEqual(high.volume_trend_score, 100.0)
        self.assertLessEqual(high.liquidity_score, 100.0)
        self.assertLessEqual(high.volume_score, 100.0)


if __name__ == "__main__":
    unittest.main()
