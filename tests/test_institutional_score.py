import unittest

from analysis import BaseScore, InstitutionalScore, ScoreResult


class InstitutionalScoreTest(unittest.TestCase):

    def test_positive_institutional_metrics_score_higher(self):
        scorer = InstitutionalScore()
        weak = {
            "institutional_ownership_pct": 5,
            "institutional_ownership_change_qoq": -1,
            "net_institutional_buying": -100,
            "insider_buying_flag": 0,
            "insider_selling_flag": 1,
        }
        strong = {
            "institutional_ownership_pct": 75,
            "institutional_ownership_change_qoq": 4,
            "net_institutional_buying": 1000000,
            "insider_buying_flag": 1,
            "insider_selling_flag": 0,
        }

        self.assertGreater(
            scorer.calculate(strong).value,
            scorer.calculate(weak).value,
        )

    def test_missing_metrics_do_not_crash(self):
        result = InstitutionalScore().calculate({})

        self.assertIsInstance(result, ScoreResult)
        self.assertGreaterEqual(result.value, 0.0)
        self.assertLessEqual(result.value, 100.0)
        self.assertTrue(result.details["warnings"])

    def test_apply_adds_institutional_score_without_mutating_input(self):
        metrics = {"institutional_ownership_pct": 50}

        scored = InstitutionalScore().apply(metrics)

        self.assertIn("institutional_score", scored)
        self.assertNotIn("institutional_score", metrics)

    def test_institutional_score_is_score_provider(self):
        self.assertIsInstance(InstitutionalScore(), BaseScore)


if __name__ == "__main__":
    unittest.main()
