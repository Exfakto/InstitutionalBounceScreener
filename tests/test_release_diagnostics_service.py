from pathlib import Path

from services.app_config_service import AppConfigService
from services.release_diagnostics_service import ReleaseDiagnosticsService
from services.resource_path_service import ResourcePathService
from tests.release_test_utils import app_config, create_sqlite, prepare_resource_root


def test_release_diagnostics_reports_resource_and_database_health(tmp_path):
    config = app_config(tmp_path)
    create_sqlite(config.database_path)
    for directory in [
        config.export_directory,
        config.log_directory,
        config.data_directory,
        config.config_directory,
    ]:
        directory.mkdir(parents=True, exist_ok=True)
    resource_root = prepare_resource_root(tmp_path / "bundle")

    report = ReleaseDiagnosticsService(
        config_service=AppConfigService(config),
        resource_service=ResourcePathService(resource_root),
    ).run()

    assert report.status in {"PASS", "WARNING"}
    item_names = {item.name for item in report.items}
    assert {"packaged_mode", "resources_directory", "database_backup_health"}.issubset(item_names)
    assert any(item.name == "database_backup_health" and item.status == "PASS" for item in report.items)


def test_release_diagnostics_warns_for_missing_database(tmp_path):
    config = app_config(tmp_path)
    resource_root = prepare_resource_root(tmp_path / "bundle")

    report = ReleaseDiagnosticsService(
        config_service=AppConfigService(config),
        resource_service=ResourcePathService(resource_root),
    ).run()

    assert report.status == "WARNING"
    assert any("Database file does not exist" in warning for warning in report.warnings)


def test_release_diagnostics_fails_for_invalid_database(tmp_path):
    config = app_config(tmp_path)
    config.database_path.parent.mkdir(parents=True)
    config.database_path.write_text("not sqlite", encoding="utf-8")
    resource_root = prepare_resource_root(tmp_path / "bundle")

    report = ReleaseDiagnosticsService(
        config_service=AppConfigService(config),
        resource_service=ResourcePathService(resource_root),
    ).run()

    assert report.status == "FAIL"
    assert any("integrity check failed" in error.lower() for error in report.errors)
