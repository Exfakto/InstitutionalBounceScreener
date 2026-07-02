from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Callable

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from providers.provider_config import ProviderConfig
from providers.provider_manager import ProviderManager
from services.historical_sync_service import HistoricalSyncService
from services.live_data_service import LiveDataService


SUPPORTED_PROVIDERS = {"polygon"}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sync historical price data into the local database."
    )
    parser.add_argument("--ticker", help="Single ticker to sync.")
    parser.add_argument("--tickers", help="Comma-separated ticker list to sync.")
    parser.add_argument("--start", help="Start date in YYYY-MM-DD format.")
    parser.add_argument("--end", help="End date in YYYY-MM-DD format.")
    parser.add_argument(
        "--provider",
        default=None,
        help="Provider override. Currently supports polygon.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would sync without provider calls or database writes.",
    )
    parser.add_argument("--limit", type=int, help="Limit number of tickers synced.")

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    return run(
        ticker=args.ticker,
        tickers=args.tickers,
        start=args.start,
        end=args.end,
        provider=args.provider,
        dry_run=args.dry_run,
        limit=args.limit,
    )


def run(
    ticker: str | None = None,
    tickers: str | None = None,
    start: str | None = None,
    end: str | None = None,
    provider: str | None = None,
    dry_run: bool = False,
    limit: int | None = None,
    service_factory: Callable[[], HistoricalSyncService] | None = None,
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

    start_date = parse_date(start)
    end_date = parse_date(end)

    if start is not None and start_date is None:
        output("Invalid start date. Use YYYY-MM-DD.")
        return 2

    if end is not None and end_date is None:
        output("Invalid end date. Use YYYY-MM-DD.")
        return 2

    normalized_provider = normalize_provider(provider)

    if normalized_provider is None and provider is not None:
        output(f"Invalid provider: {provider}")
        return 2

    if dry_run:
        output(
            format_dry_run(
                normalized_tickers,
                start_date,
                end_date,
                normalized_provider,
            )
        )
        return 0

    service = (
        service_factory()
        if service_factory is not None
        else build_historical_sync_service(normalized_provider)
    )

    if len(normalized_tickers) == 1:
        summary = service.sync_ticker(
            normalized_tickers[0],
            start=start_date,
            end=end_date,
        )
    else:
        summary = service.sync_tickers(
            normalized_tickers,
            start=start_date,
            end=end_date,
        )

    output(format_summary(summary))

    return 1 if summary.get("failed", 0) else 0


def build_historical_sync_service(provider: str | None = None) -> HistoricalSyncService:
    if provider is None:
        return HistoricalSyncService()

    provider_config = ProviderConfig(
        active_provider=provider,
        providers={
            "local": {"enabled": True},
            provider: {"enabled": True},
        },
    )
    provider_manager = ProviderManager(provider_config=provider_config)
    live_data_service = LiveDataService(provider_manager=provider_manager)

    return HistoricalSyncService(live_data_service=live_data_service)


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


def parse_date(value: str | None) -> str | None:
    if value is None:
        return None

    try:
        return datetime.strptime(value, "%Y-%m-%d").date().isoformat()
    except ValueError:
        return None


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


def format_dry_run(
    tickers: list[str],
    start: str | None,
    end: str | None,
    provider: str | None,
) -> str:
    return "\n".join(
        [
            "Historical Sync Dry Run",
            f"Provider: {provider or 'configured default'}",
            f"Tickers: {', '.join(tickers)}",
            f"Start: {start or '--'}",
            f"End: {end or '--'}",
            "Provider calls: no",
            "Database writes: no",
        ]
    )


def format_summary(summary: dict) -> str:
    warnings = summary.get("warnings") or []

    lines = [
        "Historical Sync Summary",
        f"Ticker: {summary.get('ticker') or '--'}",
        f"Processed: {summary.get('processed', 0)}",
        f"Inserted: {summary.get('inserted', 0)}",
        f"Updated: {summary.get('updated', 0)}",
        f"Skipped: {summary.get('skipped', 0)}",
        f"Failed: {summary.get('failed', 0)}",
        f"Warnings: {len(warnings)}",
    ]

    if warnings:
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
