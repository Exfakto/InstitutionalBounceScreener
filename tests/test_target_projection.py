from analysis.score_result import ScoreResult
from analysis.target_projection import TargetProjectionCalculator


def historical_metrics():
    return {
        "ticker": "AAPL",
        "current_price": 100.0,
        "nearest_support_low": 96.0,
        "nearest_support_high": 98.0,
        "nearest_support_mid": 97.0,
        "atr": 2.0,
        "atr_pct": 2.0,
        "average_bounce_pct": 10.0,
        "median_bounce_pct": 6.0,
        "bounce_success_rate": 82.0,
        "support_strength_score": 85.0,
        "institutional_bounce_score": 88.0,
        "opportunity_rating_score": 84.0,
    }


def calculate(metrics):
    return TargetProjectionCalculator().calculate(metrics)


def test_historical_bounce_based_targets():
    result = calculate(historical_metrics())

    assert result.target_1 == 106.0
    assert result.target_2 == 110.0
    assert result.target_3 == 112.5
    assert result.target_method == "Historical Bounce"
    assert result.conservative_reward_pct == 6.0
    assert result.expected_reward_pct == 10.0
    assert result.aggressive_reward_pct == 12.5
    assert "Targets use historical bounce behavior" in result.reasons


def test_atr_fallback_targets():
    metrics = historical_metrics()
    metrics.pop("average_bounce_pct")
    metrics.pop("median_bounce_pct")

    result = calculate(metrics)

    assert result.target_1 == 103.0
    assert result.target_2 == 105.0
    assert result.target_3 == 108.0
    assert result.target_method == "ATR Fallback"
    assert "Missing bounce target data" in result.warnings


def test_resistance_cap_behavior():
    metrics = historical_metrics()
    metrics["resistance_level"] = 108.0

    result = calculate(metrics)

    assert result.target_1 == 106.0
    assert result.target_2 == 108.0
    assert result.target_3 == 108.0
    assert "Resistance capped projected target" in result.warnings


def test_missing_current_price():
    metrics = historical_metrics()
    metrics["current_price"] = None

    result = calculate(metrics)

    assert result.target_1 is None
    assert result.target_method == "Unavailable"
    assert result.confidence == "Very Low"
    assert "Missing current price" in result.warnings


def test_missing_bounce_data_uses_atr_with_warning():
    metrics = historical_metrics()
    metrics["average_bounce_pct"] = None
    metrics["median_bounce_pct"] = None

    result = calculate(metrics)

    assert result.target_method == "ATR Fallback"
    assert result.target_1 == 103.0
    assert "Missing bounce target data" in result.warnings


def test_missing_atr_data_uses_bounce_with_warning():
    metrics = historical_metrics()
    metrics["atr"] = None
    metrics["atr_pct"] = None

    result = calculate(metrics)

    assert result.target_method == "Historical Bounce"
    assert result.target_2 == 110.0
    assert "Missing ATR target data" in result.warnings


def test_missing_bounce_and_atr_data_is_unavailable():
    metrics = historical_metrics()
    metrics["average_bounce_pct"] = None
    metrics["median_bounce_pct"] = None
    metrics["atr"] = None
    metrics["atr_pct"] = None

    result = calculate(metrics)

    assert result.target_1 is None
    assert result.target_method == "Unavailable"
    assert result.confidence == "Very Low"
    assert "Missing bounce target data" in result.warnings
    assert "Missing ATR target data" in result.warnings


def test_strong_confidence():
    result = calculate(historical_metrics())

    assert result.confidence == "Very High"


def test_weak_confidence():
    metrics = historical_metrics()
    metrics["bounce_success_rate"] = 35.0
    metrics["support_strength_score"] = 40.0
    metrics["institutional_bounce_score"] = 42.0

    result = calculate(metrics)

    assert result.confidence == "Low"


def test_deterministic_output():
    metrics = historical_metrics()
    metrics["support_strength_score"] = ScoreResult("support_strength_score", 85.0)

    first = calculate(metrics)
    second = calculate(dict(reversed(list(metrics.items()))))

    assert first == second


def test_reward_percentage_calculation():
    result = calculate(historical_metrics())

    assert result.conservative_reward_pct == (
        (result.target_1 - historical_metrics()["current_price"])
        / historical_metrics()["current_price"]
    ) * 100.0
    assert result.expected_reward_pct == (
        (result.target_2 - historical_metrics()["current_price"])
        / historical_metrics()["current_price"]
    ) * 100.0
    assert result.aggressive_reward_pct == (
        (result.target_3 - historical_metrics()["current_price"])
        / historical_metrics()["current_price"]
    ) * 100.0
