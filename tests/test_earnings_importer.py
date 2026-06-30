import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from earnings import EarningsImporter


class EarningsImporterTest(unittest.TestCase):

    def test_missing_csv_returns_empty_dataframe(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "missing.csv"

            dataframe = EarningsImporter(path).load()

        self.assertTrue(dataframe.empty)
        self.assertEqual(list(dataframe.columns), EarningsImporter.COLUMNS)

    def test_loads_and_normalizes_earnings_csv(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "earnings.csv"
            path.write_text(
                "ticker,next_earnings_date,days_until_earnings,"
                "eps_surprise_pct\n"
                " aapl ,2026-07-15,15,8.5\n",
                encoding="utf-8",
            )

            dataframe = EarningsImporter(path).load()

        self.assertEqual(dataframe.loc[0, "ticker"], "AAPL")
        self.assertEqual(str(dataframe.loc[0, "next_earnings_date"]), "2026-07-15")
        self.assertEqual(dataframe.loc[0, "days_until_earnings"], 15)
        self.assertEqual(dataframe.loc[0, "eps_surprise_pct"], 8.5)
        self.assertIn("revenue_surprise_pct", dataframe.columns)
        self.assertTrue(pd.isna(dataframe.loc[0, "revenue_surprise_pct"]))

    def test_missing_ticker_column_raises(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "earnings.csv"
            path.write_text("days_until_earnings\n10\n", encoding="utf-8")

            with self.assertRaises(ValueError):
                EarningsImporter(path).load()


if __name__ == "__main__":
    unittest.main()
