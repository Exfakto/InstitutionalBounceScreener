from __future__ import annotations

from dataclasses import dataclass, field
from statistics import median

from bounce import BounceValidator
from database.manager import DatabaseManager
from services.ohlcv_cache_access import fetch_ohlcv_frame


@dataclass(frozen=True)
class BounceAnalytics:
    ticker: str
    primary_support: float | None = None
    support_zone_high: float | None = None
    support_zone_low: float | None = None
    support_width: float | None = None
    distance_from_support_pct: float | None = None
    historical_tests: int = 0
    successful_bounces: int = 0
    failed_breakdowns: int = 0
    bounce_success_pct: float | None = None
    average_bounce_pct: float | None = None
    median_bounce_pct: float | None = None
    largest_bounce_pct: float | None = None
    average_days_to_peak: float | None = None
    most_recent_bounce_date: object | None = None
    support_strength: float | None = None
    quality_score: float = 0.0
    quality_label: str = "Weak"
    history: list[dict] = field(default_factory=list)

    def metrics(self):
        return {
            "primary_support": self.primary_support,
            "support_price": self.primary_support,
            "support_level": self.primary_support,
            "support_zone_high": self.support_zone_high,
            "support_zone_low": self.support_zone_low,
            "support_width": self.support_width,
            "distance_to_support_pct": self.distance_from_support_pct,
            "support_tests": self.historical_tests,
            "bounce_count": self.historical_tests,
            "successful_bounces": self.successful_bounces,
            "successful_support_tests": self.successful_bounces,
            "validated_bounces": self.successful_bounces,
            "failed_support_breaks": self.failed_breakdowns,
            "failed_breakdowns": self.failed_breakdowns,
            "bounce_success_rate": self.bounce_success_pct,
            "bounce_success_pct": self.bounce_success_pct,
            "historical_bounce_success_rate": self.bounce_success_pct,
            "average_bounce": self.average_bounce_pct,
            "average_bounce_pct": self.average_bounce_pct,
            "median_bounce": self.median_bounce_pct,
            "median_bounce_pct": self.median_bounce_pct,
            "largest_bounce": self.largest_bounce_pct,
            "largest_bounce_pct": self.largest_bounce_pct,
            "average_days_to_bounce_peak": self.average_days_to_peak,
            "average_days_to_peak": self.average_days_to_peak,
            "latest_bounce_date": self.most_recent_bounce_date,
            "most_recent_bounce": self.most_recent_bounce_date,
            "support_strength": self.support_strength,
            "support_strength_score": self.support_strength,
            "bounce_quality_score": self.quality_score,
            "bounce_quality": self.quality_label,
            "bounce_history": self.history,
        }


class BounceAnalyticsService:
    """
    Build historical bounce analytics from stored support and validation data.
    """

    def __init__(self, db=None, validator=None):
        self.db = db or DatabaseManager()
        self.validator = validator or BounceValidator()

    def analytics_for_ticker(self, ticker):
        ticker = str(ticker or "").strip().upper()
        support_levels = self.rows("get_support_levels", ticker)
        validations = self.rows("get_bounce_validations", ticker)

        if not support_levels:
            return BounceAnalytics(ticker=ticker)

        primary = support_levels[0]
        frame = fetch_ohlcv_frame(self.db, ticker)
        history = self.history_rows(frame, support_levels)
        aggregate = self.aggregate_from_history(history)
        fallback = self.aggregate_from_validations(validations)

        historical_tests = self.first_number(
            aggregate.get("historical_tests"),
            fallback.get("historical_tests"),
            primary.get("touches"),
        )
        successful_bounces = self.first_number(
            aggregate.get("successful_bounces"),
            fallback.get("successful_bounces"),
        )
        failed_breakdowns = self.first_number(
            aggregate.get("failed_breakdowns"),
            fallback.get("failed_breakdowns"),
        )
        bounce_success_pct = self.first_number(
            aggregate.get("bounce_success_pct"),
            fallback.get("bounce_success_pct"),
        )
        average_bounce_pct = self.first_number(
            aggregate.get("average_bounce_pct"),
            fallback.get("average_bounce_pct"),
        )
        median_bounce_pct = self.first_number(
            aggregate.get("median_bounce_pct"),
            fallback.get("median_bounce_pct"),
        )
        largest_bounce_pct = self.first_number(
            aggregate.get("largest_bounce_pct"),
            fallback.get("largest_bounce_pct"),
            average_bounce_pct,
        )
        average_days_to_peak = self.first_number(
            aggregate.get("average_days_to_peak"),
            fallback.get("average_days_to_peak"),
        )
        most_recent = self.first_existing(
            aggregate.get("most_recent_bounce_date"),
            fallback.get("most_recent_bounce_date"),
            primary.get("last_touch_date"),
        )

        quality_score = self.quality_score(
            support_strength=self.number(primary.get("strength_score")),
            success_rate=bounce_success_pct,
            average_bounce=average_bounce_pct,
            median_bounce=median_bounce_pct,
            tests=historical_tests,
            most_recent=most_recent,
        )

        return BounceAnalytics(
            ticker=ticker,
            primary_support=self.number(primary.get("zone_mid")),
            support_zone_high=self.number(primary.get("zone_high")),
            support_zone_low=self.number(primary.get("zone_low")),
            support_width=self.support_width(primary),
            distance_from_support_pct=self.first_number(
                primary.get("distance_from_current_pct"),
                fallback.get("distance_from_support_pct"),
            ),
            historical_tests=int(historical_tests or 0),
            successful_bounces=int(successful_bounces or 0),
            failed_breakdowns=int(failed_breakdowns or 0),
            bounce_success_pct=bounce_success_pct,
            average_bounce_pct=average_bounce_pct,
            median_bounce_pct=median_bounce_pct,
            largest_bounce_pct=largest_bounce_pct,
            average_days_to_peak=average_days_to_peak,
            most_recent_bounce_date=most_recent,
            support_strength=self.number(primary.get("strength_score")),
            quality_score=quality_score,
            quality_label=self.quality_label(quality_score),
            history=history,
        )

    def history_rows(self, frame, support_levels):
        if frame is None or frame.empty:
            return []

        history = []
        for support in support_levels:
            try:
                touch_indices = self.validator.touch_events(frame, support)
            except Exception:
                continue

            for touch_index in touch_indices:
                outcome = self.validator.validate_touch(frame, touch_index, support)
                support_price = self.number(support.get("zone_mid"))
                bounce_pct = self.number(outcome.get("bounce_pct"))
                peak_price = (
                    support_price * (1 + bounce_pct / 100)
                    if support_price is not None and bounce_pct is not None
                    else None
                )
                touch_row = frame.iloc[touch_index]
                touch_date = frame.index[touch_index]
                history.append(
                    {
                        "date": self.date_text(touch_date),
                        "support_price": support_price,
                        "low_price": self.number(touch_row.get("Low")),
                        "peak_price": peak_price,
                        "bounce_pct": bounce_pct,
                        "days_to_peak": outcome.get("days_to_peak"),
                        "successful": outcome.get("outcome") == "success",
                    }
                )

        history.sort(key=lambda row: str(row.get("date") or ""))
        return history

    @staticmethod
    def aggregate_from_history(history):
        if not history:
            return {}
        bounces = [
            row["bounce_pct"]
            for row in history
            if row.get("bounce_pct") is not None
        ]
        days = [
            row["days_to_peak"]
            for row in history
            if row.get("days_to_peak") is not None
        ]
        successful = sum(1 for row in history if row.get("successful"))
        failed = len(history) - successful
        return {
            "historical_tests": len(history),
            "successful_bounces": successful,
            "failed_breakdowns": failed,
            "bounce_success_pct": successful / len(history) * 100 if history else None,
            "average_bounce_pct": sum(bounces) / len(bounces) if bounces else None,
            "median_bounce_pct": median(bounces) if bounces else None,
            "largest_bounce_pct": max(bounces) if bounces else None,
            "average_days_to_peak": sum(days) / len(days) if days else None,
            "most_recent_bounce_date": max(
                (row.get("date") for row in history if row.get("date")),
                default=None,
            ),
        }

    def aggregate_from_validations(self, validations):
        if not validations:
            return {}
        tests = sum(int(self.number(row.get("total_touches")) or 0) for row in validations)
        successful = sum(
            int(self.number(row.get("successful_bounces")) or 0) for row in validations
        )
        failed = sum(
            int(self.number(row.get("failed_breakdowns")) or 0) for row in validations
        )
        averages = [
            self.number(row.get("average_bounce_pct"))
            for row in validations
            if self.number(row.get("average_bounce_pct")) is not None
        ]
        medians = [
            self.number(row.get("median_bounce_pct"))
            for row in validations
            if self.number(row.get("median_bounce_pct")) is not None
        ]
        days = [
            self.number(row.get("average_days_to_bounce_peak"))
            for row in validations
            if self.number(row.get("average_days_to_bounce_peak")) is not None
        ]
        return {
            "historical_tests": tests,
            "successful_bounces": successful,
            "failed_breakdowns": failed,
            "bounce_success_pct": successful / tests * 100 if tests else None,
            "average_bounce_pct": sum(averages) / len(averages) if averages else None,
            "median_bounce_pct": median(medians) if medians else None,
            "largest_bounce_pct": max(averages) if averages else None,
            "average_days_to_peak": sum(days) / len(days) if days else None,
            "distance_from_support_pct": self.first_number(
                *[row.get("current_distance_to_support_pct") for row in validations]
            ),
            "most_recent_bounce_date": self.first_existing(
                *[row.get("validated_at") for row in validations]
            ),
        }

    def quality_score(
        self,
        support_strength,
        success_rate,
        average_bounce,
        median_bounce,
        tests,
        most_recent,
    ):
        consistency = 100.0
        if average_bounce is not None and median_bounce is not None:
            consistency = max(0.0, 100.0 - abs(average_bounce - median_bounce) * 5)
        tests_score = min((tests or 0) * 12.5, 100.0)
        recency_score = 80.0 if most_recent else 40.0
        values = [
            (support_strength or 0.0) * 0.25,
            (success_rate or 0.0) * 0.30,
            consistency * 0.15,
            tests_score * 0.20,
            recency_score * 0.10,
        ]
        return max(0.0, min(100.0, sum(values)))

    @staticmethod
    def quality_label(score):
        if score >= 85:
            return "Excellent"
        if score >= 70:
            return "Good"
        if score >= 50:
            return "Average"
        return "Weak"

    def rows(self, method_name, ticker):
        method = getattr(self.db, method_name, None)
        if method is None:
            return []
        return [self.row_dict(row) for row in method(ticker) or []]

    @staticmethod
    def support_width(support):
        low = BounceAnalyticsService.number(support.get("zone_low"))
        high = BounceAnalyticsService.number(support.get("zone_high"))
        if low is None or high is None:
            return None
        return high - low

    @staticmethod
    def row_dict(row):
        if row is None:
            return {}
        if isinstance(row, dict):
            return dict(row)
        if hasattr(row, "keys"):
            return {key: row[key] for key in row.keys()}
        return {}

    @staticmethod
    def date_text(value):
        if hasattr(value, "date"):
            return str(value.date())
        return str(value) if value is not None else None

    @staticmethod
    def first_existing(*values):
        for value in values:
            if value not in (None, ""):
                return value
        return None

    @staticmethod
    def first_number(*values):
        for value in values:
            number = BounceAnalyticsService.number(value)
            if number is not None:
                return number
        return None

    @staticmethod
    def number(value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
