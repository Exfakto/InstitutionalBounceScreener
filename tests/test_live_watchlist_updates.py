import pytest
from PySide6.QtWidgets import QApplication

from controllers.watchlist_controller import WatchlistController
from providers.provider_result import ProviderResult
from ui.main_window import MainWindow
from ui.widgets.watchlist_panel import WatchlistPanel


@pytest.fixture(scope="module")
def app():
    application = QApplication.instance()

    if application is None:
        application = QApplication([])

    return application


class FakeLiveDataService:

    def __init__(self, results):
        self.results = dict(results)
        self.calls = []

    def get_price_history(self, ticker):
        self.calls.append(ticker)
        result = self.results.get(ticker)

        if result is None:
            return ProviderResult.fail("missing", source="fake")

        return result


class FakeMarketStatusService:

    def __init__(self, status):
        self.status = status

    def get_status(self, now=None):
        return type("MarketStatus", (), {"status": self.status})()


class FakeWatchlistController:

    def __init__(self, quotes):
        self.quotes = quotes
        self.tickers = None

    def refresh_watchlist(self, tickers):
        self.tickers = tickers
        return {
            "success": True,
            "message": "refreshed",
            "quotes": self.quotes,
        }


class FakeWatchlistPanel:

    def __init__(self, tickers):
        self.tickers = tickers
        self.updated = None

    def visible_tickers(self):
        return self.tickers

    def update_quotes(self, quotes):
        self.updated = quotes


class FakeRefreshScheduler:

    refresh_interval = 300

    def is_running(self):
        return True


class FakeHeaderBar:

    def set_refresh_status(self, **kwargs):
        self.kwargs = kwargs


def price_result(rows):
    return ProviderResult.ok(data=rows, source="fake")


def test_refresh_one_ticker():
    live_data_service = FakeLiveDataService(
        {
            "AAPL": price_result(
                [
                    {"close": 100.0, "date": "2026-07-01"},
                    {"close": 105.0, "date": "2026-07-02"},
                ]
            )
        }
    )
    controller = WatchlistController(
        watchlist_service=object(),
        live_data_service=live_data_service,
    )

    result = controller.refresh_watchlist(["aapl"])

    assert result["success"] is True
    assert live_data_service.calls == ["AAPL"]
    assert result["quotes"]["AAPL"]["success"] is True
    assert result["quotes"]["AAPL"]["last_price"] == 105.0
    assert result["quotes"]["AAPL"]["daily_change"] == 5.0
    assert result["quotes"]["AAPL"]["percent_change"] == 5.0
    assert result["quotes"]["AAPL"]["timestamp"] == "2026-07-02"


def test_refresh_multiple_tickers():
    live_data_service = FakeLiveDataService(
        {
            "AAPL": price_result([{"close": 100}, {"close": 101}]),
            "MSFT": price_result([{"close": 200}, {"close": 210}]),
        }
    )
    controller = WatchlistController(
        watchlist_service=object(),
        live_data_service=live_data_service,
    )

    result = controller.refresh_watchlist(["AAPL", "MSFT"])

    assert live_data_service.calls == ["AAPL", "MSFT"]
    assert result["quotes"]["AAPL"]["last_price"] == 101.0
    assert result["quotes"]["MSFT"]["daily_change"] == 10.0


def test_failed_refresh_returns_failure_quote():
    live_data_service = FakeLiveDataService(
        {
            "AAPL": ProviderResult.fail(
                "provider failed",
                source="fake",
                warnings=["planned failure"],
            )
        }
    )
    controller = WatchlistController(
        watchlist_service=object(),
        live_data_service=live_data_service,
    )

    result = controller.refresh_watchlist(["AAPL"])

    assert result["quotes"]["AAPL"]["success"] is False
    assert result["quotes"]["AAPL"]["message"] == "provider failed"
    assert result["quotes"]["AAPL"]["warnings"] == ["planned failure"]


def test_watchlist_panel_row_update(app):
    panel = WatchlistPanel()
    panel.refresh_items(
        [
            {
                "id": 1,
                "ticker": "AAPL",
                "company_name": "Apple Inc.",
                "status": "Watching",
                "notes": "",
                "added_at": "2026-07-01",
            }
        ]
    )

    updated = panel.update_quote(
        "AAPL",
        {
            "success": True,
            "last_price": 105,
            "daily_change": 2.5,
            "percent_change": 2.44,
            "timestamp": "2026-07-02 10:30",
        },
    )

    assert updated is True
    assert panel.table.item(0, 4).text() == "105.00"
    assert panel.table.item(0, 5).text() == "+2.50"
    assert panel.table.item(0, 6).text() == "+2.44%"
    assert panel.table.item(0, 7).text() == "2026-07-02 10:30"
    assert panel.visible_tickers() == ["AAPL"]


def test_watchlist_panel_failed_update_preserves_previous_value(app):
    panel = WatchlistPanel()
    panel.refresh_items([{"id": 1, "ticker": "AAPL", "last_price": 100}])
    panel.update_quote("AAPL", {"success": True, "last_price": 101})

    updated = panel.update_quote("AAPL", {"success": False})

    assert updated is False
    assert panel.table.item(0, 4).text() == "101.00"


def test_market_closed_skips_watchlist_refresh():
    window = MainWindow.__new__(MainWindow)
    window.market_status_service = FakeMarketStatusService("Closed")
    window.watchlist_controller = FakeWatchlistController({})
    window.watchlist_panel = FakeWatchlistPanel(["AAPL"])

    window.refresh_visible_watchlist_quotes()

    assert window.watchlist_controller.tickers is None
    assert window.watchlist_panel.updated is None


def test_scheduler_callback_refreshes_watchlist():
    window = MainWindow.__new__(MainWindow)
    window.market_status_service = FakeMarketStatusService("Open")
    window.watchlist_controller = FakeWatchlistController(
        {
            "AAPL": {
                "success": True,
                "last_price": 105,
                "daily_change": 1,
                "percent_change": 0.96,
                "timestamp": "2026-07-02 10:30",
            }
        }
    )
    window.watchlist_panel = FakeWatchlistPanel(["AAPL"])
    window.refresh_scheduler = FakeRefreshScheduler()
    window.header_bar = FakeHeaderBar()
    window.last_refresh_at = None
    window.next_refresh_at = None

    window.handle_live_refresh_result("AAPL", object())

    assert window.watchlist_controller.tickers == ["AAPL"]
    assert window.watchlist_panel.updated["AAPL"]["last_price"] == 105
    assert window.last_refresh_at is not None


def test_timestamp_update_from_controller_to_panel(app):
    panel = WatchlistPanel()
    panel.refresh_items([{"id": 1, "ticker": "MSFT"}])
    panel.update_quotes(
        {
            "MSFT": {
                "success": True,
                "last_price": 210,
                "daily_change": 10,
                "percent_change": 5,
                "timestamp": "2026-07-02 11:00",
            }
        }
    )

    assert panel.table.item(0, 7).text() == "2026-07-02 11:00"
