from __future__ import annotations

from dataclasses import dataclass, field

from backtesting.backtest_result import BacktestResult


@dataclass(frozen=True)
class StrategyComparisonRow:
    strategy_name: str
    total_trades: int = 0
    win_rate: float = 0.0
    total_return: float = 0.0
    annualized_return: float = 0.0
    max_drawdown: float = 0.0
    profit_factor: float = 0.0
    expectancy: float = 0.0
    average_hold_days: float = 0.0
    score: float = 0.0


@dataclass(frozen=True)
class StrategyComparisonResult:
    strategy_count: int = 0
    rankings: list[str] = field(default_factory=list)
    best_strategy: str | None = None
    worst_strategy: str | None = None
    comparison_rows: list[StrategyComparisonRow] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class StrategyComparisonEngine:
    """
    Deterministic side-by-side comparison for backtest results.

    Score heuristic:
    total_return + win_rate percentage + profit_factor * 10 + max_drawdown.
    Max drawdown is usually negative, so deeper drawdowns lower the score.
    """

    def compare(self, results) -> StrategyComparisonResult:
        if not results:
            return StrategyComparisonResult(
                warnings=["No backtest results supplied."],
            )

        if not isinstance(results, list):
            raise TypeError("Strategy comparison requires a list of results.")

        warnings = []
        rows = []

        for index, result in enumerate(results, start=1):
            row, row_warnings = self.comparison_row(result, index)
            rows.append(row)
            warnings.extend(row_warnings)

        ranked_rows = sorted(
            rows,
            key=lambda row: (-row.score, row.strategy_name),
        )

        return StrategyComparisonResult(
            strategy_count=len(rows),
            rankings=[row.strategy_name for row in ranked_rows],
            best_strategy=ranked_rows[0].strategy_name if ranked_rows else None,
            worst_strategy=ranked_rows[-1].strategy_name if ranked_rows else None,
            comparison_rows=rows,
            warnings=warnings,
        )

    @classmethod
    def comparison_row(cls, result, index):
        data = cls.result_mapping(result)
        warnings = []

        if data is None:
            raise TypeError("Comparison input must be a BacktestResult or dictionary.")

        strategy_name = cls.strategy_name(data, index)
        statistics = cls.value_for(data, "statistics") or {}
        equity_curve = cls.value_for(data, "equity_curve") or {}
        portfolio_analytics = cls.value_for(data, "portfolio_analytics") or {}

        if not cls.has_metric(statistics, "total_trades"):
            warnings.append(f"{strategy_name}: missing total_trades.")

        total_trades = int(cls.metric(statistics, "total_trades", 0) or 0)
        win_rate = cls.metric(statistics, "win_rate", 0.0)
        total_return = cls.first_metric(
            portfolio_analytics,
            equity_curve,
            names=("total_return", "cumulative_return"),
        )
        annualized_return = cls.first_metric(
            portfolio_analytics,
            equity_curve,
            names=("annualized_return", "cagr"),
        )
        max_drawdown = cls.first_metric(
            portfolio_analytics,
            statistics,
            names=("max_drawdown",),
        )
        profit_factor = cls.metric(statistics, "profit_factor", 0.0)
        expectancy = cls.metric(statistics, "expectancy", 0.0)
        average_hold_days = cls.metric(statistics, "average_hold_days", 0.0)
        score = cls.score(
            total_return=total_return,
            win_rate=win_rate,
            max_drawdown=max_drawdown,
            profit_factor=profit_factor,
        )

        return (
            StrategyComparisonRow(
                strategy_name=strategy_name,
                total_trades=total_trades,
                win_rate=win_rate,
                total_return=total_return,
                annualized_return=annualized_return,
                max_drawdown=max_drawdown,
                profit_factor=profit_factor,
                expectancy=expectancy,
                average_hold_days=average_hold_days,
                score=score,
            ),
            warnings,
        )

    @staticmethod
    def score(total_return, win_rate, max_drawdown, profit_factor):
        return total_return + (win_rate * 100.0) + (profit_factor * 10.0) + max_drawdown

    @classmethod
    def first_metric(cls, primary, fallback, names):
        for name in names:
            value = cls.metric(primary, name, None)
            if value is not None:
                return value

            value = cls.metric(fallback, name, None)
            if value is not None:
                return value

        return 0.0

    @classmethod
    def metric(cls, source, name, default):
        value = cls.value_for(source, name)

        if value is None:
            return default

        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @classmethod
    def has_metric(cls, source, name):
        return cls.value_for(source, name) is not None

    @staticmethod
    def strategy_name(data, index):
        name = StrategyComparisonEngine.value_for(data, "strategy_name")
        if name is None:
            name = StrategyComparisonEngine.value_for(data, "name")

        if name in (None, ""):
            return f"Strategy {index}"

        return str(name)

    @staticmethod
    def result_mapping(result):
        if isinstance(result, BacktestResult):
            return {
                "statistics": result.statistics,
                "equity_curve": result.equity_curve,
                "portfolio_analytics": result.portfolio_analytics,
            }

        if isinstance(result, dict):
            return result

        return None

    @staticmethod
    def value_for(source, name):
        if source is None:
            return None

        if isinstance(source, dict):
            return source.get(name)

        return getattr(source, name, None)
