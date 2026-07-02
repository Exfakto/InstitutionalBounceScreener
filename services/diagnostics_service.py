from __future__ import annotations

import platform
import sys
from pathlib import Path
from typing import Any

from config.settings import DATABASE_FOLDER, DATABASE_NAME
from providers.provider_config import ProviderConfig


class DiagnosticsService:
    """
    Collect lightweight runtime diagnostics without network or file writes.
    """

    DEFAULT_VERSION = "v3.0.0-beta"

    def __init__(
        self,
        provider_config_path: str | Path = "config/providers.json",
        database_path: str | Path | None = None,
        log_path: str | Path | None = None,
    ) -> None:
        self.provider_config_path = Path(provider_config_path)
        self.database_path = (
            Path(database_path)
            if database_path is not None
            else Path(DATABASE_FOLDER) / DATABASE_NAME
        )
        self.log_path = Path(log_path) if log_path is not None else Path("logs")

    def get_diagnostics(self) -> dict[str, Any]:
        """
        Return display-safe application diagnostics.
        """

        provider_config = ProviderConfig.load(self.provider_config_path)

        return {
            "app_name": "Institutional Bounce Screener",
            "version": self._version(),
            "python_version": sys.version.split()[0],
            "operating_system": platform.platform(),
            "active_provider": provider_config.active_provider,
            "provider_config_path": str(self.provider_config_path),
            "provider_config_available": self.provider_config_path.exists(),
            "database_path": str(self.database_path),
            "working_directory": str(Path.cwd()),
            "log_path": str(self.log_path),
            "test_build_mode": "Unavailable",
            "warnings": list(provider_config.warnings),
        }

    def diagnostics_text(self) -> str:
        """
        Return a readable diagnostics summary suitable for the clipboard.
        """

        diagnostics = self.get_diagnostics()
        labels = {
            "app_name": "Application",
            "version": "Version",
            "python_version": "Python",
            "operating_system": "Operating System",
            "active_provider": "Active Provider",
            "provider_config_path": "Provider Config",
            "database_path": "Database Path",
            "working_directory": "Working Directory",
            "log_path": "Log Path",
            "test_build_mode": "Test/Build Mode",
        }
        lines = [
            f"{label}: {diagnostics.get(key) or '--'}"
            for key, label in labels.items()
        ]

        warnings = diagnostics.get("warnings") or []

        if warnings:
            lines.append("Warnings: " + "; ".join(str(warning) for warning in warnings))

        return "\n".join(lines)

    def _version(self) -> str:
        return self.DEFAULT_VERSION
