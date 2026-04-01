<div align="center">

# Stockish

### Multi-Model Valuation | Forward Return Classification | AI Sentiment Analysis

A full-stack equity research tool that estimates intrinsic value through multiple valuation models, classifies forward return potential with an XGBoost model trained on fundamental data, and surfaces AI-driven market sentiment from recent news — all in real time.

> **This application is for educational and research purposes only. Nothing presented by Stockish constitutes financial advice, a recommendation to buy or sell any security, or a guarantee of prediction accuracy. All model outputs are analytical estimates based on historical data and publicly available information. Always conduct your own due diligence and consult a qualified financial advisor before making any investment decisions.**

[Features](#features) · [How It Works](#how-it-works) · [Tech Stack](#tech-stack) · [Getting Started](#getting-started) · [API Reference](#api-reference)

---

</div>

## Features

### Multi-Model Intrinsic Value Estimation

Stockish estimates a stock's fair value using five valuation methodologies, automatically selecting the most appropriate model based on the company's financial profile:

- **DCF (Discounted Cash Flow)** — Projects future free cash flows, discounts them to present value using WACC, and adds a terminal value via the Gordon Growth Model. Includes Blume beta adjustment, FCF growth fade, and multi-tier fallback growth rates.
- **P/E Comparable** — Applies sector-median trailing P/E multiples to the company's earnings per share.
- **Revenue Multiple (P/S)** — Values the company on revenue rather than earnings — useful for high-growth or pre-profit companies where P/E is unreliable.
- **Dividend Discount Model (DDM)** — For dividend-paying stocks with 5+ years of history, estimates fair value as the present value of expected future dividends.
- **Book Value (P/B)** — Applies sector-median price-to-book ratios — best suited for financials, real estate, and capital-intensive industries.

Each model returns a fair value estimate, a confidence level (High / Medium / Low), and any warnings about the assumptions used. The primary model is chosen by a decision tree that considers sector, dividend history, growth profile, and data availability.

### Forward Return Classification

An XGBoost classifier trained on historical fundamental data predicts which decile (0–9) a stock's forward 1-year return is likely to fall into. The model uses nine features:

| Feature | What It Captures |
|---|---|
| Gross Profitability | Earning power relative to assets |
| ROIC | Capital allocation efficiency |
| FCF Yield | Cash generation relative to market cap |
| Revenue Growth YoY | Top-line momentum |
| 6-Month Price Momentum | Recent price trend |
| EV/EBITDA | Enterprise valuation multiple |
| Accrual Ratio | Earnings quality |
| Interest Coverage | Debt servicing capacity |
| Shares Outstanding Growth | Dilution or buyback activity |

A stock classified in decile 9, for example, means its current fundamentals historically correspond to the top 10% of forward returns.

### AI Market Sentiment Analysis

Recent headlines are fetched from Yahoo Finance and analyzed by OpenAI, which returns:

- A **sentiment scalar** (0.5–1.5) representing how current news should adjust fair value expectations (1.0 = neutral)
- **Structured insights** — 3 to 5 thematic summaries, each tagged Bullish, Bearish, or Neutral with reasoning grounded in the actual headlines

Sentiment results are cached per ticker for 24 hours. Analysis is rate-limited to 3 requests per IP per day.

### Composite Model Score

All three signals — valuation gap, forward return decile, and sentiment scalar — are combined into a single weighted composite score (-1 to +1):

| Signal | Weight |
|---|---|
| Valuation (upside/downside %) | 50% (adjusted by confidence) |
| Forward Return Classification | 30% |
| AI Sentiment | 20% |

The composite score produces a verdict ranging from historically weak to historically strong patterns, with a confidence level based on how many signals are available.

### Market Overview & Search

- **Top Movers / Gainers / Losers** — Live market data via Financial Modeling Prep
- **Ticker Search** — Fast symbol lookup by name or ticker
- **ETF Detection** — ETFs are automatically identified and excluded from valuation and classification

---

## How It Works

```
User searches for a stock
         │
         ▼
┌─────────────────────────────────────────────┐
│              FastAPI Backend                 │
│                                             │
│  ┌─────────────┐  ┌──────────────────────┐  │
│  │  yfinance    │  │  Financial Modeling   │  │
│  │  (live data) │  │  Prep API            │  │
│  └──────┬──────┘  └──────────┬───────────┘  │
│         │                    │               │
│         ▼                    ▼               │
│  ┌─────────────────────────────────────┐     │
│  │     Valuation Engine                │     │
│  │  DCF · P/E · P/S · DDM · P/B       │     │
│  └─────────────────┬───────────────────┘     │
│                    │                         │
│  ┌─────────────────┴───────────────────┐     │
│  │  XGBoost Forward Return Classifier  │     │
│  │  (9 fundamental features → decile)  │     │
│  └─────────────────┬───────────────────┘     │
│                    │                         │
│  ┌─────────────────┴───────────────────┐     │
│  │  OpenAI Sentiment Analysis          │     │
│  │  (news headlines → scalar + insights)│    │
│  └─────────────────┬───────────────────┘     │
│                    │                         │
│         ┌──────────┴──────────┐              │
│         │  Composite Score    │              │
│         │  (weighted blend)   │              │
│         └──────────┬──────────┘              │
│                    │                         │
│              PostgreSQL Cache                │
└────────────────────┬────────────────────────┘
                     │
                     ▼
          React Frontend (Vite)
```

Valuation results are cached until new financial statements are published. Forward return classification and sentiment are fetched asynchronously in parallel for fast response times.

---

## Tech Stack

| Layer | Tools |
|---|---|
| **Backend** | Python 3.10+, FastAPI, Uvicorn |
| **ML** | XGBoost (multi-class classifier), scikit-learn, joblib |
| **AI / NLP** | OpenAI API (async) |
| **Data Sources** | yfinance, Financial Modeling Prep API |
| **Database** | PostgreSQL (psycopg2) |
| **HTTP Client** | httpx (async) |
| **Frontend** | React 19, React Router, Vite, Axios |

---

## Getting Started

### Prerequisites
- Python 3.10+
- Node.js
- PostgreSQL
- OpenAI API key
- Financial Modeling Prep API key

### 1. Clone the repo

```bash
git clone https://github.com/Muntasir-Contractor/StockInsight-ML.git
cd StockInsight-ML
```

### 2. Set up environment variables

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=your_openai_key
FINANCE_KEY=your_financial_modeling_prep_key
DB_PASSWORD=your_postgres_password
```

### 3. Install dependencies & start the backend

```bash
pip install -r requirements.txt
cd backend
uvicorn main:app --reload
```

### 4. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/stock/{ticker}` | Intrinsic value (all models), current price, valuation label, forward return decile, composite score |
| `GET` | `/stocksentiment/{ticker}` | Sentiment scalar (0.5–1.5), structured insights, remaining daily analyses |
| `GET` | `/search/{query}` | Symbol search results (name + ticker, deduplicated) |
| `GET` | `/topmovers` | Most actively traded stocks |
| `GET` | `/topgainers` | Biggest daily percentage gainers |
| `GET` | `/toplosers` | Biggest daily percentage losers |

---

## Project Structure

```
StockInsight-ML/
├── backend/
│   ├── main.py                  # FastAPI app, CORS, route handlers
│   ├── application.py           # Valuation orchestration, FR prediction, composite scoring
│   ├── newssentiment.py         # OpenAI sentiment analysis
│   ├── fetchnews.py             # Yahoo Finance news fetching
│   ├── fetchfromAPI.py          # Financial Modeling Prep API client
│   ├── db_funcs.py              # PostgreSQL operations (sentiment, rate limits, valuations)
│   └── model/
│       └── XGBoost_newestfr_model.joblib
├── scripts/
│   ├── valuation_models.py      # DCF, P/E, P/S, DDM, P/B implementations
│   ├── fetch_fr_stockdata.py    # Forward return feature extraction
│   ├── train_forwardreturn_model.py  # XGBoost training + Optuna hyperparameter tuning
│   └── ...
├── frontend/
│   ├── src/
│   │   ├── App.jsx              # Home page — search, market movers
│   │   ├── StockDetail.jsx      # Detail page — valuations, FR, sentiment, composite
│   │   └── components/
│   │       └── api.js           # Axios HTTP client
│   └── package.json
├── requirements.txt
└── README.md
```

---

## Disclaimer

> **Stockish is built for educational and research purposes only.** It is not a registered investment advisor and does not provide financial advice. All valuation estimates, forward return classifications, and sentiment analyses are model-generated outputs based on historical data and publicly available information. They should not be interpreted as buy, sell, or hold recommendations. Model outputs may be inaccurate, incomplete, or based on stale data. Past patterns do not guarantee future results. Always do your own research and consult a qualified financial professional before making investment decisions.

---

<div align="center">

**Built by Muntasir Contractor**

[muntasir.contractor06@gmail.com](mailto:muntasir.contractor06@gmail.com) · [LinkedIn](https://www.linkedin.com/in/muntasir-contractor06) · [GitHub](https://github.com/Muntasir-Contractor)

</div>
