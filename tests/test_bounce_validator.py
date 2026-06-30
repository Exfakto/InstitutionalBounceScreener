import unittest

import pandas as pd

from bounce import BounceValidator


class BounceValidatorTest(unittest.TestCase):

    def support_zone(self):
        return {
            "id": 1,
            "ticker": "AAA",
            "zone_low": 10.0,
            "zone_high": 10.2,
            "zone_mid": 10.1,
        }

    def dataframe(self, lows, highs, closes):
        return pd.DataFrame(
            {
                "Low": lows,
                "High": highs,
                "Close": closes,
            },
            index=pd.date_range("2026-01-01", periods=len(lows)),
        )

    def test_collapses_consecutive_candles_inside_zone(self):
        dataframe = self.dataframe(
            lows=[10.1, 10.0, 10.05, 11.0, 10.1],
            highs=[10.3, 10.2, 10.2, 11.2, 10.2],
            closes=[10.2, 10.1, 10.1, 11.0, 10.1],
        )

        touches = BounceValidator().touch_events(dataframe, self.support_zone())

        self.assertEqual(touches, [0, 4])

    def test_success_requires_bounce_before_breakdown(self):
        dataframe = self.dataframe(
            lows=[10.1, 10.5, 9.0],
            highs=[10.2, 10.7, 9.8],
            closes=[10.1, 10.6, 9.5],
        )

        metrics = BounceValidator().validate(dataframe, self.support_zone())

        self.assertEqual(metrics["total_touches"], 1)
        self.assertEqual(metrics["successful_bounces"], 1)
        self.assertEqual(metrics["failed_breakdowns"], 0)

    def test_failure_requires_breakdown_before_bounce(self):
        dataframe = self.dataframe(
            lows=[10.1, 9.0, 10.5],
            highs=[10.2, 10.0, 10.8],
            closes=[10.1, 9.5, 10.7],
        )

        metrics = BounceValidator().validate(dataframe, self.support_zone())

        self.assertEqual(metrics["total_touches"], 1)
        self.assertEqual(metrics["successful_bounces"], 0)
        self.assertEqual(metrics["failed_breakdowns"], 1)

    def test_neutral_when_no_target_or_breakdown_in_forward_window(self):
        dataframe = self.dataframe(
            lows=[10.1, 10.4, 10.5],
            highs=[10.2, 10.4, 10.5],
            closes=[10.1, 10.4, 10.5],
        )

        metrics = BounceValidator().validate(dataframe, self.support_zone())

        self.assertEqual(metrics["neutral_touches"], 1)
        self.assertEqual(metrics["successful_bounces"], 0)
        self.assertEqual(metrics["failed_breakdowns"], 0)

    def test_calculates_aggregate_metrics(self):
        dataframe = self.dataframe(
            lows=[10.1, 10.5, 11.0, 10.1, 10.5],
            highs=[10.2, 10.7, 11.0, 10.2, 10.7],
            closes=[10.1, 10.6, 11.0, 10.1, 10.6],
        )

        metrics = BounceValidator().validate(dataframe, self.support_zone())

        self.assertEqual(metrics["total_touches"], 2)
        self.assertEqual(metrics["successful_bounces"], 2)
        self.assertEqual(metrics["bounce_success_rate"], 100.0)
        self.assertGreater(metrics["average_bounce_pct"], 0)
        self.assertGreater(metrics["median_bounce_pct"], 0)
        self.assertEqual(metrics["average_days_to_bounce_peak"], 1)


if __name__ == "__main__":
    unittest.main()
