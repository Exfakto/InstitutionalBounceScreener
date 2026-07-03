from __future__ import annotations

from market_data.live_provider import LiveMarketDataProvider
from market_data.models import OhlcvRow, UniverseSymbol


class PolygonMarketDataProvider(LiveMarketDataProvider):
    SOURCE = "polygon"
    BASE_URL = "https://api.polygon.io"

    def fetch_daily_ohlcv(self, ticker, start_date=None, end_date=None):
        normalized = self.normalize_ticker(ticker)
        data = self.safe_get_json(
            f"/v2/aggs/ticker/{normalized}/range/1/day/{start_date or '1900-01-01'}/{end_date or '2100-01-01'}",
            params={"adjusted": "true", "sort": "asc", "apiKey": self.api_key},
        )
        results = (data or {}).get("results") if isinstance(data, dict) else []
        return [
            OhlcvRow(
                ticker=normalized,
                date=self.date_from_polygon(item),
                open=float(item.get("o")),
                high=float(item.get("h")),
                low=float(item.get("l")),
                close=float(item.get("c")),
                volume=int(float(item.get("v", 0))),
                source=self.SOURCE,
            )
            for item in (results or [])
            if all(key in item for key in ("o", "h", "l", "c", "v"))
        ]

    def fetch_fundamentals(self, ticker):
        normalized = self.normalize_ticker(ticker)
        data = self.safe_get_json(
            f"/v3/reference/tickers/{normalized}",
            params={"apiKey": self.api_key},
        )
        result = (data or {}).get("results") if isinstance(data, dict) else None
        if not isinstance(result, dict):
            return None
        return {
            "ticker": normalized,
            "company_name": result.get("name"),
            "exchange": result.get("primary_exchange"),
            "sector": result.get("sic_description"),
            "industry": result.get("type"),
            "market_cap": result.get("market_cap"),
        }

    def fetch_universe_symbols(self, exchange=None):
        params = {"market": "stocks", "active": "true", "limit": 1000, "apiKey": self.api_key}
        data = self.safe_get_json("/v3/reference/tickers", params=params)
        results = (data or {}).get("results") if isinstance(data, dict) else []
        exchange_filter = str(exchange or "").upper()
        symbols = []
        for item in results or []:
            item_exchange = str(item.get("primary_exchange") or "").upper()
            if exchange_filter and item_exchange != exchange_filter:
                continue
            symbols.append(
                UniverseSymbol(
                    ticker=str(item.get("ticker") or "").upper(),
                    exchange=item_exchange or None,
                    security_type=item.get("type"),
                    company_name=item.get("name"),
                )
            )
        return [symbol for symbol in symbols if symbol.ticker]

    @staticmethod
    def date_from_polygon(item):
        from datetime import datetime, timezone

        timestamp = item.get("t")
        if timestamp is None:
            return str(item.get("date"))
        return datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc).date().isoformat()

    @staticmethod
    def normalize_ticker(ticker):
        return str(ticker or "").strip().upper()


class FinancialModelingPrepProvider(LiveMarketDataProvider):
    SOURCE = "fmp"
    BASE_URL = "https://financialmodelingprep.com/api/v3"

    def fetch_daily_ohlcv(self, ticker, start_date=None, end_date=None):
        normalized = self.normalize_ticker(ticker)
        data = self.safe_get_json(
            f"/historical-price-full/{normalized}",
            params={"from": start_date, "to": end_date, "apikey": self.api_key},
        )
        rows = (data or {}).get("historical") if isinstance(data, dict) else []
        return [
            OhlcvRow(
                ticker=normalized,
                date=str(item.get("date")),
                open=float(item.get("open")),
                high=float(item.get("high")),
                low=float(item.get("low")),
                close=float(item.get("close")),
                volume=int(float(item.get("volume", 0))),
                source=self.SOURCE,
            )
            for item in (rows or [])
            if item.get("date")
        ][::-1]

    def fetch_fundamentals(self, ticker):
        normalized = self.normalize_ticker(ticker)
        data = self.safe_get_json(f"/profile/{normalized}", params={"apikey": self.api_key})
        item = data[0] if isinstance(data, list) and data else None
        if not isinstance(item, dict):
            return None
        return {
            "ticker": normalized,
            "company_name": item.get("companyName"),
            "exchange": item.get("exchangeShortName"),
            "sector": item.get("sector"),
            "industry": item.get("industry"),
            "market_cap": item.get("mktCap"),
        }

    def fetch_universe_symbols(self, exchange=None):
        data = self.safe_get_json("/stock/list", params={"apikey": self.api_key})
        exchange_filter = str(exchange or "").upper()
        symbols = []
        for item in data or []:
            item_exchange = str(item.get("exchangeShortName") or item.get("exchange") or "").upper()
            if exchange_filter and item_exchange != exchange_filter:
                continue
            symbols.append(
                UniverseSymbol(
                    ticker=str(item.get("symbol") or "").upper(),
                    exchange=item_exchange or None,
                    security_type=item.get("type") or "Common Stock",
                    company_name=item.get("name"),
                )
            )
        return [symbol for symbol in symbols if symbol.ticker]

    @staticmethod
    def normalize_ticker(ticker):
        return str(ticker or "").strip().upper()


class AlpacaMarketDataProvider(LiveMarketDataProvider):
    SOURCE = "alpaca"
    BASE_URL = "https://data.alpaca.markets"
    REQUIRED_CREDENTIALS = ("api_key", "api_secret")

    def fetch_daily_ohlcv(self, ticker, start_date=None, end_date=None):
        normalized = self.normalize_ticker(ticker)
        data = self.safe_get_json(
            f"/v2/stocks/{normalized}/bars",
            params={"timeframe": "1Day", "start": start_date, "end": end_date},
            headers=self.headers(),
        )
        rows = (data or {}).get("bars") if isinstance(data, dict) else []
        return [
            OhlcvRow(
                ticker=normalized,
                date=str(item.get("t", ""))[:10],
                open=float(item.get("o")),
                high=float(item.get("h")),
                low=float(item.get("l")),
                close=float(item.get("c")),
                volume=int(float(item.get("v", 0))),
                source=self.SOURCE,
            )
            for item in rows or []
            if item.get("t")
        ]

    def fetch_fundamentals(self, ticker):
        self.last_warnings = ["Alpaca fundamentals are not available in this adapter"]
        return None

    def fetch_universe_symbols(self, exchange=None):
        data = self.safe_get_json("/v2/assets", params={"status": "active"}, headers=self.headers())
        exchange_filter = str(exchange or "").upper()
        symbols = []
        for item in data or []:
            item_exchange = str(item.get("exchange") or "").upper()
            if exchange_filter and item_exchange != exchange_filter:
                continue
            symbols.append(
                UniverseSymbol(
                    ticker=str(item.get("symbol") or "").upper(),
                    exchange=item_exchange or None,
                    security_type=item.get("class") or item.get("asset_class"),
                    company_name=item.get("name"),
                )
            )
        return [symbol for symbol in symbols if symbol.ticker]

    def headers(self):
        return {
            "APCA-API-KEY-ID": self.api_key or "",
            "APCA-API-SECRET-KEY": self.api_secret or "",
        }

    @staticmethod
    def normalize_ticker(ticker):
        return str(ticker or "").strip().upper()
