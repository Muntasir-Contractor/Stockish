import yfinance as yf
import pandas as pd
from scripts.fetch_fr_stockdata import get_stock_data_fr
from scripts.valuation_models import discounted_cashflow_analysis
from db_funcs import (
    exists_in_stockdb, insert_stockfr, fetch_fr_class, get_date_stamp, update_stock,
    exists_in_dcfdb, insert_dcf, fetch_dcf, get_dcf_date_stamp, update_dcf,
)
from datetime import datetime


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
        return "Significantly Undervalued"
    elif upside_pct > 10:
        return "Moderately Undervalued"
    elif upside_pct > 5:
        return "Slightly Undervalued"
    elif upside_pct < -20:
        return "Significantly Overvalued"
    elif upside_pct < -10:
        return "Moderately Overvalued"
    elif upside_pct < -5:
        return "Slightly Overvalued"
    else:
        return "Fairly Valued"


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


# ── Final Analysis ────────────────────────────────────────────────────────────

def compute_final_analysis(dcf_result: dict | None, fr_prediction: float | None, sentiment_scalar: float | None) -> dict | None:
    signals = []

    # DCF signal: upside_pct mapped to [-1, 1], clamped at +/-50%
    # Weight is scaled by DCF confidence: high=1.0, medium=0.5, low=0.25
    if dcf_result is not None and dcf_result.get("upside_downside_pct") is not None:
        upside = dcf_result["upside_downside_pct"]
        dcf_score = max(-1.0, min(1.0, upside / 50.0))
        conf = dcf_result.get("dcf_confidence", "high")
        conf_multiplier = {"high": 1.0, "medium": 0.5, "low": 0.25}.get(conf, 1.0)
        signals.append({"name": "dcf", "score": dcf_score, "weight": 0.50 * conf_multiplier})

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
        verdict = "Strong Buy"
    elif composite > 0.20:
        verdict = "Buy"
    elif composite > -0.20:
        verdict = "Hold"
    elif composite > -0.50:
        verdict = "Sell"
    else:
        verdict = "Strong Sell"

    confidence = "High" if len(signals) >= 3 else "Medium" if len(signals) == 2 else "Low"

    return {
        "verdict": verdict,
        "composite_score": round(composite, 3),
        "signals_used": len(signals),
        "confidence": confidence,
    }


# ── Forward Return Classification ─────────────────────────────────────────────

async def get_fr_prediction(ticker: str, model) -> float:
    if (is_etf(ticker))[0]:
        return None
    if exists_in_stockdb(ticker):
        latest_income_statement_date = (str((yf.Ticker(ticker).financials.columns)[0]).split(" "))[0]
        latest_income_statement_date = datetime.strptime(latest_income_statement_date, "%Y-%m-%d")
        if latest_income_statement_date > get_date_stamp(ticker):
            data = await get_stock_data_fr(ticker)
            data = pd.DataFrame([data]).astype(float)
            fr = float(model.predict(data)[0])
            update_stock(ticker, fr, latest_income_statement_date)
            return fr
        else:
            fr = fetch_fr_class(ticker)
            return fr
    else:
        data = await get_stock_data_fr(ticker)
        data = pd.DataFrame([data]).astype(float)
        fr = float(model.predict(data)[0])
        insert_stockfr(ticker, fr)
        return fr
