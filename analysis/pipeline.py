"""
Analysis pipeline orchestration.
"""

from __future__ import annotations

from time import perf_counter

from config.logging_config import logger
from services.scoring_service import ScoringService


class AnalysisPipeline:
    """
    Scores all active tickers and returns ranked candidates.
    """

    def __init__(self, scoring_service=None):
        self.scoring_service = scoring_service or ScoringService()

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

            candidates.append(candidate)

        candidates.sort(
            key=lambda candidate: candidate.composite_score.value,
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

    def close(self):
        self.scoring_service.close()
