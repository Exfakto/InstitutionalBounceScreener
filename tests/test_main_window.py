from pathlib import Path
from types import SimpleNamespace

import pytest
from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import QApplication, QDockWidget, QHeaderView

from ui import main_window as main_window_module
from ui.main_window import MainWindow


@pytest.fixture(scope="module")
def app():
    application = QApplication.instance()
    if application is None:
        application = QApplication([])
    return application


class FakeMarketController:
    def __init__(self):
        self.stats = {
            "stocks": 0,
            "rows": 0,
            "indicator_rows": 0,
            "support_levels": 0,
            "validated_zones": 0,
        }
        self.market_universe_records = []

    def get_statistics(self):
        return dict(self.stats)

    def update_universe(self):
        return 0, 0

    def get_active_market_universe_records(self):
        return list(self.market_universe_records)

    def download_prices(self):
        return {}, 0

    def close(self):
        pass


class FakeProcessingController:
    def calculate_indicators(self):
        return {
            "tickers": 0,
            "processed": 0,
            "processed_tickers": [],
            "skipped": 0,
            "skipped_tickers": [],
            "rows": 0,
            "elapsed_seconds": 0.0,
        }

    def detect_support(self):
        return {
            "tickers": 0,
            "processed": 0,
            "processed_tickers": [],
            "skipped": 0,
            "skipped_tickers": [],
            "zones": 0,
            "elapsed_seconds": 0.0,
        }

    def validate_bounces(self):
        return {
            "support_levels": 0,
            "processed": 0,
            "processed_tickers": [],
            "skipped": 0,
            "skipped_tickers": [],
            "validated": 0,
            "elapsed_seconds": 0.0,
        }

    def close(self):
        pass


class FakeScoringController:
    def __init__(self):
        self.calls = 0
        self.candidate_sets = []

    def run_screener(self):
        self.calls += 1
        scores = {
            "quality_score": SimpleNamespace(value=90.0),
            "institutional_score": SimpleNamespace(value=76.0),
            "technical_score": SimpleNamespace(value=84.0),
            "support_score": SimpleNamespace(value=91.0),
            "bounce_score": SimpleNamespace(value=80.0),
        }
        candidates = self.candidate_sets.pop(0) if self.candidate_sets else [
            self.make_candidate("AAPL", "Apple Inc.", 91.0, scores)
        ]
        return {
            "candidates": candidates,
            "processed": 1,
            "skipped": 0,
            "elapsed_seconds": 0.1,
        }

    @staticmethod
    def make_candidate(ticker, company_name, score, score_map=None):
        return SimpleNamespace(
            ticker=ticker,
            company_name=company_name,
            primary_score_value=score,
            composite_score=SimpleNamespace(value=score),
            score_map=score_map or {},
            scores=[],
            warnings=[],
        )

    def get_candidate_detail(self, ticker):
        return {}

    def close(self):
        pass


class FakeChartController:
    def get_chart_data(self, ticker):
        return {
            "ticker": ticker,
            "prices": [],
            "indicators": [],
            "support_zones": [],
            "bounce_validations": [],
            "warnings": [],
        }

    def close(self):
        pass


class FakeWatchlistController:
    def get_items(self, status=None):
        return {"success": True, "item": [], "count": 0}

    def get_watchlist_intelligence(self):
        return SimpleNamespace(total_items=0)


class FakeTradeJournalController:
    def get_trades(self):
        return {"success": True, "trades": []}


class FakeMarketStatusService:
    def get_status(self, now=None):
        return SimpleNamespace(status="Closed")


class FakeRefreshScheduler:
    def __init__(self):
        self.refresh_interval = None

    def register_callback(self, callback):
        self.callback = callback

    def set_refresh_interval(self, interval):
        self.refresh_interval = interval

    def start(self):
        pass

    def stop(self):
        pass

    def is_running(self):
        return False

    def clear_tickers(self):
        pass

    def register_ticker(self, ticker):
        pass


class FakeWorkspaceStateService:
    state = {}
    saved_states = []

    def load_state(self):
        return dict(self.state)

    def save_state(self, state):
        self.saved_states.append(state)
        self.state = dict(state)
        return state


class FakeAppSettingsService:
    preferences = SimpleNamespace(
        default_scan_mode="Manual ticker input",
        default_scan_preset="Institutional Quality",
        max_scan_size=250,
        large_scan_warning_threshold=250,
        default_export_directory="exports/results",
        ui_density="NORMAL",
        auto_refresh_results=True,
        show_rejected_candidates=True,
    )

    def get_preferences(self):
        return self.preferences


class FakeScreeningRepository:
    def __init__(self):
        self.ranked_candidates = []
        self.run_history = []
        self.ranked_by_run = {}
        self.runs_by_id = {}
        self.latest_run = None
        self.ranked_calls = 0
        self.history_calls = 0
        self.run_candidate_calls = []

    def fetch_latest_ranked_candidates(self, limit=None, offset=0):
        self.ranked_calls += 1
        return self.page(self.ranked_candidates, limit, offset)

    def fetch_screening_run_history(self, limit=25, offset=0):
        self.history_calls += 1
        return self.page(self.run_history, limit, offset)

    def fetch_ranked_candidates(self, run_id, limit=None, offset=0):
        self.run_candidate_calls.append(run_id)
        return self.page(self.ranked_by_run.get(run_id, []), limit, offset)

    def count_ranked_candidates(self, run_id):
        return len(self.ranked_by_run.get(run_id, []))

    def count_latest_ranked_candidates(self):
        return len(self.ranked_candidates)

    def count_screening_runs(self):
        return len(self.run_history)

    def fetch_screening_run(self, run_id):
        if run_id in self.runs_by_id:
            return self.runs_by_id[run_id]
        for run in self.run_history:
            value = run.get("run_id") if isinstance(run, dict) else getattr(run, "run_id", None)
            if value == run_id:
                return run
        return None

    def fetch_latest_screening_run(self):
        if self.latest_run is not None:
            return self.latest_run
        return self.run_history[0] if self.run_history else None

    @staticmethod
    def page(rows, limit=None, offset=0):
        rows = list(rows or [])
        if limit is None:
            return rows
        return rows[offset:offset + limit]


class FakeResultsExportService:
    def __init__(self):
        self.calls = []
        self.fail = False

    def export_ranked_candidates_csv(self, candidates, output_dir, filename):
        return self.record("csv", candidates, output_dir, filename)

    def export_ranked_candidates_json(self, candidates, output_dir, filename):
        return self.record("json", candidates, output_dir, filename)

    def export_full_run_package(self, run_metadata, candidates, output_dir, filename):
        return self.record("full_package", candidates, output_dir, filename, run_metadata)

    def record(self, kind, candidates, output_dir, filename, run_metadata=None):
        self.calls.append(
            {
                "kind": kind,
                "candidates": list(candidates or []),
                "output_dir": output_dir,
                "filename": filename,
                "run_metadata": run_metadata,
            }
        )
        if self.fail:
            return {
                "success": False,
                "message": "Export failed: planned failure",
                "path": None,
                "count": None,
            }
        return {
            "success": True,
            "message": f"{kind} exported",
            "path": f"C:/tmp/{filename}",
            "count": len(candidates or []),
        }


class FakeScreeningWorker(QObject):
    started_signal = Signal(str)
    progress_signal = Signal(object)
    completed_signal = Signal(object)
    failed_signal = Signal(str)
    cancelled_signal = Signal(object)
    instances = []

    def __init__(self, tickers=None, repository=None, parent=None, **kwargs):
        super().__init__(parent)
        self.tickers = tickers or []
        self.repository = repository
        self.started = False
        self.cancel_requested = False
        FakeScreeningWorker.instances.append(self)

    def request_cancel(self):
        self.cancel_requested = True

    def start(self):
        self.started = True

    def isRunning(self):
        return self.started

    def quit(self):
        self.started = False

    def wait(self, timeout=None):
        return True


@pytest.fixture
def patched_window(monkeypatch, app):
    monkeypatch.setattr(main_window_module, "MarketController", FakeMarketController)
    monkeypatch.setattr(main_window_module, "IndicatorController", FakeProcessingController)
    monkeypatch.setattr(main_window_module, "SupportController", FakeProcessingController)
    monkeypatch.setattr(main_window_module, "BounceController", FakeProcessingController)
    monkeypatch.setattr(main_window_module, "ScoringController", FakeScoringController)
    monkeypatch.setattr(main_window_module, "ChartController", FakeChartController)
    monkeypatch.setattr(main_window_module, "WatchlistController", FakeWatchlistController)
    monkeypatch.setattr(main_window_module, "TradeJournalController", FakeTradeJournalController)
    monkeypatch.setattr(main_window_module, "MarketStatusService", FakeMarketStatusService)
    monkeypatch.setattr(main_window_module, "RefreshScheduler", FakeRefreshScheduler)
    monkeypatch.setattr(main_window_module, "WorkspaceStateService", FakeWorkspaceStateService)
    monkeypatch.setattr(main_window_module, "AppSettingsService", FakeAppSettingsService)
    FakeWorkspaceStateService.state = {}
    FakeWorkspaceStateService.saved_states = []
    FakeAppSettingsService.preferences = SimpleNamespace(
        default_scan_mode="Manual ticker input",
        default_scan_preset="Institutional Quality",
        max_scan_size=250,
        large_scan_warning_threshold=250,
        default_export_directory="exports/results",
        ui_density="NORMAL",
        auto_refresh_results=True,
        show_rejected_candidates=True,
    )

    window = MainWindow()
    yield window
    window.close()


def test_professional_screener_workspace_creation(patched_window):
    window = patched_window

    assert window.dashboard is not None
    assert window.dashboard_controller is not None
    assert window.screening_results_panel is not None
    assert window.pipeline_progress_panel is not None
    assert window.dashboard.activity_feed_table is not None


def test_main_window_responsive_startup_size_and_minimum(patched_window):
    window = patched_window

    assert window.size().width() <= 1280
    assert window.size().height() <= 760
    assert window.minimumWidth() <= 900
    assert window.minimumHeight() <= 620


def test_main_window_key_panels_allow_compact_resizing(patched_window):
    window = patched_window

    assert window.price_chart.minimumWidth() <= 360
    assert window.price_chart.minimumHeight() <= 180
    assert window.candidates_table.minimumWidth() <= 420
    assert window.candidates_table.minimumHeight() <= 220
    assert window.screener_filters_panel.maximumWidth() <= 230
    assert window.dashboard.activity_count() >= 1
    assert window.screener_workspace_splitter.count() == 2
    assert set(window.filter_sections) == {
        "Universe",
        "Fundamentals",
        "Institutional",
        "Technical",
        "Risk",
    }
    assert window.candidates_table.parent() is window.screener_workspace_splitter
    assert window.statusBar() is not None


def test_main_window_dashboard_layout_prioritizes_candidate_workspace(patched_window):
    window = patched_window
    layout = window.centralWidget().layout()

    assert layout.indexOf(window.header_bar) < layout.indexOf(window.kpi_strip)
    assert layout.indexOf(window.kpi_strip) < layout.indexOf(window.operations_toolbar)
    assert layout.indexOf(window.operations_toolbar) < layout.indexOf(
        window.screener_workspace_splitter
    )
    assert layout.indexOf(window.screener_workspace_splitter) < layout.indexOf(
        window.pipeline_progress_panel
    )
    assert layout.indexOf(window.pipeline_progress_panel) < layout.indexOf(window.dashboard)
    assert window.screener_filters_panel.maximumWidth() <= 280
    assert window.candidates_table.minimumWidth() <= 620
    assert window.screener_workspace_splitter.sizes()[1] > (
        window.screener_workspace_splitter.sizes()[0]
    )


def test_main_window_dashboard_starts_with_empty_sections(patched_window):
    window = patched_window

    assert window.dashboard.opportunity_labels["candidates_screened"].text() == "0"
    assert window.dashboard.best_opportunities_table.rowCount() == 0
    assert window.dashboard.best_opportunities_empty.isHidden() is False
    assert window.dashboard.section_frames["institutional_activity"].isHidden() is True
    assert window.dashboard.section_frames["recent_research"].isHidden() is True
    assert window.dashboard.section_frames["backtesting_snapshot"].isHidden() is True


def test_main_window_dashboard_summary_widgets_are_created(patched_window):
    window = patched_window

    assert window.dashboard_summary_panel is not None
    assert set(window.dashboard_summary_labels) == {
        "total_stocks_loaded",
        "stocks_passing_filters",
        "last_refresh_time",
        "database_name",
    }


def test_main_window_candidate_kpi_updates_without_duplicate_cards(patched_window):
    window = patched_window

    initial_card_keys = list(window.kpi_strip.cards)
    window.candidates_by_ticker = {
        "AAPL": SimpleNamespace(ticker="AAPL"),
        "MSFT": SimpleNamespace(ticker="MSFT"),
    }

    window.refresh_candidate_kpi()

    assert window.kpi_strip.value_for("candidates") == "2"
    assert list(window.kpi_strip.cards) == initial_card_keys

    window.candidates_by_ticker = {"NVDA": SimpleNamespace(ticker="NVDA")}
    window.refresh_candidate_kpi()

    assert window.kpi_strip.value_for("candidates") == "1"
    assert list(window.kpi_strip.cards) == initial_card_keys


def test_main_window_update_summary_executes_without_exceptions(patched_window):
    window = patched_window

    window.update_summary()

    assert window.dashboard_summary_labels["total_stocks_loaded"].text() == "0"
    assert window.dashboard_summary_labels["stocks_passing_filters"].text() == "0"


def test_main_window_dashboard_summary_values_change_after_data_updates(
    patched_window,
    monkeypatch,
):
    window = patched_window
    monkeypatch.setattr(
        window.settings_service,
        "load",
        lambda: {"paths": {"database_path": "data/MockDashboard.db"}},
    )
    window.controller.stats = {
        "stocks": 125,
        "rows": 10,
        "indicator_rows": 0,
        "support_levels": 0,
        "validated_zones": 0,
    }
    window.latest_statistics = window.controller.get_statistics()
    window.candidates_by_ticker = {
        "AAPL": SimpleNamespace(ticker="AAPL"),
        "MSFT": SimpleNamespace(ticker="MSFT"),
    }
    window.last_refresh_at = "2026-07-03 12:30:00"

    window.update_summary()

    assert window.dashboard_summary_labels["total_stocks_loaded"].text() == "125"
    assert window.dashboard_summary_labels["stocks_passing_filters"].text() == "2"
    assert window.dashboard_summary_labels["last_refresh_time"].text() == "2026-07-03 12:30:00"
    assert window.dashboard_summary_labels["database_name"].text() == "MockDashboard.db"

    window.controller.stats["stocks"] = 300
    window.latest_statistics = window.controller.get_statistics()
    window.candidates_by_ticker = {"NVDA": SimpleNamespace(ticker="NVDA")}

    window.update_summary()

    assert window.dashboard_summary_labels["total_stocks_loaded"].text() == "300"
    assert window.dashboard_summary_labels["stocks_passing_filters"].text() == "1"


def test_main_window_dashboard_summary_missing_values_show_na(
    patched_window,
    monkeypatch,
):
    window = patched_window
    monkeypatch.setattr(window.settings_service, "load", lambda: {"paths": {}})
    window.latest_statistics = {"stocks": None}
    window.last_refresh_at = None
    window.last_screen_time = None
    window.candidates_by_ticker = {}

    window.update_summary()

    assert window.dashboard_summary_labels["total_stocks_loaded"].text() == "N/A"
    assert window.dashboard_summary_labels["last_refresh_time"].text() == "N/A"
    assert window.dashboard_summary_labels["database_name"].text() == "N/A"


def test_main_window_dashboard_empty_data_shows_empty_message(patched_window):
    window = patched_window
    window.clear_screener_results()

    assert window.dashboard_status_label.text() == "No results available"
    assert window.dashboard_status_label.isHidden() is False
    assert window.candidates_table.rowCount() == 0
    assert window.dashboard.best_opportunities_table.rowCount() == 0


def test_main_window_dashboard_zero_filtered_matches_shows_filter_message(patched_window):
    window = patched_window
    window.controller.market_universe_records = [
        {"ticker": "AAPL", "company_name": "Apple Inc.", "exchange": "NASDAQ"}
    ]
    window.refresh_dashboard_results()
    assert window.candidates_table.rowCount() == 1
    window.apply_screener_filters({"Universe": {"enabled": False}})
    window.controller.market_universe_records = []

    window.refresh_dashboard_results()

    assert window.dashboard_status_label.text() == "No stocks match the current filters"
    assert window.candidates_table.rowCount() == 0
    assert window.dashboard.best_opportunities_table.rowCount() == 0


def test_main_window_dashboard_exception_shows_error_and_clears_stale_rows(
    patched_window,
    monkeypatch,
):
    window = patched_window
    window.controller.market_universe_records = [
        {"ticker": "AAPL", "company_name": "Apple Inc.", "exchange": "NASDAQ"}
    ]
    window.refresh_dashboard_results()
    assert window.candidates_table.rowCount() == 1

    def raise_error():
        raise RuntimeError("load failed")

    monkeypatch.setattr(window.controller, "get_active_market_universe_records", raise_error)
    result = window.refresh_dashboard_results()

    assert result["success"] is False
    assert window.dashboard_status_label.text() == "Unable to load dashboard data"
    assert window.candidates_table.rowCount() == 0
    assert window.dashboard.best_opportunities_table.rowCount() == 0
    assert window.dashboard.activity_entries[-1]["status"] == "error"
    assert window.dashboard.activity_entries[-1]["message"] == "Unable to load dashboard data"


def test_main_window_dashboard_valid_refresh_clears_state_message(patched_window):
    window = patched_window
    window.clear_screener_results(message="Unable to load dashboard data")
    window.controller.market_universe_records = [
        {"ticker": "AAPL", "company_name": "Apple Inc.", "exchange": "NASDAQ"}
    ]

    window.refresh_dashboard_results()

    assert window.dashboard_status_label.isHidden() is True
    assert window.dashboard_status_label.text() == ""
    assert window.candidates_table.rowCount() == 1
    assert window.dashboard.best_opportunities_table.rowCount() == 1


def test_main_window_creates_dock_widgets(patched_window):
    window = patched_window

    assert set(window.workspace_docks) == {
        "chart",
        "research",
        "trade_card",
        "watchlist",
        "activity",
        "portfolio",
        "results",
    }
    assert all(isinstance(dock, QDockWidget) for dock in window.workspace_docks.values())
    assert window.chart_dock.windowTitle() == "Chart"
    assert window.research_dock.windowTitle() == "Research"
    assert window.trade_card_dock.windowTitle() == "Trade Card"
    assert window.watchlist_dock.windowTitle() == "Watchlist"
    assert window.activity_dock.windowTitle() == "Activity"
    assert window.portfolio_dock.windowTitle() == "Portfolio"
    assert window.results_dock.windowTitle() == "Results"


def test_main_window_embeds_existing_widgets_in_docks(patched_window):
    window = patched_window

    assert window.chart_dock.widget() is window.price_chart
    assert window.research_dock.widget() is window.research_preview
    assert window.trade_card_dock.widget() is window.trade_card
    assert window.watchlist_dock.widget() is window.watchlist_panel
    assert window.activity_dock.widget() is window.activity_panel
    assert window.portfolio_dock.widget() is window.performance_dashboard
    assert window.results_dock.widget() is window.screening_results_panel


def test_main_window_toolbar_wiring(patched_window):
    window = patched_window

    assert "run_screener" in window.operations_toolbar.buttons
    assert "save_preset" in window.operations_toolbar.buttons
    assert "load_preset" in window.operations_toolbar.buttons
    assert "reset_filters" in window.operations_toolbar.buttons
    assert "refresh_results" in window.operations_toolbar.buttons


def test_main_window_dashboard_results_table_sorting_enabled(patched_window):
    window = patched_window

    assert window.candidates_table.isSortingEnabled() is True


def test_main_window_dashboard_results_table_expected_headers(patched_window):
    window = patched_window
    headers = [
        window.candidates_table.horizontalHeaderItem(column).text()
        for column in range(window.candidates_table.columnCount())
    ]

    assert headers == [
        "Rank",
        "Ticker",
        "Overall Score",
        "Signal",
        "Quality",
        "Institutional",
        "Technical",
        "Support",
        "Bounce",
        "Distance to Support",
        "Support Strength",
        "Last Bounce",
        "Detail",
    ]
    assert len(headers) == len(set(headers))


def test_main_window_dashboard_results_table_numeric_sort_values(patched_window):
    window = patched_window
    candidates = [
        FakeScoringController.make_candidate("LOW", "Low Corp", 9.0),
        FakeScoringController.make_candidate("HIGH", "High Corp", 100.0),
        FakeScoringController.make_candidate("MID", "Mid Corp", 50.0),
    ]

    window.candidates_table.populate(candidates)
    window.candidates_table.sortItems(2, Qt.AscendingOrder)

    assert window.candidates_table.item(0, 1).text() == "LOW"
    assert window.candidates_table.item(1, 1).text() == "MID"
    assert window.candidates_table.item(2, 1).text() == "HIGH"
    assert window.candidates_table.item(2, 2).data(Qt.UserRole) == 100.0


def test_main_window_preset_actions_update_status(patched_window):
    window = patched_window

    save_result = window.save_screener_preset()
    load_result = window.load_screener_preset()

    assert save_result["success"] is True
    assert load_result["success"] is True
    assert window.active_preset_status.text() == "Active preset: Default"


def test_main_window_run_screen_updates_results_and_status(patched_window):
    window = patched_window

    window.run_screener()

    assert window.scoring_controller.calls == 1
    assert window.candidates_table.rowCount() == 1
    assert window.candidate_count_status.text() == "Candidate count: 1"
    assert "Last screen time: --" not in window.last_screen_time_status.text()
    assert window.dashboard.opportunity_labels["candidates_screened"].text() == "1"
    assert window.dashboard.opportunity_labels["high_conviction"].text() == "1"
    assert window.dashboard.best_opportunities_table.rowCount() == 1
    assert window.dashboard.best_opportunities_table.item(0, 0).text() == "AAPL"
    assert window.dashboard.section_frames["institutional_activity"].isHidden() is False
    assert window.pipeline_progress_panel.status_for("screener") == "Complete"


def test_main_window_dashboard_refresh_handles_missing_data(patched_window):
    window = patched_window
    window.candidates_by_ticker = {"XYZ": SimpleNamespace(ticker="XYZ")}

    window.refresh_dashboard()

    assert window.dashboard.opportunity_labels["candidates_screened"].text() == "1"
    assert window.dashboard.opportunity_labels["average_opportunity_score"].text() == "--"
    assert window.dashboard.best_opportunities_table.item(0, 0).text() == "XYZ"
    assert window.dashboard.best_opportunities_table.item(0, 1).text() == "--"
    assert window.dashboard.section_frames["institutional_activity"].isHidden() is True


def test_main_window_dashboard_clear_reset_behavior(patched_window):
    window = patched_window
    window.run_screener()

    window.dashboard.clear()

    assert window.dashboard.opportunity_labels["candidates_screened"].text() == "0"
    assert window.dashboard.best_opportunities_table.rowCount() == 0
    assert window.dashboard.section_frames["institutional_activity"].isHidden() is True


def test_main_window_refresh_results_reuses_run_screen(patched_window):
    window = patched_window
    window.controller.market_universe_records = [
        {"ticker": "AAPL", "company_name": "Apple Inc.", "exchange": "NASDAQ"}
    ]

    window.refresh_screener_results()
    window.refresh_screener_results()

    assert window.scoring_controller.calls == 0
    assert window.candidates_table.rowCount() == 1


def test_main_window_dashboard_refresh_method_exists(patched_window):
    window = patched_window

    assert callable(window.refresh_dashboard_results)


def test_main_window_dashboard_loads_rows_from_market_universe(patched_window):
    window = patched_window
    window.controller.market_universe_records = [
        {
            "ticker": "MSFT",
            "company_name": "Microsoft Corporation",
            "exchange": "NASDAQ",
            "security_type": "Common Stock",
            "sector": "Technology",
            "industry": "Software Infrastructure",
            "market_cap": 3200000000000,
            "price": 450.0,
            "average_volume": 22000000,
            "average_dollar_volume": 9900000000,
        },
        {
            "ticker": "JPM",
            "company_name": "JPMorgan Chase & Co.",
            "exchange": "NYSE",
            "security_type": "Common Stock",
            "sector": "Financial Services",
            "industry": "Banks Diversified",
        },
    ]

    result = window.refresh_dashboard_results()

    assert result == {"success": True, "records": 2}
    assert window.scoring_controller.calls == 0
    assert window.candidates_table.rowCount() == 2
    assert window.candidates_table.item(0, 1).text() == "MSFT"
    assert window.candidates_table.item(1, 1).text() == "JPM"
    assert window.dashboard.best_opportunities_table.rowCount() == 2
    assert window.dashboard.best_opportunities_table.item(0, 0).text() == "MSFT"
    assert window.dashboard.best_opportunities_table.item(0, 1).text() == "Microsoft Corporation"
    assert window.dashboard_summary_labels["stocks_passing_filters"].text() == "2"


def test_main_window_market_universe_row_selection_updates_research_preview(patched_window):
    window = patched_window
    window.controller.market_universe_records = [
        {
            "ticker": "MSFT",
            "company_name": "Microsoft Corporation",
            "exchange": "NASDAQ",
            "market_cap": 3200000000000,
        }
    ]
    window.refresh_dashboard_results()

    window.candidates_table.selectRow(0)
    window.update_open_detail_state()

    assert window.research_preview.ticker_label.text() == "MSFT"
    assert window.research_preview.signal_label.text() == "Opportunity rating unavailable."
    assert window.research_preview.summary_labels["overall"].text() == "-"
    assert window.research_preview.fundamental_labels["market_cap"].text() == "$3.20T"


def test_main_window_open_detail_uses_candidate_detail_window(
    patched_window,
    monkeypatch,
):
    window = patched_window
    opened = []

    class FakeCandidateDetailWindow:
        def __init__(self, candidate=None, detail=None, parent=None):
            self.candidate = candidate
            self.detail = detail
            self.parent = parent
            self.shown = False
            opened.append(self)

        def show(self):
            self.shown = True

    monkeypatch.setattr(
        main_window_module,
        "CandidateDetailWindow",
        FakeCandidateDetailWindow,
    )
    window.candidates_by_ticker = {
        "AAPL": SimpleNamespace(ticker="AAPL", company_name="Apple Inc.")
    }
    window.candidates_table.populate(list(window.candidates_by_ticker.values()))
    window.candidates_table.selectRow(0)

    window.open_selected_stock_detail()

    assert len(opened) == 1
    assert opened[0].candidate.ticker == "AAPL"
    assert opened[0].shown is True
    assert window.detail_windows[-1] is opened[0]


def test_main_window_open_detail_handles_partial_candidate(
    patched_window,
    monkeypatch,
):
    window = patched_window
    opened = []

    class FakeCandidateDetailWindow:
        def __init__(self, candidate=None, detail=None, parent=None):
            self.candidate = candidate
            opened.append(self)

        def show(self):
            pass

    monkeypatch.setattr(
        main_window_module,
        "CandidateDetailWindow",
        FakeCandidateDetailWindow,
    )
    window.candidates_by_ticker = {"PART": SimpleNamespace(ticker="PART")}
    window.candidates_table.populate(list(window.candidates_by_ticker.values()))
    window.candidates_table.selectRow(0)

    window.open_selected_stock_detail()

    assert opened[0].candidate.ticker == "PART"


def test_main_window_dashboard_empty_market_universe_shows_empty_message(patched_window):
    window = patched_window

    result = window.refresh_dashboard_results()

    assert result == {"success": True, "records": 0}
    assert window.scoring_controller.calls == 0
    assert window.candidates_table.rowCount() == 0
    assert window.dashboard.best_opportunities_table.rowCount() == 0
    assert window.dashboard_status_label.text() == "No results available"
    assert window.dashboard_status_label.isHidden() is False


def test_main_window_screening_results_view_construction(patched_window):
    window = patched_window
    panel = window.screening_results_panel

    ranked_headers = [
        panel.ranked_candidates_table.horizontalHeaderItem(column).text()
        for column in range(panel.ranked_candidates_table.columnCount())
    ]
    history_headers = [
        panel.run_history_table.horizontalHeaderItem(column).text()
        for column in range(panel.run_history_table.columnCount())
    ]

    assert ranked_headers == [
        "Rank",
        "Ticker",
        "Final Score",
        "Grade",
        "Confidence",
        "Setup",
        "Warnings",
        "Rejections",
    ]
    assert history_headers == [
        "Run ID",
        "Status",
        "Started",
        "Completed",
        "Requested",
        "Processed",
        "Candidates",
    ]
    assert window.results_dock.widget() is panel
    assert panel.export_candidates_csv_button.text() == "Export Candidates CSV"
    assert panel.export_candidates_json_button.text() == "Export Candidates JSON"
    assert panel.export_full_run_package_button.text() == (
        "Export Full Run Package JSON"
    )
    assert panel.scroll_area.widgetResizable() is True
    assert panel.scroll_area.horizontalScrollBarPolicy() == Qt.ScrollBarAlwaysOff


def test_main_window_results_tables_have_professional_configuration(patched_window):
    panel = patched_window.screening_results_panel
    ranked = panel.ranked_candidates_table
    history = panel.run_history_table

    assert ranked.alternatingRowColors() is True
    assert ranked.isSortingEnabled() is True
    assert ranked.showGrid() is False
    assert ranked.verticalHeader().defaultSectionSize() >= 30
    assert ranked.horizontalHeader().sectionResizeMode(5) == QHeaderView.Stretch
    assert history.horizontalHeader().sectionResizeMode(0) == QHeaderView.Stretch


def test_main_window_results_status_rendering(patched_window):
    panel = patched_window.screening_results_panel

    panel.set_screening_status("Processing AAPL")
    assert panel.screening_status_label.property("status") == "running"

    panel.set_screening_status("Screening complete")
    assert panel.screening_status_label.property("status") == "success"

    panel.set_screening_status("Unable to load dashboard data")
    assert panel.screening_status_label.property("status") == "error"


def test_main_window_responsive_resize_behavior(patched_window):
    window = patched_window

    window.resize(1180, 720)

    assert window.price_chart.minimumWidth() <= 520
    assert window.candidates_table.minimumWidth() <= 620
    assert window.dashboard.maximumHeight() <= 280


def test_main_window_loads_ranked_candidates_view(patched_window):
    window = patched_window
    repository = FakeScreeningRepository()
    repository.ranked_candidates = [
        SimpleNamespace(
            rank=1,
            ticker="AAPL",
            final_score=91.25,
            grade="A+",
            confidence_level="HIGH",
            setup_label="Elite Institutional Bounce",
            warnings=["Minor"],
            rejection_reasons=[],
        )
    ]
    window._screening_repository = repository

    rows = window.refresh_ranked_candidates_view()
    table = window.screening_results_panel.ranked_candidates_table

    assert rows == repository.ranked_candidates
    assert table.rowCount() == 1
    assert table.item(0, 0).text() == "1"
    assert table.item(0, 1).text() == "AAPL"
    assert table.item(0, 2).text() == "91.25"
    assert table.item(0, 6).text() == "1"
    assert window.screening_results_panel.ranked_empty_label.isHidden() is True


def test_main_window_loads_screening_run_history_view(patched_window):
    window = patched_window
    repository = FakeScreeningRepository()
    repository.run_history = [
        {
            "run_id": "run-1",
            "status": "COMPLETED",
            "started_at": "2026-07-03T10:00:00+00:00",
            "completed_at": "2026-07-03T10:01:00+00:00",
            "tickers_requested": 25,
            "tickers_processed": 25,
            "candidate_count": 4,
        }
    ]
    window._screening_repository = repository

    rows = window.refresh_screening_run_history_view()
    table = window.screening_results_panel.run_history_table

    assert rows == repository.run_history
    assert table.rowCount() == 1
    assert table.item(0, 0).text() == "run-1"
    assert table.item(0, 1).text() == "COMPLETED"
    assert table.item(0, 4).text() == "25"
    assert table.item(0, 6).text() == "4"
    assert window.screening_results_panel.run_history_empty_label.isHidden() is True


def test_main_window_screening_results_refresh_buttons(patched_window):
    window = patched_window
    repository = FakeScreeningRepository()
    repository.ranked_candidates = [
        SimpleNamespace(
            rank=1,
            ticker="MSFT",
            final_score=82.0,
            grade="A",
            confidence_level="HIGH",
            setup_label="High-Quality Bounce",
            warnings=[],
            rejection_reasons=[],
        )
    ]
    repository.run_history = [
        {
            "run_id": "run-refresh",
            "status": "COMPLETED",
            "tickers_requested": 1,
            "tickers_processed": 1,
            "candidate_count": 1,
        }
    ]
    window._screening_repository = repository

    window.screening_results_panel.refresh_ranked_candidates_requested.emit()
    window.screening_results_panel.refresh_run_history_requested.emit()

    assert repository.ranked_calls == 1
    assert repository.history_calls == 1
    assert window.screening_results_panel.ranked_candidates_table.item(0, 1).text() == "MSFT"
    assert window.screening_results_panel.run_history_table.item(0, 0).text() == "run-refresh"


def test_main_window_ranked_candidates_load_incrementally(patched_window):
    window = patched_window
    repository = FakeScreeningRepository()
    window.RESULTS_PAGE_SIZE = 2
    repository.ranked_candidates = [
        SimpleNamespace(rank=1, ticker="AAA", final_score=95),
        SimpleNamespace(rank=2, ticker="BBB", final_score=90),
        SimpleNamespace(rank=3, ticker="CCC", final_score=85),
    ]
    window._screening_repository = repository

    first_page = window.refresh_ranked_candidates_view()
    table = window.screening_results_panel.ranked_candidates_table

    assert [item.ticker for item in first_page] == ["AAA", "BBB"]
    assert table.rowCount() == 2
    assert window.screening_results_panel.ranked_count_label.text() == "Loaded 2 of 3"
    assert window.screening_results_panel.ranked_load_more_button.isEnabled() is True

    window.screening_results_panel.ranked_load_more_button.click()

    assert table.rowCount() == 3
    assert {
        table.item(row, 1).text()
        for row in range(table.rowCount())
    } == {"AAA", "BBB", "CCC"}
    assert window.screening_results_panel.ranked_count_label.text() == "Loaded 3 of 3"
    assert window.screening_results_panel.ranked_load_more_button.isEnabled() is False


def test_main_window_run_history_loads_incrementally(patched_window):
    window = patched_window
    repository = FakeScreeningRepository()
    window.RUN_HISTORY_PAGE_SIZE = 2
    repository.run_history = [
        {"run_id": "run-1", "status": "COMPLETED"},
        {"run_id": "run-2", "status": "COMPLETED"},
        {"run_id": "run-3", "status": "PARTIAL"},
    ]
    window._screening_repository = repository

    first_page = window.refresh_screening_run_history_view()
    table = window.screening_results_panel.run_history_table

    assert [row["run_id"] for row in first_page] == ["run-1", "run-2"]
    assert table.rowCount() == 2
    assert window.screening_results_panel.run_history_count_label.text() == "Loaded 2 of 3"
    assert window.screening_results_panel.run_history_load_more_button.isEnabled() is True

    window.screening_results_panel.run_history_load_more_button.click()

    assert table.rowCount() == 3
    assert {
        table.item(row, 0).text()
        for row in range(table.rowCount())
    } == {"run-1", "run-2", "run-3"}
    assert window.screening_results_panel.run_history_count_label.text() == "Loaded 3 of 3"
    assert window.screening_results_panel.run_history_load_more_button.isEnabled() is False


def test_main_window_screening_results_empty_states(patched_window):
    window = patched_window
    repository = FakeScreeningRepository()
    window._screening_repository = repository

    window.refresh_ranked_candidates_view()
    window.refresh_screening_run_history_view()

    assert window.screening_results_panel.ranked_candidates_table.isHidden() is True
    assert window.screening_results_panel.ranked_empty_label.text() == "No ranked candidates available"
    assert window.screening_results_panel.ranked_empty_label.isHidden() is False
    assert window.screening_results_panel.run_history_table.isHidden() is True
    assert window.screening_results_panel.run_history_empty_label.text() == "No screening runs available"
    assert window.screening_results_panel.run_history_empty_label.isHidden() is False
    assert window.screening_results_panel.export_candidates_csv_button.isEnabled() is False
    assert window.screening_results_panel.export_status_label.text() == "No exportable results"
    assert window.screening_results_panel.ranked_count_label.text() == "Loaded 0 of 0"
    assert window.screening_results_panel.run_history_count_label.text() == "Loaded 0 of 0"


def test_main_window_hides_rejected_candidates_when_setting_disabled(patched_window):
    window = patched_window
    repository = FakeScreeningRepository()
    repository.ranked_candidates = [
        SimpleNamespace(rank=1, ticker="KEEP", final_score=91, grade="A"),
        SimpleNamespace(rank=0, ticker="DROP", final_score=45, grade="REJECT"),
    ]
    window._screening_repository = repository
    window.app_preferences = SimpleNamespace(show_rejected_candidates=False)

    rows = window.refresh_ranked_candidates_view()

    assert [row.ticker for row in rows] == ["KEEP"]
    assert window.screening_results_panel.ranked_candidates_table.rowCount() == 1
    assert window.screening_results_panel.ranked_candidates_table.item(0, 1).text() == "KEEP"


def test_main_window_selected_run_export_uses_selected_candidates(patched_window):
    window = patched_window
    repository = FakeScreeningRepository()
    export_service = FakeResultsExportService()
    repository.run_history = [
        {"run_id": "run-a", "status": "COMPLETED", "candidate_count": 1},
        {"run_id": "run-b", "status": "COMPLETED", "candidate_count": 1},
    ]
    repository.ranked_by_run = {
        "run-b": [
            SimpleNamespace(
                rank=1,
                ticker="MSFT",
                final_score=88.0,
                grade="A",
                confidence_level="HIGH",
                setup_label="High-Quality Bounce",
                explanation=[],
                warnings=[],
                rejection_reasons=[],
            )
        ]
    }
    window._screening_repository = repository
    window._results_export_service = export_service

    window.refresh_screening_run_history_view()
    table = window.screening_results_panel.run_history_table
    run_b_row = next(
        row for row in range(table.rowCount()) if table.item(row, 0).text() == "run-b"
    )
    table.selectRow(run_b_row)
    window.screening_results_panel.export_candidates_csv_button.click()

    assert export_service.calls[-1]["kind"] == "csv"
    assert export_service.calls[-1]["filename"] == "ranked_candidates_run-b"
    assert export_service.calls[-1]["candidates"][0].ticker == "MSFT"
    assert window.screening_results_panel.export_status_label.text().startswith(
        "Export saved:"
    )


def test_main_window_export_falls_back_to_latest_run(patched_window):
    window = patched_window
    repository = FakeScreeningRepository()
    export_service = FakeResultsExportService()
    repository.latest_run = {"run_id": "latest-run", "status": "COMPLETED"}
    repository.ranked_candidates = [
        SimpleNamespace(
            rank=1,
            ticker="AAPL",
            final_score=91.0,
            grade="A+",
            confidence_level="HIGH",
            setup_label="Elite Institutional Bounce",
            explanation=[],
            warnings=[],
            rejection_reasons=[],
        )
    ]
    repository.ranked_by_run = {"latest-run": list(repository.ranked_candidates)}
    window._screening_repository = repository
    window._results_export_service = export_service

    window.refresh_ranked_candidates_view()
    window.screening_results_panel.export_candidates_json_button.click()

    assert export_service.calls[-1]["kind"] == "json"
    assert export_service.calls[-1]["filename"] == "ranked_candidates_latest-run"
    assert export_service.calls[-1]["candidates"][0].ticker == "AAPL"


def test_main_window_export_uses_settings_default_directory(patched_window):
    window = patched_window
    repository = FakeScreeningRepository()
    export_service = FakeResultsExportService()
    repository.latest_run = {"run_id": "settings-export", "status": "COMPLETED"}
    repository.ranked_candidates = [
        SimpleNamespace(rank=1, ticker="AAPL", final_score=91.0)
    ]
    repository.ranked_by_run = {"settings-export": list(repository.ranked_candidates)}
    window._screening_repository = repository
    window._results_export_service = export_service
    window.app_preferences = SimpleNamespace(
        default_scan_mode="Manual ticker input",
        default_scan_preset="Institutional Quality",
        max_scan_size=250,
        large_scan_warning_threshold=250,
        default_export_directory="D:/Exports",
        ui_density="NORMAL",
        auto_refresh_results=True,
        show_rejected_candidates=True,
    )
    window.apply_app_preferences_to_ui()

    window.refresh_ranked_candidates_view()
    window.export_ranked_candidates_csv()

    assert Path(export_service.calls[-1]["output_dir"]) == Path("D:/Exports")


def test_main_window_export_no_data_shows_safe_message(patched_window):
    window = patched_window
    repository = FakeScreeningRepository()
    export_service = FakeResultsExportService()
    window._screening_repository = repository
    window._results_export_service = export_service

    result = window.export_ranked_candidates_csv()

    assert result["success"] is False
    assert result["message"] == "No screening run available."
    assert export_service.calls == []
    assert window.screening_results_panel.export_status_label.text() == (
        "No screening run available."
    )


def test_main_window_json_export_button_calls_service(patched_window):
    window = patched_window
    repository = FakeScreeningRepository()
    export_service = FakeResultsExportService()
    repository.latest_run = {"run_id": "json-run", "status": "COMPLETED"}
    repository.ranked_candidates = [
        SimpleNamespace(rank=1, ticker="NVDA", final_score=95.0)
    ]
    repository.ranked_by_run = {"json-run": list(repository.ranked_candidates)}
    window._screening_repository = repository
    window._results_export_service = export_service

    window.refresh_ranked_candidates_view()
    window.screening_results_panel.export_candidates_json_button.click()

    assert export_service.calls[-1]["kind"] == "json"


def test_main_window_full_package_export_button_calls_service(patched_window):
    window = patched_window
    repository = FakeScreeningRepository()
    export_service = FakeResultsExportService()
    repository.latest_run = {"run_id": "package-run", "status": "COMPLETED"}
    repository.ranked_candidates = [
        SimpleNamespace(rank=1, ticker="TSLA", final_score=81.0)
    ]
    repository.ranked_by_run = {"package-run": list(repository.ranked_candidates)}
    window._screening_repository = repository
    window._results_export_service = export_service

    window.refresh_ranked_candidates_view()
    window.screening_results_panel.export_full_run_package_button.click()

    assert export_service.calls[-1]["kind"] == "full_package"
    assert export_service.calls[-1]["run_metadata"]["run_id"] == "package-run"


def test_main_window_export_failure_message_handling(patched_window):
    window = patched_window
    repository = FakeScreeningRepository()
    export_service = FakeResultsExportService()
    export_service.fail = True
    repository.latest_run = {"run_id": "fail-run", "status": "COMPLETED"}
    repository.ranked_candidates = [
        SimpleNamespace(rank=1, ticker="AMD", final_score=79.0)
    ]
    repository.ranked_by_run = {"fail-run": list(repository.ranked_candidates)}
    window._screening_repository = repository
    window._results_export_service = export_service

    window.refresh_ranked_candidates_view()
    result = window.export_ranked_candidates_csv()

    assert result["success"] is False
    assert window.screening_results_panel.export_status_label.text() == (
        "Export failed: planned failure"
    )


def test_main_window_run_selection_loads_correct_candidates(patched_window):
    window = patched_window
    repository = FakeScreeningRepository()
    repository.run_history = [
        {
            "run_id": "run-a",
            "status": "COMPLETED",
            "started_at": "2026-07-03T10:00:00+00:00",
            "completed_at": "2026-07-03T10:01:00+00:00",
            "tickers_requested": 2,
            "tickers_processed": 2,
            "candidate_count": 1,
            "warnings": [],
            "errors": [],
        },
        {
            "run_id": "run-b",
            "status": "PARTIAL",
            "tickers_requested": 2,
            "tickers_processed": 1,
            "candidate_count": 1,
            "warnings": ["run warning"],
            "errors": ["BAD: support failed"],
        },
    ]
    repository.ranked_by_run = {
        "run-b": [
            SimpleNamespace(
                rank=1,
                ticker="MSFT",
                final_score=88.0,
                grade="A",
                confidence_level="HIGH",
                setup_label="High-Quality Bounce",
                explanation=["Strong setup"],
                warnings=[],
                rejection_reasons=[],
            )
        ]
    }
    window._screening_repository = repository

    window.refresh_screening_run_history_view()
    table = window.screening_results_panel.run_history_table
    run_b_row = next(
        row for row in range(table.rowCount()) if table.item(row, 0).text() == "run-b"
    )
    table.selectRow(run_b_row)

    assert repository.run_candidate_calls == ["run-b"]
    assert window.screening_results_panel.ranked_candidates_table.rowCount() == 1
    assert window.screening_results_panel.ranked_candidates_table.item(0, 1).text() == "MSFT"
    assert window.screening_results_panel.run_detail_labels["run_id"].text() == "run-b"
    assert window.screening_results_panel.run_detail_labels["warnings"].text() == "run warning"
    assert window.screening_results_panel.run_detail_labels["errors"].text() == "BAD: support failed"


def test_main_window_candidate_selection_loads_detail_panel(patched_window):
    window = patched_window
    repository = FakeScreeningRepository()
    repository.ranked_candidates = [
        SimpleNamespace(
            rank=2,
            ticker="NVDA",
            final_score=94.5,
            grade="A+",
            confidence_level="HIGH",
            setup_label="Elite Institutional Bounce",
            explanation=["Support quality is strong", "Institutional sponsorship is strong"],
            warnings=["Minor warning"],
            rejection_reasons=[],
        )
    ]
    window._screening_repository = repository

    window.refresh_ranked_candidates_view()
    window.screening_results_panel.ranked_candidates_table.selectRow(0)

    labels = window.screening_results_panel.candidate_detail_labels
    assert labels["ticker"].text() == "NVDA"
    assert labels["rank"].text() == "2"
    assert labels["final_score"].text() == "94.50"
    assert labels["grade"].text() == "A+"
    assert labels["confidence_level"].text() == "HIGH"
    assert labels["setup_label"].text() == "Elite Institutional Bounce"
    assert "Support quality is strong" in labels["explanation"].text()
    assert labels["warnings"].text() == "Minor warning"
    assert labels["rejection_reasons"].text() == "N/A"
    assert window.screening_results_panel.candidate_detail_empty_label.isHidden() is True
    assert (
        window.screening_results_panel.candidate_chart_panel.overlay_labels[
            "ticker"
        ].text()
        == "NVDA"
    )


def test_main_window_candidate_selection_updates_chart_panel(patched_window):
    window = patched_window
    repository = FakeScreeningRepository()
    repository.ranked_candidates = [
        SimpleNamespace(
            rank=1,
            ticker="AAPL",
            final_score=91.0,
            grade="A+",
            confidence_level="HIGH",
            setup_label="Elite Institutional Bounce",
            explanation=["Strong institutional support"],
            warnings=[],
            rejection_reasons=[],
        )
    ]
    window._screening_repository = repository

    window.refresh_ranked_candidates_view()
    window.screening_results_panel.ranked_candidates_table.selectRow(0)

    chart_panel = window.screening_results_panel.candidate_chart_panel
    assert chart_panel.empty_label.isHidden() is True
    assert chart_panel.overlay_labels["ticker"].text() == "AAPL"
    assert "91.00" in chart_panel.overlay_labels["candidate_score"].text()
    assert "Missing price history" in chart_panel.overlay_labels["warnings"].text()


def test_main_window_candidate_chart_panel_empty_state(patched_window):
    window = patched_window
    chart_panel = window.screening_results_panel.candidate_chart_panel

    assert chart_panel.empty_label.isHidden() is False
    assert chart_panel.content.isHidden() is True
    assert chart_panel.empty_label.text() == "Select a candidate to view chart context."


def test_main_window_candidate_chart_panel_is_compact_resizable(patched_window):
    panel = patched_window.screening_results_panel.candidate_chart_panel

    assert panel.minimumWidth() <= 0
    assert panel.maximumWidth() > 1000


def test_main_window_results_warning_and_error_display(patched_window):
    window = patched_window
    repository = FakeScreeningRepository()
    repository.run_history = [
        {
            "run_id": "warn-run",
            "status": "PARTIAL",
            "warnings": ["No price history", "Missing technical data"],
            "errors": ["BAD: support failed"],
        }
    ]
    repository.ranked_by_run = {
        "warn-run": [
            SimpleNamespace(
                rank=0,
                ticker="BAD",
                final_score=45.0,
                grade="REJECT",
                confidence_level="LOW",
                setup_label="Rejected",
                explanation=["Limited evidence"],
                warnings=["Missing institutional data"],
                rejection_reasons=["Low confidence candidates are rejected"],
            )
        ]
    }
    window._screening_repository = repository

    window.refresh_screening_run_history_view()
    window.screening_results_panel.run_history_table.selectRow(0)
    window.screening_results_panel.ranked_candidates_table.selectRow(0)

    assert "No price history" in window.screening_results_panel.run_detail_labels["warnings"].text()
    assert "BAD: support failed" in window.screening_results_panel.run_detail_labels["errors"].text()
    assert window.screening_results_panel.candidate_detail_labels["warnings"].text() == "Missing institutional data"
    assert (
        window.screening_results_panel.candidate_detail_labels["rejection_reasons"].text()
        == "Low confidence candidates are rejected"
    )


def test_main_window_empty_run_behavior(patched_window):
    window = patched_window
    repository = FakeScreeningRepository()
    repository.run_history = [
        {
            "run_id": "empty-candidates",
            "status": "COMPLETED",
            "candidate_count": 0,
            "warnings": [],
            "errors": [],
        }
    ]
    window._screening_repository = repository

    window.refresh_screening_run_history_view()
    window.screening_results_panel.run_history_table.selectRow(0)

    assert window.screening_results_panel.ranked_candidates_table.isHidden() is True
    assert window.screening_results_panel.ranked_empty_label.text() == "Run has no candidates"
    assert window.screening_results_panel.ranked_empty_label.isHidden() is False
    assert window.screening_results_panel.candidate_detail_empty_label.text() == "No selected candidate"


def test_main_window_no_selected_candidate_behavior(patched_window):
    window = patched_window
    repository = FakeScreeningRepository()
    repository.ranked_candidates = [
        SimpleNamespace(
            rank=1,
            ticker="AAPL",
            final_score=91.0,
            grade="A+",
            confidence_level="HIGH",
            setup_label="Elite Institutional Bounce",
            explanation=[],
            warnings=[],
            rejection_reasons=[],
        )
    ]
    window._screening_repository = repository

    window.refresh_ranked_candidates_view()
    window.screening_results_panel.ranked_candidates_table.clearSelection()

    assert window.screening_results_panel.candidate_detail_empty_label.text() == "No selected candidate"
    assert window.screening_results_panel.candidate_detail_empty_label.isHidden() is False
    assert window.screening_results_panel.candidate_detail_content.isHidden() is True


def test_main_window_screening_ticker_parsing(patched_window):
    window = patched_window

    assert window.parse_screening_tickers(" aapl, msft, AAPL,, nvda ") == [
        "AAPL",
        "MSFT",
        "NVDA",
    ]


def test_main_window_manual_screening_mode_still_uses_ticker_input(
    patched_window,
    monkeypatch,
):
    window = patched_window
    FakeScreeningWorker.instances = []
    monkeypatch.setattr(main_window_module, "ScreeningWorker", FakeScreeningWorker)
    window.controller.market_universe_records = [{"ticker": "SHOULDNOTUSE"}]
    window.screening_results_panel.screening_mode_combo.setCurrentText(
        "Manual ticker input"
    )

    window.start_screening_from_input("aapl, msft")

    assert window.screening_results_panel.ticker_input.isEnabled() is True
    assert FakeScreeningWorker.instances[0].tickers == ["AAPL", "MSFT"]


def test_main_window_universe_mode_disables_ticker_input_and_shows_count(
    patched_window,
):
    window = patched_window
    window.controller.market_universe_records = [
        {
            "ticker": "aapl",
            "market_cap": 5_000_000_000,
            "price": 25,
            "average_volume": 800_000,
            "average_dollar_volume": 20_000_000,
            "exchange": "NASDAQ",
            "security_type": "Common Stock",
        },
        {
            "ticker": "msft",
            "market_cap": 5_000_000_000,
            "price": 25,
            "average_volume": 800_000,
            "average_dollar_volume": 20_000_000,
            "exchange": "NASDAQ",
            "security_type": "Common Stock",
        },
    ]

    window.screening_results_panel.screening_mode_combo.setCurrentText(
        "Universe scan mode"
    )

    assert window.screening_results_panel.ticker_input.isEnabled() is False
    assert window.screening_results_panel.universe_count_label.text() == "Universe: 2"
    assert window.screening_results_panel.screening_status_label.text() == (
        "Universe scan ready: 2 ticker(s)"
    )


def test_main_window_universe_scan_mode_uses_adapter_tickers(
    patched_window,
    monkeypatch,
):
    window = patched_window
    FakeScreeningWorker.instances = []
    monkeypatch.setattr(main_window_module, "ScreeningWorker", FakeScreeningWorker)
    window.controller.market_universe_records = [
        {
            "ticker": "aapl",
            "market_cap": 5_000_000_000,
            "price": 25,
            "average_volume": 800_000,
            "average_dollar_volume": 20_000_000,
            "exchange": "NASDAQ",
            "security_type": "Common Stock",
        },
        {
            "ticker": "AAPL",
            "market_cap": 5_000_000_000,
            "price": 25,
            "average_volume": 800_000,
            "average_dollar_volume": 20_000_000,
            "exchange": "NASDAQ",
            "security_type": "Common Stock",
        },
        {
            "ticker": "nvda",
            "market_cap": 5_000_000_000,
            "price": 25,
            "average_volume": 800_000,
            "average_dollar_volume": 20_000_000,
            "exchange": "NASDAQ",
            "security_type": "Common Stock",
        },
    ]
    window.screening_results_panel.ticker_input.setText("manual")
    window.screening_results_panel.screening_mode_combo.setCurrentText(
        "Universe scan mode"
    )

    window.start_screening_from_input()

    assert FakeScreeningWorker.instances[0].tickers == ["AAPL", "NVDA"]


def test_main_window_universe_scan_empty_universe_shows_safe_message(
    patched_window,
    monkeypatch,
):
    window = patched_window
    FakeScreeningWorker.instances = []
    monkeypatch.setattr(main_window_module, "ScreeningWorker", FakeScreeningWorker)
    window.controller.market_universe_records = []
    window.screening_results_panel.screening_mode_combo.setCurrentText(
        "Universe scan mode"
    )

    worker = window.start_screening_from_input()

    assert worker is None
    assert FakeScreeningWorker.instances == []
    assert window.screening_results_panel.screening_status_label.text() == (
        "No eligible tickers"
    )


def test_main_window_universe_scan_max_ticker_limit_behavior(
    patched_window,
    monkeypatch,
):
    window = patched_window
    FakeScreeningWorker.instances = []
    monkeypatch.setattr(main_window_module, "ScreeningWorker", FakeScreeningWorker)
    window.MAX_UNIVERSE_SCAN_TICKERS = 3
    window.app_preferences = SimpleNamespace(
        max_scan_size=3,
        large_scan_warning_threshold=3,
    )
    window.controller.market_universe_records = [
        {
            "ticker": f"T{i}",
            "market_cap": 5_000_000_000,
            "price": 25,
            "average_volume": 800_000,
            "average_dollar_volume": 20_000_000,
            "exchange": "NASDAQ",
            "security_type": "Common Stock",
        }
        for i in range(5)
    ]
    window.screening_results_panel.screening_mode_combo.setCurrentText(
        "Universe scan mode"
    )

    window.start_screening_from_input()

    assert FakeScreeningWorker.instances[0].tickers == ["T0", "T1", "T2"]
    assert window.screening_results_panel.screening_status_label.text() == (
        "Large scan limited to 3 ticker(s)"
    )


def test_main_window_scan_settings_warning_threshold(patched_window):
    window = patched_window
    window.app_preferences = SimpleNamespace(
        max_scan_size=10,
        large_scan_warning_threshold=3,
    )

    tickers = window.apply_screening_ticker_guardrails(["A", "B", "C"])

    assert tickers == ["A", "B", "C"]
    assert window.screening_results_panel.screening_status_label.text() == (
        "Large scan warning: 3 ticker(s)"
    )


def test_main_window_scan_preset_dropdown_behavior(patched_window):
    window = patched_window
    combo = window.screening_results_panel.scan_preset_combo

    names = [combo.itemText(index) for index in range(combo.count())]

    assert names == [
        "Institutional Quality",
        "Liquid Large Cap",
        "Growth Bounce Watchlist",
        "Conservative Quality",
    ]
    combo.setCurrentText("Liquid Large Cap")
    assert "Liquid Large Cap" in window.screening_results_panel.preset_description_label.text()


def test_main_window_scan_filter_summary_text(patched_window):
    window = patched_window
    window.screening_results_panel.scan_preset_combo.setCurrentText("Conservative Quality")

    summary = window.screening_results_panel.active_filter_summary_label.text()

    assert "Market cap >= 5B" in summary
    assert "Price >= $15" in summary
    assert "Exchanges: NYSE, NASDAQ" in summary
    assert "Types: Common Stock" in summary


def test_main_window_ticker_count_refreshes_after_preset_change(patched_window):
    window = patched_window
    window.controller.market_universe_records = [
        {
            "ticker": "BIG",
            "market_cap": 20_000_000_000,
            "price": 100,
            "average_volume": 2_000_000,
            "average_dollar_volume": 200_000_000,
            "exchange": "NASDAQ",
            "security_type": "Common Stock",
        },
        {
            "ticker": "SMALL",
            "market_cap": 2_000_000_000,
            "price": 7,
            "average_volume": 400_000,
            "average_dollar_volume": 6_000_000,
            "exchange": "NASDAQ",
            "security_type": "Common Stock",
        },
    ]
    panel = window.screening_results_panel
    panel.screening_mode_combo.setCurrentText("Universe scan mode")
    panel.scan_preset_combo.setCurrentText("Growth Bounce Watchlist")

    assert panel.universe_count_label.text() == "Universe: 2"

    panel.scan_preset_combo.setCurrentText("Liquid Large Cap")

    assert panel.universe_count_label.text() == "Universe: 1"
    assert panel.screening_status_label.text() == "Universe scan ready: 1 ticker(s)"


def test_main_window_run_screening_button_starts_worker(
    patched_window,
    monkeypatch,
):
    window = patched_window
    FakeScreeningWorker.instances = []
    repository = FakeScreeningRepository()
    window._screening_repository = repository
    monkeypatch.setattr(main_window_module, "ScreeningWorker", FakeScreeningWorker)

    window.screening_results_panel.ticker_input.setText("aapl, msft")
    window.screening_results_panel.run_screening_button.click()

    assert len(FakeScreeningWorker.instances) == 1
    assert FakeScreeningWorker.instances[0].tickers == ["AAPL", "MSFT"]
    assert FakeScreeningWorker.instances[0].repository is repository
    assert FakeScreeningWorker.instances[0].started is True


def test_main_window_run_screening_button_disabled_during_run(
    patched_window,
    monkeypatch,
):
    window = patched_window
    FakeScreeningWorker.instances = []
    monkeypatch.setattr(main_window_module, "ScreeningWorker", FakeScreeningWorker)

    window.start_screening_from_input("AAPL")

    assert window.screening_results_panel.run_screening_button.isEnabled() is False
    assert window.screening_results_panel.screening_status_label.text().startswith(
        "Starting screening"
    )
    assert window.screening_results_panel.cancel_screening_button.isEnabled() is True


def test_main_window_screening_progress_updates_status(
    patched_window,
    monkeypatch,
):
    window = patched_window
    FakeScreeningWorker.instances = []
    monkeypatch.setattr(main_window_module, "ScreeningWorker", FakeScreeningWorker)

    worker = window.start_screening_from_input("AAPL,MSFT")
    worker.progress_signal.emit(
        {
            "total_tickers": 2,
            "processed_tickers": 1,
            "current_ticker": "MSFT",
            "progress_percentage": 50,
            "status_message": "Processing MSFT",
        }
    )

    assert window.screening_results_panel.screening_status_label.text() == (
        "Processing MSFT (1/2, 50%, current: MSFT)"
    )


def test_main_window_cancel_screening_requests_worker_cancel(
    patched_window,
    monkeypatch,
):
    window = patched_window
    FakeScreeningWorker.instances = []
    monkeypatch.setattr(main_window_module, "ScreeningWorker", FakeScreeningWorker)

    worker = window.start_screening_from_input("AAPL")
    result = window.cancel_screening()

    assert result is True
    assert worker.cancel_requested is True
    assert window.screening_results_panel.screening_status_label.text() == "Cancellation requested"
    assert window.screening_results_panel.cancel_screening_button.isEnabled() is False


def test_main_window_screening_completion_refreshes_results(
    patched_window,
    monkeypatch,
):
    window = patched_window
    FakeScreeningWorker.instances = []
    repository = FakeScreeningRepository()
    repository.ranked_candidates = [
        SimpleNamespace(
            rank=1,
            ticker="AAPL",
            final_score=91,
            grade="A+",
            confidence_level="HIGH",
            setup_label="Elite Institutional Bounce",
            explanation=[],
            warnings=[],
            rejection_reasons=[],
        )
    ]
    repository.run_history = [
        {
            "run_id": "run-complete",
            "status": "COMPLETED",
            "tickers_requested": 1,
            "tickers_processed": 1,
            "candidate_count": 1,
        }
    ]
    window._screening_repository = repository
    monkeypatch.setattr(main_window_module, "ScreeningWorker", FakeScreeningWorker)

    worker = window.start_screening_from_input("AAPL")
    worker.completed_signal.emit(SimpleNamespace(ranked_candidates=repository.ranked_candidates))

    assert window.screening_results_panel.run_screening_button.isEnabled() is True
    assert window.screening_results_panel.screening_status_label.text() == (
        "Screening complete: 1 ranked candidate(s)"
    )
    assert window.screening_results_panel.ranked_candidates_table.item(0, 1).text() == "AAPL"
    assert window.screening_results_panel.run_history_table.item(0, 0).text() == "run-complete"
    assert repository.ranked_calls == 1
    assert repository.history_calls == 1


def test_main_window_auto_refresh_results_setting_can_disable_refresh(
    patched_window,
    monkeypatch,
):
    window = patched_window
    FakeScreeningWorker.instances = []
    repository = FakeScreeningRepository()
    repository.ranked_candidates = [SimpleNamespace(rank=1, ticker="AAPL")]
    repository.run_history = [{"run_id": "no-refresh", "status": "COMPLETED"}]
    window._screening_repository = repository
    window.app_preferences = SimpleNamespace(auto_refresh_results=False)
    monkeypatch.setattr(main_window_module, "ScreeningWorker", FakeScreeningWorker)

    worker = window.start_screening_from_input("AAPL")
    worker.completed_signal.emit(SimpleNamespace(ranked_candidates=repository.ranked_candidates))

    assert repository.ranked_calls == 0
    assert repository.history_calls == 0
    assert window.screening_results_panel.screening_status_label.text() == (
        "Screening complete: 1 ranked candidate(s)"
    )


def test_main_window_screening_cancel_resets_ui_and_refreshes_results(
    patched_window,
    monkeypatch,
):
    window = patched_window
    FakeScreeningWorker.instances = []
    repository = FakeScreeningRepository()
    repository.run_history = [
        {
            "run_id": "cancel-run",
            "status": "PARTIAL_CANCELLED",
            "tickers_requested": 2,
            "tickers_processed": 1,
            "candidate_count": 1,
        }
    ]
    repository.ranked_candidates = [
        SimpleNamespace(
            rank=1,
            ticker="AAPL",
            final_score=80,
            grade="A",
            confidence_level="HIGH",
            setup_label="High-Quality Bounce",
            explanation=[],
            warnings=[],
            rejection_reasons=[],
        )
    ]
    window._screening_repository = repository
    monkeypatch.setattr(main_window_module, "ScreeningWorker", FakeScreeningWorker)

    worker = window.start_screening_from_input("AAPL,MSFT")
    worker.cancelled_signal.emit(
        SimpleNamespace(status="PARTIAL_CANCELLED", ranked_candidates=repository.ranked_candidates)
    )

    assert window.screening_results_panel.run_screening_button.isEnabled() is True
    assert window.screening_results_panel.cancel_screening_button.isEnabled() is False
    assert window.screening_results_panel.screening_status_label.text() == (
        "Screening cancelled: 1 ranked candidate(s)"
    )
    assert window.screening_worker is None
    assert window.screening_results_panel.run_history_table.item(0, 1).text() == "PARTIAL_CANCELLED"
    assert window.screening_results_panel.ranked_candidates_table.item(0, 1).text() == "AAPL"


def test_main_window_screening_failure_shows_safe_error_state(
    patched_window,
    monkeypatch,
):
    window = patched_window
    FakeScreeningWorker.instances = []
    monkeypatch.setattr(main_window_module, "ScreeningWorker", FakeScreeningWorker)

    worker = window.start_screening_from_input("AAPL")
    worker.failed_signal.emit("planned failure")

    assert window.screening_results_panel.run_screening_button.isEnabled() is True
    assert window.screening_results_panel.cancel_screening_button.isEnabled() is False
    assert window.screening_results_panel.screening_status_label.text() == (
        "Screening failed: planned failure"
    )
    assert window.screening_worker is None


def test_main_window_dashboard_refresh_clears_old_rows_before_loading_new_rows(patched_window):
    window = patched_window
    old_records = [
        {"ticker": "OLD1", "company_name": "Old One", "exchange": "NYSE"},
        {"ticker": "OLD2", "company_name": "Old Two", "exchange": "NASDAQ"},
    ]
    new_records = [
        {"ticker": "NEW", "company_name": "New Corp", "exchange": "NYSE"}
    ]

    window.controller.market_universe_records = old_records
    window.refresh_dashboard_results()
    assert window.candidates_table.rowCount() == 2
    assert window.dashboard.best_opportunities_table.rowCount() == 2

    window.controller.market_universe_records = new_records
    window.refresh_dashboard_results()

    assert window.candidates_table.rowCount() == 1
    assert window.candidates_table.item(0, 1).text() == "NEW"
    assert window.dashboard.best_opportunities_table.rowCount() == 1
    assert window.dashboard.best_opportunities_table.item(0, 0).text() == "NEW"


def test_main_window_refresh_results_action_is_wired_to_dashboard_refresh(patched_window):
    window = patched_window
    window.controller.market_universe_records = [
        {"ticker": "AAPL", "company_name": "Apple Inc.", "exchange": "NASDAQ"}
    ]

    window.operations_toolbar.buttons["refresh_results"].click()

    assert window.scoring_controller.calls == 0
    assert window.candidates_table.rowCount() == 1
    assert window.dashboard.best_opportunities_table.rowCount() == 1


def test_main_window_reset_clears_results_and_filters(patched_window):
    window = patched_window
    window.run_screener()

    result = window.reset_screener_filters()

    assert result["success"] is True
    assert window.candidates_table.rowCount() == 0
    assert window.dashboard.best_opportunities_table.rowCount() == 0
    assert window.candidate_count_status.text() == "Candidate count: 0"
    assert window.active_preset_status.text() == "Active preset: --"


def test_main_window_no_duplicate_core_widgets(patched_window):
    window = patched_window

    assert window.findChildren(type(window.candidates_table)).count(window.candidates_table) == 1
    assert window.findChildren(type(window.research_preview)).count(window.research_preview) == 1
    assert window.findChildren(type(window.trade_card)).count(window.trade_card) == 1


def test_main_window_restores_workspace_state(monkeypatch, app):
    monkeypatch.setattr(main_window_module, "MarketController", FakeMarketController)
    monkeypatch.setattr(main_window_module, "IndicatorController", FakeProcessingController)
    monkeypatch.setattr(main_window_module, "SupportController", FakeProcessingController)
    monkeypatch.setattr(main_window_module, "BounceController", FakeProcessingController)
    monkeypatch.setattr(main_window_module, "ScoringController", FakeScoringController)
    monkeypatch.setattr(main_window_module, "ChartController", FakeChartController)
    monkeypatch.setattr(main_window_module, "WatchlistController", FakeWatchlistController)
    monkeypatch.setattr(main_window_module, "TradeJournalController", FakeTradeJournalController)
    monkeypatch.setattr(main_window_module, "MarketStatusService", FakeMarketStatusService)
    monkeypatch.setattr(main_window_module, "RefreshScheduler", FakeRefreshScheduler)
    monkeypatch.setattr(main_window_module, "WorkspaceStateService", FakeWorkspaceStateService)
    FakeWorkspaceStateService.saved_states = []
    FakeWorkspaceStateService.state = {
        "window": {"size": [1100, 700], "position": [30, 40], "maximized": False},
        "splitters": {
            "workspace_splitter": [500, 200],
            "bottom_splitter": [700, 300],
        },
        "active_workspace": "Research",
        "active_screener_preset": "Momentum",
    }

    window = MainWindow()

    try:
        assert window.size().width() == 1100
        assert window.size().height() == 700
        assert window.research_dock.windowTitle() == "Research"
        assert window.active_preset_status.text() == "Active preset: Momentum"
    finally:
        window.close()


def test_main_window_saves_workspace_state_on_close(patched_window):
    window = patched_window
    window.screener_preset_controller.active_preset = "Default"
    window.watchlist_dock.raise_()

    window.close()

    saved = FakeWorkspaceStateService.saved_states[-1]
    assert saved["window"]["size"][0] > 0
    assert saved["window"]["size"][1] > 0
    assert "workspace_splitter" in saved["splitters"]
    assert saved["dock_state"]
    assert saved["active_workspace"] in {
        "Chart",
        "Research",
        "Trade Card",
        "Watchlist",
        "Activity",
        "Portfolio",
        "Results",
    }
    assert saved["active_screener_preset"] == "Default"


def test_main_window_dock_widgets_can_be_restored(patched_window):
    window = patched_window

    window.chart_dock.setFloating(True)
    assert window.chart_dock.isFloating() is True

    window.restoreDockWidget(window.chart_dock)
    window.chart_dock.setFloating(False)

    assert window.chart_dock.isFloating() is False


def test_main_window_default_layout_sets_expected_docks(patched_window):
    window = patched_window

    window.apply_default_layout()

    assert window.active_workspace_layout == "Default"
    assert window.chart_dock.isHidden() is False
    assert window.research_dock.isHidden() is False
    assert window.trade_card_dock.isHidden() is False
    assert window.watchlist_dock.isHidden() is False
    assert window.activity_dock.isHidden() is False
    assert window.portfolio_dock.isHidden() is False
    assert window.screener_workspace_splitter.sizes()[0] > 0


def test_main_window_research_layout_prioritizes_research_panel(patched_window):
    window = patched_window

    window.apply_research_layout()

    assert window.active_workspace_layout == "Research"
    assert window.research_dock.isHidden() is False
    assert window.chart_dock.isHidden() is False
    assert window.watchlist_dock.isHidden() is False
    assert window.trade_card_dock.isHidden() is True
    assert window.portfolio_dock.isHidden() is True
    assert window.screener_workspace_splitter.sizes()[0] <= 260


def test_main_window_trading_layout_prioritizes_chart_and_trade_card(patched_window):
    window = patched_window

    window.apply_trading_layout()

    assert window.active_workspace_layout == "Trading"
    assert window.chart_dock.isHidden() is False
    assert window.trade_card_dock.isHidden() is False
    assert window.research_dock.isHidden() is False
    assert window.activity_dock.isHidden() is True
    assert window.portfolio_dock.isHidden() is False


def test_main_window_compact_layout_reduces_dock_footprint(patched_window):
    window = patched_window

    window.apply_compact_layout()

    assert window.active_workspace_layout == "Compact"
    assert window.chart_dock.isHidden() is False
    assert window.research_dock.isHidden() is False
    assert window.trade_card_dock.isHidden() is True
    assert window.watchlist_dock.isHidden() is True
    assert window.activity_dock.isHidden() is True
    assert window.portfolio_dock.isHidden() is True


def test_main_window_capture_workspace_state_includes_layout_metadata(patched_window):
    window = patched_window

    window.apply_compact_layout()
    window.research_dock.setFloating(True)
    state = window.capture_workspace_state()

    assert state["active_layout"] == "Compact"
    assert state["dock_visibility"]["watchlist"] is False
    assert state["dock_floating"]["research"] is True
    assert state["dock_state"]


def test_main_window_reset_workspace_restores_default_and_clears_custom_arrangement(patched_window):
    window = patched_window
    window.screener_preset_controller.active_preset = "Momentum"
    window.apply_compact_layout()

    saved = window.reset_workspace()

    assert window.active_workspace_layout == "Default"
    assert window.trade_card_dock.isHidden() is False
    assert saved["active_layout"] == "Default"
    assert saved["dock_state"] is None
    assert saved["active_screener_preset"] == "Momentum"


def test_main_window_restores_named_layout_and_dock_metadata(monkeypatch, app):
    monkeypatch.setattr(main_window_module, "MarketController", FakeMarketController)
    monkeypatch.setattr(main_window_module, "IndicatorController", FakeProcessingController)
    monkeypatch.setattr(main_window_module, "SupportController", FakeProcessingController)
    monkeypatch.setattr(main_window_module, "BounceController", FakeProcessingController)
    monkeypatch.setattr(main_window_module, "ScoringController", FakeScoringController)
    monkeypatch.setattr(main_window_module, "ChartController", FakeChartController)
    monkeypatch.setattr(main_window_module, "WatchlistController", FakeWatchlistController)
    monkeypatch.setattr(main_window_module, "TradeJournalController", FakeTradeJournalController)
    monkeypatch.setattr(main_window_module, "MarketStatusService", FakeMarketStatusService)
    monkeypatch.setattr(main_window_module, "RefreshScheduler", FakeRefreshScheduler)
    monkeypatch.setattr(main_window_module, "WorkspaceStateService", FakeWorkspaceStateService)
    FakeWorkspaceStateService.saved_states = []
    FakeWorkspaceStateService.state = {
        "active_layout": "Trading",
        "dock_visibility": {
            "activity": False,
            "trade_card": True,
        },
        "dock_floating": {
            "chart": False,
        },
    }

    window = MainWindow()

    try:
        assert window.active_workspace_layout == "Trading"
        assert window.trade_card_dock.isHidden() is False
        assert window.activity_dock.isHidden() is True
        assert window.chart_dock.isFloating() is False
    finally:
        window.close()
