"""
Read-only chart data assembly service.
"""

from __future__ import annotations

import pandas as pd

from database.manager import DatabaseManager


class ChartDataService:
    """
    Assemble local SQLite data needed by future chart widgets.
    """

    def __init__(self, db=None):
        self.db = db or DatabaseManager()

    def get_chart_data(self, ticker):
        """
        Return chart-ready data for one ticker without writing to storage.
        """

        warnings = []
        prices = self.price_history_records(self.db.get_price_history(ticker))
        indicators = self.row_records(self.db.get_technical_indicators(ticker))
        prices = self.merge_indicators(prices, indicators)

        if not prices:
            warnings.append("Missing price history")

        bounce_validations = self.row_records(self.db.get_bounce_validations(ticker))
        support_zones = self.support_zone_records(
            self.row_records(self.db.get_support_levels(ticker)),
            bounce_validations,
        )

        if not indicators:
            warnings.append("Missing technical indicators")

        if not support_zones:
            warnings.append("Missing support zones")

        if not bounce_validations:
            warnings.append("Missing bounce validations")

        return {
            "ticker": ticker,
            "prices": prices,
            "indicators": indicators,
            "support_zones": support_zones,
            "bounce_validations": bounce_validations,
            "warnings": warnings,
        }

    @classmethod
    def price_history_records(cls, dataframe):
        if dataframe is None or dataframe.empty:
            return []

        records = []

        for date, row in dataframe.iterrows():
            records.append(
                {
                    "date": cls.format_date(date),
                    "open": cls.value_or_none(row.get("Open")),
                    "high": cls.value_or_none(row.get("High")),
                    "low": cls.value_or_none(row.get("Low")),
                    "close": cls.value_or_none(row.get("Close")),
                    "volume": cls.value_or_none(row.get("Volume")),
                }
            )

        return records

    @classmethod
    def row_records(cls, rows):
        return [
            cls.row_to_dict(row)
            for row in (rows or [])
        ]

    @classmethod
    def merge_indicators(cls, prices, indicators):
        indicators_by_date = {
            cls.format_date(row.get("date")): row
            for row in indicators
            if row.get("date") is not None
        }

        merged = []

        for price in prices:
            row = dict(price)
            indicator = indicators_by_date.get(row.get("date"), {})

            for key in ["sma20", "sma50", "sma200"]:
                row[key] = cls.value_or_none(indicator.get(key))

            merged.append(row)

        return merged

    @classmethod
    def support_zone_records(cls, support_zones, bounce_validations):
        validations_by_support_id = {
            validation.get("support_level_id"): validation
            for validation in bounce_validations
            if validation.get("support_level_id") is not None
        }

        records = []

        for zone in support_zones:
            validation = validations_by_support_id.get(zone.get("id"), {})
            success_rate = cls.value_or_none(validation.get("bounce_success_rate"))
            bounce_count = cls.value_or_none(validation.get("successful_bounces"))

            records.append(
                {
                    **zone,
                    "support_low": cls.value_or_none(zone.get("zone_low")),
                    "support_high": cls.value_or_none(zone.get("zone_high")),
                    "support_strength": cls.value_or_none(
                        zone.get("strength_score")
                    ),
                    "validated": bool(validation),
                    "bounce_count": bounce_count,
                    "success_rate": success_rate,
                }
            )

        return records

    @staticmethod
    def row_to_dict(row):
        if isinstance(row, dict):
            return dict(row)

        if hasattr(row, "keys"):
            return {
                key: row[key]
                for key in row.keys()
            }

        return {}

    @staticmethod
    def format_date(value):
        if hasattr(value, "date"):
            return str(value.date())

        return str(value)

    @staticmethod
    def value_or_none(value):
        if pd.isna(value):
            return None

        if hasattr(value, "item"):
            return value.item()

        return value

    def close(self):
        self.db.close()
