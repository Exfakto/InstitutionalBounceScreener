from __future__ import annotations

from typing import Any

from services.diagnostics_service import DiagnosticsService


class DiagnosticsController:
    """
    Thin controller for application diagnostics.
    """

    def __init__(
        self,
        diagnostics_service: DiagnosticsService | None = None,
    ) -> None:
        self.diagnostics_service = diagnostics_service or DiagnosticsService()

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
