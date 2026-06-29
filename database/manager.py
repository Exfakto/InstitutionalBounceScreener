from pathlib import Path
import sqlite3
import pandas as pd

from database.schema import (
    PRICE_HISTORY_TABLE,
    SUPPORT_LEVELS_TABLE,
    STOCKS_TABLE,
    TECHNICAL_INDICATORS_TABLE,
)

DATABASE_NAME = "InstitutionalBounce.db"
DATABASE_PATH = Path("data") / DATABASE_NAME


class DatabaseManager:
    """
    Central SQLite database manager.

    Responsibilities
    ----------------
    - Create/open the database
    - Initialize database schema
    - Manage the stock universe
    - Store price history
    - Store technical indicators
    - Provide database statistics
    """

    def __init__(self):

        DATABASE_PATH.parent.mkdir(exist_ok=True)

        self.connection = sqlite3.connect(DATABASE_PATH)
        self.connection.row_factory = sqlite3.Row

        self.cursor = self.connection.cursor()

        self.initialize()

    # ==========================================================
    # Database Initialization
    # ==========================================================

    def initialize(self):

        self.cursor.execute(STOCKS_TABLE)
        self.cursor.execute(PRICE_HISTORY_TABLE)
        self.cursor.execute(TECHNICAL_INDICATORS_TABLE)
        self.cursor.execute(SUPPORT_LEVELS_TABLE)

        self.connection.commit()

    # ==========================================================
    # Universe
    # ==========================================================

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

    def add_stocks(self, dataframe):

        rows = []

        for _, row in dataframe.iterrows():

            rows.append(
                (
                    row["ticker"],
                    row["company"],
                    row["exchange"],
                    row.get("sector", ""),
                    row.get("industry", ""),
                )
            )

        self.cursor.executemany(
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
            rows,
        )

        self.connection.commit()

        return len(rows)

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

    def stock_count(self):

        self.cursor.execute(
            """
            SELECT COUNT(*)
            FROM stocks
            """
        )

        return self.cursor.fetchone()[0]

    # ==========================================================
    # Price History
    # ==========================================================

    def save_price_history(self, ticker, history):

        inserted = 0

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

            inserted += self.cursor.rowcount

        self.connection.commit()

        return inserted

    def get_price_history(self, ticker):
        """
        Returns all historical prices for a ticker.

        Returns
        -------
        pandas.DataFrame
        """

        query = """
        SELECT
            date,
            open,
            high,
            low,
            close,
            volume
        FROM price_history
        WHERE ticker = ?
        ORDER BY date
        """

        dataframe = pd.read_sql_query(
            query,
            self.connection,
            params=(ticker,),
        )

        if dataframe.empty:
            return dataframe

        dataframe.rename(
            columns={
                "open": "Open",
                "high": "High",
                "low": "Low",
                "close": "Close",
                "volume": "Volume",
            },
            inplace=True,
        )

        dataframe["date"] = pd.to_datetime(
            dataframe["date"]
        )

        dataframe.set_index(
            "date",
            inplace=True,
        )

        return dataframe

    def get_total_rows(self):

        self.cursor.execute(
            """
            SELECT COUNT(*)
            FROM price_history
            """
        )

        return self.cursor.fetchone()[0]

    # ==========================================================
    # Technical Indicators
    # ==========================================================

    def save_indicator_row(self, values):
        """
        Save one row of technical indicators.

        Expected tuple order:

        (
            ticker,
            date,
            sma20,
            sma50,
            sma200,
            ema21,
            rsi14,
            atr14,
            avg_volume20,
            relative_volume,
            high52,
            low52,
            macd,
            macd_signal,
            macd_histogram,
        )
        """

        self.cursor.execute(
            """
            INSERT OR REPLACE INTO technical_indicators
            (
                ticker,
                date,
                sma20,
                sma50,
                sma200,
                ema21,
                rsi14,
                atr14,
                avg_volume20,
                relative_volume,
                high52,
                low52,
                macd,
                macd_signal,
                macd_histogram
            )
            VALUES
            (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            """,
            values,
        )

    def save_sma(self, dataframe):
        """
        Save SMA calculations into technical_indicators.
        """

        rows = []

        for date, row in dataframe.iterrows():

            rows.append(
                (
                    row["ticker"],
                    str(date.date()),
                    row["sma20"],
                    row["sma50"],
                    row["sma200"],
                )
            )

        self.cursor.executemany(
            """
            INSERT OR REPLACE INTO technical_indicators
            (
                ticker,
                date,
                sma20,
                sma50,
                sma200
            )
            VALUES
            (
                ?, ?, ?, ?, ?
            )
            """,
            rows,
        )

        self.connection.commit()

    def indicator_count(self):

        self.cursor.execute(
            """
            SELECT COUNT(*)
            FROM technical_indicators
            """
        )

        return self.cursor.fetchone()[0]

    # ==========================================================
    # Support Levels
    # ==========================================================

    def save_support_levels(self, ticker, zones):
        """
        Replace stored support levels for one ticker.
        """

        self.delete_support_levels(ticker)

        rows = []

        for zone in zones:
            rows.append(
                (
                    ticker,
                    float(zone["zone_low"]),
                    float(zone["zone_high"]),
                    float(zone["zone_mid"]),
                    int(zone["touches"]),
                    float(zone["strength_score"]),
                    float(zone["current_price"]),
                    float(zone["distance_from_current"]),
                    float(zone["distance_from_current_pct"]),
                    self._format_date(zone.get("first_touch_date")),
                    self._format_date(zone.get("last_touch_date")),
                )
            )

        if rows:
            self.cursor.executemany(
                """
                INSERT INTO support_levels
                (
                    ticker,
                    zone_low,
                    zone_high,
                    zone_mid,
                    touches,
                    strength_score,
                    current_price,
                    distance_from_current,
                    distance_from_current_pct,
                    first_touch_date,
                    last_touch_date
                )
                VALUES
                (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                """,
                rows,
            )

        self.connection.commit()

        return len(rows)

    def delete_support_levels(self, ticker):
        """
        Delete stored support levels for one ticker.
        """

        self.cursor.execute(
            """
            DELETE FROM support_levels
            WHERE ticker = ?
            """,
            (ticker,),
        )

    def support_level_count(self):

        self.cursor.execute(
            """
            SELECT COUNT(*)
            FROM support_levels
            """
        )

        return self.cursor.fetchone()[0]

    def get_support_levels(self, ticker):

        self.cursor.execute(
            """
            SELECT
                ticker,
                zone_low,
                zone_high,
                zone_mid,
                touches,
                strength_score,
                current_price,
                distance_from_current,
                distance_from_current_pct,
                first_touch_date,
                last_touch_date
            FROM support_levels
            WHERE ticker = ?
            ORDER BY strength_score DESC, zone_mid
            """,
            (ticker,),
        )

        return self.cursor.fetchall()

    # ==========================================================
    # Utilities
    # ==========================================================

    def execute(self, sql, params=None):

        if params is None:
            self.cursor.execute(sql)
        else:
            self.cursor.execute(sql, params)

        self.connection.commit()

    def query(self, sql, params=None):

        if params is None:
            self.cursor.execute(sql)
        else:
            self.cursor.execute(sql, params)

        return self.cursor.fetchall()

    def commit(self):
        """
        Commit current transaction.
        """
        self.connection.commit()

    @staticmethod
    def _format_date(value):

        if value is None:
            return None

        if hasattr(value, "date"):
            return str(value.date())

        return str(value)

    # ==========================================================
    # Shutdown
    # ==========================================================

    def close(self):

        self.connection.close()

        
