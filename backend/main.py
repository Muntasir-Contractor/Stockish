import asyncio
from fastapi import FastAPI, Response, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fetchfromAPI import get_top_movers, get_top_losers, get_top_gainers
import joblib
import sys
import httpx
from pathlib import Path
import os
from dotenv import load_dotenv
from newssentiment import get_sentiment_analysis
from db_funcs import get_daily_usage, increment_usage, DAILY_LIMIT
root = Path(__file__).resolve().parent.parent
sys.path.insert(0,str(root))
from application import get_stock_price, is_etf, get_fr_prediction, get_valuation, dcf_valuation_label, compute_final_analysis


"""


TODO: Replace hardcoded sector medians (scripts/valuation_models)
       with medians of top 5-15 companies in that sector, caching,
       and refetching every quarter.

       Show users limitations and assumptions made on the
       valuations models, let users make their own assumptions
       to output a new value

       Have a 'How to interpret the output' (replacing placeholder 1) section that explains throughouly
       the fr classification, the features it is trained on, and what the output means

       Show users how confidence level is obtained; urging that confidence level
       does not emphasize an action rather that precise variables
       were used instead of fallback/default values



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
            symbol_res, name_res = await asyncio.gather(
                client.get(f"https://financialmodelingprep.com/stable/search-symbol?query={query}&apikey={FINANCE_API_KEY}"),
                client.get(f"https://financialmodelingprep.com/stable/search-name?query={query}&apikey={FINANCE_API_KEY}"),
            )
            symbol_results = symbol_res.json() if symbol_res.status_code == 200 else []
            name_results = name_res.json() if name_res.status_code == 200 else []

            seen = set()
            merged = []
            for r in symbol_results + name_results:
                sym = r.get("symbol")
                if sym and sym not in seen:
                    seen.add(sym)
                    merged.append({
                        "symbol": sym,
                        "name": r.get("name", ""),
                        "exchange": r.get("exchangeShortName", ""),
                        "type": r.get("type", "")
                    })

            return {
                "query": query,
                "results": merged[:10]
            }
    except Exception as e:
        print(str(e))

@app.get("/stock/{ticker}")
async def get_stock_info(ticker: str):
    try:
        current_price = get_stock_price(ticker)

        valuation_data, fr_prediction = await asyncio.gather(
            asyncio.to_thread(get_valuation, ticker),
            get_fr_prediction(ticker, fr_MODEL),
        )

        intrinsic_value = None
        upside_pct = None
        valuation = "Cannot Valuate ETF" if is_etf(ticker)[0] else "Unavailable"
        wacc = None
        growth_rate = None
        dcf_confidence = None
        dcf_warnings = []
        primary_model = None
        models = []

        primary_result = None
        if valuation_data is not None:
            primary_result = valuation_data.get("primary_result")
            primary_model = valuation_data.get("primary_model")

            if primary_result is not None:
                intrinsic_value = primary_result.get("intrinsic_value")
                upside_pct = primary_result.get("upside_downside_pct")
                dcf_confidence = primary_result.get("confidence")
                dcf_warnings = primary_result.get("warnings", [])
                if upside_pct is not None:
                    valuation = dcf_valuation_label(upside_pct)

            # Build models array for frontend
            for m in valuation_data.get("all_models", []):
                models.append({
                    "model_type": m.get("model_type"),
                    "intrinsic_value": m.get("intrinsic_value"),
                    "upside_downside_pct": m.get("upside_downside_pct"),
                    "confidence": m.get("confidence"),
                    "warnings": m.get("warnings", []),
                })

        final_analysis = compute_final_analysis(primary_result, fr_prediction, None)

        return {
            "ticker": ticker.upper(),
            "current_price": current_price,
            "intrinsic_value": intrinsic_value,
            "upside_pct": upside_pct,
            "valuation": valuation,
            "wacc": wacc,
            "growth_rate": growth_rate,
            "fr_prediction": fr_prediction,
            "final_analysis": final_analysis,
            "dcf_confidence": dcf_confidence,
            "dcf_warnings": dcf_warnings,
            "primary_model": primary_model,
            "models": models,
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
        if scalar is None and insights is None:
            remaining = max(0, DAILY_LIMIT - usage)
            return {"scalar": None, "insights": None, "remaining": remaining}
        new_count = increment_usage(client_ip)
        remaining = max(0, DAILY_LIMIT - new_count)
        return {"scalar": scalar, "insights": insights, "remaining": remaining}
    except HTTPException:
        raise
    except Exception as e:
        raise Exception(e)
        
    


#uvicorn main:app --reload
