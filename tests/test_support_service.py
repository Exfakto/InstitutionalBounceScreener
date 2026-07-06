import unittest

import pandas as pd

from services.support_service import SupportDetectionService
from support import SupportStrength, SupportZoneClusterer, SwingLowDetector


class FakeSupportDatabase:

    def __init__(self):
        self.saved = {}
        self.committed = False
        self.closed = False

    def get_all_tickers(self):
        return ["AAA", "EMPTY"]

    def get_price_history(self, ticker):
        if ticker == "EMPTY":
            return pd.DataFrame()

        return pd.DataFrame(
            {
                "Open": [12, 11, 12, 11, 12, 11, 12],
                "High": [13, 12, 13, 12, 13, 12, 13],
                "Low": [11, 10, 11, 10.1, 11, 10.05, 11],
                "Close": [12, 11, 12, 11, 12, 11, 12],
                "Volume": [100] * 7,
            },
            index=pd.date_range("2026-01-01", periods=7),
        )

    def fetch_ohlcv(self, ticker, start_date=None, end_date=None):
        return self.get_price_history(ticker)

    def save_support_levels(self, ticker, zones):
        self.saved[ticker] = zones
        return len(zones)

    def commit(self):
        self.committed = True

    def close(self):
        self.closed = True


class SupportDetectionServiceTest(unittest.TestCase):

    def build_service(self):
        service = SupportDetectionService.__new__(SupportDetectionService)
        service.db = FakeSupportDatabase()
        service.detector = SwingLowDetector(left_window=1, right_window=1)
        service.clusterer = SupportZoneClusterer(tolerance_pct=2.0)
        service.strength = SupportStrength()
        return service

    def test_detect_support_saves_zones_and_returns_summary(self):
        service = self.build_service()

        results = service.detect_support()

        self.assertEqual(results["tickers"], 2)
        self.assertEqual(results["processed"], 1)
        self.assertEqual(results["processed_tickers"], ["AAA"])
        self.assertEqual(results["skipped"], 1)
        self.assertEqual(results["skipped_tickers"], ["EMPTY"])
        self.assertEqual(results["zones"], 1)
        self.assertGreaterEqual(results["elapsed_seconds"], 0.0)
        self.assertTrue(service.db.committed)
        self.assertIn("strength_score", service.db.saved["AAA"][0])

    def test_close_closes_database(self):
        service = self.build_service()

        service.close()

        self.assertTrue(service.db.closed)


if __name__ == "__main__":
    unittest.main()
