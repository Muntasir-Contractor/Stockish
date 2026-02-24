import sqlite3
from datetime import date , datetime

CONNECTION = "newsentiment.db"


def exists_in_db(ticker : str) -> bool:
    conn = sqlite3.connect(CONNECTION)
    cursor = conn.cursor()
    #If the ticker pops up in the database return true
    cursor.execute("SELECT * FROM stock_info WHERE ticker = ?" , (ticker,))
    stock_info = cursor.fetchone()
    #If the ticker does not exist in data return false
    if stock_info == None:
        return False
    #Otherwise the ticker exists in data
    return True

#Always run exists_in_db before implementing this
#If exists_in_db returns false then run this
"""
def insert_stock(ticker : str, scalar : float, notes = ""):
    conn = sqlite3.connect(CONNECTION)
    cursor = conn.cursor()
    today = date.today()
    date_stamp = today.strftime("%Y-%m-%d")
    cursor.execute(
        "INSERT INTO stock_sentiment (ticker, scalar, notes, date_stamp) VALUES (?, ?, ?, ?)",
        (ticker, scalar, notes or None, date_stamp)
    )
    conn.commit()
    conn.close()
    """
def insert_stock(ticker : str, scalar : float, insights,token_usage=None):
    conn = sqlite3.connect(CONNECTION)
    cursor = conn.cursor()
    today = date.today()
    date_stamp = today.strftime("%Y-%m-%d")
    cursor.execute(
        "INSERT INTO stock_sentiment (ticker, scalar, raw_json, date_stamp, token_usage) VALUES (?, ?, ?, ?, ?)",
        (ticker, scalar, insights, date_stamp, token_usage)
    )
    conn.commit()
    conn.close()


#gets the date stamp from ticker
#runs exists_in_db before running this
def get_date(ticker : str):
    conn = sqlite3.connect(CONNECTION)
    cursor = conn.cursor()
    cursor.execute(f"SELECT date_stamp FROM stock_sentiment WHERE ticker = ?" , (ticker,))
    #Unpacking the date
    date = (cursor.fetchone())[0]
    conn.close()
    return date

#returns The difference in days
# Use .total_seconds() / 3600 to get hour difference
def date_difference(date_stamp : str):
    today = date.today()
    current_date = today.strftime("%Y-%m-%d")
    #YYYY-MM-DD
    date_stamp = datetime(int(date_stamp[:4]) , int(date_stamp[5:7]) , int(date_stamp[8:]))
    current_date = datetime(int(current_date[:4]) , int(current_date[5:7]) , int(current_date[8:]))
    return (current_date - date_stamp)

def get_scalar_from_db(ticker : str):
    conn = sqlite3.connect(CONNECTION)
    cursor = conn.cursor()
    cursor.execute("SELECT scalar FROM stock_sentiment WHERE ticker = ?", (ticker,))
    res = (cursor.fetchone())[0]
    conn.close()
    return res

def update_row(ticker : str, scalar, note=""):
    conn = sqlite3.connect(CONNECTION)
    cursor = conn.cursor()
    cursor.execute("UPDATE stock_sentiment SET scalar = ? , raw_json = ? WHERE ticker = ?" , (scalar, None if not note else note, ticker))
    conn.commit()
    conn.exit()
    return