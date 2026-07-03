PRICE_HISTORY_TABLE = """
CREATE TABLE IF NOT EXISTS price_history (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    ticker TEXT NOT NULL,

    date TEXT NOT NULL,

    open REAL,

    high REAL,

    low REAL,

    close REAL,

    volume INTEGER,

    UNIQUE(ticker, date)
);
"""


STOCKS_TABLE = """
CREATE TABLE IF NOT EXISTS stocks (

    ticker TEXT PRIMARY KEY,

    company TEXT,

    exchange TEXT,

    sector TEXT,

    industry TEXT,

    active INTEGER DEFAULT 1

);
"""


MARKET_UNIVERSE_TABLE = """
CREATE TABLE IF NOT EXISTS market_universe (

    ticker TEXT PRIMARY KEY,

    company_name TEXT,

    exchange TEXT,

    security_type TEXT,

    sector TEXT,

    industry TEXT,

    market_cap REAL,

    price REAL,

    average_volume REAL,

    average_dollar_volume REAL,

    is_active INTEGER DEFAULT 1,

    last_updated TEXT DEFAULT CURRENT_TIMESTAMP

);
"""


MARKET_UNIVERSE_INDEXES = [
    """
    CREATE INDEX IF NOT EXISTS idx_market_universe_ticker
    ON market_universe(ticker);
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_market_universe_exchange
    ON market_universe(exchange);
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_market_universe_security_type
    ON market_universe(security_type);
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_market_universe_market_cap
    ON market_universe(market_cap);
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_market_universe_average_dollar_volume
    ON market_universe(average_dollar_volume);
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_market_universe_is_active
    ON market_universe(is_active);
    """,
]

TECHNICAL_INDICATORS_TABLE = """
CREATE TABLE IF NOT EXISTS technical_indicators (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    ticker TEXT NOT NULL,

    date TEXT NOT NULL,

    sma20 REAL,
    sma50 REAL,
    sma200 REAL,

    ema21 REAL,

    rsi14 REAL,

    atr14 REAL,

    avg_volume20 REAL,

    relative_volume REAL,

    high52 REAL,

    low52 REAL,

    macd REAL,
    macd_signal REAL,
    macd_histogram REAL,

    UNIQUE(ticker, date)

);
"""


SUPPORT_LEVELS_TABLE = """
CREATE TABLE IF NOT EXISTS support_levels (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    ticker TEXT NOT NULL,

    zone_low REAL NOT NULL,

    zone_high REAL NOT NULL,

    zone_mid REAL NOT NULL,

    touches INTEGER NOT NULL,

    strength_score REAL NOT NULL,

    current_price REAL NOT NULL,

    distance_from_current REAL NOT NULL,

    distance_from_current_pct REAL NOT NULL,

    first_touch_date TEXT,

    last_touch_date TEXT,

    created_at TEXT DEFAULT CURRENT_TIMESTAMP

);
"""


BOUNCE_VALIDATIONS_TABLE = """
CREATE TABLE IF NOT EXISTS bounce_validations (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    support_level_id INTEGER NOT NULL,

    ticker TEXT NOT NULL,

    total_touches INTEGER NOT NULL,

    successful_bounces INTEGER NOT NULL,

    failed_breakdowns INTEGER NOT NULL,

    neutral_touches INTEGER NOT NULL,

    bounce_success_rate REAL NOT NULL,

    average_bounce_pct REAL,

    median_bounce_pct REAL,

    average_days_to_bounce_peak REAL,

    current_distance_to_support REAL NOT NULL,

    current_distance_to_support_pct REAL NOT NULL,

    validated_at TEXT DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(support_level_id)

);
"""


FUNDAMENTALS_TABLE = """
CREATE TABLE IF NOT EXISTS fundamentals (

    ticker TEXT PRIMARY KEY,

    company_name TEXT,

    sector TEXT,

    industry TEXT,

    market_cap REAL,

    revenue_growth_ttm REAL,

    eps_growth_ttm REAL,

    roe REAL,

    gross_margin REAL,

    free_cash_flow REAL,

    debt_to_equity REAL,

    current_ratio REAL,

    quality_score REAL,

    updated_at TEXT DEFAULT CURRENT_TIMESTAMP

);
"""


INSTITUTIONAL_METRICS_TABLE = """
CREATE TABLE IF NOT EXISTS institutional_metrics (

    ticker TEXT PRIMARY KEY,

    institutional_ownership_pct REAL,

    institutional_ownership_change_qoq REAL,

    net_institutional_buying REAL,

    insider_buying_flag INTEGER DEFAULT 0,

    insider_selling_flag INTEGER DEFAULT 0,

    institutional_score REAL,

    source TEXT,

    as_of_date TEXT,

    updated_at TEXT DEFAULT CURRENT_TIMESTAMP

);
"""


EARNINGS_TABLE = """
CREATE TABLE IF NOT EXISTS earnings (

    ticker TEXT PRIMARY KEY,

    next_earnings_date TEXT,

    days_until_earnings INTEGER,

    previous_earnings_date TEXT,

    eps_surprise_pct REAL,

    revenue_surprise_pct REAL,

    earnings_risk_score REAL,

    updated_at TEXT DEFAULT CURRENT_TIMESTAMP

);
"""


WATCHLIST_TABLE = """
CREATE TABLE IF NOT EXISTS watchlist (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    ticker TEXT NOT NULL UNIQUE,

    company_name TEXT,

    status TEXT NOT NULL DEFAULT 'Watching'
        CHECK (status IN ('Watching', 'Ready', 'Entered', 'Rejected', 'Closed')),

    notes TEXT,

    source TEXT,

    added_at TEXT DEFAULT CURRENT_TIMESTAMP,

    updated_at TEXT DEFAULT CURRENT_TIMESTAMP

);
"""


PAPER_TRADES_TABLE = """
CREATE TABLE IF NOT EXISTS paper_trades (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    ticker TEXT NOT NULL,

    company_name TEXT,

    entry_date TEXT,

    entry_price REAL,

    stop_price REAL,

    target_price REAL,

    exit_date TEXT,

    exit_price REAL,

    status TEXT NOT NULL DEFAULT 'Watching'
        CHECK (
            status IN (
                'Watching',
                'Entered',
                'Exited Win',
                'Exited Loss',
                'Cancelled'
            )
        ),

    shares INTEGER,

    risk_reward REAL,

    opportunity_rating TEXT,

    confidence TEXT,

    notes TEXT,

    created_at TEXT DEFAULT CURRENT_TIMESTAMP,

    updated_at TEXT DEFAULT CURRENT_TIMESTAMP

);
"""


RANKED_CANDIDATES_TABLE = """
CREATE TABLE IF NOT EXISTS ranked_candidates (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    ticker TEXT NOT NULL,

    rank INTEGER NOT NULL,

    final_score REAL NOT NULL,

    grade TEXT,

    confidence_level TEXT,

    setup_label TEXT,

    explanation_json TEXT,

    warnings_json TEXT,

    rejection_reasons_json TEXT,

    run_id TEXT NOT NULL,

    created_at TEXT DEFAULT CURRENT_TIMESTAMP

);
"""


RANKED_CANDIDATES_INDEXES = [
    """
    CREATE INDEX IF NOT EXISTS idx_ranked_candidates_run_id
    ON ranked_candidates(run_id);
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_ranked_candidates_created_at
    ON ranked_candidates(created_at);
    """,
]


SCREENING_RUNS_TABLE = """
CREATE TABLE IF NOT EXISTS screening_runs (

    run_id TEXT PRIMARY KEY,

    status TEXT NOT NULL
        CHECK (
            status IN (
                'STARTED',
                'COMPLETED',
                'FAILED',
                'PARTIAL',
                'CANCELLED',
                'PARTIAL_CANCELLED'
            )
        ),

    started_at TEXT,

    completed_at TEXT,

    tickers_requested INTEGER DEFAULT 0,

    tickers_processed INTEGER DEFAULT 0,

    candidate_count INTEGER DEFAULT 0,

    warnings_json TEXT,

    errors_json TEXT

);
"""


SCREENING_RUNS_INDEXES = [
    """
    CREATE INDEX IF NOT EXISTS idx_screening_runs_started_at
    ON screening_runs(started_at);
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_screening_runs_completed_at
    ON screening_runs(completed_at);
    """,
]
