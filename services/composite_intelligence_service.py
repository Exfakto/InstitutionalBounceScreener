"""
Generation 2 composite intelligence orchestration service.
"""

from __future__ import annotations

from time import perf_counter

from analysis.composite_intelligence import (
    CompositeIntelligenceCalculator,
    CompositeIntelligenceResult,
)
from analysis.earnings_score import EarningsScore
from config.logging_config import logger
from services.atr_risk_service import ATRRiskService
from services.institutional_momentum_service import InstitutionalMomentumService
from services.relative_strength_service import RelativeStrengthService
from services.scoring_service import ScoringService
from services.support_distance_service import SupportDistanceService
from services.trend_strength_service import TrendStrengthService
from services.volume_intelligence_service import VolumeIntelligenceService


class CompositeIntelligenceService:
    """
    Gather available analytics and calculate Gen 2 composite intelligence.
    """

    def __init__(self):
        self.scoring_service = ScoringService()
        self.relative_strength_service = RelativeStrengthService()
        self.volume_service = VolumeIntelligenceService()
        self.trend_service = TrendStrengthService()
        self.atr_service = ATRRiskService()
        self.support_distance_service = SupportDistanceService()
        self.institutional_momentum_service = InstitutionalMomentumService()
        self.earnings_score = EarningsScore()
        self.calculator = CompositeIntelligenceCalculator()

    def calculate_for_ticker(self, ticker):
        started_at = perf_counter()
        result = {
            "ticker": ticker,
            "processed": False,
            "skipped": False,
            "result": None,
            "component_scores": {},
            "warnings": [],
            "elapsed_seconds": 0.0,
        }

        component_scores = {}
        warnings = []

        self.add_core_scores(ticker, component_scores, warnings)
        self.add_relative_strength_score(ticker, component_scores, warnings)
        self.add_volume_score(ticker, component_scores, warnings)
        self.add_trend_score(ticker, component_scores, warnings)
        self.add_atr_risk_score(ticker, component_scores, warnings)
        self.add_support_distance_score(ticker, component_scores, warnings)
        self.add_earnings_score(ticker, component_scores, warnings)
        self.add_institutional_momentum_score(ticker, component_scores, warnings)

        composite = self.calculator.calculate(component_scores)

        warnings.extend(composite.warnings)
        result["component_scores"] = component_scores
        result["warnings"] = warnings
        result["elapsed_seconds"] = perf_counter() - started_at

        if self.is_skipped_result(composite):
            result["skipped"] = True
            logger.info(
                "Skipping %s because no composite intelligence components were available",
                ticker,
            )
            return result

        result["processed"] = True
        result["result"] = composite

        return result

    def calculate_all(self, tickers=None):
        target_tickers = (
            list(tickers)
            if tickers is not None
            else self.scoring_service.db.get_all_tickers()
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

        started_at = perf_counter()

        logger.info(
            "Starting composite intelligence calculation for %s tickers",
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
            "Finished composite intelligence calculation: %s processed, %s skipped in %.2fs",
            results["processed"],
            results["skipped"],
            results["elapsed_seconds"],
        )

        return results

    def add_core_scores(self, ticker, component_scores, warnings):
        try:
            candidate = self.scoring_service.score_candidate(ticker)
        except Exception as error:
            warnings.append(f"Core scoring unavailable: {error}")
            return

        for score in candidate.scores:
            component_scores[score.name] = score.value

    def add_relative_strength_score(self, ticker, component_scores, warnings):
        try:
            summary = self.relative_strength_service.calculate_relative_strength([ticker])
        except Exception as error:
            warnings.append(f"Relative strength unavailable: {error}")
            return

        result = summary.get("results", {}).get(ticker)

        if result is None:
            warnings.append("Relative strength score missing")
            return

        component_scores["relative_strength_score"] = result.rs_score

    def add_volume_score(self, ticker, component_scores, warnings):
        self.add_service_score(
            ticker,
            self.volume_service,
            "volume_score",
            "volume_score",
            component_scores,
            warnings,
        )

    def add_trend_score(self, ticker, component_scores, warnings):
        self.add_service_score(
            ticker,
            self.trend_service,
            "trend_score",
            "trend_score",
            component_scores,
            warnings,
        )

    def add_atr_risk_score(self, ticker, component_scores, warnings):
        self.add_service_score(
            ticker,
            self.atr_service,
            "risk_score",
            "risk_score",
            component_scores,
            warnings,
        )

    def add_support_distance_score(self, ticker, component_scores, warnings):
        self.add_service_score(
            ticker,
            self.support_distance_service,
            "entry_quality_score",
            "entry_quality_score",
            component_scores,
            warnings,
        )

    def add_earnings_score(self, ticker, component_scores, warnings):
        db = getattr(self.scoring_service, "db", None)

        if db is None or not hasattr(db, "get_earnings"):
            warnings.append("Earnings score missing")
            return

        row = db.get_earnings(ticker)

        if row is None:
            warnings.append("Earnings score missing")
            return

        metrics = self.row_to_dict(row)
        existing = metrics.get("earnings_risk_score")

        if existing is not None:
            component_scores["earnings_risk_score"] = existing
            return

        component_scores["earnings_risk_score"] = (
            self.earnings_score.calculate(metrics).value
        )

    def add_institutional_momentum_score(self, ticker, component_scores, warnings):
        try:
            summary = self.institutional_momentum_service.calculate_for_ticker(ticker)
        except Exception as error:
            warnings.append(f"Institutional momentum unavailable: {error}")
            return

        result = summary.get("result")

        if result is None:
            warnings.append("Institutional momentum score missing")
            return

        component_scores["institutional_momentum_score"] = result.momentum_score

    def add_service_score(
        self,
        ticker,
        service,
        result_attribute,
        component_name,
        component_scores,
        warnings,
    ):
        try:
            summary = service.calculate_for_ticker(ticker)
        except Exception as error:
            warnings.append(f"{component_name} unavailable: {error}")
            return

        result = summary.get("result")

        if result is None:
            warnings.append(f"{component_name} missing")
            return

        component_scores[component_name] = getattr(result, result_attribute)

    @staticmethod
    def row_to_dict(row):
        if isinstance(row, dict):
            return dict(row)

        if hasattr(row, "keys"):
            return {
                key: row[key]
                for key in row.keys()
            }

        return {}

    @staticmethod
    def is_skipped_result(result: CompositeIntelligenceResult):
        return result.institutional_bounce_score == 0.0 and not result.component_scores

    def close(self):
        for service in [
            self.scoring_service,
            self.relative_strength_service,
            self.volume_service,
            self.trend_service,
            self.atr_service,
            self.support_distance_service,
        ]:
            if hasattr(service, "close"):
                service.close()
