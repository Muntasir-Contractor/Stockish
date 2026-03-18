from fastapi import FastAPI, Response, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fetchfromAPI import get_top_movers, get_top_losers, get_top_gainers
import joblib
import sys
import httpx
import pandas as pd
from pathlib import Path
import os
from dotenv import load_dotenv
from newssentiment import get_sentiment_analysis
from db_funcs import get_daily_usage, increment_usage, DAILY_LIMIT
root = Path(__file__).resolve().parent.parent
sys.path.insert(0,str(root))
from application import price_prediction, valuation, get_stock_price, is_etf, get_fr_prediction
from scripts.fetch_fr_stockdata import get_stock_data_fr



"""TO DO: Create a method in application.py to return the predicted forward return, --- DONE 
          Cache the the forward return output, as financial statements 10-k and balance sheets are prepared annually
          Create new table in database to cache data
          Migrate to PostgreSQL 
"""



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

MODEL = joblib.load(Path(__file__).resolve().parent / "model" / "XGboost_model.joblib")
fr_MODEL = joblib.load(Path(__file__).resolve().parent / "model" / "XGBoost_newestfr_model.joblib")
load_dotenv()
FINANCE_API_KEY = os.getenv("FINANCE_KEY")


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
        fr_prediction = get_fr_prediction(ticker,fr_MODEL)
        return{
            "ticker": ticker.upper(),
            "current_price": current_price,
            "predicted_price": round(stock_price_prediction,2) if type(stock_price_prediction) == float else stock_price_prediction,
            "valuation": conclusion,
            "relative_error": signed_pct,
            "smape": smape,
            "fr_prediction": fr_prediction
        }
    except Exception as e:
        raise Exception(e)

@app.get("/stocksentiment/{ticker}")
async def get_stock_insight(ticker: str, request: Request):
    try:
        if (is_etf(ticker))[0] == True:
            return {"Sentiment": "Cannot evaluate etf"}
        client_ip = request.client.host
        usage = get_daily_usage(client_ip)
        if usage >= DAILY_LIMIT:
            raise HTTPException(
                status_code=429,
                detail={"message": "Daily limit reached. Try again tomorrow.", "remaining": 0}
            )
        scalar, insights = await get_sentiment_analysis(ticker)
        new_count = increment_usage(client_ip)
        remaining = max(0, DAILY_LIMIT - new_count)
        return {"scalar": scalar, "insights": insights, "remaining": remaining}
    except HTTPException:
        raise
    except Exception as e:
        raise Exception(e)
        
    


#uvicorn main:app --reload
