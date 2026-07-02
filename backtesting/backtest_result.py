from __future__ import annotations

from dataclasses import dataclass, field

from backtesting.backtest_models import BacktestStatistics, BacktestTrade


@dataclass(frozen=True)
class BacktestResult:
    """
    Deterministic output of a backtest run.
    """

    trades: list[BacktestTrade] = field(default_factory=list)
    statistics: BacktestStatistics = field(default_factory=BacktestStatistics)
    warnings: list[str] = field(default_factory=list)
