"""
Risk/reward evaluation utilities.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from analysis.score_result import ScoreResult


@dataclass(frozen=True)
class RiskRewardResult:
    """
    Pure v2.4 risk/reward output.
    """

    risk_amount: float | None
    reward_1: float | None
    reward_2: float | None
    reward_3: float | None
    rr_1: float | None
    rr_2: float | None
    rr_3: float | None
    best_target: float | None
    best_rr: float | None
    recommended_trade: str
    recommendation_reason: str
    warnings: list[str] = field(default_factory=list)


class RiskRewardCalculator:
    """
    Combine entry, stop, target, and probability context into trade quality.

    These are v2.4 placeholder heuristics:
    - risk is recommended_entry minus recommended_stop
    - rewards are target minus recommended_entry
    - reward/risk ratios are calculated for all valid targets
    - recommendations combine opportunity score, entry quality, best R:R,
      and bounce success probability
    """

    STRONG_BUY = "Strong Buy"
    BUY = "Buy"
    WATCH = "Watch"
    AVOID = "Avoid"

    def calculate(self, metrics):
        metrics = metrics or {}
        warnings = []
        entry = self.metric(metrics, "recommended_entry")

        if entry is None:
            entry = self.metric(metrics, "current_price")

        stop = self.metric(metrics, "recommended_stop")
        targets = [
            self.metric(metrics, "target_1"),
            self.metric(metrics, "target_2"),
            self.metric(metrics, "target_3"),
        ]
        opportunity_score = self.metric(metrics, "opportunity_rating_score")
        entry_score = self.metric(metrics, "entry_score")
        bounce_success = self.metric(metrics, "bounce_success_rate")

        if entry is None or entry <= 0:
            warnings.append("Missing entry")

        if stop is None:
            warnings.append("Missing stop")

        for index, target in enumerate(targets, start=1):
            if target is None:
                warnings.append(f"Missing target {index}")

        if entry is None or entry <= 0 or stop is None:
            return self.result(
                risk_amount=None,
                rewards=[None, None, None],
                ratios=[None, None, None],
                best_target=None,
                best_rr=None,
                recommended_trade=self.AVOID,
                recommendation_reason="Missing data prevents risk/reward evaluation.",
                warnings=self.dedupe(warnings + ["Missing data"]),
            )

        risk_amount = entry - stop

        if risk_amount <= 0:
            warnings.append("Stop must be below entry")
            return self.result(
                risk_amount=risk_amount,
                rewards=[None, None, None],
                ratios=[None, None, None],
                best_target=None,
                best_rr=None,
                recommended_trade=self.AVOID,
                recommendation_reason="Stop placement creates invalid downside risk.",
                warnings=self.dedupe(warnings),
            )

        if risk_amount / entry > 0.12:
            warnings.append("Stop too wide")

        rewards = [
            self.reward(entry, target, warnings)
            for target in targets
        ]
        ratios = [
            self.ratio(reward, risk_amount)
            for reward in rewards
        ]
        best_target, best_rr = self.best_target(targets, ratios)

        if best_rr is None:
            warnings.append("Missing data")
            recommended_trade = self.AVOID
            reason = "No valid upside target is available."
        else:
            if best_rr < 1.0:
                warnings.append("Poor reward/risk")
            if any(reward is not None and reward <= risk_amount for reward in rewards):
                warnings.append("Target too close")

            recommended_trade, reason = self.recommendation(
                opportunity_score=opportunity_score,
                entry_score=entry_score,
                bounce_success=bounce_success,
                best_rr=best_rr,
            )

        return self.result(
            risk_amount=self.round_value(risk_amount),
            rewards=[self.round_value(value) for value in rewards],
            ratios=[self.round_value(value) for value in ratios],
            best_target=self.round_value(best_target),
            best_rr=self.round_value(best_rr),
            recommended_trade=recommended_trade,
            recommendation_reason=reason,
            warnings=self.dedupe(warnings),
        )

    def recommendation(
        self,
        opportunity_score,
        entry_score,
        bounce_success,
        best_rr,
    ):
        if best_rr is None:
            return self.AVOID, "Reward/risk is unavailable."

        if (
            opportunity_score is not None
            and opportunity_score >= 85
            and entry_score is not None
            and entry_score >= 80
            and bounce_success is not None
            and bounce_success >= 75
            and best_rr >= 2.5
        ):
            return (
                self.STRONG_BUY,
                "Opportunity, entry quality, bounce probability, and reward/risk are strong.",
            )

        if (
            opportunity_score is not None
            and opportunity_score >= 75
            and entry_score is not None
            and entry_score >= 65
            and (bounce_success is None or bounce_success >= 60)
            and best_rr >= 1.8
        ):
            return self.BUY, "Reward/risk is favorable with acceptable setup quality."

        if (
            opportunity_score is not None
            and opportunity_score >= 60
            and entry_score is not None
            and entry_score >= 50
            and best_rr >= 1.2
        ):
            return self.WATCH, "Setup is monitorable but reward/risk or quality is not compelling."

        return self.AVOID, "Reward/risk or setup quality is insufficient."

    @staticmethod
    def reward(entry, target, warnings):
        if target is None:
            return None

        reward = target - entry

        if reward <= 0:
            warnings.append("Target too close")
            return reward

        return reward

    @staticmethod
    def ratio(reward, risk_amount):
        if reward is None or risk_amount <= 0:
            return None

        return reward / risk_amount

    @staticmethod
    def best_target(targets, ratios):
        best = None

        for target, ratio in zip(targets, ratios):
            if target is None or ratio is None:
                continue

            if best is None or ratio > best[1]:
                best = (target, ratio)

        if best is None:
            return None, None

        return best

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
    def round_value(value):
        if value is None:
            return None

        return round(float(value), 6)

    @staticmethod
    def dedupe(values):
        deduped = []

        for value in values:
            if value not in deduped:
                deduped.append(value)

        return deduped

    @staticmethod
    def result(
        risk_amount,
        rewards,
        ratios,
        best_target,
        best_rr,
        recommended_trade,
        recommendation_reason,
        warnings,
    ):
        return RiskRewardResult(
            risk_amount=risk_amount,
            reward_1=rewards[0],
            reward_2=rewards[1],
            reward_3=rewards[2],
            rr_1=ratios[0],
            rr_2=ratios[1],
            rr_3=ratios[2],
            best_target=best_target,
            best_rr=best_rr,
            recommended_trade=recommended_trade,
            recommendation_reason=recommendation_reason,
            warnings=warnings,
        )
