import unittest

from support.support_strength import SupportStrength


class SupportStrengthTest(unittest.TestCase):

    def test_calculate_scores_more_touches_higher(self):
        strength = SupportStrength()
        weak_zone = {
            "touches": 2,
            "zone_low": 10.0,
            "zone_high": 10.2,
            "zone_mid": 10.1,
            "distance_from_current_pct": 5.0,
        }
        strong_zone = dict(weak_zone)
        strong_zone["touches"] = 4

        self.assertGreater(
            strength.calculate(strong_zone),
            strength.calculate(weak_zone),
        )

    def test_apply_adds_strength_score(self):
        zones = [
            {
                "touches": 2,
                "zone_low": 10.0,
                "zone_high": 10.2,
                "zone_mid": 10.1,
                "distance_from_current_pct": 5.0,
            }
        ]

        scored = SupportStrength().apply(zones)

        self.assertIn("strength_score", scored[0])
        self.assertNotIn("strength_score", zones[0])


if __name__ == "__main__":
    unittest.main()
