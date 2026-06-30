import unittest

import pandas as pd

from services.chart_data_service import ChartDataService


class FakeChartDatabase:

    def __init__(
        self,
        prices=None,
        indicators=None,
        support_zones=None,
        bounce_validations=None,
    ):
        self.prices = prices
        self.indicators = indicators or []
        self.support_zones = support_zones or []
        self.bounce_validations = bounce_validations or []
        self.closed = False

    def get_price_history(self, ticker):
        if self.prices is None:
            return pd.DataFrame()

        return self.prices

    def get_technical_indicators(self, ticker):
        return self.indicators

    def get_support_levels(self, ticker):
        return self.support_zones

    def get_bounce_validations(self, ticker):
        return self.bounce_validations

    def close(self):
        self.closed = True

    def __getattr__(self, name):
        if (
            name.startswith("save")
            or name.startswith("delete")
            or name in {"commit", "execute"}
        ):
            raise AssertionError(f"ChartDataService called write method {name}")

        raise AttributeError(name)


class ChartDataServiceTest(unittest.TestCase):

    def build_service(
        self,
        prices=None,
        indicators=None,
        support_zones=None,
        bounce_validations=None,
    ):
        return ChartDataService(
            db=FakeChartDatabase(
                prices=prices,
                indicators=indicators,
                support_zones=support_zones,
                bounce_validations=bounce_validations,
            )
        )

    def price_history(self):
        return pd.DataFrame(
            {
                "Open": [100.0, 101.0],
                "High": [102.0, 103.0],
                "Low": [99.0, 100.0],
                "Close": [101.0, 102.0],
                "Volume": [1000, 1100],
            },
            index=pd.to_datetime(["2026-01-01", "2026-01-02"]),
        )

    def test_returns_price_history_only_with_optional_warnings(self):
        service = self.build_service(prices=self.price_history())

        chart_data = service.get_chart_data("AAA")

        self.assertEqual(chart_data["ticker"], "AAA")
        self.assertEqual(len(chart_data["prices"]), 2)
        self.assertEqual(chart_data["prices"][0]["date"], "2026-01-01")
        self.assertEqual(chart_data["prices"][0]["close"], 101.0)
        self.assertIsNone(chart_data["prices"][0]["sma20"])
        self.assertIsNone(chart_data["prices"][0]["sma50"])
        self.assertIsNone(chart_data["prices"][0]["sma200"])
        self.assertEqual(chart_data["indicators"], [])
        self.assertEqual(chart_data["support_zones"], [])
        self.assertEqual(chart_data["bounce_validations"], [])
        self.assertIn("Missing technical indicators", chart_data["warnings"])
        self.assertIn("Missing support zones", chart_data["warnings"])
        self.assertIn("Missing bounce validations", chart_data["warnings"])
        self.assertNotIn("Missing price history", chart_data["warnings"])

    def test_returns_price_history_with_indicators(self):
        service = self.build_service(
            prices=self.price_history(),
            indicators=[
                {
                    "ticker": "AAA",
                    "date": "2026-01-01",
                    "sma20": 100.5,
                    "sma50": 99.5,
                    "sma200": 95.0,
                }
            ],
        )

        chart_data = service.get_chart_data("AAA")

        self.assertEqual(len(chart_data["prices"]), 2)
        self.assertEqual(chart_data["indicators"][0]["sma20"], 100.5)
        self.assertEqual(chart_data["prices"][0]["sma20"], 100.5)
        self.assertEqual(chart_data["prices"][0]["sma50"], 99.5)
        self.assertEqual(chart_data["prices"][0]["sma200"], 95.0)
        self.assertIsNone(chart_data["prices"][1]["sma20"])
        self.assertNotIn("Missing technical indicators", chart_data["warnings"])

    def test_merges_indicator_rows_with_price_history_by_date(self):
        service = self.build_service(
            prices=self.price_history(),
            indicators=[
                {
                    "ticker": "AAA",
                    "date": "2026-01-02",
                    "sma20": 101.5,
                    "sma50": None,
                    "sma200": None,
                }
            ],
        )

        chart_data = service.get_chart_data("AAA")

        self.assertIsNone(chart_data["prices"][0]["sma20"])
        self.assertEqual(chart_data["prices"][1]["sma20"], 101.5)

    def test_missing_indicator_rows_do_not_crash_price_data(self):
        service = self.build_service(
            prices=self.price_history(),
            indicators=[
                {
                    "ticker": "AAA",
                    "date": "2026-01-03",
                    "sma20": 105.0,
                    "sma50": 104.0,
                    "sma200": 100.0,
                }
            ],
        )

        chart_data = service.get_chart_data("AAA")

        self.assertEqual(len(chart_data["prices"]), 2)
        self.assertIsNone(chart_data["prices"][0]["sma20"])
        self.assertIsNone(chart_data["prices"][1]["sma20"])

    def test_returns_price_history_with_support_zones(self):
        service = self.build_service(
            prices=self.price_history(),
            support_zones=[
                {
                    "id": 1,
                    "ticker": "AAA",
                    "zone_low": 98.0,
                    "zone_high": 100.0,
                    "strength_score": 85.0,
                }
            ],
        )

        chart_data = service.get_chart_data("AAA")

        self.assertEqual(chart_data["support_zones"][0]["zone_low"], 98.0)
        self.assertNotIn("Missing support zones", chart_data["warnings"])

    def test_returns_price_history_with_bounce_validations(self):
        service = self.build_service(
            prices=self.price_history(),
            bounce_validations=[
                {
                    "support_level_id": 1,
                    "ticker": "AAA",
                    "bounce_success_rate": 80.0,
                    "successful_bounces": 4,
                }
            ],
        )

        chart_data = service.get_chart_data("AAA")

        self.assertEqual(
            chart_data["bounce_validations"][0]["bounce_success_rate"],
            80.0,
        )
        self.assertNotIn("Missing bounce validations", chart_data["warnings"])

    def test_missing_price_history_returns_safe_empty_chart_data(self):
        service = self.build_service()

        chart_data = service.get_chart_data("EMPTY")

        self.assertEqual(chart_data["ticker"], "EMPTY")
        self.assertEqual(chart_data["prices"], [])
        self.assertEqual(chart_data["indicators"], [])
        self.assertEqual(chart_data["support_zones"], [])
        self.assertEqual(chart_data["bounce_validations"], [])
        self.assertIn("Missing price history", chart_data["warnings"])

    def test_missing_optional_data_does_not_crash(self):
        service = self.build_service(prices=self.price_history())

        chart_data = service.get_chart_data("AAA")

        self.assertEqual(len(chart_data["prices"]), 2)
        self.assertEqual(len(chart_data["warnings"]), 3)

    def test_service_is_read_only(self):
        service = self.build_service(
            prices=self.price_history(),
            indicators=[{"date": "2026-01-01", "sma20": 100.0}],
            support_zones=[{"zone_low": 98.0, "zone_high": 100.0}],
            bounce_validations=[{"bounce_success_rate": 80.0}],
        )

        chart_data = service.get_chart_data("AAA")

        self.assertEqual(chart_data["ticker"], "AAA")

    def test_close_closes_database(self):
        service = self.build_service(prices=self.price_history())

        service.close()

        self.assertTrue(service.db.closed)


if __name__ == "__main__":
    unittest.main()
