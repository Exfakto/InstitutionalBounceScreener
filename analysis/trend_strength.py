"""
Trend strength calculation utilities.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


@dataclass(frozen=True)
class TrendStrengthResult:
    """
    Pure trend strength calculation output.
    """

    close_price: float | None
    sma20: float | None
    sma50: float | None
    sma200: float | None
    price_vs_sma20_pct: float | None
    price_vs_sma50_pct: float | None
    price_vs_sma200_pct: float | None
    price_above_sma20: bool
    price_above_sma50: bool
    price_above_sma200: bool
    sma20_above_sma50: bool
    sma50_above_sma200: bool
    trend_score: float
    warnings: list[str] = field(default_factory=list)


class TrendStrengthCalculator:
    """
    Calculate trend quality from price and moving average alignment.

    The score is a v2.1 placeholder heuristic:
    - bullish price/SMA alignment contributes most of the score
    - SMA stack order contributes heavily
    - distance from moving averages adds a smaller adjustment
    """

    REQUIRED_COLUMNS = {"Close"}
    SMA_KEYS = ["sma20", "sma50", "sma200"]

    def calculate(
        self,
        price_history: pd.DataFrame,
        sma_values: dict,
    ) -> TrendStrengthResult:
        warnings = []

        close_price = self.latest_close(price_history, warnings)
        sma20 = self.number_or_none(sma_values, "sma20", warnings)
        sma50 = self.number_or_none(sma_values, "sma50", warnings)
        sma200 = self.number_or_none(sma_values, "sma200", warnings)

        price_vs_sma20_pct = self.distance_pct(close_price, sma20)
        price_vs_sma50_pct = self.distance_pct(close_price, sma50)
        price_vs_sma200_pct = self.distance_pct(close_price, sma200)

        price_above_sma20 = self.greater_than(close_price, sma20)
        price_above_sma50 = self.greater_than(close_price, sma50)
        price_above_sma200 = self.greater_than(close_price, sma200)
        sma20_above_sma50 = self.greater_than(sma20, sma50)
        sma50_above_sma200 = self.greater_than(sma50, sma200)

        score = self.score(
            price_above_sma20=price_above_sma20,
            price_above_sma50=price_above_sma50,
            price_above_sma200=price_above_sma200,
            sma20_above_sma50=sma20_above_sma50,
            sma50_above_sma200=sma50_above_sma200,
            distances=[
                price_vs_sma20_pct,
                price_vs_sma50_pct,
                price_vs_sma200_pct,
            ],
        )

        return TrendStrengthResult(
            close_price=close_price,
            sma20=sma20,
            sma50=sma50,
            sma200=sma200,
            price_vs_sma20_pct=price_vs_sma20_pct,
            price_vs_sma50_pct=price_vs_sma50_pct,
            price_vs_sma200_pct=price_vs_sma200_pct,
            price_above_sma20=price_above_sma20,
            price_above_sma50=price_above_sma50,
            price_above_sma200=price_above_sma200,
            sma20_above_sma50=sma20_above_sma50,
            sma50_above_sma200=sma50_above_sma200,
            trend_score=score,
            warnings=warnings,
        )

    def latest_close(self, price_history, warnings):
        if price_history is None or price_history.empty:
            warnings.append("Missing price history")
            return None

        if not self.REQUIRED_COLUMNS.issubset(price_history.columns):
            warnings.append("Missing required columns: Close")
            return None

        close = pd.to_numeric(price_history["Close"], errors="coerce").dropna()

        if close.empty:
            warnings.append("No usable close prices")
            return None

        return float(close.iloc[-1])

    @staticmethod
    def number_or_none(values, key, warnings):
        value = (values or {}).get(key)

        if value is None or value == "":
            warnings.append(f"Missing {key}")
            return None

        try:
            if pd.isna(value):
                warnings.append(f"Missing {key}")
                return None
            return float(value)
        except (TypeError, ValueError):
            warnings.append(f"Invalid {key}")
            return None

    @staticmethod
    def distance_pct(close_price, moving_average):
        if close_price is None or moving_average is None or moving_average <= 0:
            return None

        return ((close_price - moving_average) / moving_average) * 100.0

    @staticmethod
    def greater_than(left, right):
        if left is None or right is None:
            return False

        return left > right

    def score(
        self,
        price_above_sma20,
        price_above_sma50,
        price_above_sma200,
        sma20_above_sma50,
        sma50_above_sma200,
        distances,
    ):
        score = 0.0

        if price_above_sma20:
            score += 20.0
        if price_above_sma50:
            score += 15.0
        if price_above_sma200:
            score += 15.0
        if sma20_above_sma50:
            score += 25.0
        if sma50_above_sma200:
            score += 20.0

        distance_values = [
            distance
            for distance in distances
            if distance is not None
        ]

        if distance_values:
            average_distance = sum(distance_values) / len(distance_values)
            score += max(-10.0, min(5.0, average_distance * 0.25))

        return self.clamp(score)

    @staticmethod
    def clamp(value):
        return max(0.0, min(100.0, float(value)))
