from database.manager import DatabaseManager
from services.algorithm_validation_service import OutcomeLabelingService
from tests.algorithm_validation_test_utils import price_rows, sample_signal


def test_outcome_labeling_forward_windows_and_extremes(tmp_path):
    db = DatabaseManager(tmp_path / "outcomes.db")
    db.upsert_ohlcv("AAPL", price_rows(base=100, step=2), source="test")

    outcomes = OutcomeLabelingService(db, profit_target_pct=10, stop_loss_pct=5).label(
        [sample_signal(entry_price=100)],
        windows=[5, 10, 20, 60],
    )

    assert len(outcomes) == 1
    outcome = outcomes[0]
    assert set(outcome.forward_returns) == {"5", "10", "20", "60"}
    assert outcome.forward_returns["20"] > outcome.forward_returns["5"]
    assert outcome.max_gain_pct > 0
    assert outcome.max_drawdown_pct >= 0
    assert outcome.hit_profit_target is True
    assert outcome.hit_stop_loss is False


def test_outcome_labeling_missing_forward_data_is_safe(tmp_path):
    db = DatabaseManager(tmp_path / "outcomes.db")
    db.upsert_ohlcv("MSFT", price_rows(count=10), source="test")

    outcomes = OutcomeLabelingService(db).label(
        [sample_signal(ticker="MSFT", signal_date="2024-03-01")]
    )

    assert len(outcomes) == 1
    assert outcomes[0].forward_returns["20"] is None
    assert outcomes[0].warnings == ["No forward OHLCV rows available."]
