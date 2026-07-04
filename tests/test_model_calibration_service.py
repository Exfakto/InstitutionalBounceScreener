from database.manager import DatabaseManager
from services.algorithm_validation_service import (
    FactorBucketResult,
    SignalQualityAnalysisService,
    SignalQualityGroupResult,
)
from services.model_calibration_service import ModelCalibrationService
from tests.test_signal_quality_analysis_service import enriched_outcome


def test_model_calibration_generates_recommendations_from_signal_quality():
    quality_report = SignalQualityAnalysisService().analyze(
        [
            enriched_outcome("A", -7, 61, "LOW", "Speculative / Low Conviction"),
            enriched_outcome("B", -4, 64, "LOW", "Speculative / Low Conviction"),
            enriched_outcome("C", 12, 86, "HIGH", "High-Quality Bounce"),
        ],
        validation_run_id="validation-1",
    )

    result = ModelCalibrationService().calibrate(
        signal_quality_report=quality_report,
        run_id="cal-1",
    )
    recommendations = result["recommendations"]
    categories = {recommendation.category for recommendation in recommendations}

    assert "minimum_final_score" in categories
    assert "confidence_filtering_rules" in categories
    assert any(category.startswith("minimum_") for category in categories)
    assert result["run"].source_validation_run_id == "validation-1"
    assert result["run"].source_signal_quality_run_id == quality_report.report_id


def test_model_calibration_no_data_case_is_safe():
    result = ModelCalibrationService().calibrate(run_id="cal-empty")

    assert result["recommendations"] == []
    assert result["run"].status == "NO_RECOMMENDATIONS"
    assert "No validation or signal-quality data available" in result["warnings"][0]


def test_model_calibration_detects_weak_groups_directly():
    weak_groups = [
        SignalQualityGroupResult(
            dimension="grade",
            group="C",
            signal_count=6,
            win_rate=0.2,
            expectancy=-4.0,
            average_return=-3.0,
            max_drawdown=-15.0,
            weak=True,
            reasons=["Expectancy below target", "Drawdown worse than 12.0%"],
        ),
        SignalQualityGroupResult(
            dimension="technical_score_bucket",
            group="60-69",
            signal_count=4,
            win_rate=0.25,
            expectancy=-2.0,
            average_return=-1.0,
            max_drawdown=-8.0,
            weak=True,
            reasons=["Win rate below target"],
        ),
    ]
    report = {
        "report_id": "quality-1",
        "validation_run_id": "validation-1",
        "weak_groups": weak_groups,
        "recommendations": [],
        "warnings": [],
    }

    result = ModelCalibrationService().calibrate(
        signal_quality_report=report,
        run_id="cal-weak",
    )
    by_category = {item.category: item for item in result["recommendations"]}

    assert "minimum_final_score" in by_category
    assert "minimum_technical_score" in by_category
    assert "confidence_filtering_rules" in by_category
    assert by_category["minimum_technical_score"].recommended_value == 70


def test_model_calibration_uses_validation_factor_buckets():
    validation_result = {
        "run_id": "validation-2",
        "factor_bucket_results": [
            FactorBucketResult(
                factor="support_score",
                bucket="0-59",
                signal_count=8,
                win_rate=0.25,
                average_return=-2.5,
                median_return=-2.0,
                max_drawdown=-9.0,
                expectancy=-2.5,
            ),
            FactorBucketResult(
                factor="final_score",
                bucket="60-69",
                signal_count=8,
                win_rate=0.3,
                average_return=-1.5,
                median_return=-1.0,
                max_drawdown=-7.0,
                expectancy=-1.5,
            ),
        ],
    }

    result = ModelCalibrationService().calibrate(
        validation_result=validation_result,
        run_id="cal-factor",
    )
    categories = {item.category for item in result["recommendations"]}

    assert "minimum_support_score" in categories
    assert "minimum_final_score" in categories
    assert result["run"].source_validation_run_id == "validation-2"


def test_model_calibration_persistence_integration(tmp_path):
    db = DatabaseManager(tmp_path / "calibration.db")
    quality_report = SignalQualityAnalysisService().analyze(
        [enriched_outcome("A", -6, 62, "LOW")],
        validation_run_id="validation-run",
    )

    result = ModelCalibrationService(db).calibrate(
        signal_quality_report=quality_report,
        run_id="cal-persist",
    )
    latest = db.fetch_latest_calibration_run()
    recommendations = db.fetch_calibration_recommendations("cal-persist")

    assert result["run"]["run_id"] == "cal-persist"
    assert latest["run_id"] == "cal-persist"
    assert recommendations
    assert recommendations[0]["run_id"] == "cal-persist"


def test_model_calibration_recommendations_include_confidence_and_rationale():
    weak_group = SignalQualityGroupResult(
        dimension="institutional_score_bucket",
        group="0-59",
        signal_count=12,
        win_rate=0.1,
        expectancy=-5.0,
        average_return=-4.0,
        max_drawdown=-13.0,
        weak=True,
        reasons=["Drawdown worse than target"],
    )

    result = ModelCalibrationService().calibrate(
        signal_quality_report={"weak_groups": [weak_group]},
        run_id="cal-fields",
    )
    recommendation = next(
        item for item in result["recommendations"]
        if item.category == "minimum_institutional_score"
    )

    assert recommendation.confidence == "HIGH"
    assert "Evidence:" in recommendation.rationale
    assert recommendation.expected_impact
