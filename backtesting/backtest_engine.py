from __future__ import annotations

from backtesting.backtest_models import BacktestStatistics, BacktestTrade
from backtesting.backtest_result import BacktestResult
from backtesting.strategy import BacktestStrategy


class BacktestEngine:
    """
    Deterministic architecture shell for historical strategy evaluation.
    """

    def run_backtest(self, historical_candidates, strategy) -> BacktestResult:
        if not isinstance(strategy, BacktestStrategy):
            raise TypeError("strategy must implement BacktestStrategy.")

        candidates = historical_candidates or []
        trades = list(strategy.generate_trades(candidates))
        warnings = []

        for trade in trades:
            if not isinstance(trade, BacktestTrade):
                raise TypeError("strategy generated an invalid trade.")

        if not candidates:
            warnings.append("No historical candidates supplied.")

        return BacktestResult(
            trades=trades,
            statistics=self.calculate_statistics(trades),
            warnings=warnings,
        )

    @classmethod
    def calculate_statistics(cls, trades: list[BacktestTrade]) -> BacktestStatistics:
        total = len(trades)

        if total == 0:
            return BacktestStatistics()

        returns = [trade.return_pct for trade in trades]
        gains = [value for value in returns if value > 0]
        losses = [value for value in returns if value < 0]
        wins = len(gains)
        loss_count = len(losses)
        win_rate = wins / total
        average_gain = sum(gains) / len(gains) if gains else 0.0
        average_loss = sum(losses) / len(losses) if losses else 0.0
        expectancy = (win_rate * average_gain) + ((1.0 - win_rate) * average_loss)
        average_hold_days = sum(trade.hold_days for trade in trades) / total

        return BacktestStatistics(
            total_trades=total,
            wins=wins,
            losses=loss_count,
            win_rate=win_rate,
            average_gain=average_gain,
            average_loss=average_loss,
            expectancy=expectancy,
            average_hold_days=average_hold_days,
            max_drawdown=cls.max_drawdown(trades),
            largest_winner=max(gains) if gains else 0.0,
            largest_loser=min(losses) if losses else 0.0,
        )

    @staticmethod
    def max_drawdown(trades: list[BacktestTrade]) -> float:
        equity = 0.0
        peak = 0.0
        max_drawdown = 0.0

        for trade in trades:
            equity += trade.profit_loss
            peak = max(peak, equity)
            drawdown = equity - peak
            max_drawdown = min(max_drawdown, drawdown)

        return max_drawdown
