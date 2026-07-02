import json

from analysis.research_report import ResearchReportResult
from services.export_service import ExportService


def test_export_service_csv_export(tmp_path):
    service = ExportService()
    destination = tmp_path / "watchlist.csv"

    result = service.export_watchlist(
        [{"ticker": "AAPL", "status": "Watching"}],
        destination,
        "csv",
    )

    assert result["success"] is True
    assert result["path"] == str(destination)
    assert "ticker,status" in destination.read_text(encoding="utf-8")
    assert "AAPL,Watching" in destination.read_text(encoding="utf-8")


def test_export_service_json_export(tmp_path):
    service = ExportService()
    destination = tmp_path / "stats.json"

    result = service.export_portfolio_statistics(
        {"total_trades": 3, "win_rate": 66.7},
        destination,
        "json",
    )

    assert result["success"] is True
    assert json.loads(destination.read_text(encoding="utf-8"))["total_trades"] == 3


def test_export_service_invalid_path_fails_safely():
    service = ExportService()

    result = service.export_watchlist([], "", "csv")

    assert result["success"] is False
    assert "Destination path is required" in result["message"]


def test_export_service_overwrite_protection(tmp_path):
    service = ExportService()
    destination = tmp_path / "watchlist.csv"
    destination.write_text("existing", encoding="utf-8")

    result = service.export_watchlist(
        [{"ticker": "MSFT"}],
        destination,
        "csv",
    )

    assert result["success"] is False
    assert destination.read_text(encoding="utf-8") == "existing"


def test_export_service_allows_explicit_overwrite(tmp_path):
    service = ExportService()
    destination = tmp_path / "watchlist.csv"
    destination.write_text("existing", encoding="utf-8")

    result = service.export_watchlist(
        [{"ticker": "MSFT"}],
        destination,
        "csv",
        allow_overwrite=True,
    )

    assert result["success"] is True
    assert "MSFT" in destination.read_text(encoding="utf-8")


def test_export_service_empty_dataset(tmp_path):
    service = ExportService()
    destination = tmp_path / "empty.csv"

    result = service.export_trade_journal([], destination, "csv")

    assert result["success"] is True
    assert result["count"] == 0
    assert destination.read_text(encoding="utf-8") == ""


def test_export_service_research_summary_csv(tmp_path):
    service = ExportService()
    destination = tmp_path / "research.csv"

    result = service.export_research_summary(
        {"ticker": "NVDA", "summary": "Institutional setup."},
        destination,
        "csv",
    )

    assert result["success"] is True
    assert "ticker,summary" in destination.read_text(encoding="utf-8")


def test_export_service_unsupported_format(tmp_path):
    service = ExportService()

    result = service.export_strategy_analytics(
        {"total_trades": 1},
        tmp_path / "analytics.xlsx",
        "xlsx",
    )

    assert result["success"] is False
    assert "Unsupported export format" in result["message"]


def sample_report():
    return ResearchReportResult(
        title="AAPL Institutional Bounce Research Report",
        executive_summary="AAPL has a strong setup.\n\nPrimary risks remain defined.",
        setup_quality="Opportunity rating: Elite Bounce.",
        technical_analysis="Support: 91, a positive contributor.",
        fundamental_analysis="Revenue Growth: 12.5% - growth supports the setup.",
        institutional_analysis="Ownership: 72.5% - ownership sponsorship is strong.",
        trade_plan="Entry: Ideal Entry; Stop: Technical.",
        risk_summary="Warnings: Review liquidity before entry.",
        warnings=["Review liquidity before entry."],
        conclusion="AAPL conclusion: High Conviction.",
        confidence="Very High",
    )


def test_export_service_research_report_json(tmp_path):
    service = ExportService()
    destination = tmp_path / "reports" / "aapl.json"

    result = service.export_research_report(sample_report(), destination, "json")

    exported = json.loads(destination.read_text(encoding="utf-8"))
    assert result["success"] is True
    assert result["path"] == str(destination)
    assert exported["title"] == "AAPL Institutional Bounce Research Report"
    assert exported["warnings"] == ["Review liquidity before entry."]


def test_export_service_research_report_txt(tmp_path):
    service = ExportService()
    destination = tmp_path / "aapl.txt"

    result = service.export_research_report(sample_report(), destination, "txt")

    text = destination.read_text(encoding="utf-8")
    assert result["success"] is True
    assert "Executive Summary" in text
    assert "AAPL has a strong setup." in text
    assert "# " not in text


def test_export_service_research_report_markdown(tmp_path):
    service = ExportService()
    destination = tmp_path / "aapl"

    result = service.export_research_report(sample_report(), destination, "markdown")

    markdown_path = tmp_path / "aapl.md"
    text = markdown_path.read_text(encoding="utf-8")
    assert result["success"] is True
    assert result["path"] == str(markdown_path)
    assert text.startswith("# AAPL Institutional Bounce Research Report")
    assert "## Technical Assessment" in text
    assert "- Review liquidity before entry." in text


def test_export_service_research_report_overwrite_protection(tmp_path):
    service = ExportService()
    destination = tmp_path / "aapl.md"
    destination.write_text("existing", encoding="utf-8")

    result = service.export_research_report(
        sample_report(),
        destination,
        "markdown",
    )

    assert result["success"] is False
    assert destination.read_text(encoding="utf-8") == "existing"


def test_export_service_research_report_allows_overwrite(tmp_path):
    service = ExportService()
    destination = tmp_path / "aapl.txt"
    destination.write_text("existing", encoding="utf-8")

    result = service.export_research_report(
        sample_report(),
        destination,
        "txt",
        overwrite=True,
    )

    assert result["success"] is True
    assert "AAPL Institutional Bounce Research Report" in destination.read_text(
        encoding="utf-8"
    )


def test_export_service_research_report_invalid_path_fails_safely():
    service = ExportService()

    result = service.export_research_report(sample_report(), "", "json")

    assert result["success"] is False
    assert "Destination path is required" in result["message"]


def test_export_service_research_report_partial_report(tmp_path):
    service = ExportService()
    destination = tmp_path / "partial.md"

    result = service.export_research_report(
        {"title": "Partial Report", "confidence": "Low"},
        destination,
        "markdown",
    )

    text = destination.read_text(encoding="utf-8")
    assert result["success"] is True
    assert "# Partial Report" in text
    assert "## Confidence" in text
    assert "Revenue Growth" not in text
