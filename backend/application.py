import numpy
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error , r2_score
from sklearn.linear_model import LinearRegression
import yfinance as yf
import pandas as pd
import joblib
from scripts.scrape import get_stock_data
import os
from scripts.fetch_fr_stockdata import get_stock_data_fr
from db_funcs import exists_in_stockdb, insert_stockfr, fetch_fr_class, get_date_stamp, update_stock
from datetime import datetime


# FEATURES NEEDS CHANGING
# Get rid of feautures that leak price, RMC , 52w high/low, 52 week change percent, 50 day average, 200 day 

FEATURES = [
    "Regular Market Change", "52 Week High", "52 Week Low", "52 Week Change Percent",
    "50 Day Average", "200 Day Average", "Volume", "Market Volume", "Beta",
    "Market Cap", "Forward PE", "Trailing PE", "Price to Book", "Price To Sales 12 Months",
    "Enterprise Value", "Enterprise To EBITA", "Enterprise To Revenue",
    "Gross Margins", "Profit Margins", "Operating Margins", "EBITA Margins",
    "Return on Assets", "Return on Equity", "Net Income to Common", "EBITA",
    "Earnings Growth", "Total Debt", "Debt to Equity", "Total Cash", "Free Cashflow",
    "Operating Cashflow", "Current Ratio", "Quick Ratio", "Revenue Growth",
    "Total Cash Per Share", "Recommendation Mean", "Target Mean Price"
]

def load_model(path=r"model\XGboost_model.joblib"):
    model = joblib.load(path)
    return model

def is_ticker(ticker):
    stock = yf.Ticker(ticker)
    if len(stock.info) <= 1:
        return False
    return True


#Takes in the dataframe of stockdata and returns it into two different dataframes, the stock metrics, and stock price
def prepare_data(df):
    """Ensure input is one-row DataFrame with correct columns."""
    if isinstance(df, dict):
        df = pd.DataFrame([df])
    else:
        df = df.copy()

    for col in FEATURES:
        if col not in df.columns:
            df[col] = 0

    return df[FEATURES]

def is_etf(ticker : str) -> tuple[bool, float]:
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
        fund_type , price = is_etf(ticker)
        return price
    except Exception as e:
        raise Exception(e)

async def price_prediction(ticker : str, MODEL) -> float | str:
    if not is_ticker(ticker):
        return
    #model = load_model(path=r'model\\XGboost_model.joblib')
    fund_type , price = is_etf(ticker)
    if fund_type:
        return "Cannot Valuate ETF"

    stock_data = get_stock_data(ticker)
    """
    stock_price = stock_data["Current Price"]
    if pd.isna(stock_price):
        raise Exception("Stock price not found")
    """
    stock_data = pd.DataFrame(stock_data,index=[0])
    stock_data = stock_data.dropna(axis=1)
    processed_stock_data = prepare_data(stock_data)
    stock_prediction = (MODEL.predict(processed_stock_data))[0] #XGBOOST
    stock_prediction = float(numpy.round(stock_prediction,decimals=2))
    return round(stock_prediction,2)
    
def valuation(ticker: str, stock_prediction: float) -> tuple[str, float, float]:
    """
    Determine if a stock is overvalued or undervalued based on prediction vs current price.
    
    Returns:
        tuple: (valuation_status, relative_error)
    """

    if not is_ticker(ticker):
        raise ValueError(f"Invalid ticker: {ticker}")
    
    if type(stock_prediction) == str:
        # e.g., cannot valuate ETF or other string response from predictor
        return (None, None, None)
    
    stock_price = get_stock_price(ticker)
    if stock_price is None or pd.isna(stock_price):
        raise ValueError(f"No price data available for {ticker}")
    
    # Signed percent difference (directional)
    signed_pct = (stock_prediction - stock_price) / stock_price

    # sMAPE: symmetric Mean Absolute Percentage Error (magnitude of error)
    denom = (abs(stock_prediction) + abs(stock_price)) / 2
    if denom == 0:
        smape = 0.0
    else:
        smape = abs(stock_prediction - stock_price) / denom

    # Round for readability
    signed_pct = float(round(signed_pct, 4))
    smape = float(round(smape, 4))

    # Keep labeling thresholds based on signed_pct (direction + severity)
    if signed_pct > 0.20:
        return ("Significantly Undervalued", smape, signed_pct)
    elif signed_pct > 0.10:
        return ("Moderately Undervalued", smape, signed_pct)
    elif signed_pct > 0.05:
        return ("Slightly Undervalued", smape, signed_pct)
    elif signed_pct < -0.20:
        return ("Significantly Overvalued", smape, signed_pct)
    elif signed_pct < -0.10:
        return ("Moderately Overvalued", smape, signed_pct)
    elif signed_pct < -0.05:
        return ("Slightly Overvalued", smape, signed_pct)
    else:
        # Between -0.05 and 0.05
        return ("Fairly Valued", smape, signed_pct)
    
def feature_importance(model):
    importance = model.get_booster().get_score(importance_type='gain')
    importance_df = pd.DataFrame({'feature': list(importance.keys()), 
                                'gain': list(importance.values())})
    importance_df = importance_df.sort_values('gain', ascending=False)
    print(importance_df.head(20))

async def get_fr_prediction(ticker : str, model) -> float:
    if exists_in_stockdb(ticker):
        #Gets the latest published date of the companies income statement, if the current income statement date
        # is greater than the datestamp, we must run a new analysis on the forward return classification
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





    
if __name__ == "__main__":
    feature_importance(load_model())