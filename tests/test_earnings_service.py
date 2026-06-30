import unittest

import pandas as pd

from analysis.earnings_score import EarningsScore
from services.earnings_service import EarningsService


class FakeEarningsImporter:

    def __init__(self, dataframe):
        self.dataframe = dataframe

    def load(self):
        return self.dataframe


class FakeEarningsDatabase:

    def __init__(self):
        self.records = []
        self.closed = False

    def save_earnings(self, records):
        self.records = records
        return len(records)

    def close(self):
        self.closed = True


class EarningsServiceTest(unittest.TestCase):

    def build_service(self, dataframe):
        service = EarningsService.__new__(EarningsService)
        service.db = FakeEarningsDatabase()
        service.importer = FakeEarningsImporter(dataframe)
        service.score = EarningsScore()
        return service

    def test_import_earnings_scores_and_saves_records(self):
        dataframe = pd.DataFrame(
            [
                {
                    "ticker": "AAPL",
                    "next_earnings_date": "2026-07-15",
                    "days_until_earnings": 15,
                    "previous_earnings_date": "2026-04-15",
                    "eps_surprise_pct": 8.0,
                    "revenue_surprise_pct": 2.0,
                }
            ]
        )
        service = self.build_service(dataframe)

        results = service.import_earnings()

        self.assertEqual(results["rows"], 1)
        self.assertEqual(results["imported"], 1)
        self.assertEqual(results["skipped"], 0)
        self.assertGreaterEqual(results["elapsed_seconds"], 0.0)
        self.assertEqual(service.db.records[0]["ticker"], "AAPL")
        self.assertIn("earnings_risk_score", service.db.records[0])

    def test_empty_csv_is_safe(self):
        service = self.build_service(pd.DataFrame())

        results = service.import_earnings()

        self.assertEqual(results["rows"], 0)
        self.assertEqual(results["imported"], 0)
        self.assertEqual(results["skipped"], 0)

    def test_blank_ticker_is_skipped(self):
        dataframe = pd.DataFrame(
            [
                {
                    "ticker": "",
                    "days_until_earnings": 10,
                    "eps_surprise_pct": 0,
                    "revenue_surprise_pct": 0,
                }
            ]
        )
        service = self.build_service(dataframe)

        results = service.import_earnings()

        self.assertEqual(results["imported"], 0)
        self.assertEqual(results["skipped"], 1)

    def test_close_closes_database(self):
        service = self.build_service(pd.DataFrame())

        service.close()

        self.assertTrue(service.db.closed)


if __name__ == "__main__":
    unittest.main()
