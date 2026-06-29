"""
Institutional Bounce Platform
Indicator Engine

Base class for all technical indicators.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
import pandas as pd


class BaseIndicator(ABC):
    """
    Abstract base class for every technical indicator.

    Every indicator must:

    - Receive a pandas DataFrame
    - Return a pandas DataFrame
    - Never modify the original dataframe
    - Never access SQLite
    - Never download data
    - Never interact with the GUI
    """

    name = "Base Indicator"

    @abstractmethod
    def calculate(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate the indicator.

        Parameters
        ----------
        dataframe
            DataFrame containing historical market data.

        Returns
        -------
        pandas.DataFrame
            Original dataframe with additional indicator columns.
        """
        raise NotImplementedError

    @staticmethod
    def validate_columns(
        dataframe: pd.DataFrame,
        required_columns: list[str],
    ) -> None:
        """
        Validate required dataframe columns.
        """

        missing = [
            column
            for column in required_columns
            if column not in dataframe.columns
        ]

        if missing:
            raise ValueError(
                f"Missing required columns: {', '.join(missing)}"
            )