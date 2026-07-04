from __future__ import annotations

from typing import Any

from services.diagnostics_service import DiagnosticsService
from services.production_readiness_dashboard_service import (
    ProductionReadinessDashboardService,
)
from services.screening_diagnostics_service import ScreeningDiagnosticsService


class DiagnosticsController:
    """
    Thin controller for application diagnostics.
    """

    def __init__(
        self,
        diagnostics_service: DiagnosticsService | None = None,
        screening_diagnostics_service: ScreeningDiagnosticsService | None = None,
        production_readiness_dashboard_service: ProductionReadinessDashboardService | None = None,
    ) -> None:
        self.diagnostics_service = diagnostics_service or DiagnosticsService()
        self.screening_diagnostics_service = (
            screening_diagnostics_service or ScreeningDiagnosticsService()
        )
        self.production_readiness_dashboard_service = (
            production_readiness_dashboard_service
            or ProductionReadinessDashboardService(
                startup_diagnostics_service=self.diagnostics_service,
                screening_diagnostics_service=self.screening_diagnostics_service,
                production_packaging_service=self.diagnostics_service,
            )
        )

    def get_diagnostics(self) -> dict[str, Any]:
        return self.diagnostics_service.get_diagnostics()

    def diagnostics_text(self) -> str:
        return self.diagnostics_service.diagnostics_text()

    def startup_report(self):
        if hasattr(self.diagnostics_service, "startup_report"):
            return self.diagnostics_service.startup_report()
        return None

    def health_report(self):
        if hasattr(self.diagnostics_service, "health_report"):
            return self.diagnostics_service.health_report()
        return None

    def get_screening_diagnostics(self):
        return self.screening_diagnostics_service.get_latest_diagnostics()

    def get_production_readiness_dashboard(self):
        return self.production_readiness_dashboard_service.build_dashboard()
