import csv
import json
from types import SimpleNamespace

from services.candidate_ranking_engine import RankedCandidate
from services.results_export_service import ResultsExportService


def candidate():
    return RankedCandidate(
        rank=1,
        ticker="AAPL",
        final_score=91.25,
        grade="A+",
        confidence_level="HIGH",
        setup_label="Elite Institutional Bounce",
        explanation=["Strong support", "Institutional sponsorship"],
        warnings=["Minor warning"],
        rejection_reasons=[],
        source={"run_id": "run-1", "created_at": "2026-07-03T10:00:00"},
    )


def run_metadata():
    return {
        "run_id": "run-1",
        "status": "COMPLETED",
        "started_at": "2026-07-03T10:00:00",
        "completed_at": "2026-07-03T10:01:00",
        "tickers_requested": 5,
        "tickers_processed": 5,
        "candidate_count": 1,
        "warnings": [],
        "errors": [],
    }


def test_results_export_service_csv_export(tmp_path):
    service = ResultsExportService()

    result = service.export_ranked_candidates_csv(
        [candidate()],
        tmp_path / "exports",
        "ranked",
    )

    path = tmp_path / "exports" / "ranked.csv"
    rows = list(csv.DictReader(path.open(encoding="utf-8")))

    assert result["success"] is True
    assert result["path"] == str(path)
    assert result["count"] == 1
    assert rows[0]["ticker"] == "AAPL"
    assert rows[0]["explanation"] == "Strong support; Institutional sponsorship"
    assert rows[0]["warnings"] == "Minor warning"
    assert rows[0]["run_id"] == "run-1"


def test_results_export_service_json_export(tmp_path):
    service = ResultsExportService()

    result = service.export_ranked_candidates_json(
        [candidate()],
        tmp_path,
        "ranked.json",
    )

    exported = json.loads((tmp_path / "ranked.json").read_text(encoding="utf-8"))

    assert result["success"] is True
    assert exported[0]["ticker"] == "AAPL"
    assert exported[0]["final_score"] == 91.25
    assert exported[0]["created_at"] == "2026-07-03T10:00:00"


def test_results_export_service_screening_run_metadata_json(tmp_path):
    service = ResultsExportService()

    result = service.export_screening_run_metadata_json(
        run_metadata(),
        tmp_path,
        "run-metadata",
    )

    exported = json.loads((tmp_path / "run-metadata.json").read_text(encoding="utf-8"))

    assert result["success"] is True
    assert exported["run_id"] == "run-1"
    assert exported["candidate_count"] == 1


def test_results_export_service_full_run_package_export(tmp_path):
    service = ResultsExportService()

    result = service.export_full_run_package(
        run_metadata(),
        [candidate()],
        tmp_path,
        "package",
    )

    exported = json.loads((tmp_path / "package.json").read_text(encoding="utf-8"))

    assert result["success"] is True
    assert result["count"] == 1
    assert exported["run"]["run_id"] == "run-1"
    assert exported["candidates"][0]["ticker"] == "AAPL"


def test_results_export_service_empty_candidates(tmp_path):
    service = ResultsExportService()

    result = service.export_ranked_candidates_csv([], tmp_path, "empty")

    path = tmp_path / "empty.csv"
    text = path.read_text(encoding="utf-8")

    assert result["success"] is True
    assert result["count"] == 0
    assert "ticker" in text
    assert len(list(csv.DictReader(path.open(encoding="utf-8")))) == 0


def test_results_export_service_filename_sanitization(tmp_path):
    service = ResultsExportService()

    result = service.export_ranked_candidates_json(
        [candidate()],
        tmp_path,
        "bad name:run/one?.json",
    )

    assert result["success"] is True
    assert result["path"].endswith("one.json")
    assert "/" not in result["path"].replace(str(tmp_path), "")


def test_results_export_service_invalid_output_directory():
    service = ResultsExportService()

    result = service.export_ranked_candidates_json([candidate()], "", "ranked")

    assert result["success"] is False
    assert "Output directory is required" in result["message"]


def test_results_export_service_accepts_dict_and_object_candidates(tmp_path):
    service = ResultsExportService()
    object_candidate = SimpleNamespace(
        rank=2,
        ticker="MSFT",
        final_score=82,
        grade="A",
        confidence_level="HIGH",
        setup_label="High-Quality Bounce",
        explanation=["Good setup"],
        warnings=[],
        rejection_reasons=[],
        run_id="run-object",
        created_at="2026-07-03T11:00:00",
    )

    service.export_ranked_candidates_json(
        [
            {
                "rank": 1,
                "ticker": "AAPL",
                "final_score": 91,
                "grade": "A+",
                "confidence_level": "HIGH",
                "setup_label": "Elite Institutional Bounce",
                "explanation": ["Strong"],
                "warnings": [],
                "rejection_reasons": [],
                "run_id": "run-dict",
                "created_at": "2026-07-03T10:00:00",
            },
            object_candidate,
        ],
        tmp_path,
        "mixed",
    )

    exported = json.loads((tmp_path / "mixed.json").read_text(encoding="utf-8"))

    assert [row["ticker"] for row in exported] == ["AAPL", "MSFT"]
    assert exported[1]["run_id"] == "run-object"
