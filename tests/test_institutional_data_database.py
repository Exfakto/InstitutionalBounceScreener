import sqlite3
import unittest

from database.institutional_data import InstitutionalData
from database.manager import DatabaseManager


class InstitutionalDataDatabaseTest(unittest.TestCase):

    def build_manager(self):
        manager = DatabaseManager.__new__(DatabaseManager)
        manager.connection = sqlite3.connect(":memory:")
        manager.connection.row_factory = sqlite3.Row
        manager.cursor = manager.connection.cursor()
        manager.initialize()
        return manager

    def test_institutional_data_table_created(self):
        manager = self.build_manager()

        manager.cursor.execute("PRAGMA table_info(institutional_metrics)")
        columns = {row["name"] for row in manager.cursor.fetchall()}

        self.assertIn("ticker", columns)
        self.assertIn("institutional_ownership_pct", columns)
        self.assertIn("source", columns)
        self.assertIn("as_of_date", columns)
        self.assertIn("updated_at", columns)

        manager.close()

    def test_upsert_institutional_data_inserts_and_updates(self):
        manager = self.build_manager()

        inserted = manager.upsert_institutional_data(
            InstitutionalData(
                ticker="aapl",
                institutional_ownership_pct=61.5,
                institutional_ownership_change_qoq=1.2,
                net_institutional_buying=250000000,
                insider_buying_flag=1,
                insider_selling_flag=0,
                source="unit-test",
                as_of_date="2026-06-30",
            )
        )

        self.assertEqual(inserted.ticker, "AAPL")
        self.assertEqual(inserted.institutional_ownership_pct, 61.5)
        self.assertEqual(inserted.source, "unit-test")

        updated = manager.upsert_institutional_data(
            {
                "ticker": "AAPL",
                "institutional_ownership_pct": 64.0,
                "institutional_ownership_change_qoq": 2.0,
                "net_institutional_buying": 300000000,
                "insider_buying_flag": 0,
                "insider_selling_flag": 1,
                "source": "updated",
                "as_of_date": "2026-07-01",
            }
        )

        self.assertEqual(manager.institutional_metrics_count(), 1)
        self.assertEqual(updated.institutional_ownership_pct, 64.0)
        self.assertEqual(updated.insider_selling_flag, 1)
        self.assertEqual(updated.source, "updated")
        self.assertEqual(updated.as_of_date, "2026-07-01")

        manager.close()

    def test_fetch_institutional_data_by_ticker(self):
        manager = self.build_manager()

        manager.upsert_institutional_data(
            {
                "ticker": "MSFT",
                "institutional_ownership_pct": 70,
                "source": "fixture",
            }
        )

        stored = manager.get_institutional_data("msft")

        self.assertIsInstance(stored, InstitutionalData)
        self.assertEqual(stored.ticker, "MSFT")
        self.assertEqual(stored.institutional_ownership_pct, 70)
        self.assertEqual(stored.source, "fixture")

        manager.close()

    def test_fetch_institutional_data_for_multiple_tickers(self):
        manager = self.build_manager()

        manager.upsert_institutional_data({"ticker": "AAA", "institutional_ownership_pct": 40})
        manager.upsert_institutional_data({"ticker": "BBB", "institutional_ownership_pct": 50})

        records = manager.get_institutional_data_for_tickers(["aaa", "BBB", "MISS"])

        self.assertEqual(set(records), {"AAA", "BBB"})
        self.assertEqual(records["AAA"].institutional_ownership_pct, 40)
        self.assertEqual(records["BBB"].institutional_ownership_pct, 50)

        manager.close()

    def test_missing_ticker_returns_none_or_empty(self):
        manager = self.build_manager()

        self.assertIsNone(manager.get_institutional_data("MISSING"))
        self.assertIsNone(manager.get_institutional_data(""))
        self.assertEqual(manager.get_institutional_data_for_tickers([]), {})

        manager.close()

    def test_legacy_save_institutional_metrics_preserves_row_api(self):
        manager = self.build_manager()

        self.assertEqual(
            manager.save_institutional_metrics(
                [
                    {
                        "ticker": "NVDA",
                        "institutional_ownership_pct": 66,
                        "source": "legacy",
                        "as_of_date": "2026-06-30",
                    }
                ]
            ),
            1,
        )

        row = manager.get_institutional_metrics("NVDA")

        self.assertEqual(row["ticker"], "NVDA")
        self.assertEqual(row["source"], "legacy")
        self.assertEqual(row["as_of_date"], "2026-06-30")

        manager.close()


if __name__ == "__main__":
    unittest.main()
