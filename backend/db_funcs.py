import psycopg2
from datetime import date, datetime
import json
import os
from dotenv import load_dotenv

#IMPLEMENT POOLING UPON DEPLOYMENT

load_dotenv()

PASSWORD = os.getenv("PASSWORD")
DAILY_LIMIT = 3

conn = psycopg2.connect(
    host="localhost",
    dbname="postgres",
    user="postgres",
    password=PASSWORD,
    port=5432
)
conn.autocommit = True
cursor = conn.cursor()


def _ensure_tables():
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stock_sentiment (
            ticker      TEXT PRIMARY KEY,
            scalar      FLOAT,
            raw_json    JSONB,
            date_stamp  DATE,
            token_usage INTEGER
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rate_limits (
            ip          TEXT,
            date_stamp  DATE,
            count       INTEGER,
            PRIMARY KEY (ip, date_stamp)
        )
    """)

_ensure_tables()


# Rate Limiting 

def get_daily_usage(ip: str) -> int:
    today = date.today()
    cursor.execute(
        "SELECT count FROM rate_limits WHERE ip = %s AND date_stamp = %s",
        (ip, today)
    )
    row = cursor.fetchone()
    return row[0] if row else 0


def increment_usage(ip: str) -> int:
    today = date.today()
    cursor.execute("""
        INSERT INTO rate_limits (ip, date_stamp, count) VALUES (%s, %s, 1)
        ON CONFLICT (ip, date_stamp) DO UPDATE SET count = rate_limits.count + 1
    """, (ip, today))
    cursor.execute(
        "SELECT count FROM rate_limits WHERE ip = %s AND date_stamp = %s",
        (ip, today)
    )
    return cursor.fetchone()[0]

def exists_in_db(ticker: str) -> bool:
    cursor.execute(
        "SELECT 1 FROM stock_sentiment WHERE ticker = %s",
        (ticker,)
    )
    return cursor.fetchone() is not None


def insert_stock(ticker: str, scalar: float, insights, token_usage=None):
    today = date.today()
    if hasattr(token_usage, "total_tokens"):
        token_usage = token_usage.total_tokens
    cursor.execute(
        "INSERT INTO stock_sentiment (ticker, scalar, raw_json, date_stamp, token_usage) VALUES (%s, %s, %s, %s, %s)",
        (ticker, scalar, json.dumps(insights), today, token_usage)
    )


def get_date(ticker: str):
    if not exists_in_db(ticker):
        return None
    cursor.execute(
        "SELECT date_stamp FROM stock_sentiment WHERE ticker = %s",
        (ticker,)
    )
    date_stamp = cursor.fetchone()[0]
    # psycopg2 returns a date object for DATE columns
    return date_stamp.strftime("%Y-%m-%d") if hasattr(date_stamp, "strftime") else str(date_stamp)


def date_difference(date_stamp: str):
    today = date.today()
    current_date = datetime(today.year, today.month, today.day)
    date_stamp = datetime(int(date_stamp[:4]), int(date_stamp[5:7]), int(date_stamp[8:]))
    return current_date - date_stamp


def get_scalar_from_db(ticker: str):
    cursor.execute(
        "SELECT scalar FROM stock_sentiment WHERE ticker = %s",
        (ticker,)
    )
    return cursor.fetchone()[0]


def get_insights_from_db(ticker: str):
    if not exists_in_db(ticker):
        return None
    cursor.execute(
        "SELECT scalar, raw_json FROM stock_sentiment WHERE ticker = %s",
        (ticker,)
    )
    scalar, insights = cursor.fetchone()
    # psycopg2 returns JSONB as a dict already, but guard for string just in case
    if isinstance(insights, str):
        insights = json.loads(insights)
    return scalar, insights


def update_row(ticker: str, scalar, insights="", token_usage=0):
    if not exists_in_db(ticker):
        return None
    today = date.today()
    if hasattr(token_usage, "total_tokens"):
        token_usage = token_usage.total_tokens
    cursor.execute(
        "UPDATE stock_sentiment SET scalar = %s, raw_json = %s, token_usage = %s, date_stamp = %s WHERE ticker = %s",
        (scalar, None if not insights else json.dumps(insights), token_usage, today, ticker)
    )
