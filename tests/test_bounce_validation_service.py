import unittest

import pandas as pd

from bounce import BounceValidator
from services.bounce_validation_service import BounceValidationService


class FakeBounceDatabase:

    def __init__(self):
        self.saved = []
        self.committed = False
        self.closed = False

    def get_all_support_levels(self):
        return [
            {
                "id": 1,
                "ticker": "AAA",
                "zone_low": 10.0,
                "zone_high": 10.2,
                "zone_mid": 10.1,
            },
            {
                "id": 2,
                "ticker": "EMPTY",
                "zone_low": 20.0,
                "zone_high": 20.2,
                "zone_mid": 20.1,
            },
        ]

    def get_price_history(self, ticker):
        if ticker == "EMPTY":
            return pd.DataFrame()

        return pd.DataFrame(
            {
                "Low": [10.1, 10.5, 11.0],
                "High": [10.2, 10.7, 11.0],
                "Close": [10.1, 10.6, 11.0],
            },
            index=pd.date_range("2026-01-01", periods=3),
        )

    def fetch_ohlcv(self, ticker, start_date=None, end_date=None):
        return self.get_price_history(ticker)

    def save_bounce_validations(self, validations):
        self.saved = validations
        return len(validations)

    def commit(self):
        self.committed = True

    def close(self):
        self.closed = True


class BounceValidationServiceTest(unittest.TestCase):

    def build_service(self):
        service = BounceValidationService.__new__(BounceValidationService)
        service.db = FakeBounceDatabase()
        service.validator = BounceValidator()
        return service

    def test_validate_bounces_saves_metrics_and_returns_summary(self):
        service = self.build_service()

        results = service.validate_bounces()

        self.assertEqual(results["support_levels"], 2)
        self.assertEqual(results["processed"], 1)
        self.assertEqual(results["processed_tickers"], ["AAA"])
        self.assertEqual(results["skipped"], 1)
        self.assertEqual(results["skipped_tickers"], ["EMPTY"])
        self.assertEqual(results["validated"], 1)
        self.assertGreaterEqual(results["elapsed_seconds"], 0.0)
        self.assertTrue(service.db.committed)
        self.assertEqual(service.db.saved[0]["support_level_id"], 1)
        self.assertEqual(service.db.saved[0]["ticker"], "AAA")

    def test_close_closes_database(self):
        service = self.build_service()

        service.close()

        self.assertTrue(service.db.closed)


if __name__ == "__main__":
    unittest.main()
