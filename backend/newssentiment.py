#from scripts.scrape import get_stock_data
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("OPENAI_API_KEY")

def get_news_headlines(ticker):
    headlines = []
    #fetch data from a news api (NewsAPI) about recent financial/market news about a ticker from the last 7 days
    return headlines

def get_news_scalar(ticker):
    prompt = f"""
    You are a financial analyst assistant.

    1. Summarize recent news about the company with the ticker symbol ${ticker}, limited to the last 7 days. Provide only relevant financial or market news.

    2. Based on the news summary and the company's current fair value (assume you are given it), calculate a scalar multiplier that reflects how the news might adjust the company's value, calculate scalar multiplier that reflects how the news might adjust the company's value.

    3. Return ONLY the scalar multiplier as numbers, without additional explaination.
    """

    client = OpenAI(
        api_key=API_KEY,
    )

    response = client.responses.create(
        model="gpt-5-mini",
        input=prompt,
        store=True,
    )
    return response.output_text

print(get_news_scalar("NVDA"))

