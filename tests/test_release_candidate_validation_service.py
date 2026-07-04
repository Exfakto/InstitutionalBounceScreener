from dataclasses import dataclass

from services.live_provider_resilience_service import ProviderHealthResult
from services.release_candidate_validation_service import (
    CHECK_FAILED,
    CHECK_PASSED,
    CHECK_WARNING,
    RC_BLOCKED,
    RC_READY,
    RC_READY_WITH_WARNINGS,
    ReleaseCandidateValidationService,
)


@dataclass(frozen=True)
class Result:
    status: str
    summary: str = "Check passed"
    recommended_fix: str = "No action required."


class Service:
    def __init__(self, result):
        self.result = result
        self.called = False

    def run(self):
        self.called = True
        return self.result


class ProviderHealth:
    def __init__(self, providers):
        self.providers = providers

    def all_health(self):
        return list(self.providers)


def passing_service():
    return Service(Result("passed"))


def validator(**overrides):
    defaults = {
        "startup_diagnostics_service": passing_service(),
        "production_readiness_dashboard_service": passing_service(),
        "provider_configuration_validation_service": passing_service(),
        "provider_health_service": ProviderHealth(
            [ProviderHealthResult("polygon", "healthy")]
        ),
        "full_universe_validation_service": passing_service(),
        "screening_diagnostics_service": passing_service(),
        "model_calibration_service": passing_service(),
        "export_system_service": passing_service(),
        "packaging_status_service": passing_service(),
        "clock": lambda: "2026-07-04T12:00:00+00:00",
    }
    defaults.update(overrides)
    return ReleaseCandidateValidationService(**defaults)


def test_release_candidate_validation_all_ready():
    result = validator().validate()

    assert result.overall_status == RC_READY
    assert result.generated_at == "2026-07-04T12:00:00+00:00"
    assert len(result.checks) == 9
    assert all(check.status == CHECK_PASSED for check in result.checks)


def test_release_candidate_validation_warning_status():
    result = validator(
        provider_configuration_validation_service=Service(
            Result("warning", summary="Failover provider missing")
        )
    ).validate()

    assert result.overall_status == RC_READY_WITH_WARNINGS
    assert result.warning_checks[0].name == "Provider Configuration"
    assert result.warning_checks[0].status == CHECK_WARNING
    assert result.warning_checks[0].reason == "Failover provider missing"


def test_release_candidate_validation_failed_status_blocks_rc():
    result = validator(
        full_universe_validation_service=Service(
            Result("failed", summary="Universe validation failed")
        )
    ).validate()

    assert result.overall_status == RC_BLOCKED
    failed = result.failed_checks[0]
    assert failed.name == "Full Universe Validation"
    assert failed.status == CHECK_FAILED
    assert failed.reason == "Universe validation failed"
    assert "full universe" in failed.recommended_fix.lower()


def test_release_candidate_validation_provider_health_warning_and_failure():
    warning = validator(
        provider_health_service=ProviderHealth(
            [
                ProviderHealthResult("polygon", "healthy"),
                ProviderHealthResult("fmp", "degraded"),
            ]
        )
    ).validate()

    provider_check = [check for check in warning.checks if check.name == "Provider Health"][0]
    assert warning.overall_status == RC_READY_WITH_WARNINGS
    assert provider_check.status == CHECK_WARNING
    assert "degraded=1" in provider_check.reason

    failed = validator(
        provider_health_service=ProviderHealth(
            [ProviderHealthResult("polygon", "unavailable")]
        )
    ).validate()
    provider_check = [check for check in failed.checks if check.name == "Provider Health"][0]
    assert failed.overall_status == RC_BLOCKED
    assert provider_check.status == CHECK_FAILED


def test_release_candidate_validation_missing_service_warns():
    result = validator(export_system_service=None).validate()

    export = [check for check in result.checks if check.name == "Export System"][0]
    assert result.overall_status == RC_READY_WITH_WARNINGS
    assert export.status == CHECK_WARNING
    assert "not configured" in export.reason


def test_release_candidate_validation_service_exception_records_failed_check():
    class FailingService:
        def run(self):
            raise RuntimeError("packaging unavailable")

    result = validator(packaging_status_service=FailingService()).validate()

    packaging = [check for check in result.checks if check.name == "Packaging Status"][0]
    assert result.overall_status == RC_BLOCKED
    assert packaging.status == CHECK_FAILED
    assert packaging.reason == "packaging unavailable"
