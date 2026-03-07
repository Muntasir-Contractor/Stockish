import yfinance as yf
import numpy as np


# ── Constants ─────────────────────────────────────────────────────────────────

RISK_FREE_RATE      = 0.0396
EQUITY_RISK_PREMIUM = 0.0438
MAX_WACC            = 0.15
MAX_TAX_RATE        = 0.40
MIN_TAX_RATE        = 0.0
MAX_GROWTH_RATE     = 0.60
MIN_GROWTH_RATE     = -0.10
FCF_SANITY_LIMIT    = 5e12   # warn if any projected FCF exceeds $5T



def cost_of_equity(beta: float) -> float:
    """CAPM: risk-free rate + beta * equity risk premium."""
    return RISK_FREE_RATE + (beta * EQUITY_RISK_PREMIUM)


def WACC(mc: float, td: float, coe: float, cod: float, tr: float) -> float:
    """
    Weighted Average Cost of Capital.
    If there is no debt, WACC simply equals the cost of equity.
    """
    if td == 0:
        return coe
    v = mc + td
    return ((mc / v) * coe) + ((td / v) * cod * (1 - tr))


def TV_perpetuity(fcf: float, g: float, wacc: float) -> float:
    """Gordon Growth Model terminal value."""
    if wacc <= g:
        raise ValueError(f"WACC ({wacc:.2%}) must be greater than growth rate ({g:.2%})")
    return (fcf * (1 + g)) / (wacc - g)


def TV_exitMultiple(metric: float, multiple: float) -> float:
    """Exit-multiple terminal value (e.g. EV/EBITDA)."""
    return metric * multiple


def estimate_growth_rate(tk: yf.Ticker) -> tuple[float, bool]:
    """
    Estimate near-term FCF growth using 3-year historical FCF CAGR.
    Returns (growth_rate, used_fallback).
    Capped between MIN_GROWTH_RATE and MAX_GROWTH_RATE.
    """
    try:
        cf = tk.cashflow
        fcf_row = cf.loc["Free Cash Flow"]
        fcf_values = fcf_row.dropna().values  # most recent first
        if len(fcf_values) >= 2:
            latest, oldest = fcf_values[0], fcf_values[-1]
            n = len(fcf_values) - 1
            if oldest > 0 and latest > 0:
                cagr = (latest / oldest) ** (1 / n) - 1
                return float(np.clip(cagr, MIN_GROWTH_RATE, MAX_GROWTH_RATE)), False
    except Exception:
        pass
    return 0.05, True   # fallback — flag it


def project_fcfs_with_fade(
    base_fcf: float,
    g_near: float,
    g_terminal: float,
    n_years: int,
) -> list[float]:
    """
    Project FCFs while linearly fading growth from g_near to g_terminal.
    Warns if any projected FCF exceeds FCF_SANITY_LIMIT.
    """
    fcfs = []
    fcf = base_fcf
    for yr in range(1, n_years + 1):
        weight = (yr - 1) / (n_years - 1) if n_years > 1 else 1.0
        g = g_near + weight * (g_terminal - g_near)
        fcf = fcf * (1 + g)
        if abs(fcf) > FCF_SANITY_LIMIT:
            print(f"  [WARNING] Year {yr} projected FCF ${fcf:,.0f} exceeds sanity limit — "
                  f"growth rate may be unrealistic.")
        fcfs.append(fcf)
    return fcfs


def discount_cashflows(cashflows: list[float], discount_rate: float) -> list[float]:
    """Discount a series of future cash flows back to present value."""
    return [cf / (1 + discount_rate) ** (i + 1) for i, cf in enumerate(cashflows)]


def intrinsic_value_per_share(
    pv_fcfs: float,
    terminal_value: float,
    wacc: float,
    n_years: int,
    total_debt: float,
    cash: float,
    shares_outstanding: int,
) -> float:
    """
    Equity value per share from enterprise value.

    Enterprise Value = PV(FCFs) + PV(Terminal Value)
    Equity Value     = EV - Net Debt
    Price per Share  = Equity Value / Shares Outstanding
    """
    pv_tv = terminal_value / (1 + wacc) ** n_years
    enterprise_value = pv_fcfs + pv_tv
    net_debt = total_debt - cash
    equity_value = enterprise_value - net_debt
    if shares_outstanding <= 0:
        return np.nan
    return equity_value / shares_outstanding


# ── Main DCF function ─────────────────────────────────────────────────────────

def discounted_cashflow_analysis(
    ticker_symbol: str,
    n_years: int = 5,
    terminal_growth_rate: float = 0.025,
    method: str = "perpetuity",      # "perpetuity" | "exit_multiple"
    exit_multiple: float = 15.0,
) -> dict | None:
    """
    Full DCF analysis for a publicly traded company.

    Parameters
    ----------
    ticker_symbol        : e.g. "AAPL"
    n_years              : projection horizon (default 5)
    terminal_growth_rate : perpetuity growth rate for terminal value
    method               : terminal-value method ("perpetuity" or "exit_multiple")
    exit_multiple        : EV / FCF multiple (only for exit_multiple method)

    Returns
    -------
    dict with DCF results, or None if required data is unavailable.
    """
    tk = yf.Ticker(ticker_symbol)
    info = tk.info

    # ── Pull raw data ──────────────────────────────────────────────────────────
    try:
        bs   = tk.balancesheet.iloc[:, 0]
        fins = tk.financials.iloc[:, 0]
    except Exception:
        print(f"[{ticker_symbol}] Could not retrieve financial statements.")
        return None

    free_cash_flow = info.get("freeCashflow")
    beta           = info.get("beta")
    market_cap     = info.get("marketCap")
    total_debt     = info.get("totalDebt", 0) or 0
    shares_out     = info.get("sharesOutstanding", 0) or 0
    current_price  = info.get("currentPrice") or info.get("regularMarketPrice")
    cash           = info.get("totalCash") or info.get("cash", 0) or 0

    # ── Validate required inputs ───────────────────────────────────────────────
    missing = []
    if free_cash_flow is None: missing.append("freeCashflow")
    if beta is None:           missing.append("beta")
    if market_cap is None:     missing.append("marketCap")
    if beta == np.inf:         missing.append("beta=inf")

    if missing:
        print(f"[{ticker_symbol}] Missing or invalid data: {missing}")
        return None

    # ── Cost of capital ────────────────────────────────────────────────────────
    # Tax rate — clamp between 0% and 40% to handle benefit years
    try:
        raw_tax_rate = fins["Tax Provision"] / fins["Pretax Income"]
        tax_rate = float(np.clip(raw_tax_rate, MIN_TAX_RATE, MAX_TAX_RATE))
        if raw_tax_rate != tax_rate:
            print(f"  [WARNING] Tax rate {float(raw_tax_rate):.2%} clamped to {tax_rate:.2%}")
    except (KeyError, ZeroDivisionError):
        tax_rate = 0.21
        print(f"  [WARNING] Could not compute tax rate for {ticker_symbol}, using 21% fallback")

    # Cost of debt — default to 0 if no debt (avoids nan for debt-free companies)
    try:
        if total_debt > 0:
            bs_debt = bs.get("Total Debt", 0)
            cod = abs(fins["Interest Expense"]) / bs_debt if bs_debt else 0.04
        else:
            cod = 0.0
    except (KeyError, ZeroDivisionError):
        cod = 0.04 if total_debt > 0 else 0.0
        print(f"  [WARNING] Could not compute COD for {ticker_symbol}, using fallback")

    coe  = cost_of_equity(beta)
    wacc = WACC(market_cap, total_debt, coe, cod, tax_rate)

    # Cap WACC to avoid extreme discounting from high-beta stocks
    if wacc > MAX_WACC:
        print(f"  [WARNING] WACC {wacc:.2%} capped at {MAX_WACC:.2%} for {ticker_symbol}")
        wacc = MAX_WACC

    # ── Growth rate estimate ───────────────────────────────────────────────────
    g_near, used_fallback = estimate_growth_rate(tk)
    if used_fallback:
        print(f"  [WARNING] Could not compute FCF CAGR for {ticker_symbol}, using 5% fallback")

    # ── Project & discount FCFs ────────────────────────────────────────────────
    projected_fcfs  = project_fcfs_with_fade(free_cash_flow, g_near, terminal_growth_rate, n_years)
    discounted_fcfs = discount_cashflows(projected_fcfs, wacc)
    pv_sum_fcfs     = sum(discounted_fcfs)

    # ── Terminal value ─────────────────────────────────────────────────────────
    terminal_fcf = projected_fcfs[-1]

    if method == "exit_multiple":
        tv = TV_exitMultiple(terminal_fcf, exit_multiple)
    else:
        tv = TV_perpetuity(terminal_fcf, terminal_growth_rate, wacc)

    tv_perp = TV_perpetuity(terminal_fcf, terminal_growth_rate, wacc)

    # ── Intrinsic value per share ──────────────────────────────────────────────
    price_target = intrinsic_value_per_share(
        pv_sum_fcfs, tv, wacc, n_years, total_debt, cash, shares_out
    )

    upside = ((price_target / current_price) - 1) if (current_price and price_target) else None

    # ── Assemble results ───────────────────────────────────────────────────────
    results = {
        "ticker":                ticker_symbol.upper(),
        "current_price":         round(current_price, 2) if current_price else None,
        "intrinsic_value":       round(float(price_target), 2) if price_target else None,
        "upside_downside_pct":   round(float(upside) * 100, 1) if upside is not None else None,
        "wacc":                  round(float(wacc) * 100, 2),
        "coe":                   round(coe * 100, 2),
        "cod":                   round(float(cod) * 100, 2),
        "tax_rate":              round(float(tax_rate) * 100, 2),
        "beta":                  round(beta, 2),
        "near_term_growth":      round(g_near * 100, 2),
        "used_growth_fallback":  used_fallback,
        "terminal_growth":       round(terminal_growth_rate * 100, 2),
        "terminal_value_method": method,
        "base_fcf":              free_cash_flow,
        "projected_fcfs":        [round(f, 0) for f in projected_fcfs],
        "discounted_fcfs":       [round(f, 0) for f in discounted_fcfs],
        "pv_sum_fcfs":           round(pv_sum_fcfs, 0),
        "terminal_value":        round(float(tv), 0),
        "tv_perpetuity_ref":     round(float(tv_perp), 0),
        "enterprise_value":      round(pv_sum_fcfs + float(tv) / (1 + wacc) ** n_years, 0),
    }

    # ── Pretty print ───────────────────────────────────────────────────────────
    fallback_flag = " ⚠ fallback" if used_fallback else ""
    print(f"\n{'='*55}")
    print(f"  DCF Analysis — {results['ticker']}")
    print(f"{'='*55}")
    print(f"  Current Price       : ${results['current_price']}")
    print(f"  Intrinsic Value     : ${results['intrinsic_value']}")
    upside_str = f"{results['upside_downside_pct']:+.1f}%" if results['upside_downside_pct'] is not None else "N/A"
    print(f"  Upside / Downside   : {upside_str}")
    print(f"{'-'*55}")
    print(f"  WACC                : {results['wacc']}%")
    print(f"  Cost of Equity      : {results['coe']}%")
    print(f"  Cost of Debt        : {results['cod']}%")
    print(f"  Tax Rate            : {results['tax_rate']}%")
    print(f"  Beta                : {results['beta']}")
    print(f"{'-'*55}")
    print(f"  Near-term FCF Growth: {results['near_term_growth']}%{fallback_flag}")
    print(f"  Terminal Growth     : {results['terminal_growth']}%")
    print(f"  TV Method           : {results['terminal_value_method']}")
    print(f"{'-'*55}")
    print(f"  Base FCF            : ${free_cash_flow:,.0f}")
    for i, (proj, disc) in enumerate(zip(results['projected_fcfs'], results['discounted_fcfs']), 1):
        print(f"  Year {i} FCF (PV)    : ${proj:>14,.0f}  →  ${disc:>14,.0f}")
    print(f"  PV of FCFs          : ${results['pv_sum_fcfs']:>14,.0f}")
    print(f"  Terminal Value      : ${results['terminal_value']:>14,.0f}")
    print(f"  Enterprise Value    : ${results['enterprise_value']:>14,.0f}")
    print(f"{'='*55}\n")

    return results


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    tickers = ["NVDA", "TSLA", "AMD", "MSFT", "COKE", "CVX", "PLTR", "AMZN", "GOOGL"]
    results = {}
    for t in tickers:
        r = discounted_cashflow_analysis(t)
        if r:
            results[t] = r
            print(f"{t}: Current Price: {r['current_price']}, "
                  f"Intrinsic Value: {r['intrinsic_value']}")