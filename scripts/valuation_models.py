import yfinance as yf
import numpy as np


# ── Constants ─────────────────────────────────────────────────────────────────

RISK_FREE_RATE      = 0.0396
EQUITY_RISK_PREMIUM = 0.0438
MAX_WACC            = 0.15
MIN_WACC            = 0.05
MIN_WACC_GROWTH_SPREAD = 0.02  # floor for Gordon Growth denominator (WACC - g)
MAX_TAX_RATE        = 0.40
MIN_TAX_RATE        = 0.0
MAX_GROWTH_RATE     = 0.30
MIN_GROWTH_RATE     = -0.10
FCF_SANITY_LIMIT    = 5e12   # warn if any projected FCF exceeds $5T

# ── Sector Median Multiples ──────────────────────────────────────────────────

SECTOR_MEDIANS = {
    "Technology":             {"pe": 28.0, "ps": 6.0, "pb": 7.0, "ev_ebitda": 20.0},
    "Communication Services": {"pe": 18.0, "ps": 3.0, "pb": 3.0, "ev_ebitda": 12.0},
    "Consumer Cyclical":      {"pe": 20.0, "ps": 1.5, "pb": 4.0, "ev_ebitda": 14.0},
    "Consumer Defensive":     {"pe": 22.0, "ps": 2.0, "pb": 4.5, "ev_ebitda": 15.0},
    "Energy":                 {"pe": 12.0, "ps": 1.2, "pb": 1.8, "ev_ebitda": 6.0},
    "Financial Services":     {"pe": 13.0, "ps": 3.0, "pb": 1.3, "ev_ebitda": 10.0},
    "Healthcare":             {"pe": 22.0, "ps": 4.0, "pb": 4.0, "ev_ebitda": 16.0},
    "Industrials":            {"pe": 20.0, "ps": 2.0, "pb": 4.0, "ev_ebitda": 13.0},
    "Basic Materials":        {"pe": 14.0, "ps": 1.5, "pb": 2.0, "ev_ebitda": 8.0},
    "Real Estate":            {"pe": 35.0, "ps": 6.0, "pb": 1.8, "ev_ebitda": 18.0},
    "Utilities":              {"pe": 18.0, "ps": 2.5, "pb": 1.8, "ev_ebitda": 12.0},
}
DEFAULT_MEDIANS = {"pe": 18.0, "ps": 2.5, "pb": 3.0, "ev_ebitda": 12.0}


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
    """Gordon Growth Model terminal value with minimum spread guardrail."""
    if fcf < 0:
        print(f"  [WARNING] Terminal FCF is negative (${fcf:,.0f}). "
              f"Terminal value capped at 0 (not projecting perpetual losses).")
        return 0.0
    spread = wacc - g
    if spread < MIN_WACC_GROWTH_SPREAD:
        print(f"  [WARNING] WACC-growth spread ({spread:.2%}) floored at "
              f"{MIN_WACC_GROWTH_SPREAD:.2%}. Terminal value is capped.")
        spread = MIN_WACC_GROWTH_SPREAD
    return (fcf * (1 + g)) / spread


def TV_exitMultiple(metric: float, multiple: float) -> float:
    """Exit-multiple terminal value (e.g. EV/EBITDA)."""
    return metric * multiple


def _ocf_cagr(tk: yf.Ticker) -> float | None:
    """
    Operating Cash Flow CAGR — used as a fallback when FCF is distorted
    by lumpy capex (e.g. AMZN, GOOG during heavy infrastructure investment).
    Returns None if insufficient data.
    """
    try:
        cf = tk.cashflow
        if "Operating Cash Flow" not in cf.index:
            return None
        ocf_values = cf.loc["Operating Cash Flow"].dropna().values
        if len(ocf_values) >= 2:
            latest, oldest = ocf_values[0], ocf_values[-1]
            if latest > 0 and oldest > 0:
                n = len(ocf_values) - 1
                return float((latest / oldest) ** (1 / n) - 1)
    except Exception:
        pass
    return None


def estimate_growth_rate(tk: yf.Ticker) -> tuple[float, bool]:
    """
    Estimate near-term FCF growth using historical CAGR.
    Returns (growth_rate, used_fallback).
    Capped between MIN_GROWTH_RATE and MAX_GROWTH_RATE.

    Fallback hierarchy (best -> worst):
      1. Full-period FCF CAGR — both endpoint years are positive.
      2. Positive-years-only FCF CAGR — skips negative trough years.
      3. Operating Cash Flow CAGR — when FCF CAGR is negative but OCF is
         growing, capex is distorting FCF. Uses OCF growth as proxy.
      4. All FCFs negative -> 0% (flat cash burn assumption).
      5. Only one positive year or exception -> 5%.
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
                # Tier 1b: if FCF CAGR is negative, check if OCF tells a better story
                if cagr < 0:
                    ocf_growth = _ocf_cagr(tk)
                    if ocf_growth is not None and ocf_growth > 0:
                        print(f"  [INFO] FCF CAGR ({cagr:.1%}) is negative but OCF CAGR "
                              f"({ocf_growth:.1%}) is positive — capex likely distorting FCF. "
                              f"Using OCF growth as proxy.")
                        return float(np.clip(ocf_growth, MIN_GROWTH_RATE, MAX_GROWTH_RATE)), False
                return float(np.clip(cagr, MIN_GROWTH_RATE, MAX_GROWTH_RATE)), False

            # Tier 2: CAGR across only the positive-FCF years (skip negative trough)
            positives = [(i, v) for i, v in enumerate(fcf_values) if v > 0]
            if len(positives) >= 2:
                i_rec, v_rec = positives[0]   # most recent positive year
                i_old, v_old = positives[-1]  # oldest positive year
                n_pos = i_old - i_rec
                if n_pos > 0:
                    cagr = (v_rec / v_old) ** (1 / n_pos) - 1
                    if cagr < 0:
                        ocf_growth = _ocf_cagr(tk)
                        if ocf_growth is not None and ocf_growth > 0:
                            print(f"  [INFO] FCF CAGR ({cagr:.1%}) is negative but OCF CAGR "
                                  f"({ocf_growth:.1%}) is positive — using OCF growth as proxy.")
                            return float(np.clip(ocf_growth, MIN_GROWTH_RATE, MAX_GROWTH_RATE)), False
                    return float(np.clip(cagr, MIN_GROWTH_RATE, MAX_GROWTH_RATE)), False

            # Tier 3: OCF fallback when no usable FCF CAGR at all
            ocf_growth = _ocf_cagr(tk)
            if ocf_growth is not None and ocf_growth > 0:
                print(f"  [INFO] No usable FCF CAGR — falling back to OCF CAGR ({ocf_growth:.1%}).")
                return float(np.clip(ocf_growth, MIN_GROWTH_RATE, MAX_GROWTH_RATE)), False

            # Tier 4: all negative — flat cash burn
            if all(v <= 0 for v in fcf_values):
                print("  [WARNING] All historical FCFs are negative; using 0% fallback growth.")
                return 0.0, True

            # Tier 5: only one positive year, no trend computable
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

    weight=0 in year 1  -> uses g_near
    weight=1 in year N  -> uses g_terminal
    For n_years=1 weight is forced to 0 so the single year uses g_near.

    Warns if any projected FCF exceeds FCF_SANITY_LIMIT.
    """
    fcfs = []
    fcf = base_fcf
    for yr in range(1, n_years + 1):
        if n_years > 1:
            t = (yr - 1) / (n_years - 1)        # 0..1
            weight = 1 - np.exp(-3 * t)          # exponential decay: ~0 at yr1, ~0.95 at yr5
        else:
            weight = 0.0
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


def _assess_dcf_confidence(
    intrinsic_value: float,
    current_price: float,
    pv_tv: float,
    enterprise_value: float,
    net_debt: float,
    base_fcf: float,
    used_fallback: bool,
) -> tuple[str, list[str]]:
    """
    Assess confidence in DCF result.
    Returns (level, [warnings]) where level is "high", "medium", or "low".
    """
    warnings = []

    if not _is_valid_float(intrinsic_value) or current_price <= 0:
        return "low", ["Invalid intrinsic value or price"]

    ratio = intrinsic_value / current_price
    if ratio > 10.0 or ratio < 0.1:
        warnings.append(f"Intrinsic value is {ratio:.1f}x current price (extreme)")
    elif ratio > 5.0 or ratio < 0.2:
        warnings.append(f"Intrinsic value is {ratio:.1f}x current price")

    if enterprise_value != 0:
        tv_pct = abs(pv_tv) / abs(enterprise_value)
        if tv_pct > 0.90:
            warnings.append(f"Terminal value is {tv_pct:.0%} of enterprise value")

    if enterprise_value > 0 and net_debt > 0.5 * enterprise_value:
        warnings.append(f"Net debt is {net_debt / enterprise_value:.0%} of EV")

    if base_fcf < 0:
        warnings.append("Base FCF is negative")

    if used_fallback:
        warnings.append("Used fallback growth rate")

    extreme = any("extreme" in w for w in warnings)
    if len(warnings) >= 3 or extreme:
        level = "low"
    elif len(warnings) >= 1:
        level = "medium"
    else:
        level = "high"

    return level, warnings


# ── Shared helpers for multi-model valuation ─────────────────────────────────

def _get_ticker_data(ticker: str):
    """Single yfinance call shared across models. Returns (tk, info)."""
    tk = yf.Ticker(ticker)
    info = tk.info
    return tk, info


def _get_sector_medians(info: dict) -> dict:
    """Lookup sector medians with fallback to DEFAULT_MEDIANS."""
    sector = info.get("sector", "")
    return SECTOR_MEDIANS.get(sector, DEFAULT_MEDIANS)


# ── P/E Comparable Valuation ─────────────────────────────────────────────────

def pe_valuation(ticker: str, tk=None, info=None, custom_overrides: dict | None = None) -> dict | None:
    """Fair value = sector_median_pe * trailing_eps."""
    if tk is None or info is None:
        tk, info = _get_ticker_data(ticker)

    trailing_eps = info.get("trailingEps")
    current_price = info.get("currentPrice") or info.get("regularMarketPrice")

    if not _is_valid_float(trailing_eps) or trailing_eps <= 0 or not _is_valid_float(current_price):
        return None

    medians = _get_sector_medians(info)
    pe_multiple = medians["pe"]
    if custom_overrides and "sector_pe" in custom_overrides:
        pe_multiple = float(custom_overrides["sector_pe"])
    fair_value = pe_multiple * trailing_eps

    upside = ((fair_value / current_price) - 1) * 100

    # Confidence assessment
    warnings = []
    forward_pe = info.get("forwardPE")
    trailing_pe = info.get("trailingPE")

    if _is_valid_float(forward_pe) and _is_valid_float(trailing_pe) and trailing_pe > 0:
        pe_divergence = abs(forward_pe - trailing_pe) / trailing_pe
        if pe_divergence > 0.3:
            warnings.append(f"Forward P/E diverges {pe_divergence:.0%} from trailing")

    ratio = fair_value / current_price
    if ratio > 5.0 or ratio < 0.2:
        warnings.append(f"Fair value is {ratio:.1f}x current price")

    if len(warnings) >= 2:
        confidence = "low"
    elif len(warnings) == 1:
        confidence = "medium"
    else:
        confidence = "high"

    return {
        "model_type": "pe_comparable",
        "ticker": ticker.upper(),
        "current_price": round(current_price, 2),
        "intrinsic_value": round(fair_value, 2),
        "upside_downside_pct": round(upside, 1),
        "confidence": confidence,
        "warnings": warnings,
        "sector_median_pe": pe_multiple,
        "trailing_eps": round(trailing_eps, 2),
        "assumptions": {
            "sector_pe": {"value": pe_multiple, "label": "Sector Median P/E Ratio", "unit": "x", "min": 1, "max": 100, "step": 0.5},
        },
        "assumptions_readonly": {
            "trailing_eps": {"value": round(trailing_eps, 2), "label": "Trailing Earnings Per Share", "unit": "$"},
        },
        "limitations": [
            "Assumes this company deserves the sector median P/E multiple",
            "Does not account for company-specific growth or risk differences vs. peers",
            "Trailing earnings may not reflect future profitability",
            "Sector medians are static benchmarks, not dynamically computed from current peers",
        ],
    }


# ── Revenue Multiple Valuation ───────────────────────────────────────────────

def revenue_multiple_valuation(ticker: str, tk=None, info=None, custom_overrides: dict | None = None) -> dict | None:
    """Fair value = sector_median_ps * revenue_per_share."""
    if tk is None or info is None:
        tk, info = _get_ticker_data(ticker)

    revenue_per_share = info.get("revenuePerShare")
    current_price = info.get("currentPrice") or info.get("regularMarketPrice")

    if not _is_valid_float(revenue_per_share) or revenue_per_share <= 0 or not _is_valid_float(current_price):
        return None

    medians = _get_sector_medians(info)
    ps_multiple = medians["ps"]
    if custom_overrides and "sector_ps" in custom_overrides:
        ps_multiple = float(custom_overrides["sector_ps"])
    fair_value = ps_multiple * revenue_per_share

    upside = ((fair_value / current_price) - 1) * 100

    # Confidence assessment
    warnings = []
    revenue_growth = info.get("revenueGrowth")
    if _is_valid_float(revenue_growth) and revenue_growth < 0:
        warnings.append("Revenue is declining")

    ratio = fair_value / current_price
    if ratio > 5.0 or ratio < 0.2:
        warnings.append(f"Fair value is {ratio:.1f}x current price")

    if len(warnings) >= 2:
        confidence = "low"
    elif len(warnings) == 1:
        confidence = "medium"
    else:
        confidence = "high"

    return {
        "model_type": "revenue_multiple",
        "ticker": ticker.upper(),
        "current_price": round(current_price, 2),
        "intrinsic_value": round(fair_value, 2),
        "upside_downside_pct": round(upside, 1),
        "confidence": confidence,
        "warnings": warnings,
        "sector_median_ps": ps_multiple,
        "revenue_per_share": round(revenue_per_share, 2),
        "assumptions": {
            "sector_ps": {"value": ps_multiple, "label": "Sector Median P/S Ratio", "unit": "x", "min": 0.1, "max": 50, "step": 0.1},
        },
        "assumptions_readonly": {
            "revenue_per_share": {"value": round(revenue_per_share, 2), "label": "Revenue Per Share", "unit": "$"},
        },
        "limitations": [
            "Revenue multiples ignore profitability entirely",
            "Assumes this company will achieve sector-average margins over time",
            "Most useful for high-growth companies where earnings are not yet meaningful",
            "Sector medians are static benchmarks, not dynamically computed from current peers",
        ],
    }


# ── Dividend Discount Model (DDM) ───────────────────────────────────────────

def ddm_valuation(ticker: str, tk=None, info=None, custom_overrides: dict | None = None) -> dict | None:
    """Gordon Growth Model: fair_value = D1 / (r - g)."""
    if tk is None or info is None:
        tk, info = _get_ticker_data(ticker)

    dividend_rate = info.get("dividendRate")
    current_price = info.get("currentPrice") or info.get("regularMarketPrice")

    if not _is_valid_float(dividend_rate) or dividend_rate <= 0 or not _is_valid_float(current_price):
        return None

    # Compute dividend growth from annual dividend sums CAGR
    try:
        divs = tk.dividends
        if divs is None or len(divs) == 0:
            return None
        annual_divs = divs.resample("YE").sum()
        annual_divs = annual_divs[annual_divs > 0]
        if len(annual_divs) >= 2:
            latest = float(annual_divs.iloc[-1])
            oldest = float(annual_divs.iloc[0])
            n = len(annual_divs) - 1
            if oldest > 0 and latest > 0:
                div_growth = (latest / oldest) ** (1 / n) - 1
            else:
                div_growth = 0.02
        else:
            div_growth = 0.02
    except Exception:
        div_growth = 0.02

    # Cap dividend growth at 8%
    div_growth = min(div_growth, 0.08)
    if div_growth < 0:
        div_growth = 0.0

    # Discount rate from CAPM
    beta = info.get("beta", 1.0) or 1.0
    adjusted_beta = (2 / 3) * beta + (1 / 3)
    r = cost_of_equity(adjusted_beta)

    # Apply user overrides
    if custom_overrides:
        if "dividend_growth" in custom_overrides:
            div_growth = float(custom_overrides["dividend_growth"]) / 100
        if "cost_of_equity" in custom_overrides:
            r = float(custom_overrides["cost_of_equity"]) / 100

    spread = r - div_growth
    if spread <= 0.01:
        spread = 0.01

    d1 = dividend_rate * (1 + div_growth)
    fair_value = d1 / spread

    upside = ((fair_value / current_price) - 1) * 100

    # Confidence
    warnings = []
    if spread < 0.02:
        warnings.append("Very narrow discount spread — sensitive to rate assumptions")
    ratio = fair_value / current_price
    if ratio > 5.0 or ratio < 0.2:
        warnings.append(f"Fair value is {ratio:.1f}x current price")

    if len(warnings) >= 2:
        confidence = "low"
    elif len(warnings) == 1:
        confidence = "medium"
    else:
        confidence = "high"

    return {
        "model_type": "ddm",
        "ticker": ticker.upper(),
        "current_price": round(current_price, 2),
        "intrinsic_value": round(fair_value, 2),
        "upside_downside_pct": round(upside, 1),
        "confidence": confidence,
        "warnings": warnings,
        "dividend_rate": round(dividend_rate, 4),
        "dividend_growth": round(div_growth * 100, 2),
        "cost_of_equity": round(r * 100, 2),
        "assumptions": {
            "dividend_growth": {"value": round(div_growth * 100, 2), "label": "Dividend Growth Rate", "unit": "%", "min": 0, "max": 15, "step": 0.25},
            "cost_of_equity": {"value": round(r * 100, 2), "label": "Cost of Equity (Discount Rate)", "unit": "%", "min": 1, "max": 25, "step": 0.25},
        },
        "assumptions_readonly": {
            "dividend_rate": {"value": round(dividend_rate, 4), "label": "Current Annual Dividend", "unit": "$"},
        },
        "limitations": [
            "Only applicable to dividend-paying stocks",
            "Assumes dividends grow at a constant rate forever (Gordon Growth Model)",
            "Very sensitive to the spread between discount rate and growth rate",
            "Does not capture value from retained earnings or share buybacks",
        ],
    }


# ── Book Value (P/B) Valuation ───────────────────────────────────────────────

def pb_valuation(ticker: str, tk=None, info=None, custom_overrides: dict | None = None) -> dict | None:
    """Fair value = sector_median_pb * book_value_per_share."""
    if tk is None or info is None:
        tk, info = _get_ticker_data(ticker)

    book_value = info.get("bookValue")
    current_price = info.get("currentPrice") or info.get("regularMarketPrice")

    if not _is_valid_float(book_value) or book_value <= 0 or not _is_valid_float(current_price):
        return None

    medians = _get_sector_medians(info)
    pb_multiple = medians["pb"]
    if custom_overrides and "sector_pb" in custom_overrides:
        pb_multiple = float(custom_overrides["sector_pb"])
    fair_value = pb_multiple * book_value

    upside = ((fair_value / current_price) - 1) * 100

    # Confidence
    warnings = []
    ratio = fair_value / current_price
    if ratio > 5.0 or ratio < 0.2:
        warnings.append(f"Fair value is {ratio:.1f}x current price")

    if len(warnings) >= 1:
        confidence = "medium"
    else:
        confidence = "high"

    return {
        "model_type": "book_value",
        "ticker": ticker.upper(),
        "current_price": round(current_price, 2),
        "intrinsic_value": round(fair_value, 2),
        "upside_downside_pct": round(upside, 1),
        "confidence": confidence,
        "warnings": warnings,
        "sector_median_pb": pb_multiple,
        "book_value_per_share": round(book_value, 2),
        "assumptions": {
            "sector_pb": {"value": pb_multiple, "label": "Sector Median P/B Ratio", "unit": "x", "min": 0.1, "max": 20, "step": 0.1},
        },
        "assumptions_readonly": {
            "book_value_per_share": {"value": round(book_value, 2), "label": "Book Value Per Share", "unit": "$"},
        },
        "limitations": [
            "Book value may not reflect market value of assets",
            "Intangible assets (brand, IP, goodwill) are poorly captured",
            "Most appropriate for financial and real estate companies with tangible asset bases",
            "Sector medians are static benchmarks, not dynamically computed from current peers",
        ],
    }


# ── Model Selector 

def select_best_model(ticker: str, tk=None, info=None) -> dict:
    """Decision tree to pick the best primary valuation model for a ticker.

    Returns dict with 'model', 'reason', and 'criteria' keys.
    """
    if tk is None or info is None:
        tk, info = _get_ticker_data(ticker)

    sector = info.get("sector", "")
    dividend_yield = info.get("dividendYield") or 0
    trailing_pe = info.get("trailingPE")
    revenue_growth = info.get("revenueGrowth") or 0
    fcf = info.get("freeCashflow")
    book_value = info.get("bookValue")
    medians = _get_sector_medians(info)

    # Check dividend history length
    has_dividend_history = False
    div_history_years = 0
    try:
        divs = tk.dividends
        if divs is not None and len(divs) > 0:
            div_history_years = round((divs.index[-1] - divs.index[0]).days / 365.25, 1)
            has_dividend_history = div_history_years >= 5
    except Exception:
        pass

    # 1. Financial Services / Real Estate + positive book value -> Book Value
    if sector in ("Financial Services", "Real Estate") and _is_valid_float(book_value) and book_value > 0:
        return {
            "model": "book_value",
            "reason": (
                f"This company operates in the {sector} sector, where asset-based valuation "
                f"is more meaningful than earnings-based approaches. Balance sheet assets are "
                f"central to how {sector} companies generate value. Book value per share is "
                f"${book_value:.2f}, providing a solid basis for Price-to-Book comparison "
                f"against the sector median P/B of {medians['pb']:.1f}x."
            ),
            "criteria": {
                "sector": sector,
                "book_value_per_share": round(book_value, 2),
                "sector_median_pb": medians["pb"],
            },
        }

    # 2. Dividend yield >2% + 5+ years history -> DDM
    #    yfinance returns dividendYield as a percentage (e.g. 2.7 = 2.7%)
    if dividend_yield > 2.0 and has_dividend_history:
        return {
            "model": "ddm",
            "reason": (
                f"This company has a dividend yield of {dividend_yield:.1f}% and over "
                f"{div_history_years:.0f} years of dividend history, making the Dividend "
                f"Discount Model appropriate. A long, consistent dividend track record "
                f"supports estimating fair value from expected future dividend payments."
            ),
            "criteria": {
                "dividend_yield_pct": round(dividend_yield, 2),
                "dividend_history_years": div_history_years,
            },
        }

    # 3. Revenue growth >15% + (no P/E or P/E >40 or FCF <0) -> Revenue Multiple
    high_growth = revenue_growth > 0.15
    no_pe = not _is_valid_float(trailing_pe) or trailing_pe <= 0
    high_pe = _is_valid_float(trailing_pe) and trailing_pe > 40
    negative_fcf = _is_valid_float(fcf) and fcf < 0
    if high_growth and (no_pe or high_pe or negative_fcf):
        earnings_issue = (
            "no positive trailing P/E" if no_pe else
            f"an elevated P/E of {trailing_pe:.1f}x" if high_pe else
            "negative free cash flow"
        )
        return {
            "model": "revenue_multiple",
            "reason": (
                f"With revenue growth of {revenue_growth:.0%} and {earnings_issue}, "
                f"earnings-based models are unreliable for this company. Revenue Multiple "
                f"valuation is more appropriate for high-growth companies where profitability "
                f"has not yet stabilized, comparing against the {sector or 'market'} sector "
                f"median P/S of {medians['ps']:.1f}x."
            ),
            "criteria": {
                "revenue_growth_pct": round(revenue_growth * 100, 1),
                "earnings_issue": earnings_issue,
                "sector": sector or "N/A",
                "sector_median_ps": medians["ps"],
            },
        }

    # 4. Positive trailing P/E -> P/E Comparable
    if _is_valid_float(trailing_pe) and trailing_pe > 0:
        return {
            "model": "pe_comparable",
            "reason": (
                f"This company has a positive trailing P/E of {trailing_pe:.1f}x, enabling "
                f"direct comparison to the {sector or 'market'} sector median P/E of "
                f"{medians['pe']:.1f}x. P/E Comparable valuation is the most straightforward "
                f"approach when a company has stable, positive earnings."
            ),
            "criteria": {
                "trailing_pe": round(trailing_pe, 1),
                "sector": sector or "N/A",
                "sector_median_pe": medians["pe"],
            },
        }

    # 5. Default -> DCF
    return {
        "model": "dcf",
        "reason": (
            "No specialized model criteria were met for this company (not a financial/real "
            "estate company, insufficient dividend history, not a high-growth pre-earnings "
            "company, and no positive trailing P/E). Discounted Cash Flow is used as the "
            "comprehensive default, projecting future free cash flows and discounting them "
            "back to present value."
        ),
        "criteria": {
            "sector": sector or "N/A",
            "fallback": True,
        },
    }


# ── Run All Applicable Models ────────────────────────────────────────────────

def run_all_applicable_models(ticker: str) -> dict:
    """Run all applicable valuation models and return results."""
    tk, info = _get_ticker_data(ticker)
    selection = select_best_model(ticker, tk, info)
    primary_model = selection["model"]

    all_models = []

    # Try each model
    pe_result = pe_valuation(ticker, tk, info)
    if pe_result:
        all_models.append(pe_result)

    rev_result = revenue_multiple_valuation(ticker, tk, info)
    if rev_result:
        all_models.append(rev_result)

    ddm_result = ddm_valuation(ticker, tk, info)
    if ddm_result:
        all_models.append(ddm_result)

    pb_result = pb_valuation(ticker, tk, info)
    if pb_result:
        all_models.append(pb_result)

    dcf_result = discounted_cashflow_analysis(ticker, verbose=False, tk=tk, info=info)
    if dcf_result:
        # Normalize DCF keys to standard shape
        dcf_normalized = {
            "model_type": "dcf",
            "ticker": dcf_result["ticker"],
            "current_price": dcf_result["current_price"],
            "intrinsic_value": dcf_result["intrinsic_value"],
            "upside_downside_pct": dcf_result["upside_downside_pct"],
            "confidence": dcf_result.get("dcf_confidence", "medium"),
            "warnings": dcf_result.get("dcf_warnings", []),
            "assumptions": dcf_result.get("assumptions"),
            "assumptions_readonly": dcf_result.get("assumptions_readonly"),
            "limitations": dcf_result.get("limitations"),
        }
        all_models.append(dcf_normalized)

    # Find primary result
    primary_result = None
    for m in all_models:
        if m["model_type"] == primary_model:
            primary_result = m
            break

    # If the selected primary model didn't produce a result, fall back to first available
    if primary_result is None and all_models:
        primary_result = all_models[0]
        primary_model = primary_result["model_type"]

    return {
        "primary_model": primary_model,
        "primary_result": primary_result,
        "all_models": all_models,
        "selection_reasoning": selection,
    }


# ── Main DCF function ─────────────────────────────────────────────────────────

def discounted_cashflow_analysis(
    ticker_symbol: str,
    n_years: int = 5,
    terminal_growth_rate: float = 0.025,
    method: str = "perpetuity",      # "perpetuity" | "exit_multiple"
    exit_multiple: float = 15.0,
    risk_free_rate: float = RISK_FREE_RATE,
    equity_risk_premium: float = EQUITY_RISK_PREMIUM,
    verbose: bool = True,
    tk=None,
    info=None,
    override_growth_rate: float | None = None,
    override_wacc: float | None = None,
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

    if tk is None or info is None:
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

    # Clamp WACC to [MIN_WACC, MAX_WACC]
    if wacc > MAX_WACC:
        print(f"  [WARNING] WACC {wacc:.2%} capped at {MAX_WACC:.2%} for {ticker_symbol}. "
              f"Intrinsic value will be overstated — treat result with caution.")
        wacc = MAX_WACC
    elif wacc < MIN_WACC:
        print(f"  [WARNING] WACC {wacc:.2%} floored at {MIN_WACC:.2%} for {ticker_symbol}.")
        wacc = MIN_WACC

    # ── Growth rate estimate ───────────────────────────────────────────────────
    g_near, used_fallback = estimate_growth_rate(tk)
    if used_fallback:
        print(f"  [WARNING] Could not compute FCF CAGR for {ticker_symbol}, using fallback")

    # Negative base FCF + positive growth = diverging losses; zero out growth
    if free_cash_flow < 0 and g_near > 0:
        print(f"  [WARNING] Base FCF is negative (${free_cash_flow:,.0f}) with positive "
              f"near-term growth ({g_near:.1%}). Setting growth to 0% to avoid "
              f"diverging negative projections.")
        g_near = 0.0

    # ── Apply user overrides (skip computed values) ────────────────────────────
    if override_growth_rate is not None:
        g_near = override_growth_rate / 100
    if override_wacc is not None:
        wacc = override_wacc / 100

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

    # ── Confidence assessment ─────────────────────────────────────────────────
    pv_tv = float(tv) / (1 + wacc) ** n_years
    enterprise_value = pv_sum_fcfs + pv_tv
    net_debt = total_debt - cash

    confidence_level, confidence_warnings = _assess_dcf_confidence(
        price_target, current_price, pv_tv, enterprise_value,
        net_debt, free_cash_flow, used_fallback,
    )

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
        "enterprise_value":      round(enterprise_value, 0),
        "dcf_confidence":        confidence_level,
        "dcf_warnings":          confidence_warnings,
        "assumptions": {
            "growth_rate":    {"value": round(g_near * 100, 2),                "label": "Near-term FCF Growth Rate",  "unit": "%",     "min": -10, "max": 50,  "step": 0.5},
            "wacc":           {"value": round(float(wacc) * 100, 2),           "label": "Weighted Avg Cost of Capital", "unit": "%",   "min": 1,   "max": 30,  "step": 0.25},
            "terminal_growth": {"value": round(terminal_growth_rate * 100, 2), "label": "Terminal Growth Rate",       "unit": "%",     "min": 0,   "max": 5,   "step": 0.25},
            "projection_years": {"value": n_years,                             "label": "Projection Horizon",         "unit": "years", "min": 1,   "max": 10,  "step": 1},
        },
        "assumptions_readonly": {
            "base_fcf":       {"value": f"${free_cash_flow:,.0f}",             "label": "Base Free Cash Flow",        "unit": ""},
            "beta":           {"value": round(beta, 2),                        "label": "Beta (Raw)",                 "unit": ""},
            "adjusted_beta":  {"value": round(adjusted_beta, 2),               "label": "Beta (Blume Adjusted)",      "unit": ""},
            "cost_of_equity": {"value": round(coe * 100, 2),                   "label": "Cost of Equity",             "unit": "%"},
            "cost_of_debt":   {"value": round(float(cod) * 100, 2),            "label": "Cost of Debt",               "unit": "%"},
            "tax_rate":       {"value": round(float(tax_rate) * 100, 2),       "label": "Effective Tax Rate",         "unit": "%"},
        },
        "limitations": [
            "Assumes cash flows continue indefinitely at the terminal growth rate",
            "Highly sensitive to WACC and growth rate assumptions",
            "Terminal value typically represents 60-90% of total estimated value",
            "Historical growth may not reflect future performance",
            "WACC is clamped to 5-15% range, which may not suit all companies",
        ],
    }

    # ── Pretty print ───────────────────────────────────────────────────────────
    if verbose:
        fallback_flag = " !! fallback" if used_fallback else ""
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
        print(f"  Beta (raw/adj)      : {results['beta']} -> {results['adjusted_beta']} (Blume)")
        print(f"{'-'*55}")
        print(f"  Near-term FCF Growth: {results['near_term_growth']}%{fallback_flag}")
        print(f"  Terminal Growth     : {results['terminal_growth']}%")
        print(f"  TV Method           : {results['terminal_value_method']}")
        print(f"{'-'*55}")
        print(f"  Base FCF            : ${free_cash_flow:,.0f}")
        for i, (proj, disc) in enumerate(zip(results['projected_fcfs'], results['discounted_fcfs']), 1):
            print(f"  Year {i} FCF (PV)    : ${proj:>14,.0f}  ->  ${disc:>14,.0f}")
        print(f"  PV of FCFs          : ${results['pv_sum_fcfs']:>14,.0f}")
        print(f"  Terminal Value      : ${results['terminal_value']:>14,.0f}")
        print(f"  Enterprise Value    : ${results['enterprise_value']:>14,.0f}")
        print(f"{'-'*55}")
        print(f"  Confidence          : {confidence_level.upper()}")
        if confidence_warnings:
            for w in confidence_warnings:
                print(f"    !! {w}")
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
