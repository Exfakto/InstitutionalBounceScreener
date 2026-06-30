import unittest

from analysis import BaseScore, ScoreResult, TechnicalScore


class TechnicalScoreTest(unittest.TestCase):

    def test_technical_score_returns_score_result(self):
        result = TechnicalScore().calculate(
            {
                "close": 120,
                "sma20": 110,
                "sma50": 100,
                "sma200": 90,
                "rsi14": 55,
            }
        )

        self.assertIsInstance(result, ScoreResult)
        self.assertEqual(result.name, "technical_score")
        self.assertEqual(result.value, 100.0)

    def test_missing_data_returns_safe_score_with_warnings(self):
        result = TechnicalScore().calculate({})

        self.assertEqual(result.value, 0.0)
        self.assertTrue(result.details["warnings"])

    def test_technical_score_is_score_provider(self):
        self.assertIsInstance(TechnicalScore(), BaseScore)


if __name__ == "__main__":
    unittest.main()
