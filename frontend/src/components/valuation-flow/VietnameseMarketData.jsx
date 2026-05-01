import React from 'react';

/**
 * VietnameseMarketData Component
 * Displays Vietnam-specific market information including:
 * - Foreign Ownership Limit (FOL) status
 * - Exchange information (HOSE, HNX, UPCOM)
 * - VND/USD conversions
 * - Trading calendar info
 * - Sector peers
 * - Market index performance
 */
const VietnameseMarketData = ({ vietnamData }) => {
  if (!vietnamData) return null;

  const {
    stock_info,
    fol_status,
    exchange_info,
    currency_info,
    trading_calendar,
    sector_peers,
    index_data,
    data_quality
  } = vietnamData;

  return (
    <div className="vietnamese-market-data">
      <h3>Vietnamese Market Data</h3>
      
      {/* Stock Basic Info */}
      {stock_info && (
        <div className="info-section">
          <h4>Stock Information</h4>
          <div className="info-grid">
            <div className="info-item">
              <label>Ticker:</label>
              <span>{stock_info.ticker}</span>
            </div>
            <div className="info-item">
              <label>Company Name:</label>
              <span>{stock_info.name_en || stock_info.name_vi}</span>
            </div>
            <div className="info-item">
              <label>Sector:</label>
              <span>{stock_info.sector}</span>
            </div>
            <div className="info-item">
              <label>Exchange:</label>
              <span>{stock_info.exchange}</span>
            </div>
            {stock_info.sub_sector && (
              <div className="info-item">
                <label>Sub-Sector:</label>
                <span>{stock_info.sub_sector}</span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Foreign Ownership Limit */}
      {fol_status && (
        <div className="info-section">
          <h4>Foreign Ownership Status</h4>
          <div className="info-grid">
            <div className="info-item">
              <label>Foreign Limit:</label>
              <span>{fol_status.foreign_limit}%</span>
            </div>
            <div className="info-item">
              <label>Current Foreign Ownership:</label>
              <span>{fol_status.current_foreign_ownership}%</span>
            </div>
            <div className="info-item">
              <label>Available for Foreign:</label>
              <span>{fol_status.available_for_foreign}%</span>
            </div>
            <div className="info-item">
              <label>Status:</label>
              <span className={`status-badge ${fol_status.status.toLowerCase()}`}>
                {fol_status.status}
              </span>
            </div>
          </div>
          {fol_status.status === 'CLOSED' && (
            <div className="warning-box" style={{ marginTop: '10px' }}>
              ⚠️ This stock is currently closed to foreign investors
            </div>
          )}
        </div>
      )}

      {/* Exchange Information */}
      {exchange_info && (
        <div className="info-section">
          <h4>Exchange Information</h4>
          <div className="info-grid">
            <div className="info-item">
              <label>Market:</label>
              <span>{exchange_info.market_name}</span>
            </div>
            <div className="info-item">
              <label>Trading Hours:</label>
              <span>{exchange_info.trading_hours}</span>
            </div>
            <div className="info-item">
              <label>Settlement:</label>
              <span>T+{exchange_info.settlement_cycle}</span>
            </div>
            <div className="info-item">
              <label>Currency:</label>
              <span>{exchange_info.currency}</span>
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
              <span>VND (Vietnamese Dong)</span>
            </div>
            <div className="info-item">
              <label>USD/VND Rate:</label>
              <span>{currency_info.usd_vnd_rate?.toLocaleString()}</span>
            </div>
            {currency_info.market_cap_usd && (
              <div className="info-item">
                <label>Market Cap (USD):</label>
                <span>${currency_info.market_cap_usd.toLocaleString()}M</span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Trading Calendar */}
      {trading_calendar && (
        <div className="info-section">
          <h4>Trading Calendar</h4>
          <div className="info-grid">
            <div className="info-item">
              <label>Market Status:</label>
              <span className={`status-badge ${trading_calendar.is_open ? 'open' : 'closed'}`}>
                {trading_calendar.is_open ? 'Open' : 'Closed'}
              </span>
            </div>
            <div className="info-item">
              <label>Next Trading Day:</label>
              <span>{trading_calendar.next_trading_day}</span>
            </div>
            {trading_calendar.upcoming_holiday && (
              <div className="info-item">
                <label>Next Holiday:</label>
                <span>{trading_calendar.upcoming_holiday}</span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Sector Peers */}
      {sector_peers && sector_peers.length > 0 && (
        <div className="info-section">
          <h4>Sector Peers ({sector_peers.length})</h4>
          <div className="peers-list">
            {sector_peers.slice(0, 10).map((peer, idx) => (
              <div key={idx} className="peer-item">
                <span className="peer-ticker">{peer.ticker}</span>
                <span className="peer-name">{peer.name_en || peer.name_vi}</span>
                {peer.market_cap && (
                  <span className="peer-mcap">
                    {peer.market_cap.toLocaleString()}B VND
                  </span>
                )}
              </div>
            ))}
            {sector_peers.length > 10 && (
              <div className="more-peers">+{sector_peers.length - 10} more peers</div>
            )}
          </div>
        </div>
      )}

      {/* Index Data */}
      {index_data && (
        <div className="info-section">
          <h4>Market Index Performance</h4>
          <div className="info-grid">
            <div className="info-item">
              <label>Index:</label>
              <span>{index_data.index_name}</span>
            </div>
            <div className="info-item">
              <label>Current Level:</label>
              <span>{index_data.current_level?.toLocaleString()}</span>
            </div>
            <div className="info-item">
              <label>Change:</label>
              <span className={index_data.change_percent >= 0 ? 'positive' : 'negative'}>
                {index_data.change_percent >= 0 ? '+' : ''}{index_data.change_percent.toFixed(2)}%
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Data Quality Assessment */}
      {data_quality && (
        <div className="info-section">
          <h4>Data Quality Assessment</h4>
          <div className="quality-indicator">
            <div className={`quality-badge quality-${data_quality.overall_score.toLowerCase()}`}>
              {data_quality.overall_score}
            </div>
            <p style={{ marginTop: '8px', fontSize: '0.9em' }}>{data_quality.notes}</p>
            {data_quality.recommendations && data_quality.recommendations.length > 0 && (
              <ul style={{ marginTop: '8px', fontSize: '0.85em', color: '#666' }}>
                {data_quality.recommendations.map((rec, idx) => (
                  <li key={idx}>{rec}</li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default VietnameseMarketData;
