"""
Endpoint tests for the Stockish FastAPI backend.

Grouped by category: health/smoke, happy path, boundary/input-validation,
negative/error paths, and external-dependency isolation (mocking).

All external seams (FMP, OpenAI, yfinance, the DB, the XGBoost model) are mocked so
the suite is deterministic and runs offline in CI with no secrets. We patch the names
*as bound in backend.main* (main.py does `from X import name`, so the route looks up
`backend.main.name`, not the original module).
"""

import pytest



# SMOKE / HEALTH — does the app boot and answer?
class TestHealth:
    """The service boots and the health endpoints respond 200."""

    def test_root_returns_200(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert resp.json() == {"Hello": "World"}

    def test_health_returns_200(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_health_payload_shape(self, client):
        resp = client.get("/health")
        assert resp.json().get("status") == "ok"



# 2. HAPPY PATH — valid ticker returns 200 and the expected contract.
class TestStockHappyPath:
    """Valid ticker returns 200 with the documented stock payload shape."""

    def _patch_services(self, monkeypatch, fake_valuation, fake_fr):
        import backend.main as m

        async def fake_get_fr_prediction(ticker, model):
            return fake_fr

        monkeypatch.setattr(m, "get_stock_price", lambda ticker: 192.5)
        monkeypatch.setattr(m, "is_etf", lambda ticker: (False, 192.5))
        monkeypatch.setattr(m, "get_valuation", lambda ticker: fake_valuation)
        monkeypatch.setattr(m, "get_fr_prediction", fake_get_fr_prediction)
        # compute_final_analysis is stubbed so the test stays decoupled from scoring logic.
        monkeypatch.setattr(
            m, "compute_final_analysis",
            lambda primary, fr, sentiment: {
                "verdict": "Strong Overall Score",
                "composite_score": 0.71,
                "signals_used": 2,
                "confidence": "High",
            },
        )

    def test_known_ticker_returns_200(self, client, monkeypatch, fake_valuation, fake_fr):
        self._patch_services(monkeypatch, fake_valuation, fake_fr)

        resp = client.get("/stock/AAPL")
        assert resp.status_code == 200
        body = resp.json()
        # Assert on the contract, not exact values.
        assert body["ticker"] == "AAPL"
        assert "current_price" in body
        assert "fr_prediction" in body
        assert body["final_analysis"]["confidence"] == "High"
        assert isinstance(body["models"], list)

    def test_response_is_json(self, client, monkeypatch, fake_valuation, fake_fr):
        self._patch_services(monkeypatch, fake_valuation, fake_fr)

        resp = client.get("/stock/AAPL")
        assert resp.headers["content-type"].startswith("application/json")

    def test_ticker_is_uppercased(self, client, monkeypatch, fake_valuation, fake_fr):
        self._patch_services(monkeypatch, fake_valuation, fake_fr)

        resp = client.get("/stock/aapl")
        assert resp.status_code == 200
        assert resp.json()["ticker"] == "AAPL"



# 3. BOUNDARY / INPUT VALIDATION — equivalence partitioning + boundaries.

class TestStockBoundaries:
    """Malformed tickers are rejected cleanly (422), never 500'd."""

    @pytest.mark.parametrize("bad_symbol", [
        "TOOLONGTICKER",   # over max length (>10)
        "12345",           # numeric / invalid format
        "AA PL",           # whitespace
        "..etc",           # punctuation junk (light security boundary)
        "1AAPL",           # must start with a letter
    ])
    def test_invalid_ticker_is_handled(self, client, bad_symbol):
        resp = client.get(f"/stock/{bad_symbol}")
        # Contract: a clean client error, never a 500.
        assert resp.status_code in (400, 404, 422)
        assert resp.status_code != 500



# 4. NEGATIVE / ERROR PATHS — upstream failure degrades gracefully.
class TestUpstreamFailure:
    """When the data provider errors, /stock returns 502, not a leaked 500."""

    def test_provider_failure_returns_502(self, client, monkeypatch):
        import backend.main as m

        def boom(ticker):
            raise TimeoutError("FMP/yfinance unreachable")

        monkeypatch.setattr(m, "get_stock_price", boom)
        monkeypatch.setattr(m, "is_etf", lambda ticker: (False, None))

        resp = client.get("/stock/AAPL")
        assert resp.status_code == 502
        assert resp.status_code != 500


# 5. SENTIMENT (OpenAI) — mock the LLM call; never hit the real API.
class TestSentiment:
    """Sentiment endpoint returns structured output; the LLM call is mocked."""

    def _patch(self, monkeypatch, *, is_etf=False, usage=0, result=None):
        import backend.main as m

        async def fake_get_sentiment_analysis(ticker):
            return result

        monkeypatch.setattr(m, "is_etf", lambda ticker: (is_etf, None))
        monkeypatch.setattr(m, "get_daily_usage", lambda ip: usage)
        monkeypatch.setattr(m, "increment_usage", lambda ip: usage + 1)
        monkeypatch.setattr(m, "get_sentiment_analysis", fake_get_sentiment_analysis)

    def test_sentiment_happy_path(self, client, monkeypatch, fake_sentiment):
        self._patch(monkeypatch, usage=0, result=fake_sentiment)

        resp = client.get("/stocksentiment/AAPL")
        assert resp.status_code == 200
        body = resp.json()
        assert 0.5 <= body["scalar"] <= 1.5          # boundary check on the multiplier
        assert isinstance(body["insights"], list)
        for ins in body["insights"]:
            assert ins["sentiment"] in ("Bullish", "Bearish", "Neutral")
        assert "remaining" in body

    def test_etf_is_rejected(self, client, monkeypatch, fake_sentiment):
        self._patch(monkeypatch, is_etf=True, result=fake_sentiment)

        resp = client.get("/stocksentiment/SPY")
        assert resp.status_code == 200
        assert resp.json() == {"Sentiment": "Cannot evaluate etf"}

    def test_daily_limit_returns_429(self, client, monkeypatch, fake_sentiment):
        self._patch(monkeypatch, usage=3, result=fake_sentiment)  # DAILY_LIMIT == 3

        resp = client.get("/stocksentiment/AAPL")
        assert resp.status_code == 429

    def test_no_news_returns_null_scalar(self, client, monkeypatch):
        self._patch(monkeypatch, usage=1, result=(None, None))

        resp = client.get("/stocksentiment/AAPL")
        assert resp.status_code == 200
        body = resp.json()
        assert body["scalar"] is None
        assert body["insights"] is None



# 6. MARKET MOVERS — list endpoints; mock the FMP fetch.
class TestMarketMovers:
    """Movers endpoints return a list; the FMP call is mocked."""

    def test_topmovers_returns_list(self, client, monkeypatch):
        import backend.main as m

        async def fake_get_top_movers():
            return [{"symbol": "AAPL", "price": 192.5}, {"symbol": "MSFT", "price": 410.0}]

        monkeypatch.setattr(m, "get_top_movers", fake_get_top_movers)

        resp = client.get("/topmovers")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


# 7. RECALCULATE — input validation on the POST body.
class TestRecalculate:
    """Recalculate validates model_type and assumptions before running."""

    def test_unknown_model_type_is_422(self, client):
        resp = client.post("/stock/AAPL/recalculate", json={"model_type": "nope"})
        assert resp.status_code == 422

    def test_unknown_assumption_is_422(self, client):
        resp = client.post(
            "/stock/AAPL/recalculate",
            json={"model_type": "dcf", "assumptions": {"bogus": 5}},
        )
        assert resp.status_code == 422

    def test_out_of_range_assumption_is_422(self, client):
        resp = client.post(
            "/stock/AAPL/recalculate",
            json={"model_type": "dcf", "assumptions": {"wacc": 999}},  # range (1, 30)
        )
        assert resp.status_code == 422

    def test_valid_recalculation_returns_200(self, client, monkeypatch):
        import backend.main as m

        monkeypatch.setattr(
            m, "_run_recalculation",
            lambda ticker, model_type, assumptions: {
                "model_type": "dcf",
                "intrinsic_value": 205.0,
                "upside_downside_pct": 6.5,
                "confidence": "medium",
                "warnings": [],
            },
        )

        resp = client.post(
            "/stock/AAPL/recalculate",
            json={"model_type": "dcf", "assumptions": {"wacc": 9, "growth_rate": 8}},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["intrinsic_value"] == 205.0
        assert body["confidence"] == "medium"


# 8. SEARCH — graceful degradation when the upstream search errors.
class TestSearch:
    """Search returns an object with a results list, even on upstream failure."""

    def test_search_degrades_gracefully(self, client, monkeypatch):
        import backend.main as m

        class BoomClient:
            async def __aenter__(self):
                raise RuntimeError("FMP search unreachable")

            async def __aexit__(self, *exc):
                return False

        monkeypatch.setattr(m.httpx, "AsyncClient", lambda *a, **k: BoomClient())

        resp = client.get("/search/apple")
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body["results"], list)
        assert body["results"] == []
