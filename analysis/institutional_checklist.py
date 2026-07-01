"""
Pure institutional bounce checklist evaluation.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from analysis.score_result import ScoreResult


@dataclass(frozen=True)
class InstitutionalChecklistCheck:
    """
    One decision-support checklist item.
    """

    name: str
    status: str
    message: str
    value: float | None = None


@dataclass(frozen=True)
class InstitutionalChecklistResult:
    """
    Structured checklist output for institutional bounce candidates.
    """

    passed_checks: list[InstitutionalChecklistCheck] = field(default_factory=list)
    failed_checks: list[InstitutionalChecklistCheck] = field(default_factory=list)
    warning_checks: list[InstitutionalChecklistCheck] = field(default_factory=list)
    total_checks: int = 0
    passed_count: int = 0
    warning_count: int = 0
    failed_count: int = 0
    overall_percentage: float = 0.0
    overall_label: str = "Avoid"
    checks: list[InstitutionalChecklistCheck] = field(default_factory=list)


class InstitutionalChecklistEvaluator:
    """
    Evaluate institutional bounce decision criteria from existing metrics.

    The evaluator is intentionally pure and read-only. It does not calculate or
    persist scores; it classifies already-available metrics into checklist
    statuses for downstream presentation.
    """

    CHECK_ORDER = [
        "Near validated support",
        "Bounce success rate acceptable",
        "Relative Strength strong",
        "Trend aligned",
        "Institutional ownership acceptable",
        "Institutional momentum positive",
        "Volume accumulation present",
        "Earnings window safe",
        "ATR risk acceptable",
        "Opportunity rating acceptable",
    ]

    def evaluate(self, metrics):
        metrics = metrics or {}
        checks = [
            self.near_validated_support(metrics),
            self.bounce_success_rate_acceptable(metrics),
            self.relative_strength_strong(metrics),
            self.trend_aligned(metrics),
            self.institutional_ownership_acceptable(metrics),
            self.institutional_momentum_positive(metrics),
            self.volume_accumulation_present(metrics),
            self.earnings_window_safe(metrics),
            self.atr_risk_acceptable(metrics),
            self.opportunity_rating_acceptable(metrics),
        ]

        passed_checks = [
            check for check in checks if check.status == "pass"
        ]
        warning_checks = [
            check for check in checks if check.status == "warning"
        ]
        failed_checks = [
            check for check in checks if check.status == "fail"
        ]
        total_checks = len(checks)
        passed_count = len(passed_checks)
        warning_count = len(warning_checks)
        failed_count = len(failed_checks)
        overall_percentage = self.percentage(passed_count, total_checks)

        return InstitutionalChecklistResult(
            passed_checks=passed_checks,
            failed_checks=failed_checks,
            warning_checks=warning_checks,
            total_checks=total_checks,
            passed_count=passed_count,
            warning_count=warning_count,
            failed_count=failed_count,
            overall_percentage=overall_percentage,
            overall_label=self.overall_label(overall_percentage),
            checks=checks,
        )

    def near_validated_support(self, metrics):
        distance = self.metric(metrics, "distance_to_support_pct")
        support_score = self.metric(metrics, "support_score")

        if distance is None and support_score is None:
            return self.warning(
                "Near validated support",
                "Support proximity is unavailable.",
            )

        if distance is not None:
            if distance <= 3:
                return self.pass_check(
                    "Near validated support",
                    "Price is close to validated support.",
                    distance,
                )
            if distance <= 7:
                return self.warning(
                    "Near validated support",
                    "Price is moderately above support.",
                    distance,
                )
            return self.fail(
                "Near validated support",
                "Price is extended above support.",
                distance,
            )

        if support_score >= 75:
            return self.pass_check(
                "Near validated support",
                "Support quality is strong.",
                support_score,
            )
        if support_score >= 55:
            return self.warning(
                "Near validated support",
                "Support quality is only moderate.",
                support_score,
            )
        return self.fail(
            "Near validated support",
            "Support quality is weak.",
            support_score,
        )

    def bounce_success_rate_acceptable(self, metrics):
        value = self.metric(metrics, "bounce_success_rate")

        if value is None:
            return self.score_fallback(
                metrics,
                "bounce_score",
                "Bounce success rate acceptable",
                "Bounce validation is strong.",
                "Bounce validation is moderate.",
                "Bounce validation is weak.",
            )

        if value >= 70:
            return self.pass_check(
                "Bounce success rate acceptable",
                "Historical bounce success rate is acceptable.",
                value,
            )
        if value >= 50:
            return self.warning(
                "Bounce success rate acceptable",
                "Historical bounce success rate is mixed.",
                value,
            )
        return self.fail(
            "Bounce success rate acceptable",
            "Historical bounce success rate is weak.",
            value,
        )

    def relative_strength_strong(self, metrics):
        return self.score_check(
            metrics,
            "relative_strength_score",
            "Relative Strength strong",
            "Relative strength is strong.",
            "Relative strength is only moderate.",
            "Relative strength is weak.",
            pass_at=75,
            warn_at=50,
        )

    def trend_aligned(self, metrics):
        return self.score_check(
            metrics,
            "trend_score",
            "Trend aligned",
            "Trend is aligned with the setup.",
            "Trend alignment is mixed.",
            "Trend is not aligned.",
            pass_at=70,
            warn_at=50,
        )

    def institutional_ownership_acceptable(self, metrics):
        return self.score_check(
            metrics,
            "institutional_score",
            "Institutional ownership acceptable",
            "Institutional ownership profile is acceptable.",
            "Institutional ownership profile is mixed.",
            "Institutional ownership profile is weak.",
            pass_at=70,
            warn_at=50,
        )

    def institutional_momentum_positive(self, metrics):
        return self.score_check(
            metrics,
            "institutional_momentum_score",
            "Institutional momentum positive",
            "Institutional momentum is positive.",
            "Institutional momentum is mixed.",
            "Institutional momentum is weak.",
            pass_at=70,
            warn_at=50,
        )

    def volume_accumulation_present(self, metrics):
        return self.score_check(
            metrics,
            "volume_score",
            "Volume accumulation present",
            "Volume accumulation is present.",
            "Volume accumulation is inconclusive.",
            "Volume accumulation is absent.",
            pass_at=70,
            warn_at=50,
        )

    def earnings_window_safe(self, metrics):
        value = self.metric(metrics, "earnings_risk_score")

        if value is None:
            return self.warning(
                "Earnings window safe",
                "Earnings risk data is unavailable.",
            )

        if value <= 35:
            return self.pass_check(
                "Earnings window safe",
                "Near-term earnings risk is low.",
                value,
            )
        if value <= 65:
            return self.warning(
                "Earnings window safe",
                "Near-term earnings risk is elevated.",
                value,
            )
        return self.fail(
            "Earnings window safe",
            "Near-term earnings risk is high.",
            value,
        )

    def atr_risk_acceptable(self, metrics):
        return self.score_check(
            metrics,
            "risk_score",
            "ATR risk acceptable",
            "ATR risk profile is acceptable.",
            "ATR risk profile is mixed.",
            "ATR risk profile is unfavorable.",
            pass_at=70,
            warn_at=50,
        )

    def opportunity_rating_acceptable(self, metrics):
        value = self.metric(metrics, "opportunity_rating_score")

        if value is None:
            value = self.metric(metrics, "institutional_bounce_score")

        if value is None:
            return self.warning(
                "Opportunity rating acceptable",
                "Opportunity rating is unavailable.",
            )

        if value >= 70:
            return self.pass_check(
                "Opportunity rating acceptable",
                "Opportunity rating is acceptable.",
                value,
            )
        if value >= 60:
            return self.warning(
                "Opportunity rating acceptable",
                "Opportunity rating is weak but monitorable.",
                value,
            )
        return self.fail(
            "Opportunity rating acceptable",
            "Opportunity rating is below threshold.",
            value,
        )

    def score_fallback(
        self,
        metrics,
        metric_name,
        check_name,
        pass_message,
        warning_message,
        fail_message,
    ):
        value = self.metric(metrics, metric_name)

        if value is None:
            return self.warning(check_name, f"{metric_name} is unavailable.")

        return self.classify_score(
            check_name,
            value,
            pass_message,
            warning_message,
            fail_message,
            pass_at=70,
            warn_at=50,
        )

    def score_check(
        self,
        metrics,
        metric_name,
        check_name,
        pass_message,
        warning_message,
        fail_message,
        pass_at,
        warn_at,
    ):
        value = self.metric(metrics, metric_name)

        if value is None:
            return self.warning(check_name, f"{metric_name} is unavailable.")

        return self.classify_score(
            check_name,
            value,
            pass_message,
            warning_message,
            fail_message,
            pass_at,
            warn_at,
        )

    def classify_score(
        self,
        check_name,
        value,
        pass_message,
        warning_message,
        fail_message,
        pass_at,
        warn_at,
    ):
        if value >= pass_at:
            return self.pass_check(check_name, pass_message, value)
        if value >= warn_at:
            return self.warning(check_name, warning_message, value)
        return self.fail(check_name, fail_message, value)

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
    def percentage(passed_count, total_checks):
        if total_checks <= 0:
            return 0.0

        return round((passed_count / total_checks) * 100.0, 1)

    @staticmethod
    def overall_label(percentage):
        if percentage >= 100:
            return "Exceptional"
        if percentage >= 90:
            return "Excellent"
        if percentage >= 80:
            return "Strong"
        if percentage >= 70:
            return "Acceptable"
        if percentage >= 60:
            return "Weak"
        return "Avoid"

    @staticmethod
    def pass_check(name, message, value=None):
        return InstitutionalChecklistCheck(
            name=name,
            status="pass",
            message=message,
            value=value,
        )

    @staticmethod
    def warning(name, message, value=None):
        return InstitutionalChecklistCheck(
            name=name,
            status="warning",
            message=message,
            value=value,
        )

    @staticmethod
    def fail(name, message, value=None):
        return InstitutionalChecklistCheck(
            name=name,
            status="fail",
            message=message,
            value=value,
        )
