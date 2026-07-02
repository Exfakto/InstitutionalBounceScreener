from datetime import datetime, timezone

import pandas as pd
import pytest
from PySide6.QtWidgets import QApplication

from analysis.candidate_score import CandidateScore
from analysis.institutional_checklist import InstitutionalChecklistEvaluator
from analysis.opportunity_rating import OpportunityRatingCalculator
from analysis.portfolio_statistics import PortfolioStatisticsCalculator
from analysis.score_result import ScoreResult
from analysis.strategy_analytics import StrategyAnalyticsCalculator
from analysis.trade_thesis import TradeThesisGenerator
from controllers.watchlist_controller import WatchlistController
from providers.provider_result import ProviderResult
from services.bounce_validation_service import BounceValidationService
from services.historical_sync_service import HistoricalSyncService
from services.indicator_service import IndicatorService
from services.sync_diagnostics_service import SyncDiagnosticsService
from services.support_service import SupportDetectionService
from indicators.moving_averages.sma import SMAIndicator
from ui.widgets.performance_dashboard import PerformanceDashboard
from ui.widgets.research_preview import ResearchPreview
from ui.widgets.trade_card import TradeCard


@pytest.fixture(scope="module")
def app():
    application = QApplication.instance()

    if application is None:
        application = QApplication([])

    return application


class FakeLiveDataService:
    def __init__(self, results):
        self.results = results
        self.calls = []

    def get_price_history(self, ticker, start=None, end=None):
        self.calls.append((ticker, start, end))
        return self.results.get(ticker, ProviderResult.ok(data=[], source="fake"))


class WorkflowDatabase:
    def __init__(self, tickers=None):
        self.tickers = tickers or ["AAPL"]
        self.price_rows = {}
        self.sma_rows = []
        self.support_levels = []
        self.bounce_validations = []
        self.commit_count = 0
        self.cursor = WorkflowCursor(self)

    def get_all_tickers(self):
        return list(self.tickers)

    def get_price_history(self, ticker):
        rows = [
            {"date": row_date, **values}
            for (row_ticker, row_date), values in sorted(self.price_rows.items())
            if row_ticker == ticker
        ]

        if not rows:
            return pd.DataFrame()

        frame = pd.DataFrame(rows)
        frame["date"] = pd.to_datetime(frame["date"])
        frame.set_index("date", inplace=True)
        frame.rename(
            columns={
                "open": "Open",
                "high": "High",
                "low": "Low",
                "close": "Close",
                "volume": "Volume",
            },
            inplace=True,
        )
        return frame[["Open", "High", "Low", "Close", "Volume"]]

    def save_sma(self, dataframe):
        self.sma_rows.extend(dataframe.reset_index().to_dict("records"))

    def save_support_levels(self, ticker, zones):
        start_id = len(self.support_levels) + 1
        for index, zone in enumerate(zones, start=start_id):
            record = {"id": index, "ticker": ticker, **zone}
            self.support_levels.append(record)
        return len(zones)

    def get_all_support_levels(self):
        return list(self.support_levels)

    def save_bounce_validations(self, validations):
        self.bounce_validations.extend(validations)
        return len(validations)

    def commit(self):
        self.commit_count += 1

    def close(self):
        pass


class WorkflowCursor:
    def __init__(self, database):
        self.database = database
        self.fetchone_result = None

    def execute(self, sql, params):
        statement = " ".join(sql.split()).upper()

        if statement.startswith("SELECT"):
            ticker, row_date = params
            self.fetchone_result = self.database.price_rows.get((ticker, row_date))
            return

        if statement.startswith("INSERT"):
            ticker, row_date, open_, high, low, close, volume = params
            self.database.price_rows[(ticker, row_date)] = {
                "open": open_,
                "high": high,
                "low": low,
                "close": close,
                "volume": volume,
            }
            return

        if statement.startswith("UPDATE"):
            open_, high, low, close, volume, ticker, row_date = params
            self.database.price_rows[(ticker, row_date)] = {
                "open": open_,
                "high": high,
                "low": low,
                "close": close,
                "volume": volume,
            }

    def fetchone(self):
        return self.fetchone_result


class FakeSupportDetector:
    def detect(self, dataframe):
        return [{"price": float(dataframe["Low"].min())}]


class FakeSupportClusterer:
    def cluster(self, swing_lows, current_price):
        return [
            {
                "zone_low": 95.0,
                "zone_high": 101.0,
                "zone_mid": 98.0,
                "touches": 4,
                "strength_score": 88.0,
                "current_price": current_price,
                "distance_from_current": current_price - 98.0,
                "distance_from_current_pct": 2.0,
                "first_touch_date": "2026-01-01",
                "last_touch_date": "2026-06-01",
            }
        ]


class FakeSupportStrength:
    def apply(self, zones):
        return zones


class FakeBounceValidator:
    def validate(self, dataframe, support_level):
        return {
            "support_level_id": support_level["id"],
            "ticker": support_level["ticker"],
            "total_touches": 4,
            "successful_bounces": 3,
            "failed_breakdowns": 0,
            "neutral_touches": 1,
            "bounce_success_rate": 75.0,
            "average_bounce_pct": 8.0,
            "median_bounce_pct": 7.0,
            "average_days_to_bounce_peak": 5.0,
            "current_distance_to_support": 2.0,
            "current_distance_to_support_pct": 2.0,
        }


def price_frame(periods=260, end="2026-07-02"):
    dates = pd.bdate_range(end=end, periods=periods)
    closes = [100.0 + index * 0.1 for index in range(periods)]
    return pd.DataFrame(
        {
            "Open": closes,
            "High": [value + 1 for value in closes],
            "Low": [value - 1 for value in closes],
            "Close": closes,
            "Volume": [1_000_000 + index for index in range(periods)],
        },
        index=dates,
    )


def decision_metrics():
    return {
        "ticker": "AAPL",
        "company_name": "Apple Inc.",
        "institutional_bounce_score": 88.0,
        "opportunity_rating_score": 84.0,
        "quality_score": 85.0,
        "institutional_score": 80.0,
        "institutional_momentum_score": 82.0,
        "technical_score": 86.0,
        "relative_strength_score": 83.0,
        "support_score": 90.0,
        "bounce_score": 78.0,
        "entry_quality_score": 82.0,
        "volume_score": 80.0,
        "trend_score": 81.0,
        "earnings_risk_score": 20.0,
        "risk_score": 76.0,
        "distance_to_support_pct": 2.0,
        "bounce_success_rate": 75.0,
        "average_bounce_pct": 8.0,
    }


def candidate_from_metrics(metrics):
    opportunity = OpportunityRatingCalculator().calculate(metrics)
    checklist_metrics = dict(metrics)
    checklist_metrics["opportunity_rating_score"] = opportunity.rating_score
    checklist = InstitutionalChecklistEvaluator().evaluate(checklist_metrics)
    thesis_metrics = dict(checklist_metrics)
    thesis_metrics["opportunity_rating"] = opportunity
    thesis_metrics["institutional_checklist"] = checklist
    thesis = TradeThesisGenerator().generate(thesis_metrics)

    return CandidateScore(
        ticker=metrics["ticker"],
        composite_score=ScoreResult("composite_score", 86.0),
        scores=[
            ScoreResult("quality_score", metrics["quality_score"]),
            ScoreResult("institutional_score", metrics["institutional_score"]),
            ScoreResult("technical_score", metrics["technical_score"]),
            ScoreResult("support_score", metrics["support_score"]),
            ScoreResult("bounce_score", metrics["bounce_score"]),
        ],
        institutional_bounce_score=metrics["institutional_bounce_score"],
        composite_intelligence_component_scores={
            key: value
            for key, value in metrics.items()
            if key.endswith("_score") or key.endswith("_pct")
        },
        opportunity_rating=opportunity,
        institutional_checklist=checklist,
        trade_thesis=thesis,
        timestamp=datetime(2026, 7, 2, tzinfo=timezone.utc),
    )


def test_workflow_1_historical_sync_to_research_preview(app):
    database = WorkflowDatabase()
    sync = HistoricalSyncService(
        live_data_service=FakeLiveDataService(
            {"AAPL": ProviderResult.ok(data=price_frame(), source="polygon")}
        ),
        database_manager=database,
    )

    sync_summary = sync.sync_ticker("AAPL")

    indicator_service = IndicatorService.__new__(IndicatorService)
    indicator_service.db = database
    indicator_service.sma = SMAIndicator()
    indicator_summary = indicator_service.calculate_sma()

    support_service = SupportDetectionService.__new__(SupportDetectionService)
    support_service.db = database
    support_service.detector = FakeSupportDetector()
    support_service.clusterer = FakeSupportClusterer()
    support_service.strength = FakeSupportStrength()
    support_summary = support_service.detect_support()

    bounce_service = BounceValidationService.__new__(BounceValidationService)
    bounce_service.db = database
    bounce_service.validator = FakeBounceValidator()
    bounce_summary = bounce_service.validate_bounces()

    preview = ResearchPreview()
    preview.set_candidate(candidate_from_metrics(decision_metrics()))

    assert sync_summary["inserted"] == 260
    assert indicator_summary["processed"] == 1
    assert support_summary["zones"] == 1
    assert bounce_summary["validated"] == 1
    assert preview.ticker_label.text() == "AAPL"
    assert preview.rating_label.text().endswith(("Elite Bounce", "High Probability"))


def test_workflow_2_historical_sync_to_candidate_rating_and_trade_card(app):
    database = WorkflowDatabase()
    sync = HistoricalSyncService(
        live_data_service=FakeLiveDataService(
            {"AAPL": ProviderResult.ok(data=price_frame(periods=20), source="polygon")}
        ),
        database_manager=database,
    )
    sync_summary = sync.sync_ticker("AAPL")

    candidate = candidate_from_metrics(decision_metrics())
    trade_card_payload = {
        "ticker": candidate.ticker,
        "company_name": "Apple Inc.",
        "opportunity_rating": candidate.opportunity_rating,
        "overall_status": "Watch",
        "entry": 101.0,
        "recommended_stop": 96.0,
        "target_1": 108.0,
        "target_2": 114.0,
        "target_3": 122.0,
        "best_rr": 2.6,
        "position_size": 100,
        "confidence": candidate.trade_thesis.confidence,
        "trade_thesis": candidate.trade_thesis,
    }
    trade_card = TradeCard()
    trade_card.set_trade_card(trade_card_payload)

    assert sync_summary["processed"] == 20
    assert candidate.opportunity_rating.rating_score >= 80
    assert candidate.trade_thesis.summary
    assert trade_card.ticker_label.text() == "AAPL"
    assert trade_card.risk_labels["risk_reward"].text() == "2.60:1"


def test_workflow_3_historical_sync_to_portfolio_performance_dashboard(app):
    database = WorkflowDatabase()
    sync = HistoricalSyncService(
        live_data_service=FakeLiveDataService(
            {"AAPL": ProviderResult.ok(data=price_frame(periods=10), source="polygon")}
        ),
        database_manager=database,
    )
    sync_summary = sync.sync_ticker("AAPL")

    trades = [
        {
            "ticker": "AAPL",
            "entry_date": "2026-06-01",
            "entry_price": 100.0,
            "exit_date": "2026-06-10",
            "exit_price": 110.0,
            "status": "Exited Win",
            "shares": 10,
            "risk_reward": 2.5,
            "opportunity_rating": "High Probability",
            "confidence": "High",
        }
    ]
    portfolio_stats = PortfolioStatisticsCalculator().calculate(trades)
    strategy_stats = StrategyAnalyticsCalculator().calculate(
        [
            {
                **trades[0],
                "sector": "Technology",
            }
        ]
    )
    dashboard = PerformanceDashboard()
    dashboard.set_statistics(portfolio_stats, strategy_stats)

    assert sync_summary["inserted"] == 10
    assert portfolio_stats.total_trades == 1
    assert portfolio_stats.win_rate == 100.0
    assert dashboard.summary_labels["total_trades"].text() == "1"
    assert dashboard.summary_labels["win_rate"].text() == "100.00%"


class FakeWatchlistService:
    def __init__(self):
        self.items = []

    def add_item(self, ticker, company_name=None, notes=None, source=None):
        item = {
            "id": len(self.items) + 1,
            "ticker": ticker.upper(),
            "company_name": company_name,
            "notes": notes,
            "source": source,
        }
        self.items.append(item)
        return {"success": True, "message": "added", "item": item}


def test_workflow_4_watchlist_live_refresh_to_research_preview(app):
    history = price_frame(periods=2)
    controller = WatchlistController(
        watchlist_service=FakeWatchlistService(),
        live_data_service=FakeLiveDataService(
            {"AAPL": ProviderResult.ok(data=history, source="local")}
        ),
    )

    add_result = controller.add_candidate("aapl", company_name="Apple Inc.")
    refresh_result = controller.refresh_watchlist(["AAPL"])
    preview = ResearchPreview()
    preview.set_candidate(candidate_from_metrics(decision_metrics()))

    assert add_result["success"] is True
    assert refresh_result["quotes"]["AAPL"]["success"] is True
    assert refresh_result["quotes"]["AAPL"]["last_price"] == history["Close"].iloc[-1]
    assert preview.ticker_label.text() == "AAPL"


def test_workflow_5_provider_sync_diagnostics_to_research(app):
    database = WorkflowDatabase()
    provider_data = ProviderResult.ok(data=price_frame(periods=251), source="polygon")
    sync = HistoricalSyncService(
        live_data_service=FakeLiveDataService({"AAPL": provider_data}),
        database_manager=database,
    )

    sync_summary = sync.sync_ticker("AAPL")
    diagnostics = SyncDiagnosticsService(database).diagnose_ticker(
        "AAPL",
        today="2026-07-02",
    )
    preview = ResearchPreview()
    preview.set_candidate(candidate_from_metrics(decision_metrics()))

    assert sync_summary["provider"] == "polygon"
    assert diagnostics["status"] == "Current"
    assert diagnostics["missing_days_count"] == 0
    assert preview.summary_labels["checklist"].text().endswith(
        preview.format_checklist_summary(
            candidate_from_metrics(decision_metrics()).institutional_checklist
        ).split(" ", 1)[1]
    )
