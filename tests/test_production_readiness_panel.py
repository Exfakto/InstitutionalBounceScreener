from PySide6.QtWidgets import QApplication

from services.production_readiness_dashboard_service import (
    ProductionReadinessDashboard,
    ProductionReadinessSubsystem,
)
from ui.widgets.production_readiness_panel import ProductionReadinessPanel


def app():
    return QApplication.instance() or QApplication([])


def dashboard(status="Ready"):
    return ProductionReadinessDashboard(
        overall_status=status,
        generated_at="2026-07-04T12:00:00+00:00",
        subsystems=[
            ProductionReadinessSubsystem(
                name="Startup Diagnostics",
                status="Ready",
                summary="Startup checks passed",
                last_check_time="2026-07-04T10:00:00+00:00",
                recommended_action="No action required.",
            ),
            ProductionReadinessSubsystem(
                name="Provider Health",
                status=status,
                summary="1 provider healthy",
                last_check_time="2026-07-04T11:00:00+00:00",
                recommended_action="Review provider settings.",
            ),
        ],
    )


def test_production_readiness_panel_initial_state():
    app()
    panel = ProductionReadinessPanel()

    assert panel.status_label.text() == "Overall Status: N/A"
    assert panel.message_label.text() == "Refresh to check production readiness"
    assert panel.subsystem_table.isHidden()


def test_production_readiness_panel_renders_dashboard():
    app()
    panel = ProductionReadinessPanel()

    panel.set_dashboard(dashboard("Ready with Warnings"))

    assert "Overall Status: Ready with Warnings" in panel.status_label.text()
    assert panel.message_label.isHidden()
    assert panel.subsystem_table.rowCount() == 2
    assert panel.subsystem_table.item(0, 0).text() == "Startup Diagnostics"
    assert panel.subsystem_table.item(1, 1).text() == "Ready with Warnings"
    assert panel.subsystem_table.item(1, 4).text() == "Review provider settings."


def test_production_readiness_panel_empty_dashboard():
    app()
    panel = ProductionReadinessPanel()

    panel.set_dashboard(
        ProductionReadinessDashboard(
            overall_status="Ready with Warnings",
            generated_at="2026-07-04T12:00:00+00:00",
            subsystems=[],
        )
    )

    assert panel.message_label.text() == "No production readiness checks available"
    assert panel.subsystem_table.isHidden()


def test_production_readiness_panel_refresh_behavior():
    app()

    class Controller:
        def __init__(self):
            self.called = False

        def get_production_readiness_dashboard(self):
            self.called = True
            return dashboard("Ready")

    controller = Controller()
    panel = ProductionReadinessPanel(controller=controller)

    loaded = panel.refresh_dashboard()

    assert controller.called is True
    assert loaded.overall_status == "Ready"
    assert panel.subsystem_table.rowCount() == 2


def test_production_readiness_panel_error_state():
    app()

    class Controller:
        def get_production_readiness_dashboard(self):
            raise RuntimeError("readiness unavailable")

    panel = ProductionReadinessPanel(controller=Controller())

    assert panel.refresh_dashboard() is None
    assert panel.status_label.text() == "Overall Status: Not Ready"
    assert panel.message_label.text() == "Unable to load production readiness dashboard"
    assert panel.message_label.property("state") == "error"
