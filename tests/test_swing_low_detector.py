import unittest

import pandas as pd

from support.swing_low_detector import SwingLowDetector


class SwingLowDetectorTest(unittest.TestCase):

    def test_detect_finds_local_lows(self):
        dataframe = pd.DataFrame(
            {"Low": [5, 3, 5, 4, 2, 4, 6]},
            index=pd.date_range("2026-01-01", periods=7),
        )

        swing_lows = SwingLowDetector(left_window=1, right_window=1).detect(dataframe)

        self.assertEqual(len(swing_lows), 2)
        self.assertEqual(swing_lows[0]["price"], 3.0)
        self.assertEqual(swing_lows[1]["price"], 2.0)

    def test_detect_handles_short_dataframe(self):
        dataframe = pd.DataFrame({"Low": [5, 3]})

        swing_lows = SwingLowDetector(left_window=1, right_window=1).detect(dataframe)

        self.assertEqual(swing_lows, [])

    def test_detect_requires_low_column(self):
        dataframe = pd.DataFrame({"Close": [1, 2, 3]})

        with self.assertRaises(ValueError):
            SwingLowDetector(left_window=1, right_window=1).detect(dataframe)


if __name__ == "__main__":
    unittest.main()
