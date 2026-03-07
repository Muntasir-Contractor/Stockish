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


def _is_valid_float(x) -> bool:
    """Return True if x is a finite, non-NaN number."""
    try:
        return x is not None and np.isfinite(float(x))
    except (TypeError, ValueError):
        return False


def cost_of_equity(
    beta: float,
    risk_free_rate: float = RISK_FREE_RATE,
    equity_risk_premium: float = EQUITY_RISK_PREMIUM,
) -> float:
    """CAPM: risk-free rate + beta * equity risk premium."""
    return risk_free_rate + (beta * equity_risk_premium)


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
    Estimate near-term FCF growth using historical FCF CAGR.
    Returns (growth_rate, used_fallback).
    Capped between MIN_GROWTH_RATE and MAX_GROWTH_RATE.

    Fallback hierarchy (best → worst):
      1. Full-period CAGR — both endpoint years are positive.
      2. Positive-years-only CAGR — skips negative trough years and computes
         CAGR between the most-recent and oldest positive year. Handles
         companies like AMZN that had a loss period mid-history.
      3. All FCFs negative → 0% (flat cash burn assumption).
      4. Only one positive year or exception → 5%.
    """
    try:
        cf = tk.cashflow
        fcf_row = cf.loc["Free Cash Flow"]
        fcf_values = fcf_row.dropna().values  # most recent first

        if len(fcf_values) >= 2:
            latest, oldest = fcf_values[0], fcf_values[-1]
            n = len(fcf_values) - 1

            # Tier 1: full-period CAGR (both endpoints positive)
            if oldest > 0 and latest > 0:
                cagr = (latest / oldest) ** (1 / n) - 1
                return float(np.clip(cagr, MIN_GROWTH_RATE, MAX_GROWTH_RATE)), False

            # Tier 2: CAGR across only the positive-FCF years (skip negative trough)
            positives = [(i, v) for i, v in enumerate(fcf_values) if v > 0]
            if len(positives) >= 2:
                i_rec, v_rec = positives[0]   # most recent positive year
                i_old, v_old = positives[-1]  # oldest positive year
                n_pos = i_old - i_rec
                if n_pos > 0:
                    cagr = (v_rec / v_old) ** (1 / n_pos) - 1
                    return float(np.clip(cagr, MIN_GROWTH_RATE, MAX_GROWTH_RATE)), False

            # Tier 3: all negative — flat cash burn
            if all(v <= 0 for v in fcf_values):
                print("  [WARNING] All historical FCFs are negative; using 0% fallback growth.")
                return 0.0, True

            # Tier 4: only one positive year, no trend computable
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

    weight=0 in year 1  → uses g_near
    weight=1 in year N  → uses g_terminal
    For n_years=1 weight is forced to 0 so the single year uses g_near.

    Warns if any projected FCF exceeds FCF_SANITY_LIMIT.
    """
    fcfs = []
    fcf = base_fcf
    for yr in range(1, n_years + 1):
        # FIX: use 0.0 (g_near) when n_years=1 instead of 1.0 (g_terminal)
        weight = (yr - 1) / (n_years - 1) if n_years > 1 else 0.0
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
    risk_free_rate: float = RISK_FREE_RATE,
    equity_risk_premium: float = EQUITY_RISK_PREMIUM,
) -> dict | None:
    """
    Full DCF analysis for a publicly traded company.

    Parameters
    ----------
    ticker_symbol        : e.g. "AAPL"
    n_years              : projection horizon (default 5); must be >= 1
    terminal_growth_rate : perpetuity growth rate for terminal value
    method               : terminal-value method ("perpetuity" or "exit_multiple")
    exit_multiple        : EV / FCF multiple (only for exit_multiple method)
    risk_free_rate       : override default risk-free rate (default 3.96%)
    equity_risk_premium  : override default ERP (default 4.38%)

    Returns
    -------
    dict with DCF results, or None if required data is unavailable.
    """
    # ── Input validation ───────────────────────────────────────────────────────
    if n_years < 1:
        print(f"[{ticker_symbol}] n_years must be >= 1 (got {n_years}).")
        return None

    tk = yf.Ticker(ticker_symbol)
    info = tk.info

    # ── Pull raw data ──────────────────────────────────────────────────────────
    try:
        bs   = tk.balancesheet.iloc[:, 0]
        fins = tk.financials.iloc[:, 0]
    except Exception:
        print(f"[{ticker_symbol}] Could not retrieve financial statements.")
        return None

    # TTM FCF from info is the most current 12-month figure.
    # Falls back to the most recent annual from the cashflow statement if unavailable.
    free_cash_flow = info.get("freeCashflow")
    if free_cash_flow is None:
        try:
            _cf_stmt = tk.cashflow
            if "Free Cash Flow" in _cf_stmt.index:
                _fcf_series = _cf_stmt.loc["Free Cash Flow"].dropna()
                if len(_fcf_series) > 0:
                    free_cash_flow = float(_fcf_series.iloc[0])
        except Exception:
            pass

    beta           = info.get("beta")
    market_cap     = info.get("marketCap")
    total_debt     = info.get("totalDebt", 0) or 0
    shares_out     = info.get("sharesOutstanding", 0) or 0
    current_price  = info.get("currentPrice") or info.get("regularMarketPrice")
    cash           = info.get("totalCash") or info.get("cash", 0) or 0

    # ── Validate required inputs ───────────────────────────────────────────────
    missing = []
    if free_cash_flow is None:                        missing.append("freeCashflow")
    if beta is None:                                  missing.append("beta")
    if market_cap is None:                            missing.append("marketCap")
    if current_price is None:                         missing.append("currentPrice")
    if beta is not None and not np.isfinite(beta):    missing.append("beta=non-finite")

    if missing:
        print(f"[{ticker_symbol}] Missing or invalid data: {missing}")
        return None

    # ── Warn about unusual beta ────────────────────────────────────────────────
    if beta < 0:
        print(f"  [WARNING] Beta is negative ({beta:.2f}) for {ticker_symbol}. "
              f"Cost of equity will be below the risk-free rate.")

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
            bs_debt = float(bs.get("Total Debt", 0) or 0)
            interest_raw = fins.get("Interest Expense", None)
            if _is_valid_float(interest_raw) and bs_debt > 0:
                cod = abs(float(interest_raw)) / bs_debt
            else:
                cod = 0.04
                print(f"  [WARNING] Could not compute COD for {ticker_symbol} "
                      f"(missing/NaN interest expense), using 4% fallback")
        else:
            cod = 0.0
    except (KeyError, ZeroDivisionError, TypeError):
        cod = 0.04 if total_debt > 0 else 0.0
        print(f"  [WARNING] Could not compute COD for {ticker_symbol}, using fallback")

    # Blume (2/3, 1/3) beta adjustment: mean-reverts extreme betas toward market average.
    # Industry standard (Bloomberg). Reduces the discount-rate penalty for high-beta growth stocks.
    adjusted_beta = (2 / 3) * beta + (1 / 3)

    coe  = cost_of_equity(adjusted_beta, risk_free_rate, equity_risk_premium)
    wacc = WACC(market_cap, total_debt, coe, cod, tax_rate)

    # Cap WACC to avoid extreme discounting from high-beta stocks
    if wacc > MAX_WACC:
        print(f"  [WARNING] WACC {wacc:.2%} capped at {MAX_WACC:.2%} for {ticker_symbol}. "
              f"Intrinsic value will be overstated — treat result with caution.")
        wacc = MAX_WACC

    # ── Growth rate estimate ───────────────────────────────────────────────────
    g_near, used_fallback = estimate_growth_rate(tk)
    if used_fallback:
        print(f"  [WARNING] Could not compute FCF CAGR for {ticker_symbol}, using fallback")

    # Warn if negative base FCF is paired with positive growth (projections diverge negatively)
    if free_cash_flow < 0 and g_near > 0:
        print(f"  [WARNING] Base FCF is negative (${free_cash_flow:,.0f}) with positive "
              f"near-term growth ({g_near:.1%}). Projections will become increasingly negative.")

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

    # Perpetuity reference value — only computed for exit_multiple path,
    # and only when the WACC > terminal growth constraint is satisfied.
    tv_perp: float | None = None
    if method == "exit_multiple":
        try:
            tv_perp = TV_perpetuity(terminal_fcf, terminal_growth_rate, wacc)
        except ValueError:
            pass  # WACC ≤ terminal growth; reference unavailable
    else:
        tv_perp = tv

    # ── Intrinsic value per share ──────────────────────────────────────────────
    price_target = intrinsic_value_per_share(
        pv_sum_fcfs, tv, wacc, n_years, total_debt, cash, shares_out
    )

    # Use explicit finite check — avoids Python falsy issues with 0.0, negatives, and np.nan
    price_is_valid = _is_valid_float(price_target)
    upside = ((price_target / current_price) - 1) if price_is_valid else None

    # ── Assemble results ───────────────────────────────────────────────────────
    results = {
        "ticker":                ticker_symbol.upper(),
        "current_price":         round(current_price, 2),
        "intrinsic_value":       round(float(price_target), 2) if price_is_valid else None,
        "upside_downside_pct":   round(float(upside) * 100, 1) if upside is not None else None,
        "wacc":                  round(float(wacc) * 100, 2),
        "coe":                   round(coe * 100, 2),
        "cod":                   round(float(cod) * 100, 2),
        "tax_rate":              round(float(tax_rate) * 100, 2),
        "beta":                  round(beta, 2),
        "adjusted_beta":         round(adjusted_beta, 2),
        "near_term_growth":      round(g_near * 100, 2),
        "used_growth_fallback":  used_fallback,
        "terminal_growth":       round(terminal_growth_rate * 100, 2),
        "terminal_value_method": method,
        "base_fcf":              free_cash_flow,
        "projected_fcfs":        [round(f, 0) for f in projected_fcfs],
        "discounted_fcfs":       [round(f, 0) for f in discounted_fcfs],
        "pv_sum_fcfs":           round(pv_sum_fcfs, 0),
        "terminal_value":        round(float(tv), 0),
        "tv_perpetuity_ref":     round(float(tv_perp), 0) if _is_valid_float(tv_perp) else None,
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
    print(f"  Beta (raw/adj)      : {results['beta']} → {results['adjusted_beta']} (Blume)")
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
    tickers = ["TD","NVDA", "TSLA", "AMD", "MSFT", "COKE", "CVX", "PLTR", "AMZN", "GOOGL"]
    results = {}
    for t in tickers:
        r = discounted_cashflow_analysis(t)
        if r:
            results[t] = r
            print(f"{t}: Current Price: {r['current_price']}, "
                  f"Intrinsic Value: {r['intrinsic_value']}")
