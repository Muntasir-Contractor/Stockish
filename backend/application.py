import numpy
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error , r2_score
from sklearn.linear_model import LinearRegression
import yfinance as yf
import pandas as pd
import joblib
from scripts.scrape import get_stock_data

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

def load_model(path=r'model\finalized_model.joblib'):
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
    
def valuation(ticker: str, stock_prediction: float) -> tuple[str, float]:
    """
    Determine if a stock is overvalued or undervalued based on prediction vs current price.
    
    Returns:
        tuple: (valuation_status, relative_error)
    """

    if not is_ticker(ticker):
        raise ValueError(f"Invalid ticker: {ticker}")
    
    if type(stock_prediction) == str:
        return "Cannot Valuate ETF"
    
    stock_price = get_stock_price(ticker)
    if stock_price is None or pd.isna(stock_price):
        raise ValueError(f"No price data available for {ticker}")
    
    relative_error = float(round((stock_prediction - stock_price) / stock_price, 2))
    
    if relative_error > 0.20:
        return ("Significantly Undervalued", relative_error)
    elif relative_error > 0.10:
        return ("Moderately Undervalued", relative_error)
    elif relative_error > 0.05:
        return ("Slightly Undervalued", relative_error)
    elif relative_error < -0.20:
        return ("Significantly Overvalued", relative_error)
    elif relative_error < -0.10:
        return ("Moderately Overvalued", relative_error)
    elif relative_error < -0.05:
        return ("Slightly Overvalued", relative_error)
    else:
        # Between -0.05 and 0.05
        return ("Fairly Valued", relative_error)
#python -m backend.application


    
