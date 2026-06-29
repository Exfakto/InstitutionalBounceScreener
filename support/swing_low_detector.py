"""
Support swing-low detection.
"""

from __future__ import annotations

import pandas as pd


class SwingLowDetector:
    """
    Detects local lows in price history.
    """

    REQUIRED_COLUMNS = [
        "Low",
    ]

    def __init__(self, left_window=3, right_window=3):
        self.left_window = left_window
        self.right_window = right_window

    def detect(self, dataframe):
        """
        Return swing lows as dictionaries with date and price.
        """

        self.validate_columns(dataframe)

        if dataframe.empty:
            return []

        required_length = self.left_window + self.right_window + 1

        if len(dataframe) < required_length:
            return []

        swing_lows = []

        for position in range(self.left_window, len(dataframe) - self.right_window):

            low = dataframe["Low"].iloc[position]
            window = dataframe["Low"].iloc[
                position - self.left_window: position + self.right_window + 1
            ]

            if low != window.min():
                continue

            if (window == low).sum() > 1:
                continue

            swing_lows.append(
                {
                    "date": dataframe.index[position],
                    "price": float(low),
                }
            )

        return swing_lows

    def validate_columns(self, dataframe):
        missing = [
            column
            for column in self.REQUIRED_COLUMNS
            if column not in dataframe.columns
        ]

        if missing:
            raise ValueError(
                f"Missing required columns: {', '.join(missing)}"
            )
