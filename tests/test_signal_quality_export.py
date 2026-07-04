import csv
import json

from services.algorithm_validation_service import (
    AlgorithmValidationReportService,
    SignalQualityAnalysisService,
)
from tests.test_signal_quality_analysis_service import enriched_outcome


def test_signal_quality_recommendation_export_json_and_csv(tmp_path):
    report = SignalQualityAnalysisService().analyze(
        [enriched_outcome("A", -5, 62)],
        validation_run_id="validation-run",
    )
    service = AlgorithmValidationReportService()

    json_result = service.export_recommendations_json(report, tmp_path, "quality")
    csv_result = service.export_recommendations_csv(report, tmp_path, "quality")

    assert json_result["success"] is True
    assert csv_result["success"] is True
    assert csv_result["count"] == len(report.recommendations)

    with open(json_result["path"], encoding="utf-8") as handle:
        payload = json.load(handle)
    assert payload["validation_run_id"] == "validation-run"

    with open(csv_result["path"], newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["field"]
