from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class ProviderConfig:
    """
    Safe provider configuration wrapper.
    """

    active_provider: str = "local"
    providers: dict = field(default_factory=lambda: {"local": {"enabled": True}})
    source_path: str | None = None
    warnings: list[str] = field(default_factory=list)

    @classmethod
    def load(cls, path="config/providers.json"):
        config_path = Path(path)

        if not config_path.exists():
            return cls(
                source_path=str(config_path),
                warnings=["Provider config not found; using defaults."],
            )

        try:
            payload = json.loads(config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return cls(
                source_path=str(config_path),
                warnings=["Provider config malformed; using defaults."],
            )

        if not isinstance(payload, dict):
            return cls(
                source_path=str(config_path),
                warnings=["Provider config malformed; using defaults."],
            )

        active_provider = cls.normalize_name(payload.get("active_provider")) or "local"
        providers = payload.get("providers")

        if not isinstance(providers, dict):
            providers = {"local": {"enabled": True}}

        if "local" not in providers:
            providers = dict(providers)
            providers["local"] = {"enabled": True}

        return cls(
            active_provider=active_provider,
            providers=providers,
            source_path=str(config_path),
            warnings=[],
        )

    def provider_settings(self, name):
        normalized_name = self.normalize_name(name)

        if normalized_name is None:
            return {}

        settings = self.providers.get(normalized_name, {})

        if not isinstance(settings, dict):
            return {}

        return dict(settings)

    def is_enabled(self, name):
        settings = self.provider_settings(name)

        return bool(settings.get("enabled", False))

    @staticmethod
    def normalize_name(name):
        if name is None:
            return None

        normalized = str(name).strip().lower()

        if not normalized:
            return None

        return normalized
