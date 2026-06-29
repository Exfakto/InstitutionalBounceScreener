from database.manager import DatabaseManager


class DatabaseService:

    def __init__(self):

        self.manager = DatabaseManager()

    def initialize(self):

        self.manager.db.initialize()

    def save_price_history(self, ticker, history):

        return self.manager.save_price_history(
            ticker,
            history,
        )

    def total_rows(self):

        return self.manager.get_total_rows()

    def close(self):

        self.manager.close()