from types import SimpleNamespace

from services.institutional_bounce_scoring_engine import (
    InstitutionalBounceScoreInput,
    InstitutionalBounceScoringEngine,
)


def score_for(**kwargs):
    return InstitutionalBounceScoringEngine().score(kwargs)


def test_institutional_bounce_scoring_elite_setup():
    result = score_for(
        ticker="ELITE",
        fundamental_quality_score=95,
        institutional_sponsorship_score=96,
        support_strength_score=94,
        bounce_success_rate=95,
        average_bounce_pct=20,
        relative_strength_score=92,
        volume_accumulation_score=90,
        risk_rating="Low",
    )

    assert result.final_score >= 90
    assert result.rating_label == "A+ Elite Bounce Setup"
    assert result.opportunity_rating == "Strong"
    assert result.risk_rating == "Low"
    assert "Final score" in result.explanation


def test_institutional_bounce_scoring_high_probability_setup():
    result = score_for(
        fundamental_quality_score=85,
        institutional_sponsorship_score=84,
        support_strength_score=83,
        bounce_success_rate=82,
        average_bounce_pct=14,
        relative_strength_score=82,
        volume_accumulation_score=80,
        risk_rating="Low",
    )

    assert 80 <= result.final_score < 90
    assert result.rating_label == "A High-Probability Setup"
    assert result.opportunity_rating == "Strong"


def test_institutional_bounce_scoring_watchlist_candidate():
    result = score_for(
        fundamental_quality_score=75,
        institutional_sponsorship_score=76,
        support_strength_score=74,
        bounce_success_rate=72,
        average_bounce_pct=10,
        relative_strength_score=73,
        volume_accumulation_score=72,
        risk_rating="Low",
    )

    assert 70 <= result.final_score < 80
    assert result.rating_label == "B Watchlist Candidate"
    assert result.opportunity_rating == "Moderate"


def test_institutional_bounce_scoring_weak_and_reject_candidates():
    weak = score_for(
        fundamental_quality_score=65,
        institutional_sponsorship_score=65,
        support_strength_score=65,
        bounce_success_rate=62,
        average_bounce_pct=8,
        relative_strength_score=65,
        volume_accumulation_score=65,
        risk_rating="Low",
    )
    reject = score_for(
        fundamental_quality_score=30,
        institutional_sponsorship_score=25,
        support_strength_score=20,
        bounce_success_rate=15,
        average_bounce_pct=2,
        relative_strength_score=25,
        volume_accumulation_score=20,
        risk_rating="High",
    )

    assert weak.rating_label == "C Weak / Needs Confirmation"
    assert weak.opportunity_rating == "Weak"
    assert reject.rating_label == "Reject"
    assert reject.opportunity_rating == "Reject"


def test_institutional_bounce_scoring_risk_penalty_cap():
    result = score_for(
        fundamental_quality_score=100,
        institutional_sponsorship_score=100,
        support_strength_score=100,
        bounce_success_rate=100,
        average_bounce_pct=50,
        relative_strength_score=100,
        volume_accumulation_score=100,
        risk_score=500,
    )

    assert result.risk_penalty_score == 15.0
    assert result.final_score == 85.0


def test_institutional_bounce_scoring_missing_data_does_not_crash():
    result = InstitutionalBounceScoringEngine().score(
        InstitutionalBounceScoreInput(ticker="MISS")
    )

    assert result.final_score >= 0
    assert result.risk_rating == "Unknown"
    assert result.warnings
    assert result.explanation


def test_institutional_bounce_scoring_accepts_namespace_metrics():
    candidate = SimpleNamespace(
        ticker="NS",
        metrics={
            "quality_score": 90,
            "institutional_score": 88,
            "support_strength_score": 86,
            "bounce_success_rate": 84,
            "average_bounce": 12,
            "relative_strength_score": 82,
            "volume_score": 80,
            "overall_risk_score": 20,
        },
    )

    result = InstitutionalBounceScoringEngine().score(candidate)

    assert result.ticker == "NS"
    assert result.final_score > 75
