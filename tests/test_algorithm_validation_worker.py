from PySide6.QtWidgets import QApplication

from ui.algorithm_validation_worker import AlgorithmValidationWorker


def app():
    return QApplication.instance() or QApplication([])


class FakeValidationService:
    def __init__(self, fail=False):
        self.fail = fail
        self.progress_callbacks = []
        self.cancel_callbacks = []

    def run_validation(self, **kwargs):
        if self.fail:
            raise RuntimeError("validation exploded")
        progress_callback = kwargs["progress_callback"]
        cancellation_callback = kwargs["cancellation_callback"]
        self.progress_callbacks.append(progress_callback)
        self.cancel_callbacks.append(cancellation_callback)
        progress_callback({"progress_percentage": 50, "status_message": "Halfway"})
        return {"run_id": kwargs.get("run_id") or "worker-run", "cancelled": cancellation_callback()}


def test_algorithm_validation_worker_completed_signal_and_progress():
    app()
    service = FakeValidationService()
    worker = AlgorithmValidationWorker(
        repository=object(),
        config={"start_date": "2024-01-01", "end_date": "2024-02-01"},
        service=service,
    )
    progress = []
    completed = []
    worker.progress_signal.connect(progress.append)
    worker.completed_signal.connect(completed.append)

    worker.run()

    assert len(progress) >= 2
    assert completed[0]["run_id"] == "worker-run"


def test_algorithm_validation_worker_cancelled_signal():
    app()
    service = FakeValidationService()
    worker = AlgorithmValidationWorker(repository=object(), service=service)
    cancelled = []
    worker.cancelled_signal.connect(cancelled.append)
    worker.request_cancel()

    worker.run()

    assert cancelled[0]["cancelled"] is True


def test_algorithm_validation_worker_failed_signal():
    app()
    worker = AlgorithmValidationWorker(
        repository=object(),
        service=FakeValidationService(fail=True),
    )
    failures = []
    worker.failed_signal.connect(failures.append)

    worker.run()

    assert failures == ["validation exploded"]
