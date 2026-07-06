from __future__ import annotations

from dataclasses import dataclass, field

from database.manager import DatabaseManager


@dataclass(frozen=True)
class FundamentalAnalytics:
    ticker: str
    metrics: dict = field(default_factory=dict)
    scores: dict = field(default_factory=dict)
    intelligence_score: float = 0.0
    classification: str = "Critical"
    flags: list[str] = field(default_factory=list)
    commentary: str = "Fundamental analytics are not available."
    research_summary: str = "Fundamental analytics are not available."

    def as_metrics(self):
        values = dict(self.metrics)
        values.update(self.scores)
        values.update(
            {
                "fundamental_intelligence_score": self.intelligence_score,
                "fundamental_classification": self.classification,
                "fundamental_quality_flags": list(self.flags),
                "fundamental_commentary": self.commentary,
                "fundamental_research_summary": self.research_summary,
                "risk_rating": self.risk_rating(),
                "overall_risk_score": round(max(0.0, 100.0 - self.intelligence_score), 1),
                "debt_risk_score": round(max(0.0, 100.0 - (self.scores.get("leverage_score") or 0.0)), 1),
                "excessive_debt": 1 if "Aggressive Leverage" in self.flags else 0,
                "quality_score": self.intelligence_score,
            }
        )
        return values

    def risk_rating(self):
        if self.intelligence_score >= 75:
            return "Low"
        if self.intelligence_score >= 55:
            return "Moderate"
        if self.intelligence_score >= 35:
            return "Elevated"
        return "High"


class FundamentalAnalyticsService:
    """
    Convert stored fundamentals into actionable company-quality analytics.
    """

    def __init__(self, db=None):
        self.db = db or DatabaseManager()

    def analytics_for_ticker(self, ticker):
        ticker = str(ticker or "").strip().upper()
        row = self.fetch_fundamentals(ticker)
        if not row:
            return FundamentalAnalytics(ticker=ticker)

        metrics = self.derived_metrics(row)
        scores = self.component_scores(metrics)
        intelligence_score = self.weighted_score(scores)
        classification = self.classification(intelligence_score)
        flags = self.quality_flags(metrics, scores)
        commentary = self.commentary(metrics, scores, classification)
        summary = self.research_summary(metrics, scores, classification, flags)

        return FundamentalAnalytics(
            ticker=ticker,
            metrics=metrics,
            scores=scores,
            intelligence_score=intelligence_score,
            classification=classification,
            flags=flags,
            commentary=commentary,
            research_summary=summary,
        )

    def fetch_fundamentals(self, ticker):
        for method_name in ("fetch_fundamental_data", "get_fundamentals"):
            method = getattr(self.db, method_name, None)
            if method is None:
                continue
            row = method(ticker)
            if row:
                return self.row_dict(row)
        return {}

    def derived_metrics(self, row):
        revenue = self.value(row, "revenue", "total_revenue")
        gross_profit = self.value(row, "gross_profit")
        operating_income = self.value(row, "operating_income")
        net_income = self.value(row, "net_income")
        ebitda = self.value(row, "ebitda")
        enterprise_value = self.value(row, "enterprise_value", "ev")
        market_cap = self.value(row, "market_cap")
        free_cash_flow = self.value(row, "free_cash_flow", "fcf")

        metrics = {
            "revenue_growth_ttm": self.value(row, "revenue_growth_ttm", "revenue_growth"),
            "eps_growth_ttm": self.value(row, "eps_growth_ttm", "eps_growth"),
            "operating_margin": self.value(row, "operating_margin")
            or self.percent(operating_income, revenue),
            "gross_margin": self.value(row, "gross_margin")
            or self.percent(gross_profit, revenue),
            "net_margin": self.value(row, "net_margin")
            or self.percent(net_income, revenue),
            "roe": self.value(row, "roe", "return_on_equity"),
            "roa": self.value(row, "roa", "return_on_assets"),
            "current_ratio": self.value(row, "current_ratio"),
            "quick_ratio": self.value(row, "quick_ratio"),
            "debt_to_equity": self.value(row, "debt_to_equity", "debt_equity"),
            "interest_coverage": self.value(row, "interest_coverage"),
            "free_cash_flow": free_cash_flow,
            "free_cash_flow_margin": self.value(row, "free_cash_flow_margin")
            or self.percent(free_cash_flow, revenue),
            "enterprise_value": enterprise_value,
            "ev_to_ebitda": self.value(row, "ev_to_ebitda", "ev_ebitda")
            or self.ratio(enterprise_value, ebitda),
            "price_to_sales": self.value(row, "price_to_sales", "price_sales")
            or self.ratio(market_cap, revenue),
            "forward_pe": self.value(row, "forward_pe"),
            "trailing_pe": self.value(row, "trailing_pe", "pe_ratio"),
            "market_cap": market_cap,
        }
        return {
            key: value
            for key, value in metrics.items()
            if value is not None
        }

    def component_scores(self, metrics):
        return {
            "liquidity_score": self.average(
                self.score_high(metrics.get("current_ratio"), 1.0, 2.0),
                self.score_high(metrics.get("quick_ratio"), 0.8, 1.5),
            ),
            "profitability_score": self.average(
                self.score_high(metrics.get("gross_margin"), 20.0, 60.0),
                self.score_high(metrics.get("operating_margin"), 5.0, 30.0),
                self.score_high(metrics.get("net_margin"), 3.0, 20.0),
                self.score_high(metrics.get("roe"), 5.0, 25.0),
                self.score_high(metrics.get("roa"), 2.0, 12.0),
            ),
            "leverage_score": self.average(
                self.score_low(metrics.get("debt_to_equity"), 2.5, 0.5),
                self.score_high(metrics.get("interest_coverage"), 2.0, 10.0),
            ),
            "cash_flow_score": self.average(
                self.score_positive(metrics.get("free_cash_flow")),
                self.score_high(metrics.get("free_cash_flow_margin"), 0.0, 15.0),
            ),
            "growth_score": self.average(
                self.score_high(metrics.get("revenue_growth_ttm"), 0.0, 20.0),
                self.score_high(metrics.get("eps_growth_ttm"), 0.0, 25.0),
            ),
            "valuation_score": self.average(
                self.score_low(metrics.get("ev_to_ebitda"), 25.0, 10.0),
                self.score_low(metrics.get("price_to_sales"), 12.0, 3.0),
                self.score_low(metrics.get("forward_pe"), 35.0, 15.0),
                self.score_low(metrics.get("trailing_pe"), 40.0, 18.0),
            ),
        }

    @staticmethod
    def weighted_score(scores):
        weights = {
            "growth_score": 0.20,
            "profitability_score": 0.25,
            "liquidity_score": 0.15,
            "leverage_score": 0.15,
            "cash_flow_score": 0.15,
            "valuation_score": 0.10,
        }
        seen = [(scores[key], weight) for key, weight in weights.items() if scores.get(key) is not None]
        if not seen:
            return 0.0
        total_weight = sum(weight for _, weight in seen)
        return round(sum(score * weight for score, weight in seen) / total_weight, 1)

    @staticmethod
    def classification(score):
        if score >= 90:
            return "Elite"
        if score >= 80:
            return "Excellent"
        if score >= 70:
            return "Strong"
        if score >= 50:
            return "Average"
        if score >= 30:
            return "Weak"
        return "Critical"

    def quality_flags(self, metrics, scores):
        flags = []
        if (scores.get("liquidity_score") or 0) >= 75 and (scores.get("leverage_score") or 0) >= 75:
            flags.append("Strong Balance Sheet")
        if (scores.get("profitability_score") or 0) >= 80:
            flags.append("High Profitability")
        if self.number(metrics.get("free_cash_flow")) is not None and self.number(metrics.get("free_cash_flow")) < 0:
            flags.append("Negative Cash Flow")
        if self.number(metrics.get("debt_to_equity")) is not None and self.number(metrics.get("debt_to_equity")) >= 2.5:
            flags.append("Aggressive Leverage")
        if self.number(metrics.get("revenue_growth_ttm")) is not None and self.number(metrics.get("revenue_growth_ttm")) < 0:
            flags.append("Declining Revenue")
        if self.number(metrics.get("operating_margin")) is not None and self.number(metrics.get("gross_margin")) is not None:
            if self.number(metrics.get("operating_margin")) >= 0.45 * self.number(metrics.get("gross_margin")):
                flags.append("Improving Margins")
        if self.number(metrics.get("roe")) is not None and self.number(metrics.get("roe")) >= 20 and self.number(metrics.get("free_cash_flow")) not in (None, 0):
            flags.append("Excellent Capital Allocation")
        return flags

    def commentary(self, metrics, scores, classification):
        fragments = [f"Fundamental intelligence is {classification.lower()}"]
        growth = self.describe_growth(metrics)
        profitability = self.describe_profitability(scores)
        balance_sheet = self.describe_balance_sheet(scores)
        if growth:
            fragments.append(growth)
        if profitability:
            fragments.append(profitability)
        if balance_sheet:
            fragments.append(balance_sheet)
        return " while ".join(fragments) + "."

    def research_summary(self, metrics, scores, classification, flags):
        sentences = [
            f"The company earns a {classification} Fundamental Intelligence classification with a balanced score of {self.weighted_score(scores):.1f}.",
            self.describe_growth(metrics, sentence=True),
            self.describe_profitability(scores, sentence=True),
            self.describe_balance_sheet(scores, sentence=True),
            self.describe_cash_flow(metrics, scores),
            self.describe_valuation(scores),
        ]
        if flags:
            sentences.append("Key quality flags include " + ", ".join(flags[:4]) + ".")
        return " ".join(sentence for sentence in sentences if sentence)

    def describe_growth(self, metrics, sentence=False):
        revenue_growth = self.number(metrics.get("revenue_growth_ttm"))
        eps_growth = self.number(metrics.get("eps_growth_ttm"))
        if revenue_growth is None and eps_growth is None:
            return "growth data is limited" if not sentence else "Growth data is limited."
        if (revenue_growth or 0) >= 15 or (eps_growth or 0) >= 20:
            text = "strong revenue and earnings expansion"
        elif (revenue_growth or 0) < 0:
            text = "declining revenue trends"
        elif (revenue_growth or 0) >= 5:
            text = "moderate growth"
        else:
            text = "muted growth"
        return text if not sentence else text.capitalize() + "."

    @staticmethod
    def describe_profitability(scores, sentence=False):
        score = scores.get("profitability_score")
        if score is None:
            text = "profitability data is limited"
        elif score >= 80:
            text = "profitability is excellent"
        elif score >= 60:
            text = "profitability is solid"
        else:
            text = "profitability is under pressure"
        return text if not sentence else text.capitalize() + "."

    @staticmethod
    def describe_balance_sheet(scores, sentence=False):
        liquidity = scores.get("liquidity_score")
        leverage = scores.get("leverage_score")
        if liquidity is None and leverage is None:
            text = "balance sheet visibility is limited"
        elif (liquidity or 0) >= 70 and (leverage or 0) >= 70:
            text = "the balance sheet appears conservative"
        elif (leverage or 0) < 40:
            text = "leverage risk is elevated"
        else:
            text = "the balance sheet is adequate"
        return text if not sentence else text.capitalize() + "."

    @staticmethod
    def describe_cash_flow(metrics, scores):
        fcf = FundamentalAnalyticsService.number(metrics.get("free_cash_flow"))
        score = scores.get("cash_flow_score")
        if fcf is None and score is None:
            return "Cash flow data is limited."
        if fcf is not None and fcf < 0:
            return "Free cash flow is negative and requires monitoring."
        if (score or 0) >= 75:
            return "Cash generation supports reinvestment and shareholder returns."
        return "Cash flow support is moderate."

    @staticmethod
    def describe_valuation(scores):
        score = scores.get("valuation_score")
        if score is None:
            return "Valuation data is limited."
        if score >= 75:
            return "Valuation appears reasonable relative to available fundamentals."
        if score >= 50:
            return "Valuation is fair but not clearly discounted."
        return "Valuation appears demanding relative to fundamentals."

    @staticmethod
    def row_dict(row):
        if row is None:
            return {}
        if isinstance(row, dict):
            return dict(row)
        if hasattr(row, "keys"):
            return {key: row[key] for key in row.keys()}
        return {}

    @classmethod
    def value(cls, row, *keys):
        for key in keys:
            value = row.get(key)
            number = cls.number(value)
            if number is not None:
                return number
        return None

    @staticmethod
    def number(value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @classmethod
    def ratio(cls, numerator, denominator):
        numerator = cls.number(numerator)
        denominator = cls.number(denominator)
        if numerator is None or denominator in (None, 0):
            return None
        return numerator / denominator

    @classmethod
    def percent(cls, numerator, denominator):
        ratio = cls.ratio(numerator, denominator)
        return None if ratio is None else ratio * 100

    @staticmethod
    def average(*values):
        present = [value for value in values if value is not None]
        if not present:
            return None
        return sum(present) / len(present)

    @staticmethod
    def clamp(value):
        return max(0.0, min(100.0, value))

    @classmethod
    def score_high(cls, value, weak, strong):
        value = cls.number(value)
        if value is None:
            return None
        if strong == weak:
            return 50.0
        return cls.clamp((value - weak) / (strong - weak) * 100)

    @classmethod
    def score_low(cls, value, weak, strong):
        value = cls.number(value)
        if value is None:
            return None
        if weak == strong:
            return 50.0
        return cls.clamp((weak - value) / (weak - strong) * 100)

    @classmethod
    def score_positive(cls, value):
        value = cls.number(value)
        if value is None:
            return None
        if value < 0:
            return 0.0
        if value == 0:
            return 50.0
        return 100.0
