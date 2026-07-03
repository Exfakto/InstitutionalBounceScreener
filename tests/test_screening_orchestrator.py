import sqlite3
from types import SimpleNamespace

from database.manager import DatabaseManager
from services.bounce_composite_scoring_engine import BounceCompositeScoreResult
from services.candidate_pipeline_adapter import CandidatePipelineAdapter
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

    def get_price_history(self, ticker):
        return list(self.rows)


class FakeSupportEngine:
    def __init__(self, fail_tickers=None, warnings=None):
        self.fail_tickers = set(fail_tickers or [])
        self.warnings = warnings or {}

    def detect_support_zones(self, ticker, prices):
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

    def analyze_bounces(self, ticker, prices, zones):
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

    def calculate(self, prices, ticker=None):
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

    def score_ticker(self, ticker):
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

    def score(self, ticker=None, support=None, bounce=None, technical=None, institutional=None):
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
    )


class FailingPipelineAdapter:
    def __init__(self, repository):
        self.repository = repository

    def run(self, *args, **kwargs):
        raise RuntimeError("adapter failed")


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
