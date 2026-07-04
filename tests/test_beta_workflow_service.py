from types import SimpleNamespace

from database.manager import DatabaseManager
from services.beta_testing_service import BetaWorkflowService


class ProviderDiagnostics:
    def run(self):
        return SimpleNamespace(selected_provider="local_csv", credential_status="Configured")


class Coverage:
    def report(self):
        return {
            "ticker_count": 2,
            "ohlcv_covered_count": 2,
            "missing_fundamentals": [],
            "missing_institutional": [],
            "warnings": [],
        }


class ScanRunner:
    def run_scan(self, **kwargs):
        return SimpleNamespace(
            processed=2,
            warnings=[],
            errors=[],
            details={
                "ranked_candidates": [
                    {"ticker": "AAPL", "rank": 1, "final_score": 90, "grade": "A", "setup_label": "Elite"}
                ]
            },
        )


def test_beta_workflow_runs_scan_review_pack_persistence_and_exports(tmp_path):
    db = DatabaseManager(tmp_path / "beta.db")
    progress = []
    service = BetaWorkflowService(
        repository=db,
        provider_diagnostics_service=ProviderDiagnostics(),
        coverage_service=Coverage(),
        scan_runner=ScanRunner(),
    )

    result = service.run_workflow(
        top_n=1,
        export_report=False,
        progress_callback=progress.append,
        run_id="beta-workflow",
    )

    assert result.run.status == "PASS"
    assert result.run.scanned_count == 2
    assert result.run.candidates_count == 1
    assert result.review_pack[0].ticker == "AAPL"
    assert db.fetch_beta_test_run("beta-workflow")["status"] == "PASS"
    assert progress[-1]["progress_percentage"] == 100


def test_beta_workflow_cancellation_returns_cancelled_run(tmp_path):
    db = DatabaseManager(tmp_path / "beta.db")
    service = BetaWorkflowService(
        repository=db,
        provider_diagnostics_service=ProviderDiagnostics(),
        coverage_service=Coverage(),
        scan_runner=ScanRunner(),
    )

    result = service.run_workflow(
        cancellation_callback=lambda: True,
        run_id="beta-cancel",
    )

    assert result.run.status == "CANCELLED"
    assert db.fetch_beta_test_run("beta-cancel")["status"] == "CANCELLED"


def test_beta_workflow_failed_scan_sets_fail_status(tmp_path):
    class FailingScan:
        def run_scan(self, **kwargs):
            raise RuntimeError("boom")

    service = BetaWorkflowService(
        repository=DatabaseManager(tmp_path / "beta.db"),
        provider_diagnostics_service=ProviderDiagnostics(),
        coverage_service=Coverage(),
        scan_runner=FailingScan(),
    )

    result = service.run_workflow(export_report=False)

    assert result.run.status == "FAIL"
    assert "Full market scan failed" in result.run.errors
