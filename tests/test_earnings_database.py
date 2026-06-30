import sqlite3
import unittest

from database.manager import DatabaseManager
from database.schema import EARNINGS_TABLE


class EarningsDatabaseTest(unittest.TestCase):

    def build_manager(self):
        manager = DatabaseManager.__new__(DatabaseManager)
        manager.connection = sqlite3.connect(":memory:")
        manager.connection.row_factory = sqlite3.Row
        manager.cursor = manager.connection.cursor()
        manager.cursor.execute(EARNINGS_TABLE)
        manager.connection.commit()
        return manager

    def test_save_earnings_replaces_rows_by_ticker(self):
        manager = self.build_manager()
        original = {
            "ticker": "AAPL",
            "next_earnings_date": "2026-07-15",
            "days_until_earnings": 15,
            "previous_earnings_date": "2026-04-15",
            "eps_surprise_pct": 5.0,
            "revenue_surprise_pct": 2.0,
            "earnings_risk_score": 80.0,
        }
        replacement = dict(original)
        replacement["days_until_earnings"] = 5
        replacement["earnings_risk_score"] = 35.0

        self.assertEqual(manager.save_earnings([original]), 1)
        self.assertEqual(manager.save_earnings([replacement]), 1)
        self.assertEqual(manager.earnings_count(), 1)

        stored = manager.get_earnings("AAPL")

        self.assertEqual(stored["days_until_earnings"], 5)
        self.assertEqual(stored["earnings_risk_score"], 35.0)

        manager.close()

    def test_empty_save_is_safe(self):
        manager = self.build_manager()

        self.assertEqual(manager.save_earnings([]), 0)
        self.assertEqual(manager.earnings_count(), 0)

        manager.close()


if __name__ == "__main__":
    unittest.main()
