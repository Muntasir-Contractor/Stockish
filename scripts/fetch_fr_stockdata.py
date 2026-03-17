import yfinance as yf
import pandas as pd

"""  Fetching the necessary data required for the model to predict percentile return """

def get_stock_data_fr(ticker: str) -> dict:
    # Features: Gross_Profitability, ROIC, FCF_Yield, Revenue_Growth_YoY,
    #           Momentum_6M, EV_to_EBITDA, Accrual_Ratio, Interest_Coverage,
    #           Shares_Outstanding_YoY_Growth

    data = yf.Ticker(ticker)
    info = data.info
    fin  = data.financials    
    bal  = data.balance_sheet    
    cf   = data.cashflow         

    # Helper: safe row lookup (returns None if row missing)
    def get(df, row):
        try:
            return df.loc[row]
        except KeyError:
            return None

    # Income Statement (most recent annual = col 0, 1yr ago = col 1) 
    gross_profit_now  = get(fin, 'Gross Profit')
    op_income_now     = get(fin, 'Operating Income')
    net_income_now    = get(fin, 'Net Income')
    interest_exp_now  = get(fin, 'Interest Expense')   # negative in yfinance
    revenue_now       = get(fin, 'Total Revenue')
    da_now            = get(fin, 'Reconciled Depreciation')

    # Balance Sheet
    total_assets  = get(bal, 'Total Assets')
    total_debt    = get(bal, 'Total Debt')
    equity        = get(bal, 'Stockholders Equity')
    cash          = get(bal, 'Cash And Cash Equivalents')
    shares        = get(bal, 'Ordinary Shares Number')

    # Cash Flow
    op_cf  = get(cf, 'Operating Cash Flow')
    capex  = get(cf, 'Capital Expenditure')   # negative in yfinance

    # Use most recent annual column (index 0)
    def v(series, col=0):
        try:
            val = series.iloc[col]
            return float(val) if pd.notna(val) else None
        except Exception:
            return None

    gp    = v(gross_profit_now)
    ebit  = v(op_income_now)
    ni    = v(net_income_now)
    ie    = v(interest_exp_now)   # negative
    rev0  = v(revenue_now, 0)
    rev1  = v(revenue_now, 1)     # 1 year ago
    da    = v(da_now)

    ta    = v(total_assets)
    debt  = v(total_debt)
    eq    = v(equity)
    cash_ = v(cash)
    sh0   = v(shares, 0)
    sh1   = v(shares, 1)          # 1 year ago

    ocf   = v(op_cf)
    cx    = v(capex)              # negative

    # Market data
    mkt_cap = info.get('marketCap')

    # 6-Month Price Momentum (126 trading days ≈ 6 months)
    hist = data.history(period='1y')
    momentum_6m = None
    if not hist.empty and len(hist) >= 126:
        price_now    = float(hist['Close'].iloc[-1])
        price_6m_ago = float(hist['Close'].iloc[-126])
        momentum_6m  = (price_now - price_6m_ago) / price_6m_ago

    # Compute features
    invested_capital = (debt or 0) + (eq or 0)
    fcf = (ocf or 0) + (cx or 0)   # cx is already negative → subtraction

    gross_profitability       = gp / ta                      if gp and ta else None
    roic                      = ebit / invested_capital      if ebit and invested_capital else None
    fcf_yield                 = fcf / mkt_cap                if fcf and mkt_cap else None
    revenue_growth_yoy        = (rev0 - rev1) / abs(rev1)   if rev0 and rev1 else None
    ev_to_ebitda              = None
    accrual_ratio             = None
    interest_coverage         = None
    shares_outstanding_growth = None

    if ebit and da and mkt_cap is not None and debt is not None and cash_ is not None:
        ebitda = ebit + (da or 0)
        ev     = mkt_cap + (debt or 0) - (cash_ or 0)
        ev_to_ebitda = ev / ebitda if ebitda else None

    if ni and fcf is not None and ta:
        accrual_ratio = (ni - fcf) / ta

    if ebit and ie:
        interest_coverage = ebit / abs(ie) if ie != 0 else None

    if sh0 and sh1:
        shares_outstanding_growth = (sh0 - sh1) / abs(sh1)

    return {
        'Gross_Profitability':           gross_profitability,
        'ROIC':                          roic,
        'FCF_Yield':                     fcf_yield,
        'Revenue_Growth_YoY':            revenue_growth_yoy,
        'Momentum_6M':                   momentum_6m,
        'EV_to_EBITDA':                  ev_to_ebitda,
        'Accrual_Ratio':                 accrual_ratio,
        'Interest_Coverage':             interest_coverage,
        'Shares_Outstanding_YoY_Growth': shares_outstanding_growth,
    }


if __name__ == '__main__':
    ticker = 'HIMS'
    result = get_stock_data_fr(ticker)
    print(f"\n--- {ticker} Features ---")
    for k, v in result.items():
        print(f"  {k}: {round(v, 4) if v is not None else 'N/A'}")
