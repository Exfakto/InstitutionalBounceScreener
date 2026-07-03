import sqlite3

from database.manager import DatabaseManager
from services.bounce_composite_scoring_engine import BounceCompositeScoreResult
from services.candidate_pipeline_adapter import CandidatePipelineAdapter
from services.candidate_ranking_engine import RankedCandidate


def build_manager():
    manager = DatabaseManager.__new__(DatabaseManager)
    manager.connection = sqlite3.connect(":memory:")
    manager.connection.row_factory = sqlite3.Row
    manager.cursor = manager.connection.cursor()
    manager.initialize()
    return manager


def composite(ticker, final_score, confidence="HIGH", explanation=None, warnings=None):
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


def ranked(ticker, rank, score, grade="A", reasons=None):
    return RankedCandidate(
        rank=rank,
        ticker=ticker,
        final_score=score,
        grade=grade,
        confidence_level="HIGH",
        setup_label="High-Quality Bounce",
        explanation=["Strong support", "Institutional sponsorship is strong"],
        warnings=["Minor warning"],
        rejection_reasons=reasons or [],
    )


def test_ranked_candidates_table_created():
    manager = build_manager()

    manager.cursor.execute("PRAGMA table_info(ranked_candidates)")
    columns = {row["name"] for row in manager.cursor.fetchall()}

    assert "ticker" in columns
    assert "rank" in columns
    assert "final_score" in columns
    assert "explanation_json" in columns
    assert "warnings_json" in columns
    assert "rejection_reasons_json" in columns
    assert "run_id" in columns
    manager.close()


def test_save_and_fetch_ranked_candidates():
    manager = build_manager()

    saved = manager.save_ranked_candidates(
        "run-1",
        [ranked("AAA", 1, 91, "A+"), ranked("BBB", 2, 82, "A")],
    )
    fetched = manager.fetch_ranked_candidates("run-1")

    assert saved == 2
    assert [item.ticker for item in fetched] == ["AAA", "BBB"]
    assert fetched[0].rank == 1
    assert fetched[0].final_score == 91
    assert fetched[0].grade == "A+"
    assert fetched[0].explanation == ["Strong support", "Institutional sponsorship is strong"]
    assert fetched[0].warnings == ["Minor warning"]
    assert fetched[0].source["run_id"] == "run-1"
    manager.close()


def test_fetch_latest_ranked_candidates():
    manager = build_manager()

    manager.save_ranked_candidates("run-1", [ranked("AAA", 1, 91)])
    manager.save_ranked_candidates("run-2", [ranked("CCC", 1, 93)])

    latest = manager.fetch_latest_ranked_candidates()

    assert [item.ticker for item in latest] == ["CCC"]
    assert latest[0].source["run_id"] == "run-2"
    manager.close()


def test_clear_ranked_candidates_by_run_id():
    manager = build_manager()
    manager.save_ranked_candidates("run-1", [ranked("AAA", 1, 91)])
    manager.save_ranked_candidates("run-2", [ranked("BBB", 1, 88)])

    deleted = manager.clear_ranked_candidates("run-1")

    assert deleted == 1
    assert manager.fetch_ranked_candidates("run-1") == []
    assert [item.ticker for item in manager.fetch_ranked_candidates("run-2")] == ["BBB"]
    manager.close()


def test_pipeline_adapter_ranking_and_persistence():
    manager = build_manager()
    adapter = CandidatePipelineAdapter(manager)

    result = adapter.run(
        [
            composite("LOW", 45, "HIGH"),
            composite("TOP", 92, "HIGH"),
            composite("MID", 76, "MEDIUM"),
        ],
        run_id="pipeline-1",
    )
    persisted = manager.fetch_ranked_candidates("pipeline-1")

    assert result.run_id == "pipeline-1"
    assert [item.ticker for item in result.ranked_candidates] == ["TOP", "MID"]
    assert [item.rank for item in result.ranked_candidates] == [1, 2]
    assert [item.ticker for item in persisted] == ["TOP", "MID", "LOW"]
    assert persisted[-1].grade == "REJECT"
    assert persisted[-1].rejection_reasons
    manager.close()


def test_pipeline_adapter_empty_input_persists_empty_run():
    manager = build_manager()
    adapter = CandidatePipelineAdapter(manager)

    result = adapter.run([], run_id="empty-run")

    assert result.run_id == "empty-run"
    assert result.ranked_candidates == []
    assert result.rejected_candidates == []
    assert result.warnings == ["No composite scores provided"]
    assert manager.fetch_ranked_candidates("empty-run") == []
    manager.close()


def test_json_explanation_warning_and_rejection_persistence():
    manager = build_manager()
    candidate = ranked(
        "REJ",
        0,
        42,
        grade="REJECT",
        reasons=["Final score below minimum threshold (60)", "Low confidence candidates are rejected"],
    )

    manager.save_ranked_candidates("json-run", [candidate])
    fetched = manager.fetch_ranked_candidates("json-run")[0]

    assert fetched.explanation == ["Strong support", "Institutional sponsorship is strong"]
    assert fetched.warnings == ["Minor warning"]
    assert fetched.rejection_reasons == [
        "Final score below minimum threshold (60)",
        "Low confidence candidates are rejected",
    ]
    manager.close()
