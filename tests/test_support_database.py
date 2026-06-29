import sqlite3
import unittest

import pandas as pd

from database.manager import DatabaseManager
from database.schema import SUPPORT_LEVELS_TABLE


class SupportDatabaseTest(unittest.TestCase):

    def build_manager(self):
        manager = DatabaseManager.__new__(DatabaseManager)
        manager.connection = sqlite3.connect(":memory:")
        manager.connection.row_factory = sqlite3.Row
        manager.cursor = manager.connection.cursor()
        manager.cursor.execute(SUPPORT_LEVELS_TABLE)
        manager.connection.commit()
        return manager

    def test_save_support_levels_replaces_existing_levels(self):
        manager = self.build_manager()
        zones = [
            {
                "zone_low": 10.0,
                "zone_high": 10.2,
                "zone_mid": 10.1,
                "touches": 2,
                "strength_score": 75.0,
                "current_price": 12.0,
                "distance_from_current": 1.8,
                "distance_from_current_pct": 15.0,
                "first_touch_date": pd.Timestamp("2026-01-01"),
                "last_touch_date": pd.Timestamp("2026-02-01"),
            }
        ]

        self.assertEqual(manager.save_support_levels("AAA", zones), 1)
        self.assertEqual(manager.save_support_levels("AAA", []), 0)
        self.assertEqual(manager.support_level_count(), 0)

        manager.close()

    def test_get_support_levels_orders_by_strength(self):
        manager = self.build_manager()
        zones = [
            {
                "zone_low": 10.0,
                "zone_high": 10.2,
                "zone_mid": 10.1,
                "touches": 2,
                "strength_score": 50.0,
                "current_price": 12.0,
                "distance_from_current": 1.8,
                "distance_from_current_pct": 15.0,
                "first_touch_date": "2026-01-01",
                "last_touch_date": "2026-02-01",
            },
            {
                "zone_low": 8.0,
                "zone_high": 8.2,
                "zone_mid": 8.1,
                "touches": 4,
                "strength_score": 90.0,
                "current_price": 12.0,
                "distance_from_current": 3.8,
                "distance_from_current_pct": 31.6,
                "first_touch_date": "2026-01-01",
                "last_touch_date": "2026-02-01",
            },
        ]

        manager.save_support_levels("AAA", zones)
        stored = manager.get_support_levels("AAA")

        self.assertEqual(len(stored), 2)
        self.assertEqual(stored[0]["strength_score"], 90.0)

        manager.close()


if __name__ == "__main__":
    unittest.main()
