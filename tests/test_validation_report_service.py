import csv
import json

from services.algorithm_validation_service import (
    AlgorithmValidationReport,
    AlgorithmValidationReportService,
    metrics_for_outcomes,
)
from tests.algorithm_validation_test_utils import sample_outcome


def sample_report():
    outcomes = [sample_outcome()]
    return AlgorithmValidationReport(
        run_id="validation-report",
        started_at="2024-01-01T00:00:00+00:00",
        completed_at="2024-01-01T00:01:00+00:00",
        start_date="2024-01-01",
        end_date="2024-02-01",
        replay_frequency="weekly",
        signal_count=1,
        outcome_count=1,
        summary_metrics=metrics_for_outcomes(outcomes),
        warnings=["warning one"],
        errors=["error one"],
        outcomes=outcomes,
    )


def test_validation_report_service_exports_json_and_csv(tmp_path):
    service = AlgorithmValidationReportService()
    report = sample_report()

    json_result = service.export_json(report, tmp_path, "report")
    summary_result = service.export_summary_csv(report, tmp_path, "summary")
    issues_result = service.export_issue_csv(report, tmp_path, "issues")

    assert json_result["success"] is True
    assert summary_result["success"] is True
    assert issues_result["success"] is True

    with open(json_result["path"], encoding="utf-8") as handle:
        payload = json.load(handle)
    assert payload["run_id"] == "validation-report"

    with open(summary_result["path"], newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["signal_count"] == "1"

    with open(issues_result["path"], newline="", encoding="utf-8") as handle:
        issues = list(csv.DictReader(handle))
    assert {row["severity"] for row in issues} == {"warning", "error"}
