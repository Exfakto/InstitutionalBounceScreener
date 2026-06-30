import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from fundamentals import FundamentalImporter


class FundamentalImporterTest(unittest.TestCase):

    def test_missing_csv_returns_empty_dataframe(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "missing.csv"

            dataframe = FundamentalImporter(path).load()

        self.assertTrue(dataframe.empty)
        self.assertEqual(list(dataframe.columns), FundamentalImporter.COLUMNS)

    def test_loads_and_normalizes_fundamental_csv(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "fundamentals.csv"
            path.write_text(
                "ticker,market_cap,revenue_growth_ttm\n"
                " aapl ,3000000000000,8.5\n",
                encoding="utf-8",
            )

            dataframe = FundamentalImporter(path).load()

        self.assertEqual(dataframe.loc[0, "ticker"], "AAPL")
        self.assertEqual(dataframe.loc[0, "market_cap"], 3000000000000)
        self.assertEqual(dataframe.loc[0, "revenue_growth_ttm"], 8.5)
        self.assertIn("current_ratio", dataframe.columns)

    def test_missing_ticker_column_raises(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "fundamentals.csv"
            path.write_text("market_cap\n100\n", encoding="utf-8")

            with self.assertRaises(ValueError):
                FundamentalImporter(path).load()


if __name__ == "__main__":
    unittest.main()
