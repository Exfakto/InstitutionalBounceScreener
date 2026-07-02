from analysis.candidate_score import CandidateScore
from analysis.institutional_checklist import InstitutionalChecklistEvaluator
from analysis.opportunity_rating import OpportunityRatingCalculator
from analysis.research_report import ResearchReportGenerator, ResearchReportResult
from analysis.score_result import ScoreResult
from analysis.trade_thesis import TradeThesisGenerator


def full_metrics():
    metrics = {
        "ticker": "AAPL",
        "company_name": "Apple Inc.",
        "overall_score": 88.5,
        "quality_score": 90.0,
        "technical_score": 84.0,
        "institutional_score": 76.0,
        "institutional_bounce_score": 88.5,
        "composite_intelligence_score": 88.5,
        "relative_strength_score": 82.0,
        "support_score": 91.0,
        "bounce_score": 80.0,
        "volume_score": 78.0,
        "trend_score": 76.0,
        "earnings_risk_score": 20.0,
        "risk_score": 74.0,
        "distance_to_support_pct": 2.0,
        "bounce_success_rate": 75.0,
        "average_bounce_pct": 8.5,
        "institutional_momentum_score": 80.0,
        "institutional_ownership_pct": 72.5,
        "institutional_ownership_change_qoq": 1.3,
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
        "warnings": ["Review liquidity before entry."],
    }
    opportunity = OpportunityRatingCalculator().calculate(metrics)
    metrics["opportunity_rating"] = opportunity
    metrics["opportunity_rating_score"] = opportunity.rating_score
    checklist = InstitutionalChecklistEvaluator().evaluate(metrics)
    metrics["institutional_checklist"] = checklist
    metrics["trade_thesis"] = TradeThesisGenerator().generate(metrics)
    return metrics


def test_fully_populated_candidate_report():
    report = ResearchReportGenerator().generate(full_metrics())

    assert isinstance(report, ResearchReportResult)
    assert report.title == "AAPL Institutional Bounce Research Report - Apple Inc."
    assert "AAPL (Apple Inc.)" in report.executive_summary
    assert "Elite Bounce" in report.executive_summary
    assert len(report.executive_summary.split("\n\n")) == 4
    assert "quality score 90" in report.setup_quality
    assert "Support: 91, a positive contributor" in report.technical_analysis
    assert "Bounce Quality: 80, a positive contributor" in report.technical_analysis
    assert "Trend: 76, a constructive" in report.technical_analysis
    assert "Relative Strength: 82, a positive contributor" in report.technical_analysis
    assert "Volume: 78, a constructive" in report.technical_analysis
    assert "Revenue Growth: 12.5%" in report.fundamental_analysis
    assert "EPS Growth: 10.2%" in report.fundamental_analysis
    assert "ROE: 24.7%" in report.fundamental_analysis
    assert "Margins: 46.2%" in report.fundamental_analysis
    assert "Cash Flow: $95.00B" in report.fundamental_analysis
    assert "Debt: 1.2" in report.fundamental_analysis
    assert "Current Ratio: 0.9" in report.fundamental_analysis
    assert "Market Cap: $3.00T" in report.fundamental_analysis
    assert "Institutional Score: 76" in report.institutional_analysis
    assert "Ownership: 72.5%" in report.institutional_analysis
    assert "Accumulation: 80" in report.institutional_analysis
    assert "13F: $250.00M" in report.institutional_analysis
    assert "Checklist:" in report.institutional_analysis
    assert "Entry: Ideal Entry" in report.trade_plan
    assert "Stop: Technical" in report.trade_plan
    assert "Target: High" in report.trade_plan
    assert "Risk/Reward: 2.4" in report.trade_plan
    assert "Position Size: 150" in report.trade_plan
    assert "Risk/reward: 2.4" in report.risk_summary
    assert report.conclusion.startswith("AAPL conclusion: High Conviction.")
    assert report.confidence in {"Very High", "High", "Moderate", "Low"}
    assert "Review liquidity before entry." in report.warnings
    assert "guaranteed" not in report.conclusion.lower()
    assert "risk-free" not in report.conclusion.lower()


def test_candidate_score_input_report():
    metrics = full_metrics()
    candidate = CandidateScore(
        ticker="AAPL",
        scores=[
            ScoreResult("quality_score", 90.0),
            ScoreResult("technical_score", 84.0),
            ScoreResult("institutional_score", 76.0),
            ScoreResult("support_score", 91.0),
            ScoreResult("bounce_score", 80.0),
        ],
        composite_score=ScoreResult("composite_score", 85.0),
        institutional_bounce_score=88.5,
        composite_intelligence_component_scores={
            "relative_strength_score": 82.0,
            "trend_score": 76.0,
            "volume_score": 78.0,
        },
        opportunity_rating=metrics["opportunity_rating"],
        institutional_checklist=metrics["institutional_checklist"],
        trade_thesis=metrics["trade_thesis"],
        metrics={
            "company_name": "Apple Inc.",
            "revenue_growth": 12.5,
            "eps_growth": 10.2,
            "roe": 24.7,
            "gross_margin": 46.2,
        },
        warnings=["Candidate warning."],
    )

    report = ResearchReportGenerator().generate(candidate)

    assert "AAPL" in report.title
    assert "Apple Inc." in report.title
    assert "Revenue Growth: 12.5%" in report.fundamental_analysis
    assert "Candidate warning." in report.warnings


def test_missing_fundamentals_degrades_gracefully():
    metrics = full_metrics()
    for key in [
        "revenue_growth",
        "eps_growth",
        "roe",
        "gross_margin",
        "free_cash_flow",
        "debt_to_equity",
        "current_ratio",
        "market_cap",
    ]:
        metrics.pop(key, None)

    report = ResearchReportGenerator().generate(metrics)

    assert report.fundamental_analysis == "Fundamental analysis data is unavailable."
    assert "revenue growth" not in report.fundamental_analysis


def test_missing_trade_plan_degrades_gracefully():
    metrics = full_metrics()
    for key in ["entry_zone", "stop_loss", "target_projection", "position_size", "risk_reward"]:
        metrics.pop(key, None)

    report = ResearchReportGenerator().generate(metrics)

    assert report.trade_plan == "Trade plan data is unavailable."
    assert "Missing data: trade plan" in report.risk_summary


def test_weak_candidate_report():
    metrics = {
        "ticker": "WEAK",
        "overall_score": 42.0,
        "technical_score": 35.0,
        "support_score": 40.0,
        "bounce_score": 30.0,
        "earnings_risk_score": 85.0,
        "warnings": ["Support quality is weak."],
    }

    report = ResearchReportGenerator().generate(metrics)

    assert "overall setup score of 42" in report.executive_summary
    assert report.confidence == "Low"
    assert "Support quality is weak." in report.warnings
    assert report.conclusion.startswith("WEAK conclusion: Avoid.")


def test_average_candidate_report():
    metrics = {
        "ticker": "AVG",
        "overall_score": 64.0,
        "support_score": 62.0,
        "bounce_score": 58.0,
        "trend_score": 61.0,
        "relative_strength_score": 57.0,
        "volume_score": 55.0,
        "institutional_score": 60.0,
        "opportunity_rating": {"rating_score": 62.0, "rating_label": "Weak Setup"},
        "institutional_checklist": {"overall_percentage": 60.0, "overall_label": "Weak"},
    }

    report = ResearchReportGenerator().generate(metrics)

    assert "AVG" in report.executive_summary
    assert "mixed contributor" in report.technical_analysis
    assert report.conclusion.startswith("AVG conclusion: Watch List.")
    assert report.confidence in {"Moderate", "Low"}


def test_missing_technicals_degrades_gracefully():
    metrics = full_metrics()
    for key in [
        "technical_score",
        "support_score",
        "bounce_score",
        "trend_score",
        "relative_strength_score",
        "volume_score",
    ]:
        metrics.pop(key, None)

    report = ResearchReportGenerator().generate(metrics)

    assert report.technical_analysis == "Technical analysis data is unavailable."
    assert "Missing data: technical assessment" in report.risk_summary


def test_warning_propagation_from_decision_objects():
    metrics = full_metrics()
    metrics["warnings"] = ["Primary warning"]

    report = ResearchReportGenerator().generate(metrics)

    assert "Primary warning" in report.warnings
    assert len(report.warnings) == len(set(report.warnings))


def test_deterministic_output():
    metrics = full_metrics()
    generator = ResearchReportGenerator()

    first = generator.generate(metrics)
    second = generator.generate(metrics)

    assert first == second


def test_empty_input():
    report = ResearchReportGenerator().generate({})

    assert report.title == "Candidate Institutional Bounce Research Report"
    assert "limited available data" in report.executive_summary
    assert report.confidence == "Low"
    assert report.warnings == []


def test_no_invented_values():
    report = ResearchReportGenerator().generate({"ticker": "MSFT"})
    combined = " ".join(
        [
            report.executive_summary,
            report.setup_quality,
            report.technical_analysis,
            report.fundamental_analysis,
            report.institutional_analysis,
            report.trade_plan,
            report.risk_summary,
            report.conclusion,
        ]
    )

    assert "MSFT" in combined
    assert "Apple" not in combined
    assert "12.5" not in combined
    assert "$95.00B" not in combined
    assert "Revenue Growth" not in combined
