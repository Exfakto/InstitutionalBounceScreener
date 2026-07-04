from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from providers.base_provider import BaseProvider
from providers.provider_result import ProviderResult


class SECEdgarProvider(BaseProvider):
    """
    SEC EDGAR provider for filing-based institutional and insider data.
    """

    SOURCE = "sec_edgar"
    BASE_URL = "https://data.sec.gov"
    TICKER_URL = "https://www.sec.gov/files/company_tickers.json"
    USER_AGENT = "InstitutionalBounceScreener contact@example.com"

    def __init__(self, opener=None, base_url=None, ticker_url=None, user_agent=None):
        self.opener = opener or urlopen
        self.base_url = (base_url or self.BASE_URL).rstrip("/")
        self.ticker_url = ticker_url or self.TICKER_URL
        self.user_agent = user_agent or self.USER_AGENT

    def get_price_history(self, ticker, start=None, end=None):
        return self.not_implemented_result(ticker, "price history")

    def get_company_profile(self, ticker):
        return self.not_implemented_result(ticker, "company profile")

    def get_fundamentals(self, ticker):
        return self.not_implemented_result(ticker, "fundamentals")

    def get_earnings(self, ticker):
        return self.not_implemented_result(ticker, "earnings")

    def fetch_universe_symbols(self, exchange=None):
        return ProviderResult.fail(
            message="SEC EDGAR universe provider is not implemented.",
            source=self.SOURCE,
            warnings=["Not yet implemented."],
            metadata={"exchange": exchange},
        )

    def get_institutional_metrics(self, ticker):
        normalized_ticker = self.normalize_ticker(ticker)

        if normalized_ticker is None:
            return self.missing_ticker_result()

        resolved = self.resolve_submission(normalized_ticker)

        if not resolved.success:
            return resolved

        data = self.institutional_metrics_from_submission(
            resolved.data["submission"],
            resolved.data["cik"],
        )

        if data is None:
            return self.failure(
                f"SEC response was malformed for {normalized_ticker}.",
                normalized_ticker,
                warnings=["Malformed response."],
            )

        return ProviderResult.ok(
            data=data,
            message="SEC institutional metrics retrieved.",
            source=self.SOURCE,
            metadata={
                "ticker": normalized_ticker,
                "cik": resolved.data["cik"],
                "filings": len(data["filing_urls"]),
            },
        )

    def get_insider_activity(self, ticker):
        normalized_ticker = self.normalize_ticker(ticker)

        if normalized_ticker is None:
            return self.missing_ticker_result()

        resolved = self.resolve_submission(normalized_ticker)

        if not resolved.success:
            return resolved

        data = self.insider_activity_from_submission(
            resolved.data["submission"],
            resolved.data["cik"],
        )

        if data is None:
            return self.failure(
                f"SEC response was malformed for {normalized_ticker}.",
                normalized_ticker,
                warnings=["Malformed response."],
            )

        return ProviderResult.ok(
            data=data,
            message="SEC insider activity retrieved.",
            source=self.SOURCE,
            metadata={
                "ticker": normalized_ticker,
                "cik": resolved.data["cik"],
                "filings": sum(len(items) for items in data.values()),
            },
        )

    def resolve_submission(self, ticker):
        try:
            ticker_map = self.fetch_json(self.ticker_url)
            cik = self.cik_for_ticker(ticker_map, ticker)
        except HTTPError as exc:
            return self.http_failure(exc, ticker)
        except (URLError, TimeoutError, OSError) as exc:
            return self.failure(
                f"SEC request failed for {ticker}.",
                ticker,
                warnings=[str(exc)],
            )
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            return self.failure(
                f"SEC response was malformed for {ticker}.",
                ticker,
                warnings=[str(exc)],
            )

        if cik is None:
            return self.failure(
                f"No SEC CIK mapping found for {ticker}.",
                ticker,
            )

        try:
            submission = self.fetch_json(self.submission_url(cik))
        except HTTPError as exc:
            return self.http_failure(exc, ticker)
        except (URLError, TimeoutError, OSError) as exc:
            return self.failure(
                f"SEC request failed for {ticker}.",
                ticker,
                warnings=[str(exc)],
            )
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            return self.failure(
                f"SEC response was malformed for {ticker}.",
                ticker,
                warnings=[str(exc)],
            )

        if not isinstance(submission, dict):
            return self.failure(
                f"SEC response was malformed for {ticker}.",
                ticker,
                warnings=["Malformed response."],
            )

        return ProviderResult.ok(
            data={"cik": cik, "submission": submission},
            message="SEC submission retrieved.",
            source=self.SOURCE,
            metadata={"ticker": ticker, "cik": cik},
        )

    def fetch_json(self, url):
        request = Request(url, headers={"User-Agent": self.user_agent})

        with self.opener(request, timeout=30) as response:
            raw = response.read()

        return json.loads(raw.decode("utf-8"))

    def submission_url(self, cik):
        return f"{self.base_url}/submissions/CIK{cik}.json"

    @classmethod
    def institutional_metrics_from_submission(cls, submission, cik):
        recent = cls.recent_filings(submission)

        if recent is None:
            return None

        filings = [
            filing for filing in recent
            if str(filing.get("form", "")).upper().startswith("13F")
        ]
        latest = filings[0] if filings else None

        return {
            "latest_13f_filing_date": latest.get("filing_date") if latest else None,
            "reporting_institutions": cls.reporting_institutions(submission),
            "institutional_ownership_summary": cls.ownership_summary(submission),
            "filing_urls": [
                cls.filing_url(cik, filing["accession_number"])
                for filing in filings
                if filing.get("accession_number")
            ],
        }

    @classmethod
    def insider_activity_from_submission(cls, submission, cik):
        recent = cls.recent_filings(submission)

        if recent is None:
            return None

        results = {
            "form_3": [],
            "form_4": [],
            "form_5": [],
        }
        form_keys = {
            "3": "form_3",
            "4": "form_4",
            "5": "form_5",
        }

        for filing in recent:
            form = str(filing.get("form", "")).upper()

            if form not in form_keys:
                continue

            results[form_keys[form]].append(
                {
                    "insider_name": filing.get("insider_name"),
                    "filing_date": filing.get("filing_date"),
                    "transaction_type": filing.get("transaction_type"),
                    "shares": filing.get("shares"),
                    "price": filing.get("price"),
                    "filing_url": cls.filing_url(cik, filing["accession_number"])
                    if filing.get("accession_number")
                    else None,
                }
            )

        return results

    @classmethod
    def recent_filings(cls, submission):
        recent = submission.get("filings", {}).get("recent")

        if not isinstance(recent, dict):
            return None

        forms = recent.get("form")
        filing_dates = recent.get("filingDate")
        accession_numbers = recent.get("accessionNumber")

        if not all(isinstance(value, list) for value in [forms, filing_dates, accession_numbers]):
            return None

        if not (len(forms) == len(filing_dates) == len(accession_numbers)):
            return None

        owner_names = cls.optional_list(recent, "reportingOwnerName", len(forms))
        transaction_types = cls.optional_list(recent, "transactionType", len(forms))
        shares = cls.optional_list(recent, "transactionShares", len(forms))
        prices = cls.optional_list(recent, "transactionPricePerShare", len(forms))

        return [
            {
                "form": forms[index],
                "filing_date": filing_dates[index],
                "accession_number": accession_numbers[index],
                "insider_name": owner_names[index],
                "transaction_type": transaction_types[index],
                "shares": shares[index],
                "price": prices[index],
            }
            for index in range(len(forms))
        ]

    @staticmethod
    def optional_list(recent, key, expected_length):
        values = recent.get(key)

        if not isinstance(values, list) or len(values) != expected_length:
            return [None] * expected_length

        return values

    @staticmethod
    def reporting_institutions(submission):
        entity_name = submission.get("name")

        if not entity_name:
            return []

        return [entity_name]

    @staticmethod
    def ownership_summary(submission):
        summary = submission.get("institutionalOwnershipSummary")

        if isinstance(summary, dict):
            return dict(summary)

        return None

    @staticmethod
    def filing_url(cik, accession_number):
        compact_accession = str(accession_number).replace("-", "")
        return (
            f"https://www.sec.gov/Archives/edgar/data/"
            f"{int(cik)}/{compact_accession}/{accession_number}-index.html"
        )

    @staticmethod
    def cik_for_ticker(ticker_map, ticker):
        if not isinstance(ticker_map, dict):
            return None

        for item in ticker_map.values():
            if not isinstance(item, dict):
                return None

            if str(item.get("ticker", "")).upper() != ticker:
                continue

            cik = item.get("cik_str")

            try:
                return f"{int(cik):010d}"
            except (TypeError, ValueError):
                return None

        return None

    def not_implemented_result(self, ticker, data_type):
        normalized_ticker = self.normalize_ticker(ticker)

        if normalized_ticker is None:
            return self.missing_ticker_result()

        return self.failure(
            f"SEC EDGAR {data_type} provider is not yet implemented.",
            normalized_ticker,
            warnings=["Not yet implemented."],
        )

    @classmethod
    def http_failure(cls, error, ticker):
        if error.code == 429:
            return cls.failure(
                f"SEC rate limit reached for {ticker}.",
                ticker,
                warnings=["Rate limited."],
            )

        return cls.failure(
            f"SEC request failed for {ticker}.",
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
