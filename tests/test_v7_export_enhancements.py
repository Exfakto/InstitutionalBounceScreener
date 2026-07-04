import csv
import json

from services.results_export_service import ResultsExportService


def test_v7_export_universe_and_coverage_reports(tmp_path):
    service = ResultsExportService()

    universe = service.export_universe_list_csv(
        [{"ticker": "AAPL", "exchange": "NASDAQ", "security_type": "Common Stock"}],
        tmp_path,
        "universe",
    )
    report = {
        "ticker_count": 2,
        "missing_ohlcv": ["MSFT"],
        "missing_fundamentals": [],
        "missing_institutional": ["MSFT"],
        "stale_data": [],
    }
    report_json = service.export_coverage_readiness_report_json(report, tmp_path, "coverage")
    report_csv = service.export_coverage_readiness_report_csv(report, tmp_path, "coverage")
    package = service.export_full_run_package({}, [], tmp_path, "package", coverage_metadata=report)

    assert universe["count"] == 1
    assert report_json["success"] is True
    assert report_csv["count"] == 2
    assert package["success"] is True

    with open(tmp_path / "coverage.json", encoding="utf-8") as handle:
        assert json.load(handle)["ticker_count"] == 2
    with open(tmp_path / "coverage.csv", newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert {row["category"] for row in rows} == {"missing_ohlcv", "missing_institutional"}
    assert "coverage_metadata" in (tmp_path / "package.json").read_text(encoding="utf-8")
