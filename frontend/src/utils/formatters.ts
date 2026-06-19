/**
 * Locale-Aware Financial Number Formatting Engine
 * 
 * Uses native Intl.NumberFormat — no heavy third-party dependencies.
 * All raw API numbers MUST pass through this engine before display.
 * 
 * Rounding Policies:
 * - Share Prices / Per-Share: exactly 2 decimal places
 * - Growth Rates / WACC / Multiples: exactly 1 decimal place
 * - Percentages: exactly 1 decimal place
 */

// ======================== TYPES ========================

type Currency = 'USD' | 'VND' | 'EUR';

interface CurrencyFormatOptions {
  currency?: Currency;
  compact?: boolean;
  decimals?: number;
  locale?: string;
}

interface PercentFormatOptions {
  decimals?: number;
  showSign?: boolean;
}

// ======================== CURRENCY FORMATTING ========================

/**
 * Format a number as currency with locale-aware separators.
 * 
 * International (en-US): $1.2B, $45.6M, $320K
 * Vietnam (vi-VN): 1.200 tỷ ₫, 45,6 tr ₫
 * 
 * @example
 * formatCurrency(1450000000) // "$1.45B"
 * formatCurrency(1450000000, { compact: true, currency: 'VND' }) // "1.450 tỷ ₫"
 * formatCurrency(154.23) // "$154.23"
 */
export function formatCurrency(
  value: number | null | undefined,
  options: CurrencyFormatOptions = {}
): string {
  if (value === null || value === undefined || isNaN(value)) {
    return '—';
  }

  const {
    currency = 'USD',
    compact = false,
    decimals,
    locale,
  } = options;

  const resolvedLocale = locale || (currency === 'VND' ? 'vi-VN' : 'en-US');

  // Default decimals: 2 for prices, 1 for large compact values
  const resolvedDecimals = decimals ?? (compact ? 1 : 2);

  try {
    const formatter = new Intl.NumberFormat(resolvedLocale, {
      style: 'currency',
      currency,
      notation: compact ? 'compact' : 'standard',
      compactDisplay: 'short',
      minimumFractionDigits: resolvedDecimals,
      maximumFractionDigits: resolvedDecimals,
    });

    return formatter.format(value);
  } catch {
    // Fallback if Intl fails
    return `${currency} ${value.toLocaleString()}`;
  }
}

// ======================== PERCENTAGE FORMATTING ========================

/**
 * Format a decimal value as a percentage with exactly 1 decimal place.
 * 
 * @example
 * formatPercent(0.125) // "12.5%"
 * formatPercent(0.084, { showSign: true }) // "+8.4%"
 * formatPercent(-0.032) // "-3.2%"
 */
export function formatPercent(
  value: number | null | undefined,
  options: PercentFormatOptions = {}
): string {
  if (value === null || value === undefined || isNaN(value)) {
    return '—';
  }

  const { decimals = 1, showSign = false } = options;

  // Convert from decimal (0.125) to percentage (12.5)
  const percentValue = value * 100;
  const sign = showSign && percentValue > 0 ? '+' : '';

  return `${sign}${percentValue.toFixed(decimals)}%`;
}

// ======================== MULTIPLE FORMATTING ========================

/**
 * Format a valuation multiple with 'x' suffix.
 * Always 1 decimal place.
 * 
 * @example
 * formatMultiple(11.23) // "11.2x"
 * formatMultiple(0.85) // "0.9x"
 */
export function formatMultiple(
  value: number | null | undefined
): string {
  if (value === null || value === undefined || isNaN(value)) {
    return '—';
  }

  return `${value.toFixed(1)}x`;
}

// ======================== COMPACT / SHORT-HAND FORMATTING ========================

/**
 * Format large numbers with compact notation.
 * 
 * International: $1.45B, $240.2M, $320K
 * Vietnam: 1.450 tỷ, 240,2 tr
 * 
 * @example
 * formatCompact(1450000000) // "$1.45B"
 * formatCompact(240200000) // "$240.2M"
 * formatCompact(320000) // "$320K"
 * formatCompact(1450000000, 'vi-VN') // "1,45 مليار"
 */
export function formatCompact(
  value: number | null | undefined,
  locale: string = 'en-US'
): string {
  if (value === null || value === undefined || isNaN(value)) {
    return '—';
  }

  try {
    const formatter = new Intl.NumberFormat(locale, {
      notation: 'compact',
      compactDisplay: 'short',
      maximumFractionDigits: 1,
    });

    return formatter.format(value);
  } catch {
    // Fallback
    if (Math.abs(value) >= 1e9) return `${(value / 1e9).toFixed(1)}B`;
    if (Math.abs(value) >= 1e6) return `${(value / 1e6).toFixed(1)}M`;
    if (Math.abs(value) >= 1e3) return `${(value / 1e3).toFixed(1)}K`;
    return value.toString();
  }
}

// ======================== SHARE PRICE FORMATTING ========================

/**
 * Format share price with exactly 2 decimal places.
 * 
 * @example
 * formatSharePrice(154.23) // "$154.23"
 * formatSharePrice(32500, 'VND') // "32,500.00 ₫"
 */
export function formatSharePrice(
  value: number | null | undefined,
  currency: Currency = 'USD'
): string {
  if (value === null || value === undefined || isNaN(value)) {
    return '—';
  }

  return formatCurrency(value, {
    currency,
    compact: false,
    decimals: 2,
  });
}

// ======================== RAW NUMBER FORMATTING ========================

/**
 * Format a raw number with locale-aware thousands separators.
 * No currency symbol.
 * 
 * @example
 * formatNumber(1234567.89) // "1,234,567.89"
 * formatNumber(1234567.89, 'vi-VN') // "1.234.567,89"
 */
export function formatNumber(
  value: number | null | undefined,
  locale: string = 'en-US',
  decimals: number = 2
): string {
  if (value === null || value === undefined || isNaN(value)) {
    return '—';
  }

  try {
    return new Intl.NumberFormat(locale, {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    }).format(value);
  } catch {
    return value.toLocaleString();
  }
}

// ======================== BILLIONS / TRILLIONS ABBREVIATION ========================

/**
 * Format large numbers as abbreviated scale labels for charts.
 * 
 * @example
 * formatScaleLabel(1500000000) // "$1.5B"
 * formatScaleLabel(240000000) // "$240M"
 */
export function formatScaleLabel(
  value: number,
  currency: Currency = 'USD'
): string {
  const symbol = currency === 'USD' ? '$' : currency === 'VND' ? '' : '€';
  const suffix = currency === 'VND' ? ' ₫' : '';

  if (Math.abs(value) >= 1e12) {
    return `${symbol}${(value / 1e12).toFixed(1)}T${suffix}`;
  }
  if (Math.abs(value) >= 1e9) {
    return `${symbol}${(value / 1e9).toFixed(1)}B${suffix}`;
  }
  if (Math.abs(value) >= 1e6) {
    return `${symbol}${(value / 1e6).toFixed(0)}M${suffix}`;
  }
  if (Math.abs(value) >= 1e3) {
    return `${symbol}${(value / 1e3).toFixed(0)}K${suffix}`;
  }
  return `${symbol}${value}${suffix}`;
}

// ======================== DEFAULT EXPORT ========================

const formatters = {
  formatCurrency,
  formatPercent,
  formatMultiple,
  formatCompact,
  formatSharePrice,
  formatNumber,
  formatScaleLabel,
};

export default formatters;
