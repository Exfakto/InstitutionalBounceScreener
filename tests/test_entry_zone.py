from analysis.entry_zone import EntryZoneCalculator
from analysis.score_result import ScoreResult


def base_metrics(price=101.0):
    return {
        "ticker": "AAPL",
        "current_price": price,
        "nearest_support_low": 98.0,
        "nearest_support_high": 100.0,
        "nearest_support_mid": 99.0,
        "atr_pct": 2.0,
        "risk_score": 75.0,
        "support_strength_score": 75.0,
        "bounce_success_rate": 70.0,
        "average_bounce_pct": 6.0,
        "entry_quality_score": 72.0,
        "institutional_bounce_score": 74.0,
        "opportunity_rating_score": 74.0,
    }


def calculate(metrics):
    return EntryZoneCalculator().calculate(metrics)


def test_price_inside_support_zone():
    result = calculate(base_metrics(price=99.0))

    assert result.entry_label == "Ideal Entry"
    assert result.distance_to_support_pct == 0.0
    assert result.ideal_entry_low == 98.0
    assert result.ideal_entry_high == 102.0
    assert result.acceptable_entry_low == 102.0
    assert result.acceptable_entry_high == 105.0
    assert "Price is inside the validated support zone" in result.reasons


def test_price_one_percent_above_support():
    result = calculate(base_metrics(price=101.0))

    assert result.entry_label == "Ideal Entry"
    assert result.distance_to_support_pct == 1.0
    assert "Price is within 2% above support" in result.reasons


def test_price_three_percent_above_support():
    result = calculate(base_metrics(price=103.0))

    assert result.entry_label == "Acceptable Entry"
    assert result.distance_to_support_pct == 3.0
    assert result.entry_score < calculate(base_metrics(price=101.0)).entry_score


def test_price_six_percent_above_support():
    result = calculate(base_metrics(price=106.0))

    assert result.entry_label == "Extended"
    assert result.distance_to_support_pct == 6.0
    assert "Price is 5% to 8% above support" in result.reasons


def test_price_ten_percent_above_support():
    result = calculate(base_metrics(price=110.0))

    assert result.entry_label == "Too Late"
    assert result.distance_to_support_pct == 10.0
    assert "Price is more than 8% above support" in result.reasons


def test_missing_current_price():
    metrics = base_metrics()
    metrics["current_price"] = None

    result = calculate(metrics)

    assert result.entry_label == "Unavailable"
    assert result.entry_score == 0.0
    assert result.current_price is None
    assert "Missing current price" in result.warnings


def test_missing_support_zone():
    metrics = base_metrics()
    metrics.pop("nearest_support_low")
    metrics.pop("nearest_support_high")

    result = calculate(metrics)

    assert result.entry_label == "Unavailable"
    assert result.ideal_entry_low is None
    assert "Missing support zone" in result.warnings


def test_strong_support_adjustment():
    normal = base_metrics(price=103.0)
    strong = base_metrics(price=103.0)
    strong["support_strength_score"] = 95.0
    strong["bounce_success_rate"] = 92.0
    strong["entry_quality_score"] = 94.0
    strong["institutional_bounce_score"] = 93.0

    normal_result = calculate(normal)
    strong_result = calculate(strong)

    assert strong_result.entry_score > normal_result.entry_score
    assert "Strong support strength improves entry quality" in strong_result.reasons
    assert "Strong bounce history improves entry quality" in strong_result.reasons


def test_high_atr_penalty():
    normal = calculate(base_metrics(price=103.0))
    high_atr_metrics = base_metrics(price=103.0)
    high_atr_metrics["atr_pct"] = 9.0

    high_atr = calculate(high_atr_metrics)

    assert high_atr.entry_score < normal.entry_score
    assert "Very high ATR increases entry risk" in high_atr.reasons


def test_score_clamping():
    high = base_metrics(price=99.0)
    high.update(
        {
            "support_strength_score": 500.0,
            "bounce_success_rate": 500.0,
            "entry_quality_score": 500.0,
            "institutional_bounce_score": 500.0,
            "opportunity_rating_score": 500.0,
        }
    )
    low = base_metrics(price=150.0)
    low.update({"atr_pct": 50.0, "risk_score": 0.0})

    assert calculate(high).entry_score == 100.0
    assert calculate(low).entry_score == 0.0


def test_deterministic_output():
    metrics = base_metrics(price=103.0)
    metrics["support_strength_score"] = ScoreResult("support_strength_score", 88.0)

    first = calculate(metrics)
    second = calculate(dict(reversed(list(metrics.items()))))

    assert first == second
