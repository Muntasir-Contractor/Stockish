#from scripts.scrape import get_stock_data
from openai import AsyncOpenAI
import os
from dotenv import load_dotenv
from fetchnews import get_ticker_news, news_toString
from db_funcs import *
import asyncio
from pydantic import BaseModel, Field
from typing import Literal

load_dotenv()

API_KEY = os.getenv("OPENAI_API_KEY")

class Insight(BaseModel):
    insight: str
    sentiment: Literal["Bullish", "Bearish", "Neutral"]
    reasoning: str

class SentimentResult(BaseModel):
    scalar: float = Field(ge=0.5,le=1.5)
    insights: list[Insight]


### HELPER FUNCTION, NEVER ACTUALLY USE THIS, USE get_news_analysis
async def get_news_sentiment(ticker):
    top_headlines_summary_json = get_ticker_news(ticker)
    if len(top_headlines_summary_json) < 1:
        return None,None,None
    headlines_summaries = news_toString(top_headlines_summary_json)
    
    prompt = f"""
    You are a financial analyst specializing in market sentiment analysis. Below are recent news headlines related to {ticker}


    COMPANY: {ticker}
    RECENT HEADLINES and summaries(last 7 days):
    {headlines_summaries}

    TASK:
    Analyze these headlines and their summaries, return a single JSON object with exactly two keys:

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
        - "reasoning": 2-3 sentences grounded in the headlines (string), but do not make direct reference from "headline", state as if factual
            Example:
                DONT: "Headline States X", "Headline describes Y"
                DO: "X", "Y"

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

    response = await client.responses.parse(
        model="gpt-5-mini",
        input=prompt,
        text_format=SentimentResult,
        store=True,
    )
    result = response.output_parsed
    if result is None:
        return None,None,None
    scalar = result.scalar
    sentiment = [i.model_dump() for i in result.insights]

    token_usage = response.usage
    return scalar, sentiment, token_usage

def get_final_analysis(sentiment_score : float) -> str:
    if type(sentiment_score) != float:
        return None
    if 0.5<=sentiment_score<0.97:
        return "Bearish"
    elif 0.97<=sentiment_score<=1.03:
        return "Neutral"
    elif sentiment_score>1.03:
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
            if scalar==None and insights==None and token_usage==None:
                return None,None
            update_row(ticker, scalar, insights, token_usage) # Notes needs to be addressed
            return scalar, insights
    else:
        scalar, insights, token_usage = await get_news_sentiment(ticker)
        if scalar is None and insights is None:
            return None, None
        insert_stock(ticker, scalar, insights, token_usage)
        return scalar, insights



    #If the difference in hours is less than 24 hours get the scalar from database
    #If the difference is greater than 24 hours AND it exists in db, get new scalar and update db
    # Otherwise get new scalar and insert into db