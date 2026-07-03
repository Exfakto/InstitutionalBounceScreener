from datetime import datetime
from types import SimpleNamespace

from controllers.dashboard_controller import DashboardController


class FakeMarketController:
    def get_statistics(self):
        return {"stocks": 10, "rows": 100}


class FakeMarketStatusService:
    def get_status(self):
        return SimpleNamespace(status="Closed")


class FakeSettingsService:
    def provider_status(self):
        return {"current_provider": "polygon"}


class FakeWatchlistController:
    def get_watchlist_intelligence(self):
        return SimpleNamespace(total_items=3, high_priority=1, average_score=82.4)


def make_controller():
    return DashboardController(
        market_controller=FakeMarketController(),
        watchlist_controller=FakeWatchlistController(),
        market_status_service=FakeMarketStatusService(),
        settings_service=FakeSettingsService(),
    )


def test_dashboard_controller_empty_state():
    controller = make_controller()

    data = controller.get_dashboard_data()

    assert data["market_summary"]["market_status"] == "Closed"
    assert data["market_summary"]["active_provider"] == "polygon"
    assert data["market_summary"]["database_status"] == "Available"
    assert data["opportunity_summary"]["candidates_screened"] == 0
    assert data["best_opportunities"] == []
    assert data["institutional_activity"] == []


def test_dashboard_controller_populated_dashboard():
    controller = make_controller()
    candidates = [
        SimpleNamespace(
            ticker="MSFT",
            company_name="Microsoft",
            primary_score_value=78.0,
            metrics={"risk_reward": 2.1, "confidence": "Medium"},
            score_map={"institutional_score": SimpleNamespace(value=71.0)},
        ),
        SimpleNamespace(
            ticker="AAPL",
            company_name="Apple Inc.",
            primary_score_value=91.0,
            trade_thesis=SimpleNamespace(confidence="High"),
            metrics={
                "risk_reward": 3.2,
                "ownership_trend": "Rising",
                "insider_activity": "Neutral",
                "13f_status": "Current",
            },
            score_map={"institutional_score": SimpleNamespace(value=86.0)},
        ),
    ]

    data = controller.get_dashboard_data(
        candidates=candidates,
        last_refresh=datetime(2026, 7, 3, 10, 30),
    )

    assert data["market_summary"]["last_refresh"] == "2026-07-03 10:30:00"
    assert data["opportunity_summary"]["candidates_screened"] == 2
    assert data["opportunity_summary"]["high_conviction"] == 1
    assert data["opportunity_summary"]["watch_candidates"] == 1
    assert data["opportunity_summary"]["average_opportunity_score"] == 84.5
    assert data["best_opportunities"][0]["ticker"] == "AAPL"
    assert data["best_opportunities"][0]["confidence"] == "High"
    assert data["institutional_activity"][0]["ticker"] == "AAPL"
    assert data["watchlist_summary"]["total_items"] == 3


def test_dashboard_controller_handles_missing_optional_fields():
    controller = DashboardController()
    candidate = SimpleNamespace(ticker="XYZ")

    data = controller.get_dashboard_data(candidates=[candidate])

    assert data["market_summary"]["market_status"] is None
    assert data["market_summary"]["active_provider"] is None
    assert data["opportunity_summary"]["average_opportunity_score"] is None
    assert data["best_opportunities"][0]["ticker"] == "XYZ"
    assert data["best_opportunities"][0]["company"] is None
    assert data["institutional_activity"] == []
    assert data["warnings"] == []


def test_dashboard_controller_does_not_invent_unavailable_sections():
    controller = make_controller()

    data = controller.get_dashboard_data(
        recent_research=None,
        backtesting_snapshot=None,
    )

    assert data["recent_research"] == []
    assert data["backtesting_snapshot"] == {}
