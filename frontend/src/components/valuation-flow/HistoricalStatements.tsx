import React, { useState } from 'react';

// ─── Format helpers ──────────────────────────────────────────────────────────

const fmtCurrency = (val: any, market?: string) => {
  if (val === null || val === undefined) return '\u2014';
  const num = Number(val);
  if (isNaN(num)) return String(val);
  const sym = market === 'vietnam' ? '\u20ab' : '$';
  if (Math.abs(num) >= 1e9) return `${sym}${(num / 1e9).toFixed(1)}B`;
  if (Math.abs(num) >= 1e6) return `${sym}${(num / 1e6).toFixed(1)}M`;
  if (Math.abs(num) >= 1e3) return `${sym}${(num / 1e3).toFixed(0)}K`;
  if (Math.abs(num) < 10) return `${sym}${num.toFixed(2)}`;
  return `${sym}${num.toLocaleString()}`;
};

const fmtPct = (val: any) => {
  if (val === null || val === undefined) return '\u2014';
  const num = Number(val);
  if (isNaN(num)) return String(val);
  return `${(num * 100).toFixed(1)}%`;
};

const fmtNum = (val: any) => {
  if (val === null || val === undefined) return '\u2014';
  const num = Number(val);
  if (isNaN(num)) return String(val);
  return num.toLocaleString(undefined, { maximumFractionDigits: 1 });
};

/** Fields that should be formatted as percentages */
const PCT_FIELDS = ['margin', 'rate', 'growth', 'yield', 'ratio', 'turnover', 'pct'];

const formatCell = (val: any, field: string, market?: string) => {
  if (val === null || val === undefined) return '\u2014';
  const num = Number(val);
  if (isNaN(num)) return String(val);
  const isPct = PCT_FIELDS.some(k => field.toLowerCase().includes(k));
  if (isPct) {
    return Math.abs(num) <= 10 ? fmtPct(num) : fmtNum(num);
  }
  if (Math.abs(num) >= 1e6) return fmtCurrency(num, market);
  return fmtNum(num);
};

// ─── Field display labels ────────────────────────────────────────────────────

const FIELD_LABELS: Record<string, string> = {
  revenue: 'Revenue',
  cost_of_revenue: 'Cost of Revenue',
  gross_profit: 'Gross Profit',
  operating_income: 'Operating Income',
  net_income: 'Net Income',
  ebitda: 'EBITDA',
  ebit: 'EBIT',
  eps_diluted: 'EPS (Diluted)',
  shares_outstanding: 'Shares Outstanding',
  total_assets: 'Total Assets',
  total_liabilities: 'Total Liabilities',
  total_equity: 'Total Equity',
  cash_and_equivalents: 'Cash & Equivalents',
  short_term_investments: 'Short-Term Investments',
  accounts_receivable: 'Accounts Receivable',
  inventory: 'Inventory',
  total_current_assets: 'Total Current Assets',
  net_ppe: 'Net PP&E',
  intangible_assets: 'Intangible Assets',
  total_current_liabilities: 'Total Current Liabilities',
  accounts_payable: 'Accounts Payable',
  short_term_debt: 'Short-Term Debt',
  long_term_debt: 'Long-Term Debt',
  total_debt: 'Total Debt',
  retained_earnings: 'Retained Earnings',
  operating_cash_flow: 'Operating Cash Flow',
  capital_expenditure: 'CapEx',
  capex: 'CapEx',
  free_cash_flow: 'Free Cash Flow',
  dividends_paid: 'Dividends Paid',
  share_buybacks: 'Share Buybacks',
  stock_buybacks: 'Stock Buybacks',
  tax_paid: 'Tax Paid',
  interest_paid: 'Interest Paid',
  debt_repayments: 'Debt Repayments',
  debt_issuance: 'Debt Issuance',
  net_borrowings: 'Net Borrowings',
  shares_issued: 'Shares Issued',
  total_revenue: 'Total Revenue',
  cost_of_goods_sold: 'COGS',
  selling_general_admin: 'SG&A',
  depreciation_amortization: 'Depreciation & Amortization',
  interest_expense: 'Interest Expense',
  income_tax_expense: 'Income Tax',
  other_operating_expenses: 'Other Operating Expenses',
};

const getFieldLabel = (field: string) => {
  if (FIELD_LABELS[field]) return FIELD_LABELS[field];
  return field.replace(/_/g, ' ').replace(/\b\w/g, (l: string) => l.toUpperCase());
};

// ─── HistoricalStatements Component ──────────────────────────────────────────

interface HistoricalStatementsProps {
  completeFinancialStatements: any;
  market?: string;
  loading?: boolean;
  sessionId?: string;
}

const HistoricalStatements: React.FC<HistoricalStatementsProps> = ({
  completeFinancialStatements: data,
  market = 'international',
  loading = false,
}) => {
  const [activeTab, setActiveTab] = useState('income_statement');

  const tabs = [
    { key: 'income_statement', icon: '\ud83d\udcc8', label: 'Income Statement' },
    { key: 'balance_sheet', icon: '\ud83c\udfe6', label: 'Balance Sheet' },
    { key: 'cash_flow', icon: '\ud83d\udcb0', label: 'Cash Flow' },
  ];

  if (loading) {
    return (
      <div style={{
        background: 'var(--canvas-surface)', border: '1px solid var(--border-default)', borderRadius: '6px',
        marginBottom: '16px', padding: '16px', textAlign: 'center',
      }}>
        <div className="loading-spinner" style={{ margin: '0 auto 12px' }} />
        <span style={{ color: 'var(--text-secondary)', fontSize: '11px' }}>Loading financial statements...</span>
      </div>
    );
  }

  if (!data || !data.periods || data.periods.length === 0) {
    return (
      <div style={{
        background: 'var(--canvas-surface)', border: '1px solid var(--border-default)', borderRadius: '6px',
        marginBottom: '16px', padding: '12px',
      }}>
        <h3 style={{ margin: 0, color: 'var(--text-secondary)', fontSize: '13px' }}>
          \ud83d\udccb Historical Financial Statements
        </h3>
        <p style={{ color: 'var(--text-tertiary)', fontSize: '11px', margin: '6px 0 0' }}>
          No financial statement data available yet. Complete earlier steps to populate this view.
        </p>
      </div>
    );
  }

  const periods: string[] = data.periods || [];
  const sectionData = data[activeTab] || {};

  // Build field order from all periods, filtering duplicate fields
  // Some fields appear under multiple names from different data sources
  const fieldSet = new Set<string>();
  // Duplicate field groups: keep only the canonical name
  const DUPLICATE_GROUPS: Record<string, string[]> = {
    // Equity: shareholders_equity and total_shareholders_equity are identical to total_equity
    total_equity: ['shareholders_equity', 'total_shareholders_equity'],
    // CapEx: capital_expenditure and capex are the same value
    capital_expenditure: ['capex'],
    // Buybacks: share_buybacks and stock_buybacks are the same value
    share_buybacks: ['stock_buybacks'],
  };
  // Build reverse lookup: dup_field → canonical_field
  const dupToCanonical = new Map<string, string>();
  for (const [canonical, dups] of Object.entries(DUPLICATE_GROUPS)) {
    for (const dup of dups) {
      dupToCanonical.set(dup, canonical);
    }
  }

  for (const p of periods) {
    const pData = sectionData[p] || {};
    for (const k of Object.keys(pData)) {
      const canonical = dupToCanonical.get(k);
      if (canonical) {
        // This is a duplicate field — skip if canonical already added
        if (fieldSet.has(canonical)) continue;
        // If canonical not yet added but this dup has data, add canonical instead
        fieldSet.add(canonical);
        // Remove any other dups of same group that were added before canonical
        for (const [c, dups] of Object.entries(DUPLICATE_GROUPS)) {
          if (c === canonical) {
            for (const d of dups) fieldSet.delete(d);
          }
        }
      } else {
        // Check if this field IS a canonical that has duplicates already added
        if (DUPLICATE_GROUPS[k]) {
          for (const dup of DUPLICATE_GROUPS[k]) fieldSet.delete(dup);
        }
        fieldSet.add(k);
      }
    }
  }
  const fieldOrder = Array.from(fieldSet);

  return (
    <div style={{
      background: 'var(--canvas-surface)', border: '1px solid var(--border-default)', borderRadius: '6px',
      marginBottom: '16px', overflow: 'hidden',
    }}>
      {/* Header */}
      <div style={{
        background: 'var(--canvas-surface-elevated)', padding: '8px 12px',
        borderBottom: '1px solid var(--border-default)',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      }}>
        <h3 style={{ margin: 0, color: 'var(--accent-primary)', fontSize: '13px', fontWeight: 700 }}>
          \ud83d\udccb Historical Financial Statements
        </h3>
        <span style={{ color: 'var(--text-tertiary)', fontSize: '10px' }}>
          {periods.length} periods
          {data.completeness && (
            <>{' \u2014 '}
              {Object.entries(data.completeness).map(([s, pct]: [string, any]) =>
                `${s}: ${Math.round((pct || 0) * 100)}%`
              ).join(' | ')}
            </>
          )}
        </span>
      </div>

      {/* Tab bar */}
      <div style={{ display: 'flex', gap: 0, borderBottom: '1px solid var(--border-default)', background: 'var(--canvas-bg)' }}>
        {tabs.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            style={{
              padding: '8px 16px', border: 'none',
              borderBottom: activeTab === tab.key ? '2px solid var(--accent-primary)' : '2px solid transparent',
              cursor: 'pointer',
              background: activeTab === tab.key ? 'var(--accent-primary-subtle)' : 'transparent',
              color: activeTab === tab.key ? 'var(--accent-primary)' : 'var(--text-tertiary)',
              fontSize: '11px',
              fontWeight: activeTab === tab.key ? 700 : 500,
            }}
          >
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      {/* Table */}
      <div style={{ overflowX: 'auto', maxHeight: '500px' }}>
        <table style={{
          width: '100%', borderCollapse: 'collapse', fontSize: '12px',
          fontFamily: 'var(--font-mono)',
        }}>
          <thead>
            <tr>
              <th style={{
                textAlign: 'left', padding: '6px 10px', borderBottom: '2px solid var(--border-default)',
                background: 'var(--canvas-surface-elevated)', color: 'var(--text-tertiary)', position: 'sticky', top: 0, zIndex: 1,
                fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.05em',
              }}>
                Field
              </th>
              {periods.map(p => (
                <th key={p} style={{
                  textAlign: 'right', padding: '6px 10px', borderBottom: '2px solid var(--border-default)',
                  background: 'var(--canvas-surface-elevated)', color: 'var(--text-tertiary)', position: 'sticky', top: 0, zIndex: 1,
                  fontSize: '10px', fontWeight: 700,
                }}>
                  {p.length > 4 ? p.slice(0, 7) : p}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {fieldOrder.map((field, idx) => (
              <tr key={field} style={{
                background: idx % 2 === 0 ? 'transparent' : 'var(--border-subtle)',
              }}>
                <td style={{
                  padding: '5px 10px', borderBottom: '1px solid var(--border-default)',
                  color: 'var(--text-primary)', fontWeight: 600, whiteSpace: 'nowrap',
                  position: 'sticky', left: 0, background: idx % 2 === 0 ? 'var(--canvas-surface)' : 'var(--canvas-surface-elevated)',
                  zIndex: 1, fontSize: '10px',
                }}>
                  {getFieldLabel(field)}
                </td>
                {periods.map(p => {
                  const val = sectionData[p]?.[field];
                  const display = formatCell(val, field, market);
                  const isMissing = val === null || val === undefined;
                  return (
                    <td key={p} style={{
                      textAlign: 'right', padding: '5px 10px', borderBottom: '1px solid var(--border-default)',
                      color: isMissing ? 'var(--text-tertiary)' : 'var(--text-primary)',
                      fontWeight: isMissing ? 400 : 500,
                      fontVariantNumeric: 'tabular-nums',
                    }}>
                      {display}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Data completeness footer */}
      {data.completeness && (
        <div style={{
          padding: '6px 12px', borderTop: '1px solid var(--border-default)',
          fontSize: '9px', color: 'var(--text-tertiary)', display: 'flex', gap: '10px', flexWrap: 'wrap',
        }}>
          {Object.entries(data.completeness).map(([section, pct]: [string, any]) => (
            <span key={section}>
              {section.replace(/_/g, ' ')}: {Math.round((pct || 0) * 100)}%
            </span>
          ))}
        </div>
      )}
    </div>
  );
};

export default HistoricalStatements;
