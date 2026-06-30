import unittest

import pandas as pd

from analysis import (
    BounceScore,
    CompositeScore,
    InstitutionalScore,
    QualityScore,
    SupportScore,
    TechnicalScore,
)
from services.scoring_service import ScoringService


class FakeDetailDatabase:

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
        return pd.DataFrame({"Close": [100, 120]})

    def get_support_levels(self, ticker):
        return [
            {
                "zone_low": 10.0,
                "zone_high": 10.2,
                "zone_mid": 10.1,
                "touches": 3,
                "strength_score": 80.0,
                "distance_from_current_pct": 2.0,
            }
        ]

    def get_bounce_validations(self, ticker):
        return [
            {
                "total_touches": 3,
                "successful_bounces": 2,
                "failed_breakdowns": 1,
                "neutral_touches": 0,
                "bounce_success_rate": 66.7,
                "average_bounce_pct": 8.0,
                "median_bounce_pct": 7.5,
                "average_days_to_bounce_peak": 4,
            }
        ]


class EmptyDetailDatabase(FakeDetailDatabase):

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


class StockDetailDataTest(unittest.TestCase):

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
        service.composite = CompositeScore()
        return service

    def test_get_candidate_detail_returns_read_only_sections(self):
        service = self.build_service(FakeDetailDatabase())

        detail = service.get_candidate_detail("AAPL")

        self.assertEqual(detail["ticker"], "AAPL")
        self.assertEqual(detail["candidate"].ticker, "AAPL")
        self.assertIn("revenue_growth_ttm", detail["fundamentals"])
        self.assertIn("institutional_ownership_pct", detail["institutional"])
        self.assertIn("close", detail["technical"])
        self.assertIn("strength_score", detail["support"])
        self.assertIn("bounce_success_rate", detail["bounce"])

    def test_get_candidate_detail_handles_missing_data(self):
        service = self.build_service(EmptyDetailDatabase())

        detail = service.get_candidate_detail("EMPTY")

        self.assertEqual(detail["ticker"], "EMPTY")
        self.assertEqual(detail["fundamentals"], {})
        self.assertEqual(detail["institutional"], {})
        self.assertEqual(detail["technical"], {})
        self.assertEqual(detail["support"], {})
        self.assertEqual(detail["bounce"], {})


if __name__ == "__main__":
    unittest.main()
