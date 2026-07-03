from types import SimpleNamespace

from services.institutional_intelligence_service import (
    DEFAULT_COMPONENT_SCORE,
    InstitutionalIntelligenceService,
)


def test_strong_institutional_accumulation_scores_high():
    service = InstitutionalIntelligenceService()

    result = service.calculate(
        institutional_ownership_pct=75,
        institutional_ownership_change_qoq=4,
        net_institutional_buying=450_000_000,
        insider_buying_flag=True,
        insider_selling_flag=False,
    )

    assert result.ownership_score == 100.0
    assert result.ownership_trend_score > 80
    assert result.institutional_buying_score > 90
    assert result.insider_activity_score == 85.0
    assert result.overall_institutional_strength_score >= 85
    assert "strong" in result.ownership_explanation.lower()
    assert "increased" in result.ownership_trend_explanation.lower()
    assert "positive" in result.institutional_buying_explanation.lower()
    assert "strong" in result.overall_explanation.lower()


def test_neutral_case_scores_near_middle():
    service = InstitutionalIntelligenceService()

    result = service.calculate(
        institutional_ownership_pct=35,
        institutional_ownership_change_qoq=0,
        net_institutional_buying=0,
        insider_buying_flag=False,
        insider_selling_flag=False,
    )

    assert result.ownership_score == 50.0
    assert result.ownership_trend_score == 50.0
    assert result.institutional_buying_score == 50.0
    assert result.insider_activity_score == 55.0
    assert 45 <= result.overall_institutional_strength_score <= 60
    assert "moderate" in result.ownership_explanation.lower()
    assert "flat" in result.ownership_trend_explanation.lower()


def test_weak_distribution_scores_low():
    service = InstitutionalIntelligenceService()

    result = service.calculate(
        institutional_ownership_pct=10,
        institutional_ownership_change_qoq=-5,
        net_institutional_buying=-600_000_000,
        insider_buying_flag=False,
        insider_selling_flag=True,
    )

    assert result.ownership_score < 20
    assert result.ownership_trend_score == 0.0
    assert result.institutional_buying_score == 0.0
    assert result.insider_activity_score == 20.0
    assert result.overall_institutional_strength_score < 25
    assert "weak" in result.overall_explanation.lower()


def test_insider_buying_component_score():
    service = InstitutionalIntelligenceService()
    warnings = []

    score, explanation = service.score_insider_activity("yes", "no", warnings)

    assert score == 85.0
    assert "buying" in explanation.lower()
    assert warnings == []


def test_insider_selling_component_score():
    service = InstitutionalIntelligenceService()
    warnings = []

    score, explanation = service.score_insider_activity(False, True, warnings)

    assert score == 20.0
    assert "selling" in explanation.lower()
    assert warnings == []


def test_missing_data_uses_neutral_defaults():
    service = InstitutionalIntelligenceService()

    result = service.calculate()

    assert result.ownership_score == DEFAULT_COMPONENT_SCORE
    assert result.ownership_trend_score == DEFAULT_COMPONENT_SCORE
    assert result.institutional_buying_score == DEFAULT_COMPONENT_SCORE
    assert result.insider_activity_score == DEFAULT_COMPONENT_SCORE
    assert result.overall_institutional_strength_score == DEFAULT_COMPONENT_SCORE
    assert "unavailable" in result.ownership_explanation.lower()
    assert len(result.warnings) == 4


def test_score_bounds_are_clamped_to_zero_to_one_hundred():
    service = InstitutionalIntelligenceService()

    high = service.calculate(
        institutional_ownership_pct=500,
        institutional_ownership_change_qoq=100,
        net_institutional_buying=10_000_000_000,
        insider_buying_flag=True,
        insider_selling_flag=False,
    )
    low = service.calculate(
        institutional_ownership_pct=-50,
        institutional_ownership_change_qoq=-100,
        net_institutional_buying=-10_000_000_000,
        insider_buying_flag=False,
        insider_selling_flag=True,
    )

    for result in (high, low):
        scores = [
            result.ownership_score,
            result.ownership_trend_score,
            result.institutional_buying_score,
            result.insider_activity_score,
            result.overall_institutional_strength_score,
        ]
        assert all(0 <= score <= 100 for score in scores)


def test_calculate_from_record_supports_dict_and_object_records():
    service = InstitutionalIntelligenceService()

    dict_result = service.calculate_from_record(
        {
            "institutional_ownership_pct": "70",
            "institutional_ownership_change_qoq": "2",
            "net_institutional_buying": "250000000",
            "insider_buying_flag": "true",
            "insider_selling_flag": "false",
        }
    )
    object_result = service.calculate_from_record(
        SimpleNamespace(
            institutional_ownership_pct=70,
            institutional_ownership_change_qoq=2,
            net_institutional_buying=250_000_000,
            insider_buying_flag=True,
            insider_selling_flag=False,
        )
    )

    assert dict_result == object_result
