import unittest

import pandas as pd

from analysis.institutional_momentum import InstitutionalMomentumCalculator
from services.institutional_momentum_service import InstitutionalMomentumService


class FakeInstitutionalMomentumImporter:

    def __init__(self, dataframe):
        self.dataframe = dataframe

    def load(self):
        return self.dataframe


class InstitutionalMomentumServiceTest(unittest.TestCase):

    def build_dataframe(self):
        return pd.DataFrame(
            [
                {
                    "ticker": "AAA",
                    "report_date": "2026-01-01",
                    "institutional_ownership_pct": 55.0,
                    "new_large_buyers": 1,
                    "new_large_sellers": 0,
                    "insider_buying_flag": 0,
                    "insider_selling_flag": 0,
                },
                {
                    "ticker": "AAA",
                    "report_date": "2026-04-01",
                    "institutional_ownership_pct": 60.0,
                    "new_large_buyers": 2,
                    "new_large_sellers": 0,
                    "insider_buying_flag": 1,
                    "insider_selling_flag": 0,
                },
                {
                    "ticker": "BBB",
                    "report_date": "2026-04-01",
                    "institutional_ownership_pct": None,
                    "new_large_buyers": 0,
                    "new_large_sellers": 3,
                    "insider_buying_flag": 0,
                    "insider_selling_flag": 1,
                },
            ]
        )

    def build_service(self, dataframe):
        service = InstitutionalMomentumService.__new__(InstitutionalMomentumService)
        service.importer = FakeInstitutionalMomentumImporter(dataframe)
        service.calculator = InstitutionalMomentumCalculator()
        return service

    def test_calculate_for_ticker_processes_history(self):
        service = self.build_service(self.build_dataframe())

        result = service.calculate_for_ticker("AAA")

        self.assertTrue(result["processed"])
        self.assertFalse(result["skipped"])
        self.assertEqual(result["ticker"], "AAA")
        self.assertEqual(result["result"].ownership_trend, "increasing")
        self.assertGreaterEqual(result["elapsed_seconds"], 0.0)

    def test_calculate_for_ticker_skips_missing_history(self):
        service = self.build_service(self.build_dataframe())

        result = service.calculate_for_ticker("MISSING")

        self.assertFalse(result["processed"])
        self.assertTrue(result["skipped"])
        self.assertIn("Missing institutional history", result["warnings"])

    def test_calculate_for_ticker_skips_missing_current_ownership(self):
        service = self.build_service(self.build_dataframe())

        result = service.calculate_for_ticker("BBB")

        self.assertFalse(result["processed"])
        self.assertTrue(result["skipped"])
        self.assertIn("Missing current institutional ownership", result["warnings"])

    def test_calculate_all_processes_available_tickers(self):
        service = self.build_service(self.build_dataframe())

        results = service.calculate_all()

        self.assertEqual(results["tickers"], 2)
        self.assertEqual(results["processed"], 1)
        self.assertEqual(results["processed_tickers"], ["AAA"])
        self.assertEqual(results["skipped"], 1)
        self.assertEqual(results["skipped_tickers"], ["BBB"])
        self.assertIn("AAA", results["results"])
        self.assertGreaterEqual(results["elapsed_seconds"], 0.0)

    def test_calculate_all_accepts_explicit_tickers(self):
        service = self.build_service(self.build_dataframe())

        results = service.calculate_all(["AAA"])

        self.assertEqual(results["tickers"], 1)
        self.assertEqual(results["processed"], 1)
        self.assertEqual(results["processed_tickers"], ["AAA"])

    def test_empty_csv_is_safe(self):
        service = self.build_service(pd.DataFrame())

        results = service.calculate_all()

        self.assertEqual(results["tickers"], 0)
        self.assertEqual(results["processed"], 0)
        self.assertEqual(results["skipped"], 0)


if __name__ == "__main__":
    unittest.main()
