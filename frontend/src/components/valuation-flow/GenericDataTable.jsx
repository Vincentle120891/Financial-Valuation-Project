import React from 'react';
import {
  formatCurrency,
  formatPercent,
  formatNumber,
  extractValue,
  extractDataField,
  getRecommendedUnit
} from '../../utils/dataUtils';

/**
 * GenericDataTable Component
 *
 * A reusable table component that renders DataField arrays from unified schema.
 * Automatically handles currency formatting, unit scaling, and status indicators.
 *
 * @param {Array} columns - Column definitions with field keys and metadata
 * @param {Object} data - Data object containing fields to display
 * @param {string} market - Market type ('international' or 'vietnamese') for currency/unit handling
 * @param {boolean} showStatus - Whether to show status badges (RETRIEVED, CALCULATED, etc.)
 * @param {string} title - Optional table title
 */
const GenericDataTable = ({
  columns,
  data,
  market = 'international',
  showStatus = true,
  title = null
}) => {
  if (!data || !columns || columns.length === 0) {
    return null;
  }

  const currency = market === 'vietnamese' ? 'VND' : 'USD';

  // Helper to render cell value based on column type
  const renderCellValue = (value, column) => {
    const extractedValue = extractValue(value);

    if (extractedValue === null || extractedValue === undefined) {
      return <span style={{ color: '#999', fontStyle: 'italic' }}>N/A</span>;
    }

    switch (column.type) {
      case 'currency':
        return (
          <span title={`${extractedValue} ${currency}`}>
            {formatCurrency(extractedValue, currency, column.unit || 'auto')}
          </span>
        );

      case 'percent':
        return (
          <span>
            {formatPercent(extractedValue, column.isDecimal ?? false, column.decimals ?? 2)}
          </span>
        );

      case 'number':
        return (
          <span>
            {formatNumber(extractedValue, market === 'vietnamese' ? 'vi-VN' : 'en-US', column.decimals ?? 2)}
          </span>
        );

      case 'text':
      default:
        return <span>{String(extractedValue)}</span>;
    }
  };

  // Helper to render status badge
  const renderStatusBadge = (field) => {
    const dataField = extractDataField(field);

    const statusStyles = {
      RETRIEVED: { bg: '#e8f5e9', color: '#2e7d32', label: '✓ FETCHED' },
      CALCULATED: { bg: '#e3f2fd', color: '#1976d2', label: '📊 CALCULATED' },
      ESTIMATED: { bg: '#fff3e0', color: '#f57c00', label: '🔮 ESTIMATED' },
      MANUAL_OVERRIDE: { bg: '#f3e5f5', color: '#7b1fa2', label: '✏️ MANUAL' },
      MISSING: { bg: '#ffebee', color: '#c62828', label: '⚠ MISSING' }
    };

    const style = statusStyles[dataField.status] || statusStyles.MISSING;

    return (
      <span style={{
        background: style.bg,
        color: style.color,
        padding: '2px 8px',
        borderRadius: '4px',
        fontSize: '10px',
        fontWeight: 600,
        whiteSpace: 'nowrap'
      }}>
        {style.label}
      </span>
    );
  };

  return (
    <div className="generic-data-table" style={{
      marginBottom: '20px',
      border: '1px solid #e0e0e0',
      borderRadius: '8px',
      overflow: 'hidden'
    }}>
      {title && (
        <div style={{
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          color: 'white',
          padding: '12px 16px',
          fontWeight: 600
        }}>
          {title}
        </div>
      )}

      <div className="table-responsive" style={{ overflowX: 'auto' }}>
        <table style={{
          width: '100%',
          borderCollapse: 'collapse',
          fontSize: '13px'
        }}>
          <thead>
            <tr style={{ background: '#f5f5f5', borderBottom: '2px solid #e0e0e0' }}>
              {columns.map((col, idx) => (
                <th key={idx} style={{
                  padding: '12px',
                  textAlign: col.align || 'left',
                  fontWeight: 600,
                  color: '#424242',
                  minWidth: col.minWidth || 'auto'
                }}>
                  {col.header}
                  {col.tooltip && (
                    <span style={{
                      marginLeft: '4px',
                      color: '#9e9e9e',
                      cursor: 'help',
                      fontSize: '11px'
                    }} title={col.tooltip}>
                      ℹ️
                    </span>
                  )}
                </th>
              ))}
              {showStatus && (
                <th style={{
                  padding: '12px',
                  textAlign: 'center',
                  fontWeight: 600,
                  color: '#424242',
                  minWidth: '100px'
                }}>
                  Status
                </th>
              )}
            </tr>
          </thead>
          <tbody>
            {columns.map((col, rowIdx) => {
              const fieldKey = col.field;
              const fieldValue = data[fieldKey];

              return (
                <tr
                  key={rowIdx}
                  style={{
                    borderBottom: rowIdx < columns.length - 1 ? '1px solid #f0f0f0' : 'none',
                    background: rowIdx % 2 === 0 ? 'white' : '#fafafa'
                  }}
                >
                  <td style={{
                    padding: '12px',
                    fontWeight: 500,
                    color: '#424242'
                  }}>
                    {col.label || fieldKey}
                  </td>
                  <td style={{
                    padding: '12px',
                    textAlign: col.align || 'left',
                    color: fieldValue === null || fieldValue === undefined ? '#999' : '#212121'
                  }}>
                    {renderCellValue(fieldValue, col)}
                  </td>
                  {showStatus && (
                    <td style={{
                      padding: '12px',
                      textAlign: 'center'
                    }}>
                      {fieldValue !== null && fieldValue !== undefined ? renderStatusBadge(fieldValue) : '-'}
                    </td>
                  )}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default GenericDataTable;