import unittest

from analysis import BaseScore, QualityScore, ScoreResult


class QualityScoreTest(unittest.TestCase):

    def test_stronger_fundamentals_score_higher(self):
        scorer = QualityScore()
        weak = {
            "revenue_growth_ttm": -5,
            "eps_growth_ttm": -2,
            "roe": 3,
            "gross_margin": 20,
            "free_cash_flow": -100,
            "debt_to_equity": 3,
            "current_ratio": 0.5,
        }
        strong = {
            "revenue_growth_ttm": 25,
            "eps_growth_ttm": 30,
            "roe": 30,
            "gross_margin": 70,
            "free_cash_flow": 1000000,
            "debt_to_equity": 0.2,
            "current_ratio": 2,
        }

        self.assertGreater(
            scorer.calculate(strong).value,
            scorer.calculate(weak).value,
        )

    def test_missing_metrics_do_not_crash(self):
        result = QualityScore().calculate({})

        self.assertIsInstance(result, ScoreResult)
        self.assertGreaterEqual(result.value, 0.0)
        self.assertLessEqual(result.value, 100.0)
        self.assertTrue(result.details["warnings"])

    def test_apply_adds_quality_score_without_mutating_input(self):
        metrics = {"revenue_growth_ttm": 10}

        scored = QualityScore().apply(metrics)

        self.assertIn("quality_score", scored)
        self.assertNotIn("quality_score", metrics)

    def test_quality_score_is_score_provider(self):
        self.assertIsInstance(QualityScore(), BaseScore)


if __name__ == "__main__":
    unittest.main()
