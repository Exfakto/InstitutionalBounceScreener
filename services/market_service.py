from market.universe import UniverseManager
from market.downloader import download_multiple_stocks

from database.manager import DatabaseManager


class MarketService:
    """
    Business logic for market operations.
    """

    def __init__(self):
        self.db = DatabaseManager()
        self.universe = UniverseManager()

    # --------------------------------------------------
    # Universe
    # --------------------------------------------------

    def import_universe(self):
        """
        Import the master universe into SQLite using a batch transaction.
        """

        dataframe = self.universe.load_master_universe()

        return self.db.add_stocks(dataframe)

    def get_active_tickers(self):
        """
        Return all active tickers from the database.
        """

        return self.db.get_all_tickers()

    def get_active_market_universe_records(self):
        """
        Return active records from the market universe table.
        """

        return self.db.get_active_market_universe_records()

    # --------------------------------------------------
    # Market Data
    # --------------------------------------------------

    def download_prices(self):
        """
        Download market data for every active ticker.
        """

        tickers = self.get_active_tickers()

        if not tickers:
            return {}

        return download_multiple_stocks(tickers)

    def save_market_data(self, market):
        """
        Save downloaded market data into SQLite.
        """

        results = {}

        for ticker, history in market.items():

            rows = self.db.save_price_history(
                ticker,
                history,
            )

            results[ticker] = rows

        return results

    # --------------------------------------------------
    # Statistics
    # --------------------------------------------------

    def total_stocks(self):
        return self.db.stock_count()

    def total_price_rows(self):
        return self.db.get_total_rows()

    def total_indicator_rows(self):
        return self.db.indicator_count()

    def total_support_levels(self):
        return self.db.support_level_count()

    def total_validated_zones(self):
        return self.db.bounce_validation_count()

    # --------------------------------------------------

    def close(self):
        self.db.close()
