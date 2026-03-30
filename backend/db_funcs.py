from psycopg2 import pool
from datetime import date, datetime
import json
import os
from dotenv import load_dotenv

load_dotenv()

PASSWORD = os.getenv("PASSWORD")
DAILY_LIMIT = 3

connection_pool = pool.ThreadedConnectionPool(
    minconn=1,
    maxconn=10,
    host="localhost",
    dbname="postgres",
    user="postgres",
    password=PASSWORD,
    port=5432
)

def get_conn():
    conn = connection_pool.getconn()
    conn.autocommit = True
    return conn

def put_conn(conn):
    connection_pool.putconn(conn)


def _ensure_tables():
    conn = get_conn()
    try:
        cursor = conn.cursor()
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
        cursor.close()
    finally:
        put_conn(conn)

_ensure_tables()


# Rate Limiting

def get_daily_usage(ip: str) -> int:
    conn = get_conn()
    try:
        cursor = conn.cursor()
        today = date.today()
        cursor.execute(
            "SELECT count FROM rate_limits WHERE ip = %s AND date_stamp = %s",
            (ip, today)
        )
        row = cursor.fetchone()
        cursor.close()
        return row[0] if row else 0
    finally:
        put_conn(conn)


def increment_usage(ip: str) -> int:
    conn = get_conn()
    try:
        cursor = conn.cursor()
        today = date.today()
        cursor.execute("""
            INSERT INTO rate_limits (ip, date_stamp, count) VALUES (%s, %s, 1)
            ON CONFLICT (ip, date_stamp) DO UPDATE SET count = rate_limits.count + 1
        """, (ip, today))
        cursor.execute(
            "SELECT count FROM rate_limits WHERE ip = %s AND date_stamp = %s",
            (ip, today)
        )
        result = cursor.fetchone()[0]
        cursor.close()
        return result
    finally:
        put_conn(conn)

def exists_in_db(ticker: str) -> bool:
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT 1 FROM stock_sentiment WHERE ticker = %s",
            (ticker,)
        )
        result = cursor.fetchone() is not None
        cursor.close()
        return result
    finally:
        put_conn(conn)


def insert_stock(ticker: str, scalar: float, insights, token_usage=None):
    conn = get_conn()
    try:
        cursor = conn.cursor()
        today = date.today()
        if hasattr(token_usage, "total_tokens"):
            token_usage = token_usage.total_tokens
        cursor.execute(
            "INSERT INTO stock_sentiment (ticker, scalar, raw_json, date_stamp, token_usage) VALUES (%s, %s, %s, %s, %s)",
            (ticker, scalar, json.dumps(insights), today, token_usage)
        )
        cursor.close()
    finally:
        put_conn(conn)


def get_date(ticker: str):
    if not exists_in_db(ticker):
        return None
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT date_stamp FROM stock_sentiment WHERE ticker = %s",
            (ticker,)
        )
        date_stamp = cursor.fetchone()[0]
        cursor.close()
        return date_stamp.strftime("%Y-%m-%d") if hasattr(date_stamp, "strftime") else str(date_stamp)
    finally:
        put_conn(conn)


def date_difference(date_stamp: str):
    today = date.today()
    current_date = datetime(today.year, today.month, today.day)
    date_stamp = datetime(int(date_stamp[:4]), int(date_stamp[5:7]), int(date_stamp[8:]))
    return current_date - date_stamp


def get_scalar_from_db(ticker: str):
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT scalar FROM stock_sentiment WHERE ticker = %s",
            (ticker,)
        )
        result = cursor.fetchone()[0]
        cursor.close()
        return result
    finally:
        put_conn(conn)


def get_insights_from_db(ticker: str):
    if not exists_in_db(ticker):
        return None
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT scalar, raw_json FROM stock_sentiment WHERE ticker = %s",
            (ticker,)
        )
        scalar, insights = cursor.fetchone()
        cursor.close()
        if isinstance(insights, str):
            insights = json.loads(insights)
        return scalar, insights
    finally:
        put_conn(conn)


def update_row(ticker: str, scalar, insights="", token_usage=0):
    if not exists_in_db(ticker):
        return None
    conn = get_conn()
    try:
        cursor = conn.cursor()
        today = date.today()
        if hasattr(token_usage, "total_tokens"):
            token_usage = token_usage.total_tokens
        cursor.execute(
            "UPDATE stock_sentiment SET scalar = %s, raw_json = %s, token_usage = %s, date_stamp = %s WHERE ticker = %s",
            (scalar, None if not insights else json.dumps(insights), token_usage, today, ticker)
        )
        cursor.close()
    finally:
        put_conn(conn)

def exists_in_stockdb(ticker : str) -> bool:
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT 1 FROM stock WHERE ticker = %s",
            (ticker,)
        )
        result = cursor.fetchone() is not None
        cursor.close()
        return result
    finally:
        put_conn(conn)

def fetch_fr_class(ticker : str) -> float:
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT fr_class FROM stock WHERE ticker = %s", (ticker,))
        result = (cursor.fetchone())[0]
        cursor.close()
        return result
    finally:
        put_conn(conn)

def insert_stockfr(ticker : str, fr_class : float):
    conn = get_conn()
    try:
        cursor = conn.cursor()
        d = datetime.today()
        cursor.execute("INSERT INTO stock (ticker, fr_class, date_stamp) VALUES(%s, %s, %s)", (ticker, fr_class, d))
        cursor.close()
    finally:
        put_conn(conn)

def get_date_stamp(ticker : str):
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT date_stamp FROM stock WHERE ticker = %s", (ticker,))
        d = (cursor.fetchone())[0]
        cursor.close()
        return datetime(d.year, d.month, d.day)
    finally:
        put_conn(conn)

def update_stock(ticker : str, fr_class, date_stamp):
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE stock SET fr_class = %s , date_stamp = %s WHERE ticker = %s", (fr_class, date_stamp, ticker))
        cursor.close()
    finally:
        put_conn(conn)
