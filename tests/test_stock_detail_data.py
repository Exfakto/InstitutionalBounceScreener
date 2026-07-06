import unittest

import pandas as pd
from PySide6.QtWidgets import QApplication

from analysis import (
    BounceScore,
    CompositeScore,
    InstitutionalScore,
    QualityScore,
    SupportScore,
    TechnicalScore,
)
from services.scoring_service import ScoringService
from services.candidate_detail_data_service import CandidateDetailDataService
from ui.candidate_detail_window import CandidateDetailWindow


class FakeUniverseCursor:

    def __init__(self):
        self.params = None

    def execute(self, sql, params):
        self.params = params

    def fetchone(self):
        ticker = self.params[0]
        if ticker == "NEE":
            return {
                "company_name": "NextEra Energy, Inc.",
                "exchange": "NYSE",
                "sector": "Utilities",
                "industry": "Utilities - Regulated Electric",
            }
        return None


class FakeCandidateDetailAnalyticsDatabase:

    def __init__(self):
        self.cursor = FakeUniverseCursor()

    def fetch_ohlcv(self, ticker, start_date=None, end_date=None):
        return [
            {
                "date": "2025-07-08",
                "open": 60.0,
                "high": 62.0,
                "low": 59.5,
                "close": 61.0,
                "volume": 1000000,
            },
            {
                "date": "2026-07-02",
                "open": 72.0,
                "high": 74.5,
                "low": 70.5,
                "close": 73.25,
                "volume": 3456789,
            },
        ]

    def get_fundamentals(self, ticker):
        return None

    def get_institutional_metrics(self, ticker):
        return None

    def get_technical_indicators(self, ticker):
        return [
            {
                "date": "2026-07-02",
                "sma20": 71.2,
                "sma50": 69.8,
                "sma200": 65.4,
                "ema20": 72.1,
                "ema50": 70.4,
                "ema200": 66.2,
                "rsi14": 58.0,
                "atr14": 2.2,
                "macd": 0.84,
                "macd_signal": 0.52,
                "macd_histogram": 0.32,
                "vwap": 71.9,
                "average_volume_20": 3100000,
                "relative_volume": 1.12,
                "distance_from_ema20": 1.59,
                "distance_from_ema50": 4.05,
                "distance_from_ema200": 10.65,
                "relative_strength_spy": None,
                "trend": "Bullish",
                "market_structure": "Strong Bullish Structure",
            }
        ]

    def get_support_levels(self, ticker):
        return [
            {
                "zone_low": 68.0,
                "zone_high": 69.5,
                "zone_mid": 68.75,
                "touches": 5,
                "strength_score": 88.0,
                "current_price": 73.25,
                "distance_from_current": 4.5,
                "distance_from_current_pct": 6.1,
                "first_touch_date": "2025-09-15",
                "last_touch_date": "2026-06-20",
            }
        ]

    def get_bounce_validations(self, ticker):
        return [
            {
                "support_level_id": 1,
                "ticker": ticker,
                "total_touches": 5,
                "successful_bounces": 4,
                "failed_breakdowns": 1,
                "neutral_touches": 0,
                "bounce_success_rate": 80.0,
                "average_bounce_pct": 7.4,
                "median_bounce_pct": 6.8,
                "average_days_to_bounce_peak": 9,
                "current_distance_to_support": 4.5,
                "current_distance_to_support_pct": 6.1,
                "validated_at": "2026-06-21",
            }
        ]

    def fetch_latest_ranked_candidates(self):
        return []


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

    def fetch_ohlcv(self, ticker, start_date=None, end_date=None):
        return [
            {"date": "2026-07-01", "close": 100},
            {"date": "2026-07-02", "close": 120},
        ]

    def get_technical_indicators(self, ticker):
        return [
            {
                "date": "2026-07-02",
                "sma20": 110,
                "sma50": 105,
                "sma200": 95,
                "rsi14": 62,
            }
        ]

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

    def fetch_ohlcv(self, ticker, start_date=None, end_date=None):
        return []

    def get_technical_indicators(self, ticker):
        return []

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
        self.assertEqual(
            detail["institutional"]["status"],
            "Institutional data not configured",
        )
        self.assertEqual(detail["technical"], {})
        self.assertEqual(detail["support"], {})
        self.assertEqual(detail["bounce"], {})

    def test_nee_candidate_detail_populates_existing_analytics(self):
        service = CandidateDetailDataService(FakeCandidateDetailAnalyticsDatabase())

        detail = service.get_candidate_detail("NEE")

        self.assertEqual(detail["company_name"], "NextEra Energy, Inc.")
        self.assertEqual(detail["exchange"], "NYSE")
        self.assertEqual(detail["metrics"]["current_price"], 73.25)
        self.assertEqual(detail["metrics"]["latest_close_date"], "2026-07-02")
        self.assertEqual(detail["metrics"]["latest_volume"], 3456789)
        self.assertEqual(detail["metrics"]["week_52_high"], 74.5)
        self.assertEqual(detail["metrics"]["week_52_low"], 59.5)
        self.assertEqual(detail["metrics"]["primary_support"], 68.75)
        self.assertEqual(detail["metrics"]["support_zone_low"], 68.0)
        self.assertEqual(detail["metrics"]["support_zone_high"], 69.5)
        self.assertEqual(detail["metrics"]["support_strength_score"], 88.0)
        self.assertEqual(detail["metrics"]["distance_to_support_pct"], 6.1)
        self.assertEqual(detail["metrics"]["bounce_success_pct"], 80.0)
        self.assertEqual(detail["metrics"]["support_tests"], 5)
        self.assertEqual(detail["metrics"]["average_bounce"], 7.4)
        self.assertEqual(detail["metrics"]["latest_bounce_date"], "2026-06-21")
        self.assertEqual(detail["technical"]["ema20"], 72.1)
        self.assertEqual(detail["technical"]["ema50"], 70.4)
        self.assertEqual(detail["technical"]["ema200"], 66.2)
        self.assertEqual(detail["technical"]["trend"], "Bullish")
        self.assertEqual(
            detail["technical"]["market_structure"],
            "Strong Bullish Structure",
        )
        self.assertEqual(
            detail["institutional"]["status"],
            "Institutional data not configured",
        )

    def test_nee_candidate_detail_window_has_no_blank_analytics_tabs(self):
        app = QApplication.instance() or QApplication([])
        service = CandidateDetailDataService(FakeCandidateDetailAnalyticsDatabase())
        detail = service.get_candidate_detail("NEE")

        window = CandidateDetailWindow(detail=detail)

        self.assertEqual(window.summary_labels["company_name"].text(), "NextEra Energy, Inc.")
        self.assertEqual(window.summary_labels["current_price"].text(), "$73.25")
        self.assertEqual(window.summary_labels["latest_volume"].text(), "3,456,789")
        self.assertEqual(window.summary_labels["week_52_high"].text(), "$74.50")
        self.assertEqual(window.summary_labels["primary_support"].text(), "$68.75")
        self.assertEqual(window.technical_labels["trend"].text(), "Bullish")
        self.assertEqual(
            window.technical_labels["market_structure"].text(),
            "Strong Bullish Structure",
        )
        self.assertEqual(window.technical_labels["ema20"].text(), "$72.10")
        self.assertEqual(window.technical_labels["ema50"].text(), "$70.40")
        self.assertEqual(window.technical_labels["ema200"].text(), "$66.20")
        self.assertEqual(window.technical_labels["rsi"].text(), "58.0 (Bullish)")
        self.assertEqual(window.technical_labels["macd"].text(), "0.8 (Bullish)")
        self.assertEqual(window.technical_labels["atr"].text(), "2.2")
        self.assertEqual(window.technical_labels["vwap"].text(), "$71.90")
        self.assertEqual(window.technical_labels["relative_volume"].text(), "1.1")
        self.assertEqual(window.technical_labels["distance_from_ema20"].text(), "1.6%")
        self.assertEqual(window.technical_labels["relative_strength"].text(), "Coming in v2.2")
        self.assertEqual(window.bounce_summary_labels["support_tests"].text(), "5")
        self.assertEqual(window.bounce_summary_labels["success_pct"].text(), "80.0%")
        self.assertEqual(window.bounce_summary_labels["average_bounce"].text(), "7.4%")
        self.assertEqual(window.bounce_summary_labels["most_recent_bounce"].text(), "2026-06-21")
        self.assertGreater(window.bounce_history_table.rowCount(), 0)
        self.assertNotEqual(window.technical_summary_label.text(), "Data not available")
        self.assertIsNotNone(app)


if __name__ == "__main__":
    unittest.main()
