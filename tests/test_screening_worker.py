from types import SimpleNamespace

from PySide6.QtWidgets import QApplication

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
