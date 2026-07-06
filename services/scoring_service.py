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
from services.candidate_detail_data_service import CandidateDetailDataService
from services.ohlcv_cache_access import fetch_ohlcv_frame


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
        service = CandidateDetailDataService(db=self.db)
        detail = service.get_candidate_detail(ticker, scored_candidate=candidate)
        detail["timestamp"] = candidate.timestamp
        return detail

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
        self.merge_latest_price(context, fetch_ohlcv_frame(self.db, ticker))
        if hasattr(self.db, "get_technical_indicators"):
            self.merge_row(
                context,
                self.last_row(self.db.get_technical_indicators(ticker)),
            )
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
    def last_row(rows):

        if not rows:
            return None

        return rows[-1]

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
