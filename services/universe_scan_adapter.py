"""
Adapter for converting the market universe into screening ticker lists.
"""

from __future__ import annotations


class UniverseScanAdapter:
    """
    Load eligible tickers from the existing market universe layer.
    """

    def __init__(self, universe_source):
        self.universe_source = universe_source

    def load_tickers(self, filters=None):
        records = self.load_records()
        return self.normalize_tickers(
            record.get("ticker") if isinstance(record, dict) else getattr(record, "ticker", None)
            for record in self.apply_filters(records, filters or {})
        )

    def load_records(self):
        if self.universe_source is None:
            return []
        if hasattr(self.universe_source, "get_active_market_universe_records"):
            return self.universe_source.get_active_market_universe_records() or []
        if callable(self.universe_source):
            return self.universe_source() or []
        return []

    @staticmethod
    def apply_filters(records, filters):
        if (filters or {}).get("Universe", {}).get("enabled", True) is False:
            return []
        return list(records or [])

    @staticmethod
    def normalize_tickers(tickers):
        normalized = []
        for ticker in tickers or []:
            value = str(ticker or "").strip().upper()
            if value and value not in normalized:
                normalized.append(value)
        return normalized
