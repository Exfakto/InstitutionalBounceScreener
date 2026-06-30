from datetime import datetime, timezone

import pytest
from PySide6.QtWidgets import QApplication

from analysis.candidate_score import CandidateScore
from analysis.score_result import ScoreResult
from ui.widgets.research_preview import ResearchPreview


@pytest.fixture(scope="module")
def app():
    application = QApplication.instance()

    if application is None:
        application = QApplication([])

    return application


def make_candidate(overall=88.5, scores=None):
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
        timestamp=datetime(2026, 6, 30, tzinfo=timezone.utc),
    )


def test_research_preview_clear_shows_empty_state(app):
    preview = ResearchPreview()
    preview.set_candidate(make_candidate())

    preview.clear()

    assert (
        preview.empty_state_label.text()
        == "Select a candidate to begin research."
    )
    assert preview.empty_state_label.isHidden() is False
    assert preview.ticker_label.isHidden() is True
    assert preview.overall_score_label.isHidden() is True
    assert preview.warning_label.text() == "No warnings"


def test_research_preview_displays_candidate_score(app):
    preview = ResearchPreview()

    preview.set_candidate(make_candidate())

    assert preview.empty_state_label.isHidden() is True
    assert preview.ticker_label.text() == "AAPL"
    assert preview.signal_label.text() == "🟢 BUY"
    assert preview.overall_score_label.text() == "88.5"
    assert preview.score_labels["quality_score"].text() == "90.0"
    assert preview.score_labels["institutional_score"].text() == "72.0"
    assert preview.score_labels["technical_score"].text() == "84.0"
    assert preview.score_labels["support_score"].text() == "91.0"
    assert preview.score_labels["bounce_score"].text() == "76.0"


def test_research_preview_displays_gen2_overall_when_available(app):
    preview = ResearchPreview()
    candidate = make_candidate(overall=40.0)
    candidate = CandidateScore(
        ticker=candidate.ticker,
        composite_score=candidate.composite_score,
        scores=candidate.scores,
        institutional_bounce_score=91.0,
        warnings=["Missing components reduced confidence"],
        timestamp=candidate.timestamp,
    )

    preview.set_candidate(candidate)

    assert preview.signal_label.text() == "🟢 STRONG BUY"
    assert preview.overall_score_label.text() == "91.0"
    assert "Missing components reduced confidence" in preview.warning_label.text()


@pytest.mark.parametrize(
    ("overall", "signal"),
    [
        (90.0, "🟢 STRONG BUY"),
        (80.0, "🟢 BUY"),
        (70.0, "🟡 WATCH"),
        (69.9, "🔴 AVOID"),
    ],
)
def test_research_preview_signal_labels(app, overall, signal):
    preview = ResearchPreview()

    preview.set_candidate(make_candidate(overall=overall))

    assert preview.signal_label.text() == signal


def test_research_preview_displays_warnings(app):
    preview = ResearchPreview()

    preview.set_candidate(make_candidate())

    assert preview.warning_label.text() == "Institutional data is stale"


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

    assert preview.warning_label.text() == (
        "4 missing metrics\n"
        "Missing revenue_growth_ttm\n"
        "Missing eps_growth_ttm\n"
        "...and 2 more"
    )


def test_research_preview_handles_missing_component_scores(app):
    preview = ResearchPreview()

    preview.set_candidate(make_candidate(overall=50.0, scores=[]))

    assert preview.ticker_label.text() == "AAPL"
    assert preview.signal_label.text() == "🔴 AVOID"
    assert preview.overall_score_label.text() == "50.0"
    assert preview.score_labels["quality_score"].text() == "—"
    assert preview.score_labels["institutional_score"].text() == "—"
    assert preview.score_labels["technical_score"].text() == "—"
    assert preview.score_labels["support_score"].text() == "—"
    assert preview.score_labels["bounce_score"].text() == "—"
    assert preview.warning_label.text() == "No warnings"
