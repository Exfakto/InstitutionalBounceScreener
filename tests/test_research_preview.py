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


def make_candidate():
    return CandidateScore(
        ticker="AAPL",
        composite_score=ScoreResult("composite_score", 88.5),
        scores=[
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


def test_research_preview_clear_resets_display(app):
    preview = ResearchPreview()
    preview.set_candidate(make_candidate())

    preview.clear()

    assert preview.ticker_label.text() == "No candidate selected"
    assert preview.timestamp_label.text() == "Unavailable"
    assert preview.score_labels["overall"].text() == "Unavailable"
    assert preview.warning_label.text() == "Unavailable"


def test_research_preview_displays_candidate_score(app):
    preview = ResearchPreview()

    preview.set_candidate(make_candidate())

    assert preview.ticker_label.text() == "AAPL"
    assert preview.score_labels["overall"].text() == "88.5"
    assert preview.score_labels["quality_score"].text() == "90.0"
    assert preview.score_labels["institutional_score"].text() == "72.0"
    assert preview.score_labels["technical_score"].text() == "84.0"
    assert preview.score_labels["support_score"].text() == "91.0"
    assert preview.score_labels["bounce_score"].text() == "76.0"
    assert preview.warning_label.text() == "Institutional data is stale"


def test_research_preview_handles_missing_scores(app):
    preview = ResearchPreview()
    candidate = CandidateScore(
        ticker="MSFT",
        composite_score=ScoreResult("composite_score", 50.0),
        scores=[],
    )

    preview.set_candidate(candidate)

    assert preview.ticker_label.text() == "MSFT"
    assert preview.score_labels["overall"].text() == "50.0"
    assert preview.score_labels["quality_score"].text() == "Missing"
    assert preview.warning_label.text() == "None"
