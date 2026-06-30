from analysis.opportunity_rating import OpportunityRatingCalculator
from analysis.score_result import ScoreResult


def base_metrics(value):
    return {
        "institutional_bounce_score": value,
        "quality_score": value,
        "institutional_score": value,
        "institutional_momentum_score": value,
        "technical_score": value,
        "relative_strength_score": value,
        "support_score": value,
        "bounce_score": value,
        "entry_quality_score": value,
        "volume_score": value,
        "trend_score": value,
        "earnings_risk_score": 30,
        "risk_score": value,
        "distance_to_support_pct": 5,
        "bounce_success_rate": 70,
        "average_bounce_pct": 5,
    }


def calculate(metrics):
    return OpportunityRatingCalculator().calculate(metrics)


def test_elite_bounce_setup():
    metrics = base_metrics(95)
    metrics["earnings_risk_score"] = 10
    metrics["distance_to_support_pct"] = 2
    metrics["bounce_success_rate"] = 88
    metrics["average_bounce_pct"] = 10

    result = calculate(metrics)

    assert result.rating_score == 100.0
    assert result.rating_label == "Elite Bounce"
    assert result.stars == 5
    assert "Strong Gen 2 institutional bounce score" in result.strengths
    assert "Price is close to support" in result.strengths


def test_high_probability_setup():
    result = calculate(base_metrics(82))

    assert 80 <= result.rating_score < 90
    assert result.rating_label == "High Probability"
    assert result.stars == 4


def test_watch_list_setup():
    result = calculate(base_metrics(72))

    assert 70 <= result.rating_score < 80
    assert result.rating_label == "Watch List"
    assert result.stars == 3


def test_weak_setup():
    result = calculate(base_metrics(63))

    assert 60 <= result.rating_score < 70
    assert result.rating_label == "Weak Setup"
    assert result.stars == 2


def test_avoid_setup():
    metrics = base_metrics(45)
    metrics["earnings_risk_score"] = 75
    metrics["distance_to_support_pct"] = 16
    metrics["bounce_success_rate"] = 40
    metrics["average_bounce_pct"] = 2

    result = calculate(metrics)

    assert result.rating_score < 60
    assert result.rating_label == "Avoid"
    assert result.stars == 1
    assert "Weak historical bounce success rate" in result.weaknesses


def test_missing_metrics_do_not_crash_and_create_warnings():
    result = calculate({"institutional_bounce_score": 82})

    assert result.rating_label == "High Probability"
    assert result.warnings
    assert "Missing metric: support_score" in result.warnings
    assert "Missing metric: earnings_risk_score" in result.warnings


def test_no_metrics_returns_avoid_with_warnings():
    result = calculate({})

    assert result.rating_score == 0.0
    assert result.rating_label == "Avoid"
    assert "No valid opportunity score metrics available" in result.warnings


def test_distance_too_far_from_support_reduces_rating():
    near_support = base_metrics(85)
    near_support["distance_to_support_pct"] = 3
    extended = base_metrics(85)
    extended["distance_to_support_pct"] = 25

    near_result = calculate(near_support)
    extended_result = calculate(extended)

    assert near_result.rating_score > extended_result.rating_score
    assert "Price is extended above support" in extended_result.weaknesses


def test_high_earnings_risk_penalty():
    metrics = base_metrics(85)
    metrics["earnings_risk_score"] = 90

    result = calculate(metrics)

    assert result.rating_score < 80
    assert "Severe near-term earnings risk" in result.weaknesses


def test_strengths_and_weaknesses_output():
    metrics = base_metrics(58)
    metrics["support_score"] = 88
    metrics["relative_strength_score"] = 45
    metrics["trend_score"] = 42
    metrics["risk_score"] = 40

    result = calculate(metrics)

    assert "Strong support quality" in result.strengths
    assert "Weak relative strength" in result.weaknesses
    assert "Weak trend" in result.weaknesses
    assert "Unfavorable risk profile" in result.weaknesses


def test_score_result_inputs_and_clamping():
    metrics = base_metrics(150)
    metrics["institutional_bounce_score"] = ScoreResult(
        name="institutional_bounce_score",
        value=150,
    )
    metrics["earnings_risk_score"] = 0
    metrics["distance_to_support_pct"] = 0
    metrics["bounce_success_rate"] = 150
    metrics["average_bounce_pct"] = 20

    result = calculate(metrics)

    assert result.rating_score == 100.0
    assert result.rating_label == "Elite Bounce"
