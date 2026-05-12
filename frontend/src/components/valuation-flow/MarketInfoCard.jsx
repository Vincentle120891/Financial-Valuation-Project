import React from 'react';
import {
  formatCurrency,
  formatPercent,
  formatNumber,
  extractValue,
  getRecommendedUnit
} from '../../utils/dataUtils';

/**
 * MarketInfoCard Component
 *
 * A reusable component that displays market-specific information cards.
 * Replaces both InternationalMarketData and VietnameseMarketData components.
 * Accepts unified data structure and renders based on available fields.
 *
 * @param {Object} marketData - Market data object with standardized fields
 * @param {string} marketType - Market type ('international' or 'vietnamese')
 * @param {string} title - Optional custom title
 */
const MarketInfoCard = ({ marketData, marketType = 'international', title = null }) => {
  if (!marketData) {
    return null;
  }

  const currency = marketType === 'vietnamese' ? 'VND' : 'USD';
  const locale = marketType === 'vietnamese' ? 'vi-VN' : 'en-US';

  // Default title based on market type
  const defaultTitle = marketType === 'vietnamese'
    ? '🇻🇳 Vietnamese Market Data'
    : '🌍 International Market Data';

  const displayTitle = title || defaultTitle;

  // Helper to render info grid item
  const renderInfoItem = (label, value, type = 'text', highlight = false) => {
    const extractedValue = extractValue(value);

    if (extractedValue === null || extractedValue === undefined) {
      return null;
    }

    let formattedValue;
    switch (type) {
      case 'currency':
        formattedValue = formatCurrency(extractedValue, currency, 'auto');
        break;
      case 'percent':
        formattedValue = formatPercent(extractedValue, false, 2);
        break;
      case 'number':
        formattedValue = formatNumber(extractedValue, locale, 2);
        break;
      default:
        formattedValue = String(extractedValue);
    }

    return (
      <div className="info-item" style={{
        padding: '10px 0',
        borderBottom: '1px solid #f0f0f0',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <label style={{
          fontWeight: 500,
          color: '#616161',
          fontSize: '13px'
        }}>
          {label}
        </label>
        <span style={{
          fontWeight: highlight ? 600 : 400,
          color: highlight ? '#1976d2' : '#212121',
          fontSize: '14px'
        }}>
          {formattedValue}
        </span>
      </div>
    );
  };

  // Render section with title and items
  const renderSection = (sectionTitle, items, icon = '📊') => {
    const hasItems = items.some(item => item.value !== null && item.value !== undefined);

    if (!hasItems) {
      return null;
    }

    return (
      <div className="market-info-section" style={{
        marginBottom: '24px',
        border: '1px solid #e0e0e0',
        borderRadius: '8px',
        overflow: 'hidden'
      }}>
        <div style={{
          background: 'linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)',
          padding: '12px 16px',
          borderBottom: '1px solid #e0e0e0'
        }}>
          <h4 style={{
            margin: 0,
            fontSize: '15px',
            fontWeight: 600,
            color: '#37474f'
          }}>
            {icon} {sectionTitle}
          </h4>
        </div>
        <div style={{ padding: '16px' }}>
          {items.map((item, idx) => renderInfoItem(item.label, item.value, item.type, item.highlight))}
        </div>
      </div>
    );
  };

  // Build sections based on available data
  const sections = [];

  // Company/Stock Information Section
  if (marketData.stock_info || marketData.ticker_info) {
    const info = marketData.stock_info || marketData.ticker_info;
    sections.push({
      title: marketType === 'vietnamese' ? 'Stock Information' : 'Company Information',
      icon: marketType === 'vietnamese' ? '🏢' : '🏭',
      items: [
        { label: marketType === 'vietnamese' ? 'Ticker' : 'Symbol', value: info.ticker || info.symbol, type: 'text', highlight: true },
        { label: 'Company Name', value: info.name_en || info.name_vi || info.name, type: 'text' },
        { label: 'Sector', value: info.sector, type: 'text' },
        { label: 'Industry', value: info.industry, type: 'text' },
        { label: 'Exchange', value: info.exchange, type: 'text' },
        { label: 'Sub-Sector', value: info.sub_sector, type: 'text' }
      ]
    });
  }

  // Market/Exchange Information Section
  if (marketData.market_info || marketData.exchange_info) {
    const info = marketData.market_info || marketData.exchange_info;
    sections.push({
      title: 'Market Information',
      icon: '📈',
      items: [
        { label: 'Market Name', value: info.market_name || info.exchange_name, type: 'text', highlight: true },
        { label: 'Market Code', value: info.market_code, type: 'text' },
        { label: 'Region', value: info.region, type: 'text' },
        { label: 'Trading Hours', value: info.trading_hours, type: 'text' },
        { label: 'Settlement', value: info.settlement_cycle ? `T+${info.settlement_cycle}` : null, type: 'text' },
        { label: 'Currency', value: info.currency || 'USD', type: 'text' }
      ]
    });
  }

  // Currency Information Section
  if (marketData.currency_info) {
    const info = marketData.currency_info;
    sections.push({
      title: 'Currency Information',
      icon: '💱',
      items: [
        { label: 'Local Currency', value: marketType === 'vietnamese' ? 'VND (Vietnamese Dong)' : `${info.currency_code} (${info.currency_name})`, type: 'text' },
        { label: marketType === 'vietnamese' ? 'USD/VND Rate' : `USD/${info.currency_code || ''} Rate`, value: info.usd_vnd_rate || info.usd_exchange_rate, type: 'number' },
        { label: 'Market Cap (USD)', value: info.market_cap_usd, type: 'currency', highlight: true }
      ]
    });
  }

  // Vietnam-specific: Foreign Ownership Status
  if (marketType === 'vietnamese' && marketData.fol_status) {
    const info = marketData.fol_status;
    sections.push({
      title: 'Foreign Ownership Status',
      icon: '🌐',
      items: [
        { label: 'Foreign Limit', value: `${info.foreign_limit}%`, type: 'percent', highlight: true },
        { label: 'Current Foreign Ownership', value: `${info.current_foreign_ownership}%`, type: 'percent' },
        { label: 'Available for Foreign', value: `${info.available_for_foreign}%`, type: 'percent' },
        { label: 'Status', value: info.status, type: 'text', highlight: info.status === 'CLOSED' }
      ],
      warning: info.status === 'CLOSED' ? '⚠️ This stock is currently closed to foreign investors' : null
    });
  }

  // Vietnam-specific: Trading Calendar
  if (marketType === 'vietnamese' && marketData.trading_calendar) {
    const info = marketData.trading_calendar;
    sections.push({
      title: 'Trading Calendar',
      icon: '📅',
      items: [
        { label: 'Market Status', value: info.is_open ? 'Open' : 'Closed', type: 'text', highlight: true },
        { label: 'Next Trading Day', value: info.next_trading_day, type: 'text' },
        { label: 'Next Holiday', value: info.upcoming_holiday, type: 'text' }
      ]
    });
  }

  // Data Availability (International)
  if (marketType === 'international' && marketData.data_availability) {
    const info = marketData.data_availability;
    sections.push({
      title: 'Data Availability',
      icon: '✅',
      items: [
        { label: 'Financial Statements', value: info.financials ? '✓ Available' : '✗ Not Available', type: 'text', highlight: info.financials },
        { label: 'Analyst Estimates', value: info.estimates ? '✓ Available' : '✗ Not Available', type: 'text', highlight: info.estimates },
        { label: 'Historical Prices', value: info.historical_prices ? '✓ Available' : '✗ Not Available', type: 'text', highlight: info.historical_prices },
        { label: 'Key Statistics', value: info.key_stats ? '✓ Available' : '✗ Not Available', type: 'text', highlight: info.key_stats }
      ],
      warnings: info.warnings
    });
  }

  // Peers Section
  if (marketData.sector_peers || marketData.regional_peers) {
    const peers = marketData.sector_peers || marketData.regional_peers;
    sections.push({
      title: `Sector Peers (${peers.length})`,
      icon: '🏢',
      items: peers.slice(0, 10).map(peer => ({
        label: peer.ticker || peer.symbol,
        value: `${peer.name_en || peer.name_vi || peer.name} - ${formatCurrency(peer.market_cap, currency, 'auto')}`,
        type: 'text'
      }))
    });
  }

  // Index Data (Vietnam)
  if (marketType === 'vietnamese' && marketData.index_data) {
    const info = marketData.index_data;
    sections.push({
      title: 'Market Index Performance',
      icon: '📊',
      items: [
        { label: 'Index', value: info.index_name, type: 'text', highlight: true },
        { label: 'Current Level', value: info.current_level, type: 'number' },
        { label: 'Change', value: `${info.change_percent >= 0 ? '+' : ''}${info.change_percent.toFixed(2)}%`, type: 'percent' }
      ]
    });
  }

  // Data Quality Assessment
  if (marketData.data_quality) {
    const info = marketData.data_quality;
    sections.push({
      title: 'Data Quality Assessment',
      icon: '⭐',
      items: [
        { label: 'Overall Score', value: info.overall_score, type: 'text', highlight: true }
      ],
      notes: info.notes,
      recommendations: info.recommendations
    });
  }

  return (
    <div className="market-info-card" style={{
      maxWidth: '800px',
      margin: '0 auto'
    }}>
      <h3 style={{
        fontSize: '20px',
        fontWeight: 700,
        color: '#1a237e',
        marginBottom: '20px',
        textAlign: 'center'
      }}>
        {displayTitle}
      </h3>

      {sections.map((section, idx) => (
        <React.Fragment key={idx}>
          {renderSection(section.title, section.items, section.icon)}

          {/* Warning message if present */}
          {section.warning && (
            <div style={{
              background: '#fff3e0',
              border: '1px solid #ffb74d',
              borderRadius: '6px',
              padding: '12px 16px',
              marginBottom: '16px',
              color: '#e65100',
              fontWeight: 500
            }}>
              {section.warning}
            </div>
          )}

          {/* Warnings list if present */}
          {section.warnings && section.warnings.length > 0 && (
            <div style={{
              background: '#fff3e0',
              border: '1px solid #ffb74d',
              borderRadius: '6px',
              padding: '12px 16px',
              marginBottom: '16px'
            }}>
              <p style={{
                margin: '0 0 8px 0',
                fontWeight: 600,
                color: '#e65100'
              }}>
                ⚠️ Warnings:
              </p>
              <ul style={{
                margin: 0,
                paddingLeft: '20px',
                color: '#ef6c00',
                fontSize: '13px'
              }}>
                {section.warnings.map((warning, wIdx) => (
                  <li key={wIdx}>{warning}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Notes if present */}
          {section.notes && (
            <p style={{
              background: '#e3f2fd',
              border: '1px solid #90caf9',
              borderRadius: '6px',
              padding: '12px 16px',
              marginBottom: '16px',
              color: '#1565c0',
              fontSize: '13px',
              margin: '0 0 16px 0'
            }}>
              📝 {section.notes}
            </p>
          )}

          {/* Recommendations if present */}
          {section.recommendations && section.recommendations.length > 0 && (
            <div style={{
              background: '#f3e5f5',
              border: '1px solid #ce93d8',
              borderRadius: '6px',
              padding: '12px 16px',
              marginBottom: '16px'
            }}>
              <p style={{
                margin: '0 0 8px 0',
                fontWeight: 600,
                color: '#6a1b9a'
              }}>
                💡 Recommendations:
              </p>
              <ul style={{
                margin: 0,
                paddingLeft: '20px',
                color: '#7b1fa2',
                fontSize: '13px'
              }}>
                {section.recommendations.map((rec, rIdx) => (
                  <li key={rIdx}>{rec}</li>
                ))}
              </ul>
            </div>
          )}
        </React.Fragment>
      ))}

      {sections.length === 0 && (
        <div style={{
          background: '#f5f5f5',
          border: '1px solid #e0e0e0',
          borderRadius: '8px',
          padding: '24px',
          textAlign: 'center',
          color: '#757575'
        }}>
          No market data available
        </div>
      )}
    </div>
  );
};

export default MarketInfoCard;