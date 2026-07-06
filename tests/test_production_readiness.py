import logging
import sqlite3
import sys
from pathlib import Path

from config.app_metadata import APPLICATION_NAME, BUILD_DATE, SCHEMA_VERSION, VERSION
from config.logging_config import configure_logging
from database.manager import DatabaseManager
from services.app_config_service import AppConfig, AppConfigService
from services.exception_handler import GlobalExceptionHandler
from services.health_check_service import HealthCheckService
from services.startup_diagnostics_service import StartupDiagnosticsService


def build_manager(path):
    return DatabaseManager(path)


def test_release_metadata_constants():
    assert APPLICATION_NAME == "Institutional Bounce Platform"
    assert VERSION == "v2.2.0 RC"
    assert BUILD_DATE == "Release Candidate"
    assert SCHEMA_VERSION == "1"


def test_logging_initialization(tmp_path):
    root = configure_logging(level="DEBUG", log_dir=tmp_path, log_file="app.log")

    assert root.level == logging.DEBUG
    assert len(root.handlers) == 2
    assert (tmp_path / "app.log").exists()


def test_app_config_validation(tmp_path):
    config = AppConfig(
        database_path=tmp_path / "data" / "app.db",
        export_directory=tmp_path / "exports",
        log_directory=tmp_path / "logs",
        data_directory=tmp_path / "data",
        config_directory=tmp_path / "config",
    )
    service = AppConfigService(config)

    result = service.validate()

    assert result.valid is True
    assert (tmp_path / "exports").exists()
    assert result.checked_paths["export_directory"].endswith("exports")


def test_startup_diagnostics(tmp_path):
    config = AppConfig(
        database_path=tmp_path / "data" / "app.db",
        export_directory=tmp_path / "exports",
        log_directory=tmp_path / "logs",
        data_directory=tmp_path / "data",
        config_directory=tmp_path / "config",
    )
    service = StartupDiagnosticsService(
        config_service=AppConfigService(config),
        database_factory=build_manager,
    )

    report = service.run()

    assert report.status in {"PASS", "WARNING"}
    assert any(check.name == "database_connectivity" for check in report.checks)
    assert any(check.name == "settings_table" for check in report.checks)


def test_health_check_service(tmp_path):
    config = AppConfig(
        database_path=tmp_path / "data" / "app.db",
        export_directory=tmp_path / "exports",
        log_directory=tmp_path / "logs",
        data_directory=tmp_path / "data",
        config_directory=tmp_path / "config",
    )
    service = HealthCheckService(
        config_service=AppConfigService(config),
        database_factory=build_manager,
    )

    report = service.run()

    assert report.status in {"PASS", "WARNING"}
    assert any(check.name == "database" for check in report.checks)
    assert any(check.name == "export_service" for check in report.checks)


def test_exception_handler_registration(monkeypatch):
    captured = []
    logger = logging.getLogger("test_exception_handler")
    monkeypatch.setattr(logger, "error", lambda *args, **kwargs: captured.append(args))
    handler = GlobalExceptionHandler(logger=logger, dialog_factory=lambda *args: None)

    handler.register()
    try:
        assert sys.excepthook == handler.handle_exception
        handler.handle_exception(RuntimeError, RuntimeError("planned"), None)
        assert captured
    finally:
        sys.excepthook = handler.previous_hook
