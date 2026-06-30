from services.chart_data_service import ChartDataService


class ChartController:
    """
    Controller responsible for read-only chart data requests.
    """

    def __init__(self):
        self.chart_data_service = ChartDataService()

    def get_chart_data(self, ticker):
        """
        Return local chart data for one ticker.
        """

        return self.chart_data_service.get_chart_data(ticker)

    def close(self):
        self.chart_data_service.close()
