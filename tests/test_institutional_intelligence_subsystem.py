import sqlite3
from abc import ABC

import pytest

from database.manager import DatabaseManager
from services.institutional_data_provider import (
    InstitutionalDataProvider,
    LocalInstitutionalDataProvider,
    UnavailableInstitutionalDataProvider,
)
from services.institutional_intelligence_engine import (
    InstitutionalIntelligenceEngine,
    InstitutionalSignal,
)


def build_manager():
    manager = DatabaseManager.__new__(DatabaseManager)
    manager.connection = sqlite3.connect(":memory:")
    manager.connection.row_factory = sqlite3.Row
    manager.cursor = manager.connection.cursor()
    manager.initialize()
    return manager


class FakeProvider(InstitutionalDataProvider):
    def __init__(self, records):
        self.records = records

    def fetch_for_ticker(self, ticker):
        return self.records.get(ticker)

    def fetch_for_tickers(self, tickers):
        return {ticker: self.records.get(ticker) for ticker in tickers}


def test_institutional_data_provider_interface_contract():
    assert issubclass(InstitutionalDataProvider, ABC)

    with pytest.raises(TypeError):
        InstitutionalDataProvider()


def test_local_provider_fetches_single_ticker_from_repository():
    manager = build_manager()
    manager.upsert_institutional_data(
        {
            "ticker": "AAPL",
            "institutional_ownership_pct": 71,
            "institutional_ownership_change_qoq": 2.2,
            "net_institutional_buying": 200_000_000,
            "insider_buying_flag": 1,
            "insider_selling_flag": 0,
            "source": "unit-test",
            "as_of_date": "2026-06-30",
        }
    )
    provider = LocalInstitutionalDataProvider(manager)

    record = provider.fetch_for_ticker("aapl")

    assert record.ticker == "AAPL"
    assert record.institutional_ownership_pct == 71
    assert record.source == "unit-test"
    assert record.as_of_date == "2026-06-30"
    manager.close()


def test_local_provider_batch_returns_empty_records_for_missing_tickers():
    manager = build_manager()
    manager.upsert_institutional_data(
        {
            "ticker": "MSFT",
            "institutional_ownership_pct": 65,
            "insider_buying_flag": 0,
            "insider_selling_flag": 0,
        }
    )
    provider = LocalInstitutionalDataProvider(manager)

    records = provider.fetch_for_tickers(["msft", "missing"])

    assert set(records) == {"MSFT", "MISSING"}
    assert records["MSFT"].institutional_ownership_pct == 65
    assert records["MISSING"].ticker == "MISSING"
    assert records["MISSING"].institutional_ownership_pct is None
    assert records["MISSING"].insider_buying_flag is None
    manager.close()


def test_engine_scores_single_ticker():
    manager = build_manager()
    manager.upsert_institutional_data(
        {
            "ticker": "NVDA",
            "institutional_ownership_pct": 75,
            "institutional_ownership_change_qoq": 4,
            "net_institutional_buying": 450_000_000,
            "insider_buying_flag": 1,
            "insider_selling_flag": 0,
            "source": "local",
            "as_of_date": "2026-07-01",
        }
    )
    engine = InstitutionalIntelligenceEngine(LocalInstitutionalDataProvider(manager))

    signal = engine.score_ticker("nvda")

    assert isinstance(signal, InstitutionalSignal)
    assert signal.ticker == "NVDA"
    assert signal.source == "local"
    assert signal.as_of_date == "2026-07-01"
    assert signal.score_result.overall_institutional_strength_score >= 85
    assert signal.warnings == []
    manager.close()


def test_engine_scores_batch_tickers():
    manager = build_manager()
    manager.upsert_institutional_data(
        {
            "ticker": "AAA",
            "institutional_ownership_pct": 75,
            "institutional_ownership_change_qoq": 3,
            "net_institutional_buying": 350_000_000,
            "insider_buying_flag": 1,
            "insider_selling_flag": 0,
        }
    )
    manager.upsert_institutional_data(
        {
            "ticker": "BBB",
            "institutional_ownership_pct": 15,
            "institutional_ownership_change_qoq": -4,
            "net_institutional_buying": -300_000_000,
            "insider_buying_flag": 0,
            "insider_selling_flag": 1,
        }
    )
    engine = InstitutionalIntelligenceEngine(LocalInstitutionalDataProvider(manager))

    signals = engine.score_tickers(["bbb", "aaa"])

    assert list(signals) == ["BBB", "AAA"]
    assert signals["AAA"].score_result.overall_institutional_strength_score > signals["BBB"].score_result.overall_institutional_strength_score
    manager.close()


def test_engine_missing_data_returns_neutral_signal_with_warnings():
    manager = build_manager()
    engine = InstitutionalIntelligenceEngine(LocalInstitutionalDataProvider(manager))

    signal = engine.score_ticker("MISS")

    assert signal.ticker == "MISS"
    assert signal.raw_institutional_data.ticker == "MISS"
    assert signal.score_result.overall_institutional_strength_score == 50.0
    assert "Missing institutional ownership" in signal.warnings
    assert "Missing insider buying flag" in signal.warnings
    manager.close()


def test_engine_missing_ticker_returns_safe_signal():
    engine = InstitutionalIntelligenceEngine(FakeProvider({}))

    signal = engine.score_ticker("")

    assert signal.ticker == ""
    assert signal.raw_institutional_data is None
    assert signal.score_result.overall_institutional_strength_score == 50.0
    assert "Missing ticker" in signal.warnings


def test_engine_without_provider_returns_unavailable_signal():
    signal = InstitutionalIntelligenceEngine(
        UnavailableInstitutionalDataProvider()
    ).score_ticker("AAPL")

    assert signal.ticker == "AAPL"
    assert signal.raw_institutional_data is None
    assert signal.institutional_score_available is False
    assert signal.score_result.overall_institutional_strength_score == 50.0
    assert "Institutional data provider unavailable; institutional score unavailable" in signal.warnings
