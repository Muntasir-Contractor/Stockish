import httpx
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("FINANCE_KEY")
append_key = f"?apikey={API_KEY}"
top_movers_endpoint = f"https://financialmodelingprep.com/stable/most-actives" + append_key
async def get_top_movers():
    async with httpx.AsyncClient() as client:
        response = await client.get(top_movers_endpoint)
        stocks = response.json()
        return stocks[:8]