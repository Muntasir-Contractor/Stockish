import yfinance as yf
import pandas as pd
Features = [

    "fcf_yield", # (Op Cashflow - Capex)/Enterprise Value
    "shareholder_yield", # Dividend Yield + Net Buyback yield

    # --- 2. Profitability & Quality (Looking for efficiency) ---
    "gross_profitability",   # (Revenue - COGS) / Total Assets
    "roic",                  # Operating Income / (Total Debt + Shareholder Equity)

    # --- 3. Capital Allocation (Looking for "empire building" red flags) ---
    "asset_growth_1yr",      # Year-over-Year % change in Total Assets
    "accruals",              # Net Income minus Operating Cash Flow

    # --- 4. Long-Term Price Dynamics (Looking for mean reversion/stability) ---
    "past_3yr_return",       # The stock's total return over the previous 36 months
    "price_volatility",      # The standard deviation of the stock's monthly returns
    
    # --- 5. Sector Neutralization (For XGBoost, otherwise for future NN implementation, standardize all metrics sector-wise)
    "is_technology",         # 1 if true, 0 if false
    "is_healthcare",         # 1 if true, 0 if false
    "is_financials",         # 1 if true, 0 if false ... So on
    "is_consumer_staples",   
    "is_utilities",          
    "is_energy",             
    "is_industrials",       
    "is_materials",          
    "is_real_estate",        
    "is_communication",      
    "is_consumer_disc"       
]

tickers = ["AAPL", "NVDA", "AMD"]
feature_data = []

for ticker in tickers:
    try:
        stock = yf.Ticker(ticker)
        inc = stock.financials
        bal = stock.balance_sheet

        if len(inc.columns) > 1:
            period_end_date = inc.columns[1]
            inc = inc.iloc[:, 1]
            bal = bal.iloc[:, 1]
        else:
            continue # We look at the PREVIOUS year's financials (Index 1 instead of 0)
                     # so we have enough time to look 6 months into the future.
        gross_profit = inc.get("Gross Profit", 0)
        op_income = inc.get("Operating Income", 0)
        total_assets = bal.get("Total Assets", 0)
        total_debt = bal.get("Total Debt", 0)
        equity = bal.get("Stockholders Equity", bal.get("Total Equity Gross Minority Interest", 0))

        gross_profitability = (gross_profit / total_assets) if total_assets else None
        invested_capital = total_debt + equity
        roic = (op_income / invested_capital) if invested_capital else None

        trade_date = period_end_date - pd.Timedelta(days=90)
        future_date = trade_date + pd.Timedelta(days=180)

        prices = yf.download(ticker, start=trade_date, end=future_date + pd.Timedelta(days=5), progress=False)["Close"]

        if not prices.empty and len(prices) > 1:
            buy_price = float(prices.iloc[0])
            sell_price = float(prices.iloc[-1])

            forward_6m_return = (sell_price / buy_price) - 1
        else:
            forward_6m_return = None
        
        feature_data.append({
            "Ticker": ticker,
            "Period_end": period_end_date.strftime('%Y-%m-%d'),
            "Traded Date": trade_date.strftime('%Y-%m-%d'),
            "Gross Profitability": round(gross_profitability, 4) if gross_profitability is not None else None,
            "ROIC": round(roic, 4) if roic is not None else None,
            "Target_6m_Return": round(forward_6m_return, 4) if forward_6m_return is not None else None

        })
        print(f"Successfully processed {ticker}")



    except Exception as e:
        print(f"Failed {ticker}: {e}")


df = pd.DataFrame(feature_data)
print(df)
