from analysis.institutional_checklist import InstitutionalChecklistEvaluator
from analysis.score_result import ScoreResult


def perfect_metrics():
    return {
        "institutional_bounce_score": 95,
        "opportunity_rating_score": 92,
        "quality_score": 90,
        "institutional_score": 85,
        "institutional_momentum_score": 88,
        "technical_score": 84,
        "relative_strength_score": 86,
        "support_score": 91,
        "bounce_score": 89,
        "entry_quality_score": 87,
        "volume_score": 82,
        "trend_score": 83,
        "earnings_risk_score": 20,
        "risk_score": 78,
        "distance_to_support_pct": 2.5,
        "bounce_success_rate": 82,
        "average_bounce_pct": 8,
    }


def evaluate(metrics):
    return InstitutionalChecklistEvaluator().evaluate(metrics)


def statuses(result):
    return {
        check.name: check.status
        for check in result.checks
    }


def test_perfect_candidate_passes_all_checks():
    result = evaluate(perfect_metrics())

    assert result.total_checks == 10
    assert result.passed_count == 10
    assert result.warning_count == 0
    assert result.failed_count == 0
    assert result.overall_percentage == 100.0
    assert result.overall_label == "Exceptional"
    assert all(check.status == "pass" for check in result.checks)


def test_weak_candidate_fails_key_checks():
    metrics = perfect_metrics()
    metrics.update(
        {
            "opportunity_rating_score": 45,
            "institutional_score": 30,
            "institutional_momentum_score": 25,
            "relative_strength_score": 35,
            "trend_score": 30,
            "volume_score": 20,
            "earnings_risk_score": 85,
            "risk_score": 25,
            "distance_to_support_pct": 12,
            "bounce_success_rate": 30,
        }
    )

    result = evaluate(metrics)

    assert result.passed_count == 0
    assert result.warning_count == 0
    assert result.failed_count == 10
    assert result.overall_percentage == 0.0
    assert result.overall_label == "Avoid"


def test_mixed_candidate_has_pass_warning_and_fail_checks():
    metrics = perfect_metrics()
    metrics.update(
        {
            "distance_to_support_pct": 5,
            "bounce_success_rate": 45,
            "relative_strength_score": 76,
            "trend_score": 55,
            "institutional_score": 45,
            "institutional_momentum_score": 72,
            "volume_score": 60,
            "earnings_risk_score": 50,
            "risk_score": 80,
            "opportunity_rating_score": 65,
        }
    )

    result = evaluate(metrics)
    by_name = statuses(result)

    assert by_name["Near validated support"] == "warning"
    assert by_name["Bounce success rate acceptable"] == "fail"
    assert by_name["Relative Strength strong"] == "pass"
    assert by_name["Trend aligned"] == "warning"
    assert by_name["Institutional ownership acceptable"] == "fail"
    assert by_name["Institutional momentum positive"] == "pass"
    assert by_name["Volume accumulation present"] == "warning"
    assert by_name["Earnings window safe"] == "warning"
    assert by_name["ATR risk acceptable"] == "pass"
    assert by_name["Opportunity rating acceptable"] == "warning"
    assert result.passed_count == 3
    assert result.warning_count == 5
    assert result.failed_count == 2
    assert result.overall_percentage == 30.0


def test_missing_metrics_generate_warnings_not_failures():
    result = evaluate({})

    assert result.total_checks == 10
    assert result.passed_count == 0
    assert result.warning_count == 10
    assert result.failed_count == 0
    assert result.overall_percentage == 0.0
    assert all(check.value is None for check in result.warning_checks)
    assert all(check.status == "warning" for check in result.checks)


def test_invalid_metrics_generate_warnings():
    result = evaluate(
        {
            "distance_to_support_pct": "near",
            "bounce_success_rate": "strong",
            "relative_strength_score": "high",
            "trend_score": object(),
            "institutional_score": None,
            "institutional_momentum_score": [],
            "volume_score": {},
            "earnings_risk_score": "tomorrow",
            "risk_score": "low",
            "opportunity_rating_score": "elite",
        }
    )

    assert result.warning_count == 10
    assert result.failed_count == 0
    assert all("unavailable" in check.message for check in result.warning_checks)


def test_percentage_calculation_counts_passes_only():
    metrics = perfect_metrics()
    metrics.update(
        {
            "distance_to_support_pct": 4,
            "bounce_success_rate": 55,
            "relative_strength_score": 80,
            "trend_score": 75,
            "institutional_score": 80,
            "institutional_momentum_score": 80,
            "volume_score": 80,
            "earnings_risk_score": 80,
            "risk_score": 40,
            "opportunity_rating_score": 80,
        }
    )

    result = evaluate(metrics)

    assert result.passed_count == 6
    assert result.warning_count == 2
    assert result.failed_count == 2
    assert result.overall_percentage == 60.0
    assert result.overall_label == "Weak"


def test_label_assignment_boundaries():
    evaluator = InstitutionalChecklistEvaluator()

    assert evaluator.overall_label(100) == "Exceptional"
    assert evaluator.overall_label(90) == "Excellent"
    assert evaluator.overall_label(80) == "Strong"
    assert evaluator.overall_label(70) == "Acceptable"
    assert evaluator.overall_label(60) == "Weak"
    assert evaluator.overall_label(59.9) == "Avoid"


def test_output_is_deterministic():
    metrics = perfect_metrics()
    first = evaluate(metrics)
    second = evaluate(dict(reversed(list(metrics.items()))))

    assert first == second
    assert [check.name for check in first.checks] == [
        "Near validated support",
        "Bounce success rate acceptable",
        "Relative Strength strong",
        "Trend aligned",
        "Institutional ownership acceptable",
        "Institutional momentum positive",
        "Volume accumulation present",
        "Earnings window safe",
        "ATR risk acceptable",
        "Opportunity rating acceptable",
    ]


def test_score_result_inputs_are_supported():
    metrics = perfect_metrics()
    metrics["relative_strength_score"] = ScoreResult(
        "relative_strength_score",
        90,
    )

    result = evaluate(metrics)

    assert statuses(result)["Relative Strength strong"] == "pass"
    assert result.passed_count == 10
