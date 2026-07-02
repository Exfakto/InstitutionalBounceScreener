from copy import deepcopy

import pytest

from backtesting.backtest_models import BacktestStatistics
from backtesting.backtest_result import BacktestResult
from backtesting.equity_curve import EquityCurve
from backtesting.strategy_comparison import (
    StrategyComparisonEngine,
    StrategyComparisonResult,
    StrategyComparisonRow,
)


def result(
    name,
    total_trades=10,
    win_rate=0.5,
    total_return=10.0,
    annualized_return=8.0,
    max_drawdown=-5.0,
    profit_factor=1.5,
    expectancy=2.0,
    average_hold_days=4.0,
):
    return {
        "strategy_name": name,
        "statistics": {
            "total_trades": total_trades,
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "expectancy": expectancy,
            "average_hold_days": average_hold_days,
            "max_drawdown": max_drawdown,
        },
        "equity_curve": {
            "cumulative_return": total_return,
            "cagr": annualized_return,
        },
        "portfolio_analytics": {
            "total_return": total_return,
            "annualized_return": annualized_return,
            "max_drawdown": max_drawdown,
        },
    }


def test_strategy_comparison_empty_input_returns_safe_result():
    comparison = StrategyComparisonEngine().compare([])

    assert isinstance(comparison, StrategyComparisonResult)
    assert comparison.strategy_count == 0
    assert comparison.rankings == []
    assert comparison.best_strategy is None
    assert comparison.worst_strategy is None
    assert comparison.comparison_rows == []
    assert comparison.warnings == ["No backtest results supplied."]


def test_strategy_comparison_single_strategy():
    comparison = StrategyComparisonEngine().compare([result("Default")])

    assert comparison.strategy_count == 1
    assert comparison.rankings == ["Default"]
    assert comparison.best_strategy == "Default"
    assert comparison.worst_strategy == "Default"
    assert comparison.comparison_rows == [
        StrategyComparisonRow(
            strategy_name="Default",
            total_trades=10,
            win_rate=0.5,
            total_return=10.0,
            annualized_return=8.0,
            max_drawdown=-5.0,
            profit_factor=1.5,
            expectancy=2.0,
            average_hold_days=4.0,
            score=70.0,
        )
    ]


def test_strategy_comparison_multiple_strategies_best_and_worst():
    comparison = StrategyComparisonEngine().compare(
        [
            result("Base", total_return=8.0, win_rate=0.5, max_drawdown=-8.0, profit_factor=1.2),
            result("Strong", total_return=20.0, win_rate=0.7, max_drawdown=-4.0, profit_factor=2.0),
            result("Weak", total_return=-3.0, win_rate=0.3, max_drawdown=-12.0, profit_factor=0.8),
        ]
    )

    assert comparison.strategy_count == 3
    assert comparison.rankings == ["Strong", "Base", "Weak"]
    assert comparison.best_strategy == "Strong"
    assert comparison.worst_strategy == "Weak"


def test_strategy_comparison_accepts_backtest_result_objects():
    backtest_result = BacktestResult(
        statistics=BacktestStatistics(
            total_trades=4,
            win_rate=0.75,
            profit_factor=2.5,
            expectancy=4.0,
            average_hold_days=3.0,
            max_drawdown=-2.0,
        ),
        equity_curve=EquityCurve(
            cumulative_return=12.0,
            cagr=11.0,
            drawdown_series=[0.0, -2.0],
        ),
        portfolio_analytics={
            "total_return": 12.0,
            "annualized_return": 11.0,
            "max_drawdown": -2.0,
        },
    )

    comparison = StrategyComparisonEngine().compare([backtest_result])

    row = comparison.comparison_rows[0]
    assert row.strategy_name == "Strategy 1"
    assert row.total_trades == 4
    assert row.win_rate == 0.75
    assert row.total_return == 12.0
    assert row.annualized_return == 11.0
    assert row.max_drawdown == -2.0
    assert row.profit_factor == 2.5
    assert row.expectancy == 4.0
    assert row.average_hold_days == 3.0


def test_strategy_comparison_handles_missing_metrics_safely():
    comparison = StrategyComparisonEngine().compare(
        [
            {
                "strategy_name": "Sparse",
                "statistics": {},
                "equity_curve": {},
                "portfolio_analytics": {},
            }
        ]
    )

    row = comparison.comparison_rows[0]
    assert row.strategy_name == "Sparse"
    assert row.total_trades == 0
    assert row.win_rate == 0.0
    assert row.total_return == 0.0
    assert row.score == 0.0
    assert comparison.warnings == ["Sparse: missing total_trades."]


def test_strategy_comparison_ties_are_sorted_by_strategy_name():
    comparison = StrategyComparisonEngine().compare(
        [
            result("Zulu", total_return=10.0, win_rate=0.5, max_drawdown=-5.0, profit_factor=1.0),
            result("Alpha", total_return=10.0, win_rate=0.5, max_drawdown=-5.0, profit_factor=1.0),
        ]
    )

    assert comparison.rankings == ["Alpha", "Zulu"]
    assert comparison.best_strategy == "Alpha"
    assert comparison.worst_strategy == "Zulu"


def test_strategy_comparison_output_is_deterministic():
    inputs = [
        result("A", total_return=5.0),
        result("B", total_return=7.0),
    ]
    engine = StrategyComparisonEngine()

    assert engine.compare(inputs) == engine.compare(inputs)


def test_strategy_comparison_does_not_mutate_input_results():
    inputs = [
        result("A", total_return=5.0),
        result("B", total_return=7.0),
    ]
    original = deepcopy(inputs)

    StrategyComparisonEngine().compare(inputs)

    assert inputs == original


def test_strategy_comparison_rejects_invalid_input_type():
    with pytest.raises(TypeError, match="list"):
        StrategyComparisonEngine().compare(object())

    with pytest.raises(TypeError, match="BacktestResult"):
        StrategyComparisonEngine().compare([object()])
