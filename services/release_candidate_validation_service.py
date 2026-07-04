from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


CHECK_PASSED = "passed"
CHECK_WARNING = "warning"
CHECK_FAILED = "failed"
RC_READY = "ready"
RC_READY_WITH_WARNINGS = "ready_with_warnings"
RC_BLOCKED = "blocked"


@dataclass(frozen=True)
class ReleaseCandidateValidationCheck:
    name: str
    status: str
    reason: str
    severity: str
    recommended_fix: str


@dataclass(frozen=True)
class ReleaseCandidateValidationResult:
    overall_status: str
    checks: list[ReleaseCandidateValidationCheck] = field(default_factory=list)
    generated_at: str = ""

    @property
    def failed_checks(self):
        return [check for check in self.checks if check.status == CHECK_FAILED]

    @property
    def warning_checks(self):
        return [check for check in self.checks if check.status == CHECK_WARNING]


class ReleaseCandidateValidationService:
    """Final release-candidate validation aggregator for v2.0 readiness."""

    CHECKS = (
        (
            "Startup Diagnostics",
            "startup_diagnostics_service",
            ("startup_report", "run", "get_diagnostics"),
            "Resolve startup diagnostics failures before tagging the release candidate.",
        ),
        (
            "Production Readiness Dashboard",
            "production_readiness_dashboard_service",
            ("build_dashboard", "run"),
            "Resolve production readiness warnings or failures.",
        ),
        (
            "Provider Configuration",
            "provider_configuration_validation_service",
            ("validate", "run"),
            "Fix provider credentials, endpoints, timeout, retry, and failover settings.",
        ),
        (
            "Provider Health",
            "provider_health_service",
            ("provider_health_dashboard", "all_health", "run"),
            "Verify at least one healthy provider and review failover configuration.",
        ),
        (
            "Full Universe Validation",
            "full_universe_validation_service",
            ("validate", "run"),
            "Run and resolve full universe validation issues.",
        ),
        (
            "Screening Diagnostics",
            "screening_diagnostics_service",
            ("get_latest_diagnostics", "run", "validate"),
            "Resolve screening diagnostics before validating the release candidate.",
        ),
        (
            "Model Calibration",
            "model_calibration_service",
            ("audit", "validate", "run"),
            "Review calibration audit and validation warnings.",
        ),
        (
            "Export System",
            "export_system_service",
            ("health_check", "validate", "run", "check"),
            "Verify export destinations and export service health.",
        ),
        (
            "Packaging Status",
            "packaging_status_service",
            ("run", "check", "validate"),
            "Complete release diagnostics and packaging checks.",
        ),
    )

    def __init__(
        self,
        startup_diagnostics_service=None,
        production_readiness_dashboard_service=None,
        provider_configuration_validation_service=None,
        provider_health_service=None,
        full_universe_validation_service=None,
        screening_diagnostics_service=None,
        model_calibration_service=None,
        export_system_service=None,
        packaging_status_service=None,
        clock=None,
    ):
        self.startup_diagnostics_service = startup_diagnostics_service
        self.production_readiness_dashboard_service = production_readiness_dashboard_service
        self.provider_configuration_validation_service = (
            provider_configuration_validation_service
        )
        self.provider_health_service = provider_health_service
        self.full_universe_validation_service = full_universe_validation_service
        self.screening_diagnostics_service = screening_diagnostics_service
        self.model_calibration_service = model_calibration_service
        self.export_system_service = export_system_service
        self.packaging_status_service = packaging_status_service
        self.clock = clock or now_utc

    def validate(self):
        generated_at = self.clock()
        checks = []
        for name, attr, methods, recommended_fix in self.CHECKS:
            result = call(getattr(self, attr), methods)
            checks.append(self.check_from_result(name, result, recommended_fix))
        return ReleaseCandidateValidationResult(
            overall_status=overall_status(checks),
            checks=checks,
            generated_at=generated_at,
        )

    def check_from_result(self, name, result, recommended_fix):
        if isinstance(result, Exception):
            return ReleaseCandidateValidationCheck(
                name=name,
                status=CHECK_FAILED,
                reason=str(result) or f"{name} validation failed.",
                severity="failed",
                recommended_fix=recommended_fix,
            )
        if result is None:
            return ReleaseCandidateValidationCheck(
                name=name,
                status=CHECK_WARNING,
                reason=f"{name} validation is not configured.",
                severity="warning",
                recommended_fix=f"Wire {name.lower()} into release candidate validation.",
            )
        if name == "Provider Health":
            return provider_health_check(result, recommended_fix)
        status = normalize_status(status_text(result))
        action = action_text(result)
        if status != CHECK_PASSED and action.strip().lower() == "no action required.":
            action = ""
        return ReleaseCandidateValidationCheck(
            name=name,
            status=status,
            reason=reason_text(result, default=f"{name} check {status}."),
            severity=status,
            recommended_fix=action or (
                "No action required." if status == CHECK_PASSED else recommended_fix
            ),
        )


def provider_health_check(result, recommended_fix):
    if isinstance(result, dict) and "providers" in result:
        providers = list(result.get("providers") or [])
    elif isinstance(result, list):
        providers = result
    else:
        providers = []
    if not providers:
        return ReleaseCandidateValidationCheck(
            name="Provider Health",
            status=CHECK_FAILED,
            reason="No market data providers are configured.",
            severity="failed",
            recommended_fix=recommended_fix,
        )
    statuses = [str(value(provider, "status") or "").lower() for provider in providers]
    if any(status == "healthy" for status in statuses):
        status = CHECK_WARNING if any(status != "healthy" for status in statuses) else CHECK_PASSED
    else:
        status = CHECK_FAILED
    return ReleaseCandidateValidationCheck(
        name="Provider Health",
        status=status,
        reason=(
            f"{len(providers)} provider(s); healthy={statuses.count('healthy')}; "
            f"degraded={statuses.count('degraded')}; unavailable={statuses.count('unavailable')}"
        ),
        severity=status,
        recommended_fix="No action required." if status == CHECK_PASSED else recommended_fix,
    )


def call(service, methods):
    if service is None:
        return None
    if callable(service) and not any(hasattr(service, method) for method in methods):
        try:
            return service()
        except Exception as exc:
            return exc
    for method_name in methods:
        method = getattr(service, method_name, None)
        if callable(method):
            try:
                return method()
            except Exception as exc:
                return exc
    return service


def normalize_status(raw):
    text = str(raw or "").strip().lower()
    if text in {
        "pass",
        "passed",
        "ready",
        "healthy",
        "success",
        "complete",
        "completed",
        "ok",
    }:
        return CHECK_PASSED
    if text in {
        "warn",
        "warning",
        "ready with warnings",
        "ready_with_warnings",
        "partial",
        "degraded",
    }:
        return CHECK_WARNING
    if text in {"fail", "failed", "error", "blocked", "not ready", "unavailable"}:
        return CHECK_FAILED
    return CHECK_WARNING


def overall_status(checks):
    if any(check.status == CHECK_FAILED for check in checks):
        return RC_BLOCKED
    if any(check.status == CHECK_WARNING for check in checks):
        return RC_READY_WITH_WARNINGS
    return RC_READY


def status_text(source):
    for key in ("overall_status", "status", "health_status", "result"):
        raw = value(source, key)
        if raw not in (None, ""):
            return raw
    items = value(source, "items") or value(source, "checks") or []
    statuses = [normalize_status(value(item, "status")) for item in items]
    if CHECK_FAILED in statuses:
        return CHECK_FAILED
    if CHECK_WARNING in statuses:
        return CHECK_WARNING
    return CHECK_PASSED if statuses else CHECK_WARNING


def reason_text(source, default):
    for key in ("reason", "summary", "message", "diagnostic_summary", "description"):
        raw = value(source, key)
        if raw not in (None, ""):
            return str(raw)
    errors = list(value(source, "errors") or [])
    warnings = list(value(source, "warnings") or [])
    if errors:
        return "; ".join(str(item) for item in errors[:2])
    if warnings:
        return "; ".join(str(item) for item in warnings[:2])
    issues = list(value(source, "issues") or [])
    if issues:
        raw = value(issues[0], "message") or value(issues[0], "issue_description")
        if raw:
            return str(raw)
    return default


def action_text(source):
    for key in ("recommended_fix", "recommended_action", "action"):
        raw = value(source, key)
        if raw not in (None, ""):
            return str(raw)
    issues = list(value(source, "issues") or [])
    if issues:
        raw = value(issues[0], "recommended_fix") or value(issues[0], "recommended_action")
        if raw:
            return str(raw)
    return ""


def value(source, key, default=None):
    if source is None:
        return default
    if isinstance(source, dict):
        return source.get(key, default)
    return getattr(source, key, default)


def now_utc():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
