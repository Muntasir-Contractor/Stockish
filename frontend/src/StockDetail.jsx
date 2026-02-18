import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from './components/api.js';
import './StockDetail.css';

// Logokit helpers for ticker logo + fallback
const LOGOKIT_TOKEN = 'pk_fr2e451b952a202aafbaec';
const getLogokitUrl = (symbol) => {
  if (!symbol) return '';
  return `https://img.logokit.com/ticker/${encodeURIComponent(symbol)}?token=${LOGOKIT_TOKEN}`;
};
const getAvatarFallback = (name, bg = '1976d2') => {
  return `https://ui-avatars.com/api/?name=${encodeURIComponent(name)}&size=256&rounded=false&color=ffffff&background=${bg}`;
};

function StockDetail() {
  const { ticker } = useParams();
  const navigate = useNavigate();
  const [stockData, setStockData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchStockData = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await api.get(`/stock/${ticker.toUpperCase()}`);
        console.log('Raw response:', response);
        console.log('Response Data:', response.data);
        setStockData(response.data);
      } catch (err) {
        console.error("Failed to fetch stock:", err);
        setError("Failed to load stock data");
      } finally {
        setLoading(false);
      }
    };

    fetchStockData();
  }, [ticker]);

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

  // Normalize numeric values and handle nulls/strings
  const currentPriceRaw = stockData?.current_price;
  const predictedPriceRaw = stockData?.predicted_price;
  const relativeErrorRaw = stockData?.relative_error;
  const smapeRaw = stockData?.smape;

  const currentPrice = typeof currentPriceRaw === 'number' ? currentPriceRaw : parseFloat(currentPriceRaw);
  const predictedPrice = typeof predictedPriceRaw === 'number' ? predictedPriceRaw : parseFloat(predictedPriceRaw);
  const relativeError = typeof relativeErrorRaw === 'number' ? relativeErrorRaw : parseFloat(relativeErrorRaw);
  const smape = typeof smapeRaw === 'number' ? smapeRaw : parseFloat(smapeRaw);

  const hasCurrent = !Number.isNaN(currentPrice) && currentPrice != null;
  const hasPredicted = !Number.isNaN(predictedPrice) && predictedPrice != null;
  const hasRelative = !Number.isNaN(relativeError) && relativeError != null;
  const hasSmape = !Number.isNaN(smape) && smape != null;

  const priceDiff = (hasCurrent && hasPredicted) ? Math.abs(predictedPrice - currentPrice) : null;

  // Compute a color for valuation: use relativeError for smooth gradient when available,
  // otherwise fall back to label-based mapping.
  const lerp = (a, b, t) => a + (b - a) * t;
  const hexToRgb = (hex) => {
    const h = hex.replace('#', '');
    return [parseInt(h.substring(0,2),16), parseInt(h.substring(2,4),16), parseInt(h.substring(4,6),16)];
  };
  const rgbToHex = (r,g,b) => '#'+[r,g,b].map(x=>x.toString(16).padStart(2,'0')).join('');

  // Use sMAPE magnitude to map from dark green (very good) -> bright red (very bad)
  const valuationColorFromSmape = (smapeVal) => {
    const GOOD = '#0b3d16'; // dark green (very good)
    const BAD = '#ff3b30';  // bright red (very bad)
    const [g1,g2,g3] = hexToRgb(GOOD);
    const [b1,b2,b3] = hexToRgb(BAD);
    const MAX = 0.3; // clamp sMAPE for color scale
    const t = Math.max(0, Math.min(1, (smapeVal || 0) / MAX));
    const ri = Math.round(lerp(g1, b1, t));
    const gi = Math.round(lerp(g2, b2, t));
    const bi = Math.round(lerp(g3, b3, t));
    return rgbToHex(ri, gi, bi);
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
      'Significantly Undervalued': '#2e7d32'
    };
    return map[label] || '#666';
  };

  const valuationColor = hasSmape ? valuationColorFromSmape(smape) : valuationColorFromLabel(stockData.valuation);
  const smapeColor = hasSmape ? valuationColorFromSmape(smape) : '#666';

  return (
    <div className="stock-detail-page">
      <div className="navbar-placeholder"></div>
      
      <div className="stock-detail-container">
        <button className="back-btn" onClick={() => navigate('/')}>
          ← Back to Home
        </button>

        <div className="stock-header">
          {stockData?.ticker && (
            <img
              src={getLogokitUrl(stockData.ticker)}
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

        <div className="stock-info-grid">
          <div className="info-card">
            <div className="info-label">Predicted Price</div>
            <div className="info-value">{hasPredicted ? `$${predictedPrice.toFixed(2)}` : 'N/A'}</div>
          </div>

          <div className="info-card">
            <div className="info-label">Valuation
              <span className="info-help" tabIndex="0" aria-label="More info">ℹ
                <span className="tooltip">This is not financial advice or a buy/sell indicator.</span>
              </span>
            </div>
            <div className="info-value" style={{ color: valuationColor }}>{stockData.valuation || 'N/A'}</div>
          </div>

          <div className="info-card">
            <div className="info-label">Relative Error
              <span className="info-help" tabIndex="0" aria-label="More info">ℹ
                <span className="tooltip">Signed percent difference: (predicted - current) / current — shows direction and magnitude.</span>
              </span>
            </div>
            <div className={`info-value ${hasRelative ? (relativeError >= 0 ? 'positive' : 'negative') : ''}`}>
              {hasRelative ? `${(relativeError * 100).toFixed(2)}%` : 'N/A'}
            </div>
          </div>

          <div className="info-card">
            <div className="info-label">sMAPE
              <span className="info-help" tabIndex="0" aria-label="More info">ℹ
                <span className="tooltip">Symmetric Mean Absolute Percentage Error — magnitude of prediction error.</span>
              </span>
            </div>
            <div className={`info-value`} style={{ color: smapeColor }}>
              {hasSmape ? `${(smape * 100).toFixed(2)}%` : 'N/A'}
            </div>
          </div>

          <div className="info-card">
            <div className="info-label">Price Difference
              <span className="info-help" tabIndex="0" aria-label="More info">ℹ
                <span className="tooltip">Absolute dollar difference between predicted and current price.</span>
              </span>
            </div>
            <div className={`info-value ${priceDiff !== null ? (predictedPrice >= currentPrice ? 'positive' : 'negative') : ''}`}>
              {priceDiff !== null ? `$${priceDiff.toFixed(2)}` : 'N/A'}
            </div>
          </div>

          <div className="info-card">
            <div className="info-label">AI Market Sentiment Analysis Score</div>
            <div className="info-value">None</div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default StockDetail;