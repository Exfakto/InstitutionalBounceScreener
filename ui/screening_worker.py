from PySide6.QtCore import QThread, Signal

from services.candidate_pipeline_adapter import CandidatePipelineAdapter
from services.screening_orchestrator import ScreeningOrchestrator


class ScreeningWorker(QThread):
    started_signal = Signal(str)
    progress_signal = Signal(str)
    completed_signal = Signal(object)
    failed_signal = Signal(str)

    def __init__(self, tickers, repository=None, orchestrator=None, run_id=None, parent=None):
        super().__init__(parent)
        self.tickers = list(tickers or [])
        self.repository = repository
        self.orchestrator = orchestrator
        self.run_id = run_id

    def run(self):
        try:
            self.started_signal.emit("Screening started")
            self.progress_signal.emit(f"Processing {len(self.tickers)} tickers")
            orchestrator = self.orchestrator or self.build_orchestrator()
            result = orchestrator.run(self.tickers, run_id=self.run_id)
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
