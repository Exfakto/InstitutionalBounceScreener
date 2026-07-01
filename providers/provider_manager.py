from __future__ import annotations

from threading import RLock

from providers.local_provider import LocalProvider
from providers.provider_result import ProviderResult


class ProviderManager:
    """
    Routes data requests through the active provider.
    """

    DEFAULT_PROVIDER_NAME = "local"

    def __init__(self, default_provider=None):
        self._lock = RLock()
        self._providers = {}
        self._active_provider_name = self.DEFAULT_PROVIDER_NAME
        self.register_provider(
            self.DEFAULT_PROVIDER_NAME,
            default_provider or LocalProvider(),
        )

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

        if provider is None:
            return ProviderResult.fail(
                "No active provider is available.",
                source="provider_manager",
                warnings=["Missing provider."],
                metadata={"provider": self.active_provider_name},
            )

        method = getattr(provider, method_name, None)

        if method is None:
            return ProviderResult.fail(
                f"Active provider does not support {method_name}.",
                source="provider_manager",
                warnings=["Provider method unavailable."],
                metadata={"provider": self.active_provider_name},
            )

        try:
            result = method(*args, **kwargs)
        except Exception as exc:
            return ProviderResult.fail(
                f"Provider request failed for {method_name}.",
                source="provider_manager",
                warnings=[str(exc)],
                metadata={"provider": self.active_provider_name},
            )

        if isinstance(result, ProviderResult):
            return result

        return ProviderResult.fail(
            f"Provider returned an invalid result for {method_name}.",
            source="provider_manager",
            warnings=["Invalid provider result."],
            metadata={"provider": self.active_provider_name},
        )

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
