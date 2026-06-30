"""
Volume intelligence calculation utilities.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


@dataclass(frozen=True)
class VolumeIntelligenceResult:
    """
    Pure volume intelligence calculation output.
    """

    avg_volume_20: float | None
    avg_volume_50: float | None
    relative_volume: float | None
    dollar_volume: float | None
    volume_trend_score: float
    liquidity_score: float
    volume_score: float
    warnings: list[str] = field(default_factory=list)


class VolumeIntelligenceCalculator:
    """
    Calculate liquidity, relative volume, and trend metrics.

    The scores are v2.1 placeholder heuristics:
    - dollar volume maps liquidity from thin trading toward institutional scale
    - relative volume around 1.0 is neutral
    - relative volume above 1.5 improves volume score
    - relative volume below 0.7 reduces volume score
    - avg_volume_20 above avg_volume_50 improves trend score
    """

    REQUIRED_COLUMNS = {"Close", "Volume"}

    def calculate(self, price_history: pd.DataFrame) -> VolumeIntelligenceResult:
        warnings = []

        if price_history is None or price_history.empty:
            warnings.append("Missing price history")
            return self.empty_result(warnings)

        missing_columns = self.REQUIRED_COLUMNS - set(price_history.columns)

        if missing_columns:
            warnings.append(
                "Missing required columns: " + ", ".join(sorted(missing_columns))
            )
            return self.empty_result(warnings)

        dataframe = price_history.copy()
        dataframe = dataframe.sort_index()
        dataframe["Close"] = pd.to_numeric(dataframe["Close"], errors="coerce")
        dataframe["Volume"] = pd.to_numeric(dataframe["Volume"], errors="coerce")
        dataframe = dataframe.dropna(subset=["Close", "Volume"])

        if dataframe.empty:
            warnings.append("No usable close and volume rows")
            return self.empty_result(warnings)

        if len(dataframe) < 20:
            warnings.append("Insufficient history for avg_volume_20")

        if len(dataframe) < 50:
            warnings.append("Insufficient history for avg_volume_50")

        latest = dataframe.iloc[-1]
        latest_close = float(latest["Close"])
        latest_volume = float(latest["Volume"])
        avg_volume_20 = self.average_volume(dataframe, 20)
        avg_volume_50 = self.average_volume(dataframe, 50)
        relative_volume = self.relative_volume(latest_volume, avg_volume_20)
        dollar_volume = latest_close * latest_volume
        trend_score = self.volume_trend_score(avg_volume_20, avg_volume_50)
        liquidity_score = self.liquidity_score(dollar_volume)
        volume_score = self.volume_score(relative_volume, trend_score, liquidity_score)

        return VolumeIntelligenceResult(
            avg_volume_20=avg_volume_20,
            avg_volume_50=avg_volume_50,
            relative_volume=relative_volume,
            dollar_volume=dollar_volume,
            volume_trend_score=trend_score,
            liquidity_score=liquidity_score,
            volume_score=volume_score,
            warnings=warnings,
        )

    def empty_result(self, warnings):
        return VolumeIntelligenceResult(
            avg_volume_20=None,
            avg_volume_50=None,
            relative_volume=None,
            dollar_volume=None,
            volume_trend_score=0.0,
            liquidity_score=0.0,
            volume_score=0.0,
            warnings=warnings,
        )

    @staticmethod
    def average_volume(dataframe, window):
        if len(dataframe) < window:
            return None

        return float(dataframe["Volume"].tail(window).mean())

    @staticmethod
    def relative_volume(latest_volume, avg_volume_20):
        if avg_volume_20 is None or avg_volume_20 <= 0:
            return None

        return float(latest_volume / avg_volume_20)

    def volume_trend_score(self, avg_volume_20, avg_volume_50):
        if avg_volume_20 is None or avg_volume_50 is None or avg_volume_50 <= 0:
            return 0.0

        trend_ratio = avg_volume_20 / avg_volume_50

        # Placeholder heuristic: flat trend is 50; +/-50% trend spans 0..100.
        return self.clamp(50.0 + ((trend_ratio - 1.0) * 100.0))

    def liquidity_score(self, dollar_volume):
        if dollar_volume is None or dollar_volume <= 0:
            return 0.0

        # Placeholder heuristic: $0 to $100M daily dollar volume maps 0..100.
        return self.clamp((dollar_volume / 100_000_000.0) * 100.0)

    def volume_score(self, relative_volume, trend_score, liquidity_score):
        if relative_volume is None:
            return 0.0

        if relative_volume >= 1.5:
            relative_score = 75.0 + min(25.0, (relative_volume - 1.5) * 25.0)
        elif relative_volume >= 0.7:
            relative_score = 50.0 + ((relative_volume - 1.0) * 50.0)
        else:
            relative_score = max(0.0, relative_volume / 0.7 * 35.0)

        blended = (
            self.clamp(relative_score) * 0.5
            + trend_score * 0.25
            + liquidity_score * 0.25
        )

        return self.clamp(blended)

    @staticmethod
    def clamp(value):
        return max(0.0, min(100.0, float(value)))
