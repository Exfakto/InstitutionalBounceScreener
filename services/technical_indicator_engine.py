"""
Deterministic technical indicator engine for OHLCV price history.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from math import isfinite


@dataclass(frozen=True)
class TechnicalIndicatorResult:
    ticker: str | None = None
    date: object | None = None
    close: float | None = None
    ema20: float | None = None
    ema50: float | None = None
    ema200: float | None = None
    rsi14: float | None = None
    macd: float | None = None
    macd_signal: float | None = None
    macd_histogram: float | None = None
    atr14: float | None = None
    vwap: float | None = None
    average_volume_20: float | None = None
    relative_volume: float | None = None
    distance_from_ema20: float | None = None
    distance_from_ema50: float | None = None
    distance_from_ema200: float | None = None
    warnings: list[str] = field(default_factory=list)


class TechnicalIndicatorEngine:
    """
    Calculate latest technical indicators from chronological OHLCV rows.
    """

    REQUIRED_FIELDS = ("high", "low", "close")

    def calculate(self, price_history, ticker=None):
        rows, warnings = self.normalize_rows(price_history)
        if not rows:
            return TechnicalIndicatorResult(
                ticker=ticker,
                warnings=["Missing price history"],
            )

        closes = [row["close"] for row in rows]
        highs = [row["high"] for row in rows]
        lows = [row["low"] for row in rows]
        volumes = [row.get("volume") for row in rows]
        latest = rows[-1]
        close = latest["close"]

        ema20 = self.latest_ema(closes, 20)
        ema50 = self.latest_ema(closes, 50)
        ema200 = self.latest_ema(closes, 200)
        macd_line, macd_signal, macd_histogram = self.latest_macd(closes)
        average_volume_20 = self.latest_average(volumes, 20)
        latest_volume = volumes[-1]

        return TechnicalIndicatorResult(
            ticker=ticker or latest.get("ticker"),
            date=latest.get("date"),
            close=close,
            ema20=ema20,
            ema50=ema50,
            ema200=ema200,
            rsi14=self.latest_rsi(closes, 14),
            macd=macd_line,
            macd_signal=macd_signal,
            macd_histogram=macd_histogram,
            atr14=self.latest_atr(highs, lows, closes, 14),
            vwap=self.latest_vwap(rows),
            average_volume_20=average_volume_20,
            relative_volume=self.safe_divide(latest_volume, average_volume_20),
            distance_from_ema20=self.distance_percent(close, ema20),
            distance_from_ema50=self.distance_percent(close, ema50),
            distance_from_ema200=self.distance_percent(close, ema200),
            warnings=warnings,
        )

    def normalize_rows(self, price_history):
        if not price_history:
            return [], []

        rows = []
        warnings = []
        for index, source in enumerate(price_history):
            row = {
                "ticker": self.row_value(source, "ticker"),
                "date": self.row_value(source, "date") or self.row_value(source, "timestamp"),
                "open": self.clean_number(self.row_value(source, "open")),
                "high": self.clean_number(self.row_value(source, "high")),
                "low": self.clean_number(self.row_value(source, "low")),
                "close": self.clean_number(self.row_value(source, "close")),
                "volume": self.clean_number(self.row_value(source, "volume")),
            }
            missing = [field for field in self.REQUIRED_FIELDS if row[field] is None]
            if missing:
                warnings.append(
                    f"Skipped row {index}: missing {', '.join(missing)}"
                )
                continue
            rows.append(row)

        rows.sort(key=self.sort_key)
        if not rows:
            warnings.append("No valid OHLC rows")
        return rows, warnings

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
    def ema_series(values, period):
        if len(values) < period or any(value is None for value in values):
            return []
        multiplier = 2 / (period + 1)
        ema = sum(values[:period]) / period
        series = [None] * (period - 1) + [ema]
        for value in values[period:]:
            ema = (value - ema) * multiplier + ema
            series.append(ema)
        return series

    def latest_ema(self, values, period):
        series = self.ema_series(values, period)
        return series[-1] if series else None

    def latest_macd(self, closes):
        ema12 = self.ema_series(closes, 12)
        ema26 = self.ema_series(closes, 26)
        if not ema12 or not ema26:
            return None, None, None

        macd_values = []
        for fast, slow in zip(ema12, ema26):
            if fast is None or slow is None:
                continue
            macd_values.append(fast - slow)

        if not macd_values:
            return None, None, None

        signal = self.latest_ema(macd_values, 9)
        macd = macd_values[-1]
        histogram = macd - signal if signal is not None else None
        return macd, signal, histogram

    @staticmethod
    def latest_rsi(closes, period):
        if len(closes) < period + 1:
            return None

        gains = []
        losses = []
        for previous, current in zip(closes[-period - 1 : -1], closes[-period:]):
            change = current - previous
            gains.append(max(change, 0))
            losses.append(abs(min(change, 0)))

        average_gain = sum(gains) / period
        average_loss = sum(losses) / period
        if average_loss == 0:
            return 100.0 if average_gain > 0 else 50.0
        relative_strength = average_gain / average_loss
        return 100 - (100 / (1 + relative_strength))

    @staticmethod
    def latest_atr(highs, lows, closes, period):
        if len(closes) < period + 1:
            return None

        true_ranges = []
        start = len(closes) - period
        for index in range(start, len(closes)):
            high = highs[index]
            low = lows[index]
            previous_close = closes[index - 1]
            true_ranges.append(
                max(
                    high - low,
                    abs(high - previous_close),
                    abs(low - previous_close),
                )
            )
        return sum(true_ranges) / period

    @staticmethod
    def latest_vwap(rows):
        numerator = 0.0
        denominator = 0.0
        for row in rows:
            volume = row.get("volume")
            if volume is None or volume <= 0:
                continue
            typical_price = (row["high"] + row["low"] + row["close"]) / 3
            numerator += typical_price * volume
            denominator += volume
        if denominator == 0:
            return None
        return numerator / denominator

    @staticmethod
    def latest_average(values, period):
        if len(values) < period:
            return None
        window = values[-period:]
        if any(value is None for value in window):
            return None
        return sum(window) / period

    @staticmethod
    def safe_divide(numerator, denominator):
        if numerator is None or denominator in (None, 0):
            return None
        return numerator / denominator

    @staticmethod
    def distance_percent(value, baseline):
        if value is None or baseline in (None, 0):
            return None
        return ((value - baseline) / baseline) * 100
