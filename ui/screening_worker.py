from PySide6.QtCore import QThread, Signal

from services.candidate_pipeline_adapter import CandidatePipelineAdapter
from services.screening_orchestrator import ScreeningOrchestrator


class ScreeningWorker(QThread):
    started_signal = Signal(str)
    progress_signal = Signal(object)
    completed_signal = Signal(object)
    failed_signal = Signal(str)
    cancelled_signal = Signal(object)

    def __init__(self, tickers, repository=None, orchestrator=None, run_id=None, parent=None):
        super().__init__(parent)
        self.tickers = list(tickers or [])
        self.repository = repository
        self.orchestrator = orchestrator
        self.run_id = run_id
        self._cancel_requested = False

    def request_cancel(self):
        self._cancel_requested = True

    def is_cancel_requested(self):
        return self._cancel_requested

    def run(self):
        try:
            self.started_signal.emit("Screening started")
            self.progress_signal.emit(
                {
                    "total_tickers": len(self.tickers),
                    "processed_tickers": 0,
                    "current_ticker": None,
                    "progress_percentage": 0,
                    "status_message": f"Processing {len(self.tickers)} tickers",
                }
            )
            orchestrator = self.orchestrator or self.build_orchestrator()
            result = orchestrator.run(
                self.tickers,
                run_id=self.run_id,
                progress_callback=self.progress_signal.emit,
                cancellation_callback=self.is_cancel_requested,
            )
            if getattr(result, "status", "") in {"CANCELLED", "PARTIAL_CANCELLED"}:
                self.cancelled_signal.emit(result)
            else:
                self.completed_signal.emit(result)
        except Exception as exc:
            self.failed_signal.emit(str(exc))

    def build_orchestrator(self):
        pipeline_adapter = (
            CandidatePipelineAdapter(self.repository)
            if self.repository is not None
            else None
        )
        return ScreeningOrchestrator(
            price_history_provider=self.repository,
            pipeline_adapter=pipeline_adapter,
            repository=self.repository,
        )
