from analysis.candidate_score import CandidateScore
from analysis.institutional_checklist import InstitutionalChecklistEvaluator
from analysis.opportunity_rating import OpportunityRatingCalculator
from analysis.score_result import ScoreResult
from analysis.trade_thesis import TradeThesisGenerator


def base_metrics(value=85):
    return {
        "ticker": "AMZN",
        "company_name": "Amazon.com",
        "institutional_bounce_score": value,
        "relative_strength_score": value,
        "trend_score": value,
        "institutional_score": value,
        "support_score": value,
        "bounce_score": value,
        "volume_score": value,
        "institutional_momentum_score": value,
        "earnings_risk_score": 25,
        "risk_score": value,
        "distance_to_support_pct": 2.4,
        "bounce_success_rate": 86,
        "average_bounce_pct": 9,
    }


def enrich(metrics):
    metrics = dict(metrics)
    metrics["opportunity_rating"] = OpportunityRatingCalculator().calculate(metrics)
    metrics["institutional_checklist"] = InstitutionalChecklistEvaluator().evaluate(
        {
            **metrics,
            "opportunity_rating_score": metrics["opportunity_rating"].rating_score,
        }
    )
    return metrics


def generate(metrics):
    return TradeThesisGenerator().generate(metrics)


def sentence_count(summary):
    return len(
        [
            sentence
            for sentence in summary.replace("Amazon.com", "Amazon").split(".")
            if sentence.strip()
        ]
    )


def test_elite_bounce_candidate():
    metrics = base_metrics(95)
    metrics["earnings_risk_score"] = 10
    result = generate(enrich(metrics))

    assert result.title == "AMZN Elite Bounce Trade Thesis"
    assert result.confidence == "Very High"
    assert "2.4% above a validated institutional support zone" in result.summary
    assert "86% historical bounce success rate" in result.summary
    assert "Elite Bounce" in result.summary
    assert "support quality is strong" in result.strengths
    assert 2 <= sentence_count(result.summary) <= 5


def test_high_probability_candidate():
    metrics = base_metrics(80)
    metrics["distance_to_support_pct"] = 5
    metrics["bounce_success_rate"] = 70
    metrics["average_bounce_pct"] = 5
    result = generate(enrich(metrics))

    assert result.title == "AMZN High Probability Trade Thesis"
    assert result.confidence == "High"
    assert "High Probability" in result.summary
    assert "relative strength remains favorable" in result.summary.lower()


def test_weak_candidate():
    metrics = base_metrics(45)
    metrics.update(
        {
            "distance_to_support_pct": 14,
            "bounce_success_rate": 35,
            "trend_score": 35,
            "risk_score": 30,
            "earnings_risk_score": 80,
        }
    )

    result = generate(enrich(metrics))

    assert result.confidence in {"Very Low", "Low"}
    assert "Avoid" in result.title
    assert "price is extended above support" in result.risks
    assert "ATR risk is unfavorable" in result.risks


def test_missing_metrics_do_not_get_invented():
    result = generate({"ticker": "MSFT"})

    assert result.title == "MSFT Trade Thesis - Very Low Confidence"
    assert result.confidence == "Very Low"
    assert "insufficient available data" in result.summary
    assert "%" not in result.summary
    assert result.strengths == []
    assert result.risks == []


def test_earnings_warning_is_mentioned():
    metrics = base_metrics(82)
    metrics["earnings_risk_score"] = 75

    result = generate(enrich(metrics))

    assert "earnings risk is elevated" in result.risks
    assert "earnings risk is elevated" in result.summary


def test_poor_trend_is_mentioned():
    metrics = base_metrics(82)
    metrics["trend_score"] = 35

    result = generate(enrich(metrics))

    assert "trend alignment is weak" in result.risks
    assert "trend alignment is weak" in result.summary


def test_strong_institutional_buying_is_mentioned():
    metrics = base_metrics(80)
    metrics["institutional_momentum_score"] = 92

    result = generate(enrich(metrics))

    assert "institutional momentum is positive" in result.strengths
    assert "institutional momentum is positive" in result.summary


def test_output_is_deterministic():
    metrics = enrich(base_metrics(88))

    first = generate(metrics)
    second = generate(dict(reversed(list(metrics.items()))))

    assert first == second


def test_empty_input():
    result = generate({})

    assert result.title == "Candidate Trade Thesis - Very Low Confidence"
    assert result.summary == (
        "Candidate has insufficient available data for a complete institutional "
        "bounce thesis. Overall confidence is very low until more evidence is "
        "available."
    )
    assert result.confidence == "Very Low"


def test_candidate_score_input():
    metrics = enrich(base_metrics(85))
    candidate = CandidateScore(
        ticker="AMZN",
        scores=[
            ScoreResult("relative_strength_score", 85),
            ScoreResult("trend_score", 85),
            ScoreResult("support_score", 85),
            ScoreResult("bounce_score", 85),
            ScoreResult("volume_score", 85),
        ],
        composite_score=ScoreResult("composite_score", 85),
        institutional_bounce_score=85,
        composite_intelligence_component_scores={
            "institutional_momentum_score": 85,
            "earnings_risk_score": 20,
            "risk_score": 85,
            "distance_to_support_pct": 2.4,
            "bounce_success_rate": 86,
        },
        institutional_checklist=metrics["institutional_checklist"],
    )

    result = TradeThesisGenerator().generate(candidate)

    assert result.title == "AMZN Trade Thesis - Very High Confidence"
    assert "AMZN is trading 2.4% above" in result.summary
