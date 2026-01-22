import sqlite3
from datetime import date

CONNECTION = "newsentiment.db"

#Gets time stamp of when news scalar was produced
def stock_time_stamp(ticker : str) -> str:
    connection = sqlite3.connect(CONNECTION)
    cursor = connection.cursor()
    # Fetching date stamp of the ticker, if None return none
    command = f"""SELECT date_stamp 
    FROM stock_info 
    WHERE ticker = '{ticker}';"""
    cursor.execute(command)
    date = (cursor.fetchone())[0]
    print(date)
    return False

def exists_in_db(ticker : str) -> bool:
    conn = sqlite3.connect(CONNECTION)
    cursor = conn.cursor()
        #If the ticker pops up in the database return true
    command = f""" SELECT * FROM stock_info
        WHERE ticker = '{ticker}';
        """
    cursor.execute(command)
    stock_info = cursor.fetchone()
    #If the ticker does not exist in data return false
    if stock_info == None:
        return False
    #Otherwise the ticker exists in data
    return True

#Always run exists_in_db before implementing this
#If exists_in_db returns false then run this
def insert_stock(ticker : str, scalar : float, notes = ""):
    conn = sqlite3.connect(CONNECTION)
    cursor = conn.cursor()
    today = date.today()
    date_stamp = today.strftime("%Y-%m-%d")
    cursor.execute(
        "INSERT INTO stock_info (ticker, scalar, notes, date_stamp) VALUES (?, ?, ?, ?)",
        (ticker, scalar, notes or None, date_stamp)
    )
    conn.commit()
    conn.close()