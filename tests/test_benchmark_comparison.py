from database.manager import DatabaseManager
from services.algorithm_validation_service import BenchmarkComparisonService
from tests.algorithm_validation_test_utils import price_rows, sample_outcome


def test_benchmark_comparison_calculates_alpha_and_hit_rate(tmp_path):
    db = DatabaseManager(tmp_path / "benchmark.db")
    db.upsert_ohlcv("SPY", price_rows(base=100, step=0.2), source="test")
    outcomes = [
        sample_outcome("AAPL", return_20=8),
        sample_outcome("MSFT", return_20=-1),
    ]

    comparison = BenchmarkComparisonService(db).compare(outcomes, "spy", return_window=20)

    assert comparison.benchmark_ticker == "SPY"
    assert comparison.comparisons == 2
    assert comparison.alpha != 0
    assert 0 <= comparison.hit_rate_vs_benchmark <= 1
    assert comparison.warnings == []


def test_benchmark_comparison_missing_data_warns(tmp_path):
    db = DatabaseManager(tmp_path / "benchmark.db")

    comparison = BenchmarkComparisonService(db).compare([sample_outcome()], "SPY")

    assert comparison.comparisons == 0
    assert comparison.warnings == ["No benchmark data available for SPY."]
