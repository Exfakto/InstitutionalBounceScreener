import pytest

from backtesting.backtest_models import BacktestTrade
from backtesting.strategy import BacktestStrategy
from backtesting.walk_forward import WalkForwardResult, WalkForwardValidator


class WindowThresholdStrategy(BacktestStrategy):
    def __init__(self, threshold=1):
        self.threshold = threshold

    def generate_trades(self, historical_candidates):
        trades = []

        for candidate in historical_candidates:
            if candidate["score"] < self.threshold:
                continue

            trades.append(
                BacktestTrade(
                    ticker=candidate["ticker"],
                    entry_date=candidate["date"],
                    exit_date=candidate["exit_date"],
                    entry_price=100.0,
                    exit_price=candidate["exit_price"],
                )
            )

        return trades


def candidate(day, score, exit_price, ticker=None):
    return {
        "ticker": ticker or f"T{day}",
        "date": f"2026-01-{day:02d}",
        "exit_date": f"2026-01-{day:02d}",
        "score": score,
        "exit_price": exit_price,
    }


def candidates():
    return [
        candidate(1, 1, 95.0, "TRAIN_LOSS_1"),
        candidate(2, 3, 110.0, "TRAIN_WIN_1"),
        candidate(3, 3, 112.0, "TRAIN_WIN_2"),
        candidate(4, 1, 94.0, "TRAIN_LOSS_2"),
        candidate(5, 3, 111.0, "VAL_WIN_1"),
        candidate(6, 1, 96.0, "VAL_LOSS_1"),
        candidate(7, 3, 113.0, "VAL_WIN_2"),
        candidate(8, 1, 97.0, "VAL_LOSS_2"),
    ]


def test_walk_forward_empty_input_returns_safe_result():
    result = WalkForwardValidator().validate(
        [],
        WindowThresholdStrategy(),
        {"threshold": [1, 3]},
        training_window_days=4,
        validation_window_days=2,
    )

    assert isinstance(result, WalkForwardResult)
    assert result.windows == []
    assert result.window_count == 0
    assert result.best_window is None
    assert result.worst_window is None
    assert result.aggregate_validation_statistics.total_trades == 0
    assert result.stability_score == 0.0
    assert result.warnings == ["No historical candidates supplied."]


def test_walk_forward_invalid_dates_are_warned_and_skipped():
    result = WalkForwardValidator().validate(
        [
            {"ticker": "BAD", "date": "not-a-date"},
            candidate(1, 3, 110.0),
        ],
        WindowThresholdStrategy(),
        {"threshold": [1, 3]},
        training_window_days=1,
        validation_window_days=1,
    )

    assert "Candidate 1 has invalid date." in result.warnings
    assert "Insufficient historical data for walk-forward validation." in result.warnings
    assert result.window_count == 0


def test_walk_forward_insufficient_data_returns_warning():
    result = WalkForwardValidator().validate(
        [candidate(1, 3, 110.0)],
        WindowThresholdStrategy(),
        {"threshold": [1, 3]},
        training_window_days=3,
        validation_window_days=2,
    )

    assert result.window_count == 0
    assert result.warnings == ["Insufficient historical data for walk-forward validation."]


def test_walk_forward_empty_parameter_grid_returns_warning():
    result = WalkForwardValidator().validate(
        candidates(),
        WindowThresholdStrategy(),
        {},
        training_window_days=4,
        validation_window_days=2,
    )

    assert result.window_count == 0
    assert result.warnings == ["No optimization parameters supplied."]


def test_walk_forward_single_window_selected_parameter_propagation():
    result = WalkForwardValidator().validate(
        candidates(),
        WindowThresholdStrategy(),
        {"threshold": [1, 3]},
        training_window_days=4,
        validation_window_days=4,
    )

    assert result.window_count == 1
    window = result.windows[0]
    assert window.training_start.isoformat() == "2026-01-01"
    assert window.training_end.isoformat() == "2026-01-04"
    assert window.validation_start.isoformat() == "2026-01-05"
    assert window.validation_end.isoformat() == "2026-01-08"
    assert window.selected_parameters == {"threshold": 3}
    assert window.training_statistics.total_trades == 2
    assert window.validation_statistics.total_trades == 2
    assert [trade.ticker for trade in window.validation_trades] == [
        "VAL_WIN_1",
        "VAL_WIN_2",
    ]
    assert result.best_window == window
    assert result.worst_window == window


def test_walk_forward_multiple_windows_and_step_days_behavior():
    result = WalkForwardValidator().validate(
        candidates(),
        WindowThresholdStrategy(),
        {"threshold": [1, 3]},
        training_window_days=3,
        validation_window_days=2,
        step_days=2,
    )

    assert result.window_count == 2
    assert [window.validation_start.isoformat() for window in result.windows] == [
        "2026-01-04",
        "2026-01-06",
    ]
    assert all(window.selected_parameters == {"threshold": 3} for window in result.windows)


def test_walk_forward_defaults_step_days_to_validation_window_days():
    explicit = WalkForwardValidator().validate(
        candidates(),
        WindowThresholdStrategy(),
        {"threshold": [1, 3]},
        training_window_days=3,
        validation_window_days=2,
        step_days=2,
    )
    defaulted = WalkForwardValidator().validate(
        candidates(),
        WindowThresholdStrategy(),
        {"threshold": [1, 3]},
        training_window_days=3,
        validation_window_days=2,
    )

    assert explicit == defaulted


def test_walk_forward_aggregate_validation_statistics_and_stability_score():
    result = WalkForwardValidator().validate(
        candidates(),
        WindowThresholdStrategy(),
        {"threshold": [1, 3]},
        training_window_days=3,
        validation_window_days=2,
        step_days=2,
    )

    assert result.aggregate_validation_statistics.total_trades == 2
    assert result.aggregate_validation_statistics.wins == 2
    assert result.aggregate_validation_statistics.win_rate == 1.0
    assert result.stability_score > 0.0


def test_walk_forward_warning_propagation_from_optimizer_and_validation():
    result = WalkForwardValidator().validate(
        candidates(),
        WindowThresholdStrategy(),
        {"threshold": [1, 1, 3]},
        training_window_days=3,
        validation_window_days=2,
        step_days=2,
    )

    assert any(
        "Skipped 1 duplicate parameter combinations." in warning
        for warning in result.warnings
    )
    assert any(window.warnings for window in result.windows)


def test_walk_forward_output_is_deterministic():
    validator = WalkForwardValidator()
    args = (
        candidates(),
        WindowThresholdStrategy(),
        {"threshold": [1, 3]},
    )

    first = validator.validate(
        *args,
        training_window_days=3,
        validation_window_days=2,
        step_days=2,
    )
    second = validator.validate(
        *args,
        training_window_days=3,
        validation_window_days=2,
        step_days=2,
    )

    assert first == second


def test_walk_forward_rejects_invalid_window_sizes_and_strategy():
    with pytest.raises(ValueError, match="training_window_days"):
        WalkForwardValidator().validate(
            candidates(),
            WindowThresholdStrategy(),
            {"threshold": [1]},
            training_window_days=0,
            validation_window_days=2,
        )

    with pytest.raises(TypeError, match="BacktestStrategy"):
        WalkForwardValidator().validate(
            candidates(),
            object(),
            {"threshold": [1]},
            training_window_days=2,
            validation_window_days=2,
        )
