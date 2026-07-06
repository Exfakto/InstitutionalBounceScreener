from PySide6.QtCore import QThread, Signal

from services.candidate_pipeline_adapter import CandidatePipelineAdapter
from services.screening_orchestrator import ScreeningOrchestrator


class ScreeningWorker(QThread):
    started_signal = Signal(str)
    progress_signal = Signal(object)
    completed_signal = Signal(object)
    failed_signal = Signal(str)
    cancelled_signal = Signal(object)

    def __init__(
        self,
        tickers,
        repository=None,
        repository_factory=None,
        orchestrator=None,
        run_id=None,
        parent=None,
        market_data_lookback_years=5,
    ):
        super().__init__(parent)
        self.tickers = list(tickers or [])
        self.repository = repository
        self.repository_factory = repository_factory
        self.orchestrator = orchestrator
        self.run_id = run_id
        self.market_data_lookback_years = market_data_lookback_years
        self._cancel_requested = False

    def request_cancel(self):
        self._cancel_requested = True

    def is_cancel_requested(self):
        return self._cancel_requested

    def run(self):
        repository = None
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
            orchestrator, repository = self.build_worker_orchestrator()
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
        finally:
            if repository is not None and hasattr(repository, "close"):
                repository.close()

    def build_worker_orchestrator(self):
        if self.orchestrator is not None:
            return self.orchestrator, None
        repository = self.build_repository()
        return self.build_orchestrator(repository), repository

    def build_repository(self):
        if self.repository_factory is not None:
            return self.repository_factory()
        return self.repository

    def build_orchestrator(self, repository=None):
        repository = repository if repository is not None else self.repository
        pipeline_adapter = (
            CandidatePipelineAdapter(repository)
            if repository is not None
            else None
        )
        market_data_refresh_service = None
        if repository is not None:
            from services.market_data_refresh_service import MarketDataRefreshService
            market_data_refresh_service = MarketDataRefreshService(
                repository=repository,
                lookback_years=self.market_data_lookback_years,
            )
        return ScreeningOrchestrator(
            price_history_provider=repository,
            pipeline_adapter=pipeline_adapter,
            repository=repository,
            market_data_refresh_service=market_data_refresh_service,
        )
