from __future__ import annotations

import os
from dataclasses import asdict, dataclass, field, is_dataclass


@dataclass(frozen=True)
class ProviderDiagnosticsResult:
    selected_provider: str = "local_csv"
    resolved_provider: str | None = None
    provider_class: str | None = None
    credential_status: str = "Unknown"
    connectivity_status: str = "Not tested"
    local_csv_available: bool = False
    request_timeout_seconds: int | None = None
    max_retries: int | None = None
    rate_limit_sleep_seconds: int | None = None
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class ProviderDiagnosticsService:
    def __init__(self, settings_service=None, provider_factory=None):
        self.settings_service = settings_service
        self.provider_factory = provider_factory

    def run(self, connectivity_test=False):
        settings = self.settings()
        provider = str(settings.get("selected_market_data_provider") or "local_csv")
        factory_result = self.create_provider()
        if factory_result is not None and getattr(factory_result, "provider_name", None):
            resolved_provider = factory_result.provider_name
            provider_object = getattr(factory_result, "provider", None)
            provider_class = type(provider_object).__name__ if provider_object is not None else None
        else:
            resolved_provider = provider
            provider_class = None
        warnings = []
        errors = []
        credential_status = self.credential_status(provider, settings)
        if credential_status != "Configured":
            warnings.append(credential_status)

        connectivity_status = "Not tested"
        if connectivity_test:
            connectivity_status = self.test_connectivity(factory_result)
            if connectivity_status != "PASS":
                warnings.append(connectivity_status)

        return ProviderDiagnosticsResult(
            selected_provider=provider,
            resolved_provider=resolved_provider,
            provider_class=provider_class,
            credential_status=credential_status,
            connectivity_status=connectivity_status,
            local_csv_available=provider == "local_csv" or self.local_csv_available(settings),
            request_timeout_seconds=settings.get("request_timeout_seconds"),
            max_retries=settings.get("max_retries"),
            rate_limit_sleep_seconds=settings.get("rate_limit_sleep_seconds"),
            warnings=self.unique(warnings),
            errors=errors,
        )

    def settings(self):
        if self.settings_service is None:
            return {}
        if hasattr(self.settings_service, "get_all_preferences"):
            return self.as_mapping(self.settings_service.get_all_preferences())
        if hasattr(self.settings_service, "get_preferences"):
            return self.as_mapping(self.settings_service.get_preferences())
        if hasattr(self.settings_service, "get_all_settings"):
            return self.settings_service.get_all_settings()
        return {}

    def create_provider(self):
        if self.provider_factory is None or not hasattr(self.provider_factory, "create"):
            return None
        return self.provider_factory.create()

    def test_connectivity(self, factory_result=None):
        if self.provider_factory is None or not hasattr(self.provider_factory, "create"):
            return "No provider factory configured"
        result = factory_result if factory_result is not None else self.provider_factory.create()
        if not getattr(result, "success", False):
            errors = getattr(result, "errors", []) or []
            return "; ".join(errors) if errors else "Provider unavailable"
        provider = getattr(result, "provider", None)
        if provider is None:
            return "Provider unavailable"
        if hasattr(provider, "get_last_updated"):
            try:
                provider.get_last_updated()
            except Exception as exc:
                return str(exc)
        return "PASS"

    @staticmethod
    def as_mapping(settings):
        if is_dataclass(settings):
            return asdict(settings)
        return settings if isinstance(settings, dict) else {}

    @staticmethod
    def credential_status(provider, settings):
        provider = str(provider or "local_csv")
        if provider == "local_csv":
            return "Configured"
        if provider == "polygon":
            return "Configured" if credential(settings, "polygon_api_key", "POLYGON_API_KEY") else "Polygon API key missing"
        if provider == "fmp":
            return "Configured" if credential(settings, "fmp_api_key", "FMP_API_KEY") else "FMP API key missing"
        if provider == "alpaca":
            if not credential(settings, "alpaca_api_key", "ALPACA_API_KEY"):
                return "Alpaca API key missing"
            if not credential(settings, "alpaca_api_secret", "ALPACA_API_SECRET"):
                return "Alpaca API secret missing"
            return "Configured"
        return "Unknown provider"

    @staticmethod
    def local_csv_available(settings):
        return bool(settings.get("local_csv_directory") or settings.get("market_data_directory"))

    @staticmethod
    def unique(values):
        result = []
        for value in values or []:
            if value and value not in result:
                result.append(value)
        return result


def credential(settings, key, environment_key):
    value = str(settings.get(key) or "").strip()
    if value:
        return value
    return str(os.getenv(environment_key) or "").strip()
