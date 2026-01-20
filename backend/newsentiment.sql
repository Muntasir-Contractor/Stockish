CREATE TABLE stock_info(
    ticker varchar(4) PRIMARY KEY,
    sentiment_score float NOT NULL,
    date_entered DATE
);