import sqlite3

from database.manager import DatabaseManager
from services.app_settings_repository import AppSettingsRepository
from services.app_settings_service import AppPreferences, AppSettingsService


def build_manager():
    manager = DatabaseManager.__new__(DatabaseManager)
    manager.connection = sqlite3.connect(":memory:")
    manager.connection.row_factory = sqlite3.Row
    manager.cursor = manager.connection.cursor()
    manager.initialize()
    return manager


def test_app_settings_table_created():
    manager = build_manager()

    manager.cursor.execute("PRAGMA table_info(app_settings)")
    columns = {row["name"] for row in manager.cursor.fetchall()}

    assert {"key", "value_json", "updated_at"}.issubset(columns)
    manager.close()


def test_app_settings_repository_set_get_delete():
    manager = build_manager()
    repository = AppSettingsRepository(manager)

    repository.set_setting("scan", {"mode": "Universe scan mode"})

    assert repository.get_setting("scan") == {"mode": "Universe scan mode"}
    assert repository.get_all_settings()["scan"] == {"mode": "Universe scan mode"}
    assert repository.delete_setting("scan") == 1
    assert repository.get_setting("scan", default="missing") == "missing"
    manager.close()


def test_app_settings_service_typed_defaults():
    manager = build_manager()
    service = AppSettingsService(AppSettingsRepository(manager))

    preferences = service.get_preferences()

    assert isinstance(preferences, AppPreferences)
    assert preferences.default_scan_mode == "Manual ticker input"
    assert preferences.max_scan_size == 250
    assert preferences.ui_density == "NORMAL"
    assert preferences.show_rejected_candidates is True
    assert preferences.selected_market_data_provider == "local_csv"
    assert preferences.request_timeout_seconds == 10
    manager.close()


def test_app_settings_service_validation():
    manager = build_manager()
    service = AppSettingsService(AppSettingsRepository(manager))

    preferences = service.save_preferences(
        {
            "default_scan_mode": "bad",
            "max_scan_size": -10,
            "large_scan_warning_threshold": 9999,
            "ui_density": "wide",
            "auto_refresh_results": False,
            "selected_market_data_provider": "bad",
            "request_timeout_seconds": -1,
            "max_retries": -1,
            "rate_limit_sleep_seconds": -1,
        }
    )

    assert preferences.default_scan_mode == "Manual ticker input"
    assert preferences.max_scan_size == 250
    assert preferences.large_scan_warning_threshold == 250
    assert preferences.ui_density == "NORMAL"
    assert preferences.auto_refresh_results is False
    assert preferences.selected_market_data_provider == "local_csv"
    assert preferences.request_timeout_seconds == 10
    assert preferences.max_retries == 3
    assert preferences.rate_limit_sleep_seconds == 1
    assert preferences.historical_ohlcv_lookback_years == 5
    manager.close()


def test_app_settings_service_provider_credentials_persist():
    manager = build_manager()
    service = AppSettingsService(AppSettingsRepository(manager))

    preferences = service.save_preferences(
        {
            "selected_market_data_provider": "polygon",
            "polygon_api_key": "polygon-key",
            "fmp_api_key": "fmp-key",
            "alpaca_api_key": "alpaca-key",
            "alpaca_api_secret": "alpaca-secret",
            "request_timeout_seconds": 7,
            "max_retries": 3,
            "rate_limit_sleep_seconds": 2,
            "historical_ohlcv_lookback_years": 4,
        }
    )

    assert preferences.selected_market_data_provider == "polygon"
    assert preferences.polygon_api_key == "polygon-key"
    assert preferences.alpaca_api_secret == "alpaca-secret"
    assert preferences.request_timeout_seconds == 7
    assert preferences.max_retries == 3
    assert preferences.rate_limit_sleep_seconds == 2
    assert preferences.historical_ohlcv_lookback_years == 4
    manager.close()
