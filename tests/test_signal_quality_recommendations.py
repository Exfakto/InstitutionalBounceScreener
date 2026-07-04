from services.algorithm_validation_service import (
    SignalQualityAnalysisService,
    SignalQualityGroupResult,
)
from tests.test_signal_quality_analysis_service import enriched_outcome


def test_recommendation_generation_for_weak_final_and_component_scores():
    outcomes = [
        enriched_outcome("A", -8, 61, "LOW", "Speculative / Low Conviction"),
        enriched_outcome("B", -5, 64, "LOW", "Speculative / Low Conviction"),
        enriched_outcome("C", 10, 85, "HIGH", "High-Quality Bounce"),
    ]

    report = SignalQualityAnalysisService().analyze(outcomes)
    fields = {recommendation.field for recommendation in report.recommendations}

    assert "minimum_final_score" in fields
    assert "confidence_requirement" in fields
    assert "setup_label_filter" in fields
    assert any(field.startswith("minimum_") and field.endswith("_score") for field in fields)


def test_manual_review_recommendation_for_unmapped_weak_group():
    weak_group = SignalQualityGroupResult(
        dimension="grade",
        group="B",
        signal_count=2,
        win_rate=0.0,
        expectancy=-5.0,
        average_return=-5.0,
        max_drawdown=-6.0,
        weak=True,
        reasons=["Expectancy below target"],
    )

    recommendations = SignalQualityAnalysisService().recommendations_from_weak_groups(
        [weak_group]
    )

    assert recommendations[0].recommendation_type == "review"
    assert recommendations[0].field == "manual_review"
