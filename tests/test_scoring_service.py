import unittest

import pandas as pd

from analysis import (
    BounceScore,
    CandidateScore,
    InstitutionalScore,
    QualityScore,
    ScoreResult,
    SupportScore,
    TechnicalScore,
)
from services.scoring_service import ScoringService


class FakeScoringDatabase:

    def __init__(self):
        self.closed = False

    def get_fundamentals(self, ticker):
        return {
            "ticker": ticker,
            "revenue_growth_ttm": 20,
            "eps_growth_ttm": 20,
            "roe": 25,
            "gross_margin": 60,
            "free_cash_flow": 100,
            "debt_to_equity": 0.2,
            "current_ratio": 2,
        }

    def get_institutional_metrics(self, ticker):
        return {
            "ticker": ticker,
            "institutional_ownership_pct": 70,
            "institutional_ownership_change_qoq": 3,
            "net_institutional_buying": 100,
            "insider_buying_flag": 1,
            "insider_selling_flag": 0,
        }

    def get_price_history(self, ticker):
        return pd.DataFrame(
            {
                "Close": [100, 120],
            }
        )

    def get_support_levels(self, ticker):
        return [
            {
                "strength_score": 80,
                "touches": 4,
                "distance_from_current_pct": 3,
            }
        ]

    def get_bounce_validations(self, ticker):
        return [
            {
                "bounce_success_rate": 80,
                "average_bounce_pct": 8,
                "total_touches": 4,
                "failed_breakdowns": 1,
            }
        ]

    def close(self):
        self.closed = True


class EmptyScoringDatabase(FakeScoringDatabase):

    def get_fundamentals(self, ticker):
        return None

    def get_institutional_metrics(self, ticker):
        return None

    def get_price_history(self, ticker):
        return pd.DataFrame()

    def get_support_levels(self, ticker):
        return []

    def get_bounce_validations(self, ticker):
        return []


class TestCompositeScore:

    def calculate(self, context):
        values = [
            context["quality_score"].value,
            context["institutional_score"].value,
            context["technical_score"].value,
            context["support_score"].value,
            context["bounce_score"].value,
        ]

        return ScoreResult(
            name="composite_score",
            value=sum(values) / len(values),
        )


class ScoringServiceTest(unittest.TestCase):

    def build_service(self, database):
        service = ScoringService.__new__(ScoringService)
        service.db = database
        service.providers = [
            QualityScore(),
            InstitutionalScore(),
            TechnicalScore(),
            SupportScore(),
            BounceScore(),
        ]
        service.composite = TestCompositeScore()
        return service

    def test_score_candidate_returns_candidate_score(self):
        service = self.build_service(FakeScoringDatabase())

        candidate = service.score_candidate("AAPL")

        self.assertIsInstance(candidate, CandidateScore)
        self.assertEqual(candidate.ticker, "AAPL")
        self.assertEqual(len(candidate.scores), 5)
        self.assertIn("quality_score", candidate.score_map)
        self.assertIn("institutional_score", candidate.score_map)
        self.assertIn("technical_score", candidate.score_map)
        self.assertIn("support_score", candidate.score_map)
        self.assertIn("bounce_score", candidate.score_map)
        self.assertEqual(candidate.composite_score.name, "composite_score")

    def test_missing_data_does_not_crash(self):
        service = self.build_service(EmptyScoringDatabase())

        candidate = service.score_candidate("EMPTY")

        self.assertEqual(candidate.ticker, "EMPTY")
        self.assertEqual(len(candidate.scores), 5)
        self.assertGreaterEqual(candidate.composite_score.value, 0.0)

    def test_close_closes_database(self):
        database = FakeScoringDatabase()
        service = self.build_service(database)

        service.close()

        self.assertTrue(database.closed)


if __name__ == "__main__":
    unittest.main()
