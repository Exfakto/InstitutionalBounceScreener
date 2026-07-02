from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from backtesting.backtest_engine import BacktestEngine
from backtesting.backtest_models import BacktestStatistics, BacktestTrade
from backtesting.parameter_optimizer import ParameterOptimizer
from backtesting.strategy import BacktestStrategy


@dataclass(frozen=True)
class WalkForwardWindow:
    training_start: date
    training_end: date
    validation_start: date
    validation_end: date
    selected_parameters: dict = field(default_factory=dict)
    training_statistics: BacktestStatistics = field(default_factory=BacktestStatistics)
    validation_statistics: BacktestStatistics = field(default_factory=BacktestStatistics)
    validation_trades: list[BacktestTrade] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class WalkForwardResult:
    windows: list[WalkForwardWindow] = field(default_factory=list)
    window_count: int = 0
    best_window: WalkForwardWindow | None = None
    worst_window: WalkForwardWindow | None = None
    aggregate_validation_statistics: BacktestStatistics = field(default_factory=BacktestStatistics)
    stability_score: float = 0.0
    warnings: list[str] = field(default_factory=list)


class WalkForwardValidator:
    """
    Deterministic walk-forward validator using grid optimization per window.
    """

    def __init__(
        self,
        backtest_engine: BacktestEngine | None = None,
        optimizer: ParameterOptimizer | None = None,
    ):
        self.backtest_engine = backtest_engine or BacktestEngine()
        self.optimizer = optimizer or ParameterOptimizer(self.backtest_engine)

    def validate(
        self,
        historical_candidates,
        strategy,
        parameter_grid,
        training_window_days,
        validation_window_days,
        step_days=None,
    ) -> WalkForwardResult:
        if not isinstance(strategy, BacktestStrategy):
            raise TypeError("strategy must implement BacktestStrategy.")

        training_days = self.positive_days(training_window_days, "training_window_days")
        validation_days = self.positive_days(validation_window_days, "validation_window_days")
        step = self.positive_days(
            validation_window_days if step_days is None else step_days,
            "step_days",
        )
        warnings = []

        try:
            parameters = self.optimizer.normalize_parameter_grid(parameter_grid)
        except (TypeError, ValueError) as exc:
            return WalkForwardResult(warnings=[f"Invalid parameter grid: {exc}"])

        if not parameters:
            return WalkForwardResult(
                warnings=["No optimization parameters supplied."],
            )

        candidates, candidate_warnings = self.normalized_candidates(historical_candidates)
        warnings.extend(candidate_warnings)

        if not candidates:
            if not warnings:
                warnings.append("No historical candidates supplied.")
            return WalkForwardResult(warnings=warnings)

        windows = self.window_ranges(candidates, training_days, validation_days, step)

        if not windows:
            warnings.append("Insufficient historical data for walk-forward validation.")
            return WalkForwardResult(warnings=warnings)

        walk_forward_windows = [
            self.evaluate_window(
                candidates,
                strategy,
                parameter_grid,
                training_start,
                training_end,
                validation_start,
                validation_end,
            )
            for training_start, training_end, validation_start, validation_end in windows
        ]
        all_validation_trades = [
            trade
            for window in walk_forward_windows
            for trade in window.validation_trades
        ]
        aggregate_statistics = self.backtest_engine.calculate_statistics(
            all_validation_trades
        )
        stability_score = self.stability_score(walk_forward_windows)

        warnings.extend(
            warning
            for window in walk_forward_windows
            for warning in window.warnings
        )

        ranked_windows = sorted(
            walk_forward_windows,
            key=lambda window: (
                -self.window_score(window),
                window.validation_start,
            ),
        )

        return WalkForwardResult(
            windows=walk_forward_windows,
            window_count=len(walk_forward_windows),
            best_window=ranked_windows[0] if ranked_windows else None,
            worst_window=ranked_windows[-1] if ranked_windows else None,
            aggregate_validation_statistics=aggregate_statistics,
            stability_score=stability_score,
            warnings=warnings,
        )

    def evaluate_window(
        self,
        candidates,
        strategy,
        parameter_grid,
        training_start,
        training_end,
        validation_start,
        validation_end,
    ) -> WalkForwardWindow:
        training_candidates = self.candidates_in_range(
            candidates,
            training_start,
            training_end,
        )
        validation_candidates = self.candidates_in_range(
            candidates,
            validation_start,
            validation_end,
        )
        warnings = []

        optimization = self.optimizer.optimize(
            training_candidates,
            strategy,
            parameter_grid,
        )
        selected_parameters = (
            dict(optimization.best_result.tested_parameters)
            if optimization.best_result is not None
            else {}
        )

        warnings.extend(optimization.execution_summary.get("warnings") or [])

        if not selected_parameters:
            warnings.append("No selected parameters for validation window.")

        validation_strategy = self.optimizer.configured_strategy(
            strategy,
            selected_parameters,
        )
        validation_result = self.backtest_engine.run_backtest(
            validation_candidates,
            validation_strategy,
        )
        warnings.extend(validation_result.warnings)

        return WalkForwardWindow(
            training_start=training_start,
            training_end=training_end,
            validation_start=validation_start,
            validation_end=validation_end,
            selected_parameters=selected_parameters,
            training_statistics=optimization.best_result.statistics
            if optimization.best_result is not None
            else BacktestStatistics(),
            validation_statistics=validation_result.statistics,
            validation_trades=validation_result.trades,
            warnings=warnings,
        )

    @classmethod
    def window_ranges(cls, candidates, training_days, validation_days, step_days):
        start = min(candidate["_date"] for candidate in candidates)
        end = max(candidate["_date"] for candidate in candidates)
        windows = []
        training_start = start

        while True:
            training_end = training_start + timedelta(days=training_days - 1)
            validation_start = training_end + timedelta(days=1)
            validation_end = validation_start + timedelta(days=validation_days - 1)

            if validation_end > end:
                break

            windows.append(
                (training_start, training_end, validation_start, validation_end)
            )
            training_start = training_start + timedelta(days=step_days)

        return windows

    @staticmethod
    def candidates_in_range(candidates, start, end):
        return [
            candidate
            for candidate in candidates
            if start <= candidate["_date"] <= end
        ]

    @classmethod
    def normalized_candidates(cls, candidates):
        if not candidates:
            return [], []

        normalized = []
        warnings = []

        for index, candidate in enumerate(candidates, start=1):
            data = cls.object_mapping(candidate)
            raw_date = cls.first_value(data, "date", "signal_date", "entry_date")

            if raw_date is None:
                warnings.append(f"Candidate {index} missing date.")
                continue

            try:
                parsed_date = cls.date_value(raw_date)
            except ValueError:
                warnings.append(f"Candidate {index} has invalid date.")
                continue

            row = dict(data)
            row["_date"] = parsed_date
            normalized.append(row)

        return (
            sorted(normalized, key=lambda candidate: candidate["_date"]),
            warnings,
        )

    @classmethod
    def stability_score(cls, windows):
        if not windows:
            return 0.0

        profitable_rate = (
            len(
                [
                    window
                    for window in windows
                    if window.validation_statistics.expectancy > 0
                ]
            )
            / len(windows)
        )
        average_expectancy = (
            sum(window.validation_statistics.expectancy for window in windows)
            / len(windows)
        )
        drawdowns = [
            abs(window.validation_statistics.max_drawdown)
            for window in windows
        ]
        average_drawdown = sum(drawdowns) / len(drawdowns) if drawdowns else 0.0
        parameter_consistency = cls.parameter_consistency(windows)

        return (
            (profitable_rate * 40.0)
            + average_expectancy
            - average_drawdown
            + (parameter_consistency * 20.0)
        )

    @staticmethod
    def parameter_consistency(windows):
        if not windows:
            return 0.0

        parameter_sets = [
            tuple(sorted(window.selected_parameters.items()))
            for window in windows
        ]
        most_common_count = max(
            parameter_sets.count(parameter_set)
            for parameter_set in set(parameter_sets)
        )

        return most_common_count / len(parameter_sets)

    @staticmethod
    def window_score(window):
        stats = window.validation_statistics
        return (
            (stats.win_rate * 100.0)
            + stats.expectancy
            + (stats.profit_factor * 10.0)
            + stats.max_drawdown
        )

    @staticmethod
    def positive_days(value, name):
        try:
            days = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{name} must be a positive integer.") from exc

        if days <= 0:
            raise ValueError(f"{name} must be a positive integer.")

        return days

    @staticmethod
    def object_mapping(value):
        if isinstance(value, dict):
            return value

        if hasattr(value, "__dict__"):
            return vars(value)

        return {}

    @staticmethod
    def first_value(source, *names):
        for name in names:
            if isinstance(source, dict):
                value = source.get(name)
            else:
                value = getattr(source, name, None)

            if value not in (None, ""):
                return value

        return None

    @staticmethod
    def date_value(value) -> date:
        if isinstance(value, datetime):
            return value.date()

        if isinstance(value, date):
            return value

        try:
            return datetime.fromisoformat(str(value)).date()
        except (TypeError, ValueError) as exc:
            raise ValueError("Candidate dates must be date-like values.") from exc
