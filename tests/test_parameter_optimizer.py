import pytest

from backtesting.backtest_models import BacktestTrade
from backtesting.parameter_optimizer import (
    OptimizationParameter,
    OptimizationResult,
    ParameterOptimizationReport,
    ParameterOptimizer,
)
from backtesting.strategy import BacktestStrategy


class ThresholdStrategy(BacktestStrategy):
    def __init__(self, threshold=1, fail_value=None):
        self.threshold = threshold
        self.fail_value = fail_value

    def generate_trades(self, historical_candidates):
        if self.threshold == self.fail_value:
            raise ValueError("bad threshold")

        trades = []

        for candidate in historical_candidates:
            if candidate["score"] < self.threshold:
                continue

            trades.append(
                BacktestTrade(
                    ticker=candidate["ticker"],
                    entry_date="2026-01-01",
                    exit_date="2026-01-02",
                    entry_price=100.0,
                    exit_price=candidate["exit_price"],
                )
            )

        return trades


def candidates():
    return [
        {"ticker": "WIN", "score": 3, "exit_price": 110.0},
        {"ticker": "LOSS", "score": 1, "exit_price": 95.0},
    ]


def test_parameter_optimizer_empty_optimization():
    report = ParameterOptimizer().optimize(candidates(), ThresholdStrategy(), {})

    assert isinstance(report, ParameterOptimizationReport)
    assert report.best_result is None
    assert report.ranked_results == []
    assert report.parameter_count == 0
    assert report.execution_summary == {
        "tested": 0,
        "succeeded": 0,
        "failed": 0,
        "warnings": ["No optimization parameters supplied."],
    }


def test_parameter_optimizer_one_parameter():
    report = ParameterOptimizer().optimize(
        candidates(),
        ThresholdStrategy(),
        {"threshold": [1]},
    )

    assert report.parameter_count == 1
    assert len(report.ranked_results) == 1
    result = report.ranked_results[0]
    assert isinstance(result, OptimizationResult)
    assert result.tested_parameters == {"threshold": 1}
    assert result.statistics.total_trades == 2
    assert result.statistics.wins == 1
    assert result.statistics.losses == 1
    assert result.rank == 1
    assert result.warnings == []


def test_parameter_optimizer_multiple_parameters_and_best_result():
    report = ParameterOptimizer().optimize(
        candidates(),
        ThresholdStrategy(),
        {
            "threshold": [1, 3],
            "max_hold_days": [5],
        },
    )

    assert report.parameter_count == 2
    assert [result.rank for result in report.ranked_results] == [1, 2]
    assert report.best_result == report.ranked_results[0]
    assert report.best_result.tested_parameters == {
        "threshold": 3,
        "max_hold_days": 5,
    }
    assert report.best_result.statistics.total_trades == 1
    assert report.best_result.statistics.win_rate == 1.0


def test_parameter_optimizer_duplicate_parameter_combinations_are_skipped():
    report = ParameterOptimizer().optimize(
        candidates(),
        ThresholdStrategy(),
        {"threshold": [1, 1, 3]},
    )

    assert report.parameter_count == 2
    assert "Skipped 1 duplicate parameter combinations." in report.execution_summary["warnings"]
    assert [result.tested_parameters for result in report.ranked_results] == [
        {"threshold": 3},
        {"threshold": 1},
    ]


def test_parameter_optimizer_rejects_invalid_parameters():
    with pytest.raises(TypeError, match="dictionary or list"):
        ParameterOptimizer().optimize(candidates(), ThresholdStrategy(), object())

    with pytest.raises(ValueError, match="values cannot be empty"):
        ParameterOptimizer().optimize(
            candidates(),
            ThresholdStrategy(),
            {"threshold": []},
        )

    with pytest.raises(TypeError, match="values must be a list"):
        OptimizationParameter("threshold", 1)

    with pytest.raises(TypeError, match="BacktestStrategy"):
        ParameterOptimizer().optimize(candidates(), object(), {"threshold": [1]})


def test_parameter_optimizer_deterministic_ranking():
    optimizer = ParameterOptimizer()
    grid = {"threshold": [1, 3]}

    first = optimizer.optimize(candidates(), ThresholdStrategy(), grid)
    second = optimizer.optimize(candidates(), ThresholdStrategy(), grid)

    assert first == second


def test_parameter_optimizer_warning_propagation_for_empty_candidates():
    report = ParameterOptimizer().optimize(
        [],
        ThresholdStrategy(),
        {"threshold": [1]},
    )

    assert report.ranked_results[0].warnings == ["No historical candidates supplied."]
    assert "No historical candidates supplied." in report.execution_summary["warnings"]


def test_parameter_optimizer_handles_failed_backtests():
    report = ParameterOptimizer().optimize(
        candidates(),
        ThresholdStrategy(fail_value=2),
        {"threshold": [1, 2, 3]},
    )

    failed = [
        result
        for result in report.ranked_results
        if result.tested_parameters == {"threshold": 2}
    ][0]

    assert failed.score == float("-inf")
    assert failed.statistics.total_trades == 0
    assert failed.warnings == ["Backtest failed: bad threshold"]
    assert report.execution_summary["failed"] == 1
    assert report.best_result.tested_parameters == {"threshold": 3}


def test_parameter_optimizer_does_not_mutate_base_strategy():
    strategy = ThresholdStrategy(threshold=99)

    ParameterOptimizer().optimize(
        candidates(),
        strategy,
        {"threshold": [1, 3]},
    )

    assert strategy.threshold == 99
