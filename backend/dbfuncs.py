import sqlite3
from datetime import date , datetime
import json

CONNECTION = "newsentiment.db"

#### DOUBLE-OPENING CONNECTION WITH EXISTS_IN_DB AND OTHER FUNCTIONS
#### OPTIMIZE LATER


def exists_in_db(ticker : str) -> bool:
    with sqlite3.connect(CONNECTION) as conn:
        cursor = conn.cursor()
        #If the ticker pops up in the database return true
        cursor.execute("SELECT * FROM stock_sentiment WHERE ticker = ?" , (ticker,))
        stock_info = cursor.fetchone()
        #If the ticker does not exist in data return false
        if stock_info == None:
            return False
        #Otherwise the ticker exists in data
        return True

#Always run exists_in_db before implementing this
#If exists_in_db returns false then run this
def insert_stock(ticker : str, scalar : float, insights,token_usage=None):
    with sqlite3.connect(CONNECTION) as conn:
        cursor = conn.cursor()
        today = date.today()
        date_stamp = today.strftime("%Y-%m-%d")
        cursor.execute(
            "INSERT INTO stock_sentiment (ticker, scalar, raw_json, date_stamp, token_usage) VALUES (?, ?, ?, ?, ?)",
            (ticker, scalar, insights, date_stamp, token_usage)
        )
        conn.commit()


#gets the date stamp from ticker
#runs exists_in_db before running this
def get_date(ticker : str):
    if not exists_in_db(ticker):
        return None
    with sqlite3.connect(CONNECTION) as conn:
        cursor = conn.cursor()
        cursor.execute(f"SELECT date_stamp FROM stock_sentiment WHERE ticker = ?" , (ticker,))
        #Unpacking the date
        date_stamp = (cursor.fetchone())[0]
        return date_stamp

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
    with sqlite3.connect(CONNECTION) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT scalar FROM stock_sentiment WHERE ticker = ?", (ticker,))
        res = (cursor.fetchone())[0]
        return res

def get_insights_from_db(ticker : str):
    if not exists_in_db(ticker):
        return None
    with sqlite3.connect(CONNECTION) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT scalar, raw_json FROM stock_sentiment WHERE ticker = ?", (ticker,))
        tupl = cursor.fetchone()
        scalar, insights = tupl
        insights = json.loads(insights)
        return scalar, insights

def update_row(ticker : str, scalar, insights="", token_usage=0):
    if not exists_in_db(ticker):
        return None
    with sqlite3.connect(CONNECTION) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE stock_sentiment SET scalar = ? , raw_json = ?, token_usage = ? WHERE ticker = ?" , (scalar, None if not insights else insights, token_usage, ticker))
        conn.commit()
    return