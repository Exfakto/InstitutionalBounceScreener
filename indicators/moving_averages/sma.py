"""
Institutional Bounce Platform
Indicator Engine

Simple Moving Average (SMA)
"""

from __future__ import annotations

import pandas as pd

from indicators.base_indicator import BaseIndicator


class SMAIndicator(BaseIndicator):
    """
    Calculates Simple Moving Averages.

    Indicators
    ----------
    SMA20
    SMA50
    SMA200
    """

    name = "Simple Moving Average"

    REQUIRED_COLUMNS = [
        "Close",
    ]

    def calculate(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate SMA20, SMA50 and SMA200.
        """

        self.validate_columns(
            dataframe,
            self.REQUIRED_COLUMNS,
        )

        result = dataframe.copy()

        result["sma20"] = (
            result["Close"]
            .rolling(window=20, min_periods=20)
            .mean()
        )

        result["sma50"] = (
            result["Close"]
            .rolling(window=50, min_periods=50)
            .mean()
        )

        result["sma200"] = (
            result["Close"]
            .rolling(window=200, min_periods=200)
            .mean()
        )

        return result

    @staticmethod
    def latest_values(dataframe: pd.DataFrame) -> dict:
        """
        Returns the most recent SMA values.
        """

        if dataframe.empty:

            return {
                "sma20": None,
                "sma50": None,
                "sma200": None,
            }

        last = dataframe.iloc[-1]

        return {
            "sma20": last.get("sma20"),
            "sma50": last.get("sma50"),
            "sma200": last.get("sma200"),
        }