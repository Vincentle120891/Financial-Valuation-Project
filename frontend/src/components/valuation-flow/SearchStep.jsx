import React from 'react';

/**
 * SearchStep Component
 * Step 1: Input Company Name or Ticker
 * 
 * Features:
 * - Market toggle (International/Vietnamese)
 * - Search input with enter key support
 * - Search results display
 * - Error handling
 */
const SearchStep = ({ 
  searchQuery, 
  setSearchQuery, 
  searchResults, 
  loading, 
  error, 
  market, 
  setMarket, 
  onSearch, 
  onSelectCompany 
}) => {
  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      onSearch();
    }
  };

  return (
    <div className="step-container">
      <h2>Step 1: Input Company Name or Ticker</h2>
      
      {/* Market Toggle */}
      <div className="market-toggle" style={{ marginBottom: '20px' }}>
        <label style={{ marginRight: '20px' }}>
          <input
            type="radio"
            value="international"
            checked={market === 'international'}
            onChange={(e) => setMarket(e.target.value)}
          />
          International Company
        </label>
        <label>
          <input
            type="radio"
            value="vietnamese"
            checked={market === 'vietnamese'}
            onChange={(e) => setMarket(e.target.value)}
          />
          Vietnamese Company
        </label>
      </div>

      {/* Search Input */}
      <div className="input-group">
        <input
          type="text"
          placeholder={
            market === 'vietnamese' 
              ? "Enter ticker (e.g., VNM) or company name" 
              : "Enter ticker (e.g., AAPL) or company name"
          }
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          onKeyPress={handleKeyPress}
          className="search-input"
        />
        <button 
          onClick={onSearch} 
          disabled={loading} 
          className="btn-primary"
        >
          {loading ? 'Searching...' : 'Search'}
        </button>
      </div>

      {/* Search Results */}
      {searchResults.length > 0 && (
        <div className="search-results">
          {searchResults.map((result) => (
            <div key={result.symbol} className="result-item">
              <span>{result.name} ({result.symbol}) - {result.exchange}</span>
              <button 
                onClick={() => onSelectCompany(result)} 
                className="btn-secondary"
              >
                Select
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Error Message */}
      {error && (
        <div className="error-message">{error}</div>
      )}
    </div>
  );
};

export default SearchStep;
