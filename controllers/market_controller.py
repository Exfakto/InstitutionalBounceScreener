from services.market_service import MarketService


class MarketController:
    """
    Controller responsible for all market-related actions.
    """

    def __init__(self):
        self.market = MarketService()

    # --------------------------------------------------
    # Universe
    # --------------------------------------------------

    def update_universe(self):
        """
        Import the master universe CSV into SQLite.
        """

        imported = self.market.import_universe()

        total = self.market.total_stocks()

        return imported, total

    def get_active_market_universe_records(self):
        """
        Return active records from the market universe table.
        """

        return self.market.get_active_market_universe_records()

    # --------------------------------------------------
    # Prices
    # --------------------------------------------------

    def download_prices(self):
        """
        Download price history for every active stock.
        """

        market = self.market.download_prices()

        if not market:
            return {}, self.market.total_price_rows()

        results = self.market.save_market_data(market)

        total_rows = self.market.total_price_rows()

        return results, total_rows

    # --------------------------------------------------
    # Statistics
    # --------------------------------------------------

    def get_statistics(self):

        return {
            "stocks": self.market.total_stocks(),
            "rows": self.market.total_price_rows(),
            "indicator_rows": self.market.total_indicator_rows(),
            "support_levels": self.market.total_support_levels(),
            "validated_zones": self.market.total_validated_zones(),
        }

    def close(self):
        self.market.close()
