from types import SimpleNamespace

from database.manager import DatabaseManager
from services.bounce_analytics_service import BounceAnalyticsService
from services.fundamental_analytics_service import FundamentalAnalyticsService
from services.ohlcv_cache_access import fetch_ohlcv_frame
from services.risk_analytics_service import RiskAnalyticsService


class CandidateDetailDataService:
    """
    Assemble the read-only view model used by CandidateDetailWindow.
    """

    def __init__(self, db=None):
        self.db = db or DatabaseManager()
        self.bounce_analytics_service = BounceAnalyticsService(self.db)
        self.fundamental_analytics_service = FundamentalAnalyticsService(self.db)
        self.risk_analytics_service = RiskAnalyticsService()

    def get_candidate_detail(self, ticker, scored_candidate=None):
        ticker = self.normalize_ticker(ticker)
        if not ticker:
            return {}

        universe = self.fetch_universe(ticker)
        fundamentals = self.fetch_row("get_fundamentals", ticker)
        fundamental_analytics = self.fundamental_analytics_service.analytics_for_ticker(ticker)
        fundamental_metrics = (
            fundamental_analytics.as_metrics()
            if fundamental_analytics.metrics
            else {}
        )
        ohlcv = self.fetch_ohlcv(ticker)
        technical = self.fetch_latest_row("get_technical_indicators", ticker)
        support = self.fetch_first_row("get_support_levels", ticker)
        bounce = self.fetch_first_row("get_bounce_validations", ticker)
        bounce_analytics = self.bounce_analytics_service.analytics_for_ticker(ticker)
        bounce_metrics = (
            bounce_analytics.metrics()
            if bounce_analytics.primary_support is not None
            or bounce_analytics.historical_tests > 0
            else {}
        )
        institutional = self.fetch_row("get_institutional_metrics", ticker)
        ranked = self.fetch_ranked_candidate(ticker)

        metrics = {}
        self.merge(metrics, universe)
        self.merge(metrics, fundamentals)
        self.merge(metrics, fundamental_metrics)
        self.merge(metrics, ohlcv)
        self.merge(metrics, technical)
        self.merge(metrics, self.support_metrics(support))
        self.merge(metrics, self.bounce_metrics(bounce))
        self.merge(metrics, bounce_metrics)
        self.merge(metrics, institutional)
        self.merge(metrics, self.ranked_metrics(ranked))

        metrics.setdefault("ticker", ticker)
        metrics.setdefault("current_price", metrics.get("close"))
        metrics.setdefault("price", metrics.get("current_price"))
        metrics.setdefault(
            "institutional_status",
            "Available" if institutional else "Institutional data not configured",
        )
        risk_analytics = self.risk_analytics_service.analytics_for_metrics(
            ticker,
            metrics,
        )
        self.merge(metrics, risk_analytics.as_metrics())

        candidate = self.build_candidate(ticker, metrics, ranked, scored_candidate)
        detail = {
            "ticker": ticker,
            "candidate": candidate,
            "company_name": metrics.get("company_name"),
            "exchange": metrics.get("exchange"),
            "sector": metrics.get("sector"),
            "industry": metrics.get("industry"),
            "technical": self.technical_detail(metrics),
            "fundamentals": self.fundamental_detail(metrics),
            "risk": self.risk_detail(metrics),
            "support": self.support_metrics(support) or bounce_metrics,
            "bounce": self.bounce_detail(metrics),
            "bounce_history": bounce_analytics.history or self.bounce_history(metrics),
            "institutional": self.institutional_detail(institutional),
            "screening_result": self.ranked_metrics(ranked),
            "metrics": metrics,
        }
        return detail

    def fetch_universe(self, ticker):
        row = self.query_one(
            """
            SELECT company_name, exchange, sector, industry
            FROM universe_symbols
            WHERE UPPER(ticker) = ?
            """,
            (ticker,),
        )
        if row:
            return row
        return self.query_one(
            """
            SELECT company_name, exchange, sector, industry
            FROM market_universe
            WHERE UPPER(ticker) = ?
            """,
            (ticker,),
        ) or {}

    def fetch_ohlcv(self, ticker):
        frame = fetch_ohlcv_frame(self.db, ticker)
        if frame is None or frame.empty:
            return {}

        latest = frame.iloc[-1]
        result = {
            "current_price": latest.get("Close"),
            "close": latest.get("Close"),
            "latest_close_date": str(frame.index[-1].date())
            if hasattr(frame.index[-1], "date")
            else str(frame.index[-1]),
            "latest_volume": latest.get("Volume"),
            "volume": latest.get("Volume"),
        }
        if "High" in frame:
            result["high52"] = frame.tail(252)["High"].max()
            result["week_52_high"] = result["high52"]
        if "Low" in frame:
            result["low52"] = frame.tail(252)["Low"].min()
            result["week_52_low"] = result["low52"]
        return result

    def fetch_row(self, method_name, ticker):
        method = getattr(self.db, method_name, None)
        if method is None:
            return {}
        return self.row_dict(method(ticker))

    def fetch_first_row(self, method_name, ticker):
        rows = self.fetch_rows(method_name, ticker)
        return rows[0] if rows else {}

    def fetch_latest_row(self, method_name, ticker):
        rows = self.fetch_rows(method_name, ticker)
        return rows[-1] if rows else {}

    def fetch_rows(self, method_name, ticker):
        method = getattr(self.db, method_name, None)
        if method is None:
            return []
        return [self.row_dict(row) for row in method(ticker) or []]

    def fetch_ranked_candidate(self, ticker):
        method = getattr(self.db, "fetch_latest_ranked_candidates", None)
        if method is None:
            return None
        for candidate in method() or []:
            if self.normalize_ticker(self.value(candidate, "ticker")) == ticker:
                return candidate
        return None

    def build_candidate(self, ticker, metrics, ranked, scored_candidate):
        source = scored_candidate or ranked
        score = self.first_existing(
            self.value(source, "final_score"),
            self.value(source, "primary_score_value"),
            self.value(source, "institutional_bounce_score"),
        )
        explanation = self.first_existing(
            self.value(source, "explanation"),
            self.value(source, "summary"),
        )
        if isinstance(explanation, (list, tuple)):
            explanation_text = " ".join(str(item) for item in explanation if item)
        else:
            explanation_text = explanation
        summary_text = self.summary_text(explanation_text, metrics, ticker)

        return SimpleNamespace(
            ticker=ticker,
            company_name=metrics.get("company_name"),
            exchange=metrics.get("exchange"),
            sector=metrics.get("sector"),
            industry=metrics.get("industry"),
            current_price=metrics.get("current_price"),
            price=metrics.get("current_price"),
            primary_score_value=score,
            institutional_bounce_score=score,
            signal=self.value(source, "signal"),
            opportunity_rating=self.value(source, "opportunity_rating"),
            opportunity=self.value(source, "opportunity_rating"),
            risk_rating=self.value(source, "risk_rating") or metrics.get("risk_rating"),
            risk_recommendation=metrics.get("risk_recommendation"),
            summary=summary_text,
            reasons=[self.explanation_text(ticker, metrics)],
            metrics=metrics,
            grade=self.value(source, "grade"),
            confidence_level=self.value(source, "confidence_level"),
            setup_label=self.value(source, "setup_label"),
            warnings=list(self.value(source, "warnings") or []),
        )

    def summary_text(self, explanation_text, metrics, ticker):
        if explanation_text:
            return explanation_text
        risk_summary = metrics.get("risk_research_summary")
        fundamental_summary = metrics.get("fundamental_research_summary")
        if risk_summary and fundamental_summary:
            return f"{risk_summary} {fundamental_summary}"
        return risk_summary or fundamental_summary or self.explanation_text(ticker, metrics)

    def technical_detail(self, metrics):
        keys = {
            "current_price",
            "close",
            "latest_volume",
            "volume",
            "high52",
            "low52",
            "week_52_high",
            "week_52_low",
            "sma20",
            "sma50",
            "sma200",
            "ema20",
            "ema50",
            "ema200",
            "ema21",
            "rsi",
            "rsi14",
            "atr",
            "atr14",
            "macd",
            "macd_signal",
            "macd_histogram",
            "vwap",
            "avg_volume20",
            "average_volume_20",
            "relative_volume",
            "distance_from_ema20",
            "distance_from_ema50",
            "distance_from_ema200",
            "relative_strength_spy",
            "trend",
            "market_structure",
            "primary_support",
            "support_strength_score",
            "distance_to_support_pct",
            "bounce_success_rate",
            "historical_bounce_success_rate",
            "average_bounce_pct",
        }
        detail = {
            key: value
            for key, value in metrics.items()
            if key in keys and value not in (None, "")
        }
        if not detail:
            return {}
        detail["trend"] = detail.get("trend") or self.trend_label(detail)
        detail["market_structure"] = (
            detail.get("market_structure") or self.market_structure_label(detail)
        )
        return detail

    def fundamental_detail(self, metrics):
        return {
            key: metrics[key]
            for key in (
                "market_cap",
                "revenue_growth_ttm",
                "eps_growth_ttm",
                "roe",
                "gross_margin",
                "free_cash_flow",
                "debt_to_equity",
                "current_ratio",
                "quality_score",
                "operating_margin",
                "net_margin",
                "roa",
                "quick_ratio",
                "interest_coverage",
                "free_cash_flow_margin",
                "enterprise_value",
                "ev_to_ebitda",
                "price_to_sales",
                "forward_pe",
                "trailing_pe",
                "liquidity_score",
                "profitability_score",
                "leverage_score",
                "cash_flow_score",
                "growth_score",
                "valuation_score",
                "fundamental_intelligence_score",
                "fundamental_classification",
                "fundamental_quality_flags",
                "fundamental_commentary",
                "fundamental_research_summary",
            )
            if key in metrics and metrics[key] is not None
        }

    def risk_detail(self, metrics):
        risk = {}
        for key in (
            "debt_to_equity",
            "debt_risk_score",
            "excessive_debt",
            "overall_risk_score",
            "risk_rating",
            "fundamental_classification",
            "atr_risk",
            "support_failure_risk",
            "support_failure_risk_pct",
            "distance_from_support_risk",
            "volatility_risk",
            "volatility_pct",
            "trend_risk",
            "liquidity_risk",
            "gap_risk",
            "fundamental_risk",
            "market_structure_risk",
            "historical_bounce_reliability",
            "risk_recommendation",
            "risk_flags",
            "risk_commentary",
            "risk_research_summary",
            "price_above_support_10pct",
            "price_below_200dma",
            "recent_support_break",
        ):
            if key in metrics and metrics[key] is not None:
                risk[key] = metrics[key]
        return risk

    def support_metrics(self, support):
        if not support:
            return {}
        return {
            **support,
            "primary_support": support.get("zone_mid"),
            "support_price": support.get("zone_mid"),
            "support_level": support.get("zone_mid"),
            "support_zone_low": support.get("zone_low"),
            "support_zone_high": support.get("zone_high"),
            "support_tests": support.get("touches"),
            "support_strength": support.get("strength_score"),
            "support_strength_score": support.get("strength_score"),
            "distance_to_support_pct": support.get("distance_from_current_pct"),
            "latest_bounce_date": support.get("last_touch_date"),
            "most_recent_bounce": support.get("last_touch_date"),
        }

    def bounce_metrics(self, bounce):
        if not bounce:
            return {}
        return {
            **bounce,
            "support_tests": bounce.get("total_touches"),
            "bounce_count": bounce.get("total_touches"),
            "successful_support_tests": bounce.get("successful_bounces"),
            "validated_bounces": bounce.get("successful_bounces"),
            "bounce_success_pct": bounce.get("bounce_success_rate"),
            "historical_bounce_success_rate": bounce.get("bounce_success_rate"),
            "average_bounce": bounce.get("average_bounce_pct"),
            "median_bounce": bounce.get("median_bounce_pct"),
            "failed_support_breaks": bounce.get("failed_breakdowns"),
            "latest_bounce_date": bounce.get("validated_at"),
            "most_recent_bounce": bounce.get("validated_at"),
        }

    def bounce_detail(self, metrics):
        return {
            key: value
            for key, value in metrics.items()
            if key
            in {
                "support_tests",
                "bounce_count",
                "successful_bounces",
                "successful_support_tests",
                "validated_bounces",
                "bounce_success_rate",
                "bounce_success_pct",
                "historical_bounce_success_rate",
                "average_bounce",
                "average_bounce_pct",
                "median_bounce",
                "median_bounce_pct",
                "failed_support_breaks",
                "support_width",
                "latest_bounce_date",
                "most_recent_bounce",
                "bounce_quality",
                "bounce_quality_score",
                "primary_support",
                "support_price",
                "support_zone_low",
                "support_zone_high",
                "support_strength",
                "support_strength_score",
            }
        }

    def bounce_history(self, metrics):
        support = metrics.get("primary_support")
        if support in (None, ""):
            return []
        return [
            {
                "date": metrics.get("latest_bounce_date")
                or metrics.get("last_touch_date")
                or metrics.get("validated_at")
                or "Latest",
                "support_price": support,
                "low_price": metrics.get("support_zone_low"),
                "peak_price": metrics.get("high52"),
                "bounce_pct": metrics.get("average_bounce") or metrics.get("average_bounce_pct"),
                "days_to_peak": metrics.get("average_days_to_bounce_peak"),
                "successful": True,
            }
        ]

    def institutional_detail(self, institutional):
        if not institutional:
            return {
                "recent_13f_activity": "Institutional data not configured",
                "recent_13f_accumulation": "Institutional data not configured",
                "insider_net_activity": "Institutional data not configured",
                "status": "Institutional data not configured",
            }
        return dict(institutional)

    def ranked_metrics(self, ranked):
        if ranked is None:
            return {}
        category_scores = self.value(ranked, "category_scores") or {}
        return {
            "score": self.value(ranked, "final_score"),
            "final_score": self.value(ranked, "final_score"),
            "signal": self.value(ranked, "signal"),
            "opportunity_rating": self.value(ranked, "opportunity_rating"),
            "risk_rating": self.value(ranked, "risk_rating"),
            "explanation": self.value(ranked, "explanation"),
            "category_scores": category_scores,
            **category_scores,
        }

    def explanation_text(self, ticker, metrics):
        parts = []
        success = self.number(metrics.get("historical_bounce_success_rate"))
        support = self.number(metrics.get("primary_support"))
        trend = self.trend_label(metrics).lower()

        if success is not None and support is not None:
            parts.append(
                f"{ticker} has repeatedly respected support near ${support:,.2f} "
                f"with a {success:.0f}% historical bounce validation."
            )
        elif support is not None:
            parts.append(f"{ticker} is approaching a support area near ${support:,.2f}.")
        else:
            parts.append(f"{ticker} has a candidate profile assembled from available market data.")

        if "bullish" in trend or "positive" in trend:
            parts.append("Technical momentum remains positive.")
        elif "bearish" in trend:
            parts.append("Technical momentum is weakening and should be monitored.")
        else:
            parts.append("Technical momentum is mixed.")

        if metrics.get("institutional_status") == "Institutional data not configured":
            parts.append("Institutional data is not configured.")
        else:
            parts.append("Institutional support data is available for review.")

        return " ".join(parts)

    def trend_label(self, metrics):
        price = self.number(metrics.get("current_price") or metrics.get("close"))
        average50 = self.number(metrics.get("ema50"))
        if average50 is None:
            average50 = self.number(metrics.get("sma50"))
        average200 = self.number(metrics.get("ema200"))
        if average200 is None:
            average200 = self.number(metrics.get("sma200"))
        rsi = self.number(metrics.get("rsi14") or metrics.get("rsi"))
        macd = self.number(metrics.get("macd"))

        bullish_votes = 0
        bearish_votes = 0
        if price is not None and average50 is not None:
            bullish_votes += int(price >= average50)
            bearish_votes += int(price < average50)
        if average50 is not None and average200 is not None:
            bullish_votes += int(average50 >= average200)
            bearish_votes += int(average50 < average200)
        if rsi is not None:
            bullish_votes += int(rsi >= 50)
            bearish_votes += int(rsi < 45)
        if macd is not None:
            bullish_votes += int(macd > 0)
            bearish_votes += int(macd < 0)

        if bullish_votes > bearish_votes:
            return "Bullish"
        if bearish_votes > bullish_votes:
            return "Bearish"
        return "Neutral"

    def market_structure_label(self, metrics):
        price = self.number(metrics.get("current_price") or metrics.get("close"))
        ema20 = self.number(metrics.get("ema20"))
        ema50 = self.number(metrics.get("ema50"))
        ema200 = self.number(metrics.get("ema200"))

        if None not in (price, ema20, ema50, ema200):
            if price > ema20 > ema50 > ema200:
                return "Strong Bullish Structure"
            if price < ema20 < ema50 < ema200:
                return "Strong Bearish Structure"
        return self.trend_label(metrics)

    def query_one(self, sql, params):
        cursor = getattr(self.db, "cursor", None)
        if cursor is None:
            return {}
        cursor.execute(sql, params)
        return self.row_dict(cursor.fetchone())

    @classmethod
    def merge(cls, target, source):
        for key, value in (source or {}).items():
            if value not in (None, ""):
                target[key] = value

    @staticmethod
    def row_dict(row):
        if row is None:
            return {}
        if isinstance(row, dict):
            return dict(row)
        if hasattr(row, "keys"):
            return {key: row[key] for key in row.keys()}
        return {}

    @staticmethod
    def normalize_ticker(ticker):
        return str(ticker or "").strip().upper()

    @staticmethod
    def first_existing(*values):
        for value in values:
            if value not in (None, ""):
                return value
        return None

    @staticmethod
    def value(source, key):
        if source is None:
            return None
        if isinstance(source, dict):
            return source.get(key)
        return getattr(source, key, None)

    @staticmethod
    def number(value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
