from __future__ import annotations

from copy import copy
from dataclasses import dataclass, field
from itertools import product

from backtesting.backtest_engine import BacktestEngine
from backtesting.backtest_models import BacktestStatistics
from backtesting.strategy import BacktestStrategy


@dataclass(frozen=True)
class OptimizationParameter:
    name: str
    values: list

    def __post_init__(self) -> None:
        if not str(self.name or "").strip():
            raise ValueError("OptimizationParameter requires a name.")

        if not isinstance(self.values, list):
            raise TypeError("OptimizationParameter values must be a list.")

        if not self.values:
            raise ValueError("OptimizationParameter values cannot be empty.")


@dataclass(frozen=True)
class OptimizationResult:
    tested_parameters: dict
    statistics: BacktestStatistics = field(default_factory=BacktestStatistics)
    score: float = 0.0
    rank: int | None = None
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ParameterOptimizationReport:
    best_result: OptimizationResult | None = None
    ranked_results: list[OptimizationResult] = field(default_factory=list)
    parameter_count: int = 0
    execution_summary: dict = field(default_factory=dict)


class ParameterOptimizer:
    """
    Deterministic grid-search optimizer for backtest strategy parameters.

    Score heuristic:
    win_rate percentage + expectancy + profit_factor * 10 + max_drawdown + total_return.
    Max drawdown is usually negative, so deeper drawdowns lower the score.
    """

    def __init__(self, backtest_engine: BacktestEngine | None = None):
        self.backtest_engine = backtest_engine or BacktestEngine()

    def optimize(self, historical_candidates, strategy, parameter_grid):
        if not isinstance(strategy, BacktestStrategy):
            raise TypeError("strategy must implement BacktestStrategy.")

        parameters = self.normalize_parameter_grid(parameter_grid)

        if not parameters:
            return ParameterOptimizationReport(
                parameter_count=0,
                execution_summary={
                    "tested": 0,
                    "succeeded": 0,
                    "failed": 0,
                    "warnings": ["No optimization parameters supplied."],
                },
            )

        combinations, duplicate_count = self.parameter_combinations(parameters)
        results = [
            self.evaluate_combination(historical_candidates, strategy, combination)
            for combination in combinations
        ]
        ranked_results = self.rank_results(results)
        warnings = []

        if duplicate_count:
            warnings.append(f"Skipped {duplicate_count} duplicate parameter combinations.")

        for result in ranked_results:
            warnings.extend(result.warnings)

        failed = len([result for result in ranked_results if result.warnings])

        return ParameterOptimizationReport(
            best_result=ranked_results[0] if ranked_results else None,
            ranked_results=ranked_results,
            parameter_count=len(combinations),
            execution_summary={
                "tested": len(combinations),
                "succeeded": len(combinations) - failed,
                "failed": failed,
                "warnings": warnings,
            },
        )

    def evaluate_combination(self, historical_candidates, strategy, parameters):
        try:
            configured_strategy = self.configured_strategy(strategy, parameters)
            result = self.backtest_engine.run_backtest(
                historical_candidates,
                configured_strategy,
            )
            return OptimizationResult(
                tested_parameters=dict(parameters),
                statistics=result.statistics,
                score=self.score(result.statistics, result),
                warnings=list(result.warnings),
            )
        except Exception as exc:
            return OptimizationResult(
                tested_parameters=dict(parameters),
                statistics=BacktestStatistics(),
                score=float("-inf"),
                warnings=[f"Backtest failed: {exc}"],
            )

    @staticmethod
    def configured_strategy(strategy, parameters):
        configured = copy(strategy)

        if hasattr(configured, "with_parameters"):
            candidate = configured.with_parameters(**parameters)
            if candidate is not None:
                configured = candidate

        for name, value in parameters.items():
            setattr(configured, name, value)

        return configured

    @classmethod
    def normalize_parameter_grid(cls, parameter_grid):
        if parameter_grid in (None, {}, []):
            return []

        if isinstance(parameter_grid, dict):
            items = [
                OptimizationParameter(name, values)
                for name, values in parameter_grid.items()
            ]
        elif isinstance(parameter_grid, list):
            items = []
            for item in parameter_grid:
                if isinstance(item, OptimizationParameter):
                    items.append(item)
                elif isinstance(item, dict):
                    items.append(
                        OptimizationParameter(
                            item.get("name"),
                            item.get("values"),
                        )
                    )
                else:
                    raise TypeError("Parameter grid entries must be parameters or dictionaries.")
        else:
            raise TypeError("parameter_grid must be a dictionary or list.")

        names = [item.name for item in items]
        if len(names) != len(set(names)):
            raise ValueError("Duplicate optimization parameter names are not allowed.")

        return items

    @staticmethod
    def parameter_combinations(parameters):
        names = [parameter.name for parameter in parameters]
        raw_combinations = [
            dict(zip(names, values))
            for values in product(*[parameter.values for parameter in parameters])
        ]
        seen = set()
        combinations = []
        duplicate_count = 0

        for combination in raw_combinations:
            key = tuple((name, combination[name]) for name in names)

            if key in seen:
                duplicate_count += 1
                continue

            seen.add(key)
            combinations.append(combination)

        return combinations, duplicate_count

    @classmethod
    def rank_results(cls, results):
        ranked = sorted(
            results,
            key=lambda result: (
                -result.score,
                tuple(sorted(result.tested_parameters.items())),
            ),
        )

        return [
            OptimizationResult(
                tested_parameters=result.tested_parameters,
                statistics=result.statistics,
                score=result.score,
                rank=index,
                warnings=result.warnings,
            )
            for index, result in enumerate(ranked, start=1)
        ]

    @staticmethod
    def score(statistics, backtest_result):
        total_return = 0.0

        if hasattr(backtest_result, "portfolio_analytics"):
            total_return = backtest_result.portfolio_analytics.get("total_return", 0.0)

        return (
            (statistics.win_rate * 100.0)
            + statistics.expectancy
            + (statistics.profit_factor * 10.0)
            + statistics.max_drawdown
            + total_return
        )
