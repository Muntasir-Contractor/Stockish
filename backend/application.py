import yfinance as yf
import pandas as pd
from scripts.fetch_fr_stockdata import get_stock_data_fr
from scripts.valuation_models import discounted_cashflow_analysis, run_all_applicable_models
from db_funcs import (
    exists_in_stockdb, insert_stockfr, fetch_fr_row, update_stock, update_stock_price,
    exists_in_dcfdb, insert_dcf, fetch_dcf, get_dcf_date_stamp, update_dcf,
    exists_in_valuations, insert_valuation, fetch_all_valuations,
    update_valuation, get_valuation_date_stamp,
)
from datetime import datetime, timedelta


def is_ticker(ticker):
    stock = yf.Ticker(ticker)
    if len(stock.info) <= 1:
        return False
    return True


def is_etf(ticker: str) -> tuple[bool, float]:
    direct_data = yf.Ticker(ticker)
    info = direct_data.info
    if info.get("quoteType") == "ETF":
        return (True, info.get("open"))
    else:
        return (False, info.get("currentPrice"))


def get_stock_price(ticker):
    if not is_ticker(ticker):
        return
    try:
        fund_type, price = is_etf(ticker)
        return price
    except Exception as e:
        raise Exception(e)


# ── DCF Valuation ─────────────────────────────────────────────────────────────

def dcf_valuation_label(upside_pct: float) -> str:
    if upside_pct > 20:
        return "Strong Positive Gap"
    elif upside_pct > 10:
        return "Moderate Positive Gap"
    elif upside_pct > 5:
        return "Slight Positive Gap"
    elif upside_pct < -20:
        return "Strong Negative Gap"
    elif upside_pct < -10:
        return "Moderate Negative Gap"
    elif upside_pct < -5:
        return "Slight Negative Gap"
    else:
        return "Near Model Estimate"


def get_dcf_valuation(ticker: str) -> dict | None:
    if is_etf(ticker)[0]:
        return None

    if exists_in_dcfdb(ticker):
        latest_income_statement_date = (str((yf.Ticker(ticker).financials.columns)[0]).split(" "))[0]
        latest_income_statement_date = datetime.strptime(latest_income_statement_date, "%Y-%m-%d")
        if latest_income_statement_date > get_dcf_date_stamp(ticker):
            result = discounted_cashflow_analysis(ticker, verbose=False)
            if result is None:
                return None
            update_dcf(ticker, result)
            return result
        else:
            return fetch_dcf(ticker)
    else:
        result = discounted_cashflow_analysis(ticker, verbose=False)
        if result is None:
            return None
        insert_dcf(ticker, result)
        return result


# ── Multi-Model Valuation ────────────────────────────────────────────────────

def get_valuation(ticker: str) -> dict | None:
    """Primary valuation entry point — runs all applicable models with caching."""
    if is_etf(ticker)[0]:
        return None

    # Check freshness: compare latest income statement date against cache
    try:
        latest_income_statement_date = (str((yf.Ticker(ticker).financials.columns)[0]).split(" "))[0]
        latest_income_statement_date = datetime.strptime(latest_income_statement_date, "%Y-%m-%d")
    except Exception:
        latest_income_statement_date = None

    # Check if we have a cached primary model result
    cached_date = get_valuation_date_stamp(ticker, "primary")
    is_fresh = (cached_date is not None
                and latest_income_statement_date is not None
                and latest_income_statement_date <= cached_date)

    if is_fresh:
        cached_models = fetch_all_valuations(ticker)
        if cached_models:
            # Reconstruct the response from cache
            primary_info = None
            all_models = []
            for m in cached_models:
                if m.get("model_type") == "primary":
                    primary_info = m
                else:
                    all_models.append(m)
            primary_model = primary_info.get("_primary_model") if primary_info else "dcf"
            primary_result = next((m for m in all_models if m["model_type"] == primary_model), None)
            if primary_result is None and all_models:
                primary_result = all_models[0]
                primary_model = primary_result["model_type"]
            selection_reasoning = primary_info.get("_selection_reasoning") if primary_info else None
            return {
                "primary_model": primary_model,
                "primary_result": primary_result,
                "all_models": all_models,
                "selection_reasoning": selection_reasoning,
            }

    # Run fresh analysis
    result = run_all_applicable_models(ticker)
    if result is None or result.get("primary_result") is None:
        return None

    # Cache each model result
    for m in result["all_models"]:
        model_type = m["model_type"]
        if exists_in_valuations(ticker, model_type):
            update_valuation(ticker, model_type, m)
        else:
            insert_valuation(ticker, model_type, m)

    # Store a sentinel "primary" row to track the cache date and which model is primary
    primary_sentinel = {"model_type": "primary", "_primary_model": result["primary_model"], "_selection_reasoning": result.get("selection_reasoning")}
    if exists_in_valuations(ticker, "primary"):
        update_valuation(ticker, "primary", primary_sentinel)
    else:
        insert_valuation(ticker, "primary", primary_sentinel)

    return result


# ── Final Analysis ────────────────────────────────────────────────────────────

def compute_final_analysis(valuation_result: dict | None, fr_prediction: float | None, sentiment_scalar: float | None) -> dict | None:
    signals = []

    # Valuation signal: upside_pct mapped to [-1, 1], clamped at +/-50%
    # Weight is scaled by confidence: high=1.0, medium=0.5, low=0.25
    if valuation_result is not None and valuation_result.get("upside_downside_pct") is not None:
        upside = valuation_result["upside_downside_pct"]
        val_score = max(-1.0, min(1.0, upside / 50.0))
        conf = valuation_result.get("confidence") or valuation_result.get("dcf_confidence", "high")
        conf_multiplier = {"high": 1.0, "medium": 0.5, "low": 0.25}.get(conf, 1.0)
        signals.append({"name": "valuation", "score": val_score, "weight": 0.50 * conf_multiplier})

    # FR signal: decile 0-9 mapped to [-1, 1]
    if fr_prediction is not None:
        fr_score = (fr_prediction - 4.5) / 4.5
        signals.append({"name": "fr", "score": fr_score, "weight": 0.30})

    # Sentiment signal: scalar 0.5-1.5 mapped to [-1, 1]
    if sentiment_scalar is not None:
        sent_score = (sentiment_scalar - 1.0) / 0.5
        signals.append({"name": "sentiment", "score": sent_score, "weight": 0.20})

    if not signals:
        return None

    total_weight = sum(s["weight"] for s in signals)
    composite = sum(s["score"] * s["weight"] / total_weight for s in signals)

    if composite > 0.50:
        verdict = "Very Strong Overall Score"
    elif composite > 0.20:
        verdict = "Strong Overall Score"
    elif composite > -0.20:
        verdict = "Neutral"
    elif composite > -0.50:
        verdict = "Weak Overall Score"
    else:
        verdict = "Very Weak Overall Score"

    confidence = "High" if len(signals) >= 3 else "Medium" if len(signals) == 2 else "Low"

    return {
        "verdict": verdict,
        "composite_score": round(composite, 3),
        "signals_used": len(signals),
        "confidence": confidence,
    }


# ── Forward Return Classification ─────────────────────────────────────────────

async def get_fr_prediction(ticker: str, model) -> dict | None:
    """Return {fr_class, price_at_prediction, prediction_date} or None for ETFs."""
    if (is_etf(ticker))[0]:
        return None

    if exists_in_stockdb(ticker):
        latest_income_statement_date = (str((yf.Ticker(ticker).financials.columns)[0]).split(" "))[0]
        latest_income_statement_date = datetime.strptime(latest_income_statement_date, "%Y-%m-%d")
        cached = fetch_fr_row(ticker)
        cached_fr, cached_price, cached_date = cached if cached else (None, None, None)

        if cached_date is None or latest_income_statement_date > cached_date:
            data = await get_stock_data_fr(ticker)
            data = pd.DataFrame([data]).astype(float)
            fr = float(model.predict(data)[0])
            price_at = get_stock_price(ticker)
            update_stock(ticker, fr, latest_income_statement_date, price_at)
            return {
                "fr_class": fr,
                "price_at_prediction": price_at,
                "prediction_date": latest_income_statement_date.strftime("%Y-%m-%d"),
            }

        price_at = cached_price
        if price_at is None:
            price_at = get_price_predicted_at(ticker, cached_date)
            if price_at is not None:
                update_stock_price(ticker, price_at)
        return {
            "fr_class": cached_fr,
            "price_at_prediction": price_at,
            "prediction_date": cached_date.strftime("%Y-%m-%d"),
        }

    data = await get_stock_data_fr(ticker)
    data = pd.DataFrame([data]).astype(float)
    fr = float(model.predict(data)[0])
    price_at = get_stock_price(ticker)
    insert_stockfr(ticker, fr, price_at)
    return {
        "fr_class": fr,
        "price_at_prediction": price_at,
        "prediction_date": datetime.today().strftime("%Y-%m-%d"),
    }


"""We want to keep track of at what price the ML model outputs the Forward Return Classification. To let
the user know when the prediction was made vs when they are currently viewing it
"""
def get_price_predicted_at(ticker: str, date_string) -> float | None:
    if isinstance(date_string, datetime):
        target = date_string
    else:
        target = datetime.strptime(date_string, "%Y-%m-%d")
    hist = yf.Ticker(ticker).history(start=target, end=target + timedelta(days=5))
    if hist.empty:
        return None
    return float(hist["Close"].iloc[0])

