 * Data Utilities for Financial Valuation Platform
 *
 * Provides standardized utilities for:
 * - Currency conversion and formatting
 * - Unit conversion (millions, billions, etc.)
 * - Unified schema data transformation
 * - Value extraction from DataField wrappers
 *
 * Supports both International (USD) and Vietnamese (VND) markets
 */

// =============================================================================
// CURRENCY CONFIGURATION
// =============================================================================

export const CURRENCY_CONFIG = {
  international: {
    code: 'USD',
    symbol: '$',
    locale: 'en-US',
    defaultUnit: 'millions',
    exchangeRateToVND: 25000 // Approximate rate, can be updated dynamically
  },
  vietnam: {
    code: 'VND',
    symbol: '₫',
    locale: 'vi-VN',
    defaultUnit: 'millions',
    exchangeRateToUSD: 0.00004 // Approximate rate
  }
};

// =============================================================================
// DATAFIELD EXTRACTION UTILITIES
// =============================================================================

/**
 * Extract value from Unified Schema DataField wrapper
 * Handles both legacy format and new DataField format
 *
 * @param {Object|number|null} data - Can be DataField object, raw number, or null
 * @returns {number|null} - Extracted numeric value or null
 */
export const extractValue = (data) => {
  if (data === null || data === undefined) {
    return null;
  }

  // If it's already a number, return it
  if (typeof data === 'number') {
    return data;
  }

  // If it's a DataField wrapper (unified schema)
  if (typeof data === 'object' && data.value !== undefined) {
    return data.value;
  }

  // Legacy format: direct value
  return data;
};

/**
 * Extract value with metadata from DataField wrapper
 * Returns full DataField object for access to status, source, etc.
 *
 * @param {Object|number|null} data - DataField object or raw value
 * @returns {Object} - Object with value and metadata
 */
export const extractDataField = (data) => {
  if (data === null || data === undefined) {
    return {
      value: null,
      status: 'MISSING',
      source: null,
      currency: null,
      unit: null,
      isMissing: true
    };
  }

  // If it's a number, wrap it with default metadata
  if (typeof data === 'number') {
    return {
      value: data,
      status: 'RETRIEVED',
      source: 'unknown',
      currency: null,
      unit: null,
      isMissing: false
    };
  }

  // If it's already a DataField, return as-is with safe defaults
  if (typeof data === 'object') {
    return {
      value: data.value ?? null,
      status: data.status ?? 'RETRIEVED',
      source: data.source ?? null,
      currency: data.currency ?? null,
      unit: data.unit ?? null,
      confidence_score: data.confidence_score ?? null,
      formula: data.formula ?? null,
      isMissing: data.is_missing ?? (data.value === null)
    };
  }

  return {
    value: null,
    status: 'MISSING',
    source: null,
    currency: null,
    unit: null,
    isMissing: true
  };
};

/**
 * Extract time-series data from various formats
 * Handles: DataField[], raw objects {year: value}, arrays of values
 *
 * @param {Array|Object} data - Time-series data in various formats
 * @returns {Object} - Normalized object with years as keys
 */
export const extractTimeSeries = (data) => {
  if (!data) return {};

  // If it's an array of DataField objects
  if (Array.isArray(data)) {
    const result = {};
    data.forEach(item => {
      const field = extractDataField(item);
      if (item.reporting_period) {
        result[item.reporting_period] = field.value;
      } else if (item.year) {
        result[item.year] = field.value;
      }
    });
    return result;
  }

  // If it's already an object with period keys
  if (typeof data === 'object') {
    return data;
  }

  return {};
};

// =============================================================================
// CURRENCY FORMATTING UTILITIES
// =============================================================================

/**
 * Format currency value with appropriate scale (K, M, B, T)
 * Automatically detects magnitude and applies suitable abbreviation
 *
 * @param {number|null} value - Numeric value to format
 * @param {string} currency - Currency code ('USD' or 'VND')
 * @param {string} targetUnit - Target unit ('actual', 'thousands', 'millions', 'billions', 'trillions')
 * @returns {string} - Formatted currency string
 */
export const formatCurrency = (value, currency = 'USD', targetUnit = 'auto') => {
  const numValue = extractValue(value);

  if (numValue === null || numValue === undefined) {
    return 'N/A';
  }

  const config = currency === 'VND' ? CURRENCY_CONFIG.vietnam : CURRENCY_CONFIG.international;
  const symbol = config.symbol;

  // Auto-detect appropriate unit based on magnitude
  let divisor = 1;
  let unitLabel = '';

  if (targetUnit === 'auto') {
    const absValue = Math.abs(numValue);
    if (absValue >= 1e12) {
      divisor = 1e12;
      unitLabel = 'T';
    } else if (absValue >= 1e9) {
      divisor = 1e9;
      unitLabel = 'B';
    } else if (absValue >= 1e6) {
      divisor = 1e6;
      unitLabel = 'M';
    } else if (absValue >= 1e3) {
      divisor = 1e3;
      unitLabel = 'K';
    }
  } else {
    switch (targetUnit) {
      case 'thousands':
        divisor = 1e3;
        unitLabel = 'K';
        break;
      case 'millions':
        divisor = 1e6;
        unitLabel = 'M';
        break;
      case 'billions':
        divisor = 1e9;
        unitLabel = 'B';
        break;
      case 'trillions':
        divisor = 1e12;
        unitLabel = 'T';
        break;
      default:
        divisor = 1;
        unitLabel = '';
    }
  }

  const scaledValue = numValue / divisor;
  const formatted = scaledValue.toLocaleString(config.locale, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  });

  return `${symbol}${formatted}${unitLabel ? unitLabel : ''}`;
};

/**
 * Format percentage value
 *
 * @param {number|null} value - Numeric value (as decimal or percentage)
 * @param {boolean} isDecimal - Whether input is in decimal form (0.15 vs 15)
 * @param {number} decimals - Number of decimal places
 * @returns {string} - Formatted percentage string
 */
export const formatPercent = (value, isDecimal = false, decimals = 2) => {
  const numValue = extractValue(value);

  if (numValue === null || numValue === undefined) {
    return 'N/A';
  }

  let percentValue = numValue;
  if (isDecimal && Math.abs(numValue) <= 1) {
    percentValue = numValue * 100;
  }

  return `${percentValue.toFixed(decimals)}%`;
};

/**
 * Format plain number with locale-specific separators
 *
 * @param {number|null} value - Numeric value
 * @param {string} locale - Locale code ('en-US' or 'vi-VN')
 * @param {number} decimals - Number of decimal places
 * @returns {string} - Formatted number string
 */
export const formatNumber = (value, locale = 'en-US', decimals = 2) => {
  const numValue = extractValue(value);

  if (numValue === null || numValue === undefined) {
    return 'N/A';
  }

  return numValue.toLocaleString(locale, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals
  });
};

// =============================================================================
// UNIT CONVERSION UTILITIES
// =============================================================================

/**
 * Convert value between different units (thousands, millions, billions)
 *
 * @param {number} value - Numeric value
 * @param {string} fromUnit - Source unit ('actual', 'thousands', 'millions', 'billions')
 * @param {string} toUnit - Target unit
 * @returns {number} - Converted value
 */
export const convertUnit = (value, fromUnit = 'actual', toUnit = 'actual') => {
  const unitMultipliers = {
    actual: 1,
    thousands: 1e3,
    millions: 1e6,
    billions: 1e9,
    trillions: 1e12
  };

  const fromMultiplier = unitMultipliers[fromUnit] || 1;
  const toMultiplier = unitMultipliers[toUnit] || 1;

  return (value * fromMultiplier) / toMultiplier;
};

/**
 * Convert currency between USD and VND
 *
 * @param {number} value - Numeric value
 * @param {string} fromCurrency - Source currency ('USD' or 'VND')
 * @param {string} toCurrency - Target currency
 * @param {number|null} customRate - Optional custom exchange rate
 * @returns {number} - Converted value
 */
export const convertCurrency = (value, fromCurrency = 'USD', toCurrency = 'VND', customRate = null) => {
  const numValue = extractValue(value);

  if (numValue === null || numValue === undefined) {
    return null;
  }

  if (fromCurrency === toCurrency) {
    return numValue;
  }

  const rate = customRate ?? CURRENCY_CONFIG.international.exchangeRateToVND;

  if (fromCurrency === 'USD' && toCurrency === 'VND') {
    return numValue * rate;
  } else if (fromCurrency === 'VND' && toCurrency === 'USD') {
    return numValue / rate;
  }

  return numValue;
};

/**
 * Detect appropriate display unit based on value magnitude and market
 *
 * @param {number} value - Numeric value
 * @param {string} market - Market type ('international' or 'vietnam')
 * @returns {string} - Recommended unit ('millions', 'billions', etc.)
 */
export const getRecommendedUnit = (value, market = 'international') => {
  const numValue = extractValue(value);

  if (numValue === null || numValue === undefined) {
    return 'millions';
  }

  const absValue = Math.abs(numValue);

  // Vietnamese values are typically larger due to VND denomination
  if (market === 'vietnam') {
    if (absValue >= 1e13) return 'trillions';
    if (absValue >= 1e10) return 'billions';
    if (absValue >= 1e7) return 'millions';
    return 'millions'; // Default to millions for VND
  } else {
    // International (USD)
    if (absValue >= 1e12) return 'trillions';
    if (absValue >= 1e9) return 'billions';
    if (absValue >= 1e6) return 'millions';
    if (absValue >= 1e3) return 'thousands';
    return 'actual';
  }
};

// =============================================================================
// UNIFIED SCHEMA TRANSFORMATION UTILITIES
// =============================================================================

/**
 * Transform legacy API response to unified schema format
 * Handles backward compatibility during migration
 *
 * @param {Object} legacyData - Legacy format data
 * @param {string} dataType - Type of data ('historical_financials', 'forecast_drivers', etc.)
 * @returns {Object} - Transformed unified schema data
 */
export const transformLegacyToUnified = (legacyData, dataType) => {
  if (!legacyData) return null;

  // If already in unified format (has DataField structure), return as-is
  if (legacyData.value !== undefined || legacyData.status !== undefined) {
    return legacyData;
  }

  // Transform based on data type
  switch (dataType) {
    case 'historical_financials':
      return transformHistoricalFinancials(legacyData);
    case 'forecast_drivers':
      return transformForecastDrivers(legacyData);
    case 'market_data':
      return transformMarketData(legacyData);
    default:
      return legacyData;
  }
};

/**
 * Transform historical financials from legacy to unified format
 */
const transformHistoricalFinancials = (legacyData) => {
  const transformed = {};

  // Map common fields
  const fieldMappings = {
    revenue: ['revenue', 'total_revenue', 'Total Revenue'],
    cogs: ['cogs', 'cost_of_revenue', 'COGS'],
    ebitda: ['ebitda', 'EBITDA'],
    net_income: ['net_income', 'netIncome', 'Net Income'],
    operating_expenses: ['operating_expenses', 'opex', 'Operating Expenses'],
    depreciation: ['depreciation', 'depreciation_and_amortization'],
    capex: ['capex', 'capital_expenditures', 'CapEx'],
    free_cash_flow: ['free_cash_flow', 'fcf', 'FCF'],
    total_assets: ['total_assets', 'Total Assets'],
    total_debt: ['total_debt', 'long_term_debt'],
    cash_and_equivalents: ['cash', 'cash_and_equivalents'],
    shareholders_equity: ['equity', 'shareholders_equity', 'Stockholders Equity']
  };

  Object.entries(fieldMappings).forEach(([unifiedKey, legacyKeys]) => {
    for (const legacyKey of legacyKeys) {
      if (legacyData[legacyKey] !== undefined) {
        transformed[unifiedKey] = {
          value: legacyData[legacyKey],
          status: 'RETRIEVED',
          source: 'legacy_api'
        };
        break;
      }
    }
  });

  return transformed;
};

/**
 * Transform forecast drivers from legacy to unified format
 */
const transformForecastDrivers = (legacyData) => {
  const transformed = {};

  const fieldMappings = {
    revenue_growth_forecast: ['revenue_growth', 'revenue_growth_rate'],
    ebitda_margin_forecast: ['ebitda_margin', 'target_ebitda_margin'],
    tax_rate: ['tax_rate', 'effective_tax_rate'],
    wacc: ['wacc', 'discount_rate'],
    terminal_growth_rate: ['terminal_growth', 'perpetual_growth_rate'],
    beta: ['beta', 'levered_beta'],
    risk_free_rate: ['risk_free_rate', 'rf_rate']
  };

  Object.entries(fieldMappings).forEach(([unifiedKey, legacyKeys]) => {
    for (const legacyKey of legacyKeys) {
      if (legacyData[legacyKey] !== undefined) {
        transformed[unifiedKey] = {
          value: legacyData[legacyKey],
          status: 'RETRIEVED',
          source: 'legacy_api'
        };
        break;
      }
    }
  });

  return transformed;
};

/**
 * Transform market data from legacy to unified format
 */
const transformMarketData = (legacyData) => {
  const transformed = {};

  const fieldMappings = {
    current_stock_price: ['current_price', 'price', 'stock_price'],
    market_cap: ['market_cap', 'marketCap'],
    beta: ['beta'],
    shares_outstanding: ['shares_outstanding', 'sharesOutstanding'],
    total_debt: ['total_debt', 'debt'],
    cash: ['cash', 'cash_and_equivalents']
  };

  Object.entries(fieldMappings).forEach(([unifiedKey, legacyKeys]) => {
    for (const legacyKey of legacyKeys) {
      if (legacyData[legacyKey] !== undefined) {
        transformed[unifiedKey] = {
          value: legacyData[legacyKey],
          status: 'RETRIEVED',
          source: 'legacy_api',
          currency: 'USD'
        };
        break;
      }
    }
  });

  return transformed;
};

// =============================================================================
// DATA QUALITY UTILITIES
// =============================================================================

/**
 * Calculate data completeness score
 *
 * @param {Object} dataObject - Object containing data fields
 * @returns {Object} - Completeness metrics
 */
export const calculateDataCompleteness = (dataObject) => {
  if (!dataObject || typeof dataObject !== 'object') {
    return {
      totalFields: 0,
      filledFields: 0,
      missingFields: 0,
      completenessScore: 0
    };
  }

  const entries = Object.entries(dataObject);
  const totalFields = entries.length;

  const filledFields = entries.filter(([_, value]) => {
    const extracted = extractValue(value);
    return extracted !== null && extracted !== undefined;
  }).length;

  const missingFields = totalFields - filledFields;
  const completenessScore = totalFields > 0 ? (filledFields / totalFields) * 100 : 0;

  return {
    totalFields,
    filledFields,
    missingFields,
    completenessScore: Math.round(completenessScore * 100) / 100
  };
};

/**
 * Get data status summary
 *
 * @param {Object} dataObject - Object containing DataField wrappers
 * @returns {Object} - Status breakdown
 */
export const getDataStatusSummary = (dataObject) => {
  if (!dataObject || typeof dataObject !== 'object') {
    return {
      retrieved: 0,
      calculated: 0,
      estimated: 0,
      missing: 0,
      manual_override: 0
    };
  }

  const summary = {
    retrieved: 0,
    calculated: 0,
    estimated: 0,
    missing: 0,
    manual_override: 0
  };

  Object.values(dataObject).forEach(field => {
    const dataField = extractDataField(field);
    const status = dataField.status?.toLowerCase() || 'missing';

    if (summary[status] !== undefined) {
      summary[status]++;
    } else if (dataField.isMissing) {
      summary.missing++;
    }
  });

  return summary;
};

// =============================================================================
// EXPORT ALL UTILITIES
// =============================================================================

export default {
  // Configuration
  CURRENCY_CONFIG,

  // DataField extraction
  extractValue,
  extractDataField,
  extractTimeSeries,

  // Formatting
  formatCurrency,
  formatPercent,
  formatNumber,

  // Conversion
  convertUnit,
  convertCurrency,
  getRecommendedUnit,

  // Transformation
  transformLegacyToUnified,

  // Data quality
  calculateDataCompleteness,
  getDataStatusSummary
};
