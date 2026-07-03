from __future__ import annotations

import sys
from pathlib import Path


class ResourcePathService:
    """
    Resolve resource paths consistently in dev mode and PyInstaller bundles.
    """

    def __init__(self, base_path: str | Path | None = None):
        self.base_path = Path(base_path) if base_path is not None else self.default_base_path()

    @staticmethod
    def default_base_path():
        packaged_root = getattr(sys, "_MEIPASS", None)
        if packaged_root:
            return Path(packaged_root)
        return Path(__file__).resolve().parents[1]

    @staticmethod
    def is_packaged():
        return bool(getattr(sys, "frozen", False))

    def path(self, *parts):
        return self.base_path.joinpath(*[str(part) for part in parts])

    def exists(self, *parts):
        return self.path(*parts).exists()

    def default_config_path(self, filename="providers.json"):
        return self.path("config", filename)

    def icon_path(self):
        return self.path("resources", "app_icon.ico")
