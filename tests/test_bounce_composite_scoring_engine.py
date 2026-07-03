from database.institutional_data import InstitutionalData
from services.bounce_composite_scoring_engine import (
    BounceCompositeScoringEngine,
    BounceCompositeScoreResult,
)
from services.bounce_detection_engine import BounceAnalysisResult
from services.institutional_intelligence_engine import InstitutionalSignal
from services.institutional_intelligence_service import InstitutionalScoreResult
from services.support_zone_engine import SupportZone
from services.technical_indicator_engine import TechnicalIndicatorResult


def support(strength=85, confidence=88, touches=5):
    return SupportZone(
        ticker="AAA",
        zone_low=95,
        zone_high=100,
        zone_center=97.5,
        zone_width_pct=5.1,
        touch_count=touches,
        first_touch_date="2026-01-01",
        last_touch_date="2026-06-01",
        support_age_days=150,
        average_touch_volume=2_000_000,
        support_strength_score=strength,
        confidence_score=confidence,
    )


def bounce(success=85, average=18, largest=35, tests=5, failures=0):
    return BounceAnalysisResult(
        ticker="AAA",
        support_zone=support(),
        total_support_tests=tests,
        successful_bounces=4,
        failed_bounces=1,
        bounce_success_rate=success,
        average_bounce_pct=average,
        median_bounce_pct=16,
        largest_bounce_pct=largest,
        average_days_to_peak=18,
        failed_support_breaks=failures,
    )


def technical(close=120, ema20=112, ema50=106, ema200=95, rsi=62, macd_hist=1.4, rel_volume=1.6):
    return TechnicalIndicatorResult(
        ticker="AAA",
        close=close,
        ema20=ema20,
        ema50=ema50,
        ema200=ema200,
        rsi14=rsi,
        macd_histogram=macd_hist,
        relative_volume=rel_volume,
    )


def institutional(score=88, warnings=None):
    score_result = InstitutionalScoreResult(
        ownership_score=90,
        ownership_trend_score=85,
        institutional_buying_score=90,
        insider_activity_score=85,
        overall_institutional_strength_score=score,
        ownership_explanation="Strong ownership.",
        ownership_trend_explanation="Ownership rising.",
        institutional_buying_explanation="Buying positive.",
        insider_activity_explanation="Insider buying present.",
        overall_explanation="Strong institutional strength.",
        warnings=warnings or [],
    )
    return InstitutionalSignal(
        ticker="AAA",
        raw_institutional_data=InstitutionalData(ticker="AAA"),
        score_result=score_result,
        as_of_date="2026-06-30",
        source="unit-test",
        warnings=warnings or [],
    )


def test_excellent_institutional_bounce_setup_scores_high():
    result = BounceCompositeScoringEngine().score(
        ticker="AAA",
        support=support(),
        bounce=bounce(),
        technical=technical(),
        institutional=institutional(),
    )

    assert isinstance(result, BounceCompositeScoreResult)
    assert result.ticker == "AAA"
    assert result.final_score >= 85
    assert result.confidence_level == "HIGH"
    assert result.warnings == []
    assert any("Support quality is strong" in item for item in result.explanation)
    assert any("Institutional sponsorship is strong" in item for item in result.explanation)


def test_average_setup_scores_middle_with_medium_confidence():
    result = BounceCompositeScoringEngine().score(
        support=support(strength=58, confidence=60, touches=3),
        bounce=bounce(success=55, average=8, largest=14, tests=3),
        technical=technical(close=100, ema20=102, ema50=98, ema200=96, rsi=44, macd_hist=0, rel_volume=1.0),
        institutional=institutional(score=58),
    )

    assert 50 <= result.final_score <= 70
    assert result.confidence_level == "MEDIUM"
    assert result.support_score < 70
    assert result.bounce_score < 70


def test_weak_setup_scores_low_confidence():
    result = BounceCompositeScoringEngine().score(
        support=support(strength=20, confidence=25, touches=2),
        bounce=bounce(success=20, average=2, largest=4, tests=2, failures=2),
        technical=technical(close=80, ema20=95, ema50=100, ema200=110, rsi=25, macd_hist=-2, rel_volume=0.5),
        institutional=institutional(score=20),
    )

    assert result.final_score < 35
    assert result.confidence_level == "LOW"
    assert any("weak" in item.lower() for item in result.explanation)


def test_missing_institutional_data_warns_and_uses_neutral_component():
    result = BounceCompositeScoringEngine().score(
        support=support(),
        bounce=bounce(),
        technical=technical(),
        institutional=None,
    )

    assert result.institutional_score == 50.0
    assert "Missing institutional data" in result.warnings
    assert result.confidence_level == "MEDIUM"


def test_missing_technical_data_warns_and_uses_neutral_component():
    result = BounceCompositeScoringEngine().score(
        support=support(),
        bounce=bounce(),
        technical=None,
        institutional=institutional(),
    )

    assert result.technical_score == 50.0
    assert "Missing technical data" in result.warnings
    assert result.confidence_level == "MEDIUM"


def test_score_bounds_are_clamped():
    high = BounceCompositeScoringEngine().score(
        support={"ticker": "HI", "support_strength_score": 900, "confidence_score": 900},
        bounce={"ticker": "HI", "bounce_success_rate": 900, "average_bounce_pct": 900, "largest_bounce_pct": 900},
        technical={"ticker": "HI", "close": 100, "ema20": 1, "ema50": 1, "ema200": 1, "rsi14": 60, "macd_histogram": 5, "relative_volume": 10},
        institutional={"ticker": "HI", "overall_institutional_strength_score": 900},
    )
    low = BounceCompositeScoringEngine().score(
        support={"ticker": "LOW", "support_strength_score": -900, "confidence_score": -900},
        bounce={"ticker": "LOW", "bounce_success_rate": -900, "average_bounce_pct": -900, "largest_bounce_pct": -900, "failed_support_breaks": 5},
        technical={"ticker": "LOW", "close": 1, "ema20": 100, "ema50": 100, "ema200": 100, "rsi14": 99, "macd_histogram": -5, "relative_volume": -10},
        institutional={"ticker": "LOW", "overall_institutional_strength_score": -900},
    )

    assert 90 <= high.final_score <= 100
    assert all(0 <= value <= 100 for value in [
        high.support_score,
        high.bounce_score,
        high.technical_score,
        high.institutional_score,
    ])
    assert 0 <= low.final_score <= 100
    assert all(0 <= value <= 100 for value in [
        low.support_score,
        low.bounce_score,
        low.technical_score,
        low.institutional_score,
    ])


def test_confidence_levels_reflect_missing_components():
    engine = BounceCompositeScoringEngine()

    high = engine.score(support=support(), bounce=bounce(), technical=technical(), institutional=institutional())
    medium = engine.score(support=support(), bounce=bounce(), technical=technical(), institutional=None)
    low = engine.score(support=None, bounce=None, technical=technical(), institutional=institutional())

    assert high.confidence_level == "HIGH"
    assert medium.confidence_level == "MEDIUM"
    assert low.confidence_level == "LOW"


def test_explanation_and_warning_output_for_sparse_data():
    result = BounceCompositeScoringEngine().score(
        ticker="SPARSE",
        support=None,
        bounce=None,
        technical={"ticker": "SPARSE"},
        institutional=institutional(score=50, warnings=["Missing ownership trend"]),
    )

    assert result.ticker == "SPARSE"
    assert result.explanation
    assert "Missing support data" in result.warnings
    assert "Missing bounce history" in result.warnings
    assert "Missing technical metrics" in result.warnings
    assert "Missing ownership trend" in result.warnings
