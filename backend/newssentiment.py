#from scripts.scrape import get_stock_data
from openai import OpenAI
import os
from dotenv import load_dotenv
from backend.fetchnews import get_ticker_news
import sqlite3

load_dotenv()

API_KEY = os.getenv("OPENAI_API_KEY")

#Gets time stamp of when news scalar was produced
def stock_time_stamp(ticker : str) -> bool:
    connection = sqlite3.connect("newsentiment.db")
    cursor = connection.cursor()
    command = f"""SELECT date_stamp 
    FROM stock_info 
    WHERE ticker = '{ticker}';"""
    cursor.execute(command)
    date = (cursor.fetchone())[0]
    print(date)
    return False

def get_news_scalar(ticker):

     # Connect news to an sql data base to avoid repeat use of llm
    # If news was collected say, in the past 36 hours, use the same sentiment score
    # Otherwise, collect newer news and get new sentiment score
    
    f = stock_time_stamp(ticker)
    return None #Testing out the sql querying, do not want to run rest of code, delete this later
    
    top_headlines=get_ticker_news(ticker)

    prompt = f"""
    You are a financial analyst evaluating news impact on stock valuation.

    COMPANY: {ticker}
    RECENT HEADLINES (last 7 days):

    {top_headlines}

    TASK:
    Analyze these headlines and determine their collect impact on the company's fair value.

    OUTPUT REQUIREMENTS:
    Return ONLY a scalar multiplier as a decimal number betwen 0.5 and 1.5, where:
    - 1.0 = neutral (no change to fair value)
    - > 1.0 = poistive news (increase fair value)
    - < 1.0 = negative news (decreases fair value)

    Examples:
    - Major positive news (earnings beat, big contract): 1.15
    - Minor positive news: 1.03
    - Neutral/mixed news: 1.0
    - Minor negative news: 0.97
    - Major negative news (lawsuit, earnings miss): 0.83

    Reply with ONLY the scalar multiplier as a number, without additional explaination.
    """

    client = OpenAI(
        api_key=API_KEY,
    )

    response = client.responses.create(
        model="gpt-5-mini",
        input=prompt,
        store=True,
    )
    scalar = response.output_text
    
    return scalar


get_news_scalar("NVD")
