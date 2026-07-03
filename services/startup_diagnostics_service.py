from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field

from config.app_metadata import SCHEMA_VERSION
from database.manager import DatabaseManager
from services.app_config_service import AppConfigService


@dataclass(frozen=True)
class DiagnosticCheck:
    name: str
    status: str
    message: str


@dataclass(frozen=True)
class StartupDiagnosticReport:
    status: str
    checks: list[DiagnosticCheck] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class StartupDiagnosticsService:
    """
    Read-only startup diagnostics for local application readiness.
    """

    def __init__(self, config_service=None, database_factory=None):
        self.config_service = config_service or AppConfigService()
        self.database_factory = database_factory or DatabaseManager

    def run(self):
        checks = []
        warnings = []
        errors = []

        config_result = self.config_service.validate(create_missing=True)
        checks.append(
            DiagnosticCheck(
                "configuration",
                "PASS" if config_result.valid else "FAIL",
                "Configuration paths validated" if config_result.valid else "; ".join(config_result.errors),
            )
        )
        warnings.extend(config_result.warnings)
        errors.extend(config_result.errors)

        db = None
        try:
            db = self.database_factory(self.config_service.load().database_path)
            db.cursor.execute("SELECT 1")
            checks.append(DiagnosticCheck("database_connectivity", "PASS", "Database connection succeeded"))

            db.cursor.execute("PRAGMA user_version")
            row = db.cursor.fetchone()
            checks.append(
                DiagnosticCheck(
                    "schema_version",
                    "PASS",
                    f"Schema version {SCHEMA_VERSION}; SQLite user_version {row[0] if row else 0}",
                )
            )

            db.cursor.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table' AND name = 'app_settings'
                """
            )
            if db.cursor.fetchone():
                checks.append(DiagnosticCheck("settings_table", "PASS", "app_settings table available"))
            else:
                checks.append(DiagnosticCheck("settings_table", "FAIL", "app_settings table missing"))
                errors.append("app_settings table missing")
        except sqlite3.Error as exc:
            checks.append(DiagnosticCheck("database_connectivity", "FAIL", str(exc)))
            errors.append(str(exc))
        finally:
            if db is not None:
                db.close()

        for name, path in config_result.checked_paths.items():
            checks.append(DiagnosticCheck(name, "PASS", path))

        status = self.overall_status(checks, warnings, errors)
        return StartupDiagnosticReport(
            status=status,
            checks=checks,
            warnings=warnings,
            errors=errors,
        )

    @staticmethod
    def overall_status(checks, warnings, errors):
        if errors or any(check.status == "FAIL" for check in checks):
            return "FAIL"
        if warnings or any(check.status == "WARNING" for check in checks):
            return "WARNING"
        return "PASS"
