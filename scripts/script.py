import pandas as pd
from scrape import get_stock_data

tickers_data = []
with open("nasdaq_tickers.txt",'r') as f:
    for ticker in f:
        ticker = ticker.strip()
        data = get_stock_data(ticker=ticker)
        tickers_data.append(data)

