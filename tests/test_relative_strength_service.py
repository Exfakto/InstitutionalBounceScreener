import unittest

import pandas as pd

from services.relative_strength_service import RelativeStrengthService


class FakeRelativeStrengthDatabase:

    def __init__(self, histories):
        self.histories = histories
        self.closed = False

    def get_all_tickers(self):
        return ["AAA", "BBB", "SPY"]

    def get_price_history(self, ticker):
        return self.histories.get(ticker, pd.DataFrame())

    def fetch_ohlcv(self, ticker, start_date=None, end_date=None):
        return self.get_price_history(ticker)

    def close(self):
        self.closed = True


class RelativeStrengthServiceTest(unittest.TestCase):

    def build_history(self, start_price, daily_step, periods):
        closes = [start_price + (daily_step * index) for index in range(periods)]
        return pd.DataFrame(
            {"Close": closes},
            index=pd.date_range("2025-01-01", periods=periods, freq="B"),
        )

    def build_service(self, histories, benchmark_ticker="SPY"):
        service = RelativeStrengthService.__new__(RelativeStrengthService)
        service.db = FakeRelativeStrengthDatabase(histories)
        from analysis.relative_strength import RelativeStrengthCalculator

        service.calculator = RelativeStrengthCalculator()
        service.benchmark_ticker = benchmark_ticker
        return service

    def test_service_processes_tickers_against_default_benchmark(self):
        histories = {
            "AAA": self.build_history(100, 1.0, 260),
            "BBB": self.build_history(100, 0.2, 120),
            "SPY": self.build_history(100, 0.5, 260),
        }
        service = self.build_service(histories)

        results = service.calculate_relative_strength()

        self.assertEqual(results["benchmark_ticker"], "SPY")
        self.assertTrue(results["benchmark_available"])
        self.assertEqual(results["processed"], 2)
        self.assertEqual(results["processed_tickers"], ["AAA", "BBB"])
        self.assertEqual(results["skipped"], 0)
        self.assertIn("AAA", results["results"])
        self.assertIn("BBB", results["results"])
        self.assertGreaterEqual(results["elapsed_seconds"], 0.0)

    def test_service_skips_all_when_benchmark_is_missing(self):
        histories = {
            "AAA": self.build_history(100, 1.0, 260),
        }
        service = self.build_service(histories)

        results = service.calculate_relative_strength(["AAA"])

        self.assertFalse(results["benchmark_available"])
        self.assertEqual(results["processed"], 0)
        self.assertEqual(results["skipped"], 1)
        self.assertEqual(results["skipped_tickers"], ["AAA"])
        self.assertEqual(
            results["skip_reason"],
            "Benchmark price history not found for SPY",
        )

    def test_service_skips_ticker_when_stock_history_is_missing(self):
        histories = {
            "SPY": self.build_history(100, 0.5, 260),
        }
        service = self.build_service(histories)

        results = service.calculate_relative_strength(["AAA"])

        self.assertTrue(results["benchmark_available"])
        self.assertEqual(results["processed"], 0)
        self.assertEqual(results["skipped"], 1)
        self.assertEqual(results["skipped_tickers"], ["AAA"])

    def test_service_skips_when_relative_strength_cannot_be_calculated(self):
        histories = {
            "AAA": self.build_history(100, 1.0, 40),
            "SPY": self.build_history(100, 0.5, 40),
        }
        service = self.build_service(histories)

        results = service.calculate_relative_strength(["AAA"])

        self.assertEqual(results["processed"], 0)
        self.assertEqual(results["skipped"], 1)
        self.assertEqual(results["skipped_tickers"], ["AAA"])

    def test_close_closes_database(self):
        service = self.build_service({})

        service.close()

        self.assertTrue(service.db.closed)


if __name__ == "__main__":
    unittest.main()
