from __future__ import annotations

from typing import Any

from services.settings_service import SettingsService
from services.app_settings_service import AppSettingsService


class SettingsController:
    """
    Thin controller for application settings.
    """

    def __init__(
        self,
        settings_service: SettingsService | None = None,
        app_settings_service: AppSettingsService | None = None,
    ) -> None:
        self.settings_service = settings_service or SettingsService()
        self.app_settings_service = app_settings_service

    def load_settings(self) -> dict[str, Any]:
        return self.settings_service.load()

    def save_settings(self, settings: dict[str, Any]) -> dict[str, Any]:
        return self.settings_service.save(settings)

    def provider_status(self) -> dict[str, Any]:
        return self.settings_service.provider_status()

    def load_app_preferences(self):
        return self.app_preferences_service().get_preferences()

    def save_app_preferences(self, preferences):
        return self.app_preferences_service().save_preferences(preferences)

    def reset_app_preferences(self):
        return self.app_preferences_service().reset_preferences()

    def app_preferences_service(self):
        if self.app_settings_service is None:
            self.app_settings_service = AppSettingsService()
        return self.app_settings_service
