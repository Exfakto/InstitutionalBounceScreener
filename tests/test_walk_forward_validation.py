from datetime import date, timedelta

from services.algorithm_validation_service import WalkForwardValidationService
from tests.algorithm_validation_test_utils import sample_outcome


def dated_outcomes(count=16):
    start = date.fromisoformat("2024-01-01")
    outcomes = []
    for index in range(count):
        outcomes.append(
            sample_outcome(
                ticker=f"T{index}",
                signal_date=(start + timedelta(days=index * 15)).isoformat(),
                return_20=5 if index % 2 == 0 else -2,
                final_score=80,
            )
        )
    return outcomes


def test_walk_forward_validation_builds_training_testing_windows():
    windows = WalkForwardValidationService().validate(
        dated_outcomes(),
        window_days=60,
        step_days=30,
        max_combinations=2,
    )

    assert windows
    assert windows[0].training_start < windows[0].training_end
    assert windows[0].testing_start == windows[0].training_end
    assert windows[0].selected_weights
    assert windows[0].signal_count > 0


def test_walk_forward_validation_empty_or_insufficient_data_is_safe():
    assert WalkForwardValidationService().validate([]) == []
    assert WalkForwardValidationService().validate(dated_outcomes(2), window_days=180, step_days=90) == []
