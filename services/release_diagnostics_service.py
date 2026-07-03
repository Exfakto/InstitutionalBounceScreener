from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from services.app_config_service import AppConfigService
from services.database_backup_service import DatabaseBackupService
from services.resource_path_service import ResourcePathService


@dataclass(frozen=True)
class ReleaseDiagnosticItem:
    name: str
    status: str
    message: str


@dataclass(frozen=True)
class ReleaseDiagnosticsReport:
    status: str
    items: list[ReleaseDiagnosticItem] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class ReleaseDiagnosticsService:
    def __init__(
        self,
        config_service=None,
        resource_service=None,
        backup_service_factory=DatabaseBackupService,
    ):
        self.config_service = config_service or AppConfigService()
        self.resource_service = resource_service or ResourcePathService()
        self.backup_service_factory = backup_service_factory

    def run(self):
        config = self.config_service.load()
        items = [
            ReleaseDiagnosticItem(
                "packaged_mode",
                "PASS" if self.resource_service.is_packaged() else "WARNING",
                "Packaged mode detected" if self.resource_service.is_packaged() else "Running in dev mode",
            )
        ]

        for name, parts in [
            ("config_directory", ("config",)),
            ("data_directory", ("data",)),
            ("docs_directory", ("docs",)),
            ("resources_directory", ("resources",)),
        ]:
            path = self.resource_service.path(*parts)
            items.append(
                ReleaseDiagnosticItem(
                    name,
                    "PASS" if path.exists() else "WARNING",
                    f"{path} {'available' if path.exists() else 'missing'}",
                )
            )

        validation = self.config_service.validate(create_missing=True)
        for key, value in validation.checked_paths.items():
            path = Path(value)
            status = "PASS" if path.exists() or key == "database_path" else "FAIL"
            items.append(ReleaseDiagnosticItem(key, status, str(path)))

        backup_service = self.backup_service_factory(
            config.database_path,
            Path(config.data_directory) / "backups",
        )
        if Path(config.database_path).exists():
            backup_ok = backup_service.validate_backup(config.database_path)
            items.append(
                ReleaseDiagnosticItem(
                    "database_backup_health",
                    "PASS" if backup_ok else "FAIL",
                    "Database integrity check passed" if backup_ok else "Database integrity check failed",
                )
            )
        else:
            items.append(
                ReleaseDiagnosticItem(
                    "database_backup_health",
                    "WARNING",
                    "Database file does not exist yet",
                )
            )

        warnings = list(validation.warnings)
        errors = list(validation.errors)
        warnings.extend(item.message for item in items if item.status == "WARNING")
        errors.extend(item.message for item in items if item.status == "FAIL")
        return ReleaseDiagnosticsReport(
            status=self.overall_status(items, warnings, errors),
            items=items,
            warnings=self.unique(warnings),
            errors=self.unique(errors),
        )

    @staticmethod
    def overall_status(items, warnings, errors):
        if errors or any(item.status == "FAIL" for item in items):
            return "FAIL"
        if warnings or any(item.status == "WARNING" for item in items):
            return "WARNING"
        return "PASS"

    @staticmethod
    def unique(values):
        result = []
        for value in values or []:
            if value and value not in result:
                result.append(value)
        return result
