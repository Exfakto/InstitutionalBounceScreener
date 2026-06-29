import unittest

import pandas as pd

from support.support_zone_clusterer import SupportZoneClusterer


class SupportZoneClustererTest(unittest.TestCase):

    def test_cluster_groups_nearby_swing_lows(self):
        swing_lows = [
            {"date": pd.Timestamp("2026-01-01"), "price": 10.00},
            {"date": pd.Timestamp("2026-02-01"), "price": 10.10},
            {"date": pd.Timestamp("2026-03-01"), "price": 20.00},
        ]

        zones = SupportZoneClusterer(
            tolerance_pct=2.0,
            minimum_touches=2,
        ).cluster(swing_lows, current_price=12.0)

        self.assertEqual(len(zones), 1)
        self.assertEqual(zones[0]["touches"], 2)
        self.assertAlmostEqual(zones[0]["zone_low"], 10.00)
        self.assertAlmostEqual(zones[0]["zone_high"], 10.10)
        self.assertAlmostEqual(zones[0]["distance_from_current"], 1.90)

    def test_cluster_requires_minimum_touches(self):
        swing_lows = [
            {"date": pd.Timestamp("2026-01-01"), "price": 10.00},
        ]

        zones = SupportZoneClusterer(minimum_touches=2).cluster(
            swing_lows,
            current_price=12.0,
        )

        self.assertEqual(zones, [])


if __name__ == "__main__":
    unittest.main()
