from pathlib import Path

import pandas as pd

from database.manager import DatabaseManager


class MarketUniverseImporter:
    """
    Imports a CSV stock universe into the market_universe table.
    """

    COLUMNS = [
        "ticker",
        "company_name",
        "exchange",
        "security_type",
        "sector",
        "industry",
        "market_cap",
        "price",
        "average_volume",
        "average_dollar_volume",
        "is_active",
        "last_updated",
    ]

    NUMERIC_COLUMNS = [
        "market_cap",
        "price",
        "average_volume",
        "average_dollar_volume",
    ]

    EXCHANGE_ALIASES = {
        "N": "NYSE",
        "NEW YORK STOCK EXCHANGE": "NYSE",
        "NYSE": "NYSE",
        "NYSE ARCA": "NYSE",
        "Q": "NASDAQ",
        "NASDAQ": "NASDAQ",
        "NASDAQ GLOBAL MARKET": "NASDAQ",
        "NASDAQ GLOBAL SELECT": "NASDAQ",
        "NASDAQ CAPITAL MARKET": "NASDAQ",
        "NMS": "NASDAQ",
    }

    def __init__(self, csv_path=None, db=None, provider=None):
        self.csv_path = Path(csv_path or "data/universe/market_universe.csv")
        self.db = db or DatabaseManager()
        self.provider = provider

    def import_csv(self, csv_path=None):
        path = Path(csv_path) if csv_path is not None else self.csv_path
        summary = {
            "total_rows_read": 0,
            "records_imported": 0,
            "records_skipped": 0,
            "errors": [],
        }

        if not path.exists():
            summary["errors"].append(f"CSV file not found: {path}")
            return summary

        try:
            dataframe = pd.read_csv(path)
        except Exception as exc:
            summary["errors"].append(str(exc))
            return summary

        summary["total_rows_read"] = len(dataframe.index)
        records = []

        for row_number, (_, row) in enumerate(dataframe.iterrows(), start=2):
            try:
                record = self.normalize_row(row)
            except Exception as exc:
                summary["records_skipped"] += 1
                summary["errors"].append(f"Row {row_number}: {exc}")
                continue

            if record is None:
                summary["records_skipped"] += 1
                continue

            records.append(record)

        try:
            summary["records_imported"] = self.db.upsert_market_universe_records(records)
        except Exception as exc:
            summary["records_imported"] = 0
            summary["records_skipped"] = summary["total_rows_read"]
            summary["errors"].append(str(exc))

        return summary

    def import_from_provider(self, provider=None):
        provider = provider or self.provider
        summary = {
            "total_rows_read": 0,
            "records_imported": 0,
            "records_skipped": 0,
            "errors": [],
        }

        if provider is None:
            summary["errors"].append("Market data provider is required.")
            return summary

        try:
            universe = provider.get_market_universe()
        except Exception as exc:
            summary["errors"].append(str(exc))
            return summary

        summary["total_rows_read"] = len(universe or [])
        records = []

        for index, row in enumerate(universe or [], start=1):
            try:
                record = self.normalize_row(row)
            except Exception as exc:
                summary["records_skipped"] += 1
                summary["errors"].append(f"Record {index}: {exc}")
                continue

            if record is None:
                summary["records_skipped"] += 1
                continue

            records.append(record)

        try:
            summary["records_imported"] = self.db.upsert_market_universe_records(records)
        except Exception as exc:
            summary["records_imported"] = 0
            summary["records_skipped"] = summary["total_rows_read"]
            summary["errors"].append(str(exc))

        return summary

    def normalize_row(self, row):
        ticker = self.text_value(row, "ticker").upper()
        exchange = self.normalize_exchange(self.text_value(row, "exchange"))

        if not ticker or not exchange:
            return None

        record = {}
        for column in self.COLUMNS:
            if column in self.NUMERIC_COLUMNS:
                record[column] = self.numeric_value(row, column)
            elif column == "ticker":
                record[column] = ticker
            elif column == "exchange":
                record[column] = exchange
            elif column == "is_active":
                record[column] = self.active_value(self.value(row, column))
            else:
                record[column] = self.text_value(row, column) or None

        return record

    @classmethod
    def normalize_exchange(cls, value):
        normalized = str(value or "").strip().upper()
        if not normalized:
            return ""
        return cls.EXCHANGE_ALIASES.get(normalized, normalized)

    @classmethod
    def text_value(cls, row, column):
        value = cls.value(row, column)
        if pd.isna(value):
            return ""
        return str(value).strip()

    @staticmethod
    def numeric_value(row, column):
        value = MarketUniverseImporter.value(row, column)
        if pd.isna(value) or value == "":
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def active_value(value):
        if pd.isna(value) or value in (None, ""):
            return True
        if isinstance(value, str):
            return value.strip().lower() not in {"0", "false", "no", "n", "inactive"}
        return bool(value)

    @staticmethod
    def value(row, column):
        if isinstance(row, dict):
            return row.get(column)
        return row[column] if column in row else None

    def close(self):
        close = getattr(self.db, "close", None)
        if callable(close):
            close()
