import sqlite3
import unittest

from database.manager import DatabaseManager
from database.schema import BOUNCE_VALIDATIONS_TABLE, SUPPORT_LEVELS_TABLE


class BounceDatabaseTest(unittest.TestCase):

    def build_manager(self):
        manager = DatabaseManager.__new__(DatabaseManager)
        manager.connection = sqlite3.connect(":memory:")
        manager.connection.row_factory = sqlite3.Row
        manager.cursor = manager.connection.cursor()
        manager.cursor.execute(SUPPORT_LEVELS_TABLE)
        manager.cursor.execute(BOUNCE_VALIDATIONS_TABLE)
        manager.connection.commit()
        return manager

    def test_get_all_support_levels_includes_ids(self):
        manager = self.build_manager()
        manager.save_support_levels(
            "AAA",
            [
                {
                    "zone_low": 10.0,
                    "zone_high": 10.2,
                    "zone_mid": 10.1,
                    "touches": 2,
                    "strength_score": 75.0,
                    "current_price": 12.0,
                    "distance_from_current": 1.8,
                    "distance_from_current_pct": 15.0,
                    "first_touch_date": "2026-01-01",
                    "last_touch_date": "2026-02-01",
                }
            ],
        )

        support_levels = manager.get_all_support_levels()

        self.assertEqual(len(support_levels), 1)
        self.assertEqual(support_levels[0]["id"], 1)

        manager.close()

    def test_save_bounce_validations_replaces_existing_metrics(self):
        manager = self.build_manager()
        validation = {
            "support_level_id": 1,
            "ticker": "AAA",
            "total_touches": 2,
            "successful_bounces": 1,
            "failed_breakdowns": 0,
            "neutral_touches": 1,
            "bounce_success_rate": 50.0,
            "average_bounce_pct": 4.5,
            "median_bounce_pct": 4.5,
            "average_days_to_bounce_peak": 3.0,
            "current_distance_to_support": 1.8,
            "current_distance_to_support_pct": 15.0,
        }
        replacement = dict(validation)
        replacement["successful_bounces"] = 2
        replacement["bounce_success_rate"] = 100.0

        self.assertEqual(manager.save_bounce_validations([validation]), 1)
        self.assertEqual(manager.save_bounce_validations([replacement]), 1)
        self.assertEqual(manager.bounce_validation_count(), 1)

        stored = manager.get_bounce_validations("AAA")

        self.assertEqual(stored[0]["successful_bounces"], 2)
        self.assertEqual(stored[0]["bounce_success_rate"], 100.0)

        manager.close()


if __name__ == "__main__":
    unittest.main()
