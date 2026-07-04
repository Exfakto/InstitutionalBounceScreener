import sqlite3

import pytest

from database.manager import DatabaseManager
from services.strategy_validation_repository import StrategyValidationRepository
from services.strategy_validation_service import StrategyValidationService


def build_manager():
    manager = DatabaseManager.__new__(DatabaseManager)
    manager.connection = sqlite3.connect(":memory:")
    manager.connection.row_factory = sqlite3.Row
    manager.cursor = manager.connection.cursor()
    manager.initialize()
    return manager


def sample(ticker="AAPL", score=95, signal_date="2024-01-01", return_20d=12.0):
    prices = {
        ticker: [
            {"date": "2024-01-01", "close": 90, "high": 90, "low": 90},
            {"date": "2024-01-02", "close": 100, "high": 100, "low": 100},
            {"date": "2024-01-03", "close": 101, "high": 104, "low": 98},
            {"date": "2024-01-04", "close": 102, "high": 105, "low": 97},
            {"date": "2024-01-05", "close": 103, "high": 106, "low": 96},
            {"date": "2024-01-06", "close": 104, "high": 107, "low": 95},
            {"date": "2024-01-07", "close": 105, "high": 108, "low": 94},
        ]
    }
    prices[ticker].extend(
        {"date": f"2024-01-{day:02d}", "close": 100, "high": 100, "low": 100}
        for day in range(8, 22)
    )
    prices[ticker].append(
        {
            "date": "2024-01-22",
            "close": 100 * (1 + return_20d / 100),
            "high": 100 * (1 + return_20d / 100),
            "low": 100,
        }
    )
    candidate = {
        "ticker": ticker,
        "signal_date": signal_date,
        "final_score": score,
    }
    return StrategyValidationService(horizons=(5, 10, 20), primary_horizon=20).validate_sample(
        candidate,
        prices,
    )


def test_strategy_validation_tables_created():
    manager = build_manager()

    manager.cursor.execute("PRAGMA table_info(strategy_validation_runs)")
    run_columns = {row["name"] for row in manager.cursor.fetchall()}
    manager.cursor.execute("PRAGMA table_info(strategy_validation_samples)")
    sample_columns = {row["name"] for row in manager.cursor.fetchall()}

    assert {"id", "created_at", "strategy_name", "universe_size", "sample_count", "notes"}.issubset(run_columns)
    assert {"run_id", "ticker", "screen_date", "score_bucket", "return_20d", "outcome"}.issubset(sample_columns)
    manager.close()


def test_save_and_retrieve_validation_run_and_samples():
    manager = build_manager()
    repository = StrategyValidationRepository(manager)

    run = repository.save_run(
        run_id="run-1",
        strategy_name="Institutional Bounce",
        universe_size=500,
        sample_count=1,
        notes="test run",
    )
    count = repository.save_samples("run-1", [sample()])

    assert run["id"] == "run-1"
    assert run["strategy_name"] == "Institutional Bounce"
    assert count == 1
    rows = repository.get_samples_for_ticker("aapl")
    assert len(rows) == 1
    assert rows[0]["ticker"] == "AAPL"
    assert rows[0]["score_bucket"] == "90-100"
    assert rows[0]["outcome"] == "win"
    manager.close()


def test_empty_database_queries_return_empty_results():
    manager = build_manager()
    repository = StrategyValidationRepository(manager)

    assert repository.get_run("missing") is None
    assert repository.get_recent_runs() == []
    assert repository.get_samples_for_ticker("AAPL") == []
    assert repository.get_samples_for_bucket("90-100") == []
    assert repository.get_samples_by_date_range("2024-01-01", "2024-01-31") == []
    assert repository.get_summary_statistics()["sample_count"] == 0
    manager.close()


def test_duplicate_sample_upserts_instead_of_inserting_duplicate():
    manager = build_manager()
    repository = StrategyValidationRepository(manager)

    repository.save_run("run-dup", "Test", 1, 1)
    repository.save_samples("run-dup", [sample(return_20d=12)])
    repository.save_samples("run-dup", [sample(return_20d=-4)])

    rows = repository.get_samples_for_ticker("AAPL", run_id="run-dup")
    assert len(rows) == 1
    assert rows[0]["return_20d"] == pytest.approx(-4.0)
    assert rows[0]["outcome"] == "loss"
    manager.close()


def test_filtering_by_bucket_and_date_range():
    manager = build_manager()
    repository = StrategyValidationRepository(manager)

    repository.save_run("run-filter", "Test", 3, 3)
    repository.save_samples(
        "run-filter",
        [
            sample("AAA", score=95, signal_date="2024-01-01"),
            sample("BBB", score=82, signal_date="2024-01-03"),
            sample("CCC", score=65, signal_date="2024-01-05"),
        ],
    )

    assert [row["ticker"] for row in repository.get_samples_for_bucket("80-89")] == ["BBB"]
    assert [row["ticker"] for row in repository.get_samples_by_date_range("2024-01-02", "2024-01-05")] == ["BBB", "CCC"]
    manager.close()


def test_summary_statistics_for_run():
    manager = build_manager()
    repository = StrategyValidationRepository(manager)

    repository.save_run("run-summary", "Test", 2, 2)
    repository.save_samples(
        "run-summary",
        [
            sample("AAA", return_20d=10),
            sample("BBB", score=75, return_20d=-5),
        ],
    )

    summary = repository.get_summary_statistics(run_id="run-summary")

    assert summary["sample_count"] == 2
    assert summary["completed_count"] == 2
    assert summary["average_return"] == pytest.approx(2.5)
    assert summary["win_rate"] == pytest.approx(0.5)
    manager.close()
