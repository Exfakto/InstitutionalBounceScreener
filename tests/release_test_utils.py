import sqlite3
from pathlib import Path

from services.app_config_service import AppConfig


def create_sqlite(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.execute("CREATE TABLE sample (id INTEGER PRIMARY KEY, name TEXT)")
    connection.execute("INSERT INTO sample (name) VALUES ('original')")
    connection.commit()
    connection.close()
    return path


def app_config(tmp_path):
    return AppConfig(
        database_path=tmp_path / "data" / "app.db",
        export_directory=tmp_path / "exports",
        log_directory=tmp_path / "logs",
        data_directory=tmp_path / "data",
        config_directory=tmp_path / "config",
    )


def prepare_resource_root(path):
    for directory in ["config", "data", "docs", "resources"]:
        (Path(path) / directory).mkdir(parents=True, exist_ok=True)
    return Path(path)
