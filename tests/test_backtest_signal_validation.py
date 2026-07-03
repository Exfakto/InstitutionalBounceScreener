import sqlite3

from PySide6.QtWidgets import QApplication

from backtesting.signal_validation import (
    BacktestConfig,
    BacktestEngine,
    BacktestMetricsService,
    BacktestSignal,
)
from database.manager import DatabaseManager
from services.results_export_service import ResultsExportService
from ui.widgets.screening_results_panel import ScreeningResultsPanel


def build_manager():
    manager = DatabaseManager.__new__(DatabaseManager)
    manager.connection = sqlite3.connect(":memory:")
    manager.connection.row_factory = sqlite3.Row
    manager.cursor = manager.connection.cursor()
    manager.initialize()
    return manager


def seed_prices(manager, ticker, closes):
    rows = []
    for index, close in enumerate(closes, start=1):
        rows.append(
            {
                "date": f"2026-01-{index:02d}",
                "open": close,
                "high": close * 1.02,
                "low": close * 0.98,
                "close": close,
                "volume": 1000,
            }
        )
    manager.upsert_ohlcv(ticker, rows, source="unit")


def candidate(**overrides):
    data = {
        "ticker": "AAA",
        "created_at": "2026-01-01",
        "price": 100,
        "final_score": 90,
        "grade": "A",
        "confidence_level": "HIGH",
        "setup_label": "Elite Institutional Bounce",
        "source": {"run_id": "screen-run"},
    }
    data.update(overrides)
    return data


def test_backtest_signal_creation_from_ranked_candidate():
    engine = BacktestEngine()
    signals, warnings, rejected, invalid = engine.ranked_candidates_to_signals(
        [candidate()],
        config=BacktestConfig(),
    )

    assert signals == [
        BacktestSignal(
            ticker="AAA",
            signal_date="2026-01-01",
            entry_price=100.0,
            support_zone=None,
            final_score=90.0,
            grade="A",
            confidence_level="HIGH",
            setup_label="Elite Institutional Bounce",
            source_run_id="screen-run",
        )
    ]
    assert warnings == []
    assert rejected == 0
    assert invalid == 0


def test_backtest_profit_target_exit():
    manager = build_manager()
    seed_prices(manager, "AAA", [100, 100, 125])
    engine = BacktestEngine(repository=manager)

    result = engine.run_backtest(
        [candidate()],
        config=BacktestConfig(profit_target_pct=20, stop_loss_pct=8),
        run_id="target-run",
    )

    trade = result.trades[0]
    assert trade.exit_reason == "profit_target"
    assert round(trade.return_pct, 2) == 20.0
    assert trade.entry_date == "2026-01-02"
    manager.close()


def test_backtest_stop_loss_exit():
    manager = build_manager()
    seed_prices(manager, "AAA", [100, 100, 90])
    engine = BacktestEngine(repository=manager)

    result = engine.run_backtest(
        [candidate()],
        config=BacktestConfig(profit_target_pct=20, stop_loss_pct=5),
    )

    trade = result.trades[0]
    assert trade.exit_reason == "stop_loss"
    assert round(trade.return_pct, 2) == -5.0
    manager.close()


def test_backtest_max_holding_exit():
    manager = build_manager()
    seed_prices(manager, "AAA", [100, 100, 101, 102, 103])
    engine = BacktestEngine(repository=manager)

    result = engine.run_backtest(
        [candidate()],
        config=BacktestConfig(profit_target_pct=50, stop_loss_pct=50, max_holding_days=2),
    )

    trade = result.trades[0]
    assert trade.exit_reason == "max_holding_days"
    assert trade.holding_days == 2
    manager.close()


def test_backtest_missing_ohlcv_is_warning_not_crash():
    manager = build_manager()
    result = BacktestEngine(repository=manager).run_backtest([candidate()])

    assert result.trades == []
    assert "AAA: missing OHLCV data" in result.warnings
    assert result.metrics["invalid_signal_count"] == 1
    manager.close()


def test_backtest_metrics_calculation():
    metrics = BacktestMetricsService().calculate(
        [
            type("Trade", (), {"return_pct": 10, "max_drawdown_pct": -2})(),
            type("Trade", (), {"return_pct": -5, "max_drawdown_pct": -8})(),
        ],
        rejected_signal_count=1,
        invalid_signal_count=2,
    )

    assert metrics["total_trades"] == 2
    assert metrics["win_rate"] == 0.5
    assert metrics["average_return"] == 2.5
    assert metrics["profit_factor"] == 2.0
    assert metrics["max_drawdown"] == -8
    assert metrics["rejected_signal_count"] == 1
    assert metrics["invalid_signal_count"] == 2


def test_backtest_persistence_save_fetch_latest_history_and_clear():
    manager = build_manager()
    seed_prices(manager, "AAA", [100, 100, 125])
    result = BacktestEngine(repository=manager).run_backtest(
        [candidate()],
        run_id="persist-run",
    )

    saved = manager.save_backtest_run(result, source_run_id="screen-run")
    latest = manager.fetch_latest_backtest_run()
    history = manager.fetch_backtest_run_history()

    assert saved["run_id"] == "persist-run"
    assert saved["source_run_id"] == "screen-run"
    assert saved["trades"][0]["ticker"] == "AAA"
    assert latest["run_id"] == "persist-run"
    assert history[0]["run_id"] == "persist-run"
    assert manager.clear_backtest_run("persist-run") == 2
    assert manager.fetch_backtest_run("persist-run") is None
    manager.close()


def test_backtest_export_summary_json_and_trades_csv(tmp_path):
    manager = build_manager()
    seed_prices(manager, "AAA", [100, 100, 125])
    result = BacktestEngine(repository=manager).run_backtest(
        [candidate()],
        run_id="export-run",
    )
    service = ResultsExportService()

    summary = service.export_backtest_summary_json(result, tmp_path, "summary")
    trades = service.export_backtest_trades_csv(result.trades, tmp_path, "trades")

    assert summary["success"] is True
    assert trades["success"] is True
    assert "AAA" in (tmp_path / "trades.csv").read_text()
    manager.close()


def test_backtest_panel_ui_construction_and_population():
    app = QApplication.instance() or QApplication([])
    panel = ScreeningResultsPanel()
    manager = build_manager()
    seed_prices(manager, "AAA", [100, 100, 125])
    result = BacktestEngine(repository=manager).run_backtest([candidate()])

    assert panel.run_backtest_button.text() == "Run Backtest"
    assert panel.backtest_min_score_spin.value() == 60

    panel.populate_backtest_results(result)

    assert panel.backtest_trades_table.rowCount() == 1
    assert "1 trades" in panel.backtest_summary_label.text()
    assert app is not None
    manager.close()
