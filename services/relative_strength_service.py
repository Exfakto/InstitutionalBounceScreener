"""
Relative strength orchestration service.
"""

from __future__ import annotations

from time import perf_counter

from analysis.relative_strength import (
    RelativeStrengthCalculator,
    RelativeStrengthResult,
)
from config.logging_config import logger
from database.manager import DatabaseManager
from services.ohlcv_cache_access import fetch_ohlcv_frame


class RelativeStrengthService:
    """
    Calculate relative strength versus a benchmark using stored price history.
    """

    def __init__(self, benchmark_ticker="SPY"):
        self.db = DatabaseManager()
        self.calculator = RelativeStrengthCalculator()
        self.benchmark_ticker = benchmark_ticker

    def calculate_relative_strength(self, tickers=None):
        target_tickers = list(tickers) if tickers is not None else self.db.get_all_tickers()

        results = {
            "benchmark_ticker": self.benchmark_ticker,
            "tickers": len(target_tickers),
            "processed": 0,
            "processed_tickers": [],
            "skipped": 0,
            "skipped_tickers": [],
            "results": {},
            "elapsed_seconds": 0.0,
            "benchmark_available": True,
        }

        started_at = perf_counter()

        benchmark_history = fetch_ohlcv_frame(self.db, self.benchmark_ticker)

        if benchmark_history.empty:
            results["benchmark_available"] = False
            results["skipped"] = len(target_tickers)
            results["skipped_tickers"] = list(target_tickers)
            results["skip_reason"] = (
                f"Benchmark price history not found for {self.benchmark_ticker}"
            )
            results["elapsed_seconds"] = perf_counter() - started_at

            logger.info(results["skip_reason"])

            return results

        logger.info(
            "Starting relative strength calculation for %s tickers vs %s",
            len(target_tickers),
            self.benchmark_ticker,
        )

        for ticker in target_tickers:
            if ticker == self.benchmark_ticker:
                continue

            stock_history = fetch_ohlcv_frame(self.db, ticker)

            if stock_history.empty:
                logger.info("Skipping %s because no price history exists", ticker)
                results["skipped"] += 1
                results["skipped_tickers"].append(ticker)
                continue

            relative_strength = self.calculator.calculate(
                stock_history,
                benchmark_history,
            )

            if self.is_skipped_result(relative_strength):
                logger.info(
                    "Skipping %s because relative strength could not be calculated",
                    ticker,
                )
                results["skipped"] += 1
                results["skipped_tickers"].append(ticker)
                continue

            results["processed"] += 1
            results["processed_tickers"].append(ticker)
            results["results"][ticker] = relative_strength

        results["elapsed_seconds"] = perf_counter() - started_at

        logger.info(
            "Finished relative strength calculation: %s processed, %s skipped in %.2fs",
            results["processed"],
            results["skipped"],
            results["elapsed_seconds"],
        )

        return results

    def is_skipped_result(self, result: RelativeStrengthResult):
        return (
            result.rs_3m is None
            and result.rs_6m is None
            and result.rs_12m is None
        )

    def close(self):
        self.db.close()
