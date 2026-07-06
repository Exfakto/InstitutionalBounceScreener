import unittest

import pandas as pd

from analysis.atr_risk import ATRRiskCalculator
from services.atr_risk_service import ATRRiskService


class FakeATRRiskDatabase:

    def __init__(self, histories):
        self.histories = histories
        self.closed = False

    def get_all_tickers(self):
        return ["AAA", "BBB", "EMPTY"]

    def get_price_history(self, ticker):
        return self.histories.get(ticker, pd.DataFrame())

    def fetch_ohlcv(self, ticker, start_date=None, end_date=None):
        return self.get_price_history(ticker)

    def close(self):
        self.closed = True


class ATRRiskServiceTest(unittest.TestCase):

    def build_history(self, rows=20):
        return pd.DataFrame(
            {
                "High": [12.0] * rows,
                "Low": [10.0] * rows,
                "Close": [11.0] * rows,
            },
            index=pd.date_range("2026-01-01", periods=rows, freq="B"),
        )

    def build_service(self, histories):
        service = ATRRiskService.__new__(ATRRiskService)
        service.db = FakeATRRiskDatabase(histories)
        service.calculator = ATRRiskCalculator()
        return service

    def test_calculate_for_ticker_processes_price_history(self):
        service = self.build_service({"AAA": self.build_history()})

        result = service.calculate_for_ticker("AAA")

        self.assertTrue(result["processed"])
        self.assertFalse(result["skipped"])
        self.assertEqual(result["ticker"], "AAA")
        self.assertIsNotNone(result["result"])
        self.assertGreaterEqual(result["elapsed_seconds"], 0.0)

    def test_calculate_for_ticker_skips_missing_history(self):
        service = self.build_service({})

        result = service.calculate_for_ticker("EMPTY")

        self.assertFalse(result["processed"])
        self.assertTrue(result["skipped"])
        self.assertIn("Missing price history", result["warnings"])

    def test_calculate_for_ticker_skips_insufficient_history(self):
        service = self.build_service({"AAA": self.build_history(rows=10)})

        result = service.calculate_for_ticker("AAA")

        self.assertFalse(result["processed"])
        self.assertTrue(result["skipped"])
        self.assertIn("Insufficient history for ATR14", result["warnings"])

    def test_calculate_all_processes_active_tickers(self):
        histories = {
            "AAA": self.build_history(),
            "BBB": self.build_history(),
        }
        service = self.build_service(histories)

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
        service = self.build_service({"AAA": self.build_history()})

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
