from types import SimpleNamespace

import pytest
from PySide6.QtWidgets import QApplication

from ui.candidate_detail_window import CandidateDetailWindow


@pytest.fixture(scope="module")
def app():
    application = QApplication.instance()

    if application is None:
        application = QApplication([])

    return application


def test_candidate_detail_window_can_be_created(app):
    window = CandidateDetailWindow(
        SimpleNamespace(ticker="AAPL", company_name="Apple Inc.")
    )

    assert window.windowTitle() == "AAPL Candidate Detail"
    assert window.tabs.count() == 5


def test_candidate_detail_window_accepts_candidate_object(app):
    candidate = SimpleNamespace(
        ticker="MSFT",
        company_name="Microsoft Corporation",
        exchange="NASDAQ",
        sector="Technology",
        industry="Software Infrastructure",
        price=450.25,
        primary_score_value=91.4,
        opportunity_rating=SimpleNamespace(
            rating_label="Elite Bounce",
            rating_score=93.2,
        ),
        risk_rating=SimpleNamespace(rating_label="Moderate"),
        summary="High-quality institutional bounce setup.",
        metrics={
            "institutional_ownership_pct": 72.0,
            "successful_support_tests": 3,
            "relative_strength_score": 81.0,
            "bounce_probability": 84.0,
        },
    )

    window = CandidateDetailWindow(candidate)

    assert window.summary_labels["ticker"].text() == "MSFT"
    assert window.summary_labels["company_name"].text() == "Microsoft Corporation"
    assert window.summary_labels["exchange"].text() == "NASDAQ"
    assert window.summary_labels["sector"].text() == "Technology"
    assert window.summary_labels["industry"].text() == "Software Infrastructure"
    assert window.summary_labels["current_price"].text() == "$450.25"
    assert window.summary_labels["score"].text() == "91.4"
    assert window.summary_labels["overall_rating"].text() == "Elite"
    assert window.summary_labels["signal"].text() == "Strong Buy"
    assert window.summary_labels["opportunity"].text() == "Elite Bounce 93.2"
    assert window.summary_labels["risk"].text() == "Moderate"
    assert window.summary_text.toPlainText() == "High-quality institutional bounce setup."
    assert [label.text() for label in window.why_labels] == [
        "* Strong institutional ownership",
        "* Three successful support tests",
        "* Positive relative strength",
        "* High bounce probability",
    ]


def test_candidate_detail_window_missing_fields_show_na(app):
    window = CandidateDetailWindow(SimpleNamespace(ticker="MISS"))

    assert window.summary_labels["ticker"].text() == "MISS"
    assert window.summary_labels["company_name"].text() == "N/A"
    assert window.summary_labels["exchange"].text() == "N/A"
    assert window.summary_labels["sector"].text() == "N/A"
    assert window.summary_labels["industry"].text() == "N/A"
    assert window.summary_labels["current_price"].text() == "N/A"
    assert window.summary_labels["score"].text() == "N/A"
    assert window.summary_labels["overall_rating"].text() == "N/A"
    assert window.summary_labels["opportunity"].text() == "N/A"
    assert window.summary_text.toPlainText() == "N/A"
    assert [label.text() for label in window.why_labels] == ["N/A"]


def test_candidate_detail_window_accepts_explicit_reasons(app):
    candidate = {
        "ticker": "NVDA",
        "company_name": "NVIDIA Corporation",
        "primary_score_value": 76,
        "reasons": ["Positive relative strength", "High bounce probability"],
    }

    window = CandidateDetailWindow(candidate)

    assert window.summary_labels["signal"].text() == "Buy"
    assert window.summary_labels["overall_rating"].text() == "Strong"
    assert [label.text() for label in window.why_labels] == [
        "* Positive relative strength",
        "* High bounce probability",
    ]
