import pytest
from types import SimpleNamespace
from PySide6.QtCore import Qt
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
    distance_to_support=None,
    support_strength=None,
    last_bounce=None,
):
    candidate = make_gen2_candidate(ticker, overall, overall)
    metrics = {}
    if risk_reward is not None:
        metrics["risk_reward"] = risk_reward
    if confidence is not None:
        metrics["confidence"] = confidence
    if distance_to_support is not None:
        metrics["distance_to_support"] = distance_to_support
    if support_strength is not None:
        metrics["support_strength"] = support_strength
    if last_bounce is not None:
        metrics["last_bounce"] = last_bounce

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
    assert table.item(0, 0).text() == "1"
    assert table.item(0, 1).text() == "HIGH"
    assert table.item(1, 1).text() == "MID"
    assert table.item(2, 1).text() == "LOW"
    assert table.item(0, 2).text() == "90.0"
    assert table.item(0, 3).text() == "High Conviction"


def test_candidate_table_uses_professional_headers(app):
    table = CandidateTable()

    assert [
        table.horizontalHeaderItem(column).text()
        for column in range(table.columnCount())
    ] == [
        "Rank",
        "Ticker",
        "Overall Score",
        "Signal",
        "Quality",
        "Institutional",
        "Technical",
        "Support",
        "Bounce",
        "Distance to Support",
        "Support Strength",
        "Last Bounce",
        "Detail",
    ]


def test_candidate_table_uses_gen2_score_for_overall_when_available(app):
    table = CandidateTable()

    table.populate(
        [
            make_gen2_candidate("LEGACY_HIGH", 95.0, 30.0),
            make_gen2_candidate("GEN2_HIGH", 50.0, 99.0),
        ]
    )

    assert table.rowCount() == 2
    assert table.item(0, 1).text() == "GEN2_HIGH"
    assert table.item(0, 2).text() == "99.0"


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


def test_candidate_table_adds_local_ticker_badge_icon(app):
    table = CandidateTable()

    table.populate([make_candidate("AAPL", 75.0)])

    assert table.item(0, 1).text() == "AAPL"
    assert table.item(0, 1).icon().isNull() is False


def test_candidate_table_emits_ticker_on_double_click(app):
    table = CandidateTable()
    table.populate([make_candidate("MSFT", 82.0)])
    emitted = []

    table.ticker_double_clicked.connect(emitted.append)
    table.emit_double_clicked_ticker(0, 0)

    assert emitted == ["MSFT"]


def test_candidate_table_detail_column_emits_detail_request(app):
    table = CandidateTable()
    table.populate([make_candidate("AAPL", 88.0)])
    emitted = []

    table.detail_requested.connect(emitted.append)
    table.emit_detail_requested(0, table.columnCount() - 1)

    assert emitted == ["AAPL"]


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
                distance_to_support=2.8,
                support_strength=88.0,
                last_bounce="2026-07-01",
            )
        ]
    )

    assert table.horizontalHeaderItem(3).text() == "Signal"
    assert table.horizontalHeaderItem(9).text() == "Distance to Support"
    assert table.horizontalHeaderItem(12).text() == "Detail"
    assert table.item(0, 3).text() == "Elite Bounce 93.2"
    assert table.item(0, 9).text() == "2.8%"
    assert table.item(0, 9).data(Qt.UserRole) == 2.8
    assert table.item(0, 10).text() == "88.0"
    assert table.item(0, 11).text() == "2026-07-01"
    assert table.item(0, 12).text() == "View"


def test_candidate_table_color_codes_scores_and_signal(app):
    table = CandidateTable()

    table.populate(
        [
            make_professional_candidate(
                "AAPL",
                91.0,
                opportunity=SimpleNamespace(
                    rating_label="High Conviction",
                    rating_score=91.0,
                ),
                distance_to_support=2.0,
            )
        ]
    )

    assert table.item(0, 2).font().bold() is True
    assert table.item(0, 3).font().bold() is True
    assert table.item(0, 9).font().bold() is True
    assert table.item(0, 3).foreground().color().isValid()


def test_candidate_table_missing_values_display_safely(app):
    table = CandidateTable()
    candidate = CandidateScore(
        ticker="MISS",
        composite_score=ScoreResult("composite_score", 0),
        scores=[],
        institutional_bounce_score=None,
    )

    table.populate([candidate])

    assert table.item(0, 2).text() == "0.0"
    assert table.item(0, 3).text() == "Avoid"
    assert table.item(0, 4).text() == "N/A"
    assert table.item(0, 9).text() == "N/A"
    assert table.item(0, 11).text() == "N/A"


def test_candidate_table_empty_and_repeated_refresh_do_not_duplicate_rows(app):
    table = CandidateTable()

    table.populate([])

    assert table.rowCount() == 0
    assert table.selected_ticker() is None

    table.populate([make_candidate("AAPL", 75.0)])
    table.populate([make_candidate("MSFT", 80.0)])

    assert table.rowCount() == 1
    assert table.item(0, 1).text() == "MSFT"


def test_candidate_table_public_methods_preserved(app):
    table = CandidateTable()

    assert callable(table.populate)
    assert callable(table.selected_ticker)
    assert callable(table.ticker_at_row)
    assert callable(table.format_score)
    assert table.format_score(None) == "N/A"
