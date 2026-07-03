from types import SimpleNamespace

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QDockWidget

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
    FakeWorkspaceStateService.state = {}
    FakeWorkspaceStateService.saved_states = []

    window = MainWindow()
    yield window
    window.close()


def test_professional_screener_workspace_creation(patched_window):
    window = patched_window

    assert window.dashboard is not None
    assert window.dashboard_controller is not None
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
    }
    assert all(isinstance(dock, QDockWidget) for dock in window.workspace_docks.values())
    assert window.chart_dock.windowTitle() == "Chart"
    assert window.research_dock.windowTitle() == "Research"
    assert window.trade_card_dock.windowTitle() == "Trade Card"
    assert window.watchlist_dock.windowTitle() == "Watchlist"
    assert window.activity_dock.windowTitle() == "Activity"
    assert window.portfolio_dock.windowTitle() == "Portfolio"


def test_main_window_embeds_existing_widgets_in_docks(patched_window):
    window = patched_window

    assert window.chart_dock.widget() is window.price_chart
    assert window.research_dock.widget() is window.research_preview
    assert window.trade_card_dock.widget() is window.trade_card
    assert window.watchlist_dock.widget() is window.watchlist_panel
    assert window.activity_dock.widget() is window.activity_panel
    assert window.portfolio_dock.widget() is window.performance_dashboard


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


def test_main_window_dashboard_empty_market_universe_shows_empty_message(patched_window):
    window = patched_window

    result = window.refresh_dashboard_results()

    assert result == {"success": True, "records": 0}
    assert window.scoring_controller.calls == 0
    assert window.candidates_table.rowCount() == 0
    assert window.dashboard.best_opportunities_table.rowCount() == 0
    assert window.dashboard_status_label.text() == "No results available"
    assert window.dashboard_status_label.isHidden() is False


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
