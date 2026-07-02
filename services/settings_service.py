from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Any

from config.settings import DATABASE_FOLDER, DATABASE_NAME
from providers.provider_config import ProviderConfig


class SettingsService:
    """
    JSON-backed application settings service.

    The service owns only user-configurable application preferences. Provider
    API keys remain in environment variables and are never read from or written
    to the settings file.
    """

    DEFAULT_SETTINGS: dict[str, Any] = {
        "general": {
            "default_workspace": "Dashboard",
            "auto_save_layout": True,
            "remember_last_ticker": True,
        },
        "refresh": {
            "enabled": True,
            "interval": 300,
            "market_aware": True,
        },
        "appearance": {
            "theme": "Dark",
            "font_scaling": "100%",
        },
        "paths": {
            "database_path": str(Path(DATABASE_FOLDER) / DATABASE_NAME),
            "export_path": "exports",
            "log_path": "logs",
        },
    }

    API_KEY_ENVIRONMENT = {
        "Polygon": "POLYGON_API_KEY",
        "FMP": "FMP_API_KEY",
        "Finnhub": "FINNHUB_API_KEY",
    }

    def __init__(
        self,
        settings_path: str | Path = "config/settings.json",
        provider_config_path: str | Path = "config/providers.json",
    ) -> None:
        self.settings_path = Path(settings_path)
        self.provider_config_path = Path(provider_config_path)

    def load(self) -> dict[str, Any]:
        """
        Load settings with safe defaults.
        """

        loaded = self._read_json_file(self.settings_path)

        if not isinstance(loaded, dict):
            loaded = {}

        return self._deep_merge(deepcopy(self.DEFAULT_SETTINGS), loaded)

    def save(self, settings: dict[str, Any] | None) -> dict[str, Any]:
        """
        Save settings while preserving unrelated existing keys.
        """

        current = self._read_json_file(self.settings_path)

        if not isinstance(current, dict):
            current = {}

        incoming = settings if isinstance(settings, dict) else {}
        merged = self._deep_merge(current, incoming)
        complete = self._deep_merge(deepcopy(self.DEFAULT_SETTINGS), merged)

        self.settings_path.parent.mkdir(parents=True, exist_ok=True)
        self.settings_path.write_text(
            json.dumps(complete, indent=2, sort_keys=True),
            encoding="utf-8",
        )

        return complete

    def provider_status(self) -> dict[str, Any]:
        """
        Return display-safe provider configuration and API key status.
        """

        provider_config = ProviderConfig.load(self.provider_config_path)
        enabled_providers = [
            name
            for name in sorted(provider_config.providers)
            if provider_config.is_enabled(name)
        ]

        api_key_status = {
            provider_name: self._configured_label(os.getenv(environment_name))
            for provider_name, environment_name in self.API_KEY_ENVIRONMENT.items()
        }
        api_key_status["SEC EDGAR"] = "Configured"

        return {
            "current_provider": provider_config.active_provider,
            "enabled_providers": enabled_providers,
            "api_key_status": api_key_status,
        }

    @classmethod
    def _deep_merge(
        cls,
        base: dict[str, Any],
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        for key, value in updates.items():
            if (
                isinstance(value, dict)
                and isinstance(base.get(key), dict)
            ):
                base[key] = cls._deep_merge(dict(base[key]), value)
            else:
                base[key] = value

        return base

    @staticmethod
    def _read_json_file(path: Path) -> Any:
        if not path.exists():
            return {}

        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    @staticmethod
    def _configured_label(value: str | None) -> str:
        if value and value.strip():
            return "Configured"

        return "Not Configured"
