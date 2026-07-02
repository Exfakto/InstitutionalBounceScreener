from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime

from backtesting.backtest_models import BacktestTrade


@dataclass(frozen=True)
class EquityCurve:
    """
    Realized equity curve built from completed trades in chronological order.
    """

    dates: list[date | datetime | str] = field(default_factory=list)
    equity_values: list[float] = field(default_factory=list)
    cumulative_return: float = 0.0
    peak_equity: float = 0.0
    drawdown_series: list[float] = field(default_factory=list)
    cagr: float = 0.0
    average_drawdown: float = 0.0
    recovery_periods: list[int] = field(default_factory=list)
    rolling_equity_highs: list[float] = field(default_factory=list)

    def performance_analysis(self, initial_equity: float = 100_000.0):
        from backtesting.performance_analysis import PerformanceAnalysis

        return PerformanceAnalysis.from_equity_curve(
            self,
            initial_equity=initial_equity,
        )

    @classmethod
    def from_trades(
        cls,
        trades: list[BacktestTrade],
        initial_equity: float = 100_000.0,
    ) -> "EquityCurve":
        if initial_equity <= 0:
            raise ValueError("initial_equity must be positive.")

        for trade in trades:
            if not isinstance(trade, BacktestTrade):
                raise TypeError("EquityCurve requires BacktestTrade instances.")

        ordered_trades = sorted(
            trades,
            key=lambda trade: cls.date_value(trade.exit_date),
        )

        if not ordered_trades:
            return cls(
                cumulative_return=0.0,
                peak_equity=initial_equity,
            )

        dates = []
        equity_values = []
        drawdowns = []
        rolling_highs = []
        recovery_periods = []
        equity = initial_equity
        peak = initial_equity
        drawdown_start_index = None

        for index, trade in enumerate(ordered_trades):
            equity += trade.profit_loss
            peak_before = peak
            peak = max(peak, equity)
            drawdown = equity - peak

            if drawdown < 0 and drawdown_start_index is None:
                drawdown_start_index = index

            if drawdown_start_index is not None and equity >= peak_before:
                recovery_periods.append(index - drawdown_start_index)
                drawdown_start_index = None

            dates.append(trade.exit_date)
            equity_values.append(equity)
            rolling_highs.append(peak)
            drawdowns.append(drawdown)

        cumulative_return = ((equity_values[-1] - initial_equity) / initial_equity) * 100.0
        average_drawdown = (
            sum(drawdowns) / len(drawdowns)
            if drawdowns
            else 0.0
        )

        return cls(
            dates=dates,
            equity_values=equity_values,
            cumulative_return=cumulative_return,
            peak_equity=peak,
            drawdown_series=drawdowns,
            cagr=cls.cagr(ordered_trades, initial_equity, equity_values[-1]),
            average_drawdown=average_drawdown,
            recovery_periods=recovery_periods,
            rolling_equity_highs=rolling_highs,
        )

    @classmethod
    def cagr(
        cls,
        trades: list[BacktestTrade],
        initial_equity: float,
        final_equity: float,
    ) -> float:
        start = cls.date_value(trades[0].entry_date)
        end = cls.date_value(trades[-1].exit_date)
        days = (end - start).days

        if days <= 0:
            return 0.0

        years = days / 365.25
        return (((final_equity / initial_equity) ** (1.0 / years)) - 1.0) * 100.0

    @staticmethod
    def date_value(value: date | datetime | str) -> date:
        if isinstance(value, datetime):
            return value.date()

        if isinstance(value, date):
            return value

        try:
            return datetime.fromisoformat(str(value)).date()
        except (TypeError, ValueError) as exc:
            raise ValueError("EquityCurve dates must be date-like values.") from exc
