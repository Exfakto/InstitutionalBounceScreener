import unittest

import pandas as pd

from analysis.support_distance import SupportDistanceCalculator
from services.support_distance_service import SupportDistanceService


class FakeSupportDistanceDatabase:

    def __init__(self, histories, supports=None, bounces=None):
        self.histories = histories
        self.supports = supports or {}
        self.bounces = bounces or {}
        self.closed = False

    def get_all_tickers(self):
        return ["AAA", "BBB", "EMPTY"]

    def get_price_history(self, ticker):
        return self.histories.get(ticker, pd.DataFrame())

    def get_support_levels(self, ticker):
        return self.supports.get(ticker, [])

    def get_bounce_validations(self, ticker):
        return self.bounces.get(ticker, [])

    def close(self):
        self.closed = True


class SupportDistanceServiceTest(unittest.TestCase):

    def build_history(self, close):
        return pd.DataFrame(
            {"Close": [close]},
            index=pd.date_range("2026-01-01", periods=1),
        )

    def zone(self, low=98.0, high=100.0, mid=99.0, zone_id=1):
        return {
            "id": zone_id,
            "zone_low": low,
            "zone_high": high,
            "zone_mid": mid,
            "strength_score": 80.0,
        }

    def bounce(self, support_level_id=1):
        return {
            "support_level_id": support_level_id,
            "bounce_success_rate": 75.0,
            "average_bounce_pct": 8.0,
        }

    def build_service(self, histories, supports=None, bounces=None):
        service = SupportDistanceService.__new__(SupportDistanceService)
        service.db = FakeSupportDistanceDatabase(histories, supports, bounces)
        service.calculator = SupportDistanceCalculator()
        return service

    def test_calculate_for_ticker_processes_support_distance(self):
        service = self.build_service(
            {"AAA": self.build_history(101.0)},
            {"AAA": [self.zone()]},
            {"AAA": [self.bounce()]},
        )

        result = service.calculate_for_ticker("AAA")

        self.assertTrue(result["processed"])
        self.assertFalse(result["skipped"])
        self.assertEqual(result["ticker"], "AAA")
        self.assertIsNotNone(result["result"])
        self.assertGreaterEqual(result["elapsed_seconds"], 0.0)

    def test_calculate_for_ticker_skips_missing_price(self):
        service = self.build_service({}, {"AAA": [self.zone()]})

        result = service.calculate_for_ticker("AAA")

        self.assertFalse(result["processed"])
        self.assertTrue(result["skipped"])
        self.assertIn("Missing current price", result["warnings"])

    def test_calculate_for_ticker_skips_missing_support(self):
        service = self.build_service({"AAA": self.build_history(101.0)})

        result = service.calculate_for_ticker("AAA")

        self.assertFalse(result["processed"])
        self.assertTrue(result["skipped"])
        self.assertIn("No support zones available", result["warnings"])

    def test_calculate_all_processes_active_tickers(self):
        service = self.build_service(
            {
                "AAA": self.build_history(101.0),
                "BBB": self.build_history(111.0),
            },
            {
                "AAA": [self.zone()],
                "BBB": [self.zone(low=108, high=110, mid=109)],
            },
            {
                "AAA": [self.bounce()],
                "BBB": [self.bounce()],
            },
        )

        results = service.calculate_all()

        self.assertEqual(results["tickers"], 3)
        self.assertEqual(results["processed"], 2)
        self.assertEqual(results["processed_tickers"], ["AAA", "BBB"])
        self.assertEqual(results["skipped"], 1)
        self.assertEqual(results["skipped_tickers"], ["EMPTY"])
        self.assertIn("AAA", results["results"])
        self.assertIn("BBB", results["results"])
        self.assertGreaterEqual(results["elapsed_seconds"], 0.0)

    def test_calculate_all_accepts_explicit_tickers(self):
        service = self.build_service(
            {"AAA": self.build_history(101.0)},
            {"AAA": [self.zone()]},
            {"AAA": [self.bounce()]},
        )

        results = service.calculate_all(["AAA"])

        self.assertEqual(results["tickers"], 1)
        self.assertEqual(results["processed"], 1)
        self.assertEqual(results["processed_tickers"], ["AAA"])

    def test_close_closes_database(self):
        service = self.build_service({})

        service.close()

        self.assertTrue(service.db.closed)


if __name__ == "__main__":
    unittest.main()
