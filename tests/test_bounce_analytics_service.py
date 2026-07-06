import unittest

from services.bounce_analytics_service import BounceAnalyticsService
from services.candidate_detail_data_service import CandidateDetailDataService


class FakeBounceAnalyticsDatabase:

    cursor = None

    def get_fundamentals(self, ticker):
        return None

    def get_institutional_metrics(self, ticker):
        return None

    def get_technical_indicators(self, ticker):
        return []

    def fetch_latest_ranked_candidates(self):
        return []

    def get_support_levels(self, ticker):
        return [
            {
                "id": 1,
                "ticker": ticker,
                "zone_low": 100.0,
                "zone_high": 102.0,
                "zone_mid": 101.0,
                "touches": 3,
                "strength_score": 90.0,
                "current_price": 110.0,
                "distance_from_current": 8.0,
                "distance_from_current_pct": 7.3,
                "first_touch_date": "2026-01-01",
                "last_touch_date": "2026-01-08",
            }
        ]

    def get_bounce_validations(self, ticker):
        return [
            {
                "support_level_id": 1,
                "ticker": ticker,
                "total_touches": 3,
                "successful_bounces": 2,
                "failed_breakdowns": 1,
                "neutral_touches": 0,
                "bounce_success_rate": 66.7,
                "average_bounce_pct": 5.3,
                "median_bounce_pct": 5.9,
                "average_days_to_bounce_peak": 1.0,
                "current_distance_to_support": 8.0,
                "current_distance_to_support_pct": 7.3,
                "validated_at": "2026-01-09",
            }
        ]

    def fetch_ohlcv(self, ticker, start_date=None, end_date=None):
        return [
            {"date": "2026-01-01", "open": 103, "high": 102, "low": 100, "close": 101, "volume": 1000},
            {"date": "2026-01-02", "open": 104, "high": 108, "low": 104, "close": 107, "volume": 1000},
            {"date": "2026-01-03", "open": 108, "high": 110, "low": 106, "close": 109, "volume": 1000},
            {"date": "2026-01-04", "open": 109, "high": 111, "low": 105, "close": 110, "volume": 1000},
            {"date": "2026-01-05", "open": 103, "high": 101.5, "low": 100.5, "close": 101, "volume": 1000},
            {"date": "2026-01-06", "open": 100, "high": 103, "low": 96, "close": 97, "volume": 1000},
            {"date": "2026-01-07", "open": 103, "high": 110, "low": 105, "close": 108, "volume": 1000},
            {"date": "2026-01-08", "open": 102, "high": 102, "low": 100, "close": 101, "volume": 1000},
            {"date": "2026-01-09", "open": 104, "high": 107, "low": 103, "close": 106, "volume": 1000},
        ]


class EmptyBounceAnalyticsDatabase:

    def get_support_levels(self, ticker):
        return []

    def get_bounce_validations(self, ticker):
        return []

    def fetch_ohlcv(self, ticker, start_date=None, end_date=None):
        return []


class BounceAnalyticsServiceTest(unittest.TestCase):

    def test_generates_complete_bounce_analytics_from_support_and_prices(self):
        analytics = BounceAnalyticsService(
            FakeBounceAnalyticsDatabase()
        ).analytics_for_ticker("AAA")

        self.assertEqual(analytics.primary_support, 101.0)
        self.assertEqual(analytics.support_zone_low, 100.0)
        self.assertEqual(analytics.support_zone_high, 102.0)
        self.assertEqual(analytics.support_width, 2.0)
        self.assertEqual(analytics.distance_from_support_pct, 7.3)
        self.assertEqual(analytics.historical_tests, 3)
        self.assertEqual(analytics.successful_bounces, 2)
        self.assertEqual(analytics.failed_breakdowns, 1)
        self.assertAlmostEqual(analytics.bounce_success_pct, 66.66666666666666)
        self.assertGreater(analytics.average_bounce_pct, 0)
        self.assertGreater(analytics.median_bounce_pct, 0)
        self.assertGreater(analytics.largest_bounce_pct, analytics.average_bounce_pct)
        self.assertEqual(analytics.average_days_to_peak, 1.0)
        self.assertEqual(analytics.most_recent_bounce_date, "2026-01-08")
        self.assertGreaterEqual(analytics.quality_score, 50.0)
        self.assertIn(analytics.quality_label, {"Average", "Good", "Excellent"})

    def test_generates_one_history_record_per_touch(self):
        analytics = BounceAnalyticsService(
            FakeBounceAnalyticsDatabase()
        ).analytics_for_ticker("AAA")

        self.assertEqual(len(analytics.history), 3)
        self.assertEqual(analytics.history[0]["date"], "2026-01-01")
        self.assertEqual(analytics.history[0]["support_price"], 101.0)
        self.assertEqual(analytics.history[0]["low_price"], 100.0)
        self.assertAlmostEqual(analytics.history[0]["peak_price"], 108.0)
        self.assertTrue(analytics.history[0]["successful"])
        self.assertFalse(analytics.history[1]["successful"])
        self.assertEqual(analytics.history[2]["days_to_peak"], 1)

    def test_returns_empty_analytics_when_support_is_missing(self):
        analytics = BounceAnalyticsService(
            EmptyBounceAnalyticsDatabase()
        ).analytics_for_ticker("MISS")

        self.assertEqual(analytics.ticker, "MISS")
        self.assertIsNone(analytics.primary_support)
        self.assertEqual(analytics.historical_tests, 0)
        self.assertEqual(analytics.history, [])
        self.assertEqual(analytics.quality_label, "Weak")

    def test_candidate_detail_uses_bounce_analytics(self):
        detail = CandidateDetailDataService(
            FakeBounceAnalyticsDatabase()
        ).get_candidate_detail("AAA")

        self.assertEqual(detail["metrics"]["support_tests"], 3)
        self.assertEqual(detail["metrics"]["successful_bounces"], 2)
        self.assertEqual(detail["metrics"]["failed_support_breaks"], 1)
        self.assertEqual(detail["metrics"]["support_width"], 2.0)
        self.assertIn(detail["metrics"]["bounce_quality"], {"Average", "Good", "Excellent"})
        self.assertEqual(len(detail["bounce_history"]), 3)
        self.assertEqual(detail["bounce_history"][0]["date"], "2026-01-01")
        self.assertTrue(detail["bounce_history"][0]["successful"])


if __name__ == "__main__":
    unittest.main()
