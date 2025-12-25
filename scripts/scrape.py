import requests
from bs4 import BeautifulSoup
import pandas as pd
import yfinance as yf # pyright: ignore[reportMissingImports]

def get_industry_sector(ticker : str) -> list:
    data = yf.Ticker(ticker).info
    return [data["sector"] , data["industry"]]

def create_link(ticker):
    return f"https://ca.finance.yahoo.com/quote/{ticker}/"

def get_stock_data(ticker):
    
    
    #Fetch key stock metrics using yfinance safely with .get().
    #Returns a dictionary of metrics or None if ticker fails.
    
    
    data = yf.Ticker(ticker)
    try:
        info = data.info
    except Exception as e:
        print(f"Failed to fetch {ticker}: {e}")
        return None
    
    tickerData = {
        "Ticker": ticker,
        "Current Price": info.get("currentPrice"),
        #"Market Price": info.get("regularMarketPrice"),
        "Regular Market Change": info.get("regularMarketChangePercent"),
        "52 Week High": info.get("fiftyTwoWeekHigh"),
        "52 Week Low": info.get("fiftyTwoWeekLow"),
        "52 Week Change Percent": info.get("fiftyTwoWeekChangePercent"),
        "50 Day Average": info.get("fiftyDayAverage"),
        "200 Day Average": info.get("twoHundredDayAverage"),
        "Volume": info.get("volume"),
        "Market Volume": info.get("regularMarketVolume"),
        "Beta": info.get("beta"),
        "Market Cap": info.get("marketCap"),
        "Forward PE": info.get("forwardPE"),
        "Trailing PE": info.get("trailingPE"),
        "Price to Book": info.get("priceToBook"),
        "Price To Sales 12 Months": info.get("priceToSalesTrailing12Months"),
        "Enterprise Value": info.get("enterpriseValue"),
        "Enterprise To EBITA": info.get("enterpriseToEbitda"),
        "Enterprise To Revenue": info.get("enterpriseToRevenue"),
        "Gross Margins": info.get("grossMargins"),
        "Profit Margins": info.get("profitMargins"),
        "Operating Margins": info.get("operatingMargins"),
        "EBITA Margins": info.get("ebitdaMargins"),
        "Return on Assets": info.get("returnOnAssets"),
        "Return on Equity": info.get("returnOnEquity"),
        "Net Income to Common": info.get("netIncomeToCommon"),
        "EBITA": info.get("ebitda"),
        "Earnings Growth": info.get("earningsGrowth"),
        "Total Debt": info.get("totalDebt"),
        "Debt to Equity": info.get("debtToEquity"),
        "Total Cash": info.get("totalCash"),
        "Free Cashflow": info.get("freeCashflow"),
        "Operating Cashflow": info.get("operatingCashflow"),
        "Current Ratio": info.get("currentRatio"),
        "Quick Ratio": info.get("quickRatio"),
        "Revenue Growth": info.get("revenueGrowth"),
        "Total Cash Per Share": info.get("totalCashPerShare"),
        "Recommendation Mean": info.get("recommendationMean"),
        "Target Mean Price": info.get("targetMeanPrice"),
    }
    
    return tickerData

"""
def scrape_stock(ticker):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.99 Safari/537.36'}
        source = requests.get(create_link(ticker),headers=headers).text
    except:
        print("INVALID TICKER SYMBOL")
    
    soup = BeautifulSoup(source, 'html.parser')
    #print(soup.prettify())
    title = soup.find("fin-streamer", {"data-field": "regularMarketPreviousClose"})
    print(title)

    #Get data such as price pe ratio expected return and else through soup
    def get_value(data):
        pass
    
    data = {
        "Ticker": ticker

    }

scrape_stock(create_link("NVDA"))
"""

