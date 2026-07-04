import csv
import json

from controllers.results_export_controller import ResultsExportController
from services.candidate_ranking_engine import RankedCandidate
from services.results_export_service import ResultsExportService


class ExportWorkflowRepository:
    def __init__(self):
        self.run = {
            "run_id": "e2e-export",
            "status": "COMPLETED",
            "started_at": "2026-07-04T10:00:00+00:00",
            "completed_at": "2026-07-04T10:01:00+00:00",
            "tickers_requested": 2,
            "tickers_processed": 2,
            "candidate_count": 1,
        }
        self.candidates = [
            RankedCandidate(
                rank=1,
                ticker="AAPL",
                final_score=92.0,
                grade="A+",
                confidence_level="HIGH",
                setup_label="Elite Institutional Bounce",
                explanation=["Strong support and institutional sponsorship"],
                warnings=[],
                rejection_reasons=[],
                source={"run_id": "e2e-export", "created_at": "2026-07-04T10:01:00+00:00"},
            )
        ]

    def fetch_latest_screening_run(self):
        return self.run

    def fetch_screening_run(self, run_id):
        return self.run if run_id == self.run["run_id"] else None

    def fetch_ranked_candidates(self, run_id):
        return list(self.candidates) if run_id == self.run["run_id"] else []


def test_end_to_end_export_workflow_generates_csv_json_and_package(tmp_path):
    repository = ExportWorkflowRepository()
    controller = ResultsExportController(
        repository,
        export_service=ResultsExportService(),
        output_dir=tmp_path,
    )

    csv_result = controller.export_candidates_csv()
    json_result = controller.export_candidates_json("e2e-export")
    package_result = controller.export_full_run_package_json("e2e-export")

    assert csv_result["success"] is True
    assert json_result["success"] is True
    assert package_result["success"] is True

    with open(csv_result["path"], newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["ticker"] == "AAPL"
    assert rows[0]["grade"] == "A+"

    candidates_payload = json.loads(open(json_result["path"], encoding="utf-8").read())
    assert candidates_payload[0]["ticker"] == "AAPL"
    assert candidates_payload[0]["setup_label"] == "Elite Institutional Bounce"

    package_payload = json.loads(open(package_result["path"], encoding="utf-8").read())
    assert package_payload["run"]["run_id"] == "e2e-export"
    assert package_payload["candidates"][0]["ticker"] == "AAPL"
    assert package_result["count"] == 1
