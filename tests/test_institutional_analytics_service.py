import pytest

from providers.institutional_provider import (
    InsiderActivity,
    InstitutionalOwnership,
    InstitutionalProvider,
    OwnershipTrend,
    ShortInterest,
    ThirteenFActivity,
)
from services.candidate_detail_data_service import CandidateDetailDataService
from services.institutional_analytics_service import InstitutionalAnalyticsService
from tests.test_stock_detail_data import EmptyDetailDatabase
from ui.candidate_detail_window import CandidateDetailWindow


class FakeInstitutionalProvider(InstitutionalProvider):
    provider_name = "FakeInstitutional"

    def __init__(
        self,
        ownership=None,
        history=None,
        thirteen_f=None,
        insider=None,
        short_interest=None,
        fail=False,
    ):
        self.ownership = ownership
        self.history = history or []
        self.thirteen_f = thirteen_f
        self.insider = insider
        self.short_interest = short_interest
        self.fail = fail

    def maybe_fail(self):
        if self.fail:
            raise RuntimeError("provider offline")

    def get_ownership(self, ticker):
        self.maybe_fail()
        return self.ownership

    def get_ownership_history(self, ticker):
        self.maybe_fail()
        return self.history

    def get_13f_activity(self, ticker):
        self.maybe_fail()
        return self.thirteen_f

    def get_insider_activity(self, ticker):
        self.maybe_fail()
        return self.insider

    def get_short_interest(self, ticker):
        self.maybe_fail()
        return self.short_interest


@pytest.fixture(scope="module")
def app():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def test_no_provider_configured_returns_safe_status():
    analytics = InstitutionalAnalyticsService().analytics_for_ticker("AAPL")

    assert analytics.provider_status == "Provider not configured"
    assert analytics.institutional_score is None
    assert analytics.as_metrics()["institutional_status"] == "Provider not configured"


def test_provider_returns_complete_institutional_data():
    provider = FakeInstitutionalProvider(
        ownership=InstitutionalOwnership("AAA", ownership_pct=72, holders_count=1200),
        history=[OwnershipTrend("AAA", change_qoq_pct=2.5, holders_change=40)],
        thirteen_f=ThirteenFActivity(
            "AAA",
            net_buying=250_000_000,
            accumulation_label="accumulation",
            summary="Net institutional buying",
            major_buyers=["BlackRock"],
        ),
        insider=InsiderActivity("AAA", buying=True, selling=False, net_activity=2_000_000),
        short_interest=ShortInterest("AAA", short_interest_pct=4.5),
    )

    analytics = InstitutionalAnalyticsService(provider).analytics_for_ticker("AAA")

    assert analytics.provider_status == "Available"
    assert analytics.ownership_pct == 72
    assert analytics.ownership_trend == "Increasing"
    assert analytics.thirteen_f_summary == "Net institutional buying"
    assert analytics.insider_activity == "Insider buying"
    assert analytics.short_interest_pct == 4.5
    assert analytics.smart_money_score is not None
    assert analytics.confidence_level == "High"


def test_provider_partial_data_returns_partial_analytics():
    provider = FakeInstitutionalProvider(
        ownership=InstitutionalOwnership("PART", ownership_pct=41),
    )

    analytics = InstitutionalAnalyticsService(provider).analytics_for_ticker("PART")

    assert analytics.provider_status == "Available"
    assert analytics.ownership_pct == 41
    assert analytics.confidence_level == "Low"
    assert analytics.smart_money_score is not None


def test_provider_failure_is_safe():
    analytics = InstitutionalAnalyticsService(
        FakeInstitutionalProvider(fail=True)
    ).analytics_for_ticker("FAIL")

    assert analytics.provider_status == "Provider not configured"
    assert analytics.institutional_score is None
    assert "provider offline" in analytics.warnings[0]


def test_candidate_detail_uses_provider_analytics(app):
    provider = FakeInstitutionalProvider(
        ownership=InstitutionalOwnership("AAA", ownership_pct=70, holders_count=100),
        history=[OwnershipTrend("AAA", change_qoq_pct=3)],
        thirteen_f=ThirteenFActivity("AAA", net_buying=100_000_000),
        insider=InsiderActivity("AAA", buying=True),
        short_interest=ShortInterest("AAA", short_interest_pct=5.5),
    )
    detail = CandidateDetailDataService(
        EmptyDetailDatabase(),
        institutional_provider=provider,
    ).get_candidate_detail("AAA")

    window = CandidateDetailWindow(detail=detail)

    assert detail["institutional"]["institutional_provider_status"] == "Available"
    assert window.institutional_labels["provider_status"].text() == "Available"
    assert window.institutional_labels["ownership"].text() == "70.0%"
    assert window.institutional_labels["short_interest"].text() == "5.5%"
    assert window.institutional_labels["smart_money_score"].text() != "Data not available"


def test_candidate_detail_no_provider_displays_provider_not_configured(app):
    detail = CandidateDetailDataService(EmptyDetailDatabase()).get_candidate_detail("MISS")
    window = CandidateDetailWindow(detail=detail)

    assert detail["institutional"]["status"] == "Provider not configured"
    assert window.institutional_labels["provider_status"].text() == "Provider not configured"
    assert window.institutional_labels["ownership"].text() == "Provider not configured"
    assert window.institutional_summary_label.text() == "Provider not configured."
