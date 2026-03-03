# StockInsight-ML

A full-stack stock analysis tool that combines machine learning price prediction with AI-powered news sentiment analysis to help evaluate whether a stock is overvalued or undervalued.

---

## Overview

StockInsight-ML pulls real-time stock data from Yahoo Finance and financial APIs, runs it through a trained XGBoost model to predict fair value, and uses OpenAI to analyze recent news sentiment — all served through a FastAPI backend and React frontend.

---

## Features

- **ML Price Prediction** — XGBoost model trained on fundamental financial metrics (PE ratios, margins, growth rates, leverage, etc.) predicts a fair value price for a given stock
- **Valuation Rating** — Compares predicted price to current market price and labels the stock: Significantly/Moderately/Slightly Overvalued or Undervalued, or Fairly Valued
- **News Sentiment Analysis** — Fetches recent headlines via Yahoo Finance and passes them to OpenAI, which returns a sentiment scalar (0.5–1.5) and structured insights (Bullish / Bearish / Neutral)
- **Sentiment Caching** — SQLite database caches sentiment results per ticker for 24 hours to minimize redundant API calls
- **Market Overview** — Endpoints for top movers, biggest gainers, and biggest losers via Financial Modeling Prep API
- **Ticker Search** — Symbol search endpoint backed by Financial Modeling Prep
- **ETF Detection** — ETFs are detected and excluded from valuation/sentiment (which only apply to equities)

---

## Tech Stack

**Backend**
- Python 3.10+
- FastAPI + Uvicorn
- XGBoost (company valuation model)
- OpenAI API (async, news sentiment)
- yfinance (stock data + news headlines)
- SQLite (sentiment cache, querying to find top picks)
- httpx (async HTTP to external APIs)

**Frontend**
- React + Vite
- Axios

**Data Sources**
- Yahoo Finance (yfinance) — stock fundamentals and news
- Financial Modeling Prep API — top movers/gainers/losers, symbol search

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/stock/{ticker}` | Predicted price, current price, valuation label, sMAPE |
| GET | `/stocksentiment/{ticker}` | Sentiment scalar + AI-generated insights |
| GET | `/search/{query}` | Symbol search results |
| GET | `/topmovers` | Most active stocks |
| GET | `/topgainers` | Biggest daily gainers |
| GET | `/toplosers` | Biggest daily losers |

---

## Getting Started

### 1. Clone the repository
```bash
git clone https://github.com/Muntasir-Contractor/StockInsight-ML.git
cd StockInsight-ML
```

### 2. Set up environment variables

Create a `.env` file in the project root:
```
OPENAI_API_KEY=your_openai_key
FINANCE_KEY=your_financial_modeling_prep_key
```

### 3. Install Python dependencies
```bash
pip install -r requirements.txt
```

### 4. Start the backend
```bash
cd backend
uvicorn main:app --reload
```

### 5. Start the frontend
```bash
cd frontend
npm install
npm run dev
```

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

This tool is for educational and research purposes only. It does not provide financial advice or guaranteed predictions. Always conduct your own due diligence before making investment decisions.

---

## Author

Muntasir Contractor
- Email: muntasir.contractor06@gmail.com
- [LinkedIn](https://www.linkedin.com/in/muntasir-contractor06)
- [GitHub](https://github.com/Muntasir-Contractor)