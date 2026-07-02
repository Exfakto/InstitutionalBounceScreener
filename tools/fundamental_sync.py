from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Callable

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from providers.fmp_provider import FMPProvider
from providers.provider_config import ProviderConfig
from providers.provider_manager import ProviderManager
from services.fundamental_sync_service import FundamentalSyncService
from services.live_data_service import LiveDataService


SUPPORTED_PROVIDERS = {"fmp"}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sync fundamental data into the local database."
    )
    parser.add_argument("--ticker", help="Single ticker to sync.")
    parser.add_argument("--tickers", help="Comma-separated ticker list to sync.")
    parser.add_argument(
        "--provider",
        default=None,
        help="Provider override. Currently supports fmp.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would sync without provider calls or database writes.",
    )
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="Print summary counts without detailed warnings.",
    )
    parser.add_argument("--limit", type=int, help="Limit number of tickers synced.")

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    return run(
        ticker=args.ticker,
        tickers=args.tickers,
        provider=args.provider,
        dry_run=args.dry_run,
        summary_only=args.summary_only,
        limit=args.limit,
    )


def run(
    ticker: str | None = None,
    tickers: str | None = None,
    provider: str | None = None,
    dry_run: bool = False,
    summary_only: bool = False,
    limit: int | None = None,
    service_factory: Callable[[], FundamentalSyncService] | None = None,
    output=print,
) -> int:
    normalized_tickers = parse_tickers(ticker=ticker, tickers=tickers)

    if not normalized_tickers:
        output("No ticker provided. Use --ticker AAPL or --tickers AAPL,MSFT.")
        return 2

    if limit is not None:
        if limit <= 0:
            output("Limit must be greater than zero.")
            return 2

        normalized_tickers = normalized_tickers[:limit]

    normalized_provider = normalize_provider(provider)

    if normalized_provider is None and provider is not None:
        output(f"Invalid provider: {provider}")
        return 2

    if (
        not dry_run
        and normalized_provider == "fmp"
        and not os.getenv("FMP_API_KEY")
    ):
        output("FMP API key is not configured.")
        return 1

    if dry_run:
        output(format_dry_run(normalized_tickers, normalized_provider))
        return 0

    service = (
        service_factory()
        if service_factory is not None
        else build_fundamental_sync_service(normalized_provider)
    )

    if len(normalized_tickers) == 1:
        summary = service.sync_ticker(normalized_tickers[0])
    else:
        summary = service.sync_tickers(normalized_tickers)

    output(
        format_summary(
            summary,
            provider=normalized_provider,
            ticker_count=len(normalized_tickers),
            summary_only=summary_only,
        )
    )

    return 1 if summary.get("failed", 0) else 0


def build_fundamental_sync_service(
    provider: str | None = None,
) -> FundamentalSyncService:
    if provider is None:
        return FundamentalSyncService()

    provider_config = ProviderConfig(
        active_provider=provider,
        providers={
            "local": {"enabled": True},
            provider: {"enabled": True, "api_key_env": "FMP_API_KEY"},
        },
    )
    provider_manager = ProviderManager(provider_config=provider_config)

    if provider == "fmp":
        provider_manager.register_provider("fmp", FMPProvider())
        provider_manager.set_active_provider("fmp")

    live_data_service = LiveDataService(provider_manager=provider_manager)

    return FundamentalSyncService(live_data_service=live_data_service)


def parse_tickers(ticker: str | None = None, tickers: str | None = None) -> list[str]:
    values = []

    if ticker:
        values.append(ticker)

    if tickers:
        values.extend(tickers.split(","))

    normalized = []

    for value in values:
        ticker_value = normalize_ticker(value)

        if ticker_value is not None and ticker_value not in normalized:
            normalized.append(ticker_value)

    return normalized


def normalize_ticker(value: str | None) -> str | None:
    normalized = str(value or "").strip().upper()

    return normalized or None


def normalize_provider(provider: str | None) -> str | None:
    if provider is None:
        return None

    normalized = str(provider).strip().lower()

    if normalized in SUPPORTED_PROVIDERS:
        return normalized

    return None


def format_dry_run(tickers: list[str], provider: str | None) -> str:
    return "\n".join(
        [
            "Fundamental Sync Dry Run",
            f"Provider: {provider or 'configured default'}",
            f"Ticker count: {len(tickers)}",
            f"Tickers: {', '.join(tickers)}",
            "Provider calls: no",
            "Database writes: no",
        ]
    )


def format_summary(
    summary: dict,
    provider: str | None = None,
    ticker_count: int | None = None,
    summary_only: bool = False,
) -> str:
    warnings = summary.get("warnings") or []

    lines = [
        "Fundamental Sync Summary",
        f"Provider: {summary.get('provider') or provider or 'configured default'}",
        f"Ticker: {summary.get('ticker') or '--'}",
        f"Ticker count: {ticker_count if ticker_count is not None else 1}",
        f"Processed: {summary.get('processed', 0)}",
        f"Inserted: {summary.get('inserted', 0)}",
        f"Updated: {summary.get('updated', 0)}",
        f"Skipped: {summary.get('skipped', 0)}",
        f"Failed: {summary.get('failed', 0)}",
        f"Warning count: {len(warnings)}",
    ]

    if warnings and not summary_only:
        lines.append("Warning details:")
        lines.extend(f"- {sanitize_message(warning)}" for warning in warnings)

    return "\n".join(lines)


def sanitize_message(message: str | None) -> str:
    text = str(message or "")

    for environment_name in ["POLYGON_API_KEY", "FMP_API_KEY", "FINNHUB_API_KEY"]:
        value = os.getenv(environment_name)

        if value:
            text = text.replace(value, "[redacted]")

    return text


if __name__ == "__main__":
    raise SystemExit(main())
