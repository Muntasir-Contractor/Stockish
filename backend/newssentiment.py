#from scripts.scrape import get_stock_data
from openai import AsyncOpenAI
import os
from dotenv import load_dotenv
from backend.fetchnews import get_ticker_news
from backend.dbfuncs import *
import json
import asyncio

load_dotenv()

API_KEY = os.getenv("OPENAI_API_KEY")


### HELPER FUNCTION, NEVER ACTUALLY USE THIS, USE get_news_analysis
async def get_news_sentiment(ticker):
    top_headlines = get_ticker_news(ticker)
    
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

    client = AsyncOpenAI(api_key=API_KEY)

    response = await client.responses.create(
        model="gpt-5-mini",
        input=prompt,
        store=True,
    )

    result = json.loads(response.output_text.strip())
    scalar = float(result["scalar"])
    sentiment = result["insights"]

    token_usage = response.usage

    return scalar, sentiment, token_usage

def get_final_analysis(sentiment_score : float) -> str:
    if type(scalar) != float:
        return None
    if 0.5<=scalar<0.97:
        return "Bearish"
    elif 0.97<=scalar<=1.03:
        return "Neutral"
    elif scalar>1.03:
        return "Bullish"
    
    

async def get_sentiment_analysis(ticker : str):
    #NOT FINISHED
    #Create an update_row functions in dbfuncs to continue this function
    if exists_in_db(ticker):
        difference = date_difference(get_date(ticker))
        difference_hours = difference.total_seconds() // 3600
        if difference_hours < 24:
            return get_insights_from_db(ticker)
        else:
            scalar, insights, token_usage = await get_news_sentiment(ticker)
            update_row(ticker, scalar, insights, token_usage) # Notes needs to be addressed
            return scalar, insights
    else:
        scalar, insights, token_usage = await get_news_sentiment(ticker)
        insert_stock(ticker, scalar, insights, token_usage)
        return scalar, insights

scalar, notes = asyncio.run(get_news_sentiment("NVDA"))
print(scalar)
print(notes)


    #If the difference in hours is less than 24 hours get the scalar from database
    #If the difference is greater than 24 hours AND it exists in db, get new scalar and update db
    # Otherwise get new scalar and insert into db