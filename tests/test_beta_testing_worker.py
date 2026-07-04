from services.beta_testing_service import BetaTestRun, BetaWorkflowResult
from ui.beta_testing_worker import BetaTestingWorker


class FakeBetaService:
    def __init__(self, status="PASS", fail=False):
        self.status = status
        self.fail = fail

    def run_workflow(self, **kwargs):
        if self.fail:
            raise RuntimeError("beta exploded")
        kwargs["progress_callback"]({"progress_percentage": 50, "status_message": "Halfway"})
        return BetaWorkflowResult(
            run=BetaTestRun(
                run_id=kwargs.get("run_id") or "beta-worker",
                started_at="2026-01-01T00:00:00+00:00",
                status=self.status,
            )
        )


def test_beta_testing_worker_completed_and_progress_signals():
    worker = BetaTestingWorker(service=FakeBetaService(), config={"run_id": "worker"})
    progress = []
    completed = []
    worker.progress_signal.connect(progress.append)
    worker.completed_signal.connect(completed.append)

    worker.run()

    assert progress[0]["progress_percentage"] == 50
    assert completed[0].run.run_id == "worker"


def test_beta_testing_worker_cancelled_signal():
    worker = BetaTestingWorker(service=FakeBetaService(status="CANCELLED"))
    cancelled = []
    worker.cancelled_signal.connect(cancelled.append)

    worker.run()

    assert cancelled[0].run.status == "CANCELLED"


def test_beta_testing_worker_failed_signal():
    worker = BetaTestingWorker(service=FakeBetaService(fail=True))
    failed = []
    worker.failed_signal.connect(failed.append)

    worker.run()

    assert failed == ["beta exploded"]
