"""
Pure trade thesis generation for institutional bounce candidates.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from analysis.candidate_score import CandidateScore
from analysis.institutional_checklist import InstitutionalChecklistResult
from analysis.opportunity_rating import OpportunityRatingResult
from analysis.score_result import ScoreResult


@dataclass(frozen=True)
class TradeThesisResult:
    """
    Concise read-only trade thesis output.
    """

    title: str
    summary: str
    strengths: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    confidence: str = "Very Low"


class TradeThesisGenerator:
    """
    Generate a professional thesis from existing intelligence outputs.

    The generator does not calculate new scores or persist state. It only
    translates available metrics into deterministic decision-support prose.
    """

    def generate(self, source):
        metrics = self.metrics_from_source(source)
        ticker = metrics.get("ticker") or "Candidate"
        company_name = metrics.get("company_name")
        display_name = f"{ticker} ({company_name})" if company_name else ticker
        opportunity_label = self.opportunity_label(metrics.get("opportunity_rating"))
        score = self.metric(metrics, "institutional_bounce_score")
        checklist = metrics.get("institutional_checklist")

        strengths = self.strengths(metrics)
        risks = self.risks(metrics)
        confidence = self.confidence(metrics, strengths, risks)
        title = self.title(ticker, opportunity_label, confidence)
        summary = self.summary(
            display_name,
            metrics,
            opportunity_label,
            score,
            checklist,
            strengths,
            risks,
            confidence,
        )

        return TradeThesisResult(
            title=title,
            summary=summary,
            strengths=strengths,
            risks=risks,
            confidence=confidence,
        )

    def summary(
        self,
        display_name,
        metrics,
        opportunity_label,
        score,
        checklist,
        strengths,
        risks,
        confidence,
    ):
        sentences = []
        setup_parts = []
        distance = self.metric(metrics, "distance_to_support_pct")
        bounce_success = self.metric(metrics, "bounce_success_rate")

        if distance is not None:
            setup_parts.append(
                f"is trading {self.format_number(distance)}% above a validated "
                "institutional support zone"
            )

        if bounce_success is not None:
            setup_parts.append(
                f"has a {self.format_number(bounce_success)}% historical bounce "
                "success rate"
            )

        if setup_parts:
            sentences.append(f"{display_name} {' and '.join(setup_parts)}.")
        elif score is not None:
            sentences.append(
                f"{display_name} has an institutional bounce score of "
                f"{self.format_number(score)}."
            )
        else:
            sentences.append(
                f"{display_name} has insufficient available data for a complete "
                "institutional bounce thesis."
            )

        if strengths:
            sentences.append(self.strength_sentence(strengths))

        risk_sentence = self.risk_sentence(risks)
        if risk_sentence:
            sentences.append(risk_sentence)

        conclusion_parts = []
        if opportunity_label:
            conclusion_parts.append(f"a {opportunity_label} setup")
        if checklist is not None:
            conclusion_parts.append(
                f"a {self.format_number(checklist.overall_percentage)}% "
                f"{checklist.overall_label} checklist"
            )

        if conclusion_parts:
            sentences.append(
                f"Overall, the evidence supports {' with '.join(conclusion_parts)} "
                f"and {confidence.lower()} confidence."
            )
        else:
            sentences.append(
                f"Overall confidence is {confidence.lower()} until more evidence is "
                "available."
            )

        return " ".join(sentences[:5])

    @staticmethod
    def title(ticker, opportunity_label, confidence):
        if opportunity_label:
            return f"{ticker} {opportunity_label} Trade Thesis"

        return f"{ticker} Trade Thesis - {confidence} Confidence"

    def strengths(self, metrics):
        strengths = []

        if self.metric(metrics, "relative_strength_score") is not None:
            value = self.metric(metrics, "relative_strength_score")
            if value >= 75:
                strengths.append("Relative Strength remains favorable")

        if self.metric(metrics, "trend_score") is not None:
            value = self.metric(metrics, "trend_score")
            if value >= 70:
                strengths.append("Trend Strength remains favorable")

        if self.metric(metrics, "institutional_momentum_score") is not None:
            value = self.metric(metrics, "institutional_momentum_score")
            if value >= 70:
                strengths.append("institutional momentum is positive")

        if self.metric(metrics, "volume_score") is not None:
            value = self.metric(metrics, "volume_score")
            if value >= 70:
                strengths.append("volume accumulation is present")

        if self.metric(metrics, "support_score") is not None:
            value = self.metric(metrics, "support_score")
            if value >= 80:
                strengths.append("support quality is strong")

        if self.metric(metrics, "bounce_score") is not None:
            value = self.metric(metrics, "bounce_score")
            if value >= 80:
                strengths.append("bounce validation is strong")

        if self.metric(metrics, "average_bounce_pct") is not None:
            value = self.metric(metrics, "average_bounce_pct")
            if value >= 8:
                strengths.append(
                    f"average historical bounce is {self.format_number(value)}%"
                )

        return strengths

    def risks(self, metrics):
        risks = []
        earnings_risk = self.metric(metrics, "earnings_risk_score")
        trend = self.metric(metrics, "trend_score")
        risk_score = self.metric(metrics, "risk_score")
        distance = self.metric(metrics, "distance_to_support_pct")
        checklist = metrics.get("institutional_checklist")

        if earnings_risk is not None:
            if earnings_risk >= 70:
                risks.append("earnings risk is elevated")
            elif earnings_risk <= 35:
                risks.append("earnings are not an immediate risk")

        if trend is not None and trend < 50:
            risks.append("trend alignment is weak")

        if risk_score is not None and risk_score < 50:
            risks.append("ATR risk is unfavorable")

        if distance is not None and distance > 10:
            risks.append("price is extended above support")

        if checklist is not None:
            for check in checklist.warning_checks + checklist.failed_checks:
                if check.message not in risks:
                    risks.append(check.message)

        warnings = metrics.get("warnings") or []
        for warning in warnings:
            if warning not in risks:
                risks.append(warning)

        return risks

    @staticmethod
    def strength_sentence(strengths):
        if len(strengths) == 1:
            return f"{strengths[0].capitalize()}."

        return (
            f"{', '.join(strengths[:-1]).capitalize()}, while "
            f"{strengths[-1]}."
        )

    @staticmethod
    def risk_sentence(risks):
        if not risks:
            return ""

        first_risks = risks[:2]

        if len(first_risks) == 1:
            return f"Key risk: {first_risks[0]}."

        return f"Key risks: {first_risks[0]} and {first_risks[1]}."

    def confidence(self, metrics, strengths, risks):
        evidence_count = self.evidence_count(metrics)
        opportunity_score = self.opportunity_score(metrics.get("opportunity_rating"))
        institutional_score = self.metric(metrics, "institutional_bounce_score")
        checklist = metrics.get("institutional_checklist")
        checklist_percentage = (
            checklist.overall_percentage
            if isinstance(checklist, InstitutionalChecklistResult)
            else None
        )
        score_values = [
            value
            for value in [
                opportunity_score,
                institutional_score,
                checklist_percentage,
            ]
            if value is not None
        ]
        base_score = sum(score_values) / len(score_values) if score_values else 0.0
        risk_penalty = max(0, len([risk for risk in risks if "not an immediate" not in risk]) - 1) * 5
        evidence_penalty = max(0, 8 - evidence_count) * 4
        adjusted_score = max(0.0, base_score - risk_penalty - evidence_penalty)

        if adjusted_score >= 90 and evidence_count >= 8:
            return "Very High"
        if adjusted_score >= 80 and evidence_count >= 6:
            return "High"
        if adjusted_score >= 65 and evidence_count >= 4:
            return "Moderate"
        if adjusted_score >= 45 and evidence_count >= 2:
            return "Low"
        return "Very Low"

    @staticmethod
    def evidence_count(metrics):
        evidence_names = [
            "institutional_bounce_score",
            "relative_strength_score",
            "trend_score",
            "support_score",
            "bounce_score",
            "volume_score",
            "institutional_momentum_score",
            "earnings_risk_score",
            "risk_score",
            "distance_to_support_pct",
            "bounce_success_rate",
            "average_bounce_pct",
        ]

        return sum(1 for name in evidence_names if metrics.get(name) is not None)

    def metrics_from_source(self, source):
        if isinstance(source, CandidateScore):
            metrics = {
                "ticker": source.ticker,
                "institutional_bounce_score": source.institutional_bounce_score,
                "institutional_checklist": source.institutional_checklist,
                "warnings": list(source.warnings),
            }
            metrics.update(source.composite_intelligence_component_scores)
            metrics.update({
                score.name: score.value
                for score in source.scores
            })
            return metrics

        return dict(source or {})

    @staticmethod
    def metric(metrics, name):
        value = metrics.get(name)

        if isinstance(value, ScoreResult):
            value = value.value

        if value is None:
            return None

        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def opportunity_label(value):
        if isinstance(value, OpportunityRatingResult):
            return value.rating_label

        if isinstance(value, dict):
            return value.get("rating_label") or value.get("label")

        if isinstance(value, str):
            return value

        return None

    def opportunity_score(self, value):
        if isinstance(value, OpportunityRatingResult):
            return value.rating_score

        if isinstance(value, dict):
            score = value.get("rating_score") or value.get("score")
            try:
                return float(score)
            except (TypeError, ValueError):
                return None

        return self.metric({"opportunity_rating": value}, "opportunity_rating")

    @staticmethod
    def format_number(value):
        number = float(value)

        if number.is_integer():
            return f"{number:.0f}"

        return f"{number:.1f}"
