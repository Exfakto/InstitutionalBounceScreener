import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from institutional import InstitutionalImporter


class InstitutionalImporterTest(unittest.TestCase):

    def test_missing_csv_returns_empty_dataframe(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "missing.csv"

            dataframe = InstitutionalImporter(path).load()

        self.assertTrue(dataframe.empty)
        self.assertEqual(list(dataframe.columns), InstitutionalImporter.COLUMNS)

    def test_loads_and_normalizes_institutional_csv(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "institutional.csv"
            path.write_text(
                "ticker,institutional_ownership_pct,insider_buying_flag,insider_selling_flag\n"
                " msft ,72.5,yes,no\n",
                encoding="utf-8",
            )

            dataframe = InstitutionalImporter(path).load()

        self.assertEqual(dataframe.loc[0, "ticker"], "MSFT")
        self.assertEqual(dataframe.loc[0, "institutional_ownership_pct"], 72.5)
        self.assertEqual(dataframe.loc[0, "insider_buying_flag"], 1)
        self.assertEqual(dataframe.loc[0, "insider_selling_flag"], 0)

    def test_missing_ticker_column_raises(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "institutional.csv"
            path.write_text("institutional_ownership_pct\n50\n", encoding="utf-8")

            with self.assertRaises(ValueError):
                InstitutionalImporter(path).load()


if __name__ == "__main__":
    unittest.main()
