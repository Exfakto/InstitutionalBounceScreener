from __future__ import annotations

from copy import deepcopy
from typing import Any


class ScreenerPresetController:
    """
    Lightweight controller for UI screener preset state.
    """

    def __init__(self) -> None:
        self.presets: dict[str, dict[str, Any]] = {}
        self.active_preset: str | None = None

    def save_preset(self, name: str = "Default", filters: dict[str, Any] | None = None):
        preset_name = self.normalize_name(name)
        self.presets[preset_name] = deepcopy(filters or {})
        self.active_preset = preset_name
        return {
            "success": True,
            "message": f"Preset saved: {preset_name}",
            "name": preset_name,
            "filters": deepcopy(self.presets[preset_name]),
        }

    def load_preset(self, name: str | None = None):
        preset_name = self.normalize_name(name or self.active_preset or "Default")
        filters = deepcopy(self.presets.get(preset_name, {}))
        self.active_preset = preset_name if preset_name in self.presets else None
        return {
            "success": preset_name in self.presets,
            "message": (
                f"Preset loaded: {preset_name}"
                if preset_name in self.presets
                else "Preset not found."
            ),
            "name": self.active_preset,
            "filters": filters,
        }

    def reset_filters(self):
        self.active_preset = None
        return {
            "success": True,
            "message": "Screener filters reset.",
            "name": None,
            "filters": {},
        }

    @staticmethod
    def normalize_name(name: str | None) -> str:
        normalized = str(name or "").strip()
        return normalized or "Default"
