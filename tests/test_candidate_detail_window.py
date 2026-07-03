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
            "rsi14": 58.2,
            "macd": 1.25,
            "atr": 3.2,
            "ema20": 448.5,
            "ema50": 431.25,
            "ema200": 390.1,
            "vwap": 446.75,
            "trend_score": 76.0,
            "distance_to_support_pct": 2.4,
            "support_strength_score": 88.0,
            "institutional_ownership_change_qoq": 1.3,
            "net_institutional_buying": 250000000,
            "institutional_holders": 1240,
            "recent_13f_activity": "Current",
            "insider_buying_flag": 1,
            "insider_selling_flag": 0,
            "upcoming_earnings": "2026-07-24",
            "short_interest_pct": 6.5,
            "support_failure_risk_pct": 22.0,
            "volatility_pct": 14.2,
            "debt_risk_score": 35.0,
            "insider_selling_risk": 80.0,
            "overall_risk_score": 62.0,
            "support_tests": 5,
            "successful_bounces": 4,
            "bounce_success_pct": 80.0,
            "average_bounce": 6.2,
            "median_bounce": 5.5,
            "largest_bounce": 12.4,
            "most_recent_bounce": "2026-06-28",
            "bounce_history": [
                {
                    "date": "2026-06-01",
                    "support_price": 420.0,
                    "bounce_pct": 7.5,
                    "days_to_peak": 6,
                    "successful": True,
                },
                {
                    "date": "2026-06-28",
                    "support_price": 436.5,
                    "bounce_pct": 4.2,
                    "days_to_peak": 3,
                    "successful": False,
                },
            ],
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
    assert window.technical_labels["rsi"].text() == "58.2"
    assert window.technical_labels["macd"].text() == "1.2"
    assert window.technical_labels["atr"].text() == "$3.20"
    assert window.technical_labels["ema20"].text() == "$448.50"
    assert window.technical_labels["ema50"].text() == "$431.25"
    assert window.technical_labels["ema200"].text() == "$390.10"
    assert window.technical_labels["vwap"].text() == "$446.75"
    assert window.technical_labels["trend"].text() == "76.0"
    assert window.technical_labels["relative_strength"].text() == "81.0"
    assert window.technical_labels["distance_to_support"].text() == "2.4%"
    assert window.technical_labels["support_strength"].text() == "88.0"
    assert window.technical_labels["bounce_probability"].text() == "84.0%"
    assert window.technical_labels["bounce_probability"].property("status") == "positive"
    assert window.institutional_outlook_label.text() == "Strong"
    assert window.institutional_outlook_label.property("status") == "positive"
    assert window.institutional_labels["ownership"].text() == "72.0%"
    assert window.institutional_labels["ownership_change_qoq"].text() == "+1.3%"
    assert window.institutional_labels["net_buying"].text() == "$250.00M"
    assert window.institutional_labels["holder_count"].text() == "1,240"
    assert window.institutional_labels["recent_13f_activity"].text() == "Current"
    assert window.institutional_labels["insider_buying"].text() == "Yes"
    assert window.institutional_labels["insider_selling"].text() == "No"
    assert window.risk_labels["risk_rating"].text() == "Moderate"
    assert window.risk_labels["risk_rating"].property("status") == "watch"
    assert window.risk_labels["upcoming_earnings"].text() == "2026-07-24"
    assert window.risk_labels["short_interest"].text() == "6.5%"
    assert window.risk_labels["short_interest"].property("status") == "positive"
    assert window.risk_labels["support_failure_risk"].text() == "22.0%"
    assert window.risk_labels["support_failure_risk"].property("status") == "negative"
    assert window.risk_labels["volatility"].text() == "14.2%"
    assert window.risk_labels["volatility"].property("status") == "watch"
    assert window.risk_labels["debt_risk"].text() == "35.0"
    assert window.risk_labels["debt_risk"].property("status") == "positive"
    assert window.risk_labels["insider_selling_risk"].text() == "80.0"
    assert window.risk_labels["insider_selling_risk"].property("status") == "negative"
    assert window.risk_labels["overall_risk_score"].text() == "62.0"
    assert window.risk_labels["overall_risk_score"].property("status") == "watch"
    assert [label.text() for label in window.risk_warning_labels] == [
        "* Support Failure Risk: 22.0%",
        "* Insider Selling Risk: 80.0",
    ]
    assert window.bounce_summary_labels["support_tests"].text() == "5"
    assert window.bounce_summary_labels["successful_bounces"].text() == "4"
    assert window.bounce_summary_labels["success_pct"].text() == "80.0%"
    assert window.bounce_summary_labels["average_bounce"].text() == "6.2%"
    assert window.bounce_summary_labels["median_bounce"].text() == "5.5%"
    assert window.bounce_summary_labels["largest_bounce"].text() == "12.4%"
    assert window.bounce_summary_labels["most_recent_bounce"].text() == "2026-06-28"
    assert window.bounce_empty_label.isHidden()
    assert window.bounce_history_table.rowCount() == 2
    assert window.bounce_history_table.item(0, 0).text() == "2026-06-01"
    assert window.bounce_history_table.item(0, 1).text() == "$420.00"
    assert window.bounce_history_table.item(0, 2).text() == "7.5%"
    assert window.bounce_history_table.item(0, 3).text() == "6"
    assert window.bounce_history_table.item(0, 4).text() == "Yes"
    assert window.bounce_history_table.item(1, 4).text() == "No"


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
    assert all(label.text() == "N/A" for label in window.technical_labels.values())
    assert window.institutional_outlook_label.text() == "N/A"
    assert all(label.text() == "N/A" for label in window.institutional_labels.values())
    assert all(label.text() == "N/A" for label in window.risk_labels.values())
    assert [label.text() for label in window.risk_warning_labels] == [
        "No active risks highlighted."
    ]
    assert all(label.text() == "N/A" for label in window.bounce_summary_labels.values())
    assert window.bounce_empty_label.text() == "No historical bounce data available."
    assert not window.bounce_empty_label.isHidden()
    assert window.bounce_history_table.rowCount() == 0


def test_candidate_detail_window_institutional_outlook_can_be_weak(app):
    candidate = SimpleNamespace(
        ticker="WEAK",
        metrics={
            "institutional_ownership_pct": 20.0,
            "institutional_ownership_change_qoq": -2.0,
            "net_institutional_buying": -50000000,
            "insider_buying_flag": 0,
            "insider_selling_flag": 1,
        },
    )

    window = CandidateDetailWindow(candidate)

    assert window.institutional_outlook_label.text() == "Weak"
    assert window.institutional_outlook_label.property("status") == "negative"
    assert window.institutional_labels["net_buying"].text() == "-$50.00M"
    assert window.institutional_labels["insider_selling"].text() == "Yes"


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


def test_candidate_detail_window_accepts_bounce_detail_history(app):
    window = CandidateDetailWindow(
        {"ticker": "BOUNCE"},
        detail={
            "bounce": {
                "support_test_count": 1,
                "successful_bounce_count": 1,
                "bounce_success_rate": 100,
                "history": [
                    {
                        "bounce_date": "2026-05-15",
                        "support_level": 25.5,
                        "max_bounce_pct": 9.25,
                        "peak_days": 4,
                        "validated": 1,
                    }
                ],
            }
        },
    )

    assert window.bounce_summary_labels["support_tests"].text() == "1"
    assert window.bounce_summary_labels["successful_bounces"].text() == "1"
    assert window.bounce_summary_labels["success_pct"].text() == "100.0%"
    assert window.bounce_history_table.rowCount() == 1
    assert window.bounce_history_table.item(0, 0).text() == "2026-05-15"
    assert window.bounce_history_table.item(0, 1).text() == "$25.50"
    assert window.bounce_history_table.item(0, 2).text() == "9.2%"
    assert window.bounce_history_table.item(0, 3).text() == "4"
    assert window.bounce_history_table.item(0, 4).text() == "Yes"


def test_candidate_detail_window_accepts_risk_detail_values(app):
    window = CandidateDetailWindow(
        {"ticker": "RISK"},
        detail={
            "risk": {
                "rating": "High",
                "next_earnings_date": "2026-08-01",
                "short_float_pct": 21.5,
                "breakdown_risk": 15.0,
                "atr_pct": 8.0,
                "leverage_risk": 72.0,
                "insider_selling_score": 0,
                "composite_risk_score": 78.0,
            }
        },
    )

    assert window.risk_labels["risk_rating"].text() == "High"
    assert window.risk_labels["risk_rating"].property("status") == "negative"
    assert window.risk_labels["upcoming_earnings"].text() == "2026-08-01"
    assert window.risk_labels["short_interest"].text() == "21.5%"
    assert window.risk_labels["short_interest"].property("status") == "negative"
    assert window.risk_labels["support_failure_risk"].text() == "15.0%"
    assert window.risk_labels["support_failure_risk"].property("status") == "watch"
    assert window.risk_labels["volatility"].text() == "8.0%"
    assert window.risk_labels["volatility"].property("status") == "positive"
    assert window.risk_labels["debt_risk"].text() == "72.0"
    assert window.risk_labels["debt_risk"].property("status") == "negative"
    assert window.risk_labels["insider_selling_risk"].text() == "0.0"
    assert window.risk_labels["insider_selling_risk"].property("status") == "positive"
    assert window.risk_labels["overall_risk_score"].text() == "78.0"
    assert window.risk_labels["overall_risk_score"].property("status") == "negative"
    assert [label.text() for label in window.risk_warning_labels] == [
        "* Risk Rating: High",
        "* Short Interest: 21.5%",
        "* Debt Risk: 72.0",
        "* Overall Risk Score: 78.0",
    ]
