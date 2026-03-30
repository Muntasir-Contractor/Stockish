import { useEffect, useState, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from './components/api.js';
import './StockDetail.css';

// Logokit helpers for ticker logo + fallback
const LOGOKIT_TOKEN = 'pk_fr2e451b952a202aafbaec';
const getLogo = (symbol) => {
  if (!symbol) return '';
  return `https://img.logokit.com/ticker/${encodeURIComponent(symbol)}?token=${LOGOKIT_TOKEN}`;
};
const getAvatarFallback = (name, bg = '1976d2') => {
  return `https://ui-avatars.com/api/?name=${encodeURIComponent(name)}&size=256&rounded=false&color=ffffff&background=${bg}`;
};

// Client-side final analysis (mirrors backend logic)
function computeFinalAnalysis(upsidePct, frPrediction, sentimentScalar) {
  const signals = [];

  if (upsidePct != null) {
    const dcfScore = Math.max(-1, Math.min(1, upsidePct / 50));
    signals.push({ name: 'dcf', score: dcfScore, weight: 0.50 });
  }
  if (frPrediction != null) {
    const frScore = (frPrediction - 4.5) / 4.5;
    signals.push({ name: 'fr', score: frScore, weight: 0.30 });
  }
  if (sentimentScalar != null) {
    const sentScore = (sentimentScalar - 1.0) / 0.5;
    signals.push({ name: 'sentiment', score: sentScore, weight: 0.20 });
  }

  if (signals.length === 0) return null;

  const totalWeight = signals.reduce((s, x) => s + x.weight, 0);
  const composite = signals.reduce((s, x) => s + (x.score * x.weight / totalWeight), 0);

  let verdict;
  if (composite > 0.50) verdict = 'Strong Buy';
  else if (composite > 0.20) verdict = 'Buy';
  else if (composite > -0.20) verdict = 'Hold';
  else if (composite > -0.50) verdict = 'Sell';
  else verdict = 'Strong Sell';

  const confidence = signals.length >= 3 ? 'High' : signals.length === 2 ? 'Medium' : 'Low';

  return { verdict, composite, confidence, signalsUsed: signals.length };
}

const verdictColor = (verdict) => {
  const map = {
    'Strong Buy': '#2e7d32',
    'Buy': '#4caf50',
    'Hold': '#666666',
    'Sell': '#e74c3c',
    'Strong Sell': '#c62828',
  };
  return map[verdict] || '#666';
};

const confidenceColor = (confidence) => {
  const map = { 'High': '#2e7d32', 'Medium': '#f59e0b', 'Low': '#e74c3c' };
  return map[confidence] || '#666';
};


function StockDetail() {
  const { ticker } = useParams();
  const navigate = useNavigate();
  const [stockData, setStockData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [insights, setInsights] = useState(null);
  const [insightsLoading, setInsightsLoading] = useState(false);
  const [insightsError, setInsightsError] = useState(null);
  const [remaining, setRemaining] = useState(null);

  useEffect(() => {
    const fetchStockData = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await api.get(`/stock/${ticker.toUpperCase()}`);
        setStockData(response.data);
      } catch (err) {
        console.error("Failed to fetch stock:", err);
        setError("Failed to load stock data");
      } finally {
        setLoading(false);
      }
    };

    fetchStockData();
    setInsights(null);
    setInsightsError(null);
    setRemaining(null);
  }, [ticker]);

  const handleGetInsights = async () => {
    try {
      setInsightsLoading(true);
      setInsightsError(null);
      const response = await api.get(`/stocksentiment/${ticker.toUpperCase()}`);
      if (response.data.scalar === null && response.data.insights === null) {
        setInsightsError("No recent news coverage found for this stock. Sentiment analysis is unavailable.");
        setRemaining(response.data.remaining);
        return;
      }
      setInsights(response.data);
      setRemaining(response.data.remaining);
    } catch (err) {
      if (err.response?.status === 429) {
        setInsightsError("Daily limit reached. Try again tomorrow.");
        setRemaining(0);
      } else {
        console.error("Failed to fetch insights:", err);
        setInsightsError("Failed to load stock insights");
      }
    } finally {
      setInsightsLoading(false);
    }
  };

  // Recompute final analysis client-side when sentiment arrives
  const finalAnalysis = useMemo(() => {
    if (!stockData) return null;
    const sentimentScalar = insights?.scalar ?? null;
    return computeFinalAnalysis(stockData.upside_pct, stockData.fr_prediction, sentimentScalar);
  }, [stockData, insights]);

  if (loading) {
    return (
      <div className="stock-detail-page">
        <div className="navbar-placeholder"></div>
        <div className="loading">Loading {ticker}...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="stock-detail-page">
        <div className="navbar-placeholder"></div>
        <div className="error">
          <h2>{error}</h2>
          <button onClick={() => navigate('/')}>Go Home</button>
        </div>
      </div>
    );
  }

  // Derived values
  const currentPrice = stockData?.current_price;
  const intrinsicValue = stockData?.intrinsic_value;
  const upsidePct = stockData?.upside_pct;
  const frPrediction = stockData?.fr_prediction;

  const hasCurrent = currentPrice != null && !Number.isNaN(currentPrice);
  const hasIntrinsic = intrinsicValue != null && !Number.isNaN(intrinsicValue);
  const hasUpside = upsidePct != null && !Number.isNaN(upsidePct);
  const hasFr = frPrediction != null && !Number.isNaN(frPrediction);
  const isEtf = stockData?.valuation === 'Cannot Valuate ETF';

  const frLabel = (decile) => {
    const low = decile * 10;
    const high = low + 10;
    const percentile = decile === 9 ? 'top 10%' : decile === 0 ? 'bottom 10%' : `${low}\u2013${high}th percentile`;
    const color =
      decile >= 8 ? '#2e7d32' :
      decile >= 6 ? '#4caf50' :
      decile >= 4 ? '#666666' :
      decile >= 2 ? '#e74c3c' : '#c62828';
    return {
      label: `Fundamentals match the ${percentile} of historical 1-yr forward returners`,
      color,
    };
  };

  const valuationColorFromLabel = (label) => {
    if (!label) return '#666';
    const map = {
      'Significantly Overvalued': '#c62828',
      'Moderately Overvalued': '#e74c3c',
      'Slightly Overvalued': '#ff8a65',
      'Fairly Valued': '#666666',
      'Slightly Undervalued': '#8bc34a',
      'Moderately Undervalued': '#4caf50',
      'Significantly Undervalued': '#2e7d32',
      'Cannot Valuate ETF': '#666666',
      'Unavailable': '#666666',
    };
    return map[label] || '#666';
  };

  return (
    <div className="stock-detail-page">
      <div className="navbar-placeholder"></div>

      <div className="stock-detail-container">
        <button className="back-btn" onClick={() => navigate('/')}>
          &larr; Back to Home
        </button>

        <div className="stock-header">
          {stockData?.ticker && (
            <img
              src={getLogo(stockData.ticker)}
              alt={`${stockData.ticker} logo`}
              className="stock-header-badge"
              onError={(e) => { e.currentTarget.onerror = null; e.currentTarget.src = getAvatarFallback(stockData.ticker); }}
              loading="lazy"
            />
          )}
          <h1>{stockData.ticker}</h1>
          <div className="current-price-big">
            {hasCurrent ? `$${currentPrice.toFixed(2)}` : 'N/A'}
          </div>
        </div>

        {/* Final Analysis Hero Card */}
        {finalAnalysis && (
          <div className="final-analysis-card">
            <div className="final-analysis-header">
              <h2 className="final-analysis-title">Final Analysis</h2>
              <span className="confidence-badge" style={{ color: confidenceColor(finalAnalysis.confidence) }}>
                {finalAnalysis.confidence} Confidence
              </span>
            </div>
            <div className="final-analysis-verdict" style={{ color: verdictColor(finalAnalysis.verdict) }}>
              {finalAnalysis.verdict}
            </div>
            <div className="final-analysis-gauge">
              <span className="gauge-label-left">Strong Sell</span>
              <div className="gauge-track">
                <div
                  className="gauge-marker"
                  style={{ left: `${((finalAnalysis.composite + 1) / 2) * 100}%` }}
                />
              </div>
              <span className="gauge-label-right">Strong Buy</span>
            </div>
            <div className="final-analysis-signals">
              {hasUpside && (
                <span className="signal-chip">
                  DCF: {upsidePct > 0 ? '+' : ''}{upsidePct.toFixed(1)}% upside
                </span>
              )}
              {hasFr && (
                <span className="signal-chip">
                  Fundamentals: Decile {frPrediction}
                </span>
              )}
              {insights ? (
                <span className="signal-chip">
                  Sentiment: {insights.scalar.toFixed(2)}
                </span>
              ) : (
                <span className="signal-chip signal-chip-missing">
                  Sentiment: Not yet analyzed
                </span>
              )}
            </div>
          </div>
        )}

        {!finalAnalysis && !isEtf && (
          <div className="final-analysis-card">
            <div className="final-analysis-verdict" style={{ color: '#666' }}>
              Insufficient data for analysis
            </div>
          </div>
        )}

        <div className="stock-info-grid">
          <div className="info-card">
            <div className="info-label">Intrinsic Value (DCF)
              <span className="info-help" tabIndex="0" aria-label="More info">&#8505;
                <span className="tooltip">Discounted Cash Flow valuation based on projected free cash flows and WACC.</span>
              </span>
            </div>
            <div className="info-value">
              {hasIntrinsic ? `$${intrinsicValue.toFixed(2)}` : isEtf ? 'Cannot value ETF' : 'Unavailable'}
            </div>
          </div>

          <div className="info-card">
            <div className="info-label">Valuation
              <span className="info-help" tabIndex="0" aria-label="More info">&#8505;
                <span className="tooltip">Based on intrinsic value vs. current market price. This is not financial advice.</span>
              </span>
            </div>
            <div className="info-value" style={{ color: valuationColorFromLabel(stockData.valuation) }}>
              {stockData.valuation || 'N/A'}
            </div>
          </div>

          <div className="info-card">
            <div className="info-label">Upside / Downside
              <span className="info-help" tabIndex="0" aria-label="More info">&#8505;
                <span className="tooltip">Percentage difference between intrinsic value and current price. Positive means undervalued.</span>
              </span>
            </div>
            <div className={`info-value ${hasUpside ? (upsidePct >= 0 ? 'positive' : 'negative') : ''}`}>
              {hasUpside ? `${upsidePct > 0 ? '+' : ''}${upsidePct.toFixed(1)}%` : 'N/A'}
            </div>
          </div>

          <div className="info-card">
            <div className="info-label">Forward Return Classification
              <span className="info-help" tabIndex="0" aria-label="More info">&#8505;
                <span className="tooltip">XGBoost-predicted return decile (0-9) based on fundamental quality and momentum signals. Higher deciles indicate stronger expected forward returns.</span>
              </span>
            </div>
            <div className="info-value" style={{ color: hasFr ? frLabel(frPrediction).color : '#666' }}>
              {hasFr ? frLabel(frPrediction).label : isEtf ? 'Cannot classify ETF' : 'N/A'}
            </div>
          </div>

          <div className="info-card">
            <div className="info-label">AI Market Sentiment Analysis Score</div>
            {insights ? (
              <div
                className={`info-value ${insights.scalar > 1.03 ? 'positive' : insights.scalar < 0.97 ? 'negative' : ''}`}
              >
                {insights.scalar.toFixed(2)}
              </div>
            ) : (
              <button
                className="get-insights-btn sentiment-card-btn"
                onClick={handleGetInsights}
                disabled={insightsLoading || remaining === 0}
              >
                {insightsLoading ? 'Analyzing\u2026' : remaining === 0 ? 'Limit reached' : 'Get Score'}
              </button>
            )}
          </div>
        </div>

        <div className="insights-section">
          <div className="insights-header-row">
            <h2 className="insights-title">AI Market Sentiment Insights</h2>
            <div className="insights-btn-wrap">
              <button
                className="get-insights-btn"
                onClick={handleGetInsights}
                disabled={insightsLoading || remaining === 0}
              >
                {insightsLoading
                  ? 'Analyzing\u2026'
                  : insights
                  ? 'Refresh Analysis'
                  : 'Get Sentiment Analysis'}
              </button>
              {remaining !== null && (
                <span className={`insights-remaining ${remaining === 0 ? 'exhausted' : ''}`}>
                  {remaining === 0 ? 'No analyses left today' : `${remaining} of ${3} remaining today`}
                </span>
              )}
            </div>
          </div>

          {insightsLoading && (
            <div className="insights-loading">Analyzing market sentiment for {ticker.toUpperCase()}\u2026</div>
          )}

          {insightsError && !insightsLoading && (
            <div className="insights-error">{insightsError}</div>
          )}

          {insights && !insightsLoading && (
            <>
              <div className="insights-scalar-bar">
                <span className="insights-scalar-label">Sentiment Score</span>
                <div className="insights-scalar-track">
                  <div
                    className="insights-scalar-fill"
                    style={{ width: `${Math.min(Math.max((insights.scalar - 0.5) / 1.0, 0), 1) * 100}%` }}
                  />
                  <span
                    className="insights-scalar-marker"
                    style={{ left: `${Math.min(Math.max((insights.scalar - 0.5) / 1.0, 0), 1) * 100}%` }}
                  />
                </div>
                <span
                  className={`insights-scalar-value ${insights.scalar > 1.03 ? 'bullish' : insights.scalar < 0.97 ? 'bearish' : 'neutral'}`}
                >
                  {insights.scalar.toFixed(2)}
                  &nbsp;&middot;&nbsp;
                  {insights.scalar > 1.03 ? 'Bullish' : insights.scalar < 0.97 ? 'Bearish' : 'Neutral'}
                </span>
              </div>

              <div className="insights-cards">
                {insights.insights.map((item, i) => (
                  <div key={i} className={`insight-card sentiment-${item.sentiment.toLowerCase()}`}>
                    <div className="insight-card-header">
                      <span className="insight-title">{item.insight}</span>
                      <span className={`insight-badge ${item.sentiment.toLowerCase()}`}>{item.sentiment}</span>
                    </div>
                    <p className="insight-reasoning">{item.reasoning}</p>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default StockDetail;
