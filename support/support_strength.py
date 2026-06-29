"""
Support strength scoring.
"""

from __future__ import annotations


class SupportStrength:
    """
    Calculates a basic support strength score.
    """

    def calculate(self, zone):
        """
        Return a score from 0 to 100.
        """

        touches = zone.get("touches", 0)
        zone_mid = zone.get("zone_mid", 0)
        zone_width = zone.get("zone_high", 0) - zone.get("zone_low", 0)

        touch_score = min(touches, 5) * 15

        if zone_mid:
            width_pct = zone_width / zone_mid * 100
            tightness_score = max(0, 25 - (width_pct * 5))
        else:
            tightness_score = 0

        distance_pct = abs(zone.get("distance_from_current_pct", 0))
        distance_score = max(0, 20 - distance_pct)

        return min(100.0, touch_score + tightness_score + distance_score)

    def apply(self, zones):
        """
        Add strength_score to each zone.
        """

        scored_zones = []

        for zone in zones:
            scored_zone = dict(zone)
            scored_zone["strength_score"] = self.calculate(scored_zone)
            scored_zones.append(scored_zone)

        return scored_zones
