import csv
import json

from services.app_config_service import AppConfigService
from services.beta_report_export_service import BetaReportExportService as CalibrationBetaReportExportService
from services.beta_review_pack_service import BetaReviewPack
from services.beta_testing_service import (
    BetaReportExportService,
    BetaTestRun,
    BetaWorkflowResult,
    CandidateReviewItem,
    ManualReviewChecklistItem,
)
from services.model_calibration_recommendation_service import CalibrationRecommendationView
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


def test_beta_report_export_includes_calibration_recommendations(tmp_path):
    class RecommendationService:
        def get_recommendations(self, run_id=None):
            return [
                CalibrationRecommendationView(
                    title="Minimum Technical Score",
                    severity="MEDIUM",
                    recommended_action="70",
                    reason="Technical buckets underperformed",
                    related_metric="minimum_technical_score",
                    timestamp="2026-01-02T00:00:00Z",
                )
            ]

    service = CalibrationBetaReportExportService(
        AppConfigService(app_config(tmp_path)),
        calibration_recommendation_service=RecommendationService(),
    )
    workflow_result = result()

    exports = service.export_all(workflow_result, output_dir=tmp_path, basename="beta")

    with open(exports["summary_json"], encoding="utf-8") as handle:
        summary = json.load(handle)
    with open(exports["review_pack_json"], encoding="utf-8") as handle:
        review_pack = json.load(handle)

    assert summary["calibration_recommendations"][0]["title"] == "Minimum Technical Score"
    assert review_pack["calibration_recommendations"][0] == {
        "title": "Minimum Technical Score",
        "severity": "MEDIUM",
        "recommended_action": "70",
        "reason": "Technical buckets underperformed",
        "related_metric": "minimum_technical_score",
        "timestamp": "2026-01-02T00:00:00Z",
    }


def test_beta_report_export_handles_embedded_empty_calibration_recommendations(tmp_path):
    service = CalibrationBetaReportExportService(AppConfigService(app_config(tmp_path)))
    pack = BetaReviewPack(
        candidates=[CandidateReviewItem("AAPL", "A", 90, "Elite")],
        calibration_recommendations=[],
    )

    exported = service.export_review_pack_json(pack, tmp_path, "pack.json")

    with open(exported["path"], encoding="utf-8") as handle:
        payload = json.load(handle)
    assert payload["calibration_recommendations"] == []
    assert payload["candidates"][0]["ticker"] == "AAPL"


def test_beta_report_export_failure_handling_for_unwritable_destination(tmp_path):
    service = CalibrationBetaReportExportService(AppConfigService(app_config(tmp_path)))
    blocking_file = tmp_path / "not_a_directory"
    blocking_file.write_text("blocked", encoding="utf-8")

    try:
        service.export_run_summary_json(result(), output_dir=blocking_file)
    except OSError:
        pass
    else:
        raise AssertionError("Expected export failure to propagate for invalid output path")
