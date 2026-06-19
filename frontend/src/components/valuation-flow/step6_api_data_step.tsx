import React from 'react';
import { useTranslation } from 'react-i18next';
import DataFieldDisplay, { DataFieldGrid } from './DataFieldDisplay';

interface ApiDataStepProps {
  [key: string]: any;
}

/**
 * ApiDataStep Component
 * Step 6: Fetch API Data - Display all retrieved data + calculated inputs + identify missing inputs
 *
 * Features:
 * - Display historical financials retrieved from API with detailed numbers
 * - Show forecast drivers from API with period-by-period values
 * - Display peer comparison data with individual company metrics
 * - Show DCF inputs (WACC, terminal growth) from API
 * - Display DuPont analysis results with detailed ratios
 * - Show Comps analysis results with all multiples
 * - Navigate to Step 7 (Process Historical Data) or back to Step 5 (Prepare Inputs)
 */
const ApiDataStep: React.FC<ApiDataStepProps> = ({
  historicalData,
  forecastDrivers,
  peerData,
  dcfInputs,
  dupontResults,
  compsResults,
  calculatedMetrics,
  onBackToRequirements,
  onContinueToAiAssumptions,
  loading,
  sessionId,
  market = 'international',
  selectedModel
}) => {
  const { t } = useTranslation();
  // Check if data has been retrieved - improved check to include peerData with companies
  // FIXED: Check for historical_financials object directly, not nested inside historicalData
  const hasRetrievedData = (historicalData && historicalData.historical_financials) ||
                           (peerData && peerData.companies && peerData.companies.length > 0) ||
                           dcfInputs ||
                           dupontResults ||
                           compsResults ||
                           calculatedMetrics;

  // API key management is now handled by the floating 🔍 API Keys button

  // API key management is now handled by the floating 🔍 API Keys button

  // ─── DYNAMIC FIELD RENDERING ──────────────────────────────────────────────
  // Instead of a hardcoded list, we render fields dynamically from the backend response.
  // The backend returns historical_financials, market_data, forecast_drivers, etc.
  // as objects with named keys. Each value is a DataField { value, status, source, ... }.
  // This means any new field added to the backend automatically appears in the UI.
  
  // Category display config
  const CATEGORY_CONFIG: Record<string, { label: string; gradient: string; icon: string }> = {
    historical_financials: { label: 'Historical Financials', gradient: 'linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%)', icon: '📊' },
    market_data: { label: 'Market Data', gradient: 'linear-gradient(135deg, #fff3e0 0%, var(--color-neutral-bg) 100%)', icon: '📈' },
    forecast_drivers: { label: 'Forecast Drivers', gradient: 'linear-gradient(135deg, #ede7f6 0%, #d1c4e9 100%)', icon: '🔮' },
    balance_sheet_opening: { label: 'Balance Sheet', gradient: 'linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%)', icon: '📋' },
    peer_comparables: { label: 'Peer Comparables (WACC)', gradient: 'linear-gradient(135deg, #fce4ec 0%, #f8bbd0 100%)', icon: '🏢' },
  };
  
  // Friendly names for field_name → display name mapping
  const FIELD_LABELS: Record<string, string> = {
    revenue: 'Total Revenue', cogs: 'Cost of Revenue (COGS)', gross_profit: 'Gross Profit',
    operating_expenses: 'Operating Expenses', research_development: 'Research & Development',
    sg_and_a: 'SG&A Expenses', ebitda: 'EBITDA', ebit: 'EBIT / Operating Income',
    interest_expense: 'Interest Expense', other_income: 'Other Income/Expense',
    pretax_income: 'Pre-Tax Income', tax_provision: 'Tax Provision',
    net_income: 'Net Income', depreciation_amortization: 'Depreciation & Amortization',
    deferred_tax: 'Deferred Tax',
    capex: 'Capital Expenditures (CapEx)', operating_cash_flow: 'Operating Cash Flow',
    free_cash_flow: 'Free Cash Flow', working_capital_changes: 'Working Capital Changes',
    interest_paid: 'Interest Paid (Cash)', tax_paid: 'Income Tax Paid (Cash)',
    share_buybacks: 'Share Buybacks', debt_repayments: 'Debt Repayments',
    debt_issuance: 'Debt Issuance', dividends_paid: 'Dividends Paid',
    accounts_receivable: 'Accounts Receivable', inventory: 'Inventory',
    accounts_payable: 'Accounts Payable', cash_and_equivalents: 'Cash & Equivalents',
    total_assets: 'Total Assets', total_debt: 'Total Debt',
    long_term_debt: 'Long-Term Debt', current_debt: 'Current Debt',
    shareholders_equity: 'Shareholders Equity', retained_earnings: 'Retained Earnings',
    shares_outstanding: 'Shares Outstanding', interest_income: 'Interest Income',
    working_capital: 'Working Capital (Direct)',
    net_ppe: 'PP&E (Net)', net_debt: 'Net Debt',
    total_current_assets: 'Total Current Assets', total_current_liabilities: 'Total Current Liabilities',
    total_liabilities: 'Total Liabilities',
    non_current_marketable_securities: 'Non-Current Marketable Securities',
    other_current_liabilities: 'Other Current Liabilities',
    deferred_tax_liabilities: 'Deferred Tax Liabilities',
    current_accrued_expenses: 'Current Accrued Expenses',
    current_deferred_liabilities: 'Current Deferred Liabilities',
    trade_and_other_payables_non_current: 'Trade and Other Payables Non Current',
    other_non_current_liabilities: 'Other Non Current Liabilities',
    other_short_term_investments: 'Other Short Term Investments',
    other_current_assets: 'Other Current Assets',
    other_non_current_assets: 'Other Non Current Assets',
    common_stock: 'Common Stock',
    other_equity_adjustments: 'Other Equity Adjustments',
    current_stock_price: 'Current Stock Price', market_cap: 'Market Cap', beta: 'Beta',
    risk_free_rate: 'Risk-Free Rate', equity_risk_premium: 'Equity Risk Premium',
    net_debt_opening: 'Net Debt', ppe_gross: 'PP&E (Gross)',
    accumulated_depreciation: 'Accumulated Depreciation',
    deferred_tax_assets: 'Deferred Tax Assets',
    deferred_tax_liabilities_opening: 'Deferred Tax Liabilities',
    non_current_marketable_securities_opening: 'Non-Current Marketable Securities',
    other_current_liabilities_opening: 'Other Current Liabilities',
  };
  
  // Extract all fields from the backend response, grouped by category
  const extractAllFields = (): Record<string, Array<{ key: string; label: string; dataField: any }>> => {
    const grouped: Record<string, Array<{ key: string; label: string; dataField: any }>> = {};
    
    // 1. Historical Financials (from historicalData.historical_financials)
    const histFin = historicalData?.historical_financials;
    if (histFin) {
      const fields: Array<{ key: string; label: string; dataField: any }> = [];
      // If data_fields array exists (from DCF processor), use it directly
      if (Array.isArray(histFin.data_fields)) {
        for (const df of histFin.data_fields) {
          if (df.field_name && df.value !== undefined) {
            fields.push({ key: df.field_name, label: df.display_name || FIELD_LABELS[df.field_name] || df.field_name, dataField: df });
          }
        }
      } else {
        // Fallback: iterate over named keys (revenue, cogs, etc.)
        for (const [key, val] of Object.entries(histFin)) {
          if (key === 'years' || key === 'data_fields') continue;
          if (val && typeof val === 'object' && 'value' in (val as any)) {
            fields.push({ key, label: FIELD_LABELS[key] || key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()), dataField: val });
          }
        }
      }
      if (fields.length > 0) grouped['historical_financials'] = fields;
    }
    
    // 2. Market Data (from historicalData.market_data)
    const mktData = historicalData?.market_data;
    if (mktData) {
      const fields: Array<{ key: string; label: string; dataField: any }> = [];
      if (Array.isArray(mktData.data_fields)) {
        for (const df of mktData.data_fields) {
          if (df.field_name && df.value !== undefined) {
            fields.push({ key: df.field_name, label: df.display_name || FIELD_LABELS[df.field_name] || df.field_name, dataField: df });
          }
        }
      } else {
        for (const [key, val] of Object.entries(mktData)) {
          if (key === 'data_fields') continue;
          if (val && typeof val === 'object' && 'value' in (val as any)) {
            fields.push({ key, label: FIELD_LABELS[key] || key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()), dataField: val });
          }
        }
      }
      if (fields.length > 0) grouped['market_data'] = fields;
    }
    
    // 3. Forecast Drivers (from historicalData.forecast_drivers)
    const fcDrivers = historicalData?.forecast_drivers;
    if (fcDrivers) {
      const fields: Array<{ key: string; label: string; dataField: any }> = [];
      if (Array.isArray(fcDrivers.data_fields)) {
        for (const df of fcDrivers.data_fields) {
          if (df.field_name && df.value !== undefined) {
            fields.push({ key: df.field_name, label: df.display_name || FIELD_LABELS[df.field_name] || df.field_name, dataField: df });
          }
        }
      } else {
        for (const [key, val] of Object.entries(fcDrivers)) {
          if (key === 'data_fields') continue;
          if (val && typeof val === 'object' && 'value' in (val as any)) {
            fields.push({ key, label: FIELD_LABELS[key] || key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()), dataField: val });
          }
        }
      }
      if (fields.length > 0) grouped['forecast_drivers'] = fields;
    }
    
    // 4. Balance Sheet Opening (from historicalData.balance_sheet_opening)
    const bsOpening = historicalData?.balance_sheet_opening;
    if (bsOpening) {
      const fields: Array<{ key: string; label: string; dataField: any }> = [];
      for (const [key, val] of Object.entries(bsOpening)) {
        if (key === 'data_fields') continue;
        if (val && typeof val === 'object' && 'value' in (val as any)) {
          fields.push({ key, label: FIELD_LABELS[key] || key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()), dataField: val });
        }
      }
      if (fields.length > 0) grouped['balance_sheet_opening'] = fields;
    }
    
    // 5. Peer Comparables (from historicalData.peer_comparables)
    const peerComp = historicalData?.peer_comparables;
    if (peerComp) {
      const fields: Array<{ key: string; label: string; dataField: any }> = [];
      for (const [key, val] of Object.entries(peerComp)) {
        if (key === 'data_fields') continue;
        if (val && typeof val === 'object' && 'value' in (val as any)) {
          fields.push({ key, label: FIELD_LABELS[key] || key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()), dataField: val });
        }
      }
      if (fields.length > 0) grouped['peer_comparables'] = fields;
    }
    
    return grouped;
  };
  
  const groupedFields = extractAllFields();

  /**
   * Helper function to extract values from unified schema format
   * Backend returns: { historical_financials: { revenue: { value: [...], status: 'RETRIEVED', ... } } }
   * Extracts period values from DataField objects
   */
  const getFieldValues = (data, fieldName) => {
    if (!data || !data.historical_financials) return {};

    const fieldData = data.historical_financials[fieldName];
    if (!fieldData) return {};

    // Handle DataField with array of period values
    if (fieldData.value && Array.isArray(fieldData.value)) {
      const result = {};
      fieldData.value.forEach(periodValue => {
        if (periodValue.period && periodValue.value !== undefined) {
          result[periodValue.period] = periodValue.value;
        }
      });
      return result;
    }

    // Handle single value case
    if (fieldData.value !== undefined) {
      return { value: fieldData.value };
    }

    return {};
  };

  // Helper function to format numbers
  const formatNumber = (num, decimals = 2) => {
    if (num === null || num === undefined) return 'N/A';
    return Number(num).toLocaleString('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
  };

  const formatCurrency = (num) => {
    if (num === null || num === undefined) return 'N/A';
    const absNum = Math.abs(num);
    if (absNum >= 1e9) return `$${(num / 1e9).toFixed(2)}B`;
    if (absNum >= 1e6) return `$${(num / 1e6).toFixed(2)}M`;
    if (absNum >= 1e3) return `$${(num / 1e3).toFixed(2)}K`;
    return `$${num.toFixed(2)}`;
  };

  const formatPercent = (num) => {
    if (num === null || num === undefined) return 'N/A';
    return `${(num * 100).toFixed(2)}%`;
  };

  // Render ALL expected inputs DYNAMICALLY from backend response
  // No hardcoded field list — any new field added to the backend automatically appears
  const renderAllInputs = () => {
    const categories = Object.keys(groupedFields);
    
    if (categories.length === 0) {
      return (
        <div className="summary-box" style={{ background: 'var(--color-bearish-bg)', marginBottom: '20px' }}>
          <h3>⚠️ No Data Retrieved</h3>
          <p style={{ color: 'var(--color-bearish)' }}>Unable to display inputs. Please check if data was successfully fetched from APIs.</p>
        </div>
      );
    }

    return (
      <div style={{ marginBottom: '20px' }}>
        {categories.map(category => {
          const fields = groupedFields[category];
          const config = CATEGORY_CONFIG[category] || { label: category, gradient: 'linear-gradient(135deg, var(--canvas-bg) 0%, #e0e0e0 100%)', icon: '📊' };

          return (
            <div key={category} className="summary-box" style={{ background: config.gradient, marginBottom: '20px' }}>
              <h3 style={{ marginBottom: '16px' }}>{config.icon} {config.label}</h3>
              <div style={{ display: 'grid', gap: '12px' }}>
                {fields.map(({ key, label, dataField }) => {
                  const fieldData = dataField;
                  const hasData = fieldData && (
                    (Array.isArray(fieldData.value) && fieldData.value.some((v: any) => v !== null && v !== undefined)) ||
                    (!Array.isArray(fieldData.value) && fieldData.value !== null && fieldData.value !== undefined)
                  );

                  const getStatusInfo = () => {
                    if (!hasData || fieldData?.is_missing) return { status: 'MISSING', label: '⚠ MISSING', color: 'var(--color-neutral)', bg: 'var(--color-neutral-bg)' };
                    switch (fieldData.status) {
                      case 'CALCULATED': return { status: 'CALCULATED', label: '📊 CALC', color: 'var(--accent-primary)', bg: 'var(--accent-primary-subtle)' };
                      case 'RETRIEVED': return { status: 'RETRIEVED', label: '✓ FETCHED', color: 'var(--color-bullish)', bg: 'var(--color-bullish-bg)' };
                      case 'MANUAL_OVERRIDE': return { status: 'MANUAL', label: '✏️ MANUAL', color: 'var(--color-manual)', bg: 'rgba(124, 58, 237, 0.08)' };
                      default: return { status: 'UNKNOWN', label: '? UNKNOWN', color: 'var(--text-tertiary)', bg: 'var(--canvas-bg)' };
                    }
                  };
                  const statusInfo = getStatusInfo();

                  // Normalize value to array of {period, value} objects
                  const normalizeValues = (val: any): Array<{ period: string; value: any }> => {
                    if (!val) return [];
                    if (Array.isArray(val)) {
                      if (val.length > 0 && typeof val[0] === 'object' && val[0] !== null && 'period' in val[0]) {
                        return val;
                      }
                      return val.map((v: any, idx: number) => ({
                        period: fieldData.reporting_period
                          ? `${fieldData.reporting_period.split('-')[0]}${idx > 0 ? ` T${idx}` : ''}`
                          : (calculatedMetrics?.periodsCovered?.[idx] || `Year ${idx + 1}`),
                        value: v
                      }));
                    }
                    return [{ period: 'Current', value: val }];
                  };

                  const periodValues = normalizeValues(fieldData.value)
                    .filter((pv: any) => pv.period !== null && pv.value !== null && pv.value !== undefined);

                  const formatVal = (v: any) => {
                    if (v === null || v === undefined) return 'N/A';
                    if (fieldData.unit === '%') {
                      const num = typeof v === 'number' ? v : parseFloat(v);
                      return !isNaN(num) ? `${(Math.abs(num) <= 1 ? num * 100 : num).toFixed(2)}%` : `${v}%`;
                    }
                    if (fieldData.unit === 'USD' || fieldData.unit === 'currency') {
                      return formatCurrency(v);
                    }
                    return typeof v === 'number' ? v.toLocaleString() : v;
                  };

                  return (
                    <div key={key} style={{
                      background: 'var(--canvas-surface)', padding: '12px', borderRadius: '6px',
                      border: hasData ? `2px solid ${statusInfo.color}` : '2px dashed #ff9800',
                      opacity: hasData ? 1 : 0.7
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                        <strong style={{ color: hasData ? statusInfo.color : '#f57c00' }}>{label}</strong>
                        <span style={{ background: statusInfo.color, color: 'white', padding: '2px 8px', borderRadius: '4px', fontSize: '11px', fontWeight: 600 }}>
                          {statusInfo.label}
                        </span>
                      </div>
                      {hasData ? (
                        <>
                          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(100px, 1fr))', gap: '6px', marginBottom: '8px' }}>
                            {periodValues.map((pv: any, idx: number) => (
                              <div key={idx} style={{ textAlign: 'center', padding: '6px', background: statusInfo.bg, borderRadius: '4px', border: `1px solid ${statusInfo.color}33` }}>
                                <small style={{ color: 'var(--text-tertiary)', display: 'block', fontSize: '11px' }}>{pv.period}</small>
                                <span style={{
                                  color: typeof pv.value === 'number' && pv.value < 0 ? 'var(--color-bearish)' : statusInfo.color,
                                  fontWeight: 600, fontSize: '12px'
                                }}>{formatVal(pv.value)}</span>
                                {fieldData.source && (
                                  <div style={{ fontSize: '9px', color: 'var(--text-secondary)', marginTop: '2px' }} title={fieldData.source}>
                                    {fieldData.status === 'CALCULATED' ? '📊 ' : '✓ '}{fieldData.source.replace('yfinance', 'Yahoo').replace('Calculated from', 'Calc:')}
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                          {fieldData.formula && (
                            <div style={{ fontSize: '11px', color: 'var(--text-secondary)', fontStyle: 'italic', borderTop: '1px dashed var(--border-default)', paddingTop: '6px' }}>
                              Formula: {fieldData.formula}
                            </div>
                          )}
                        </>
                      ) : (
                        <div style={{ textAlign: 'center', padding: '12px', background: 'var(--color-neutral-bg)', borderRadius: '4px', color: 'var(--color-neutral)', fontSize: '13px' }}>
                          ⚠️ This data point was not retrieved. You may need to manually input it in the next step.
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    );
  };

  // Render historical financials with detailed numbers (legacy view - kept for backward compatibility)
  const renderHistoricalDataLegacy = () => {

    // Extract data from unified schema format: historical_financials.{field_name}.value
    const revenue = historicalData.historical_financials?.revenue || getFieldValues(historicalData, 'revenue');
    const ebitda = historicalData.historical_financials?.ebitda || getFieldValues(historicalData, 'ebitda');
    const netIncome = historicalData.historical_financials?.net_income || getFieldValues(historicalData, 'net_income');
    const cogs = historicalData.historical_financials?.cogs || getFieldValues(historicalData, 'cogs');
    const operatingExpenses = historicalData.historical_financials?.operating_expenses || getFieldValues(historicalData, 'operating_expenses');
    const depreciation = historicalData.historical_financials?.depreciation || getFieldValues(historicalData, 'depreciation');
    const capex = historicalData.historical_financials?.capex || getFieldValues(historicalData, 'capex');
    const accountsReceivable = historicalData.historical_financials?.accounts_receivable || getFieldValues(historicalData, 'accounts_receivable');
    const inventory = historicalData.historical_financials?.inventory || getFieldValues(historicalData, 'inventory');
    const accountsPayable = historicalData.historical_financials?.accounts_payable || getFieldValues(historicalData, 'accounts_payable');
    const cashAndEquivalents = historicalData.historical_financials?.cash_and_equivalents || getFieldValues(historicalData, 'cash_and_equivalents');
    const shareholdersEquity = historicalData.historical_financials?.shareholders_equity || getFieldValues(historicalData, 'shareholders_equity');
    const totalAssets = historicalData.historical_financials?.total_assets || getFieldValues(historicalData, 'total_assets');
    const totalDebt = historicalData.historical_financials?.total_debt || getFieldValues(historicalData, 'total_debt');
    const freeCashFlow = historicalData.historical_financials?.free_cash_flow || getFieldValues(historicalData, 'free_cash_flow');

    if (!historicalData) return null;

    return (
      <div className="summary-box" style={{ background: 'var(--accent-primary-subtle)', marginBottom: '20px' }}>
        <h3>📊 {t('sections.historical_financials')}</h3>

        {/* Revenue Table */}
        {revenue && Object.keys(revenue).length > 0 && (
          <div style={{ marginTop: '16px' }}>
            <h4 style={{ color: 'var(--accent-primary)', marginBottom: '8px' }}>Revenue (3-4 years) <span style={{ background: 'var(--color-bullish)', color: 'white', padding: '2px 8px', borderRadius: '4px', fontSize: '12px', marginLeft: '8px' }}>✓ Auto-Fetched</span></h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '8px' }}>
              {Object.entries(revenue).map(([year, value]) => (
                <div key={year} style={{ background: 'var(--canvas-surface)', padding: '12px', borderRadius: '6px', textAlign: 'center' }}>
                  <strong style={{ display: 'block', marginBottom: '4px', color: 'var(--text-secondary)' }}>{year}</strong>
                  <span style={{ color: 'var(--accent-primary)', fontWeight: 600 }}>{formatCurrency(value)}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* COGS Table */}
        {cogs && Object.keys(cogs).length > 0 && (
          <div style={{ marginTop: '16px' }}>
            <h4 style={{ color: 'var(--accent-primary)', marginBottom: '8px' }}>COGS <span style={{ background: 'var(--color-bullish)', color: 'white', padding: '2px 8px', borderRadius: '4px', fontSize: '12px', marginLeft: '8px' }}>✓ Auto-Fetched</span></h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '8px' }}>
              {Object.entries(cogs).map(([year, value]) => (
                <div key={year} style={{ background: 'var(--canvas-surface)', padding: '12px', borderRadius: '6px', textAlign: 'center' }}>
                  <strong style={{ display: 'block', marginBottom: '4px', color: 'var(--text-secondary)' }}>{year}</strong>
                  <span style={{ color: 'var(--color-neutral)', fontWeight: 600 }}>{formatCurrency(value)}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* EBITDA Table */}
        {ebitda && Object.keys(ebitda).length > 0 && (
          <div style={{ marginTop: '16px' }}>
            <h4 style={{ color: 'var(--accent-primary)', marginBottom: '8px' }}>EBITDA (3-4 years) <span style={{ background: 'var(--color-bullish)', color: 'white', padding: '2px 8px', borderRadius: '4px', fontSize: '12px', marginLeft: '8px' }}>✓ Auto-Fetched</span></h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '8px' }}>
              {Object.entries(ebitda).map(([year, value]) => (
                <div key={year} style={{ background: 'var(--canvas-surface)', padding: '12px', borderRadius: '6px', textAlign: 'center' }}>
                  <strong style={{ display: 'block', marginBottom: '4px', color: 'var(--text-secondary)' }}>{year}</strong>
                  <span style={{ color: Number(value) >= 0 ? 'var(--color-bullish)' : 'var(--color-bearish)', fontWeight: 600 }}>{formatCurrency(value)}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Net Income Table */}
        {netIncome && Object.keys(netIncome).length > 0 && (
          <div style={{ marginTop: '16px' }}>
            <h4 style={{ color: 'var(--accent-primary)', marginBottom: '8px' }}>Net Income (3-4 years) <span style={{ background: 'var(--color-bullish)', color: 'white', padding: '2px 8px', borderRadius: '4px', fontSize: '12px', marginLeft: '8px' }}>✓ Auto-Fetched</span></h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '8px' }}>
              {Object.entries(netIncome).map(([year, value]) => (
                <div key={year} style={{ background: 'var(--canvas-surface)', padding: '12px', borderRadius: '6px', textAlign: 'center' }}>
                  <strong style={{ display: 'block', marginBottom: '4px', color: 'var(--text-secondary)' }}>{year}</strong>
                  <span style={{ color: Number(value) >= 0 ? 'var(--color-bullish)' : 'var(--color-bearish)', fontWeight: 600 }}>{formatCurrency(value)}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* SG&A / OpEx Table */}
        {(operatingExpenses) && (
          <div style={{ marginTop: '16px' }}>
            <h4 style={{ color: 'var(--accent-primary)', marginBottom: '8px' }}>SG&A / OpEx <span style={{ background: 'var(--color-bullish)', color: 'white', padding: '2px 8px', borderRadius: '4px', fontSize: '12px', marginLeft: '8px' }}>✓ Auto-Fetched</span></h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '8px' }}>
              {Object.entries(operatingExpenses).map(([year, value]) => (
                <div key={year} style={{ background: 'var(--canvas-surface)', padding: '12px', borderRadius: '6px', textAlign: 'center' }}>
                  <strong style={{ display: 'block', marginBottom: '4px', color: 'var(--text-secondary)' }}>{year}</strong>
                  <span style={{ color: 'var(--color-neutral)', fontWeight: 600 }}>{formatCurrency(value)}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Depreciation & Amortization Table */}
        {depreciation && Object.keys(depreciation).length > 0 && (
          <div style={{ marginTop: '16px' }}>
            <h4 style={{ color: 'var(--accent-primary)', marginBottom: '8px' }}>Depreciation & Amortization <span style={{ background: 'var(--color-bullish)', color: 'white', padding: '2px 8px', borderRadius: '4px', fontSize: '12px', marginLeft: '8px' }}>✓ Auto-Fetched</span></h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '8px' }}>
              {Object.entries(depreciation).map(([year, value]) => (
                <div key={year} style={{ background: 'var(--canvas-surface)', padding: '12px', borderRadius: '6px', textAlign: 'center' }}>
                  <strong style={{ display: 'block', marginBottom: '4px', color: 'var(--text-secondary)' }}>{year}</strong>
                  <span style={{ color: 'var(--accent-primary)', fontWeight: 600 }}>{formatCurrency(value)}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* CapEx Table */}
        {capex && Object.keys(capex).length > 0 && (
          <div style={{ marginTop: '16px' }}>
            <h4 style={{ color: 'var(--accent-primary)', marginBottom: '8px' }}>CapEx <span style={{ background: 'var(--color-bullish)', color: 'white', padding: '2px 8px', borderRadius: '4px', fontSize: '12px', marginLeft: '8px' }}>✓ Auto-Fetched</span></h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '8px' }}>
              {Object.entries(capex).map(([year, value]) => (
                <div key={year} style={{ background: 'var(--canvas-surface)', padding: '12px', borderRadius: '6px', textAlign: 'center' }}>
                  <strong style={{ display: 'block', marginBottom: '4px', color: 'var(--text-secondary)' }}>{year}</strong>
                  <span style={{ color: 'var(--color-manual)', fontWeight: 600 }}>{formatCurrency(value)}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Working Capital Items Group */}
        <div style={{ marginTop: '24px', background: 'var(--color-bullish-bg)', padding: '16px', borderRadius: '8px' }}>
          <h4 style={{ color: 'var(--color-bullish)', marginBottom: '16px' }}>Working Capital Items (AR, Inventory, AP) <span style={{ background: 'var(--color-bullish)', color: 'white', padding: '2px 8px', borderRadius: '4px', fontSize: '12px', marginLeft: '8px' }}>✓ Auto-Fetched</span></h4>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
            {/* Accounts Receivable */}
            {accountsReceivable && Object.keys(accountsReceivable).length > 0 && (
              <div style={{ background: 'var(--canvas-surface)', padding: '12px', borderRadius: '6px' }}>
                <strong style={{ display: 'block', marginBottom: '8px', color: 'var(--text-secondary)', fontSize: '14px' }}>Accounts Receivable</strong>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(80px, 1fr))', gap: '4px' }}>
                  {Object.entries(accountsReceivable).map(([year, value]) => (
                    <div key={year} style={{ textAlign: 'center' }}>
                      <small style={{ color: 'var(--text-tertiary)', display: 'block' }}>{year}</small>
                      <span style={{ color: 'var(--color-manual)', fontWeight: 600, fontSize: '13px' }}>{formatCurrency(value)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Inventory */}
            {inventory && Object.keys(inventory).length > 0 && (
              <div style={{ background: 'var(--canvas-surface)', padding: '12px', borderRadius: '6px' }}>
                <strong style={{ display: 'block', marginBottom: '8px', color: 'var(--text-secondary)', fontSize: '14px' }}>Inventory</strong>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(80px, 1fr))', gap: '4px' }}>
                  {Object.entries(inventory).map(([year, value]) => (
                    <div key={year} style={{ textAlign: 'center' }}>
                      <small style={{ color: 'var(--text-tertiary)', display: 'block' }}>{year}</small>
                      <span style={{ color: 'var(--color-ai)', fontWeight: 600, fontSize: '13px' }}>{formatCurrency(value)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Accounts Payable */}
            {accountsPayable && Object.keys(accountsPayable).length > 0 && (
              <div style={{ background: 'var(--canvas-surface)', padding: '12px', borderRadius: '6px' }}>
                <strong style={{ display: 'block', marginBottom: '8px', color: 'var(--text-secondary)', fontSize: '14px' }}>Accounts Payable</strong>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(80px, 1fr))', gap: '4px' }}>
                  {Object.entries(accountsPayable).map(([year, value]) => (
                    <div key={year} style={{ textAlign: 'center' }}>
                      <small style={{ color: 'var(--text-tertiary)', display: 'block' }}>{year}</small>
                      <span style={{ color: 'var(--color-bearish)', fontWeight: 600, fontSize: '13px' }}>{formatCurrency(value)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Shareholders Equity Table */}
        {shareholdersEquity && Object.keys(shareholdersEquity).length > 0 && (
          <div style={{ marginTop: '16px' }}>
            <h4 style={{ color: 'var(--accent-primary)', marginBottom: '8px' }}>Shareholders Equity <span style={{ background: 'var(--color-bullish)', color: 'white', padding: '2px 8px', borderRadius: '4px', fontSize: '12px', marginLeft: '8px' }}>✓ Auto-Fetched</span></h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '8px' }}>
              {Object.entries(shareholdersEquity).map(([year, value]) => (
                <div key={year} style={{ background: 'var(--canvas-surface)', padding: '12px', borderRadius: '6px', textAlign: 'center' }}>
                  <strong style={{ display: 'block', marginBottom: '4px', color: 'var(--text-secondary)' }}>{year}</strong>
                  <span style={{ color: 'var(--accent-primary)', fontWeight: 600 }}>{formatCurrency(value)}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Total Assets Table */}
        {totalAssets && Object.keys(totalAssets).length > 0 && (
          <div style={{ marginTop: '16px' }}>
            <h4 style={{ color: 'var(--accent-primary)', marginBottom: '8px' }}>Total Assets <span style={{ background: 'var(--color-bullish)', color: 'white', padding: '2px 8px', borderRadius: '4px', fontSize: '12px', marginLeft: '8px' }}>✓ Auto-Fetched</span></h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '8px' }}>
              {Object.entries(totalAssets).map(([year, value]) => (
                <div key={year} style={{ background: 'var(--canvas-surface)', padding: '12px', borderRadius: '6px', textAlign: 'center' }}>
                  <strong style={{ display: 'block', marginBottom: '4px', color: 'var(--text-secondary)' }}>{year}</strong>
                  <span style={{ color: 'var(--accent-primary)', fontWeight: 600 }}>{formatCurrency(value)}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Total Debt Table */}
        {totalDebt && Object.keys(totalDebt).length > 0 && (
          <div style={{ marginTop: '16px' }}>
            <h4 style={{ color: 'var(--accent-primary)', marginBottom: '8px' }}>Total Debt <span style={{ background: 'var(--color-bullish)', color: 'white', padding: '2px 8px', borderRadius: '4px', fontSize: '12px', marginLeft: '8px' }}>✓ Auto-Fetched</span></h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '8px' }}>
              {Object.entries(totalDebt).map(([year, value]) => (
                <div key={year} style={{ background: 'var(--canvas-surface)', padding: '12px', borderRadius: '6px', textAlign: 'center' }}>
                  <strong style={{ display: 'block', marginBottom: '4px', color: 'var(--text-secondary)' }}>{year}</strong>
                  <span style={{ color: 'var(--color-bearish)', fontWeight: 600 }}>{formatCurrency(value)}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Free Cash Flow Table */}
        {freeCashFlow && Object.keys(freeCashFlow).length > 0 && (
          <div style={{ marginTop: '16px' }}>
            <h4 style={{ color: 'var(--accent-primary)', marginBottom: '8px' }}>Free Cash Flow <span style={{ background: 'var(--color-bullish)', color: 'white', padding: '2px 8px', borderRadius: '4px', fontSize: '12px', marginLeft: '8px' }}>✓ Auto-Fetched</span></h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '8px' }}>
              {Object.entries(freeCashFlow).map(([year, value]) => (
                <div key={year} style={{ background: 'var(--canvas-surface)', padding: '12px', borderRadius: '6px', textAlign: 'center' }}>
                  <strong style={{ display: 'block', marginBottom: '4px', color: 'var(--text-secondary)' }}>{year}</strong>
                  <span style={{ color: Number(value) >= 0 ? 'var(--color-bullish)' : 'var(--color-bearish)', fontWeight: 600 }}>{formatCurrency(value)}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Cash & Equivalents Table */}
        {cashAndEquivalents && Object.keys(cashAndEquivalents).length > 0 && (
          <div style={{ marginTop: '16px' }}>
            <h4 style={{ color: 'var(--accent-primary)', marginBottom: '8px' }}>Cash & Equivalents <span style={{ background: 'var(--color-bullish)', color: 'white', padding: '2px 8px', borderRadius: '4px', fontSize: '12px', marginLeft: '8px' }}>✓ Auto-Fetched</span></h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '8px' }}>
              {Object.entries(cashAndEquivalents).map(([year, value]) => (
                <div key={year} style={{ background: 'var(--canvas-surface)', padding: '12px', borderRadius: '6px', textAlign: 'center' }}>
                  <strong style={{ display: 'block', marginBottom: '4px', color: 'var(--text-secondary)' }}>{year}</strong>
                  <span style={{ color: 'var(--accent-primary)', fontWeight: 600 }}>{formatCurrency(value)}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Summary Metrics */}
        <div style={{ marginTop: '20px', padding: '16px', background: 'var(--canvas-surface)', borderRadius: '8px' }}>
          <h4 style={{ color: 'var(--accent-primary)', marginBottom: '12px' }}>📊 Key Financial Metrics</h4>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '12px' }}>
            {historicalData.revenue_cagr !== undefined && (
              <div>
                <strong>Revenue CAGR:</strong>
                <p style={{ margin: '4px 0 0 0', color: 'var(--color-bullish)', fontWeight: 600 }}>
                  {(historicalData.revenue_cagr * 100).toFixed(2)}%
                </p>
              </div>
            )}
            {historicalData.avg_ebitda_margin !== undefined && (
              <div>
                <strong>Avg EBITDA Margin:</strong>
                <p style={{ margin: '4px 0 0 0', color: 'var(--accent-primary)', fontWeight: 600 }}>
                  {(historicalData.avg_ebitda_margin * 100).toFixed(2)}%
                </p>
              </div>
            )}
            {historicalData.avg_roe !== undefined && (
              <div>
                <strong>Avg ROE:</strong>
                <p style={{ margin: '4px 0 0 0', color: 'var(--color-manual)', fontWeight: 600 }}>
                  {(historicalData.avg_roe * 100).toFixed(2)}%
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  };

  // Render forecast drivers with detailed period values
  const renderForecastDrivers = () => {
    if (!forecastDrivers || Object.keys(forecastDrivers).length === 0) {
      return (
        <div className="summary-box" style={{ background: 'var(--color-bullish-bg)', marginBottom: '20px' }}>
          <h3>📈 {t('sections.forecast_drivers')}</h3>
          <div style={{ padding: '20px', textAlign: 'center', color: 'var(--text-secondary)' }}>
            <p style={{ margin: 0, fontSize: '14px' }}>
              ⚠️ No forecast drivers retrieved from the API. These will be generated in 
              <strong> Step 7: Process Historical Data</strong>.
            </p>
          </div>
        </div>
      );
    }

    return (
      <div className="summary-box" style={{ background: 'var(--color-bullish-bg)', marginBottom: '20px' }}>
        <h3>📈 {t('sections.forecast_drivers')}</h3>

        {['base_case', 'best_case', 'worst_case'].map(scenario => {
          const scenarioData = forecastDrivers[scenario];
          if (!scenarioData) return null;

          return (
            <div key={scenario} style={{ marginTop: '16px', paddingBottom: '16px', borderBottom: scenario === 'worst_case' ? 'none' : '1px solid #a5d6a7' }}>
              <h4 style={{ color: 'var(--color-bullish)', marginBottom: '12px', textTransform: 'capitalize' }}>
                {scenario.replace('_', ' ')} Scenario
              </h4>

              {/* Revenue Growth */}
              {scenarioData.revenue_growth && scenarioData.revenue_growth.length > 0 && (
                <div style={{ marginBottom: '12px' }}>
                  <strong style={{ display: 'block', marginBottom: '6px', color: 'var(--text-secondary)' }}>Revenue Growth:</strong>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                    {scenarioData.revenue_growth.map((value, idx) => (
                      <div key={idx} style={{ background: 'var(--canvas-surface)', padding: '8px 12px', borderRadius: '4px', minWidth: '80px', textAlign: 'center' }}>
                        <span style={{ fontSize: '11px', color: 'var(--text-tertiary)', display: 'block' }}>Y{idx + 1}</span>
                        <span style={{ color: 'var(--color-bullish)', fontWeight: 600 }}>{formatPercent(value)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Inflation Rate */}
              {scenarioData.inflation_rate && scenarioData.inflation_rate.length > 0 && (
                <div style={{ marginBottom: '12px' }}>
                  <strong style={{ display: 'block', marginBottom: '6px', color: 'var(--text-secondary)' }}>Inflation Rate:</strong>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                    {scenarioData.inflation_rate.map((value, idx) => (
                      <div key={idx} style={{ background: 'var(--canvas-surface)', padding: '8px 12px', borderRadius: '4px', minWidth: '80px', textAlign: 'center' }}>
                        <span style={{ fontSize: '11px', color: 'var(--text-tertiary)', display: 'block' }}>Y{idx + 1}</span>
                        <span style={{ color: 'var(--color-bullish)', fontWeight: 600 }}>{formatPercent(value)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* OpEx Growth */}
              {scenarioData.opex_growth && scenarioData.opex_growth.length > 0 && (
                <div style={{ marginBottom: '12px' }}>
                  <strong style={{ display: 'block', marginBottom: '6px', color: 'var(--text-secondary)' }}>OpEx Growth:</strong>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                    {scenarioData.opex_growth.map((value, idx) => (
                      <div key={idx} style={{ background: 'var(--canvas-surface)', padding: '8px 12px', borderRadius: '4px', minWidth: '80px', textAlign: 'center' }}>
                        <span style={{ fontSize: '11px', color: 'var(--text-tertiary)', display: 'block' }}>Y{idx + 1}</span>
                        <span style={{ color: 'var(--color-bullish)', fontWeight: 600 }}>{formatPercent(value)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Capital Expenditure */}
              {scenarioData.capital_expenditure && scenarioData.capital_expenditure.length > 0 && (
                <div style={{ marginBottom: '12px' }}>
                  <strong style={{ display: 'block', marginBottom: '6px', color: 'var(--text-secondary)' }}>Capital Expenditure (% of Revenue):</strong>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                    {scenarioData.capital_expenditure.map((value, idx) => (
                      <div key={idx} style={{ background: 'var(--canvas-surface)', padding: '8px 12px', borderRadius: '4px', minWidth: '80px', textAlign: 'center' }}>
                        <span style={{ fontSize: '11px', color: 'var(--text-tertiary)', display: 'block' }}>Y{idx + 1}</span>
                        <span style={{ color: 'var(--color-bullish)', fontWeight: 600 }}>{formatPercent(value)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* AR Days */}
              {scenarioData.ar_days && scenarioData.ar_days.length > 0 && (
                <div style={{ marginBottom: '12px' }}>
                  <strong style={{ display: 'block', marginBottom: '6px', color: 'var(--text-secondary)' }}>Accounts Receivable Days:</strong>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                    {scenarioData.ar_days.map((value, idx) => (
                      <div key={idx} style={{ background: 'var(--canvas-surface)', padding: '8px 12px', borderRadius: '4px', minWidth: '80px', textAlign: 'center' }}>
                        <span style={{ fontSize: '11px', color: 'var(--text-tertiary)', display: 'block' }}>Y{idx + 1}</span>
                        <span style={{ color: 'var(--color-bullish)', fontWeight: 600 }}>{formatNumber(value, 0)} days</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Inventory Days */}
              {scenarioData.inv_days && scenarioData.inv_days.length > 0 && (
                <div style={{ marginBottom: '12px' }}>
                  <strong style={{ display: 'block', marginBottom: '6px', color: 'var(--text-secondary)' }}>Inventory Days:</strong>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                    {scenarioData.inv_days.map((value, idx) => (
                      <div key={idx} style={{ background: 'var(--canvas-surface)', padding: '8px 12px', borderRadius: '4px', minWidth: '80px', textAlign: 'center' }}>
                        <span style={{ fontSize: '11px', color: 'var(--text-tertiary)', display: 'block' }}>Y{idx + 1}</span>
                        <span style={{ color: 'var(--color-bullish)', fontWeight: 600 }}>{formatNumber(value, 0)} days</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* AP Days */}
              {scenarioData.ap_days && scenarioData.ap_days.length > 0 && (
                <div style={{ marginBottom: '12px' }}>
                  <strong style={{ display: 'block', marginBottom: '6px', color: 'var(--text-secondary)' }}>Accounts Payable Days:</strong>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                    {scenarioData.ap_days.map((value, idx) => (
                      <div key={idx} style={{ background: 'var(--canvas-surface)', padding: '8px 12px', borderRadius: '4px', minWidth: '80px', textAlign: 'center' }}>
                        <span style={{ fontSize: '11px', color: 'var(--text-tertiary)', display: 'block' }}>Y{idx + 1}</span>
                        <span style={{ color: 'var(--color-bullish)', fontWeight: 600 }}>{formatNumber(value, 0)} days</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Tax Rate */}
              {scenarioData.tax_rate && scenarioData.tax_rate.length > 0 && (
                <div>
                  <strong style={{ display: 'block', marginBottom: '6px', color: 'var(--text-secondary)' }}>Tax Rate:</strong>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                    {scenarioData.tax_rate.map((value, idx) => (
                      <div key={idx} style={{ background: 'var(--canvas-surface)', padding: '8px 12px', borderRadius: '4px', minWidth: '80px', textAlign: 'center' }}>
                        <span style={{ fontSize: '11px', color: 'var(--text-tertiary)', display: 'block' }}>Y{idx + 1}</span>
                        <span style={{ color: 'var(--color-bullish)', fontWeight: 600 }}>{formatPercent(value)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    );
  };

  // Render peer data with detailed company information
  const renderPeerData = () => {
    // Check if peerData exists and has companies array
    const hasPeerData = peerData && (
      (peerData.companies && peerData.companies.length > 0) ||
      (Array.isArray(peerData) && peerData.length > 0)
    );

    if (!hasPeerData) {
      return (
        <div className="summary-box" style={{ background: 'var(--color-neutral-bg)', marginBottom: '20px' }}>
          <h3>🏢 {t('sections.peer_comparison')}</h3>
          <div style={{ padding: '20px', textAlign: 'center', color: 'var(--text-secondary)' }}>
            <p style={{ margin: 0, fontSize: '14px' }}>
              ⚠️ No peer comparison data retrieved from the API. Peer data is fetched based on your peer selection in Step 4.
            </p>
            <p style={{ margin: '10px 0 0 0', fontSize: '13px', fontStyle: 'italic' }}>
              💡 Tip: Check the RAW DATA DEBUG section below to see what peer data was received.
            </p>
          </div>
        </div>
      );
    }

    const companies = peerData.companies || (Array.isArray(peerData) ? peerData : []);

    return (
      <div className="summary-box" style={{ background: 'var(--color-neutral-bg)', marginBottom: '20px' }}>
        <h3>🏢 {t('sections.peer_comparison')}</h3>

        {/* Summary Statistics */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '12px', marginBottom: '20px' }}>
          <div style={{ background: 'var(--canvas-surface)', padding: '12px', borderRadius: '6px' }}>
            <strong>Peers Found:</strong>
            <p style={{ margin: '4px 0 0 0', color: 'var(--text-secondary)' }}>
              {companies.length} companies ✓
            </p>
          </div>
          {peerData.median_ev_ebitda && (
            <div style={{ background: 'var(--canvas-surface)', padding: '12px', borderRadius: '6px' }}>
              <strong>Median EV/EBITDA:</strong>
              <p style={{ margin: '4px 0 0 0', color: 'var(--text-secondary)' }}>
                {peerData.median_ev_ebitda.toFixed(1)}x ✓
              </p>
            </div>
          )}
          {peerData.median_pe && (
            <div style={{ background: 'var(--canvas-surface)', padding: '12px', borderRadius: '6px' }}>
              <strong>Median P/E:</strong>
              <p style={{ margin: '4px 0 0 0', color: 'var(--text-secondary)' }}>
                {peerData.median_pe.toFixed(1)}x ✓
              </p>
            </div>
          )}
          {peerData.median_ev_revenue && (
            <div style={{ background: 'var(--canvas-surface)', padding: '12px', borderRadius: '6px' }}>
              <strong>Median EV/Revenue:</strong>
              <p style={{ margin: '4px 0 0 0', color: 'var(--text-secondary)' }}>
                {peerData.median_ev_revenue.toFixed(1)}x ✓
              </p>
            </div>
          )}
          {peerData.median_pb && (
            <div style={{ background: 'var(--canvas-surface)', padding: '12px', borderRadius: '6px' }}>
              <strong>Median P/B:</strong>
              <p style={{ margin: '4px 0 0 0', color: 'var(--text-secondary)' }}>
                {peerData.median_pb.toFixed(1)}x ✓
              </p>
            </div>
          )}
        </div>

        {/* Individual Company Details */}
        {companies.length > 0 && (
          <div>
            <h4 style={{ color: 'var(--color-neutral)', marginBottom: '12px' }}>Individual Peer Companies</h4>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
                <thead>
                  <tr style={{ background: 'var(--color-neutral-bg)', borderBottom: '2px solid var(--color-neutral)' }}>
                    <th style={{ padding: '10px', textAlign: 'left', border: '1px solid var(--color-neutral-bg)' }}>Ticker</th>
                    <th style={{ padding: '10px', textAlign: 'right', border: '1px solid var(--color-neutral-bg)' }}>Market Cap</th>
                    <th style={{ padding: '10px', textAlign: 'right', border: '1px solid var(--color-neutral-bg)' }}>EV/EBITDA</th>
                    <th style={{ padding: '10px', textAlign: 'right', border: '1px solid var(--color-neutral-bg)' }}>P/E</th>
                    <th style={{ padding: '10px', textAlign: 'right', border: '1px solid var(--color-neutral-bg)' }}>EV/Revenue</th>
                    <th style={{ padding: '10px', textAlign: 'right', border: '1px solid var(--color-neutral-bg)' }}>P/B</th>
                  </tr>
                </thead>
                <tbody>
                  {companies.map((company, idx) => (
                    <tr key={idx} style={{ borderBottom: '1px solid var(--color-neutral-bg)', background: idx % 2 === 0 ? 'white' : '#fff8e1' }}>
                      <td style={{ padding: '10px', fontWeight: 600, color: 'var(--text-primary)', border: '1px solid var(--color-neutral-bg)' }}>
                        {company.ticker || company.symbol || 'N/A'}
                      </td>
                      <td style={{ padding: '10px', textAlign: 'right', color: 'var(--text-secondary)', border: '1px solid var(--color-neutral-bg)' }}>
                        {company.market_cap ? formatCurrency(company.market_cap) : 'N/A'}
                      </td>
                      <td style={{ padding: '10px', textAlign: 'right', color: 'var(--text-secondary)', border: '1px solid var(--color-neutral-bg)' }}>
                        {company.ev_ebitda ? company.ev_ebitda.toFixed(1) + 'x' : 'N/A'}
                      </td>
                      <td style={{ padding: '10px', textAlign: 'right', color: 'var(--text-secondary)', border: '1px solid var(--color-neutral-bg)' }}>
                        {company.pe_ratio ? company.pe_ratio.toFixed(1) + 'x' : 'N/A'}
                      </td>
                      <td style={{ padding: '10px', textAlign: 'right', color: 'var(--text-secondary)', border: '1px solid var(--color-neutral-bg)' }}>
                        {company.ev_revenue ? company.ev_revenue.toFixed(1) + 'x' : 'N/A'}
                      </td>
                      <td style={{ padding: '10px', textAlign: 'right', color: 'var(--text-secondary)', border: '1px solid var(--color-neutral-bg)' }}>
                        {company.pb_ratio ? company.pb_ratio.toFixed(1) + 'x' : 'N/A'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    );
  };

  // Render DCF inputs with all components
  const renderDcfInputs = () => {
    // NOTE: DCF inputs (WACC, terminal growth, etc.) are generated in Step 8 (AI Assumptions)
    // Step 7 only shows raw API data and forecast drivers from the API
    if (!dcfInputs || Object.keys(dcfInputs).length === 0) {
      return (
        <div className="summary-box" style={{ background: 'rgba(124, 58, 237, 0.08)', marginBottom: '20px' }}>
          <h3>💰 {t('sections.dcf_model_inputs')}</h3>
          <div style={{ padding: '20px', textAlign: 'center', color: 'var(--text-secondary)' }}>
            <p style={{ margin: '0 0 10px 0', fontWeight: 600 }}>⏳ DCF Inputs Not Yet Generated</p>
            <p style={{ margin: 0, fontSize: '14px' }}>
              DCF inputs (WACC, Terminal Growth Rate, Risk-Free Rate, etc.) will be generated in 
              <strong> Step 7: Process Historical Data</strong> based on the historical data reviewed above.
            </p>
            <p style={{ margin: '10px 0 0 0', fontSize: '13px', fontStyle: 'italic' }}>
              💡 Tip: Review the forecast drivers below to see what data was retrieved from the API.
            </p>
          </div>
        </div>
      );
    }

    return (
      <div className="summary-box" style={{ background: 'rgba(124, 58, 237, 0.08)', marginBottom: '20px' }}>
        <h3>💰 {t('sections.dcf_model_inputs')}</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '12px' }}>
          {dcfInputs.risk_free_rate !== undefined && (
            <div style={{ background: 'var(--canvas-surface)', padding: '12px', borderRadius: '6px' }}>
              <strong>Risk-Free Rate:</strong>
              <p style={{ margin: '4px 0 0 0', color: 'var(--text-secondary)' }}>
                {(dcfInputs.risk_free_rate * 100).toFixed(2)}% ✓
              </p>
            </div>
          )}
          {dcfInputs.equity_risk_premium !== undefined && (
            <div style={{ background: 'var(--canvas-surface)', padding: '12px', borderRadius: '6px' }}>
              <strong>Equity Risk Premium:</strong>
              <p style={{ margin: '4px 0 0 0', color: 'var(--text-secondary)' }}>
                {(dcfInputs.equity_risk_premium * 100).toFixed(2)}% ✓
              </p>
            </div>
          )}
          {dcfInputs.beta !== undefined && (
            <div style={{ background: 'var(--canvas-surface)', padding: '12px', borderRadius: '6px' }}>
              <strong>Beta:</strong>
              <p style={{ margin: '4px 0 0 0', color: 'var(--text-secondary)' }}>
                {dcfInputs.beta.toFixed(2)} ✓
              </p>
            </div>
          )}
          {dcfInputs.cost_of_debt !== undefined && (
            <div style={{ background: 'var(--canvas-surface)', padding: '12px', borderRadius: '6px' }}>
              <strong>Cost of Debt:</strong>
              <p style={{ margin: '4px 0 0 0', color: 'var(--text-secondary)' }}>
                {(dcfInputs.cost_of_debt * 100).toFixed(2)}% ✓
              </p>
            </div>
          )}
          {dcfInputs.wacc && (
            <div style={{ background: 'var(--canvas-surface)', padding: '12px', borderRadius: '6px', borderLeft: '4px solid #9c27b0' }}>
              <strong>WACC (Calculated):</strong>
              <p style={{ margin: '4px 0 0 0', color: 'var(--color-manual)', fontWeight: 600 }}>
                {(dcfInputs.wacc * 100).toFixed(2)}% ✓
              </p>
            </div>
          )}
          {dcfInputs.terminal_growth_rate && (
            <div style={{ background: 'var(--canvas-surface)', padding: '12px', borderRadius: '6px' }}>
              <strong>Terminal Growth Rate:</strong>
              <p style={{ margin: '4px 0 0 0', color: 'var(--text-secondary)' }}>
                {(dcfInputs.terminal_growth_rate * 100).toFixed(2)}% ✓
              </p>
            </div>
          )}
          {dcfInputs.terminal_ebitda_multiple && (
            <div style={{ background: 'var(--canvas-surface)', padding: '12px', borderRadius: '6px' }}>
              <strong>Terminal EBITDA Multiple:</strong>
              <p style={{ margin: '4px 0 0 0', color: 'var(--text-secondary)' }}>
                {dcfInputs.terminal_ebitda_multiple.toFixed(1)}x ✓
              </p>
            </div>
          )}
          {dcfInputs.useful_life_existing && (
            <div style={{ background: 'var(--canvas-surface)', padding: '12px', borderRadius: '6px' }}>
              <strong>Useful Life (Existing Assets):</strong>
              <p style={{ margin: '4px 0 0 0', color: 'var(--text-secondary)' }}>
                {dcfInputs.useful_life_existing} years ✓
              </p>
            </div>
          )}
        </div>
      </div>
    );
  };

  // Render DuPont results with detailed ratios
  const renderDupontResults = () => {
    if (!dupontResults) return null;

    return (
      <div className="summary-box" style={{ background: 'var(--color-bearish-bg)', marginBottom: '20px' }}>
        <h3>📊 {t('sections.dupont_analysis')}</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '12px' }}>
          {dupontResults.net_profit_margin && (
            <div style={{ background: 'var(--canvas-surface)', padding: '12px', borderRadius: '6px' }}>
              <strong>Net Profit Margin:</strong>
              <p style={{ margin: '4px 0 0 0', color: 'var(--text-secondary)' }}>
                {(dupontResults.net_profit_margin * 100).toFixed(2)}% ✓
              </p>
            </div>
          )}
          {dupontResults.asset_turnover && (
            <div style={{ background: 'var(--canvas-surface)', padding: '12px', borderRadius: '6px' }}>
              <strong>Asset Turnover:</strong>
              <p style={{ margin: '4px 0 0 0', color: 'var(--text-secondary)' }}>
                {dupontResults.asset_turnover.toFixed(2)}x ✓
              </p>
            </div>
          )}
          {dupontResults.equity_multiplier && (
            <div style={{ background: 'var(--canvas-surface)', padding: '12px', borderRadius: '6px' }}>
              <strong>Equity Multiplier:</strong>
              <p style={{ margin: '4px 0 0 0', color: 'var(--text-secondary)' }}>
                {dupontResults.equity_multiplier.toFixed(2)}x ✓
              </p>
            </div>
          )}
          {dupontResults.roe && (
            <div style={{ background: 'var(--canvas-surface)', padding: '12px', borderRadius: '6px', borderLeft: '4px solid #e91e63' }}>
              <strong>ROE (Calculated):</strong>
              <p style={{ margin: '4px 0 0 0', color: 'var(--color-bearish)', fontWeight: 600 }}>
                {(dupontResults.roe * 100).toFixed(2)}% ✓
              </p>
            </div>
          )}
        </div>
      </div>
    );
  };

  // Render Comps results with all multiples
  const renderCompsResults = () => {
    if (!compsResults) return null;

    return (
      <div className="summary-box" style={{ background: 'var(--accent-primary-subtle)', marginBottom: '20px' }}>
        <h3>📈 {t('sections.comps_analysis')}</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '12px' }}>
          {compsResults.ev_ebitda && (
            <div style={{ background: 'var(--canvas-surface)', padding: '12px', borderRadius: '6px' }}>
              <strong>EV/EBITDA:</strong>
              <p style={{ margin: '4px 0 0 0', color: 'var(--text-secondary)' }}>
                {compsResults.ev_ebitda.toFixed(1)}x ✓
              </p>
            </div>
          )}
          {compsResults.pe_ratio && (
            <div style={{ background: 'var(--canvas-surface)', padding: '12px', borderRadius: '6px' }}>
              <strong>P/E Ratio:</strong>
              <p style={{ margin: '4px 0 0 0', color: 'var(--text-secondary)' }}>
                {compsResults.pe_ratio.toFixed(1)}x ✓
              </p>
            </div>
          )}
          {compsResults.ev_revenue && (
            <div style={{ background: 'var(--canvas-surface)', padding: '12px', borderRadius: '6px' }}>
              <strong>EV/Revenue:</strong>
              <p style={{ margin: '4px 0 0 0', color: 'var(--text-secondary)' }}>
                {compsResults.ev_revenue.toFixed(1)}x ✓
              </p>
            </div>
          )}
          {compsResults.pb_ratio && (
            <div style={{ background: 'var(--canvas-surface)', padding: '12px', borderRadius: '6px' }}>
              <strong>P/B Ratio:</strong>
              <p style={{ margin: '4px 0 0 0', color: 'var(--text-secondary)' }}>
                {compsResults.pb_ratio.toFixed(1)}x ✓
              </p>
            </div>
          )}
          {compsResults.peg_ratio && (
            <div style={{ background: 'var(--canvas-surface)', padding: '12px', borderRadius: '6px' }}>
              <strong>PEG Ratio:</strong>
              <p style={{ margin: '4px 0 0 0', color: 'var(--text-secondary)' }}>
                {compsResults.peg_ratio.toFixed(2)}x ✓
              </p>
            </div>
          )}
        </div>
      </div>
    );
  };

  // Render calculated metrics section (intermediate metrics calculated by backend)
  const renderCalculatedMetrics = () => {
    if (!calculatedMetrics || !calculatedMetrics.data_fields || calculatedMetrics.data_fields.length === 0) return null;

    return (
      <div className="summary-box" style={{ background: 'var(--color-bullish-bg)', marginBottom: '20px' }}>
        <h3>🧮 {t('sections.calculated_metrics')}</h3>
        <p style={{ color: 'var(--text-secondary)', marginBottom: '16px', fontStyle: 'italic' }}>
          These metrics are automatically calculated from retrieved data (not final valuations).
        </p>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px' }}>
          {calculatedMetrics.data_fields.map((metric, idx) => (
            <div key={idx} style={{
              background: 'var(--canvas-surface)',
              padding: '12px',
              borderRadius: '6px',
              border: '2px solid var(--color-bullish)',
              position: 'relative'
            }}>
              <div style={{
                position: 'absolute',
                top: '4px',
                right: '4px',
                background: 'var(--color-bullish)',
                color: 'white',
                padding: '2px 6px',
                borderRadius: '4px',
                fontSize: '10px',
                fontWeight: 600
              }}>
                CALCULATED
              </div>
              <strong style={{ display: 'block', marginBottom: '8px', color: 'var(--color-bullish)', paddingRight: '70px' }}>
                {metric.field_name || metric.display_name || 'Unknown Metric'}
              </strong>
              <div style={{ fontSize: '18px', fontWeight: 700, color: 'var(--color-bullish)' }}>
                {metric.unit === '%'
                  ? `${(metric.value * 100).toFixed(2)}%`
                  : metric.unit === 'USD'
                    ? formatCurrency(metric.value)
                    : formatNumber(metric.value, 2)
                }
              </div>
              {metric.formula && (
                <div style={{ fontSize: '11px', color: 'var(--text-tertiary)', marginTop: '6px', fontStyle: 'italic' }}>
                  Formula: {metric.formula}
                </div>
              )}
              {metric.source && (
                <div style={{ fontSize: '10px', color: '#aaa', marginTop: '4px' }}>
                  Source: {metric.source}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    );
  };

  return (
    <div className="step-container">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <div>
          <h2>{t('steps.step6')}</h2>
          <p style={{ color: 'var(--text-secondary)', marginTop: '8px' }}>{t('stepDescriptions.step6')}</p>
        </div>
        <button onClick={onBackToRequirements} className="btn-secondary">
          ← Back to Requirements
        </button>
      </div>

      <div style={{ marginBottom: '20px', padding: '16px', background: 'var(--accent-primary-subtle)', borderRadius: '8px' }}>
        <p style={{ margin: 0, color: 'var(--accent-primary)' }}>
          <strong>ℹ️ About this step:</strong> This screen shows all financial data retrieved automatically from external APIs (yfinance v1.3.0 + AlphaVantage).
          Review the data below before proceeding to AI-generated assumptions.
        </p>
      </div>

      {!hasRetrievedData ? (
        <div className="summary-box" style={{ background: 'var(--color-neutral-bg)' }}>
          <h3 style={{ color: 'var(--color-neutral)' }}>⚠ {t('messages.no_data_retrieved')}</h3>
          <p>{t('messages.please_go_back')}</p>
        </div>
      ) : (
        <>
          {renderAllInputs()}
          {renderForecastDrivers()}
          {renderPeerData()}
          {renderDcfInputs()}
          {renderDupontResults()}
          {renderCompsResults()}
          {renderCalculatedMetrics()}

          <div style={{ marginTop: '20px', display: 'flex', justifyContent: 'flex-end' }}>
            <button
              onClick={onContinueToAiAssumptions}
              className="btn-next-step"
              disabled={loading}
              title="Proceed to historical data extraction (API keys managed via floating button)"
            >
              Continue to Historical Data Extraction →
            </button>
          </div>
        </>
      )}

      {/* ============================================ */}
      {/* RAW DATA DEBUG SECTION - FOR TROUBLESHOOTING */}
      {/* ============================================ */}
      <div style={{
        marginTop: '40px',
        padding: '20px',
        background: 'var(--canvas-bg)',
        borderRadius: '8px',
        color: 'var(--text-primary)',
        fontFamily: 'var(--font-mono)',
        fontSize: '11px'
      }}>
        <h3 style={{ color: 'var(--accent-primary)', marginTop: 0, borderBottom: '1px solid #455a64', paddingBottom: '10px' }}>
          🔍 RAW DATA DEBUG (Backend Response)
        </h3>
        <p style={{ color: 'var(--text-secondary)', marginBottom: '15px' }}>
          This section shows the exact data received from the backend API. Use this to debug mapping issues.
        </p>

        <details style={{ marginBottom: '15px' }}>
          <summary style={{ cursor: 'pointer', color: 'var(--accent-primary)', fontWeight: 'bold', marginBottom: '10px' }}>
            📊 Historical Data ({historicalData ? Object.keys(historicalData).length : 0} keys)
          </summary>
          <pre style={{
            background: '#1e272e',
            padding: '15px',
            borderRadius: '4px',
            overflow: 'auto',
            maxHeight: '400px',
            border: '1px solid #455a64'
          }}>
            {JSON.stringify(historicalData, null, 2)}
          </pre>
        </details>

        <details style={{ marginBottom: '15px' }}>
          <summary style={{ cursor: 'pointer', color: 'var(--accent-primary)', fontWeight: 'bold', marginBottom: '10px' }}>
            📈 Forecast Drivers ({forecastDrivers ? Object.keys(forecastDrivers).length : 0} keys)
          </summary>
          <pre style={{
            background: '#1e272e',
            padding: '15px',
            borderRadius: '4px',
            overflow: 'auto',
            maxHeight: '400px',
            border: '1px solid #455a64'
          }}>
            {JSON.stringify(forecastDrivers, null, 2)}
          </pre>
        </details>

        <details style={{ marginBottom: '15px' }}>
          <summary style={{ cursor: 'pointer', color: 'var(--accent-primary)', fontWeight: 'bold', marginBottom: '10px' }}>
            🏢 Peer Data ({peerData ? Object.keys(peerData).length : 0} keys)
          </summary>
          <pre style={{
            background: '#1e272e',
            padding: '15px',
            borderRadius: '4px',
            overflow: 'auto',
            maxHeight: '400px',
            border: '1px solid #455a64'
          }}>
            {JSON.stringify(peerData, null, 2)}
          </pre>
        </details>

        <details style={{ marginBottom: '15px' }}>
          <summary style={{ cursor: 'pointer', color: 'var(--accent-primary)', fontWeight: 'bold', marginBottom: '10px' }}>
            💰 DCF Inputs ({dcfInputs ? Object.keys(dcfInputs).length : 0} keys)
          </summary>
          <pre style={{
            background: '#1e272e',
            padding: '15px',
            borderRadius: '4px',
            overflow: 'auto',
            maxHeight: '400px',
            border: '1px solid #455a64'
          }}>
            {JSON.stringify(dcfInputs, null, 2)}
          </pre>
        </details>

        <details style={{ marginBottom: '15px' }}>
          <summary style={{ cursor: 'pointer', color: 'var(--accent-primary)', fontWeight: 'bold', marginBottom: '10px' }}>
            📐 DuPont Results ({dupontResults ? Object.keys(dupontResults).length : 0} keys)
          </summary>
          <pre style={{
            background: '#1e272e',
            padding: '15px',
            borderRadius: '4px',
            overflow: 'auto',
            maxHeight: '400px',
            border: '1px solid #455a64'
          }}>
            {JSON.stringify(dupontResults, null, 2)}
          </pre>
        </details>

        <details style={{ marginBottom: '15px' }}>
          <summary style={{ cursor: 'pointer', color: 'var(--accent-primary)', fontWeight: 'bold', marginBottom: '10px' }}>
            📊 Comps Results ({compsResults ? Object.keys(compsResults).length : 0} keys)
          </summary>
          <pre style={{
            background: '#1e272e',
            padding: '15px',
            borderRadius: '4px',
            overflow: 'auto',
            maxHeight: '400px',
            border: '1px solid #455a64'
          }}>
            {JSON.stringify(compsResults, null, 2)}
          </pre>
        </details>

        <details>
          <summary style={{ cursor: 'pointer', color: 'var(--accent-primary)', fontWeight: 'bold', marginBottom: '10px' }}>
            🧮 Calculated Metrics ({calculatedMetrics ? Object.keys(calculatedMetrics).length : 0} keys)
          </summary>
          <pre style={{
            background: '#1e272e',
            padding: '15px',
            borderRadius: '4px',
            overflow: 'auto',
            maxHeight: '400px',
            border: '1px solid #455a64'
          }}>
            {JSON.stringify(calculatedMetrics, null, 2)}
          </pre>
        </details>
      </div>

      {/* API Key management handled by floating 🔍 API Keys button */}
    </div>
  );
};

export default ApiDataStep;
