from PySide6.QtWidgets import QApplication

from backtesting.signal_validation import BacktestTradeResult
from services.chart_analytics_service import ChartAnalyticsService
from services.chart_data_service import ChartDataService
from services.results_export_service import ResultsExportService
from ui.widgets.backtest_analytics_panel import BacktestAnalyticsPanel
from ui.widgets.candidate_chart_panel import CandidateChartPanel


class EmptyDb:
    def get_price_history(self, ticker):
        return None

    def get_technical_indicators(self, ticker):
        return []

    def get_support_levels(self, ticker):
        return []

    def get_bounce_validations(self, ticker):
        return []


def price_rows():
    return [
        {
            "date": "2026-01-01",
            "open": 100,
            "high": 105,
            "low": 98,
            "close": 104,
            "volume": 1000,
        },
        {
            "date": "2026-01-02",
            "open": 104,
            "high": 110,
            "low": 102,
            "close": 108,
            "volume": 1500,
        },
    ]


def trade(return_pct=10):
    return BacktestTradeResult(
        ticker="AAA",
        entry_date="2026-01-01",
        exit_date="2026-01-02",
        entry_price=100,
        exit_price=100 + return_pct,
        return_pct=return_pct,
        max_gain_pct=max(return_pct, 0),
        max_drawdown_pct=min(return_pct, 0),
        holding_days=1,
        exit_reason="profit_target" if return_pct > 0 else "stop_loss",
        final_score=90,
        grade="A",
        confidence_level="HIGH",
        setup_label="Elite Institutional Bounce",
        source_run_id="run-1",
        signal_date="2026-01-01",
    )


def service():
    return ChartAnalyticsService(
        chart_data_service=ChartDataService(db=EmptyDb()),
        initial_equity=100_000,
    )


def test_chart_analytics_candidate_view_with_ohlcv_support_bounce_data():
    model = service().build_candidate_view(
        ticker="AAA",
        candidate={"ticker": "AAA", "final_score": 92, "grade": "A+"},
        price_rows=price_rows(),
        support_zones=[{"zone_low": 98, "zone_high": 101, "strength_score": 85}],
        bounce_markers=[{"date": "2026-01-01", "bounce_pct": 12, "successful": True}],
        technical_indicators=[{"date": "2026-01-02", "ema20": 103}],
        institutional_signal={"score_result": {"overall_score": 88}},
    )

    assert len(model.candles) == 2
    assert len(model.volume_bars) == 2
    assert model.support_zones[0].zone_low == 98
    assert model.bounce_markers[0].bounce_percentage == 12
    assert model.candidate_annotation.grade == "A+"


def test_chart_analytics_backtest_trade_chart_data():
    model = service().build_backtest_trade_chart(trade(), price_rows=price_rows())

    assert len(model.trade_markers) == 2
    assert model.trade_markers[0].marker_type == "entry"
    assert {overlay.overlay_type for overlay in model.price_overlays} == {
        "entry",
        "stop_loss",
        "profit_target",
    }


def test_chart_analytics_equity_and_drawdown_curves():
    analytics_service = service()
    equity = analytics_service.build_equity_curve_data([trade(10), trade(-10)])
    drawdown = analytics_service.build_drawdown_curve_data(equity)

    assert round(equity[0].equity, 2) == 110000
    assert round(equity[1].equity, 2) == 99000
    assert drawdown[0].drawdown_pct == 0
    assert round(drawdown[1].drawdown_pct, 2) == -10


def test_chart_analytics_backtest_summary_top_winners_losers():
    model = service().build_backtest_analytics(
        {
            "trades": [trade(15), trade(-8), trade(5)],
            "metrics": {"total_trades": 3, "expectancy": 4, "profit_factor": 2.5},
        }
    )

    assert model.summary["total_trades"] == 3
    assert model.summary["profit_factor"] == 2.5
    assert model.top_winners[0].return_pct == 15
    assert model.top_losers[0].return_pct == -8


def test_chart_analytics_missing_data_behavior():
    model = service().build_candidate_view(candidate={})
    analytics = service().build_backtest_analytics({"trades": []})

    assert model.candles == []
    assert "Missing ticker" in model.warnings
    assert "No backtest trades available" in analytics.warnings


def test_candidate_chart_panel_displays_advanced_overlays():
    app = QApplication.instance() or QApplication([])
    panel = CandidateChartPanel()
    model = service().build_backtest_trade_chart(trade(), price_rows=price_rows())

    panel.set_chart_model(model)

    assert panel.overlay_labels["trade_markers"].text() != "N/A"
    assert panel.overlay_labels["price_overlays"].text() != "N/A"
    assert panel.overlay_labels["volume_bars"].text() == "2"
    assert app is not None


def test_backtest_analytics_panel_construction_and_population():
    app = QApplication.instance() or QApplication([])
    panel = BacktestAnalyticsPanel()
    model = service().build_backtest_analytics({"trades": [trade(12), trade(-4)]})

    panel.set_analytics_model(model)

    assert panel.current_model is model
    assert "2 trade" in panel.summary_labels["distribution"].text()
    assert panel.winners_table.rowCount() > 0
    assert app is not None


def test_chart_and_analytics_export_enhancements(tmp_path):
    analytics_service = service()
    chart_model = analytics_service.build_candidate_view(
        ticker="AAA",
        price_rows=price_rows(),
    )
    analytics = analytics_service.build_backtest_analytics({"trades": [trade(10), trade(-5)]})
    export_service = ResultsExportService()

    chart = export_service.export_chart_data_json(chart_model, tmp_path, "chart")
    equity = export_service.export_equity_curve_csv(
        analytics.equity_curve,
        tmp_path,
        "equity",
    )
    drawdown = export_service.export_drawdown_curve_csv(
        analytics.drawdown_curve,
        tmp_path,
        "drawdown",
    )
    analytics_json = export_service.export_backtest_analytics_json(
        analytics,
        tmp_path,
        "analytics",
    )

    assert chart["success"] is True
    assert equity["count"] == 2
    assert drawdown["count"] == 2
    assert analytics_json["success"] is True
    assert "cumulative_return_pct" in (tmp_path / "equity.csv").read_text()
