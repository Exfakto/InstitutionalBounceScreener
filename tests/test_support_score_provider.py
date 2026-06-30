import unittest

from analysis import BaseScore, ScoreResult, SupportScore


class SupportScoreProviderTest(unittest.TestCase):

    def test_support_score_returns_score_result(self):
        result = SupportScore().calculate(
            {
                "strength_score": 80,
                "touches": 4,
                "distance_from_current_pct": 3,
            }
        )

        self.assertIsInstance(result, ScoreResult)
        self.assertEqual(result.name, "support_score")
        self.assertGreater(result.value, 0)
        self.assertLessEqual(result.value, 100)

    def test_missing_data_returns_safe_score_with_warnings(self):
        result = SupportScore().calculate({})

        self.assertEqual(result.value, 20.0)
        self.assertTrue(result.details["warnings"])

    def test_support_score_is_score_provider(self):
        self.assertIsInstance(SupportScore(), BaseScore)


if __name__ == "__main__":
    unittest.main()
