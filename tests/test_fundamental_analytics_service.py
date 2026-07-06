import unittest

from services.candidate_detail_data_service import CandidateDetailDataService
from services.fundamental_analytics_service import FundamentalAnalyticsService


class StrongFundamentalDatabase:

    cursor = None

    def fetch_fundamental_data(self, ticker):
        return {
            "ticker": ticker,
            "company_name": "Quality Compounder",
            "market_cap": 50_000_000_000,
            "revenue": 10_000_000_000,
            "gross_profit": 6_500_000_000,
            "operating_income": 3_200_000_000,
            "net_income": 2_200_000_000,
            "ebitda": 3_700_000_000,
            "enterprise_value": 55_000_000_000,
            "revenue_growth_ttm": 18.0,
            "eps_growth_ttm": 24.0,
            "roe": 28.0,
            "roa": 13.0,
            "gross_margin": 65.0,
            "free_cash_flow": 1_900_000_000,
            "debt_to_equity": 0.35,
            "current_ratio": 2.4,
            "quick_ratio": 1.8,
            "interest_coverage": 14.0,
            "forward_pe": 18.0,
            "trailing_pe": 21.0,
        }

    def get_fundamentals(self, ticker):
        return self.fetch_fundamental_data(ticker)

    def fetch_ohlcv(self, ticker, start_date=None, end_date=None):
        return []

    def get_technical_indicators(self, ticker):
        return []

    def get_support_levels(self, ticker):
        return []

    def get_bounce_validations(self, ticker):
        return []

    def get_institutional_metrics(self, ticker):
        return None

    def fetch_latest_ranked_candidates(self):
        return []


class WeakFundamentalDatabase(StrongFundamentalDatabase):

    def fetch_fundamental_data(self, ticker):
        return {
            "ticker": ticker,
            "revenue": 5_000_000_000,
            "gross_profit": 900_000_000,
            "operating_income": -100_000_000,
            "net_income": -250_000_000,
            "revenue_growth_ttm": -8.0,
            "eps_growth_ttm": -20.0,
            "roe": -5.0,
            "gross_margin": 18.0,
            "free_cash_flow": -300_000_000,
            "debt_to_equity": 3.4,
            "current_ratio": 0.7,
            "interest_coverage": 0.8,
            "trailing_pe": 60.0,
        }


class FundamentalAnalyticsServiceTest(unittest.TestCase):

    def test_strong_fundamentals_generate_intelligence_scores_and_flags(self):
        analytics = FundamentalAnalyticsService(
            StrongFundamentalDatabase()
        ).analytics_for_ticker("AAA")

        self.assertGreaterEqual(analytics.intelligence_score, 75.0)
        self.assertIn(analytics.classification, {"Strong", "Excellent", "Elite"})
        self.assertGreaterEqual(analytics.scores["profitability_score"], 80.0)
        self.assertGreaterEqual(analytics.scores["liquidity_score"], 80.0)
        self.assertGreaterEqual(analytics.scores["leverage_score"], 80.0)
        self.assertIn("Strong Balance Sheet", analytics.flags)
        self.assertIn("High Profitability", analytics.flags)
        self.assertIn("Excellent Capital Allocation", analytics.flags)
        self.assertIn("strong revenue and earnings expansion", analytics.commentary)
        self.assertGreaterEqual(len(analytics.research_summary.split(". ")), 5)

    def test_weak_fundamentals_generate_risk_flags(self):
        analytics = FundamentalAnalyticsService(
            WeakFundamentalDatabase()
        ).analytics_for_ticker("WEAK")

        self.assertLess(analytics.intelligence_score, 50.0)
        self.assertIn(analytics.classification, {"Weak", "Critical"})
        self.assertIn("Negative Cash Flow", analytics.flags)
        self.assertIn("Aggressive Leverage", analytics.flags)
        self.assertIn("Declining Revenue", analytics.flags)
        metrics = analytics.as_metrics()
        self.assertEqual(metrics["excessive_debt"], 1)
        self.assertIn(metrics["risk_rating"], {"High", "Elevated"})

    def test_candidate_detail_receives_fundamental_analytics(self):
        detail = CandidateDetailDataService(
            StrongFundamentalDatabase()
        ).get_candidate_detail("AAA")

        self.assertIn("fundamental_intelligence_score", detail["fundamentals"])
        self.assertIn("liquidity_score", detail["fundamentals"])
        self.assertIn("fundamental_research_summary", detail["fundamentals"])
        self.assertEqual(detail["risk"]["risk_rating"], detail["metrics"]["risk_rating"])
        self.assertEqual(detail["risk"]["excessive_debt"], 0)
        self.assertIn("Fundamental Intelligence", detail["candidate"].summary)


if __name__ == "__main__":
    unittest.main()
