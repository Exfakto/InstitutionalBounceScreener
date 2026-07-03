"""
Candidate ranking engine for Institutional Bounce decision support.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from services.institutional_bounce_scoring_engine import (
    InstitutionalBounceScoringEngine,
)

MINIMUM_CANDIDATE_SCORE = 60.0
GRADE_A_PLUS_THRESHOLD = 90.0
GRADE_A_THRESHOLD = 80.0
GRADE_B_THRESHOLD = 70.0
GRADE_C_THRESHOLD = 60.0
GRADE_D_THRESHOLD = 50.0


@dataclass(frozen=True)
class RankedCandidate:
    rank: int
    ticker: str
    final_score: float
    signal: str = ""
    opportunity_rating: str = ""
    risk_rating: str = ""
    explanation: str | list[str] = ""
    category_scores: dict = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    source: object | None = None
    grade: str = "REJECT"
    confidence_level: str = "LOW"
    setup_label: str = "Rejected"
    rejection_reasons: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class CandidateRankingResult:
    ranked_candidates: list[RankedCandidate] = field(default_factory=list)
    rejected_candidates: list[RankedCandidate] = field(default_factory=list)
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
                grade=item.grade,
                confidence_level=item.confidence_level,
                setup_label=item.setup_label,
                rejection_reasons=item.rejection_reasons,
            )
            for index, item in enumerate(ranked)
        ]
        return CandidateRankingResult(ranked_candidates=ranked, warnings=warnings)

    def rank_composite_scores(
        self,
        scores,
        minimum_score=MINIMUM_CANDIDATE_SCORE,
        allow_low_confidence=False,
    ):
        if not scores:
            return CandidateRankingResult(warnings=["No composite scores provided"])

        accepted = []
        rejected = []
        warnings = []

        for score in scores:
            ticker = str(self.first_existing(self.value(score, "ticker"), "N/A"))
            final_score = self.clamp(self.value(score, "final_score"))
            confidence = str(self.first_existing(self.value(score, "confidence_level"), "LOW")).upper()
            score_warnings = list(self.value(score, "warnings") or [])
            explanation = list(self.value(score, "explanation") or [])
            reasons = self.rejection_reasons(
                final_score,
                confidence,
                minimum_score,
                allow_low_confidence,
            )
            ranked = RankedCandidate(
                rank=0,
                ticker=ticker,
                final_score=final_score,
                signal=self.signal_label(final_score, "Unknown"),
                opportunity_rating=self.opportunity_rating(final_score),
                risk_rating="Unknown",
                explanation=explanation,
                category_scores={
                    "support_score": self.clamp(self.value(score, "support_score")),
                    "bounce_score": self.clamp(self.value(score, "bounce_score")),
                    "technical_score": self.clamp(self.value(score, "technical_score")),
                    "institutional_score": self.clamp(self.value(score, "institutional_score")),
                },
                warnings=score_warnings,
                source=score,
                grade=self.grade(final_score) if not reasons else "REJECT",
                confidence_level=confidence,
                setup_label=self.setup_label(final_score, confidence, rejected=bool(reasons)),
                rejection_reasons=reasons,
            )
            warnings.extend(score_warnings)
            if reasons:
                rejected.append(ranked)
            else:
                accepted.append(ranked)

        accepted.sort(key=lambda item: (-item.final_score, item.ticker))
        rejected.sort(key=lambda item: (-item.final_score, item.ticker))

        accepted = [self.replace_rank(item, index + 1) for index, item in enumerate(accepted)]
        return CandidateRankingResult(
            ranked_candidates=accepted,
            rejected_candidates=rejected,
            warnings=warnings,
        )

    @staticmethod
    def rejection_reasons(final_score, confidence_level, minimum_score, allow_low_confidence):
        reasons = []
        if final_score < minimum_score:
            reasons.append(f"Final score below minimum threshold ({minimum_score:.0f})")
        if confidence_level == "LOW" and not allow_low_confidence:
            reasons.append("Low confidence candidates are rejected")
        return reasons

    @staticmethod
    def replace_rank(item, rank):
        return RankedCandidate(
            rank=rank,
            ticker=item.ticker,
            final_score=item.final_score,
            signal=item.signal,
            opportunity_rating=item.opportunity_rating,
            risk_rating=item.risk_rating,
            explanation=item.explanation,
            category_scores=item.category_scores,
            warnings=item.warnings,
            source=item.source,
            grade=item.grade,
            confidence_level=item.confidence_level,
            setup_label=item.setup_label,
            rejection_reasons=item.rejection_reasons,
        )

    @staticmethod
    def grade(final_score):
        if final_score >= GRADE_A_PLUS_THRESHOLD:
            return "A+"
        if final_score >= GRADE_A_THRESHOLD:
            return "A"
        if final_score >= GRADE_B_THRESHOLD:
            return "B"
        if final_score >= GRADE_C_THRESHOLD:
            return "C"
        if final_score >= GRADE_D_THRESHOLD:
            return "D"
        return "REJECT"

    @staticmethod
    def setup_label(final_score, confidence_level, rejected=False):
        if rejected:
            return "Rejected"
        if final_score >= GRADE_A_PLUS_THRESHOLD and confidence_level == "HIGH":
            return "Elite Institutional Bounce"
        if final_score >= GRADE_A_THRESHOLD:
            return "High-Quality Bounce"
        if final_score >= GRADE_B_THRESHOLD:
            return "Watchlist Candidate"
        if final_score >= GRADE_C_THRESHOLD:
            return "Speculative / Low Conviction"
        return "Rejected"

    @staticmethod
    def opportunity_rating(final_score):
        if final_score >= GRADE_A_THRESHOLD:
            return "Strong"
        if final_score >= GRADE_B_THRESHOLD:
            return "Moderate"
        if final_score >= GRADE_C_THRESHOLD:
            return "Weak"
        return "Reject"

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

    @staticmethod
    def clamp(value):
        try:
            number = float(value)
        except (TypeError, ValueError):
            return 0.0
        return max(0.0, min(100.0, number))
