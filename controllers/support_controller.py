from services.support_service import SupportDetectionService


class SupportController:
    """
    Controller responsible for support detection actions.
    """

    def __init__(self):
        self.support = SupportDetectionService()

    def detect_support(self):
        """
        Detect support levels for active tickers.
        """

        return self.support.detect_support()

    def close(self):
        self.support.close()
