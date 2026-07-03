from __future__ import annotations

from dataclasses import asdict, is_dataclass, replace

from services.chart_data_service import ChartDataService
from services.chart_models import (
    BacktestAnalyticsModel,
    DrawdownPoint,
    EquityCurvePoint,
    PriceLevelOverlay,
    TradeMarker,
    VolumeBar,
)


class ChartAnalyticsService:
    def __init__(self, chart_data_service=None, repository=None, initial_equity=100_000.0):
        self.chart_data_service = chart_data_service or ChartDataService()
        self.repository = repository
        self.initial_equity = float(initial_equity)

    def build_candidate_view(
        self,
        ticker=None,
        candidate=None,
        price_rows=None,
        support_zones=None,
        bounce_markers=None,
        technical_indicators=None,
        institutional_signal=None,
    ):
        model = self.chart_data_service.build_candidate_chart_data(
            ticker=ticker,
            candidate=candidate,
            price_rows=price_rows,
            support_zones=support_zones,
            bounce_markers=bounce_markers,
            technical_indicators=technical_indicators,
            institutional_signal=institutional_signal,
        )
        return self.with_volume_bars(model)

    def build_backtest_trade_chart(self, trade, price_rows=None):
        ticker = self.value(trade, "ticker")
        rows = price_rows
        if rows is None and self.repository is not None and hasattr(self.repository, "fetch_ohlcv"):
            rows = self.repository.fetch_ohlcv(ticker) or []
        model = self.build_candidate_view(
            ticker=ticker,
            candidate={
                "ticker": ticker,
                "final_score": self.value(trade, "final_score"),
                "grade": self.value(trade, "grade"),
                "confidence_level": self.value(trade, "confidence_level"),
                "setup_label": self.value(trade, "setup_label"),
            },
            price_rows=rows,
        )
        entry_price = self.number(self.value(trade, "entry_price"))
        exit_price = self.number(self.value(trade, "exit_price"))
        return self.replace_model(
            model,
            trade_markers=[
                TradeMarker(
                    date=self.value(trade, "entry_date"),
                    price=entry_price,
                    marker_type="entry",
                    label="Entry",
                ),
                TradeMarker(
                    date=self.value(trade, "exit_date"),
                    price=exit_price,
                    marker_type="exit",
                    label=self.value(trade, "exit_reason") or "Exit",
                ),
            ],
            price_overlays=self.trade_price_overlays(trade),
        )

    def build_equity_curve_data(self, trades):
        equity = self.initial_equity
        points = []
        for trade in sorted(trades or [], key=lambda item: str(self.value(item, "exit_date") or "")):
            return_pct = self.number(self.value(trade, "return_pct")) or 0.0
            equity *= 1 + (return_pct / 100)
            points.append(
                EquityCurvePoint(
                    date=self.value(trade, "exit_date"),
                    equity=equity,
                    cumulative_return_pct=((equity - self.initial_equity) / self.initial_equity) * 100,
                )
            )
        return points

    def build_drawdown_curve_data(self, equity_curve):
        peak = self.initial_equity
        points = []
        for point in equity_curve or []:
            peak = max(peak, point.equity)
            drawdown = 0.0 if peak == 0 else ((point.equity - peak) / peak) * 100
            points.append(DrawdownPoint(date=point.date, drawdown_pct=drawdown))
        return points

    def build_backtest_analytics(self, backtest_result):
        trades = self.value(backtest_result, "trades") or []
        metrics = self.value(backtest_result, "metrics") or {}
        warnings = list(self.value(backtest_result, "warnings") or [])
        if not trades:
            warnings.append("No backtest trades available")
        equity = self.build_equity_curve_data(trades)
        drawdown = self.build_drawdown_curve_data(equity)
        ordered = sorted(trades, key=lambda trade: self.number(self.value(trade, "return_pct")) or 0.0)
        return BacktestAnalyticsModel(
            equity_curve=equity,
            drawdown_curve=drawdown,
            summary={
                "total_trades": self.value(metrics, "total_trades") or len(trades),
                "expectancy": self.value(metrics, "expectancy") or 0.0,
                "profit_factor": self.value(metrics, "profit_factor") or 0.0,
                "max_drawdown": min((point.drawdown_pct for point in drawdown), default=0.0),
                "final_equity": equity[-1].equity if equity else self.initial_equity,
            },
            top_winners=list(reversed(ordered[-5:])),
            top_losers=ordered[:5],
            warnings=self.unique(warnings),
        )

    def export_chart_data_payload(self, model):
        return self.json_safe(model)

    @classmethod
    def with_volume_bars(cls, model):
        volume_bars = [
            VolumeBar(
                date=candle.date,
                volume=candle.volume,
                direction="up" if (candle.close or 0) >= (candle.open or 0) else "down",
            )
            for candle in model.candles
        ]
        return cls.replace_model(model, volume_bars=volume_bars)

    @classmethod
    def trade_price_overlays(cls, trade):
        overlays = []
        entry = cls.number(cls.value(trade, "entry_price"))
        if entry is not None:
            stop = cls.number(cls.value(trade, "stop_price"))
            target = cls.number(cls.value(trade, "target_price"))
            if stop is None:
                stop = entry * 0.92
            if target is None:
                target = entry * 1.20
            overlays.extend(
                [
                    PriceLevelOverlay(entry, "Entry", "entry"),
                    PriceLevelOverlay(stop, "Stop Loss", "stop_loss"),
                    PriceLevelOverlay(target, "Profit Target", "profit_target"),
                ]
            )
        return overlays

    @staticmethod
    def replace_model(model, **updates):
        return replace(model, **updates)

    @staticmethod
    def value(source, key):
        if source is None:
            return None
        if isinstance(source, dict):
            return source.get(key)
        return getattr(source, key, None)

    @staticmethod
    def number(value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @classmethod
    def json_safe(cls, value):
        if is_dataclass(value):
            return cls.json_safe(asdict(value))
        if isinstance(value, dict):
            return {str(key): cls.json_safe(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [cls.json_safe(item) for item in value]
        return value

    @staticmethod
    def unique(values):
        result = []
        for value in values or []:
            if value and value not in result:
                result.append(value)
        return result
