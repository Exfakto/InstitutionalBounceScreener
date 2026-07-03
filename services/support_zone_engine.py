"""
Deterministic support zone detection engine for historical OHLCV data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from math import isfinite


@dataclass(frozen=True)
class SupportTouch:
    date: object | None
    low_price: float
    close_price: float
    volume: float | None
    distance_from_zone_center: float
    held_support: bool


@dataclass(frozen=True)
class SupportZone:
    ticker: str
    zone_low: float
    zone_high: float
    zone_center: float
    zone_width_pct: float
    touch_count: int
    first_touch_date: object | None
    last_touch_date: object | None
    support_age_days: int | None
    average_touch_volume: float | None
    support_strength_score: float
    confidence_score: float
    touches: list[SupportTouch] = field(default_factory=list)


@dataclass(frozen=True)
class SupportZoneResult:
    ticker: str
    zones: list[SupportZone] = field(default_factory=list)
    primary_zone: SupportZone | None = None
    warnings: list[str] = field(default_factory=list)


class SupportZoneEngine:
    """
    Detect repeatable support zones by grouping separated low-price tests.
    """

    def __init__(
        self,
        min_touches=3,
        max_zone_width_pct=7.0,
        min_touch_separation_days=5,
        outlier_threshold_pct=12.0,
        min_history=20,
    ):
        self.min_touches = min_touches
        self.max_zone_width_pct = max_zone_width_pct
        self.min_touch_separation_days = min_touch_separation_days
        self.outlier_threshold_pct = outlier_threshold_pct
        self.min_history = min_history

    def detect_support_zones(self, ticker, prices):
        rows, warnings = self.normalize_rows(prices)
        if len(rows) < self.min_history:
            warnings.append("Insufficient price history")
            return SupportZoneResult(ticker=ticker, warnings=warnings)

        candidates = self.candidate_touch_rows(rows)
        zones = []
        for group in self.group_candidates(candidates):
            zone = self.build_zone(ticker, group, rows[-1])
            if zone is not None:
                zones.append(zone)

        ranked = self.rank_support_zones(zones)
        if not ranked:
            warnings.append("No support zones found")
        return SupportZoneResult(
            ticker=ticker,
            zones=ranked,
            primary_zone=ranked[0] if ranked else None,
            warnings=warnings,
        )

    def get_primary_support_zone(self, ticker, prices):
        return self.detect_support_zones(ticker, prices).primary_zone

    @staticmethod
    def rank_support_zones(zones):
        return sorted(
            zones,
            key=lambda zone: (
                zone.confidence_score,
                zone.support_strength_score,
                zone.touch_count,
                zone.last_touch_date_key,
            ),
            reverse=True,
        )

    def normalize_rows(self, prices):
        if not prices:
            return [], ["Missing price history"]

        rows = []
        warnings = []
        for index, source in enumerate(prices):
            row = {
                "date": self.row_value(source, "date") or self.row_value(source, "timestamp"),
                "open": self.clean_number(self.row_value(source, "open")),
                "high": self.clean_number(self.row_value(source, "high")),
                "low": self.clean_number(self.row_value(source, "low")),
                "close": self.clean_number(self.row_value(source, "close")),
                "volume": self.clean_number(self.row_value(source, "volume")),
            }
            if row["low"] is None or row["close"] is None:
                warnings.append(f"Skipped row {index}: missing low or close")
                continue
            rows.append(row)

        rows.sort(key=self.sort_key)
        return rows, warnings

    def candidate_touch_rows(self, rows):
        if len(rows) < 3:
            return []

        candidates = []
        for index in range(1, len(rows) - 1):
            row = rows[index]
            low = row["low"]
            previous_low = rows[index - 1]["low"]
            next_low = rows[index + 1]["low"]
            if low <= previous_low and low <= next_low:
                if self.percent_distance(row["close"], low) > self.max_zone_width_pct * 2:
                    continue
                candidates.append({**row, "index": index})
        return candidates

    def group_candidates(self, candidates):
        groups = []
        for candidate in sorted(candidates, key=lambda row: row["low"]):
            placed = False
            for group in groups:
                center = sum(item["low"] for item in group) / len(group)
                prospective_lows = [item["low"] for item in group] + [candidate["low"]]
                width_pct = self.zone_width_pct(min(prospective_lows), max(prospective_lows), center)
                if width_pct <= self.max_zone_width_pct:
                    group.append(candidate)
                    placed = True
                    break
            if not placed:
                groups.append([candidate])

        separated = [self.apply_touch_separation(group) for group in groups]
        return [group for group in separated if len(group) >= self.min_touches]

    def apply_touch_separation(self, group):
        selected = []
        for candidate in sorted(group, key=lambda row: row["index"]):
            if not selected:
                selected.append(candidate)
                continue
            if candidate["index"] - selected[-1]["index"] >= self.min_touch_separation_days:
                selected.append(candidate)
        return selected

    def build_zone(self, ticker, group, latest_row):
        lows = [row["low"] for row in group]
        zone_low = min(lows)
        zone_high = max(lows)
        zone_center = sum(lows) / len(lows)
        zone_width_pct = self.zone_width_pct(zone_low, zone_high, zone_center)
        if zone_width_pct > self.max_zone_width_pct:
            return None

        touches = [
            SupportTouch(
                date=row["date"],
                low_price=row["low"],
                close_price=row["close"],
                volume=row["volume"],
                distance_from_zone_center=self.percent_signed_distance(row["low"], zone_center),
                held_support=row["close"] >= zone_low,
            )
            for row in sorted(group, key=lambda item: item["index"])
        ]
        volumes = [touch.volume for touch in touches if touch.volume is not None]
        support_age_days = self.days_between(touches[0].date, latest_row.get("date"))
        average_volume = sum(volumes) / len(volumes) if volumes else None
        held_count = sum(1 for touch in touches if touch.held_support)
        hold_rate = held_count / len(touches)
        recency_score = self.recency_score(touches[-1].date, latest_row.get("date"))
        touch_score = min(100.0, (len(touches) / max(self.min_touches, 1)) * 55)
        tightness_score = max(0.0, 25.0 * (1 - zone_width_pct / self.max_zone_width_pct))
        hold_score = hold_rate * 20
        support_strength_score = min(100.0, touch_score + tightness_score + hold_score)
        confidence_score = min(100.0, support_strength_score * 0.75 + recency_score * 0.25)

        return SupportZone(
            ticker=ticker,
            zone_low=zone_low,
            zone_high=zone_high,
            zone_center=zone_center,
            zone_width_pct=zone_width_pct,
            touch_count=len(touches),
            first_touch_date=touches[0].date,
            last_touch_date=touches[-1].date,
            support_age_days=support_age_days,
            average_touch_volume=average_volume,
            support_strength_score=support_strength_score,
            confidence_score=confidence_score,
            touches=touches,
        )

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
    def sort_key(row):
        value = row.get("date")
        if isinstance(value, (date, datetime)):
            return value
        return str(value or "")

    @staticmethod
    def zone_width_pct(zone_low, zone_high, center):
        if center == 0:
            return 0.0
        return ((zone_high - zone_low) / center) * 100

    @staticmethod
    def percent_distance(value, baseline):
        if baseline == 0:
            return 0.0
        return abs((value - baseline) / baseline) * 100

    @staticmethod
    def percent_signed_distance(value, baseline):
        if baseline == 0:
            return 0.0
        return ((value - baseline) / baseline) * 100

    @staticmethod
    def days_between(start, end):
        start_date = SupportZoneEngine.coerce_date(start)
        end_date = SupportZoneEngine.coerce_date(end)
        if start_date is None or end_date is None:
            return None
        return max(0, (end_date - start_date).days)

    @staticmethod
    def recency_score(start, end):
        days = SupportZoneEngine.days_between(start, end)
        if days is None:
            return 50.0
        return max(0.0, 100.0 - min(days, 120) * (100.0 / 120.0))

    @staticmethod
    def coerce_date(value):
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value).date()
            except ValueError:
                return None
        return None


SupportZone.last_touch_date_key = property(
    lambda self: SupportZoneEngine.coerce_date(self.last_touch_date) or date.min
)
