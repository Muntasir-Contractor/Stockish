import httpx
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("FINANCE_KEY")
append_key = f"?apikey={API_KEY}"
top_movers_endpoint = f"https://financialmodelingprep.com/stable/most-actives" + append_key
top_gainers_endpoint = f"https://financialmodelingprep.com/stable/biggest-gainers" + append_key
top_losers_endpoint = f"https://financialmodelingprep.com/stable/biggest-losers" + append_key


async def get_insight(endpoint, amount=8):
    async with httpx.AsyncClient() as client:
        response = await client.get(endpoint)
        stocks = response.json()
        return stocks[:amount]

async def get_top_movers():
    response = await get_insight(top_movers_endpoint)
    return response

async def get_top_gainers():
    response = await get_insight(top_gainers_endpoint)
    return response
    
async def get_top_losers():
    response = await get_insight(top_losers_endpoint)
    return response