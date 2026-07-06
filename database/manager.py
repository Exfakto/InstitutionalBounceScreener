from pathlib import Path
import json
import sqlite3
from uuid import uuid4
import pandas as pd

from database.institutional_data import InstitutionalData
from database.schema import (
    APP_SETTINGS_TABLE,
    BACKTEST_INDEXES,
    BACKTEST_RUNS_TABLE,
    BACKTEST_TRADE_RESULTS_TABLE,
    BETA_TEST_RUNS_TABLE,
    BOUNCE_VALIDATIONS_TABLE,
    CALIBRATION_RECOMMENDATIONS_TABLE,
    CALIBRATION_RUNS_TABLE,
    EARNINGS_TABLE,
    FUNDAMENTALS_TABLE,
    HISTORICAL_OHLCV_CACHE_INDEXES,
    HISTORICAL_OHLCV_CACHE_TABLE,
    OHLCV_SYNC_METADATA_INDEXES,
    OHLCV_SYNC_METADATA_TABLE,
    INSTITUTIONAL_METRICS_TABLE,
    MARKET_UNIVERSE_INDEXES,
    MARKET_UNIVERSE_TABLE,
    PAPER_TRADES_TABLE,
    PRICE_HISTORY_TABLE,
    RANKED_CANDIDATES_INDEXES,
    RANKED_CANDIDATES_TABLE,
    SCREENING_SIGNAL_HISTORY_INDEXES,
    SCREENING_SIGNAL_HISTORY_TABLE,
    SCREENING_RUNS_INDEXES,
    SCREENING_RUNS_TABLE,
    SIGNAL_QUALITY_RECOMMENDATION_REPORTS_TABLE,
    STRATEGY_VALIDATION_INDEXES,
    STRATEGY_VALIDATION_RUNS_TABLE,
    STRATEGY_VALIDATION_SAMPLES_TABLE,
    SUPPORT_LEVELS_TABLE,
    STOCKS_TABLE,
    TECHNICAL_INDICATORS_TABLE,
    UNIVERSE_SYMBOLS_INDEXES,
    UNIVERSE_SYMBOLS_TABLE,
    VALIDATION_INDEXES,
    VALIDATION_RUNS_TABLE,
    VALIDATION_SIGNAL_RESULTS_TABLE,
    WATCHLIST_TABLE,
    WEIGHT_OPTIMIZATION_RESULTS_TABLE,
)
from services.candidate_ranking_engine import RankedCandidate

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

    def __init__(self, database_path=None):

        self.database_path = Path(database_path) if database_path is not None else DATABASE_PATH
        self.database_path.parent.mkdir(exist_ok=True)

        self.connection = sqlite3.connect(self.database_path)
        self.connection.row_factory = sqlite3.Row

        self.cursor = self.connection.cursor()

        self.initialize()

    # ==========================================================
    # Database Initialization
    # ==========================================================

    def initialize(self):

        self.cursor.execute(STOCKS_TABLE)
        self.cursor.execute(MARKET_UNIVERSE_TABLE)
        for index_statement in MARKET_UNIVERSE_INDEXES:
            self.cursor.execute(index_statement)
        self.cursor.execute(UNIVERSE_SYMBOLS_TABLE)
        for index_statement in UNIVERSE_SYMBOLS_INDEXES:
            self.cursor.execute(index_statement)
        self.cursor.execute(PRICE_HISTORY_TABLE)
        self.cursor.execute(HISTORICAL_OHLCV_CACHE_TABLE)
        for index_statement in HISTORICAL_OHLCV_CACHE_INDEXES:
            self.cursor.execute(index_statement)
        self.cursor.execute(OHLCV_SYNC_METADATA_TABLE)
        for index_statement in OHLCV_SYNC_METADATA_INDEXES:
            self.cursor.execute(index_statement)
        self.cursor.execute(TECHNICAL_INDICATORS_TABLE)
        self.ensure_technical_indicator_columns()
        self.cursor.execute(SUPPORT_LEVELS_TABLE)
        self.cursor.execute(BOUNCE_VALIDATIONS_TABLE)
        self.cursor.execute(FUNDAMENTALS_TABLE)
        self.ensure_fundamentals_profile_columns()
        self.ensure_v7_fundamentals_columns()
        self.cursor.execute(INSTITUTIONAL_METRICS_TABLE)
        self.ensure_institutional_metrics_columns()
        self.cursor.execute(EARNINGS_TABLE)
        self.cursor.execute(WATCHLIST_TABLE)
        self.cursor.execute(PAPER_TRADES_TABLE)
        self.cursor.execute(RANKED_CANDIDATES_TABLE)
        for index_statement in RANKED_CANDIDATES_INDEXES:
            self.cursor.execute(index_statement)
        self.cursor.execute(SCREENING_SIGNAL_HISTORY_TABLE)
        for index_statement in SCREENING_SIGNAL_HISTORY_INDEXES:
            self.cursor.execute(index_statement)
        self.cursor.execute(SCREENING_RUNS_TABLE)
        for index_statement in SCREENING_RUNS_INDEXES:
            self.cursor.execute(index_statement)
        self.cursor.execute(APP_SETTINGS_TABLE)
        self.cursor.execute(BACKTEST_RUNS_TABLE)
        self.cursor.execute(BACKTEST_TRADE_RESULTS_TABLE)
        for index_statement in BACKTEST_INDEXES:
            self.cursor.execute(index_statement)
        self.cursor.execute(STRATEGY_VALIDATION_RUNS_TABLE)
        self.cursor.execute(STRATEGY_VALIDATION_SAMPLES_TABLE)
        for index_statement in STRATEGY_VALIDATION_INDEXES:
            self.cursor.execute(index_statement)
        self.cursor.execute(VALIDATION_RUNS_TABLE)
        self.cursor.execute(VALIDATION_SIGNAL_RESULTS_TABLE)
        self.cursor.execute(WEIGHT_OPTIMIZATION_RESULTS_TABLE)
        self.cursor.execute(SIGNAL_QUALITY_RECOMMENDATION_REPORTS_TABLE)
        self.cursor.execute(BETA_TEST_RUNS_TABLE)
        self.cursor.execute(CALIBRATION_RUNS_TABLE)
        self.cursor.execute(CALIBRATION_RECOMMENDATIONS_TABLE)
        for index_statement in VALIDATION_INDEXES:
            self.cursor.execute(index_statement)

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
            FROM universe_symbols
            WHERE active = 1
            """
        )

        return self.cursor.fetchone()[0]

    # ==========================================================
    # Price History
    # ==========================================================

    def save_price_history(self, ticker, history):

        normalized_ticker = self._normalize_ticker(ticker)
        if normalized_ticker is None:
            return 0

        rows = []
        if hasattr(history, "iterrows"):
            for date, row in history.iterrows():
                rows.append(
                    {
                        "date": str(date.date()) if hasattr(date, "date") else str(date),
                        "open": row.get("Open", row.get("open")),
                        "high": row.get("High", row.get("high")),
                        "low": row.get("Low", row.get("low")),
                        "close": row.get("Close", row.get("close")),
                        "volume": row.get("Volume", row.get("volume")),
                    }
                )
        else:
            rows = list(history or [])

        existing_dates = {
            row.get("date")
            for row in self.fetch_ohlcv(normalized_ticker)
        }
        inserted = sum(1 for row in rows if str(row.get("date")) not in existing_dates)
        self.upsert_ohlcv(normalized_ticker, rows, "legacy_price_history")
        return inserted

    def get_price_history(self, ticker):
        """
        Compatibility wrapper around the canonical historical OHLCV cache.

        Returns
        -------
        pandas.DataFrame
        """

        rows = self.fetch_ohlcv(ticker)
        dataframe = pd.DataFrame(rows)

        if dataframe.empty:
            return pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])

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

    # ==========================================================
    # Historical OHLCV Cache
    # ==========================================================

    def upsert_ohlcv(self, ticker, rows, source=None):
        normalized = self._normalize_ticker(ticker)
        if normalized is None:
            return 0

        payload = []
        for row in rows or []:
            date_value = self.record_value(row, "date")
            if date_value in (None, ""):
                continue
            payload.append(
                (
                    normalized,
                    str(date_value),
                    self._sqlite_float(self.record_value(row, "open")),
                    self._sqlite_float(self.record_value(row, "high")),
                    self._sqlite_float(self.record_value(row, "low")),
                    self._sqlite_float(self.record_value(row, "close")),
                    self._sqlite_int(self.record_value(row, "volume")),
                    source or self.record_value(row, "source"),
                )
            )

        if not payload:
            return 0

        self.cursor.executemany(
            """
            INSERT INTO historical_ohlcv_cache
            (
                ticker,
                date,
                open,
                high,
                low,
                close,
                volume,
                source,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(ticker, date) DO UPDATE SET
                open = excluded.open,
                high = excluded.high,
                low = excluded.low,
                close = excluded.close,
                volume = excluded.volume,
                source = excluded.source,
                updated_at = CURRENT_TIMESTAMP
            """,
            payload,
        )
        self.connection.commit()
        return len(payload)

    def fetch_ohlcv(self, ticker, start_date=None, end_date=None):
        normalized = self._normalize_ticker(ticker)
        if normalized is None:
            return []

        filters = ["ticker = ?"]
        params = [normalized]
        if start_date is not None:
            filters.append("date >= ?")
            params.append(str(start_date))
        if end_date is not None:
            filters.append("date <= ?")
            params.append(str(end_date))

        self.cursor.execute(
            f"""
            SELECT ticker, date, open, high, low, close, volume, source, updated_at
            FROM historical_ohlcv_cache
            WHERE {" AND ".join(filters)}
            ORDER BY date ASC
            """,
            params,
        )
        return [dict(row) for row in self.cursor.fetchall()]

    def clear_ohlcv(self, ticker):
        normalized = self._normalize_ticker(ticker)
        if normalized is None:
            return 0

        self.cursor.execute(
            """
            DELETE FROM historical_ohlcv_cache
            WHERE ticker = ?
            """,
            (normalized,),
        )
        deleted = self.cursor.rowcount
        self.connection.commit()
        return deleted

    def clear_all_ohlcv(self):
        self.cursor.execute("DELETE FROM historical_ohlcv_cache")
        deleted = self.cursor.rowcount
        self.connection.commit()
        return deleted

    def fetch_ohlcv_cache_coverage(self, ticker=None):
        normalized = self._normalize_ticker(ticker)
        filters = []
        params = []
        if normalized is not None:
            filters.append("ticker = ?")
            params.append(normalized)
        where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
        self.cursor.execute(
            f"""
            SELECT
                ticker,
                COUNT(*) AS row_count,
                MIN(date) AS first_date,
                MAX(date) AS last_date,
                MAX(updated_at) AS last_updated,
                GROUP_CONCAT(DISTINCT source) AS sources
            FROM historical_ohlcv_cache
            {where_clause}
            GROUP BY ticker
            ORDER BY ticker
            """,
            params,
        )
        return [dict(row) for row in self.cursor.fetchall()]

    def upsert_ohlcv_sync_metadata(
        self,
        ticker,
        last_attempted_at=None,
        last_success_at=None,
        last_error=None,
        empty_response_count=None,
        status=None,
    ):
        normalized = self._normalize_ticker(ticker)
        if normalized is None:
            return 0

        current = self.get_ohlcv_sync_metadata(normalized)
        values = {
            "last_attempted_at": (
                last_attempted_at
                if last_attempted_at is not None
                else (current or {}).get("last_attempted_at")
            ),
            "last_success_at": (
                last_success_at
                if last_success_at is not None
                else (current or {}).get("last_success_at")
            ),
            "last_error": (
                last_error
                if last_error is not None
                else (current or {}).get("last_error")
            ),
            "empty_response_count": (
                int(empty_response_count)
                if empty_response_count is not None
                else int((current or {}).get("empty_response_count") or 0)
            ),
            "status": status or (current or {}).get("status") or "stale",
        }
        self.cursor.execute(
            """
            INSERT INTO ohlcv_sync_metadata
            (
                ticker,
                last_attempted_at,
                last_success_at,
                last_error,
                empty_response_count,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(ticker) DO UPDATE SET
                last_attempted_at = excluded.last_attempted_at,
                last_success_at = excluded.last_success_at,
                last_error = excluded.last_error,
                empty_response_count = excluded.empty_response_count,
                status = excluded.status
            """,
            (
                normalized,
                values["last_attempted_at"],
                values["last_success_at"],
                values["last_error"],
                values["empty_response_count"],
                values["status"],
            ),
        )
        self.connection.commit()
        return 1

    def get_ohlcv_sync_metadata(self, ticker):
        normalized = self._normalize_ticker(ticker)
        if normalized is None:
            return None
        self.cursor.execute(
            """
            SELECT
                ticker,
                last_attempted_at,
                last_success_at,
                last_error,
                empty_response_count,
                status
            FROM ohlcv_sync_metadata
            WHERE ticker = ?
            """,
            (normalized,),
        )
        row = self.cursor.fetchone()
        return dict(row) if row is not None else None

    def fetch_ohlcv_sync_metadata(self, tickers=None):
        normalized = [
            ticker
            for ticker in (self._normalize_ticker(ticker) for ticker in (tickers or []))
            if ticker is not None
        ]
        if normalized:
            placeholders = ", ".join("?" for _ in normalized)
            where_clause = f"WHERE ticker IN ({placeholders})"
            params = normalized
        else:
            where_clause = ""
            params = []
        self.cursor.execute(
            f"""
            SELECT
                ticker,
                last_attempted_at,
                last_success_at,
                last_error,
                empty_response_count,
                status
            FROM ohlcv_sync_metadata
            {where_clause}
            ORDER BY ticker
            """,
            params,
        )
        return [dict(row) for row in self.cursor.fetchall()]

    def get_total_rows(self):

        return sum(
            int(row.get("row_count") or 0)
            for row in self.fetch_ohlcv_cache_coverage()
        )

    # ==========================================================
    # Technical Indicators
    # ==========================================================

    V22_TECHNICAL_INDICATOR_COLUMNS = {
        "ema20": "REAL",
        "ema50": "REAL",
        "ema200": "REAL",
        "vwap": "REAL",
        "average_volume_20": "REAL",
        "distance_from_ema20": "REAL",
        "distance_from_ema50": "REAL",
        "distance_from_ema200": "REAL",
        "relative_strength_spy": "REAL",
        "trend": "TEXT",
        "market_structure": "TEXT",
    }

    def ensure_technical_indicator_columns(self):
        """
        Add v2.2 technical indicator columns to existing databases.
        """

        self.cursor.execute("PRAGMA table_info(technical_indicators)")
        existing = {row["name"] if hasattr(row, "keys") else row[1] for row in self.cursor.fetchall()}

        for column, column_type in self.V22_TECHNICAL_INDICATOR_COLUMNS.items():
            if column not in existing:
                self.cursor.execute(
                    f"ALTER TABLE technical_indicators ADD COLUMN {column} {column_type}"
                )

        self.connection.commit()

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

    def save_technical_indicators(self, indicator, commit=True, ensure_schema=True):
        """
        Persist one v2.2 technical indicator result.
        """

        if ensure_schema:
            self.ensure_technical_indicator_columns()

        ticker = self.record_value(indicator, "ticker")
        date_value = self.record_value(indicator, "date")
        close = self._sqlite_float(self.record_value(indicator, "close"))
        ema20 = self._sqlite_float(self.record_value(indicator, "ema20"))
        ema50 = self._sqlite_float(self.record_value(indicator, "ema50"))
        ema200 = self._sqlite_float(self.record_value(indicator, "ema200"))
        rsi14 = self._sqlite_float(self.record_value(indicator, "rsi14"))
        macd = self._sqlite_float(self.record_value(indicator, "macd"))

        trend = self.record_value(indicator, "trend") or self._classify_trend(
            close,
            ema20,
            ema50,
            ema200,
            rsi14,
            macd,
        )
        market_structure = (
            self.record_value(indicator, "market_structure")
            or self._classify_market_structure(close, ema20, ema50, ema200)
        )

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
                ema20,
                ema50,
                ema200,
                rsi14,
                atr14,
                avg_volume20,
                average_volume_20,
                relative_volume,
                high52,
                low52,
                macd,
                macd_signal,
                macd_histogram,
                vwap,
                distance_from_ema20,
                distance_from_ema50,
                distance_from_ema200,
                relative_strength_spy,
                trend,
                market_structure
            )
            VALUES
            (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            """,
            (
                ticker,
                self._format_date(date_value),
                self._sqlite_float(self.record_value(indicator, "sma20")),
                self._sqlite_float(self.record_value(indicator, "sma50")),
                self._sqlite_float(self.record_value(indicator, "sma200")),
                self._sqlite_float(self.record_value(indicator, "ema21")),
                ema20,
                ema50,
                ema200,
                rsi14,
                self._sqlite_float(self.record_value(indicator, "atr14")),
                self._sqlite_float(
                    self.first_existing(
                        self.record_value(indicator, "avg_volume20"),
                        self.record_value(indicator, "average_volume_20"),
                    )
                ),
                self._sqlite_float(
                    self.first_existing(
                        self.record_value(indicator, "average_volume_20"),
                        self.record_value(indicator, "avg_volume20"),
                    )
                ),
                self._sqlite_float(self.record_value(indicator, "relative_volume")),
                self._sqlite_float(self.record_value(indicator, "high52")),
                self._sqlite_float(self.record_value(indicator, "low52")),
                macd,
                self._sqlite_float(self.record_value(indicator, "macd_signal")),
                self._sqlite_float(self.record_value(indicator, "macd_histogram")),
                self._sqlite_float(self.record_value(indicator, "vwap")),
                self._sqlite_float(self.record_value(indicator, "distance_from_ema20")),
                self._sqlite_float(self.record_value(indicator, "distance_from_ema50")),
                self._sqlite_float(self.record_value(indicator, "distance_from_ema200")),
                self._sqlite_float(self.record_value(indicator, "relative_strength_spy")),
                trend,
                market_structure,
            ),
        )
        if commit:
            self.connection.commit()

    @staticmethod
    def _classify_trend(close, ema20, ema50, ema200, rsi14, macd):
        votes = []
        if close is not None and ema20 is not None:
            votes.append(1 if close > ema20 else -1 if close < ema20 else 0)
        if close is not None and ema50 is not None:
            votes.append(1 if close > ema50 else -1 if close < ema50 else 0)
        if ema50 is not None and ema200 is not None:
            votes.append(1 if ema50 > ema200 else -1 if ema50 < ema200 else 0)
        if rsi14 is not None:
            votes.append(1 if rsi14 >= 50 else -1)
        if macd is not None:
            votes.append(1 if macd > 0 else -1 if macd < 0 else 0)

        bullish = sum(1 for vote in votes if vote > 0)
        bearish = sum(1 for vote in votes if vote < 0)
        if bullish > bearish:
            return "Bullish"
        if bearish > bullish:
            return "Bearish"
        return "Neutral"

    @staticmethod
    def _classify_market_structure(close, ema20, ema50, ema200):
        if None not in (close, ema20, ema50, ema200):
            if close > ema20 > ema50 > ema200:
                return "Strong Bullish Structure"
            if close < ema20 < ema50 < ema200:
                return "Strong Bearish Structure"
        return "Mixed Structure"

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

        self.ensure_technical_indicator_columns()

        self.cursor.execute(
            """
            SELECT
                ticker,
                date,
                sma20,
                sma50,
                sma200,
                ema21,
                ema20,
                ema50,
                ema200,
                rsi14,
                atr14,
                avg_volume20,
                average_volume_20,
                relative_volume,
                high52,
                low52,
                macd,
                macd_signal,
                macd_histogram,
                vwap,
                distance_from_ema20,
                distance_from_ema50,
                distance_from_ema200,
                relative_strength_spy,
                trend,
                market_structure
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
                    record.get("company_name"),
                    record.get("sector"),
                    record.get("industry"),
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
                    company_name,
                    sector,
                    industry,
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
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
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
                company_name,
                sector,
                industry,
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

    def ensure_fundamentals_profile_columns(self):
        """
        Add v3.2 profile columns to existing local fundamentals tables.
        """

        self.cursor.execute("PRAGMA table_info(fundamentals)")
        existing_columns = {row[1] for row in self.cursor.fetchall()}

        for column in ("company_name", "sector", "industry"):
            if column in existing_columns:
                continue

            self.cursor.execute(
                f"ALTER TABLE fundamentals ADD COLUMN {column} TEXT"
            )

    def ensure_v7_fundamentals_columns(self):

        self.cursor.execute("PRAGMA table_info(fundamentals)")
        existing_columns = {row[1] for row in self.cursor.fetchall()}
        migrations = {
            "bankruptcy_risk": "ALTER TABLE fundamentals ADD COLUMN bankruptcy_risk REAL",
            "going_concern_warning": "ALTER TABLE fundamentals ADD COLUMN going_concern_warning INTEGER DEFAULT 0",
            "last_earnings_date": "ALTER TABLE fundamentals ADD COLUMN last_earnings_date TEXT",
            "source": "ALTER TABLE fundamentals ADD COLUMN source TEXT",
        }
        for column, statement in migrations.items():
            if column not in existing_columns:
                self.cursor.execute(statement)

    def fundamentals_count(self):

        self.cursor.execute(
            """
            SELECT COUNT(*)
            FROM fundamentals
            """
        )

        return self.cursor.fetchone()[0]

    def upsert_fundamental_data(self, records):

        rows = []
        for record in records or []:
            ticker = self._normalize_ticker(self.record_value(record, "ticker"))
            if ticker is None:
                continue
            rows.append(
                (
                    ticker,
                    self.record_value(record, "company_name"),
                    self.record_value(record, "sector"),
                    self.record_value(record, "industry"),
                    self._sqlite_float(self.record_value(record, "market_cap")),
                    self._sqlite_float(self.record_value(record, "revenue_growth_ttm")),
                    self._sqlite_float(self.record_value(record, "eps_growth_ttm")),
                    self._sqlite_float(self.record_value(record, "roe")),
                    self._sqlite_float(self.record_value(record, "gross_margin")),
                    self._sqlite_float(self.record_value(record, "free_cash_flow")),
                    self._sqlite_float(self.record_value(record, "debt_to_equity")),
                    self._sqlite_float(self.record_value(record, "current_ratio")),
                    self._sqlite_float(self.record_value(record, "quality_score")),
                    self._sqlite_float(self.record_value(record, "bankruptcy_risk")),
                    self._sqlite_int(self.record_value(record, "going_concern_warning")),
                    self._format_date(self.record_value(record, "last_earnings_date")),
                    self.record_value(record, "source"),
                )
            )
        if not rows:
            return 0
        self.cursor.executemany(
            """
            INSERT INTO fundamentals
            (
                ticker, company_name, sector, industry, market_cap,
                revenue_growth_ttm, eps_growth_ttm, roe, gross_margin,
                free_cash_flow, debt_to_equity, current_ratio, quality_score,
                bankruptcy_risk, going_concern_warning, last_earnings_date,
                source, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(ticker) DO UPDATE SET
                company_name = excluded.company_name,
                sector = excluded.sector,
                industry = excluded.industry,
                market_cap = excluded.market_cap,
                revenue_growth_ttm = excluded.revenue_growth_ttm,
                eps_growth_ttm = excluded.eps_growth_ttm,
                roe = excluded.roe,
                gross_margin = excluded.gross_margin,
                free_cash_flow = excluded.free_cash_flow,
                debt_to_equity = excluded.debt_to_equity,
                current_ratio = excluded.current_ratio,
                quality_score = excluded.quality_score,
                bankruptcy_risk = excluded.bankruptcy_risk,
                going_concern_warning = excluded.going_concern_warning,
                last_earnings_date = excluded.last_earnings_date,
                source = excluded.source,
                updated_at = CURRENT_TIMESTAMP
            """,
            rows,
        )
        self.connection.commit()
        return len(rows)

    def fetch_fundamental_data(self, ticker):

        normalized = self._normalize_ticker(ticker)
        if normalized is None:
            return None
        self.cursor.execute(
            """
            SELECT *
            FROM fundamentals
            WHERE ticker = ?
            """,
            (normalized,),
        )
        row = self.cursor.fetchone()
        return None if row is None else dict(row)

    def fetch_missing_fundamental_tickers(self, tickers):

        normalized = [
            ticker
            for ticker in (self._normalize_ticker(value) for value in (tickers or []))
            if ticker is not None
        ]
        if not normalized:
            return []
        placeholders = ", ".join("?" for _ in normalized)
        self.cursor.execute(
            f"""
            SELECT ticker
            FROM fundamentals
            WHERE ticker IN ({placeholders})
            """,
            normalized,
        )
        present = {row["ticker"] for row in self.cursor.fetchall()}
        return [ticker for ticker in normalized if ticker not in present]

    def upsert_market_universe_records(self, records):

        rows = []

        for record in records or []:
            normalized = self.normalize_market_universe_record(record)
            if normalized is not None:
                rows.append(normalized)

        if not rows:
            return 0

        self.cursor.executemany(
            """
            INSERT INTO market_universe
            (
                ticker,
                company_name,
                exchange,
                security_type,
                sector,
                industry,
                market_cap,
                price,
                average_volume,
                average_dollar_volume,
                is_active,
                last_updated
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, COALESCE(?, CURRENT_TIMESTAMP))
            ON CONFLICT(ticker) DO UPDATE SET
                company_name = excluded.company_name,
                exchange = excluded.exchange,
                security_type = excluded.security_type,
                sector = excluded.sector,
                industry = excluded.industry,
                market_cap = excluded.market_cap,
                price = excluded.price,
                average_volume = excluded.average_volume,
                average_dollar_volume = excluded.average_dollar_volume,
                is_active = excluded.is_active,
                last_updated = excluded.last_updated
            """,
            rows,
        )

        self.connection.commit()
        return len(rows)

    def get_active_market_universe_records(self):

        self.cursor.execute(
            """
            SELECT *
            FROM market_universe
            WHERE is_active = 1
            ORDER BY ticker
            """
        )

        return [dict(row) for row in self.cursor.fetchall()]

    def get_market_universe_by_exchange(self, exchange, active_only=True):

        if exchange in (None, ""):
            return []

        query = """
            SELECT *
            FROM market_universe
            WHERE UPPER(exchange) = ?
        """
        params = [str(exchange).strip().upper()]

        if active_only:
            query += " AND is_active = 1"

        query += " ORDER BY ticker"

        self.cursor.execute(query, params)
        return [dict(row) for row in self.cursor.fetchall()]

    def deactivate_stale_market_universe_records(self, active_tickers):

        tickers = [
            str(ticker).strip().upper()
            for ticker in (active_tickers or [])
            if str(ticker or "").strip()
        ]

        if not tickers:
            self.cursor.execute("UPDATE market_universe SET is_active = 0")
            self.connection.commit()
            return self.cursor.rowcount

        placeholders = ", ".join("?" for _ in tickers)
        self.cursor.execute(
            f"""
            UPDATE market_universe
            SET is_active = 0
            WHERE ticker NOT IN ({placeholders})
            """,
            tickers,
        )
        self.connection.commit()
        return self.cursor.rowcount

    @classmethod
    def normalize_market_universe_record(cls, record):

        if record is None:
            return None

        ticker = cls.record_value(record, "ticker")
        ticker = str(ticker or "").strip().upper()

        if not ticker:
            return None

        average_volume = cls._sqlite_float(cls.record_value(record, "average_volume"))
        price = cls._sqlite_float(cls.record_value(record, "price"))
        average_dollar_volume = cls._sqlite_float(
            cls.record_value(record, "average_dollar_volume")
        )

        if average_dollar_volume is None and average_volume is not None and price is not None:
            average_dollar_volume = average_volume * price

        return (
            ticker,
            cls.record_value(record, "company_name") or cls.record_value(record, "company") or "",
            cls.record_value(record, "exchange") or "",
            cls.record_value(record, "security_type") or "",
            cls.record_value(record, "sector") or "",
            cls.record_value(record, "industry") or "",
            cls._sqlite_float(cls.record_value(record, "market_cap")),
            price,
            average_volume,
            average_dollar_volume,
            1 if cls.record_value(record, "is_active") not in (False, 0, "0") else 0,
            cls.record_value(record, "last_updated"),
        )

    # ==========================================================
    # Universe Symbols Master
    # ==========================================================

    def upsert_universe_symbols(self, records):

        rows = []
        for record in records or []:
            normalized = self.normalize_universe_symbol(record)
            if normalized is not None:
                rows.append(normalized)

        if not rows:
            return 0

        self.cursor.executemany(
            """
            INSERT INTO universe_symbols
            (
                ticker,
                company_name,
                exchange,
                security_type,
                sector,
                industry,
                market_cap,
                active,
                source,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(ticker) DO UPDATE SET
                company_name = excluded.company_name,
                exchange = excluded.exchange,
                security_type = excluded.security_type,
                sector = excluded.sector,
                industry = excluded.industry,
                market_cap = excluded.market_cap,
                active = excluded.active,
                source = excluded.source,
                updated_at = CURRENT_TIMESTAMP
            """,
            rows,
        )
        self.connection.commit()
        return len(rows)

    def fetch_universe_symbols(
        self,
        active_only=True,
        exchange=None,
        security_type=None,
        min_market_cap=None,
    ):

        filters = []
        params = []
        if active_only:
            filters.append("active = 1")
        if exchange not in (None, ""):
            filters.append("UPPER(exchange) = ?")
            params.append(str(exchange).strip().upper())
        if security_type not in (None, ""):
            filters.append("UPPER(security_type) = ?")
            params.append(str(security_type).strip().upper())
        if min_market_cap is not None:
            filters.append("market_cap >= ?")
            params.append(self._sqlite_float(min_market_cap))

        where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
        self.cursor.execute(
            f"""
            SELECT ticker, company_name, exchange, security_type, sector, industry,
                   market_cap, active, source, updated_at
            FROM universe_symbols
            {where_clause}
            ORDER BY ticker
            """,
            params,
        )
        return [dict(row) for row in self.cursor.fetchall()]

    def fetch_eligible_universe_tickers(self):

        return [
            row["ticker"]
            for row in self.fetch_universe_symbols(
                active_only=True,
                security_type="COMMON STOCK",
            )
        ]

    def deactivate_stale_universe_symbols(self, active_tickers):

        tickers = [
            str(ticker).strip().upper()
            for ticker in (active_tickers or [])
            if str(ticker or "").strip()
        ]

        if not tickers:
            self.cursor.execute("UPDATE universe_symbols SET active = 0")
            self.connection.commit()
            return self.cursor.rowcount

        placeholders = ", ".join("?" for _ in tickers)
        self.cursor.execute(
            f"""
            UPDATE universe_symbols
            SET active = 0
            WHERE ticker NOT IN ({placeholders})
            """,
            tickers,
        )
        self.connection.commit()
        return self.cursor.rowcount

    @classmethod
    def normalize_universe_symbol(cls, record):

        if record is None:
            return None

        ticker = (
            cls.record_value(record, "ticker")
            or cls.record_value(record, "symbol")
        )
        ticker = str(ticker or "").strip().upper()
        exchange = str(cls.record_value(record, "exchange") or "").strip().upper()

        if not ticker or not exchange:
            return None

        company_name = (
            cls.record_value(record, "company_name")
            or cls.record_value(record, "company")
            or cls.record_value(record, "name")
            or ""
        )
        security_type = (
            cls.record_value(record, "security_type")
            or cls.record_value(record, "type")
            or "Common Stock"
        )

        return (
            ticker,
            company_name,
            exchange,
            str(security_type or "").strip(),
            cls.record_value(record, "sector") or "",
            cls.record_value(record, "industry") or "",
            cls._sqlite_float(cls.record_value(record, "market_cap")),
            1 if cls.record_value(record, "active") not in (False, 0, "0") else 0,
            cls.record_value(record, "source"),
        )

    @staticmethod
    def record_value(record, key):

        if isinstance(record, dict):
            return record.get(key)

        return getattr(record, key, None)

    @staticmethod
    def first_existing(*values):

        for value in values:
            if value not in (None, ""):
                return value
        return None

    @classmethod
    def _signal_value(cls, candidate, source, source_metrics, *keys):
        for key in keys:
            value = cls.first_existing(
                cls.record_value(candidate, key),
                cls.record_value(source, key),
                cls.record_value(source_metrics, key),
            )
            if value not in (None, ""):
                return value
        return None

    @staticmethod
    def _entry_zone_text(value):
        if value in (None, ""):
            return None
        if isinstance(value, (list, tuple)):
            return " - ".join(str(item) for item in value if item not in (None, ""))
        return str(value)

    # ==========================================================
    # Institutional Metrics
    # ==========================================================

    def ensure_institutional_metrics_columns(self):
        """
        Add institutional data storage columns to existing local databases.
        """

        self.cursor.execute("PRAGMA table_info(institutional_metrics)")
        existing_columns = {row[1] for row in self.cursor.fetchall()}

        migrations = {
            "source": "ALTER TABLE institutional_metrics ADD COLUMN source TEXT",
            "as_of_date": "ALTER TABLE institutional_metrics ADD COLUMN as_of_date TEXT",
        }

        for column, statement in migrations.items():
            if column not in existing_columns:
                self.cursor.execute(statement)

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
                    record.get("source"),
                    self._format_date(record.get("as_of_date")),
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
                    institutional_score,
                    source,
                    as_of_date
                )
                VALUES
                (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                """,
                rows,
            )

        self.connection.commit()

        return len(rows)

    def upsert_institutional_data(self, record):
        """
        Insert or update institutional data by ticker.
        """

        data = self._institutional_record_to_dict(record)
        ticker = self._normalize_ticker(data.get("ticker"))
        if ticker is None:
            return None

        self.cursor.execute(
            """
            INSERT INTO institutional_metrics
            (
                ticker,
                institutional_ownership_pct,
                institutional_ownership_change_qoq,
                net_institutional_buying,
                insider_buying_flag,
                insider_selling_flag,
                source,
                as_of_date,
                updated_at
            )
            VALUES
            (
                ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP
            )
            ON CONFLICT(ticker) DO UPDATE SET
                institutional_ownership_pct = excluded.institutional_ownership_pct,
                institutional_ownership_change_qoq = excluded.institutional_ownership_change_qoq,
                net_institutional_buying = excluded.net_institutional_buying,
                insider_buying_flag = excluded.insider_buying_flag,
                insider_selling_flag = excluded.insider_selling_flag,
                source = excluded.source,
                as_of_date = excluded.as_of_date,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                ticker,
                self._sqlite_float(data.get("institutional_ownership_pct")),
                self._sqlite_float(data.get("institutional_ownership_change_qoq")),
                self._sqlite_float(data.get("net_institutional_buying")),
                self._sqlite_int(data.get("insider_buying_flag")),
                self._sqlite_int(data.get("insider_selling_flag")),
                data.get("source"),
                self._format_date(data.get("as_of_date")),
            ),
        )
        self.connection.commit()
        return self.get_institutional_data(ticker)

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
                institutional_score,
                source,
                as_of_date,
                updated_at
            FROM institutional_metrics
            WHERE ticker = ?
            """,
            (ticker,),
        )

        return self.cursor.fetchone()

    def get_institutional_data(self, ticker):
        normalized_ticker = self._normalize_ticker(ticker)
        if normalized_ticker is None:
            return None

        row = self.get_institutional_metrics(normalized_ticker)
        return self._row_to_institutional_data(row)

    def get_institutional_data_for_tickers(self, tickers):
        normalized = [
            ticker
            for ticker in (self._normalize_ticker(value) for value in (tickers or []))
            if ticker is not None
        ]
        if not normalized:
            return {}

        placeholders = ",".join("?" for _ in normalized)
        self.cursor.execute(
            f"""
            SELECT
                ticker,
                institutional_ownership_pct,
                institutional_ownership_change_qoq,
                net_institutional_buying,
                insider_buying_flag,
                insider_selling_flag,
                source,
                as_of_date,
                updated_at
            FROM institutional_metrics
            WHERE ticker IN ({placeholders})
            """,
            normalized,
        )

        return {
            row["ticker"]: self._row_to_institutional_data(row)
            for row in self.cursor.fetchall()
        }

    def institutional_metrics_count(self):

        self.cursor.execute(
            """
            SELECT COUNT(*)
            FROM institutional_metrics
            """
        )

        return self.cursor.fetchone()[0]

    # ==========================================================
    # Ranked Candidates
    # ==========================================================

    def save_ranked_candidates(self, run_id, candidates):
        """
        Replace and persist ranked candidate rows for a run.
        """

        if run_id in (None, ""):
            return 0

        self.clear_ranked_candidates(run_id)
        rows = []

        for candidate in candidates or []:
            ticker = self._normalize_ticker(self.record_value(candidate, "ticker"))
            if ticker is None:
                continue

            rows.append(
                (
                    ticker,
                    self._sqlite_int(self.record_value(candidate, "rank")) or 0,
                    self._sqlite_float(self.record_value(candidate, "final_score")) or 0.0,
                    self.record_value(candidate, "grade"),
                    self.record_value(candidate, "confidence_level"),
                    self.record_value(candidate, "setup_label"),
                    self._json_text(self.record_value(candidate, "explanation")),
                    self._json_text(self.record_value(candidate, "warnings")),
                    self._json_text(self.record_value(candidate, "rejection_reasons")),
                    str(run_id),
                )
            )

        if rows:
            self.cursor.executemany(
                """
                INSERT INTO ranked_candidates
                (
                    ticker,
                    rank,
                    final_score,
                    grade,
                    confidence_level,
                    setup_label,
                    explanation_json,
                    warnings_json,
                    rejection_reasons_json,
                    run_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
            self.connection.commit()

        return len(rows)

    def fetch_ranked_candidates(self, run_id, limit=None, offset=0):
        if run_id in (None, ""):
            return []

        paging_sql, paging_values = self._limit_offset_clause(limit, offset)
        self.cursor.execute(
            f"""
            SELECT
                ticker,
                rank,
                final_score,
                grade,
                confidence_level,
                setup_label,
                explanation_json,
                warnings_json,
                rejection_reasons_json,
                run_id,
                created_at
            FROM ranked_candidates
            WHERE run_id = ?
            ORDER BY
                CASE WHEN rank <= 0 THEN 1 ELSE 0 END,
                rank ASC,
                final_score DESC,
                ticker ASC
            {paging_sql}
            """,
            (str(run_id), *paging_values),
        )

        return [self._row_to_ranked_candidate(row) for row in self.cursor.fetchall()]

    def fetch_latest_ranked_candidates(self, limit=None, offset=0):
        self.cursor.execute(
            """
            SELECT run_id
            FROM ranked_candidates
            ORDER BY created_at DESC, id DESC
            LIMIT 1
            """
        )
        row = self.cursor.fetchone()
        if row is None:
            return []
        return self.fetch_ranked_candidates(row["run_id"], limit=limit, offset=offset)

    def count_ranked_candidates(self, run_id):
        if run_id in (None, ""):
            return 0

        self.cursor.execute(
            """
            SELECT COUNT(*)
            FROM ranked_candidates
            WHERE run_id = ?
            """,
            (str(run_id),),
        )
        return self.cursor.fetchone()[0]

    def count_latest_ranked_candidates(self):
        self.cursor.execute(
            """
            SELECT run_id
            FROM ranked_candidates
            ORDER BY created_at DESC, id DESC
            LIMIT 1
            """
        )
        row = self.cursor.fetchone()
        return 0 if row is None else self.count_ranked_candidates(row["run_id"])

    def clear_ranked_candidates(self, run_id):
        if run_id in (None, ""):
            return 0

        self.cursor.execute(
            """
            DELETE FROM ranked_candidates
            WHERE run_id = ?
            """,
            (str(run_id),),
        )
        deleted = self.cursor.rowcount
        self.connection.commit()
        return deleted

    # ==========================================================
    # Screening Signal History
    # ==========================================================

    def save_screening_run(self, run_id, candidates, created_at=None, notes=None):
        """
        Append generated screening candidates to permanent validation history.
        """

        if run_id in (None, ""):
            return 0

        rows = []
        for candidate in candidates or []:
            row = self._screening_signal_row(run_id, candidate, created_at, notes)
            if row is not None:
                rows.append(row)

        if rows:
            self.cursor.executemany(
                """
                INSERT INTO screening_signal_history
                (
                    signal_id,
                    run_id,
                    created_at,
                    ticker,
                    company_name,
                    sector,
                    industry,
                    overall_score,
                    technical_score,
                    bounce_score,
                    fundamental_score,
                    risk_score,
                    current_price,
                    entry_zone,
                    support,
                    stop_loss,
                    target_1,
                    target_2,
                    target_3,
                    signal_status,
                    notes,
                    price_after_5d,
                    price_after_10d,
                    price_after_20d,
                    price_after_60d,
                    max_drawdown,
                    max_runup,
                    outcome
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, NULL, NULL, NULL, NULL, NULL)
                """,
                rows,
            )
            self.connection.commit()

        return len(rows)

    def fetch_screening_history(self, run_id=None, ticker=None, limit=100, offset=0):
        filters = []
        values = []
        if run_id not in (None, ""):
            filters.append("run_id = ?")
            values.append(str(run_id))
        normalized_ticker = self._normalize_ticker(ticker)
        if normalized_ticker is not None:
            filters.append("ticker = ?")
            values.append(normalized_ticker)

        where_clause = ""
        if filters:
            where_clause = "WHERE " + " AND ".join(filters)
        paging_sql, paging_values = self._limit_offset_clause(limit, offset)
        values.extend(paging_values)

        self.cursor.execute(
            f"""
            SELECT *
            FROM screening_signal_history
            {where_clause}
            ORDER BY created_at DESC, rowid DESC
            {paging_sql}
            """,
            tuple(values),
        )
        return [self._row_to_screening_signal(row) for row in self.cursor.fetchall()]

    def fetch_signal(self, signal_id):
        if signal_id in (None, ""):
            return None

        self.cursor.execute(
            """
            SELECT *
            FROM screening_signal_history
            WHERE signal_id = ?
            """,
            (str(signal_id),),
        )
        return self._row_to_screening_signal(self.cursor.fetchone())

    def fetch_latest_signals(self, limit=20, offset=0):
        paging_sql, paging_values = self._limit_offset_clause(limit, offset)
        self.cursor.execute(
            f"""
            SELECT *
            FROM screening_signal_history
            ORDER BY created_at DESC, rowid DESC
            {paging_sql}
            """,
            tuple(paging_values),
        )
        return [self._row_to_screening_signal(row) for row in self.cursor.fetchall()]

    def _screening_signal_row(self, run_id, candidate, created_at, notes):
        ticker = self._normalize_ticker(self.record_value(candidate, "ticker"))
        if ticker is None:
            return None

        category_scores = self.record_value(candidate, "category_scores") or {}
        source = self.record_value(candidate, "source")
        source_metrics = self.record_value(source, "metrics") or {}
        trade_thesis = self.record_value(candidate, "trade_thesis") or self.record_value(source, "trade_thesis")

        return (
            str(uuid4()),
            str(run_id),
            created_at,
            ticker,
            self._signal_value(candidate, source, source_metrics, "company_name", "company", "name"),
            self._signal_value(candidate, source, source_metrics, "sector"),
            self._signal_value(candidate, source, source_metrics, "industry"),
            self._sqlite_float(
                self.first_existing(
                    self.record_value(candidate, "final_score"),
                    self.record_value(candidate, "overall_score"),
                    self.record_value(candidate, "primary_score_value"),
                )
            ),
            self._sqlite_float(
                self.first_existing(
                    self.record_value(category_scores, "technical_score"),
                    self.record_value(source, "technical_score"),
                    self.record_value(source_metrics, "technical_score"),
                )
            ),
            self._sqlite_float(
                self.first_existing(
                    self.record_value(category_scores, "bounce_score"),
                    self.record_value(category_scores, "bounce_history_score"),
                    self.record_value(source, "bounce_score"),
                    self.record_value(source_metrics, "bounce_score"),
                )
            ),
            self._sqlite_float(
                self.first_existing(
                    self.record_value(category_scores, "fundamental_score"),
                    self.record_value(category_scores, "fundamental_quality_score"),
                    self.record_value(source, "fundamental_score"),
                    self.record_value(source_metrics, "fundamental_score"),
                )
            ),
            self._sqlite_float(
                self.first_existing(
                    self.record_value(category_scores, "risk_score"),
                    self.record_value(category_scores, "risk_penalty_score"),
                    self.record_value(source, "risk_score"),
                    self.record_value(source_metrics, "risk_score"),
                )
            ),
            self._sqlite_float(
                self._signal_value(
                    candidate,
                    source,
                    source_metrics,
                    "current_price",
                    "price",
                    "close",
                    "latest_close",
                )
            ),
            self._entry_zone_text(
                self._signal_value(candidate, source, source_metrics, "entry_zone", "ideal_buy_zone")
            ),
            self._sqlite_float(
                self._signal_value(
                    candidate,
                    source,
                    source_metrics,
                    "support",
                    "support_price",
                    "primary_support",
                    "support_level",
                )
            ),
            self._sqlite_float(
                self.first_existing(
                    self._signal_value(candidate, source, source_metrics, "stop_loss", "technical_stop"),
                    self.record_value(trade_thesis, "stop_loss"),
                )
            ),
            self._sqlite_float(
                self.first_existing(
                    self._signal_value(candidate, source, source_metrics, "target_1", "target1"),
                    self.record_value(trade_thesis, "target_1"),
                )
            ),
            self._sqlite_float(
                self.first_existing(
                    self._signal_value(candidate, source, source_metrics, "target_2", "target2"),
                    self.record_value(trade_thesis, "target_2"),
                )
            ),
            self._sqlite_float(
                self.first_existing(
                    self._signal_value(candidate, source, source_metrics, "target_3", "target3"),
                    self.record_value(trade_thesis, "target_3"),
                )
            ),
            self.record_value(candidate, "signal_status") or "OPEN",
            notes or self.record_value(candidate, "notes"),
        )

    # ==========================================================
    # Screening Runs
    # ==========================================================

    def create_screening_run(
        self,
        run_id,
        started_at=None,
        tickers_requested=0,
        tickers_processed=0,
        candidate_count=0,
        warnings=None,
        errors=None,
        status="STARTED",
    ):
        if run_id in (None, ""):
            return None

        self.cursor.execute(
            """
            INSERT OR REPLACE INTO screening_runs
            (
                run_id,
                status,
                started_at,
                completed_at,
                tickers_requested,
                tickers_processed,
                candidate_count,
                warnings_json,
                errors_json
            )
            VALUES (?, ?, ?, NULL, ?, ?, ?, ?, ?)
            """,
            (
                str(run_id),
                self._valid_screening_status(status),
                started_at,
                self._sqlite_int(tickers_requested),
                self._sqlite_int(tickers_processed),
                self._sqlite_int(candidate_count),
                self._json_text(warnings),
                self._json_text(errors),
            ),
        )
        self.connection.commit()
        return self.fetch_screening_run(run_id)

    def update_screening_run(
        self,
        run_id,
        status=None,
        completed_at=None,
        tickers_requested=None,
        tickers_processed=None,
        candidate_count=None,
        warnings=None,
        errors=None,
    ):
        if run_id in (None, ""):
            return None

        fields = []
        values = []
        if status is not None:
            fields.append("status = ?")
            values.append(self._valid_screening_status(status))
        if completed_at is not None:
            fields.append("completed_at = ?")
            values.append(completed_at)
        if tickers_requested is not None:
            fields.append("tickers_requested = ?")
            values.append(self._sqlite_int(tickers_requested))
        if tickers_processed is not None:
            fields.append("tickers_processed = ?")
            values.append(self._sqlite_int(tickers_processed))
        if candidate_count is not None:
            fields.append("candidate_count = ?")
            values.append(self._sqlite_int(candidate_count))
        if warnings is not None:
            fields.append("warnings_json = ?")
            values.append(self._json_text(warnings))
        if errors is not None:
            fields.append("errors_json = ?")
            values.append(self._json_text(errors))

        if not fields:
            return self.fetch_screening_run(run_id)

        values.append(str(run_id))
        self.cursor.execute(
            f"""
            UPDATE screening_runs
            SET {", ".join(fields)}
            WHERE run_id = ?
            """,
            values,
        )
        self.connection.commit()
        return self.fetch_screening_run(run_id)

    def fetch_screening_run(self, run_id):
        if run_id in (None, ""):
            return None

        self.cursor.execute(
            """
            SELECT
                run_id,
                status,
                started_at,
                completed_at,
                tickers_requested,
                tickers_processed,
                candidate_count,
                warnings_json,
                errors_json
            FROM screening_runs
            WHERE run_id = ?
            """,
            (str(run_id),),
        )
        return self._row_to_screening_run(self.cursor.fetchone())

    def fetch_latest_screening_run(self):
        self.cursor.execute(
            """
            SELECT
                run_id,
                status,
                started_at,
                completed_at,
                tickers_requested,
                tickers_processed,
                candidate_count,
                warnings_json,
                errors_json
            FROM screening_runs
            ORDER BY COALESCE(completed_at, started_at) DESC, rowid DESC
            LIMIT 1
            """
        )
        return self._row_to_screening_run(self.cursor.fetchone())

    def fetch_screening_run_history(self, limit=25, offset=0):
        paging_sql, paging_values = self._limit_offset_clause(limit, offset)
        self.cursor.execute(
            f"""
            SELECT
                run_id,
                status,
                started_at,
                completed_at,
                tickers_requested,
                tickers_processed,
                candidate_count,
                warnings_json,
                errors_json
            FROM screening_runs
            ORDER BY COALESCE(completed_at, started_at) DESC, rowid DESC
            {paging_sql}
            """,
            tuple(paging_values),
        )
        return [self._row_to_screening_run(row) for row in self.cursor.fetchall()]

    def count_screening_runs(self):
        self.cursor.execute(
            """
            SELECT COUNT(*)
            FROM screening_runs
            """
        )
        return self.cursor.fetchone()[0]

    # ==========================================================
    # Backtest Runs
    # ==========================================================

    def save_backtest_run(self, run_result, source_run_id=None):
        run_id = self.record_value(run_result, "run_id")
        if run_id in (None, ""):
            return None
        config = self.record_value(run_result, "config")
        metrics = self.record_value(run_result, "metrics") or {}
        warnings = self.record_value(run_result, "warnings") or []
        errors = self.record_value(run_result, "errors") or []
        trades = self.record_value(run_result, "trades") or []
        self.cursor.execute(
            """
            INSERT OR REPLACE INTO backtest_runs
            (
                run_id,
                source_run_id,
                completed_at,
                config_json,
                metrics_json,
                warnings_json,
                errors_json
            )
            VALUES (?, ?, CURRENT_TIMESTAMP, ?, ?, ?, ?)
            """,
            (
                str(run_id),
                source_run_id,
                json.dumps(self._json_safe(config)),
                json.dumps(self._json_safe(metrics)),
                self._json_text(warnings),
                self._json_text(errors),
            ),
        )
        self.clear_backtest_trade_results(run_id, commit=False)
        self.save_backtest_trade_results(run_id, trades, commit=False)
        self.connection.commit()
        return self.fetch_backtest_run(run_id)

    def save_backtest_trade_results(self, run_id, trades, commit=True):
        payload = []
        for trade in trades or []:
            payload.append(
                (
                    str(run_id),
                    self.record_value(trade, "ticker"),
                    self.record_value(trade, "entry_date"),
                    self.record_value(trade, "exit_date"),
                    self._sqlite_float(self.record_value(trade, "entry_price")),
                    self._sqlite_float(self.record_value(trade, "exit_price")),
                    self._sqlite_float(self.record_value(trade, "return_pct")),
                    self._sqlite_float(self.record_value(trade, "max_gain_pct")),
                    self._sqlite_float(self.record_value(trade, "max_drawdown_pct")),
                    self._sqlite_int_or_none(self.record_value(trade, "holding_days")),
                    self.record_value(trade, "exit_reason"),
                    self._sqlite_float(self.record_value(trade, "final_score")),
                    self.record_value(trade, "grade"),
                    self.record_value(trade, "confidence_level"),
                    self.record_value(trade, "setup_label"),
                    self.record_value(trade, "source_run_id"),
                    self.record_value(trade, "signal_date"),
                    self._json_text(self.record_value(trade, "warnings") or []),
                )
            )
        if payload:
            self.cursor.executemany(
                """
                INSERT INTO backtest_trade_results
                (
                    run_id,
                    ticker,
                    entry_date,
                    exit_date,
                    entry_price,
                    exit_price,
                    return_pct,
                    max_gain_pct,
                    max_drawdown_pct,
                    holding_days,
                    exit_reason,
                    final_score,
                    grade,
                    confidence_level,
                    setup_label,
                    source_run_id,
                    signal_date,
                    warnings_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                payload,
            )
        if commit:
            self.connection.commit()
        return len(payload)

    def fetch_backtest_run(self, run_id):
        if run_id in (None, ""):
            return None
        self.cursor.execute(
            """
            SELECT run_id, source_run_id, started_at, completed_at, config_json,
                   metrics_json, warnings_json, errors_json
            FROM backtest_runs
            WHERE run_id = ?
            """,
            (str(run_id),),
        )
        run = self._row_to_backtest_run(self.cursor.fetchone())
        if run is not None:
            run["trades"] = self.fetch_backtest_trade_results(run_id)
        return run

    def fetch_latest_backtest_run(self):
        self.cursor.execute(
            """
            SELECT run_id, source_run_id, started_at, completed_at, config_json,
                   metrics_json, warnings_json, errors_json
            FROM backtest_runs
            ORDER BY completed_at DESC, rowid DESC
            LIMIT 1
            """
        )
        row = self.cursor.fetchone()
        return self.fetch_backtest_run(row["run_id"]) if row is not None else None

    def fetch_backtest_run_history(self, limit=25, offset=0):
        paging_sql, paging_values = self._limit_offset_clause(limit, offset)
        self.cursor.execute(
            f"""
            SELECT run_id, source_run_id, started_at, completed_at, config_json,
                   metrics_json, warnings_json, errors_json
            FROM backtest_runs
            ORDER BY completed_at DESC, rowid DESC
            {paging_sql}
            """,
            tuple(paging_values),
        )
        return [self._row_to_backtest_run(row) for row in self.cursor.fetchall()]

    def fetch_backtest_trade_results(self, run_id):
        if run_id in (None, ""):
            return []
        self.cursor.execute(
            """
            SELECT ticker, entry_date, exit_date, entry_price, exit_price,
                   return_pct, max_gain_pct, max_drawdown_pct, holding_days,
                   exit_reason, final_score, grade, confidence_level, setup_label,
                   source_run_id, signal_date, warnings_json, created_at
            FROM backtest_trade_results
            WHERE run_id = ?
            ORDER BY entry_date, ticker
            """,
            (str(run_id),),
        )
        return [self._row_to_backtest_trade_result(row) for row in self.cursor.fetchall()]

    def clear_backtest_run(self, run_id):
        if run_id in (None, ""):
            return 0
        deleted_trades = self.clear_backtest_trade_results(run_id, commit=False)
        self.cursor.execute("DELETE FROM backtest_runs WHERE run_id = ?", (str(run_id),))
        deleted_runs = self.cursor.rowcount
        self.connection.commit()
        return deleted_runs + deleted_trades

    def clear_backtest_trade_results(self, run_id, commit=True):
        self.cursor.execute(
            "DELETE FROM backtest_trade_results WHERE run_id = ?",
            (str(run_id),),
        )
        deleted = self.cursor.rowcount
        if commit:
            self.connection.commit()
        return deleted

    # ==========================================================
    # Algorithm Validation
    # ==========================================================

    def save_validation_run(self, report):
        run_id = self.record_value(report, "run_id")
        if run_id in (None, ""):
            return None
        self.cursor.execute(
            """
            INSERT OR REPLACE INTO validation_runs
            (
                run_id,
                started_at,
                completed_at,
                start_date,
                end_date,
                replay_frequency,
                signal_count,
                outcome_count,
                summary_metrics_json,
                factor_bucket_results_json,
                walk_forward_results_json,
                benchmark_comparison_json,
                warnings_json,
                errors_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(run_id),
                self.record_value(report, "started_at"),
                self.record_value(report, "completed_at"),
                self.record_value(report, "start_date"),
                self.record_value(report, "end_date"),
                self.record_value(report, "replay_frequency"),
                self._sqlite_int(self.record_value(report, "signal_count")) or 0,
                self._sqlite_int(self.record_value(report, "outcome_count")) or 0,
                json.dumps(self._json_safe(self.record_value(report, "summary_metrics") or {})),
                json.dumps(self._json_safe(self.record_value(report, "factor_bucket_results") or [])),
                json.dumps(self._json_safe(self.record_value(report, "walk_forward_results") or [])),
                json.dumps(self._json_safe(self.record_value(report, "benchmark_comparison") or {})),
                self._json_text(self.record_value(report, "warnings") or []),
                self._json_text(self.record_value(report, "errors") or []),
            ),
        )
        self.connection.commit()
        return self.fetch_validation_run(run_id)

    def save_validation_signal_results(self, run_id, outcomes):
        if run_id in (None, ""):
            return 0
        self.clear_validation_signal_results(run_id, commit=False)
        payload = []
        for outcome in outcomes or []:
            ticker = self._normalize_ticker(self.record_value(outcome, "ticker"))
            if ticker is None:
                continue
            payload.append(
                (
                    str(run_id),
                    ticker,
                    self.record_value(outcome, "signal_date"),
                    self._sqlite_float(self.record_value(outcome, "entry_price")),
                    json.dumps(self._json_safe(self.record_value(outcome, "forward_returns") or {})),
                    self._sqlite_float(self.record_value(outcome, "max_gain_pct")),
                    self._sqlite_float(self.record_value(outcome, "max_drawdown_pct")),
                    self._sqlite_int(bool(self.record_value(outcome, "hit_profit_target"))),
                    self._sqlite_int(bool(self.record_value(outcome, "hit_stop_loss"))),
                    self._sqlite_float(self.record_value(outcome, "support_score")),
                    self._sqlite_float(self.record_value(outcome, "bounce_score")),
                    self._sqlite_float(self.record_value(outcome, "technical_score")),
                    self._sqlite_float(self.record_value(outcome, "institutional_score")),
                    self._sqlite_float(self.record_value(outcome, "final_score")),
                    self.record_value(outcome, "grade"),
                    self._json_text(self.record_value(outcome, "warnings") or []),
                )
            )
        if payload:
            self.cursor.executemany(
                """
                INSERT INTO validation_signal_results
                (
                    run_id, ticker, signal_date, entry_price, forward_returns_json,
                    max_gain_pct, max_drawdown_pct, hit_profit_target, hit_stop_loss,
                    support_score, bounce_score, technical_score, institutional_score,
                    final_score, grade, warnings_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                payload,
            )
        self.connection.commit()
        return len(payload)

    def save_weight_optimization_results(self, run_id, results):
        if run_id in (None, ""):
            return 0
        self.clear_weight_optimization_results(run_id, commit=False)
        payload = []
        for result in results or []:
            payload.append(
                (
                    str(run_id),
                    self._sqlite_int(self.record_value(result, "rank")) or 0,
                    json.dumps(self._json_safe(self.record_value(result, "weights") or {})),
                    self._sqlite_float(self.record_value(result, "score")),
                    self._sqlite_float(self.record_value(result, "expectancy")),
                    self._sqlite_float(self.record_value(result, "win_rate")),
                    self._sqlite_float(self.record_value(result, "average_return")),
                    self._sqlite_float(self.record_value(result, "max_drawdown")),
                    self._sqlite_float(self.record_value(result, "profit_factor")),
                    self._json_text(self.record_value(result, "warnings") or []),
                )
            )
        if payload:
            self.cursor.executemany(
                """
                INSERT INTO weight_optimization_results
                (
                    run_id, rank, weights_json, score, expectancy, win_rate,
                    average_return, max_drawdown, profit_factor, warnings_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                payload,
            )
        self.connection.commit()
        return len(payload)

    def fetch_validation_run(self, run_id):
        if run_id in (None, ""):
            return None
        self.cursor.execute(
            """
            SELECT *
            FROM validation_runs
            WHERE run_id = ?
            """,
            (str(run_id),),
        )
        run = self._row_to_validation_run(self.cursor.fetchone())
        if run is not None:
            run["outcomes"] = self.fetch_validation_signal_results(run_id)
            run["best_weight_configs"] = self.fetch_weight_optimization_results(run_id)
        return run

    def fetch_latest_validation_run(self):
        self.cursor.execute(
            """
            SELECT run_id
            FROM validation_runs
            ORDER BY completed_at DESC, rowid DESC
            LIMIT 1
            """
        )
        row = self.cursor.fetchone()
        return self.fetch_validation_run(row["run_id"]) if row is not None else None

    def fetch_validation_run_history(self, limit=25, offset=0):
        paging_sql, paging_values = self._limit_offset_clause(limit, offset)
        self.cursor.execute(
            f"""
            SELECT *
            FROM validation_runs
            ORDER BY completed_at DESC, rowid DESC
            {paging_sql}
            """,
            tuple(paging_values),
        )
        return [self._row_to_validation_run(row) for row in self.cursor.fetchall()]

    def fetch_validation_signal_results(self, run_id):
        if run_id in (None, ""):
            return []
        self.cursor.execute(
            """
            SELECT *
            FROM validation_signal_results
            WHERE run_id = ?
            ORDER BY signal_date ASC, ticker ASC
            """,
            (str(run_id),),
        )
        return [self._row_to_validation_signal_result(row) for row in self.cursor.fetchall()]

    def fetch_weight_optimization_results(self, run_id):
        if run_id in (None, ""):
            return []
        self.cursor.execute(
            """
            SELECT *
            FROM weight_optimization_results
            WHERE run_id = ?
            ORDER BY rank ASC, score DESC
            """,
            (str(run_id),),
        )
        return [self._row_to_weight_optimization_result(row) for row in self.cursor.fetchall()]

    def clear_validation_run(self, run_id):
        if run_id in (None, ""):
            return 0
        deleted_signals = self.clear_validation_signal_results(run_id, commit=False)
        deleted_weights = self.clear_weight_optimization_results(run_id, commit=False)
        self.cursor.execute("DELETE FROM validation_runs WHERE run_id = ?", (str(run_id),))
        deleted_runs = self.cursor.rowcount
        self.connection.commit()
        return deleted_runs + deleted_signals + deleted_weights

    def clear_validation_signal_results(self, run_id, commit=True):
        self.cursor.execute(
            "DELETE FROM validation_signal_results WHERE run_id = ?",
            (str(run_id),),
        )
        deleted = self.cursor.rowcount
        if commit:
            self.connection.commit()
        return deleted

    def clear_weight_optimization_results(self, run_id, commit=True):
        self.cursor.execute(
            "DELETE FROM weight_optimization_results WHERE run_id = ?",
            (str(run_id),),
        )
        deleted = self.cursor.rowcount
        if commit:
            self.connection.commit()
        return deleted

    def save_signal_quality_recommendation_report(self, report):
        report_id = self.record_value(report, "report_id")
        if report_id in (None, ""):
            return None
        self.cursor.execute(
            """
            INSERT OR REPLACE INTO signal_quality_recommendation_reports
            (
                report_id,
                validation_run_id,
                created_at,
                weak_groups_json,
                recommendations_json,
                warnings_json
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                str(report_id),
                self.record_value(report, "validation_run_id"),
                self.record_value(report, "created_at"),
                json.dumps(self._json_safe(self.record_value(report, "weak_groups") or [])),
                json.dumps(self._json_safe(self.record_value(report, "recommendations") or [])),
                self._json_text(self.record_value(report, "warnings") or []),
            ),
        )
        self.connection.commit()
        return self.fetch_signal_quality_recommendation_report(report_id)

    def fetch_signal_quality_recommendation_report(self, report_id):
        if report_id in (None, ""):
            return None
        self.cursor.execute(
            """
            SELECT *
            FROM signal_quality_recommendation_reports
            WHERE report_id = ?
            """,
            (str(report_id),),
        )
        return self._row_to_signal_quality_recommendation_report(self.cursor.fetchone())

    def fetch_latest_signal_quality_recommendation_report(self, validation_run_id=None):
        params = []
        where = ""
        if validation_run_id not in (None, ""):
            where = "WHERE validation_run_id = ?"
            params.append(str(validation_run_id))
        self.cursor.execute(
            f"""
            SELECT *
            FROM signal_quality_recommendation_reports
            {where}
            ORDER BY created_at DESC, rowid DESC
            LIMIT 1
            """,
            params,
        )
        return self._row_to_signal_quality_recommendation_report(self.cursor.fetchone())

    def fetch_signal_quality_recommendation_history(self, limit=25, offset=0):
        paging_sql, paging_values = self._limit_offset_clause(limit, offset)
        self.cursor.execute(
            f"""
            SELECT *
            FROM signal_quality_recommendation_reports
            ORDER BY created_at DESC, rowid DESC
            {paging_sql}
            """,
            tuple(paging_values),
        )
        return [
            self._row_to_signal_quality_recommendation_report(row)
            for row in self.cursor.fetchall()
        ]

    # ==========================================================
    # Beta Test Runs
    # ==========================================================

    def save_beta_test_run(self, run):
        run_id = self.record_value(run, "run_id")
        if run_id in (None, ""):
            return None
        self.cursor.execute(
            """
            INSERT OR REPLACE INTO beta_test_runs
            (
                run_id,
                started_at,
                completed_at,
                provider,
                universe_count,
                scanned_count,
                candidates_count,
                backtest_count,
                status,
                warnings_json,
                errors_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(run_id),
                self.record_value(run, "started_at"),
                self.record_value(run, "completed_at"),
                self.record_value(run, "provider"),
                self._sqlite_int(self.record_value(run, "universe_count")) or 0,
                self._sqlite_int(self.record_value(run, "scanned_count")) or 0,
                self._sqlite_int(self.record_value(run, "candidates_count")) or 0,
                self._sqlite_int(self.record_value(run, "backtest_count")) or 0,
                self.record_value(run, "status"),
                self._json_text(self.record_value(run, "warnings") or []),
                self._json_text(self.record_value(run, "errors") or []),
            ),
        )
        self.connection.commit()
        return self.fetch_beta_test_run(run_id)

    def fetch_beta_test_run(self, run_id):
        if run_id in (None, ""):
            return None
        self.cursor.execute(
            """
            SELECT *
            FROM beta_test_runs
            WHERE run_id = ?
            """,
            (str(run_id),),
        )
        return self._row_to_beta_test_run(self.cursor.fetchone())

    def fetch_latest_beta_test_run(self):
        self.cursor.execute(
            """
            SELECT *
            FROM beta_test_runs
            ORDER BY completed_at DESC, started_at DESC, rowid DESC
            LIMIT 1
            """
        )
        return self._row_to_beta_test_run(self.cursor.fetchone())

    def fetch_beta_test_run_history(self, limit=25, offset=0):
        paging_sql, paging_values = self._limit_offset_clause(limit, offset)
        self.cursor.execute(
            f"""
            SELECT *
            FROM beta_test_runs
            ORDER BY completed_at DESC, started_at DESC, rowid DESC
            {paging_sql}
            """,
            tuple(paging_values),
        )
        return [self._row_to_beta_test_run(row) for row in self.cursor.fetchall()]

    def clear_beta_test_run(self, run_id):
        if run_id in (None, ""):
            return 0
        self.cursor.execute(
            "DELETE FROM beta_test_runs WHERE run_id = ?",
            (str(run_id),),
        )
        deleted = self.cursor.rowcount
        self.connection.commit()
        return deleted

    # ==========================================================
    # Model Calibration
    # ==========================================================

    def save_calibration_run(self, run):
        run_id = self.record_value(run, "run_id")
        if run_id in (None, ""):
            return None
        self.cursor.execute(
            """
            INSERT OR REPLACE INTO calibration_runs
            (
                run_id,
                started_at,
                completed_at,
                status,
                source_validation_run_id,
                source_signal_quality_run_id,
                summary,
                warnings_json,
                errors_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(run_id),
                self.record_value(run, "started_at"),
                self.record_value(run, "completed_at"),
                self.record_value(run, "status"),
                self.record_value(run, "source_validation_run_id"),
                self.record_value(run, "source_signal_quality_run_id"),
                self.record_value(run, "summary"),
                self._json_text(self.record_value(run, "warnings") or []),
                self._json_text(self.record_value(run, "errors") or []),
            ),
        )
        self.connection.commit()
        return self.fetch_calibration_run(run_id)

    def save_calibration_recommendations(self, run_id, recommendations):
        if run_id in (None, ""):
            return []
        self.clear_calibration_recommendations(run_id, commit=False)
        rows = []
        for recommendation in recommendations or []:
            recommendation_id = self.record_value(recommendation, "recommendation_id")
            if recommendation_id in (None, ""):
                continue
            rows.append(
                (
                    str(recommendation_id),
                    str(run_id),
                    self.record_value(recommendation, "category"),
                    json.dumps(
                        self._json_safe(
                            self.record_value(recommendation, "current_value")
                        )
                    ),
                    json.dumps(
                        self._json_safe(
                            self.record_value(recommendation, "recommended_value")
                        )
                    ),
                    self.record_value(recommendation, "rationale"),
                    self.record_value(recommendation, "expected_impact"),
                    self.record_value(recommendation, "confidence"),
                )
            )
        if rows:
            self.cursor.executemany(
                """
                INSERT OR REPLACE INTO calibration_recommendations
                (
                    recommendation_id,
                    run_id,
                    category,
                    current_value_json,
                    recommended_value_json,
                    rationale,
                    expected_impact,
                    confidence
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
        self.connection.commit()
        return self.fetch_calibration_recommendations(run_id)

    def fetch_calibration_run(self, run_id):
        if run_id in (None, ""):
            return None
        self.cursor.execute(
            """
            SELECT *
            FROM calibration_runs
            WHERE run_id = ?
            """,
            (str(run_id),),
        )
        run = self._row_to_calibration_run(self.cursor.fetchone())
        if run is not None:
            run["recommendations"] = self.fetch_calibration_recommendations(run_id)
        return run

    def fetch_latest_calibration_run(self):
        self.cursor.execute(
            """
            SELECT *
            FROM calibration_runs
            ORDER BY completed_at DESC, started_at DESC, rowid DESC
            LIMIT 1
            """
        )
        run = self._row_to_calibration_run(self.cursor.fetchone())
        if run is not None:
            run["recommendations"] = self.fetch_calibration_recommendations(
                run["run_id"]
            )
        return run

    def fetch_calibration_run_history(self, limit=25, offset=0):
        paging_sql, paging_values = self._limit_offset_clause(limit, offset)
        self.cursor.execute(
            f"""
            SELECT *
            FROM calibration_runs
            ORDER BY completed_at DESC, started_at DESC, rowid DESC
            {paging_sql}
            """,
            tuple(paging_values),
        )
        return [self._row_to_calibration_run(row) for row in self.cursor.fetchall()]

    def fetch_calibration_recommendations(self, run_id):
        if run_id in (None, ""):
            return []
        self.cursor.execute(
            """
            SELECT *
            FROM calibration_recommendations
            WHERE run_id = ?
            ORDER BY created_at ASC, rowid ASC
            """,
            (str(run_id),),
        )
        return [
            self._row_to_calibration_recommendation(row)
            for row in self.cursor.fetchall()
        ]

    def clear_calibration_recommendations(self, run_id, commit=True):
        if run_id in (None, ""):
            return 0
        self.cursor.execute(
            "DELETE FROM calibration_recommendations WHERE run_id = ?",
            (str(run_id),),
        )
        deleted = self.cursor.rowcount
        if commit:
            self.connection.commit()
        return deleted

    def clear_calibration_run(self, run_id):
        if run_id in (None, ""):
            return 0
        self.clear_calibration_recommendations(run_id, commit=False)
        self.cursor.execute(
            "DELETE FROM calibration_runs WHERE run_id = ?",
            (str(run_id),),
        )
        deleted = self.cursor.rowcount
        self.connection.commit()
        return deleted

    @staticmethod
    def _limit_offset_clause(limit=None, offset=0):
        if limit is None:
            return "", []
        safe_limit = max(0, int(limit or 0))
        safe_offset = max(0, int(offset or 0))
        return "LIMIT ? OFFSET ?", [safe_limit, safe_offset]

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
    # Paper Trade Journal
    # ==========================================================

    def create_trade(
        self,
        ticker,
        company_name=None,
        entry_date=None,
        entry_price=None,
        stop_price=None,
        target_price=None,
        status="Watching",
        shares=None,
        risk_reward=None,
        opportunity_rating=None,
        confidence=None,
        notes=None,
    ):
        """
        Create a paper trade journal entry.
        """

        normalized_ticker = self._normalize_ticker(ticker)

        if normalized_ticker is None:
            return None

        if not self._valid_trade_status(status or "Watching"):
            return None

        self.cursor.execute(
            """
            INSERT INTO paper_trades
            (
                ticker,
                company_name,
                entry_date,
                entry_price,
                stop_price,
                target_price,
                status,
                shares,
                risk_reward,
                opportunity_rating,
                confidence,
                notes
            )
            VALUES
            (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            """,
            (
                normalized_ticker,
                company_name,
                self._format_date(entry_date),
                self._sqlite_float(entry_price),
                self._sqlite_float(stop_price),
                self._sqlite_float(target_price),
                status or "Watching",
                self._sqlite_int_or_none(shares),
                self._sqlite_float(risk_reward),
                opportunity_rating,
                confidence,
                notes,
            ),
        )

        self.connection.commit()

        return self.get_trade(self.cursor.lastrowid)

    def update_trade(self, trade_id, **updates):
        """
        Update provided fields for a paper trade.
        """

        if trade_id is None:
            return None

        allowed_fields = {
            "ticker",
            "company_name",
            "entry_date",
            "entry_price",
            "stop_price",
            "target_price",
            "exit_date",
            "exit_price",
            "status",
            "shares",
            "risk_reward",
            "opportunity_rating",
            "confidence",
            "notes",
        }
        fields = []
        values = []

        for field, value in updates.items():
            if field not in allowed_fields or value is None:
                continue

            fields.append(f"{field} = ?")

            if field == "ticker":
                normalized_ticker = self._normalize_ticker(value)
                if normalized_ticker is None:
                    return None
                values.append(normalized_ticker)
            elif field in {"entry_date", "exit_date"}:
                values.append(self._format_date(value))
            elif field in {
                "entry_price",
                "stop_price",
                "target_price",
                "exit_price",
                "risk_reward",
            }:
                values.append(self._sqlite_float(value))
            elif field == "shares":
                values.append(self._sqlite_int_or_none(value))
            elif field == "status":
                if not self._valid_trade_status(value):
                    return None
                values.append(value)
            else:
                values.append(value)

        if not fields:
            return self.get_trade(trade_id)

        fields.append("updated_at = CURRENT_TIMESTAMP")
        values.append(trade_id)

        self.cursor.execute(
            f"""
            UPDATE paper_trades
            SET {", ".join(fields)}
            WHERE id = ?
            """,
            values,
        )

        self.connection.commit()

        if self.cursor.rowcount == 0:
            return None

        return self.get_trade(trade_id)

    def close_trade(
        self,
        trade_id,
        exit_date=None,
        exit_price=None,
        status="Exited Win",
        notes=None,
    ):
        """
        Close a paper trade with exit information.
        """

        updates = {
            "exit_date": exit_date,
            "exit_price": exit_price,
            "status": status,
        }

        if notes is not None:
            updates["notes"] = notes

        return self.update_trade(trade_id, **updates)

    def delete_trade(self, trade_id):
        """
        Delete a paper trade by id.
        """

        if trade_id is None:
            return False

        self.cursor.execute(
            """
            DELETE FROM paper_trades
            WHERE id = ?
            """,
            (trade_id,),
        )

        self.connection.commit()

        return self.cursor.rowcount > 0

    def get_trade(self, trade_id):
        """
        Return one paper trade by id.
        """

        if trade_id is None:
            return None

        self.cursor.execute(
            """
            SELECT
                id,
                ticker,
                company_name,
                entry_date,
                entry_price,
                stop_price,
                target_price,
                exit_date,
                exit_price,
                status,
                shares,
                risk_reward,
                opportunity_rating,
                confidence,
                notes,
                created_at,
                updated_at
            FROM paper_trades
            WHERE id = ?
            """,
            (trade_id,),
        )

        return self.cursor.fetchone()

    def get_trades(self, status=None, ticker=None):
        """
        Return paper trades, optionally filtered by status and/or ticker.
        """

        filters = []
        values = []

        if status is not None:
            filters.append("status = ?")
            values.append(status)

        normalized_ticker = self._normalize_ticker(ticker)
        if normalized_ticker is not None:
            filters.append("ticker = ?")
            values.append(normalized_ticker)

        where_clause = ""
        if filters:
            where_clause = "WHERE " + " AND ".join(filters)

        self.cursor.execute(
            f"""
            SELECT
                id,
                ticker,
                company_name,
                entry_date,
                entry_price,
                stop_price,
                target_price,
                exit_date,
                exit_price,
                status,
                shares,
                risk_reward,
                opportunity_rating,
                confidence,
                notes,
                created_at,
                updated_at
            FROM paper_trades
            {where_clause}
            ORDER BY created_at DESC, id DESC
            """,
            values,
        )

        return self.cursor.fetchall()

    def count_trades(self, status=None):
        """
        Count paper trades, optionally filtered by status.
        """

        if status is None:
            self.cursor.execute(
                """
                SELECT COUNT(*)
                FROM paper_trades
                """
            )
            return self.cursor.fetchone()[0]

        self.cursor.execute(
            """
            SELECT COUNT(*)
            FROM paper_trades
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
    def _institutional_record_to_dict(record):
        if record is None:
            return {}
        if isinstance(record, InstitutionalData):
            return {
                "ticker": record.ticker,
                "institutional_ownership_pct": record.institutional_ownership_pct,
                "institutional_ownership_change_qoq": record.institutional_ownership_change_qoq,
                "net_institutional_buying": record.net_institutional_buying,
                "insider_buying_flag": record.insider_buying_flag,
                "insider_selling_flag": record.insider_selling_flag,
                "source": record.source,
                "as_of_date": record.as_of_date,
            }
        if isinstance(record, dict):
            return dict(record)
        return {
            "ticker": getattr(record, "ticker", None),
            "institutional_ownership_pct": getattr(
                record,
                "institutional_ownership_pct",
                None,
            ),
            "institutional_ownership_change_qoq": getattr(
                record,
                "institutional_ownership_change_qoq",
                None,
            ),
            "net_institutional_buying": getattr(record, "net_institutional_buying", None),
            "insider_buying_flag": getattr(record, "insider_buying_flag", 0),
            "insider_selling_flag": getattr(record, "insider_selling_flag", 0),
            "source": getattr(record, "source", None),
            "as_of_date": getattr(record, "as_of_date", None),
        }

    @staticmethod
    def _row_to_institutional_data(row):
        if row is None:
            return None
        return InstitutionalData(
            ticker=row["ticker"],
            institutional_ownership_pct=row["institutional_ownership_pct"],
            institutional_ownership_change_qoq=row[
                "institutional_ownership_change_qoq"
            ],
            net_institutional_buying=row["net_institutional_buying"],
            insider_buying_flag=row["insider_buying_flag"],
            insider_selling_flag=row["insider_selling_flag"],
            source=row["source"],
            as_of_date=row["as_of_date"],
            updated_at=row["updated_at"],
        )

    @staticmethod
    def _row_to_ranked_candidate(row):
        if row is None:
            return None

        return RankedCandidate(
            rank=row["rank"],
            ticker=row["ticker"],
            final_score=row["final_score"],
            explanation=DatabaseManager._json_list(row["explanation_json"]),
            warnings=DatabaseManager._json_list(row["warnings_json"]),
            grade=row["grade"] or "REJECT",
            confidence_level=row["confidence_level"] or "LOW",
            setup_label=row["setup_label"] or "Rejected",
            rejection_reasons=DatabaseManager._json_list(
                row["rejection_reasons_json"]
            ),
            source={
                "run_id": row["run_id"],
                "created_at": row["created_at"],
            },
        )

    @staticmethod
    def _row_to_screening_run(row):
        if row is None:
            return None

        return {
            "run_id": row["run_id"],
            "status": row["status"],
            "started_at": row["started_at"],
            "completed_at": row["completed_at"],
            "tickers_requested": row["tickers_requested"],
            "tickers_processed": row["tickers_processed"],
            "candidate_count": row["candidate_count"],
            "warnings": DatabaseManager._json_list(row["warnings_json"]),
            "errors": DatabaseManager._json_list(row["errors_json"]),
        }

    @staticmethod
    def _row_to_screening_signal(row):
        if row is None:
            return None

        return {
            "signal_id": row["signal_id"],
            "run_id": row["run_id"],
            "created_at": row["created_at"],
            "ticker": row["ticker"],
            "company_name": row["company_name"],
            "sector": row["sector"],
            "industry": row["industry"],
            "overall_score": row["overall_score"],
            "technical_score": row["technical_score"],
            "bounce_score": row["bounce_score"],
            "fundamental_score": row["fundamental_score"],
            "risk_score": row["risk_score"],
            "current_price": row["current_price"],
            "entry_zone": row["entry_zone"],
            "support": row["support"],
            "stop_loss": row["stop_loss"],
            "target_1": row["target_1"],
            "target_2": row["target_2"],
            "target_3": row["target_3"],
            "signal_status": row["signal_status"],
            "notes": row["notes"],
            "price_after_5d": row["price_after_5d"],
            "price_after_10d": row["price_after_10d"],
            "price_after_20d": row["price_after_20d"],
            "price_after_60d": row["price_after_60d"],
            "max_drawdown": row["max_drawdown"],
            "max_runup": row["max_runup"],
            "outcome": row["outcome"],
        }

    @staticmethod
    def _row_to_validation_run(row):
        if row is None:
            return None
        return {
            "run_id": row["run_id"],
            "started_at": row["started_at"],
            "completed_at": row["completed_at"],
            "start_date": row["start_date"],
            "end_date": row["end_date"],
            "replay_frequency": row["replay_frequency"],
            "signal_count": row["signal_count"],
            "outcome_count": row["outcome_count"],
            "summary_metrics": DatabaseManager._json_dict(row["summary_metrics_json"]),
            "factor_bucket_results": DatabaseManager._json_load(row["factor_bucket_results_json"], []),
            "walk_forward_results": DatabaseManager._json_load(row["walk_forward_results_json"], []),
            "benchmark_comparison": DatabaseManager._json_dict(row["benchmark_comparison_json"]),
            "warnings": DatabaseManager._json_list(row["warnings_json"]),
            "errors": DatabaseManager._json_list(row["errors_json"]),
        }

    @staticmethod
    def _row_to_validation_signal_result(row):
        if row is None:
            return None
        return {
            "ticker": row["ticker"],
            "signal_date": row["signal_date"],
            "entry_price": row["entry_price"],
            "forward_returns": DatabaseManager._json_dict(row["forward_returns_json"]),
            "max_gain_pct": row["max_gain_pct"],
            "max_drawdown_pct": row["max_drawdown_pct"],
            "hit_profit_target": bool(row["hit_profit_target"]),
            "hit_stop_loss": bool(row["hit_stop_loss"]),
            "support_score": row["support_score"],
            "bounce_score": row["bounce_score"],
            "technical_score": row["technical_score"],
            "institutional_score": row["institutional_score"],
            "final_score": row["final_score"],
            "grade": row["grade"],
            "warnings": DatabaseManager._json_list(row["warnings_json"]),
            "created_at": row["created_at"],
        }

    @staticmethod
    def _row_to_weight_optimization_result(row):
        if row is None:
            return None
        return {
            "rank": row["rank"],
            "weights": DatabaseManager._json_dict(row["weights_json"]),
            "score": row["score"],
            "expectancy": row["expectancy"],
            "win_rate": row["win_rate"],
            "average_return": row["average_return"],
            "max_drawdown": row["max_drawdown"],
            "profit_factor": row["profit_factor"],
            "warnings": DatabaseManager._json_list(row["warnings_json"]),
            "created_at": row["created_at"],
        }

    @staticmethod
    def _row_to_signal_quality_recommendation_report(row):
        if row is None:
            return None
        return {
            "report_id": row["report_id"],
            "validation_run_id": row["validation_run_id"],
            "created_at": row["created_at"],
            "weak_groups": DatabaseManager._json_load(row["weak_groups_json"], []),
            "recommendations": DatabaseManager._json_load(row["recommendations_json"], []),
            "warnings": DatabaseManager._json_list(row["warnings_json"]),
        }

    @staticmethod
    def _row_to_beta_test_run(row):
        if row is None:
            return None
        return {
            "run_id": row["run_id"],
            "started_at": row["started_at"],
            "completed_at": row["completed_at"],
            "provider": row["provider"],
            "universe_count": row["universe_count"],
            "scanned_count": row["scanned_count"],
            "candidates_count": row["candidates_count"],
            "backtest_count": row["backtest_count"],
            "status": row["status"],
            "warnings": DatabaseManager._json_list(row["warnings_json"]),
            "errors": DatabaseManager._json_list(row["errors_json"]),
        }

    @staticmethod
    def _row_to_calibration_run(row):
        if row is None:
            return None
        return {
            "run_id": row["run_id"],
            "started_at": row["started_at"],
            "completed_at": row["completed_at"],
            "status": row["status"],
            "source_validation_run_id": row["source_validation_run_id"],
            "source_signal_quality_run_id": row["source_signal_quality_run_id"],
            "summary": row["summary"],
            "warnings": DatabaseManager._json_list(row["warnings_json"]),
            "errors": DatabaseManager._json_list(row["errors_json"]),
        }

    @staticmethod
    def _row_to_calibration_recommendation(row):
        if row is None:
            return None
        return {
            "recommendation_id": row["recommendation_id"],
            "run_id": row["run_id"],
            "category": row["category"],
            "current_value": DatabaseManager._json_load(
                row["current_value_json"], None
            ),
            "recommended_value": DatabaseManager._json_load(
                row["recommended_value_json"], None
            ),
            "rationale": row["rationale"],
            "expected_impact": row["expected_impact"],
            "confidence": row["confidence"],
            "created_at": row["created_at"],
        }

    @staticmethod
    def _json_text(value):
        if value in (None, ""):
            payload = []
        elif isinstance(value, list):
            payload = value
        elif isinstance(value, tuple):
            payload = list(value)
        else:
            payload = [str(value)]
        return json.dumps(payload)

    @staticmethod
    def _json_list(value):
        if value in (None, ""):
            return []
        try:
            payload = json.loads(value)
        except (TypeError, ValueError, json.JSONDecodeError):
            return [str(value)]
        if isinstance(payload, list):
            return payload
        return [payload]

    @staticmethod
    def _json_dict(value):
        if value in (None, ""):
            return {}
        try:
            payload = json.loads(value)
        except (TypeError, ValueError, json.JSONDecodeError):
            return {}
        return payload if isinstance(payload, dict) else {}

    @staticmethod
    def _json_load(value, default=None):
        if value in (None, ""):
            return default
        try:
            return json.loads(value)
        except (TypeError, ValueError, json.JSONDecodeError):
            return default

    @staticmethod
    def _json_safe(value):
        if value is None:
            return None
        if isinstance(value, dict):
            return {str(key): DatabaseManager._json_safe(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [DatabaseManager._json_safe(item) for item in value]
        if hasattr(value, "__dict__"):
            return DatabaseManager._json_safe(vars(value))
        return value

    @staticmethod
    def _row_to_backtest_run(row):
        if row is None:
            return None
        return {
            "run_id": row["run_id"],
            "source_run_id": row["source_run_id"],
            "started_at": row["started_at"],
            "completed_at": row["completed_at"],
            "config": DatabaseManager._json_dict(row["config_json"]),
            "metrics": DatabaseManager._json_dict(row["metrics_json"]),
            "warnings": DatabaseManager._json_list(row["warnings_json"]),
            "errors": DatabaseManager._json_list(row["errors_json"]),
        }

    @staticmethod
    def _row_to_backtest_trade_result(row):
        if row is None:
            return None
        return {
            "ticker": row["ticker"],
            "entry_date": row["entry_date"],
            "exit_date": row["exit_date"],
            "entry_price": row["entry_price"],
            "exit_price": row["exit_price"],
            "return_pct": row["return_pct"],
            "max_gain_pct": row["max_gain_pct"],
            "max_drawdown_pct": row["max_drawdown_pct"],
            "holding_days": row["holding_days"],
            "exit_reason": row["exit_reason"],
            "final_score": row["final_score"],
            "grade": row["grade"],
            "confidence_level": row["confidence_level"],
            "setup_label": row["setup_label"],
            "source_run_id": row["source_run_id"],
            "signal_date": row["signal_date"],
            "warnings": DatabaseManager._json_list(row["warnings_json"]),
            "created_at": row["created_at"],
        }

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

    @staticmethod
    def _valid_trade_status(status):

        return status in {
            "Watching",
            "Entered",
            "Exited Win",
            "Exited Loss",
            "Cancelled",
        }

    @staticmethod
    def _valid_screening_status(status):
        normalized = str(status or "STARTED").strip().upper()
        if normalized not in {
            "STARTED",
            "COMPLETED",
            "FAILED",
            "PARTIAL",
            "CANCELLED",
            "PARTIAL_CANCELLED",
        }:
            return "FAILED"
        return normalized

    # ==========================================================
    # Shutdown
    # ==========================================================

    def close(self):

        self.connection.close()

        
