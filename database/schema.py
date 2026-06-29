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
