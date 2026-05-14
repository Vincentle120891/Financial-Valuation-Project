import React from 'react';
import { DataFieldDisplay } from '@/components/valuation/DataFieldDisplay';

/**
 * ApiDataStep Component
 * Step 6: Review Data Retrieved from APIs
 *
 * Features:
 * - Display historical financials retrieved from API with detailed numbers
 * - Show forecast drivers from API with period-by-period values
 * - Display peer comparison data with individual company metrics
 * - Show DCF inputs (WACC, terminal growth) from API
 * - Display DuPont analysis results with detailed ratios
 * - Show Comps analysis results with all multiples
 * - Navigate to Step 7 (AI Assumptions) or back to Step 5
 */
const ApiDataStep = ({
  historicalData,
  forecastDrivers,
  peerData,
  dcfInputs,
  dupontResults,
  compsResults,
  calculatedMetrics,
  onBackToRequirements,
  onContinueToAiAssumptions,
  loading
}) => {
  // Check if data has been retrieved - improved check to include peerData with companies
  const hasRetrievedData = historicalData?.historical_financials ||
                           (peerData && peerData.companies && peerData.companies.length > 0) ||
                           dcfInputs ||
                           dupontResults ||
                           compsResults ||
                           calculatedMetrics;

  // Comprehensive list of ALL expected inputs to display (even if missing/errors)
  const allExpectedInputs = [
    // Historical Financials - Income Statement
    { category: 'historical_financials', key: 'revenue', name: 'Total Revenue', patterns: ['Total Revenue', 'total_revenue', 'revenue'] },
    { category: 'historical_financials', key: 'cogs', name: 'Cost of Revenue (COGS)', patterns: ['COGS', 'cogs', 'Cost Of Revenue', 'cost_of_revenue'] },
    { category: 'historical_financials', key: 'gross_profit', name: 'Gross Profit', patterns: ['Gross Profit', 'gross_profit'] },
    { category: 'historical_financials', key: 'operating_expenses', name: 'Operating Expenses', patterns: ['Operating Expenses', 'operating_expenses', 'Operating Expense', 'SG&A', 'sg_and_a', 'Selling General And Administrative'] },
    { category: 'historical_financials', key: 'research_development', name: 'Research & Development', patterns: ['Research And Development', 'Research Development', 'research_development'] },
    { category: 'historical_financials', key: 'ebitda', name: 'EBITDA', patterns: ['EBITDA', 'ebitda', 'Normalized EBITDA'] },
    { category: 'historical_financials', key: 'ebit', name: 'EBIT', patterns: ['EBIT', 'ebit', 'Operating Income', 'operating_income'] },
    { category: 'historical_financials', key: 'interest_expense', name: 'Interest Expense', patterns: ['Interest Expense', 'interest_expense'] },
    { category: 'historical_financials', key: 'other_income', name: 'Other Income/Expense', patterns: ['Other Income Expense', 'Other Income Expense Net', 'other_income'] },
    { category: 'historical_financials', key: 'pretax_income', name: 'Pre-Tax Income', patterns: ['Pre-Tax Income', 'Pretax Income', 'pretax_income'] },
    { category: 'historical_financials', key: 'tax_provision', name: 'Tax Provision', patterns: ['Tax Provision', 'tax_provision', 'Income Tax'] },
    { category: 'historical_financials', key: 'net_income', name: 'Net Income', patterns: ['Net Income', 'net_income', 'netIncome'] },
    { category: 'historical_financials', key: 'depreciation', name: 'Depreciation & Amortization', patterns: ['Depreciation', 'depreciation', 'Depreciation And Amortization', 'depreciation_and_amortization', 'Depreciation Amortization Depletion'] },

    // Historical Financials - Cash Flow
    { category: 'historical_financials', key: 'capex', name: 'Capital Expenditures (CapEx)', patterns: ['CapEx', 'capex', 'Capital Expenditures', 'capital_expenditures', 'Purchase Of PPE'] },
    { category: 'historical_financials', key: 'operating_cash_flow', name: 'Operating Cash Flow', patterns: ['Operating Cash Flow', 'operating_cash_flow'] },
    { category: 'historical_financials', key: 'free_cash_flow', name: 'Free Cash Flow', patterns: ['Free Cash Flow', 'free_cash_flow', 'fcf'] },
    { category: 'historical_financials', key: 'working_capital_changes', name: 'Working Capital Changes', patterns: ['Change In Working Capital', 'working_capital_changes'] },

    // Historical Financials - Balance Sheet (Working Capital)
    { category: 'historical_financials', key: 'accounts_receivable', name: 'Accounts Receivable', patterns: ['Accounts Receivable', 'accounts_receivable', 'receivables', 'Account Receivable'] },
    { category: 'historical_financials', key: 'inventory', name: 'Inventory', patterns: ['Inventory', 'inventory', 'inventories'] },
    { category: 'historical_financials', key: 'accounts_payable', name: 'Accounts Payable', patterns: ['Accounts Payable', 'accounts_payable', 'payables', 'Account Payable'] },
    { category: 'historical_financials', key: 'cash_equivalents', name: 'Cash & Equivalents', patterns: ['Cash And Cash Equivalents', 'cash_and_cash_equivalents', 'Cash Cash Equivalents And Short Term Investments'] },

    // Historical Financials - Balance Sheet (Long-term)
    { category: 'historical_financials', key: 'total_assets', name: 'Total Assets', patterns: ['Total Assets', 'total_assets'] },
    { category: 'historical_financials', key: 'total_debt', name: 'Total Debt', patterns: ['Total Debt', 'total_debt', 'long_term_debt', 'Current Debt', 'Long Term Debt'] },
    { category: 'historical_financials', key: 'shareholders_equity', name: 'Shareholders Equity', patterns: ['Shareholders Equity', 'shareholders_equity', 'Stockholders Equity', 'Common Stock Equity'] },
    { category: 'historical_financials', key: 'retained_earnings', name: 'Retained Earnings', patterns: ['Retained Earnings', 'retained_earnings'] },
    { category: 'historical_financials', key: 'shares_outstanding', name: 'Shares Outstanding', patterns: ['Ordinary Shares Number', 'shares_outstanding', 'Shares Outstanding'] },

    // Market Data
    { category: 'market_data', key: 'current_stock_price', name: 'Current Stock Price', patterns: ['Current Stock Price', 'current_stock_price', 'currentPrice'] },
    { category: 'market_data', key: 'market_cap', name: 'Market Cap', patterns: ['Market Cap', 'market_cap', 'marketCap'] },
    { category: 'market_data', key: 'beta', name: 'Beta', patterns: ['Beta', 'beta'] },
    { category: 'market_data', key: 'risk_free_rate', name: 'Risk-Free Rate', patterns: ['Risk Free Rate', 'risk_free_rate'] },
    { category: 'market_data', key: 'equity_risk_premium', name: 'Equity Risk Premium', patterns: ['Equity Risk Premium', 'equity_risk_premium'] },

    // Balance Sheet Opening
    { category: 'balance_sheet_opening', key: 'net_debt_opening', name: 'Net Debt (Opening)', patterns: ['Net Debt Opening', 'net_debt_opening'] },
    { category: 'balance_sheet_opening', key: 'ppe_gross', name: 'PP&E (Gross)', patterns: ['PP&E Gross', 'ppe_gross', 'Net PPE'] },
    { category: 'balance_sheet_opening', key: 'accumulated_depreciation', name: 'Accumulated Depreciation', patterns: ['Accumulated Depreciation', 'accumulated_depreciation'] },

    // Peer Comparables for WACC
    { category: 'peer_comparables', key: 'peer_market_caps', name: 'Peer Market Caps', patterns: ['Peer Market Caps', 'peer_market_caps'] },
    { category: 'peer_comparables', key: 'peer_betas', name: 'Peer Betas', patterns: ['Peer Betas', 'peer_betas'] },
    { category: 'peer_comparables', key: 'peer_total_debt', name: 'Peer Total Debt', patterns: ['Peer Total Debt', 'peer_total_debt'] },
    { category: 'peer_comparables', key: 'peer_cash', name: 'Peer Cash', patterns: ['Peer Cash', 'peer_cash'] },
    { category: 'peer_comparables', key: 'peer_tax_rates', name: 'Peer Tax Rates', patterns: ['Peer Tax Rates', 'peer_tax_rates'] },
  ];

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

  // Render ALL expected inputs with clear status indicators (shows missing/errors explicitly)
  const renderAllInputs = () => {
    // Check if we have ANY data to display (historical, peer, dcf inputs, etc.)
    const hasAnyData = hasRetrievedData;

    if (!hasAnyData) {
      return (
        <div className="summary-box" style={{ background: '#ffebee', marginBottom: '20px' }}>
          <h3>⚠️ No Data Retrieved</h3>
          <p style={{ color: '#c62828' }}>Unable to display inputs. Please check if data was successfully fetched from APIs.</p>
        </div>
      );
    }

    // Group inputs by category
    const categories = [...new Set(allExpectedInputs.map(input => input.category))];

    return (
      <div style={{ marginBottom: '20px' }}>
        {categories.map(category => {
          const categoryInputs = allExpectedInputs.filter(input => input.category === category);
          const categoryTitle = category.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());

          return (
            <div key={category} className="summary-box" style={{
              background: category === 'historical_financials' ? 'linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%)' :
                         category === 'market_data' ? 'linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%)' :
                         category === 'balance_sheet_opening' ? 'linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%)' :
                         'linear-gradient(135deg, #f3e5f5 0%, #e1bee7 100%)',
              marginBottom: '20px'
            }}>
              <h3 style={{ marginBottom: '16px' }}>
                {category === 'historical_financials' && '📊 '}
                {category === 'market_data' && '📈 '}
                {category === 'balance_sheet_opening' && '📋 '}
                {category === 'peer_comparables' && '🏢 '}
                {categoryTitle}
              </h3>

              <div style={{ display: 'grid', gap: '12px' }}>
                {categoryInputs.map(input => {
                  // Get full field object from unified schema: historical_financials.{field}
                  const fieldData = historicalData?.historical_financials?.[input.key];

                  // Map backend status to frontend status format
                  const mapStatus = (backendStatus) => {
                    if (!backendStatus) return undefined;
                    if (backendStatus === 'RETRIEVED') return 'fetched';
                    if (backendStatus === 'CALCULATED') return 'calculated';
                    if (backendStatus === 'ESTIMATED') return 'estimated';
                    if (backendStatus === 'MISSING') return 'missing';
                    return undefined;
                  };

                  // Convert periods array to the format expected by DataFieldDisplay
                  const convertPeriods = (value) => {
                    if (!value) return [];
                    if (Array.isArray(value)) {
                      return value.map(pv => ({
                        period: pv.period || 'N/A',
                        value: pv.value
                      }));
                    }
                    return [];
                  };

                  // Create dataField object for DataFieldDisplay component
                  const dataField = fieldData ? {
                    value: Array.isArray(fieldData.value) ? fieldData.value[0]?.value : fieldData.value,
                    unit: fieldData.unit,
                    status: mapStatus(fieldData.status),
                    source: fieldData.source,
                    confidence: fieldData.confidence,
                    periods: convertPeriods(fieldData.value)
                  } : undefined;

                  return (
                    <DataFieldDisplay
                      key={input.key}
                      label={input.name}
                      dataField={dataField}
                    />
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
    const shareholdersEquity = historicalData.historical_financials?.shareholders_equity || getFieldValues(historicalData, 'shareholders_equity');
    const totalAssets = historicalData.historical_financials?.total_assets || getFieldValues(historicalData, 'total_assets');
    const totalDebt = historicalData.historical_financials?.total_debt || getFieldValues(historicalData, 'total_debt');
    const freeCashFlow = historicalData.historical_financials?.free_cash_flow || getFieldValues(historicalData, 'free_cash_flow');

    if (!historicalData) return null;

    return (
      <div className="summary-box" style={{ background: 'linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%)', marginBottom: '20px' }}>
        <h3>📊 Historical Financials (from API)</h3>

        {/* Revenue Table */}
        {revenue && Object.keys(revenue).length > 0 && (
          <div style={{ marginTop: '16px' }}>
            <h4 style={{ color: '#1565c0', marginBottom: '8px' }}>Revenue (3-5 years) <span style={{ background: '#4caf50', color: 'white', padding: '2px 8px', borderRadius: '4px', fontSize: '12px', marginLeft: '8px' }}>✓ Auto-Fetched</span></h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '8px' }}>
              {Object.entries(revenue).map(([year, value]) => (
                <div key={year} style={{ background: 'white', padding: '12px', borderRadius: '6px', textAlign: 'center' }}>
                  <strong style={{ display: 'block', marginBottom: '4px', color: '#666' }}>{year}</strong>
                  <span style={{ color: '#1976d2', fontWeight: 600 }}>{formatCurrency(value)}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* COGS Table */}
        {cogs && Object.keys(cogs).length > 0 && (
          <div style={{ marginTop: '16px' }}>
            <h4 style={{ color: '#1565c0', marginBottom: '8px' }}>COGS <span style={{ background: '#4caf50', color: 'white', padding: '2px 8px', borderRadius: '4px', fontSize: '12px', marginLeft: '8px' }}>✓ Auto-Fetched</span></h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '8px' }}>
              {Object.entries(cogs).map(([year, value]) => (
                <div key={year} style={{ background: 'white', padding: '12px', borderRadius: '6px', textAlign: 'center' }}>
                  <strong style={{ display: 'block', marginBottom: '4px', color: '#666' }}>{year}</strong>
                  <span style={{ color: '#ff9800', fontWeight: 600 }}>{formatCurrency(value)}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* EBITDA Table */}
        {ebitda && Object.keys(ebitda).length > 0 && (
          <div style={{ marginTop: '16px' }}>
            <h4 style={{ color: '#1565c0', marginBottom: '8px' }}>EBITDA (3-5 years) <span style={{ background: '#4caf50', color: 'white', padding: '2px 8px', borderRadius: '4px', fontSize: '12px', marginLeft: '8px' }}>✓ Auto-Fetched</span></h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '8px' }}>
              {Object.entries(ebitda).map(([year, value]) => (
                <div key={year} style={{ background: 'white', padding: '12px', borderRadius: '6px', textAlign: 'center' }}>
                  <strong style={{ display: 'block', marginBottom: '4px', color: '#666' }}>{year}</strong>
                  <span style={{ color: value >= 0 ? '#4caf50' : '#f44336', fontWeight: 600 }}>{formatCurrency(value)}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Net Income Table */}
        {netIncome && Object.keys(netIncome).length > 0 && (
          <div style={{ marginTop: '16px' }}>
            <h4 style={{ color: '#1565c0', marginBottom: '8px' }}>Net Income (3-5 years) <span style={{ background: '#4caf50', color: 'white', padding: '2px 8px', borderRadius: '4px', fontSize: '12px', marginLeft: '8px' }}>✓ Auto-Fetched</span></h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '8px' }}>
              {Object.entries(netIncome).map(([year, value]) => (
                <div key={year} style={{ background: 'white', padding: '12px', borderRadius: '6px', textAlign: 'center' }}>
                  <strong style={{ display: 'block', marginBottom: '4px', color: '#666' }}>{year}</strong>
                  <span style={{ color: value >= 0 ? '#4caf50' : '#f44336', fontWeight: 600 }}>{formatCurrency(value)}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* SG&A / OpEx Table */}
        {(operatingExpenses) && (
          <div style={{ marginTop: '16px' }}>
            <h4 style={{ color: '#1565c0', marginBottom: '8px' }}>SG&A / OpEx <span style={{ background: '#4caf50', color: 'white', padding: '2px 8px', borderRadius: '4px', fontSize: '12px', marginLeft: '8px' }}>✓ Auto-Fetched</span></h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '8px' }}>
              {Object.entries(operatingExpenses).map(([year, value]) => (
                <div key={year} style={{ background: 'white', padding: '12px', borderRadius: '6px', textAlign: 'center' }}>
                  <strong style={{ display: 'block', marginBottom: '4px', color: '#666' }}>{year}</strong>
                  <span style={{ color: '#ff9800', fontWeight: 600 }}>{formatCurrency(value)}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Depreciation & Amortization Table */}
        {depreciation && Object.keys(depreciation).length > 0 && (
          <div style={{ marginTop: '16px' }}>
            <h4 style={{ color: '#1565c0', marginBottom: '8px' }}>Depreciation & Amortization <span style={{ background: '#4caf50', color: 'white', padding: '2px 8px', borderRadius: '4px', fontSize: '12px', marginLeft: '8px' }}>✓ Auto-Fetched</span></h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '8px' }}>
              {Object.entries(depreciation).map(([year, value]) => (
                <div key={year} style={{ background: 'white', padding: '12px', borderRadius: '6px', textAlign: 'center' }}>
                  <strong style={{ display: 'block', marginBottom: '4px', color: '#666' }}>{year}</strong>
                  <span style={{ color: '#00bcd4', fontWeight: 600 }}>{formatCurrency(value)}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* CapEx Table */}
        {capex && Object.keys(capex).length > 0 && (
          <div style={{ marginTop: '16px' }}>
            <h4 style={{ color: '#1565c0', marginBottom: '8px' }}>CapEx <span style={{ background: '#4caf50', color: 'white', padding: '2px 8px', borderRadius: '4px', fontSize: '12px', marginLeft: '8px' }}>✓ Auto-Fetched</span></h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '8px' }}>
              {Object.entries(capex).map(([year, value]) => (
                <div key={year} style={{ background: 'white', padding: '12px', borderRadius: '6px', textAlign: 'center' }}>
                  <strong style={{ display: 'block', marginBottom: '4px', color: '#666' }}>{year}</strong>
                  <span style={{ color: '#9c27b0', fontWeight: 600 }}>{formatCurrency(value)}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Working Capital Items Group */}
        <div style={{ marginTop: '24px', background: 'linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%)', padding: '16px', borderRadius: '8px' }}>
          <h4 style={{ color: '#2e7d32', marginBottom: '16px' }}>Working Capital Items (AR, Inventory, AP) <span style={{ background: '#4caf50', color: 'white', padding: '2px 8px', borderRadius: '4px', fontSize: '12px', marginLeft: '8px' }}>✓ Auto-Fetched</span></h4>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
            {/* Accounts Receivable */}
            {accountsReceivable && Object.keys(accountsReceivable).length > 0 && (
              <div style={{ background: 'white', padding: '12px', borderRadius: '6px' }}>
                <strong style={{ display: 'block', marginBottom: '8px', color: '#666', fontSize: '14px' }}>Accounts Receivable</strong>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(80px, 1fr))', gap: '4px' }}>
                  {Object.entries(accountsReceivable).map(([year, value]) => (
                    <div key={year} style={{ textAlign: 'center' }}>
                      <small style={{ color: '#999', display: 'block' }}>{year}</small>
                      <span style={{ color: '#673ab7', fontWeight: 600, fontSize: '13px' }}>{formatCurrency(value)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Inventory */}
            {inventory && Object.keys(inventory).length > 0 && (
              <div style={{ background: 'white', padding: '12px', borderRadius: '6px' }}>
                <strong style={{ display: 'block', marginBottom: '8px', color: '#666', fontSize: '14px' }}>Inventory</strong>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(80px, 1fr))', gap: '4px' }}>
                  {Object.entries(inventory).map(([year, value]) => (
                    <div key={year} style={{ textAlign: 'center' }}>
                      <small style={{ color: '#999', display: 'block' }}>{year}</small>
                      <span style={{ color: '#ff5722', fontWeight: 600, fontSize: '13px' }}>{formatCurrency(value)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Accounts Payable */}
            {accountsPayable && Object.keys(accountsPayable).length > 0 && (
              <div style={{ background: 'white', padding: '12px', borderRadius: '6px' }}>
                <strong style={{ display: 'block', marginBottom: '8px', color: '#666', fontSize: '14px' }}>Accounts Payable</strong>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(80px, 1fr))', gap: '4px' }}>
                  {Object.entries(accountsPayable).map(([year, value]) => (
                    <div key={year} style={{ textAlign: 'center' }}>
                      <small style={{ color: '#999', display: 'block' }}>{year}</small>
                      <span style={{ color: '#e91e63', fontWeight: 600, fontSize: '13px' }}>{formatCurrency(value)}</span>
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
            <h4 style={{ color: '#1565c0', marginBottom: '8px' }}>Shareholders Equity <span style={{ background: '#4caf50', color: 'white', padding: '2px 8px', borderRadius: '4px', fontSize: '12px', marginLeft: '8px' }}>✓ Auto-Fetched</span></h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '8px' }}>
              {Object.entries(shareholdersEquity).map(([year, value]) => (
                <div key={year} style={{ background: 'white', padding: '12px', borderRadius: '6px', textAlign: 'center' }}>
                  <strong style={{ display: 'block', marginBottom: '4px', color: '#666' }}>{year}</strong>
                  <span style={{ color: '#00bcd4', fontWeight: 600 }}>{formatCurrency(value)}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Total Assets Table */}
        {totalAssets && Object.keys(totalAssets).length > 0 && (
          <div style={{ marginTop: '16px' }}>
            <h4 style={{ color: '#1565c0', marginBottom: '8px' }}>Total Assets <span style={{ background: '#4caf50', color: 'white', padding: '2px 8px', borderRadius: '4px', fontSize: '12px', marginLeft: '8px' }}>✓ Auto-Fetched</span></h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '8px' }}>
              {Object.entries(totalAssets).map(([year, value]) => (
                <div key={year} style={{ background: 'white', padding: '12px', borderRadius: '6px', textAlign: 'center' }}>
                  <strong style={{ display: 'block', marginBottom: '4px', color: '#666' }}>{year}</strong>
                  <span style={{ color: '#0097a7', fontWeight: 600 }}>{formatCurrency(value)}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Total Debt Table */}
        {totalDebt && Object.keys(totalDebt).length > 0 && (
          <div style={{ marginTop: '16px' }}>
            <h4 style={{ color: '#1565c0', marginBottom: '8px' }}>Total Debt <span style={{ background: '#4caf50', color: 'white', padding: '2px 8px', borderRadius: '4px', fontSize: '12px', marginLeft: '8px' }}>✓ Auto-Fetched</span></h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '8px' }}>
              {Object.entries(totalDebt).map(([year, value]) => (
                <div key={year} style={{ background: 'white', padding: '12px', borderRadius: '6px', textAlign: 'center' }}>
                  <strong style={{ display: 'block', marginBottom: '4px', color: '#666' }}>{year}</strong>
                  <span style={{ color: '#f44336', fontWeight: 600 }}>{formatCurrency(value)}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Free Cash Flow Table */}
        {freeCashFlow && Object.keys(freeCashFlow).length > 0 && (
          <div style={{ marginTop: '16px' }}>
            <h4 style={{ color: '#1565c0', marginBottom: '8px' }}>Free Cash Flow <span style={{ background: '#4caf50', color: 'white', padding: '2px 8px', borderRadius: '4px', fontSize: '12px', marginLeft: '8px' }}>✓ Auto-Fetched</span></h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '8px' }}>
              {Object.entries(freeCashFlow).map(([year, value]) => (
                <div key={year} style={{ background: 'white', padding: '12px', borderRadius: '6px', textAlign: 'center' }}>
                  <strong style={{ display: 'block', marginBottom: '4px', color: '#666' }}>{year}</strong>
                  <span style={{ color: value >= 0 ? '#4caf50' : '#f44336', fontWeight: 600 }}>{formatCurrency(value)}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Cash & Equivalents Table */}
        {historicalData.cash_and_equivalents && Object.keys(historicalData.cash_and_equivalents).length > 0 && (
          <div style={{ marginTop: '16px' }}>
            <h4 style={{ color: '#1565c0', marginBottom: '8px' }}>Cash & Equivalents <span style={{ background: '#4caf50', color: 'white', padding: '2px 8px', borderRadius: '4px', fontSize: '12px', marginLeft: '8px' }}>✓ Auto-Fetched</span></h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '8px' }}>
              {Object.entries(historicalData.cash_and_equivalents).map(([year, value]) => (
                <div key={year} style={{ background: 'white', padding: '12px', borderRadius: '6px', textAlign: 'center' }}>
                  <strong style={{ display: 'block', marginBottom: '4px', color: '#666' }}>{year}</strong>
                  <span style={{ color: '#00acc1', fontWeight: 600 }}>{formatCurrency(value)}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Summary Metrics */}
        <div style={{ marginTop: '20px', padding: '16px', background: 'white', borderRadius: '8px' }}>
          <h4 style={{ color: '#1565c0', marginBottom: '12px' }}>📊 Key Financial Metrics</h4>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '12px' }}>
            {historicalData.revenue_cagr !== undefined && (
              <div>
                <strong>Revenue CAGR:</strong>
                <p style={{ margin: '4px 0 0 0', color: '#2e7d32', fontWeight: 600 }}>
                  {(historicalData.revenue_cagr * 100).toFixed(2)}%
                </p>
              </div>
            )}
            {historicalData.avg_ebitda_margin !== undefined && (
              <div>
                <strong>Avg EBITDA Margin:</strong>
                <p style={{ margin: '4px 0 0 0', color: '#1976d2', fontWeight: 600 }}>
                  {(historicalData.avg_ebitda_margin * 100).toFixed(2)}%
                </p>
              </div>
            )}
            {historicalData.avg_roe !== undefined && (
              <div>
                <strong>Avg ROE:</strong>
                <p style={{ margin: '4px 0 0 0', color: '#7b1fa2', fontWeight: 600 }}>
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
    if (!forecastDrivers) return null;

    return (
      <div className="summary-box" style={{ background: 'linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%)', marginBottom: '20px' }}>
        <h3>📈 Forecast Drivers (from API)</h3>

        {['base_case', 'best_case', 'worst_case'].map(scenario => {
          const scenarioData = forecastDrivers[scenario];
          if (!scenarioData) return null;

          return (
            <div key={scenario} style={{ marginTop: '16px', paddingBottom: '16px', borderBottom: scenario === 'worst_case' ? 'none' : '1px solid #a5d6a7' }}>
              <h4 style={{ color: '#2e7d32', marginBottom: '12px', textTransform: 'capitalize' }}>
                {scenario.replace('_', ' ')} Scenario
              </h4>

              {/* Sales Volume Growth */}
              {scenarioData.sales_volume_growth && scenarioData.sales_volume_growth.length > 0 && (
                <div style={{ marginBottom: '12px' }}>
                  <strong style={{ display: 'block', marginBottom: '6px', color: '#555' }}>Sales Volume Growth:</strong>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                    {scenarioData.sales_volume_growth.map((value, idx) => (
                      <div key={idx} style={{ background: 'white', padding: '8px 12px', borderRadius: '4px', minWidth: '80px', textAlign: 'center' }}>
                        <span style={{ fontSize: '11px', color: '#999', display: 'block' }}>Y{idx + 1}</span>
                        <span style={{ color: '#2e7d32', fontWeight: 600 }}>{formatPercent(value)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Inflation Rate */}
              {scenarioData.inflation_rate && scenarioData.inflation_rate.length > 0 && (
                <div style={{ marginBottom: '12px' }}>
                  <strong style={{ display: 'block', marginBottom: '6px', color: '#555' }}>Inflation Rate:</strong>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                    {scenarioData.inflation_rate.map((value, idx) => (
                      <div key={idx} style={{ background: 'white', padding: '8px 12px', borderRadius: '4px', minWidth: '80px', textAlign: 'center' }}>
                        <span style={{ fontSize: '11px', color: '#999', display: 'block' }}>Y{idx + 1}</span>
                        <span style={{ color: '#2e7d32', fontWeight: 600 }}>{formatPercent(value)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* OpEx Growth */}
              {scenarioData.opex_growth && scenarioData.opex_growth.length > 0 && (
                <div style={{ marginBottom: '12px' }}>
                  <strong style={{ display: 'block', marginBottom: '6px', color: '#555' }}>OpEx Growth:</strong>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                    {scenarioData.opex_growth.map((value, idx) => (
                      <div key={idx} style={{ background: 'white', padding: '8px 12px', borderRadius: '4px', minWidth: '80px', textAlign: 'center' }}>
                        <span style={{ fontSize: '11px', color: '#999', display: 'block' }}>Y{idx + 1}</span>
                        <span style={{ color: '#2e7d32', fontWeight: 600 }}>{formatPercent(value)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Capital Expenditure */}
              {scenarioData.capital_expenditure && scenarioData.capital_expenditure.length > 0 && (
                <div style={{ marginBottom: '12px' }}>
                  <strong style={{ display: 'block', marginBottom: '6px', color: '#555' }}>Capital Expenditure (% of Revenue):</strong>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                    {scenarioData.capital_expenditure.map((value, idx) => (
                      <div key={idx} style={{ background: 'white', padding: '8px 12px', borderRadius: '4px', minWidth: '80px', textAlign: 'center' }}>
                        <span style={{ fontSize: '11px', color: '#999', display: 'block' }}>Y{idx + 1}</span>
                        <span style={{ color: '#2e7d32', fontWeight: 600 }}>{formatPercent(value)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* AR Days */}
              {scenarioData.ar_days && scenarioData.ar_days.length > 0 && (
                <div style={{ marginBottom: '12px' }}>
                  <strong style={{ display: 'block', marginBottom: '6px', color: '#555' }}>Accounts Receivable Days:</strong>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                    {scenarioData.ar_days.map((value, idx) => (
                      <div key={idx} style={{ background: 'white', padding: '8px 12px', borderRadius: '4px', minWidth: '80px', textAlign: 'center' }}>
                        <span style={{ fontSize: '11px', color: '#999', display: 'block' }}>Y{idx + 1}</span>
                        <span style={{ color: '#2e7d32', fontWeight: 600 }}>{formatNumber(value, 0)} days</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Inventory Days */}
              {scenarioData.inv_days && scenarioData.inv_days.length > 0 && (
                <div style={{ marginBottom: '12px' }}>
                  <strong style={{ display: 'block', marginBottom: '6px', color: '#555' }}>Inventory Days:</strong>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                    {scenarioData.inv_days.map((value, idx) => (
                      <div key={idx} style={{ background: 'white', padding: '8px 12px', borderRadius: '4px', minWidth: '80px', textAlign: 'center' }}>
                        <span style={{ fontSize: '11px', color: '#999', display: 'block' }}>Y{idx + 1}</span>
                        <span style={{ color: '#2e7d32', fontWeight: 600 }}>{formatNumber(value, 0)} days</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* AP Days */}
              {scenarioData.ap_days && scenarioData.ap_days.length > 0 && (
                <div style={{ marginBottom: '12px' }}>
                  <strong style={{ display: 'block', marginBottom: '6px', color: '#555' }}>Accounts Payable Days:</strong>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                    {scenarioData.ap_days.map((value, idx) => (
                      <div key={idx} style={{ background: 'white', padding: '8px 12px', borderRadius: '4px', minWidth: '80px', textAlign: 'center' }}>
                        <span style={{ fontSize: '11px', color: '#999', display: 'block' }}>Y{idx + 1}</span>
                        <span style={{ color: '#2e7d32', fontWeight: 600 }}>{formatNumber(value, 0)} days</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Tax Rate */}
              {scenarioData.tax_rate && scenarioData.tax_rate.length > 0 && (
                <div>
                  <strong style={{ display: 'block', marginBottom: '6px', color: '#555' }}>Tax Rate:</strong>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                    {scenarioData.tax_rate.map((value, idx) => (
                      <div key={idx} style={{ background: 'white', padding: '8px 12px', borderRadius: '4px', minWidth: '80px', textAlign: 'center' }}>
                        <span style={{ fontSize: '11px', color: '#999', display: 'block' }}>Y{idx + 1}</span>
                        <span style={{ color: '#2e7d32', fontWeight: 600 }}>{formatPercent(value)}</span>
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
    if (!peerData || (Array.isArray(peerData) && peerData.length === 0)) return null;

    const companies = peerData.companies || (Array.isArray(peerData) ? peerData : []);

    return (
      <div className="summary-box" style={{ background: 'linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%)', marginBottom: '20px' }}>
        <h3>🏢 Peer Comparison Data (from API)</h3>

        {/* Summary Statistics */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '12px', marginBottom: '20px' }}>
          <div style={{ background: 'white', padding: '12px', borderRadius: '6px' }}>
            <strong>Peers Found:</strong>
            <p style={{ margin: '4px 0 0 0', color: '#666' }}>
              {companies.length} companies ✓
            </p>
          </div>
          {peerData.median_ev_ebitda && (
            <div style={{ background: 'white', padding: '12px', borderRadius: '6px' }}>
              <strong>Median EV/EBITDA:</strong>
              <p style={{ margin: '4px 0 0 0', color: '#666' }}>
                {peerData.median_ev_ebitda.toFixed(1)}x ✓
              </p>
            </div>
          )}
          {peerData.median_pe && (
            <div style={{ background: 'white', padding: '12px', borderRadius: '6px' }}>
              <strong>Median P/E:</strong>
              <p style={{ margin: '4px 0 0 0', color: '#666' }}>
                {peerData.median_pe.toFixed(1)}x ✓
              </p>
            </div>
          )}
          {peerData.median_ev_revenue && (
            <div style={{ background: 'white', padding: '12px', borderRadius: '6px' }}>
              <strong>Median EV/Revenue:</strong>
              <p style={{ margin: '4px 0 0 0', color: '#666' }}>
                {peerData.median_ev_revenue.toFixed(1)}x ✓
              </p>
            </div>
          )}
          {peerData.median_pb && (
            <div style={{ background: 'white', padding: '12px', borderRadius: '6px' }}>
              <strong>Median P/B:</strong>
              <p style={{ margin: '4px 0 0 0', color: '#666' }}>
                {peerData.median_pb.toFixed(1)}x ✓
              </p>
            </div>
          )}
        </div>

        {/* Individual Company Details */}
        {companies.length > 0 && (
          <div>
            <h4 style={{ color: '#e65100', marginBottom: '12px' }}>Individual Peer Companies</h4>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
                <thead>
                  <tr style={{ background: '#fff8e1', borderBottom: '2px solid #ff9800' }}>
                    <th style={{ padding: '10px', textAlign: 'left', border: '1px solid #ffe0b2' }}>Ticker</th>
                    <th style={{ padding: '10px', textAlign: 'right', border: '1px solid #ffe0b2' }}>Market Cap</th>
                    <th style={{ padding: '10px', textAlign: 'right', border: '1px solid #ffe0b2' }}>EV/EBITDA</th>
                    <th style={{ padding: '10px', textAlign: 'right', border: '1px solid #ffe0b2' }}>P/E</th>
                    <th style={{ padding: '10px', textAlign: 'right', border: '1px solid #ffe0b2' }}>EV/Revenue</th>
                    <th style={{ padding: '10px', textAlign: 'right', border: '1px solid #ffe0b2' }}>P/B</th>
                  </tr>
                </thead>
                <tbody>
                  {companies.map((company, idx) => (
                    <tr key={idx} style={{ borderBottom: '1px solid #ffe0b2', background: idx % 2 === 0 ? 'white' : '#fff8e1' }}>
                      <td style={{ padding: '10px', fontWeight: 600, color: '#333', border: '1px solid #ffe0b2' }}>
                        {company.ticker || company.symbol || 'N/A'}
                      </td>
                      <td style={{ padding: '10px', textAlign: 'right', color: '#666', border: '1px solid #ffe0b2' }}>
                        {company.market_cap ? formatCurrency(company.market_cap) : 'N/A'}
                      </td>
                      <td style={{ padding: '10px', textAlign: 'right', color: '#666', border: '1px solid #ffe0b2' }}>
                        {company.ev_ebitda ? company.ev_ebitda.toFixed(1) + 'x' : 'N/A'}
                      </td>
                      <td style={{ padding: '10px', textAlign: 'right', color: '#666', border: '1px solid #ffe0b2' }}>
                        {company.pe_ratio ? company.pe_ratio.toFixed(1) + 'x' : 'N/A'}
                      </td>
                      <td style={{ padding: '10px', textAlign: 'right', color: '#666', border: '1px solid #ffe0b2' }}>
                        {company.ev_revenue ? company.ev_revenue.toFixed(1) + 'x' : 'N/A'}
                      </td>
                      <td style={{ padding: '10px', textAlign: 'right', color: '#666', border: '1px solid #ffe0b2' }}>
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
    if (!dcfInputs) return null;

    return (
      <div className="summary-box" style={{ background: 'linear-gradient(135deg, #f3e5f5 0%, #e1bee7 100%)', marginBottom: '20px' }}>
        <h3>💰 DCF Model Inputs (from API)</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '12px' }}>
          {dcfInputs.risk_free_rate !== undefined && (
            <div style={{ background: 'white', padding: '12px', borderRadius: '6px' }}>
              <strong>Risk-Free Rate:</strong>
              <p style={{ margin: '4px 0 0 0', color: '#666' }}>
                {(dcfInputs.risk_free_rate * 100).toFixed(2)}% ✓
              </p>
            </div>
          )}
          {dcfInputs.equity_risk_premium !== undefined && (
            <div style={{ background: 'white', padding: '12px', borderRadius: '6px' }}>
              <strong>Equity Risk Premium:</strong>
              <p style={{ margin: '4px 0 0 0', color: '#666' }}>
                {(dcfInputs.equity_risk_premium * 100).toFixed(2)}% ✓
              </p>
            </div>
          )}
          {dcfInputs.beta !== undefined && (
            <div style={{ background: 'white', padding: '12px', borderRadius: '6px' }}>
              <strong>Beta:</strong>
              <p style={{ margin: '4px 0 0 0', color: '#666' }}>
                {dcfInputs.beta.toFixed(2)} ✓
              </p>
            </div>
          )}
          {dcfInputs.cost_of_debt !== undefined && (
            <div style={{ background: 'white', padding: '12px', borderRadius: '6px' }}>
              <strong>Cost of Debt:</strong>
              <p style={{ margin: '4px 0 0 0', color: '#666' }}>
                {(dcfInputs.cost_of_debt * 100).toFixed(2)}% ✓
              </p>
            </div>
          )}
          {dcfInputs.wacc && (
            <div style={{ background: 'white', padding: '12px', borderRadius: '6px', borderLeft: '4px solid #9c27b0' }}>
              <strong>WACC (Calculated):</strong>
              <p style={{ margin: '4px 0 0 0', color: '#9c27b0', fontWeight: 600 }}>
                {(dcfInputs.wacc * 100).toFixed(2)}% ✓
              </p>
            </div>
          )}
          {dcfInputs.terminal_growth_rate && (
            <div style={{ background: 'white', padding: '12px', borderRadius: '6px' }}>
              <strong>Terminal Growth Rate:</strong>
              <p style={{ margin: '4px 0 0 0', color: '#666' }}>
                {(dcfInputs.terminal_growth_rate * 100).toFixed(2)}% ✓
              </p>
            </div>
          )}
          {dcfInputs.terminal_ebitda_multiple && (
            <div style={{ background: 'white', padding: '12px', borderRadius: '6px' }}>
              <strong>Terminal EBITDA Multiple:</strong>
              <p style={{ margin: '4px 0 0 0', color: '#666' }}>
                {dcfInputs.terminal_ebitda_multiple.toFixed(1)}x ✓
              </p>
            </div>
          )}
          {dcfInputs.useful_life_existing && (
            <div style={{ background: 'white', padding: '12px', borderRadius: '6px' }}>
              <strong>Useful Life (Existing Assets):</strong>
              <p style={{ margin: '4px 0 0 0', color: '#666' }}>
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
      <div className="summary-box" style={{ background: 'linear-gradient(135deg, #fce4ec 0%, #f8bbd9 100%)', marginBottom: '20px' }}>
        <h3>📊 DuPont Analysis Results (from API)</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '12px' }}>
          {dupontResults.net_profit_margin && (
            <div style={{ background: 'white', padding: '12px', borderRadius: '6px' }}>
              <strong>Net Profit Margin:</strong>
              <p style={{ margin: '4px 0 0 0', color: '#666' }}>
                {(dupontResults.net_profit_margin * 100).toFixed(2)}% ✓
              </p>
            </div>
          )}
          {dupontResults.asset_turnover && (
            <div style={{ background: 'white', padding: '12px', borderRadius: '6px' }}>
              <strong>Asset Turnover:</strong>
              <p style={{ margin: '4px 0 0 0', color: '#666' }}>
                {dupontResults.asset_turnover.toFixed(2)}x ✓
              </p>
            </div>
          )}
          {dupontResults.equity_multiplier && (
            <div style={{ background: 'white', padding: '12px', borderRadius: '6px' }}>
              <strong>Equity Multiplier:</strong>
              <p style={{ margin: '4px 0 0 0', color: '#666' }}>
                {dupontResults.equity_multiplier.toFixed(2)}x ✓
              </p>
            </div>
          )}
          {dupontResults.roe && (
            <div style={{ background: 'white', padding: '12px', borderRadius: '6px', borderLeft: '4px solid #e91e63' }}>
              <strong>ROE (Calculated):</strong>
              <p style={{ margin: '4px 0 0 0', color: '#e91e63', fontWeight: 600 }}>
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
      <div className="summary-box" style={{ background: 'linear-gradient(135deg, #e0f7fa 0%, #b2ebf2 100%)', marginBottom: '20px' }}>
        <h3>📈 Comps Analysis Results (from API)</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '12px' }}>
          {compsResults.ev_ebitda && (
            <div style={{ background: 'white', padding: '12px', borderRadius: '6px' }}>
              <strong>EV/EBITDA:</strong>
              <p style={{ margin: '4px 0 0 0', color: '#666' }}>
                {compsResults.ev_ebitda.toFixed(1)}x ✓
              </p>
            </div>
          )}
          {compsResults.pe_ratio && (
            <div style={{ background: 'white', padding: '12px', borderRadius: '6px' }}>
              <strong>P/E Ratio:</strong>
              <p style={{ margin: '4px 0 0 0', color: '#666' }}>
                {compsResults.pe_ratio.toFixed(1)}x ✓
              </p>
            </div>
          )}
          {compsResults.ev_revenue && (
            <div style={{ background: 'white', padding: '12px', borderRadius: '6px' }}>
              <strong>EV/Revenue:</strong>
              <p style={{ margin: '4px 0 0 0', color: '#666' }}>
                {compsResults.ev_revenue.toFixed(1)}x ✓
              </p>
            </div>
          )}
          {compsResults.pb_ratio && (
            <div style={{ background: 'white', padding: '12px', borderRadius: '6px' }}>
              <strong>P/B Ratio:</strong>
              <p style={{ margin: '4px 0 0 0', color: '#666' }}>
                {compsResults.pb_ratio.toFixed(1)}x ✓
              </p>
            </div>
          )}
          {compsResults.peg_ratio && (
            <div style={{ background: 'white', padding: '12px', borderRadius: '6px' }}>
              <strong>PEG Ratio:</strong>
              <p style={{ margin: '4px 0 0 0', color: '#666' }}>
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
      <div className="summary-box" style={{ background: 'linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%)', marginBottom: '20px' }}>
        <h3>🧮 Calculated Intermediate Metrics</h3>
        <p style={{ color: '#666', marginBottom: '16px', fontStyle: 'italic' }}>
          These metrics are automatically calculated from retrieved data (not final valuations).
        </p>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px' }}>
          {calculatedMetrics.data_fields.map((metric, idx) => (
            <div key={idx} style={{
              background: 'white',
              padding: '12px',
              borderRadius: '6px',
              border: '2px solid #4caf50',
              position: 'relative'
            }}>
              <div style={{
                position: 'absolute',
                top: '4px',
                right: '4px',
                background: '#4caf50',
                color: 'white',
                padding: '2px 6px',
                borderRadius: '4px',
                fontSize: '10px',
                fontWeight: 600
              }}>
                CALCULATED
              </div>
              <strong style={{ display: 'block', marginBottom: '8px', color: '#2e7d32', paddingRight: '70px' }}>
                {metric.field_name || metric.display_name || 'Unknown Metric'}
              </strong>
              <div style={{ fontSize: '18px', fontWeight: 700, color: '#1b5e20' }}>
                {metric.unit === '%'
                  ? `${(metric.value * 100).toFixed(2)}%`
                  : metric.unit === 'USD'
                    ? formatCurrency(metric.value)
                    : formatNumber(metric.value, 2)
                }
              </div>
              {metric.formula && (
                <div style={{ fontSize: '11px', color: '#999', marginTop: '6px', fontStyle: 'italic' }}>
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
          <h2>Step 6: Review Retrieved Financial Data</h2>
          <p style={{ color: '#666', marginTop: '8px' }}>Review all financial data fetched from yfinance and AlphaVantage APIs. Verify accuracy before proceeding.</p>
        </div>
        <button onClick={onBackToRequirements} className="btn-secondary">
          ← Back to Requirements
        </button>
      </div>

      <div style={{ marginBottom: '20px', padding: '16px', background: '#e3f2fd', borderRadius: '8px' }}>
        <p style={{ margin: 0, color: '#1565c0' }}>
          <strong>ℹ️ About this step:</strong> This screen shows all financial data retrieved automatically from external APIs (yfinance v1.3.0 + AlphaVantage).
          Review the data below before proceeding to AI-generated assumptions.
        </p>
      </div>

      {!hasRetrievedData ? (
        <div className="summary-box" style={{ background: 'linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%)' }}>
          <h3 style={{ color: '#e65100' }}>⚠ No Data Retrieved</h3>
          <p>Please go back to Step 5 and click "Retrieve Data" first.</p>
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

          <div style={{ marginTop: '20px', display: 'flex', gap: '10px' }}>
            <button
              onClick={onContinueToAiAssumptions}
              className="btn-primary"
              disabled={loading}
            >
              Continue to AI Assumptions →
            </button>
          </div>
        </>
      )}
    </div>
  );
};

export default ApiDataStep;