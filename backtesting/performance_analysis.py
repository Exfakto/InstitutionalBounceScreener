from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime

from backtesting.equity_curve import EquityCurve


@dataclass(frozen=True)
class PerformanceAnalysis:
    """
    Deterministic drawdown and period-return analytics for an equity curve.
    """

    drawdown_analysis: dict = field(default_factory=dict)
    monthly_returns: dict = field(default_factory=dict)
    yearly_returns: dict = field(default_factory=dict)
    best_month: tuple[str, float] | None = None
    worst_month: tuple[str, float] | None = None
    best_year: tuple[str, float] | None = None
    worst_year: tuple[str, float] | None = None
    positive_months: int = 0
    negative_months: int = 0
    positive_month_rate: float = 0.0
    summary: dict = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    @classmethod
    def from_equity_curve(
        cls,
        equity_curve: EquityCurve,
        initial_equity: float = 100_000.0,
    ) -> "PerformanceAnalysis":
        if not isinstance(equity_curve, EquityCurve):
            raise TypeError("PerformanceAnalysis requires an EquityCurve.")

        warnings = []

        if initial_equity <= 0:
            raise ValueError("initial_equity must be positive.")

        if not equity_curve.equity_values:
            warnings.append("No equity curve data available.")

        drawdown_analysis = cls.calculate_drawdown_analysis(equity_curve)
        monthly_returns = cls.period_returns(equity_curve, initial_equity, "month")
        yearly_returns = cls.period_returns(equity_curve, initial_equity, "year")
        best_month = cls.best_period(monthly_returns)
        worst_month = cls.worst_period(monthly_returns)
        best_year = cls.best_period(yearly_returns)
        worst_year = cls.worst_period(yearly_returns)
        positive_months = len([value for value in monthly_returns.values() if value > 0])
        negative_months = len([value for value in monthly_returns.values() if value < 0])
        month_count = len(monthly_returns)
        positive_month_rate = positive_months / month_count if month_count else 0.0
        summary = {
            "total_return": equity_curve.cumulative_return,
            "annualized_return": equity_curve.cagr,
            "max_drawdown": drawdown_analysis["max_drawdown"],
            "average_drawdown": drawdown_analysis["average_drawdown"],
            "monthly_returns": monthly_returns,
            "yearly_returns": yearly_returns,
            "warnings": warnings,
        }

        return cls(
            drawdown_analysis=drawdown_analysis,
            monthly_returns=monthly_returns,
            yearly_returns=yearly_returns,
            best_month=best_month,
            worst_month=worst_month,
            best_year=best_year,
            worst_year=worst_year,
            positive_months=positive_months,
            negative_months=negative_months,
            positive_month_rate=positive_month_rate,
            summary=summary,
            warnings=warnings,
        )

    @classmethod
    def calculate_drawdown_analysis(cls, equity_curve: EquityCurve) -> dict:
        dates = list(equity_curve.dates)
        drawdowns = list(equity_curve.drawdown_series)

        if not drawdowns:
            return {
                "max_drawdown": 0.0,
                "average_drawdown": 0.0,
                "drawdown_duration": 0,
                "longest_drawdown": 0,
                "recovery_periods": [],
                "current_drawdown": 0.0,
                "drawdown_start_date": None,
                "drawdown_end_date": None,
                "recovery_date": None,
            }

        max_drawdown = min(drawdowns)
        average_drawdown = sum(drawdowns) / len(drawdowns)
        longest_drawdown = 0
        current_duration = 0
        current_start_index = None
        worst_start_index = None
        worst_end_index = drawdowns.index(max_drawdown)
        recovery_index = None
        drawdown_duration = 0

        for index, drawdown in enumerate(drawdowns):
            if drawdown < 0:
                if current_duration == 0:
                    current_start_index = index
                current_duration += 1
            else:
                if current_duration > 0:
                    if current_duration > longest_drawdown:
                        longest_drawdown = current_duration
                    if recovery_index is None and worst_start_index is not None:
                        recovery_index = index
                    current_duration = 0

            if index == worst_end_index:
                worst_start_index = current_start_index

        if current_duration > longest_drawdown:
            longest_drawdown = current_duration

        if worst_start_index is not None:
            drawdown_duration = worst_end_index - worst_start_index + 1

        current_drawdown = drawdowns[-1]
        drawdown_start_date = cls.date_at(dates, worst_start_index)
        drawdown_end_date = cls.date_at(dates, worst_end_index)
        recovery_date = cls.date_at(dates, recovery_index)

        return {
            "max_drawdown": max_drawdown,
            "average_drawdown": average_drawdown,
            "drawdown_duration": drawdown_duration,
            "longest_drawdown": longest_drawdown,
            "recovery_periods": list(equity_curve.recovery_periods),
            "current_drawdown": current_drawdown,
            "drawdown_start_date": drawdown_start_date,
            "drawdown_end_date": drawdown_end_date,
            "recovery_date": recovery_date,
        }

    @classmethod
    def period_returns(
        cls,
        equity_curve: EquityCurve,
        initial_equity: float,
        period: str,
    ) -> dict:
        if not equity_curve.equity_values:
            return {}

        returns = {}
        period_start_equity = initial_equity
        active_period = None

        for raw_date, equity in zip(equity_curve.dates, equity_curve.equity_values):
            current_period = cls.period_key(raw_date, period)

            if active_period is None:
                active_period = current_period

            if current_period != active_period:
                period_start_equity = previous_equity
                active_period = current_period

            returns[current_period] = (
                ((equity - period_start_equity) / period_start_equity) * 100.0
                if period_start_equity
                else 0.0
            )
            previous_equity = equity

        return returns

    @staticmethod
    def best_period(period_returns: dict) -> tuple[str, float] | None:
        if not period_returns:
            return None

        return max(period_returns.items(), key=lambda item: item[1])

    @staticmethod
    def worst_period(period_returns: dict) -> tuple[str, float] | None:
        if not period_returns:
            return None

        return min(period_returns.items(), key=lambda item: item[1])

    @classmethod
    def period_key(cls, value, period):
        parsed = cls.date_value(value)

        if period == "year":
            return f"{parsed.year:04d}"

        if period == "month":
            return f"{parsed.year:04d}-{parsed.month:02d}"

        raise ValueError("Unsupported period.")

    @staticmethod
    def date_at(dates, index):
        if index is None:
            return None

        if index < 0 or index >= len(dates):
            return None

        return dates[index]

    @staticmethod
    def date_value(value) -> date:
        if isinstance(value, datetime):
            return value.date()

        if isinstance(value, date):
            return value

        try:
            return datetime.fromisoformat(str(value)).date()
        except (TypeError, ValueError) as exc:
            raise ValueError("PerformanceAnalysis dates must be date-like values.") from exc
