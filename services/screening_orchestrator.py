"""
Backend orchestration for institutional bounce screening runs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

from services.bounce_composite_scoring_engine import BounceCompositeScoringEngine
from services.bounce_detection_engine import BounceDetectionEngine
from services.candidate_pipeline_adapter import CandidatePipelineAdapter
from services.candidate_ranking_engine import CandidateRankingEngine
from services.institutional_intelligence_engine import InstitutionalIntelligenceEngine
from services.support_zone_engine import SupportZoneEngine
from services.technical_indicator_engine import TechnicalIndicatorEngine


@dataclass(frozen=True)
class ScreeningRunResult:
    run_id: str
    started_at: str
    completed_at: str
    tickers_requested: int
    tickers_processed: int
    ranked_candidates: list = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class ScreeningOrchestrator:
    """
    Run the institutional bounce backend pipeline for a ticker list.
    """

    def __init__(
        self,
        price_history_provider=None,
        support_engine=None,
        bounce_engine=None,
        technical_engine=None,
        institutional_engine=None,
        composite_engine=None,
        pipeline_adapter=None,
        repository=None,
    ):
        self.price_history_provider = price_history_provider
        self.support_engine = support_engine or SupportZoneEngine()
        self.bounce_engine = bounce_engine or BounceDetectionEngine()
        self.technical_engine = technical_engine or TechnicalIndicatorEngine()
        self.institutional_engine = institutional_engine or InstitutionalIntelligenceEngine()
        self.composite_engine = composite_engine or BounceCompositeScoringEngine()
        self.pipeline_adapter = pipeline_adapter
        if self.pipeline_adapter is None and repository is not None:
            self.pipeline_adapter = CandidatePipelineAdapter(repository)

    def run(
        self,
        tickers,
        run_id=None,
        minimum_score=None,
        allow_low_confidence=False,
    ):
        run_id = str(run_id or uuid4())
        started_at = self.timestamp()
        normalized_tickers = self.normalize_tickers(tickers)
        warnings = []
        errors = []
        composite_scores = []
        processed = 0

        if not normalized_tickers:
            warnings.append("No tickers provided")
            pipeline_result = self.persist_scores(
                composite_scores,
                run_id,
                minimum_score,
                allow_low_confidence,
                warnings,
                errors,
            )
            return ScreeningRunResult(
                run_id=run_id,
                started_at=started_at,
                completed_at=self.timestamp(),
                tickers_requested=0,
                tickers_processed=0,
                ranked_candidates=pipeline_result.ranked_candidates,
                warnings=[*warnings, *pipeline_result.warnings],
                errors=errors,
            )

        for ticker in normalized_tickers:
            try:
                prices = self.fetch_price_history(ticker)
                support_result = self.support_engine.detect_support_zones(ticker, prices)
                zones = self.value(support_result, "zones") or []
                bounce_result = self.bounce_engine.analyze_bounces(ticker, prices, zones)
                technical_result = self.technical_engine.calculate(prices, ticker=ticker)
                institutional_result = self.institutional_engine.score_ticker(ticker)
                composite_result = self.composite_engine.score(
                    ticker=ticker,
                    support=support_result,
                    bounce=bounce_result,
                    technical=technical_result,
                    institutional=institutional_result,
                )
                composite_scores.append(composite_result)
                processed += 1
                self.collect_warnings(
                    ticker,
                    warnings,
                    support_result,
                    bounce_result,
                    technical_result,
                    institutional_result,
                    composite_result,
                )
            except Exception as exc:
                errors.append(f"{ticker}: {exc}")

        pipeline_result = self.persist_scores(
            composite_scores,
            run_id,
            minimum_score,
            allow_low_confidence,
            warnings,
            errors,
        )

        return ScreeningRunResult(
            run_id=run_id,
            started_at=started_at,
            completed_at=self.timestamp(),
            tickers_requested=len(normalized_tickers),
            tickers_processed=processed,
            ranked_candidates=pipeline_result.ranked_candidates,
            warnings=self.unique([*warnings, *pipeline_result.warnings]),
            errors=errors,
        )

    def persist_scores(
        self,
        composite_scores,
        run_id,
        minimum_score,
        allow_low_confidence,
        warnings,
        errors,
    ):
        if self.pipeline_adapter is None:
            warnings.append("No candidate pipeline adapter configured")
            if minimum_score is None:
                ranking_result = CandidateRankingEngine().rank_composite_scores(
                    composite_scores,
                    allow_low_confidence=allow_low_confidence,
                )
            else:
                ranking_result = CandidateRankingEngine().rank_composite_scores(
                    composite_scores,
                    minimum_score=minimum_score,
                    allow_low_confidence=allow_low_confidence,
                )
            return ranking_result

        try:
            if minimum_score is None:
                return self.pipeline_adapter.run(
                    composite_scores,
                    run_id=run_id,
                    allow_low_confidence=allow_low_confidence,
                )
            return self.pipeline_adapter.run(
                composite_scores,
                run_id=run_id,
                minimum_score=minimum_score,
                allow_low_confidence=allow_low_confidence,
            )
        except Exception as exc:
            errors.append(f"Pipeline persistence failed: {exc}")
            if minimum_score is None:
                ranking_result = CandidateRankingEngine().rank_composite_scores(
                    composite_scores,
                    allow_low_confidence=allow_low_confidence,
                )
            else:
                ranking_result = CandidateRankingEngine().rank_composite_scores(
                    composite_scores,
                    minimum_score=minimum_score,
                    allow_low_confidence=allow_low_confidence,
                )
            return ranking_result

    def fetch_price_history(self, ticker):
        if self.price_history_provider is None:
            return []

        if hasattr(self.price_history_provider, "get_price_history"):
            prices = self.price_history_provider.get_price_history(ticker)
        elif hasattr(self.price_history_provider, "fetch_price_history"):
            prices = self.price_history_provider.fetch_price_history(ticker)
        else:
            prices = self.price_history_provider(ticker)

        return self.normalize_price_rows(prices)

    @staticmethod
    def normalize_price_rows(prices):
        if prices is None:
            return []
        if hasattr(prices, "iterrows"):
            rows = []
            for index, row in prices.iterrows():
                rows.append(
                    {
                        "date": index,
                        "open": row.get("Open", row.get("open")),
                        "high": row.get("High", row.get("high")),
                        "low": row.get("Low", row.get("low")),
                        "close": row.get("Close", row.get("close")),
                        "volume": row.get("Volume", row.get("volume")),
                    }
                )
            return rows
        return list(prices or [])

    @staticmethod
    def collect_warnings(ticker, warnings, *results):
        for result in results:
            if isinstance(result, (list, tuple)):
                for item in result:
                    ScreeningOrchestrator.collect_warnings(ticker, warnings, item)
                continue
            for warning in ScreeningOrchestrator.value(result, "warnings") or []:
                warnings.append(f"{ticker}: {warning}")

    @staticmethod
    def normalize_tickers(tickers):
        normalized = []
        for ticker in tickers or []:
            value = str(ticker or "").strip().upper()
            if value and value not in normalized:
                normalized.append(value)
        return normalized

    @staticmethod
    def timestamp():
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def value(source, key):
        if source is None:
            return None
        if isinstance(source, dict):
            return source.get(key)
        return getattr(source, key, None)

    @staticmethod
    def unique(values):
        unique_values = []
        for value in values:
            if value and value not in unique_values:
                unique_values.append(value)
        return unique_values
