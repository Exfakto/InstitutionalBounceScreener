from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Callable

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from providers.finnhub_provider import FinnhubProvider
from providers.fmp_provider import FMPProvider
from providers.polygon_provider import PolygonProvider
from providers.provider_result import ProviderResult
from providers.sec_edgar_provider import SECEdgarProvider


PROVIDER_ORDER = ("polygon", "fmp", "finnhub", "sec")

PROVIDER_CONFIG = {
    "polygon": {
        "display_name": "Polygon",
        "environment": "POLYGON_API_KEY",
        "factory": PolygonProvider,
        "method": "get_price_history",
    },
    "fmp": {
        "display_name": "FMP",
        "environment": "FMP_API_KEY",
        "factory": FMPProvider,
        "method": "get_company_profile",
    },
    "finnhub": {
        "display_name": "Finnhub",
        "environment": "FINNHUB_API_KEY",
        "factory": FinnhubProvider,
        "method": "get_company_profile",
    },
    "sec": {
        "display_name": "SEC EDGAR",
        "environment": None,
        "factory": SECEdgarProvider,
        "method": "get_institutional_metrics",
    },
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Safely smoke test premium provider connectivity."
    )
    parser.add_argument(
        "--provider",
        choices=[*PROVIDER_ORDER, "all"],
        default="all",
        help="Provider to test.",
    )
    parser.add_argument("--ticker", default="AAPL", help="Ticker symbol to test.")
    parser.add_argument(
        "--live",
        action="store_true",
        help="Perform one live provider request per selected provider.",
    )

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    return run_smoke_test(
        provider=args.provider,
        ticker=args.ticker,
        live=args.live,
    )


def run_smoke_test(
    provider: str = "all",
    ticker: str = "AAPL",
    live: bool = False,
    provider_factories: dict[str, Callable[[], object]] | None = None,
    output=print,
) -> int:
    selected_providers = selected_provider_names(provider)

    if not selected_providers:
        output(f"Invalid provider: {provider}")
        return 2

    normalized_ticker = normalize_ticker(ticker) or "AAPL"
    provider_factories = provider_factories or {}
    exit_code = 0

    for provider_name in selected_providers:
        result = smoke_provider(
            provider_name,
            normalized_ticker,
            live,
            provider_factories=provider_factories,
        )
        output(format_result(result))

        if result["result_success"] is False:
            exit_code = 1

    return exit_code


def smoke_provider(
    provider_name: str,
    ticker: str,
    live: bool,
    provider_factories: dict[str, Callable[[], object]] | None = None,
) -> dict[str, object]:
    config = PROVIDER_CONFIG[provider_name]
    key_status = key_status_for(config["environment"])

    result = {
        "provider": config["display_name"],
        "ticker": ticker,
        "key_status": key_status,
        "live": live,
        "result_success": None,
        "message": "Dry run only. Use --live to perform one safe request.",
        "warning_count": 0,
        "record_count": None,
    }

    if not live:
        return result

    environment_name = config["environment"]

    if environment_name and key_status != "Configured":
        result.update(
            {
                "result_success": False,
                "message": f"{config['display_name']} API key is not configured.",
            }
        )
        return result

    try:
        factory = (provider_factories or {}).get(provider_name) or config["factory"]
        provider = factory()
        provider_result = getattr(provider, config["method"])(ticker)
    except Exception as exc:
        provider_result = ProviderResult.fail(
            message=sanitize_message(str(exc)) or "Provider smoke test failed.",
            source=provider_name,
            warnings=["Provider raised an exception."],
        )

    result.update(
        {
            "result_success": bool(provider_result.success),
            "message": sanitize_message(provider_result.message),
            "warning_count": len(provider_result.warnings or []),
            "record_count": record_count(provider_result.data),
        }
    )

    return result


def selected_provider_names(provider: str) -> list[str]:
    normalized = str(provider or "").strip().lower()

    if normalized == "all":
        return list(PROVIDER_ORDER)

    if normalized in PROVIDER_CONFIG:
        return [normalized]

    return []


def key_status_for(environment_name: str | None) -> str:
    if environment_name is None:
        return "Configured"

    value = os.getenv(environment_name)

    if value and value.strip():
        return "Configured"

    return "Not Configured"


def record_count(data) -> int | None:
    if data is None:
        return None

    if hasattr(data, "shape"):
        try:
            return int(data.shape[0])
        except (TypeError, ValueError, IndexError):
            return None

    if isinstance(data, (list, tuple, set, dict)):
        return len(data)

    return 1


def format_result(result: dict[str, object]) -> str:
    return "\n".join(
        [
            f"Provider: {result['provider']}",
            f"Ticker: {result['ticker']}",
            f"Key status: {result['key_status']}",
            f"Live mode: {str(result['live']).lower()}",
            f"Result: {result_label(result['result_success'])}",
            f"Message: {result['message']}",
            f"Warning count: {result['warning_count']}",
            f"Record count: {result['record_count'] if result['record_count'] is not None else '--'}",
        ]
    )


def result_label(success) -> str:
    if success is True:
        return "success"

    if success is False:
        return "failure"

    return "not run"


def sanitize_message(message: str | None) -> str:
    text = str(message or "").strip()

    for environment_name in ["POLYGON_API_KEY", "FMP_API_KEY", "FINNHUB_API_KEY"]:
        value = os.getenv(environment_name)

        if value:
            text = text.replace(value, "[redacted]")

    return text


def normalize_ticker(ticker: str | None) -> str | None:
    normalized = str(ticker or "").strip().upper()

    return normalized or None


if __name__ == "__main__":
    raise SystemExit(main())
