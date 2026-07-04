from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ProviderHealthResult:
    provider_name: str
    status: str
    success_count: int = 0
    error_count: int = 0
    average_latency_seconds: float = 0.0
    last_failure_reason: str | None = None


@dataclass(frozen=True)
class ProviderCallResult:
    success: bool
    value: object = None
    provider_name: str | None = None
    attempts: int = 0
    errors: list[str] = field(default_factory=list)
    health: ProviderHealthResult | None = None


class LiveProviderResilienceService:
    """Provider-level retry, timeout, health tracking, and failover."""

    def __init__(self, providers=None, max_retries=2, timeout_seconds=10):
        self.providers = list(providers or [])
        self.max_retries = max(0, int(max_retries or 0))
        self.timeout_seconds = max(0.01, float(timeout_seconds or 10))
        self.metrics = {}

    def call(self, method_name, *args, **kwargs):
        errors = []
        attempts = 0
        for provider in self.providers:
            provider_name = self.provider_name(provider)
            for _attempt in range(self.max_retries + 1):
                attempts += 1
                started = time.perf_counter()
                try:
                    value = self.call_with_timeout(provider, method_name, *args, **kwargs)
                    latency = time.perf_counter() - started
                    self.record_success(provider_name, latency)
                    return ProviderCallResult(
                        success=True,
                        value=value,
                        provider_name=provider_name,
                        attempts=attempts,
                        errors=errors,
                        health=self.health_for(provider_name),
                    )
                except Exception as exc:
                    latency = time.perf_counter() - started
                    reason = str(exc) or exc.__class__.__name__
                    errors.append(f"{provider_name}: {reason}")
                    self.record_failure(provider_name, latency, reason)
                    if not self.is_transient(exc):
                        break
        provider_name = self.provider_name(self.providers[-1]) if self.providers else "unconfigured"
        return ProviderCallResult(
            success=False,
            provider_name=provider_name,
            attempts=attempts,
            errors=errors or ["No live market data provider configured"],
            health=self.health_for(provider_name),
        )

    def call_with_timeout(self, provider, method_name, *args, **kwargs):
        method = getattr(provider, method_name)
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(method, *args, **kwargs)
            try:
                return future.result(timeout=self.timeout_seconds)
            except FutureTimeoutError as exc:
                future.cancel()
                raise TimeoutError(f"Provider call timed out after {self.timeout_seconds:.2f}s") from exc

    def health_for(self, provider_name):
        metrics = self.metrics.get(provider_name, {})
        successes = int(metrics.get("success_count") or 0)
        errors = int(metrics.get("error_count") or 0)
        latency_values = metrics.get("latencies") or []
        average_latency = (
            sum(latency_values) / len(latency_values)
            if latency_values
            else 0.0
        )
        if successes == 0 and errors > 0:
            status = "unavailable"
        elif errors > 0:
            status = "degraded"
        else:
            status = "healthy"
        return ProviderHealthResult(
            provider_name=provider_name,
            status=status,
            success_count=successes,
            error_count=errors,
            average_latency_seconds=round(average_latency, 6),
            last_failure_reason=metrics.get("last_failure_reason"),
        )

    def all_health(self):
        names = [self.provider_name(provider) for provider in self.providers]
        names.extend(name for name in self.metrics if name not in names)
        return [self.health_for(name) for name in names]

    def record_success(self, provider_name, latency):
        metrics = self.metrics.setdefault(provider_name, self.empty_metrics())
        metrics["success_count"] += 1
        metrics["latencies"].append(float(latency))

    def record_failure(self, provider_name, latency, reason):
        metrics = self.metrics.setdefault(provider_name, self.empty_metrics())
        metrics["error_count"] += 1
        metrics["latencies"].append(float(latency))
        metrics["last_failure_reason"] = reason

    @staticmethod
    def empty_metrics():
        return {
            "success_count": 0,
            "error_count": 0,
            "latencies": [],
            "last_failure_reason": None,
        }

    @staticmethod
    def provider_name(provider):
        if provider is None:
            return "unconfigured"
        return getattr(provider, "SOURCE", provider.__class__.__name__)

    @staticmethod
    def is_transient(exc):
        text = str(exc).lower()
        transient_tokens = ("timeout", "tempor", "rate", "429", "500", "502", "503", "504", "connection")
        return isinstance(exc, TimeoutError) or any(token in text for token in transient_tokens)
