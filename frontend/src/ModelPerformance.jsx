import { Link } from 'react-router-dom'
import './ModelPerformance.css'

const FEATURES = [
  {
    name: 'FCF_Yield',
    formula: 'Free Cash Flow / Market Cap',
    category: 'Value',
    barWidth: 81,
    desc: 'How much free cash flow the company generates relative to its market value. High yield historically signals undervaluation.',
  },
  {
    name: 'EV_to_EBITDA',
    formula: 'Enterprise Value / EBITDA',
    category: 'Value',
    barWidth: 72,
    desc: 'Valuation multiple that accounts for debt. Lower multiples relative to peers can indicate undervaluation.',
  },
  {
    name: 'ROIC',
    formula: 'EBIT / Invested Capital',
    category: 'Quality',
    barWidth: 67,
    desc: 'Measures how efficiently a company uses its capital to generate earnings. A strong moat indicator.',
  },
  {
    name: 'Gross_Profitability',
    formula: 'Gross Profit / Total Assets',
    category: 'Quality',
    barWidth: 58,
    desc: 'Asset productivity proxy. Higher values indicate a durable competitive advantage.',
  },
  {
    name: 'Momentum_6M',
    formula: 'Price return over 126 trading days',
    category: 'Momentum',
    barWidth: 54,
    desc: 'Six-month price momentum. Stocks that have recently outperformed tend to continue doing so in the short term.',
  },
  {
    name: 'Revenue_Growth_YoY',
    formula: 'YoY % change in revenue',
    category: 'Growth',
    barWidth: 45,
    desc: 'Year-over-year top-line growth. Captures business expansion momentum.',
  },
  {
    name: 'Interest_Coverage',
    formula: 'EBIT / Interest Expense',
    category: 'Quality',
    barWidth: 31,
    desc: 'Ability to service debt. Low coverage ratios signal financial fragility and potential distress risk.',
  },
  {
    name: 'Accrual_Ratio',
    formula: '(Net Income − FCF) / Total Assets',
    category: 'Quality',
    barWidth: 22,
    desc: 'Earnings quality signal. High accruals suggest earnings are less backed by actual cash flow.',
  },
  {
    name: 'Shares_Outstanding_YoY',
    formula: 'YoY % change in diluted shares',
    category: 'Dilution',
    barWidth: 18,
    desc: 'Dilution signal. Growing share counts reduce per-share value for existing shareholders.',
  },
]

function ModelPerformance() {
  return (
    <div className="mp-page">
      <div className="Navbar">
        <Link to="/">
          <img className="logo" src="/new-transparent-logo.png" alt="StockInsight" />
        </Link>
        <nav>
          <ul className="nav_links">
            <li><Link to="/guide">How to Use</Link></li>
            <li><Link to="/model-performance">Model Performance</Link></li>
            <li><Link to="/feedback">Feedback</Link></li>
          </ul>
        </nav>
      </div>
      <div className="navbar-placeholder"></div>

      <div className="mp-container">
        <div className="mp-hero">
          <h1 className="mp-title">Model Performance</h1>
          <p className="mp-subtitle">
            XGBoost 10-class forward return classifier — trained to predict which decile a stock's
            12-month return will fall into, relative to the broader market.
          </p>
        </div>

        {/* ── Model Overview ── */}
        <section className="mp-section">
          <h2 className="mp-section-header">MODEL OVERVIEW</h2>
          <div className="mp-stats-row">
            <div className="mp-stat-card">
              <div className="mp-stat-value">XGBoost</div>
              <div className="mp-stat-label">Algorithm</div>
            </div>
            <div className="mp-stat-card">
              <div className="mp-stat-value">10</div>
              <div className="mp-stat-label">Classes (Deciles 0–9)</div>
            </div>
            <div className="mp-stat-card">
              <div className="mp-stat-value">~15–16%</div>
              <div className="mp-stat-label">Test Accuracy</div>
            </div>
            <div className="mp-stat-card">
              <div className="mp-stat-value">~10%</div>
              <div className="mp-stat-label">Random Baseline</div>
            </div>
            <div className="mp-stat-card">
              <div className="mp-stat-value">80 / 20</div>
              <div className="mp-stat-label">Train / Test Split</div>
            </div>
            <div className="mp-stat-card">
              <div className="mp-stat-value">Optuna</div>
              <div className="mp-stat-label">Hyperparameter Tuning</div>
            </div>
          </div>
        </section>

        {/* ── Why 15% Matters ── */}
        <section className="mp-section">
          <h2 className="mp-section-header">WHY ~15% IS MEANINGFUL</h2>
          <div className="mp-explainer-card">
            <p className="mp-explainer-text">
              With 10 equally-likely classes, a model that guesses randomly would achieve ~10% accuracy.
              Our model achieves ~15–16%, representing a <strong>50–60% improvement over random chance</strong>.
              While this may sound modest, predicting equity return deciles is an exceptionally difficult
              task — financial markets are designed to be difficult to predict. Even small edges, applied
              consistently across large populations of stocks, compound meaningfully.
            </p>
            <div className="mp-accuracy-compare">
              <div className="mp-accuracy-row">
                <span className="mp-accuracy-label">Random Baseline (10-class)</span>
                <div className="mp-accuracy-bar-wrap">
                  <div className="mp-accuracy-bar mp-accuracy-baseline" style={{ width: '10%' }}></div>
                </div>
                <span className="mp-accuracy-pct">~10%</span>
              </div>
              <div className="mp-accuracy-row">
                <span className="mp-accuracy-label">XGBoost Model</span>
                <div className="mp-accuracy-bar-wrap">
                  <div className="mp-accuracy-bar mp-accuracy-model" style={{ width: '15.5%' }}></div>
                </div>
                <span className="mp-accuracy-pct">~15–16%</span>
              </div>
            </div>
            <p className="mp-explainer-note">
              The model is used as one of three signals in the composite score, not as a standalone
              buy/sell signal. It contributes 30% weight to the final composite.
            </p>
          </div>
        </section>

        {/* ── Feature Importance ── */}
        <section className="mp-section">
          <h2 className="mp-section-header">FEATURE IMPORTANCE</h2>
          <p className="mp-section-intro">
            The model was trained on 9 quantitative features spanning value, quality, momentum,
            growth, and dilution factors. Bar widths below reflect approximate relative importance
            based on the model's gain-based feature scores.
          </p>
          <div className="mp-feature-chart">
            {FEATURES.map(f => (
              <div className="mp-feature-row" key={f.name}>
                <span className="mp-feature-name">{f.name}</span>
                <div className="mp-feature-bar-wrap">
                  <div className="mp-feature-bar" style={{ width: `${f.barWidth}%` }}>
                    <span className="mp-feature-bar-label">{Math.round(f.barWidth / 4.5)}%</span>
                  </div>
                </div>
                <span className={`mp-feature-tag mp-feature-tag--${f.category.toLowerCase()}`}>
                  {f.category}
                </span>
              </div>
            ))}
          </div>
          <p className="mp-feature-note">
            Feature importance values are approximate and based on the model's gain metric at training
            time. Exact values vary across retraining runs.
          </p>
        </section>

        {/* ── Train / Test Methodology ── */}
        <section className="mp-section">
          <h2 className="mp-section-header">TRAIN / TEST METHODOLOGY</h2>
          <div className="mp-method-card">
            <div className="mp-split-visual">
              <div className="mp-split-train">
                <div className="mp-split-label">Training Set</div>
                <div className="mp-split-sub">80% — Older data</div>
              </div>
              <div className="mp-split-divider"></div>
              <div className="mp-split-test">
                <div className="mp-split-label">Test Set</div>
                <div className="mp-split-sub">20% — Recent data</div>
              </div>
            </div>
            <ul className="mp-method-list">
              <li>
                <strong>Chronological split</strong> — no future data leaks into the training set.
                The test set represents the most recent portion of the dataset.
              </li>
              <li>
                <strong>Target variable</strong> — 12-month forward return percentile vs. the overall market,
                binned into 10 equal deciles (0 = worst 10%, 9 = best 10%).
              </li>
              <li>
                <strong>Optuna hyperparameter search</strong> — Bayesian optimisation over
                max_depth, learning_rate, n_estimators, subsample, colsample_bytree,
                min_child_weight, and gamma.
              </li>
              <li>
                <strong>Feature engineering</strong> — all features are ratio-based (not raw
                financials) to ensure cross-sector comparability and reduce scale bias.
              </li>
            </ul>
          </div>
        </section>

        {/* ── Feature Definitions ── */}
        <section className="mp-section">
          <h2 className="mp-section-header">FEATURE DEFINITIONS</h2>
          <div className="mp-feature-defs">
            <div className="mp-feature-def-header">
              <span>Feature</span>
              <span>Formula</span>
              <span>Category</span>
              <span>Description</span>
            </div>
            {FEATURES.map(f => (
              <div className="mp-feature-def-row" key={f.name}>
                <div className="mp-feature-def-name">{f.name}</div>
                <div className="mp-feature-def-formula">{f.formula}</div>
                <div className={`mp-feature-def-category mp-feature-tag--${f.category.toLowerCase()}`}>
                  {f.category}
                </div>
                <div className="mp-feature-def-desc">{f.desc}</div>
              </div>
            ))}
          </div>
        </section>

        <footer className="mp-footer">
          All outputs are for educational and research purposes only. Past model performance
          does not guarantee future predictive accuracy.
        </footer>
      </div>
    </div>
  )
}

export default ModelPerformance
