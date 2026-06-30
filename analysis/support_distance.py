"""
Support distance calculation utilities.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


@dataclass(frozen=True)
class SupportDistanceResult:
    """
    Pure support distance calculation output.
    """

    current_price: float | None
    nearest_support_low: float | None
    nearest_support_high: float | None
    nearest_support_mid: float | None
    distance_to_support_pct: float | None
    distance_to_support_abs: float | None
    support_strength_score: float | None
    bounce_success_rate: float | None
    average_bounce_pct: float | None
    risk_reward_estimate: float
    entry_quality_score: float
    warnings: list[str] = field(default_factory=list)


class SupportDistanceCalculator:
    """
    Calculate distance and entry context for the nearest support zone.

    The scores are v2.1 placeholder heuristics:
    - price inside or within 2% above support receives the strongest base score
    - 2% to 5% above support receives a moderate score
    - more than 5% above support receives a lower score
    - support strength and bounce success improve entry quality
    - average bounce percent improves the risk/reward estimate
    """

    def calculate(
        self,
        current_price,
        support_zones,
        bounce_metrics=None,
    ) -> SupportDistanceResult:
        warnings = []
        price = self.number_or_none(current_price)

        if price is None or price <= 0:
            warnings.append("Missing current price")
            return self.empty_result(warnings)

        zones = list(support_zones or [])

        if not zones:
            warnings.append("No support zones available")
            return self.empty_result(warnings, current_price=price)

        nearest = self.nearest_support_zone(price, zones)

        if nearest is None:
            warnings.append("No support zones below or near current price")
            return self.empty_result(warnings, current_price=price)

        zone_low = self.number_or_none(self.value(nearest, "zone_low"))
        zone_high = self.number_or_none(self.value(nearest, "zone_high"))
        zone_mid = self.number_or_none(self.value(nearest, "zone_mid"))

        if zone_mid is None and zone_low is not None and zone_high is not None:
            zone_mid = (zone_low + zone_high) / 2.0

        if zone_low is None or zone_high is None or zone_mid is None:
            warnings.append("Selected support zone is missing price range")
            return self.empty_result(warnings, current_price=price)

        distance_abs = self.distance_abs(price, zone_low, zone_high, zone_mid)
        distance_pct = 0.0 if distance_abs == 0 else (distance_abs / price) * 100.0
        strength_score = self.number_or_none(self.value(nearest, "strength_score"))
        matching_bounce = self.match_bounce_metrics(nearest, bounce_metrics or [])
        bounce_success_rate = self.number_or_none(
            self.value(matching_bounce, "bounce_success_rate")
        )
        average_bounce_pct = self.number_or_none(
            self.value(matching_bounce, "average_bounce_pct")
        )

        if matching_bounce is None:
            warnings.append("Missing bounce validation metrics")

        risk_reward = self.risk_reward_estimate(
            average_bounce_pct,
            distance_pct,
        )
        entry_quality = self.entry_quality_score(
            distance_pct,
            strength_score,
            bounce_success_rate,
            average_bounce_pct,
        )

        return SupportDistanceResult(
            current_price=price,
            nearest_support_low=zone_low,
            nearest_support_high=zone_high,
            nearest_support_mid=zone_mid,
            distance_to_support_pct=distance_pct,
            distance_to_support_abs=distance_abs,
            support_strength_score=strength_score,
            bounce_success_rate=bounce_success_rate,
            average_bounce_pct=average_bounce_pct,
            risk_reward_estimate=risk_reward,
            entry_quality_score=entry_quality,
            warnings=warnings,
        )

    def nearest_support_zone(self, current_price, support_zones):
        candidates = []

        for zone in support_zones:
            zone_low = self.number_or_none(self.value(zone, "zone_low"))
            zone_high = self.number_or_none(self.value(zone, "zone_high"))
            zone_mid = self.number_or_none(self.value(zone, "zone_mid"))

            if zone_mid is None and zone_low is not None and zone_high is not None:
                zone_mid = (zone_low + zone_high) / 2.0

            if zone_low is None or zone_high is None or zone_mid is None:
                continue

            if zone_low <= current_price <= zone_high:
                distance = 0.0
            elif zone_high < current_price:
                distance = current_price - zone_high
            else:
                continue

            candidates.append((abs(distance), zone))

        if not candidates:
            return None

        candidates.sort(key=lambda item: item[0])
        return candidates[0][1]

    @staticmethod
    def distance_abs(current_price, zone_low, zone_high, zone_mid):
        if zone_low <= current_price <= zone_high:
            return 0.0

        if current_price > zone_high:
            return current_price - zone_high

        return zone_low - current_price if current_price < zone_low else abs(current_price - zone_mid)

    def match_bounce_metrics(self, support_zone, bounce_metrics):
        metrics = list(bounce_metrics or [])

        if not metrics:
            return None

        support_id = self.value(support_zone, "id")

        if support_id is not None:
            for metric in metrics:
                if self.value(metric, "support_level_id") == support_id:
                    return metric

        return metrics[0]

    def risk_reward_estimate(self, average_bounce_pct, distance_pct):
        if average_bounce_pct is None:
            return 0.0

        distance_floor = max(distance_pct or 0.0, 1.0)

        # Placeholder heuristic: expected bounce vs entry distance scaled 0..100.
        return self.clamp((average_bounce_pct / distance_floor) * 10.0)

    def entry_quality_score(
        self,
        distance_pct,
        strength_score,
        bounce_success_rate,
        average_bounce_pct,
    ):
        if distance_pct is None:
            return 0.0

        if distance_pct <= 2.0:
            score = 70.0
        elif distance_pct <= 5.0:
            score = 55.0 - ((distance_pct - 2.0) * 5.0)
        else:
            score = max(10.0, 35.0 - ((distance_pct - 5.0) * 3.0))

        if strength_score is not None:
            score += self.clamp(strength_score) * 0.15

        if bounce_success_rate is not None:
            score += self.clamp(bounce_success_rate) * 0.15

        if average_bounce_pct is not None:
            score += min(10.0, max(0.0, average_bounce_pct * 0.5))

        return self.clamp(score)

    @staticmethod
    def value(row, key):
        if row is None:
            return None

        if isinstance(row, dict):
            return row.get(key)

        try:
            return row[key]
        except (IndexError, KeyError, TypeError):
            return None

    @staticmethod
    def number_or_none(value):
        if value is None or value == "":
            return None

        if pd.isna(value):
            return None

        return float(value)

    @staticmethod
    def empty_result(warnings, current_price=None):
        return SupportDistanceResult(
            current_price=current_price,
            nearest_support_low=None,
            nearest_support_high=None,
            nearest_support_mid=None,
            distance_to_support_pct=None,
            distance_to_support_abs=None,
            support_strength_score=None,
            bounce_success_rate=None,
            average_bounce_pct=None,
            risk_reward_estimate=0.0,
            entry_quality_score=0.0,
            warnings=warnings,
        )

    @staticmethod
    def clamp(value):
        return max(0.0, min(100.0, float(value)))
