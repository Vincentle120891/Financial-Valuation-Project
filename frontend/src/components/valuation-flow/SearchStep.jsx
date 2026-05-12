import React, { useState } from 'react';
import { searchVietnameseStocks } from '../../services/api';

/**
 * SearchStep Component
 * Step 1: Input Company Name or Ticker
 * 
 * Features:
 * - Market toggle (International/Vietnamese)
 * - Search input with enter key support
 * - Search results display
 * - Error handling
 * - Vietnamese stock search integration
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
  onSelectCompany,
  marketValidation
}) => {
  const [vietnameseSearchLoading, setVietnameseSearchLoading] = useState(false);
  
  const handleKeyPress = async (e) => {
    if (e.key === 'Enter') {
      await performSearch();
    }
  };

  const performSearch = async () => {
    if (market === 'vietnamese' && searchQuery.trim()) {
      // Use Vietnamese-specific search - results will be handled by parent's handleSearch
      setVietnameseSearchLoading(true);
      try {
        // Call onSearch which triggers parent's handleSearch to fetch and set results
        await onSearch();
      } catch (err) {
        console.error('Vietnamese search error:', err);
      } finally {
        setVietnameseSearchLoading(false);
      }
    } else {
      // Use international search
      await onSearch();
    }
  };

  const isLoading = loading || vietnameseSearchLoading;

  return (
    <div className="step-container">
      <h2>Step 1: Search Company</h2>
      <p style={{ marginBottom: '20px', color: '#666' }}>Enter a company name or ticker symbol to begin your valuation analysis.</p>
      
      {/* Market Validation Feedback */}
      {marketValidation && marketValidation.message && (
        <div 
          className={`validation-message ${marketValidation.isValid ? 'success' : 'error'}`}
          style={{
            marginTop: '15px',
            padding: '12px 16px',
            borderRadius: '6px',
            backgroundColor: marketValidation.isValid ? '#d4edda' : '#f8d7da',
            border: `1px solid ${marketValidation.isValid ? '#c3e6cb' : '#f5c6cb'}`,
            color: marketValidation.isValid ? '#155724' : '#721c24',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}
        >
          <span style={{ fontSize: '1.2em' }}>
            {marketValidation.isValid ? '✓' : '⚠️'}
          </span>
          <span>{marketValidation.message}</span>
        </div>
      )}

      {/* Market Toggle */}
      <div className="market-toggle" style={{ marginBottom: '20px', marginTop: '20px' }}>
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
              ? "Enter ticker (e.g., VNM, VIC, HPG) or company name (Vinamilk, Vingroup)" 
              : "Enter ticker (e.g., AAPL, MSFT) or company name"
          }
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          onKeyPress={handleKeyPress}
          className="search-input"
          disabled={isLoading}
        />
        <button 
          onClick={performSearch} 
          disabled={isLoading} 
          className="btn-primary"
        >
          {isLoading ? 'Searching...' : 'Search'}
        </button>
      </div>

      {/* Market-specific hints */}
      {market === 'vietnamese' && (
        <div className="market-hint" style={{ marginTop: '10px', fontSize: '0.9em', color: '#666' }}>
          <p><strong>Popular Vietnamese stocks:</strong> VNM (Vinamilk), VIC (Vingroup), HPG (Hoa Phat), VCB (Vietcombank), FPT (FPT Corp)</p>
          <p><strong>Supported exchanges:</strong> HOSE (.VN), HNX (.HA), UPCOM (.VC)</p>
        </div>
      )}

      {/* Search Results */}
      {searchResults.length > 0 && (
        <div className="search-results">
          {searchResults.map((result, index) => {
            // Create a more unique key by combining symbol, name, and index
            const uniqueKey = `${result.symbol}-${result.name}-${index}`;
            
            return (
              <div key={uniqueKey} className="result-item">
                <div style={{ flex: 1 }}>
                  <span style={{ fontWeight: 'bold' }}>{result.name}</span>
                  <span style={{ marginLeft: '8px', color: '#666' }}>({result.symbol})</span>
                  {result.sector && (
                    <span style={{ marginLeft: '8px', fontSize: '0.85em', color: '#888' }}>
                      • {result.sector}
                    </span>
                  )}
                  {result.exchange && (
                    <span style={{ marginLeft: '8px', fontSize: '0.85em', color: '#888' }}>
                      • {result.exchange}
                    </span>
                  )}
                </div>
                <button 
                  onClick={() => onSelectCompany(result)} 
                  className="btn-secondary"
                >
                  Select
                </button>
              </div>
            );
          })}
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
