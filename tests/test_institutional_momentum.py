import unittest

from analysis.institutional_momentum import InstitutionalMomentumCalculator


class InstitutionalMomentumCalculatorTest(unittest.TestCase):

    def setUp(self):
        self.calculator = InstitutionalMomentumCalculator()

    def test_increasing_ownership_scores_higher(self):
        result = self.calculator.calculate(
            current_ownership=65,
            previous_ownership=60,
            ownership_history=[55, 60, 65],
            insider_metrics={"new_large_buyers": 2},
        )

        self.assertEqual(result.ownership_trend, "increasing")
        self.assertEqual(result.ownership_change_pct, 5.0)
        self.assertGreater(result.momentum_score, 70.0)

    def test_decreasing_ownership_scores_lower(self):
        result = self.calculator.calculate(
            current_ownership=50,
            previous_ownership=60,
            ownership_history=[70, 60, 50],
            insider_metrics={"new_large_sellers": 3},
        )

        self.assertEqual(result.ownership_trend, "decreasing")
        self.assertLess(result.momentum_score, 40.0)

    def test_flat_ownership_scores_near_neutral(self):
        result = self.calculator.calculate(
            current_ownership=60,
            previous_ownership=60,
            ownership_history=[60, 60, 60],
            insider_metrics={},
        )

        self.assertEqual(result.ownership_trend, "flat")
        self.assertEqual(result.momentum_score, 50.0)

    def test_multiple_accumulation_quarters_improve_score(self):
        one_quarter = self.calculator.calculate(62, 60, [60, 62], {})
        multiple_quarters = self.calculator.calculate(66, 64, [58, 60, 62, 64, 66], {})

        self.assertGreater(
            multiple_quarters.consecutive_increase_quarters,
            one_quarter.consecutive_increase_quarters,
        )
        self.assertGreater(multiple_quarters.momentum_score, one_quarter.momentum_score)

    def test_multiple_distribution_quarters_reduce_score(self):
        one_quarter = self.calculator.calculate(58, 60, [60, 58], {})
        multiple_quarters = self.calculator.calculate(52, 54, [60, 58, 56, 54, 52], {})

        self.assertGreater(
            multiple_quarters.consecutive_decrease_quarters,
            one_quarter.consecutive_decrease_quarters,
        )
        self.assertLess(multiple_quarters.momentum_score, one_quarter.momentum_score)

    def test_insider_buying_improves_score(self):
        no_buying = self.calculator.calculate(60, 60, [60, 60], {})
        buying = self.calculator.calculate(
            60,
            60,
            [60, 60],
            {"insider_buying_flag": 1},
        )

        self.assertGreater(buying.insider_buying_score, 0.0)
        self.assertGreater(buying.momentum_score, no_buying.momentum_score)

    def test_insider_selling_reduces_score(self):
        no_selling = self.calculator.calculate(60, 60, [60, 60], {})
        selling = self.calculator.calculate(
            60,
            60,
            [60, 60],
            {"insider_selling_flag": 1},
        )

        self.assertGreater(selling.insider_selling_score, 0.0)
        self.assertLess(selling.momentum_score, no_selling.momentum_score)

    def test_missing_ownership_history_is_safe(self):
        result = self.calculator.calculate(None, None, None, {})

        self.assertIsNone(result.current_ownership_pct)
        self.assertEqual(result.ownership_trend, "unknown")
        self.assertIn("Missing current institutional ownership", result.warnings)
        self.assertIn("Missing ownership history", result.warnings)

    def test_missing_insider_data_is_safe(self):
        result = self.calculator.calculate(60, 58, [58, 60], None)

        self.assertGreater(result.momentum_score, 50.0)
        self.assertIn("Missing insider metrics", result.warnings)

    def test_score_is_clamped(self):
        high = self.calculator.momentum_score(100, 20, 0, 100, 0, 100, 0)
        low = self.calculator.momentum_score(-100, 0, 20, 0, 100, 0, 100)

        self.assertEqual(high, 100.0)
        self.assertEqual(low, 0.0)


if __name__ == "__main__":
    unittest.main()
