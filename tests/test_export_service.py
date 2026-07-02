import json

from analysis.research_report import ResearchReportResult
from analysis.watchlist_intelligence import WatchlistIntelligenceResult
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


def sample_watchlist_intelligence():
    return WatchlistIntelligenceResult(
        total_items=3,
        ready_count=1,
        watching_count=1,
        rejected_count=1,
        high_conviction_count=1,
        average_opportunity_score=78.5,
        top_candidates=[
            {
                "ticker": "AAPL",
                "company_name": "Apple Inc.",
                "status": "Ready",
                "opportunity_score": 91.0,
            }
        ],
        weak_candidates=[
            {
                "ticker": "TSLA",
                "status": "Rejected",
                "opportunity_score": 42.0,
            }
        ],
        stale_items=[
            {
                "ticker": "MSFT",
                "status": "Watching",
                "updated_at": "2026-06-20",
            }
        ],
        warning_count=1,
        summary="Watchlist contains 3 item(s); 1 ready; 1 watching.",
        warnings=["TSLA: Support quality is weak."],
    )


def test_export_service_watchlist_intelligence_json(tmp_path):
    service = ExportService()
    destination = tmp_path / "intelligence.json"

    result = service.export_watchlist_intelligence(
        sample_watchlist_intelligence(),
        destination,
        "json",
    )

    exported = json.loads(destination.read_text(encoding="utf-8"))
    assert result["success"] is True
    assert exported["total_items"] == 3
    assert exported["ready_count"] == 1
    assert exported["top_candidates"][0]["ticker"] == "AAPL"
    assert exported["warnings"] == ["TSLA: Support quality is weak."]


def test_export_service_watchlist_intelligence_txt(tmp_path):
    service = ExportService()
    destination = tmp_path / "intelligence.txt"

    result = service.export_watchlist_intelligence(
        sample_watchlist_intelligence(),
        destination,
        "txt",
    )

    text = destination.read_text(encoding="utf-8")
    assert result["success"] is True
    assert text.startswith("Watchlist Intelligence")
    assert "Summary" in text
    assert "Total items: 3" in text
    assert "Top Candidates" in text
    assert "AAPL" in text
    assert "# " not in text


def test_export_service_watchlist_intelligence_markdown(tmp_path):
    service = ExportService()
    destination = tmp_path / "intelligence"

    result = service.export_watchlist_intelligence(
        sample_watchlist_intelligence(),
        destination,
        "markdown",
    )

    markdown_path = tmp_path / "intelligence.md"
    text = markdown_path.read_text(encoding="utf-8")
    assert result["success"] is True
    assert result["path"] == str(markdown_path)
    assert text.startswith("# Watchlist Intelligence")
    assert "## Metrics" in text
    assert "- **Average opportunity score:** 78.5" in text
    assert "## Stale Items" in text


def test_export_service_watchlist_intelligence_overwrite_protection(tmp_path):
    service = ExportService()
    destination = tmp_path / "intelligence.md"
    destination.write_text("existing", encoding="utf-8")

    result = service.export_watchlist_intelligence(
        sample_watchlist_intelligence(),
        destination,
        "markdown",
    )

    assert result["success"] is False
    assert destination.read_text(encoding="utf-8") == "existing"


def test_export_service_watchlist_intelligence_allows_overwrite(tmp_path):
    service = ExportService()
    destination = tmp_path / "intelligence.txt"
    destination.write_text("existing", encoding="utf-8")

    result = service.export_watchlist_intelligence(
        sample_watchlist_intelligence(),
        destination,
        "txt",
        overwrite=True,
    )

    assert result["success"] is True
    assert "Watchlist Intelligence" in destination.read_text(encoding="utf-8")


def test_export_service_watchlist_intelligence_invalid_destination():
    service = ExportService()

    result = service.export_watchlist_intelligence(
        sample_watchlist_intelligence(),
        "",
        "json",
    )

    assert result["success"] is False
    assert "Destination path is required" in result["message"]


def test_export_service_watchlist_intelligence_empty(tmp_path):
    service = ExportService()
    destination = tmp_path / "empty.md"
    intelligence = WatchlistIntelligenceResult(
        total_items=0,
        ready_count=0,
        watching_count=0,
        rejected_count=0,
        high_conviction_count=0,
        average_opportunity_score=None,
        summary="Watchlist is empty; no opportunity or health metrics are available.",
    )

    result = service.export_watchlist_intelligence(
        intelligence,
        destination,
        "markdown",
    )

    text = destination.read_text(encoding="utf-8")
    assert result["success"] is True
    assert "Watchlist is empty" in text
    assert "- **Average opportunity score:** --" in text
    assert "## Top Candidates" in text


def test_export_service_watchlist_intelligence_partial(tmp_path):
    service = ExportService()
    destination = tmp_path / "partial.txt"

    result = service.export_watchlist_intelligence(
        {"summary": "Partial watchlist intelligence.", "total_items": 1},
        destination,
        "txt",
    )

    text = destination.read_text(encoding="utf-8")
    assert result["success"] is True
    assert "Partial watchlist intelligence." in text
    assert "Total items: 1" in text
    assert "Ready count: --" in text


def test_export_service_watchlist_intelligence_no_provider_database_calls(
    tmp_path,
    monkeypatch,
):
    def fail_call(*args, **kwargs):
        raise AssertionError("provider/database call was not expected")

    monkeypatch.setattr("providers.provider_manager.ProviderManager", fail_call)
    monkeypatch.setattr("database.manager.DatabaseManager", fail_call)

    result = ExportService().export_watchlist_intelligence(
        sample_watchlist_intelligence(),
        tmp_path / "intelligence.json",
        "json",
    )

    assert result["success"] is True
