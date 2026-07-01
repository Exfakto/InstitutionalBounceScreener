import json
from urllib.error import HTTPError

from providers.sec_edgar_provider import SECEdgarProvider


class FakeResponse:

    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        if isinstance(self.payload, bytes):
            return self.payload

        return json.dumps(self.payload).encode("utf-8")


class FakeOpener:

    def __init__(self, responses=None, error=None):
        self.responses = list(responses or [])
        self.error = error
        self.calls = []

    def __call__(self, request, timeout=None):
        self.calls.append((request, timeout))

        if self.error is not None:
            raise self.error

        return FakeResponse(self.responses.pop(0))


def ticker_map():
    return {
        "0": {
            "cik_str": 320193,
            "ticker": "AAPL",
            "title": "Apple Inc.",
        }
    }


def submission_payload():
    return {
        "name": "Apple Inc.",
        "filings": {
            "recent": {
                "form": ["13F-HR", "4", "3", "5", "10-K"],
                "filingDate": [
                    "2026-02-14",
                    "2026-02-10",
                    "2026-01-20",
                    "2026-01-15",
                    "2025-10-31",
                ],
                "accessionNumber": [
                    "0000320193-26-000001",
                    "0000320193-26-000002",
                    "0000320193-26-000003",
                    "0000320193-26-000004",
                    "0000320193-25-000100",
                ],
                "reportingOwnerName": [
                    None,
                    "Jane Insider",
                    "John Insider",
                    "Alex Insider",
                    None,
                ],
                "transactionType": [None, "A", None, "D", None],
                "transactionShares": [None, 100, None, 25, None],
                "transactionPricePerShare": [None, 150.25, None, None, None],
            }
        },
        "institutionalOwnershipSummary": {
            "shares": 1000000,
            "holders": 1200,
        },
    }


def http_error(status):
    return HTTPError(
        url="https://data.sec.gov/submissions/test",
        code=status,
        msg="planned",
        hdrs=None,
        fp=None,
    )


def test_sec_edgar_provider_successful_institutional_metrics():
    opener = FakeOpener(responses=[ticker_map(), submission_payload()])
    provider = SECEdgarProvider(opener=opener)

    result = provider.get_institutional_metrics(" aapl ")

    assert result.success is True
    assert result.source == "sec_edgar"
    assert result.message == "SEC institutional metrics retrieved."
    assert result.metadata == {
        "ticker": "AAPL",
        "cik": "0000320193",
        "filings": 1,
    }
    assert result.data["latest_13f_filing_date"] == "2026-02-14"
    assert result.data["reporting_institutions"] == ["Apple Inc."]
    assert result.data["institutional_ownership_summary"] == {
        "shares": 1000000,
        "holders": 1200,
    }
    assert result.data["filing_urls"] == [
        "https://www.sec.gov/Archives/edgar/data/"
        "320193/000032019326000001/0000320193-26-000001-index.html"
    ]
    assert opener.calls[0][1] == 30
    assert opener.calls[0][0].headers["User-agent"]


def test_sec_edgar_provider_successful_insider_activity():
    opener = FakeOpener(responses=[ticker_map(), submission_payload()])
    provider = SECEdgarProvider(opener=opener)

    result = provider.get_insider_activity("aapl")

    assert result.success is True
    assert result.source == "sec_edgar"
    assert result.message == "SEC insider activity retrieved."
    assert result.metadata == {
        "ticker": "AAPL",
        "cik": "0000320193",
        "filings": 3,
    }
    assert result.data["form_4"] == [
        {
            "insider_name": "Jane Insider",
            "filing_date": "2026-02-10",
            "transaction_type": "A",
            "shares": 100,
            "price": 150.25,
            "filing_url": "https://www.sec.gov/Archives/edgar/data/"
            "320193/000032019326000002/0000320193-26-000002-index.html",
        }
    ]
    assert result.data["form_3"][0]["insider_name"] == "John Insider"
    assert result.data["form_5"][0]["transaction_type"] == "D"


def test_sec_edgar_provider_missing_ticker():
    provider = SECEdgarProvider(opener=FakeOpener())

    result = provider.get_institutional_metrics(" ")

    assert result.success is False
    assert result.message == "Ticker is required."
    assert result.source == "sec_edgar"
    assert "Missing ticker." in result.warnings


def test_sec_edgar_provider_malformed_ticker_map():
    provider = SECEdgarProvider(opener=FakeOpener(responses=[[]]))

    result = provider.get_institutional_metrics("AAPL")

    assert result.success is False
    assert result.message == "No SEC CIK mapping found for AAPL."


def test_sec_edgar_provider_malformed_submission_response():
    provider = SECEdgarProvider(opener=FakeOpener(responses=[ticker_map(), []]))

    result = provider.get_institutional_metrics("AAPL")

    assert result.success is False
    assert result.message == "SEC response was malformed for AAPL."
    assert "Malformed response." in result.warnings


def test_sec_edgar_provider_malformed_recent_filings():
    provider = SECEdgarProvider(
        opener=FakeOpener(
            responses=[
                ticker_map(),
                {"filings": {"recent": {"form": ["4"], "filingDate": []}}},
            ]
        )
    )

    result = provider.get_insider_activity("AAPL")

    assert result.success is False
    assert result.message == "SEC response was malformed for AAPL."
    assert "Malformed response." in result.warnings


def test_sec_edgar_provider_malformed_json():
    provider = SECEdgarProvider(opener=FakeOpener(responses=[b"{not-json"]))

    result = provider.get_institutional_metrics("AAPL")

    assert result.success is False
    assert result.message == "SEC response was malformed for AAPL."


def test_sec_edgar_provider_server_error():
    provider = SECEdgarProvider(opener=FakeOpener(error=http_error(500)))

    result = provider.get_institutional_metrics("AAPL")

    assert result.success is False
    assert result.message == "SEC request failed for AAPL."
    assert "HTTP 500" in result.warnings


def test_sec_edgar_provider_rate_limit():
    provider = SECEdgarProvider(opener=FakeOpener(error=http_error(429)))

    result = provider.get_institutional_metrics("AAPL")

    assert result.success is False
    assert result.message == "SEC rate limit reached for AAPL."
    assert "Rate limited." in result.warnings


def test_sec_edgar_provider_deterministic_normalization():
    first_provider = SECEdgarProvider(
        opener=FakeOpener(responses=[ticker_map(), submission_payload()])
    )
    second_provider = SECEdgarProvider(
        opener=FakeOpener(responses=[ticker_map(), submission_payload()])
    )

    first = first_provider.get_institutional_metrics(" aapl ")
    second = second_provider.get_institutional_metrics("AAPL")

    assert first.data == second.data
    assert first.metadata == second.metadata


def test_sec_edgar_provider_unimplemented_methods():
    provider = SECEdgarProvider(opener=FakeOpener())

    results = [
        provider.get_price_history("AAPL"),
        provider.get_company_profile("AAPL"),
        provider.get_fundamentals("AAPL"),
        provider.get_earnings("AAPL"),
    ]

    assert all(result.success is False for result in results)
    assert all(result.source == "sec_edgar" for result in results)
    assert all("Not yet implemented." in result.warnings for result in results)
