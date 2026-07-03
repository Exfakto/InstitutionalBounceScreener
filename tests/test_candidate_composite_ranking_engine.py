from services.bounce_composite_scoring_engine import BounceCompositeScoreResult
from services.candidate_ranking_engine import CandidateRankingEngine


def score(ticker, final_score, confidence="HIGH", explanation=None, warnings=None):
    return BounceCompositeScoreResult(
        ticker=ticker,
        final_score=final_score,
        support_score=final_score,
        bounce_score=final_score,
        technical_score=final_score,
        institutional_score=final_score,
        confidence_level=confidence,
        explanation=explanation or [f"{ticker} explanation"],
        warnings=warnings or [],
    )


def test_composite_ranking_order_descending():
    result = CandidateRankingEngine().rank_composite_scores(
        [
            score("BBB", 72, "MEDIUM"),
            score("AAA", 95, "HIGH"),
            score("CCC", 84, "HIGH"),
        ]
    )

    assert [item.ticker for item in result.ranked_candidates] == ["AAA", "CCC", "BBB"]
    assert [item.final_score for item in result.ranked_candidates] == [95, 84, 72]


def test_composite_grade_assignment():
    engine = CandidateRankingEngine()

    result = engine.rank_composite_scores(
        [
            score("APLUS", 95, "HIGH"),
            score("A", 85, "HIGH"),
            score("B", 75, "MEDIUM"),
            score("C", 65, "MEDIUM"),
            score("D", 55, "MEDIUM"),
        ],
        minimum_score=50,
    )

    grades = {item.ticker: item.grade for item in result.ranked_candidates}
    assert grades == {
        "APLUS": "A+",
        "A": "A",
        "B": "B",
        "C": "C",
        "D": "D",
    }


def test_composite_rejection_by_score():
    result = CandidateRankingEngine().rank_composite_scores(
        [score("LOW", 45, "HIGH")],
    )

    assert result.ranked_candidates == []
    assert result.rejected_candidates[0].ticker == "LOW"
    assert result.rejected_candidates[0].grade == "REJECT"
    assert result.rejected_candidates[0].setup_label == "Rejected"
    assert "Final score below minimum threshold (60)" in result.rejected_candidates[0].rejection_reasons


def test_composite_rejection_by_low_confidence():
    result = CandidateRankingEngine().rank_composite_scores(
        [score("LOWCONF", 88, "LOW")],
    )

    assert result.ranked_candidates == []
    assert result.rejected_candidates[0].ticker == "LOWCONF"
    assert "Low confidence candidates are rejected" in result.rejected_candidates[0].rejection_reasons


def test_allow_low_confidence_accepts_otherwise_valid_candidate():
    result = CandidateRankingEngine().rank_composite_scores(
        [score("LOWCONF", 88, "LOW")],
        allow_low_confidence=True,
    )

    assert [item.ticker for item in result.ranked_candidates] == ["LOWCONF"]
    assert result.ranked_candidates[0].grade == "A"
    assert result.ranked_candidates[0].setup_label == "High-Quality Bounce"
    assert result.rejected_candidates == []


def test_composite_rank_numbering_after_filtering():
    result = CandidateRankingEngine().rank_composite_scores(
        [
            score("REJECTED", 40, "HIGH"),
            score("SECOND", 70, "MEDIUM"),
            score("FIRST", 90, "HIGH"),
        ]
    )

    assert [(item.rank, item.ticker) for item in result.ranked_candidates] == [
        (1, "FIRST"),
        (2, "SECOND"),
    ]
    assert result.rejected_candidates[0].rank == 0


def test_composite_empty_input_returns_safe_result():
    result = CandidateRankingEngine().rank_composite_scores([])

    assert result.ranked_candidates == []
    assert result.rejected_candidates == []
    assert result.warnings == ["No composite scores provided"]


def test_composite_explanation_warnings_and_rejection_reasons_preserved():
    result = CandidateRankingEngine().rank_composite_scores(
        [
            score(
                "SPARSE",
                58,
                "LOW",
                explanation=["Sparse support evidence"],
                warnings=["Missing technical data"],
            )
        ]
    )

    rejected = result.rejected_candidates[0]
    assert rejected.explanation == ["Sparse support evidence"]
    assert rejected.warnings == ["Missing technical data"]
    assert result.warnings == ["Missing technical data"]
    assert "Final score below minimum threshold (60)" in rejected.rejection_reasons
    assert "Low confidence candidates are rejected" in rejected.rejection_reasons
