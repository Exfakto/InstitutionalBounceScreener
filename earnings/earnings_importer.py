from pathlib import Path

import pandas as pd


class EarningsImporter:
    """
    Loads CSV-based earnings intelligence.
    """

    COLUMNS = [
        "ticker",
        "next_earnings_date",
        "days_until_earnings",
        "previous_earnings_date",
        "eps_surprise_pct",
        "revenue_surprise_pct",
    ]

    DATE_COLUMNS = [
        "next_earnings_date",
        "previous_earnings_date",
    ]

    NUMERIC_COLUMNS = [
        "days_until_earnings",
        "eps_surprise_pct",
        "revenue_surprise_pct",
    ]

    def __init__(self, csv_path=None):
        self.csv_path = Path(csv_path or "data/earnings/master_earnings.csv")

    def load(self):
        """
        Return an empty dataframe when the CSV file is missing.
        """

        if not self.csv_path.exists():
            return pd.DataFrame(columns=self.COLUMNS)

        dataframe = pd.read_csv(self.csv_path)

        if "ticker" not in dataframe.columns:
            raise ValueError("Missing required column: ticker")

        for column in self.COLUMNS:
            if column not in dataframe.columns:
                dataframe[column] = None

        dataframe = dataframe[self.COLUMNS].copy()
        dataframe["ticker"] = dataframe["ticker"].astype(str).str.upper().str.strip()

        for column in self.DATE_COLUMNS:
            dataframe[column] = pd.to_datetime(
                dataframe[column],
                errors="coerce",
            ).dt.date

        for column in self.NUMERIC_COLUMNS:
            dataframe[column] = pd.to_numeric(dataframe[column], errors="coerce")

        return dataframe
