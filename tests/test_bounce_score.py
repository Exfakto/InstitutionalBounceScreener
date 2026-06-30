import unittest

from analysis import BaseScore, BounceScore, ScoreResult


class BounceScoreTest(unittest.TestCase):

    def test_bounce_score_returns_score_result(self):
        result = BounceScore().calculate(
            {
                "bounce_success_rate": 80,
                "average_bounce_pct": 8,
                "total_touches": 4,
                "failed_breakdowns": 1,
            }
        )

        self.assertIsInstance(result, ScoreResult)
        self.assertEqual(result.name, "bounce_score")
        self.assertGreater(result.value, 0)
        self.assertLessEqual(result.value, 100)

    def test_missing_data_returns_safe_score_with_warnings(self):
        result = BounceScore().calculate({})

        self.assertEqual(result.value, 0.0)
        self.assertTrue(result.details["warnings"])

    def test_bounce_score_is_score_provider(self):
        self.assertIsInstance(BounceScore(), BaseScore)


if __name__ == "__main__":
    unittest.main()
