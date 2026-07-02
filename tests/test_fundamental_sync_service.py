import sqlite3

from database.manager import DatabaseManager
from database.schema import FUNDAMENTALS_TABLE
from providers.provider_result import ProviderResult
from services.fundamental_sync_service import FundamentalSyncService


class FakeLiveDataService:

    def __init__(self, profile_result=None, fundamentals_result=None):
        self.profile_result = profile_result or ProviderResult.ok(
            data={},
            message="profile ok",
            source="fmp",
        )
        self.fundamentals_result = fundamentals_result or ProviderResult.ok(
            data={},
            message="fundamentals ok",
            source="fmp",
        )
        self.calls = []

    def get_company_profile(self, ticker):
        self.calls.append(("get_company_profile", ticker))
        return self.profile_result

    def get_fundamentals(self, ticker):
        self.calls.append(("get_fundamentals", ticker))
        return self.fundamentals_result


def build_manager():
    manager = DatabaseManager.__new__(DatabaseManager)
    manager.connection = sqlite3.connect(":memory:")
    manager.connection.row_factory = sqlite3.Row
    manager.cursor = manager.connection.cursor()
    manager.cursor.execute(FUNDAMENTALS_TABLE)
    manager.connection.commit()
    return manager


def profile_payload():
    return {
        "symbol": "AAPL",
        "companyName": "Apple Inc.",
        "sector": "Technology",
        "industry": "Consumer Electronics",
        "mktCap": 3000000000000,
    }


def fundamentals_payload():
    return {
        "income_statement": [
            {"revenue": 1100, "eps": 6.0},
            {"revenue": 1000, "eps": 5.0},
        ],
        "balance_sheet_statement": [
            {"totalDebt": 120, "totalStockholdersEquity": 100}
        ],
        "cash_flow_statement": [{"freeCashFlow": 95000000000}],
        "ratios": [
            {
                "returnOnEquity": 1.45,
                "grossProfitMargin": 0.46,
                "currentRatio": 0.9,
            }
        ],
    }


def build_service(profile_result=None, fundamentals_result=None):
    live_service = FakeLiveDataService(profile_result, fundamentals_result)
    database_manager = build_manager()
    service = FundamentalSyncService(
        live_data_service=live_service,
        database_manager=database_manager,
    )
    return service, live_service, database_manager


def test_sync_ticker_inserts_new_fundamentals():
    profile = ProviderResult.ok(data=profile_payload(), message="ok", source="fmp")
    fundamentals = ProviderResult.ok(
        data=fundamentals_payload(),
        message="ok",
        source="fmp",
    )
    service, live_service, database_manager = build_service(profile, fundamentals)

    summary = service.sync_ticker(" aapl ")
    stored = database_manager.get_fundamentals("AAPL")

    assert summary["ticker"] == "AAPL"
    assert summary["processed"] == 1
    assert summary["inserted"] == 1
    assert summary["updated"] == 0
    assert summary["failed"] == 0
    assert summary["warnings"] == []
    assert live_service.calls == [
        ("get_company_profile", "AAPL"),
        ("get_fundamentals", "AAPL"),
    ]
    assert stored["company_name"] == "Apple Inc."
    assert stored["sector"] == "Technology"
    assert stored["industry"] == "Consumer Electronics"
    assert stored["market_cap"] == 3000000000000
    assert stored["revenue_growth_ttm"] == 10.0
    assert stored["eps_growth_ttm"] == 20.0
    assert stored["roe"] == 1.45
    assert stored["gross_margin"] == 0.46
    assert stored["free_cash_flow"] == 95000000000
    assert stored["debt_to_equity"] == 1.2
    assert stored["current_ratio"] == 0.9

    database_manager.close()


def test_sync_ticker_updates_existing_row():
    profile = ProviderResult.ok(data=profile_payload(), message="ok", source="fmp")
    fundamentals = ProviderResult.ok(
        data=fundamentals_payload(),
        message="ok",
        source="fmp",
    )
    service, _, database_manager = build_service(profile, fundamentals)

    first = service.sync_ticker("AAPL")
    second = service.sync_ticker("AAPL")

    assert first["inserted"] == 1
    assert second["updated"] == 1
    assert database_manager.fundamentals_count() == 1

    database_manager.close()


def test_sync_tickers_aggregates_summaries():
    profile = ProviderResult.ok(data=profile_payload(), message="ok", source="fmp")
    fundamentals = ProviderResult.ok(
        data=fundamentals_payload(),
        message="ok",
        source="fmp",
    )
    service, _, database_manager = build_service(profile, fundamentals)

    summary = service.sync_tickers(["aapl", "msft"])

    assert summary["ticker"] == "MULTIPLE"
    assert summary["processed"] == 2
    assert summary["inserted"] == 2
    assert summary["failed"] == 0
    assert len(summary["tickers"]) == 2

    database_manager.close()


def test_missing_ticker_fails_safely():
    service, live_service, database_manager = build_service()

    summary = service.sync_ticker(" ")

    assert summary["failed"] == 1
    assert "Ticker is required." in summary["warnings"]
    assert live_service.calls == []

    database_manager.close()


def test_provider_failure_fails_safely_when_both_requests_fail():
    failure = ProviderResult.fail(
        "FMP API key is required.",
        source="fmp",
        warnings=["Missing FMP_API_KEY."],
    )
    service, _, database_manager = build_service(failure, failure)

    summary = service.sync_ticker("AAPL")

    assert summary["failed"] == 1
    assert summary["inserted"] == 0
    assert "FMP API key is required." in summary["warnings"]
    assert "Missing FMP_API_KEY." in summary["warnings"]
    assert database_manager.fundamentals_count() == 0

    database_manager.close()


def test_partial_provider_failure_stores_available_profile_data():
    profile = ProviderResult.ok(data=profile_payload(), message="ok", source="fmp")
    failure = ProviderResult.fail(
        "No FMP fundamentals found for AAPL.",
        source="fmp",
    )
    service, _, database_manager = build_service(profile, failure)

    summary = service.sync_ticker("AAPL")
    stored = database_manager.get_fundamentals("AAPL")

    assert summary["inserted"] == 1
    assert summary["failed"] == 0
    assert "No FMP fundamentals found for AAPL." in summary["warnings"]
    assert stored["company_name"] == "Apple Inc."
    assert stored["market_cap"] == 3000000000000

    database_manager.close()


def test_empty_data_skips_without_crashing():
    profile = ProviderResult.ok(data={}, message="empty", source="fmp")
    fundamentals = ProviderResult.ok(data={}, message="empty", source="fmp")
    service, _, database_manager = build_service(profile, fundamentals)

    summary = service.sync_ticker("AAPL")

    assert summary["processed"] == 0
    assert summary["skipped"] == 1
    assert summary["failed"] == 0
    assert "Provider returned no usable fundamental data." in summary["warnings"]
    assert database_manager.fundamentals_count() == 0

    database_manager.close()


def test_invalid_rows_are_ignored_with_profile_still_stored():
    profile = ProviderResult.ok(data=profile_payload(), message="ok", source="fmp")
    fundamentals = ProviderResult.ok(
        data={
            "income_statement": ["not-a-row"],
            "cash_flow_statement": ["not-a-row"],
            "ratios": ["not-a-row"],
        },
        message="ok",
        source="fmp",
    )
    service, _, database_manager = build_service(profile, fundamentals)

    summary = service.sync_ticker("AAPL")
    stored = database_manager.get_fundamentals("AAPL")

    assert summary["inserted"] == 1
    assert stored["company_name"] == "Apple Inc."
    assert stored["revenue_growth_ttm"] is None

    database_manager.close()
