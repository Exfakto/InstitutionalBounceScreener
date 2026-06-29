from services.market_service import MarketService

from services.database_service import DatabaseService


class MarketController:

    def __init__(self):

        self.market = MarketService()

        self.database = DatabaseService()

    def download_market(self):

        market = self.market.download_market()

        results = {}

        for ticker, history in market.items():

            rows = self.database.save_price_history(
                ticker,
                history,
            )

            results[ticker] = rows

        total = self.database.total_rows()

        self.database.close()

        return results, total