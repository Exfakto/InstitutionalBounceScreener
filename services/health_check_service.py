from __future__ import annotations

from dataclasses import dataclass, field

from database.manager import DatabaseManager
from services.app_config_service import AppConfigService
from services.app_settings_repository import AppSettingsRepository
from services.results_export_service import ResultsExportService


@dataclass(frozen=True)
class HealthCheckResult:
    name: str
    status: str
    message: str


@dataclass(frozen=True)
class HealthReport:
    status: str
    checks: list[HealthCheckResult] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class HealthCheckService:
    """
    Local health checks for production readiness.
    """

    def __init__(self, config_service=None, database_factory=None):
        self.config_service = config_service or AppConfigService()
        self.database_factory = database_factory or DatabaseManager

    def run(self):
        checks = []
        warnings = []
        errors = []
        db = None

        try:
            db = self.database_factory(self.config_service.load().database_path)
            db.cursor.execute("SELECT 1")
            checks.append(HealthCheckResult("database", "PASS", "Database reachable"))

            repository = AppSettingsRepository(db)
            repository.get_all_settings()
            checks.append(HealthCheckResult("settings", "PASS", "Settings repository reachable"))

            db.cursor.execute("SELECT COUNT(*) FROM sqlite_master")
            checks.append(HealthCheckResult("repository", "PASS", "SQLite repository metadata readable"))
        except Exception as exc:
            checks.append(HealthCheckResult("database", "FAIL", str(exc)))
            errors.append(str(exc))
        finally:
            if db is not None:
                db.close()

        config_result = self.config_service.validate(create_missing=True)
        if config_result.valid:
            checks.append(HealthCheckResult("configuration", "PASS", "Configuration valid"))
        else:
            checks.append(HealthCheckResult("configuration", "FAIL", "; ".join(config_result.errors)))
            errors.extend(config_result.errors)
        warnings.extend(config_result.warnings)

        try:
            destination = ResultsExportService.destination_path(
                self.config_service.load().export_directory,
                "health_check",
                "json",
            )
            if destination is not None:
                checks.append(HealthCheckResult("export_service", "PASS", "Export destination can be resolved"))
            else:
                checks.append(HealthCheckResult("export_service", "FAIL", "Export destination unavailable"))
                errors.append("Export destination unavailable")
        except Exception as exc:
            checks.append(HealthCheckResult("export_service", "FAIL", str(exc)))
            errors.append(str(exc))

        status = self.overall_status(checks, warnings, errors)
        return HealthReport(status=status, checks=checks, warnings=warnings, errors=errors)

    @staticmethod
    def overall_status(checks, warnings, errors):
        if errors or any(check.status == "FAIL" for check in checks):
            return "FAIL"
        if warnings or any(check.status == "WARNING" for check in checks):
            return "WARNING"
        return "PASS"
