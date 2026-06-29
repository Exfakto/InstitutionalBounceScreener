from services.indicator_service import IndicatorService


class IndicatorController:
    """
    Controller responsible for indicator-related actions.
    """

    def __init__(self):
        self.indicators = IndicatorService()

    # --------------------------------------------------
    # Indicators
    # --------------------------------------------------

    def calculate_indicators(self):
        """
        Calculate all supported technical indicators.
        """

        return self.indicators.calculate_indicators()

    def calculate_sma(self):
        """
        Calculate SMA20, SMA50 and SMA200.
        """

        return self.indicators.calculate_sma()

    def close(self):
        self.indicators.close()
