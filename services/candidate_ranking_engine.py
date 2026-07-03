"""
Candidate ranking engine for Institutional Bounce decision support.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from services.institutional_bounce_scoring_engine import (
    InstitutionalBounceScoringEngine,
)


@dataclass(frozen=True)
class RankedCandidate:
    rank: int
    ticker: str
    final_score: float
    signal: str
    opportunity_rating: str
    risk_rating: str
    explanation: str
    category_scores: dict
    warnings: list[str] = field(default_factory=list)
    source: object | None = None


@dataclass(frozen=True)
class CandidateRankingResult:
    ranked_candidates: list[RankedCandidate] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class CandidateRankingEngine:
    def __init__(self, scoring_engine=None):
        self.scoring_engine = scoring_engine or InstitutionalBounceScoringEngine()

    def rank_candidates(self, candidates):
        if not candidates:
            return CandidateRankingResult(warnings=["No candidates provided"])

        ranked = []
        warnings = []
        for candidate in candidates:
            score_result = self.scoring_engine.score(candidate)
            ticker = self.first_existing(self.value(candidate, "ticker"), score_result.ticker, "N/A")
            category_scores = {
                "fundamental_quality_score": score_result.fundamental_quality_score,
                "institutional_sponsorship_score": score_result.institutional_sponsorship_score,
                "support_strength_score": score_result.support_strength_score,
                "bounce_history_score": score_result.bounce_history_score,
                "relative_strength_score": score_result.relative_strength_score,
                "volume_accumulation_score": score_result.volume_accumulation_score,
                "risk_penalty_score": score_result.risk_penalty_score,
            }
            ranked.append(
                RankedCandidate(
                    rank=0,
                    ticker=str(ticker),
                    final_score=score_result.final_score,
                    signal=self.signal_label(score_result.final_score, score_result.risk_rating),
                    opportunity_rating=score_result.opportunity_rating,
                    risk_rating=score_result.risk_rating,
                    explanation=score_result.explanation,
                    category_scores=category_scores,
                    warnings=score_result.warnings,
                    source=candidate,
                )
            )
            warnings.extend(score_result.warnings)

        ranked.sort(key=lambda item: (-item.final_score, item.ticker))
        ranked = [
            RankedCandidate(
                rank=index + 1,
                ticker=item.ticker,
                final_score=item.final_score,
                signal=item.signal,
                opportunity_rating=item.opportunity_rating,
                risk_rating=item.risk_rating,
                explanation=item.explanation,
                category_scores=item.category_scores,
                warnings=item.warnings,
                source=item.source,
            )
            for index, item in enumerate(ranked)
        ]
        return CandidateRankingResult(ranked_candidates=ranked, warnings=warnings)

    @staticmethod
    def signal_label(final_score, risk_rating):
        high_risk = str(risk_rating or "").lower() == "high"
        if final_score >= 90 and not high_risk:
            return "Strong Buy"
        if final_score >= 80 and high_risk:
            return "Buy"
        if final_score >= 80 and not high_risk:
            return "Buy"
        if final_score >= 70 or high_risk and final_score >= 60:
            return "Watch"
        if final_score >= 60:
            return "Wait"
        return "Avoid"

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
