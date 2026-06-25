"""
Unit tests for scripts/valuation_models.py.

Strategy: feed *fake but fully controlled* inputs into the valuation math and
assert against *real expected answers* computed by hand from the formulas
(CAPM, WACC, Gordon Growth, DCF discounting). No network, no yfinance calls —
the comparable/DCF model functions accept injected `tk`/`info`, and we hand-roll
a tiny FakeTicker for the few that read pandas frames.

Every magic number in an assertion is derived in the comment above it so the
"expected answer" is auditable, not reverse-engineered from the code.
"""

import numpy as np
import pandas as pd
import pytest

from scripts.valuation_models import (
    RISK_FREE_RATE,
    EQUITY_RISK_PREMIUM,
    MIN_WACC_GROWTH_SPREAD,
    cost_of_equity,
    WACC,
    TV_perpetuity,
    TV_exitMultiple,
    project_fcfs_with_fade,
    discount_cashflows,
    intrinsic_value_per_share,
    pe_valuation,
    revenue_multiple_valuation,
    pb_valuation,
    ddm_valuation,
    select_best_model,
    discounted_cashflow_analysis,
)


# A minimal stand-in for yfinance.Ticker.
# Only implements the attributes the functions under test actually read.

class FakeTicker:
    def __init__(self, info=None, dividends=None, cashflow=None,
                 balancesheet=None, financials=None):
        self.info = info or {}
        self._dividends = dividends
        self.cashflow = cashflow if cashflow is not None else pd.DataFrame()
        self.balancesheet = balancesheet if balancesheet is not None else pd.DataFrame()
        self.financials = financials if financials is not None else pd.DataFrame()

    @property
    def dividends(self):
        return self._dividends


def _annual_dividends(values, start_year=2016):
    """Build a year-end-indexed dividend Series, one entry per year."""
    idx = pd.to_datetime([f"{start_year + i}-12-31" for i in range(len(values))])
    return pd.Series(values, index=idx)


# Cost of capital

class TestCostOfEquity:
    """CAPM: r = risk_free + beta * equity_risk_premium (0.0396 + beta*0.0438)."""

    def test_beta_one(self):
        # 0.0396 + 1.0 * 0.0438 = 0.0834
        assert cost_of_equity(1.0) == pytest.approx(0.0834)

    def test_beta_two(self):
        # 0.0396 + 2.0 * 0.0438 = 0.1272
        assert cost_of_equity(2.0) == pytest.approx(0.1272)

    def test_zero_beta_is_risk_free(self):
        assert cost_of_equity(0.0) == pytest.approx(RISK_FREE_RATE)

    def test_custom_rates(self):
        # 0.05 + 1.5 * 0.06 = 0.14
        assert cost_of_equity(1.5, risk_free_rate=0.05, equity_risk_premium=0.06) == pytest.approx(0.14)


class TestWACC:
    def test_no_debt_returns_cost_of_equity(self):
        # td == 0 short-circuits to coe regardless of other args.
        assert WACC(mc=1000, td=0, coe=0.08, cod=0.05, tr=0.21) == pytest.approx(0.08)

    def test_with_debt(self):
        # v = 800 + 200 = 1000
        # (800/1000)*0.10 + (200/1000)*0.05*(1-0.20)
        #   = 0.08 + 0.2*0.05*0.8 = 0.08 + 0.008 = 0.088
        assert WACC(mc=800, td=200, coe=0.10, cod=0.05, tr=0.20) == pytest.approx(0.088)


# Terminal value

class TestTVPerpetuity:
    def test_normal(self):
        # spread = 0.10 - 0.02 = 0.08 (>= floor); (100 * 1.02) / 0.08 = 1275.0
        assert TV_perpetuity(fcf=100, g=0.02, wacc=0.10) == pytest.approx(1275.0)

    def test_spread_is_floored(self):
        # raw spread = 0.10 - 0.09 = 0.01 < 0.02 floor -> uses 0.02
        # (100 * 1.09) / 0.02 = 5450.0
        assert TV_perpetuity(fcf=100, g=0.09, wacc=0.10) == pytest.approx(5450.0)
        assert MIN_WACC_GROWTH_SPREAD == 0.02  # guards the floor constant

    def test_negative_fcf_caps_at_zero(self):
        # Never projects perpetual losses.
        assert TV_perpetuity(fcf=-50, g=0.02, wacc=0.10) == 0.0


class TestTVExitMultiple:
    def test_multiplies(self):
        assert TV_exitMultiple(metric=100, multiple=15.0) == 1500.0


# Projection & discounting

class TestProjectFCFs:
    def test_single_year_uses_near_growth(self):
        # n_years == 1 forces weight 0 -> base * (1 + g_near) = 100 * 1.10
        assert project_fcfs_with_fade(100.0, g_near=0.10, g_terminal=0.025, n_years=1) == [pytest.approx(110.0)]

    def test_first_year_always_uses_near_growth(self):
        # Year 1 weight is exp-decayed from 0, so it always grows at g_near.
        fcfs = project_fcfs_with_fade(100.0, g_near=0.10, g_terminal=0.025, n_years=5)
        assert len(fcfs) == 5
        assert fcfs[0] == pytest.approx(110.0)
        # Growth fades toward terminal, so each step's growth rate shrinks.
        growth_steps = [fcfs[i] / fcfs[i - 1] - 1 for i in range(1, 5)]
        assert all(growth_steps[i] < growth_steps[i - 1] for i in range(1, 4))


class TestDiscountCashflows:
    def test_discounting(self):
        # 100/1.1, 100/1.1^2, 100/1.1^3
        out = discount_cashflows([100, 100, 100], 0.10)
        assert out[0] == pytest.approx(90.9090909, rel=1e-6)
        assert out[1] == pytest.approx(82.6446281, rel=1e-6)
        assert out[2] == pytest.approx(75.1314801, rel=1e-6)


class TestIntrinsicValuePerShare:
    def test_equity_value_per_share(self):
        # pv_tv = 5000 / 1.1^5 = 3104.60660...
        # EV = 1000 + 3104.6066 = 4104.6066
        # net_debt = 200 - 100 = 100; equity = 4004.6066
        # per share = 4004.6066 / 100 = 40.046066
        val = intrinsic_value_per_share(
            pv_fcfs=1000, terminal_value=5000, wacc=0.10, n_years=5,
            total_debt=200, cash=100, shares_outstanding=100,
        )
        assert val == pytest.approx(40.046066, rel=1e-6)

    def test_zero_shares_is_nan(self):
        val = intrinsic_value_per_share(1000, 5000, 0.10, 5, 0, 0, shares_outstanding=0)
        assert np.isnan(val)


# Comparable models (injected info dict; no network)

class TestComparableModels:
    def test_pe_valuation(self):
        # Technology sector median P/E = 28.0; fair = 28 * 6.0 = 168.0
        # upside = (168/150 - 1) * 100 = 12.0%
        info = {
            "trailingEps": 6.0, "currentPrice": 150.0, "sector": "Technology",
            "forwardPE": 25.0, "trailingPE": 25.0,
        }
        res = pe_valuation("AAPL", tk=FakeTicker(info), info=info)
        assert res["intrinsic_value"] == 168.0
        assert res["upside_downside_pct"] == 12.0
        assert res["sector_median_pe"] == 28.0
        assert res["confidence"] == "high"   # no divergence, ratio 1.12 in range

    def test_pe_rejects_negative_eps(self):
        info = {"trailingEps": -2.0, "currentPrice": 150.0, "sector": "Technology"}
        assert pe_valuation("X", tk=FakeTicker(info), info=info) is None

    def test_pe_custom_override(self):
        # Override sector P/E to 10 -> fair = 10 * 6.0 = 60.0
        info = {"trailingEps": 6.0, "currentPrice": 150.0, "sector": "Technology"}
        res = pe_valuation("AAPL", tk=FakeTicker(info), info=info, custom_overrides={"sector_pe": 10})
        assert res["intrinsic_value"] == 60.0

    def test_revenue_multiple(self):
        # Technology P/S = 6.0; fair = 6 * 5.0 = 30.0; upside = (30/25 - 1)*100 = 20.0%
        info = {
            "revenuePerShare": 5.0, "currentPrice": 25.0, "sector": "Technology",
            "revenueGrowth": 0.12,
        }
        res = revenue_multiple_valuation("X", tk=FakeTicker(info), info=info)
        assert res["intrinsic_value"] == 30.0
        assert res["upside_downside_pct"] == 20.0
        assert res["confidence"] == "high"

    def test_revenue_declining_lowers_confidence(self):
        # Negative revenue growth adds one warning -> confidence "medium".
        info = {
            "revenuePerShare": 5.0, "currentPrice": 25.0, "sector": "Technology",
            "revenueGrowth": -0.05,
        }
        res = revenue_multiple_valuation("X", tk=FakeTicker(info), info=info)
        assert res["confidence"] == "medium"

    def test_pb_valuation(self):
        # Financial Services P/B = 1.3; fair = 1.3 * 50 = 65.0
        # upside = (65/60 - 1)*100 = 8.333... -> rounded 8.3
        info = {"bookValue": 50.0, "currentPrice": 60.0, "sector": "Financial Services"}
        res = pb_valuation("JPM", tk=FakeTicker(info), info=info)
        assert res["intrinsic_value"] == 65.0
        assert res["upside_downside_pct"] == 8.3
        assert res["sector_median_pb"] == 1.3

    def test_unknown_sector_uses_default_medians(self):
        # Unknown sector -> DEFAULT_MEDIANS pe = 18.0; fair = 18 * 6 = 108.0
        info = {"trailingEps": 6.0, "currentPrice": 150.0, "sector": "Nonexistent"}
        res = pe_valuation("X", tk=FakeTicker(info), info=info)
        assert res["intrinsic_value"] == 108.0


class TestDDM:
    def test_ddm_with_overrides(self):
        # Overrides pin the math: div_growth=5% -> 0.05, cost_of_equity=9% -> 0.09
        # spread = 0.09 - 0.05 = 0.04
        # D1 = 2.0 * (1 + 0.05) = 2.1; fair = 2.1 / 0.04 = 52.5
        # upside = (52.5 / 50 - 1) * 100 = 5.0%
        info = {"dividendRate": 2.0, "currentPrice": 50.0, "beta": 1.0}
        tk = FakeTicker(info, dividends=_annual_dividends([1.0, 1.1, 1.2]))
        res = ddm_valuation(
            "KO", tk=tk, info=info,
            custom_overrides={"dividend_growth": 5, "cost_of_equity": 9},
        )
        assert res["intrinsic_value"] == 52.5
        assert res["upside_downside_pct"] == 5.0
        assert res["confidence"] == "high"

    def test_ddm_rejects_non_dividend_payer(self):
        info = {"dividendRate": 0.0, "currentPrice": 50.0, "beta": 1.0}
        assert ddm_valuation("X", tk=FakeTicker(info), info=info) is None


# Model selector decision tree

class TestSelectBestModel:
    def test_financials_pick_book_value(self):
        info = {"sector": "Financial Services", "bookValue": 40.0}
        assert select_best_model("JPM", tk=FakeTicker(info), info=info)["model"] == "book_value"

    def test_dividend_payer_picks_ddm(self):
        # yield > 2% AND >= 5 years of history -> DDM
        info = {"sector": "Consumer Defensive", "dividendYield": 3.0, "trailingPE": 20.0}
        tk = FakeTicker(info, dividends=_annual_dividends([1.0] * 8))  # ~7 yrs span
        assert select_best_model("KO", tk=tk, info=info)["model"] == "ddm"

    def test_high_growth_no_earnings_picks_revenue(self):
        # revenue growth > 15% and negative FCF -> revenue multiple
        info = {"sector": "Technology", "revenueGrowth": 0.40, "freeCashflow": -1e9, "trailingPE": None}
        assert select_best_model("X", tk=FakeTicker(info), info=info)["model"] == "revenue_multiple"

    def test_positive_pe_picks_pe_comparable(self):
        info = {"sector": "Technology", "trailingPE": 25.0, "revenueGrowth": 0.05}
        assert select_best_model("AAPL", tk=FakeTicker(info), info=info)["model"] == "pe_comparable"

    def test_default_falls_back_to_dcf(self):
        # No book value, no dividend, low growth, no positive P/E -> DCF
        info = {"sector": "Industrials", "trailingPE": None, "revenueGrowth": 0.03}
        assert select_best_model("X", tk=FakeTicker(info), info=info)["model"] == "dcf"


# Full DCF (overrides pin WACC & growth so the answer is hand-computable)

class TestDCFIntegration:
    def test_single_year_dcf_hand_computed(self):
        # Debt-free, single-year horizon, overrides pin wacc=10% and growth=10%:
        #   projected FCF  = 1000 * 1.10                       = 1100
        #   PV(FCF)        = 1100 / 1.1                         = 1000
        #   terminal value = (1100 * 1.025) / (0.10 - 0.025)   = 15033.333
        #   PV(TV)         = 15033.333 / 1.1                    = 13666.667
        #   EV             = 1000 + 13666.667                   = 14666.667
        #   equity/share   = 14666.667 / 100 shares            = 146.667 -> 146.67
        #   upside         = (146.667 / 100 - 1) * 100          = 46.7%
        info = {
            "freeCashflow": 1000.0, "beta": 1.0, "marketCap": 10_000.0,
            "currentPrice": 100.0, "totalDebt": 0, "sharesOutstanding": 100,
            "totalCash": 0,
        }
        tk = FakeTicker(
            info,
            balancesheet=pd.DataFrame({pd.Timestamp("2023-12-31"): {"Total Revenue": 5000}}),
            financials=pd.DataFrame({pd.Timestamp("2023-12-31"): {"Total Revenue": 5000}}),
        )
        res = discounted_cashflow_analysis(
            "X", n_years=1, terminal_growth_rate=0.025, verbose=False,
            tk=tk, info=info, override_growth_rate=10, override_wacc=10,
        )
        assert res["wacc"] == 10.0
        assert res["near_term_growth"] == 10.0
        assert res["intrinsic_value"] == 146.67
        assert res["upside_downside_pct"] == 46.7

    def test_dcf_missing_data_returns_none(self):
        # Missing beta/marketCap -> graceful None, never a crash.
        info = {"freeCashflow": 1000.0, "currentPrice": 100.0}
        tk = FakeTicker(
            info,
            balancesheet=pd.DataFrame({pd.Timestamp("2023-12-31"): {"x": 1}}),
            financials=pd.DataFrame({pd.Timestamp("2023-12-31"): {"x": 1}}),
        )
        assert discounted_cashflow_analysis("X", verbose=False, tk=tk, info=info) is None
