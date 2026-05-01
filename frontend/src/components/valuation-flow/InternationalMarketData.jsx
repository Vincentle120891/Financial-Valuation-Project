import React from 'react';

/**
 * InternationalMarketData Component
 * Displays international market information including:
 * - Market/exchange details
 * - Currency information
 * - Data availability status
 * - Regional peers
 */
const InternationalMarketData = ({ internationalData }) => {
  if (!internationalData) return null;

  const {
    ticker_info,
    market_info,
    currency_info,
    data_availability,
    regional_peers
  } = internationalData;

  return (
    <div className="international-market-data">
      <h3>International Market Data</h3>
      
      {/* Ticker Basic Info */}
      {ticker_info && (
        <div className="info-section">
          <h4>Company Information</h4>
          <div className="info-grid">
            <div className="info-item">
              <label>Ticker:</label>
              <span>{ticker_info.symbol}</span>
            </div>
            <div className="info-item">
              <label>Company Name:</label>
              <span>{ticker_info.name}</span>
            </div>
            {ticker_info.sector && (
              <div className="info-item">
                <label>Sector:</label>
                <span>{ticker_info.sector}</span>
              </div>
            )}
            {ticker_info.industry && (
              <div className="info-item">
                <label>Industry:</label>
                <span>{ticker_info.industry}</span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Market Information */}
      {market_info && (
        <div className="info-section">
          <h4>Market Information</h4>
          <div className="info-grid">
            <div className="info-item">
              <label>Exchange:</label>
              <span>{market_info.exchange_name}</span>
            </div>
            <div className="info-item">
              <label>Market Code:</label>
              <span>{market_info.market_code}</span>
            </div>
            <div className="info-item">
              <label>Region:</label>
              <span>{market_info.region}</span>
            </div>
            <div className="info-item">
              <label>Trading Hours:</label>
              <span>{market_info.trading_hours}</span>
            </div>
          </div>
        </div>
      )}

      {/* Currency Information */}
      {currency_info && (
        <div className="info-section">
          <h4>Currency Information</h4>
          <div className="info-grid">
            <div className="info-item">
              <label>Local Currency:</label>
              <span>{currency_info.currency_code} ({currency_info.currency_name})</span>
            </div>
            {currency_info.usd_exchange_rate && (
              <div className="info-item">
                <label>USD/{currency_info.currency_code} Rate:</label>
                <span>{currency_info.usd_exchange_rate.toFixed(4)}</span>
              </div>
            )}
            {currency_info.market_cap_usd && (
              <div className="info-item">
                <label>Market Cap (USD):</label>
                <span>${currency_info.market_cap_usd.toLocaleString()}M</span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Data Availability */}
      {data_availability && (
        <div className="info-section">
          <h4>Data Availability</h4>
          <div className="availability-grid">
            <div className="availability-item">
              <label>Financial Statements:</label>
              <span className={`status-badge ${data_availability.financials ? 'available' : 'unavailable'}`}>
                {data_availability.financials ? '✓ Available' : '✗ Not Available'}
              </span>
            </div>
            <div className="availability-item">
              <label>Analyst Estimates:</label>
              <span className={`status-badge ${data_availability.estimates ? 'available' : 'unavailable'}`}>
                {data_availability.estimates ? '✓ Available' : '✗ Limited'}
              </span>
            </div>
            <div className="availability-item">
              <label>Historical Prices:</label>
              <span className={`status-badge ${data_availability.historical_prices ? 'available' : 'unavailable'}`}>
                {data_availability.historical_prices ? '✓ Available' : '✗ Not Available'}
              </span>
            </div>
            <div className="availability-item">
              <label>Key Statistics:</label>
              <span className={`status-badge ${data_availability.key_stats ? 'available' : 'unavailable'}`}>
                {data_availability.key_stats ? '✓ Available' : '✗ Limited'}
              </span>
            </div>
          </div>
          {data_availability.warnings && data_availability.warnings.length > 0 && (
            <div className="warning-box" style={{ marginTop: '10px' }}>
              <strong>Warnings:</strong>
              <ul>
                {data_availability.warnings.map((warning, idx) => (
                  <li key={idx}>{warning}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Regional Peers */}
      {regional_peers && regional_peers.length > 0 && (
        <div className="info-section">
          <h4>Regional Peers ({regional_peers.length})</h4>
          <div className="peers-list">
            {regional_peers.slice(0, 8).map((peer, idx) => (
              <div key={idx} className="peer-item">
                <span className="peer-ticker">{peer.symbol}</span>
                <span className="peer-name">{peer.name}</span>
                {peer.market_cap && (
                  <span className="peer-mcap">
                    ${peer.market_cap.toLocaleString()}M
                  </span>
                )}
              </div>
            ))}
            {regional_peers.length > 8 && (
              <div className="more-peers">+{regional_peers.length - 8} more peers</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default InternationalMarketData;
