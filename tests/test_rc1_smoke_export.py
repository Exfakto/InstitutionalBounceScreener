import csv

from controllers.results_export_controller import ResultsExportController
from services.candidate_ranking_engine import RankedCandidate
from services.results_export_service import ResultsExportService


class SmokeExportRepository:
    def fetch_latest_screening_run(self):
        return {"run_id": "rc1-smoke-export", "status": "COMPLETED"}

    def fetch_ranked_candidates(self, run_id):
        return [
            RankedCandidate(
                rank=1,
                ticker="AAPL",
                final_score=88.0,
                grade="A",
                confidence_level="HIGH",
                setup_label="High-Quality Bounce",
                explanation=["RC1 smoke export"],
            )
        ]


def test_rc1_smoke_export_workflow_completes_with_mocked_results(tmp_path):
    controller = ResultsExportController(
        SmokeExportRepository(),
        export_service=ResultsExportService(),
        output_dir=tmp_path,
    )

    result = controller.export_candidates_csv()

    assert result["success"] is True
    assert result["count"] == 1
    with open(result["path"], newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["ticker"] == "AAPL"
    assert rows[0]["grade"] == "A"
