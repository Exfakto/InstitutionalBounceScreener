from __future__ import annotations

from threading import RLock

from providers.cache_manager import CacheManager
from providers.local_provider import LocalProvider
from providers.polygon_provider import PolygonProvider
from providers.provider_config import ProviderConfig
from providers.provider_result import ProviderResult


class ProviderManager:
    """
    Routes data requests through the active provider.
    """

    DEFAULT_PROVIDER_NAME = "local"
    DEFAULT_TTLS = {
        "get_price_history": 6 * 60 * 60,
        "get_fundamentals": 24 * 60 * 60,
        "get_earnings": 12 * 60 * 60,
        "get_institutional_metrics": 24 * 60 * 60,
        "get_insider_activity": 24 * 60 * 60,
        "get_company_profile": 7 * 24 * 60 * 60,
    }

    def __init__(self, default_provider=None, provider_config=None, cache_manager=None):
        self._lock = RLock()
        self._providers = {}
        self._active_provider_name = self.DEFAULT_PROVIDER_NAME
        self.provider_config = provider_config or ProviderConfig.load()
        self.cache_manager = cache_manager or CacheManager()
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
        provider = self.active_provider()
        provider_name = self.active_provider_name

        if provider is None:
            return ProviderResult.fail(
                "No active provider is available.",
                source="provider_manager",
                warnings=["Missing provider."],
                metadata={"provider": provider_name},
            )

        method = getattr(provider, method_name, None)

        if method is None:
            return ProviderResult.fail(
                f"Active provider does not support {method_name}.",
                source="provider_manager",
                warnings=["Provider method unavailable."],
                metadata={"provider": provider_name},
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
            return cached_result

        try:
            result = method(*args, **kwargs)
        except Exception as exc:
            return ProviderResult.fail(
                f"Provider request failed for {method_name}.",
                source="provider_manager",
                warnings=[str(exc)],
                metadata={"provider": provider_name},
            )

        if isinstance(result, ProviderResult):
            if result.success:
                self.cache_manager.put(
                    provider_name,
                    method_name,
                    ticker=ticker,
                    parameters=cache_parameters,
                    data=result,
                    ttl_seconds=self.ttl_for(method_name),
                )
            return result

        return ProviderResult.fail(
            f"Provider returned an invalid result for {method_name}.",
            source="provider_manager",
            warnings=["Invalid provider result."],
            metadata={"provider": provider_name},
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
