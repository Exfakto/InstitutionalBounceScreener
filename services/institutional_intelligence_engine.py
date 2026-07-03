"""
Deterministic institutional ownership and flow intelligence engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite

from database.institutional_data import InstitutionalData
from services.institutional_intelligence_service import (
    InstitutionalIntelligenceService,
    InstitutionalScoreResult,
)


@dataclass(frozen=True)
class InstitutionalActivity:
    ownership_pct: float | None = None
    ownership_change_qoq: float | None = None
    net_buying: float | None = None
    holders_count: int | None = None
    holders_change: int | None = None
    recent_13f_activity: str | None = None
    major_buyers: list[str] = field(default_factory=list)
    major_sellers: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class InsiderActivity:
    insider_buying: bool | None = None
    insider_selling: bool | None = None
    insider_net_activity: float | str | None = None


@dataclass(frozen=True)
class InstitutionalIntelligenceResult:
    ticker: str | None
    institutional_activity: InstitutionalActivity
    insider_activity: InsiderActivity
    institutional_score: float
    sponsorship_rating: str
    flow_rating: str
    insider_rating: str
    final_outlook: str
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class InstitutionalSignal:
    ticker: str
    raw_institutional_data: InstitutionalData | None
    score_result: InstitutionalScoreResult
    as_of_date: str | None = None
    source: str | None = None
    warnings: list[str] = field(default_factory=list)


class InstitutionalIntelligenceEngine:
    """
    Score institutional sponsorship, fund flow, and insider activity.
    """

    def __init__(self, provider=None, scoring_service=None):
        self.provider = provider
        self.scoring_service = scoring_service or InstitutionalIntelligenceService()

    def score_ticker(self, ticker):
        normalized = self.normalize_ticker(ticker)
        if normalized is None:
            raw_data = None
            score_result = self.scoring_service.calculate()
            return InstitutionalSignal(
                ticker="",
                raw_institutional_data=raw_data,
                score_result=score_result,
                warnings=["Missing ticker", *score_result.warnings],
            )

        self.require_provider()
        raw_data = self.provider.fetch_for_ticker(normalized)
        return self.build_signal(normalized, raw_data)

    def score_tickers(self, tickers):
        normalized = [
            value
            for value in (self.normalize_ticker(ticker) for ticker in (tickers or []))
            if value is not None
        ]
        if not normalized:
            return {}

        self.require_provider()
        raw_records = self.provider.fetch_for_tickers(normalized) or {}
        return {
            ticker: self.build_signal(ticker, raw_records.get(ticker))
            for ticker in normalized
        }

    def build_signal(self, ticker, raw_data):
        score_result = self.scoring_service.calculate_from_record(raw_data)
        warnings = [*self.missing_field_warnings(raw_data), *score_result.warnings]

        return InstitutionalSignal(
            ticker=ticker,
            raw_institutional_data=raw_data,
            score_result=score_result,
            as_of_date=self.value(raw_data, "as_of_date"),
            source=self.value(raw_data, "source"),
            warnings=self.unique_warnings(warnings),
        )

    def require_provider(self):
        if self.provider is None:
            raise ValueError("InstitutionalIntelligenceEngine requires an institutional data provider.")

    @staticmethod
    def missing_field_warnings(raw_data):
        if raw_data is None:
            return ["Missing institutional data"]

        fields = {
            "institutional_ownership_pct": "Missing institutional ownership",
            "institutional_ownership_change_qoq": "Missing institutional ownership trend",
            "net_institutional_buying": "Missing net institutional buying",
            "insider_buying_flag": "Missing insider buying flag",
            "insider_selling_flag": "Missing insider selling flag",
        }
        return [
            message
            for field, message in fields.items()
            if InstitutionalIntelligenceEngine.value(raw_data, field) in (None, "")
        ]

    @staticmethod
    def normalize_ticker(ticker):
        value = str(ticker or "").strip().upper()
        return value or None

    @staticmethod
    def unique_warnings(warnings):
        unique = []
        for warning in warnings:
            if warning and warning not in unique:
                unique.append(warning)
        return unique

    def analyze(self, candidate=None, **overrides):
        source = dict(overrides)
        ticker = self.first_existing(self.value(candidate, "ticker"), source.get("ticker"))

        activity = InstitutionalActivity(
            ownership_pct=self.number(self.first_value(candidate, source, [
                "institutional_ownership_pct",
                "institutional_ownership",
            ])),
            ownership_change_qoq=self.number(self.first_value(candidate, source, [
                "institutional_ownership_change_qoq",
                "ownership_change_qoq",
            ])),
            net_buying=self.number(self.first_value(candidate, source, [
                "net_institutional_buying",
                "13f_net_change",
                "thirteen_f_net_change",
            ])),
            holders_count=self.integer(self.first_value(candidate, source, [
                "institutional_holders",
                "holder_count",
                "holders",
            ])),
            holders_change=self.integer(self.first_value(candidate, source, [
                "institutional_holders_change",
                "holder_change",
                "holders_change_qoq",
            ])),
            recent_13f_activity=self.text(self.first_value(candidate, source, [
                "recent_13f_accumulation",
                "13f_accumulation",
                "recent_13f_activity",
                "13f_status",
            ])),
            major_buyers=self.list_value(self.first_value(candidate, source, [
                "major_buyers",
                "top_buyers",
                "institutional_buyers",
            ])),
            major_sellers=self.list_value(self.first_value(candidate, source, [
                "major_sellers",
                "top_sellers",
                "institutional_sellers",
            ])),
        )
        insider = InsiderActivity(
            insider_buying=self.bool_or_none(self.first_value(candidate, source, [
                "insider_buying",
                "insider_buying_flag",
                "insider_buying_score",
            ])),
            insider_selling=self.bool_or_none(self.first_value(candidate, source, [
                "insider_selling",
                "insider_selling_flag",
                "insider_selling_score",
            ])),
            insider_net_activity=self.first_value(candidate, source, [
                "insider_net_activity",
                "net_insider_activity",
                "insider_net_buying",
            ]),
        )

        warnings = []
        score = self.score(activity, insider, warnings)
        sponsorship = self.sponsorship_rating(activity)
        flow = self.flow_rating(activity)
        insider_rating = self.insider_rating(insider)
        outlook = self.final_outlook(sponsorship, flow, insider_rating)

        return InstitutionalIntelligenceResult(
            ticker=ticker,
            institutional_activity=activity,
            insider_activity=insider,
            institutional_score=score,
            sponsorship_rating=sponsorship,
            flow_rating=flow,
            insider_rating=insider_rating,
            final_outlook=outlook,
            warnings=warnings,
        )

    def score(self, activity, insider, warnings):
        parts = []
        if activity.ownership_pct is not None:
            parts.append(min(100.0, max(0.0, activity.ownership_pct / 75 * 100)) * 0.35)
        if activity.ownership_change_qoq is not None:
            parts.append(self.directional_score(activity.ownership_change_qoq, 5.0) * 0.15)
        if activity.net_buying is not None:
            parts.append(self.directional_score(activity.net_buying, 500_000_000) * 0.2)
        if activity.holders_change is not None:
            parts.append(self.directional_score(activity.holders_change, 100) * 0.1)
        activity_text = (activity.recent_13f_activity or "").lower()
        if activity_text:
            parts.append(self.text_flow_score(activity_text) * 0.1)
        insider_score = self.insider_score(insider)
        if insider_score is not None:
            parts.append(insider_score * 0.1)

        if not parts:
            warnings.append("Missing institutional data")
            return 0.0
        return min(100.0, max(0.0, sum(parts) / min(1.0, self.weight_sum(parts))))

    @staticmethod
    def weight_sum(parts):
        return 1.0 if parts else 0.0

    @staticmethod
    def directional_score(value, scale):
        bounded = max(-1.0, min(1.0, value / scale))
        return (bounded + 1) * 50

    @staticmethod
    def text_flow_score(text):
        if any(word in text for word in ("strong", "accumulation", "buying", "positive")):
            return 85.0
        if any(word in text for word in ("distribution", "selling", "negative")):
            return 20.0
        return 50.0

    def sponsorship_rating(self, activity):
        if activity.ownership_pct is None:
            return "Unknown"
        if activity.ownership_pct >= 60:
            return "Strong"
        if activity.ownership_pct >= 35:
            return "Moderate"
        return "Weak"

    def flow_rating(self, activity):
        values = [
            activity.ownership_change_qoq,
            activity.net_buying,
            activity.holders_change,
        ]
        if activity.recent_13f_activity:
            text_score = self.text_flow_score(activity.recent_13f_activity.lower())
            values.append(text_score - 50)
        numeric = [value for value in values if value is not None]
        if not numeric:
            return "Unknown"
        positives = sum(1 for value in numeric if value > 0)
        negatives = sum(1 for value in numeric if value < 0)
        if positives > negatives:
            return "Accumulation"
        if negatives > positives:
            return "Distribution"
        return "Neutral"

    def insider_rating(self, insider):
        if insider.insider_buying is None and insider.insider_selling is None and insider.insider_net_activity in (None, ""):
            return "Unknown"
        net = self.number(insider.insider_net_activity)
        if insider.insider_buying or (net is not None and net > 0):
            return "Positive"
        if insider.insider_selling or (net is not None and net < 0):
            return "Negative"
        return "Neutral"

    @staticmethod
    def insider_score(insider):
        if insider.insider_buying:
            return 85.0
        if insider.insider_selling:
            return 20.0
        net = InstitutionalIntelligenceEngine.number(insider.insider_net_activity)
        if net is None:
            return None
        return 75.0 if net > 0 else 25.0 if net < 0 else 50.0

    @staticmethod
    def final_outlook(sponsorship, flow, insider):
        if sponsorship == "Unknown" and flow == "Unknown" and insider == "Unknown":
            return "Unknown"
        if flow == "Distribution" or (sponsorship == "Weak" and insider == "Negative"):
            return "Distribution"
        if sponsorship == "Strong" and flow == "Accumulation":
            return "Strong Accumulation"
        if flow == "Accumulation" or sponsorship == "Strong":
            return "Accumulation"
        return "Neutral"

    @staticmethod
    def first_value(candidate, source, keys):
        values = [source.get(key) for key in keys]
        values.extend(InstitutionalIntelligenceEngine.value(candidate, key) for key in keys)
        metrics = InstitutionalIntelligenceEngine.value(candidate, "metrics")
        if isinstance(metrics, dict):
            values.extend(metrics.get(key) for key in keys)
        return InstitutionalIntelligenceEngine.first_existing(*values)

    @staticmethod
    def value(source, key):
        if source is None:
            return None
        if isinstance(source, dict):
            return source.get(key)
        return getattr(source, key, None)

    @staticmethod
    def first_existing(*values):
        for value in values:
            if value not in (None, ""):
                return value
        return None

    @staticmethod
    def number(value):
        if value in (None, ""):
            return None
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        return number if isfinite(number) else None

    @staticmethod
    def integer(value):
        number = InstitutionalIntelligenceEngine.number(value)
        return int(number) if number is not None else None

    @staticmethod
    def bool_or_none(value):
        if value in (None, ""):
            return None
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value > 0
        return str(value).strip().lower() in {"1", "true", "yes", "y", "positive", "buying"}

    @staticmethod
    def list_value(value):
        if value in (None, ""):
            return []
        if isinstance(value, (list, tuple)):
            return [str(item) for item in value]
        return [item.strip() for item in str(value).split(",") if item.strip()]

    @staticmethod
    def text(value):
        return None if value in (None, "") else str(value)
