import React from 'react';

/**
 * DynamicFormGenerator Component
 *
 * Generates form inputs dynamically based on schema metadata.
 * Supports various input types: text, number, currency, percent, date, select.
 * Automatically handles validation, formatting, and market-specific units.
 *
 * @param {Object} schema - Schema definition with field configurations
 * @param {Object} values - Current form values
 * @param {Function} onChange - Change handler function
 * @param {string} market - Market type for currency/unit handling
 * @param {boolean} readOnly - Whether fields should be read-only
 */
const DynamicFormGenerator = ({
  schema,
  values = {},
  onChange,
  market = 'international',
  readOnly = false
}) => {
  if (!schema || !schema.fields) {
    return null;
  }

  const currency = market === 'vietnamese' ? 'VND' : 'USD';

  // Render individual field based on type
  const renderField = (fieldConfig) => {
    const {
      key,
      label,
      type = 'text',
      required = false,
      placeholder,
      helpText,
      validation,
      options,
      min,
      max,
      step,
      prefix,
      suffix,
      disabled = false
    } = fieldConfig;

    const value = values[key] ?? '';
    const isInvalid = validation && !validateField(value, validation);

    const baseInputStyles = {
      width: '100%',
      padding: '10px 12px',
      border: `1px solid ${isInvalid ? '#f44336' : '#e0e0e0'}`,
      borderRadius: '6px',
      fontSize: '14px',
      transition: 'border-color 0.2s',
      background: disabled ? '#f5f5f5' : 'white',
      cursor: disabled ? 'not-allowed' : 'text'
    };

    const renderInput = () => {
      switch (type) {
        case 'select':
          return (
            <select
              value={value}
              onChange={(e) => onChange(key, e.target.value)}
              disabled={disabled || readOnly}
              style={baseInputStyles}
            >
              <option value="">Select...</option>
              {options?.map((opt, idx) => (
                <option key={idx} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          );

        case 'textarea':
          return (
            <textarea
              value={value}
              onChange={(e) => onChange(key, e.target.value)}
              disabled={disabled || readOnly}
              placeholder={placeholder}
              rows={fieldConfig.rows || 3}
              style={{
                ...baseInputStyles,
                resize: 'vertical',
                fontFamily: 'inherit'
              }}
            />
          );

        case 'number':
        case 'currency':
        case 'percent':
          return (
            <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
              {prefix && (
                <span style={{
                  padding: '10px 8px',
                  background: '#f5f5f5',
                  border: `1px solid ${isInvalid ? '#f44336' : '#e0e0e0'}`,
                  borderRight: 'none',
                  borderRadius: '6px 0 0 6px',
                  color: '#616161',
                  fontWeight: 500
                }}>
                  {prefix}
                </span>
              )}
              <input
                type="number"
                value={value}
                onChange={(e) => onChange(key, e.target.value)}
                disabled={disabled || readOnly}
                placeholder={placeholder}
                min={min}
                max={max}
                step={step || 'any'}
                style={{
                  ...baseInputStyles,
                  borderRadius: prefix ? '0 6px 6px 0' : '6px'
                }}
              />
              {suffix && (
                <span style={{
                  padding: '10px 8px',
                  background: '#f5f5f5',
                  border: `1px solid ${isInvalid ? '#f44336' : '#e0e0e0'}`,
                  borderLeft: 'none',
                  borderRadius: '0 6px 6px 0',
                  color: '#616161',
                  fontWeight: 500,
                  marginLeft: '-1px'
                }}>
                  {suffix}
                </span>
              )}
            </div>
          );

        case 'date':
          return (
            <input
              type="date"
              value={value}
              onChange={(e) => onChange(key, e.target.value)}
              disabled={disabled || readOnly}
              style={baseInputStyles}
            />
          );

        case 'checkbox':
          return (
            <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={!!value}
                onChange={(e) => onChange(key, e.target.checked)}
                disabled={disabled || readOnly}
                style={{ width: '18px', height: '18px', cursor: 'pointer' }}
              />
              <span style={{ fontSize: '14px', color: '#424242' }}>{label}</span>
            </label>
          );

        case 'text':
        default:
          return (
            <input
              type="text"
              value={value}
              onChange={(e) => onChange(key, e.target.value)}
              disabled={disabled || readOnly}
              placeholder={placeholder}
              style={baseInputStyles}
            />
          );
      }
    };

    // Checkbox doesn't need wrapper
    if (type === 'checkbox') {
      return renderInput();
    }

    return (
      <div key={key} style={{ marginBottom: '16px' }}>
        <label style={{
          display: 'block',
          marginBottom: '6px',
          fontWeight: 500,
          color: '#424242',
          fontSize: '13px'
        }}>
          {label}
          {required && <span style={{ color: '#f44336', marginLeft: '4px' }}>*</span>}
        </label>

        {renderInput()}

        {helpText && (
          <p style={{
            marginTop: '4px',
            fontSize: '11px',
            color: '#757575',
            margin: '4px 0 0 0'
          }}>
            {helpText}
          </p>
        )}

        {isInvalid && validation.message && (
          <p style={{
            marginTop: '4px',
            fontSize: '11px',
            color: '#f44336',
            margin: '4px 0 0 0'
          }}>
            ⚠️ {validation.message}
          </p>
        )}
      </div>
    );
  };

  // Simple validation helper
  const validateField = (value, validation) => {
    if (!validation) return true;

    const { required, pattern, min, max } = validation;

    if (required && (value === '' || value === null || value === undefined)) {
      return false;
    }

    if (pattern && !new RegExp(pattern).test(value)) {
      return false;
    }

    if (min !== undefined && parseFloat(value) < min) {
      return false;
    }

    if (max !== undefined && parseFloat(value) > max) {
      return false;
    }

    return true;
  };

  // Group fields by section if available
  const renderFields = () => {
    if (schema.sections) {
      return schema.sections.map((section, idx) => (
        <div key={idx} style={{
          marginBottom: '24px',
          padding: '16px',
          background: '#fafafa',
          borderRadius: '8px',
          border: '1px solid #e0e0e0'
        }}>
          <h4 style={{
            margin: '0 0 16px 0',
            fontSize: '15px',
            fontWeight: 600,
            color: '#1976d2',
            borderBottom: '2px solid #1976d2',
            paddingBottom: '8px'
          }}>
            {section.title}
          </h4>

          <div style={{
            display: 'grid',
            gridTemplateColumns: section.layout === 'horizontal' ? 'repeat(auto-fit, minmax(250px, 1fr))' : '1fr',
            gap: '16px'
          }}>
            {section.fields.map(fieldKey => {
              const fieldConfig = schema.fields.find(f => f.key === fieldKey);
              return fieldConfig ? renderField(fieldConfig) : null;
            })}
          </div>
        </div>
      ));
    }

    // Flat structure without sections
    return (
      <div style={{
        display: 'grid',
        gridTemplateColumns: schema.layout === 'horizontal' ? 'repeat(auto-fit, minmax(250px, 1fr))' : '1fr',
        gap: '16px'
      }}>
        {schema.fields.map(fieldConfig => renderField(fieldConfig))}
      </div>
    );
  };

  return (
    <div className="dynamic-form-generator">
      {schema.title && (
        <h3 style={{
          fontSize: '18px',
          fontWeight: 700,
          color: '#1a237e',
          marginBottom: '20px'
        }}>
          {schema.title}
        </h3>
      )}

      {schema.description && (
        <p style={{
          fontSize: '13px',
          color: '#616161',
          marginBottom: '20px',
          lineHeight: '1.5'
        }}>
          {schema.description}
        </p>
      )}

      {renderFields()}
    </div>
  );
};

export default DynamicFormGenerator;