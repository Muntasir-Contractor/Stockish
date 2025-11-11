import pandas as pd
from scrape import get_stock_data
from concurrent.futures import ThreadPoolExecutor, as_completed

def load_tickers(filepath="nasdaq_tickers.txt"):
    with open(filepath, 'r') as f:
        return [line.strip() for line in f if line.strip()]

def fetch_all_stock_data(tickers, max_workers=5):
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

def main():
    tickers = load_tickers()
    tickers_data = fetch_all_stock_data(tickers)
    df = pd.DataFrame(tickers_data)
    df.to_csv("stock_data.csv", index=False)
    return df
    
if __name__ == "__main__":
    main()