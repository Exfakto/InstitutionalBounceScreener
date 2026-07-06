from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class RiskAnalytics:
    ticker: str
    component_scores: dict = field(default_factory=dict)
    risk_score: float = 50.0
    risk_class: str = "Moderate"
    recommendation: str = "Speculative"
    flags: list[str] = field(default_factory=list)
    commentary: str = "Risk analytics are not available."

    def as_metrics(self):
        values = dict(self.component_scores)
        values.update(
            {
                "overall_risk_score": self.risk_score,
                "risk_score": self.risk_score,
                "risk_rating": self.risk_class,
                "risk_recommendation": self.recommendation,
                "risk_flags": list(self.flags),
                "risk_commentary": self.commentary,
                "risk_research_summary": self.commentary,
                "excessive_debt": 1 if "Aggressive Leverage" in self.flags else 0,
                "price_above_support_10pct": 1 if "Extended Above Support" in self.flags else 0,
                "price_below_200dma": 1 if "Bearish Trend" in self.flags else 0,
                "recent_support_break": 1 if "High Failure Probability" in self.flags else 0,
            }
        )
        return values


class RiskAnalyticsService:
    """
    Composite trading risk assessment from technical, bounce and fundamentals.
    """

    def analytics_for_metrics(self, ticker, metrics):
        ticker = str(ticker or "").strip().upper()
        metrics = dict(metrics or {})
        components = self.component_scores(metrics)
        risk_score = self.weighted_score(components)
        risk_class = self.risk_class(risk_score)
        recommendation = self.recommendation(risk_score)
        flags = self.flags(metrics, components)
        commentary = self.commentary(metrics, components, risk_score, risk_class, flags)

        return RiskAnalytics(
            ticker=ticker,
            component_scores=components,
            risk_score=risk_score,
            risk_class=risk_class,
            recommendation=recommendation,
            flags=flags,
            commentary=commentary,
        )

    def component_scores(self, metrics):
        return {
            "atr_risk": self.atr_risk(metrics),
            "support_failure_risk": self.support_failure_risk(metrics),
            "support_failure_risk_pct": self.support_failure_risk(metrics),
            "distance_from_support_risk": self.distance_from_support_risk(metrics),
            "volatility_risk": self.volatility_risk(metrics),
            "volatility_pct": self.volatility_risk(metrics),
            "trend_risk": self.trend_risk(metrics),
            "liquidity_risk": self.liquidity_risk(metrics),
            "gap_risk": self.gap_risk(metrics),
            "fundamental_risk": self.fundamental_risk(metrics),
            "market_structure_risk": self.market_structure_risk(metrics),
            "historical_bounce_reliability": self.bounce_reliability_risk(metrics),
            "leverage_risk": self.leverage_risk(metrics),
            "debt_risk_score": self.leverage_risk(metrics),
        }

    @classmethod
    def weighted_score(cls, components):
        weights = {
            "atr_risk": 0.10,
            "support_failure_risk": 0.15,
            "distance_from_support_risk": 0.10,
            "volatility_risk": 0.10,
            "trend_risk": 0.12,
            "liquidity_risk": 0.08,
            "gap_risk": 0.07,
            "fundamental_risk": 0.13,
            "market_structure_risk": 0.08,
            "historical_bounce_reliability": 0.07,
        }
        seen = [
            (components[key], weight)
            for key, weight in weights.items()
            if components.get(key) is not None
        ]
        if not seen:
            return 50.0
        total_weight = sum(weight for _, weight in seen)
        return round(sum(score * weight for score, weight in seen) / total_weight, 1)

    @staticmethod
    def risk_class(score):
        if score < 20:
            return "Very Low"
        if score < 40:
            return "Low"
        if score < 60:
            return "Moderate"
        if score < 80:
            return "High"
        return "Very High"

    @staticmethod
    def recommendation(score):
        if score < 20:
            return "Excellent Risk"
        if score < 40:
            return "Acceptable Risk"
        if score < 60:
            return "Speculative"
        if score < 80:
            return "High Risk"
        return "Avoid"

    def flags(self, metrics, components):
        flags = []
        if self.number(metrics.get("support_strength_score") or metrics.get("support_strength")) is not None:
            if self.number(metrics.get("support_strength_score") or metrics.get("support_strength")) < 50:
                flags.append("Weak Support")
        if (components.get("distance_from_support_risk") or 0) >= 70:
            flags.append("Extended Above Support")
        if (components.get("atr_risk") or 0) >= 70:
            flags.append("High ATR")
        if (components.get("trend_risk") or 0) >= 70:
            flags.append("Bearish Trend")
        if (components.get("fundamental_risk") or 0) >= 70:
            flags.append("Weak Fundamentals")
        if (components.get("liquidity_risk") or 0) >= 70:
            flags.append("Low Liquidity")
        if (components.get("volatility_risk") or 0) >= 70:
            flags.append("High Volatility")
        if (components.get("support_failure_risk") or 0) >= 60:
            flags.append("High Failure Probability")
        if self.number(metrics.get("debt_to_equity")) is not None and self.number(metrics.get("debt_to_equity")) >= 2.5:
            flags.append("Aggressive Leverage")
        return flags

    def commentary(self, metrics, components, score, risk_class, flags):
        sentences = [
            f"The setup carries {risk_class.lower()} composite risk with a Risk Intelligence Score of {score:.1f}."
        ]
        trend = str(metrics.get("trend") or metrics.get("market_structure") or "").lower()
        if "bull" in trend:
            sentences.append("Technical momentum remains constructive, which helps contain trend risk.")
        elif "bear" in trend:
            sentences.append("Technical momentum is bearish and increases execution risk.")
        else:
            sentences.append("Technical trend evidence is mixed, so confirmation remains important.")

        if (components.get("atr_risk") or 0) >= 60:
            sentences.append("Above-average ATR or volatility increases the probability of wider price swings.")
        elif components.get("atr_risk") is not None:
            sentences.append("Volatility appears contained relative to the current price.")

        reliability = components.get("historical_bounce_reliability")
        if reliability is not None and reliability <= 35:
            sentences.append("Historical support reliability remains strong and reduces downside risk while the support zone holds.")
        elif reliability is not None and reliability >= 65:
            sentences.append("Historical bounce reliability is weak, increasing the chance of support failure.")

        if (components.get("fundamental_risk") or 0) >= 60:
            sentences.append("Fundamental quality is a material risk contributor.")
        elif components.get("fundamental_risk") is not None:
            sentences.append("Fundamental quality provides a stabilizing offset to trading risk.")

        if flags:
            sentences.append("Active risk flags include " + ", ".join(flags[:5]) + ".")
        else:
            sentences.append("No major quantitative risk flags are active.")
        return " ".join(sentences)

    @classmethod
    def atr_risk(cls, metrics):
        atr = cls.number(metrics.get("atr14") or metrics.get("atr"))
        price = cls.number(metrics.get("current_price") or metrics.get("close") or metrics.get("price"))
        atr_pct = cls.number(metrics.get("atr_pct") or metrics.get("volatility_pct"))
        if atr_pct is None and atr is not None and price not in (None, 0):
            atr_pct = atr / price * 100
        if atr_pct is None:
            return None
        return cls.clamp(atr_pct / 8 * 100)

    @classmethod
    def support_failure_risk(cls, metrics):
        failure = cls.number(metrics.get("support_failure_risk_pct") or metrics.get("breakdown_risk"))
        if failure is not None:
            return cls.clamp(failure)
        success = cls.number(metrics.get("bounce_success_pct") or metrics.get("historical_bounce_success_rate"))
        if success is None:
            return None
        return cls.clamp(100 - success)

    @classmethod
    def distance_from_support_risk(cls, metrics):
        distance = cls.number(metrics.get("distance_to_support_pct") or metrics.get("distance_from_support_pct"))
        if distance is None:
            return None
        return cls.clamp((distance - 2) / 13 * 100)

    @classmethod
    def volatility_risk(cls, metrics):
        relative_volume = cls.number(metrics.get("relative_volume"))
        atr_risk = cls.atr_risk(metrics)
        volume_component = None
        if relative_volume is not None:
            volume_component = cls.clamp(abs(relative_volume - 1) / 2 * 100)
        values = [value for value in (atr_risk, volume_component) if value is not None]
        if not values:
            return None
        return sum(values) / len(values)

    @classmethod
    def trend_risk(cls, metrics):
        trend = str(metrics.get("trend") or "").lower()
        if "bear" in trend or "down" in trend:
            return 85.0
        if "bull" in trend or "up" in trend:
            return 20.0
        price = cls.number(metrics.get("current_price") or metrics.get("close"))
        ema200 = cls.number(metrics.get("ema200") or metrics.get("sma200"))
        if price is not None and ema200 is not None:
            return 75.0 if price < ema200 else 25.0
        return 50.0

    @classmethod
    def liquidity_risk(cls, metrics):
        volume = cls.number(metrics.get("latest_volume") or metrics.get("volume"))
        if volume is None:
            return None
        if volume >= 2_000_000:
            return 10.0
        if volume >= 500_000:
            return 35.0
        if volume >= 100_000:
            return 65.0
        return 90.0

    @classmethod
    def gap_risk(cls, metrics):
        earnings_soon = metrics.get("earnings_within_7_days")
        if str(earnings_soon).lower() in {"1", "true", "yes"} or earnings_soon is True:
            return 85.0
        if metrics.get("upcoming_earnings") or metrics.get("next_earnings_date"):
            return 45.0
        return 25.0

    @classmethod
    def fundamental_risk(cls, metrics):
        score = cls.number(metrics.get("fundamental_intelligence_score") or metrics.get("quality_score"))
        if score is None:
            return None
        return cls.clamp(100 - score)

    @classmethod
    def market_structure_risk(cls, metrics):
        structure = str(metrics.get("market_structure") or "").lower()
        if "strong bullish" in structure:
            return 15.0
        if "strong bearish" in structure:
            return 85.0
        if "bear" in structure:
            return 70.0
        if "bull" in structure:
            return 30.0
        return 50.0

    @classmethod
    def bounce_reliability_risk(cls, metrics):
        success = cls.number(metrics.get("bounce_success_pct") or metrics.get("historical_bounce_success_rate"))
        tests = cls.number(metrics.get("support_tests") or metrics.get("bounce_count"))
        if success is None and tests is None:
            return None
        success_risk = 100 - (success if success is not None else 50)
        test_penalty = 0 if (tests or 0) >= 5 else 20 if (tests or 0) >= 3 else 40
        return cls.clamp(success_risk + test_penalty)

    @classmethod
    def leverage_risk(cls, metrics):
        debt = cls.number(metrics.get("debt_to_equity"))
        if debt is None:
            return None
        return cls.clamp((debt - 0.5) / 2.5 * 100)

    @staticmethod
    def number(value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def clamp(value):
        return max(0.0, min(100.0, value))
