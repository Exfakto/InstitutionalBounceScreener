from types import SimpleNamespace

from controllers.watchlist_controller import WatchlistController
from ui.main_window import MainWindow


class FakeWatchlistService:

    def __init__(self, items=None):
        self.calls = []
        self.items = items or []

    def add_item(self, ticker, company_name=None, notes=None, source=None):
        self.calls.append(
            ("add_item", ticker, company_name, notes, source)
        )
        return {"success": True, "message": "added", "item": {"ticker": ticker}}

    def update_item(self, item_id, status=None, notes=None):
        self.calls.append(("update_item", item_id, status, notes))
        return {"success": True, "message": "updated", "item": {"id": item_id}}

    def remove_item(self, item_id):
        self.calls.append(("remove_item", item_id))
        return {"success": True, "message": "removed", "count": 0}

    def get_items(self, status=None):
        self.calls.append(("get_items", status))
        return {
            "success": True,
            "message": "items",
            "item": self.items,
            "count": len(self.items),
        }

    def count_items(self, status=None):
        self.calls.append(("count_items", status))
        return {"success": True, "message": "count", "count": 0}


class FakeCandidateTable:

    def __init__(self, ticker=None):
        self.ticker = ticker

    def selected_ticker(self):
        return self.ticker


class FakeWatchlistController:

    def __init__(self):
        self.added = None
        self.removed = None
        self.items = [{"id": 1, "ticker": "AAPL"}]

    def add_candidate(self, ticker, company_name=None, notes=None):
        self.added = (ticker, company_name, notes)
        return {"success": True, "message": "Watchlist item added."}

    def remove_item(self, item_id):
        self.removed = item_id
        return {"success": True, "message": "Watchlist item removed."}

    def get_items(self, status=None):
        return {
            "success": True,
            "message": "Watchlist items retrieved.",
            "item": self.items,
            "count": len(self.items),
        }


class FakeWatchlistPanel:

    def __init__(self, item_id=None):
        self.item_id = item_id
        self.items = None
        self.cleared = False

    def selected_item_id(self):
        return self.item_id

    def refresh_items(self, items):
        self.items = items

    def clear(self):
        self.cleared = True


class FakeActivityPanel:

    def __init__(self):
        self.logs = []

    def append_log(self, text):
        self.logs.append(text)


class FailingLiveDataService:

    def get_price_history(self, ticker):
        raise AssertionError("live data should not be called")


def test_controller_delegates_add_candidate_to_service():
    service = FakeWatchlistService()
    controller = WatchlistController(service)

    result = controller.add_candidate(
        "AAPL",
        company_name="Apple Inc.",
        notes="Near support",
    )

    assert result["success"] is True
    assert service.calls == [
        ("add_item", "AAPL", "Apple Inc.", "Near support", "Candidate")
    ]


def test_controller_delegates_update_remove_get_and_count():
    service = FakeWatchlistService()
    controller = WatchlistController(service)

    controller.update_item(1, status="Ready", notes="Confirmed")
    controller.remove_item(1)
    controller.get_items(status="Ready")
    controller.count_items(status="Ready")

    assert service.calls == [
        ("update_item", 1, "Ready", "Confirmed"),
        ("remove_item", 1),
        ("get_items", "Ready"),
        ("count_items", "Ready"),
    ]


def test_controller_returns_watchlist_intelligence():
    service = FakeWatchlistService(
        [
            {
                "ticker": "AAPL",
                "status": "Ready",
                "opportunity_rating": {"rating_score": 91},
                "confidence": "Very High",
            },
            {
                "ticker": "MSFT",
                "status": "Watching",
                "overall_score": 72,
            },
        ]
    )
    controller = WatchlistController(service, live_data_service=FailingLiveDataService())

    result = controller.get_watchlist_intelligence()

    assert result.total_items == 2
    assert result.ready_count == 1
    assert result.watching_count == 1
    assert result.high_conviction_count == 1
    assert result.top_candidates[0]["ticker"] == "AAPL"
    assert service.calls == [("get_items", None)]


def test_main_window_adds_selected_candidate_to_watchlist():
    window = MainWindow.__new__(MainWindow)
    window.candidates_table = FakeCandidateTable("AAPL")
    window.candidates_by_ticker = {
        "AAPL": SimpleNamespace(company_name="Apple Inc.")
    }
    window.watchlist_controller = FakeWatchlistController()
    window.watchlist_panel = FakeWatchlistPanel()
    window.activity_panel = FakeActivityPanel()

    window.add_selected_candidate_to_watchlist()

    assert window.watchlist_controller.added == ("AAPL", "Apple Inc.", None)
    assert window.watchlist_panel.items == [{"id": 1, "ticker": "AAPL"}]
    assert window.activity_panel.logs == ["Watchlist item added."]


def test_main_window_remove_selected_watchlist_item():
    window = MainWindow.__new__(MainWindow)
    window.watchlist_controller = FakeWatchlistController()
    window.watchlist_panel = FakeWatchlistPanel(item_id=7)
    window.activity_panel = FakeActivityPanel()

    window.remove_selected_watchlist_item()

    assert window.watchlist_controller.removed == 7
    assert window.watchlist_panel.items == [{"id": 1, "ticker": "AAPL"}]
    assert window.activity_panel.logs == ["Watchlist item removed."]


def test_main_window_missing_watchlist_selection_is_safe():
    window = MainWindow.__new__(MainWindow)
    window.watchlist_controller = FakeWatchlistController()
    window.watchlist_panel = FakeWatchlistPanel(item_id=None)
    window.activity_panel = FakeActivityPanel()

    window.remove_selected_watchlist_item()

    assert window.watchlist_controller.removed is None
    assert window.activity_panel.logs == []
