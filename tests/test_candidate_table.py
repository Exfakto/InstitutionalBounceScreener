import pytest
from types import SimpleNamespace
from PySide6.QtWidgets import QApplication, QAbstractItemView

from analysis.candidate_score import CandidateScore
from analysis.score_result import ScoreResult
from ui.widgets.candidate_table import CandidateTable


@pytest.fixture(scope="module")
def app():
    application = QApplication.instance()

    if application is None:
        application = QApplication([])

    return application


def make_candidate(ticker, overall):
    return CandidateScore(
        ticker=ticker,
        composite_score=ScoreResult("composite_score", overall),
        scores=[
            ScoreResult("quality_score", overall - 1),
            ScoreResult("institutional_score", overall - 2),
            ScoreResult("technical_score", overall - 3),
            ScoreResult("support_score", overall - 4),
            ScoreResult("bounce_score", overall - 5),
        ],
    )


def make_gen2_candidate(ticker, overall, gen2):
    candidate = make_candidate(ticker, overall)

    return CandidateScore(
        ticker=candidate.ticker,
        composite_score=candidate.composite_score,
        scores=candidate.scores,
        institutional_bounce_score=gen2,
    )


def make_professional_candidate(
    ticker,
    overall,
    opportunity=None,
    risk_reward=None,
    confidence=None,
):
    candidate = make_gen2_candidate(ticker, overall, overall)
    metrics = {}
    if risk_reward is not None:
        metrics["risk_reward"] = risk_reward
    if confidence is not None:
        metrics["confidence"] = confidence

    return CandidateScore(
        ticker=candidate.ticker,
        composite_score=candidate.composite_score,
        scores=candidate.scores,
        institutional_bounce_score=candidate.institutional_bounce_score,
        opportunity_rating=opportunity,
        metrics=metrics,
    )


def test_candidate_table_populates_sorted_by_overall_score(app):
    table = CandidateTable()

    table.populate(
        [
            make_candidate("LOW", 20.0),
            make_candidate("HIGH", 90.0),
            make_candidate("MID", 50.0),
        ]
    )

    assert table.rowCount() == 3
    assert table.item(0, 0).text() == "HIGH"
    assert table.item(1, 0).text() == "MID"
    assert table.item(2, 0).text() == "LOW"
    assert table.item(0, 1).text() == "90.0"
    assert table.item(0, 2).text() == "High Conviction"


def test_candidate_table_labels_overall_as_gen2_score(app):
    table = CandidateTable()

    assert table.horizontalHeaderItem(1).text() == "Overall (Gen 2)"


def test_candidate_table_uses_gen2_score_for_overall_when_available(app):
    table = CandidateTable()

    table.populate(
        [
            make_gen2_candidate("LEGACY_HIGH", 95.0, 30.0),
            make_gen2_candidate("GEN2_HIGH", 50.0, 99.0),
        ]
    )

    assert table.rowCount() == 2
    assert table.item(0, 0).text() == "GEN2_HIGH"
    assert table.item(0, 1).text() == "99.0"


def test_candidate_table_is_read_only_and_uses_single_row_selection(app):
    table = CandidateTable()

    assert table.editTriggers() == QAbstractItemView.NoEditTriggers
    assert table.selectionBehavior() == QAbstractItemView.SelectRows
    assert table.selectionMode() == QAbstractItemView.SingleSelection
    assert table.alternatingRowColors() is True
    assert table.showGrid() is False


def test_candidate_table_exposes_selected_ticker(app):
    table = CandidateTable()
    table.populate([make_candidate("AAPL", 75.0)])

    assert table.selected_ticker() is None

    table.selectRow(0)

    assert table.selected_ticker() == "AAPL"


def test_candidate_table_emits_ticker_on_double_click(app):
    table = CandidateTable()
    table.populate([make_candidate("MSFT", 82.0)])
    emitted = []

    table.ticker_double_clicked.connect(emitted.append)
    table.emit_double_clicked_ticker(0, 0)

    assert emitted == ["MSFT"]


def test_candidate_table_professional_columns_display_existing_values(app):
    table = CandidateTable()
    opportunity = SimpleNamespace(rating_label="Elite Bounce", rating_score=93.2)

    table.populate(
        [
            make_professional_candidate(
                "AAPL",
                91.0,
                opportunity=opportunity,
                risk_reward=2.35,
                confidence="High",
            )
        ]
    )

    assert table.horizontalHeaderItem(2).text() == "Opportunity"
    assert table.horizontalHeaderItem(6).text() == "Risk/Reward"
    assert table.horizontalHeaderItem(7).text() == "Confidence"
    assert table.item(0, 2).text() == "Elite Bounce 93.2"
    assert table.item(0, 6).text() == "2.35:1"
    assert table.item(0, 7).text() == "High"


def test_candidate_table_missing_values_display_safely(app):
    table = CandidateTable()
    candidate = CandidateScore(
        ticker="MISS",
        composite_score=ScoreResult("composite_score", 0),
        scores=[],
        institutional_bounce_score=None,
    )

    table.populate([candidate])

    assert table.item(0, 1).text() == "0.0"
    assert table.item(0, 2).text() == "Avoid"
    assert table.item(0, 3).text() == "--"
    assert table.item(0, 6).text() == "--"
    assert table.item(0, 7).text() == "--"


def test_candidate_table_empty_and_repeated_refresh_do_not_duplicate_rows(app):
    table = CandidateTable()

    table.populate([])

    assert table.rowCount() == 0
    assert table.selected_ticker() is None

    table.populate([make_candidate("AAPL", 75.0)])
    table.populate([make_candidate("MSFT", 80.0)])

    assert table.rowCount() == 1
    assert table.item(0, 0).text() == "MSFT"


def test_candidate_table_public_methods_preserved(app):
    table = CandidateTable()

    assert callable(table.populate)
    assert callable(table.selected_ticker)
    assert callable(table.ticker_at_row)
    assert callable(table.format_score)
    assert table.format_score(None) == "--"
