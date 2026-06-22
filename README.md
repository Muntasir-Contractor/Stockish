# Stockish

**Multi-model equity valuation, forward-return classification, and news sentiment in one view.**

Live at **[stockish.ai](https://stockish.ai)**

Stockish takes a ticker and answers three questions a value-minded investor actually asks: *What is this company worth? What have fundamentals like these returned historically? And what is the news saying right now?* It estimates intrinsic value across five valuation models, classifies forward 1-year return potential with an XGBoost model trained on fundamentals, and pulls a structured sentiment read from recent headlines. The three signals are blended into a single composite score.

> Built for educational and research purposes. Nothing here is financial advice or a recommendation to buy or sell any security. Model outputs are analytical estimates from historical and public data, and may be wrong. Do your own research.

---

## Why I built it

I wanted a tool that didn't just throw a single number at you. Most retail stock tools either show a black-box "fair value" or a wall of raw fundamentals. Stockish makes the *reasoning* visible: which valuation model was chosen and why, what assumptions went into it, how confident the estimate is, and how the model would change if you tweak the inputs yourself.

---

## What it does

### Five valuation models, one chosen automatically

For any stock, Stockish runs up to five models and selects the most appropriate one based on the company's sector, dividend history, growth profile, and what data is actually available:

- **DCF** — projects free cash flows, discounts them at WACC, and adds a Gordon-Growth terminal value. Includes Blume-adjusted beta, FCF growth fade, and tiered fallback growth rates when history is thin.
- **P/E comparable** — applies a sector-median trailing P/E to EPS.
- **Revenue multiple (P/S)** — values on revenue instead of earnings, for high-growth or pre-profit names where P/E breaks down.
- **Dividend Discount Model** — present value of expected dividends, for payers with 5+ years of history.
- **Book value (P/B)** — sector-median price-to-book, suited to financials, REITs, and capital-heavy industries.

Each model returns a fair value, a confidence level, and any warnings about the assumptions it had to make. A decision tree picks the primary model and explains its choice in plain language.

**You can override any assumption** (growth rate, WACC, terminal growth, sector multiples, cost of equity...) and recalculate a single model in place, with server-side range validation on every input.

### Forward-return classification

An XGBoost classifier predicts which decile (0–9) a stock's forward 1-year return is likely to land in, from nine fundamental features:

| Feature | Captures |
|---|---|
| Gross profitability | Earning power vs. assets |
| ROIC | Capital-allocation efficiency |
| FCF yield | Cash generation vs. market cap |
| Revenue growth YoY | Top-line momentum |
| 6-month price momentum | Recent trend |
| EV/EBITDA | Valuation multiple |
| Accrual ratio | Earnings quality |
| Interest coverage | Debt-servicing capacity |
| Shares outstanding growth | Dilution vs. buybacks |

Decile 9 means the current fundamentals historically lined up with the top 10% of forward returns. The model is trained with Optuna-tuned hyperparameters and backtested against held-out history.

### News sentiment, as structured output

Recent headlines are summarized by an LLM into a Pydantic-validated response:

- a **sentiment scalar** (0.5–1.5) that nudges fair-value expectations, where 1.0 is neutral
- **3–5 themed insights**, each tagged Bullish / Bearish / Neutral with reasoning grounded in the actual headlines

Results are cached per ticker for 24 hours and rate-limited to 3 analyses per IP per day.

### Composite score

Valuation gap, forward-return decile, and sentiment scalar combine into one score from -1 to +1:

| Signal | Weight |
|---|---|
| Valuation upside/downside | 50% (scaled by confidence) |
| Forward-return decile | 30% |
| Sentiment | 20% |

The score maps to a verdict with a confidence level that reflects how many of the three signals were actually available.

### Plus

Live top movers / gainers / losers, debounced ticker search with keyboard nav, automatic ETF detection (ETFs skip valuation and classification), and an in-app guide explaining every model, feature, and limitation.

---

## Architecture

```
React (Vite, Vercel)
        │  HTTPS
        ▼
Cloudflare (DNS, CDN, SSL, proxy)
        │
        ▼
Nginx ──► FastAPI (Uvicorn, Docker on EC2)
        │
        ├─ Valuation engine        DCF · P/E · P/S · DDM · P/B
        ├─ XGBoost classifier      9 features → forward-return decile
        ├─ LLM sentiment           headlines → scalar + structured insights
        └─ Composite scoring       weighted blend → verdict
        │
        ▼
PostgreSQL (AWS RDS)   sentiment cache · daily rate limits · cached valuations
```

Valuation, forward-return prediction, and sentiment are fetched concurrently, and CPU-bound valuation work is offloaded off the event loop. Valuations are cached until a company reports new statements. Tickers are validated against a strict pattern before any upstream call, malformed input returns `422`, and upstream failures degrade to `502` rather than leaking a `500`.

---

## Tech stack

| Layer | Tools |
|---|---|
| Backend | Python 3.13, FastAPI, Uvicorn, httpx (async) |
| ML | XGBoost, scikit-learn, Optuna, joblib |
| Sentiment | LLM with Pydantic-enforced structured output |
| Data | yfinance, Financial Modeling Prep |
| Database | PostgreSQL on AWS RDS (psycopg2 threaded pool) |
| Rate limiting | slowapi (per-IP, per-endpoint) |
| Frontend | React 19, React Router 7, Vite, Axios |
| Tests | pytest (fully mocked, offline) |
| Infra | Docker, GitHub Actions, AWS EC2 + Nginx, Cloudflare, Vercel |

---

## Testing & CI/CD

The backend has a pytest suite covering health checks, the happy-path response contract, input-validation boundaries (malformed tickers, out-of-range assumptions), graceful upstream-failure handling, and the rate-limit / ETF / no-news edge cases.

Every external seam — FMP, the LLM, yfinance, Postgres, and the XGBoost model — is mocked, so the suite is deterministic and runs offline in CI with **no secrets and no live database**.

Two GitHub Actions workflows:

- **CI** runs the suite on every push and PR to `main`.
- **Deploy** reruns the tests and only deploys if they pass. Deployment is a tests-gated job that ships the new image to EC2 over AWS SSM (no inbound SSH), rebuilds the Docker container, and verifies it's healthy before finishing. It triggers only when backend code, scripts, dependencies, or the Dockerfile change.

---

## Running locally

**Prerequisites:** Python 3.11+, Node.js, PostgreSQL, plus an LLM API key and a Financial Modeling Prep key.

```bash
git clone https://github.com/Muntasir-Contractor/Stockish.git
cd Stockish
```

Create `backend/.env`:

```env
OPENAI_API_KEY=your_key
FINANCE_KEY=your_fmp_key
DATABASE_HOST=localhost
DATABASE_NAME=postgres
DATABASE_USER=postgres
PASSWORD=your_postgres_password
DATABASE_PORT=5432
```

Backend:

```bash
pip install -r requirements.txt
cd backend
uvicorn main:app --reload
```

Frontend (reads `VITE_API_URL`, defaults to `http://localhost:8000`):

```bash
cd frontend
npm install
npm run dev
```

Run the tests (no keys or DB required):

```bash
pytest -v
```

Or build the backend container:

```bash
docker build -t stockish-api .
docker run -p 8000:8000 --env-file backend/.env stockish-api
```

---

## API

| Method | Endpoint | Description | Limit |
|---|---|---|---|
| `GET` | `/stock/{ticker}` | All valuation models, current price, valuation label, forward-return decile, composite score | 15/min |
| `POST` | `/stock/{ticker}/recalculate` | Re-run one model with custom, range-validated assumptions | 15/min |
| `GET` | `/stocksentiment/{ticker}` | Sentiment scalar, structured insights, remaining daily analyses | 3/day per IP |
| `GET` | `/search/{query}` | Deduplicated symbol search | 20/min |
| `GET` | `/topmovers` · `/topgainers` · `/toplosers` | Live market movers | 30/min |
| `GET` | `/health` | Liveness check | — |
| `POST` | `/feedback` | Submit feedback | — |

---

## Project layout

```
Stockish/
├── backend/
│   ├── main.py            FastAPI app: routes, CORS, validation, rate limiting
│   ├── application.py     Valuation orchestration, FR prediction, composite scoring
│   ├── newssentiment.py   LLM sentiment analysis (structured output)
│   ├── fetchnews.py       Headline fetching
│   ├── fetchfromAPI.py    Financial Modeling Prep client
│   ├── db_funcs.py        PostgreSQL: cache, rate limits, valuations
│   ├── model/             Serialized XGBoost classifier
│   └── tests/             pytest suite + fixtures (fully mocked)
├── scripts/
│   ├── valuation_models.py    DCF · P/E · P/S · DDM · P/B
│   ├── fetch_fr_stockdata.py  Forward-return feature extraction
│   ├── train_model.py         XGBoost training + Optuna tuning
│   └── *_backtesting.py       Historical performance testing
├── frontend/              React 19 + Vite app
├── .github/workflows/     CI + tests-gated backend deploy
├── Dockerfile
└── requirements.txt
```

---

## Disclaimer

Stockish is not a registered investment advisor and does not provide financial advice. Every valuation, classification, and sentiment read is a model-generated estimate from historical and public data — it may be inaccurate, incomplete, or stale, and past patterns don't guarantee future results. Always do your own research and consult a qualified professional before investing.

---

Built by **Muntasir Contractor** · [Email](mailto:muntasir.contractor06@gmail.com) · [LinkedIn](https://www.linkedin.com/in/muntasir-contractor06) · [GitHub](https://github.com/Muntasir-Contractor)
