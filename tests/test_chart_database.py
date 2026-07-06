import sqlite3
import unittest
from types import SimpleNamespace

from database.manager import DatabaseManager
from database.schema import TECHNICAL_INDICATORS_TABLE
from services.technical_indicator_engine import TechnicalIndicatorResult


class ChartDatabaseTest(unittest.TestCase):

    def build_manager(self):
        manager = DatabaseManager.__new__(DatabaseManager)
        manager.connection = sqlite3.connect(":memory:")
        manager.connection.row_factory = sqlite3.Row
        manager.cursor = manager.connection.cursor()
        manager.cursor.execute(TECHNICAL_INDICATORS_TABLE)
        manager.connection.commit()
        return manager

    def test_get_technical_indicators_returns_rows_ordered_by_date(self):
        manager = self.build_manager()
        rows = [
            (
                "AAA",
                "2026-01-02",
                102.0,
                101.0,
                98.0,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
            ),
            (
                "AAA",
                "2026-01-01",
                101.0,
                100.0,
                97.0,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
            ),
        ]

        for row in rows:
            manager.save_indicator_row(row)

        manager.commit()

        stored = manager.get_technical_indicators("AAA")

        self.assertEqual(len(stored), 2)
        self.assertEqual(stored[0]["date"], "2026-01-01")
        self.assertEqual(stored[1]["date"], "2026-01-02")
        self.assertEqual(stored[0]["sma20"], 101.0)

        manager.close()

    def test_get_technical_indicators_returns_empty_rows_when_missing(self):
        manager = self.build_manager()

        stored = manager.get_technical_indicators("MISSING")

        self.assertEqual(stored, [])

        manager.close()

    def test_save_technical_indicators_persists_v22_fields(self):
        manager = self.build_manager()
        result = TechnicalIndicatorResult(
            ticker="EMA",
            date="2026-07-02",
            close=105.0,
            ema20=101.0,
            ema50=98.0,
            ema200=90.0,
            rsi14=61.0,
            macd=1.2,
            macd_signal=0.9,
            macd_histogram=0.3,
            atr14=2.4,
            vwap=102.5,
            average_volume_20=1_500_000,
            relative_volume=1.3,
            distance_from_ema20=4.0,
            distance_from_ema50=7.1,
            distance_from_ema200=16.7,
        )

        manager.save_technical_indicators(result)
        stored = manager.get_technical_indicators("EMA")[0]

        self.assertEqual(stored["ema20"], 101.0)
        self.assertEqual(stored["ema50"], 98.0)
        self.assertEqual(stored["ema200"], 90.0)
        self.assertEqual(stored["trend"], "Bullish")
        self.assertEqual(stored["market_structure"], "Strong Bullish Structure")
        self.assertEqual(stored["vwap"], 102.5)
        self.assertEqual(stored["average_volume_20"], 1_500_000)
        self.assertEqual(stored["distance_from_ema20"], 4.0)

        manager.close()

    def test_save_technical_indicators_accepts_dict_and_object(self):
        manager = self.build_manager()

        manager.save_technical_indicators(
            {
                "ticker": "DICT",
                "date": "2026-07-02",
                "close": 80.0,
                "ema20": 82.0,
                "ema50": 84.0,
                "ema200": 90.0,
                "rsi14": 42.0,
                "macd": -1.0,
                "market_structure": "Custom Structure",
            }
        )
        manager.save_technical_indicators(
            SimpleNamespace(
                ticker="OBJ",
                date="2026-07-02",
                close=110.0,
                ema20=108.0,
                ema50=105.0,
                ema200=100.0,
                rsi14=55.0,
                macd=0.5,
                trend="Custom Trend",
            )
        )

        dict_row = manager.get_technical_indicators("DICT")[0]
        object_row = manager.get_technical_indicators("OBJ")[0]

        self.assertEqual(dict_row["trend"], "Bearish")
        self.assertEqual(dict_row["market_structure"], "Custom Structure")
        self.assertEqual(object_row["trend"], "Custom Trend")
        self.assertEqual(object_row["market_structure"], "Strong Bullish Structure")

        manager.close()

    def test_technical_indicator_migration_updates_existing_table(self):
        manager = DatabaseManager.__new__(DatabaseManager)
        manager.connection = sqlite3.connect(":memory:")
        manager.connection.row_factory = sqlite3.Row
        manager.cursor = manager.connection.cursor()
        manager.cursor.execute(
            """
            CREATE TABLE technical_indicators (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                date TEXT NOT NULL,
                sma20 REAL,
                sma50 REAL,
                sma200 REAL,
                ema21 REAL,
                rsi14 REAL,
                atr14 REAL,
                avg_volume20 REAL,
                relative_volume REAL,
                high52 REAL,
                low52 REAL,
                macd REAL,
                macd_signal REAL,
                macd_histogram REAL,
                UNIQUE(ticker, date)
            )
            """
        )
        manager.connection.commit()

        manager.ensure_technical_indicator_columns()
        manager.save_technical_indicators(
            {
                "ticker": "OLD",
                "date": "2026-07-02",
                "close": 55.0,
                "ema20": 54.0,
                "ema50": 53.0,
                "ema200": 52.0,
                "rsi14": 60.0,
                "macd": 0.2,
            }
        )
        stored = manager.get_technical_indicators("OLD")[0]

        self.assertEqual(stored["ema20"], 54.0)
        self.assertEqual(stored["trend"], "Bullish")
        self.assertEqual(stored["market_structure"], "Strong Bullish Structure")

        manager.close()


if __name__ == "__main__":
    unittest.main()
