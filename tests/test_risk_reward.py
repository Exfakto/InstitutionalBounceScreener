from analysis.risk_reward import RiskRewardCalculator
from analysis.score_result import ScoreResult


def excellent_metrics():
    return {
        "current_price": 100.0,
        "recommended_entry": 100.0,
        "recommended_stop": 95.0,
        "target_1": 110.0,
        "target_2": 115.0,
        "target_3": 120.0,
        "opportunity_rating_score": 90.0,
        "entry_score": 85.0,
        "bounce_success_rate": 82.0,
    }


def calculate(metrics):
    return RiskRewardCalculator().calculate(metrics)


def test_excellent_reward_risk():
    result = calculate(excellent_metrics())

    assert result.risk_amount == 5.0
    assert result.reward_1 == 10.0
    assert result.reward_2 == 15.0
    assert result.reward_3 == 20.0
    assert result.rr_1 == 2.0
    assert result.rr_2 == 3.0
    assert result.rr_3 == 4.0
    assert result.best_target == 120.0
    assert result.best_rr == 4.0
    assert result.recommended_trade == "Strong Buy"
    assert result.warnings == []


def test_average_reward_risk():
    metrics = excellent_metrics()
    metrics.update(
        {
            "target_1": 106.0,
            "target_2": 109.0,
            "target_3": 111.0,
            "opportunity_rating_score": 78.0,
            "entry_score": 68.0,
            "bounce_success_rate": 64.0,
        }
    )

    result = calculate(metrics)

    assert result.best_rr == 2.2
    assert result.recommended_trade == "Buy"


def test_poor_reward_risk():
    metrics = excellent_metrics()
    metrics.update(
        {
            "target_1": 101.0,
            "target_2": 102.0,
            "target_3": 103.0,
            "opportunity_rating_score": 55.0,
            "entry_score": 45.0,
            "bounce_success_rate": 40.0,
        }
    )

    result = calculate(metrics)

    assert result.best_rr == 0.6
    assert result.recommended_trade == "Avoid"
    assert "Poor reward/risk" in result.warnings
    assert "Target too close" in result.warnings


def test_missing_stop():
    metrics = excellent_metrics()
    metrics["recommended_stop"] = None

    result = calculate(metrics)

    assert result.risk_amount is None
    assert result.recommended_trade == "Avoid"
    assert "Missing stop" in result.warnings
    assert "Missing data" in result.warnings


def test_missing_targets():
    metrics = excellent_metrics()
    metrics["target_1"] = None
    metrics["target_2"] = None
    metrics["target_3"] = None

    result = calculate(metrics)

    assert result.best_target is None
    assert result.best_rr is None
    assert result.recommended_trade == "Avoid"
    assert "Missing target 1" in result.warnings
    assert "Missing target 2" in result.warnings
    assert "Missing target 3" in result.warnings


def test_missing_entry():
    metrics = excellent_metrics()
    metrics["recommended_entry"] = None
    metrics["current_price"] = None

    result = calculate(metrics)

    assert result.risk_amount is None
    assert result.recommended_trade == "Avoid"
    assert "Missing entry" in result.warnings
    assert "Missing data" in result.warnings


def test_deterministic_output():
    metrics = excellent_metrics()
    metrics["entry_score"] = ScoreResult("entry_score", 85.0)

    first = calculate(metrics)
    second = calculate(dict(reversed(list(metrics.items()))))

    assert first == second


def test_best_target_selection_ignores_missing_targets():
    metrics = excellent_metrics()
    metrics["target_1"] = None
    metrics["target_2"] = 108.0
    metrics["target_3"] = 112.0

    result = calculate(metrics)

    assert result.best_target == 112.0
    assert result.best_rr == 2.4
    assert "Missing target 1" in result.warnings


def test_recommendation_assignment_watch():
    metrics = excellent_metrics()
    metrics.update(
        {
            "target_1": 104.0,
            "target_2": 106.0,
            "target_3": 107.0,
            "opportunity_rating_score": 65.0,
            "entry_score": 55.0,
            "bounce_success_rate": 52.0,
        }
    )

    result = calculate(metrics)

    assert result.best_rr == 1.4
    assert result.recommended_trade == "Watch"


def test_warning_generation_for_stop_too_wide_and_invalid_target():
    metrics = excellent_metrics()
    metrics["recommended_stop"] = 80.0
    metrics["target_1"] = 99.0

    result = calculate(metrics)

    assert "Stop too wide" in result.warnings
    assert "Target too close" in result.warnings
