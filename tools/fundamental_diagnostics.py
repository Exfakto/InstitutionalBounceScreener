from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Callable

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.fundamental_diagnostics_service import FundamentalDiagnosticsService


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Diagnose local SQLite fundamental sync status."
    )
    parser.add_argument("--ticker", help="Single ticker to diagnose.")
    parser.add_argument("--tickers", help="Comma-separated ticker list to diagnose.")
    parser.add_argument(
        "--stale-threshold-days",
        type=int,
        default=30,
        help="Maximum acceptable calendar days since the latest update.",
    )

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    return run(
        ticker=args.ticker,
        tickers=args.tickers,
        stale_threshold_days=args.stale_threshold_days,
    )


def run(
    ticker: str | None = None,
    tickers: str | None = None,
    stale_threshold_days: int = 30,
    service_factory: Callable[[], FundamentalDiagnosticsService] | None = None,
    output=print,
) -> int:
    normalized_tickers = parse_tickers(ticker=ticker, tickers=tickers)

    if not normalized_tickers:
        output("No ticker provided. Use --ticker AAPL or --tickers AAPL,MSFT.")
        return 2

    if stale_threshold_days < 0:
        output("Stale threshold days must be zero or greater.")
        return 2

    service = (
        service_factory()
        if service_factory is not None
        else FundamentalDiagnosticsService()
    )

    if len(normalized_tickers) == 1:
        result = service.diagnose_ticker(
            normalized_tickers[0],
            stale_threshold_days=stale_threshold_days,
        )
    else:
        result = service.diagnose_tickers(
            normalized_tickers,
            stale_threshold_days=stale_threshold_days,
        )

    output(format_result(result))

    return 1 if result.get("status") == "Error" else 0


def format_result(result: dict) -> str:
    if "results" in result:
        sections = [
            "Fundamental Diagnostics",
            "Ticker: MULTIPLE",
            f"Status: {result.get('status')}",
            f"Warnings: {len(result.get('warnings') or [])}",
        ]
        sections.extend(format_result(item) for item in result.get("results", []))
        return "\n\n".join(sections)

    warnings = result.get("warnings") or []
    lines = [
        "Fundamental Diagnostics",
        f"Ticker: {result.get('ticker') or '--'}",
        f"Status: {result.get('status') or '--'}",
        f"Company name: {result.get('company_name') or '--'}",
        f"Sector: {result.get('sector') or '--'}",
        f"Market cap: {format_value(result.get('market_cap'))}",
        f"Updated at: {result.get('updated_at') or '--'}",
        f"Stale days: {result.get('stale_days', 0)}",
        f"Warnings: {len(warnings)}",
    ]

    if warnings:
        lines.append("Warning details:")
        lines.extend(f"- {warning}" for warning in warnings)

    return "\n".join(lines)


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


def format_value(value) -> str:
    if value is None or value == "":
        return "--"

    return str(value)


if __name__ == "__main__":
    raise SystemExit(main())
