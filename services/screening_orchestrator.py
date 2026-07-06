"""
Backend orchestration for institutional bounce screening runs.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

from services.bounce_composite_scoring_engine import BounceCompositeScoringEngine
from services.bounce_detection_engine import BounceDetectionEngine
from services.candidate_pipeline_adapter import CandidatePipelineAdapter
from services.candidate_ranking_engine import CandidateRankingEngine
from services.institutional_data_provider import (
    LocalInstitutionalDataProvider,
    UnavailableInstitutionalDataProvider,
)
from services.institutional_intelligence_engine import InstitutionalIntelligenceEngine
from services.ohlcv_cache_access import fetch_ohlcv_rows
from services.support_zone_engine import SupportZoneEngine
from services.technical_indicator_engine import TechnicalIndicatorEngine


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ScreeningRunResult:
    run_id: str
    status: str
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
        institutional_data_provider=None,
        composite_engine=None,
        pipeline_adapter=None,
        repository=None,
        market_data_refresh_service=None,
        batch_size=50,
    ):
        self.price_history_provider = price_history_provider
        self.market_data_refresh_service = market_data_refresh_service
        self.price_history_warnings_by_ticker = {}
        self.support_engine = support_engine or SupportZoneEngine()
        self.bounce_engine = bounce_engine or BounceDetectionEngine()
        self.technical_engine = technical_engine or TechnicalIndicatorEngine()
        self.pipeline_adapter = pipeline_adapter
        if self.pipeline_adapter is None and repository is not None:
            self.pipeline_adapter = CandidatePipelineAdapter(repository)
        self.repository = repository or getattr(self.pipeline_adapter, "repository", None)
        institutional_data_provider = (
            institutional_data_provider
            or self.default_institutional_data_provider(self.repository)
        )
        self.institutional_engine = institutional_engine or InstitutionalIntelligenceEngine(
            provider=institutional_data_provider
        )
        self.composite_engine = composite_engine or BounceCompositeScoringEngine()
        self.batch_size = max(1, int(batch_size or 50))

    @staticmethod
    def default_institutional_data_provider(repository):
        if repository is None:
            return UnavailableInstitutionalDataProvider()
        if not all(
            hasattr(repository, method_name)
            for method_name in (
                "get_institutional_data",
                "get_institutional_data_for_tickers",
            )
        ):
            return UnavailableInstitutionalDataProvider()
        return LocalInstitutionalDataProvider(repository)

    def run(
        self,
        tickers,
        run_id=None,
        minimum_score=None,
        allow_low_confidence=False,
        progress_callback=None,
        cancellation_callback=None,
        batch_size=None,
    ):
        run_id = str(run_id or uuid4())
        started_at = self.timestamp()
        normalized_tickers = self.normalize_tickers(tickers)
        warnings = []
        errors = []
        composite_scores = []
        run_cache = {
            "prices": {},
            "support": {},
            "bounce": {},
            "technical": {},
            "institutional": {},
            "composite": {},
        }
        self.log_institutional_provider()
        run_cache["institutional"].update(
            self.load_institutional_signals(normalized_tickers)
        )
        processed = 0
        cancelled = False
        self.create_run_record(
            run_id,
            started_at,
            tickers_requested=len(normalized_tickers),
        )

        if not normalized_tickers:
            warnings.append("No tickers provided")
            self.report_progress(
                progress_callback,
                total=0,
                processed=0,
                current_ticker=None,
                status_message="No tickers provided",
            )
            pipeline_result = self.persist_scores(
                composite_scores,
                run_id,
                minimum_score,
                allow_low_confidence,
                warnings,
                errors,
            )
            final_warnings = self.unique([*warnings, *pipeline_result.warnings])
            completed_at = self.timestamp()
            status = self.final_status(0, 0, errors, cancelled=False)
            self.update_run_record(
                run_id,
                status=status,
                completed_at=completed_at,
                tickers_requested=0,
                tickers_processed=0,
                candidate_count=len(pipeline_result.ranked_candidates),
                warnings=final_warnings,
                errors=errors,
            )
            return ScreeningRunResult(
                run_id=run_id,
                status=status,
                started_at=started_at,
                completed_at=completed_at,
                tickers_requested=0,
                tickers_processed=0,
                ranked_candidates=pipeline_result.ranked_candidates,
                warnings=final_warnings,
                errors=errors,
            )

        batches = self.ticker_batches(normalized_tickers, batch_size or self.batch_size)
        for batch_index, batch in enumerate(batches, start=1):
            self.report_batch_progress(
                progress_callback,
                batch_index=batch_index,
                batch_count=len(batches),
                batch_size=len(batch),
                total=len(normalized_tickers),
                processed=processed,
                status_message=f"Starting batch {batch_index} of {len(batches)}",
            )
            for ticker in batch:
                if self.cancel_requested(cancellation_callback):
                    cancelled = True
                    warnings.append("Screening cancelled")
                    self.report_progress(
                        progress_callback,
                        total=len(normalized_tickers),
                        processed=processed,
                        current_ticker=ticker,
                        status_message="Cancellation requested",
                    )
                    break

                try:
                    self.report_progress(
                        progress_callback,
                        total=len(normalized_tickers),
                        processed=processed,
                        current_ticker=ticker,
                        status_message=f"Processing {ticker}",
                    )
                    composite_result, component_results = self.score_ticker_cached(
                        ticker,
                        run_cache,
                    )
                    composite_scores.append(composite_result)
                    processed += 1
                    self.report_progress(
                        progress_callback,
                        total=len(normalized_tickers),
                        processed=processed,
                        current_ticker=ticker,
                        status_message=f"Processed {ticker}",
                    )
                    self.collect_warnings(
                        ticker,
                        warnings,
                        *component_results,
                        composite_result,
                    )
                except Exception as exc:
                    errors.append(f"{ticker}: {exc}")
            self.report_batch_progress(
                progress_callback,
                batch_index=batch_index,
                batch_count=len(batches),
                batch_size=len(batch),
                total=len(normalized_tickers),
                processed=processed,
                status_message=f"Completed batch {batch_index} of {len(batches)}",
            )
            if cancelled:
                break

        pipeline_result = self.persist_scores(
            composite_scores,
            run_id,
            minimum_score,
            allow_low_confidence,
            warnings,
            errors,
        )
        final_warnings = self.unique([*warnings, *pipeline_result.warnings])
        completed_at = self.timestamp()
        status = self.final_status(
            len(normalized_tickers),
            processed,
            errors,
            cancelled=cancelled,
        )
        self.update_run_record(
            run_id,
            status=status,
            completed_at=completed_at,
            tickers_requested=len(normalized_tickers),
            tickers_processed=processed,
            candidate_count=len(pipeline_result.ranked_candidates),
            warnings=final_warnings,
            errors=errors,
        )

        return ScreeningRunResult(
            run_id=run_id,
            status=status,
            started_at=started_at,
            completed_at=completed_at,
            tickers_requested=len(normalized_tickers),
            tickers_processed=processed,
            ranked_candidates=pipeline_result.ranked_candidates,
            warnings=final_warnings,
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

    def create_run_record(self, run_id, started_at, tickers_requested):
        if self.repository is None or not hasattr(self.repository, "create_screening_run"):
            return None
        return self.repository.create_screening_run(
            run_id=run_id,
            started_at=started_at,
            tickers_requested=tickers_requested,
            tickers_processed=0,
            candidate_count=0,
            warnings=[],
            errors=[],
            status="STARTED",
        )

    def update_run_record(
        self,
        run_id,
        status,
        completed_at,
        tickers_requested,
        tickers_processed,
        candidate_count,
        warnings,
        errors,
    ):
        if self.repository is None or not hasattr(self.repository, "update_screening_run"):
            return None
        return self.repository.update_screening_run(
            run_id=run_id,
            status=status,
            completed_at=completed_at,
            tickers_requested=tickers_requested,
            tickers_processed=tickers_processed,
            candidate_count=candidate_count,
            warnings=warnings,
            errors=errors,
        )

    def fetch_price_history(self, ticker):
        rows = fetch_ohlcv_rows(self.repository, ticker)
        if rows:
            return self.normalize_price_rows(rows)

        if self.market_data_refresh_service is not None:
            result = self.market_data_refresh_service.refresh_ticker(ticker)
            warnings = []
            warnings.extend(self.value(result, "warnings") or [])
            warnings.extend(self.value(result, "errors") or [])
            rows = self.value(result, "rows") or []
            success = bool(self.value(result, "success"))
            if not rows:
                warnings.append("Missing OHLCV data")
            if warnings:
                self.price_history_warnings_by_ticker[ticker] = self.unique(warnings)
            if success or rows:
                return self.normalize_price_rows(rows)
            return []

        if self.price_history_provider is None:
            return []

        if hasattr(self.price_history_provider, "fetch_ohlcv"):
            prices = self.price_history_provider.fetch_ohlcv(ticker)
        elif hasattr(self.price_history_provider, "fetch_daily_ohlcv"):
            prices = self.price_history_provider.fetch_daily_ohlcv(ticker)
        elif hasattr(self.price_history_provider, "get_price_history"):
            prices = self.price_history_provider.get_price_history(ticker)
        elif hasattr(self.price_history_provider, "fetch_price_history"):
            prices = self.price_history_provider.fetch_price_history(ticker)
        else:
            prices = self.price_history_provider(ticker)

        return self.normalize_price_rows(prices)

    def load_institutional_signals(self, tickers):
        provider = self.institutional_provider()
        signals = {}
        if hasattr(self.institutional_engine, "score_tickers"):
            try:
                signals = self.institutional_engine.score_tickers(tickers) or {}
            except Exception as exc:
                logger.warning("Institutional records loaded: 0")
                logger.warning("Institutional data preload failed: %s", exc)
                return {}
        count = self.count_loaded_institutional_records(signals)
        logger.info("Institutional records loaded: %s", count)
        return signals

    def log_institutional_provider(self):
        provider = self.institutional_provider()
        logger.info(
            "Institutional provider: %s",
            provider.__class__.__name__ if provider is not None else "None",
        )

    def institutional_provider(self):
        return getattr(self.institutional_engine, "provider", None)

    @staticmethod
    def count_loaded_institutional_records(signals):
        count = 0
        for signal in (signals or {}).values():
            raw_data = ScreeningOrchestrator.value(signal, "raw_institutional_data")
            if raw_data is None:
                continue
            if InstitutionalIntelligenceEngine.all_core_fields_missing(raw_data):
                continue
            count += 1
        return count

    def score_ticker_cached(self, ticker, cache):
        prices = self.cached_value(cache["prices"], ticker, self.fetch_price_history)
        price_warnings = self.price_history_warnings_by_ticker.get(ticker, [])
        support_result = self.cached_value(
            cache["support"],
            ticker,
            lambda symbol: self.support_engine.detect_support_zones(symbol, prices),
        )
        zones = self.value(support_result, "zones") or []
        bounce_result = self.cached_value(
            cache["bounce"],
            ticker,
            lambda symbol: self.bounce_engine.analyze_bounces(symbol, prices, zones),
        )
        technical_result = self.cached_value(
            cache["technical"],
            ticker,
            lambda symbol: self.technical_engine.calculate(prices, ticker=symbol),
        )
        institutional_result = self.cached_value(
            cache["institutional"],
            ticker,
            self.institutional_engine.score_ticker,
        )
        composite_result = self.cached_value(
            cache["composite"],
            ticker,
            lambda symbol: self.composite_engine.score(
                ticker=symbol,
                support=support_result,
                bounce=bounce_result,
                technical=technical_result,
                institutional=institutional_result,
            ),
        )
        return composite_result, (
            {"warnings": price_warnings},
            support_result,
            bounce_result,
            technical_result,
            institutional_result,
        )

    @staticmethod
    def cached_value(cache, key, producer):
        if key not in cache:
            cache[key] = producer(key)
        return cache[key]

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
    def ticker_batches(tickers, batch_size):
        size = max(1, int(batch_size or 1))
        return [
            list(tickers[index:index + size])
            for index in range(0, len(tickers or []), size)
        ]

    @staticmethod
    def timestamp():
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def final_status(tickers_requested, tickers_processed, errors, cancelled=False):
        if cancelled:
            return "PARTIAL_CANCELLED" if tickers_processed else "CANCELLED"
        if any(str(error).startswith("Pipeline persistence failed:") for error in errors):
            return "FAILED"
        if errors or tickers_processed < tickers_requested:
            return "PARTIAL"
        return "COMPLETED"

    @staticmethod
    def cancel_requested(cancellation_callback):
        if cancellation_callback is None:
            return False
        try:
            return bool(cancellation_callback())
        except Exception:
            return False

    @staticmethod
    def report_progress(
        progress_callback,
        total,
        processed,
        current_ticker,
        status_message,
    ):
        if progress_callback is None:
            return
        percentage = 100 if total == 0 else round(processed / total * 100, 2)
        progress = {
            "total_tickers": total,
            "processed_tickers": processed,
            "current_ticker": current_ticker,
            "progress_percentage": percentage,
            "status_message": status_message,
        }
        progress_callback(progress)

    @staticmethod
    def report_batch_progress(
        progress_callback,
        batch_index,
        batch_count,
        batch_size,
        total,
        processed,
        status_message,
    ):
        if progress_callback is None:
            return
        percentage = 100 if total == 0 else round(processed / total * 100, 2)
        progress_callback(
            {
                "total_tickers": total,
                "processed_tickers": processed,
                "current_ticker": None,
                "progress_percentage": percentage,
                "status_message": status_message,
                "batch_index": batch_index,
                "batch_count": batch_count,
                "batch_size": batch_size,
            }
        )

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
