from types import SimpleNamespace

import pytest
from PySide6.QtWidgets import QApplication, QLabel

from ui.widgets.trade_card import TradeCard


@pytest.fixture(scope="module")
def app():
    application = QApplication.instance()

    if application is None:
        application = QApplication([])

    return application


def make_trade_card(**overrides):
    card = {
        "ticker": "AMZN",
        "company_name": "Amazon.com, Inc.",
        "opportunity_rating": {
            "stars": 5,
            "rating_label": "Elite Bounce",
        },
        "overall_status": "Strong Buy",
        "entry": 181.25,
        "stop": 174.50,
        "target_1": 190.00,
        "target_2": 198.25,
        "target_3": 207.75,
        "risk_reward": "3.20:1",
        "position_size": "120 shares",
        "confidence": "High",
        "trade_thesis": {
            "summary": (
                "AMZN remains near validated institutional support with improving "
                "relative strength."
            ),
        },
        "warnings": ["Earnings in 9 days", "ATR elevated"],
    }
    card.update(overrides)
    return card


def test_trade_card_empty_state(app):
    widget = TradeCard()

    assert widget.empty_state_label.text() == "No trade card available."
    assert widget.empty_state_label.isHidden() is False
    assert widget.dashboard_frame.isHidden() is True
    assert widget.rating_label.text() == "Opportunity rating unavailable."
    assert widget.warning_label.text() == "No warnings"
    assert widget.thesis_label.text() == "No trade thesis available."
    assert widget.setup_badge_label.text() == "Missing Data"


def test_trade_card_populated_card(app):
    widget = TradeCard()

    widget.set_trade_card(make_trade_card())

    assert widget.empty_state_label.isHidden() is True
    assert widget.dashboard_frame.isHidden() is False
    assert widget.ticker_label.text() == "AMZN"
    assert widget.company_label.text() == "Amazon.com, Inc."
    assert widget.rating_label.text() == "★★★★★ Elite Bounce"
    assert widget.status_label.text() == "Strong Buy"
    assert widget.setup_badge_label.text() == "Strong Buy"
    assert widget.trade_plan_labels["entry"].text() == "$181.25"
    assert widget.trade_plan_labels["stop"].text() == "$174.50"
    assert widget.trade_plan_labels["target_1"].text() == "$190.00"
    assert widget.trade_plan_labels["target_2"].text() == "$198.25"
    assert widget.trade_plan_labels["target_3"].text() == "$207.75"
    assert widget.risk_labels["risk_reward"].text() == "3.20:1"
    assert widget.risk_labels["position_size"].text() == "120 shares"
    assert widget.risk_labels["confidence"].text() == "High"
    assert "institutional support" in widget.thesis_label.text()
    assert "Entry $181.25" in widget.current_summary


def test_trade_card_accepts_object_input(app):
    widget = TradeCard()
    card = SimpleNamespace(
        ticker="MSFT",
        company_name="Microsoft Corporation",
        opportunity_rating=SimpleNamespace(stars=4, rating_label="High Probability"),
        overall_status="Buy",
        recommended_entry=410.0,
        recommended_stop=392.25,
        target_1=426.0,
        target_2=440.0,
        target_3=455.5,
        best_rr=2.75,
        shares=50,
        confidence="Moderate",
        trade_thesis=SimpleNamespace(summary="MSFT has a defined trade plan."),
        warnings=[],
    )

    widget.set_trade_card(card)

    assert widget.ticker_label.text() == "MSFT"
    assert widget.rating_label.text() == "★★★★☆ High Probability"
    assert widget.trade_plan_labels["entry"].text() == "$410.00"
    assert widget.risk_labels["risk_reward"].text() == "2.75:1"
    assert widget.risk_labels["position_size"].text() == "50"
    assert widget.warning_label.text() == "No warnings"


def test_trade_card_missing_optional_fields(app):
    widget = TradeCard()

    widget.set_trade_card({"ticker": "TSLA"})

    assert widget.ticker_label.text() == "TSLA"
    assert widget.company_label.text() == "-"
    assert widget.rating_label.text() == "Opportunity rating unavailable."
    assert widget.status_label.text() == "-"
    assert widget.setup_badge_label.text() == "Missing Data"
    assert widget.trade_plan_labels["entry"].text() == "-"
    assert widget.risk_labels["confidence"].text() == "-"
    assert widget.thesis_label.text() == "No trade thesis available."
    assert widget.warning_label.text() == "No warnings"


def test_trade_card_repeated_updates_do_not_duplicate_widgets(app):
    widget = TradeCard()
    initial_label_count = len(widget.findChildren(QLabel))

    widget.set_trade_card(make_trade_card(ticker="AAPL"))
    widget.set_trade_card(make_trade_card(ticker="NVDA", warnings=["Spread wide"]))
    widget.set_trade_card(make_trade_card(ticker="META", warnings=[]))

    assert len(widget.findChildren(QLabel)) == initial_label_count
    assert widget.ticker_label.text() == "META"
    assert widget.warning_label.text() == "No warnings"
    assert widget.is_compact is False


def test_trade_card_clear_resets_sections(app):
    widget = TradeCard()
    widget.set_trade_card(make_trade_card())

    widget.clear()

    assert widget.empty_state_label.isHidden() is False
    assert widget.dashboard_frame.isHidden() is True
    assert widget.ticker_label.text() == ""
    assert widget.company_label.text() == ""
    assert widget.rating_label.text() == "Opportunity rating unavailable."
    assert widget.status_label.text() == "-"
    assert all(label.text() == "-" for label in widget.trade_plan_labels.values())
    assert all(label.text() == "-" for label in widget.risk_labels.values())
    assert widget.thesis_label.text() == "No trade thesis available."
    assert widget.warning_label.text() == "No warnings"


def test_trade_card_warnings_display(app):
    widget = TradeCard()

    widget.set_trade_card(make_trade_card(warnings=["Stop is wide", "Target capped"]))

    assert "- Stop is wide" in widget.warning_label.text()
    assert "- Target capped" in widget.warning_label.text()


def test_trade_card_partial_trade_data(app):
    widget = TradeCard()

    widget.set_trade_card(
        {
            "ticker": "NVDA",
            "entry": 120.0,
            "risk_reward": 2.25,
        }
    )

    assert widget.ticker_label.text() == "NVDA"
    assert widget.trade_plan_labels["entry"].text() == "$120.00"
    assert widget.trade_plan_labels["stop"].text() == "-"
    assert widget.risk_labels["risk_reward"].text() == "2.25:1"
    assert widget.setup_badge_label.text() == "Favorable Risk/Reward"


def test_trade_card_badge_display_states(app):
    widget = TradeCard()

    widget.set_trade_card(make_trade_card(overall_status="Watch"))
    assert widget.setup_badge_label.text() == "Watch"

    widget.set_trade_card(make_trade_card(overall_status="Avoid"))
    assert widget.setup_badge_label.text() == "Avoid"

    widget.set_trade_card(make_trade_card(overall_status="High Conviction"))
    assert widget.setup_badge_label.text() == "High Conviction"


def test_trade_card_copy_summary(app):
    widget = TradeCard()
    widget.set_trade_card(make_trade_card())

    copied = widget.copy_summary()

    assert copied == widget.current_summary
    clipboard_text = QApplication.clipboard().text()
    if clipboard_text:
        assert clipboard_text == widget.current_summary
    else:
        pytest.skip("OS clipboard text was unavailable after copy.")
    assert "AMZN trade plan" in copied


def test_trade_card_compact_expanded_toggle(app):
    widget = TradeCard()
    widget.set_trade_card(make_trade_card())

    widget.toggle_compact()

    assert widget.is_compact is True
    assert widget.compact_toggle_button.text() == "Expanded"

    widget.toggle_compact()

    assert widget.is_compact is False
    assert widget.compact_toggle_button.text() == "Compact"
