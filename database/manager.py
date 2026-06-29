from database.database import Database


class DatabaseManager:

    def __init__(self):
        self.db = Database()
        self.db.initialize()

    def save_price_history(self, ticker, history):

        sql = """
        INSERT OR IGNORE INTO price_history
        (ticker, date, open, high, low, close, volume)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """

        rows_saved = 0

        for date, row in history.iterrows():

            self.db.cursor.execute(
                sql,
                (
                    ticker,
                    str(date.date()),
                    float(row["Open"]),
                    float(row["High"]),
                    float(row["Low"]),
                    float(row["Close"]),
                    int(row["Volume"]),
                ),
            )

            rows_saved += 1

        self.db.connection.commit()

        return rows_saved

    def get_total_rows(self):

        self.db.cursor.execute(
            "SELECT COUNT(*) FROM price_history"
        )

        return self.db.cursor.fetchone()[0]

    def close(self):
        self.db.close()