import unittest

import pandas as pd

from indicators.base_indicator import BaseIndicator
from indicators.moving_averages.sma import SMAIndicator


class SMAIndicatorTest(unittest.TestCase):

    def test_base_indicator_cannot_be_instantiated(self):
        with self.assertRaises(TypeError):
            BaseIndicator()

    def test_validate_columns_raises_for_missing_columns(self):
        dataframe = pd.DataFrame({"Open": [1.0]})

        with self.assertRaises(ValueError) as context:
            SMAIndicator.validate_columns(dataframe, ["Close"])

        self.assertIn("Close", str(context.exception))

    def test_calculate_adds_sma_columns_without_mutating_input(self):
        prices = pd.DataFrame({"Close": range(1, 251)})
        original_columns = list(prices.columns)

        result = SMAIndicator().calculate(prices)

        self.assertEqual(list(prices.columns), original_columns)
        self.assertIn("sma20", result.columns)
        self.assertIn("sma50", result.columns)
        self.assertIn("sma200", result.columns)

    def test_calculate_sma_values(self):
        prices = pd.DataFrame({"Close": range(1, 251)})

        result = SMAIndicator().calculate(prices)

        self.assertAlmostEqual(result.loc[19, "sma20"], 10.5)
        self.assertAlmostEqual(result.loc[49, "sma50"], 25.5)
        self.assertAlmostEqual(result.loc[199, "sma200"], 100.5)
        self.assertAlmostEqual(result.loc[249, "sma20"], 240.5)
        self.assertAlmostEqual(result.loc[249, "sma50"], 225.5)
        self.assertAlmostEqual(result.loc[249, "sma200"], 150.5)

    def test_latest_values_returns_last_sma_values(self):
        prices = pd.DataFrame({"Close": range(1, 251)})
        result = SMAIndicator().calculate(prices)

        latest = SMAIndicator.latest_values(result)

        self.assertAlmostEqual(latest["sma20"], 240.5)
        self.assertAlmostEqual(latest["sma50"], 225.5)
        self.assertAlmostEqual(latest["sma200"], 150.5)

    def test_latest_values_handles_empty_dataframe(self):
        latest = SMAIndicator.latest_values(pd.DataFrame())

        self.assertEqual(
            latest,
            {
                "sma20": None,
                "sma50": None,
                "sma200": None,
            },
        )


if __name__ == "__main__":
    unittest.main()
