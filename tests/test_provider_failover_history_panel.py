from types import SimpleNamespace

from PySide6.QtWidgets import QApplication

from services.provider_failover_event_service import ProviderFailoverEvent
from ui.widgets.provider_failover_history_panel import ProviderFailoverHistoryPanel


def app():
    return QApplication.instance() or QApplication([])


def event(timestamp, previous="polygon", new="fmp", reason="timeout"):
    return ProviderFailoverEvent(
        previous_provider=previous,
        new_provider=new,
        timestamp=timestamp,
        reason=reason,
        error_count=2,
        latency_seconds=0.123456,
    )


def test_provider_failover_history_panel_populated_history():
    app()
    panel = ProviderFailoverHistoryPanel()

    panel.set_events([event("2026-07-04T10:00:00+00:00")])

    assert panel.message_label.isHidden()
    assert panel.history_table.rowCount() == 1
    assert panel.history_table.item(0, 0).text() == "2026-07-04T10:00:00+00:00"
    assert panel.history_table.item(0, 1).text() == "polygon"
    assert panel.history_table.item(0, 2).text() == "fmp"
    assert panel.history_table.item(0, 3).text() == "timeout"
    assert panel.history_table.item(0, 4).text() == "2"
    assert panel.history_table.item(0, 5).text() == "0.1235"


def test_provider_failover_history_panel_empty_state():
    app()
    panel = ProviderFailoverHistoryPanel()

    panel.set_events([])

    assert panel.message_label.text() == "No provider failover events recorded"
    assert panel.history_table.isHidden()


def test_provider_failover_history_panel_sorts_newest_first():
    app()
    panel = ProviderFailoverHistoryPanel()

    panel.set_events(
        [
            event("2026-07-04T09:00:00+00:00", previous="a", new="b"),
            event("2026-07-04T11:00:00+00:00", previous="c", new="d"),
            event("2026-07-04T10:00:00+00:00", previous="e", new="f"),
        ]
    )

    assert panel.history_table.item(0, 0).text() == "2026-07-04T11:00:00+00:00"
    assert panel.history_table.item(1, 0).text() == "2026-07-04T10:00:00+00:00"
    assert panel.history_table.item(2, 0).text() == "2026-07-04T09:00:00+00:00"


def test_provider_failover_history_panel_refresh_action():
    app()

    class Controller:
        def __init__(self):
            self.called = False

        def provider_failover_history(self):
            self.called = True
            return [event("2026-07-04T10:00:00+00:00")]

    controller = Controller()
    panel = ProviderFailoverHistoryPanel(controller=controller)

    loaded = panel.refresh_history()

    assert controller.called is True
    assert loaded[0].previous_provider == "polygon"
    assert panel.history_table.rowCount() == 1


def test_provider_failover_history_panel_error_state():
    app()

    class Controller:
        def provider_failover_history(self):
            raise RuntimeError("history unavailable")

    panel = ProviderFailoverHistoryPanel(controller=Controller())

    assert panel.refresh_history() is None
    assert panel.message_label.text() == "Unable to load provider failover history"
    assert panel.message_label.property("state") == "error"


def test_provider_failover_history_panel_accepts_dict_and_object_events():
    app()
    panel = ProviderFailoverHistoryPanel()

    panel.set_events(
        [
            {
                "timestamp": "2026-07-04T10:00:00+00:00",
                "previous_provider": "polygon",
                "new_provider": "fmp",
                "reason": "429",
                "error_count": 1,
            },
            SimpleNamespace(
                timestamp="2026-07-04T11:00:00+00:00",
                previous_provider="fmp",
                new_provider="alpaca",
                reason="timeout",
            ),
        ]
    )

    assert panel.history_table.rowCount() == 2
    assert panel.history_table.item(0, 1).text() == "fmp"
    assert panel.history_table.item(0, 5).text() == "N/A"
