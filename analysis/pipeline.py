"""
Analysis pipeline orchestration.
"""

from __future__ import annotations

from time import perf_counter

from dataclasses import replace

from analysis.institutional_checklist import InstitutionalChecklistEvaluator
from analysis.opportunity_rating import OpportunityRatingCalculator
from analysis.trade_thesis import TradeThesisGenerator
from config.logging_config import logger
from services.scoring_service import ScoringService


class AnalysisPipeline:
    """
    Scores all active tickers and returns ranked candidates.
    """

    def __init__(self, scoring_service=None):
        self.scoring_service = scoring_service or ScoringService()
        self.opportunity_calculator = OpportunityRatingCalculator()
        self.checklist_evaluator = InstitutionalChecklistEvaluator()
        self.trade_thesis_generator = TradeThesisGenerator()

    def run(self):
        """
        Run candidate scoring for all active tickers.
        """

        started_at = perf_counter()
        tickers = self.get_active_tickers()
        candidates = []
        skipped = 0

        for ticker in tickers:

            try:
                candidate = self.scoring_service.score_candidate(ticker)
            except Exception:
                logger.exception(
                    "Failed to score candidate %s",
                    ticker,
                )
                skipped += 1
                continue

            candidate = self.add_decision_support(candidate)
            candidates.append(candidate)

        candidates.sort(
            key=lambda candidate: candidate.primary_score_value,
            reverse=True,
        )

        return {
            "total_tickers": len(tickers),
            "processed": len(candidates),
            "skipped": skipped,
            "candidates": candidates,
            "elapsed_seconds": perf_counter() - started_at,
        }

    def get_active_tickers(self):
        """
        Read active tickers through the scoring service database.
        """

        return self.scoring_service.db.get_all_tickers()

    def add_institutional_checklist(self, candidate):
        """
        Backward-compatible wrapper for decision support enrichment.
        """

        return self.add_decision_support(candidate)

    def add_decision_support(self, candidate):
        """
        Attach read-only decision support outputs to a scored candidate.
        """

        metrics = self.metrics_for_candidate(candidate)
        opportunity = self.opportunity_calculator.calculate(metrics)
        metrics["opportunity_rating_score"] = opportunity.rating_score
        metrics["opportunity_rating"] = opportunity
        checklist = self.checklist_evaluator.evaluate(metrics)
        metrics["institutional_checklist"] = checklist
        metrics["ticker"] = candidate.ticker
        metrics["warnings"] = list(candidate.warnings)
        thesis = self.trade_thesis_generator.generate(metrics)

        return replace(
            candidate,
            opportunity_rating=opportunity,
            institutional_checklist=checklist,
            trade_thesis=thesis,
        )

    @staticmethod
    def metrics_for_candidate(candidate):
        metrics = {
            score.name: score.value
            for score in candidate.scores
        }
        metrics.update(candidate.composite_intelligence_component_scores)
        metrics["composite_score"] = candidate.composite_score.value

        if candidate.institutional_bounce_score is not None:
            metrics["institutional_bounce_score"] = (
                candidate.institutional_bounce_score
            )

        return metrics

    def close(self):
        self.scoring_service.close()
