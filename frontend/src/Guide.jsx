import { Link } from 'react-router-dom'
import './Guide.css'

function Guide() {
  return (
    <div className="guide-page">
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

      <div className="guide-container">
        <div className="guide-hero">
          <h1 className="guide-title">How to Use Our Data</h1>
          <p className="guide-subtitle">
            This page explains what each output on a stock's detail page means, how it's calculated,
            and how to interpret the results given the underlying assumptions.
          </p>
        </div>

        {/* ── Valuation Models ── */}
        <section className="guide-section">
          <h2 className="guide-section-header">VALUATION MODELS</h2>
          <p className="guide-section-intro">
            For each stock we run up to 5 valuation models in parallel and select the most appropriate
            one as the <strong>primary</strong> based on the company's financial profile. Each model
            produces an intrinsic value estimate and an upside/downside percentage relative to the
            current market price.
          </p>
          <div className="guide-models-grid">

            <div className="guide-model-card">
              <div className="guide-model-name">DCF — Discounted Cash Flow</div>
              <div className="guide-model-formula">
                Intrinsic Value = Σ (FCF_t / (1 + WACC)^t) + Terminal Value
              </div>
              <div className="guide-model-body">
                <h4 className="guide-model-subheader">ASSUMPTIONS</h4>
                <ul>
                  <li>WACC derived from company beta, risk-free rate (3.96%), and equity risk premium (4.38%)</li>
                  <li>FCF growth extrapolated from historical average</li>
                  <li>5-year explicit projection horizon</li>
                  <li>Terminal growth rate defaults to 2.5%</li>
                </ul>
                <h4 className="guide-model-subheader">BEST FOR</h4>
                <p>Profitable companies with positive and relatively stable free cash flow.</p>
                <h4 className="guide-model-subheader">LIMITATIONS</h4>
                <ul>
                  <li>Highly sensitive to WACC and growth rate inputs — small changes produce large value swings</li>
                  <li>Cannot be applied to companies with negative FCF</li>
                  <li>Terminal value often represents 60–80% of total value</li>
                </ul>
              </div>
            </div>

            <div className="guide-model-card">
              <div className="guide-model-name">P/E Comparable</div>
              <div className="guide-model-formula">
                Intrinsic Value = Sector Median P/E × Trailing EPS
              </div>
              <div className="guide-model-body">
                <h4 className="guide-model-subheader">ASSUMPTIONS</h4>
                <ul>
                  <li>The stock should trade at the sector's median earnings multiple</li>
                  <li>Sector P/E benchmarks are periodically updated from market data</li>
                </ul>
                <h4 className="guide-model-subheader">BEST FOR</h4>
                <p>Profitable, non-financial companies with stable earnings and no dividend.</p>
                <h4 className="guide-model-subheader">LIMITATIONS</h4>
                <ul>
                  <li>Meaningless for companies with negative or near-zero earnings</li>
                  <li>Sector median may be distorted by outliers</li>
                  <li>Does not account for growth differences within the sector</li>
                </ul>
              </div>
            </div>

            <div className="guide-model-card">
              <div className="guide-model-name">Revenue Multiple</div>
              <div className="guide-model-formula">
                Intrinsic Value = Sector Median P/S × Revenue Per Share
              </div>
              <div className="guide-model-body">
                <h4 className="guide-model-subheader">ASSUMPTIONS</h4>
                <ul>
                  <li>The stock should trade at the sector's median price-to-sales multiple</li>
                  <li>Revenue is a proxy for scale when earnings are not yet meaningful</li>
                </ul>
                <h4 className="guide-model-subheader">BEST FOR</h4>
                <p>High-growth, pre-profitability companies where P/E is not applicable.</p>
                <h4 className="guide-model-subheader">LIMITATIONS</h4>
                <ul>
                  <li>Ignores profitability entirely — two companies with identical revenue can have very different values</li>
                  <li>P/S multiples compress significantly during market downturns</li>
                </ul>
              </div>
            </div>

            <div className="guide-model-card">
              <div className="guide-model-name">DDM — Dividend Discount Model</div>
              <div className="guide-model-formula">
                Intrinsic Value = D₁ / (Cost of Equity − Dividend Growth Rate)
              </div>
              <div className="guide-model-body">
                <h4 className="guide-model-subheader">ASSUMPTIONS</h4>
                <ul>
                  <li>Dividends grow at a constant rate indefinitely (Gordon Growth Model)</li>
                  <li>Cost of equity derived via CAPM</li>
                  <li>Dividend growth estimated from historical payout data</li>
                </ul>
                <h4 className="guide-model-subheader">BEST FOR</h4>
                <p>Mature, dividend-paying companies with a long and stable payout history.</p>
                <h4 className="guide-model-subheader">LIMITATIONS</h4>
                <ul>
                  <li>Only applicable to dividend-paying stocks</li>
                  <li>Model breaks down if growth rate ≥ cost of equity</li>
                  <li>Ignores capital appreciation and buybacks</li>
                </ul>
              </div>
            </div>

            <div className="guide-model-card">
              <div className="guide-model-name">Book Value</div>
              <div className="guide-model-formula">
                Intrinsic Value = Sector Median P/B × Book Value Per Share
              </div>
              <div className="guide-model-body">
                <h4 className="guide-model-subheader">ASSUMPTIONS</h4>
                <ul>
                  <li>Balance sheet assets are fairly valued at book</li>
                  <li>The stock should trade at the sector's median price-to-book ratio</li>
                </ul>
                <h4 className="guide-model-subheader">BEST FOR</h4>
                <p>Financial institutions, banks, insurance companies, and asset-heavy industrials.</p>
                <h4 className="guide-model-subheader">LIMITATIONS</h4>
                <ul>
                  <li>Book value can be distorted by accounting choices (intangibles, depreciation)</li>
                  <li>Misleading for technology or services companies with few tangible assets</li>
                </ul>
              </div>
            </div>

          </div>
        </section>

        {/* ── Upside / Downside Gap ── */}
        <section className="guide-section">
          <h2 className="guide-section-header">UPSIDE / DOWNSIDE GAP</h2>
          <p className="guide-section-intro">
            The gap measures how far the current market price is from the model's estimated intrinsic
            value. A positive gap ("upside") means the stock appears undervalued; a negative gap
            ("downside") means it appears overvalued.
          </p>
          <div className="guide-example-card">
            <div className="guide-example-row">
              <span className="guide-example-label">Ticker</span>
              <span className="guide-example-value">????</span>
            </div>
            <div className="guide-example-row">
              <span className="guide-example-label">Current Market Price</span>
              <span className="guide-example-value">$100.00</span>
            </div>
            <div className="guide-example-row">
              <span className="guide-example-label">Model Intrinsic Value (DCF)</span>
              <span className="guide-example-value">$130.00</span>
            </div>
            <div className="guide-example-row">
              <span className="guide-example-label">Upside Gap</span>
              <span className="guide-example-value positive">+30.0%</span>
            </div>
            <p className="guide-formula-note">
              Formula: (Intrinsic Value − Current Price) / Current Price × 100
            </p>
          </div>
          <p className="guide-section-body">
            This output should be interpreted in the context of model confidence. A high-sensitivity
            DCF model showing +30% upside carries more uncertainty than a P/E comparable model
            showing the same figure. Always check the confidence label and warnings on each model card.
          </p>
        </section>

        {/* ── Forward Return Classification ── */}
        <section className="guide-section">
          <h2 className="guide-section-header">FORWARD RETURN CLASSIFICATION</h2>
          <p className="guide-section-intro">
            This output is the predicted <strong>decile rank</strong> produced by a trained XGBoost
            classifier. It represents how the stock's current fundamental and momentum profile historically
            correlates with 12-month forward returns relative to the broader market.
          </p>
          <div className="guide-decile-row">
            {[0,1,2,3,4,5,6,7,8,9].map(d => (
              <div key={d} className={`guide-decile-box${d === 7 ? ' guide-decile-active' : ''}`}>
                {d}
              </div>
            ))}
          </div>
          <p className="guide-section-body">
            <strong>Decile 0</strong> = bottom 10% of historical setups by subsequent 12-month return
            vs. the market. <strong>Decile 9</strong> = top 10%. The example above highlights Decile 7
            — a stock with this score has historically tended to outperform the market in the year
            following similar fundamental conditions.
          </p>
          <p className="guide-section-body">
            This is a <em>ranking of historical pattern similarity</em>, not a price target or a
            guarantee of future performance. The model is trained on 9 quantitative factors spanning
            value, quality, momentum, and dilution signals.
          </p>
        </section>

        {/* ── Market Sentiment Analysis ── */}
        <section className="guide-section">
          <h2 className="guide-section-header">MARKET SENTIMENT ANALYSIS</h2>
          <p className="guide-section-intro">
            The sentiment score reflects the current news sentiment surrounding the stock, derived
            from recent headlines analyzed by an AI language model. It is expressed as a scalar
            from 0.5 (strongly bearish) to 1.5 (strongly bullish), with 1.0 being neutral.
          </p>
          <div className="guide-scalar-demo">
            <div className="guide-scalar-track">
              <div className="guide-scalar-marker" style={{ left: '62%' }}></div>
            </div>
            <div className="guide-scalar-labels">
              <span className="guide-scalar-label-left">0.5 — Bearish</span>
              <span className="guide-scalar-label-mid">1.0 — Neutral</span>
              <span className="guide-scalar-label-right">1.5 — Bullish</span>
            </div>
          </div>
          <p className="guide-section-body">
            Each analysis also returns individual insight cards, each labelled Bullish, Bearish, or
            Neutral with a brief reasoning snippet. Sentiment analysis is rate-limited to 3 requests
            per day per user to manage API costs. Results are cached for 24 hours.
          </p>
          <p className="guide-section-body">
            Sentiment is a short-term signal and is given a lower weight in the composite score.
            It should not be used in isolation.
          </p>
        </section>

        {/* ── Composite Score ── */}
        <section className="guide-section">
          <h2 className="guide-section-header">COMPOSITE SCORE</h2>
          <p className="guide-section-intro">
            The composite score combines all three signals into a single weighted sum ranging from
            −1 (very weak composite) to +1 (very strong composite). It is computed client-side using the
            following weights:
          </p>
          <div className="guide-weights-table">
            <div className="guide-weight-row">
              <span className="guide-weight-label">Valuation (Upside/Downside Gap)</span>
              <div className="guide-weight-bar-wrap">
                <div className="guide-weight-bar" style={{ width: '50%' }}></div>
              </div>
              <span className="guide-weight-pct">50%</span>
            </div>
            <div className="guide-weight-row">
              <span className="guide-weight-label">Forward Return Decile</span>
              <div className="guide-weight-bar-wrap">
                <div className="guide-weight-bar" style={{ width: '30%' }}></div>
              </div>
              <span className="guide-weight-pct">30%</span>
            </div>
            <div className="guide-weight-row">
              <span className="guide-weight-label">Market Sentiment Score</span>
              <div className="guide-weight-bar-wrap">
                <div className="guide-weight-bar" style={{ width: '20%' }}></div>
              </div>
              <span className="guide-weight-pct">20%</span>
            </div>
          </div>
          <p className="guide-section-body">The composite score maps to the following verdicts:</p>
          <div className="guide-verdicts-table">
            <div className="guide-verdict-row">
              <span className="guide-verdict-range positive">&gt; 0.50</span>
              <span className="guide-verdict-label">Very Strong Composite</span>
            </div>
            <div className="guide-verdict-row">
              <span className="guide-verdict-range positive-dim">0.20 – 0.50</span>
              <span className="guide-verdict-label">Strong Composite</span>
            </div>
            <div className="guide-verdict-row">
              <span className="guide-verdict-range neutral">−0.20 – 0.20</span>
              <span className="guide-verdict-label">Neutral</span>
            </div>
            <div className="guide-verdict-row">
              <span className="guide-verdict-range negative-dim">−0.50 – −0.20</span>
              <span className="guide-verdict-label">Weak Composite</span>
            </div>
            <div className="guide-verdict-row">
              <span className="guide-verdict-range negative">&lt; −0.50</span>
              <span className="guide-verdict-label">Very Weak Composite</span>
            </div>
          </div>
          <p className="guide-section-body">
            The composite score is most reliable when all three signals are available. When sentiment
            has not been fetched, the score uses only valuation and forward return, and confidence
            is reduced accordingly.
          </p>
        </section>

        <footer className="guide-footer">
          All outputs are for educational and research purposes only. Nothing on this platform
          constitutes financial advice or a recommendation to buy or sell any security.
        </footer>
      </div>
    </div>
  )
}

export default Guide
