import json

import pytest

from analysis.research_report import ResearchReportGenerator
from services.export_service import ExportService


def sample_candidate_data():
    return {
        "ticker": "AAPL",
        "company_name": "Apple Inc.",
        "overall_score": 88.5,
        "quality_score": 90.0,
        "technical_score": 84.0,
        "institutional_score": 76.0,
        "institutional_bounce_score": 88.5,
        "relative_strength_score": 82.0,
        "support_score": 91.0,
        "bounce_score": 80.0,
        "volume_score": 78.0,
        "trend_score": 76.0,
        "earnings_risk_score": 20.0,
        "risk_score": 74.0,
        "institutional_momentum_score": 80.0,
        "institutional_ownership_pct": 72.5,
        "net_institutional_buying": 250000000,
        "risk_reward": 2.4,
        "entry_zone": {"entry_label": "Ideal Entry", "entry_score": 91},
        "stop_loss": {"recommended_stop": 94.0, "stop_type": "Technical"},
        "target_projection": {"target_1": 112.0, "confidence": "High"},
        "position_size": {"shares": 150},
        "revenue_growth": 12.5,
        "eps_growth": 10.2,
        "roe": 24.7,
        "gross_margin": 46.2,
        "free_cash_flow": 95000000000,
        "debt_to_equity": 1.2,
        "current_ratio": 0.92,
        "market_cap": 3000000000000,
        "opportunity_rating": {
            "rating_score": 91.0,
            "rating_label": "Elite Bounce",
        },
        "institutional_checklist": {
            "overall_percentage": 90.0,
            "overall_label": "Excellent",
        },
        "warnings": ["Review liquidity before entry."],
    }


def generated_report():
    return ResearchReportGenerator().generate(sample_candidate_data())


@pytest.mark.parametrize(
    ("export_format", "filename", "expected_heading"),
    [
        ("json", "aapl_report.json", None),
        ("txt", "aapl_report.txt", "Executive Summary"),
        ("markdown", "aapl_report.md", "## Executive Summary"),
    ],
)
def test_research_report_generation_and_export_workflow(
    tmp_path,
    export_format,
    filename,
    expected_heading,
):
    report = generated_report()
    destination = tmp_path / filename

    result = ExportService().export_research_report(
        report,
        destination,
        export_format,
    )

    assert result["success"] is True
    assert destination.exists()

    exported = destination.read_text(encoding="utf-8")
    assert "AAPL" in exported
    assert report.conclusion in exported
    assert report.confidence in exported

    if export_format == "json":
        payload = json.loads(exported)
        assert payload["title"] == report.title
        assert payload["executive_summary"] == report.executive_summary
        assert payload["conclusion"] == report.conclusion
        assert payload["confidence"] == report.confidence
    else:
        assert report.executive_summary in exported
        assert expected_heading in exported


def test_research_report_export_workflow_overwrite_protection(tmp_path):
    report = generated_report()
    destination = tmp_path / "aapl_report.json"

    first = ExportService().export_research_report(report, destination, "json")
    second = ExportService().export_research_report(report, destination, "json")

    assert first["success"] is True
    assert second["success"] is False
    assert "already exists" in second["message"]


def test_partial_research_report_exports_safely(tmp_path):
    partial_report = {
        "title": "MSFT Institutional Bounce Research Report",
        "executive_summary": "MSFT has limited available data.",
        "conclusion": "MSFT conclusion: Watch List.",
        "confidence": "Low",
    }
    destination = tmp_path / "partial.md"

    result = ExportService().export_research_report(
        partial_report,
        destination,
        "markdown",
    )

    exported = destination.read_text(encoding="utf-8")
    assert result["success"] is True
    assert destination.exists()
    assert "MSFT" in exported
    assert partial_report["executive_summary"] in exported
    assert partial_report["conclusion"] in exported
    assert "Low" in exported
    assert "Revenue Growth" not in exported


def test_research_report_export_workflow_requires_no_provider_or_database_calls(
    tmp_path,
    monkeypatch,
):
    def fail_call(*args, **kwargs):
        raise AssertionError("provider/database call was not expected")

    monkeypatch.setattr("providers.provider_manager.ProviderManager", fail_call)
    monkeypatch.setattr("database.manager.DatabaseManager", fail_call)

    report = generated_report()
    destination = tmp_path / "aapl_report.txt"
    result = ExportService().export_research_report(report, destination, "txt")

    assert result["success"] is True
    assert destination.exists()
