from __future__ import annotations

import json

from database.manager import DatabaseManager


class AppSettingsRepository:
    """
    SQLite-backed key/value repository for application preferences.
    """

    def __init__(self, db=None):
        self.db = db or DatabaseManager()

    def set_setting(self, key, value):
        normalized_key = self.normalize_key(key)
        if not normalized_key:
            return None

        self.db.cursor.execute(
            """
            INSERT INTO app_settings (key, value_json, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET
                value_json = excluded.value_json,
                updated_at = CURRENT_TIMESTAMP
            """,
            (normalized_key, json.dumps(value, sort_keys=True)),
        )
        self.db.connection.commit()
        return value

    def get_setting(self, key, default=None):
        normalized_key = self.normalize_key(key)
        if not normalized_key:
            return default

        self.db.cursor.execute(
            """
            SELECT value_json
            FROM app_settings
            WHERE key = ?
            """,
            (normalized_key,),
        )
        row = self.db.cursor.fetchone()
        if row is None:
            return default

        try:
            return json.loads(row["value_json"])
        except (TypeError, json.JSONDecodeError):
            return default

    def get_all_settings(self):
        self.db.cursor.execute(
            """
            SELECT key, value_json
            FROM app_settings
            ORDER BY key ASC
            """
        )
        settings = {}
        for row in self.db.cursor.fetchall():
            try:
                settings[row["key"]] = json.loads(row["value_json"])
            except (TypeError, json.JSONDecodeError):
                settings[row["key"]] = None
        return settings

    def delete_setting(self, key):
        normalized_key = self.normalize_key(key)
        if not normalized_key:
            return 0

        self.db.cursor.execute(
            """
            DELETE FROM app_settings
            WHERE key = ?
            """,
            (normalized_key,),
        )
        deleted = self.db.cursor.rowcount
        self.db.connection.commit()
        return deleted

    @staticmethod
    def normalize_key(key):
        return str(key or "").strip()
