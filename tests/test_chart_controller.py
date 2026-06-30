import unittest

from controllers.chart_controller import ChartController


class FakeChartDataService:

    def __init__(self):
        self.ticker = None
        self.closed = False

    def get_chart_data(self, ticker):
        self.ticker = ticker
        return {"ticker": ticker, "prices": []}

    def close(self):
        self.closed = True


class ChartControllerTest(unittest.TestCase):

    def build_controller(self):
        controller = ChartController.__new__(ChartController)
        controller.chart_data_service = FakeChartDataService()
        return controller

    def test_get_chart_data_delegates_to_service(self):
        controller = self.build_controller()

        result = controller.get_chart_data("AAPL")

        self.assertEqual(result, {"ticker": "AAPL", "prices": []})
        self.assertEqual(controller.chart_data_service.ticker, "AAPL")

    def test_close_closes_service(self):
        controller = self.build_controller()

        controller.close()

        self.assertTrue(controller.chart_data_service.closed)


if __name__ == "__main__":
    unittest.main()
