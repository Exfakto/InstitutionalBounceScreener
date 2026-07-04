from services.algorithm_validation_service import FactorPerformanceAnalyzer
from tests.algorithm_validation_test_utils import sample_outcome


def test_factor_performance_analysis_buckets_scores_and_returns():
    outcomes = [
        sample_outcome("A", return_20=10, final_score=92, support_score=91),
        sample_outcome("B", return_20=-4, final_score=65, support_score=62),
        sample_outcome("C", return_20=6, final_score=82, support_score=84),
    ]

    results = FactorPerformanceAnalyzer().analyze(outcomes, return_window=20)

    final_buckets = {row.bucket: row for row in results if row.factor == "final_score"}
    assert {"60-69", "80-89", "90-100"}.issubset(final_buckets)
    assert final_buckets["90-100"].win_rate == 1.0
    assert final_buckets["60-69"].average_return == -4


def test_factor_performance_analysis_empty_input_returns_empty():
    assert FactorPerformanceAnalyzer().analyze([]) == []
