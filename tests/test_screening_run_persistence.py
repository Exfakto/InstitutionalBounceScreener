import sqlite3
from types import SimpleNamespace

from database.manager import DatabaseManager


def build_manager():
    manager = DatabaseManager.__new__(DatabaseManager)
    manager.connection = sqlite3.connect(":memory:")
    manager.connection.row_factory = sqlite3.Row
    manager.cursor = manager.connection.cursor()
    manager.initialize()
    return manager


def test_screening_runs_table_created():
    manager = build_manager()

    manager.cursor.execute("PRAGMA table_info(screening_runs)")
    columns = {row["name"] for row in manager.cursor.fetchall()}

    assert "run_id" in columns
    assert "status" in columns
    assert "started_at" in columns
    assert "completed_at" in columns
    assert "tickers_requested" in columns
    assert "tickers_processed" in columns
    assert "candidate_count" in columns
    assert "warnings_json" in columns
    assert "errors_json" in columns
    manager.close()


def test_screening_signal_history_table_created():
    manager = build_manager()

    manager.cursor.execute("PRAGMA table_info(screening_signal_history)")
    columns = {row["name"] for row in manager.cursor.fetchall()}

    assert "signal_id" in columns
    assert "run_id" in columns
    assert "created_at" in columns
    assert "ticker" in columns
    assert "company_name" in columns
    assert "sector" in columns
    assert "industry" in columns
    assert "overall_score" in columns
    assert "technical_score" in columns
    assert "bounce_score" in columns
    assert "fundamental_score" in columns
    assert "risk_score" in columns
    assert "current_price" in columns
    assert "entry_zone" in columns
    assert "support" in columns
    assert "stop_loss" in columns
    assert "target_1" in columns
    assert "target_2" in columns
    assert "target_3" in columns
    assert "signal_status" in columns
    assert "notes" in columns
    assert "price_after_5d" in columns
    assert "price_after_10d" in columns
    assert "price_after_20d" in columns
    assert "price_after_60d" in columns
    assert "max_drawdown" in columns
    assert "max_runup" in columns
    assert "outcome" in columns
    manager.close()


def test_save_and_fetch_screening_signal_history():
    manager = build_manager()

    candidate = SimpleNamespace(
        ticker="nee",
        final_score=91.5,
        category_scores={
            "technical_score": 82,
            "bounce_score": 88,
            "fundamental_quality_score": 74,
            "risk_score": 23,
        },
        source={
            "company_name": "NextEra Energy",
            "sector": "Utilities",
            "industry": "Regulated Electric",
            "current_price": 72.5,
            "entry_zone": "70.00 - 72.00",
            "primary_support": 70,
            "stop_loss": 67.5,
            "target_1": 78,
            "target_2": 84,
            "target_3": 90,
        },
    )

    saved = manager.save_screening_run(
        run_id="signal-run-1",
        candidates=[candidate],
        created_at="2026-07-06T10:00:00+00:00",
    )
    history = manager.fetch_screening_history(run_id="signal-run-1")
    signal = manager.fetch_signal(history[0]["signal_id"])
    latest = manager.fetch_latest_signals(limit=1)

    assert saved == 1
    assert history[0]["ticker"] == "NEE"
    assert history[0]["company_name"] == "NextEra Energy"
    assert history[0]["overall_score"] == 91.5
    assert history[0]["technical_score"] == 82
    assert history[0]["bounce_score"] == 88
    assert history[0]["fundamental_score"] == 74
    assert history[0]["risk_score"] == 23
    assert history[0]["current_price"] == 72.5
    assert history[0]["entry_zone"] == "70.00 - 72.00"
    assert history[0]["support"] == 70
    assert history[0]["stop_loss"] == 67.5
    assert history[0]["target_1"] == 78
    assert history[0]["target_2"] == 84
    assert history[0]["target_3"] == 90
    assert history[0]["signal_status"] == "OPEN"
    assert history[0]["price_after_5d"] is None
    assert history[0]["outcome"] is None
    assert signal == history[0]
    assert latest[0]["signal_id"] == history[0]["signal_id"]
    manager.close()


def test_save_screening_run_appends_without_overwriting_previous_runs():
    manager = build_manager()
    candidate = {"ticker": "AAPL", "final_score": 80}

    first = manager.save_screening_run("run-a", [candidate], created_at="2026-07-06T10:00:00+00:00")
    second = manager.save_screening_run("run-b", [candidate], created_at="2026-07-06T11:00:00+00:00")

    assert first == 1
    assert second == 1
    assert len(manager.fetch_screening_history()) == 2
    assert {row["run_id"] for row in manager.fetch_screening_history()} == {"run-a", "run-b"}
    manager.close()


def test_create_update_and_fetch_screening_run():
    manager = build_manager()

    created = manager.create_screening_run(
        run_id="run-1",
        started_at="2026-07-03T10:00:00+00:00",
        tickers_requested=5,
    )
    updated = manager.update_screening_run(
        "run-1",
        status="COMPLETED",
        completed_at="2026-07-03T10:01:00+00:00",
        tickers_processed=5,
        candidate_count=2,
        warnings=["minor warning"],
        errors=[],
    )
    fetched = manager.fetch_screening_run("run-1")

    assert created["status"] == "STARTED"
    assert updated == fetched
    assert fetched["run_id"] == "run-1"
    assert fetched["status"] == "COMPLETED"
    assert fetched["tickers_requested"] == 5
    assert fetched["tickers_processed"] == 5
    assert fetched["candidate_count"] == 2
    assert fetched["warnings"] == ["minor warning"]
    assert fetched["errors"] == []
    manager.close()


def test_fetch_latest_screening_run():
    manager = build_manager()

    manager.create_screening_run("run-1", started_at="2026-07-03T10:00:00+00:00")
    manager.update_screening_run(
        "run-1",
        status="COMPLETED",
        completed_at="2026-07-03T10:01:00+00:00",
    )
    manager.create_screening_run("run-2", started_at="2026-07-03T11:00:00+00:00")
    manager.update_screening_run(
        "run-2",
        status="PARTIAL",
        completed_at="2026-07-03T11:01:00+00:00",
    )

    latest = manager.fetch_latest_screening_run()

    assert latest["run_id"] == "run-2"
    assert latest["status"] == "PARTIAL"
    manager.close()


def test_fetch_screening_run_history_ordering_and_limit():
    manager = build_manager()

    for index in range(4):
        run_id = f"run-{index}"
        manager.create_screening_run(
            run_id,
            started_at=f"2026-07-03T10:0{index}:00+00:00",
        )
        manager.update_screening_run(
            run_id,
            status="COMPLETED",
            completed_at=f"2026-07-03T10:0{index}:30+00:00",
        )

    history = manager.fetch_screening_run_history(limit=3)

    assert [row["run_id"] for row in history] == ["run-3", "run-2", "run-1"]
    manager.close()


def test_screening_run_cancelled_statuses_persist():
    manager = build_manager()

    manager.create_screening_run("cancelled", status="STARTED")
    manager.update_screening_run("cancelled", status="CANCELLED")
    manager.create_screening_run("partial-cancelled", status="STARTED")
    manager.update_screening_run("partial-cancelled", status="PARTIAL_CANCELLED")

    assert manager.fetch_screening_run("cancelled")["status"] == "CANCELLED"
    assert manager.fetch_screening_run("partial-cancelled")["status"] == "PARTIAL_CANCELLED"
    manager.close()


def test_fetch_screening_run_history_supports_limit_and_offset():
    manager = build_manager()

    for index in range(5):
        run_id = f"paged-run-{index}"
        manager.create_screening_run(
            run_id,
            started_at=f"2026-07-03T10:0{index}:00+00:00",
        )
        manager.update_screening_run(
            run_id,
            status="COMPLETED",
            completed_at=f"2026-07-03T10:0{index}:30+00:00",
        )

    page = manager.fetch_screening_run_history(limit=2, offset=1)

    assert [row["run_id"] for row in page] == ["paged-run-3", "paged-run-2"]
    assert manager.count_screening_runs() == 5
    manager.close()
