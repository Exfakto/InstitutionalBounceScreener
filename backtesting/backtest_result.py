from __future__ import annotations

from dataclasses import dataclass, field

from backtesting.backtest_models import BacktestStatistics, BacktestTrade
from backtesting.equity_curve import EquityCurve
from backtesting.performance_analysis import PerformanceAnalysis


@dataclass(frozen=True)
class BacktestResult:
    """
    Deterministic output of a backtest run.
    """

    trades: list[BacktestTrade] = field(default_factory=list)
    statistics: BacktestStatistics = field(default_factory=BacktestStatistics)
    equity_curve: EquityCurve = field(default_factory=EquityCurve)
    performance_analysis: PerformanceAnalysis = field(default_factory=PerformanceAnalysis)
    portfolio_analytics: dict = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
