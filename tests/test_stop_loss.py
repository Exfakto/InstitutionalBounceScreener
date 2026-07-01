from analysis.score_result import ScoreResult
from analysis.stop_loss import StopLossCalculator


def base_metrics():
    return {
        "current_price": 105.0,
        "nearest_support_low": 98.0,
        "nearest_support_high": 100.0,
        "nearest_support_mid": 99.0,
        "atr": 2.0,
        "atr_pct": 1.9,
        "support_strength_score": 65.0,
        "bounce_success_rate": 62.0,
        "risk_score": 70.0,
        "entry_zone": "Acceptable Entry",
    }


def calculate(metrics):
    return StopLossCalculator().calculate(metrics)


def test_normal_stop_calculation():
    result = calculate(base_metrics())

    assert result.technical_stop == 97.02
    assert result.atr_stop == 95.0
    assert result.protective_stop == 97.412
    assert result.recommended_stop == result.technical_stop
    assert result.stop_type == "Technical"
    assert result.warnings == []


def test_strong_support_uses_protective_stop():
    metrics = base_metrics()
    metrics["support_strength_score"] = 90.0
    metrics["bounce_success_rate"] = 82.0

    result = calculate(metrics)

    assert result.stop_type == "Protective"
    assert result.recommended_stop == result.protective_stop
    assert result.recommended_stop > result.technical_stop


def test_weak_support_uses_technical_stop():
    metrics = base_metrics()
    metrics["support_strength_score"] = 35.0
    metrics["bounce_success_rate"] = 35.0

    result = calculate(metrics)

    assert result.stop_type == "Technical"
    assert result.recommended_stop == result.technical_stop


def test_high_atr_uses_atr_stop():
    metrics = base_metrics()
    metrics["atr"] = 7.0
    metrics["atr_pct"] = 7.5

    result = calculate(metrics)

    assert result.stop_type == "ATR"
    assert result.recommended_stop == 87.5
    assert result.recommended_stop < result.technical_stop


def test_low_atr_uses_technical_stop():
    metrics = base_metrics()
    metrics["atr"] = 0.4
    metrics["atr_pct"] = 0.4

    result = calculate(metrics)

    assert result.stop_type == "Technical"
    assert result.recommended_stop == result.technical_stop


def test_missing_support():
    metrics = base_metrics()
    metrics.pop("nearest_support_low")

    result = calculate(metrics)

    assert result.stop_type == "Unavailable"
    assert result.recommended_stop is None
    assert "Missing support zone" in result.warnings


def test_missing_atr_warns_and_uses_technical_stop():
    metrics = base_metrics()
    metrics.pop("atr")
    metrics.pop("atr_pct")

    result = calculate(metrics)

    assert result.atr_stop is None
    assert result.stop_type == "Technical"
    assert result.recommended_stop == result.technical_stop
    assert "Missing ATR" in result.warnings


def test_deterministic_output():
    metrics = base_metrics()
    metrics["support_strength_score"] = ScoreResult("support_strength_score", 88.0)

    first = calculate(metrics)
    second = calculate(dict(reversed(list(metrics.items()))))

    assert first == second


def test_risk_percent_calculation():
    result = calculate(base_metrics())

    assert result.risk_percent == (
        (base_metrics()["current_price"] - result.recommended_stop)
        / base_metrics()["current_price"]
    ) * 100.0


def test_recommended_stop_selection_for_weak_risk():
    metrics = base_metrics()
    metrics["risk_score"] = 30.0

    result = calculate(metrics)

    assert result.stop_type == "ATR"
    assert result.recommended_stop == result.atr_stop
