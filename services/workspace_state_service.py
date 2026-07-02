from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any


class WorkspaceStateService:
    """
    JSON-backed persistence for non-secret workspace UI state.
    """

    DEFAULT_STATE: dict[str, Any] = {
        "window": {
            "size": [1600, 900],
            "position": None,
            "maximized": False,
        },
        "splitters": {},
        "active_layout": "Default",
        "dock_state": None,
        "dock_visibility": {},
        "dock_floating": {},
        "selected_ticker": None,
        "active_tab": None,
        "active_workspace": None,
        "active_screener_preset": None,
    }

    def __init__(
        self,
        state_path: str | Path = "config/workspace_state.json",
    ) -> None:
        self.state_path = Path(state_path)

    def load_state(self) -> dict[str, Any]:
        loaded = self._read_state()

        if not isinstance(loaded, dict):
            loaded = {}

        return self._deep_merge(deepcopy(self.DEFAULT_STATE), loaded)

    def save_state(self, state: dict[str, Any] | None) -> dict[str, Any]:
        current = self._read_state()

        if not isinstance(current, dict):
            current = {}

        incoming = state if isinstance(state, dict) else {}
        merged = self._deep_merge(current, incoming)
        complete = self._deep_merge(deepcopy(self.DEFAULT_STATE), merged)

        try:
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            self.state_path.write_text(
                json.dumps(complete, indent=2, sort_keys=True),
                encoding="utf-8",
            )
        except OSError:
            return complete

        return complete

    def clear_state(self) -> dict[str, Any]:
        try:
            if self.state_path.exists():
                self.state_path.unlink()
        except OSError:
            pass

        return deepcopy(self.DEFAULT_STATE)

    def _read_state(self) -> Any:
        if not self.state_path.exists():
            return {}

        try:
            return json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, TypeError):
            return {}

    @classmethod
    def _deep_merge(
        cls,
        base: dict[str, Any],
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        for key, value in updates.items():
            if isinstance(value, dict) and isinstance(base.get(key), dict):
                base[key] = cls._deep_merge(dict(base[key]), value)
            else:
                base[key] = value

        return base
