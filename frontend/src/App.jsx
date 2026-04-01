import { useEffect, useState, useRef } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import api from "./components/api.js";
import './App.css'

function App(){
  const navigate = useNavigate();
  const [topmovers, setTopMovers] = useState([]);
  const [toplosers, setTopLosers] = useState([]);
  const [topgainers, setTopGainers] = useState([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const [showSearchResults, setShowSearchResults] = useState(false);
  const [selectedStock, setSelectedStock] = useState(null);
  const [isSearching, setIsSearching] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  // Ref to track the search timeout
  const searchTimeoutRef = useRef(null);

  // Refs for scrollable stock card lists
  const moversRef = useRef(null);
  const gainersRef = useRef(null);
  const losersRef = useRef(null);

  // Track which arrows to show per section
  const [canScroll, setCanScroll] = useState({
    movers: { left: false, right: false },
    gainers: { left: false, right: false },
    losers: { left: false, right: false },
  });

  const updateCanScroll = (name, el) => {
    if (!el) return;
    setCanScroll(prev => ({
      ...prev,
      [name]: {
        left: el.scrollLeft > 0,
        right: el.scrollLeft + el.clientWidth < el.scrollWidth - 1,
      },
    }));
  };

  // Attach scroll listeners and run initial check once data loads
  useEffect(() => {
    const refs = { movers: moversRef, gainers: gainersRef, losers: losersRef };
    const handlers = {};
    for (const [name, ref] of Object.entries(refs)) {
      if (ref.current) {
        updateCanScroll(name, ref.current);
        handlers[name] = () => updateCanScroll(name, ref.current);
        ref.current.addEventListener('scroll', handlers[name]);
      }
    }
    return () => {
      for (const [name, ref] of Object.entries(refs)) {
        if (ref.current && handlers[name]) {
          ref.current.removeEventListener('scroll', handlers[name]);
        }
      }
    };
  }, [topmovers, topgainers, toplosers]);

  const scroll = (ref, name, direction) => {
    if (!ref.current) return;
    const el = ref.current;
    const distance = 600;
    const duration = 400;
    const start = el.scrollLeft;
    const target = direction === 'right' ? distance : -distance;
    let startTime = null;

    const step = (timestamp) => {
      if (!startTime) startTime = timestamp;
      const progress = Math.min((timestamp - startTime) / duration, 1);
      const ease = progress < 0.5
        ? 2 * progress * progress
        : 1 - Math.pow(-2 * progress + 2, 2) / 2;
      el.scrollLeft = start + target * ease;
      if (progress < 1) {
        requestAnimationFrame(step);
      } else {
        updateCanScroll(name, el);
      }
    };

    requestAnimationFrame(step);
  };

  // Logokit token state
  const [logokitToken, setLogokitToken] = useState("");

  // Fetch the token from backend on mount
  useEffect(() => {
    const fetchToken = async () => {
      try {
        const res = await api.get("/logokit-token");
        setLogokitToken(res.data.token);
      } catch (err) {
        setLogokitToken("");
      }
    };
    fetchToken();
  }, []);

  // Use backend proxy for logo images
  const getLogo = (symbol) => {
    if (!symbol) return '';
    // The backend serves the logo without exposing the token
    
    return `https://images.financialmodelingprep.com/symbol/${symbol}.png`;
  };

  const getAvatarFallback = (name, bg = '6fbf73') => {
    return `https://ui-avatars.com/api/?name=${encodeURIComponent(name)}&size=128&rounded=false&color=ffffff&background=${bg}`;
  };

  useEffect(() => {
    // Fetch all data in parallel
    const fetchAllData = async () => {
      try {
        const [moversRes, gainersRes, losersRes] = await Promise.all([
          api.get("/topmovers"),
          api.get("/topgainers"),
          api.get("/toplosers")
        ]);
        
        setTopMovers(moversRes.data);
        setTopGainers(gainersRes.data);
        setTopLosers(losersRes.data);
      } catch (error) {
        console.error("Failed to fetch stock data:", error);
      }
    };

    fetchAllData();
  }, []);

  // Debounced search - triggers 300ms after user stops typing
  const handleSearchChange = (e) => {
    const query = e.target.value;
    setSearchQuery(query);
    
    // Clear previous timeout
    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current);
    }
    
    // If query is empty, hide results
    if (!query.trim()) {
      setShowSearchResults(false);
      setSearchResults([]);
      setSelectedIndex(-1); // Reset selection
      return;
    }
    
    // Show loading state
    setIsSearching(true);
    
    // Set new timeout - search after 300ms of no typing
    searchTimeoutRef.current = setTimeout(async () => {
      try {
        const response = await api.get(`/search/${query}`);
        setSearchResults(response.data.results);
        setShowSearchResults(true);
        setIsSearching(false);
        setSelectedIndex(-1); // Reset selection on new results
      } catch (error) {
        console.error("Search failed:", error);
        setSearchResults([]);
        setIsSearching(false);
        setSelectedIndex(-1);
      }
    }, 300); // 300ms delay
  };

  const handleKeyDown = (e) => {
    if (!showSearchResults || searchResults.length === 0) return;
    
    if (e.key === 'ArrowDown'){
      e.preventDefault();
      setSelectedIndex(prev => 
        prev < searchResults.length - 1 ? prev + 1 : prev
      );
    } else if (e.key === 'ArrowUp'){
      e.preventDefault();
      setSelectedIndex(prev => prev > 0 ? prev - 1 : -1);
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (selectedIndex >= 0) {
        handleStockSelect(searchResults[selectedIndex].symbol);
      }
    } else if (e.key === 'Escape') {
      setShowSearchResults(false);
      setSelectedIndex(-1);
    }
  }

  // Handle clicking on a search result
  const handleStockSelect = (ticker) => {
    setShowSearchResults(false);
    setSearchQuery("");
    setSelectedIndex(-1);
    navigate(`/stock/${ticker}`);  // Navigate to stock page
  };

  // Close search results when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (!event.target.closest('.search-form')) {
        setShowSearchResults(false);
        setSelectedIndex(-1);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div>
      <div className="Navbar">
        <img className="logo" src="transparent-logo.png" alt="Logo" />
        <nav>
          <ul className="nav_links">
            <li><Link to="/guide">How to Use</Link></li>
            <li><Link to="/model-performance">Model Performance</Link></li>
            <li><Link to="/feedback">Feedback</Link></li>
          </ul>
        </nav>
        
        {/* Search Form */}
        <div className="search-form">
          <input
            type="text"
            placeholder="> search ticker or company..."
            value={searchQuery}
            onChange={handleSearchChange}
            onKeyDown={handleKeyDown}
            className="search-input"
            autoComplete="off"
          />
          <div className="search-icon">
            {isSearching ? (
              <div className="spinner"></div>
            ) : (
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="11" cy="11" r="8"></circle>
                <path d="m21 21-4.35-4.35"></path>
              </svg>
            )}
          </div>

          {/* Search Results Dropdown */}
          {showSearchResults && (
            <div className="search-results">
              {searchResults.length > 0 ? (
                <ul>
                  {searchResults.map((result, index) => (
                    <li
                      key={result.symbol}
                      onClick={() => handleStockSelect(result.symbol)}
                      className={selectedIndex === index ? 'selected' : ''}
                    >
                      <img
                        src={getLogo(result.symbol)}
                        alt=""
                        className="result-logo"
                        onError={(e) => { e.currentTarget.onerror = null; e.currentTarget.src = getAvatarFallback(result.symbol, '6fbf73'); }}
                      />
                      <div className="result-main">
                        <strong>{result.symbol}</strong>
                        <span className="result-name">{result.name}</span>
                      </div>
                      <span className="exchange">{result.exchange}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <div className="no-results">No results found for "{searchQuery}"</div>
              )}
            </div>
          )}
        </div>
      </div>
      
      {/* Selected Stock Details */}
      {selectedStock && (
        <div className="selected-stock">
          <button className="close-btn" onClick={() => setSelectedStock(null)}>×</button>
          <h2>{selectedStock.ticker}</h2>
          <div className="stock-details">
            <div className="detail-card">
              <span className="label">Current Price</span>
              <span className="value">${selectedStock.current_price?.toFixed(2)}</span>
            </div>
            <div className="detail-card">
              <span className="label">Model-Estimated Fair Value</span>
              <span className="value">{selectedStock.intrinsic_value ? `$${selectedStock.intrinsic_value.toFixed(2)}` : 'N/A'}</span>
            </div>
            <div className="detail-card">
              <span className="label">Model Score</span>
              <span className="value">{selectedStock.valuation}</span>
            </div>
            <div className="detail-card">
              <span className="label">Model-Implied Value Gap</span>
              <span className={`value ${selectedStock.upside_pct != null ? (selectedStock.upside_pct >= 0 ? 'positive' : 'negative') : ''}`}>
                {selectedStock.upside_pct != null ? `${selectedStock.upside_pct > 0 ? '+' : ''}${selectedStock.upside_pct.toFixed(1)}%` : 'N/A'}
              </span>
            </div>
          </div>
          <p className="popup-disclaimer">Model-generated signal for informational purposes only. Not financial advice.</p>
        </div>
      )}

      {/* Top Movers */}
      <div className="stock-list movers">
        <br />
        <br />
        <br />
        <br />
        <br />
        <h2>Top Movers</h2>
        <div className="stock-cards-wrapper">
          {canScroll.movers.left && <button className="scroll-arrow scroll-arrow-left" onClick={() => scroll(moversRef, 'movers', 'left')}>&#8249;</button>}
          <ul className="stock-cards" ref={moversRef}>
            {topmovers.map(u => (
              <li key={u.symbol} className="stock-card" onClick={() => handleStockSelect(u.symbol)}>
                <img
                  src={getLogo(u.symbol)}
                  alt={u.name}
                  className="company-badge"
                  onError={(e) => { e.currentTarget.onerror = null; e.currentTarget.src = getAvatarFallback(u.name, '1976d2'); }}
                />
                <div className="stock-symbol">{u.symbol}</div>
                <div className="stock-name">{u.name}</div>
                <div className="stock-price mono">{isNaN(Number(u.price)) ? `$${u.price} USD` : `$${Number(u.price).toFixed(2)} USD`}</div>
                <div className={`stock-change ${u.change >= 0 ? 'positive' : 'negative'}`}>
                  {u.change >= 0 ? '▲' : '▼'} {parseFloat(u.change).toFixed(2)} ({parseFloat(u.changesPercentage).toFixed(2)}%)
                </div>
              </li>
            ))}
          </ul>
          {canScroll.movers.right && <button className="scroll-arrow scroll-arrow-right" onClick={() => scroll(moversRef, 'movers', 'right')}>&#8250;</button>}
        </div>
      </div>
      {/* Top Gainers */}
      <div className="stock-list gainers">
        <h2>Top Gainers</h2>
        <div className="stock-cards-wrapper">
          {canScroll.gainers.left && <button className="scroll-arrow scroll-arrow-left" onClick={() => scroll(gainersRef, 'gainers', 'left')}>&#8249;</button>}
          <ul className="stock-cards" ref={gainersRef}>
            {topgainers.map(u => (
              <li key={u.symbol} className="stock-card" onClick={() => handleStockSelect(u.symbol)}>
                <img
                  src={getLogo(u.symbol)}
                  alt={u.name}
                  className="company-badge"
                  onError={(e) => { e.currentTarget.onerror = null; e.currentTarget.src = getAvatarFallback(u.name, '6fbf73'); }}
                />
                <div className="stock-symbol">{u.symbol}</div>
                <div className="stock-name">{u.name}</div>
                <div className="stock-price mono">{isNaN(Number(u.price)) ? `$${u.price} USD` : `$${Number(u.price).toFixed(2)} USD`}</div>
                <div className={`stock-change ${u.change >= 0 ? 'positive' : 'negative'}`}>
                  {u.change >= 0 ? '▲' : '▼'} {parseFloat(u.change).toFixed(2)} ({parseFloat(u.changesPercentage).toFixed(2)}%)
                </div>
              </li>
            ))}
          </ul>
          {canScroll.gainers.right && <button className="scroll-arrow scroll-arrow-right" onClick={() => scroll(gainersRef, 'gainers', 'right')}>&#8250;</button>}
        </div>
      </div>
      {/* Top Losers */}
      <div className="stock-list losers">
        <h2>Top Losers</h2>
        <div className="stock-cards-wrapper">
          {canScroll.losers.left && <button className="scroll-arrow scroll-arrow-left" onClick={() => scroll(losersRef, 'losers', 'left')}>&#8249;</button>}
          <ul className="stock-cards" ref={losersRef}>
            {toplosers.map(u => (
              <li key={u.symbol} className="stock-card" onClick={() => handleStockSelect(u.symbol)}>
                <img
                  src={getLogo(u.symbol)}
                  alt={u.name}
                  className="company-badge"
                  onError={(e) => { e.currentTarget.onerror = null; e.currentTarget.src = getAvatarFallback(u.name, 'e74c3c'); }}
                />
                <div className="stock-symbol">{u.symbol}</div>
                <div className="stock-name">{u.name}</div>
                <div className="stock-price mono">{isNaN(Number(u.price)) ? `$${u.price} USD` : `$${Number(u.price).toFixed(2)} USD`}</div>
                <div className={`stock-change ${u.change >= 0 ? 'positive' : 'negative'}`}>
                  {u.change >= 0 ? '▲' : '▼'} {parseFloat(u.change).toFixed(2)} ({parseFloat(u.changesPercentage).toFixed(2)}%)
                </div>
              </li>
            ))}
          </ul>
          {canScroll.losers.right && <button className="scroll-arrow scroll-arrow-right" onClick={() => scroll(losersRef, 'losers', 'right')}>&#8250;</button>}
        </div>
      </div>
    </div>
  );
}

export default App