import asyncio
import yfinance as yf
import pandas as pd
import os
from dotenv import load_dotenv
import httpx
"""  Fetching the necessary data required for the model to predict percentile return """
env_path = r'backend/.env'
load_dotenv(dotenv_path=env_path)
Finance_key = os.getenv("FINANCE_KEY")

# Helper function:
# If features cannot be computed with the yfinance data, i.e, N/A or NaN values:
# Use Financial Modeling Prep — fetches only the endpoints needed for the missing vars
async def fallback(ticker: str, *vars):
    fb_res = {}
    inc_statement = None
    fin_statement = None
    cf_statement  = None
    ratios        = None

    inc_endpoint     = f"https://financialmodelingprep.com/stable/income-statement?symbol={ticker}&apikey={Finance_key}"
    fin_endpoint     = f"https://financialmodelingprep.com/stable/balance-sheet-statement?symbol={ticker}&apikey={Finance_key}"
    cf_endpoint      = f"https://financialmodelingprep.com/stable/cash-flow-statement?symbol={ticker}&apikey={Finance_key}"
    ratio_endpoint = f"https://financialmodelingprep.com/stable/key-metrics?symbol={ticker}&apikey={Finance_key}"

    INC_VARS     = {"Gross_Profitability", "ROIC", "Revenue_Growth_YoY", "Interest_Coverage",
                    "Shares_Outstanding_YoY_Growth", "EV_to_EBITDA", "Accrual_Ratio"}
    BAL_VARS     = {"Gross_Profitability", "ROIC", "EV_to_EBITDA", "Accrual_Ratio"}
    CF_VARS      = {"FCF_Yield", "Accrual_Ratio"}
    PROFILE_VARS = {"FCF_Yield", "EV_to_EBITDA"}

    var_set = set(vars)

    async with httpx.AsyncClient() as client:
        reqs = {}
        if var_set & INC_VARS:     reqs['inc']     = client.get(inc_endpoint)
        if var_set & BAL_VARS:     reqs['bal']     = client.get(fin_endpoint)
        if var_set & CF_VARS:      reqs['cf']      = client.get(cf_endpoint)
        if var_set & PROFILE_VARS: reqs['ratios']  = client.get(ratio_endpoint)

        responses = dict(zip(reqs.keys(), await asyncio.gather(*reqs.values(), return_exceptions=True)))

    def parse(responses, key):
        r = responses.get(key)
        if r is None or isinstance(r, Exception): return None
        try:
            data = r.json()
        except Exception:
            print(f"[fallback] Empty/invalid response for '{key}' (status {r.status_code})")
            return None
        return data if isinstance(data, list) and data else None

    def parse_obj(responses, key):
        data = parse(responses, key)
        return data[0] if data else None

    if 'inc'     in reqs: inc_statement = parse(responses, 'inc')
    if 'bal'     in reqs: fin_statement = parse(responses, 'bal')
    if 'cf'      in reqs: cf_statement  = parse_obj(responses, 'cf')
    if 'ratios'  in reqs: ratios         = parse_obj(responses, 'ratios')

    def safe(d, key):
        if d is None: return None
        val = d.get(key)
        return float(val) if val not in (None, 0) else None

    inc_cur  = inc_statement[0] if inc_statement and len(inc_statement) > 0 else {}
    inc_prev = inc_statement[1] if inc_statement and len(inc_statement) > 1 else {}
    bal      = fin_statement[0] if fin_statement and len(fin_statement) > 0 else {}

    for var in vars:
        if var == "Gross_Profitability":
            # grossProfit / totalAssets (exact — balance sheet provides totalAssets)
            gp = safe(inc_cur, "grossProfit")
            ta = safe(bal,     "totalAssets")
            fb_res[var] = gp / ta if gp and ta else None

        elif var == "ROIC":
            # operatingIncome / (shortTermDebt + longTermDebt + totalStockholdersEquity)
            ebit        = safe(inc_cur, "operatingIncome")
            st_debt     = safe(bal,     "shortTermDebt") or 0
            lt_debt     = safe(bal,     "longTermDebt")  or 0
            eq          = safe(bal,     "totalStockholdersEquity")
            inv_capital = st_debt + lt_debt + (eq or 0)
            fb_res[var] = ebit / inv_capital if ebit and inv_capital else None

        elif var == "Revenue_Growth_YoY":
            rev0 = safe(inc_cur,  "revenue")
            rev1 = safe(inc_prev, "revenue")
            fb_res[var] = (rev0 - rev1) / abs(rev1) if rev0 and rev1 else None

        elif var == "Interest_Coverage":
            ebit = safe(inc_cur, "operatingIncome")
            ie   = safe(inc_cur, "interestExpense")
            fb_res[var] = ebit / ie if ebit and ie else None

        elif var == "Shares_Outstanding_YoY_Growth":
            sh0 = safe(inc_cur,  "weightedAverageShsOut")
            sh1 = safe(inc_prev, "weightedAverageShsOut")
            fb_res[var] = (sh0 - sh1) / abs(sh1) if sh0 and sh1 else None

        elif var == "FCF_Yield":
            fcf     = safe(cf_statement, "freeCashFlow")
            mkt_cap = safe(ratios,       "marketCap")
            fb_res[var] = fcf / mkt_cap if fcf and mkt_cap else None

        elif var == "EV_to_EBITDA":
            fb_res[var] = safe(ratios, "evToEBITDA")

        elif var == "Accrual_Ratio":
            ni  = safe(inc_cur,    "netIncome")
            fcf = safe(cf_statement, "freeCashFlow")
            ta  = safe(bal,        "totalAssets")
            fb_res[var] = (ni - fcf) / ta if ni and fcf is not None and ta else None

        else:
            # Momentum_6M — price data only, cannot derive from fundamentals
            fb_res[var] = None

    return fb_res

async def get_stock_data_fr(ticker: str) -> dict:
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

    features = {
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

    # Patch any None values using FMP income statement as fallback
    missing = [k for k, val in features.items() if val is None]
    if missing:
        fb = await fallback(ticker, *missing)
        for k in missing:
            if fb.get(k) is not None:
                features[k] = fb[k]

    return {k: v if v is not None else float('nan') for k, v in features.items()}


if __name__ == '__main__':
    ticker = 'BKNG'
    result = asyncio.run(get_stock_data_fr(ticker))
    print(f"\n--- {ticker} Features ---")
    for k, v in result.items():
        print(f"  {k}: {round(v, 4) if not pd.isna(v) else 'NaN'}")
