from __future__ import annotations

import json
import os
from datetime import date, datetime, timedelta
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

import pandas as pd

from providers.base_provider import BaseProvider
from providers.provider_result import ProviderResult


class PolygonProvider(BaseProvider):
    """
    Polygon.io provider for daily OHLCV aggregate history.
    """

    SOURCE = "polygon"
    BASE_URL = "https://api.polygon.io"

    def __init__(self, api_key=None, opener=None, base_url=None):
        self.api_key = api_key if api_key is not None else os.getenv("POLYGON_API_KEY")
        self.opener = opener or urlopen
        self.base_url = (base_url or self.BASE_URL).rstrip("/")

    def get_price_history(self, ticker, start=None, end=None):
        normalized_ticker = self.normalize_ticker(ticker)

        if normalized_ticker is None:
            return self.failure(
                "Ticker is required.",
                warnings=["Missing ticker."],
            )

        if not self.api_key:
            return self.failure(
                "Polygon API key is required.",
                normalized_ticker,
                warnings=["Missing POLYGON_API_KEY."],
            )

        start_date, end_date = self.date_range(start, end)
        url = self.aggregates_url(normalized_ticker, start_date, end_date)

        try:
            payload = self.fetch_json(url)
        except HTTPError as exc:
            return self.http_failure(exc, normalized_ticker)
        except (URLError, TimeoutError, OSError) as exc:
            return self.failure(
                f"Polygon request failed for {normalized_ticker}.",
                normalized_ticker,
                warnings=[str(exc)],
            )
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            return self.failure(
                f"Polygon response was malformed for {normalized_ticker}.",
                normalized_ticker,
                warnings=[str(exc)],
            )

        dataframe = self.normalize_aggregates(payload, normalized_ticker)

        if dataframe is None:
            return self.failure(
                f"Polygon response was malformed for {normalized_ticker}.",
                normalized_ticker,
                warnings=["Malformed response."],
            )

        if dataframe.empty:
            return self.failure(
                f"No Polygon price history found for {normalized_ticker}.",
                normalized_ticker,
                metadata={"ticker": normalized_ticker},
            )

        return ProviderResult.ok(
            data=dataframe,
            message="Polygon price history retrieved.",
            source=self.SOURCE,
            metadata={
                "ticker": normalized_ticker,
                "rows": len(dataframe),
                "start": start_date,
                "end": end_date,
            },
        )

    def get_fundamentals(self, ticker):
        return self.not_implemented_result(ticker, "fundamentals")

    def get_earnings(self, ticker):
        return self.not_implemented_result(ticker, "earnings")

    def get_institutional_metrics(self, ticker):
        return self.not_implemented_result(ticker, "institutional metrics")

    def get_insider_activity(self, ticker):
        return self.not_implemented_result(ticker, "insider activity")

    def get_company_profile(self, ticker):
        return self.not_implemented_result(ticker, "company profile")

    def not_implemented_result(self, ticker, data_type):
        normalized_ticker = self.normalize_ticker(ticker)

        if normalized_ticker is None:
            return self.failure(
                "Ticker is required.",
                warnings=["Missing ticker."],
            )

        return self.failure(
            f"Polygon {data_type} provider is not yet implemented.",
            normalized_ticker,
            warnings=["Not yet implemented."],
        )

    def aggregates_url(self, ticker, start, end):
        query = urlencode(
            {
                "adjusted": "true",
                "sort": "asc",
                "limit": 50000,
                "apiKey": self.api_key,
            }
        )
        return (
            f"{self.base_url}/v2/aggs/ticker/{ticker}/range/1/day/"
            f"{start}/{end}?{query}"
        )

    def fetch_json(self, url):
        with self.opener(url, timeout=30) as response:
            raw = response.read()

        return json.loads(raw.decode("utf-8"))

    @classmethod
    def normalize_aggregates(cls, payload, ticker):
        if not isinstance(payload, dict):
            return None

        results = payload.get("results")

        if results is None:
            return pd.DataFrame(
                columns=["Open", "High", "Low", "Close", "Volume"]
            )

        if not isinstance(results, list):
            return None

        rows = []

        for item in results:
            if not isinstance(item, dict):
                return None

            try:
                timestamp = int(item["t"])
                rows.append(
                    {
                        "date": pd.to_datetime(timestamp, unit="ms").normalize(),
                        "Open": float(item["o"]),
                        "High": float(item["h"]),
                        "Low": float(item["l"]),
                        "Close": float(item["c"]),
                        "Volume": int(item["v"]),
                    }
                )
            except (KeyError, TypeError, ValueError, OverflowError):
                return None

        dataframe = pd.DataFrame(rows)

        if dataframe.empty:
            return pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])

        dataframe.sort_values("date", inplace=True)
        dataframe.set_index("date", inplace=True)
        dataframe.index.name = "date"

        return dataframe[["Open", "High", "Low", "Close", "Volume"]]

    @classmethod
    def http_failure(cls, error, ticker):
        if error.code == 429:
            return cls.failure(
                f"Polygon rate limit reached for {ticker}.",
                ticker,
                warnings=["Rate limited."],
            )

        return cls.failure(
            f"Polygon request failed for {ticker}.",
            ticker,
            warnings=[f"HTTP {error.code}"],
        )

    @classmethod
    def failure(cls, message, ticker=None, warnings=None, metadata=None):
        result_metadata = dict(metadata or {})

        if ticker is not None:
            result_metadata.setdefault("ticker", ticker)

        return ProviderResult.fail(
            message=message,
            source=cls.SOURCE,
            warnings=list(warnings or []),
            metadata=result_metadata,
        )

    @staticmethod
    def normalize_ticker(ticker):
        if ticker is None:
            return None

        normalized = str(ticker).strip().upper()

        if not normalized:
            return None

        return normalized

    @staticmethod
    def date_range(start, end):
        end_date = PolygonProvider.format_date(end) if end is not None else date.today().isoformat()
        start_date = (
            PolygonProvider.format_date(start)
            if start is not None
            else (date.today() - timedelta(days=365)).isoformat()
        )
        return start_date, end_date

    @staticmethod
    def format_date(value):
        if isinstance(value, datetime):
            return value.date().isoformat()

        if isinstance(value, date):
            return value.isoformat()

        return str(value)
