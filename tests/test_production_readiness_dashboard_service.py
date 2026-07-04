from dataclasses import dataclass

from services.live_provider_resilience_service import ProviderHealthResult
from services.production_readiness_dashboard_service import (
    NOT_READY,
    READY,
    READY_WITH_WARNINGS,
    ProductionReadinessDashboardService,
)


@dataclass(frozen=True)
class Result:
    status: str
    summary: str = "Subsystem healthy"
    recommended_action: str = "No action required."
    last_check_time: str = "2026-07-04T10:00:00+00:00"


class Service:
    def __init__(self, result):
        self.result = result
        self.called = False

    def run(self):
        self.called = True
        return self.result


class ProviderHealthService:
    def __init__(self, providers):
        self.providers = providers

    def all_health(self):
        return list(self.providers)


def ready_service():
    return Service(Result("PASS"))


def service(**overrides):
    defaults = {
        "startup_diagnostics_service": ready_service(),
        "screening_diagnostics_service": ready_service(),
        "provider_health_service": ProviderHealthService(
            [ProviderHealthResult("polygon", "healthy")]
        ),
        "provider_configuration_validation_service": ready_service(),
        "full_universe_validation_service": ready_service(),
        "model_calibration_service": ready_service(),
        "production_packaging_service": ready_service(),
        "clock": lambda: "2026-07-04T12:00:00+00:00",
    }
    defaults.update(overrides)
    return ProductionReadinessDashboardService(**defaults)


def test_production_readiness_dashboard_all_ready():
    dashboard = service().build_dashboard()

    assert dashboard.overall_status == READY
    assert dashboard.generated_at == "2026-07-04T12:00:00+00:00"
    assert len(dashboard.subsystems) == 7
    assert all(item.status == READY for item in dashboard.subsystems)


def test_production_readiness_dashboard_warnings_present():
    dashboard = service(
        screening_diagnostics_service=Service(
            Result("warning", summary="Screening has warnings")
        )
    ).build_dashboard()

    assert dashboard.overall_status == READY_WITH_WARNINGS
    screening = [item for item in dashboard.subsystems if item.name == "Screening Diagnostics"][0]
    assert screening.status == READY_WITH_WARNINGS
    assert screening.summary == "Screening has warnings"


def test_production_readiness_dashboard_failures_present():
    dashboard = service(
        full_universe_validation_service=Service(
            Result("failed", summary="Universe validation failed")
        )
    ).build_dashboard()

    assert dashboard.overall_status == NOT_READY
    universe = [item for item in dashboard.subsystems if item.name == "Full Universe Validation"][0]
    assert universe.status == NOT_READY


def test_production_readiness_dashboard_provider_health_warning_and_failure():
    warning_dashboard = service(
        provider_health_service=ProviderHealthService(
            [
                ProviderHealthResult("polygon", "healthy"),
                ProviderHealthResult("fmp", "degraded"),
            ]
        )
    ).build_dashboard()
    provider = [item for item in warning_dashboard.subsystems if item.name == "Provider Health"][0]
    assert provider.status == READY_WITH_WARNINGS
    assert "degraded=1" in provider.summary

    failed_dashboard = service(
        provider_health_service=ProviderHealthService(
            [ProviderHealthResult("polygon", "unavailable")]
        )
    ).build_dashboard()
    provider = [item for item in failed_dashboard.subsystems if item.name == "Provider Health"][0]
    assert failed_dashboard.overall_status == NOT_READY
    assert provider.status == NOT_READY


def test_production_readiness_dashboard_missing_subsystem_warns():
    dashboard = service(model_calibration_service=None).build_dashboard()

    calibration = [item for item in dashboard.subsystems if item.name == "Model Calibration"][0]
    assert dashboard.overall_status == READY_WITH_WARNINGS
    assert calibration.status == READY_WITH_WARNINGS
    assert "not configured" in calibration.summary


def test_production_readiness_dashboard_service_exception_marks_not_ready():
    class FailingService:
        def run(self):
            raise RuntimeError("release check failed")

    dashboard = service(production_packaging_service=FailingService()).build_dashboard()

    packaging = [item for item in dashboard.subsystems if item.name == "Production Packaging"][0]
    assert dashboard.overall_status == NOT_READY
    assert packaging.status == NOT_READY
    assert packaging.summary == "release check failed"
