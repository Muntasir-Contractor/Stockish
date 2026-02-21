from fastapi import FastAPI, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fetchfromAPI import get_top_movers, get_top_losers, get_top_gainers
import joblib
import sys
import httpx
from pathlib import Path
import os
from dotenv import load_dotenv
root = Path(__file__).resolve().parent.parent
sys.path.insert(0,str(root))
from application import price_prediction, valuation, get_stock_price, is_etf

app = FastAPI()
origins = [
    "http://localhost:3000",
    "http://localhost:5174",
    "http://localhost:5173"

]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

#Loading model when app starts 

MODEL = joblib.load(r"model\XGboost_model.joblib")
load_dotenv()
FINANCE_API_KEY = os.getenv("FINANCE_KEY")
LOGOKIT_TOKEN = os.getenv("LOGOKIT_TOKEN")


#Get for reading
#Post for create
#Put for update
#Delete for delete

#Start of a beginning
@app.get("/")
def root():
    return {"Hello": "World"}
"""
@app.get("/stock/{ticker}")
async def get_stock_info(ticker : str):
    stock_price_prediction = await price_prediction(ticker,MODEL)
    conclusion , factor = valuation(ticker, stock_price_prediction)
    current_price = get_stock_price(ticker)
    return {
        "ticker": ticker.upper(),
        "current_price": current_price,
        "predicted_price": float(stock_price_prediction),
        "valuation": conclusion,
        "relative_error": float(factor)
    }
"""
@app.get("/topmovers")
async def top_movers():
    stocks = await get_top_movers()
    return stocks
@app.get("/topgainers")
async def top_gainers():
    stocks = await get_top_gainers()
    return stocks
@app.get("/toplosers")
async def top_losers():
    stocks = await get_top_losers()
    return stocks

@app.get("/search/{query}")
async def search_tinker(query : str):
    #Have a cache for stock symbol
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"https://financialmodelingprep.com/stable/search-symbol?query={query}&apikey={FINANCE_API_KEY}")
            results = response.json()

            return {
                "query": query,
                    "results": [
                        {
                            "symbol": r["symbol"],
                            "name": r["name"],
                            "exchange": r.get("exchangeShortName", ""),
                            "type": r.get("type", "")
                        }
                        for r in results[:10]
                    ]
            }
    except Exception as e:
        print(str(e))

@app.get("/stock/{ticker}")
async def get_stock_info(ticker : str):
    try:
        stock_price_prediction = await price_prediction(ticker, MODEL)
        conclusion, smape, signed_pct = valuation(ticker, stock_price_prediction)
        if not conclusion:
            conclusion = "Cannot Valuate ETF"
            smape = None
            signed_pct = None
        current_price = get_stock_price(ticker)
        return{
            "ticker": ticker.upper(),
            "current_price": current_price,
            "predicted_price": round(stock_price_prediction,2) if type(stock_price_prediction) == float else stock_price_prediction,
            "valuation": conclusion,
            "relative_error": signed_pct,
            "smape": smape
        }
    except Exception as e:
        raise Exception(e)

@app.get("/homepage")
def get_homepage_data():
    pass

#uvicorn main:app --reload
