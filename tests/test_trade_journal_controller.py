from types import SimpleNamespace

from controllers.trade_journal_controller import TradeJournalController
from ui.main_window import MainWindow


class FakeTradeJournalService:

    def __init__(self):
        self.calls = []

    def create_trade(self, **trade_data):
        self.calls.append(("create_trade", trade_data))
        return {"success": True, "message": "created", "trade": trade_data}

    def update_trade(self, trade_id, **updates):
        self.calls.append(("update_trade", trade_id, updates))
        return {"success": True, "message": "updated", "trade": {"id": trade_id}}

    def close_trade(
        self,
        trade_id,
        exit_date=None,
        exit_price=None,
        status="Exited Win",
        notes=None,
    ):
        self.calls.append(
            ("close_trade", trade_id, exit_date, exit_price, status, notes)
        )
        return {"success": True, "message": "closed", "trade": {"id": trade_id}}

    def delete_trade(self, trade_id):
        self.calls.append(("delete_trade", trade_id))
        return {"success": True, "message": "deleted", "count": 0}

    def get_trades(self):
        self.calls.append(("get_trades",))
        return {"success": True, "message": "trades", "trades": [], "count": 0}

    def count_trades(self):
        self.calls.append(("count_trades",))
        return {"success": True, "message": "count", "count": 0}


class FakeCandidateTable:

    def __init__(self, ticker=None):
        self.ticker = ticker

    def selected_ticker(self):
        return self.ticker


class FakeTradeJournalController:

    def __init__(self):
        self.created = None
        self.closed = None
        self.deleted = None
        self.trades = [{"id": 1, "ticker": "AAPL"}]

    def create_trade(self, **trade_data):
        self.created = trade_data
        return {"success": True, "message": "Trade created."}

    def close_trade(self, trade_id):
        self.closed = trade_id
        return {"success": True, "message": "Trade closed."}

    def delete_trade(self, trade_id):
        self.deleted = trade_id
        return {"success": True, "message": "Trade deleted."}

    def get_trades(self):
        return {
            "success": True,
            "message": "Trades retrieved.",
            "trades": self.trades,
            "count": len(self.trades),
        }


class FakeTradeJournalPanel:

    def __init__(self, trade_id=None):
        self.trade_id = trade_id
        self.trades = None
        self.cleared = False

    def selected_trade(self):
        return self.trade_id

    def refresh_trades(self, trades):
        self.trades = trades

    def clear(self):
        self.cleared = True


class FakeActivityPanel:

    def __init__(self):
        self.logs = []

    def append_log(self, text):
        self.logs.append(text)


def test_controller_delegates_create_update_close_delete_get_and_count():
    service = FakeTradeJournalService()
    controller = TradeJournalController(service)

    controller.create_trade(ticker="AAPL", company_name="Apple Inc.")
    controller.update_trade(1, status="Entered")
    controller.close_trade(1, exit_price=110.0, status="Exited Win")
    controller.delete_trade(1)
    controller.get_trades()
    controller.count_trades()

    assert service.calls == [
        ("create_trade", {"ticker": "AAPL", "company_name": "Apple Inc."}),
        ("update_trade", 1, {"status": "Entered"}),
        ("close_trade", 1, None, 110.0, "Exited Win", None),
        ("delete_trade", 1),
        ("get_trades",),
        ("count_trades",),
    ]


def test_main_window_creates_trade_from_selected_candidate():
    window = MainWindow.__new__(MainWindow)
    window.candidates_table = FakeCandidateTable("AAPL")
    window.candidates_by_ticker = {
        "AAPL": SimpleNamespace(company_name="Apple Inc.")
    }
    window.trade_journal_controller = FakeTradeJournalController()
    window.trade_journal_panel = FakeTradeJournalPanel()
    window.activity_panel = FakeActivityPanel()

    window.create_selected_candidate_trade()

    assert window.trade_journal_controller.created == {
        "ticker": "AAPL",
        "company_name": "Apple Inc.",
    }
    assert window.trade_journal_panel.trades == [{"id": 1, "ticker": "AAPL"}]
    assert window.activity_panel.logs == ["Trade created."]


def test_main_window_closes_selected_trade():
    window = MainWindow.__new__(MainWindow)
    window.trade_journal_controller = FakeTradeJournalController()
    window.trade_journal_panel = FakeTradeJournalPanel(trade_id=4)
    window.activity_panel = FakeActivityPanel()

    window.close_selected_trade()

    assert window.trade_journal_controller.closed == 4
    assert window.trade_journal_panel.trades == [{"id": 1, "ticker": "AAPL"}]
    assert window.activity_panel.logs == ["Trade closed."]


def test_main_window_deletes_selected_trade():
    window = MainWindow.__new__(MainWindow)
    window.trade_journal_controller = FakeTradeJournalController()
    window.trade_journal_panel = FakeTradeJournalPanel(trade_id=9)
    window.activity_panel = FakeActivityPanel()

    window.delete_selected_trade()

    assert window.trade_journal_controller.deleted == 9
    assert window.trade_journal_panel.trades == [{"id": 1, "ticker": "AAPL"}]
    assert window.activity_panel.logs == ["Trade deleted."]


def test_main_window_missing_trade_selection_is_safe():
    window = MainWindow.__new__(MainWindow)
    window.trade_journal_controller = FakeTradeJournalController()
    window.trade_journal_panel = FakeTradeJournalPanel(trade_id=None)
    window.activity_panel = FakeActivityPanel()

    window.close_selected_trade()
    window.delete_selected_trade()

    assert window.trade_journal_controller.closed is None
    assert window.trade_journal_controller.deleted is None
    assert window.activity_panel.logs == []
