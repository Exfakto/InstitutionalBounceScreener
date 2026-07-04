import csv
import json

from services.app_config_service import AppConfigService
from services.beta_testing_service import (
    BetaReportExportService,
    BetaTestRun,
    BetaWorkflowResult,
    CandidateReviewItem,
    ManualReviewChecklistItem,
)
from tests.release_test_utils import app_config


def result():
    run = BetaTestRun(
        run_id="beta-export",
        started_at="2026-01-01T00:00:00+00:00",
        completed_at="2026-01-01T00:01:00+00:00",
        status="PASS",
        candidates_count=1,
    )
    review = [CandidateReviewItem("AAPL", "A", 90, "Elite", warnings=["note"])]
    checklist = [ManualReviewChecklistItem("AAPL")]
    return BetaWorkflowResult(run=run, review_pack=review, checklist=checklist)


def test_beta_report_export_summary_review_pack_and_checklist(tmp_path):
    service = BetaReportExportService(AppConfigService(app_config(tmp_path)))
    workflow_result = result()

    exports = service.export_all(workflow_result, output_dir=tmp_path, basename="beta")

    assert set(exports) == {"summary_json", "review_pack_json", "review_pack_csv", "checklist_csv"}
    with open(exports["summary_json"], encoding="utf-8") as handle:
        assert json.load(handle)["run"]["run_id"] == "beta-export"
    with open(exports["review_pack_csv"], newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["ticker"] == "AAPL"
    with open(exports["checklist_csv"], newline="", encoding="utf-8") as handle:
        checklist_rows = list(csv.DictReader(handle))
    assert "risk_reward_acceptable" in checklist_rows[0]


def test_beta_report_export_individual_methods_handle_empty_payloads(tmp_path):
    service = BetaReportExportService(AppConfigService(app_config(tmp_path)))

    review_json = service.export_review_pack_json([], tmp_path, "empty_pack")
    review_csv = service.export_review_pack_csv([], tmp_path, "empty_pack")
    checklist_csv = service.export_manual_checklist_csv([], tmp_path, "empty_checklist")

    assert review_json["count"] == 0
    assert review_csv["count"] == 0
    assert checklist_csv["count"] == 0
    with open(review_csv["path"], newline="", encoding="utf-8") as handle:
        assert list(csv.DictReader(handle)) == []
