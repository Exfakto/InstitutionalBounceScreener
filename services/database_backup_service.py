from __future__ import annotations

import shutil
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class BackupResult:
    success: bool
    message: str
    path: str | None = None


class DatabaseBackupService:
    def __init__(self, database_path, backup_directory="backups"):
        self.database_path = Path(database_path)
        self.backup_directory = Path(backup_directory)

    def backup(self, timestamp=None):
        if not self.database_path.exists():
            return BackupResult(False, f"Database not found: {self.database_path}")
        try:
            self.backup_directory.mkdir(parents=True, exist_ok=True)
            destination = self.backup_path(timestamp=timestamp)
            shutil.copy2(self.database_path, destination)
            if not self.validate_backup(destination):
                destination.unlink(missing_ok=True)
                return BackupResult(False, "Backup validation failed", str(destination))
            return BackupResult(True, "Database backup created", str(destination))
        except OSError as exc:
            return BackupResult(False, f"Backup failed: {exc}")

    def restore(self, backup_path):
        source = Path(backup_path)
        if not source.exists():
            return BackupResult(False, f"Backup not found: {source}")
        if not self.validate_backup(source):
            return BackupResult(False, "Backup validation failed", str(source))
        try:
            self.database_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, self.database_path)
            return BackupResult(True, "Database restored from backup", str(source))
        except OSError as exc:
            return BackupResult(False, f"Restore failed: {exc}", str(source))

    def validate_backup(self, backup_path):
        try:
            connection = sqlite3.connect(str(backup_path))
            try:
                row = connection.execute("PRAGMA integrity_check").fetchone()
                return bool(row and row[0] == "ok")
            finally:
                connection.close()
        except sqlite3.Error:
            return False

    def backup_path(self, timestamp=None):
        stamp = timestamp or datetime.now().strftime("%Y%m%d_%H%M%S")
        return self.backup_directory / f"{self.database_path.stem}_{stamp}.db"
