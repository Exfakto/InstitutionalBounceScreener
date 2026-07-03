from __future__ import annotations

from datetime import date, datetime, timedelta


REQUIRED_OHLCV_FIELDS = ("date", "open", "high", "low", "close", "volume")


class MarketDataValidator:
    @classmethod
    def missing_ohlcv_fields(cls, row):
        return [
            field
            for field in REQUIRED_OHLCV_FIELDS
            if cls.value(row, field) in (None, "")
        ]

    @classmethod
    def duplicate_dates(cls, rows):
        seen = set()
        duplicates = []
        for row in rows or []:
            value = str(cls.value(row, "date") or "")
            if value in seen and value not in duplicates:
                duplicates.append(value)
            seen.add(value)
        return duplicates

    @classmethod
    def invalid_prices(cls, row):
        invalid = []
        for field in ("open", "high", "low", "close"):
            try:
                value = float(cls.value(row, field))
            except (TypeError, ValueError):
                invalid.append(field)
                continue
            if value <= 0:
                invalid.append(field)
        try:
            high = float(cls.value(row, "high"))
            low = float(cls.value(row, "low"))
            if high < low:
                invalid.append("high_low_range")
        except (TypeError, ValueError):
            pass
        return invalid

    @classmethod
    def invalid_volume(cls, row):
        try:
            return int(float(cls.value(row, "volume"))) < 0
        except (TypeError, ValueError):
            return True

    @classmethod
    def stale_data_warnings(cls, rows, max_age_days=10, today=None):
        if not rows:
            return ["Missing OHLCV data"]
        latest = max((cls.parse_date(cls.value(row, "date")) for row in rows), default=None)
        if latest is None:
            return ["Unable to determine latest OHLCV date"]
        reference = today or date.today()
        if isinstance(reference, datetime):
            reference = reference.date()
        if (reference - latest).days > max_age_days:
            return [f"Stale OHLCV data: latest date is {latest.isoformat()}"]
        return []

    @staticmethod
    def parse_date(value):
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        try:
            return datetime.fromisoformat(str(value)).date()
        except (TypeError, ValueError):
            return None

    @staticmethod
    def value(source, key):
        if isinstance(source, dict):
            return source.get(key)
        return getattr(source, key, None)
