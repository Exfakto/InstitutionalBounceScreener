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
        preset = (filters or {}).get("scan_preset")
        return [
            record
            for record in (records or [])
            if UniverseScanAdapter.record_matches_preset(record, preset)
        ]

    @staticmethod
    def record_matches_preset(record, preset):
        if preset is None:
            return True

        checks = [
            ("market_cap", getattr(preset, "min_market_cap", None)),
            ("price", getattr(preset, "min_price", None)),
            ("average_volume", getattr(preset, "min_avg_volume", None)),
            ("average_dollar_volume", getattr(preset, "min_avg_dollar_volume", None)),
        ]
        for field, minimum in checks:
            if minimum is not None:
                value = UniverseScanAdapter.number_value(
                    UniverseScanAdapter.record_value(record, field)
                )
                if value is None or value < minimum:
                    return False

        exchanges = [value.upper() for value in getattr(preset, "exchanges", [])]
        if exchanges:
            exchange = str(UniverseScanAdapter.record_value(record, "exchange") or "").upper()
            if exchange not in exchanges:
                return False

        security_types = [
            value.upper() for value in getattr(preset, "security_types", [])
        ]
        if security_types:
            security_type = str(
                UniverseScanAdapter.record_value(record, "security_type") or ""
            ).upper()
            if security_type not in security_types:
                return False

        return True

    @staticmethod
    def record_value(record, key):
        if isinstance(record, dict):
            return record.get(key)
        return getattr(record, key, None)

    @staticmethod
    def number_value(value):
        if value in (None, ""):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def normalize_tickers(tickers):
        normalized = []
        for ticker in tickers or []:
            value = str(ticker or "").strip().upper()
            if value and value not in normalized:
                normalized.append(value)
        return normalized
