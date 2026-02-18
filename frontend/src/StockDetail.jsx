import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from './components/api.js';
import './StockDetail.css';

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

  return (
    <div className="stock-detail-page">
      <div className="navbar-placeholder"></div>
      
      <div className="stock-detail-container">
        <button className="back-btn" onClick={() => navigate('/')}>
          ← Back to Home
        </button>

        <div className="stock-header">
          <h1>{stockData.ticker}</h1>
          <div className="current-price-big">
            ${stockData.current_price?.toFixed(2)}
          </div>
        </div>

        <div className="stock-info-grid">
          <div className="info-card">
            <div className="info-label">Predicted Price</div>
            <div className="info-value">${stockData.predicted_price?.toFixed(2)}</div>
          </div>

          <div className="info-card">
            <div className="info-label">Valuation</div>
            <div className="info-value">{stockData.valuation}</div>
          </div>

          <div className="info-card">
            <div className="info-label">Relative Error</div>
            <div className={`info-value ${stockData.relative_error >= 0 ? 'positive' : 'negative'}`}>
              {(stockData.relative_error * 100).toFixed(2)}%
            </div>
          </div>

          <div className="info-card">
            <div className="info-label">Price Difference</div>
            <div className={`info-value ${stockData.predicted_price >= stockData.current_price ? 'positive' : 'negative'}`}>
              ${Math.abs(stockData.predicted_price - stockData.current_price).toFixed(2)}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default StockDetail;