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


class ScoringService:
    """
    Read-only candidate scoring workflow.
    """

    def __init__(self):
        self.db = DatabaseManager()
        self.providers = [
            QualityScore(),
            InstitutionalScore(),
            TechnicalScore(),
            SupportScore(),
            BounceScore(),
        ]
        self.composite = CompositeScore()

    def score_candidate(self, ticker):
        """
        Return a CandidateScore for one ticker.
        """

        context = self.build_context(ticker)
        scores = [
            provider.calculate(context)
            for provider in self.providers
        ]
        score_context = dict(context)

        for score in scores:
            score_context[score.name] = score

        composite_score = self.composite.calculate(score_context)

        return CandidateScore(
            ticker=ticker,
            scores=scores,
            composite_score=composite_score,
        )

    def build_context(self, ticker):
        """
        Gather already-available metrics for one ticker.
        """

        context = {
            "ticker": ticker,
        }

        self.merge_row(context, self.db.get_fundamentals(ticker))
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

    def close(self):
        self.db.close()
