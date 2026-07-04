from PySide6.QtCore import QThread, Signal

from services.beta_testing_service import BetaWorkflowService


class BetaTestingWorker(QThread):
    started_signal = Signal(str)
    progress_signal = Signal(object)
    completed_signal = Signal(object)
    failed_signal = Signal(str)
    cancelled_signal = Signal(object)

    def __init__(self, repository=None, config=None, service=None, parent=None):
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
            self.started_signal.emit("Beta workflow started")
            service = self.service or BetaWorkflowService(repository=self.repository)
            result = service.run_workflow(
                top_n=self.config.get("top_n", 10),
                run_backtest=self.config.get("run_backtest", False),
                export_report=self.config.get("export_report", True),
                progress_callback=self.progress_signal.emit,
                cancellation_callback=self.is_cancel_requested,
                run_id=self.config.get("run_id"),
            )
            if self.is_cancel_requested() or getattr(result.run, "status", "") == "CANCELLED":
                self.cancelled_signal.emit(result)
            else:
                self.completed_signal.emit(result)
        except Exception as exc:
            self.failed_signal.emit(str(exc))
