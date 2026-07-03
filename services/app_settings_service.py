from __future__ import annotations

from dataclasses import asdict, dataclass

from services.app_settings_repository import AppSettingsRepository


VALID_SCAN_MODES = {"Manual ticker input", "Universe scan mode"}
VALID_UI_DENSITIES = {"COMPACT", "NORMAL", "COMFORTABLE"}


@dataclass(frozen=True)
class AppPreferences:
    default_scan_mode: str = "Manual ticker input"
    default_scan_preset: str = "Institutional Quality"
    max_scan_size: int = 250
    large_scan_warning_threshold: int = 100
    default_export_directory: str = "exports/results"
    ui_density: str = "NORMAL"
    auto_refresh_results: bool = True
    show_rejected_candidates: bool = True


class AppSettingsService:
    """
    Typed preference service for database-backed application settings.
    """

    SETTINGS_KEY = "preferences"
    DEFAULTS = AppPreferences()

    def __init__(self, repository=None):
        self.repository = repository or AppSettingsRepository()

    def get_preferences(self):
        stored = self.repository.get_setting(self.SETTINGS_KEY, default={})
        return self.validate_preferences(stored)

    def save_preferences(self, preferences):
        validated = self.validate_preferences(preferences)
        self.repository.set_setting(self.SETTINGS_KEY, asdict(validated))
        return validated

    def reset_preferences(self):
        self.repository.set_setting(self.SETTINGS_KEY, asdict(self.DEFAULTS))
        return self.DEFAULTS

    def set_setting(self, key, value):
        preferences = asdict(self.get_preferences())
        preferences[key] = value
        return self.save_preferences(preferences)

    def get_setting(self, key, default=None):
        return getattr(self.get_preferences(), key, default)

    @classmethod
    def validate_preferences(cls, preferences):
        data = asdict(cls.DEFAULTS)
        if isinstance(preferences, AppPreferences):
            preferences = asdict(preferences)
        if isinstance(preferences, dict):
            data.update(preferences)

        scan_mode = str(data.get("default_scan_mode") or cls.DEFAULTS.default_scan_mode)
        if scan_mode not in VALID_SCAN_MODES:
            scan_mode = cls.DEFAULTS.default_scan_mode

        ui_density = str(data.get("ui_density") or cls.DEFAULTS.ui_density).upper()
        if ui_density not in VALID_UI_DENSITIES:
            ui_density = cls.DEFAULTS.ui_density

        max_scan_size = cls.positive_int(
            data.get("max_scan_size"),
            cls.DEFAULTS.max_scan_size,
        )
        large_scan_warning_threshold = cls.positive_int(
            data.get("large_scan_warning_threshold"),
            cls.DEFAULTS.large_scan_warning_threshold,
        )
        large_scan_warning_threshold = min(
            large_scan_warning_threshold,
            max_scan_size,
        )

        return AppPreferences(
            default_scan_mode=scan_mode,
            default_scan_preset=str(
                data.get("default_scan_preset")
                or cls.DEFAULTS.default_scan_preset
            ),
            max_scan_size=max_scan_size,
            large_scan_warning_threshold=large_scan_warning_threshold,
            default_export_directory=str(
                data.get("default_export_directory")
                or cls.DEFAULTS.default_export_directory
            ),
            ui_density=ui_density,
            auto_refresh_results=bool(data.get("auto_refresh_results", True)),
            show_rejected_candidates=bool(data.get("show_rejected_candidates", True)),
        )

    @staticmethod
    def positive_int(value, default):
        try:
            number = int(value)
        except (TypeError, ValueError):
            return default
        return number if number > 0 else default
