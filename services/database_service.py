from database.manager import DatabaseManager


class DatabaseService:

    def __init__(self):

        self.manager = DatabaseManager()

    def initialize(self):

        self.manager.db.initialize()

    def save_price_history(self, ticker, history):

        return self.manager.upsert_ohlcv(
            ticker,
            history,
            "database_service",
        )

    def total_rows(self):

        return sum(
            int(row.get("row_count") or 0)
            for row in self.manager.fetch_ohlcv_cache_coverage()
        )

    def close(self):

        self.manager.close()
