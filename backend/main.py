import asyncio
from fastapi import FastAPI, Response, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from fetchfromAPI import get_top_movers, get_top_losers, get_top_gainers
import joblib
import sys
import httpx
from pydantic import BaseModel
from pathlib import Path
import os
from dotenv import load_dotenv
from newssentiment import get_sentiment_analysis
from db_funcs import get_daily_usage, increment_usage, DAILY_LIMIT
root = Path(__file__).resolve().parent.parent
sys.path.insert(0,str(root))
from application import get_stock_price, is_etf, get_fr_prediction, get_valuation, dcf_valuation_label, compute_final_analysis
from scripts.valuation_models import (
    pe_valuation, revenue_multiple_valuation, ddm_valuation,
    pb_valuation, discounted_cashflow_analysis,
)


"""


TODO: - Replace hardcoded sector medians (scripts/valuation_models)
       with medians of top 5-15 companies in that sector, caching,
       and refetching every quarter.

       - Have a 'How to interpret the output' (replacing placeholder 1) section that explains throughouly
       the fr classification, the features it is trained on, and what the output means

       - Show users how confidence level is obtained; urging that confidence level
       does not emphasize an action rather that precise variables
       were used instead of fallback/default values

       - Fix info hover over stock info cards; it is going hovering outside of the screen

       - FIX: When cacheing the valuation models, and extra coloumn with model type 'Primary' is
       added with null values. Taking up unnecessary space

       - ADD: Caching api responses from fmp model every 30mins-1h to avoid reoccuring api calls 
       upon every visit to the home page: Radis?

       - To be completed: Handling feedback message and storing them 

       #test




"""

def get_real_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host

limiter = Limiter(key_func=get_real_ip)
app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

extra_origins = os.getenv("CORS_ORIGINS", "")
origins = [
    "http://localhost:3000",
    "http://localhost:5174",
    "http://localhost:5173",
    "https://www.stockish.ai",
    "https://stockish.ai",
] + [o.strip() for o in extra_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
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
@limiter.limit("30/minute")
async def top_movers(request: Request):
    stocks = await get_top_movers()
    return stocks
@app.get("/topgainers")
@limiter.limit("30/minute")
async def top_gainers(request: Request):
    stocks = await get_top_gainers()
    return stocks
@app.get("/toplosers")
@limiter.limit("30/minute")
async def top_losers(request: Request):
    stocks = await get_top_losers()
    return stocks

@app.get("/search/{query}")
@limiter.limit("20/minute")
async def search_tinker(request: Request, query : str):
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
@limiter.limit("15/minute")
async def get_stock_info(request: Request, ticker: str):
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
        selection_reasoning = None

        primary_result = None
        if valuation_data is not None:
            primary_result = valuation_data.get("primary_result")
            primary_model = valuation_data.get("primary_model")
            selection_reasoning = valuation_data.get("selection_reasoning")

            if primary_result is not None:
                intrinsic_value = primary_result.get("intrinsic_value")
                upside_pct = primary_result.get("upside_downside_pct")
                dcf_confidence = primary_result.get("confidence")
                dcf_warnings = primary_result.get("warnings", [])
                if upside_pct is not None:
                    valuation = dcf_valuation_label(upside_pct)

            # Build models array for frontend (pass full data including assumptions)
            for m in valuation_data.get("all_models", []):
                models.append({
                    "model_type": m.get("model_type"),
                    "intrinsic_value": m.get("intrinsic_value"),
                    "upside_downside_pct": m.get("upside_downside_pct"),
                    "confidence": m.get("confidence"),
                    "warnings": m.get("warnings", []),
                    "assumptions": m.get("assumptions"),
                    "assumptions_readonly": m.get("assumptions_readonly"),
                    "limitations": m.get("limitations"),
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
            "selection_reasoning": selection_reasoning,
        }
    except Exception as e:
        raise Exception(e)

@app.get("/stocksentiment/{ticker}")
async def get_stock_insight(ticker: str, request: Request):
    try:
        if (is_etf(ticker))[0] == True:
            return {"Sentiment": "Cannot evaluate etf"}
        client_ip = get_real_ip(request)
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
        
    


ASSUMPTION_RANGES = {
    "dcf": {
        "growth_rate": (-10, 50),
        "wacc": (1, 30),
        "terminal_growth": (0, 5),
        "projection_years": (1, 10),
    },
    "pe_comparable": {
        "sector_pe": (1, 100),
    },
    "revenue_multiple": {
        "sector_ps": (0.1, 50),
    },
    "ddm": {
        "dividend_growth": (0, 15),
        "cost_of_equity": (1, 25),
    },
    "book_value": {
        "sector_pb": (0.1, 20),
    },
}

@app.post("/stock/{ticker}/recalculate")
@limiter.limit("15/minute")
async def recalculate_model(request: Request, ticker: str, body: dict):
    """Recalculate a specific valuation model with user-provided assumptions."""
    model_type = body.get("model_type")
    assumptions = body.get("assumptions", {})

    if model_type not in ASSUMPTION_RANGES:
        raise HTTPException(status_code=422, detail=f"Unknown model_type: {model_type}")

    # Validate ranges
    ranges = ASSUMPTION_RANGES[model_type]
    for key, value in assumptions.items():
        if key not in ranges:
            raise HTTPException(status_code=422, detail=f"Unknown assumption '{key}' for {model_type}")
        lo, hi = ranges[key]
        try:
            val = float(value)
        except (TypeError, ValueError):
            raise HTTPException(status_code=422, detail=f"Invalid value for '{key}': {value}")
        if val < lo or val > hi:
            raise HTTPException(status_code=422, detail=f"'{key}' must be between {lo} and {hi}, got {val}")

    try:
        result = await asyncio.to_thread(_run_recalculation, ticker, model_type, assumptions)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if result is None:
        raise HTTPException(status_code=422, detail="Model could not produce a result with these assumptions")

    # DCF uses different key names — normalize
    confidence = result.get("confidence") or result.get("dcf_confidence")
    warnings = result.get("warnings") or result.get("dcf_warnings", [])

    return {
        "model_type": result.get("model_type", model_type),
        "intrinsic_value": result.get("intrinsic_value"),
        "upside_downside_pct": result.get("upside_downside_pct"),
        "confidence": confidence,
        "warnings": warnings,
    }

class Feedback(BaseModel):
    name: str
    feedback_type:str
    message:str
    

# Place holder for now
@app.post("/feedback")
async def submit_feedback(feedback: Feedback):
    print(f"Feedback received from {feedback.name} ({feedback.feedback_type}): {feedback.message}")
    return {"status": "success", "message": "Feedback received"}


def _run_recalculation(ticker: str, model_type: str, assumptions: dict) -> dict | None:
    """Run a single model with custom assumptions (called in thread)."""
    if model_type == "dcf":
        return discounted_cashflow_analysis(
            ticker,
            n_years=int(assumptions.get("projection_years", 5)),
            terminal_growth_rate=float(assumptions.get("terminal_growth", 2.5)) / 100,
            verbose=False,
            override_growth_rate=float(assumptions["growth_rate"]) if "growth_rate" in assumptions else None,
            override_wacc=float(assumptions["wacc"]) if "wacc" in assumptions else None,
        )
    elif model_type == "pe_comparable":
        return pe_valuation(ticker, custom_overrides=assumptions)
    elif model_type == "revenue_multiple":
        return revenue_multiple_valuation(ticker, custom_overrides=assumptions)
    elif model_type == "ddm":
        return ddm_valuation(ticker, custom_overrides=assumptions)
    elif model_type == "book_value":
        return pb_valuation(ticker, custom_overrides=assumptions)
    return None


#uvicorn main:app --reload
