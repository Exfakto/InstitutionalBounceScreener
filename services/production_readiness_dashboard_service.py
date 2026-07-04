from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


READY = "Ready"
READY_WITH_WARNINGS = "Ready with Warnings"
NOT_READY = "Not Ready"


@dataclass(frozen=True)
class ProductionReadinessSubsystem:
    name: str
    status: str
    summary: str
    last_check_time: str
    recommended_action: str


@dataclass(frozen=True)
class ProductionReadinessDashboard:
    overall_status: str
    subsystems: list[ProductionReadinessSubsystem] = field(default_factory=list)
    generated_at: str = ""


class ProductionReadinessDashboardService:
    """Aggregate existing health checks into one production readiness view."""

    def __init__(
        self,
        startup_diagnostics_service=None,
        screening_diagnostics_service=None,
        provider_health_service=None,
        provider_configuration_validation_service=None,
        full_universe_validation_service=None,
        model_calibration_service=None,
        production_packaging_service=None,
        clock=None,
    ):
        self.startup_diagnostics_service = startup_diagnostics_service
        self.screening_diagnostics_service = screening_diagnostics_service
        self.provider_health_service = provider_health_service
        self.provider_configuration_validation_service = (
            provider_configuration_validation_service
        )
        self.full_universe_validation_service = full_universe_validation_service
        self.model_calibration_service = model_calibration_service
        self.production_packaging_service = production_packaging_service
        self.clock = clock or now_utc

    def build_dashboard(self):
        checked_at = self.clock()
        subsystems = [
            self.subsystem(
                "Startup Diagnostics",
                self.call(self.startup_diagnostics_service, ("startup_report", "run", "get_diagnostics")),
                checked_at,
                "Resolve startup diagnostics failures before production use.",
            ),
            self.subsystem(
                "Screening Diagnostics",
                self.call(self.screening_diagnostics_service, ("get_latest_diagnostics", "run", "validate")),
                checked_at,
                "Run or repair the screening pipeline before relying on production results.",
            ),
            self.provider_health_subsystem(checked_at),
            self.subsystem(
                "Provider Configuration Validation",
                self.call(self.provider_configuration_validation_service, ("validate", "run")),
                checked_at,
                "Fix provider credentials, timeouts, retries, rate limits, or failover settings.",
            ),
            self.subsystem(
                "Full Universe Validation",
                self.call(self.full_universe_validation_service, ("validate", "run")),
                checked_at,
                "Validate the full NYSE/NASDAQ universe before a production scan.",
            ),
            self.subsystem(
                "Model Calibration",
                self.call(self.model_calibration_service, ("audit", "validate", "run")),
                checked_at,
                "Review calibration warnings before promoting model settings.",
            ),
            self.subsystem(
                "Production Packaging",
                self.call(self.production_packaging_service, ("run", "check", "validate")),
                checked_at,
                "Complete packaging diagnostics and release checks before distribution.",
            ),
        ]
        return ProductionReadinessDashboard(
            overall_status=self.overall_status(subsystems),
            subsystems=subsystems,
            generated_at=checked_at,
        )

    def provider_health_subsystem(self, checked_at):
        result = self.call(self.provider_health_service, ("provider_health_dashboard", "all_health", "run"))
        if isinstance(result, dict) and "providers" in result:
            providers = list(result.get("providers") or [])
        elif isinstance(result, list):
            providers = result
        else:
            providers = []
        if not providers:
            return ProductionReadinessSubsystem(
                name="Provider Health",
                status=NOT_READY,
                summary="No market data providers are configured.",
                last_check_time=checked_at,
                recommended_action="Configure and validate at least one healthy provider.",
            )
        statuses = [str(value(provider, "status") or "").lower() for provider in providers]
        if any(status == "healthy" for status in statuses):
            status = READY_WITH_WARNINGS if any(status != "healthy" for status in statuses) else READY
        else:
            status = NOT_READY
        summary = (
            f"{len(providers)} provider(s); "
            f"healthy={statuses.count('healthy')}; "
            f"degraded={statuses.count('degraded')}; "
            f"unavailable={statuses.count('unavailable')}"
        )
        action = (
            "No action required."
            if status == READY
            else "Review provider health, credentials, latency, and failover configuration."
        )
        return ProductionReadinessSubsystem(
            name="Provider Health",
            status=status,
            summary=summary,
            last_check_time=checked_at,
            recommended_action=action,
        )

    def subsystem(self, name, result, checked_at, default_action):
        if isinstance(result, Exception):
            return ProductionReadinessSubsystem(
                name=name,
                status=NOT_READY,
                summary=str(result) or f"{name} check failed.",
                last_check_time=checked_at,
                recommended_action=default_action,
            )
        if result is None:
            return ProductionReadinessSubsystem(
                name=name,
                status=READY_WITH_WARNINGS,
                summary=f"{name} check is not configured.",
                last_check_time=checked_at,
                recommended_action=f"Wire {name.lower()} into diagnostics for production verification.",
            )
        status = readiness_status(status_text(result))
        summary = summary_text(result, default=f"{name} status is {status}.")
        action = action_text(result) or ("No action required." if status == READY else default_action)
        return ProductionReadinessSubsystem(
            name=name,
            status=status,
            summary=summary,
            last_check_time=last_checked(result) or checked_at,
            recommended_action=action,
        )

    @staticmethod
    def call(service, method_names):
        if service is None:
            return None
        if callable(service) and not any(hasattr(service, name) for name in method_names):
            try:
                return service()
            except Exception as exc:
                return exc
        for method_name in method_names:
            method = getattr(service, method_name, None)
            if callable(method):
                try:
                    return method()
                except Exception as exc:
                    return exc
        return service

    @staticmethod
    def overall_status(subsystems):
        statuses = {subsystem.status for subsystem in subsystems}
        if NOT_READY in statuses:
            return NOT_READY
        if READY_WITH_WARNINGS in statuses:
            return READY_WITH_WARNINGS
        return READY


def readiness_status(raw):
    text = str(raw or "").strip().lower()
    if text in {
        "ready",
        "pass",
        "passed",
        "healthy",
        "complete",
        "completed",
        "success",
        "ok",
    }:
        return READY
    if text in {"warning", "warn", "ready with warnings", "partial", "degraded"}:
        return READY_WITH_WARNINGS
    if text in {"fail", "failed", "error", "not ready", "unavailable"}:
        return NOT_READY
    return READY_WITH_WARNINGS


def status_text(source):
    for key in ("overall_status", "status", "health_status", "result"):
        raw = value(source, key)
        if raw not in (None, ""):
            return raw
    items = value(source, "items") or value(source, "checks") or []
    statuses = [value(item, "status") for item in items]
    if any(readiness_status(status) == NOT_READY for status in statuses):
        return NOT_READY
    if any(readiness_status(status) == READY_WITH_WARNINGS for status in statuses):
        return READY_WITH_WARNINGS
    return READY if statuses else READY_WITH_WARNINGS


def summary_text(source, default):
    for key in ("summary", "message", "diagnostic_summary", "description"):
        raw = value(source, key)
        if raw not in (None, ""):
            return str(raw)
    warnings = list(value(source, "warnings") or [])
    errors = list(value(source, "errors") or [])
    if errors:
        return "; ".join(str(item) for item in errors[:2])
    if warnings:
        return "; ".join(str(item) for item in warnings[:2])
    return default


def action_text(source):
    for key in ("recommended_action", "recommended_fix", "action"):
        raw = value(source, key)
        if raw not in (None, ""):
            return str(raw)
    issues = list(value(source, "issues") or [])
    if issues:
        raw = value(issues[0], "recommended_fix") or value(issues[0], "recommended_action")
        if raw:
            return str(raw)
    return ""


def last_checked(source):
    for key in ("last_check_time", "checked_at", "generated_at", "completed_at", "updated_at"):
        raw = value(source, key)
        if raw not in (None, ""):
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
