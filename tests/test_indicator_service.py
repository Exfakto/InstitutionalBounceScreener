import unittest

import pandas as pd

from indicators.moving_averages.sma import SMAIndicator
from services.indicator_service import IndicatorService


class FakeDatabase:

    def __init__(self):
        self.saved_dataframes = []
        self.saved_indicators = []
        self.committed = False
        self.closed = False

    def get_all_tickers(self):
        return ["AAA", "EMPTY"]

    def get_price_history(self, ticker):
        if ticker == "EMPTY":
            return pd.DataFrame()

        return pd.DataFrame(
            {
                "Open": range(1, 251),
                "High": [value + 1 for value in range(1, 251)],
                "Low": [value - 1 for value in range(1, 251)],
                "Close": range(1, 251),
                "Volume": [1_000_000 + value * 1_000 for value in range(1, 251)],
            },
            index=pd.date_range("2025-01-01", periods=250),
        )

    def fetch_ohlcv(self, ticker, start_date=None, end_date=None):
        return self.get_price_history(ticker)

    def save_sma(self, dataframe):
        self.saved_dataframes.append(dataframe)

    def save_technical_indicators(self, result):
        self.saved_indicators.append(result)

    def commit(self):
        self.committed = True

    def close(self):
        self.closed = True


class IndicatorServiceTest(unittest.TestCase):

    def build_service(self):
        service = IndicatorService.__new__(IndicatorService)
        service.db = FakeDatabase()
        service.sma = SMAIndicator()
        from services.technical_indicator_engine import TechnicalIndicatorEngine

        service.technical_engine = TechnicalIndicatorEngine()
        return service

    def test_calculate_sma_processes_tickers_and_returns_summary(self):
        service = self.build_service()

        results = service.calculate_sma()

        self.assertEqual(results["tickers"], 2)
        self.assertEqual(results["processed"], 1)
        self.assertEqual(results["processed_tickers"], ["AAA"])
        self.assertEqual(results["skipped"], 1)
        self.assertEqual(results["skipped_tickers"], ["EMPTY"])
        self.assertEqual(results["rows"], 250)
        self.assertGreaterEqual(results["elapsed_seconds"], 0.0)
        self.assertTrue(service.db.committed)

    def test_calculate_sma_persists_calculated_dataframe(self):
        service = self.build_service()

        service.calculate_sma()

        self.assertEqual(len(service.db.saved_dataframes), 1)

        saved = service.db.saved_dataframes[0]

        self.assertIn("ticker", saved.columns)
        self.assertIn("sma20", saved.columns)
        self.assertIn("sma50", saved.columns)
        self.assertIn("sma200", saved.columns)
        self.assertEqual(saved["ticker"].iloc[0], "AAA")
        self.assertAlmostEqual(saved["sma20"].iloc[-1], 240.5)
        self.assertAlmostEqual(saved["sma50"].iloc[-1], 225.5)
        self.assertAlmostEqual(saved["sma200"].iloc[-1], 150.5)

    def test_calculate_indicators_uses_v22_technical_workflow(self):
        service = self.build_service()

        results = service.calculate_indicators()

        self.assertEqual(results["processed"], 1)
        self.assertEqual(results["skipped"], 1)
        self.assertEqual(results["processed_tickers"], ["AAA"])
        self.assertEqual(results["skipped_tickers"], ["EMPTY"])
        self.assertEqual(results["rows"], 250)
        self.assertTrue(service.db.committed)
        self.assertEqual(len(service.db.saved_indicators), 1)

        saved = service.db.saved_indicators[0]

        self.assertEqual(saved.ticker, "AAA")
        self.assertIsNotNone(saved.ema20)
        self.assertIsNotNone(saved.ema50)
        self.assertIsNotNone(saved.ema200)
        self.assertEqual(saved.rsi14, 100.0)
        self.assertIsNotNone(saved.macd)
        self.assertIsNotNone(saved.macd_signal)
        self.assertIsNotNone(saved.macd_histogram)
        self.assertEqual(saved.atr14, 2.0)
        self.assertIsNotNone(saved.vwap)
        self.assertIsNotNone(saved.relative_volume)
        self.assertIsNotNone(saved.distance_from_ema20)
        self.assertIsNotNone(saved.distance_from_ema50)
        self.assertIsNotNone(saved.distance_from_ema200)

    def test_close_closes_database(self):
        service = self.build_service()

        service.close()

        self.assertTrue(service.db.closed)


if __name__ == "__main__":
    unittest.main()
