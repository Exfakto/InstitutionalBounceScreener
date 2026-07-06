from types import SimpleNamespace

import pytest
from PySide6.QtWidgets import QApplication, QTableWidget

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
            "macd_signal": 0.8,
            "macd_histogram": 0.45,
            "atr": 3.2,
            "ema20": 448.5,
            "ema50": 431.25,
            "ema200": 390.1,
            "vwap": 446.75,
            "market_structure": "Bullish",
            "primary_support": 438.0,
            "trend_score": 76.0,
            "distance_to_support_pct": 2.4,
            "support_strength_score": 88.0,
            "support_confidence": 82.0,
            "institutional_ownership_change_qoq": 1.3,
            "net_institutional_buying": 250000000,
            "institutional_holders": 1240,
            "institutional_holders_change": 34,
            "recent_13f_activity": "Current",
            "recent_13f_accumulation": "accumulation",
            "major_buyers": ["BlackRock", "Vanguard"],
            "major_sellers": ["Small Cap Fund"],
            "insider_buying_flag": 1,
            "insider_selling_flag": 0,
            "insider_net_activity": 1250000,
            "upcoming_earnings": "2026-07-24",
            "earnings_within_7_days": 1,
            "short_interest_pct": 6.5,
            "price_below_200dma": 0,
            "recent_support_break": 1,
            "support_failure_risk_pct": 22.0,
            "volatility_pct": 14.2,
            "debt_to_equity": 0.85,
            "excessive_debt": 0,
            "heavy_insider_selling": 1,
            "price_above_support_10pct": 0,
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
            "support_zone_low": 432.0,
            "support_zone_high": 440.0,
            "failed_support_breaks": 1,
            "bounce_history": [
                {
                    "date": "2026-06-01",
                    "support_price": 420.0,
                    "low_price": 418.5,
                    "peak_price": 451.5,
                    "bounce_pct": 7.5,
                    "days_to_peak": 6,
                    "successful": True,
                },
                {
                    "date": "2026-06-28",
                    "support_price": 436.5,
                    "low_price": 435.8,
                    "peak_price": 454.8,
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
    assert window.technical_labels["trend"].text() == "76.0"
    assert window.technical_labels["trend"].property("status") == "positive"
    assert window.technical_labels["market_structure"].text() == "Bullish"
    assert window.technical_labels["market_structure"].property("status") == "positive"
    assert window.technical_labels["ema20"].text() == "$448.50"
    assert window.technical_labels["ema50"].text() == "$431.25"
    assert window.technical_labels["ema200"].text() == "$390.10"
    assert window.technical_labels["rsi"].text() == "58.2 (Bullish)"
    assert window.technical_labels["macd"].text() == "1.2 (Bullish)"
    assert window.technical_labels["signal_line"].text() == "0.8 (Bullish)"
    assert window.technical_labels["macd_histogram"].text() == "0.5 (Bullish)"
    assert window.technical_labels["relative_strength"].text() == "81.0 (Bullish)"
    assert window.technical_labels["primary_support"].text() == "$438.00"
    assert window.technical_labels["distance_to_support"].text() == "2.4%"
    assert window.technical_labels["support_strength"].text() == "88.0 / 100"
    assert window.technical_labels["historical_tests"].text() == "5"
    assert window.technical_labels["bounce_success_rate"].text() == "80.0%"
    assert window.technical_labels["average_historical_bounce"].text() == "6.2%"
    assert window.technical_labels["support_confidence"].text() == "82.0 / 100"
    assert window.technical_labels["bounce_success_rate"].property("status") == "positive"
    assert window.technical_summary_label.text() == (
        "The stock remains above all major moving averages.\n"
        "Momentum is improving.\n"
        "Price is trading within 2.4% of a strong institutional support zone.\n"
        "Historical bounce probability is high."
    )
    assert window.institutional_outlook_label.text() == "Strong Accumulation"
    assert window.institutional_outlook_label.property("status") == "positive"
    assert window.institutional_labels["ownership"].text() == "72.0%"
    assert window.institutional_labels["ownership_change_qoq"].text() == "+1.3%"
    assert window.institutional_labels["net_buying"].text() == "$250.00M"
    assert window.institutional_labels["holder_count"].text() == "1,240"
    assert window.institutional_labels["holder_change"].text() == "+34"
    assert window.institutional_labels["recent_13f_activity"].text() == "Current"
    assert window.institutional_labels["recent_13f_accumulation"].text() == "accumulation"
    assert window.institutional_labels["major_buyers"].text() == "BlackRock, Vanguard"
    assert window.institutional_labels["major_sellers"].text() == "Small Cap Fund"
    assert window.institutional_labels["insider_buying"].text() == "Yes"
    assert window.institutional_labels["insider_selling"].text() == "No"
    assert window.institutional_labels["insider_net_activity"].text() == "$1.25M"
    assert window.institutional_summary_label.text() == (
        "Institutional sponsorship appears strong. Ownership is above 60%, "
        "holders increased last quarter, recent 13F activity suggests accumulation."
    )
    assert window.risk_labels["risk_rating"].text() == "Moderate"
    assert window.risk_labels["risk_rating"].property("status") == "watch"
    assert window.risk_labels["overall_risk_score"].text() == "62.0"
    assert window.risk_labels["overall_risk_score"].property("status") == "watch"
    assert window.risk_labels["upcoming_earnings"].text() == "2026-07-24"
    assert window.risk_labels["earnings_within_7_days"].text() == "Yes"
    assert window.risk_labels["earnings_within_7_days"].property("status") == "negative"
    assert window.risk_labels["short_interest"].text() == "6.5%"
    assert window.risk_labels["short_interest"].property("status") == "positive"
    assert window.risk_labels["price_below_200dma"].text() == "No"
    assert window.risk_labels["recent_support_break"].text() == "Yes"
    assert window.risk_labels["support_failure_risk"].text() == "22.0%"
    assert window.risk_labels["support_failure_risk"].property("status") == "negative"
    assert window.risk_labels["volatility"].text() == "14.2%"
    assert window.risk_labels["volatility"].property("status") == "watch"
    assert window.risk_labels["debt_to_equity"].text() == "0.85"
    assert window.risk_labels["excessive_debt"].text() == "No"
    assert window.risk_labels["debt_risk"].text() == "35.0"
    assert window.risk_labels["debt_risk"].property("status") == "positive"
    assert window.risk_labels["heavy_insider_selling"].text() == "Yes"
    assert window.risk_labels["insider_selling_risk"].text() == "80.0"
    assert window.risk_labels["insider_selling_risk"].property("status") == "negative"
    assert window.risk_labels["price_above_support_10pct"].text() == "No"
    assert [label.text() for label in window.risk_warning_labels] == [
        "* Earnings within 7 days",
        "* Recent support break",
        "* Heavy insider selling",
    ]
    assert window.bounce_summary_labels["support_tests"].text() == "5"
    assert window.bounce_summary_labels["successful_bounces"].text() == "4"
    assert window.bounce_summary_labels["success_pct"].text() == "80.0%"
    assert window.bounce_summary_labels["average_bounce"].text() == "6.2%"
    assert window.bounce_summary_labels["median_bounce"].text() == "5.5%"
    assert window.bounce_summary_labels["largest_bounce"].text() == "12.4%"
    assert window.bounce_summary_labels["most_recent_bounce"].text() == "2026-06-28"
    assert window.bounce_summary_labels["failed_support_breaks"].text() == "1"
    assert window.bounce_summary_labels["primary_support"].text() == "$438.00"
    assert window.bounce_summary_labels["support_zone_low"].text() == "$432.00"
    assert window.bounce_summary_labels["support_zone_high"].text() == "$440.00"
    assert window.bounce_summary_labels["support_strength"].text() == "88.0 / 100"
    assert window.bounce_empty_label.isHidden()
    assert window.bounce_history_table.rowCount() == 2
    assert window.bounce_history_table.columnCount() == 7
    assert window.bounce_history_table.item(0, 0).text() == "2026-06-01"
    assert window.bounce_history_table.item(0, 1).text() == "$420.00"
    assert window.bounce_history_table.item(0, 2).text() == "$418.50"
    assert window.bounce_history_table.item(0, 3).text() == "$451.50"
    assert window.bounce_history_table.item(0, 4).text() == "7.5%"
    assert window.bounce_history_table.item(0, 5).text() == "6"
    assert window.bounce_history_table.item(0, 6).text() == "Yes"
    assert window.bounce_history_table.item(1, 6).text() == "No"
    assert window.bounce_interpretation_label.text() == (
        "This support zone has held 4 of 5 times with a 80.0% success rate "
        "and an average bounce of 6.2%."
    )


def test_candidate_detail_window_missing_fields_show_na(app):
    window = CandidateDetailWindow(SimpleNamespace(ticker="MISS"))

    assert window.summary_labels["ticker"].text() == "MISS"
    assert window.summary_labels["company_name"].text() == "Data not available"
    assert window.summary_labels["exchange"].text() == "Data not available"
    assert window.summary_labels["sector"].text() == "Data not available"
    assert window.summary_labels["industry"].text() == "Data not available"
    assert window.summary_labels["current_price"].text() == "Data not available"
    assert window.summary_labels["score"].text() == "Data not available"
    assert window.summary_labels["overall_rating"].text() == "Data not available"
    assert window.summary_labels["opportunity"].text() == "Data not available"
    assert window.summary_text.toPlainText() == "Data not available"
    assert [label.text() for label in window.why_labels] == ["Data not available"]
    assert window.technical_labels["sma20"].text() == "Data not available"
    assert window.technical_labels["ema20"].text() == "Coming in v2.2"
    assert window.technical_labels["macd"].text() == "Coming in v2.2"
    assert window.technical_summary_label.text() == (
        "Moving average positioning is Data not available.\n"
        "Momentum readings are Coming in v2.2.\n"
        "Support proximity is Data not available.\n"
        "Historical bounce probability is Data not available."
    )
    assert window.institutional_outlook_label.text() == "Unknown"
    assert all(label.text() == "Data not available" for label in window.institutional_labels.values())
    assert window.institutional_summary_label.text() == "Institutional sponsorship is N/A."
    assert all(label.text() == "Data not available" for label in window.risk_labels.values())
    assert [label.text() for label in window.risk_warning_labels] == [
        "No major active risk warnings."
    ]
    assert all(label.text() == "Data not available" for label in window.bounce_summary_labels.values())
    assert window.bounce_empty_label.text() == "No historical bounce data available."
    assert not window.bounce_empty_label.isHidden()
    assert window.bounce_history_table.rowCount() == 0
    assert window.bounce_interpretation_label.text() == "Bounce interpretation is Data not available."


def test_candidate_detail_window_institutional_outlook_can_show_distribution(app):
    candidate = SimpleNamespace(
        ticker="WEAK",
        metrics={
            "institutional_ownership_pct": 20.0,
            "institutional_ownership_change_qoq": -2.0,
            "net_institutional_buying": -50000000,
            "institutional_holders_change": -12,
            "recent_13f_accumulation": "distribution",
            "insider_buying_flag": 0,
            "insider_selling_flag": 1,
        },
    )

    window = CandidateDetailWindow(candidate)

    assert window.institutional_outlook_label.text() == "Distribution"
    assert window.institutional_outlook_label.property("status") == "negative"
    assert window.institutional_labels["net_buying"].text() == "-$50.00M"
    assert window.institutional_labels["holder_change"].text() == "-12"
    assert window.institutional_labels["insider_selling"].text() == "Yes"
    assert window.institutional_summary_label.text() == (
        "Institutional sponsorship shows distribution risk. "
        "ownership is below institutional leadership levels, holders declined last quarter, "
        "recent 13F activity suggests distribution."
    )


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
                        "low": 25.1,
                        "peak": 27.9,
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
    assert window.bounce_history_table.item(0, 2).text() == "$25.10"
    assert window.bounce_history_table.item(0, 3).text() == "$27.90"
    assert window.bounce_history_table.item(0, 4).text() == "9.2%"
    assert window.bounce_history_table.item(0, 5).text() == "4"
    assert window.bounce_history_table.item(0, 6).text() == "Yes"


def test_candidate_detail_window_accepts_risk_detail_values(app):
    window = CandidateDetailWindow(
        {"ticker": "RISK"},
        detail={
            "risk": {
                "rating": "High",
                "next_earnings_date": "2026-08-01",
                "earnings_soon": True,
                "short_float_pct": 21.5,
                "below_200_dma": True,
                "recent_breakdown": True,
                "breakdown_risk": 15.0,
                "atr_pct": 8.0,
                "debt_to_equity_ratio": 2.5,
                "high_debt": True,
                "heavy_selling": True,
                "far_above_support": True,
                "leverage_risk": 72.0,
                "insider_selling_score": 0,
                "composite_risk_score": 78.0,
            }
        },
    )

    assert window.risk_labels["risk_rating"].text() == "High"
    assert window.risk_labels["risk_rating"].property("status") == "negative"
    assert window.risk_labels["upcoming_earnings"].text() == "2026-08-01"
    assert window.risk_labels["earnings_within_7_days"].text() == "Yes"
    assert window.risk_labels["short_interest"].text() == "21.5%"
    assert window.risk_labels["short_interest"].property("status") == "negative"
    assert window.risk_labels["price_below_200dma"].text() == "Yes"
    assert window.risk_labels["recent_support_break"].text() == "Yes"
    assert window.risk_labels["support_failure_risk"].text() == "15.0%"
    assert window.risk_labels["support_failure_risk"].property("status") == "watch"
    assert window.risk_labels["volatility"].text() == "8.0%"
    assert window.risk_labels["volatility"].property("status") == "positive"
    assert window.risk_labels["debt_to_equity"].text() == "2.50"
    assert window.risk_labels["debt_to_equity"].property("status") == "negative"
    assert window.risk_labels["excessive_debt"].text() == "Yes"
    assert window.risk_labels["debt_risk"].text() == "72.0"
    assert window.risk_labels["debt_risk"].property("status") == "negative"
    assert window.risk_labels["heavy_insider_selling"].text() == "Yes"
    assert window.risk_labels["insider_selling_risk"].text() == "0.0"
    assert window.risk_labels["insider_selling_risk"].property("status") == "positive"
    assert window.risk_labels["price_above_support_10pct"].text() == "Yes"
    assert window.risk_labels["overall_risk_score"].text() == "78.0"
    assert window.risk_labels["overall_risk_score"].property("status") == "negative"
    assert [label.text() for label in window.risk_warning_labels] == [
        "* Earnings within 7 days",
        "* Price below 200-day moving average",
        "* Recent support break",
        "* Heavy insider selling",
        "* Current price more than 10% above support",
        "* Excessive debt",
    ]


def test_candidate_detail_window_accepts_institutional_detail_values(app):
    window = CandidateDetailWindow(
        {"ticker": "INST"},
        detail={
            "institutional": {
                "institutional_ownership": 48.5,
                "ownership_change_qoq": 0.2,
                "holders": 640,
                "holder_change": 0,
                "13f_net_change": 0,
                "13f_status": "Filed",
                "13f_accumulation": "neutral",
                "top_buyers": ["State Street"],
                "top_sellers": [],
                "insider_buying": False,
                "insider_selling": False,
                "net_insider_activity": "Neutral",
            }
        },
    )

    assert window.institutional_outlook_label.text() == "Neutral"
    assert window.institutional_outlook_label.property("status") == "watch"
    assert window.institutional_labels["ownership"].text() == "48.5%"
    assert window.institutional_labels["ownership_change_qoq"].text() == "+0.2%"
    assert window.institutional_labels["holder_count"].text() == "640"
    assert window.institutional_labels["holder_change"].text() == "+0"
    assert window.institutional_labels["net_buying"].text() == "$0"
    assert window.institutional_labels["recent_13f_activity"].text() == "Filed"
    assert window.institutional_labels["recent_13f_accumulation"].text() == "neutral"
    assert window.institutional_labels["major_buyers"].text() == "State Street"
    assert window.institutional_labels["major_sellers"].text() == "Data not available"
    assert window.institutional_labels["insider_net_activity"].text() == "Neutral"
    assert window.institutional_summary_label.text() == (
        "Institutional sponsorship appears neutral. ownership is moderate, "
        "holder count was flat last quarter, recent 13F activity suggests neutral."
    )


def test_candidate_detail_window_technical_badges_can_be_bearish(app):
    window = CandidateDetailWindow(
        SimpleNamespace(
            ticker="BEAR",
            price=90,
            metrics={
                "trend": "Bearish",
                "market_structure": "Bearish",
                "ema20": 100,
                "ema50": 105,
                "ema200": 110,
                "rsi14": 34,
                "macd": -1.2,
                "macd_signal": -0.8,
                "macd_histogram": -0.4,
                "relative_strength_vs_spy": 42,
                "distance_to_support_pct": 12,
                "support_strength_score": 35,
                "bounce_success_rate": 30,
            },
        )
    )

    assert window.technical_labels["trend"].property("status") == "negative"
    assert window.technical_labels["market_structure"].property("status") == "negative"
    assert window.technical_labels["rsi"].text() == "34.0 (Bearish)"
    assert window.technical_labels["rsi"].property("status") == "negative"
    assert window.technical_labels["macd"].text() == "-1.2 (Bearish)"
    assert window.technical_labels["relative_strength"].property("status") == "negative"
    assert window.technical_labels["distance_to_support"].property("status") == "negative"
    assert window.technical_labels["support_strength"].property("status") == "negative"
    assert window.technical_summary_label.text() == (
        "The stock is trading below all major moving averages.\n"
        "Momentum is weakening.\n"
        "Price is trading within 12.0% of a developing support zone.\n"
        "Historical bounce probability is weak."
    )


def test_candidate_detail_window_set_candidate_refreshes_technical_values(app):
    window = CandidateDetailWindow(
        SimpleNamespace(
            ticker="OLD",
            price=50,
            metrics={
                "trend": "Bearish",
                "rsi14": 35,
                "macd": -0.4,
            },
        )
    )

    assert window.technical_labels["trend"].text() == "Bearish"
    assert window.technical_labels["rsi"].text() == "35.0 (Bearish)"

    window.set_candidate(
        SimpleNamespace(
            ticker="NEW",
            price=120,
            metrics={
                "trend": "Bullish",
                "rsi14": 62,
                "macd": 1.4,
            },
        )
    )

    assert window.windowTitle() == "NEW Candidate Detail"
    assert window.technical_labels["trend"].text() == "Bullish"
    assert window.technical_labels["trend"].property("status") == "positive"
    assert window.technical_labels["rsi"].text() == "62.0 (Bullish)"
    assert window.technical_labels["macd"].text() == "1.4 (Bullish)"


def test_candidate_detail_window_set_candidate_refreshes_institutional_values(app):
    window = CandidateDetailWindow(
        SimpleNamespace(
            ticker="OLD",
            metrics={
                "institutional_ownership_pct": 18,
                "net_institutional_buying": -1000000,
                "insider_selling_flag": 1,
            },
        )
    )

    assert window.institutional_outlook_label.text() == "Distribution"
    assert window.institutional_labels["ownership"].text() == "18.0%"

    window.set_candidate(
        SimpleNamespace(
            ticker="NEW",
            metrics={
                "institutional_ownership_pct": 68,
                "institutional_holders_change": 15,
                "net_institutional_buying": 2000000,
                "recent_13f_accumulation": "accumulation",
            },
        )
    )

    assert window.windowTitle() == "NEW Candidate Detail"
    assert window.institutional_outlook_label.text() == "Strong Accumulation"
    assert window.institutional_outlook_label.property("status") == "positive"
    assert window.institutional_labels["ownership"].text() == "68.0%"
    assert window.institutional_labels["holder_change"].text() == "+15"
    assert window.institutional_labels["net_buying"].text() == "$2.00M"


def test_candidate_detail_window_set_candidate_refreshes_risk_values(app):
    window = CandidateDetailWindow(
        SimpleNamespace(
            ticker="OLD",
            risk_rating=SimpleNamespace(rating_label="High"),
            metrics={
                "overall_risk_score": 82,
                "earnings_within_7_days": 1,
                "below_200_dma": 1,
                "heavy_insider_selling": 1,
            },
        )
    )

    assert window.risk_labels["risk_rating"].text() == "High"
    assert window.risk_labels["risk_rating"].property("status") == "negative"
    assert window.risk_labels["overall_risk_score"].text() == "82.0"
    assert [label.text() for label in window.risk_warning_labels] == [
        "* Earnings within 7 days",
        "* Price below 200-day moving average",
        "* Heavy insider selling",
    ]

    window.set_candidate(
        SimpleNamespace(
            ticker="NEW",
            risk_rating=SimpleNamespace(rating_label="Low"),
            metrics={
                "overall_risk_score": 18,
                "earnings_within_7_days": 0,
                "below_200_dma": 0,
                "heavy_insider_selling": 0,
                "debt_to_equity": 0.4,
            },
        )
    )

    assert window.windowTitle() == "NEW Candidate Detail"
    assert window.risk_labels["risk_rating"].text() == "Low"
    assert window.risk_labels["risk_rating"].property("status") == "positive"
    assert window.risk_labels["overall_risk_score"].text() == "18.0"
    assert window.risk_labels["debt_to_equity"].text() == "0.40"
    assert [label.text() for label in window.risk_warning_labels] == [
        "No major active risk warnings."
    ]


def test_candidate_detail_window_set_candidate_refreshes_bounce_values(app):
    window = CandidateDetailWindow(
        SimpleNamespace(
            ticker="OLD",
            metrics={
                "support_tests": 1,
                "successful_bounces": 0,
                "bounce_success_rate": 0,
                "average_bounce": 0,
                "bounce_history": [],
            },
        )
    )

    assert window.bounce_summary_labels["support_tests"].text() == "1"
    assert window.bounce_history_table.rowCount() == 0
    assert not window.bounce_empty_label.isHidden()

    window.set_candidate(
        SimpleNamespace(
            ticker="NEW",
            metrics={
                "primary_support": 101.25,
                "support_zone_low": 100.0,
                "support_zone_high": 103.0,
                "support_strength": 79,
                "support_tests": 4,
                "successful_bounces": 3,
                "bounce_success_rate": 75,
                "average_bounce": 11.5,
                "failed_support_breaks": 0,
                "bounce_history": [
                    {
                        "date": "2026-06-12",
                        "support_price": 101.25,
                        "low_price": 100.75,
                        "peak_price": 113.0,
                        "bounce_pct": 11.6,
                        "days_to_peak": 5,
                        "successful": True,
                    }
                ],
            },
        )
    )

    assert window.windowTitle() == "NEW Candidate Detail"
    assert window.bounce_summary_labels["primary_support"].text() == "$101.25"
    assert window.bounce_summary_labels["support_strength"].text() == "79.0 / 100"
    assert window.bounce_summary_labels["failed_support_breaks"].text() == "0"
    assert window.bounce_history_table.rowCount() == 1
    assert window.bounce_empty_label.isHidden()
    assert window.bounce_history_table.item(0, 3).text() == "$113.00"
    assert window.bounce_interpretation_label.text() == (
        "This support zone has held 3 of 4 times with a 75.0% success rate "
        "and an average bounce of 11.5%."
    )


def test_candidate_detail_window_detail_values_override_or_supplement_candidate(app):
    candidate = SimpleNamespace(
        ticker="MIXED",
        metrics={
            "rsi14": 40,
            "institutional_ownership_pct": 20,
            "support_tests": 1,
            "risk_score": 65,
        },
    )
    detail = {
        "technical": {"rsi14": 63, "market_structure": "Bullish"},
        "institutional": {"institutional_ownership_pct": 66, "holder_change": 4},
        "bounce": {
            "support_test_count": 6,
            "successful_bounce_count": 5,
            "bounce_success_rate": 83,
        },
        "risk": {
            "risk_score": 22,
            "earnings_within_7_days": True,
        },
    }

    window = CandidateDetailWindow(candidate, detail=detail)

    assert window.technical_labels["rsi"].text() == "63.0 (Bullish)"
    assert window.technical_labels["market_structure"].text() == "Bullish"
    assert window.institutional_labels["ownership"].text() == "66.0%"
    assert window.institutional_labels["holder_change"].text() == "+4"
    assert window.bounce_summary_labels["support_tests"].text() == "6"
    assert window.bounce_summary_labels["successful_bounces"].text() == "5"
    assert window.bounce_summary_labels["success_pct"].text() == "83.0%"
    assert window.risk_labels["overall_risk_score"].text() == "22.0"
    assert window.risk_labels["earnings_within_7_days"].text() == "Yes"


def test_candidate_detail_window_set_candidate_refreshes_all_tabs(app):
    window = CandidateDetailWindow(SimpleNamespace(ticker="OLD"))

    window.set_candidate(
        SimpleNamespace(
            ticker="FULL",
            company_name="Full Candidate Inc.",
            price=25.5,
            primary_score_value=72,
            risk_rating=SimpleNamespace(rating_label="Moderate"),
            metrics={
                "trend": "Bullish",
                "rsi14": 61,
                "institutional_ownership_pct": 64,
                "institutional_holders_change": 8,
                "net_institutional_buying": 3000000,
                "support_tests": 3,
                "successful_bounces": 2,
                "bounce_success_rate": 66,
                "average_bounce": 8.4,
                "bounce_history": [
                    {
                        "date": "2026-06-20",
                        "support_price": 24,
                        "low_price": 23.8,
                        "peak_price": 26.1,
                        "bounce_pct": 8.8,
                        "days_to_peak": 4,
                        "successful": True,
                    }
                ],
                "overall_risk_score": 44,
                "recent_support_break": True,
            },
        )
    )

    assert window.summary_labels["ticker"].text() == "FULL"
    assert window.summary_labels["company_name"].text() == "Full Candidate Inc."
    assert window.technical_labels["trend"].text() == "Bullish"
    assert window.technical_labels["rsi"].text() == "61.0 (Bullish)"
    assert window.institutional_labels["ownership"].text() == "64.0%"
    assert window.bounce_history_table.rowCount() == 1
    assert window.risk_labels["risk_rating"].text() == "Moderate"
    assert window.risk_labels["overall_risk_score"].text() == "44.0"
    assert [label.text() for label in window.risk_warning_labels] == [
        "* Recent support break"
    ]


def test_candidate_detail_window_repeated_updates_do_not_duplicate_tabs_or_tables(app):
    window = CandidateDetailWindow(SimpleNamespace(ticker="START"))

    for index in range(5):
        window.set_candidate(
            SimpleNamespace(
                ticker=f"UPD{index}",
                metrics={
                    "support_tests": index + 1,
                    "bounce_history": [
                        {
                            "date": f"2026-06-{index + 1:02d}",
                            "support_price": 10 + index,
                            "bounce_pct": 5 + index,
                            "days_to_peak": index + 1,
                            "successful": True,
                        }
                    ],
                },
            )
        )

    assert window.tabs.count() == 5
    assert window.layout().count() == 2
    assert len(window.findChildren(QTableWidget)) == 1
    assert window.bounce_history_table.rowCount() == 1
    assert window.bounce_summary_labels["support_tests"].text() == "5"
