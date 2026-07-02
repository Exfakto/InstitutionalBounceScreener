from __future__ import annotations

import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from providers.base_provider import BaseProvider
from providers.provider_result import ProviderResult


class FMPProvider(BaseProvider):
    """
    Financial Modeling Prep provider for reference and fundamental data.
    """

    SOURCE = "fmp"
    BASE_URL = "https://financialmodelingprep.com/stable"

    ENDPOINTS = {
        "company_profile": "profile",
        "income_statement": "income-statement",
        "balance_sheet_statement": "balance-sheet-statement",
        "cash_flow_statement": "cash-flow-statement",
        "ratios": "ratios",
        "earnings": "earnings",
        "insider_activity": "insider-trading",
    }

    def __init__(self, api_key=None, opener=None, base_url=None):
        self.api_key = api_key if api_key is not None else os.getenv("FMP_API_KEY")
        self.opener = opener or urlopen
        self.base_url = (base_url or self.BASE_URL).rstrip("/")

    def get_price_history(self, ticker, start=None, end=None):
        normalized_ticker = self.normalize_ticker(ticker)

        if normalized_ticker is None:
            return self.missing_ticker_result()

        return self.failure(
            "FMP price history provider is not yet implemented.",
            normalized_ticker,
            warnings=["Not yet implemented."],
        )

    def get_company_profile(self, ticker):
        return self.get_endpoint_result(
            ticker,
            endpoint_name="company_profile",
            success_message="FMP company profile retrieved.",
            missing_message="No FMP company profile found",
            first_item=True,
        )

    def get_fundamentals(self, ticker):
        normalized_ticker = self.normalize_ticker(ticker)

        if normalized_ticker is None:
            return self.missing_ticker_result()

        if not self.api_key:
            return self.failure(
                "FMP API key is required.",
                normalized_ticker,
                warnings=["Missing FMP_API_KEY."],
            )

        payloads = {}

        for endpoint_name in [
            "income_statement",
            "balance_sheet_statement",
            "cash_flow_statement",
            "ratios",
        ]:
            url = self.endpoint_url(endpoint_name, normalized_ticker)

            try:
                payload = self.fetch_json(url)
            except HTTPError as exc:
                return self.http_failure(exc, normalized_ticker)
            except (URLError, TimeoutError, OSError) as exc:
                return self.failure(
                    f"FMP request failed for {normalized_ticker}.",
                    normalized_ticker,
                    warnings=[str(exc)],
                )
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                return self.failure(
                    f"FMP response was malformed for {normalized_ticker}.",
                    normalized_ticker,
                    warnings=[str(exc)],
                )

            normalized = self.normalize_payload(payload)

            if normalized is None:
                return self.failure(
                    f"FMP response was malformed for {normalized_ticker}.",
                    normalized_ticker,
                    warnings=["Malformed response."],
                )

            payloads[endpoint_name] = normalized

        if not any(payloads.values()):
            return self.failure(
                f"No FMP fundamentals found for {normalized_ticker}.",
                normalized_ticker,
            )

        return ProviderResult.ok(
            data=payloads,
            message="FMP fundamentals retrieved.",
            source=self.SOURCE,
            metadata={
                "ticker": normalized_ticker,
                "endpoint": "fundamentals",
                "rows": sum(len(value) for value in payloads.values()),
            },
        )

    def get_earnings(self, ticker):
        return self.get_endpoint_result(
            ticker,
            endpoint_name="earnings",
            success_message="FMP earnings retrieved.",
            missing_message="No FMP earnings found",
        )

    def get_institutional_metrics(self, ticker):
        normalized_ticker = self.normalize_ticker(ticker)

        if normalized_ticker is None:
            return self.missing_ticker_result()

        return self.failure(
            "FMP institutional metrics provider is not yet implemented on stable API.",
            normalized_ticker,
            warnings=["Not yet implemented."],
        )

    def get_insider_activity(self, ticker):
        return self.get_endpoint_result(
            ticker,
            endpoint_name="insider_activity",
            success_message="FMP insider activity retrieved.",
            missing_message="No FMP insider activity found",
        )

    def get_endpoint_result(
        self,
        ticker,
        endpoint_name,
        success_message,
        missing_message,
        first_item=False,
    ):
        normalized_ticker = self.normalize_ticker(ticker)

        if normalized_ticker is None:
            return self.missing_ticker_result()

        if not self.api_key:
            return self.failure(
                "FMP API key is required.",
                normalized_ticker,
                warnings=["Missing FMP_API_KEY."],
            )

        url = self.endpoint_url(endpoint_name, normalized_ticker)

        try:
            payload = self.fetch_json(url)
        except HTTPError as exc:
            return self.http_failure(exc, normalized_ticker)
        except (URLError, TimeoutError, OSError) as exc:
            return self.failure(
                f"FMP request failed for {normalized_ticker}.",
                normalized_ticker,
                warnings=[str(exc)],
            )
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            return self.failure(
                f"FMP response was malformed for {normalized_ticker}.",
                normalized_ticker,
                warnings=[str(exc)],
            )

        normalized = self.normalize_payload(payload, first_item=first_item)

        if normalized is None:
            return self.failure(
                f"FMP response was malformed for {normalized_ticker}.",
                normalized_ticker,
                warnings=["Malformed response."],
            )

        if normalized == {} or normalized == []:
            return self.failure(
                f"{missing_message} for {normalized_ticker}.",
                normalized_ticker,
            )

        rows = len(normalized) if isinstance(normalized, list) else 1

        return ProviderResult.ok(
            data=normalized,
            message=success_message,
            source=self.SOURCE,
            metadata={
                "ticker": normalized_ticker,
                "endpoint": endpoint_name,
                "rows": rows,
            },
        )

    def endpoint_url(self, endpoint_name, ticker):
        endpoint = self.ENDPOINTS[endpoint_name]
        query = {
            "symbol": ticker,
            "apikey": self.api_key,
        }

        return f"{self.base_url}/{endpoint}?{urlencode(query)}"

    def fetch_json(self, url):
        with self.opener(url, timeout=30) as response:
            raw = response.read()

        return json.loads(raw.decode("utf-8"))

    @staticmethod
    def normalize_payload(payload, first_item=False):
        if not isinstance(payload, list):
            return None

        rows = []

        for item in payload:
            if not isinstance(item, dict):
                return None

            rows.append(dict(item))

        if first_item:
            return rows[0] if rows else {}

        return rows

    @classmethod
    def http_failure(cls, error, ticker):
        if error.code == 429:
            return cls.failure(
                f"FMP rate limit reached for {ticker}.",
                ticker,
                warnings=["Rate limited."],
            )

        return cls.failure(
            f"FMP request failed for {ticker}.",
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

    @staticmethod
    def normalize_ticker(ticker):
        if ticker is None:
            return None

        normalized = str(ticker).strip().upper()

        if not normalized:
            return None

        return normalized
