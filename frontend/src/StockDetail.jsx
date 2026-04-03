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
  if (composite > 0.50) verdict = 'Very Strong Composite';
  else if (composite > 0.20) verdict = 'Historically Strong Pattern';
  else if (composite > -0.20) verdict = 'Neutral Pattern';
  else if (composite > -0.50) verdict = 'Historically Weak Pattern';
  else verdict = 'Very Weak Composite';

  const confidence = signals.length >= 3 ? 'High' : signals.length === 2 ? 'Medium' : 'Low';

  return { verdict, composite, confidence, signalsUsed: signals.length };
}


const sensitivityLabel = (confidence) => {
  const map = { 'High': 'Low Assumption Sensitivity', 'Medium': 'Moderate Assumption Sensitivity', 'Low': 'High Assumption Sensitivity' };
  return map[confidence] || `${confidence} Sensitivity`;
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
  const [expandedModel, setExpandedModel] = useState(null);
  const [customAssumptions, setCustomAssumptions] = useState({});
  const [recalculating, setRecalculating] = useState(null);
  const [customResults, setCustomResults] = useState({});

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

  const handleAssumptionChange = (modelType, key, value) => {
    setCustomAssumptions(prev => ({
      ...prev,
      [modelType]: {
        ...prev[modelType],
        [key]: value,
      }
    }));
  };

  const getModifiedAssumptions = (modelType, assumptions) => {
    if (!assumptions || !customAssumptions[modelType]) return {};
    const modified = {};
    for (const [key, val] of Object.entries(customAssumptions[modelType])) {
      if (assumptions[key] && parseFloat(val) !== assumptions[key].value) {
        modified[key] = parseFloat(val);
      }
    }
    return modified;
  };

  const handleRecalculate = async (modelType, assumptions) => {
    const modified = getModifiedAssumptions(modelType, assumptions);
    if (Object.keys(modified).length === 0) return;
    setRecalculating(modelType);
    try {
      const response = await api.post(`/stock/${ticker.toUpperCase()}/recalculate`, {
        model_type: modelType,
        assumptions: modified,
      });
      setCustomResults(prev => ({
        ...prev,
        [modelType]: response.data,
      }));
    } catch (err) {
      console.error("Recalculation failed:", err);
    } finally {
      setRecalculating(null);
    }
  };

  const handleResetAssumptions = (modelType) => {
    setCustomAssumptions(prev => {
      const next = { ...prev };
      delete next[modelType];
      return next;
    });
    setCustomResults(prev => {
      const next = { ...prev };
      delete next[modelType];
      return next;
    });
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

  const frLabel = (decile) => {
    const low = decile * 10;
    const high = low + 10;
    const percentile = decile === 9 ? 'top 10%' : decile === 0 ? 'bottom 10%' : `${low}\u2013${high}th percentile`;
    let tooltipText;
    if (decile <= 2) {
      tooltipText = `This ticker's fundamental profile falls in the ${percentile} of historical patterns in the model's training data. Setups in this range historically showed weaker forward returns on average — this does not mean this stock will perform similarly.`;
    } else if (decile <= 5) {
      tooltipText = `This ticker's fundamental profile falls in the ${percentile} of historical patterns in the model's training data. Setups in this range historically showed mixed or average forward returns — this does not mean this stock will perform similarly.`;
    } else if (decile <= 7) {
      tooltipText = `This ticker's fundamental profile falls in the ${percentile} of historical patterns in the model's training data. Setups in this range historically showed above-average forward returns on average — this does not mean this stock will perform similarly.`;
    } else {
      tooltipText = `This ticker's fundamental profile falls in the ${percentile} of historical patterns in the model's training data. Setups in this range historically showed the strongest forward returns on average — this does not mean this stock will perform similarly.`;
    }
    return { label: `Fundamentals ranked in the ${percentile} of historical patterns`, tooltip: tooltipText };
  };

  return (
    <div className="stock-detail-page">
      <div className="navbar-placeholder"></div>

      <div className="stock-detail-container">
        <button className="back-btn" onClick={() => navigate('/')}>
          &larr; back
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
          <div className="current-price-big mono">
            {hasCurrent ? `$${currentPrice.toFixed(2)}` : 'N/A'}
          </div>
        </div>

        <div className="disclaimer-banner">
          This tool is for educational and research purposes only. All outputs are generated by statistical and machine learning models trained on historical data. Historical patterns do not guarantee future results. This is not financial advice, and nothing shown here should be used as the basis for any investment decision. The creator of this tool is not a registered financial advisor. Always consult a qualified financial professional before making investment decisions.
        </div>

        {/* Final Analysis Hero Card */}
        {finalAnalysis && (
          <div className="final-analysis-card">
            <div className="final-analysis-header">
              <h2 className="final-analysis-title">Composite Model Score</h2>
              <span className="confidence-badge">
                {sensitivityLabel(finalAnalysis.confidence)}
              </span>
            </div>
            <div className="final-analysis-verdict">
              {finalAnalysis.verdict}
            </div>
            <div className="final-analysis-gauge">
              <span className="gauge-label-left">Weak Score</span>
              <div className="gauge-track">
                <div
                  className="gauge-marker"
                  style={{ left: `${((finalAnalysis.composite + 1) / 2) * 100}%` }}
                />
              </div>
              <span className="gauge-label-right">Strong Score</span>
            </div>
            <div className="final-analysis-signals">
              {hasUpside && (
                <span className="signal-chip mono">
                  {modelLabel[stockData.primary_model] || 'DCF'}: {upsidePct > 0 ? '+' : ''}{upsidePct.toFixed(1)}% gap
                </span>
              )}
              {hasFr && (
                <span className="signal-chip mono">
                  Fundamentals: Decile {frPrediction}
                </span>
              )}
              {insights ? (
                <span className="signal-chip mono">
                  Sentiment: {insights.scalar.toFixed(2)}
                </span>
              ) : (
                <span className="signal-chip signal-chip-missing mono">
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
            <div className="info-label">Model-Estimated Intrinsic Value ({modelLabel[stockData.primary_model] || 'DCF'})
              <span className="info-help" aria-label="More info">&#8505;
                <span className="tooltip">This value is produced by applying a valuation model to the selected ticker's financials. It reflects a model estimate under specific assumptions, not an objective measure of true value. It is not a price target.</span>
              </span>
            </div>
            <div className="info-value">
              {hasIntrinsic ? `$${intrinsicValue.toFixed(2)}` : isEtf ? 'Cannot value ETF' : 'Unavailable'}
            </div>
            <p className="assumption-subtext">Estimated using the best-fit valuation model for this stock type. Sensitive to model assumptions and input data quality.</p>
            {dcfConfidence && (
              <div className="dcf-confidence-row">
                <span className="dcf-confidence-badge">
                  {sensitivityLabel(dcfConfidence)}
                </span>
                {dcfWarnings.length > 0 && (
                  <span className="info-help" aria-label="DCF warnings">&#9888;
                    <span className="tooltip tooltip-wide">{dcfWarnings.join(' | ')}</span>
                  </span>
                )}
              </div>
            )}
          </div>

          <div className="info-card">
            <div className="info-label">Model Score
              <span className="info-help" aria-label="More info">&#8505;
                <span className="tooltip">This classification reflects how this ticker's current fundamental profile compares to historical setups in the training data. It is a pattern-matching output, not a forecast of future price movement.</span>
              </span>
            </div>
            <div className="info-value">
              {stockData.valuation || 'N/A'}
            </div>
          </div>

          <div className="info-card">
            <div className="info-label">Model-Implied Value Gap
              <span className="info-help" aria-label="More info">&#8505;
                <span className="tooltip">This figure represents the percentage difference between the current market price and the model's estimated fair value. It is not a predicted return and should not be interpreted as the expected gain or loss from holding this security.</span>
              </span>
            </div>
            <div className="info-value">
              {hasUpside ? `${upsidePct > 0 ? '+' : ''}${upsidePct.toFixed(1)}%` : 'N/A'}
            </div>
          </div>

          <div className="info-card">
            <div className="info-label">Forward Return Classification
              <span className="info-help" aria-label="More info">&#8505;
                <span className="tooltip">{hasFr ? frLabel(frPrediction).tooltip : 'This classification reflects how this ticker\'s fundamental profile ranks compared to historical setups in the model\'s training data.'}</span>
              </span>
            </div>
            <div className="info-value">
              {hasFr ? frLabel(frPrediction).label : isEtf ? 'Cannot classify ETF' : 'N/A'}
            </div>
          </div>

          <div className="info-card">
            <div className="info-label">AI Market Sentiment Analysis Score</div>
            {insights ? (
              <>
                <div className="info-value">
                  {insights.scalar.toFixed(2)}
                </div>
                <p className="assumption-subtext">Based on recent news headlines. Score reflects aggregate sentiment tone, not fundamental analysis.</p>
              </>
            ) : (
              <button
                className="get-insights-btn sentiment-card-btn"
                onClick={handleGetInsights}
                disabled={insightsLoading || remaining === 0}
              >
                {insightsLoading ? 'Analyzing\u2026' : remaining === 0 ? 'Limit reached' : 'Get Sentiment Score'}
              </button>
            )}
          </div>
        </div>

        {/* Model Selection Reasoning */}
        {stockData.selection_reasoning && (
          <div className="model-reasoning-card">
            <div className="reasoning-header">
              <span className="reasoning-label">// WHY {(modelLabel[stockData.primary_model] || stockData.primary_model || '').toUpperCase()}</span>
            </div>
            <p className="reasoning-text">{stockData.selection_reasoning.reason}</p>
            <div className="reasoning-criteria">
              {Object.entries(stockData.selection_reasoning.criteria || {}).map(([key, val]) => (
                <span key={key} className="criteria-chip mono">
                  {key.replace(/_/g, ' ')}: {typeof val === 'number' ? val.toLocaleString() : String(val)}
                </span>
              ))}
            </div>
          </div>
        )}

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
                {stockData.models.map((m) => {
                  const isExpanded = expandedModel === m.model_type;
                  const custom = customResults[m.model_type];
                  const displayValue = custom ? custom.intrinsic_value : m.intrinsic_value;
                  const displayUpside = custom ? custom.upside_downside_pct : m.upside_downside_pct;
                  const hasModified = Object.keys(getModifiedAssumptions(m.model_type, m.assumptions)).length > 0;

                  return (
                    <div
                      key={m.model_type}
                      className={`model-card${m.model_type === stockData.primary_model ? ' model-primary' : ''}${isExpanded ? ' model-expanded' : ''}`}
                    >
                      {m.model_type === stockData.primary_model && (
                        <span className="primary-badge">Primary</span>
                      )}
                      {custom && <span className="custom-badge">Custom</span>}
                      <div className="model-card-name">{modelLabel[m.model_type] || m.model_type}</div>
                      <div className="model-card-value">
                        {displayValue != null ? `$${displayValue.toFixed(2)}` : 'N/A'}
                      </div>
                      <div className="model-card-upside">
                        {displayUpside != null ? `${displayUpside > 0 ? '+' : ''}${displayUpside.toFixed(1)}%` : 'N/A'}
                      </div>
                      <div className="model-card-confidence">
                        {m.confidence ? sensitivityLabel(m.confidence) : ''}
                      </div>
                      {m.warnings && m.warnings.length > 0 && (
                        <div className="model-card-warnings">
                          {m.warnings.map((w, i) => (
                            <span key={i} className="model-warning">{w}</span>
                          ))}
                        </div>
                      )}

                      <button
                        className="model-details-toggle"
                        onClick={() => setExpandedModel(isExpanded ? null : m.model_type)}
                      >
                        {isExpanded ? 'Hide Details' : 'Assumptions & Limitations'}
                      </button>

                      {isExpanded && (
                        <div className="model-details-section">
                          {/* Editable Assumptions */}
                          {m.assumptions && Object.keys(m.assumptions).length > 0 && (
                            <div className="assumptions-block">
                              <h4 className="details-section-title">// ADJUSTABLE ASSUMPTIONS</h4>
                              {Object.entries(m.assumptions).map(([key, def]) => (
                                <div key={key} className="assumption-row">
                                  <label className="assumption-label">{def.label}</label>
                                  <div className="assumption-input-wrap">
                                    <input
                                      type="number"
                                      className="assumption-input mono"
                                      value={customAssumptions[m.model_type]?.[key] ?? def.value}
                                      onChange={(e) => handleAssumptionChange(m.model_type, key, e.target.value)}
                                      min={def.min}
                                      max={def.max}
                                      step={def.step}
                                    />
                                    <span className="assumption-unit">{def.unit}</span>
                                  </div>
                                  <span className="assumption-range">({def.min} – {def.max})</span>
                                </div>
                              ))}
                            </div>
                          )}

                          {/* Read-only Assumptions */}
                          {m.assumptions_readonly && Object.keys(m.assumptions_readonly).length > 0 && (
                            <div className="assumptions-block">
                              <h4 className="details-section-title">// MODEL INPUTS</h4>
                              {Object.entries(m.assumptions_readonly).map(([key, def]) => (
                                <div key={key} className="assumption-row readonly">
                                  <label className="assumption-label">{def.label}</label>
                                  <span className="assumption-value mono">{def.value}{def.unit && def.unit !== '$' ? def.unit : ''}</span>
                                </div>
                              ))}
                            </div>
                          )}

                          {/* Limitations */}
                          {m.limitations && m.limitations.length > 0 && (
                            <div className="limitations-block">
                              <h4 className="details-section-title">// LIMITATIONS</h4>
                              <ul className="limitations-list">
                                {m.limitations.map((lim, i) => (
                                  <li key={i} className="limitation-item">{lim}</li>
                                ))}
                              </ul>
                            </div>
                          )}

                          {/* Recalculate / Reset */}
                          <div className="recalculate-actions">
                            <button
                              className="recalculate-btn"
                              onClick={() => handleRecalculate(m.model_type, m.assumptions)}
                              disabled={!hasModified || recalculating === m.model_type}
                            >
                              {recalculating === m.model_type ? 'Recalculating\u2026' : 'Recalculate'}
                            </button>
                            {(custom || hasModified) && (
                              <button
                                className="reset-btn"
                                onClick={() => handleResetAssumptions(m.model_type)}
                              >
                                Reset to Default
                              </button>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
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
                <span className="insights-scalar-value mono">
                  {insights.scalar.toFixed(2)}
                  &nbsp;&middot;&nbsp;
                  {insights.scalar > 1.03 ? 'Historically Strong' : insights.scalar < 0.97 ? 'Historically Weak' : 'Neutral'}
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
          All outputs are generated by statistical and machine learning models for educational and research purposes only. Nothing on this page constitutes financial advice or a recommendation to buy, sell, or hold any security. The creator is not a registered financial advisor. Always consult a qualified financial professional before making investment decisions.
        </footer>
      </div>
    </div>
  );
}

export default StockDetail;
