import sqlite3

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
