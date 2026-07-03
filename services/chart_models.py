from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class OhlcvCandle:
    date: object | None = None
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float | None = None
    volume: float | None = None


@dataclass(frozen=True)
class ChartSupportZone:
    zone_low: float | None = None
    zone_high: float | None = None
    zone_center: float | None = None
    strength_score: float | None = None
    confidence_score: float | None = None
    touch_count: int | None = None
    label: str = "Support Zone"


@dataclass(frozen=True)
class BounceMarker:
    date: object | None = None
    support_price: float | None = None
    bounce_percentage: float | None = None
    successful: bool | None = None
    label: str = "Bounce"


@dataclass(frozen=True)
class TradeMarker:
    date: object | None = None
    price: float | None = None
    marker_type: str = "entry"
    label: str = ""


@dataclass(frozen=True)
class PriceLevelOverlay:
    price: float | None = None
    label: str = ""
    overlay_type: str = "level"


@dataclass(frozen=True)
class VolumeBar:
    date: object | None = None
    volume: float | None = None
    direction: str | None = None


@dataclass(frozen=True)
class TechnicalIndicatorOverlay:
    name: str
    values: list[tuple[object | None, float | None]] = field(default_factory=list)
    latest_value: float | None = None
    status: str | None = None


@dataclass(frozen=True)
class InstitutionalScoreBadge:
    label: str
    score: float | None = None
    status: str | None = None
    as_of_date: object | None = None
    source: str | None = None


@dataclass(frozen=True)
class CandidateScoreAnnotation:
    final_score: float | None = None
    grade: str | None = None
    confidence_level: str | None = None
    setup_label: str | None = None
    explanation: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class CandidateChartModel:
    ticker: str | None = None
    candles: list[OhlcvCandle] = field(default_factory=list)
    support_zones: list[ChartSupportZone] = field(default_factory=list)
    bounce_markers: list[BounceMarker] = field(default_factory=list)
    technical_overlays: list[TechnicalIndicatorOverlay] = field(default_factory=list)
    institutional_badges: list[InstitutionalScoreBadge] = field(default_factory=list)
    candidate_annotation: CandidateScoreAnnotation | None = None
    trade_markers: list[TradeMarker] = field(default_factory=list)
    price_overlays: list[PriceLevelOverlay] = field(default_factory=list)
    volume_bars: list[VolumeBar] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class EquityCurvePoint:
    date: object | None = None
    equity: float = 0.0
    cumulative_return_pct: float = 0.0


@dataclass(frozen=True)
class DrawdownPoint:
    date: object | None = None
    drawdown_pct: float = 0.0


@dataclass(frozen=True)
class BacktestAnalyticsModel:
    equity_curve: list[EquityCurvePoint] = field(default_factory=list)
    drawdown_curve: list[DrawdownPoint] = field(default_factory=list)
    summary: dict = field(default_factory=dict)
    top_winners: list = field(default_factory=list)
    top_losers: list = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
