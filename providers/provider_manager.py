from __future__ import annotations

import logging
from threading import RLock

from providers.cache_manager import CacheManager
from providers.local_provider import LocalProvider
from providers.polygon_provider import PolygonProvider
from providers.provider_config import ProviderConfig
from providers.provider_result import ProviderResult


LOGGER = logging.getLogger(__name__)


class ProviderManager:
    """
    Routes data requests through the active provider.
    """

    DEFAULT_PROVIDER_NAME = "local"
    DEFAULT_PROVIDER_PRIORITIES = {
        "get_price_history": ["polygon", "local"],
        "get_company_profile": ["fmp", "finnhub", "local"],
        "get_institutional_metrics": ["sec_edgar", "fmp", "local"],
        "get_insider_activity": ["sec_edgar", "finnhub", "local"],
        "get_earnings": ["finnhub", "fmp", "local"],
        "get_fundamentals": ["fmp", "local"],
    }
    DEFAULT_TTLS = {
        "get_price_history": 6 * 60 * 60,
        "get_fundamentals": 24 * 60 * 60,
        "get_earnings": 12 * 60 * 60,
        "get_institutional_metrics": 24 * 60 * 60,
        "get_insider_activity": 24 * 60 * 60,
        "get_company_profile": 7 * 24 * 60 * 60,
    }

    def __init__(
        self,
        default_provider=None,
        provider_config=None,
        cache_manager=None,
        provider_priorities=None,
    ):
        self._lock = RLock()
        self._providers = {}
        self._active_provider_name = self.DEFAULT_PROVIDER_NAME
        self.provider_config = provider_config or ProviderConfig.load()
        self.cache_manager = cache_manager or CacheManager()
        self.provider_priorities = self.normalize_priorities(
            provider_priorities or self.DEFAULT_PROVIDER_PRIORITIES
        )
        self.register_provider(
            self.DEFAULT_PROVIDER_NAME,
            default_provider or LocalProvider(),
        )
        self.register_configured_providers()
        self.apply_configured_active_provider()

    @property
    def active_provider_name(self):
        with self._lock:
            return self._active_provider_name

    def register_provider(self, name, provider):
        normalized_name = self.normalize_name(name)

        if normalized_name is None or provider is None:
            return ProviderResult.fail(
                "Provider registration failed.",
                source="provider_manager",
                warnings=["Provider name and instance are required."],
            )

        with self._lock:
            self._providers[normalized_name] = provider

        return ProviderResult.ok(
            message="Provider registered.",
            source="provider_manager",
            metadata={"provider": normalized_name},
        )

    def set_active_provider(self, name):
        normalized_name = self.normalize_name(name)

        if normalized_name is None:
            return self.unknown_provider_result(name)

        with self._lock:
            if normalized_name not in self._providers:
                return self.unknown_provider_result(normalized_name)

            self._active_provider_name = normalized_name

        return ProviderResult.ok(
            message="Active provider selected.",
            source="provider_manager",
            metadata={"provider": normalized_name},
        )

    def register_configured_providers(self):
        if self.provider_config.is_enabled("polygon"):
            settings = self.provider_config.provider_settings("polygon")
            self.register_provider(
                "polygon",
                PolygonProvider(
                    api_key=None,
                    base_url=settings.get("base_url"),
                ),
            )

    def apply_configured_active_provider(self):
        configured_name = self.normalize_name(self.provider_config.active_provider)

        if configured_name is None or configured_name == self.DEFAULT_PROVIDER_NAME:
            return

        if not self.provider_config.is_enabled(configured_name):
            self._active_provider_name = self.DEFAULT_PROVIDER_NAME
            return

        result = self.set_active_provider(configured_name)

        if not result.success:
            self._active_provider_name = self.DEFAULT_PROVIDER_NAME

    def get_price_history(self, ticker, start=None, end=None):
        return self.delegate(
            "get_price_history",
            ticker,
            start=start,
            end=end,
        )

    def get_fundamentals(self, ticker):
        return self.delegate("get_fundamentals", ticker)

    def get_earnings(self, ticker):
        return self.delegate("get_earnings", ticker)

    def get_institutional_metrics(self, ticker):
        return self.delegate("get_institutional_metrics", ticker)

    def get_insider_activity(self, ticker):
        return self.delegate("get_insider_activity", ticker)

    def get_company_profile(self, ticker):
        return self.delegate("get_company_profile", ticker)

    def delegate(self, method_name, *args, **kwargs):
        failures = []
        skipped = []

        for provider_name in self.priority_for(method_name):
            provider_result = self.try_provider(
                provider_name,
                method_name,
                args,
                kwargs,
            )

            if provider_result.success and provider_result.data is not None:
                return provider_result.data

            if provider_result.message == "skipped":
                skipped.append(provider_result.metadata)
                continue

            failures.append(provider_result)

        return self.failover_failure(method_name, failures, skipped)

    def try_provider(self, provider_name, method_name, args, kwargs):
        provider = self.provider_by_name(provider_name)

        if not self.provider_enabled(provider_name):
            LOGGER.info(
                "Provider skipped: %s for %s is disabled.",
                provider_name,
                method_name,
            )
            return ProviderResult.ok(
                data=None,
                message="skipped",
                source="provider_manager",
                metadata={"provider": provider_name, "reason": "disabled"},
            )

        if provider is None:
            LOGGER.info(
                "Provider skipped: %s for %s is not registered.",
                provider_name,
                method_name,
            )
            return ProviderResult.ok(
                data=None,
                message="skipped",
                source="provider_manager",
                metadata={"provider": provider_name, "reason": "unregistered"},
            )

        method = getattr(provider, method_name, None)

        if method is None:
            LOGGER.info(
                "Provider skipped: %s does not support %s.",
                provider_name,
                method_name,
            )
            return ProviderResult.ok(
                data=None,
                message="skipped",
                source="provider_manager",
                metadata={
                    "provider": provider_name,
                    "reason": "method_unavailable",
                },
            )

        ticker = args[0] if args else kwargs.get("ticker")
        cache_parameters = self.cache_parameters(args, kwargs)
        cached_result = self.cache_manager.get(
            provider_name,
            method_name,
            ticker=ticker,
            parameters=cache_parameters,
        )

        if cached_result is not None:
            LOGGER.info(
                "Provider succeeded from cache: %s for %s.",
                provider_name,
                method_name,
            )
            return ProviderResult.ok(
                data=cached_result,
                message="Provider succeeded.",
                source="provider_manager",
                metadata={"provider": provider_name, "cached": True},
            )

        try:
            LOGGER.info(
                "Provider attempted: %s for %s.",
                provider_name,
                method_name,
            )
            result = method(*args, **kwargs)
        except Exception as exc:
            result = ProviderResult.fail(
                f"Provider request failed for {method_name}.",
                source="provider_manager",
                warnings=[str(exc)],
                metadata={"provider": provider_name},
            )

        if isinstance(result, ProviderResult):
            if result.success:
                LOGGER.info(
                    "Provider succeeded: %s for %s.",
                    provider_name,
                    method_name,
                )
                self.cache_manager.put(
                    provider_name,
                    method_name,
                    ticker=ticker,
                    parameters=cache_parameters,
                    data=result,
                    ttl_seconds=self.ttl_for(method_name),
                )
                return ProviderResult.ok(
                    data=result,
                    message="Provider succeeded.",
                    source="provider_manager",
                    metadata={"provider": provider_name},
                )

            LOGGER.info(
                "Provider failed: %s for %s. %s",
                provider_name,
                method_name,
                result.message,
            )
            return ProviderResult.fail(
                "Provider failed.",
                data=result,
                source="provider_manager",
                warnings=list(result.warnings),
                metadata={"provider": provider_name},
            )

        result = ProviderResult.fail(
            f"Provider returned an invalid result for {method_name}.",
            source="provider_manager",
            warnings=["Invalid provider result."],
            metadata={"provider": provider_name},
        )
        LOGGER.info(
            "Provider failed: %s for %s. Invalid provider result.",
            provider_name,
            method_name,
        )
        return ProviderResult.fail(
            "Provider failed.",
            data=result,
            source="provider_manager",
            warnings=list(result.warnings),
            metadata={"provider": provider_name},
        )

    def priority_for(self, method_name):
        configured = self.provider_priorities.get(method_name, [])
        priority = []

        if self.active_provider_name != self.DEFAULT_PROVIDER_NAME:
            priority.append(self.active_provider_name)

        priority.extend(configured)

        if self.DEFAULT_PROVIDER_NAME not in priority:
            priority.append(self.DEFAULT_PROVIDER_NAME)

        return self.unique_names(priority)

    def provider_by_name(self, name):
        normalized_name = self.normalize_name(name)

        if normalized_name is None:
            return None

        with self._lock:
            return self._providers.get(normalized_name)

    def provider_enabled(self, name):
        normalized_name = self.normalize_name(name)

        if normalized_name is None:
            return False

        if normalized_name not in self.provider_config.providers:
            return True

        return self.provider_config.is_enabled(normalized_name)

    def failover_failure(self, method_name, failures, skipped):
        warnings = []
        attempted = []

        for failure in failures:
            if not isinstance(failure, ProviderResult):
                continue

            provider = failure.metadata.get("provider")
            provider_failure = failure.data
            message = failure.message

            if isinstance(provider_failure, ProviderResult):
                message = provider_failure.message or message

            if provider is not None:
                attempted.append(provider)

            if message:
                warnings.append(f"{provider}: {message}")

            warnings.extend(failure.warnings)

        return ProviderResult.fail(
            f"No provider could satisfy {method_name}.",
            source="provider_manager",
            warnings=warnings or ["No provider returned a successful result."],
            metadata={
                "method": method_name,
                "attempted_providers": attempted,
                "skipped_providers": skipped,
            },
        )

    @staticmethod
    def cache_parameters(args, kwargs):
        parameters = dict(kwargs)

        if len(args) > 1:
            for index, value in enumerate(args[1:], start=1):
                parameters[f"arg{index}"] = value

        return parameters

    @classmethod
    def ttl_for(cls, method_name):
        return cls.DEFAULT_TTLS.get(method_name, 0)

    @classmethod
    def normalize_priorities(cls, provider_priorities):
        return {
            method_name: cls.unique_names(provider_names)
            for method_name, provider_names in provider_priorities.items()
        }

    @classmethod
    def unique_names(cls, names):
        unique = []

        for name in names:
            normalized_name = cls.normalize_name(name)

            if normalized_name is None or normalized_name in unique:
                continue

            unique.append(normalized_name)

        return unique

    def active_provider(self):
        with self._lock:
            return self._providers.get(self._active_provider_name)

    @classmethod
    def unknown_provider_result(cls, name):
        return ProviderResult.fail(
            "Unknown provider.",
            source="provider_manager",
            warnings=["Provider is not registered."],
            metadata={"provider": name},
        )

    @staticmethod
    def normalize_name(name):
        if name is None:
            return None

        normalized = str(name).strip().lower()

        if not normalized:
            return None

        return normalized
