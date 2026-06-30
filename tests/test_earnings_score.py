import unittest

from analysis.earnings_score import EarningsScore
from analysis.score_result import ScoreResult


class EarningsScoreTest(unittest.TestCase):

    def setUp(self):
        self.score = EarningsScore()

    def test_near_earnings_scores_lower(self):
        result = self.score.calculate(
            {
                "days_until_earnings": 5,
                "eps_surprise_pct": 0,
                "revenue_surprise_pct": 0,
            }
        )

        self.assertIsInstance(result, ScoreResult)
        self.assertLess(result.value, 50.0)

    def test_moderate_window_scores_neutralish(self):
        result = self.score.calculate(
            {
                "days_until_earnings": 10,
                "eps_surprise_pct": 0,
                "revenue_surprise_pct": 0,
            }
        )

        self.assertEqual(result.value, 55.0)

    def test_far_earnings_scores_higher(self):
        result = self.score.calculate(
            {
                "days_until_earnings": 30,
                "eps_surprise_pct": 0,
                "revenue_surprise_pct": 0,
            }
        )

        self.assertGreater(result.value, 70.0)

    def test_positive_surprises_improve_score(self):
        neutral = self.score.calculate(
            {
                "days_until_earnings": 30,
                "eps_surprise_pct": 0,
                "revenue_surprise_pct": 0,
            }
        )
        positive = self.score.calculate(
            {
                "days_until_earnings": 30,
                "eps_surprise_pct": 10,
                "revenue_surprise_pct": 10,
            }
        )

        self.assertGreater(positive.value, neutral.value)

    def test_negative_surprises_reduce_score(self):
        neutral = self.score.calculate(
            {
                "days_until_earnings": 30,
                "eps_surprise_pct": 0,
                "revenue_surprise_pct": 0,
            }
        )
        negative = self.score.calculate(
            {
                "days_until_earnings": 30,
                "eps_surprise_pct": -10,
                "revenue_surprise_pct": -10,
            }
        )

        self.assertLess(negative.value, neutral.value)

    def test_missing_values_are_safe(self):
        result = self.score.calculate({})

        self.assertEqual(result.value, 50.0)
        self.assertIn("Missing days_until_earnings", result.details["warnings"])

    def test_score_is_clamped(self):
        high = self.score.calculate(
            {
                "days_until_earnings": 30,
                "eps_surprise_pct": 100,
                "revenue_surprise_pct": 100,
            }
        )
        low = self.score.calculate(
            {
                "days_until_earnings": 1,
                "eps_surprise_pct": -100,
                "revenue_surprise_pct": -100,
            }
        )

        self.assertEqual(high.value, 95.0)
        self.assertEqual(low.value, 0.0)


if __name__ == "__main__":
    unittest.main()
