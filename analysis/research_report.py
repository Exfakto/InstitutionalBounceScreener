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
    confidence: str = "Very Low"


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
        parts = []
        rating_label = self.opportunity_label(opportunity)
        rating_score = self.opportunity_score(opportunity)
        overall_score = self.first_number(
            metrics,
            "overall_score",
            "institutional_bounce_score",
            "composite_intelligence_score",
            "composite_score",
        )

        if rating_label:
            parts.append(f"{display_name} is classified as {rating_label}")
        elif overall_score is not None:
            parts.append(
                f"{display_name} has an overall setup score of {self.format_number(overall_score)}"
            )
        else:
            parts.append(
                f"{display_name} has limited available data for a complete setup review"
            )

        if rating_score is not None:
            parts.append(f"Opportunity score is {self.format_number(rating_score)}")

        parts.append(f"Report confidence is {confidence}.")

        return ". ".join(part.rstrip(".") for part in parts) + "."

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
            ("technical_score", "technical score"),
            ("support_score", "support strength"),
            ("bounce_score", "bounce validation"),
            ("relative_strength_score", "relative strength"),
            ("volume_score", "volume intelligence"),
            ("trend_score", "trend"),
        ]:
            value = self.first_number(metrics, key)
            if value is not None:
                parts.append(f"{label} {self.format_number(value)}")

        return self.sentence_or_unavailable(parts, "Technical analysis data is unavailable.")

    def fundamental_analysis(self, metrics: dict[str, Any]) -> str:
        parts = []
        for keys, label, suffix in [
            (("revenue_growth", "revenue_growth_ttm"), "revenue growth", "%"),
            (("eps_growth", "eps_growth_ttm"), "EPS growth", "%"),
            (("roe",), "ROE", "%"),
            (("gross_margin",), "gross margin", "%"),
            (("free_cash_flow",), "free cash flow", ""),
            (("debt_to_equity",), "debt/equity", ""),
            (("current_ratio",), "current ratio", ""),
            (("market_cap",), "market cap", ""),
        ]:
            value = self.first_number(metrics, *keys)
            if value is not None:
                formatted = (
                    self.format_currency(value)
                    if label in {"free cash flow", "market cap"}
                    else f"{self.format_number(value)}{suffix}"
                )
                parts.append(f"{label} {formatted}")

        return self.sentence_or_unavailable(parts, "Fundamental analysis data is unavailable.")

    def institutional_analysis(self, metrics: dict[str, Any], checklist: Any) -> str:
        parts = []
        for key, label in [
            ("institutional_score", "institutional score"),
            ("institutional_momentum_score", "institutional momentum"),
            ("institutional_ownership_pct", "institutional ownership"),
            ("institutional_ownership_change_qoq", "ownership change"),
            ("net_institutional_buying", "net institutional buying"),
        ]:
            value = self.first_number(metrics, key)
            if value is not None:
                formatted = self.format_currency(value) if key == "net_institutional_buying" else self.format_number(value)
                parts.append(f"{label} {formatted}")

        if isinstance(checklist, InstitutionalChecklistResult):
            parts.append(
                f"{checklist.passed_count} of {checklist.total_checks} checklist items passed"
            )

        return self.sentence_or_unavailable(parts, "Institutional analysis data is unavailable.")

    def trade_plan(self, metrics: dict[str, Any]) -> str:
        parts = []
        for key, label in [
            ("entry_zone", "entry zone"),
            ("stop_loss", "stop loss"),
            ("target_projection", "target projection"),
            ("risk_reward", "risk/reward"),
            ("position_size", "position size"),
        ]:
            value = metrics.get(key)
            if value is not None:
                parts.append(f"{label} {self.format_value(value)}")

        return self.sentence_or_unavailable(parts, "Trade plan data is unavailable.")

    def risk_summary(self, metrics: dict[str, Any], warnings: list[str]) -> str:
        parts = []
        earnings = self.first_number(metrics, "earnings_risk_score")
        risk_reward = metrics.get("risk_reward")

        if earnings is not None:
            parts.append(f"earnings risk score {self.format_number(earnings)}")
        if risk_reward is not None:
            parts.append(f"risk/reward {self.format_value(risk_reward)}")
        if warnings:
            parts.append(f"{len(warnings)} warning item(s) require review")

        return self.sentence_or_unavailable(parts, "Risk data is unavailable.")

    def conclusion(
        self,
        ticker: str,
        opportunity: Any,
        checklist: Any,
        confidence: str,
        warnings: list[str],
    ) -> str:
        label = self.opportunity_label(opportunity)
        setup_text = f"{label} setup" if label else "setup"
        checklist_text = ""

        if isinstance(checklist, InstitutionalChecklistResult):
            checklist_text = f" with a {checklist.overall_label} checklist"

        warning_text = " Warnings should be reviewed before action." if warnings else ""

        return (
            f"{ticker} presents a {setup_text}{checklist_text}. "
            f"Overall confidence is {confidence}.{warning_text}"
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
            return "Very Low"

        average = sum(values) / len(values)

        if average >= 90:
            return "Very High"
        if average >= 80:
            return "High"
        if average >= 65:
            return "Moderate"
        if average >= 45:
            return "Low"
        return "Very Low"

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
