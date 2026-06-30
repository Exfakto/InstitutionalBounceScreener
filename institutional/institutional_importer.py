from pathlib import Path

import pandas as pd


class InstitutionalImporter:
    """
    Loads CSV-based institutional metrics.
    """

    COLUMNS = [
        "ticker",
        "institutional_ownership_pct",
        "institutional_ownership_change_qoq",
        "net_institutional_buying",
        "insider_buying_flag",
        "insider_selling_flag",
    ]

    FLAG_COLUMNS = [
        "insider_buying_flag",
        "insider_selling_flag",
    ]

    def __init__(self, csv_path=None):
        self.csv_path = Path(
            csv_path or "data/institutional/master_institutional.csv"
        )

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

            if column in self.FLAG_COLUMNS:
                dataframe[column] = dataframe[column].apply(self._flag_value)
            else:
                dataframe[column] = pd.to_numeric(dataframe[column], errors="coerce")

        return dataframe

    @staticmethod
    def _flag_value(value):

        if pd.isna(value):
            return 0

        if isinstance(value, str):
            return 1 if value.strip().lower() in {"1", "true", "yes", "y"} else 0

        return 1 if value else 0
