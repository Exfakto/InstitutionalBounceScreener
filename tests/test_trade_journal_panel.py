import pytest
from PySide6.QtWidgets import QApplication

from ui.widgets.trade_journal_panel import TradeJournalPanel


@pytest.fixture(scope="module")
def app():
    application = QApplication.instance()

    if application is None:
        application = QApplication([])

    return application


def sample_trades():
    return [
        {
            "id": 1,
            "ticker": "AAPL",
            "status": "Entered",
            "entry_price": 100.0,
            "stop_price": 95.0,
            "target_price": 115.0,
            "exit_price": None,
            "risk_reward": 3.0,
            "opportunity_rating": "Elite Bounce",
            "confidence": "High",
        },
        {
            "id": 2,
            "ticker": "MSFT",
            "status": "Exited Win",
            "entry_price": 410.25,
            "stop_price": 392.0,
            "target_price": 440.0,
            "exit_price": 440.0,
            "risk_reward": 1.63,
            "opportunity_rating": "High Probability",
            "confidence": "Moderate",
        },
    ]


def test_trade_journal_panel_populates_trades(app):
    panel = TradeJournalPanel()

    panel.refresh_trades(sample_trades())

    assert panel.table.rowCount() == 2
    assert panel.table.item(0, 0).text() == "AAPL"
    assert panel.table.item(0, 1).text() == "Entered"
    assert panel.table.item(0, 2).text() == "100.00"
    assert panel.table.item(0, 3).text() == "95.00"
    assert panel.table.item(0, 4).text() == "115.00"
    assert panel.table.item(0, 5).text() == ""
    assert panel.table.item(0, 6).text() == "3.00"
    assert panel.table.item(0, 7).text() == "Elite Bounce"
    assert panel.table.item(0, 8).text() == "High"


def test_trade_journal_panel_selection_returns_trade_id(app):
    panel = TradeJournalPanel()
    panel.refresh_trades(sample_trades())

    panel.table.selectRow(1)

    assert panel.selected_trade() == 2


def test_trade_journal_panel_missing_selection_returns_none(app):
    panel = TradeJournalPanel()
    panel.refresh_trades(sample_trades())

    assert panel.selected_trade() is None


def test_trade_journal_panel_clear(app):
    panel = TradeJournalPanel()
    panel.refresh_trades(sample_trades())

    panel.clear()

    assert panel.table.rowCount() == 0
    assert panel.selected_trade() is None


def test_trade_journal_panel_repeated_refresh_replaces_rows(app):
    panel = TradeJournalPanel()

    panel.refresh_trades(sample_trades())
    panel.refresh_trades([sample_trades()[1]])

    assert panel.table.rowCount() == 1
    assert panel.table.item(0, 0).text() == "MSFT"
    assert panel.selected_trade() is None


def test_trade_journal_panel_missing_trades_handled_safely(app):
    panel = TradeJournalPanel()

    panel.refresh_trades(None)

    assert panel.table.rowCount() == 0


def test_trade_journal_panel_buttons_emit_signals(app):
    panel = TradeJournalPanel()
    emitted = []

    panel.new_trade_requested.connect(lambda: emitted.append("new"))
    panel.close_trade_requested.connect(lambda: emitted.append("close"))
    panel.delete_trade_requested.connect(lambda: emitted.append("delete"))
    panel.refresh_requested.connect(lambda: emitted.append("refresh"))

    panel.new_button.click()
    panel.close_button.click()
    panel.delete_button.click()
    panel.refresh_button.click()

    assert emitted == ["new", "close", "delete", "refresh"]
