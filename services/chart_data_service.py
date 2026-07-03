"""
Read-only chart data assembly service.
"""

from __future__ import annotations

import pandas as pd

from database.manager import DatabaseManager
from services.chart_models import (
    BounceMarker,
    CandidateChartModel,
    CandidateScoreAnnotation,
    ChartSupportZone,
    InstitutionalScoreBadge,
    OhlcvCandle,
    TechnicalIndicatorOverlay,
)


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

    def build_candidate_chart_data(
        self,
        ticker=None,
        candidate=None,
        price_rows=None,
        support_zones=None,
        bounce_markers=None,
        technical_indicators=None,
        institutional_signal=None,
    ):
        """
        Return typed chart-ready data for a ranked candidate.
        """

        resolved_ticker = (
            ticker
            or self.value(candidate, "ticker")
            or self.value(institutional_signal, "ticker")
        )
        warnings = []

        if price_rows is None and resolved_ticker:
            try:
                local_data = self.get_chart_data(resolved_ticker)
                price_rows = local_data.get("prices", [])
                support_zones = (
                    support_zones
                    if support_zones is not None
                    else local_data.get("support_zones", [])
                )
                technical_indicators = (
                    technical_indicators
                    if technical_indicators is not None
                    else local_data.get("indicators", [])
                )
                warnings.extend(local_data.get("warnings", []))
            except Exception as exc:
                warnings.append(f"Unable to load chart data: {exc}")

        candles = self.candle_models(price_rows)
        zones = self.support_zone_models(support_zones)
        markers = self.bounce_marker_models(bounce_markers)
        overlays = self.technical_overlay_models(technical_indicators, candles)
        badges = self.institutional_badge_models(institutional_signal, candidate)
        annotation = self.candidate_annotation_model(candidate)

        if not resolved_ticker:
            warnings.append("Missing ticker")
        if not candles and "Missing price history" not in warnings:
            warnings.append("Missing price history")
        if not zones and "Missing support zones" not in warnings:
            warnings.append("Missing support zones")
        if not markers:
            warnings.append("Missing bounce markers")
        if not overlays and "Missing technical indicators" not in warnings:
            warnings.append("Missing technical indicators")
        if not badges:
            warnings.append("Missing institutional data")

        return CandidateChartModel(
            ticker=resolved_ticker,
            candles=candles,
            support_zones=zones,
            bounce_markers=markers,
            technical_overlays=overlays,
            institutional_badges=badges,
            candidate_annotation=annotation,
            warnings=self.unique_text(warnings),
        )

    @classmethod
    def candle_models(cls, rows):
        return [
            OhlcvCandle(
                date=cls.value(row, "date"),
                open=cls.value_or_none(cls.value(row, "open")),
                high=cls.value_or_none(cls.value(row, "high")),
                low=cls.value_or_none(cls.value(row, "low")),
                close=cls.value_or_none(cls.value(row, "close")),
                volume=cls.value_or_none(cls.value(row, "volume")),
            )
            for row in (rows or [])
        ]

    @classmethod
    def support_zone_models(cls, zones):
        models = []
        for zone in zones or []:
            low = cls.first_existing(
                cls.value(zone, "zone_low"),
                cls.value(zone, "support_low"),
            )
            high = cls.first_existing(
                cls.value(zone, "zone_high"),
                cls.value(zone, "support_high"),
            )
            center = cls.first_existing(
                cls.value(zone, "zone_center"),
                cls.average(low, high),
            )
            models.append(
                ChartSupportZone(
                    zone_low=cls.value_or_none(low),
                    zone_high=cls.value_or_none(high),
                    zone_center=cls.value_or_none(center),
                    strength_score=cls.value_or_none(
                        cls.first_existing(
                            cls.value(zone, "support_strength_score"),
                            cls.value(zone, "support_strength"),
                            cls.value(zone, "strength_score"),
                        )
                    ),
                    confidence_score=cls.value_or_none(
                        cls.value(zone, "confidence_score")
                    ),
                    touch_count=cls.value(zone, "touch_count")
                    or cls.value(zone, "total_touches"),
                    label=cls.value(zone, "label") or "Support Zone",
                )
            )
        return models

    @classmethod
    def bounce_marker_models(cls, markers):
        models = []
        for marker in markers or []:
            models.append(
                BounceMarker(
                    date=cls.first_existing(
                        cls.value(marker, "date"),
                        cls.value(marker, "touch_date"),
                    ),
                    support_price=cls.value_or_none(
                        cls.first_existing(
                            cls.value(marker, "support_price"),
                            cls.value(marker, "support"),
                        )
                    ),
                    bounce_percentage=cls.value_or_none(
                        cls.first_existing(
                            cls.value(marker, "bounce_percentage"),
                            cls.value(marker, "bounce_pct"),
                        )
                    ),
                    successful=cls.value(marker, "successful"),
                    label=cls.value(marker, "label") or "Bounce",
                )
            )
        return models

    @classmethod
    def technical_overlay_models(cls, indicators, candles):
        rows = list(indicators or [])
        overlays = []
        overlay_fields = [
            ("EMA 20", "ema20", "sma20"),
            ("EMA 50", "ema50", "sma50"),
            ("EMA 200", "ema200", "sma200"),
            ("RSI 14", "rsi14", None),
            ("MACD", "macd", None),
        ]

        for name, primary_key, fallback_key in overlay_fields:
            values = []
            for row in rows:
                value = cls.first_existing(
                    cls.value(row, primary_key),
                    cls.value(row, fallback_key) if fallback_key else None,
                )
                if value is not None:
                    values.append((cls.value(row, "date"), cls.value_or_none(value)))
            if values:
                overlays.append(
                    TechnicalIndicatorOverlay(
                        name=name,
                        values=values,
                        latest_value=values[-1][1],
                    )
                )

        if not overlays and candles:
            latest = candles[-1]
            if latest.close is not None:
                overlays.append(
                    TechnicalIndicatorOverlay(
                        name="Close",
                        values=[(latest.date, latest.close)],
                        latest_value=latest.close,
                        status="Price",
                    )
                )
        return overlays

    @classmethod
    def institutional_badge_models(cls, institutional_signal, candidate):
        score_result = cls.value(institutional_signal, "score_result")
        raw_data = cls.value(institutional_signal, "raw_data")
        score = cls.first_existing(
            cls.value(score_result, "overall_score"),
            cls.value(score_result, "overall_institutional_strength_score"),
            cls.value(candidate, "institutional_score"),
        )
        if score is None and raw_data is None:
            return []
        return [
            InstitutionalScoreBadge(
                label="Institutional Strength",
                score=cls.value_or_none(score),
                status=cls.value(score_result, "outlook")
                or cls.value(institutional_signal, "status"),
                as_of_date=cls.value(institutional_signal, "as_of_date")
                or cls.value(raw_data, "as_of_date"),
                source=cls.value(institutional_signal, "source")
                or cls.value(raw_data, "source"),
            )
        ]

    @classmethod
    def candidate_annotation_model(cls, candidate):
        if candidate is None:
            return None
        return CandidateScoreAnnotation(
            final_score=cls.value_or_none(cls.value(candidate, "final_score")),
            grade=cls.value(candidate, "grade"),
            confidence_level=cls.value(candidate, "confidence_level"),
            setup_label=cls.value(candidate, "setup_label"),
            explanation=cls.list_values(cls.value(candidate, "explanation")),
        )

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
            validation_fields = cls.bounce_validation_fields(validation, zone)

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
                    **validation_fields,
                }
            )

        return records

    @classmethod
    def bounce_validation_fields(cls, validation, zone):
        fields = {
            "support_level_id": validation.get("support_level_id", zone.get("id")),
            "total_touches": validation.get("total_touches"),
            "successful_bounces": validation.get("successful_bounces"),
            "failed_breakdowns": validation.get("failed_breakdowns"),
            "neutral_touches": validation.get("neutral_touches"),
            "bounce_success_rate": validation.get("bounce_success_rate"),
            "average_bounce_pct": validation.get("average_bounce_pct"),
            "median_bounce_pct": validation.get("median_bounce_pct"),
            "average_days_to_bounce_peak": validation.get(
                "average_days_to_bounce_peak"
            ),
        }

        return {
            key: cls.value_or_none(value)
            for key, value in fields.items()
        }

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
    def value(source, key):
        if source is None or key is None:
            return None
        if isinstance(source, dict):
            return source.get(key)
        return getattr(source, key, None)

    @staticmethod
    def first_existing(*values):
        for value in values:
            if value not in (None, ""):
                return value
        return None

    @staticmethod
    def average(left, right):
        try:
            if left is None or right is None:
                return None
            return (float(left) + float(right)) / 2.0
        except (TypeError, ValueError):
            return None

    @staticmethod
    def list_values(value):
        if value in (None, ""):
            return []
        if isinstance(value, (list, tuple)):
            return [str(item) for item in value]
        return [str(value)]

    @staticmethod
    def unique_text(values):
        unique = []
        for value in values or []:
            if value and value not in unique:
                unique.append(value)
        return unique

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
