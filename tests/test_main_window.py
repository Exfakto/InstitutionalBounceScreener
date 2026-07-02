from types import SimpleNamespace

import pytest
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
    def get_statistics(self):
        return {
            "stocks": 0,
            "rows": 0,
            "indicator_rows": 0,
            "support_levels": 0,
            "validated_zones": 0,
        }

    def update_universe(self):
        return 0, 0

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

    def run_screener(self):
        self.calls += 1
        scores = {
            "quality_score": SimpleNamespace(value=90.0),
            "institutional_score": SimpleNamespace(value=76.0),
            "technical_score": SimpleNamespace(value=84.0),
            "support_score": SimpleNamespace(value=91.0),
            "bounce_score": SimpleNamespace(value=80.0),
        }
        candidates = [
            SimpleNamespace(
                ticker="AAPL",
                company_name="Apple Inc.",
                primary_score_value=91.0,
                composite_score=SimpleNamespace(value=91.0),
                score_map=scores,
                scores=[],
                warnings=[],
            )
        ]
        return {
            "candidates": candidates,
            "processed": 1,
            "skipped": 0,
            "elapsed_seconds": 0.1,
        }

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


def test_main_window_refresh_results_reuses_run_screen(patched_window):
    window = patched_window

    window.refresh_screener_results()
    window.refresh_screener_results()

    assert window.scoring_controller.calls == 2
    assert window.candidates_table.rowCount() == 1


def test_main_window_reset_clears_results_and_filters(patched_window):
    window = patched_window
    window.run_screener()

    result = window.reset_screener_filters()

    assert result["success"] is True
    assert window.candidates_table.rowCount() == 0
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
