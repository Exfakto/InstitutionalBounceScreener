import sqlite3
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from config.app_metadata import BUILD_TIMESTAMP, RELEASE_CHANNEL
from services.app_config_service import AppConfig, AppConfigService
from services.database_backup_service import DatabaseBackupService
from services.release_checklist_service import ReleaseChecklistService
from services.release_diagnostics_service import ReleaseDiagnosticsService
from services.release_metadata_service import ReleaseMetadataService
from services.resource_path_service import ResourcePathService
from ui.about_dialog import AboutDialog


def create_sqlite(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.execute("CREATE TABLE sample (id INTEGER PRIMARY KEY, name TEXT)")
    connection.execute("INSERT INTO sample (name) VALUES ('original')")
    connection.commit()
    connection.close()


def test_resource_path_helper_dev_and_packaged_modes(tmp_path, monkeypatch):
    service = ResourcePathService(base_path=tmp_path)
    (tmp_path / "config").mkdir()

    assert service.path("config") == tmp_path / "config"
    assert service.exists("config") is True

    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)

    assert ResourcePathService.is_packaged() is True
    assert ResourcePathService.default_base_path() == tmp_path


def test_database_backup_and_restore_service(tmp_path):
    database_path = tmp_path / "data" / "app.db"
    backup_dir = tmp_path / "backups"
    create_sqlite(database_path)
    service = DatabaseBackupService(database_path, backup_dir)

    backup = service.backup(timestamp="20260703_120000")

    assert backup.success is True
    assert Path(backup.path).name == "app_20260703_120000.db"
    assert service.validate_backup(backup.path) is True

    connection = sqlite3.connect(database_path)
    connection.execute("DELETE FROM sample")
    connection.commit()
    connection.close()

    restore = service.restore(backup.path)

    assert restore.success is True
    connection = sqlite3.connect(database_path)
    count = connection.execute("SELECT COUNT(*) FROM sample").fetchone()[0]
    connection.close()
    assert count == 1


def test_database_restore_rejects_invalid_backup(tmp_path):
    database_path = tmp_path / "data" / "app.db"
    create_sqlite(database_path)
    invalid = tmp_path / "invalid.db"
    invalid.write_text("not sqlite", encoding="utf-8")

    result = DatabaseBackupService(database_path, tmp_path / "backups").restore(invalid)

    assert result.success is False
    assert "validation failed" in result.message.lower()


def test_release_metadata_service():
    metadata = ReleaseMetadataService().metadata()
    summary = ReleaseMetadataService().build_environment_summary()

    assert metadata.build_timestamp == BUILD_TIMESTAMP
    assert metadata.release_channel == RELEASE_CHANNEL
    assert summary["release_channel"] == RELEASE_CHANNEL


def test_release_diagnostics_service(tmp_path):
    config = AppConfig(
        database_path=tmp_path / "data" / "app.db",
        export_directory=tmp_path / "exports",
        log_directory=tmp_path / "logs",
        data_directory=tmp_path / "data",
        config_directory=tmp_path / "config",
    )
    create_sqlite(config.database_path)
    for directory in [config.export_directory, config.log_directory, config.data_directory, config.config_directory]:
        directory.mkdir(parents=True, exist_ok=True)
    resource_root = tmp_path / "bundle"
    for directory in ["config", "data", "docs", "resources"]:
        (resource_root / directory).mkdir(parents=True)

    report = ReleaseDiagnosticsService(
        config_service=AppConfigService(config),
        resource_service=ResourcePathService(resource_root),
    ).run()

    assert report.status in {"PASS", "WARNING"}
    assert any(item.name == "database_backup_health" for item in report.items)
    assert any(item.name == "resources_directory" for item in report.items)


def test_release_checklist_service(tmp_path):
    diagnostics = type(
        "Diagnostics",
        (),
        {"run": lambda self: type("Report", (), {"status": "PASS"})()},
    )()
    (tmp_path / "tests").mkdir()
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "build_release.ps1").write_text("ok", encoding="utf-8")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "BUILD_AND_RELEASE.md").write_text("ok", encoding="utf-8")
    (tmp_path / "docs" / "RELEASE_CHECKLIST.md").write_text("ok", encoding="utf-8")
    (tmp_path / "InstitutionalBounceScreener.spec").write_text("ok", encoding="utf-8")

    report = ReleaseChecklistService(
        diagnostics_service=diagnostics,
        project_root=tmp_path,
    ).run()

    assert report.status == "PASS"
    assert "release checks passing" in report.summary


def test_build_configuration_files_exist():
    assert Path("app_entry.py").exists()
    assert Path("InstitutionalBounceScreener.spec").exists()
    assert Path("scripts/build_release.ps1").exists()
    assert Path("scripts/run_release_checks.ps1").exists()
    assert Path("docs/BUILD_AND_RELEASE.md").exists()
    assert Path("docs/RELEASE_CHECKLIST.md").exists()


class FakeDiagnosticsController:
    def get_diagnostics(self):
        return {
            "app_name": "Institutional Bounce Screener",
            "version": "4.0.0",
            "build_date": "2026-07-03",
            "build_timestamp": "2026-07-03T00:00:00Z",
            "release_channel": "dev",
            "schema_version": "1",
        }

    def diagnostics_text(self):
        return "diagnostics"

    def startup_report(self):
        return None

    def health_report(self):
        return None


def test_about_dialog_release_ui_construction(monkeypatch, tmp_path):
    app = QApplication.instance() or QApplication([])
    database_path = tmp_path / "data" / "app.db"
    create_sqlite(database_path)

    config_service = AppConfigService(
        AppConfig(
            database_path=database_path,
            export_directory=tmp_path / "exports",
            log_directory=tmp_path / "logs",
            data_directory=tmp_path / "data",
            config_directory=tmp_path / "config",
        )
    )
    dialog = AboutDialog(controller=FakeDiagnosticsController())
    dialog.config_service = config_service
    dialog._render_release_readiness()

    assert dialog.release_group.title() == "Release Readiness"
    assert dialog.release_labels["release_channel"].text() == "dev"
    assert dialog.backup_database_button.text() == "Backup Database"
    assert dialog.restore_database_button.text() == "Restore Database"
    assert app is not None
