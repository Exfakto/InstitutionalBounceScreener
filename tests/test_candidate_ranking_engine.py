from types import SimpleNamespace

from services.candidate_ranking_engine import CandidateRankingEngine


def candidate(ticker, score, risk="Low"):
    return {
        "ticker": ticker,
        "fundamental_quality_score": score,
        "institutional_sponsorship_score": score,
        "support_strength_score": score,
        "bounce_success_rate": score,
        "average_bounce_pct": 20,
        "relative_strength_score": score,
        "volume_accumulation_score": score,
        "risk_rating": risk,
    }


def test_candidate_ranking_sorts_by_final_score_descending():
    result = CandidateRankingEngine().rank_candidates(
        [candidate("B", 75), candidate("A", 95), candidate("C", 85)]
    )

    assert [item.ticker for item in result.ranked_candidates] == ["A", "C", "B"]
    assert [item.rank for item in result.ranked_candidates] == [1, 2, 3]


def test_candidate_ranking_produces_signal_labels():
    ranked = CandidateRankingEngine().rank_candidates(
        [
            candidate("STRONG", 95),
            candidate("BUY", 85),
            candidate("WATCH", 75),
            candidate("WAIT", 65),
            candidate("AVOID", 40),
        ]
    ).ranked_candidates
    signals = {item.ticker: item.signal for item in ranked}

    assert signals["STRONG"] == "Strong Buy"
    assert signals["BUY"] == "Buy"
    assert signals["WATCH"] == "Watch"
    assert signals["WAIT"] == "Wait"
    assert signals["AVOID"] == "Avoid"


def test_candidate_ranking_high_risk_caps_signal():
    result = CandidateRankingEngine().rank_candidates([candidate("RISK", 85, risk="High")])

    ranked = result.ranked_candidates[0]
    assert ranked.risk_rating == "High"
    assert ranked.signal == "Watch"


def test_candidate_ranking_elite_high_risk_can_still_be_buy_not_strong_buy():
    result = CandidateRankingEngine().rank_candidates([candidate("ELITE", 100, risk="High")])

    assert result.ranked_candidates[0].signal == "Buy"


def test_candidate_ranking_handles_dictionaries_and_namespaces():
    namespace_candidate = SimpleNamespace(
        ticker="NS",
        metrics={
            "quality_score": 82,
            "institutional_score": 82,
            "support_strength_score": 82,
            "bounce_success_rate": 82,
            "average_bounce": 12,
            "relative_strength_score": 82,
            "volume_score": 82,
            "overall_risk_score": 10,
        },
    )

    result = CandidateRankingEngine().rank_candidates([candidate("DICT", 80), namespace_candidate])

    assert len(result.ranked_candidates) == 2
    assert {item.ticker for item in result.ranked_candidates} == {"DICT", "NS"}


def test_candidate_ranking_handles_partial_missing_data():
    result = CandidateRankingEngine().rank_candidates([{"ticker": "PARTIAL"}])

    ranked = result.ranked_candidates[0]
    assert ranked.ticker == "PARTIAL"
    assert ranked.final_score >= 0
    assert ranked.warnings
    assert ranked.category_scores


def test_candidate_ranking_empty_input():
    result = CandidateRankingEngine().rank_candidates([])

    assert result.ranked_candidates == []
    assert result.warnings == ["No candidates provided"]


def test_candidate_ranking_deterministic_tie_handling():
    result = CandidateRankingEngine().rank_candidates(
        [candidate("ZZZ", 80), candidate("AAA", 80)]
    )

    assert [item.ticker for item in result.ranked_candidates] == ["AAA", "ZZZ"]
