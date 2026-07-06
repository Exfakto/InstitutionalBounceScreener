from __future__ import annotations

from market_data.http_client import HttpClient
from market_data.provider import MarketDataProvider


class LiveMarketDataProvider(MarketDataProvider):
    """
    Base class for HTTP/API-style market data providers.
    """

    SOURCE = "live"
    REQUIRED_CREDENTIALS = ("api_key",)

    def __init__(
        self,
        api_key=None,
        api_secret=None,
        http_client=None,
        timeout=10,
        max_retries=3,
        rate_limit_sleep_seconds=1,
        base_url=None,
    ):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url or self.BASE_URL
        self.http_client = http_client or HttpClient(
            timeout=timeout,
            max_retries=max_retries,
            rate_limit_sleep_seconds=rate_limit_sleep_seconds,
        )
        self.last_warnings = []
        self.last_errors = []

    def credentials_available(self):
        for name in self.REQUIRED_CREDENTIALS:
            if not getattr(self, name, None):
                return False
        return True

    def missing_credentials(self):
        missing = [
            name
            for name in self.REQUIRED_CREDENTIALS
            if not getattr(self, name, None)
        ]
        return f"Missing credentials: {', '.join(missing)}" if missing else None

    def safe_get_json(self, path, params=None, headers=None):
        self.last_warnings = []
        self.last_errors = []
        if not self.credentials_available():
            self.last_errors.append(self.missing_credentials())
            return None
        url = self.url(path)
        response = self.http_client.get_json(url, params=params, headers=headers)
        self.last_warnings.extend(response.warnings)
        if not response.success:
            self.last_errors.append(response.error or "Request failed")
            return None
        return response.data

    def url(self, path):
        return f"{self.base_url.rstrip('/')}/{str(path).lstrip('/')}"

    def get_market_universe(self):
        return [symbol.__dict__ for symbol in self.fetch_universe_symbols()]

    def get_company_profile(self, ticker):
        fundamentals = self.fetch_fundamentals(ticker)
        if not isinstance(fundamentals, dict):
            return None
        return {
            "ticker": fundamentals.get("ticker"),
            "company_name": fundamentals.get("company_name"),
            "exchange": fundamentals.get("exchange"),
            "sector": fundamentals.get("sector"),
            "industry": fundamentals.get("industry"),
        }

    def get_quote(self, ticker):
        rows = self.fetch_daily_ohlcv(ticker)
        if not rows:
            return None
        latest = rows[-1]
        return {"ticker": latest.ticker, "price": latest.close, "last_updated": latest.date}

    def get_bulk_quotes(self, tickers):
        return {
            quote["ticker"]: quote
            for quote in (self.get_quote(ticker) for ticker in (tickers or []))
            if quote is not None
        }

    def get_fundamentals(self, ticker):
        return self.fetch_fundamentals(ticker)

    def get_last_updated(self):
        return None
