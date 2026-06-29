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