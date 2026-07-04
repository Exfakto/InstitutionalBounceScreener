from PySide6.QtWidgets import QApplication

from services.live_provider_resilience_service import ProviderHealthResult
from ui.widgets.provider_health_panel import ProviderHealthPanel
from ui.widgets.settings_panel import SettingsPanel


def app():
    return QApplication.instance() or QApplication([])


def dashboard(status="healthy"):
    return {
        "active_provider": "polygon",
        "failover_provider": "fmp",
        "providers": [
            ProviderHealthResult(
                provider_name="polygon",
                status=status,
                success_count=3,
                error_count=1 if status == "degraded" else 0,
                average_latency_seconds=0.1234,
                last_failure_reason="temporary timeout" if status != "healthy" else None,
            ),
            ProviderHealthResult(
                provider_name="fmp",
                status="healthy",
                success_count=2,
                error_count=0,
                average_latency_seconds=0.2,
            ),
        ],
    }


def test_provider_health_panel_renders_healthy_provider():
    app()
    panel = ProviderHealthPanel()

    panel.set_dashboard(dashboard("healthy"))

    assert panel.message_label.isHidden()
    assert "Active: polygon" in panel.summary_label.text()
    assert "Failover: fmp" in panel.summary_label.text()
    assert panel.health_table.rowCount() == 2
    assert panel.health_table.item(0, 0).text() == "polygon"
    assert panel.health_table.item(0, 1).text() == "healthy"
    assert panel.health_table.item(0, 2).text() == "3"
    assert panel.health_table.item(0, 4).text() == "0.1234"


def test_provider_health_panel_renders_degraded_provider_badge_value():
    app()
    panel = ProviderHealthPanel()

    panel.set_dashboard(dashboard("degraded"))

    assert panel.health_table.item(0, 1).text() == "degraded"
    assert panel.health_table.item(0, 5).text() == "temporary timeout"


def test_provider_health_panel_renders_unavailable_provider():
    app()
    panel = ProviderHealthPanel()
    data = dashboard("unavailable")
    data["active_provider"] = "fmp"

    panel.set_dashboard(data)

    assert panel.health_table.item(0, 1).text() == "unavailable"
    assert "Active: fmp" in panel.summary_label.text()


def test_provider_health_panel_empty_state():
    app()
    panel = ProviderHealthPanel()

    panel.set_dashboard({"providers": []})

    assert panel.message_label.text() == "No providers configured"
    assert panel.health_table.isHidden()


def test_provider_health_panel_refresh_action():
    app()

    class Controller:
        def __init__(self):
            self.called = False

        def provider_health_dashboard(self):
            self.called = True
            return dashboard("healthy")

    controller = Controller()
    panel = ProviderHealthPanel(controller=controller)

    loaded = panel.refresh_health()

    assert controller.called is True
    assert loaded["active_provider"] == "polygon"
    assert panel.health_table.rowCount() == 2


def test_provider_health_panel_error_state():
    app()

    class Controller:
        def provider_health_dashboard(self):
            raise RuntimeError("provider health unavailable")

    panel = ProviderHealthPanel(controller=Controller())

    assert panel.refresh_health() is None
    assert panel.message_label.text() == "Unable to load provider health"
    assert panel.message_label.property("state") == "error"


def test_settings_panel_contains_provider_health_panel():
    app()
    panel = SettingsPanel(market_data_controller=object())

    assert isinstance(panel.provider_health_panel, ProviderHealthPanel)
