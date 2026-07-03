"""
Deterministic historical bounce analysis for detected support zones.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite
from statistics import median

from services.support_zone_engine import SupportZone, SupportZoneEngine


@dataclass(frozen=True)
class BounceEvent:
    ticker: str
    touch_date: object | None
    support_price: float
    low_price: float
    close_price: float
    max_future_high: float | None
    bounce_percentage: float | None
    days_to_peak: int | None
    successful: bool
    failed_support_break: bool
    in_progress: bool = False
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class BounceAnalysisResult:
    ticker: str
    support_zone: SupportZone | None = None
    events: list[BounceEvent] = field(default_factory=list)
    total_support_tests: int = 0
    successful_bounces: int = 0
    failed_bounces: int = 0
    bounce_success_rate: float | None = None
    average_bounce_pct: float | None = None
    median_bounce_pct: float | None = None
    largest_bounce_pct: float | None = None
    average_days_to_peak: float | None = None
    failed_support_breaks: int = 0
    most_recent_bounce_date: object | None = None
    warnings: list[str] = field(default_factory=list)


class BounceDetectionEngine:
    """
    Analyze historical bounce behavior following support-zone touches.
    """

    def __init__(
        self,
        lookahead_window=60,
        minimum_successful_bounce_pct=10.0,
        support_failure_threshold_pct=3.0,
    ):
        self.lookahead_window = lookahead_window
        self.minimum_successful_bounce_pct = minimum_successful_bounce_pct
        self.support_failure_threshold_pct = support_failure_threshold_pct

    def analyze_bounces(self, ticker, prices, support_zones):
        zones = list(support_zones or [])
        if not zones:
            return [
                BounceAnalysisResult(
                    ticker=ticker,
                    warnings=["No support zones provided"],
                )
            ]
        return [self.analyze_zone_bounces(ticker, prices, zone) for zone in zones]

    def analyze_zone_bounces(self, ticker, prices, support_zone):
        rows, warnings = self.normalize_rows(prices)
        if not rows:
            return BounceAnalysisResult(
                ticker=ticker,
                support_zone=support_zone,
                warnings=warnings or ["Missing price history"],
            )

        touch_indices = []
        for touch in support_zone.touches:
            index = self.find_row_index(rows, touch.date)
            if index is None:
                warnings.append(f"Touch date not found: {touch.date}")
                continue
            touch_indices.append(index)

        events = []
        for position, index in enumerate(touch_indices):
            next_touch_index = (
                touch_indices[position + 1] if position + 1 < len(touch_indices) else None
            )
            events.append(
                self.build_event(ticker, rows, index, support_zone, next_touch_index)
            )

        return self.build_result(ticker, support_zone, events, warnings)

    @staticmethod
    def rank_zones_by_bounce_quality(results):
        return sorted(
            results,
            key=lambda result: (
                result.bounce_success_rate or 0,
                result.average_bounce_pct or 0,
                result.largest_bounce_pct or 0,
                result.total_support_tests,
            ),
            reverse=True,
        )

    def build_event(self, ticker, rows, touch_index, support_zone, next_touch_index=None):
        touch_row = rows[touch_index]
        end_index = touch_index + 1 + self.lookahead_window
        if next_touch_index is not None:
            end_index = min(end_index, next_touch_index)
        future_rows = rows[touch_index + 1 : end_index]
        warnings = []
        in_progress = False
        if len(future_rows) < self.lookahead_window:
            warnings.append("Insufficient future data")
            in_progress = True

        support_price = support_zone.zone_center
        failure_close = support_zone.zone_low * (
            1 - self.support_failure_threshold_pct / 100
        )
        failed_support_break = any(row["close"] < failure_close for row in future_rows)

        if future_rows:
            max_index, max_row = max(
                enumerate(future_rows),
                key=lambda item: item[1]["high"],
            )
            max_future_high = max_row["high"]
            days_to_peak = max_index + 1
            bounce_percentage = self.percent_gain(support_price, max_future_high)
        else:
            max_future_high = None
            days_to_peak = None
            bounce_percentage = None

        successful = (
            bounce_percentage is not None
            and bounce_percentage >= self.minimum_successful_bounce_pct
            and not failed_support_break
        )

        return BounceEvent(
            ticker=ticker,
            touch_date=touch_row["date"],
            support_price=support_price,
            low_price=touch_row["low"],
            close_price=touch_row["close"],
            max_future_high=max_future_high,
            bounce_percentage=bounce_percentage,
            days_to_peak=days_to_peak,
            successful=successful,
            failed_support_break=failed_support_break,
            in_progress=in_progress,
            warnings=warnings,
        )

    def build_result(self, ticker, support_zone, events, warnings):
        bounce_values = [
            event.bounce_percentage
            for event in events
            if event.bounce_percentage is not None
        ]
        days_values = [
            event.days_to_peak for event in events if event.days_to_peak is not None
        ]
        successful_bounces = sum(1 for event in events if event.successful)
        failed_support_breaks = sum(1 for event in events if event.failed_support_break)
        failed_bounces = len(events) - successful_bounces
        most_recent = max((event.touch_date for event in events), default=None)

        for event in events:
            for warning in event.warnings:
                if warning not in warnings:
                    warnings.append(warning)

        return BounceAnalysisResult(
            ticker=ticker,
            support_zone=support_zone,
            events=events,
            total_support_tests=len(events),
            successful_bounces=successful_bounces,
            failed_bounces=failed_bounces,
            bounce_success_rate=(
                successful_bounces / len(events) * 100 if events else None
            ),
            average_bounce_pct=(
                sum(bounce_values) / len(bounce_values) if bounce_values else None
            ),
            median_bounce_pct=median(bounce_values) if bounce_values else None,
            largest_bounce_pct=max(bounce_values) if bounce_values else None,
            average_days_to_peak=(
                sum(days_values) / len(days_values) if days_values else None
            ),
            failed_support_breaks=failed_support_breaks,
            most_recent_bounce_date=most_recent,
            warnings=warnings,
        )

    def normalize_rows(self, prices):
        if not prices:
            return [], ["Missing price history"]

        rows = []
        warnings = []
        for index, source in enumerate(prices):
            row = {
                "date": self.row_value(source, "date") or self.row_value(source, "timestamp"),
                "high": self.clean_number(self.row_value(source, "high")),
                "low": self.clean_number(self.row_value(source, "low")),
                "close": self.clean_number(self.row_value(source, "close")),
                "volume": self.clean_number(self.row_value(source, "volume")),
            }
            if row["high"] is None or row["low"] is None or row["close"] is None:
                warnings.append(f"Skipped row {index}: missing OHLC values")
                continue
            rows.append(row)

        rows.sort(key=SupportZoneEngine.sort_key)
        return rows, warnings

    @staticmethod
    def find_row_index(rows, touch_date):
        for index, row in enumerate(rows):
            if row["date"] == touch_date:
                return index
        return None

    @staticmethod
    def row_value(row, key):
        if isinstance(row, dict):
            return row.get(key)
        return getattr(row, key, None)

    @staticmethod
    def clean_number(value):
        if value in (None, ""):
            return None
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        return number if isfinite(number) else None

    @staticmethod
    def percent_gain(start, end):
        if start == 0:
            return None
        return ((end - start) / start) * 100
