from market.downloader import download_multiple_stocks

from config.settings import (
    DEFAULT_TICKERS,
    DOWNLOAD_PERIOD,
)


class MarketService:

    def download_market(self):

        return download_multiple_stocks(
            DEFAULT_TICKERS,
            DOWNLOAD_PERIOD,
        )