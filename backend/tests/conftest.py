# pytest fixtures for the API test suite.
#
# IMPORTANT: the DB pool is stubbed *before* importing the app. backend/db_funcs.py
# builds a ThreadedConnectionPool and runs _ensure_tables() at import time, and
# backend/main.py imports db_funcs, so `from backend.main import app` would otherwise
# require a live Postgres. Replacing the pool with a MagicMock lets the import (and
# _ensure_tables's chained cursor calls) succeed offline.

from unittest.mock import MagicMock

import psycopg2.pool
psycopg2.pool.ThreadedConnectionPool = lambda *args, **kwargs: MagicMock()

import pytest
from fastapi.testclient import TestClient
from backend.main import app


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def fake_sentiment():
    # Deterministic stand-in for get_sentiment_analysis() -> (scalar, insights).
    # Shape matches the /stocksentiment response contract.
    scalar = 1.08
    insights = [
        {
            "insight": "Strong fundamental performance driving bullish sentiment",
            "sentiment": "Bullish",
            "reasoning": "Record Q3 revenue and analyst upgrades signal strong confidence.",
        },
        {
            "insight": "Geopolitical risks creating headwinds",
            "sentiment": "Bearish",
            "reasoning": "Tightening export restrictions introduce structural downside risk.",
        },
    ]
    return scalar, insights


@pytest.fixture
def fake_valuation():
    # Deterministic stand-in for get_valuation(ticker). Mirrors the keys main.py reads:
    # primary_result, primary_model, selection_reasoning, all_models.
    return {
        "primary_result": {
            "model_type": "dcf",
            "intrinsic_value": 210.0,
            "upside_downside_pct": 9.1,
            "confidence": "high",
            "warnings": [],
        },
        "primary_model": "dcf",
        "selection_reasoning": "DCF selected: positive and stable free cash flow.",
        "all_models": [
            {
                "model_type": "dcf",
                "intrinsic_value": 210.0,
                "upside_downside_pct": 9.1,
                "confidence": "high",
                "warnings": [],
                "assumptions": {"growth_rate": 8.0, "wacc": 9.0},
                "assumptions_readonly": {},
                "limitations": [],
            }
        ],
    }


@pytest.fixture
def fake_fr():
    # Deterministic stand-in for get_fr_prediction(ticker, model).
    return {
        "fr_class": 7.0,
        "price_at_prediction": 192.5,
        "prediction_date": "2026-03-31",
    }
