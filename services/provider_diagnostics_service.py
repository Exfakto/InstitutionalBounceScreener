from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ProviderDiagnosticsResult:
    selected_provider: str = "local_csv"
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
        warnings = []
        errors = []
        credential_status = self.credential_status(provider, settings)
        if credential_status != "Configured":
            warnings.append(credential_status)

        connectivity_status = "Not tested"
        if connectivity_test:
            connectivity_status = self.test_connectivity()
            if connectivity_status != "PASS":
                warnings.append(connectivity_status)

        return ProviderDiagnosticsResult(
            selected_provider=provider,
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
            return self.settings_service.get_all_preferences()
        if hasattr(self.settings_service, "get_preferences"):
            return self.settings_service.get_preferences()
        if hasattr(self.settings_service, "get_all_settings"):
            return self.settings_service.get_all_settings()
        return {}

    def test_connectivity(self):
        if self.provider_factory is None or not hasattr(self.provider_factory, "create"):
            return "No provider factory configured"
        result = self.provider_factory.create()
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
    def credential_status(provider, settings):
        provider = str(provider or "local_csv")
        if provider == "local_csv":
            return "Configured"
        if provider == "polygon":
            return "Configured" if settings.get("polygon_api_key") else "Polygon API key missing"
        if provider == "fmp":
            return "Configured" if settings.get("fmp_api_key") else "FMP API key missing"
        if provider == "alpaca":
            if not settings.get("alpaca_api_key"):
                return "Alpaca API key missing"
            if not settings.get("alpaca_api_secret"):
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
