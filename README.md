<div align="center">

# 📈 Stockish

### ML-Powered Stock Valuation & AI Sentiment Analysis

**Is the market pricing it right? Stockish finds out.**

Stockish combines a trained XGBoost model with AI-driven news sentiment analysis to give you a data-backed view of whether a stock is overvalued or undervalued — all in real time.

[Getting Started](#getting-started) · [Features](#features) · [Tech Stack](#tech-stack) · [API Reference](#api-reference)

---

</div>

## What It Does

Stockish pulls live stock data from Yahoo Finance, runs it through a machine learning model trained on fundamental financial metrics, and uses OpenAI to analyze recent news sentiment — then wraps it all in a clean React frontend and FastAPI backend.

The result: a valuation label, a predicted fair value price, and structured AI insights on market sentiment — all in one place.

---

## Features

### 🤖 ML Price Prediction
An XGBoost model trained on real fundamental data — PE ratios, profit margins, growth rates, leverage ratios, and more — predicts a stock's fair value price.

### ⚖️ Valuation Rating
Compares the predicted price against the current market price and labels the stock:

> `Significantly Overvalued` · `Moderately Overvalued` · `Slightly Overvalued`  
> `Fairly Valued`  
> `Slightly Undervalued` · `Moderately Undervalued` · `Significantly Undervalued`

### 📰 News Sentiment Analysis
Fetches recent headlines via Yahoo Finance and sends them to OpenAI, which returns a sentiment scalar (0.5–1.5) and structured Bullish / Bearish / Neutral insights.

### ⚡ Sentiment Caching
SQLite caches sentiment results per ticker for 24 hours — minimizing redundant API calls and keeping responses fast.

### 🌍 Market Overview
Live endpoints for top movers, biggest gainers, and biggest losers via the Financial Modeling Prep API.

### 🔍 Ticker Search
Fast symbol search backed by Financial Modeling Prep — find any equity by name or ticker.

### 🚫 ETF Detection
ETFs are automatically detected and excluded from valuation and sentiment analysis, which only apply to individual equities.

---

## Tech Stack

| Layer | Tools |
|---|---|
| **Backend** | Python 3.10+, FastAPI, Uvicorn |
| **ML Model** | XGBoost |
| **AI / NLP** | OpenAI API (async) |
| **Data** | yfinance, Financial Modeling Prep API |
| **Database** | SQLite |
| **HTTP Client** | httpx (async) |
| **Frontend** | React + Vite, Axios |

---

## Getting Started

### Prerequisites
- Python 3.10+
- Node.js
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
| `GET` | `/stock/{ticker}` | Predicted price, current price, valuation label, sMAPE |
| `GET` | `/stocksentiment/{ticker}` | Sentiment scalar + AI-generated insights |
| `GET` | `/search/{query}` | Symbol search results |
| `GET` | `/topmovers` | Most active stocks |
| `GET` | `/topgainers` | Biggest daily gainers |
| `GET` | `/toplosers` | Biggest daily losers |

---

## Project Structure

```
StockInsight-ML/
├── backend/
│   ├── main.py              # FastAPI app and route handlers
│   ├── application.py       # Price prediction and valuation logic
│   ├── newssentiment.py     # OpenAI sentiment analysis
│   ├── fetchnews.py         # Yahoo Finance news fetching
│   ├── fetchfromAPI.py      # Financial Modeling Prep API calls
│   ├── dbfuncs.py           # SQLite sentiment cache operations
│   └── model/
│       └── XGboost_model.joblib
├── scripts/
│   ├── scrape.py            # Stock data scraping
│   └── train_model.py       # Model training pipeline
├── frontend/
│   └── src/
│       ├── App.jsx
│       ├── StockDetail.jsx
│       └── components/
└── requirements.txt
```

---

## Disclaimer

> Stockish is built for **educational and research purposes only**. It does not provide financial advice or guarantee prediction accuracy. Always do your own due diligence before making any investment decisions.

---

<div align="center">

**Built by Muntasir Contractor**

[muntasir.contractor06@gmail.com](mailto:muntasir.contractor06@gmail.com) · [LinkedIn](https://www.linkedin.com/in/muntasir-contractor06) · [GitHub](https://github.com/Muntasir-Contractor)

</div>
