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

const modelLabel = {
  dcf: 'DCF',
  pe_comparable: 'P/E Comparable',
  revenue_multiple: 'Revenue Multiple',
  ddm: 'Dividend Discount',
  book_value: 'Book Value',
};

// Client-side final analysis (mirrors backend logic)
function computeFinalAnalysis(upsidePct, frPrediction, sentimentScalar, dcfConfidence) {
  const signals = [];

  if (upsidePct != null) {
    const valScore = Math.max(-1, Math.min(1, upsidePct / 50));
    const confMultiplier = { high: 1.0, medium: 0.5, low: 0.25 }[dcfConfidence] ?? 1.0;
    signals.push({ name: 'valuation', score: valScore, weight: 0.50 * confMultiplier });
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
  if (composite > 0.50) verdict = 'Strong Bullish Signal';
  else if (composite > 0.20) verdict = 'Bullish Signal';
  else if (composite > -0.20) verdict = 'Neutral Signal';
  else if (composite > -0.50) verdict = 'Bearish Signal';
  else verdict = 'Strong Bearish Signal';

  const confidence = signals.length >= 3 ? 'High' : signals.length === 2 ? 'Medium' : 'Low';

  return { verdict, composite, confidence, signalsUsed: signals.length };
}

const verdictColor = (verdict) => {
  const map = {
    'Strong Bullish Signal': '#2e7d32',
    'Bullish Signal': '#4caf50',
    'Neutral Signal': '#666666',
    'Bearish Signal': '#e74c3c',
    'Strong Bearish Signal': '#c62828',
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
  const [showAllModels, setShowAllModels] = useState(false);

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
    return computeFinalAnalysis(stockData.upside_pct, stockData.fr_prediction, sentimentScalar, stockData.dcf_confidence);
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

  const dcfConfidence = stockData?.dcf_confidence;
  const dcfWarnings = stockData?.dcf_warnings || [];

  const hasCurrent = currentPrice != null && !Number.isNaN(currentPrice);
  const hasIntrinsic = intrinsicValue != null && !Number.isNaN(intrinsicValue);
  const hasUpside = upsidePct != null && !Number.isNaN(upsidePct);
  const hasFr = frPrediction != null && !Number.isNaN(frPrediction);
  const isEtf = stockData?.valuation === 'Cannot Valuate ETF';

  const dcfConfidenceColor = (level) => {
    const map = { high: '#2e7d32', medium: '#f59e0b', low: '#e74c3c' };
    return map[level] || '#666';
  };

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
      label: `Fundamentals ranked in the ${percentile} of historical patterns`,
      color,
    };
  };

  const valuationColorFromLabel = (label) => {
    if (!label) return '#666';
    const map = {
      'Strong Downside Signal': '#c62828',
      'Moderate Downside Signal': '#e74c3c',
      'Slight Downside Signal': '#ff8a65',
      'Near Fair Value': '#666666',
      'Slight Upside Signal': '#8bc34a',
      'Moderate Upside Signal': '#4caf50',
      'Strong Upside Signal': '#2e7d32',
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

        <div className="disclaimer-banner">
          This is not financial advice. The creator of this tool is not a financial advisor. All signals, scores, and estimates shown here are generated by mathematical models and machine learning algorithms for educational and informational purposes only. They do not constitute a recommendation to buy, sell, or hold any security. Always do your own research and consult a qualified financial advisor before making investment decisions.
        </div>

        {/* Final Analysis Hero Card */}
        {finalAnalysis && (
          <div className="final-analysis-card">
            <div className="final-analysis-header">
              <h2 className="final-analysis-title">Composite Signal</h2>
              <span className="confidence-badge" style={{ color: confidenceColor(finalAnalysis.confidence) }}>
                {finalAnalysis.confidence} Confidence
              </span>
            </div>
            <div className="final-analysis-verdict" style={{ color: verdictColor(finalAnalysis.verdict) }}>
              {finalAnalysis.verdict}
            </div>
            <div className="final-analysis-gauge">
              <span className="gauge-label-left">Bearish</span>
              <div className="gauge-track">
                <div
                  className="gauge-marker"
                  style={{ left: `${((finalAnalysis.composite + 1) / 2) * 100}%` }}
                />
              </div>
              <span className="gauge-label-right">Bullish</span>
            </div>
            <div className="final-analysis-signals">
              {hasUpside && (
                <span className="signal-chip">
                  {modelLabel[stockData.primary_model] || 'DCF'}: {upsidePct > 0 ? '+' : ''}{upsidePct.toFixed(1)}% upside
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
              Insufficient data for signal
            </div>
          </div>
        )}

        <div className="stock-info-grid">
          <div className="info-card">
            <div className="info-label">Intrinsic Value ({modelLabel[stockData.primary_model] || 'DCF'})
              <span className="info-help" tabIndex="0" aria-label="More info">&#8505;
                <span className="tooltip">Model-estimated value based on the best-fit valuation model for this stock. This is a mathematical estimate, not a price target.</span>
              </span>
            </div>
            <div className="info-value">
              {hasIntrinsic ? `$${intrinsicValue.toFixed(2)}` : isEtf ? 'Cannot value ETF' : 'Unavailable'}
            </div>
            {dcfConfidence && (
              <div className="dcf-confidence-row">
                <span className="dcf-confidence-badge" style={{ color: dcfConfidenceColor(dcfConfidence) }}>
                  {dcfConfidence.charAt(0).toUpperCase() + dcfConfidence.slice(1)} Confidence
                </span>
                {dcfWarnings.length > 0 && (
                  <span className="info-help" tabIndex="0" aria-label="DCF warnings">&#9888;
                    <span className="tooltip tooltip-wide">{dcfWarnings.join(' | ')}</span>
                  </span>
                )}
              </div>
            )}
          </div>

          <div className="info-card">
            <div className="info-label">Model Signal
              <span className="info-help" tabIndex="0" aria-label="More info">&#8505;
                <span className="tooltip">Mathematical comparison of model estimate vs. market price. Not a recommendation to buy or sell.</span>
              </span>
            </div>
            <div className="info-value" style={{ color: valuationColorFromLabel(stockData.valuation) }}>
              {stockData.valuation || 'N/A'}
            </div>
          </div>

          <div className="info-card">
            <div className="info-label">Upside / Downside
              <span className="info-help" tabIndex="0" aria-label="More info">&#8505;
                <span className="tooltip">Percentage difference between the model estimate and current market price. This is a mathematical signal, not investment advice.</span>
              </span>
            </div>
            <div className={`info-value ${hasUpside ? (upsidePct >= 0 ? 'positive' : 'negative') : ''}`}>
              {hasUpside ? `${upsidePct > 0 ? '+' : ''}${upsidePct.toFixed(1)}%` : 'N/A'}
            </div>
          </div>

          <div className="info-card">
            <div className="info-label">Forward Return Classification
              <span className="info-help" tabIndex="0" aria-label="More info">&#8505;
                <span className="tooltip">ML-predicted return decile (0-9) based on historical fundamental patterns. Higher deciles historically correlated with stronger forward returns. Past patterns do not guarantee future results.</span>
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

        {stockData.models && stockData.models.length > 1 && (
          <div className="all-models-section">
            <button
              className="all-models-toggle"
              onClick={() => setShowAllModels(!showAllModels)}
            >
              {showAllModels ? 'Hide' : 'Show'} All Valuation Models ({stockData.models.length})
            </button>
            {showAllModels && (
              <div className="models-grid">
                {stockData.models.map((m) => (
                  <div
                    key={m.model_type}
                    className={`model-card${m.model_type === stockData.primary_model ? ' model-primary' : ''}`}
                  >
                    {m.model_type === stockData.primary_model && (
                      <span className="primary-badge">Primary</span>
                    )}
                    <div className="model-card-name">{modelLabel[m.model_type] || m.model_type}</div>
                    <div className="model-card-value">
                      {m.intrinsic_value != null ? `$${m.intrinsic_value.toFixed(2)}` : 'N/A'}
                    </div>
                    <div className={`model-card-upside ${m.upside_downside_pct != null ? (m.upside_downside_pct >= 0 ? 'positive' : 'negative') : ''}`}>
                      {m.upside_downside_pct != null ? `${m.upside_downside_pct > 0 ? '+' : ''}${m.upside_downside_pct.toFixed(1)}%` : 'N/A'}
                    </div>
                    <div className="model-card-confidence" style={{ color: dcfConfidenceColor(m.confidence) }}>
                      {m.confidence ? m.confidence.charAt(0).toUpperCase() + m.confidence.slice(1) : ''} Confidence
                    </div>
                    {m.warnings && m.warnings.length > 0 && (
                      <div className="model-card-warnings">
                        {m.warnings.map((w, i) => (
                          <span key={i} className="model-warning">{w}</span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

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

        <footer className="disclaimer-footer">
          All signals are generated by mathematical models (DCF, ML classifiers, AI sentiment analysis) for informational and educational purposes only. Nothing on this page constitutes financial advice or a recommendation. The creator is not a financial advisor. Always do your own research and consult a licensed professional before making investment decisions.
        </footer>
      </div>
    </div>
  );
}

export default StockDetail;
