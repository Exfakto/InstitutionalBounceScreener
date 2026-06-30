import sqlite3
import unittest

from database.manager import DatabaseManager
from database.schema import FUNDAMENTALS_TABLE, INSTITUTIONAL_METRICS_TABLE


class InstitutionalAnalysisDatabaseTest(unittest.TestCase):

    def build_manager(self):
        manager = DatabaseManager.__new__(DatabaseManager)
        manager.connection = sqlite3.connect(":memory:")
        manager.connection.row_factory = sqlite3.Row
        manager.cursor = manager.connection.cursor()
        manager.cursor.execute(FUNDAMENTALS_TABLE)
        manager.cursor.execute(INSTITUTIONAL_METRICS_TABLE)
        manager.connection.commit()
        return manager

    def test_save_fundamentals_replaces_rows_by_ticker(self):
        manager = self.build_manager()
        original = {
            "ticker": "AAPL",
            "market_cap": 3000000000000,
            "revenue_growth_ttm": 8.5,
            "eps_growth_ttm": 6.2,
            "roe": 145.0,
            "gross_margin": 46.0,
            "free_cash_flow": 99500000000,
            "debt_to_equity": 1.8,
            "current_ratio": 0.9,
            "quality_score": 70.0,
        }
        replacement = dict(original)
        replacement["quality_score"] = 80.0

        self.assertEqual(manager.save_fundamentals([original]), 1)
        self.assertEqual(manager.save_fundamentals([replacement]), 1)
        self.assertEqual(manager.fundamentals_count(), 1)

        stored = manager.get_fundamentals("AAPL")

        self.assertEqual(stored["quality_score"], 80.0)

        manager.close()

    def test_save_institutional_metrics_replaces_rows_by_ticker(self):
        manager = self.build_manager()
        original = {
            "ticker": "MSFT",
            "institutional_ownership_pct": 72.5,
            "institutional_ownership_change_qoq": 1.3,
            "net_institutional_buying": 250000000,
            "insider_buying_flag": 0,
            "insider_selling_flag": 1,
            "institutional_score": 55.0,
        }
        replacement = dict(original)
        replacement["institutional_score"] = 65.0
        replacement["insider_selling_flag"] = 0

        self.assertEqual(manager.save_institutional_metrics([original]), 1)
        self.assertEqual(manager.save_institutional_metrics([replacement]), 1)
        self.assertEqual(manager.institutional_metrics_count(), 1)

        stored = manager.get_institutional_metrics("MSFT")

        self.assertEqual(stored["institutional_score"], 65.0)
        self.assertEqual(stored["insider_selling_flag"], 0)

        manager.close()

    def test_empty_saves_are_safe(self):
        manager = self.build_manager()

        self.assertEqual(manager.save_fundamentals([]), 0)
        self.assertEqual(manager.save_institutional_metrics([]), 0)
        self.assertEqual(manager.fundamentals_count(), 0)
        self.assertEqual(manager.institutional_metrics_count(), 0)

        manager.close()


if __name__ == "__main__":
    unittest.main()
