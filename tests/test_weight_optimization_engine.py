from services.algorithm_validation_service import WeightOptimizationEngine, normalize_weights
from tests.algorithm_validation_test_utils import sample_outcome


def test_weight_optimization_ranks_deterministically_without_changing_defaults():
    outcomes = [
        sample_outcome("A", return_20=12, support_score=95, bounce_score=80),
        sample_outcome("B", return_20=-5, support_score=40, bounce_score=90),
        sample_outcome("C", return_20=8, support_score=88, bounce_score=70),
    ]
    combinations = [
        {"support": 0.8, "bounce": 0.1, "technical": 0.05, "institutional": 0.05},
        {"support": 0.1, "bounce": 0.8, "technical": 0.05, "institutional": 0.05},
    ]

    first = WeightOptimizationEngine().optimize(outcomes, combinations)
    second = WeightOptimizationEngine().optimize(outcomes, combinations)

    assert [item.weights for item in first] == [item.weights for item in second]
    assert [item.rank for item in first] == [1, 2]
    assert first[0].score >= first[1].score


def test_weight_optimization_normalizes_invalid_weights_and_warns_on_empty():
    assert normalize_weights({"support": -1}) == {
        "support": 0.25,
        "bounce": 0.25,
        "technical": 0.25,
        "institutional": 0.25,
    }

    result = WeightOptimizationEngine().optimize([], [{"support": 1}], max_combinations=1)

    assert len(result) == 1
    assert result[0].warnings
