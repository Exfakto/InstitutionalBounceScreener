from __future__ import annotations

import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from providers.base_provider import BaseProvider
from providers.provider_result import ProviderResult


class FinnhubProvider(BaseProvider):
    """
    Finnhub provider for earnings, insider, and company profile intelligence.
    """

    SOURCE = "finnhub"
    BASE_URL = "https://finnhub.io/api/v1"

    def __init__(self, api_key=None, opener=None, base_url=None):
        self.api_key = api_key if api_key is not None else os.getenv("FINNHUB_API_KEY")
        self.opener = opener or urlopen
        self.base_url = (base_url or self.BASE_URL).rstrip("/")

    def get_price_history(self, ticker, start=None, end=None):
        return self.not_implemented_result(ticker, "price history")

    def get_fundamentals(self, ticker):
        return self.not_implemented_result(ticker, "fundamentals")

    def get_institutional_metrics(self, ticker):
        return self.not_implemented_result(ticker, "institutional metrics")

    def get_earnings(self, ticker):
        normalized_ticker = self.normalize_ticker(ticker)

        if normalized_ticker is None:
            return self.missing_ticker_result()

        if not self.api_key:
            return self.missing_api_key_result(normalized_ticker)

        try:
            upcoming = self.fetch_json(
                self.endpoint_url("calendar/earnings", {"symbol": normalized_ticker})
            )
            historical = self.fetch_json(
                self.endpoint_url("stock/earnings", {"symbol": normalized_ticker})
            )
        except HTTPError as exc:
            return self.http_failure(exc, normalized_ticker)
        except (URLError, TimeoutError, OSError) as exc:
            return self.failure(
                f"Finnhub request failed for {normalized_ticker}.",
                normalized_ticker,
                warnings=[str(exc)],
            )
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            return self.failure(
                f"Finnhub response was malformed for {normalized_ticker}.",
                normalized_ticker,
                warnings=[str(exc)],
            )

        data = self.normalize_earnings_payload(upcoming, historical)

        if data is None:
            return self.malformed_response_result(normalized_ticker)

        return ProviderResult.ok(
            data=data,
            message="Finnhub earnings retrieved.",
            source=self.SOURCE,
            metadata={
                "ticker": normalized_ticker,
                "historical_rows": len(data["historical_earnings_surprises"]),
            },
        )

    def get_insider_activity(self, ticker):
        normalized_ticker = self.normalize_ticker(ticker)

        if normalized_ticker is None:
            return self.missing_ticker_result()

        if not self.api_key:
            return self.missing_api_key_result(normalized_ticker)

        try:
            sentiment = self.fetch_json(
                self.endpoint_url("stock/insider-sentiment", {"symbol": normalized_ticker})
            )
            transactions = self.fetch_json(
                self.endpoint_url("stock/insider-transactions", {"symbol": normalized_ticker})
            )
        except HTTPError as exc:
            return self.http_failure(exc, normalized_ticker)
        except (URLError, TimeoutError, OSError) as exc:
            return self.failure(
                f"Finnhub request failed for {normalized_ticker}.",
                normalized_ticker,
                warnings=[str(exc)],
            )
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            return self.failure(
                f"Finnhub response was malformed for {normalized_ticker}.",
                normalized_ticker,
                warnings=[str(exc)],
            )

        data = self.normalize_insider_payload(sentiment, transactions)

        if data is None:
            return self.malformed_response_result(normalized_ticker)

        return ProviderResult.ok(
            data=data,
            message="Finnhub insider activity retrieved.",
            source=self.SOURCE,
            metadata={
                "ticker": normalized_ticker,
                "sentiment_rows": len(data["insider_sentiment"]),
                "transaction_rows": len(data["insider_transactions"]),
            },
        )

    def get_company_profile(self, ticker):
        normalized_ticker = self.normalize_ticker(ticker)

        if normalized_ticker is None:
            return self.missing_ticker_result()

        if not self.api_key:
            return self.missing_api_key_result(normalized_ticker)

        try:
            payload = self.fetch_json(
                self.endpoint_url("stock/profile2", {"symbol": normalized_ticker})
            )
        except HTTPError as exc:
            return self.http_failure(exc, normalized_ticker)
        except (URLError, TimeoutError, OSError) as exc:
            return self.failure(
                f"Finnhub request failed for {normalized_ticker}.",
                normalized_ticker,
                warnings=[str(exc)],
            )
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            return self.failure(
                f"Finnhub response was malformed for {normalized_ticker}.",
                normalized_ticker,
                warnings=[str(exc)],
            )

        data = self.normalize_profile_payload(payload, normalized_ticker)

        if data is None:
            return self.malformed_response_result(normalized_ticker)

        if data == {}:
            return self.failure(
                f"No Finnhub company profile found for {normalized_ticker}.",
                normalized_ticker,
            )

        return ProviderResult.ok(
            data=data,
            message="Finnhub company profile retrieved.",
            source=self.SOURCE,
            metadata={"ticker": normalized_ticker},
        )

    def endpoint_url(self, endpoint, parameters):
        query = dict(parameters)
        query["token"] = self.api_key

        return f"{self.base_url}/{endpoint}?{urlencode(query)}"

    def fetch_json(self, url):
        with self.opener(url, timeout=30) as response:
            raw = response.read()

        return json.loads(raw.decode("utf-8"))

    @classmethod
    def normalize_earnings_payload(cls, upcoming, historical):
        if not isinstance(upcoming, dict) or not isinstance(historical, list):
            return None

        upcoming_rows = upcoming.get("earningsCalendar", [])

        if not isinstance(upcoming_rows, list):
            return None

        normalized_history = []

        for item in historical:
            if not isinstance(item, dict):
                return None

            normalized_history.append(
                {
                    "period": item.get("period"),
                    "eps_estimate": item.get("estimate"),
                    "eps_actual": item.get("actual"),
                    "surprise_percent": item.get("surprisePercent"),
                }
            )

        upcoming_date = None

        if upcoming_rows:
            first_upcoming = upcoming_rows[0]

            if not isinstance(first_upcoming, dict):
                return None

            upcoming_date = first_upcoming.get("date")

        return {
            "upcoming_earnings_date": upcoming_date,
            "historical_earnings_surprises": normalized_history,
            "eps_estimate": normalized_history[0]["eps_estimate"]
            if normalized_history
            else None,
            "eps_actual": normalized_history[0]["eps_actual"]
            if normalized_history
            else None,
            "surprise_percent": normalized_history[0]["surprise_percent"]
            if normalized_history
            else None,
        }

    @classmethod
    def normalize_insider_payload(cls, sentiment, transactions):
        if not isinstance(sentiment, dict) or not isinstance(transactions, dict):
            return None

        sentiment_rows = sentiment.get("data", [])
        transaction_rows = transactions.get("data", [])

        if not isinstance(sentiment_rows, list) or not isinstance(transaction_rows, list):
            return None

        if not all(isinstance(item, dict) for item in sentiment_rows):
            return None

        if not all(isinstance(item, dict) for item in transaction_rows):
            return None

        return {
            "insider_sentiment": [dict(item) for item in sentiment_rows],
            "insider_transactions": [dict(item) for item in transaction_rows],
        }

    @staticmethod
    def normalize_profile_payload(payload, ticker):
        if not isinstance(payload, dict):
            return None

        if not payload:
            return {}

        return {
            "name": payload.get("name"),
            "ticker": payload.get("ticker") or ticker,
            "exchange": payload.get("exchange"),
            "industry": payload.get("finnhubIndustry"),
            "sector": payload.get("sector"),
            "market_cap": payload.get("marketCapitalization"),
            "web_url": payload.get("weburl"),
        }

    def not_implemented_result(self, ticker, data_type):
        normalized_ticker = self.normalize_ticker(ticker)

        if normalized_ticker is None:
            return self.missing_ticker_result()

        return self.failure(
            f"Finnhub {data_type} provider is not yet implemented.",
            normalized_ticker,
            warnings=["Not yet implemented."],
        )

    @classmethod
    def http_failure(cls, error, ticker):
        if error.code == 429:
            return cls.failure(
                f"Finnhub rate limit reached for {ticker}.",
                ticker,
                warnings=["Rate limited."],
            )

        return cls.failure(
            f"Finnhub request failed for {ticker}.",
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

    @classmethod
    def missing_ticker_result(cls):
        return cls.failure(
            "Ticker is required.",
            warnings=["Missing ticker."],
        )

    @classmethod
    def missing_api_key_result(cls, ticker):
        return cls.failure(
            "Finnhub API key is required.",
            ticker,
            warnings=["Missing FINNHUB_API_KEY."],
        )

    @classmethod
    def malformed_response_result(cls, ticker):
        return cls.failure(
            f"Finnhub response was malformed for {ticker}.",
            ticker,
            warnings=["Malformed response."],
        )

    @staticmethod
    def normalize_ticker(ticker):
        if ticker is None:
            return None

        normalized = str(ticker).strip().upper()

        if not normalized:
            return None

        return normalized
