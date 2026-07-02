from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any


@dataclass(frozen=True)
class WatchlistIntelligenceResult:
    """
    Deterministic health summary for an existing watchlist snapshot.
    """

    total_items: int
    ready_count: int
    watching_count: int
    rejected_count: int
    high_conviction_count: int
    average_opportunity_score: float | None
    top_candidates: list[dict[str, Any]] = field(default_factory=list)
    weak_candidates: list[dict[str, Any]] = field(default_factory=list)
    stale_items: list[dict[str, Any]] = field(default_factory=list)
    warning_count: int = 0
    summary: str = ""
    warnings: list[str] = field(default_factory=list)


class WatchlistIntelligenceAnalyzer:
    """
    Summarize watchlist quality from already-available watchlist/candidate fields.
    """

    STALE_DAYS = 7
    HIGH_CONVICTION_SCORE = 85.0
    WEAK_SCORE = 55.0

    def analyze(self, items: list[Any] | tuple[Any, ...] | None) -> WatchlistIntelligenceResult:
        normalized_items = [self.normalize_item(item) for item in items or []]
        valid_items = [item for item in normalized_items if item]
        total_items = len(valid_items)

        ready_count = self.count_status(valid_items, "ready")
        watching_count = self.count_status(valid_items, "watching")
        rejected_count = self.count_status(valid_items, "rejected")
        scored_items = [
            (item, score)
            for item in valid_items
            if (score := self.opportunity_score(item)) is not None
        ]
        average_opportunity_score = self.average_score(scored_items)
        top_candidates = self.top_candidates(scored_items)
        weak_candidates = self.weak_candidates(scored_items)
        stale_items = self.stale_items(valid_items)
        warnings = self.warning_messages(valid_items)
        high_conviction_count = sum(
            1
            for item, score in scored_items
            if score >= self.HIGH_CONVICTION_SCORE
            or self.is_high_confidence(item.get("confidence"))
        )

        return WatchlistIntelligenceResult(
            total_items=total_items,
            ready_count=ready_count,
            watching_count=watching_count,
            rejected_count=rejected_count,
            high_conviction_count=high_conviction_count,
            average_opportunity_score=average_opportunity_score,
            top_candidates=top_candidates,
            weak_candidates=weak_candidates,
            stale_items=stale_items,
            warning_count=len(warnings),
            summary=self.summary(
                total_items,
                ready_count,
                watching_count,
                rejected_count,
                high_conviction_count,
                average_opportunity_score,
                len(stale_items),
                len(warnings),
            ),
            warnings=warnings,
        )

    @classmethod
    def top_candidates(cls, scored_items: list[tuple[dict[str, Any], float]]) -> list[dict[str, Any]]:
        ranked = sorted(
            scored_items,
            key=lambda item_score: (-item_score[1], cls.ticker(item_score[0])),
        )
        return [cls.candidate_summary(item, score) for item, score in ranked[:5]]

    @classmethod
    def weak_candidates(cls, scored_items: list[tuple[dict[str, Any], float]]) -> list[dict[str, Any]]:
        weak = [
            (item, score)
            for item, score in scored_items
            if score < cls.WEAK_SCORE
        ]
        ranked = sorted(weak, key=lambda item_score: (item_score[1], cls.ticker(item_score[0])))
        return [cls.candidate_summary(item, score) for item, score in ranked[:5]]

    @classmethod
    def stale_items(cls, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        dated_items = [
            (item, updated_at)
            for item in items
            if (updated_at := cls.parse_date(item.get("updated_at"))) is not None
        ]
        if not dated_items:
            return []

        latest = max(updated_at for _, updated_at in dated_items)
        stale = [
            (item, updated_at)
            for item, updated_at in dated_items
            if (latest - updated_at).days > cls.STALE_DAYS
        ]
        return [
            cls.item_summary(item, extra={"updated_at": item.get("updated_at")})
            for item, _ in sorted(stale, key=lambda pair: (pair[1], cls.ticker(pair[0])))
        ]

    @classmethod
    def warning_messages(cls, items: list[dict[str, Any]]) -> list[str]:
        messages = []
        for item in items:
            ticker = cls.ticker(item)
            for warning in cls.as_list(item.get("warnings")):
                if not warning:
                    continue
                message = f"{ticker}: {warning}" if ticker != "Unknown" else str(warning)
                if message not in messages:
                    messages.append(message)
        return messages

    @classmethod
    def candidate_summary(cls, item: dict[str, Any], score: float) -> dict[str, Any]:
        summary = cls.item_summary(item, extra={"opportunity_score": round(score, 1)})

        for key in [
            "overall_score",
            "quality_score",
            "technical_score",
            "institutional_score",
            "risk_reward",
            "confidence",
            "last_price",
            "percent_change",
        ]:
            if item.get(key) is not None:
                summary[key] = item[key]

        return summary

    @classmethod
    def item_summary(
        cls,
        item: dict[str, Any],
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        summary = {"ticker": cls.ticker(item)}
        if item.get("company_name"):
            summary["company_name"] = item["company_name"]
        if item.get("status"):
            summary["status"] = item["status"]
        if extra:
            summary.update(extra)
        return summary

    @staticmethod
    def summary(
        total_items: int,
        ready_count: int,
        watching_count: int,
        rejected_count: int,
        high_conviction_count: int,
        average_opportunity_score: float | None,
        stale_count: int,
        warning_count: int,
    ) -> str:
        if total_items == 0:
            return "Watchlist is empty; no opportunity or health metrics are available."

        parts = [
            f"Watchlist contains {total_items} item(s)",
            f"{ready_count} ready",
            f"{watching_count} watching",
            f"{rejected_count} rejected",
            f"{high_conviction_count} high-conviction candidate(s)",
        ]
        if average_opportunity_score is not None:
            parts.append(f"average opportunity score {average_opportunity_score:.1f}")
        if stale_count:
            parts.append(f"{stale_count} stale item(s)")
        if warning_count:
            parts.append(f"{warning_count} warning(s)")

        return "; ".join(parts) + "."

    @classmethod
    def opportunity_score(cls, item: dict[str, Any]) -> float | None:
        rating = item.get("opportunity_rating")
        if isinstance(rating, dict):
            value = rating.get("rating_score") or rating.get("score")
            score = cls.safe_float(value)
            if score is not None:
                return score

        score = cls.safe_float(rating)
        if score is not None:
            return score

        return cls.first_number(item, "overall_score", "quality_score")

    @classmethod
    def average_score(cls, scored_items: list[tuple[dict[str, Any], float]]) -> float | None:
        if not scored_items:
            return None
        return round(sum(score for _, score in scored_items) / len(scored_items), 1)

    @classmethod
    def count_status(cls, items: list[dict[str, Any]], status: str) -> int:
        return sum(1 for item in items if cls.normalized_status(item.get("status")) == status)

    @classmethod
    def normalize_item(cls, item: Any) -> dict[str, Any]:
        if item is None:
            return {}
        if isinstance(item, dict):
            return dict(item)
        if hasattr(item, "_asdict"):
            return dict(item._asdict())
        if hasattr(item, "__dict__"):
            return dict(vars(item))
        return {}

    @staticmethod
    def normalized_status(value: Any) -> str:
        return str(value or "").strip().lower()

    @staticmethod
    def is_high_confidence(value: Any) -> bool:
        return str(value or "").strip().lower() in {"high", "very high"}

    @staticmethod
    def ticker(item: dict[str, Any]) -> str:
        ticker = str(item.get("ticker") or "").strip().upper()
        return ticker or "Unknown"

    @classmethod
    def first_number(cls, item: dict[str, Any], *keys: str) -> float | None:
        for key in keys:
            value = cls.safe_float(item.get(key))
            if value is not None:
                return value
        return None

    @staticmethod
    def safe_float(value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def parse_date(value: Any) -> date | None:
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        if value is None:
            return None

        text = str(value).strip()
        if not text:
            return None

        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
        except ValueError:
            try:
                return date.fromisoformat(text[:10])
            except ValueError:
                return None

    @staticmethod
    def as_list(value: Any) -> list[Any]:
        if value is None:
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, tuple):
            return list(value)
        return [value]
