from datetime import datetime, timezone

import pytest
from PySide6.QtWidgets import QApplication, QLabel

from analysis.candidate_score import CandidateScore
from analysis.score_result import ScoreResult
from ui.widgets.research_preview import ResearchPreview


@pytest.fixture(scope="module")
def app():
    application = QApplication.instance()

    if application is None:
        application = QApplication([])

    return application


def make_candidate(overall=88.5, scores=None, components=None, warnings=None):
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
        warnings=warnings or [],
        timestamp=datetime(2026, 6, 30, tzinfo=timezone.utc),
    )


def test_research_preview_empty_state(app):
    preview = ResearchPreview()

    assert preview.empty_state_label.text() == "Select a candidate to begin research."
    assert preview.empty_state_label.isHidden() is False
    assert preview.dashboard_frame.isHidden() is True
    assert preview.warning_label.text() == "No warnings"
    assert preview.thesis_label.text() == "No trade thesis available."


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
    assert preview.thesis_label.text() == "No trade thesis available."
    assert all(
        label.text() == "WARN"
        for label in preview.checklist_status_labels.values()
    )


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
    assert preview.summary_labels["opportunity"].text() != "-"
    assert preview.summary_labels["checklist"].text().endswith("%")
    assert preview.score_labels["quality_score"].text() == "90.0"
    assert preview.score_labels["institutional_score"].text() == "72.0"
    assert preview.score_labels["technical_score"].text() == "84.0"
    assert preview.score_labels["support_score"].text() == "91.0"
    assert preview.score_labels["bounce_score"].text() == "76.0"


def test_research_preview_displays_gen2_overall_when_available(app):
    preview = ResearchPreview()
    candidate = CandidateScore(
        ticker="AAPL",
        composite_score=ScoreResult("composite_score", 40.0),
        scores=make_candidate().scores,
        institutional_bounce_score=91.0,
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


def test_research_preview_placeholder_checklist(app):
    preview = ResearchPreview()
    candidate = make_candidate(
        components={
            "relative_strength_score": 80.0,
            "trend_score": 45.0,
            "volume_score": 65.0,
            "earnings_risk_score": 20.0,
            "risk_score": 78.0,
        },
    )

    preview.set_candidate(candidate)

    assert preview.checklist_status_labels["near_support"].text() == "PASS"
    assert preview.checklist_status_labels["relative_strength"].text() == "PASS"
    assert preview.checklist_status_labels["trend"].text() == "FAIL"
    assert preview.checklist_status_labels["volume"].text() == "WARN"
    assert preview.checklist_status_labels["earnings_window"].text() == "PASS"


def test_research_preview_placeholder_thesis(app):
    preview = ResearchPreview()

    preview.set_trade_thesis("Wait for a confirmed bounce above support.")

    assert preview.thesis_label.text() == "Wait for a confirmed bounce above support."

    preview.set_trade_thesis("")

    assert preview.thesis_label.text() == "No trade thesis available."


def test_research_preview_repeated_updates_do_not_duplicate_widgets(app):
    preview = ResearchPreview()
    initial_label_count = len(preview.findChildren(QLabel))
    initial_checklist_rows = len(preview.checklist_rows)
    initial_summary_labels = len(preview.summary_labels)

    preview.set_candidate(make_candidate(overall=88.5))
    preview.set_candidate(make_candidate(overall=72.0, scores=[]))
    preview.set_candidate(None)

    assert len(preview.checklist_rows) == initial_checklist_rows
    assert len(preview.summary_labels) == initial_summary_labels
    assert len(preview.findChildren(QLabel)) == initial_label_count
    assert preview.empty_state_label.isHidden() is False


def test_research_preview_handles_missing_component_scores(app):
    preview = ResearchPreview()

    preview.set_candidate(make_candidate(overall=50.0, scores=[]))

    assert preview.ticker_label.text() == "AAPL"
    assert preview.signal_label.text().endswith("Avoid")
    assert preview.overall_score_label.text() == "50.0"
    assert preview.score_labels["quality_score"].text() == "-"
    assert preview.score_labels["institutional_score"].text() == "-"
    assert preview.score_labels["technical_score"].text() == "-"
    assert preview.score_labels["support_score"].text() == "-"
    assert preview.score_labels["bounce_score"].text() == "-"
    assert "missing metrics" in preview.warning_label.text()
