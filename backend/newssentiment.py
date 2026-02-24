#from scripts.scrape import get_stock_data
from openai import OpenAI
import os
from dotenv import load_dotenv
from backend.fetchnews import get_ticker_news
from backend.dbfuncs import *
import json

load_dotenv()

API_KEY = os.getenv("OPENAI_API_KEY")


async def get_news_scalar(ticker):
    top_headlines = await get_ticker_news(ticker)
    
    prompt = f"""
    You are a financial analyst specializing in market sentiment analysis. Below are recent news headlines related to {ticker}


    COMPANY: {ticker}
    RECENT HEADLINES (last 7 days):
    {top_headlines}

    TASK:
    Analyze these headlines and return a single JSON object with exactly two keys:

    1. "scalar": a decimal multiplier between 0.5 and 1.5 representing the collective news impact on fair value:
        - 1.0 = neutral (no change)
        - > 1.0 = positive news (increases fair value)
        - < 1.0 = negative news (decreases fair value)
        Examples:
        - Major positive news (earnings beat, big contract): 1.15
        - Minor positive news: 1.03
        - Neutral/mixed news: 1.0
        - Minor negative news: 0.97
        - Major negative news (lawsuit, earnings miss): 0.83

    2. "insights": an array of 3 to 5 objects, each with:
        - "insight": short title summarizing the theme (string)
        - "sentiment": one of "Bullish", "Bearish", or "Neutral" (string)
        - "reasoning": 2-3 sentences grounded in the headlines (string)

    Rules:
    - Return valid JSON only. No preamble, no markdown, no extra text.
    - Do not invent information not supported by the headlines.
    - Be specific — avoid generic statements.
    - If conflicting signals exist within a theme, reflect that in the sentiment and reasoning.

    Expected format:
    {{
        "scalar": 1.08,
        "insights": [
            {{
                "insight": "Strong fundamental performance driving bullish sentiment",
                "sentiment": "Bullish",
                "reasoning": "Record Q3 revenue and analyst upgrades signal strong confidence. Hedge funds increasing long positions to an 18-month high further validates institutional conviction."
            }},
            {{
                "insight": "Geopolitical risks creating headwinds",
                "sentiment": "Bearish",
                "reasoning": "Tightening China export restrictions and EU antitrust scrutiny introduce structural downside risk. These pressures could limit addressable market and compress future revenue."
            }}
        ]
    }}
    """

    client = OpenAI(api_key=API_KEY)

    response = await client.responses.create(
        model="gpt-5-mini",
        input=prompt,
        store=True,
    )

    result = json.loads(response.output_text.strip())
    scalar = float(result["scalar"])
    sentiment = result["insights"]

    usage = response.usage

    return scalar, sentiment
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