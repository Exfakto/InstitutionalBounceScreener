"""
Relative strength calculation utilities.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


@dataclass(frozen=True)
class RelativeStrengthResult:
    """
    Pure relative strength calculation output.
    """

    rs_3m: float | None
    rs_6m: float | None
    rs_12m: float | None
    rs_score: float
    warnings: list[str] = field(default_factory=list)


class RelativeStrengthCalculator:
    """
    Calculate stock performance versus a benchmark.

    The score mapping is a v2.1 placeholder heuristic:
    - equal performance maps near 50
    - outperformance trends toward 100
    - underperformance trends toward 0
    """

    PERIODS = {
        "rs_3m": 63,
        "rs_6m": 126,
        "rs_12m": 252,
    }

    REQUIRED_COLUMNS = {"Close"}

    def calculate(
        self,
        stock_history: pd.DataFrame,
        benchmark_history: pd.DataFrame,
    ) -> RelativeStrengthResult:
        warnings = []

        stock_close = self.prepare_close_series(stock_history, "stock", warnings)
        benchmark_close = self.prepare_close_series(
            benchmark_history,
            "benchmark",
            warnings,
        )

        if stock_close is None or benchmark_close is None:
            return RelativeStrengthResult(
                rs_3m=None,
                rs_6m=None,
                rs_12m=None,
                rs_score=0.0,
                warnings=warnings,
            )

        aligned = pd.concat(
            [
                stock_close.rename("stock"),
                benchmark_close.rename("benchmark"),
            ],
            axis=1,
            join="inner",
        ).dropna()

        if aligned.empty:
            warnings.append("No overlapping stock and benchmark dates")
            return RelativeStrengthResult(
                rs_3m=None,
                rs_6m=None,
                rs_12m=None,
                rs_score=0.0,
                warnings=warnings,
            )

        values = {}
        calculated = []

        for name, period in self.PERIODS.items():
            rs_value = self.relative_strength_for_period(aligned, period)
            if rs_value is None:
                warnings.append(
                    f"Insufficient overlapping history for {name}"
                )
            else:
                calculated.append(rs_value)
            values[name] = rs_value

        score = self.score_from_relative_strength(calculated)

        return RelativeStrengthResult(
            rs_3m=values["rs_3m"],
            rs_6m=values["rs_6m"],
            rs_12m=values["rs_12m"],
            rs_score=score,
            warnings=warnings,
        )

    def prepare_close_series(
        self,
        history: pd.DataFrame,
        label: str,
        warnings: list[str],
    ) -> pd.Series | None:
        if history is None or history.empty:
            warnings.append(f"Missing {label} price history")
            return None

        if not self.REQUIRED_COLUMNS.issubset(history.columns):
            warnings.append(f"Missing Close column in {label} price history")
            return None

        series = history["Close"].copy()

        if not isinstance(series.index, pd.DatetimeIndex):
            series.index = pd.to_datetime(series.index)

        return series.sort_index()

    def relative_strength_for_period(
        self,
        aligned_history: pd.DataFrame,
        period: int,
    ) -> float | None:
        if len(aligned_history) <= period:
            return None

        start_row = aligned_history.iloc[-(period + 1)]
        end_row = aligned_history.iloc[-1]

        stock_start = float(start_row["stock"])
        stock_end = float(end_row["stock"])
        benchmark_start = float(start_row["benchmark"])
        benchmark_end = float(end_row["benchmark"])

        if stock_start <= 0 or benchmark_start <= 0:
            return None

        stock_return = (stock_end / stock_start) - 1.0
        benchmark_return = (benchmark_end / benchmark_start) - 1.0

        return stock_return - benchmark_return

    def score_from_relative_strength(
        self,
        values: list[float],
    ) -> float:
        if not values:
            return 0.0

        average_relative_strength = sum(values) / len(values)

        # Placeholder v2.1 heuristic:
        # +/-10% average out/underperformance spans roughly 0..100.
        score = 50.0 + (average_relative_strength * 500.0)

        return max(0.0, min(100.0, score))
