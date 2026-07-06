import sqlite3
from types import SimpleNamespace

from database.manager import DatabaseManager
from services.bounce_composite_scoring_engine import BounceCompositeScoreResult
from services.candidate_pipeline_adapter import CandidatePipelineAdapter
from services.institutional_data_provider import LocalInstitutionalDataProvider
from services.screening_orchestrator import ScreeningOrchestrator


def build_manager():
    manager = DatabaseManager.__new__(DatabaseManager)
    manager.connection = sqlite3.connect(":memory:")
    manager.connection.row_factory = sqlite3.Row
    manager.cursor = manager.connection.cursor()
    manager.initialize()
    return manager


class FakePriceProvider:
    def __init__(self, rows=None):
        self.rows = rows or [
            {"date": "2026-01-01", "open": 10, "high": 11, "low": 9, "close": 10, "volume": 1000}
        ]
        self.calls = []

    def fetch_ohlcv(self, ticker, start_date=None, end_date=None):
        self.calls.append(ticker)
        return list(self.rows)


class FakeSupportEngine:
    def __init__(self, fail_tickers=None, warnings=None):
        self.fail_tickers = set(fail_tickers or [])
        self.warnings = warnings or {}
        self.calls = []

    def detect_support_zones(self, ticker, prices):
        self.calls.append(ticker)
        if ticker in self.fail_tickers:
            raise RuntimeError("support failed")
        zone = SimpleNamespace(ticker=ticker, support_strength_score=85, confidence_score=85)
        return SimpleNamespace(
            ticker=ticker,
            zones=[zone],
            primary_zone=zone,
            warnings=self.warnings.get(ticker, []),
        )


class FakeBounceEngine:
    def __init__(self, warnings=None):
        self.warnings = warnings or {}
        self.calls = []

    def analyze_bounces(self, ticker, prices, zones):
        self.calls.append(ticker)
        return [
            SimpleNamespace(
                ticker=ticker,
                bounce_success_rate=85,
                average_bounce_pct=18,
                largest_bounce_pct=30,
                total_support_tests=5,
                failed_support_breaks=0,
                warnings=self.warnings.get(ticker, []),
            )
        ]


class FakeTechnicalEngine:
    def __init__(self, warnings=None):
        self.warnings = warnings or {}
        self.calls = []

    def calculate(self, prices, ticker=None):
        self.calls.append(ticker)
        return SimpleNamespace(
            ticker=ticker,
            close=100,
            ema20=95,
            ema50=90,
            ema200=80,
            rsi14=62,
            macd_histogram=1.2,
            relative_volume=1.5,
            warnings=self.warnings.get(ticker, []),
        )


class FakeInstitutionalEngine:
    def __init__(self, warnings=None):
        self.warnings = warnings or {}
        self.calls = []

    def score_ticker(self, ticker):
        self.calls.append(ticker)
        score_result = SimpleNamespace(
            overall_institutional_strength_score=88,
            warnings=[],
        )
        return SimpleNamespace(
            ticker=ticker,
            score_result=score_result,
            warnings=self.warnings.get(ticker, []),
        )


class FakeCompositeEngine:
    def __init__(self, scores=None, warnings=None):
        self.scores = scores or {}
        self.warnings = warnings or {}
        self.calls = []

    def score(self, ticker=None, support=None, bounce=None, technical=None, institutional=None):
        self.calls.append(ticker)
        final_score = self.scores.get(ticker, 90)
        return BounceCompositeScoreResult(
            ticker=ticker,
            final_score=final_score,
            support_score=final_score,
            bounce_score=final_score,
            technical_score=final_score,
            institutional_score=final_score,
            confidence_level="HIGH",
            explanation=[f"{ticker} composite"],
            warnings=self.warnings.get(ticker, []),
        )


def build_orchestrator(manager, **overrides):
    return ScreeningOrchestrator(
        price_history_provider=overrides.get("price_history_provider", FakePriceProvider()),
        support_engine=overrides.get("support_engine", FakeSupportEngine()),
        bounce_engine=overrides.get("bounce_engine", FakeBounceEngine()),
        technical_engine=overrides.get("technical_engine", FakeTechnicalEngine()),
        institutional_engine=overrides.get("institutional_engine", FakeInstitutionalEngine()),
        composite_engine=overrides.get("composite_engine", FakeCompositeEngine()),
        pipeline_adapter=CandidatePipelineAdapter(manager),
        market_data_refresh_service=overrides.get("market_data_refresh_service"),
    )


class FailingPipelineAdapter:
    def __init__(self, repository):
        self.repository = repository

    def run(self, *args, **kwargs):
        raise RuntimeError("adapter failed")


class FakeMarketDataRefreshService:
    def __init__(self, rows=None, success=True, warnings=None, errors=None):
        self.rows = (
            [
                {
                    "date": "2026-01-02",
                    "open": 20,
                    "high": 21,
                    "low": 19,
                    "close": 20,
                    "volume": 2000,
                }
            ]
            if rows is None
            else rows
        )
        self.success = success
        self.warnings = warnings or []
        self.errors = errors or []
        self.calls = []

    def refresh_ticker(self, ticker):
        self.calls.append(ticker)
        return SimpleNamespace(
            ticker=ticker,
            success=self.success,
            rows=list(self.rows),
            warnings=list(self.warnings),
            errors=list(self.errors),
        )


class CapturingSupportEngine(FakeSupportEngine):
    def __init__(self):
        super().__init__()
        self.prices_by_ticker = {}

    def detect_support_zones(self, ticker, prices):
        self.prices_by_ticker[ticker] = prices
        return super().detect_support_zones(ticker, prices)


def test_screening_orchestrator_successful_multi_ticker_run():
    manager = build_manager()
    orchestrator = build_orchestrator(
        manager,
        composite_engine=FakeCompositeEngine({"AAA": 92, "BBB": 78}),
    )

    result = orchestrator.run(["bbb", "aaa"], run_id="run-success")
    persisted = manager.fetch_ranked_candidates("run-success")

    assert result.run_id == "run-success"
    assert result.tickers_requested == 2
    assert result.tickers_processed == 2
    assert [item.ticker for item in result.ranked_candidates] == ["AAA", "BBB"]
    assert [item.ticker for item in persisted] == ["AAA", "BBB"]
    assert result.errors == []
    run = manager.fetch_screening_run("run-success")
    assert run["status"] == "COMPLETED"
    assert run["tickers_requested"] == 2
    assert run["tickers_processed"] == 2
    assert run["candidate_count"] == 2
    signals = manager.fetch_screening_history(run_id="run-success")
    assert {signal["ticker"] for signal in signals} == {"AAA", "BBB"}
    assert all(signal["outcome"] is None for signal in signals)
    manager.close()


def test_screening_orchestrator_one_ticker_failure_does_not_stop_run():
    manager = build_manager()
    orchestrator = build_orchestrator(
        manager,
        support_engine=FakeSupportEngine(fail_tickers={"BAD"}),
        composite_engine=FakeCompositeEngine({"AAA": 90, "CCC": 80}),
    )

    result = orchestrator.run(["AAA", "BAD", "CCC"], run_id="run-partial")
    persisted = manager.fetch_ranked_candidates("run-partial")

    assert result.tickers_requested == 3
    assert result.tickers_processed == 2
    assert [item.ticker for item in result.ranked_candidates] == ["AAA", "CCC"]
    assert [item.ticker for item in persisted] == ["AAA", "CCC"]
    assert result.errors == ["BAD: support failed"]
    run = manager.fetch_screening_run("run-partial")
    assert run["status"] == "PARTIAL"
    assert run["tickers_requested"] == 3
    assert run["tickers_processed"] == 2
    assert run["errors"] == ["BAD: support failed"]
    manager.close()


def test_screening_orchestrator_empty_ticker_input():
    manager = build_manager()
    orchestrator = build_orchestrator(manager)

    result = orchestrator.run([], run_id="empty-run")

    assert result.tickers_requested == 0
    assert result.tickers_processed == 0
    assert result.ranked_candidates == []
    assert "No tickers provided" in result.warnings
    assert "No composite scores provided" in result.warnings
    assert manager.fetch_ranked_candidates("empty-run") == []
    run = manager.fetch_screening_run("empty-run")
    assert run["status"] == "COMPLETED"
    assert run["candidate_count"] == 0
    assert "No tickers provided" in run["warnings"]
    manager.close()


def test_screening_orchestrator_run_id_propagation():
    manager = build_manager()
    orchestrator = build_orchestrator(manager)

    result = orchestrator.run(["AAA"], run_id="custom-run-id")
    persisted = manager.fetch_latest_ranked_candidates()

    assert result.run_id == "custom-run-id"
    assert persisted[0].source["run_id"] == "custom-run-id"
    assert manager.fetch_latest_screening_run()["run_id"] == "custom-run-id"
    manager.close()


def test_screening_orchestrator_collects_warnings_and_errors():
    manager = build_manager()
    orchestrator = build_orchestrator(
        manager,
        support_engine=FakeSupportEngine(warnings={"AAA": ["Support warning"]}),
        bounce_engine=FakeBounceEngine(warnings={"AAA": ["Bounce warning"]}),
        technical_engine=FakeTechnicalEngine(warnings={"AAA": ["Technical warning"]}),
        institutional_engine=FakeInstitutionalEngine(warnings={"AAA": ["Institutional warning"]}),
        composite_engine=FakeCompositeEngine(
            {"AAA": 90},
            warnings={"AAA": ["Composite warning"]},
        ),
    )

    result = orchestrator.run(["AAA"], run_id="warning-run")

    assert "AAA: Support warning" in result.warnings
    assert "AAA: Bounce warning" in result.warnings
    assert "AAA: Technical warning" in result.warnings
    assert "AAA: Institutional warning" in result.warnings
    assert "AAA: Composite warning" in result.warnings
    assert result.errors == []
    manager.close()


def test_screening_orchestrator_returns_and_persists_ranked_candidates_through_adapter():
    manager = build_manager()
    orchestrator = build_orchestrator(
        manager,
        composite_engine=FakeCompositeEngine({"WIN": 94, "REJECT": 40}),
    )

    result = orchestrator.run(["WIN", "REJECT"], run_id="adapter-run")
    persisted = manager.fetch_ranked_candidates("adapter-run")

    assert [item.ticker for item in result.ranked_candidates] == ["WIN"]
    assert [item.ticker for item in persisted] == ["WIN", "REJECT"]
    assert persisted[1].grade == "REJECT"
    assert persisted[1].rejection_reasons == ["Final score below minimum threshold (60)"]
    signals = manager.fetch_screening_history(run_id="adapter-run")
    assert {signal["ticker"] for signal in signals} == {"WIN", "REJECT"}
    run = manager.fetch_screening_run("adapter-run")
    assert run["status"] == "COMPLETED"
    assert run["candidate_count"] == 1
    manager.close()


def test_screening_orchestrator_failed_status_when_pipeline_fails():
    manager = build_manager()
    orchestrator = ScreeningOrchestrator(
        price_history_provider=FakePriceProvider(),
        support_engine=FakeSupportEngine(),
        bounce_engine=FakeBounceEngine(),
        technical_engine=FakeTechnicalEngine(),
        institutional_engine=FakeInstitutionalEngine(),
        composite_engine=FakeCompositeEngine({"AAA": 92}),
        pipeline_adapter=FailingPipelineAdapter(manager),
    )

    result = orchestrator.run(["AAA"], run_id="failed-run")
    run = manager.fetch_screening_run("failed-run")

    assert result.tickers_processed == 1
    assert result.errors == ["Pipeline persistence failed: adapter failed"]
    assert run["status"] == "FAILED"
    assert run["errors"] == ["Pipeline persistence failed: adapter failed"]
    assert run["candidate_count"] == 1
    manager.close()


def test_screening_orchestrator_cooperative_cancellation_persists_partial_cancelled():
    manager = build_manager()
    progress_events = []
    calls = {"count": 0}

    def cancel_after_first_progress():
        return calls["count"] > 0

    def progress_callback(progress):
        progress_events.append(progress)
        if progress["processed_tickers"] == 1:
            calls["count"] += 1

    orchestrator = build_orchestrator(
        manager,
        composite_engine=FakeCompositeEngine({"AAA": 92, "BBB": 90}),
    )

    result = orchestrator.run(
        ["AAA", "BBB"],
        run_id="cancelled-run",
        progress_callback=progress_callback,
        cancellation_callback=cancel_after_first_progress,
    )
    run = manager.fetch_screening_run("cancelled-run")

    assert result.status == "PARTIAL_CANCELLED"
    assert result.tickers_processed == 1
    assert "Screening cancelled" in result.warnings
    assert run["status"] == "PARTIAL_CANCELLED"
    assert run["tickers_requested"] == 2
    assert run["tickers_processed"] == 1
    assert "Screening cancelled" in run["warnings"]
    assert any(event["current_ticker"] == "BBB" for event in progress_events)
    manager.close()


def test_screening_orchestrator_cancel_before_processing_persists_cancelled():
    manager = build_manager()
    orchestrator = build_orchestrator(manager)

    result = orchestrator.run(
        ["AAA"],
        run_id="cancel-before-run",
        cancellation_callback=lambda: True,
    )
    run = manager.fetch_screening_run("cancel-before-run")

    assert result.status == "CANCELLED"
    assert result.tickers_processed == 0
    assert run["status"] == "CANCELLED"
    manager.close()


def test_screening_orchestrator_batch_processing_emits_batch_progress():
    manager = build_manager()
    progress_events = []
    orchestrator = build_orchestrator(
        manager,
        composite_engine=FakeCompositeEngine(
            {"AAA": 92, "BBB": 90, "CCC": 88, "DDD": 86, "EEE": 84}
        ),
    )

    result = orchestrator.run(
        ["AAA", "BBB", "CCC", "DDD", "EEE"],
        run_id="batch-run",
        batch_size=2,
        progress_callback=progress_events.append,
    )

    batch_events = [event for event in progress_events if "batch_index" in event]
    assert result.tickers_processed == 5
    assert [event["batch_index"] for event in batch_events if event["status_message"].startswith("Starting")] == [1, 2, 3]
    assert batch_events[0]["batch_count"] == 3
    assert batch_events[0]["batch_size"] == 2
    assert batch_events[-1]["status_message"] == "Completed batch 3 of 3"
    manager.close()


def test_screening_orchestrator_duplicate_ticker_caching_avoids_recomputation():
    manager = build_manager()
    price_provider = FakePriceProvider()
    support_engine = FakeSupportEngine()
    bounce_engine = FakeBounceEngine()
    technical_engine = FakeTechnicalEngine()
    institutional_engine = FakeInstitutionalEngine()
    composite_engine = FakeCompositeEngine({"AAA": 92})
    orchestrator = build_orchestrator(
        manager,
        price_history_provider=price_provider,
        support_engine=support_engine,
        bounce_engine=bounce_engine,
        technical_engine=technical_engine,
        institutional_engine=institutional_engine,
        composite_engine=composite_engine,
    )

    result = orchestrator.run(["aaa", "AAA", " aaa "], run_id="dedupe-run", batch_size=1)

    assert result.tickers_requested == 1
    assert result.tickers_processed == 1
    assert price_provider.calls == ["AAA"]
    assert support_engine.calls == ["AAA"]
    assert bounce_engine.calls == ["AAA"]
    assert technical_engine.calls == ["AAA"]
    assert institutional_engine.calls == ["AAA"]
    assert composite_engine.calls == ["AAA"]
    manager.close()


def test_screening_orchestrator_uses_market_data_refresh_service():
    manager = build_manager()
    refresh_service = FakeMarketDataRefreshService()
    support_engine = CapturingSupportEngine()
    orchestrator = build_orchestrator(
        manager,
        price_history_provider=None,
        market_data_refresh_service=refresh_service,
        support_engine=support_engine,
    )

    result = orchestrator.run(["AAA"], run_id="market-data-run")

    assert result.tickers_processed == 1
    assert refresh_service.calls == ["AAA"]
    assert support_engine.prices_by_ticker["AAA"][0]["close"] == 20
    assert result.errors == []
    manager.close()


def test_screening_orchestrator_missing_market_data_adds_warning_not_error():
    manager = build_manager()
    refresh_service = FakeMarketDataRefreshService(
        rows=[],
        success=False,
        warnings=["No cached data"],
        errors=["Provider unavailable"],
    )
    orchestrator = build_orchestrator(
        manager,
        price_history_provider=None,
        market_data_refresh_service=refresh_service,
    )

    result = orchestrator.run(["AAA"], run_id="missing-market-data-run")

    assert result.tickers_processed == 1
    assert "AAA: No cached data" in result.warnings
    assert "AAA: Provider unavailable" in result.warnings
    assert "AAA: Missing OHLCV data" in result.warnings
    assert result.errors == []
    manager.close()


def test_screening_orchestrator_ranks_candidates_without_institutional_provider():
    manager = build_manager()
    orchestrator = ScreeningOrchestrator(
        price_history_provider=FakePriceProvider(),
        support_engine=FakeSupportEngine(),
        bounce_engine=FakeBounceEngine(),
        technical_engine=FakeTechnicalEngine(),
        composite_engine=None,
        pipeline_adapter=CandidatePipelineAdapter(manager),
    )

    result = orchestrator.run(["AAA"], run_id="no-institutional-provider")

    assert [item.ticker for item in result.ranked_candidates] == ["AAA"]
    assert result.ranked_candidates[0].category_scores["institutional_score"] == 50.0
    assert result.errors == []
    assert any("no institutional rows found" in warning for warning in result.warnings)
    assert any("institutional score unavailable" in warning.lower() for warning in result.warnings)
    manager.close()


def test_screening_orchestrator_uses_repository_institutional_provider_when_available():
    manager = build_manager()
    manager.upsert_institutional_data(
        {
            "ticker": "AAA",
            "institutional_ownership_pct": 75,
            "institutional_ownership_change_qoq": 5,
            "net_institutional_buying": 500_000_000,
            "insider_buying_flag": 1,
            "insider_selling_flag": 0,
            "source": "unit",
            "as_of_date": "2026-07-01",
        }
    )
    orchestrator = ScreeningOrchestrator(
        price_history_provider=FakePriceProvider(),
        support_engine=FakeSupportEngine(),
        bounce_engine=FakeBounceEngine(),
        technical_engine=FakeTechnicalEngine(),
        repository=manager,
    )

    result = orchestrator.run(["AAA"], run_id="with-institutional-provider")

    assert [item.ticker for item in result.ranked_candidates] == ["AAA"]
    assert result.ranked_candidates[0].category_scores["institutional_score"] > 90.0
    assert result.errors == []
    assert not any("provider unavailable" in warning.lower() for warning in result.warnings)
    manager.close()


def test_screening_orchestrator_integrates_local_institutional_provider_from_repository(caplog):
    manager = build_manager()
    manager.upsert_ohlcv(
        "AAA",
        [
            {
                "date": "2026-01-01",
                "open": 10,
                "high": 11,
                "low": 9,
                "close": 10,
                "volume": 1000,
            }
        ],
        source="unit",
    )
    manager.upsert_institutional_data(
        {
            "ticker": "AAA",
            "institutional_ownership_pct": 75,
            "institutional_ownership_change_qoq": 5,
            "net_institutional_buying": 500_000_000,
            "insider_buying_flag": 1,
            "insider_selling_flag": 0,
            "source": "unit",
            "as_of_date": "2026-07-01",
        }
    )
    orchestrator = ScreeningOrchestrator(
        support_engine=FakeSupportEngine(),
        bounce_engine=FakeBounceEngine(),
        technical_engine=FakeTechnicalEngine(),
        repository=manager,
    )

    with caplog.at_level("INFO", logger="services.screening_orchestrator"):
        result = orchestrator.run(["AAA"], run_id="integration-local-provider")

    assert isinstance(orchestrator.institutional_engine.provider, LocalInstitutionalDataProvider)
    assert [item.ticker for item in result.ranked_candidates] == ["AAA"]
    assert result.ranked_candidates[0].category_scores["institutional_score"] > 90.0
    assert result.errors == []
    assert "Institutional provider: LocalInstitutionalDataProvider" in caplog.text
    assert "Institutional records loaded: 1" in caplog.text
    manager.close()


def test_screening_orchestrator_ranks_candidates_when_institutional_table_missing(caplog):
    manager = build_manager()
    manager.cursor.execute("DROP TABLE institutional_metrics")
    manager.connection.commit()
    manager.upsert_ohlcv(
        "AAA",
        [
            {
                "date": "2026-01-01",
                "open": 10,
                "high": 11,
                "low": 9,
                "close": 10,
                "volume": 1000,
            }
        ],
        source="unit",
    )
    orchestrator = ScreeningOrchestrator(
        support_engine=FakeSupportEngine(),
        bounce_engine=FakeBounceEngine(),
        technical_engine=FakeTechnicalEngine(),
        repository=manager,
    )

    with caplog.at_level("INFO"):
        result = orchestrator.run(["AAA"], run_id="missing-institutional-table")

    assert [item.ticker for item in result.ranked_candidates] == ["AAA"]
    assert result.ranked_candidates[0].category_scores["institutional_score"] == 50.0
    assert result.errors == []
    assert any("Institutional data unavailable" in warning for warning in result.warnings)
    assert "Institutional records loaded: 0" in caplog.text
    manager.close()
