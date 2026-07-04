from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass


VALIDATION_PASSED = "Passed"
VALIDATION_WARNING = "Warning"
VALIDATION_FAILED = "Failed"
LIVE_PROVIDERS = {"polygon", "fmp", "alpaca"}


@dataclass(frozen=True)
class ProviderConfigurationIssue:
    status: str
    message: str
    affected_setting: str
    recommended_fix: str


@dataclass(frozen=True)
class ProviderConfigurationValidationResult:
    status: str
    issues: list[ProviderConfigurationIssue] = field(default_factory=list)

    @property
    def passed(self):
        return self.status == VALIDATION_PASSED


class ProviderConfigurationValidationService:
    """Validate live market data provider configuration before screening."""

    def __init__(self, settings_service=None, resilience_service=None):
        self.settings_service = settings_service
        self.resilience_service = resilience_service

    def validate(self, settings=None, health=None):
        settings = self.normalize_settings(settings if settings is not None else self.settings())
        health = list(health if health is not None else self.provider_health())
        issues = []

        provider = str(settings.get("selected_market_data_provider") or "local_csv").lower()
        issues.extend(self.validate_credentials(provider, settings))
        issues.extend(self.validate_endpoints(provider, settings))
        issues.extend(self.validate_timeout(settings))
        issues.extend(self.validate_retries(settings))
        issues.extend(self.validate_rate_limit(settings))
        issues.extend(self.validate_failover(provider, health))
        issues.extend(self.validate_health(provider, health))

        status = self.overall_status(issues)
        return ProviderConfigurationValidationResult(status=status, issues=issues)

    def settings(self):
        if self.settings_service is None:
            return {}
        if hasattr(self.settings_service, "get_preferences"):
            return self.settings_service.get_preferences()
        if hasattr(self.settings_service, "get_all_preferences"):
            return self.settings_service.get_all_preferences()
        if hasattr(self.settings_service, "get_all_settings"):
            return self.settings_service.get_all_settings()
        return {}

    def provider_health(self):
        if self.resilience_service is None or not hasattr(
            self.resilience_service, "all_health"
        ):
            return []
        return self.resilience_service.all_health() or []

    def validate_credentials(self, provider, settings):
        if provider == "local_csv":
            return []
        missing = []
        if provider == "polygon" and not settings.get("polygon_api_key"):
            missing.append(("polygon_api_key", "Polygon API key is required"))
        elif provider == "fmp" and not settings.get("fmp_api_key"):
            missing.append(("fmp_api_key", "FMP API key is required"))
        elif provider == "alpaca":
            if not settings.get("alpaca_api_key"):
                missing.append(("alpaca_api_key", "Alpaca API key is required"))
            if not settings.get("alpaca_api_secret"):
                missing.append(("alpaca_api_secret", "Alpaca API secret is required"))
        elif provider not in LIVE_PROVIDERS:
            missing.append(("selected_market_data_provider", "Unknown provider selected"))

        return [
            ProviderConfigurationIssue(
                status=VALIDATION_FAILED,
                message=message,
                affected_setting=setting,
                recommended_fix="Enter valid provider credentials before running live screening.",
            )
            for setting, message in missing
        ]

    def validate_endpoints(self, provider, settings):
        endpoint_key = f"{provider}_endpoint"
        endpoint = str(settings.get(endpoint_key) or "").strip()
        if provider not in LIVE_PROVIDERS or not endpoint:
            return []
        if endpoint.startswith(("http://", "https://")):
            return []
        return [
            ProviderConfigurationIssue(
                status=VALIDATION_FAILED,
                message=f"{provider} endpoint must be a valid HTTP URL",
                affected_setting=endpoint_key,
                recommended_fix="Use an endpoint beginning with http:// or https://.",
            )
        ]

    def validate_timeout(self, settings):
        timeout = self.number(settings.get("request_timeout_seconds"))
        if timeout is None or timeout <= 0:
            return [
                ProviderConfigurationIssue(
                    status=VALIDATION_FAILED,
                    message="Request timeout must be greater than zero",
                    affected_setting="request_timeout_seconds",
                    recommended_fix="Set request timeout to a positive number of seconds.",
                )
            ]
        if timeout > 120:
            return [
                ProviderConfigurationIssue(
                    status=VALIDATION_WARNING,
                    message="Request timeout is unusually high",
                    affected_setting="request_timeout_seconds",
                    recommended_fix="Use a shorter timeout to keep screening responsive.",
                )
            ]
        return []

    def validate_retries(self, settings):
        retries = self.number(settings.get("max_retries"))
        if retries is None or retries < 0:
            return [
                ProviderConfigurationIssue(
                    status=VALIDATION_FAILED,
                    message="Max retries cannot be negative",
                    affected_setting="max_retries",
                    recommended_fix="Set max retries to zero or greater.",
                )
            ]
        if retries > 10:
            return [
                ProviderConfigurationIssue(
                    status=VALIDATION_WARNING,
                    message="Max retries is unusually high",
                    affected_setting="max_retries",
                    recommended_fix="Use a lower retry count to avoid long provider delays.",
                )
            ]
        return []

    def validate_rate_limit(self, settings):
        rate_limit = self.number(settings.get("rate_limit_sleep_seconds"))
        if rate_limit is None or rate_limit < 0:
            return [
                ProviderConfigurationIssue(
                    status=VALIDATION_FAILED,
                    message="Rate-limit sleep cannot be negative",
                    affected_setting="rate_limit_sleep_seconds",
                    recommended_fix="Set rate-limit sleep to zero or greater.",
                )
            ]
        return []

    def validate_failover(self, provider, health):
        if provider not in LIVE_PROVIDERS:
            return []
        available = [
            item
            for item in health
            if self.value(item, "provider_name") != provider
            and self.value(item, "status") in {"healthy", "degraded"}
        ]
        if available:
            return []
        return [
            ProviderConfigurationIssue(
                status=VALIDATION_WARNING,
                message="No failover provider is currently available",
                affected_setting="failover_provider",
                recommended_fix="Configure a secondary healthy provider for live screening resilience.",
            )
        ]

    def validate_health(self, provider, health):
        if provider == "local_csv":
            return []
        if any(self.value(item, "status") == "healthy" for item in health):
            return []
        return [
            ProviderConfigurationIssue(
                status=VALIDATION_FAILED,
                message="No healthy market data provider is configured",
                affected_setting="provider_health",
                recommended_fix="Check credentials, connectivity, and provider failover settings.",
            )
        ]

    @staticmethod
    def overall_status(issues):
        statuses = {issue.status for issue in issues}
        if VALIDATION_FAILED in statuses:
            return VALIDATION_FAILED
        if VALIDATION_WARNING in statuses:
            return VALIDATION_WARNING
        return VALIDATION_PASSED

    @staticmethod
    def normalize_settings(settings):
        if settings is None:
            return {}
        if isinstance(settings, dict):
            return dict(settings)
        if is_dataclass(settings):
            return asdict(settings)
        return dict(vars(settings)) if hasattr(settings, "__dict__") else {}

    @staticmethod
    def value(source, key):
        if source is None:
            return None
        if isinstance(source, dict):
            return source.get(key)
        return getattr(source, key, None)

    @staticmethod
    def number(value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
