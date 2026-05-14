import React from 'react';

/**
 * DataFieldDisplay Component
 * 
 * Standardized component for rendering DataField objects from the unified schema.
 * Handles all metadata display including status indicators, sources, confidence scores,
 * and period-based values.
 * 
 * @param {Object} dataField - The DataField object from unified schema
 * @param {string} label - Display label for the field
 * @param {string} unit - Unit override (optional, uses dataField.unit if not provided)
 * @param {boolean} showMetadata - Whether to show detailed metadata (default: true)
 * @param {string} size - Size variant: 'small', 'medium', 'large' (default: 'medium')
 */
const DataFieldDisplay = ({ 
  dataField, 
  label, 
  unit, 
  showMetadata = true, 
  size = 'medium' 
}) => {
  // Handle missing or invalid dataField
  if (!dataField) {
    return (
      <div style={{
        padding: size === 'small' ? '8px' : '12px',
        background: '#f5f5f5',
        borderRadius: '6px',
        border: '2px dashed #9e9e9e',
        opacity: 0.7
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
          <strong style={{ color: '#9e9e9e' }}>{label}</strong>
          <span style={{
            background: '#9e9e9e',
            color: 'white',
            padding: '2px 8px',
            borderRadius: '4px',
            fontSize: size === 'small' ? '10px' : '11px',
            fontWeight: 600
          }}>⚠ MISSING</span>
        </div>
        <div style={{ textAlign: 'center', color: '#9e9e9e', fontSize: '12px' }}>
          No data available
        </div>
      </div>
    );
  }

  // Determine status information
  const getStatusInfo = () => {
    if (dataField.is_missing || dataField.value === null || dataField.value === undefined) {
      return { 
        status: 'MISSING', 
        label: '⚠ MISSING', 
        color: '#ff9800', 
        bg: '#fff3e0',
        icon: '⚠️'
      };
    }

    switch (dataField.status) {
      case 'RETRIEVED':
        return { 
          status: 'RETRIEVED', 
          label: '✓ FETCHED', 
          color: '#4caf50', 
          bg: '#e8f5e9',
          icon: '✓'
        };
      case 'CALCULATED':
        return { 
          status: 'CALCULATED', 
          label: '📊 CALCULATED', 
          color: '#2196f3', 
          bg: '#e3f2fd',
          icon: '📊'
        };
      case 'MANUAL_OVERRIDE':
        return { 
          status: 'USER_INPUT', 
          label: '✏️ MANUAL', 
          color: '#9c27b0', 
          bg: '#f3e5f5',
          icon: '✏️'
        };
      case 'ESTIMATED':
        return { 
          status: 'AI_GENERATED', 
          label: '🤖 AI', 
          color: '#ff5722', 
          bg: '#fbe9e7',
          icon: '🤖'
        };
      default:
        return { 
          status: 'UNKNOWN', 
          label: '? UNKNOWN', 
          color: '#9e9e9e', 
          bg: '#f5f5f5',
          icon: '?'
        };
    }
  };

  const statusInfo = getStatusInfo();

  // Check if we have actual values
  const hasValues = () => {
    if (Array.isArray(dataField.value)) {
      return dataField.value.some(pv => pv.value !== null && pv.value !== undefined);
    }
    return dataField.value !== null && dataField.value !== undefined;
  };

  const hasData = hasValues();

  // Format value based on unit
  const formatValue = (value, fieldUnit) => {
    if (value === null || value === undefined) return 'N/A';
    
    const displayUnit = unit || fieldUnit;
    
    if (displayUnit === '%') {
      // Handle decimal percentages (e.g., 0.15 -> 15.00%)
      const numericValue = typeof value === 'number' ? value : parseFloat(value);
      if (!isNaN(numericValue)) {
        // If value is between -1 and 1, assume it's a decimal percentage
        if (Math.abs(numericValue) <= 1 && numericValue !== 0) {
          return `${(numericValue * 100).toFixed(2)}%`;
        }
        return `${numericValue.toFixed(2)}%`;
      }
      return `${value}%`;
    }
    
    if (displayUnit === 'USD' || displayUnit === 'VND') {
      const numericValue = typeof value === 'number' ? value : parseFloat(value);
      if (!isNaN(numericValue)) {
        const absNum = Math.abs(numericValue);
        if (absNum >= 1e12) return `${(numericValue / 1e12).toFixed(2)}T`;
        if (absNum >= 1e9) return `${(numericValue / 1e9).toFixed(2)}B`;
        if (absNum >= 1e6) return `${(numericValue / 1e6).toFixed(2)}M`;
        if (absNum >= 1e3) return `${(numericValue / 1e3).toFixed(2)}K`;
        return numericValue.toFixed(2);
      }
    }
    
    return value;
  };

  // Get periods from array values
  const getPeriods = () => {
    if (!dataField.value) return [];
    if (Array.isArray(dataField.value)) {
      return dataField.value
        .filter(pv => pv.period !== null && pv.period !== undefined)
        .map(pv => pv.period);
    }
    return ['Current'];
  };

  const periods = getPeriods();

  // Size configurations
  const sizeConfig = {
    small: { padding: '8px', fontSize: '11px', periodFontSize: '10px', valueFontSize: '12px' },
    medium: { padding: '12px', fontSize: '12px', periodFontSize: '11px', valueFontSize: '13px' },
    large: { padding: '16px', fontSize: '14px', periodFontSize: '12px', valueFontSize: '15px' }
  };

  const config = sizeConfig[size];

  return (
    <div style={{
      padding: config.padding,
      background: 'white',
      borderRadius: '6px',
      border: hasData ? `2px solid ${statusInfo.color}` : '2px dashed #ff9800',
      opacity: hasData ? 1 : 0.7,
      transition: 'all 0.2s ease'
    }}>
      {/* Header with label and status */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
        <strong style={{ color: hasData ? statusInfo.color : '#f57c00', fontSize: config.fontSize }}>
          {label}
        </strong>
        <span style={{
          background: statusInfo.color,
          color: 'white',
          padding: '2px 8px',
          borderRadius: '4px',
          fontSize: size === 'small' ? '10px' : '11px',
          fontWeight: 600,
          display: 'flex',
          alignItems: 'center',
          gap: '4px'
        }}>
          {statusInfo.icon} {statusInfo.label.split(' ')[1]}
        </span>
      </div>

      {/* Values grid */}
      {hasData && (
        <>
          <div style={{ 
            display: 'grid', 
            gridTemplateColumns: 'repeat(auto-fit, minmax(80px, 1fr))', 
            gap: '6px', 
            marginBottom: showMetadata ? '8px' : '0' 
          }}>
            {(Array.isArray(dataField.value) ? dataField.value : [{ period: 'Current', value: dataField.value }])
              .filter(pv => pv.value !== null && pv.value !== undefined)
              .map((periodValue, idx) => {
                const year = periodValue.period || 'Value';
                const displayValue = periodValue.value;

                return (
                  <div key={idx} style={{ 
                    textAlign: 'center', 
                    padding: '6px', 
                    background: statusInfo.bg, 
                    borderRadius: '4px', 
                    border: `1px solid ${statusInfo.color}33` 
                  }}>
                    <small style={{ color: '#999', display: 'block', fontSize: config.periodFontSize }}>{year}</small>
                    <span style={{
                      color: typeof displayValue === 'number' && displayValue < 0 ? '#f44336' : statusInfo.color,
                      fontWeight: 600,
                      fontSize: config.valueFontSize
                    }}>
                      {formatValue(displayValue, dataField.unit)}
                    </span>
                  </div>
                );
              })}
          </div>

          {/* Metadata footer */}
          {showMetadata && (
            <div style={{ 
              marginTop: '8px', 
              paddingTop: '8px', 
              borderTop: `1px solid ${statusInfo.color}33`,
              fontSize: '10px',
              color: '#666',
              display: 'flex',
              flexWrap: 'wrap',
              gap: '8px'
            }}>
              {dataField.source && (
                <span title={dataField.source}>
                  📡 {dataField.source}
                </span>
              )}
              {dataField.confidence_score !== null && dataField.confidence_score !== undefined && (
                <span title={`Confidence: ${dataField.confidence_score}%`}>
                  🎯 {dataField.confidence_score}%
                </span>
              )}
              {dataField.formula && (
                <span title={`Formula: ${dataField.formula}`} style={{ fontStyle: 'italic' }}>
                  🧮 {dataField.formula}
                </span>
              )}
              {dataField.currency && (
                <span>
                  💱 {dataField.currency}
                </span>
              )}
              {!dataField.source && !dataField.confidence_score && !dataField.formula && !dataField.currency && (
                <span>No additional metadata</span>
              )}
            </div>
          )}
        </>
      )}

      {/* Missing data message */}
      {!hasData && (
        <div style={{ textAlign: 'center', color: '#ff9800', fontSize: config.fontSize, padding: '8px' }}>
          ⚠️ This data point is missing. It will need to be estimated or manually entered.
        </div>
      )}
    </div>
  );
};

/**
 * DataFieldGrid Component
 * 
 * Renders a grid of DataFieldDisplay components for a category of inputs.
 * 
 * @param {Array} fields - Array of field configurations: [{ key, label, dataField }]
 * @param {string} title - Category title
 * @param {string} size - Size variant for all fields
 */
export const DataFieldGrid = ({ fields, title, size = 'medium' }) => {
  return (
    <div style={{ marginBottom: '20px' }}>
      {title && (
        <h3 style={{ marginBottom: '16px', color: '#333' }}>{title}</h3>
      )}
      <div style={{ display: 'grid', gap: '12px' }}>
        {fields.map(field => (
          <DataFieldDisplay
            key={field.key}
            dataField={field.dataField}
            label={field.label}
            size={size}
          />
        ))}
      </div>
    </div>
  );
};

export default DataFieldDisplay;
