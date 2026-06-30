"""
ATR risk calculation utilities.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


@dataclass(frozen=True)
class ATRRiskResult:
    """
    Pure ATR risk calculation output.
    """

    close_price: float | None
    atr14: float | None
    atr_pct: float | None
    expected_daily_move_pct: float | None
    suggested_stop_pct: float | None
    volatility_score: float
    risk_score: float
    warnings: list[str] = field(default_factory=list)


class ATRRiskCalculator:
    """
    Calculate ATR-based volatility and risk metrics from OHLC history.

    The scores are v2.1 placeholder heuristics:
    - volatility_score rises as ATR% rises
    - risk_score is best around moderate ATR%
    - very low ATR% is not perfect because opportunity may be limited
    - very high ATR% receives a risk penalty
    - suggested stop uses 1.75x ATR%
    """

    REQUIRED_COLUMNS = {"High", "Low", "Close"}
    ATR_WINDOW = 14

    def calculate(self, price_history: pd.DataFrame) -> ATRRiskResult:
        warnings = []

        dataframe = self.prepare_history(price_history, warnings)

        if dataframe is None:
            return self.empty_result(warnings)

        if len(dataframe) < self.ATR_WINDOW + 1:
            warnings.append("Insufficient history for ATR14")
            return self.empty_result(warnings)

        true_range = self.true_range(dataframe)
        atr14 = float(true_range.tail(self.ATR_WINDOW).mean())
        close_price = float(dataframe["Close"].iloc[-1])

        if close_price <= 0:
            warnings.append("Latest close price must be greater than zero")
            return self.empty_result(warnings)

        atr_pct = (atr14 / close_price) * 100.0
        expected_daily_move_pct = atr_pct
        suggested_stop_pct = atr_pct * 1.75
        volatility_score = self.volatility_score(atr_pct)
        risk_score = self.risk_score(atr_pct)

        return ATRRiskResult(
            close_price=close_price,
            atr14=atr14,
            atr_pct=atr_pct,
            expected_daily_move_pct=expected_daily_move_pct,
            suggested_stop_pct=suggested_stop_pct,
            volatility_score=volatility_score,
            risk_score=risk_score,
            warnings=warnings,
        )

    def prepare_history(self, price_history, warnings):
        if price_history is None or price_history.empty:
            warnings.append("Missing price history")
            return None

        missing_columns = self.REQUIRED_COLUMNS - set(price_history.columns)

        if missing_columns:
            warnings.append(
                "Missing required columns: " + ", ".join(sorted(missing_columns))
            )
            return None

        dataframe = price_history.copy().sort_index()

        for column in self.REQUIRED_COLUMNS:
            dataframe[column] = pd.to_numeric(dataframe[column], errors="coerce")

        dataframe = dataframe.dropna(subset=list(self.REQUIRED_COLUMNS))

        if dataframe.empty:
            warnings.append("No usable OHLC rows")
            return None

        return dataframe

    @staticmethod
    def true_range(dataframe):
        previous_close = dataframe["Close"].shift(1)

        ranges = pd.concat(
            [
                dataframe["High"] - dataframe["Low"],
                (dataframe["High"] - previous_close).abs(),
                (dataframe["Low"] - previous_close).abs(),
            ],
            axis=1,
        )

        return ranges.max(axis=1)

    def volatility_score(self, atr_pct):
        if atr_pct is None:
            return 0.0

        # Placeholder heuristic: 0% to 10% ATR maps to 0..100 volatility.
        return self.clamp((atr_pct / 10.0) * 100.0)

    def risk_score(self, atr_pct):
        if atr_pct is None:
            return 0.0

        if atr_pct < 1.0:
            # Very low volatility can mean limited opportunity.
            score = 65.0 + (atr_pct * 10.0)
        elif atr_pct <= 3.0:
            # Moderate volatility is the preferred risk/reward band.
            score = 90.0 - abs(atr_pct - 2.0) * 5.0
        elif atr_pct <= 6.0:
            score = 85.0 - ((atr_pct - 3.0) * 15.0)
        else:
            score = 40.0 - ((atr_pct - 6.0) * 8.0)

        return self.clamp(score)

    @staticmethod
    def empty_result(warnings):
        return ATRRiskResult(
            close_price=None,
            atr14=None,
            atr_pct=None,
            expected_daily_move_pct=None,
            suggested_stop_pct=None,
            volatility_score=0.0,
            risk_score=0.0,
            warnings=warnings,
        )

    @staticmethod
    def clamp(value):
        return max(0.0, min(100.0, float(value)))
