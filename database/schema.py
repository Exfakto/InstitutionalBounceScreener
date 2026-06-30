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

    updated_at TEXT DEFAULT CURRENT_TIMESTAMP

);
"""
