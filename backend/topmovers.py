import requests
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("FINANCE_KEY")
append_key = f"?apikey={API_KEY}"
top_movers_endpoint = f"https://financialmodelingprep.com/stable/most-actives" + append_key
def get_top_movers():
    request = requests.get(top_movers_endpoint)
    stocks = request.json()
    top_8 = []
    for stock in stocks[:8]:
        top_8.append(stock)
    return top_8