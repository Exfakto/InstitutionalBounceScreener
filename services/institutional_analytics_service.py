"""
Provider-neutral institutional analytics for Candidate Detail.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field, is_dataclass
from typing import Any

from providers.institutional_provider import (
    InsiderActivity,
    InstitutionalOwnership,
    InstitutionalProvider,
    InstitutionalSnapshot,
    NoInstitutionalProvider,
    OwnershipTrend,
    ShortInterest,
    ThirteenFActivity,
)


NOT_CONFIGURED = "Provider not configured"
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class InstitutionalAnalytics:
    ticker: str
    provider_status: str
    institutional_score: float | None = None
    ownership_pct: float | None = None
    ownership_trend: str | None = None
    ownership_change_qoq: float | None = None
    thirteen_f_summary: str | None = None
    insider_activity: str | None = None
    short_interest_pct: float | None = None
    accumulation_score: float | None = None
    distribution_score: float | None = None
    conviction_score: float | None = None
    smart_money_score: float | None = None
    confidence_level: str = "Data not available"
    warnings: list[str] = field(default_factory=list)

    def as_metrics(self) -> dict[str, Any]:
        return {
            "institutional_provider_status": self.provider_status,
            "institutional_status": self.provider_status,
            "institutional_score": self.institutional_score,
            "institutional_ownership_pct": self.ownership_pct,
            "institutional_ownership_change_qoq": self.ownership_change_qoq,
            "ownership_trend": self.ownership_trend,
            "recent_13f_activity": self.thirteen_f_summary,
            "institutional_13f_summary": self.thirteen_f_summary,
            "insider_activity_summary": self.insider_activity,
            "short_interest_pct": self.short_interest_pct,
            "accumulation_score": self.accumulation_score,
            "distribution_score": self.distribution_score,
            "conviction_score": self.conviction_score,
            "smart_money_score": self.smart_money_score,
            "institutional_confidence_level": self.confidence_level,
            "institutional_warnings": list(self.warnings),
        }

    def detail(self) -> dict[str, Any]:
        return {
            key: value
            for key, value in self.as_metrics().items()
            if value not in (None, "")
        }


class InstitutionalAnalyticsService:
    """
    Build institutional analytics from a provider snapshot or stored local row.
    """

    def __init__(self, provider: InstitutionalProvider | None = None):
        self.provider = provider or NoInstitutionalProvider()

    def analytics_for_ticker(self, ticker: str, stored_metrics: Any | None = None) -> InstitutionalAnalytics:
        normalized = self.normalize_ticker(ticker)
        if not normalized:
            return self.not_configured("")

        stored_metrics = self.row_dict(stored_metrics)
        snapshot = self.provider_snapshot(normalized)
        if snapshot.status == "Provider Error" and not self.has_stored_data(stored_metrics):
            return self.not_configured(normalized, warnings=snapshot.warnings)

        if snapshot.status == "Not Configured":
            if self.has_stored_data(stored_metrics):
                snapshot = self.snapshot_from_stored(normalized, stored_metrics)
            else:
                return self.not_configured(normalized)

        metrics = self.metrics_from_snapshot(snapshot)
        if stored_metrics:
            metrics = {**stored_metrics, **{k: v for k, v in metrics.items() if v not in (None, "")}}
        return self.analytics_from_metrics(normalized, snapshot.status, metrics, snapshot.warnings)

    def provider_snapshot(self, ticker: str) -> InstitutionalSnapshot:
        if isinstance(self.provider, NoInstitutionalProvider):
            return InstitutionalSnapshot(ticker=ticker, status="Not Configured")
        try:
            ownership = self.provider.get_ownership(ticker)
            history = self.provider.get_ownership_history(ticker) or []
            thirteen_f = self.provider.get_13f_activity(ticker)
            insider = self.provider.get_insider_activity(ticker)
            short_interest = self.provider.get_short_interest(ticker)
        except Exception as exc:
            logger.warning("Institutional provider failed for %s: %s", ticker, exc)
            return InstitutionalSnapshot(
                ticker=ticker,
                status="Provider Error",
                provider_name=getattr(self.provider, "provider_name", None),
                warnings=[f"Institutional provider failed: {exc}"],
            )

        trend = history[-1] if history else None
        has_data = any(value is not None for value in (ownership, trend, thirteen_f, insider, short_interest))
        return InstitutionalSnapshot(
            ticker=ticker,
            status="Available" if has_data else "Data not available",
            ownership=ownership,
            ownership_trend=trend,
            thirteen_f=thirteen_f,
            insider_activity=insider,
            short_interest=short_interest,
            provider_name=getattr(self.provider, "provider_name", None),
        )

    @classmethod
    def snapshot_from_stored(cls, ticker: str, metrics: dict[str, Any]) -> InstitutionalSnapshot:
        ownership = InstitutionalOwnership(
            ticker=ticker,
            ownership_pct=cls.number(metrics.get("institutional_ownership_pct")),
            holders_count=cls.integer(metrics.get("institutional_holders")),
            source=metrics.get("source"),
            as_of_date=metrics.get("as_of_date"),
        )
        trend = OwnershipTrend(
            ticker=ticker,
            change_qoq_pct=cls.number(metrics.get("institutional_ownership_change_qoq")),
            holders_change=cls.integer(metrics.get("institutional_holders_change")),
            trend_label=metrics.get("ownership_trend"),
            source=metrics.get("source"),
            as_of_date=metrics.get("as_of_date"),
        )
        thirteen_f = ThirteenFActivity(
            ticker=ticker,
            net_buying=cls.number(metrics.get("net_institutional_buying")),
            accumulation_label=metrics.get("recent_13f_accumulation") or metrics.get("recent_13f_activity"),
            summary=metrics.get("institutional_13f_summary"),
            major_buyers=cls.list_value(metrics.get("major_buyers")),
            major_sellers=cls.list_value(metrics.get("major_sellers")),
            source=metrics.get("source"),
            as_of_date=metrics.get("as_of_date"),
        )
        insider = InsiderActivity(
            ticker=ticker,
            buying=cls.bool_or_none(metrics.get("insider_buying_flag")),
            selling=cls.bool_or_none(metrics.get("insider_selling_flag")),
            net_activity=cls.number(metrics.get("insider_net_activity")),
            summary=metrics.get("insider_activity_summary"),
            source=metrics.get("source"),
            as_of_date=metrics.get("as_of_date"),
        )
        short_interest = ShortInterest(
            ticker=ticker,
            short_interest_pct=cls.number(metrics.get("short_interest_pct")),
            source=metrics.get("source"),
            as_of_date=metrics.get("as_of_date"),
        )
        return InstitutionalSnapshot(
            ticker=ticker,
            status="Stored Data",
            ownership=ownership,
            ownership_trend=trend,
            thirteen_f=thirteen_f,
            insider_activity=insider,
            short_interest=short_interest,
            provider_name=metrics.get("source"),
        )

    @classmethod
    def metrics_from_snapshot(cls, snapshot: InstitutionalSnapshot) -> dict[str, Any]:
        ownership = snapshot.ownership
        trend = snapshot.ownership_trend
        thirteen_f = snapshot.thirteen_f
        insider = snapshot.insider_activity
        short_interest = snapshot.short_interest
        return {
            "institutional_ownership_pct": cls.value(ownership, "ownership_pct"),
            "institutional_holders": cls.value(ownership, "holders_count"),
            "institutional_ownership_change_qoq": cls.value(trend, "change_qoq_pct"),
            "institutional_holders_change": cls.value(trend, "holders_change"),
            "ownership_trend": cls.value(trend, "trend_label"),
            "net_institutional_buying": cls.value(thirteen_f, "net_buying"),
            "recent_13f_accumulation": cls.value(thirteen_f, "accumulation_label"),
            "institutional_13f_summary": cls.value(thirteen_f, "summary"),
            "major_buyers": cls.value(thirteen_f, "major_buyers"),
            "major_sellers": cls.value(thirteen_f, "major_sellers"),
            "insider_buying_flag": cls.value(insider, "buying"),
            "insider_selling_flag": cls.value(insider, "selling"),
            "insider_net_activity": cls.value(insider, "net_activity"),
            "insider_activity_summary": cls.value(insider, "summary"),
            "short_interest_pct": cls.value(short_interest, "short_interest_pct"),
        }

    def analytics_from_metrics(
        self,
        ticker: str,
        status: str,
        metrics: dict[str, Any],
        warnings: list[str] | None = None,
    ) -> InstitutionalAnalytics:
        ownership = self.number(metrics.get("institutional_ownership_pct"))
        ownership_change = self.number(metrics.get("institutional_ownership_change_qoq"))
        net_buying = self.number(metrics.get("net_institutional_buying"))
        short_interest = self.number(metrics.get("short_interest_pct"))
        buying = self.bool_or_none(metrics.get("insider_buying_flag"))
        selling = self.bool_or_none(metrics.get("insider_selling_flag"))

        ownership_score = self.ownership_score(ownership)
        accumulation = self.accumulation_score(ownership_change, net_buying, metrics.get("recent_13f_accumulation"))
        distribution = 100 - accumulation if accumulation is not None else None
        conviction = self.average([ownership_score, accumulation])
        insider_score = self.insider_score(buying, selling, metrics.get("insider_net_activity"))
        smart_money = self.average([ownership_score, accumulation, insider_score])
        score = self.average([ownership_score, accumulation, conviction, smart_money])
        confidence = self.confidence_level([ownership, ownership_change, net_buying, buying, selling, short_interest])

        return InstitutionalAnalytics(
            ticker=ticker,
            provider_status=status,
            institutional_score=score,
            ownership_pct=ownership,
            ownership_trend=self.ownership_trend_label(ownership_change, metrics.get("ownership_trend")),
            ownership_change_qoq=ownership_change,
            thirteen_f_summary=self.thirteen_f_summary(net_buying, metrics),
            insider_activity=self.insider_summary(buying, selling, metrics.get("insider_activity_summary")),
            short_interest_pct=short_interest,
            accumulation_score=accumulation,
            distribution_score=distribution,
            conviction_score=conviction,
            smart_money_score=smart_money,
            confidence_level=confidence,
            warnings=list(warnings or []),
        )

    @staticmethod
    def not_configured(ticker: str, warnings: list[str] | None = None) -> InstitutionalAnalytics:
        return InstitutionalAnalytics(
            ticker=ticker,
            provider_status=NOT_CONFIGURED,
            confidence_level="Data not available",
            warnings=list(warnings or []),
        )

    @staticmethod
    def has_stored_data(metrics: dict[str, Any]) -> bool:
        return any(
            metrics.get(key) not in (None, "")
            for key in (
                "institutional_ownership_pct",
                "institutional_ownership_change_qoq",
                "net_institutional_buying",
                "insider_buying_flag",
                "insider_selling_flag",
                "short_interest_pct",
            )
        )

    @staticmethod
    def ownership_score(ownership: float | None) -> float | None:
        if ownership is None:
            return None
        return max(0.0, min(100.0, (ownership / 75.0) * 100.0))

    @classmethod
    def accumulation_score(cls, ownership_change: float | None, net_buying: float | None, text: Any) -> float | None:
        scores = []
        if ownership_change is not None:
            scores.append(cls.directional_score(ownership_change, 5.0))
        if net_buying is not None:
            scores.append(cls.directional_score(net_buying, 500_000_000.0))
        if text:
            scores.append(cls.text_score(str(text)))
        return cls.average(scores)

    @staticmethod
    def directional_score(value: float, scale: float) -> float:
        bounded = max(-1.0, min(1.0, float(value) / scale))
        return (bounded + 1.0) * 50.0

    @staticmethod
    def text_score(text: str) -> float:
        normalized = text.lower()
        if any(word in normalized for word in ("strong", "accumulation", "buying", "inflow", "positive")):
            return 85.0
        if any(word in normalized for word in ("distribution", "selling", "outflow", "negative")):
            return 20.0
        return 50.0

    @staticmethod
    def insider_score(buying: bool | None, selling: bool | None, net_activity: Any) -> float | None:
        net = InstitutionalAnalyticsService.number(net_activity)
        if buying is True or (net is not None and net > 0):
            return 85.0
        if selling is True or (net is not None and net < 0):
            return 20.0
        if buying is False or selling is False or net == 0:
            return 50.0
        return None

    @classmethod
    def average(cls, values: list[Any]) -> float | None:
        numbers = [cls.number(value) for value in values if cls.number(value) is not None]
        if not numbers:
            return None
        return round(sum(numbers) / len(numbers), 1)

    @staticmethod
    def ownership_trend_label(change: float | None, explicit: Any | None = None) -> str | None:
        if explicit not in (None, ""):
            return str(explicit)
        if change is None:
            return None
        if change > 0:
            return "Increasing"
        if change < 0:
            return "Decreasing"
        return "Stable"

    @staticmethod
    def thirteen_f_summary(net_buying: float | None, metrics: dict[str, Any]) -> str | None:
        explicit = metrics.get("institutional_13f_summary") or metrics.get("recent_13f_activity")
        if explicit not in (None, ""):
            return str(explicit)
        if net_buying is None:
            return None
        if net_buying > 0:
            return "Net institutional buying"
        if net_buying < 0:
            return "Net institutional selling"
        return "Neutral 13F activity"

    @staticmethod
    def insider_summary(buying: bool | None, selling: bool | None, explicit: Any | None = None) -> str | None:
        if explicit not in (None, ""):
            return str(explicit)
        if buying is True:
            return "Insider buying"
        if selling is True:
            return "Insider selling"
        if buying is False or selling is False:
            return "Neutral"
        return None

    @staticmethod
    def confidence_level(values: list[Any]) -> str:
        available = sum(1 for value in values if value not in (None, ""))
        if available >= 5:
            return "High"
        if available >= 3:
            return "Moderate"
        if available >= 1:
            return "Low"
        return "Data not available"

    @staticmethod
    def row_dict(row: Any) -> dict[str, Any]:
        if row is None:
            return {}
        if isinstance(row, dict):
            return dict(row)
        if is_dataclass(row):
            return asdict(row)
        if hasattr(row, "keys"):
            return {key: row[key] for key in row.keys()}
        return {
            key: getattr(row, key)
            for key in dir(row)
            if not key.startswith("_") and not callable(getattr(row, key))
        }

    @staticmethod
    def value(source: Any, key: str) -> Any:
        if source is None:
            return None
        if isinstance(source, dict):
            return source.get(key)
        return getattr(source, key, None)

    @staticmethod
    def normalize_ticker(ticker: Any) -> str:
        return str(ticker or "").strip().upper()

    @staticmethod
    def number(value: Any) -> float | None:
        if value in (None, ""):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @classmethod
    def integer(cls, value: Any) -> int | None:
        number = cls.number(value)
        return int(number) if number is not None else None

    @staticmethod
    def bool_or_none(value: Any) -> bool | None:
        if value in (None, ""):
            return None
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value > 0
        return str(value).strip().lower() in {"1", "true", "yes", "y", "positive", "buying"}

    @staticmethod
    def list_value(value: Any) -> list[str]:
        if value in (None, ""):
            return []
        if isinstance(value, (list, tuple)):
            return [str(item) for item in value]
        return [item.strip() for item in str(value).split(",") if item.strip()]
