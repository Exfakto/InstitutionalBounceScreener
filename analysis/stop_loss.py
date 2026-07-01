"""
Stop-loss recommendation utilities.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from analysis.score_result import ScoreResult


@dataclass(frozen=True)
class StopLossResult:
    """
    Pure v2.4 stop-loss output.
    """

    technical_stop: float | None
    atr_stop: float | None
    protective_stop: float | None
    recommended_stop: float | None
    risk_percent: float | None
    stop_type: str
    warnings: list[str] = field(default_factory=list)


class StopLossCalculator:
    """
    Calculate support- and ATR-aware stop-loss candidates.

    These are v2.4 placeholder heuristics:
    - technical_stop sits just below support low
    - atr_stop sits below support low by a configurable ATR multiple
    - protective_stop is a conservative stop below strong support
    - stronger support and bounce quality favor the protective stop
    - high ATR or weak risk favors the wider ATR stop when available
    """

    TECHNICAL_BUFFER_PCT = 0.01
    PROTECTIVE_BUFFER_PCT = 0.006
    DEFAULT_ATR_MULTIPLE = 1.5

    STOP_TECHNICAL = "Technical"
    STOP_ATR = "ATR"
    STOP_PROTECTIVE = "Protective"
    STOP_UNAVAILABLE = "Unavailable"

    def __init__(self, atr_multiple=DEFAULT_ATR_MULTIPLE):
        self.atr_multiple = float(atr_multiple)

    def calculate(self, metrics):
        metrics = metrics or {}
        warnings = []
        current_price = self.metric(metrics, "current_price")
        support_low = self.metric(metrics, "nearest_support_low")
        support_high = self.metric(metrics, "nearest_support_high")
        support_mid = self.metric(metrics, "nearest_support_mid")
        atr = self.metric(metrics, "atr")
        atr_pct = self.metric(metrics, "atr_pct")

        if current_price is None or current_price <= 0:
            warnings.append("Missing current price")

        if support_low is None:
            warnings.append("Missing support zone")

        if atr is None and atr_pct is None:
            warnings.append("Missing ATR")

        if current_price is None or current_price <= 0 or support_low is None:
            return self.unavailable_result(warnings)

        if support_high is not None and support_low > support_high:
            support_low, support_high = support_high, support_low

        if support_mid is None and support_high is not None:
            support_mid = (support_low + support_high) / 2.0

        if atr is None and atr_pct is not None:
            atr = current_price * (atr_pct / 100.0)

        technical_stop = support_low * (1.0 - self.TECHNICAL_BUFFER_PCT)
        protective_stop = self.protective_stop(support_low, support_mid)
        atr_stop = (
            support_low - (atr * self.atr_multiple)
            if atr is not None and atr > 0
            else None
        )
        recommended_stop, stop_type = self.recommend_stop(
            technical_stop=technical_stop,
            atr_stop=atr_stop,
            protective_stop=protective_stop,
            metrics=metrics,
        )
        risk_percent = self.risk_percent(current_price, recommended_stop)

        return StopLossResult(
            technical_stop=technical_stop,
            atr_stop=atr_stop,
            protective_stop=protective_stop,
            recommended_stop=recommended_stop,
            risk_percent=risk_percent,
            stop_type=stop_type,
            warnings=warnings,
        )

    def recommend_stop(
        self,
        technical_stop,
        atr_stop,
        protective_stop,
        metrics,
    ):
        support_strength = self.metric(metrics, "support_strength_score")
        bounce_success = self.metric(metrics, "bounce_success_rate")
        risk_score = self.metric(metrics, "risk_score")
        atr_pct = self.metric(metrics, "atr_pct")
        entry_zone = metrics.get("entry_zone")

        if atr_stop is not None and (
            (atr_pct is not None and atr_pct >= 6.0)
            or (risk_score is not None and risk_score < 45.0)
            or entry_zone in {"Extended", "Too Late"}
        ):
            return atr_stop, self.STOP_ATR

        if (
            support_strength is not None
            and support_strength >= 80.0
            and bounce_success is not None
            and bounce_success >= 70.0
            and (risk_score is None or risk_score >= 55.0)
        ):
            return protective_stop, self.STOP_PROTECTIVE

        if atr_stop is None:
            return technical_stop, self.STOP_TECHNICAL

        if atr_pct is not None and atr_pct <= 1.0:
            return technical_stop, self.STOP_TECHNICAL

        return technical_stop, self.STOP_TECHNICAL

    @classmethod
    def protective_stop(cls, support_low, support_mid):
        if support_mid is not None:
            support_width = abs(support_mid - support_low)
            buffer = max(support_low * cls.PROTECTIVE_BUFFER_PCT, support_width * 0.25)
        else:
            buffer = support_low * cls.PROTECTIVE_BUFFER_PCT

        return support_low - buffer

    @staticmethod
    def risk_percent(current_price, recommended_stop):
        if recommended_stop is None or current_price is None or current_price <= 0:
            return None

        return ((current_price - recommended_stop) / current_price) * 100.0

    @staticmethod
    def metric(metrics, name):
        value = metrics.get(name)

        if isinstance(value, ScoreResult):
            value = value.value

        if value is None or value == "":
            return None

        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def unavailable_result(warnings):
        return StopLossResult(
            technical_stop=None,
            atr_stop=None,
            protective_stop=None,
            recommended_stop=None,
            risk_percent=None,
            stop_type=StopLossCalculator.STOP_UNAVAILABLE,
            warnings=warnings,
        )
