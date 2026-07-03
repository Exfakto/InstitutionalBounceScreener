from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from PySide6.QtWidgets import QApplication, QLabel

from analysis.candidate_score import CandidateScore
from analysis.institutional_checklist import InstitutionalChecklistEvaluator
from analysis.opportunity_rating import OpportunityRatingCalculator
from analysis.research_report import ResearchReportGenerator
from analysis.score_result import ScoreResult
from analysis.trade_thesis import TradeThesisGenerator
from ui.widgets.research_preview import ResearchPreview


@pytest.fixture(scope="module")
def app():
    application = QApplication.instance()

    if application is None:
        application = QApplication([])

    return application


def checklist_for(metrics):
    return InstitutionalChecklistEvaluator().evaluate(metrics)


def opportunity_for(metrics):
    return OpportunityRatingCalculator().calculate(metrics)


def thesis_for(metrics):
    return TradeThesisGenerator().generate(metrics)


def report_for(metrics):
    return ResearchReportGenerator().generate(metrics)


def checklist_metrics():
    return {
        "institutional_bounce_score": 88.5,
        "opportunity_rating_score": 84.0,
        "institutional_score": 72.0,
        "institutional_momentum_score": 80.0,
        "relative_strength_score": 82.0,
        "trend_score": 76.0,
        "support_score": 91.0,
        "bounce_score": 76.0,
        "volume_score": 78.0,
        "earnings_risk_score": 20.0,
        "risk_score": 74.0,
        "distance_to_support_pct": 2.0,
        "bounce_success_rate": 75.0,
    }


def make_candidate(
    overall=88.5,
    scores=None,
    components=None,
    warnings=None,
    opportunity=None,
    checklist=None,
    thesis=None,
    report=None,
    fundamentals=None,
):
    metrics = checklist_metrics()
    metrics["ticker"] = "AAPL"

    if opportunity is False:
        opportunity = None
    elif opportunity is None:
        opportunity = opportunity_for(metrics)

    if opportunity is not None:
        metrics["opportunity_rating"] = opportunity
        metrics["opportunity_rating_score"] = opportunity.rating_score

    if checklist is False:
        checklist = None
    elif checklist is None:
        checklist = checklist_for(metrics)

    if checklist is not None:
        metrics["institutional_checklist"] = checklist

    if thesis is False:
        thesis = None
    elif thesis is None:
        thesis = thesis_for(metrics)

    if thesis is not None:
        metrics["trade_thesis"] = thesis

    if report is None:
        report = None

    return CandidateScore(
        ticker="AAPL",
        composite_score=ScoreResult("composite_score", overall),
        scores=scores
        if scores is not None
        else [
            ScoreResult("quality_score", 90.0),
            ScoreResult(
                "institutional_score",
                72.0,
                details={"warnings": ["Institutional data is stale"]},
            ),
            ScoreResult("technical_score", 84.0),
            ScoreResult("support_score", 91.0),
            ScoreResult("bounce_score", 76.0),
        ],
        composite_intelligence_component_scores=components or {},
        opportunity_rating=opportunity,
        institutional_checklist=checklist,
        trade_thesis=thesis,
        research_report=report,
        metrics=fundamentals or {},
        warnings=warnings or [],
        timestamp=datetime(2026, 6, 30, tzinfo=timezone.utc),
    )


def test_research_preview_empty_state(app):
    preview = ResearchPreview()

    assert preview.empty_state_label.text() == "Select a candidate to begin research."
    assert preview.empty_state_label.isHidden() is False
    assert preview.dashboard_frame.isHidden() is True
    assert preview.warning_label.text() == "No warnings"
    assert preview.thesis_title_label.text() == "Trade thesis unavailable."
    assert preview.thesis_label.text() == "No trade thesis available."
    assert preview.report_labels["title"].text() == "Research report unavailable."


def test_research_preview_clear_resets_every_section(app):
    preview = ResearchPreview()
    preview.set_candidate(make_candidate())
    preview.set_trade_thesis("Buy near support after confirmation.")

    preview.clear()

    assert preview.empty_state_label.isHidden() is False
    assert preview.dashboard_frame.isHidden() is True
    assert preview.ticker_label.text() == ""
    assert preview.signal_label.text() == ""
    assert preview.summary_labels["overall"].text() == "-"
    assert preview.summary_labels["opportunity"].text() == "-"
    assert preview.summary_labels["checklist"].text() == "-"
    assert preview.warning_label.text() == "No warnings"
    assert preview.thesis_title_label.text() == "Trade thesis unavailable."
    assert preview.thesis_label.text() == "No trade thesis available."
    assert preview.report_labels["title"].text() == "Research report unavailable."
    assert preview.report_labels["executive_summary"].text() == "--"
    assert preview.letter_grade_label.text() == "--"
    assert preview.confidence_label.text() == "--"
    assert preview.decision_label.text() == "Decision unavailable."
    assert preview.decision_label.property("decision") == "missing"
    assert all(label.text() == "--" for label in preview.technical_labels.values())
    assert all(label.text() == "--" for label in preview.institutional_labels.values())
    assert all(label.text() == "--" for label in preview.risk_labels.values())
    assert all(
        label.text() == "⚠ Warning"
        for label in preview.checklist_status_labels.values()
    )


def test_research_preview_clear_resets_fundamentals(app):
    preview = ResearchPreview()
    preview.set_candidate(
        make_candidate(
            fundamentals={
                "revenue_growth_ttm": 12.5,
                "market_cap": 3000000000000,
            }
        )
    )

    preview.clear()

    assert preview.fundamentals_unavailable_label.isHidden() is False
    assert all(label.text() == "--" for label in preview.fundamental_labels.values())


def test_research_preview_displays_score_summary(app):
    preview = ResearchPreview()

    preview.set_candidate(make_candidate())

    assert preview.group.title() == "Research Preview 2.0"
    assert preview.empty_state_label.isHidden() is True
    assert preview.dashboard_frame.isHidden() is False
    assert preview.ticker_label.text() == "AAPL"
    assert preview.signal_label.text().endswith("High Probability")
    assert preview.overall_score_label.text() == "88.5"
    assert preview.summary_labels["overall"].text() == "88.5"
    assert preview.summary_labels["opportunity"].text().endswith("High Probability")
    assert preview.summary_labels["checklist"].text() == "100% Exceptional"
    assert preview.score_labels["quality_score"].text() == "90.0"
    assert preview.score_labels["institutional_score"].text() == "72.0"
    assert preview.score_labels["technical_score"].text() == "84.0"
    assert preview.score_labels["support_score"].text() == "91.0"
    assert preview.score_labels["bounce_score"].text() == "76.0"
    assert preview.letter_grade_label.text() == "B"
    assert preview.confidence_label.text()


def test_research_preview_displays_opportunity_workspace_sections(app):
    preview = ResearchPreview()

    preview.set_candidate(
        make_candidate(
            fundamentals={
                "relative_strength_score": 82.0,
                "bounce_success_rate": 75.0,
                "volume_score": 78.0,
                "trend_score": 76.0,
                "institutional_ownership_pct": 72.5,
                "net_institutional_buying": 250000000,
                "institutional_ownership_change_qoq": 1.3,
                "insider_buying_flag": 1,
                "entry": 100.0,
                "stop": 94.0,
                "target_1": 112.0,
                "atr": 3.2,
                "risk_reward": 2.0,
                "position_size": 150,
            }
        )
    )

    assert preview.technical_labels["support_strength"].text() == "91.0"
    assert preview.technical_labels["bounce_probability"].text() == "75.0%"
    assert preview.technical_labels["relative_strength"].text() == "82.0"
    assert preview.technical_labels["volume_intelligence"].text() == "78.0"
    assert preview.technical_labels["trend"].text() == "76.0"
    assert preview.institutional_labels["institutional_ownership"].text() == "72.5%"
    assert preview.institutional_labels["recent_buying"].text() == "$250.00M"
    assert preview.institutional_labels["thirteen_f_trend"].text() == "1.3"
    assert preview.institutional_labels["insider_activity"].text() == "Buying"
    assert preview.risk_labels["entry"].text() == "$100.00"
    assert preview.risk_labels["stop"].text() == "$94.00"
    assert preview.risk_labels["target"].text() == "$112.00"
    assert preview.risk_labels["atr"].text() == "$3.20"
    assert preview.risk_labels["risk_reward"].text() == "2.00:1"
    assert preview.risk_labels["position_size"].text() == "150.0"


def test_research_preview_displays_decision_badge(app):
    preview = ResearchPreview()

    preview.set_candidate(make_candidate())

    assert preview.decision_label.text() == "High Conviction"
    assert preview.decision_label.property("decision") == "green"
    assert "#41B883" in preview.decision_label.styleSheet()


def test_research_preview_displays_watch_decision(app):
    preview = ResearchPreview()

    preview.set_candidate(
        make_candidate(
            overall=72.0,
            opportunity=False,
            checklist=False,
            thesis=False,
        )
    )

    assert preview.decision_label.text() == "Watch"
    assert preview.decision_label.property("decision") == "yellow"


def test_research_preview_displays_avoid_decision(app):
    preview = ResearchPreview()

    preview.set_candidate(
        make_candidate(
            overall=50.0,
            opportunity=False,
            checklist=False,
            thesis=False,
        )
    )

    assert preview.decision_label.text() == "Avoid"
    assert preview.decision_label.property("decision") == "red"


def test_research_preview_displays_populated_fundamentals(app):
    preview = ResearchPreview()

    preview.set_candidate(
        make_candidate(
            fundamentals={
                "revenue_growth_ttm": 12.5,
                "eps_growth_ttm": 10.25,
                "roe": 24.7,
                "gross_margin": 46.2,
                "free_cash_flow": 95000000000,
                "debt_to_equity": 1.2,
                "current_ratio": 0.92,
                "market_cap": 3000000000000,
            }
        )
    )

    assert preview.fundamentals_unavailable_label.isHidden() is True
    assert preview.fundamental_labels["revenue_growth_ttm"].text() == "12.5%"
    assert preview.fundamental_labels["eps_growth_ttm"].text() == "10.2%"
    assert preview.fundamental_labels["roe"].text() == "24.7%"
    assert preview.fundamental_labels["gross_margin"].text() == "46.2%"
    assert preview.fundamental_labels["free_cash_flow"].text() == "$95.00B"
    assert preview.fundamental_labels["debt_to_equity"].text() == "1.20"
    assert preview.fundamental_labels["current_ratio"].text() == "0.92"
    assert preview.fundamental_labels["market_cap"].text() == "$3.00T"


def test_research_preview_displays_partial_fundamentals(app):
    preview = ResearchPreview()

    preview.set_candidate(
        make_candidate(
            fundamentals={
                "revenue_growth": 8.0,
                "market_cap": 2500000000,
            }
        )
    )

    assert preview.fundamentals_unavailable_label.isHidden() is True
    assert preview.fundamental_labels["revenue_growth_ttm"].text() == "8.0%"
    assert preview.fundamental_labels["eps_growth_ttm"].text() == "--"
    assert preview.fundamental_labels["market_cap"].text() == "$2.50B"


def test_research_preview_displays_missing_fundamentals(app):
    preview = ResearchPreview()

    preview.set_candidate(make_candidate())

    assert preview.fundamentals_unavailable_label.text() == "Fundamentals unavailable."
    assert preview.fundamentals_unavailable_label.isHidden() is False
    assert all(label.text() == "--" for label in preview.fundamental_labels.values())


def test_research_preview_displays_gen2_overall_when_available(app):
    preview = ResearchPreview()
    candidate = CandidateScore(
        ticker="AAPL",
        composite_score=ScoreResult("composite_score", 40.0),
        scores=make_candidate().scores,
        institutional_bounce_score=91.0,
        opportunity_rating=opportunity_for(checklist_metrics()),
        institutional_checklist=checklist_for(checklist_metrics()),
        trade_thesis=thesis_for(checklist_metrics()),
        warnings=["Missing components reduced confidence"],
        timestamp=datetime(2026, 6, 30, tzinfo=timezone.utc),
    )

    preview.set_candidate(candidate)

    assert preview.overall_score_label.text() == "91.0"
    assert "Missing components reduced confidence" in preview.warning_label.text()


@pytest.mark.parametrize(
    ("overall", "signal"),
    [
        (90.0, "STRONG BUY"),
        (80.0, "BUY"),
        (70.0, "WATCH"),
        (69.9, "AVOID"),
    ],
)
def test_research_preview_signal_label_compatibility(app, overall, signal):
    assert ResearchPreview.signal_label_for_score(overall) == signal


def test_research_preview_warning_updates(app):
    preview = ResearchPreview()

    preview.set_candidate(make_candidate())

    assert "Institutional data is stale" in preview.warning_label.text()


def test_research_preview_summarizes_missing_metric_warnings(app):
    preview = ResearchPreview()
    warnings = [
        "Missing revenue_growth_ttm",
        "Missing eps_growth_ttm",
        "Missing roe",
        "Missing gross_margin",
    ]
    scores = [
        ScoreResult("quality_score", 50.0, details={"warnings": warnings}),
    ]

    preview.set_candidate(make_candidate(scores=scores))

    assert "missing metrics" in preview.warning_label.text()
    assert "Missing revenue_growth_ttm" in preview.warning_label.text()


def test_research_preview_displays_opportunity_rating(app):
    preview = ResearchPreview()

    preview.set_candidate(make_candidate())

    assert "★★★★" in preview.signal_label.text()
    assert "High Probability" in preview.signal_label.text()
    assert preview.summary_labels["opportunity"].text().endswith("High Probability")


def test_research_preview_displays_live_checklist(app):
    preview = ResearchPreview()

    preview.set_candidate(make_candidate())

    assert preview.checklist_unavailable_label.isHidden() is True
    assert preview.checklist_status_labels["near_support"].text() == "✓ Pass"
    assert preview.checklist_status_labels["relative_strength"].text() == "✓ Pass"
    assert preview.checklist_status_labels["trend"].text() == "✓ Pass"
    assert preview.checklist_status_labels["atr_risk"].text() == "✓ Pass"
    assert preview.checklist_name_labels["near_support"].text() == "Near Support"


def test_research_preview_displays_mixed_checklist(app):
    preview = ResearchPreview()
    metrics = checklist_metrics()
    metrics.update(
        {
            "trend_score": 45.0,
            "volume_score": 65.0,
            "earnings_risk_score": 50.0,
            "risk_score": 35.0,
        }
    )

    preview.set_candidate(make_candidate(checklist=checklist_for(metrics)))

    assert preview.checklist_status_labels["trend"].text() == "✗ Fail"
    assert preview.checklist_status_labels["volume"].text() == "⚠ Warning"
    assert preview.checklist_status_labels["earnings_window"].text() == "⚠ Warning"
    assert preview.checklist_status_labels["atr_risk"].text() == "✗ Fail"


def test_research_preview_displays_unavailable_checklist(app):
    preview = ResearchPreview()

    preview.set_candidate(make_candidate(checklist=False))

    assert preview.summary_labels["checklist"].text() == "Checklist unavailable."
    assert preview.checklist_unavailable_label.text() == "Checklist unavailable."
    assert preview.checklist_unavailable_label.isHidden() is False


def test_research_preview_displays_thesis(app):
    preview = ResearchPreview()

    preview.set_candidate(make_candidate())

    assert preview.thesis_title_label.text().startswith("AAPL")
    assert "validated institutional support zone" in preview.thesis_label.text()
    assert preview.strengths_label.text().startswith("Strengths:")
    assert preview.risks_label.text().startswith("Risks:")


def test_research_preview_displays_unavailable_thesis(app):
    preview = ResearchPreview()

    preview.set_candidate(make_candidate(thesis=False))

    assert preview.thesis_title_label.text() == "Trade thesis unavailable."
    assert preview.thesis_label.text() == "No trade thesis available."


def test_research_preview_displays_research_report(app):
    preview = ResearchPreview()
    metrics = checklist_metrics()
    metrics["ticker"] = "AAPL"
    opportunity = opportunity_for(metrics)
    metrics["opportunity_rating"] = opportunity
    metrics["opportunity_rating_score"] = opportunity.rating_score
    checklist = checklist_for(metrics)
    metrics["institutional_checklist"] = checklist
    thesis = thesis_for(metrics)
    metrics["trade_thesis"] = thesis
    metrics["warnings"] = ["Review liquidity before entry."]
    report = report_for(metrics)

    preview.set_candidate(
        make_candidate(
            opportunity=opportunity,
            checklist=checklist,
            thesis=thesis,
            report=report,
            warnings=["Review liquidity before entry."],
        )
    )

    assert preview.report_labels["title"].text() == report.title
    assert preview.report_labels["executive_summary"].text() == report.executive_summary
    assert preview.report_labels["setup_quality"].text() == report.setup_quality
    assert preview.report_labels["technical_analysis"].text() == report.technical_analysis
    assert preview.report_labels["fundamental_analysis"].text() == report.fundamental_analysis
    assert preview.report_labels["institutional_analysis"].text() == report.institutional_analysis
    assert preview.report_labels["trade_plan"].text() == report.trade_plan
    assert preview.report_labels["risk_summary"].text() == report.risk_summary
    assert preview.report_labels["conclusion"].text() == report.conclusion
    assert preview.report_labels["confidence"].text() == report.confidence
    assert "Review liquidity before entry." in preview.warning_label.text()


def test_research_preview_displays_missing_report_state(app):
    preview = ResearchPreview()

    preview.set_candidate(make_candidate())

    assert preview.report_labels["title"].text() == "Research report unavailable."
    assert preview.report_labels["executive_summary"].text() == "--"


def test_research_preview_displays_partial_report_safely(app):
    preview = ResearchPreview()
    partial_report = {
        "title": "AAPL Research Report",
        "executive_summary": "AAPL has partial report data.",
        "confidence": "Moderate",
        "warnings": ["Report warning."],
    }

    preview.set_candidate(make_candidate(report=partial_report))

    assert preview.report_labels["title"].text() == "AAPL Research Report"
    assert preview.report_labels["executive_summary"].text() == "AAPL has partial report data."
    assert preview.report_labels["setup_quality"].text() == "--"
    assert preview.report_labels["confidence"].text() == "Moderate"
    assert preview.report_labels["warnings"].text() == "Report warning."


def test_research_preview_repeated_updates_do_not_duplicate_widgets(app):
    preview = ResearchPreview()
    initial_label_count = len(preview.findChildren(QLabel))
    initial_checklist_rows = len(preview.checklist_rows)
    initial_summary_labels = len(preview.summary_labels)
    initial_technical_labels = len(preview.technical_labels)
    initial_institutional_labels = len(preview.institutional_labels)
    initial_risk_labels = len(preview.risk_labels)
    initial_report_labels = len(preview.report_labels)

    preview.set_candidate(make_candidate(overall=88.5))
    preview.set_candidate(
        make_candidate(
            overall=72.0,
            scores=[],
            report={"title": "AAPL Research Report"},
        )
    )
    preview.set_candidate(None)

    assert len(preview.checklist_rows) == initial_checklist_rows
    assert len(preview.summary_labels) == initial_summary_labels
    assert len(preview.technical_labels) == initial_technical_labels
    assert len(preview.institutional_labels) == initial_institutional_labels
    assert len(preview.risk_labels) == initial_risk_labels
    assert len(preview.report_labels) == initial_report_labels
    assert len(preview.findChildren(QLabel)) == initial_label_count
    assert preview.empty_state_label.isHidden() is False


def test_research_preview_returns_trade_card_from_candidate_object(app):
    trade_card = {"ticker": "AAPL", "entry": 100.0}
    candidate = SimpleNamespace(trade_card=trade_card)

    assert ResearchPreview.trade_card_for_candidate(candidate) == trade_card


def test_research_preview_returns_trade_card_from_candidate_dict(app):
    trade_card = {"ticker": "MSFT", "entry": 410.0}

    assert ResearchPreview.trade_card_for_candidate({"trade_card": trade_card}) == trade_card
    assert ResearchPreview.trade_card_for_candidate({}) is None
    assert ResearchPreview.trade_card_for_candidate(None) is None


def test_research_preview_handles_missing_component_scores(app):
    preview = ResearchPreview()

    preview.set_candidate(
        make_candidate(
            overall=50.0,
            scores=[],
            opportunity=False,
            checklist=False,
            thesis=False,
        )
    )

    assert preview.ticker_label.text() == "AAPL"
    assert preview.signal_label.text() == "Opportunity rating unavailable."
    assert preview.overall_score_label.text() == "50.0"
    assert preview.score_labels["quality_score"].text() == "-"
    assert preview.score_labels["institutional_score"].text() == "-"
    assert preview.score_labels["technical_score"].text() == "-"
    assert preview.score_labels["support_score"].text() == "-"
    assert preview.score_labels["bounce_score"].text() == "-"
    assert all(label.text() == "--" for label in preview.technical_labels.values())
    assert all(label.text() == "--" for label in preview.institutional_labels.values())
    assert all(label.text() == "--" for label in preview.risk_labels.values())
    assert preview.warning_label.text() == "No warnings"


def test_research_preview_handles_candidate_without_opportunity_rating(app):
    preview = ResearchPreview()
    candidate = SimpleNamespace(
        ticker="MSFT",
        company_name="Microsoft Corporation",
        metrics={"market_cap": 3200000000000},
        score_map={},
        scores=[],
        warnings=[],
    )

    preview.set_candidate(candidate)

    assert preview.ticker_label.text() == "MSFT"
    assert preview.signal_label.text() == "Opportunity rating unavailable."
    assert preview.summary_labels["overall"].text() == "-"
    assert preview.summary_labels["opportunity"].text() == "Opportunity rating unavailable."
    assert preview.decision_label.text() == "Decision unavailable."
    assert preview.fundamental_labels["market_cap"].text() == "$3.20T"
