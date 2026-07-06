from types import SimpleNamespace

from services.institutional_data_provider import UnavailableInstitutionalDataProvider
from services.institutional_intelligence_engine import InstitutionalIntelligenceEngine


def engine():
    return InstitutionalIntelligenceEngine(UnavailableInstitutionalDataProvider())


def test_institutional_intelligence_strong_accumulation_case():
    result = engine().analyze(
        {
            "ticker": "AAA",
            "institutional_ownership_pct": 72,
            "institutional_ownership_change_qoq": 2.5,
            "net_institutional_buying": 250_000_000,
            "institutional_holders": 1200,
            "institutional_holders_change": 40,
            "recent_13f_accumulation": "accumulation",
            "major_buyers": ["BlackRock", "Vanguard"],
            "insider_buying_flag": 1,
            "insider_net_activity": 2_000_000,
        }
    )

    assert result.ticker == "AAA"
    assert result.sponsorship_rating == "Strong"
    assert result.flow_rating == "Accumulation"
    assert result.insider_rating == "Positive"
    assert result.final_outlook == "Strong Accumulation"
    assert 0 <= result.institutional_score <= 100
    assert result.institutional_score >= 70


def test_institutional_intelligence_neutral_case():
    result = engine().analyze(
        SimpleNamespace(
            ticker="NEU",
            metrics={
                "institutional_ownership_pct": 45,
                "institutional_ownership_change_qoq": 0,
                "net_institutional_buying": 0,
                "institutional_holders_change": 0,
                "recent_13f_activity": "neutral",
                "insider_buying_flag": 0,
                "insider_selling_flag": 0,
            },
        )
    )

    assert result.sponsorship_rating == "Moderate"
    assert result.flow_rating == "Neutral"
    assert result.insider_rating == "Neutral"
    assert result.final_outlook == "Neutral"


def test_institutional_intelligence_distribution_case():
    result = engine().analyze(
        ticker="DIST",
        institutional_ownership_pct=18,
        institutional_ownership_change_qoq=-3,
        net_institutional_buying=-300_000_000,
        institutional_holders_change=-25,
        recent_13f_accumulation="distribution",
        insider_selling=True,
    )

    assert result.sponsorship_rating == "Weak"
    assert result.flow_rating == "Distribution"
    assert result.insider_rating == "Negative"
    assert result.final_outlook == "Distribution"
    assert 0 <= result.institutional_score <= 100


def test_institutional_intelligence_missing_data_case():
    result = engine().analyze({"ticker": "MISS"})

    assert result.sponsorship_rating == "Unknown"
    assert result.flow_rating == "Unknown"
    assert result.insider_rating == "Unknown"
    assert result.final_outlook == "Unknown"
    assert result.institutional_score == 0.0
    assert result.warnings == ["Missing institutional data"]


def test_institutional_intelligence_insider_positive_negative_logic():
    institutional_engine = engine()

    positive = institutional_engine.analyze({"ticker": "BUY", "insider_buying": True})
    negative = institutional_engine.analyze({"ticker": "SELL", "insider_selling": True})

    assert positive.insider_rating == "Positive"
    assert negative.insider_rating == "Negative"


def test_institutional_intelligence_score_boundaries():
    result = engine().analyze(
        {
            "ticker": "BOUND",
            "institutional_ownership_pct": 500,
            "institutional_ownership_change_qoq": 100,
            "net_institutional_buying": 10_000_000_000,
            "institutional_holders_change": 10000,
            "insider_buying": True,
        }
    )

    assert 0 <= result.institutional_score <= 100
