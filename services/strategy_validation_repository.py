from __future__ import annotations

from uuid import uuid4

from database.manager import DatabaseManager
from services.strategy_validation_service import StrategyValidationSample


class StrategyValidationRepository:
    """
    SQLite repository for historical strategy validation research results.
    """

    def __init__(self, db=None):
        self.db = db or DatabaseManager()

    def save_run(
        self,
        run_id=None,
        strategy_name=None,
        universe_size=0,
        sample_count=0,
        notes=None,
    ):
        run_id = str(run_id or uuid4())
        self.db.cursor.execute(
            """
            INSERT INTO strategy_validation_runs
            (
                id,
                strategy_name,
                universe_size,
                sample_count,
                notes
            )
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                strategy_name = excluded.strategy_name,
                universe_size = excluded.universe_size,
                sample_count = excluded.sample_count,
                notes = excluded.notes
            """,
            (
                run_id,
                strategy_name,
                self.integer(universe_size),
                self.integer(sample_count),
                notes,
            ),
        )
        self.db.connection.commit()
        return self.get_run(run_id)

    def save_samples(self, run_id, samples):
        if run_id in (None, ""):
            return 0
        payload = []
        for sample in samples or []:
            ticker = self.normalized_ticker(self.value(sample, "ticker"))
            if not ticker:
                continue
            payload.append(
                (
                    str(run_id),
                    ticker,
                    self.value(sample, "signal_date") or self.value(sample, "screen_date"),
                    self.float_value(
                        self.value(sample, "final_score") or self.value(sample, "score")
                    ),
                    self.score_bucket(
                        self.value(sample, "final_score") or self.value(sample, "score")
                    ),
                    self.float_value(self.value(sample, "entry_price")),
                    self.forward_return(sample, 5),
                    self.forward_return(sample, 10),
                    self.forward_return(sample, 20),
                    self.forward_return(sample, 60),
                    self.float_value(
                        self.value(sample, "max_forward_gain_pct")
                        or self.value(sample, "max_gain")
                    ),
                    self.float_value(
                        self.value(sample, "max_forward_drawdown_pct")
                        or self.value(sample, "max_drawdown")
                    ),
                    self.outcome(sample),
                )
            )
        if payload:
            self.db.cursor.executemany(
                """
                INSERT INTO strategy_validation_samples
                (
                    run_id,
                    ticker,
                    screen_date,
                    score,
                    score_bucket,
                    entry_price,
                    return_5d,
                    return_10d,
                    return_20d,
                    return_60d,
                    max_gain,
                    max_drawdown,
                    outcome
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(run_id, ticker, screen_date) DO UPDATE SET
                    score = excluded.score,
                    score_bucket = excluded.score_bucket,
                    entry_price = excluded.entry_price,
                    return_5d = excluded.return_5d,
                    return_10d = excluded.return_10d,
                    return_20d = excluded.return_20d,
                    return_60d = excluded.return_60d,
                    max_gain = excluded.max_gain,
                    max_drawdown = excluded.max_drawdown,
                    outcome = excluded.outcome
                """,
                payload,
            )
        self.db.connection.commit()
        return len(payload)

    def get_run(self, run_id):
        if run_id in (None, ""):
            return None
        self.db.cursor.execute(
            """
            SELECT id, created_at, strategy_name, universe_size, sample_count, notes
            FROM strategy_validation_runs
            WHERE id = ?
            """,
            (str(run_id),),
        )
        return self.row_dict(self.db.cursor.fetchone())

    def get_recent_runs(self, limit=25, offset=0):
        self.db.cursor.execute(
            """
            SELECT id, created_at, strategy_name, universe_size, sample_count, notes
            FROM strategy_validation_runs
            ORDER BY created_at DESC, rowid DESC
            LIMIT ? OFFSET ?
            """,
            (self.integer(limit) or 25, self.integer(offset) or 0),
        )
        return [self.row_dict(row) for row in self.db.cursor.fetchall()]

    def get_samples_for_ticker(self, ticker, run_id=None):
        ticker = self.normalized_ticker(ticker)
        if not ticker:
            return []
        query = """
            SELECT *
            FROM strategy_validation_samples
            WHERE ticker = ?
        """
        params = [ticker]
        if run_id not in (None, ""):
            query += " AND run_id = ?"
            params.append(str(run_id))
        query += " ORDER BY screen_date ASC, id ASC"
        self.db.cursor.execute(query, tuple(params))
        return [self.row_dict(row) for row in self.db.cursor.fetchall()]

    def get_samples_for_bucket(self, score_bucket, run_id=None):
        if score_bucket in (None, ""):
            return []
        query = """
            SELECT *
            FROM strategy_validation_samples
            WHERE score_bucket = ?
        """
        params = [str(score_bucket)]
        if run_id not in (None, ""):
            query += " AND run_id = ?"
            params.append(str(run_id))
        query += " ORDER BY screen_date ASC, ticker ASC"
        self.db.cursor.execute(query, tuple(params))
        return [self.row_dict(row) for row in self.db.cursor.fetchall()]

    def get_samples_by_date_range(self, start_date=None, end_date=None, run_id=None):
        query = "SELECT * FROM strategy_validation_samples WHERE 1 = 1"
        params = []
        if start_date not in (None, ""):
            query += " AND screen_date >= ?"
            params.append(str(start_date))
        if end_date not in (None, ""):
            query += " AND screen_date <= ?"
            params.append(str(end_date))
        if run_id not in (None, ""):
            query += " AND run_id = ?"
            params.append(str(run_id))
        query += " ORDER BY screen_date ASC, ticker ASC"
        self.db.cursor.execute(query, tuple(params))
        return [self.row_dict(row) for row in self.db.cursor.fetchall()]

    def get_summary_statistics(self, run_id=None, horizon="20d"):
        return_column = self.return_column(horizon)
        query = f"""
            SELECT
                COUNT(*) AS sample_count,
                COUNT({return_column}) AS completed_count,
                AVG({return_column}) AS average_return,
                SUM(CASE WHEN {return_column} > 0 THEN 1 ELSE 0 END) AS winners,
                AVG(max_gain) AS average_max_gain,
                AVG(max_drawdown) AS average_max_drawdown
            FROM strategy_validation_samples
            WHERE 1 = 1
        """
        params = []
        if run_id not in (None, ""):
            query += " AND run_id = ?"
            params.append(str(run_id))
        self.db.cursor.execute(query, tuple(params))
        row = self.row_dict(self.db.cursor.fetchone()) or {}
        completed = row.get("completed_count") or 0
        winners = row.get("winners") or 0
        return {
            "sample_count": row.get("sample_count") or 0,
            "completed_count": completed,
            "average_return": row.get("average_return") or 0.0,
            "win_rate": winners / completed if completed else 0.0,
            "average_max_gain": row.get("average_max_gain") or 0.0,
            "average_max_drawdown": row.get("average_max_drawdown") or 0.0,
        }

    @classmethod
    def forward_return(cls, sample, horizon):
        if isinstance(sample, StrategyValidationSample):
            result = sample.forward_returns.get(horizon)
            return cls.float_value(getattr(result, "return_pct", None))
        forward_returns = cls.value(sample, "forward_returns") or {}
        result = forward_returns.get(horizon) or forward_returns.get(str(horizon))
        if isinstance(result, dict):
            return cls.float_value(result.get("return_pct"))
        return cls.float_value(getattr(result, "return_pct", result))

    @classmethod
    def outcome(cls, sample):
        explicit = cls.value(sample, "outcome")
        if explicit not in (None, ""):
            return str(explicit)
        return_20d = cls.forward_return(sample, 20)
        if return_20d is None:
            return "incomplete"
        return "win" if return_20d > 0 else "loss"

    @classmethod
    def score_bucket(cls, score):
        score = cls.float_value(score)
        if score is None:
            return None
        if score >= 90:
            return "90-100"
        if score >= 80:
            return "80-89"
        if score >= 70:
            return "70-79"
        return "below 70"

    @staticmethod
    def return_column(horizon):
        normalized = str(horizon).lower().replace("return_", "")
        allowed = {"5d", "10d", "20d", "60d"}
        if normalized not in allowed:
            normalized = "20d"
        return f"return_{normalized}"

    @staticmethod
    def row_dict(row):
        return dict(row) if row is not None else None

    @staticmethod
    def value(source, key):
        if source is None:
            return None
        if isinstance(source, dict):
            return source.get(key)
        return getattr(source, key, None)

    @staticmethod
    def float_value(value):
        if hasattr(value, "value"):
            value = value.value
        if value in (None, ""):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def integer(value):
        if value in (None, ""):
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def normalized_ticker(value):
        return str(value or "").strip().upper()
