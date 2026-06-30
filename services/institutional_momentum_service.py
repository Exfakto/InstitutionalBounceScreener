"""
Institutional momentum orchestration service.
"""

from __future__ import annotations

from time import perf_counter

import pandas as pd

from analysis.institutional_momentum import (
    InstitutionalMomentumCalculator,
    InstitutionalMomentumResult,
)
from config.logging_config import logger
from institutional import InstitutionalImporter


class InstitutionalMomentumService:
    """
    Calculate institutional momentum from CSV-based institutional history.
    """

    def __init__(self, csv_path=None):
        self.importer = InstitutionalImporter(csv_path)
        self.calculator = InstitutionalMomentumCalculator()

    def calculate_for_ticker(self, ticker):
        started_at = perf_counter()
        dataframe = self.importer.load()

        return self.calculate_for_ticker_from_dataframe(
            ticker,
            dataframe,
            started_at=started_at,
        )

    def calculate_all(self, tickers=None):
        started_at = perf_counter()
        dataframe = self.importer.load()

        if dataframe.empty:
            return {
                "tickers": 0,
                "processed": 0,
                "processed_tickers": [],
                "skipped": 0,
                "skipped_tickers": [],
                "results": {},
                "elapsed_seconds": perf_counter() - started_at,
            }

        target_tickers = (
            list(tickers)
            if tickers is not None
            else sorted(dataframe["ticker"].dropna().unique().tolist())
        )

        results = {
            "tickers": len(target_tickers),
            "processed": 0,
            "processed_tickers": [],
            "skipped": 0,
            "skipped_tickers": [],
            "results": {},
            "elapsed_seconds": 0.0,
        }

        logger.info(
            "Starting institutional momentum calculation for %s tickers",
            len(target_tickers),
        )

        for ticker in target_tickers:
            ticker_result = self.calculate_for_ticker_from_dataframe(
                ticker,
                dataframe,
            )

            if ticker_result["processed"]:
                results["processed"] += 1
                results["processed_tickers"].append(ticker)
                results["results"][ticker] = ticker_result["result"]
            else:
                results["skipped"] += 1
                results["skipped_tickers"].append(ticker)

        results["elapsed_seconds"] = perf_counter() - started_at

        logger.info(
            "Finished institutional momentum calculation: %s processed, %s skipped in %.2fs",
            results["processed"],
            results["skipped"],
            results["elapsed_seconds"],
        )

        return results

    def calculate_for_ticker_from_dataframe(
        self,
        ticker,
        dataframe,
        started_at=None,
    ):
        started_at = started_at or perf_counter()
        normalized_ticker = str(ticker).upper().strip()

        result = {
            "ticker": normalized_ticker,
            "processed": False,
            "skipped": False,
            "result": None,
            "elapsed_seconds": 0.0,
            "warnings": [],
        }

        if dataframe.empty or "ticker" not in dataframe.columns:
            result["skipped"] = True
            result["warnings"].append("Missing institutional history")
            result["elapsed_seconds"] = perf_counter() - started_at
            return result

        rows = dataframe[dataframe["ticker"] == normalized_ticker].copy()

        if rows.empty:
            result["skipped"] = True
            result["warnings"].append("Missing institutional history")
            result["elapsed_seconds"] = perf_counter() - started_at
            return result

        rows = self.sort_rows(rows)
        latest = rows.iloc[-1].to_dict()
        previous = rows.iloc[-2].to_dict() if len(rows) >= 2 else {}
        history = rows.to_dict("records")

        momentum = self.calculator.calculate(
            current_ownership=latest.get("institutional_ownership_pct"),
            previous_ownership=previous.get("institutional_ownership_pct"),
            ownership_history=history,
            insider_metrics=latest,
        )

        if self.is_skipped_result(momentum):
            result["skipped"] = True
            result["warnings"] = momentum.warnings
            result["elapsed_seconds"] = perf_counter() - started_at
            return result

        result["processed"] = True
        result["result"] = momentum
        result["warnings"] = momentum.warnings
        result["elapsed_seconds"] = perf_counter() - started_at

        return result

    @staticmethod
    def sort_rows(dataframe):
        if "report_date" not in dataframe.columns:
            return dataframe

        sorted_frame = dataframe.copy()
        sorted_frame["report_date"] = pd.to_datetime(
            sorted_frame["report_date"],
            errors="coerce",
        )

        return sorted_frame.sort_values("report_date")

    @staticmethod
    def is_skipped_result(result: InstitutionalMomentumResult):
        return result.current_ownership_pct is None
