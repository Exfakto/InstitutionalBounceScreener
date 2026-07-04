from services.algorithm_validation_service import SignalQualityAnalysisService
from tests.algorithm_validation_test_utils import sample_outcome


def enriched_outcome(
    ticker,
    return_20,
    final_score,
    confidence_level="LOW",
    setup_label="Speculative / Low Conviction",
):
    outcome = sample_outcome(
        ticker=ticker,
        return_20=return_20,
        final_score=final_score,
        support_score=final_score,
        bounce_score=final_score,
        technical_score=final_score,
        institutional_score=final_score,
    )
    payload = outcome.__dict__.copy()
    payload["confidence_level"] = confidence_level
    payload["setup_label"] = setup_label
    return payload


def test_signal_quality_analysis_groups_validation_outcomes():
    outcomes = [
        enriched_outcome("A", 8, 82, "HIGH", "High-Quality Bounce"),
        enriched_outcome("B", -7, 62, "LOW", "Speculative / Low Conviction"),
        enriched_outcome("C", -4, 65, "LOW", "Speculative / Low Conviction"),
    ]

    report = SignalQualityAnalysisService().analyze(outcomes, validation_run_id="run-1")

    assert report.validation_run_id == "run-1"
    assert any(group.dimension == "grade" for group in report.weak_groups)
    assert any(group.dimension == "confidence_level" and group.group == "LOW" for group in report.weak_groups)
    assert report.recommendations


def test_signal_quality_analysis_empty_input_is_safe():
    report = SignalQualityAnalysisService().analyze([])

    assert report.weak_groups == []
    assert report.recommendations == []
    assert report.warnings == ["No validation outcomes available for signal quality analysis."]
