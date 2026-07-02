from __future__ import annotations

from datetime import date, datetime
from typing import Any

from database.manager import DatabaseManager


class FundamentalDiagnosticsService:
    """
    Read-only diagnostics for local synchronized fundamental data.
    """

    REQUIRED_PROFILE_FIELDS = ("company_name", "sector", "industry")
    REQUIRED_FUNDAMENTAL_FIELDS = (
        "market_cap",
        "revenue_growth_ttm",
        "eps_growth_ttm",
        "roe",
        "free_cash_flow",
        "debt_to_equity",
        "current_ratio",
    )

    def __init__(self, database_manager: DatabaseManager | None = None) -> None:
        self.database_manager = database_manager or DatabaseManager()

    def diagnose_ticker(
        self,
        ticker: str | None,
        stale_threshold_days: int = 30,
        today: Any = None,
    ) -> dict[str, Any]:
        normalized_ticker = self.normalize_ticker(ticker)
        reference_date = self.normalize_date(today) or date.today().isoformat()
        result = self.empty_result(normalized_ticker)

        if normalized_ticker is None:
            result["status"] = "Error"
            result["warnings"].append("Ticker is required.")
            return result

        if stale_threshold_days < 0:
            result["status"] = "Error"
            result["warnings"].append("Stale threshold days must be zero or greater.")
            return result

        try:
            row = self.database_manager.get_fundamentals(normalized_ticker)
        except Exception as exc:
            result["status"] = "Error"
            result["warnings"].append(f"Fundamentals read failed: {exc}")
            return result

        if row is None:
            result["status"] = "Missing"
            result["warnings"].append("No local fundamental row found.")
            return result

        metrics = self.row_to_dict(row)

        if not metrics:
            result["status"] = "Missing"
            result["warnings"].append("No local fundamental row found.")
            return result

        self.populate_result(result, metrics)

        missing_profile = [
            field
            for field in self.REQUIRED_PROFILE_FIELDS
            if self.is_missing(metrics.get(field))
        ]
        missing_fundamentals = [
            field
            for field in self.REQUIRED_FUNDAMENTAL_FIELDS
            if self.is_missing(self.metric_value(metrics, field))
        ]

        result["has_profile"] = not missing_profile
        result["has_fundamentals"] = not missing_fundamentals

        if missing_profile or missing_fundamentals:
            result["status"] = "Incomplete"
            if missing_profile:
                result["warnings"].append(
                    "Missing profile fields: " + ", ".join(missing_profile)
                )
            if missing_fundamentals:
                result["warnings"].append(
                    "Missing fundamental fields: "
                    + ", ".join(missing_fundamentals)
                )
            return result

        if result["updated_at"] is None:
            result["status"] = "Incomplete"
            result["warnings"].append("Missing updated_at.")
            return result

        result["stale_days"] = self.days_between(result["updated_at"], reference_date)

        if result["stale_days"] > stale_threshold_days:
            result["status"] = "Stale"
            result["warnings"].append(
                f"Fundamental row is {result['stale_days']} days old."
            )
            return result

        result["status"] = "Current"
        return result

    def diagnose_tickers(
        self,
        tickers: list[str] | tuple[str, ...],
        stale_threshold_days: int = 30,
        today: Any = None,
    ) -> dict[str, Any]:
        results = [
            self.diagnose_ticker(
                ticker,
                stale_threshold_days=stale_threshold_days,
                today=today,
            )
            for ticker in (tickers or [])
        ]

        return {
            "ticker": "MULTIPLE",
            "results": results,
            "has_profile": all(item.get("has_profile") for item in results) if results else False,
            "has_fundamentals": all(item.get("has_fundamentals") for item in results) if results else False,
            "company_name": None,
            "sector": None,
            "industry": None,
            "market_cap": None,
            "revenue_growth": None,
            "eps_growth": None,
            "roe": None,
            "free_cash_flow": None,
            "debt_to_equity": None,
            "current_ratio": None,
            "updated_at": None,
            "stale_days": max([item.get("stale_days", 0) for item in results] or [0]),
            "status": self.aggregate_status(results),
            "warnings": [
                warning
                for item in results
                for warning in item.get("warnings", [])
            ],
        }

    @classmethod
    def populate_result(cls, result: dict[str, Any], metrics: dict[str, Any]) -> None:
        result["company_name"] = metrics.get("company_name")
        result["sector"] = metrics.get("sector")
        result["industry"] = metrics.get("industry")
        result["market_cap"] = metrics.get("market_cap")
        result["revenue_growth"] = cls.metric_value(metrics, "revenue_growth_ttm")
        result["eps_growth"] = cls.metric_value(metrics, "eps_growth_ttm")
        result["roe"] = metrics.get("roe")
        result["free_cash_flow"] = metrics.get("free_cash_flow")
        result["debt_to_equity"] = metrics.get("debt_to_equity")
        result["current_ratio"] = metrics.get("current_ratio")
        result["updated_at"] = cls.normalize_date(metrics.get("updated_at"))

    @classmethod
    def metric_value(cls, metrics: dict[str, Any], key: str) -> Any:
        aliases = {
            "revenue_growth_ttm": ("revenue_growth_ttm", "revenue_growth"),
            "eps_growth_ttm": ("eps_growth_ttm", "eps_growth"),
        }

        for candidate_key in aliases.get(key, (key,)):
            value = metrics.get(candidate_key)

            if not cls.is_missing(value):
                return value

        return None

    @staticmethod
    def row_to_dict(row: Any) -> dict[str, Any]:
        if isinstance(row, dict):
            return dict(row)

        if hasattr(row, "keys"):
            return {
                key: row[key]
                for key in row.keys()
            }

        return {}

    @staticmethod
    def aggregate_status(results: list[dict[str, Any]]) -> str:
        if not results:
            return "Missing"

        for status in ["Error", "Missing", "Incomplete", "Stale"]:
            if any(item.get("status") == status for item in results):
                return status

        return "Current"

    @staticmethod
    def empty_result(ticker: str | None) -> dict[str, Any]:
        return {
            "ticker": ticker,
            "has_profile": False,
            "has_fundamentals": False,
            "company_name": None,
            "sector": None,
            "industry": None,
            "market_cap": None,
            "revenue_growth": None,
            "eps_growth": None,
            "roe": None,
            "free_cash_flow": None,
            "debt_to_equity": None,
            "current_ratio": None,
            "updated_at": None,
            "stale_days": 0,
            "status": "Missing",
            "warnings": [],
        }

    @staticmethod
    def days_between(start: str | None, end: str | None) -> int:
        start_date = FundamentalDiagnosticsService.normalize_date(start)
        end_date = FundamentalDiagnosticsService.normalize_date(end)

        if start_date is None or end_date is None:
            return 0

        parsed_start = datetime.strptime(start_date, "%Y-%m-%d").date()
        parsed_end = datetime.strptime(end_date, "%Y-%m-%d").date()

        if parsed_start >= parsed_end:
            return 0

        return (parsed_end - parsed_start).days

    @staticmethod
    def normalize_ticker(ticker: str | None) -> str | None:
        normalized = str(ticker or "").strip().upper()

        return normalized or None

    @staticmethod
    def normalize_date(value: Any) -> str | None:
        if value is None:
            return None

        if isinstance(value, datetime):
            return value.date().isoformat()

        if isinstance(value, date):
            return value.isoformat()

        text = str(value).strip()

        if not text:
            return None

        if " " in text:
            text = text.split(" ", 1)[0]

        try:
            return datetime.strptime(text, "%Y-%m-%d").date().isoformat()
        except ValueError:
            return None

    @staticmethod
    def is_missing(value: Any) -> bool:
        return value is None or value == ""
