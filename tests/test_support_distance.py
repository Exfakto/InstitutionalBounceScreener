import unittest

from analysis.support_distance import SupportDistanceCalculator


class SupportDistanceCalculatorTest(unittest.TestCase):

    def setUp(self):
        self.calculator = SupportDistanceCalculator()

    def zone(self, low=98.0, high=100.0, mid=99.0, strength=80.0, zone_id=1):
        return {
            "id": zone_id,
            "zone_low": low,
            "zone_high": high,
            "zone_mid": mid,
            "strength_score": strength,
        }

    def bounce(self, support_level_id=1, success=75.0, avg=8.0):
        return {
            "support_level_id": support_level_id,
            "bounce_success_rate": success,
            "average_bounce_pct": avg,
        }

    def test_price_inside_support_zone_scores_high(self):
        result = self.calculator.calculate(
            99.0,
            [self.zone()],
            [self.bounce()],
        )

        self.assertEqual(result.distance_to_support_pct, 0.0)
        self.assertEqual(result.distance_to_support_abs, 0.0)
        self.assertGreater(result.entry_quality_score, 90.0)

    def test_price_one_percent_above_support_scores_high(self):
        result = self.calculator.calculate(
            101.0,
            [self.zone()],
            [self.bounce()],
        )

        self.assertAlmostEqual(result.distance_to_support_abs, 1.0)
        self.assertAlmostEqual(result.distance_to_support_pct, 1.0 / 101.0 * 100.0)
        self.assertGreater(result.entry_quality_score, 85.0)

    def test_price_three_percent_above_support_scores_moderate(self):
        result = self.calculator.calculate(
            103.0,
            [self.zone()],
            [self.bounce()],
        )

        self.assertGreater(result.entry_quality_score, 60.0)
        self.assertLess(result.entry_quality_score, 90.0)

    def test_price_far_above_support_scores_lower(self):
        result = self.calculator.calculate(
            120.0,
            [self.zone()],
            [self.bounce()],
        )

        self.assertLess(result.entry_quality_score, 60.0)

    def test_multiple_support_zones_choose_smallest_distance(self):
        result = self.calculator.calculate(
            111.0,
            [
                self.zone(low=80, high=82, mid=81, zone_id=1),
                self.zone(low=108, high=110, mid=109, zone_id=2),
            ],
            [self.bounce(support_level_id=2)],
        )

        self.assertEqual(result.nearest_support_mid, 109.0)
        self.assertAlmostEqual(result.distance_to_support_abs, 1.0)

    def test_support_zones_above_price_only_are_safe(self):
        result = self.calculator.calculate(
            90.0,
            [self.zone(low=98, high=100, mid=99)],
            [],
        )

        self.assertIsNone(result.nearest_support_mid)
        self.assertEqual(result.entry_quality_score, 0.0)
        self.assertIn("No support zones below or near current price", result.warnings)

    def test_missing_current_price_is_safe(self):
        result = self.calculator.calculate(None, [self.zone()], [self.bounce()])

        self.assertIsNone(result.current_price)
        self.assertEqual(result.entry_quality_score, 0.0)
        self.assertIn("Missing current price", result.warnings)

    def test_no_support_zones_is_safe(self):
        result = self.calculator.calculate(100.0, [], [self.bounce()])

        self.assertEqual(result.current_price, 100.0)
        self.assertEqual(result.entry_quality_score, 0.0)
        self.assertIn("No support zones available", result.warnings)

    def test_missing_bounce_metrics_does_not_crash(self):
        result = self.calculator.calculate(101.0, [self.zone()], [])

        self.assertIsNone(result.bounce_success_rate)
        self.assertIsNone(result.average_bounce_pct)
        self.assertGreater(result.entry_quality_score, 0.0)
        self.assertIn("Missing bounce validation metrics", result.warnings)

    def test_risk_reward_estimate_uses_average_bounce(self):
        result = self.calculator.calculate(
            104.0,
            [self.zone()],
            [self.bounce(avg=12.0)],
        )

        self.assertGreater(result.risk_reward_estimate, 0.0)

    def test_scores_are_clamped(self):
        self.assertEqual(
            self.calculator.entry_quality_score(0.0, 1000.0, 1000.0, 1000.0),
            100.0,
        )
        self.assertEqual(
            self.calculator.risk_reward_estimate(1000.0, 0.0),
            100.0,
        )


if __name__ == "__main__":
    unittest.main()
