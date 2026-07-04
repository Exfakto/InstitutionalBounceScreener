from datetime import date, timedelta

from database.manager import DatabaseManager
from services.algorithm_validation_service import (
    AlgorithmValidationReportService,
    AlgorithmValidationService,
    BenchmarkComparisonService,
    FactorPerformanceAnalyzer,
    HistoricalSignalReplayService,
    OutcomeLabelingService,
    WeightOptimizationEngine,
)


def price_rows(start="2024-01-01", count=120, base=100.0, step=0.5):
    current = date.fromisoformat(start)
    rows = []
    for index in range(count):
        close = base + index * step
        rows.append(
            {
                "date": current.isoformat(),
                "open": close - 0.2,
                "high": close + 1.0,
                "low": close - 1.0,
                "close": close,
                "volume": 1_000_000 + index * 1000,
            }
        )
        current += timedelta(days=1)
    return rows


def test_historical_replay_uses_only_cached_rows_through_signal_date(tmp_path):
    db = DatabaseManager(tmp_path / "validation.db")
    db.upsert_ohlcv("AAPL", price_rows(), source="test")

    signals, warnings = HistoricalSignalReplayService(db).replay(
        "2024-02-01",
        "2024-03-01",
        tickers=["AAPL"],
        frequency="monthly",
    )

    assert warnings == []
    assert signals
    assert all(signal.signal_date <= "2024-03-01" for signal in signals)
    assert all(signal.entry_price is not None for signal in signals)


def test_outcome_labeling_calculates_forward_returns_and_targets(tmp_path):
    db = DatabaseManager(tmp_path / "validation.db")
    db.upsert_ohlcv("MSFT", price_rows(base=50, step=1.0), source="test")
    signal = HistoricalSignalReplayService.signal_from_history(
        "MSFT",
        date.fromisoformat("2024-02-01"),
        db.fetch_ohlcv("MSFT", end_date="2024-02-01"),
    )

    outcomes = OutcomeLabelingService(db, profit_target_pct=10, stop_loss_pct=5).label(
        [signal],
        windows=[5, 10, 20, 60],
    )

    assert len(outcomes) == 1
    assert outcomes[0].forward_returns["5"] > 0
    assert outcomes[0].hit_profit_target is True
    assert outcomes[0].hit_stop_loss is False


def test_factor_bucket_analysis_and_weight_optimization_are_deterministic(tmp_path):
    db = DatabaseManager(tmp_path / "validation.db")
    db.upsert_ohlcv("NVDA", price_rows(base=100, step=0.8), source="test")
    service = AlgorithmValidationService(db)

    report_a = service.run_validation(
        "2024-02-01",
        "2024-04-01",
        tickers=["NVDA"],
        replay_frequency="weekly",
        max_weight_combinations=3,
        benchmark_ticker="SPY",
    )
    report_b = service.run_validation(
        "2024-02-01",
        "2024-04-01",
        tickers=["NVDA"],
        replay_frequency="weekly",
        max_weight_combinations=3,
        benchmark_ticker="SPY",
    )

    assert report_a.signal_count == report_b.signal_count
    assert report_a.summary_metrics == report_b.summary_metrics
    assert report_a.factor_bucket_results
    assert [result.rank for result in report_a.best_weight_configs] == [1, 2, 3]


def test_benchmark_comparison_warns_when_benchmark_missing(tmp_path):
    db = DatabaseManager(tmp_path / "validation.db")
    db.upsert_ohlcv("AAPL", price_rows(), source="test")
    signal = HistoricalSignalReplayService.signal_from_history(
        "AAPL",
        date.fromisoformat("2024-02-01"),
        db.fetch_ohlcv("AAPL", end_date="2024-02-01"),
    )
    outcome = OutcomeLabelingService(db).label([signal])[0]

    comparison = BenchmarkComparisonService(db).compare([outcome], benchmark_ticker="SPY")

    assert comparison.comparisons == 0
    assert comparison.warnings


def test_validation_persistence_and_export(tmp_path):
    db = DatabaseManager(tmp_path / "validation.db")
    db.upsert_ohlcv("AAPL", price_rows(), source="test")
    report = AlgorithmValidationService(db).run_validation(
        "2024-02-01",
        "2024-03-15",
        tickers=["AAPL"],
        replay_frequency="weekly",
        run_id="validation-test",
    )

    fetched = db.fetch_validation_run("validation-test")
    latest = db.fetch_latest_validation_run()
    history = db.fetch_validation_run_history()
    assert fetched["run_id"] == "validation-test"
    assert fetched["outcomes"]
    assert fetched["best_weight_configs"]
    assert latest["run_id"] == "validation-test"
    assert history[0]["run_id"] == "validation-test"

    result = AlgorithmValidationReportService().export_json(
        report,
        tmp_path / "exports",
        "validation-report",
    )
    assert result["success"] is True
    assert (tmp_path / "exports" / "validation-report.json").exists()

    assert db.clear_validation_run("validation-test") >= 1
    assert db.fetch_validation_run("validation-test") is None


def test_empty_validation_returns_safe_report(tmp_path):
    db = DatabaseManager(tmp_path / "validation.db")

    report = AlgorithmValidationService(db).run_validation(
        "2024-01-01",
        "2024-02-01",
        tickers=[],
    )

    assert report.signal_count == 0
    assert report.summary_metrics["total_signals"] == 0
    assert report.warnings
