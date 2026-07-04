from types import SimpleNamespace

from services.full_market_pipeline import FullMarketRefreshOrchestrator, PipelineResult
from tests.full_market_test_utils import build_manager


def test_full_market_refresh_orchestrator_coordinates_all_stages():
    manager = build_manager()
    manager.upsert_universe_symbols(
        [{"ticker": "AAPL", "exchange": "NASDAQ", "security_type": "Common Stock"}]
    )
    progress = []
    orchestrator = FullMarketRefreshOrchestrator(
        repository=manager,
        universe_service=SimpleNamespace(update_universe=lambda: PipelineResult(persisted=1)),
        historical_service=SimpleNamespace(update_history=lambda tickers, **kwargs: PipelineResult(processed=len(tickers), persisted=2)),
        fundamental_service=SimpleNamespace(update_fundamentals=lambda tickers, **kwargs: PipelineResult(processed=len(tickers), persisted=1)),
        institutional_service=SimpleNamespace(update_institutional_data=lambda tickers, **kwargs: PipelineResult(processed=len(tickers), persisted=1, warnings=["limited institutional data"])),
    )

    result = orchestrator.refresh_all(progress_callback=progress.append)

    assert result.success is True
    assert result.processed == 1
    assert result.persisted == 5
    assert set(result.details) == {"universe", "ohlcv", "fundamentals", "institutional"}
    assert "limited institutional data" in result.warnings


def test_full_market_refresh_orchestrator_handles_missing_services_and_cancellation():
    manager = build_manager()
    missing = FullMarketRefreshOrchestrator(repository=manager).refresh_all()
    assert missing.success is False
    assert "universe service unavailable" in missing.errors

    cancelled = FullMarketRefreshOrchestrator(
        repository=manager,
        universe_service=SimpleNamespace(update_universe=lambda: PipelineResult(persisted=0)),
    ).refresh_all(cancellation_callback=lambda: True)

    assert "Full market refresh cancelled" in cancelled.warnings
