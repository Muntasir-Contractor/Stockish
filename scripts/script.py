import pandas as pd
from scrape import get_stock_data
from concurrent.futures import ThreadPoolExecutor, as_completed
import yfinance as yf 
import os

def load_tickers(filepath="nasdaq_tickers.txt"):
    with open(filepath, 'r') as f:
        return [line.strip() for line in f if line.strip()]

def fetch_all_stock_data(tickers, max_workers=5, cache_folder=None):
    if cache_folder is None:
        # default: folder named 'yfinance_cache' in current directory
        cache_folder = os.path.join(os.getcwd(), "yfinance_cache")
    os.makedirs(cache_folder, exist_ok=True)
    yf.set_tz_cache_location(cache_folder)
    results = []
    with ThreadPoolExecutor(max_workers) as exe:
        future_to_ticker = {exe.submit(get_stock_data, ticker ): ticker for ticker in tickers}
        for future in as_completed(future_to_ticker):
            ticker = future_to_ticker[future]
            try:
                data = future.result()
                results.append(data)
            except Exception as e:
                print(f"Error fetching data for {ticker}: {e}")
    return results

def main(to_csv=False):
    tickers = load_tickers()
    cache_folder = r"yfinance_cache"
    tickers_data = fetch_all_stock_data(tickers,cache_folder=cache_folder)
    df = pd.DataFrame(tickers_data)
    if to_csv:
        df.to_csv("stock_data.csv", index=False)
    return df
    
if __name__ == "__main__":
    main()