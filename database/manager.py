from pathlib import Path
import json
import sqlite3
import pandas as pd

from database.institutional_data import InstitutionalData
from database.schema import (
    BOUNCE_VALIDATIONS_TABLE,
    EARNINGS_TABLE,
    FUNDAMENTALS_TABLE,
    INSTITUTIONAL_METRICS_TABLE,
    MARKET_UNIVERSE_INDEXES,
    MARKET_UNIVERSE_TABLE,
    PAPER_TRADES_TABLE,
    PRICE_HISTORY_TABLE,
    RANKED_CANDIDATES_INDEXES,
    RANKED_CANDIDATES_TABLE,
    SCREENING_RUNS_INDEXES,
    SCREENING_RUNS_TABLE,
    SUPPORT_LEVELS_TABLE,
    STOCKS_TABLE,
    TECHNICAL_INDICATORS_TABLE,
    WATCHLIST_TABLE,
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
        self.cursor.execute(PRICE_HISTORY_TABLE)
        self.cursor.execute(TECHNICAL_INDICATORS_TABLE)
        self.cursor.execute(SUPPORT_LEVELS_TABLE)
        self.cursor.execute(BOUNCE_VALIDATIONS_TABLE)
        self.cursor.execute(FUNDAMENTALS_TABLE)
        self.ensure_fundamentals_profile_columns()
        self.cursor.execute(INSTITUTIONAL_METRICS_TABLE)
        self.ensure_institutional_metrics_columns()
        self.cursor.execute(EARNINGS_TABLE)
        self.cursor.execute(WATCHLIST_TABLE)
        self.cursor.execute(PAPER_TRADES_TABLE)
        self.cursor.execute(RANKED_CANDIDATES_TABLE)
        for index_statement in RANKED_CANDIDATES_INDEXES:
            self.cursor.execute(index_statement)
        self.cursor.execute(SCREENING_RUNS_TABLE)
        for index_statement in SCREENING_RUNS_INDEXES:
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

    def fundamentals_count(self):

        self.cursor.execute(
            """
            SELECT COUNT(*)
            FROM fundamentals
            """
        )

        return self.cursor.fetchone()[0]

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

    @staticmethod
    def record_value(record, key):

        if isinstance(record, dict):
            return record.get(key)

        return getattr(record, key, None)

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

    def fetch_ranked_candidates(self, run_id):
        if run_id in (None, ""):
            return []

        self.cursor.execute(
            """
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
            """,
            (str(run_id),),
        )

        return [self._row_to_ranked_candidate(row) for row in self.cursor.fetchall()]

    def fetch_latest_ranked_candidates(self):
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
        return self.fetch_ranked_candidates(row["run_id"])

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

    def fetch_screening_run_history(self, limit=25):
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
            LIMIT ?
            """,
            (self._sqlite_int(limit) or 25,),
        )
        return [self._row_to_screening_run(row) for row in self.cursor.fetchall()]

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

        
