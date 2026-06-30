from pathlib import Path

import pandas as pd


class FundamentalImporter:
    """
    Loads CSV-based fundamental metrics.
    """

    COLUMNS = [
        "ticker",
        "market_cap",
        "revenue_growth_ttm",
        "eps_growth_ttm",
        "roe",
        "gross_margin",
        "free_cash_flow",
        "debt_to_equity",
        "current_ratio",
    ]

    def __init__(self, csv_path=None):
        self.csv_path = Path(csv_path or "data/fundamentals/master_fundamentals.csv")

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

        for column in self.COLUMNS:
            if column == "ticker":
                continue

            dataframe[column] = pd.to_numeric(dataframe[column], errors="coerce")

        return dataframe
