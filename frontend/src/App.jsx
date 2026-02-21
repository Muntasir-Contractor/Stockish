import { useEffect, useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
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
            <li><a href="#">PlaceHolder</a></li>
            <li><a href="#">Second PlaceHolder</a></li>
            <li><a href="#">Third PlaceHolder</a></li>
          </ul>
        </nav>
        
        {/* Search Form */}
        <div className="search-form">
          <input
            type="text"
            placeholder="Search stocks..."
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
              <span className="label">Predicted Price</span>
              <span className="value">${selectedStock.predicted_price?.toFixed(2)}</span>
            </div>
            <div className="detail-card">
              <span className="label">Valuation</span>
              <span className="value">{selectedStock.valuation}</span>
            </div>
            <div className="detail-card">
              <span className="label">Relative Error</span>
              <span className={`value ${selectedStock.relative_error >= 0 ? 'positive' : 'negative'}`}>
                {(selectedStock.relative_error * 100).toFixed(2)}%
              </span>
            </div>
          </div>
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
        <ul className="stock-cards">
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
              <div className="stock-price">{isNaN(Number(u.price)) ? `$${u.price} USD` : `$${Number(u.price).toFixed(2)} USD`}</div>
              <div className={`stock-change ${u.change >= 0 ? 'positive' : 'negative'}`}>
                {u.change >= 0 ? '▲' : '▼'} {parseFloat(u.change).toFixed(2)} ({parseFloat(u.changesPercentage).toFixed(2)}%)
              </div>
            </li>
          ))}
        </ul>
      </div>
      {/* Top Gainers */}
      <div className="stock-list gainers">
        <h2>Top Gainers</h2>
        <ul className="stock-cards">
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
              <div className="stock-price">{isNaN(Number(u.price)) ? `$${u.price} USD` : `$${Number(u.price).toFixed(2)} USD`}</div>
              <div className={`stock-change ${u.change >= 0 ? 'positive' : 'negative'}`}>
                {u.change >= 0 ? '▲' : '▼'} {parseFloat(u.change).toFixed(2)} ({parseFloat(u.changesPercentage).toFixed(2)}%)
              </div>
            </li>
          ))}
        </ul>
      </div>
      {/* Top Losers */}
      <div className="stock-list losers">
        <h2>Top Losers</h2>
        <ul className="stock-cards">
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
              <div className="stock-price">{isNaN(Number(u.price)) ? `$${u.price} USD` : `$${Number(u.price).toFixed(2)} USD`}</div>
              <div className={`stock-change ${u.change >= 0 ? 'positive' : 'negative'}`}>
                {u.change >= 0 ? '▲' : '▼'} {parseFloat(u.change).toFixed(2)} ({parseFloat(u.changesPercentage).toFixed(2)}%)
              </div>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

export default App