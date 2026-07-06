from types import SimpleNamespace
import threading

from PySide6.QtWidgets import QApplication

from services.candidate_pipeline_adapter import CandidatePipelineResult
from ui import screening_worker as screening_worker_module
from ui.screening_worker import ScreeningWorker


def test_screening_worker_emits_progress_updates():
    app = QApplication.instance() or QApplication([])
    progress_events = []
    completed = []

    class FakeOrchestrator:
        def run(self, tickers, run_id=None, progress_callback=None, cancellation_callback=None):
            progress_callback(
                {
                    "total_tickers": 2,
                    "processed_tickers": 1,
                    "current_ticker": "MSFT",
                    "progress_percentage": 50,
                    "status_message": "Processing MSFT",
                }
            )
            return SimpleNamespace(status="COMPLETED", ranked_candidates=[])

    worker = ScreeningWorker(["AAPL", "MSFT"], orchestrator=FakeOrchestrator())
    worker.progress_signal.connect(progress_events.append)
    worker.completed_signal.connect(completed.append)

    worker.run()

    assert progress_events[0]["total_tickers"] == 2
    assert progress_events[1]["current_ticker"] == "MSFT"
    assert completed[0].status == "COMPLETED"


def test_screening_worker_cooperative_cancellation_emits_cancelled():
    app = QApplication.instance() or QApplication([])
    cancelled = []

    class FakeOrchestrator:
        def run(self, tickers, run_id=None, progress_callback=None, cancellation_callback=None):
            assert cancellation_callback() is True
            return SimpleNamespace(status="PARTIAL_CANCELLED", ranked_candidates=["AAPL"])

    worker = ScreeningWorker(["AAPL"], orchestrator=FakeOrchestrator())
    worker.cancelled_signal.connect(cancelled.append)

    worker.request_cancel()
    worker.run()

    assert cancelled[0].status == "PARTIAL_CANCELLED"
    assert cancelled[0].ranked_candidates == ["AAPL"]


def test_screening_worker_uses_thread_owned_repository_and_persists_results(monkeypatch):
    app = QApplication.instance() or QApplication([])
    created = []

    class ThreadOwnedRepository:
        def __init__(self):
            self.owner = threading.get_ident()
            self.ranked_candidates = []
            self.screening_runs = {}
            self.closed = False

        def assert_owner(self):
            if threading.get_ident() != self.owner:
                raise RuntimeError(
                    "SQLite objects created in a thread can only be used in that same thread"
                )

        def create_screening_run(self, **record):
            self.assert_owner()
            self.screening_runs[record["run_id"]] = dict(record)
            return record["run_id"]

        def update_screening_run(self, **record):
            self.assert_owner()
            self.screening_runs[record["run_id"]].update(record)
            return record["run_id"]

        def save_ranked_candidates(self, run_id, candidates):
            self.assert_owner()
            self.ranked_candidates.extend(candidates or [])
            return len(candidates or [])

        def close(self):
            self.assert_owner()
            self.closed = True

    class PersistingAdapter:
        def __init__(self, repository):
            self.repository = repository

        def run(self, composite_scores, run_id=None, **kwargs):
            candidate = SimpleNamespace(ticker="AAPL", rank=1, final_score=91.0)
            self.repository.save_ranked_candidates(run_id, [candidate])
            return CandidatePipelineResult(
                run_id=run_id,
                ranked_candidates=[candidate],
                rejected_candidates=[],
                warnings=[],
            )

    class PersistingOrchestrator:
        def __init__(self, repository=None, pipeline_adapter=None, **kwargs):
            self.repository = repository
            self.pipeline_adapter = pipeline_adapter

        def run(self, tickers, run_id=None, progress_callback=None, cancellation_callback=None):
            run_id = run_id or "thread-run"
            self.repository.create_screening_run(
                run_id=run_id,
                started_at="start",
                tickers_requested=len(tickers),
                tickers_processed=0,
                candidate_count=0,
                warnings=[],
                errors=[],
                status="STARTED",
            )
            result = self.pipeline_adapter.run([], run_id=run_id)
            self.repository.update_screening_run(
                run_id=run_id,
                status="COMPLETED",
                completed_at="done",
                tickers_requested=len(tickers),
                tickers_processed=len(tickers),
                candidate_count=len(result.ranked_candidates),
                warnings=[],
                errors=[],
            )
            return SimpleNamespace(
                status="COMPLETED",
                ranked_candidates=result.ranked_candidates,
            )

    def repository_factory():
        repository = ThreadOwnedRepository()
        created.append(repository)
        return repository

    monkeypatch.setattr(screening_worker_module, "CandidatePipelineAdapter", PersistingAdapter)
    monkeypatch.setattr(screening_worker_module, "ScreeningOrchestrator", PersistingOrchestrator)

    worker = ScreeningWorker(["AAPL"], repository_factory=repository_factory)
    completed = []
    failed = []
    worker.completed_signal.connect(completed.append)
    worker.failed_signal.connect(failed.append)

    worker.start()
    assert worker.wait(5000) is True
    app.processEvents()

    assert failed == []
    assert completed[0].status == "COMPLETED"
    assert len(created) == 1
    assert created[0].owner != threading.get_ident()
    assert created[0].closed is True
    assert len(created[0].ranked_candidates) == 1
    assert created[0].screening_runs["thread-run"]["status"] == "COMPLETED"
    assert created[0].screening_runs["thread-run"]["candidate_count"] == 1
