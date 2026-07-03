from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from config.app_metadata import (
    APPLICATION_NAME,
    BUILD_DATE,
    BUILD_TIMESTAMP,
    RELEASE_CHANNEL,
    SCHEMA_VERSION,
    VERSION,
)
from config.settings import DATABASE_FOLDER, DATABASE_NAME


@dataclass(frozen=True)
class AppConfig:
    application_name: str = APPLICATION_NAME
    version: str = VERSION
    build_date: str = BUILD_DATE
    build_timestamp: str = BUILD_TIMESTAMP
    release_channel: str = RELEASE_CHANNEL
    schema_version: str = SCHEMA_VERSION
    database_path: Path = Path(DATABASE_FOLDER) / DATABASE_NAME
    export_directory: Path = Path("exports/results")
    log_directory: Path = Path("logs")
    data_directory: Path = Path("data")
    config_directory: Path = Path("config")
    log_level: str = "INFO"


@dataclass(frozen=True)
class ConfigValidationResult:
    valid: bool
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    checked_paths: dict[str, str] = field(default_factory=dict)


class AppConfigService:
    """
    Central application configuration with filesystem validation.
    """

    def __init__(self, config: AppConfig | None = None):
        self.config = config or AppConfig()

    def load(self):
        return self.config

    def validate(self, create_missing=True):
        warnings = []
        errors = []
        checked_paths = {
            "database_path": str(self.config.database_path),
            "export_directory": str(self.config.export_directory),
            "log_directory": str(self.config.log_directory),
            "data_directory": str(self.config.data_directory),
            "config_directory": str(self.config.config_directory),
        }

        for directory in [
            self.config.export_directory,
            self.config.log_directory,
            self.config.data_directory,
            self.config.config_directory,
        ]:
            try:
                if create_missing:
                    directory.mkdir(parents=True, exist_ok=True)
                if not directory.exists():
                    errors.append(f"Required directory missing: {directory}")
                elif not directory.is_dir():
                    errors.append(f"Path is not a directory: {directory}")
            except OSError as exc:
                errors.append(f"Unable to prepare directory {directory}: {exc}")

        database_parent = self.config.database_path.parent
        try:
            if create_missing:
                database_parent.mkdir(parents=True, exist_ok=True)
            if not database_parent.exists():
                errors.append(f"Database directory missing: {database_parent}")
        except OSError as exc:
            errors.append(f"Unable to prepare database directory {database_parent}: {exc}")

        if not self.is_writable_directory(self.config.export_directory):
            errors.append(f"Export directory is not writable: {self.config.export_directory}")

        if not self.config.database_path.exists():
            warnings.append(f"Database file does not exist yet: {self.config.database_path}")

        return ConfigValidationResult(
            valid=not errors,
            warnings=warnings,
            errors=errors,
            checked_paths=checked_paths,
        )

    @staticmethod
    def is_writable_directory(directory):
        try:
            directory.mkdir(parents=True, exist_ok=True)
            probe = directory / ".write_test"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
            return True
        except OSError:
            return False
