import unittest

from services.candidate_detail_data_service import CandidateDetailDataService
from services.risk_analytics_service import RiskAnalyticsService


def low_risk_metrics():
    return {
        "ticker": "SAFE",
        "current_price": 100.0,
        "ema200": 80.0,
        "trend": "Bullish",
        "market_structure": "Strong Bullish Structure",
        "atr14": 2.0,
        "latest_volume": 3_000_000,
        "relative_volume": 1.1,
        "distance_to_support_pct": 3.0,
        "bounce_success_pct": 88.0,
        "support_tests": 6,
        "support_strength_score": 90.0,
        "fundamental_intelligence_score": 86.0,
        "debt_to_equity": 0.4,
    }


def high_risk_metrics():
    return {
        "ticker": "RISK",
        "current_price": 100.0,
        "ema200": 120.0,
        "trend": "Bearish",
        "market_structure": "Strong Bearish Structure",
        "atr14": 12.0,
        "latest_volume": 50_000,
        "relative_volume": 3.4,
        "distance_to_support_pct": 18.0,
        "bounce_success_pct": 35.0,
        "support_tests": 2,
        "support_strength_score": 35.0,
        "fundamental_intelligence_score": 28.0,
        "debt_to_equity": 3.2,
        "earnings_within_7_days": 1,
    }


class RiskDetailDatabase:

    cursor = None

    def get_fundamentals(self, ticker):
        return {
            "ticker": ticker,
            "revenue_growth_ttm": 18.0,
            "eps_growth_ttm": 24.0,
            "roe": 28.0,
            "gross_margin": 65.0,
            "free_cash_flow": 1_900_000_000,
            "debt_to_equity": 0.4,
            "current_ratio": 2.4,
        }

    def fetch_fundamental_data(self, ticker):
        return self.get_fundamentals(ticker)

    def fetch_ohlcv(self, ticker, start_date=None, end_date=None):
        return [
            {"date": "2026-07-01", "open": 98, "high": 101, "low": 97, "close": 100, "volume": 3_000_000}
        ]

    def get_technical_indicators(self, ticker):
        return [
            {
                "date": "2026-07-01",
                "ema200": 80.0,
                "atr14": 2.0,
                "relative_volume": 1.1,
                "trend": "Bullish",
                "market_structure": "Strong Bullish Structure",
            }
        ]

    def get_support_levels(self, ticker):
        return [
            {
                "id": 1,
                "ticker": ticker,
                "zone_low": 94.0,
                "zone_high": 96.0,
                "zone_mid": 95.0,
                "touches": 6,
                "strength_score": 90.0,
                "current_price": 100.0,
                "distance_from_current": 4.0,
                "distance_from_current_pct": 4.0,
            }
        ]

    def get_bounce_validations(self, ticker):
        return [
            {
                "support_level_id": 1,
                "ticker": ticker,
                "total_touches": 6,
                "successful_bounces": 5,
                "failed_breakdowns": 1,
                "neutral_touches": 0,
                "bounce_success_rate": 83.3,
                "average_bounce_pct": 7.0,
                "median_bounce_pct": 6.5,
                "average_days_to_bounce_peak": 4,
            }
        ]

    def get_institutional_metrics(self, ticker):
        return None

    def fetch_latest_ranked_candidates(self):
        return []


class RiskAnalyticsServiceTest(unittest.TestCase):

    def test_low_risk_profile_generates_acceptably_low_score(self):
        analytics = RiskAnalyticsService().analytics_for_metrics(
            "SAFE",
            low_risk_metrics(),
        )

        self.assertLess(analytics.risk_score, 40.0)
        self.assertIn(analytics.risk_class, {"Very Low", "Low"})
        self.assertIn(
            analytics.recommendation,
            {"Excellent Risk", "Acceptable Risk"},
        )
        self.assertEqual(analytics.flags, [])
        self.assertIn("Technical momentum remains constructive", analytics.commentary)

    def test_high_risk_profile_generates_flags_and_avoid_recommendation(self):
        analytics = RiskAnalyticsService().analytics_for_metrics(
            "RISK",
            high_risk_metrics(),
        )

        self.assertGreaterEqual(analytics.risk_score, 70.0)
        self.assertIn(analytics.risk_class, {"High", "Very High"})
        self.assertIn(analytics.recommendation, {"High Risk", "Avoid"})
        self.assertIn("Weak Support", analytics.flags)
        self.assertIn("Extended Above Support", analytics.flags)
        self.assertIn("High ATR", analytics.flags)
        self.assertIn("Bearish Trend", analytics.flags)
        self.assertIn("Weak Fundamentals", analytics.flags)
        self.assertIn("Low Liquidity", analytics.flags)
        self.assertIn("High Failure Probability", analytics.flags)

    def test_candidate_detail_receives_risk_analytics(self):
        detail = CandidateDetailDataService(RiskDetailDatabase()).get_candidate_detail("SAFE")

        self.assertIn("overall_risk_score", detail["risk"])
        self.assertIn("risk_recommendation", detail["risk"])
        self.assertIn("risk_commentary", detail["risk"])
        self.assertEqual(detail["risk"]["risk_rating"], detail["metrics"]["risk_rating"])
        self.assertEqual(detail["candidate"].risk_rating, detail["metrics"]["risk_rating"])
        self.assertIn("Risk Intelligence Score", detail["candidate"].summary)


if __name__ == "__main__":
    unittest.main()
