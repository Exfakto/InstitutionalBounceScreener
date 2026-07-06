from __future__ import annotations

from collections.abc import Callable
from threading import RLock, Timer
from typing import Any

from services.live_data_service import LiveDataService


class RefreshScheduler:
    """
    Periodically refreshes registered tickers through LiveDataService.

    The scheduler is infrastructure-only: it has no UI, provider-specific,
    analysis, scoring, or persistence responsibilities.
    """

    DEFAULT_INTERVAL_SECONDS = 300

    def __init__(
        self,
        live_data_service: LiveDataService | None = None,
        refresh_interval: float | int | None = None,
        timer_factory: Callable[[float, Callable[[], None]], Any] | None = None,
    ) -> None:
        self.live_data_service = live_data_service or LiveDataService()
        self.refresh_interval = (
            self.DEFAULT_INTERVAL_SECONDS
            if refresh_interval is None
            else self.normalize_interval(refresh_interval)
        )
        self.timer_factory = timer_factory or Timer
        self._lock = RLock()
        self._tickers = []
        self._callbacks = []
        self._timer = None
        self._running = False

    def start(self) -> bool:
        """Start periodic refresh scheduling."""
        with self._lock:
            if self._running:
                return False

            self._running = True
            self._schedule_locked()

        return True

    def stop(self) -> bool:
        """Stop future scheduled refreshes."""
        with self._lock:
            if not self._running and self._timer is None:
                return False

            self._running = False
            timer = self._timer
            self._timer = None

        if timer is not None:
            timer.cancel()

        return True

    def is_running(self) -> bool:
        with self._lock:
            return self._running

    def register_ticker(self, ticker: str) -> bool:
        """Register a ticker for future refreshes."""
        normalized_ticker = self.normalize_ticker(ticker)

        if normalized_ticker is None:
            return False

        with self._lock:
            if normalized_ticker in self._tickers:
                return False

            self._tickers.append(normalized_ticker)

        return True

    def unregister_ticker(self, ticker: str) -> bool:
        """Remove a ticker from future refreshes."""
        normalized_ticker = self.normalize_ticker(ticker)

        if normalized_ticker is None:
            return False

        with self._lock:
            if normalized_ticker not in self._tickers:
                return False

            self._tickers.remove(normalized_ticker)

        return True

    def clear_tickers(self) -> None:
        with self._lock:
            self._tickers.clear()

    def refresh_now(self) -> dict[str, object]:
        """Synchronously refresh all registered tickers."""
        with self._lock:
            tickers = list(self._tickers)
            callbacks = list(self._callbacks)

        results = {}

        for ticker in tickers:
            result = self.live_data_service.fetch_daily_ohlcv(ticker)
            results[ticker] = result
            self._notify_callbacks(ticker, result, callbacks)

        return results

    def set_refresh_interval(self, seconds: float | int) -> float:
        """Set the refresh interval in seconds."""
        interval = self.normalize_interval(seconds)

        with self._lock:
            self.refresh_interval = interval
            should_reschedule = self._running
            timer = self._timer
            self._timer = None

        if timer is not None:
            timer.cancel()

        if should_reschedule:
            with self._lock:
                if self._running:
                    self._schedule_locked()

        return interval

    def register_callback(self, callback: Callable[[str, object], None]) -> bool:
        """Register a listener called with ticker and ProviderResult."""
        if not callable(callback):
            return False

        with self._lock:
            if callback in self._callbacks:
                return False

            self._callbacks.append(callback)

        return True

    def _run_scheduled_refresh(self) -> None:
        try:
            self.refresh_now()
        finally:
            with self._lock:
                if self._running:
                    self._schedule_locked()

    def _schedule_locked(self) -> None:
        timer = self.timer_factory(
            self.refresh_interval,
            self._run_scheduled_refresh,
        )
        timer.daemon = True
        self._timer = timer
        timer.start()

    @staticmethod
    def _notify_callbacks(ticker: str, result: object, callbacks: list) -> None:
        for callback in callbacks:
            try:
                callback(ticker, result)
            except Exception:
                continue

    @staticmethod
    def normalize_ticker(ticker: str | None) -> str | None:
        if ticker is None:
            return None

        normalized = str(ticker).strip().upper()

        if not normalized:
            return None

        return normalized

    @classmethod
    def normalize_interval(cls, seconds: float | int | None) -> float:
        try:
            interval = float(seconds)
        except (TypeError, ValueError):
            return cls.DEFAULT_INTERVAL_SECONDS

        if interval <= 0:
            return cls.DEFAULT_INTERVAL_SECONDS

        return interval
