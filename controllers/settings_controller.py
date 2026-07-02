from __future__ import annotations

from typing import Any

from services.settings_service import SettingsService


class SettingsController:
    """
    Thin controller for application settings.
    """

    def __init__(self, settings_service: SettingsService | None = None) -> None:
        self.settings_service = settings_service or SettingsService()

    def load_settings(self) -> dict[str, Any]:
        return self.settings_service.load()

    def save_settings(self, settings: dict[str, Any]) -> dict[str, Any]:
        return self.settings_service.save(settings)

    def provider_status(self) -> dict[str, Any]:
        return self.settings_service.provider_status()
