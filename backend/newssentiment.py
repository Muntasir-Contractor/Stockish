#from scripts.scrape import get_stock_data
from openai import OpenAI
import os
from dotenv import load_dotenv
from backend.fetchnews import get_ticker_news
from backend.dbfuncs import *
import sqlite3

load_dotenv()

API_KEY = os.getenv("OPENAI_API_KEY")


async def get_news_scalar(ticker):
    top_headlines = await get_ticker_news(ticker)
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

    response = await client.responses.create(
        model="gpt-5-mini",
        input=prompt,
        store=True,
    )
    scalar = response.output_text
    scalar = float(scalar.strip())
    return scalar
async def get_scalar(ticker : str):
    #NOT FINISHED
    #Create an update_row functions in dbfuncs to continue this function
    if await exists_in_db(ticker):
        difference = await date_difference(get_date(ticker))
        difference_hours = difference.total_seconds() // 3600
        if difference_hours < 24:
            return await get_scalar_from_db(ticker)
        else:
            scalar = await get_news_scalar(ticker)
            await update_row(ticker, scalar) # Notes needs to be addressed
            return scalar
    else:
        scalar = await get_news_scalar(ticker)
        await insert_stock(ticker, scalar)
        return scalar



    #If the difference in hours is less than 24 hours get the scalar from database
    #If the difference is greater than 24 hours AND it exists in db, get new scalar and update db
    # Otherwise get new scalar and insert into db