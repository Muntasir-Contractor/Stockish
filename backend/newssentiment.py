#from scripts.scrape import get_stock_data
from openai import OpenAI
import os
from dotenv import load_dotenv
from fetchnews import get_ticker_news

load_dotenv()

API_KEY = os.getenv("OPENAI_API_KEY")

def get_news_scalar(ticker):
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


