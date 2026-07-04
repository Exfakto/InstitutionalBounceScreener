from PySide6.QtCore import QThread, Signal

from services.algorithm_validation_service import AlgorithmValidationService


class AlgorithmValidationWorker(QThread):
    started_signal = Signal(str)
    progress_signal = Signal(object)
    completed_signal = Signal(object)
    failed_signal = Signal(str)
    cancelled_signal = Signal(object)

    def __init__(self, repository, config=None, service=None, parent=None):
        super().__init__(parent)
        self.repository = repository
        self.config = dict(config or {})
        self.service = service
        self._cancel_requested = False

    def request_cancel(self):
        self._cancel_requested = True

    def is_cancel_requested(self):
        return self._cancel_requested

    def run(self):
        try:
            self.started_signal.emit("Algorithm validation started")
            self.progress_signal.emit(
                {
                    "total": 0,
                    "processed": 0,
                    "current_ticker": None,
                    "progress_percentage": 0,
                    "status_message": "Preparing validation",
                }
            )
            service = self.service or AlgorithmValidationService(self.repository)
            report = service.run_validation(
                start_date=self.config.get("start_date"),
                end_date=self.config.get("end_date"),
                tickers=self.config.get("tickers"),
                replay_frequency=self.config.get("replay_frequency", "monthly"),
                forward_windows=self.config.get("forward_windows"),
                max_weight_combinations=self.config.get("max_weight_combinations", 5),
                benchmark_ticker=self.config.get("benchmark_ticker", "SPY"),
                run_id=self.config.get("run_id"),
                progress_callback=self.progress_signal.emit,
                cancellation_callback=self.is_cancel_requested,
            )
            if self.is_cancel_requested():
                self.cancelled_signal.emit(report)
            else:
                self.completed_signal.emit(report)
        except Exception as exc:
            self.failed_signal.emit(str(exc))
