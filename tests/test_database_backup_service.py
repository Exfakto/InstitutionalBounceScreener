import sqlite3
from pathlib import Path

from services.database_backup_service import DatabaseBackupService
from tests.release_test_utils import create_sqlite


def test_database_backup_creates_timestamped_valid_backup(tmp_path):
    database_path = create_sqlite(tmp_path / "data" / "app.db")
    service = DatabaseBackupService(database_path, tmp_path / "backups")

    result = service.backup(timestamp="20260704_120000")

    assert result.success is True
    assert Path(result.path).name == "app_20260704_120000.db"
    assert service.validate_backup(result.path) is True


def test_database_restore_restores_valid_backup(tmp_path):
    database_path = create_sqlite(tmp_path / "data" / "app.db")
    service = DatabaseBackupService(database_path, tmp_path / "backups")
    backup = service.backup(timestamp="20260704_120000")

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


def test_database_backup_service_rejects_missing_or_invalid_files(tmp_path):
    missing = DatabaseBackupService(tmp_path / "missing.db", tmp_path / "backups").backup()
    assert missing.success is False
    assert "Database not found" in missing.message

    database_path = create_sqlite(tmp_path / "data" / "app.db")
    invalid = tmp_path / "invalid.db"
    invalid.write_text("not sqlite", encoding="utf-8")
    restore = DatabaseBackupService(database_path, tmp_path / "backups").restore(invalid)

    assert restore.success is False
    assert "validation failed" in restore.message.lower()
