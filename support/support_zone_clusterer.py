"""
Support zone clustering.
"""

from __future__ import annotations


class SupportZoneClusterer:
    """
    Clusters nearby swing lows into support zones.
    """

    def __init__(self, tolerance_pct=1.5, minimum_touches=2):
        self.tolerance_pct = tolerance_pct
        self.minimum_touches = minimum_touches

    def cluster(self, swing_lows, current_price):
        """
        Return support zones from swing lows.
        """

        if not swing_lows:
            return []

        clusters = []

        for swing_low in sorted(swing_lows, key=lambda item: item["price"]):

            cluster = self._matching_cluster(clusters, swing_low["price"])

            if cluster is None:
                clusters.append([swing_low])
            else:
                cluster.append(swing_low)

        zones = []

        for cluster in clusters:

            if len(cluster) < self.minimum_touches:
                continue

            prices = [item["price"] for item in cluster]
            dates = [item["date"] for item in cluster]

            zone_low = min(prices)
            zone_high = max(prices)
            zone_mid = (zone_low + zone_high) / 2
            distance = float(current_price) - zone_high

            zones.append(
                {
                    "zone_low": zone_low,
                    "zone_high": zone_high,
                    "zone_mid": zone_mid,
                    "touches": len(cluster),
                    "current_price": float(current_price),
                    "distance_from_current": distance,
                    "distance_from_current_pct": (
                        distance / float(current_price) * 100
                        if current_price
                        else 0.0
                    ),
                    "first_touch_date": min(dates),
                    "last_touch_date": max(dates),
                }
            )

        return sorted(zones, key=lambda zone: zone["zone_mid"])

    def _matching_cluster(self, clusters, price):

        for cluster in clusters:
            prices = [item["price"] for item in cluster]
            midpoint = (min(prices) + max(prices)) / 2
            tolerance = midpoint * (self.tolerance_pct / 100)

            if abs(price - midpoint) <= tolerance:
                return cluster

        return None
