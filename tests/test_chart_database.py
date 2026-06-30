import sqlite3
import unittest

from database.manager import DatabaseManager
from database.schema import TECHNICAL_INDICATORS_TABLE


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


if __name__ == "__main__":
    unittest.main()
