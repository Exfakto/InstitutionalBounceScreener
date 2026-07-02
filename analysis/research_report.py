from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from analysis.candidate_score import CandidateScore
from analysis.institutional_checklist import InstitutionalChecklistResult
from analysis.opportunity_rating import OpportunityRatingResult
from analysis.score_result import ScoreResult
from analysis.trade_thesis import TradeThesisResult


@dataclass(frozen=True)
class ResearchReportResult:
    """
    Structured institutional bounce research report.
    """

    title: str
    executive_summary: str
    setup_quality: str
    technical_analysis: str
    fundamental_analysis: str
    institutional_analysis: str
    trade_plan: str
    risk_summary: str
    warnings: list[str] = field(default_factory=list)
    conclusion: str = ""
    confidence: str = "Low"


class ResearchReportGenerator:
    """
    Generate deterministic written reports from existing candidate analysis.
    """

    def generate(self, source: Any) -> ResearchReportResult:
        metrics = self.metrics_from_source(source)
        ticker = str(metrics.get("ticker") or "Candidate")
        company_name = metrics.get("company_name")
        opportunity = metrics.get("opportunity_rating")
        checklist = metrics.get("institutional_checklist")
        thesis = metrics.get("trade_thesis")
        warnings = self.warning_messages(metrics, opportunity, checklist, thesis)
        confidence = self.confidence(metrics, opportunity, checklist, thesis)
        title = self.title(ticker, company_name)

        return ResearchReportResult(
            title=title,
            executive_summary=self.executive_summary(
                ticker,
                company_name,
                metrics,
                opportunity,
                confidence,
            ),
            setup_quality=self.setup_quality(metrics, opportunity, checklist),
            technical_analysis=self.technical_analysis(metrics),
            fundamental_analysis=self.fundamental_analysis(metrics),
            institutional_analysis=self.institutional_analysis(metrics, checklist),
            trade_plan=self.trade_plan(metrics),
            risk_summary=self.risk_summary(metrics, warnings),
            warnings=warnings,
            conclusion=self.conclusion(ticker, opportunity, checklist, confidence, warnings),
            confidence=confidence,
        )

    @staticmethod
    def title(ticker: str, company_name: Any = None) -> str:
        if company_name:
            return f"{ticker} Institutional Bounce Research Report - {company_name}"

        return f"{ticker} Institutional Bounce Research Report"

    def executive_summary(
        self,
        ticker: str,
        company_name: Any,
        metrics: dict[str, Any],
        opportunity: Any,
        confidence: str,
    ) -> str:
        display_name = f"{ticker} ({company_name})" if company_name else ticker
        paragraphs = []
        rating_label = self.opportunity_label(opportunity)
        rating_score = self.opportunity_score(opportunity)
        overall_score = self.first_number(
            metrics,
            "overall_score",
            "institutional_bounce_score",
            "composite_intelligence_score",
            "composite_score",
        )

        opening = []
        if rating_label:
            opening.append(f"{display_name} is classified as {rating_label}")
        elif overall_score is not None:
            opening.append(
                f"{display_name} has an overall setup score of {self.format_number(overall_score)}"
            )
        else:
            opening.append(
                f"{display_name} has limited available data for a complete setup review"
            )

        if rating_score is not None:
            opening.append(f"the opportunity score is {self.format_number(rating_score)}")

        paragraphs.append(". ".join(part.rstrip(".") for part in opening) + ".")

        strengths = self.strongest_factors(metrics, opportunity)
        if strengths:
            paragraphs.append(
                "The strongest positive factors are "
                f"{self.join_phrases(strengths[:3])}, which improves the quality of the institutional bounce setup."
            )
        else:
            paragraphs.append(
                "The positive factor set is limited by the available inputs, so conviction depends on confirmed score evidence rather than assumed support."
            )

        risks = self.primary_risks(metrics, opportunity)
        if risks:
            paragraphs.append(
                "Primary risks are "
                f"{self.join_phrases(risks[:3])}, which should be weighed before sizing or timing any trade plan."
            )
        else:
            paragraphs.append(
                "Primary risk evidence is limited in the supplied analysis; no missing value is treated as favorable."
            )

        paragraphs.append(f"Report confidence is {confidence} based on available analysis completeness.")

        return "\n\n".join(paragraphs[:4])

    def setup_quality(self, metrics: dict[str, Any], opportunity: Any, checklist: Any) -> str:
        parts = []
        rating_label = self.opportunity_label(opportunity)
        rating_score = self.opportunity_score(opportunity)
        quality_score = self.first_number(metrics, "quality_score")
        checklist_percentage = (
            checklist.overall_percentage
            if isinstance(checklist, InstitutionalChecklistResult)
            else self.dict_value(checklist, "overall_percentage")
        )
        checklist_label = (
            checklist.overall_label
            if isinstance(checklist, InstitutionalChecklistResult)
            else self.dict_value(checklist, "overall_label")
        )

        if rating_label:
            parts.append(f"Opportunity rating: {rating_label}")
        if rating_score is not None:
            parts.append(f"opportunity score {self.format_number(rating_score)}")
        if quality_score is not None:
            parts.append(f"quality score {self.format_number(quality_score)}")
        if checklist_percentage is not None:
            checklist_text = f"checklist {self.format_number(checklist_percentage)}%"
            if checklist_label:
                checklist_text += f" ({checklist_label})"
            parts.append(checklist_text)

        return self.sentence_or_unavailable(parts, "Setup quality data is unavailable.")

    def technical_analysis(self, metrics: dict[str, Any]) -> str:
        parts = []
        for key, label in [
            ("support_score", "Support"),
            ("bounce_score", "Bounce Quality"),
            ("trend_score", "Trend"),
            ("relative_strength_score", "Relative Strength"),
            ("volume_score", "Volume"),
        ]:
            value = self.first_number(metrics, key)
            if value is not None:
                parts.append(f"{label}: {self.score_assessment(value)}")

        value = self.first_number(metrics, "technical_score")
        if value is not None:
            parts.insert(0, f"Technical score: {self.score_assessment(value)}")

        return self.sentence_or_unavailable(parts, "Technical analysis data is unavailable.")

    def fundamental_analysis(self, metrics: dict[str, Any]) -> str:
        parts = []
        for keys, label, suffix, kind in [
            (("revenue_growth", "revenue_growth_ttm"), "Revenue Growth", "%", "growth"),
            (("eps_growth", "eps_growth_ttm"), "EPS Growth", "%", "growth"),
            (("roe",), "ROE", "%", "profitability"),
            (("gross_margin", "operating_margin", "net_margin"), "Margins", "%", "profitability"),
            (("free_cash_flow", "operating_cash_flow"), "Cash Flow", "", "currency"),
            (("debt_to_equity",), "Debt", "", "debt"),
            (("current_ratio",), "Current Ratio", "", "liquidity"),
            (("market_cap",), "Market Cap", "", "currency"),
        ]:
            value = self.first_number(metrics, *keys)
            if value is not None:
                formatted = (
                    self.format_currency(value)
                    if kind == "currency"
                    else f"{self.format_number(value)}{suffix}"
                )
                parts.append(f"{label}: {formatted} - {self.fundamental_assessment(kind, value)}")

        return self.sentence_or_unavailable(parts, "Fundamental analysis data is unavailable.")

    def institutional_analysis(self, metrics: dict[str, Any], checklist: Any) -> str:
        parts = []
        for keys, label, kind in [
            (("institutional_score",), "Institutional Score", "score"),
            (("institutional_ownership_pct",), "Ownership", "percent"),
            (("institutional_momentum_score", "accumulation_score"), "Accumulation", "score"),
            (("thirteen_f_net_change", "13f_net_change", "net_institutional_buying"), "13F", "currency"),
            (("insider_activity_score", "insider_net_buying"), "Insider Activity", "score"),
        ]:
            value = self.first_number(metrics, *keys)
            if value is not None:
                if kind == "currency":
                    formatted = self.format_currency(value)
                elif kind == "percent":
                    formatted = f"{self.format_number(value)}%"
                else:
                    formatted = self.format_number(value)
                parts.append(f"{label}: {formatted} - {self.institutional_assessment(kind, value)}")

        if isinstance(checklist, InstitutionalChecklistResult):
            parts.append(
                f"Checklist: {checklist.passed_count} of {checklist.total_checks} items passed ({checklist.overall_label})"
            )
        elif isinstance(checklist, dict):
            checklist_pct = self.dict_value(checklist, "overall_percentage")
            checklist_label = self.dict_value(checklist, "overall_label")
            if checklist_pct is not None:
                label = f" ({checklist_label})" if checklist_label else ""
                parts.append(f"Checklist: {self.format_number(checklist_pct)}%{label}")

        return self.sentence_or_unavailable(parts, "Institutional analysis data is unavailable.")

    def trade_plan(self, metrics: dict[str, Any]) -> str:
        parts = []
        for key, label in [
            ("entry_zone", "Entry"),
            ("stop_loss", "Stop"),
            ("target_projection", "Target"),
            ("risk_reward", "Risk/Reward"),
            ("position_size", "Position Size"),
        ]:
            value = metrics.get(key)
            if value is not None:
                parts.append(f"{label}: {self.format_value(value)}")

        return self.sentence_or_unavailable(parts, "Trade plan data is unavailable.")

    def risk_summary(self, metrics: dict[str, Any], warnings: list[str]) -> str:
        parts = []
        earnings = self.first_number(metrics, "earnings_risk_score")
        risk_reward = metrics.get("risk_reward")
        missing = self.missing_analysis(metrics)

        if earnings is not None:
            parts.append(f"Upcoming earnings risk score: {self.format_number(earnings)} - {self.earnings_risk_assessment(earnings)}")
        if risk_reward is not None:
            parts.append(f"Risk/reward: {self.format_value(risk_reward)}")
        if warnings:
            parts.append(f"Warnings: {self.join_phrases(warnings[:4])}")
        if missing:
            parts.append(f"Missing data: {self.join_phrases(missing)}")

        return self.sentence_or_unavailable(parts, "Risk data is unavailable.")

    def conclusion(
        self,
        ticker: str,
        opportunity: Any,
        checklist: Any,
        confidence: str,
        warnings: list[str],
    ) -> str:
        category = self.conclusion_category(opportunity, checklist, confidence, warnings)
        return (
            f"{ticker} conclusion: {category}. "
            "The category is derived from available scores and completeness only, and does not imply an investment guarantee."
        )

    def confidence(
        self,
        metrics: dict[str, Any],
        opportunity: Any,
        checklist: Any,
        thesis: Any,
    ) -> str:
        thesis_confidence = self.object_value(thesis, "confidence")
        if thesis_confidence:
            return str(thesis_confidence)

        checklist_percentage = (
            checklist.overall_percentage
            if isinstance(checklist, InstitutionalChecklistResult)
            else self.dict_value(checklist, "overall_percentage")
        )
        opportunity_score = self.opportunity_score(opportunity)
        overall_score = self.first_number(
            metrics,
            "overall_score",
            "institutional_bounce_score",
            "composite_intelligence_score",
            "composite_score",
        )
        values = [
            value
            for value in [checklist_percentage, opportunity_score, overall_score]
            if value is not None
        ]

        if not values:
            return "Low"

        average = sum(values) / len(values)
        completeness = self.analysis_completeness(metrics)

        if average >= 85 and completeness >= 0.75:
            return "Very High"
        if average >= 75 and completeness >= 0.55:
            return "High"
        if average >= 55 and completeness >= 0.35:
            return "Moderate"
        return "Low"

    def warning_messages(
        self,
        metrics: dict[str, Any],
        opportunity: Any,
        checklist: Any,
        thesis: Any,
    ) -> list[str]:
        warnings = []
        warnings.extend(self.as_list(metrics.get("warnings")))
        warnings.extend(self.as_list(self.object_value(opportunity, "warnings")))

        if isinstance(checklist, InstitutionalChecklistResult):
            warnings.extend(check.message for check in checklist.warning_checks)
            warnings.extend(check.message for check in checklist.failed_checks)

        warnings.extend(self.as_list(self.object_value(thesis, "risks")))

        deduped = []
        for warning in warnings:
            if warning and warning not in deduped:
                deduped.append(str(warning))

        return deduped

    def metrics_from_source(self, source: Any) -> dict[str, Any]:
        if isinstance(source, CandidateScore):
            metrics = {
                "ticker": source.ticker,
                "overall_score": source.primary_score_value,
                "institutional_bounce_score": source.institutional_bounce_score,
                "opportunity_rating": source.opportunity_rating,
                "institutional_checklist": source.institutional_checklist,
                "trade_thesis": source.trade_thesis,
                "warnings": list(source.warnings),
            }
            metrics.update(source.metrics or {})
            metrics.update(source.composite_intelligence_component_scores or {})
            metrics.update({score.name: score.value for score in source.scores})
            metrics.setdefault("composite_score", source.composite_score.value)
            return metrics

        if isinstance(source, dict):
            return dict(source)

        return {}

    @staticmethod
    def sentence_or_unavailable(parts: list[str], unavailable: str) -> str:
        if not parts:
            return unavailable

        return "; ".join(parts) + "."

    def score_assessment(self, value: float) -> str:
        formatted = self.format_number(value)
        if value >= 80:
            return f"{formatted}, a positive contributor"
        if value >= 60:
            return f"{formatted}, a constructive but not dominant contributor"
        if value >= 45:
            return f"{formatted}, a mixed contributor"
        return f"{formatted}, a negative contributor"

    def fundamental_assessment(self, kind: str, value: float) -> str:
        if kind == "growth":
            if value >= 10:
                return "growth supports the setup"
            if value >= 0:
                return "growth is positive but moderate"
            return "growth is a fundamental weakness"
        if kind == "profitability":
            if value >= 20:
                return "profitability is strong"
            if value >= 10:
                return "profitability is acceptable"
            return "profitability is limited"
        if kind == "debt":
            if value <= 0.75:
                return "leverage appears contained"
            if value <= 1.5:
                return "leverage is manageable but should be monitored"
            return "leverage is a balance-sheet risk"
        if kind == "liquidity":
            if value >= 1.5:
                return "liquidity is solid"
            if value >= 1.0:
                return "liquidity is adequate"
            return "liquidity is a constraint"
        if kind == "currency":
            if value > 0:
                return "available scale is supportive"
            if value < 0:
                return "negative value is a weakness"
        return "metric is available for context"

    def institutional_assessment(self, kind: str, value: float) -> str:
        if kind == "percent":
            if value >= 65:
                return "ownership sponsorship is strong"
            if value >= 35:
                return "ownership sponsorship is moderate"
            return "ownership sponsorship is limited"
        if kind == "currency":
            if value > 0:
                return "filing activity indicates net accumulation"
            if value < 0:
                return "filing activity indicates net distribution"
            return "filing activity is neutral"
        return self.score_assessment(value)

    @staticmethod
    def earnings_risk_assessment(value: float) -> str:
        if value <= 35:
            return "near-term earnings risk is low"
        if value <= 65:
            return "near-term earnings risk is elevated"
        return "near-term earnings risk is high"

    def strongest_factors(self, metrics: dict[str, Any], opportunity: Any) -> list[str]:
        factors = []
        if isinstance(opportunity, OpportunityRatingResult):
            factors.extend(opportunity.strengths)

        for key, label in [
            ("support_score", "support quality"),
            ("bounce_score", "bounce validation"),
            ("trend_score", "trend alignment"),
            ("relative_strength_score", "relative strength"),
            ("volume_score", "volume confirmation"),
            ("institutional_score", "institutional sponsorship"),
            ("institutional_momentum_score", "institutional accumulation"),
        ]:
            value = self.first_number(metrics, key)
            if value is not None and value >= 75:
                factors.append(f"{label} at {self.format_number(value)}")

        return self.unique_strings(factors)

    def primary_risks(self, metrics: dict[str, Any], opportunity: Any) -> list[str]:
        risks = []
        if isinstance(opportunity, OpportunityRatingResult):
            risks.extend(opportunity.weaknesses)

        for key, label in [
            ("support_score", "weak support evidence"),
            ("bounce_score", "weak bounce validation"),
            ("trend_score", "weak trend alignment"),
            ("relative_strength_score", "weak relative strength"),
            ("volume_score", "weak volume confirmation"),
        ]:
            value = self.first_number(metrics, key)
            if value is not None and value < 50:
                risks.append(f"{label} at {self.format_number(value)}")

        earnings = self.first_number(metrics, "earnings_risk_score")
        if earnings is not None and earnings >= 65:
            risks.append(f"elevated earnings risk at {self.format_number(earnings)}")

        return self.unique_strings(risks)

    def conclusion_category(
        self,
        opportunity: Any,
        checklist: Any,
        confidence: str,
        warnings: list[str],
    ) -> str:
        score = self.opportunity_score(opportunity)
        checklist_percentage = (
            checklist.overall_percentage
            if isinstance(checklist, InstitutionalChecklistResult)
            else self.dict_value(checklist, "overall_percentage")
        )
        values = [value for value in [score, checklist_percentage] if value is not None]
        average = sum(values) / len(values) if values else 0.0
        warning_penalty = min(12.0, len(warnings) * 2.0)
        adjusted = average - warning_penalty

        if adjusted >= 85 and confidence in {"Very High", "High"}:
            return "High Conviction"
        if adjusted >= 70 and confidence in {"Very High", "High", "Moderate"}:
            return "Constructive"
        if adjusted >= 55:
            return "Watch List"
        if adjusted >= 40:
            return "Speculative"
        return "Avoid"

    def analysis_completeness(self, metrics: dict[str, Any]) -> float:
        expected = [
            "support_score",
            "bounce_score",
            "trend_score",
            "relative_strength_score",
            "volume_score",
            "revenue_growth",
            "eps_growth",
            "roe",
            "gross_margin",
            "free_cash_flow",
            "institutional_score",
            "institutional_ownership_pct",
            "institutional_momentum_score",
            "entry_zone",
            "stop_loss",
            "target_projection",
            "risk_reward",
            "position_size",
        ]
        available = sum(1 for key in expected if metrics.get(key) is not None)
        return available / len(expected)

    def missing_analysis(self, metrics: dict[str, Any]) -> list[str]:
        groups = [
            ("technical assessment", ["support_score", "bounce_score", "trend_score", "relative_strength_score", "volume_score"]),
            ("fundamental assessment", ["revenue_growth", "eps_growth", "roe", "gross_margin", "free_cash_flow", "debt_to_equity", "current_ratio", "market_cap"]),
            ("institutional assessment", ["institutional_score", "institutional_ownership_pct", "institutional_momentum_score"]),
            ("trade plan", ["entry_zone", "stop_loss", "target_projection", "risk_reward", "position_size"]),
        ]
        missing = []
        for label, keys in groups:
            if not any(metrics.get(key) is not None for key in keys):
                missing.append(label)
        return missing

    @staticmethod
    def join_phrases(values: list[Any]) -> str:
        phrases = [str(value) for value in values if value]
        if not phrases:
            return ""
        if len(phrases) == 1:
            return phrases[0]
        return f"{', '.join(phrases[:-1])}, and {phrases[-1]}"

    @staticmethod
    def unique_strings(values: list[Any]) -> list[str]:
        unique = []
        for value in values:
            text = str(value)
            if text and text not in unique:
                unique.append(text)
        return unique

    def first_number(self, metrics: dict[str, Any], *keys: str) -> float | None:
        for key in keys:
            value = metrics.get(key)

            if isinstance(value, ScoreResult):
                value = value.value

            if value is None:
                continue

            try:
                return float(value)
            except (TypeError, ValueError):
                continue

        return None

    @staticmethod
    def opportunity_label(value: Any) -> str | None:
        if isinstance(value, OpportunityRatingResult):
            return value.rating_label

        if isinstance(value, dict):
            return value.get("rating_label") or value.get("label")

        if isinstance(value, str):
            return value

        return None

    def opportunity_score(self, value: Any) -> float | None:
        if isinstance(value, OpportunityRatingResult):
            return value.rating_score

        if isinstance(value, dict):
            try:
                return float(value.get("rating_score") or value.get("score"))
            except (TypeError, ValueError):
                return None

        return self.first_number({"opportunity_rating": value}, "opportunity_rating")

    @staticmethod
    def object_value(source: Any, name: str) -> Any:
        if source is None:
            return None

        if isinstance(source, dict):
            return source.get(name)

        return getattr(source, name, None)

    @staticmethod
    def dict_value(source: Any, name: str) -> Any:
        if isinstance(source, dict):
            return source.get(name)

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

    def format_value(self, value: Any) -> str:
        if isinstance(value, dict):
            label = value.get("entry_label") or value.get("stop_type") or value.get("confidence")
            if label:
                return str(label)

            for key in ["recommended_stop", "target_1", "entry_score", "shares"]:
                if key in value and value[key] is not None:
                    return str(value[key])

            return "available"

        if isinstance(value, (int, float)):
            return self.format_number(value)

        return str(value)

    @staticmethod
    def format_number(value: Any) -> str:
        number = float(value)

        if number.is_integer():
            return f"{number:.0f}"

        return f"{number:.1f}"

    @staticmethod
    def format_currency(value: Any) -> str:
        number = float(value)
        abs_value = abs(number)

        if abs_value >= 1_000_000_000_000:
            return f"${number / 1_000_000_000_000:.2f}T"
        if abs_value >= 1_000_000_000:
            return f"${number / 1_000_000_000:.2f}B"
        if abs_value >= 1_000_000:
            return f"${number / 1_000_000:.2f}M"
        return f"${number:,.0f}"
