"""
Support distance orchestration service.
"""

from __future__ import annotations

from time import perf_counter

from analysis.support_distance import (
    SupportDistanceCalculator,
    SupportDistanceResult,
)
from config.logging_config import logger
from database.manager import DatabaseManager


class SupportDistanceService:
    """
    Calculate support distance context from stored price, support, and bounce data.
    """

    def __init__(self, database_manager=None):
        self.db = database_manager or DatabaseManager()
        self.calculator = SupportDistanceCalculator()

    def calculate_for_ticker(self, ticker):
        started_at = perf_counter()
        price_history = self.db.get_price_history(ticker)

        result = {
            "ticker": ticker,
            "processed": False,
            "skipped": False,
            "result": None,
            "elapsed_seconds": 0.0,
            "warnings": [],
        }

        if price_history.empty or "Close" not in price_history.columns:
            result["skipped"] = True
            result["warnings"].append("Missing current price")
            result["elapsed_seconds"] = perf_counter() - started_at
            logger.info("Skipping %s because no current price exists", ticker)
            return result

        current_price = price_history["Close"].dropna()

        if current_price.empty:
            result["skipped"] = True
            result["warnings"].append("Missing current price")
            result["elapsed_seconds"] = perf_counter() - started_at
            logger.info("Skipping %s because no current price exists", ticker)
            return result

        support_levels = self.db.get_support_levels(ticker)
        bounce_validations = self.db.get_bounce_validations(ticker)

        support_result = self.calculator.calculate(
            float(current_price.iloc[-1]),
            support_levels,
            bounce_validations,
        )

        if self.is_skipped_result(support_result):
            result["skipped"] = True
            result["warnings"] = support_result.warnings
            result["elapsed_seconds"] = perf_counter() - started_at
            logger.info(
                "Skipping %s because support distance could not be calculated",
                ticker,
            )
            return result

        result["processed"] = True
        result["result"] = support_result
        result["warnings"] = support_result.warnings
        result["elapsed_seconds"] = perf_counter() - started_at

        return result

    def calculate_all(self, tickers=None):
        target_tickers = list(tickers) if tickers is not None else self.db.get_all_tickers()

        results = {
            "tickers": len(target_tickers),
            "processed": 0,
            "processed_tickers": [],
            "skipped": 0,
            "skipped_tickers": [],
            "results": {},
            "elapsed_seconds": 0.0,
        }

        started_at = perf_counter()

        logger.info(
            "Starting support distance calculation for %s tickers",
            len(target_tickers),
        )

        for ticker in target_tickers:
            ticker_result = self.calculate_for_ticker(ticker)

            if ticker_result["processed"]:
                results["processed"] += 1
                results["processed_tickers"].append(ticker)
                results["results"][ticker] = ticker_result["result"]
            else:
                results["skipped"] += 1
                results["skipped_tickers"].append(ticker)

        results["elapsed_seconds"] = perf_counter() - started_at

        logger.info(
            "Finished support distance calculation: %s processed, %s skipped in %.2fs",
            results["processed"],
            results["skipped"],
            results["elapsed_seconds"],
        )

        return results

    def is_skipped_result(self, result: SupportDistanceResult):
        return result.nearest_support_mid is None

    def close(self):
        self.db.close()
