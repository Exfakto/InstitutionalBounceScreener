from pathlib import Path
import sqlite3
import pandas as pd

from database.schema import (
    BOUNCE_VALIDATIONS_TABLE,
    EARNINGS_TABLE,
    FUNDAMENTALS_TABLE,
    INSTITUTIONAL_METRICS_TABLE,
    PRICE_HISTORY_TABLE,
    SUPPORT_LEVELS_TABLE,
    STOCKS_TABLE,
    TECHNICAL_INDICATORS_TABLE,
    WATCHLIST_TABLE,
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
        self.cursor.execute(BOUNCE_VALIDATIONS_TABLE)
        self.cursor.execute(FUNDAMENTALS_TABLE)
        self.cursor.execute(INSTITUTIONAL_METRICS_TABLE)
        self.cursor.execute(EARNINGS_TABLE)
        self.cursor.execute(WATCHLIST_TABLE)

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

    def get_technical_indicators(self, ticker):
        """
        Return stored technical indicator rows for a ticker ordered by date.
        """

        self.cursor.execute(
            """
            SELECT
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
            FROM technical_indicators
            WHERE ticker = ?
            ORDER BY date
            """,
            (ticker,),
        )

        return self.cursor.fetchall()

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
                id,
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

    def get_all_support_levels(self):

        self.cursor.execute(
            """
            SELECT
                id,
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
            ORDER BY ticker, strength_score DESC, zone_mid
            """
        )

        return self.cursor.fetchall()

    # ==========================================================
    # Bounce Validations
    # ==========================================================

    def save_bounce_validations(self, validations):
        """
        Save bounce validation metrics.
        """

        rows = []

        for validation in validations:
            rows.append(
                (
                    int(validation["support_level_id"]),
                    validation["ticker"],
                    int(validation["total_touches"]),
                    int(validation["successful_bounces"]),
                    int(validation["failed_breakdowns"]),
                    int(validation["neutral_touches"]),
                    float(validation["bounce_success_rate"]),
                    self._sqlite_float(validation.get("average_bounce_pct")),
                    self._sqlite_float(validation.get("median_bounce_pct")),
                    self._sqlite_float(
                        validation.get("average_days_to_bounce_peak")
                    ),
                    float(validation["current_distance_to_support"]),
                    float(validation["current_distance_to_support_pct"]),
                )
            )

        if rows:
            self.cursor.executemany(
                """
                INSERT OR REPLACE INTO bounce_validations
                (
                    support_level_id,
                    ticker,
                    total_touches,
                    successful_bounces,
                    failed_breakdowns,
                    neutral_touches,
                    bounce_success_rate,
                    average_bounce_pct,
                    median_bounce_pct,
                    average_days_to_bounce_peak,
                    current_distance_to_support,
                    current_distance_to_support_pct
                )
                VALUES
                (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                """,
                rows,
            )

        self.connection.commit()

        return len(rows)

    def bounce_validation_count(self):

        self.cursor.execute(
            """
            SELECT COUNT(*)
            FROM bounce_validations
            """
        )

        return self.cursor.fetchone()[0]

    def get_bounce_validations(self, ticker):

        self.cursor.execute(
            """
            SELECT
                support_level_id,
                ticker,
                total_touches,
                successful_bounces,
                failed_breakdowns,
                neutral_touches,
                bounce_success_rate,
                average_bounce_pct,
                median_bounce_pct,
                average_days_to_bounce_peak,
                current_distance_to_support,
                current_distance_to_support_pct
            FROM bounce_validations
            WHERE ticker = ?
            ORDER BY bounce_success_rate DESC, average_bounce_pct DESC
            """,
            (ticker,),
        )

        return self.cursor.fetchall()

    # ==========================================================
    # Fundamentals
    # ==========================================================

    def save_fundamentals(self, records):
        """
        Save fundamental metrics, replacing rows by ticker.
        """

        rows = []

        for record in records:
            rows.append(
                (
                    record["ticker"],
                    self._sqlite_float(record.get("market_cap")),
                    self._sqlite_float(record.get("revenue_growth_ttm")),
                    self._sqlite_float(record.get("eps_growth_ttm")),
                    self._sqlite_float(record.get("roe")),
                    self._sqlite_float(record.get("gross_margin")),
                    self._sqlite_float(record.get("free_cash_flow")),
                    self._sqlite_float(record.get("debt_to_equity")),
                    self._sqlite_float(record.get("current_ratio")),
                    self._sqlite_float(record.get("quality_score")),
                )
            )

        if rows:
            self.cursor.executemany(
                """
                INSERT OR REPLACE INTO fundamentals
                (
                    ticker,
                    market_cap,
                    revenue_growth_ttm,
                    eps_growth_ttm,
                    roe,
                    gross_margin,
                    free_cash_flow,
                    debt_to_equity,
                    current_ratio,
                    quality_score
                )
                VALUES
                (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                """,
                rows,
            )

        self.connection.commit()

        return len(rows)

    def get_fundamentals(self, ticker):

        self.cursor.execute(
            """
            SELECT
                ticker,
                market_cap,
                revenue_growth_ttm,
                eps_growth_ttm,
                roe,
                gross_margin,
                free_cash_flow,
                debt_to_equity,
                current_ratio,
                quality_score
            FROM fundamentals
            WHERE ticker = ?
            """,
            (ticker,),
        )

        return self.cursor.fetchone()

    def fundamentals_count(self):

        self.cursor.execute(
            """
            SELECT COUNT(*)
            FROM fundamentals
            """
        )

        return self.cursor.fetchone()[0]

    # ==========================================================
    # Institutional Metrics
    # ==========================================================

    def save_institutional_metrics(self, records):
        """
        Save institutional metrics, replacing rows by ticker.
        """

        rows = []

        for record in records:
            rows.append(
                (
                    record["ticker"],
                    self._sqlite_float(record.get("institutional_ownership_pct")),
                    self._sqlite_float(
                        record.get("institutional_ownership_change_qoq")
                    ),
                    self._sqlite_float(record.get("net_institutional_buying")),
                    self._sqlite_int(record.get("insider_buying_flag")),
                    self._sqlite_int(record.get("insider_selling_flag")),
                    self._sqlite_float(record.get("institutional_score")),
                )
            )

        if rows:
            self.cursor.executemany(
                """
                INSERT OR REPLACE INTO institutional_metrics
                (
                    ticker,
                    institutional_ownership_pct,
                    institutional_ownership_change_qoq,
                    net_institutional_buying,
                    insider_buying_flag,
                    insider_selling_flag,
                    institutional_score
                )
                VALUES
                (
                    ?, ?, ?, ?, ?, ?, ?
                )
                """,
                rows,
            )

        self.connection.commit()

        return len(rows)

    def get_institutional_metrics(self, ticker):

        self.cursor.execute(
            """
            SELECT
                ticker,
                institutional_ownership_pct,
                institutional_ownership_change_qoq,
                net_institutional_buying,
                insider_buying_flag,
                insider_selling_flag,
                institutional_score
            FROM institutional_metrics
            WHERE ticker = ?
            """,
            (ticker,),
        )

        return self.cursor.fetchone()

    def institutional_metrics_count(self):

        self.cursor.execute(
            """
            SELECT COUNT(*)
            FROM institutional_metrics
            """
        )

        return self.cursor.fetchone()[0]

    # ==========================================================
    # Earnings
    # ==========================================================

    def save_earnings(self, records):
        """
        Save earnings metrics, replacing rows by ticker.
        """

        rows = []

        for record in records:
            rows.append(
                (
                    record["ticker"],
                    self._format_date(record.get("next_earnings_date")),
                    self._sqlite_int_or_none(record.get("days_until_earnings")),
                    self._format_date(record.get("previous_earnings_date")),
                    self._sqlite_float(record.get("eps_surprise_pct")),
                    self._sqlite_float(record.get("revenue_surprise_pct")),
                    self._sqlite_float(record.get("earnings_risk_score")),
                )
            )

        if rows:
            self.cursor.executemany(
                """
                INSERT OR REPLACE INTO earnings
                (
                    ticker,
                    next_earnings_date,
                    days_until_earnings,
                    previous_earnings_date,
                    eps_surprise_pct,
                    revenue_surprise_pct,
                    earnings_risk_score
                )
                VALUES
                (
                    ?, ?, ?, ?, ?, ?, ?
                )
                """,
                rows,
            )

        self.connection.commit()

        return len(rows)

    def get_earnings(self, ticker):

        self.cursor.execute(
            """
            SELECT
                ticker,
                next_earnings_date,
                days_until_earnings,
                previous_earnings_date,
                eps_surprise_pct,
                revenue_surprise_pct,
                earnings_risk_score,
                updated_at
            FROM earnings
            WHERE ticker = ?
            """,
            (ticker,),
        )

        return self.cursor.fetchone()

    def earnings_count(self):

        self.cursor.execute(
            """
            SELECT COUNT(*)
            FROM earnings
            """
        )

        return self.cursor.fetchone()[0]

    # ==========================================================
    # Watchlist
    # ==========================================================

    def add_watchlist_item(
        self,
        ticker,
        company_name=None,
        status="Watching",
        notes=None,
        source=None,
    ):
        """
        Add a ticker to the watchlist or return the existing item.
        """

        normalized_ticker = self._normalize_ticker(ticker)

        if normalized_ticker is None:
            return None

        existing = self.get_watchlist_item_by_ticker(normalized_ticker)

        if existing is not None:
            return existing

        self.cursor.execute(
            """
            INSERT INTO watchlist
            (
                ticker,
                company_name,
                status,
                notes,
                source
            )
            VALUES
            (
                ?, ?, ?, ?, ?
            )
            """,
            (
                normalized_ticker,
                company_name,
                status or "Watching",
                notes,
                source,
            ),
        )

        self.connection.commit()

        return self.get_watchlist_item_by_ticker(normalized_ticker)

    def update_watchlist_item(self, item_id, status=None, notes=None):
        """
        Update status and/or notes for an existing watchlist item.
        """

        if item_id is None:
            return None

        fields = []
        values = []

        if status is not None:
            fields.append("status = ?")
            values.append(status)

        if notes is not None:
            fields.append("notes = ?")
            values.append(notes)

        if not fields:
            return self.get_watchlist_item_by_id(item_id)

        fields.append("updated_at = CURRENT_TIMESTAMP")
        values.append(item_id)

        self.cursor.execute(
            f"""
            UPDATE watchlist
            SET {", ".join(fields)}
            WHERE id = ?
            """,
            values,
        )

        self.connection.commit()

        if self.cursor.rowcount == 0:
            return None

        return self.get_watchlist_item_by_id(item_id)

    def remove_watchlist_item(self, item_id):
        """
        Remove a watchlist item by id.
        """

        if item_id is None:
            return False

        self.cursor.execute(
            """
            DELETE FROM watchlist
            WHERE id = ?
            """,
            (item_id,),
        )

        self.connection.commit()

        return self.cursor.rowcount > 0

    def get_watchlist_items(self, status=None):
        """
        Return watchlist items, optionally filtered by status.
        """

        if status is None:
            self.cursor.execute(
                """
                SELECT
                    id,
                    ticker,
                    company_name,
                    status,
                    notes,
                    source,
                    added_at,
                    updated_at
                FROM watchlist
                ORDER BY added_at DESC, ticker
                """
            )
            return self.cursor.fetchall()

        self.cursor.execute(
            """
            SELECT
                id,
                ticker,
                company_name,
                status,
                notes,
                source,
                added_at,
                updated_at
            FROM watchlist
            WHERE status = ?
            ORDER BY added_at DESC, ticker
            """,
            (status,),
        )

        return self.cursor.fetchall()

    def get_watchlist_item_by_ticker(self, ticker):
        """
        Return one watchlist item by normalized ticker.
        """

        normalized_ticker = self._normalize_ticker(ticker)

        if normalized_ticker is None:
            return None

        self.cursor.execute(
            """
            SELECT
                id,
                ticker,
                company_name,
                status,
                notes,
                source,
                added_at,
                updated_at
            FROM watchlist
            WHERE ticker = ?
            """,
            (normalized_ticker,),
        )

        return self.cursor.fetchone()

    def get_watchlist_item_by_id(self, item_id):
        """
        Return one watchlist item by id.
        """

        self.cursor.execute(
            """
            SELECT
                id,
                ticker,
                company_name,
                status,
                notes,
                source,
                added_at,
                updated_at
            FROM watchlist
            WHERE id = ?
            """,
            (item_id,),
        )

        return self.cursor.fetchone()

    def count_watchlist_items(self, status=None):
        """
        Count watchlist items, optionally filtered by status.
        """

        if status is None:
            self.cursor.execute(
                """
                SELECT COUNT(*)
                FROM watchlist
                """
            )
            return self.cursor.fetchone()[0]

        self.cursor.execute(
            """
            SELECT COUNT(*)
            FROM watchlist
            WHERE status = ?
            """,
            (status,),
        )

        return self.cursor.fetchone()[0]

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

    @staticmethod
    def _sqlite_float(value):

        if value is None:
            return None

        if pd.isna(value):
            return None

        return float(value)

    @staticmethod
    def _sqlite_int(value):

        if value is None:
            return 0

        if pd.isna(value):
            return 0

        return int(value)

    @staticmethod
    def _sqlite_int_or_none(value):

        if value is None:
            return None

        if pd.isna(value):
            return None

        return int(value)

    @staticmethod
    def _normalize_ticker(ticker):

        if ticker is None:
            return None

        normalized = str(ticker).strip().upper()

        if not normalized:
            return None

        return normalized

    # ==========================================================
    # Shutdown
    # ==========================================================

    def close(self):

        self.connection.close()

        
