"""
Volume intelligence orchestration service.
"""

from __future__ import annotations

from time import perf_counter

from analysis.volume_intelligence import (
    VolumeIntelligenceCalculator,
    VolumeIntelligenceResult,
)
from config.logging_config import logger
from database.manager import DatabaseManager


class VolumeIntelligenceService:
    """
    Calculate volume intelligence using stored price history.
    """

    def __init__(self):
        self.db = DatabaseManager()
        self.calculator = VolumeIntelligenceCalculator()

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

        if price_history.empty:
            result["skipped"] = True
            result["warnings"].append("Missing price history")
            result["elapsed_seconds"] = perf_counter() - started_at
            logger.info("Skipping %s because no price history exists", ticker)
            return result

        volume_result = self.calculator.calculate(price_history)

        if self.is_skipped_result(volume_result):
            result["skipped"] = True
            result["warnings"] = volume_result.warnings
            result["elapsed_seconds"] = perf_counter() - started_at
            logger.info(
                "Skipping %s because volume intelligence could not be calculated",
                ticker,
            )
            return result

        result["processed"] = True
        result["result"] = volume_result
        result["warnings"] = volume_result.warnings
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
            "Starting volume intelligence calculation for %s tickers",
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
            "Finished volume intelligence calculation: %s processed, %s skipped in %.2fs",
            results["processed"],
            results["skipped"],
            results["elapsed_seconds"],
        )

        return results

    def is_skipped_result(self, result: VolumeIntelligenceResult):
        return result.relative_volume is None or result.dollar_volume is None

    def close(self):
        self.db.close()
