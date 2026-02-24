import joblib
from backend.application import price_prediction, valuation, prepare_data, get_stock_price
from scripts.scrape import get_stock_data
import asyncio
import os
from dotenv import load_dotenv

env_path = r"backend\.env"

# Load that specific .env file
load_dotenv(dotenv_path=env_path)
SIMFIN = os.getenv("SIMFIN")

TICKERS = []

def load_model(path):
    model = joblib.load(path)
    return model

import warnings
warnings.filterwarnings("ignore")

import os
import pandas as pd
import yfinance as yf

# ---------------------------------------------------------------------------
# SimFin helpers
# ---------------------------------------------------------------------------

def _load_simfin(market: str = "us", data_dir: str = "~/simfin_data"):
    """Load SimFin datasets (downloads on first run, cached afterwards)."""
    try:
        import simfin as sf
    except ImportError:
        raise ImportError("Install simfin:  pip install simfin")

    sf.set_api_key(SIMFIN)
    sf.set_data_dir(os.path.expanduser(data_dir))

    prices   = sf.load_shareprices(variant="daily",   market=market)
    income   = sf.load_income(     variant="annual",  market=market)
    cashflow = sf.load_cashflow(   variant="annual",  market=market)
    balance  = sf.load_balance(    variant="annual",  market=market)

    return prices, income, cashflow, balance


def _latest_row(df: pd.DataFrame, ticker: str) -> pd.Series:
    """Return the most-recent row for a ticker from a SimFin multi-index df."""
    if ticker not in df.index.get_level_values(0):
        return pd.Series(dtype=float)
    sub = df.loc[ticker]
    if isinstance(sub.index, pd.MultiIndex):
        # (Ticker, Report Date) index
        sub = sub.sort_index(level=0).iloc[-1]
    elif isinstance(sub.index, pd.DatetimeIndex):
        sub = sub.sort_index().iloc[-1]
    else:
        sub = sub.iloc[-1]
    return sub


def _safe(val, default=None):
    """Return None instead of NaN."""
    try:
        return None if pd.isna(val) else val
    except Exception:
        return default

def fetch_price_at_date(
    ticker: str,
    date: "str | pd.Timestamp",
    prices_df: pd.DataFrame = None,
    market: str = "us",
    simfin_data_dir: str = "~/simfin_data",
    window_days: int = 5,
) -> dict:
    """
    Return the stock price closest to *date* (within *window_days* tolerance).

    This is used to align a metric snapshot (e.g. from an annual report dated
    2021-09-30) with the stock price at that same point in time — not today.

    Parameters
    ----------
    ticker         : e.g. "AAPL"
    date           : target date as a string "YYYY-MM-DD" or pd.Timestamp
    prices_df      : optional pre-loaded SimFin prices DataFrame (avoids
                     re-downloading when calling inside fetch_metrics)
    market         : SimFin market code, default "us"
    simfin_data_dir: local cache directory for SimFin data
    window_days    : how many calendar days either side to search if the exact
                     date has no trading data (e.g. weekend / holiday)

    Returns
    -------
    dict with keys:
        "date"          – actual date of the price record found
        "open"          – opening price
        "high"          – daily high
        "low"           – daily low
        "close"         – closing price  ← the primary value to use
        "adj_close"     – adjusted close (accounts for splits/dividends)
        "volume"        – trading volume
        "source"        – "simfin" or "yfinance" (fallback)
    Returns None for all price fields if no data is found.
    """

    ticker = ticker.upper()
    target = pd.Timestamp(date)

    # ── Try SimFin first ─────────────────────────────────────────────────────
    if prices_df is None:
        try:
            import simfin as sf
            sf.set_api_key(SIMFIN)
            sf.set_data_dir(os.path.expanduser(simfin_data_dir))
            prices_df = sf.load_shareprices(variant="daily", market=market)
        except Exception:
            prices_df = pd.DataFrame()

    px = pd.DataFrame()
    if not prices_df.empty and ticker in prices_df.index.get_level_values(0):
        px = prices_df.loc[ticker].copy()
        px.index = pd.to_datetime(px.index)
        px = px.sort_index()

    if not px.empty:
        # Find the nearest trading day within window_days
        lo = target - pd.Timedelta(days=window_days)
        hi = target + pd.Timedelta(days=window_days)
        candidates = px[(px.index >= lo) & (px.index <= hi)]

        if not candidates.empty:
            # Pick the row whose date is closest to target
            nearest_idx = (candidates.index - target).argmin()
            row = candidates.iloc[nearest_idx]
            actual_date = candidates.index[nearest_idx]

            close_col    = "Close"     if "Close"     in row.index else None
            adj_col      = "Adj. Close" if "Adj. Close" in row.index else close_col
            open_col     = "Open"      if "Open"      in row.index else None
            high_col     = "High"      if "High"      in row.index else None
            low_col      = "Low"       if "Low"       in row.index else None
            volume_col   = "Volume"    if "Volume"    in row.index else None

            return {
                "date":      actual_date.date(),
                "open":      _safe(row[open_col])   if open_col   else None,
                "high":      _safe(row[high_col])   if high_col   else None,
                "low":       _safe(row[low_col])    if low_col    else None,
                "close":     _safe(row[close_col])  if close_col  else None,
                "adj_close": _safe(row[adj_col])    if adj_col    else None,
                "volume":    _safe(row[volume_col]) if volume_col else None,
                "source":    "simfin",
            }
# ---------------------------------------------------------------------------
# Core fetcher
# ---------------------------------------------------------------------------

def fetch_metrics(
    ticker: str,
    market: str = "us",
    simfin_data_dir: str = "~/simfin_data",
) -> dict:
    """
    Fetch and compute financial metrics for *ticker*.

    Returns
    -------
    dict  keyed by the FEATURES names, values are floats / None.
    """

    ticker = ticker.upper()

    # ── 1. Load SimFin data ──────────────────────────────────────────────────
    prices_all, income_all, cashflow_all, balance_all = _load_simfin(
        market=market, data_dir=simfin_data_dir
    )

    inc  = _latest_row(income_all,   ticker)
    cf   = _latest_row(cashflow_all, ticker)
    bal  = _latest_row(balance_all,  ticker)

    # Latest daily price row
    if ticker in prices_all.index.get_level_values(0):
        px_df = prices_all.loc[ticker].sort_index()
        px_row = px_df.iloc[-1]
        close  = _safe(px_row.get("Close") or px_row.get("Adj. Close"))
        volume = _safe(px_row.get("Volume"))

        # 52-week window
        one_year_ago = px_df.index[-1] - pd.DateOffset(days=365)
        px_1y = px_df[px_df.index >= one_year_ago]["Close"].dropna()
        high_52  = _safe(px_1y.max())  if len(px_1y) else None
        low_52   = _safe(px_1y.min())  if len(px_1y) else None
        chg_52   = (
            (px_1y.iloc[-1] - px_1y.iloc[0]) / px_1y.iloc[0] * 100
            if len(px_1y) >= 2 else None
        )

        # Moving averages
        ma50  = _safe(px_df["Close"].rolling(50).mean().iloc[-1])  if len(px_df) >= 50  else None
        ma200 = _safe(px_df["Close"].rolling(200).mean().iloc[-1]) if len(px_df) >= 200 else None

        # Regular market change (1-day)
        reg_chg = (
            _safe(px_df["Close"].iloc[-1] - px_df["Close"].iloc[-2])
            if len(px_df) >= 2 else None
        )
    else:
        close = volume = high_52 = low_52 = chg_52 = ma50 = ma200 = reg_chg = None

    # ── 2. Income statement items ────────────────────────────────────────────
    revenue          = _safe(inc.get("Revenue"))
    gross_profit     = _safe(inc.get("Gross Profit"))
    operating_income = _safe(inc.get("Operating Income"))
    net_income       = _safe(inc.get("Net Income"))
    ebit             = _safe(inc.get("EBIT"))          # SimFin calls it EBIT
    # EBITDA approximation: EBIT + D&A (from cash flow)
    da               = _safe(cf.get("Depreciation & Amortization"))
    ebitda           = (ebit + da) if (ebit is not None and da is not None) else ebit

    # ── 3. Balance sheet items ───────────────────────────────────────────────
    total_assets      = _safe(bal.get("Total Assets"))
    total_equity      = _safe(bal.get("Total Equity"))
    total_debt        = _safe(
        bal.get("Long Term Debt") or bal.get("Total Debt")
    )
    current_assets    = _safe(bal.get("Total Current Assets"))
    current_liab      = _safe(bal.get("Total Current Liabilities"))
    cash              = _safe(bal.get("Cash, Cash Equivalents & Short Term Investments")
                              or bal.get("Cash & Cash Equivalents"))
    inventory         = _safe(bal.get("Inventories"))
    shares            = _safe(bal.get("Common Shares Outstanding")
                              or inc.get("Shares (Diluted)"))

    # ── 4. Cash flow items ───────────────────────────────────────────────────
    op_cf    = _safe(cf.get("Net Cash from Operating Activities"))
    capex    = _safe(cf.get("Capital Expenditures") or cf.get("Purchase of Fixed Assets"))
    free_cf  = (
        (op_cf + capex) if (op_cf is not None and capex is not None)
        else (op_cf - abs(capex) if op_cf is not None and capex is not None else None)
    )
    # Simpler free CF: operating - |capex|
    if op_cf is not None and capex is not None:
        free_cf = op_cf - abs(capex)

    # ── 5. Derived ratios ────────────────────────────────────────────────────
    def _ratio(num, den):
        try:
            return num / den if (den and den != 0) else None
        except Exception:
            return None

    market_cap    = (close * shares)            if (close and shares)          else None
    enterprise_v  = (
        market_cap + (total_debt or 0) - (cash or 0)
        if market_cap is not None else None
    )
    trailing_pe   = _ratio(close, _safe(inc.get("EPS (Diluted)")))
    price_book    = _ratio(close, _ratio(total_equity, shares))
    price_sales   = _ratio(market_cap, revenue)
    ev_ebitda     = _ratio(enterprise_v, ebitda)
    ev_revenue    = _ratio(enterprise_v, revenue)

    gross_margin  = _ratio(gross_profit, revenue)
    op_margin     = _ratio(operating_income, revenue)
    profit_margin = _ratio(net_income, revenue)
    ebitda_margin = _ratio(ebitda, revenue)

    roa           = _ratio(net_income, total_assets)
    roe           = _ratio(net_income, total_equity)
    debt_equity   = _ratio(total_debt, total_equity)
    current_ratio = _ratio(current_assets, current_liab)
    quick_ratio   = (
        _ratio((current_assets - inventory), current_liab)
        if (current_assets is not None and inventory is not None)
        else _ratio(current_assets, current_liab)
    )
    cash_per_share = _ratio(cash, shares)

    # Revenue growth: compare last two annual rows
    revenue_growth = None
    if ticker in income_all.index.get_level_values(0):
        rev_series = income_all.loc[ticker]["Revenue"].dropna().sort_index()
        if len(rev_series) >= 2:
            revenue_growth = _ratio(
                rev_series.iloc[-1] - rev_series.iloc[-2],
                abs(rev_series.iloc[-2])
            )

    # Earnings growth: same with net income
    earnings_growth = None
    if ticker in income_all.index.get_level_values(0):
        ni_series = income_all.loc[ticker]["Net Income"].dropna().sort_index()
        if len(ni_series) >= 2 and ni_series.iloc[-2] != 0:
            earnings_growth = _ratio(
                ni_series.iloc[-1] - ni_series.iloc[-2],
                abs(ni_series.iloc[-2])
            )

    # ── 6. yfinance fallback for items not in SimFin free tier ───────────────
    yf_info = {}
    try:
        yf_ticker = yf.Ticker(ticker)
        yf_info   = yf_ticker.info or {}
    except Exception:
        pass

    beta          = _safe(yf_info.get("beta"))
    forward_pe    = _safe(yf_info.get("forwardPE"))
    rec_mean      = _safe(yf_info.get("recommendationMean"))
    target_price  = _safe(yf_info.get("targetMeanPrice"))
    market_volume = _safe(yf_info.get("averageVolume"))   # 3-month avg volume

    # Override 52-week / MA from yfinance if SimFin had no price data
    if close is None:
        close       = _safe(yf_info.get("currentPrice") or yf_info.get("regularMarketPrice"))
        high_52     = _safe(yf_info.get("fiftyTwoWeekHigh"))
        low_52      = _safe(yf_info.get("fiftyTwoWeekLow"))
        chg_52      = _safe(yf_info.get("52WeekChange"))
        ma50        = _safe(yf_info.get("fiftyDayAverage"))
        ma200       = _safe(yf_info.get("twoHundredDayAverage"))
        reg_chg     = _safe(yf_info.get("regularMarketChange"))
        volume      = _safe(yf_info.get("regularMarketVolume"))
        market_cap  = _safe(yf_info.get("marketCap"))

    # ── 7. Assemble output dict ───────────────────────────────────────────────
    result = {
        "Regular Market Change":        reg_chg,
        "52 Week High":                  high_52,
        "52 Week Low":                   low_52,
        "52 Week Change Percent":        chg_52,
        "50 Day Average":                ma50,
        "200 Day Average":               ma200,
        "Volume":                        volume,
        "Market Volume":                 market_volume,
        "Beta":                          beta,
        "Market Cap":                    market_cap,
        "Forward PE":                    forward_pe,
        "Trailing PE":                   trailing_pe,
        "Price to Book":                 price_book,
        "Price To Sales 12 Months":      price_sales,
        "Enterprise Value":              enterprise_v,
        "Enterprise To EBITA":           ev_ebitda,
        "Enterprise To Revenue":         ev_revenue,
        "Gross Margins":                 gross_margin,
        "Profit Margins":                profit_margin,
        "Operating Margins":             op_margin,
        "EBITA Margins":                 ebitda_margin,
        "Return on Assets":              roa,
        "Return on Equity":              roe,
        "Net Income to Common":          net_income,
        "EBITA":                         ebitda,
        "Earnings Growth":               earnings_growth,
        "Total Debt":                    total_debt,
        "Debt to Equity":                debt_equity,
        "Total Cash":                    cash,
        "Free Cashflow":                 free_cf,
        "Operating Cashflow":            op_cf,
        "Current Ratio":                 current_ratio,
        "Quick Ratio":                   quick_ratio,
        "Revenue Growth":                revenue_growth,
        "Total Cash Per Share":          cash_per_share,
        "Recommendation Mean":           rec_mean,
        "Target Mean Price":             target_price,
    }

    return result


# ---------------------------------------------------------------------------
# Optional: pretty-print helper
# ---------------------------------------------------------------------------

def print_metrics(ticker: str, **kwargs):
    data = fetch_metrics(ticker, **kwargs)
    max_key = max(len(k) for k in data)
    print(f"\n{'=' * (max_key + 25)}")
    print(f"  Metrics for {ticker}")
    print(f"{'=' * (max_key + 25)}")
    for k, v in data.items():
        if v is None:
            display = "N/A"
        elif isinstance(v, float):
            display = f"{v:,.4f}"
        else:
            display = str(v)
        print(f"  {k:<{max_key}}  {display}")
    print()


async def simulation(ticker):
    old_data = fetch_metrics(ticker)
    model = load_model(r"scripts\model\XGboost_model.joblib")
    old_data = pd.DataFrame(old_data,index=[0])
    old_stock_data = old_data.dropna(axis=1)
    processed_stock_data = prepare_data(old_stock_data)
    old_stock_prediction = (model.predict(processed_stock_data))[0]

    old_price = fetch_price_at_date(ticker, "2025-02-23")
    current_price = get_stock_price(ticker)
    current_price_prediction = await price_prediction(ticker,model)
    
    print(f"Old price prediction: {old_stock_prediction}")
    print(f"Old price: {old_price['open']}")
    print(f"current price: {current_price}")
    print(f"current price prediction: {current_price_prediction}")
    

asyncio.run(simulation("NVDA"))
print("Hellop")