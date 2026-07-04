from PySide6.QtWidgets import QApplication

from services.live_provider_resilience_service import ProviderHealthResult
from services.production_readiness_dashboard_service import (
    ProductionReadinessDashboard,
    ProductionReadinessSubsystem,
)
from services.screening_diagnostics_service import (
    ScreeningDiagnosticsResult,
    ScreeningStageDiagnostic,
)
from ui.widgets.dashboard import InstitutionalDashboard
from ui.widgets.production_readiness_panel import ProductionReadinessPanel
from ui.widgets.provider_health_panel import ProviderHealthPanel
from ui.widgets.screening_diagnostics_panel import ScreeningDiagnosticsPanel
from ui.widgets.screening_results_panel import ScreeningResultsPanel


def app():
    return QApplication.instance() or QApplication([])


def test_rc1_smoke_dashboard_screening_provider_and_diagnostics_panels_initialize():
    app()

    dashboard = InstitutionalDashboard()
    dashboard.set_dashboard_data(
        {
            "market_summary": {
                "market_status": "Closed",
                "active_provider": "local_csv",
                "last_refresh": "2026-07-04T10:00:00+00:00",
                "database_status": "OK",
            },
            "opportunity_summary": {
                "candidates_screened": 1,
                "high_conviction": 1,
                "watch_candidates": 0,
                "average_opportunity_score": 88.0,
            },
            "best_opportunities": [
                {
                    "ticker": "AAPL",
                    "company": "Apple Inc.",
                    "opportunity_score": 88.0,
                    "confidence": "HIGH",
                    "risk_reward": 2.5,
                }
            ],
        }
    )

    results = ScreeningResultsPanel()
    provider_health = ProviderHealthPanel()
    provider_health.set_dashboard(
        {
            "active_provider": "local_csv",
            "failover_provider": "N/A",
            "providers": [
                ProviderHealthResult(
                    provider_name="local_csv",
                    status="healthy",
                    success_count=1,
                    error_count=0,
                    average_latency_seconds=0.0,
                )
            ],
            "failover_events": [],
        }
    )
    diagnostics = ScreeningDiagnosticsPanel()
    diagnostics.set_diagnostics(
        ScreeningDiagnosticsResult(
            run_id="rc1-smoke",
            overall_status="passed",
            symbol_count=1,
            stages=[
                ScreeningStageDiagnostic(
                    stage_key="candidate_ranking",
                    stage_name="Candidate Ranking",
                    status="passed",
                    timing_seconds=0.01,
                )
            ],
        )
    )
    readiness = ProductionReadinessPanel()
    readiness.set_dashboard(
        ProductionReadinessDashboard(
            overall_status="Ready",
            generated_at="2026-07-04T10:00:00+00:00",
            subsystems=[
                ProductionReadinessSubsystem(
                    name="Startup Diagnostics",
                    status="Ready",
                    summary="Startup checks passed",
                    last_check_time="2026-07-04T10:00:00+00:00",
                    recommended_action="No action required.",
                )
            ],
        )
    )

    assert dashboard.best_opportunities_table.rowCount() == 1
    assert results.run_screening_button.isEnabled() is True
    assert provider_health.health_table.rowCount() == 1
    assert diagnostics.stage_table.rowCount() == 1
    assert readiness.subsystem_table.rowCount() == 1
