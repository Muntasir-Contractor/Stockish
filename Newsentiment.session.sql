CREATE TABLE stock_sentiment(
    ticker TEXT NOT NULL,
    scalar FLOAT NOT NULL,
    raw_json TEXT NOT NULL,
    overall_sentiment TEXT,
    bullish_count INTEGER,
    bearish_count INTEGER,
    neutral_count INTEGER,
    token_usage INTEGER,
    created_at TEXT DEFAULT (datetime('now'))

)