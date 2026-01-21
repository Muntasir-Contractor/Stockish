CREATE TABLE stock_info(
    ticker varchar(4) PRIMARY KEY,
    scalar float NOT NULL,
    notes varchar(255),
    date_stamp date NOT NULL
);
