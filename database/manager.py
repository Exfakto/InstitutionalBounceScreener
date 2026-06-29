import sqlite3
from pathlib import Path

import pandas as pd

from database.schema import PRICE_HISTORY_TABLE, STOCKS_TABLE

DATABASE_NAME = "InstitutionalBounce.db"
DATABASE_PATH = Path("data") / DATABASE_NAME


class DatabaseManager:

    def __init__(self):

        DATABASE_PATH.parent.mkdir(exist_ok=True)

        self.connection = sqlite3.connect(DATABASE_PATH)

        self.cursor = self.connection.cursor()

        self.initialize()

    def initialize(self):

        self.cursor.execute(STOCKS_TABLE)

        self.cursor.execute(PRICE_HISTORY_TABLE)

        self.connection.commit()

    #######################################################

    # STOCK TABLE

    #######################################################

    def add_stock(
        self,
        ticker,
        company,
        exchange,
        sector="",
        industry="",
    ):

        self.cursor.execute(
            """
            INSERT OR REPLACE INTO stocks
            (
                ticker,
                company,
                exchange,
                sector,
                industry,
                active
            )
            VALUES (?, ?, ?, ?, ?, 1)
            """,
            (
                ticker,
                company,
                exchange,
                sector,
                industry,
            ),
        )

        self.connection.commit()

    def get_all_tickers(self):

        self.cursor.execute(
            """
            SELECT ticker
            FROM stocks
            WHERE active = 1
            ORDER BY ticker
            """
        )

        return [row[0] for row in self.cursor.fetchall()]

    #######################################################

    # PRICE HISTORY

    #######################################################

    def save_price_history(
        self,
        ticker,
        history: pd.DataFrame,
    ):

        rows_saved = 0

        for date, row in history.iterrows():

            self.cursor.execute(
                """
                INSERT OR IGNORE INTO price_history
                (
                    ticker,
                    date,
                    open,
                    high,
                    low,
                    close,
                    volume
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
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

            rows_saved += self.cursor.rowcount

        self.connection.commit()

        return rows_saved

    def get_total_rows(self):

        self.cursor.execute(
            """
            SELECT COUNT(*)
            FROM price_history
            """
        )

        return self.cursor.fetchone()[0]

    #######################################################

    # DATABASE INFO

    #######################################################

    def stock_count(self):

        self.cursor.execute(
            """
            SELECT COUNT(*)
            FROM stocks
            """
        )

        return self.cursor.fetchone()[0]

    def close(self):

        self.connection.close()