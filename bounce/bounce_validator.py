"""
Bounce validation calculations.
"""

from __future__ import annotations

from statistics import mean, median


class BounceValidator:
    """
    Validates whether support zones historically produced bounces.
    """

    REQUIRED_COLUMNS = [
        "High",
        "Low",
        "Close",
    ]

    def __init__(
        self,
        bounce_target_pct=5.0,
        breakdown_pct=2.0,
        zone_tolerance_pct=0.5,
        forward_window_days=20,
    ):
        self.bounce_target_pct = bounce_target_pct
        self.breakdown_pct = breakdown_pct
        self.zone_tolerance_pct = zone_tolerance_pct
        self.forward_window_days = forward_window_days

    def validate(self, dataframe, support_zone):
        """
        Return bounce validation metrics for one support zone.
        """

        self.validate_columns(dataframe)

        if dataframe.empty:
            return self.empty_metrics(support_zone)

        touches = self.touch_events(dataframe, support_zone)
        outcomes = [
            self.validate_touch(dataframe, touch_index, support_zone)
            for touch_index in touches
        ]

        successful = [
            outcome
            for outcome in outcomes
            if outcome["outcome"] == "success"
        ]
        failed = [
            outcome
            for outcome in outcomes
            if outcome["outcome"] == "failure"
        ]
        neutral = [
            outcome
            for outcome in outcomes
            if outcome["outcome"] == "neutral"
        ]
        bounce_pcts = [
            outcome["bounce_pct"]
            for outcome in outcomes
        ]
        days_to_peaks = [
            outcome["days_to_peak"]
            for outcome in successful
            if outcome["days_to_peak"] is not None
        ]

        total_touches = len(touches)
        current_price = float(dataframe["Close"].iloc[-1])
        zone_high = float(support_zone["zone_high"])
        current_distance = current_price - zone_high

        return {
            "support_level_id": support_zone.get("id"),
            "ticker": support_zone["ticker"],
            "total_touches": total_touches,
            "successful_bounces": len(successful),
            "failed_breakdowns": len(failed),
            "neutral_touches": len(neutral),
            "bounce_success_rate": (
                len(successful) / total_touches * 100
                if total_touches
                else 0.0
            ),
            "average_bounce_pct": (
                mean(bounce_pcts)
                if bounce_pcts
                else None
            ),
            "median_bounce_pct": (
                median(bounce_pcts)
                if bounce_pcts
                else None
            ),
            "average_days_to_bounce_peak": (
                mean(days_to_peaks)
                if days_to_peaks
                else None
            ),
            "current_distance_to_support": current_distance,
            "current_distance_to_support_pct": (
                current_distance / current_price * 100
                if current_price
                else 0.0
            ),
        }

    def touch_events(self, dataframe, support_zone):
        """
        Return first index of each collapsed support touch event.
        """

        zone_low, zone_high = self.zone_bounds(support_zone)
        touches = []
        inside_previous = False

        for index, row in enumerate(dataframe.itertuples()):
            inside_zone = row.Low <= zone_high and row.High >= zone_low

            if inside_zone and not inside_previous:
                touches.append(index)

            inside_previous = inside_zone

        return touches

    def validate_touch(self, dataframe, touch_index, support_zone):
        """
        Validate one touch inside the forward window.
        """

        zone_mid = float(support_zone["zone_mid"])
        zone_low = float(support_zone["zone_low"])
        bounce_target = zone_mid * (1 + self.bounce_target_pct / 100)
        breakdown_level = zone_low * (1 - self.breakdown_pct / 100)
        start = touch_index + 1
        end = min(
            len(dataframe),
            touch_index + self.forward_window_days + 1,
        )
        window = dataframe.iloc[start:end]

        max_high = float(dataframe["High"].iloc[touch_index])
        days_to_peak = 0

        for offset, row in enumerate(window.itertuples(), start=1):

            if row.High > max_high:
                max_high = float(row.High)
                days_to_peak = offset

            hit_bounce = row.High >= bounce_target
            hit_breakdown = row.Close <= breakdown_level

            if hit_bounce:
                return {
                    "outcome": "success",
                    "bounce_pct": (max_high - zone_mid) / zone_mid * 100,
                    "days_to_peak": days_to_peak,
                }

            if hit_breakdown:
                return {
                    "outcome": "failure",
                    "bounce_pct": (max_high - zone_mid) / zone_mid * 100,
                    "days_to_peak": None,
                }

        return {
            "outcome": "neutral",
            "bounce_pct": (max_high - zone_mid) / zone_mid * 100,
            "days_to_peak": None,
        }

    def zone_bounds(self, support_zone):
        zone_low = float(support_zone["zone_low"])
        zone_high = float(support_zone["zone_high"])
        tolerance = float(support_zone["zone_mid"]) * (
            self.zone_tolerance_pct / 100
        )

        return zone_low - tolerance, zone_high + tolerance

    def empty_metrics(self, support_zone):
        return {
            "support_level_id": support_zone.get("id"),
            "ticker": support_zone["ticker"],
            "total_touches": 0,
            "successful_bounces": 0,
            "failed_breakdowns": 0,
            "neutral_touches": 0,
            "bounce_success_rate": 0.0,
            "average_bounce_pct": None,
            "median_bounce_pct": None,
            "average_days_to_bounce_peak": None,
            "current_distance_to_support": 0.0,
            "current_distance_to_support_pct": 0.0,
        }

    def validate_columns(self, dataframe):
        missing = [
            column
            for column in self.REQUIRED_COLUMNS
            if column not in dataframe.columns
        ]

        if missing:
            raise ValueError(
                f"Missing required columns: {', '.join(missing)}"
            )
