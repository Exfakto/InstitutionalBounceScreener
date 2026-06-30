"""
ATR risk orchestration service.
"""

from __future__ import annotations

from time import perf_counter

from analysis.atr_risk import ATRRiskCalculator, ATRRiskResult
from config.logging_config import logger
from database.manager import DatabaseManager


class ATRRiskService:
    """
    Calculate ATR risk metrics using stored OHLC price history.
    """

    def __init__(self):
        self.db = DatabaseManager()
        self.calculator = ATRRiskCalculator()

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

        atr_result = self.calculator.calculate(price_history)

        if self.is_skipped_result(atr_result):
            result["skipped"] = True
            result["warnings"] = atr_result.warnings
            result["elapsed_seconds"] = perf_counter() - started_at
            logger.info(
                "Skipping %s because ATR risk could not be calculated",
                ticker,
            )
            return result

        result["processed"] = True
        result["result"] = atr_result
        result["warnings"] = atr_result.warnings
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
            "Starting ATR risk calculation for %s tickers",
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
            "Finished ATR risk calculation: %s processed, %s skipped in %.2fs",
            results["processed"],
            results["skipped"],
            results["elapsed_seconds"],
        )

        return results

    def is_skipped_result(self, result: ATRRiskResult):
        return result.atr14 is None or result.atr_pct is None

    def close(self):
        self.db.close()
