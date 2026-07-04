"""
Trend strength orchestration service.
"""

from __future__ import annotations

from time import perf_counter

from analysis.trend_strength import TrendStrengthCalculator, TrendStrengthResult
from config.logging_config import logger
from database.manager import DatabaseManager
from indicators.moving_averages.sma import SMAIndicator


class TrendStrengthService:
    """
    Calculate trend strength using stored price history and SMA values.
    """

    def __init__(self, database_manager=None):
        self.db = database_manager or DatabaseManager()
        self.calculator = TrendStrengthCalculator()
        self.sma = SMAIndicator()

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

        sma_values = self.latest_sma_values(price_history)
        trend_result = self.calculator.calculate(price_history, sma_values)

        if self.is_skipped_result(trend_result):
            result["skipped"] = True
            result["warnings"] = trend_result.warnings
            result["elapsed_seconds"] = perf_counter() - started_at
            logger.info(
                "Skipping %s because trend strength could not be calculated",
                ticker,
            )
            return result

        result["processed"] = True
        result["result"] = trend_result
        result["warnings"] = trend_result.warnings
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
            "Starting trend strength calculation for %s tickers",
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
            "Finished trend strength calculation: %s processed, %s skipped in %.2fs",
            results["processed"],
            results["skipped"],
            results["elapsed_seconds"],
        )

        return results

    def latest_sma_values(self, price_history):
        try:
            dataframe = self.sma.calculate(price_history)
        except ValueError:
            return {
                "sma20": None,
                "sma50": None,
                "sma200": None,
            }

        return self.sma.latest_values(dataframe)

    def is_skipped_result(self, result: TrendStrengthResult):
        return (
            result.close_price is None
            or result.sma20 is None
            or result.sma50 is None
            or result.sma200 is None
        )

    def close(self):
        self.db.close()
