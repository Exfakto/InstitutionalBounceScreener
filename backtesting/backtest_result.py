from __future__ import annotations

from dataclasses import dataclass, field

from backtesting.backtest_models import BacktestStatistics, BacktestTrade
from backtesting.equity_curve import EquityCurve


@dataclass(frozen=True)
class BacktestResult:
    """
    Deterministic output of a backtest run.
    """

    trades: list[BacktestTrade] = field(default_factory=list)
    statistics: BacktestStatistics = field(default_factory=BacktestStatistics)
    equity_curve: EquityCurve = field(default_factory=EquityCurve)
    portfolio_analytics: dict = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
