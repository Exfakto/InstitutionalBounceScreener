from analysis import (
    BounceScore,
    CandidateScore,
    CompositeScore,
    InstitutionalScore,
    QualityScore,
    SupportScore,
    TechnicalScore,
)
from database.manager import DatabaseManager
from config.logging_config import logger


class ScoringService:
    """
    Read-only candidate scoring workflow.
    """

    def __init__(self, composite_intelligence_service=None):
        self.db = DatabaseManager()
        self.providers = [
            QualityScore(),
            InstitutionalScore(),
            TechnicalScore(),
            SupportScore(),
            BounceScore(),
        ]
        self.composite = CompositeScore()
        self.composite_intelligence_service = composite_intelligence_service
        self._owns_composite_intelligence_service = False

    def score_candidate(self, ticker):
        """
        Return a CandidateScore for one ticker.
        """

        context = self.build_context(ticker)
        return self.score_candidate_from_context(ticker, context)

    def score_candidate_from_context(self, ticker, context):
        """
        Return a CandidateScore using an existing metric context.
        """

        scores = [
            provider.calculate(context)
            for provider in self.providers
        ]
        score_context = dict(context)

        for score in scores:
            score_context[score.name] = score

        composite_score = self.composite.calculate(score_context)

        candidate = CandidateScore(
            ticker=ticker,
            scores=scores,
            composite_score=composite_score,
            metrics=dict(context),
        )

        return self.add_composite_intelligence(candidate, score_context)

    def add_composite_intelligence(self, candidate, score_context):
        """
        Attach Gen 2 composite intelligence when it can be calculated safely.
        """

        try:
            service = self.get_composite_intelligence_service()
            result = service.calculate_from_components(score_context)
        except Exception as error:
            logger.warning(
                "Gen 2 composite intelligence unavailable for %s: %s",
                candidate.ticker,
                error,
            )
            return candidate

        if result is None or self.is_empty_intelligence_result(result):
            return candidate

        return CandidateScore(
            ticker=candidate.ticker,
            scores=candidate.scores,
            composite_score=candidate.composite_score,
            institutional_bounce_score=result.institutional_bounce_score,
            composite_intelligence=result,
            composite_intelligence_component_scores=result.component_scores,
            metrics=dict(candidate.metrics),
            missing_components=result.missing_components,
            warnings=result.warnings,
            timestamp=candidate.timestamp,
        )

    def get_composite_intelligence_service(self):
        if getattr(self, "composite_intelligence_service", None) is None:
            from services.composite_intelligence_service import (
                CompositeIntelligenceService,
            )

            self.composite_intelligence_service = CompositeIntelligenceService(
                scoring_service=self
            )
            self._owns_composite_intelligence_service = True

        return self.composite_intelligence_service

    @staticmethod
    def is_empty_intelligence_result(result):
        return (
            result.institutional_bounce_score == 0.0
            and not result.component_scores
        )

    def get_candidate_detail(self, ticker):
        """
        Return read-only detail data for one scored ticker.
        """

        context = self.build_context(ticker)
        candidate = self.score_candidate_from_context(ticker, context)

        return {
            "ticker": ticker,
            "candidate": candidate,
            "timestamp": candidate.timestamp,
            "fundamentals": self.pick(
                context,
                [
                    "market_cap",
                    "revenue_growth_ttm",
                    "eps_growth_ttm",
                    "roe",
                    "gross_margin",
                    "free_cash_flow",
                    "debt_to_equity",
                    "current_ratio",
                    "quality_score",
                ],
            ),
            "institutional": self.pick(
                context,
                [
                    "institutional_ownership_pct",
                    "institutional_ownership_change_qoq",
                    "net_institutional_buying",
                    "insider_buying_flag",
                    "insider_selling_flag",
                    "institutional_score",
                ],
            ),
            "technical": self.pick(
                context,
                [
                    "close",
                    "sma20",
                    "sma50",
                    "sma200",
                    "rsi14",
                ],
            ),
            "support": self.pick(
                context,
                [
                    "zone_low",
                    "zone_high",
                    "zone_mid",
                    "touches",
                    "strength_score",
                    "distance_from_current_pct",
                ],
            ),
            "bounce": self.pick(
                context,
                [
                    "total_touches",
                    "successful_bounces",
                    "failed_breakdowns",
                    "neutral_touches",
                    "bounce_success_rate",
                    "average_bounce_pct",
                    "median_bounce_pct",
                    "average_days_to_bounce_peak",
                ],
            ),
        }

    def build_context(self, ticker):
        """
        Gather already-available metrics for one ticker.
        """

        context = {
            "ticker": ticker,
        }

        self.merge_row(context, self.db.get_fundamentals(ticker))
        self.normalize_fundamental_context(context)
        self.merge_row(context, self.db.get_institutional_metrics(ticker))
        self.merge_latest_price(context, self.db.get_price_history(ticker))
        self.merge_row(context, self.first_row(self.db.get_support_levels(ticker)))
        self.merge_row(context, self.first_row(self.db.get_bounce_validations(ticker)))

        return context

    @staticmethod
    def merge_row(context, row):

        if row is None:
            return

        if hasattr(row, "keys"):
            keys = row.keys()
        else:
            keys = row

        for key in keys:
            context[key] = row[key]

    @staticmethod
    def first_row(rows):

        if not rows:
            return None

        return rows[0]

    @staticmethod
    def merge_latest_price(context, dataframe):

        if dataframe is None or dataframe.empty:
            return

        latest = dataframe.iloc[-1]
        context["close"] = latest.get("Close")

    @staticmethod
    def pick(context, keys):

        return {
            key: context[key]
            for key in keys
            if key in context and context[key] is not None
        }

    @staticmethod
    def normalize_fundamental_context(context):
        """
        Populate stable scoring aliases from locally synchronized fundamentals.
        """

        aliases = {
            "revenue_growth": "revenue_growth_ttm",
            "eps_growth": "eps_growth_ttm",
        }

        for source, target in aliases.items():
            if context.get(target) is None and context.get(source) is not None:
                context[target] = context[source]
            elif context.get(source) is None and context.get(target) is not None:
                context[source] = context[target]

    def close(self):
        if getattr(self, "_owns_composite_intelligence_service", False):
            self.composite_intelligence_service.close()

        self.db.close()
