from database.manager import DatabaseManager
from services.beta_testing_service import BetaTestRepository, BetaTestRun


def test_beta_test_run_model_and_repository_round_trip(tmp_path):
    db = DatabaseManager(tmp_path / "beta.db")
    run = BetaTestRun(
        run_id="beta-run",
        started_at="2026-01-01T00:00:00+00:00",
        completed_at="2026-01-01T00:01:00+00:00",
        provider="local_csv",
        universe_count=100,
        scanned_count=80,
        candidates_count=12,
        backtest_count=5,
        status="PASS",
        warnings=["warning"],
        errors=[],
    )
    repo = BetaTestRepository(db)

    saved = repo.save(run)
    fetched = db.fetch_beta_test_run("beta-run")
    latest = repo.fetch_latest()
    history = repo.fetch_history()

    assert saved["run_id"] == "beta-run"
    assert fetched["scanned_count"] == 80
    assert fetched["backtest_count"] == 5
    assert latest["provider"] == "local_csv"
    assert history[0]["warnings"] == ["warning"]
    assert repo.clear("beta-run") == 1
    assert db.fetch_beta_test_run("beta-run") is None


def test_beta_test_repository_without_database_is_safe():
    repo = BetaTestRepository(None)

    assert repo.save(object()) is None
    assert repo.fetch_latest() is None
    assert repo.fetch_history() == []
    assert repo.clear("missing") == 0
