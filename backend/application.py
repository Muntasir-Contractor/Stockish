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

def get_stock_price(ticker):
    if not is_ticker(ticker):
        return
    stock_data = get_stock_data(ticker)
    return stock_data["Current Price"]

def price_prediction(ticker) -> float:
    if not is_ticker(ticker):
        return
    model = load_model(path=r'model\XGboost_model.joblib')
    stock_data = get_stock_data(ticker)
    stock_price = stock_data["Current Price"]
    if pd.isna(stock_price):
        raise Exception("Stock price not found")
    stock_data = pd.DataFrame(stock_data,index=[0])
    stock_data = stock_data.dropna(axis=1)
    processed_stock_data = prepare_data(stock_data)
    stock_prediction = (model.predict(processed_stock_data))[0] #XGBOOST
    stock_prediction = numpy.round(stock_prediction,decimals=2)
    return stock_prediction
    

def valuation(ticker):
    if not is_ticker(ticker):
        return
    """
    model = load_model(path=r'model\XGboost_model.joblib') #xgboost
    model2 = load_model()
    stock_data = get_stock_data(ticker)
    stock_price = stock_data["Current Price"] 
    if pd.isna(stock_price):
        print(f"No price data available for {ticker}")
        return None
    
    stock_data = pd.DataFrame(stock_data,index=[0])
    stock_data = stock_data.dropna(axis=1)
    processed_stock_data = prepare_data(stock_data)
    stock_prediction = (model.predict(processed_stock_data))[0] #XGBOOST
    stock_prediction = numpy.round(stock_prediction,decimals=2)

    stock_prediction_linear_regressor = (model.predict(processed_stock_data))[0]
    """
    stock_prediction = price_prediction(ticker)
    stock_price = get_stock_price(ticker)
    relative_error = (stock_prediction-stock_price)/stock_price
    if 0.05<relative_error<=0.10:
        print("This stock is slightly undervalued")
    
    elif 0.1<relative_error<=0.2:
        print("This stock is moderately undervalued")
    
    elif relative_error>0.20:
        print("This stock is significantly undervalued")

    elif -0.10<relative_error<=-0.05:
        print("This stock is slightly overvalued")

    elif -0.2<relative_error<=-0.1:
        print("This stock is moderately overvalued")

    elif relative_error < -0.2:
        print("This stock is significantly overvalued")
    
    return relative_error
    
valuation("NVDA")
#python -m backend.application


    
