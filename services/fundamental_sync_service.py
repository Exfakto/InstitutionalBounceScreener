from __future__ import annotations

import math
import time
from typing import Any

from database.manager import DatabaseManager
from providers.provider_result import ProviderResult
from services.live_data_service import LiveDataService


class FundamentalSyncService:
    """
    Synchronize provider profile and fundamental data into local SQLite.
    """

    def __init__(
        self,
        live_data_service: LiveDataService | None = None,
        database_manager: DatabaseManager | None = None,
    ) -> None:
        self.live_data_service = live_data_service or LiveDataService()
        self.database_manager = database_manager or DatabaseManager()

    def sync_ticker(self, ticker: str | None) -> dict[str, Any]:
        started_at = time.perf_counter()
        normalized_ticker = self.normalize_ticker(ticker)
        summary = self.summary(normalized_ticker)

        if normalized_ticker is None:
            summary["failed"] = 1
            summary["warnings"].append("Ticker is required.")
            return self.finish_summary(summary, started_at)

        profile_result = self.live_data_service.get_company_profile(normalized_ticker)
        fundamentals_result = self.live_data_service.get_fundamentals(normalized_ticker)
        summary["provider"] = self.provider_summary(profile_result, fundamentals_result)

        if not profile_result.success:
            summary["warnings"].extend(profile_result.warnings or [])
            summary["warnings"].append(
                profile_result.message or "Company profile provider failed."
            )

        if not fundamentals_result.success:
            summary["warnings"].extend(fundamentals_result.warnings or [])
            summary["warnings"].append(
                fundamentals_result.message or "Fundamentals provider failed."
            )

        if not profile_result.success and not fundamentals_result.success:
            summary["failed"] = 1
            return self.finish_summary(summary, started_at)

        record = self.build_record(
            normalized_ticker,
            profile_result.data if profile_result.success else None,
            fundamentals_result.data if fundamentals_result.success else None,
        )

        if record is None:
            summary["skipped"] = 1
            summary["warnings"].append("Provider returned no usable fundamental data.")
            return self.finish_summary(summary, started_at)

        summary["processed"] = 1
        existing = self.existing_record(normalized_ticker)
        self.database_manager.save_fundamentals([record])

        if existing is None:
            summary["inserted"] = 1
        else:
            summary["updated"] = 1

        return self.finish_summary(summary, started_at)

    def sync_tickers(self, tickers: list[str] | tuple[str, ...]) -> dict[str, Any]:
        started_at = time.perf_counter()
        summaries = [self.sync_ticker(ticker) for ticker in (tickers or [])]
        aggregate = self.summary("MULTIPLE")
        aggregate["tickers"] = summaries
        aggregate["provider"] = self.aggregate_provider(summaries)

        for item in summaries:
            aggregate["processed"] += item.get("processed", 0)
            aggregate["inserted"] += item.get("inserted", 0)
            aggregate["updated"] += item.get("updated", 0)
            aggregate["skipped"] += item.get("skipped", 0)
            aggregate["failed"] += item.get("failed", 0)
            aggregate["warnings"].extend(item.get("warnings", []))

        return self.finish_summary(aggregate, started_at)

    def existing_record(self, ticker: str) -> Any:
        getter = getattr(self.database_manager, "get_fundamentals", None)

        if not callable(getter):
            return None

        return getter(ticker)

    @classmethod
    def build_record(
        cls,
        ticker: str,
        profile_data: Any,
        fundamentals_data: Any,
    ) -> dict[str, Any] | None:
        profile = cls.first_row(profile_data) or {}
        fundamentals = cls.fundamental_sections(fundamentals_data)
        income_rows = cls.rows(fundamentals.get("income_statement"))
        balance_rows = cls.rows(fundamentals.get("balance_sheet_statement"))
        cash_flow_rows = cls.rows(fundamentals.get("cash_flow_statement"))
        ratio_rows = cls.rows(fundamentals.get("ratios"))
        latest_income = cls.first_row(income_rows) or {}
        previous_income = income_rows[1] if len(income_rows) > 1 else {}
        latest_balance = cls.first_row(balance_rows) or {}
        latest_cash_flow = cls.first_row(cash_flow_rows) or {}
        latest_ratios = cls.first_row(ratio_rows) or {}

        record = {
            "ticker": ticker,
            "company_name": cls.first_value(
                profile,
                "companyName",
                "company_name",
                "name",
            ),
            "sector": cls.first_value(profile, "sector"),
            "industry": cls.first_value(profile, "industry"),
            "market_cap": cls.numeric_value(
                cls.first_value(profile, "mktCap", "marketCap", "market_cap")
            ),
            "revenue_growth_ttm": cls.growth_pct(
                latest_income.get("revenue"),
                previous_income.get("revenue"),
            ),
            "eps_growth_ttm": cls.growth_pct(
                cls.first_value(latest_income, "eps", "epsdiluted"),
                cls.first_value(previous_income, "eps", "epsdiluted"),
            ),
            "roe": cls.numeric_value(
                cls.first_value(
                    latest_ratios,
                    "returnOnEquity",
                    "roe",
                )
            ),
            "gross_margin": cls.numeric_value(
                cls.first_value(
                    latest_ratios,
                    "grossProfitMargin",
                    "gross_margin",
                )
            ),
            "free_cash_flow": cls.numeric_value(
                cls.first_value(
                    latest_cash_flow,
                    "freeCashFlow",
                    "free_cash_flow",
                )
            ),
            "debt_to_equity": cls.debt_to_equity(latest_ratios, latest_balance),
            "current_ratio": cls.numeric_value(
                cls.first_value(
                    latest_ratios,
                    "currentRatio",
                    "current_ratio",
                )
            ),
        }

        if not any(value is not None for key, value in record.items() if key != "ticker"):
            return None

        return record

    @classmethod
    def fundamental_sections(cls, data: Any) -> dict[str, Any]:
        if isinstance(data, dict):
            return data

        if isinstance(data, list):
            return {"income_statement": data}

        return {}

    @classmethod
    def rows(cls, data: Any) -> list[dict[str, Any]]:
        if data is None:
            return []

        if isinstance(data, dict):
            return [data]

        if isinstance(data, list):
            return [row for row in data if isinstance(row, dict)]

        return []

    @classmethod
    def first_row(cls, data: Any) -> dict[str, Any] | None:
        if isinstance(data, dict):
            return data

        rows = cls.rows(data)

        if not rows:
            return None

        return rows[0]

    @staticmethod
    def first_value(row: dict[str, Any], *keys: str) -> Any:
        for key in keys:
            value = row.get(key)

            if value is not None:
                return value

        return None

    @classmethod
    def debt_to_equity(
        cls,
        ratios: dict[str, Any],
        balance_sheet: dict[str, Any],
    ) -> float | None:
        ratio_value = cls.numeric_value(
            cls.first_value(ratios, "debtEquityRatio", "debt_to_equity")
        )

        if ratio_value is not None:
            return ratio_value

        debt = cls.numeric_value(
            cls.first_value(balance_sheet, "totalDebt", "totalLiabilities")
        )
        equity = cls.numeric_value(
            cls.first_value(
                balance_sheet,
                "totalStockholdersEquity",
                "totalEquity",
            )
        )

        if debt is None or equity in (None, 0):
            return None

        return debt / equity

    @classmethod
    def growth_pct(cls, current: Any, previous: Any) -> float | None:
        current_value = cls.numeric_value(current)
        previous_value = cls.numeric_value(previous)

        if current_value is None or previous_value in (None, 0):
            return None

        return ((current_value - previous_value) / abs(previous_value)) * 100

    @staticmethod
    def numeric_value(value: Any) -> float | None:
        if value is None:
            return None

        try:
            result = float(value)
        except (TypeError, ValueError):
            return None

        if not math.isfinite(result):
            return None

        return result

    @staticmethod
    def normalize_ticker(ticker: str | None) -> str | None:
        if ticker is None:
            return None

        normalized = str(ticker).strip().upper()

        return normalized or None

    @staticmethod
    def summary(ticker: str | None) -> dict[str, Any]:
        return {
            "ticker": ticker,
            "provider": None,
            "processed": 0,
            "inserted": 0,
            "updated": 0,
            "skipped": 0,
            "failed": 0,
            "warnings": [],
            "elapsed_seconds": 0.0,
        }

    @staticmethod
    def finish_summary(
        summary: dict[str, Any],
        started_at: float,
    ) -> dict[str, Any]:
        summary["elapsed_seconds"] = round(time.perf_counter() - started_at, 4)

        return summary

    @staticmethod
    def provider_summary(*results: ProviderResult) -> str | None:
        providers = []

        for result in results:
            if result.source and result.source not in providers:
                providers.append(result.source)

        if not providers:
            return None

        return ", ".join(providers)

    @staticmethod
    def aggregate_provider(summaries: list[dict[str, Any]]) -> str | None:
        providers = []

        for item in summaries:
            provider = item.get("provider")

            if provider and provider not in providers:
                providers.append(provider)

        if not providers:
            return None

        return ", ".join(providers)
