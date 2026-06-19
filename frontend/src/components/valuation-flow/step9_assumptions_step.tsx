import React, { useState, useMemo, useCallback, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import {
  validateDCFInputs,
  DCFInputs,
  DCFOutput,
} from '../../utils/dcf_types';
import { calculateBuildingBlocks } from '../../services/api';
import useValuationStore from '../../store/useValuationStore';
import { extractHistoricalActuals, HistoricalActuals } from '../../utils/historicalDataExtractor';
import { Tooltip, TooltipTrigger, TooltipContent, TooltipProvider } from '../ui/tooltip';

// ─── Backend → Frontend Data Transformation ──────────────────────────────────

/**
 * Transform backend BuildingBlockOutput.to_dict() (snake_case) to frontend DCFOutput shape (camelCase).
 * This allows the existing display components to render backend-calculated results without changes.
 */
/**
 * Transform backend BuildingBlockOutput.to_dict() (snake_case) to frontend DCFOutput (camelCase).
 * Field names now match backend dataclass names exactly — only case conversion needed.
 * No semantic renaming — the frontend types are now 1:1 with backend.
 */
function transformBackendToFrontend(data: any): DCFOutput {
  const sched = data?.supporting_schedules || {};
  const is = sched.income_statement || {};
  const wc = sched.working_capital || {};
  const dep = sched.depreciation || {};
  const tl = sched.tax_levered || {};
  const tu = sched.tax_unlevered || {};
  const cfs = data?.cash_flow_statement || {};
  const bs = data?.balance_sheet || {};
  const wacc = data?.wacc_calculation || {};
  const intSched = data?.interest_schedule || {};
  const histRefs = data?.historical_references || {};
  const fullWc = data?.full_working_capital || {};
  const metadata = data?.metadata || {};

  const years = is.years || ['FY1', 'FY2', 'FY3', 'FY4', 'FY5', 'Terminal'];

  return {
    incomeStatement: {
      years,
      revenue: is.revenue || [],
      cogs: is.cogs || [],
      grossProfit: is.gross_profit || [],
      sga: is.sga || [],
      rd: is.rd || [],
      otherOpex: is.other_opex || [],
      ebitda: is.ebitda || [],
      depreciation: is.depreciation || [],
      ebit: is.ebit || [],
      otherIncomeExpense: is.other_income_expense || [],
      interestExpense: is.interest_expense || [],
      ebt: is.ebt || [],
      currentTax: is.current_tax || [],
      deferredTax: is.deferred_tax || [],
      totalTax: is.total_tax || [],
      netIncome: is.net_income || [],
    },
    workingCapital: {
      years: wc.years || years,
      arBalance: wc.ar_balance || [],
      inventoryBalance: wc.inventory_balance || [],
      apBalance: wc.ap_balance || [],
      nwc: wc.nwc || [],
      changeInNwc: wc.change_in_nwc || [],
      arDays: wc.ar_days || [],
      invDays: wc.inv_days || [],
      apDays: wc.ap_days || [],
    },
    depreciation: {
      years: dep.years || years,
      capex: dep.capex || [],
      existingAssetDep: dep.existing_asset_dep || [],
      newAssetDep: dep.new_asset_dep || [],
      totalDepreciation: dep.total_depreciation || [],
      grossPpeEnding: dep.gross_ppe_ending || [],
      taxBasisEnding: dep.tax_basis_ending || [],
      taxDepreciation: dep.tax_depreciation || [],
    },
    taxLevered: {
      years: tl.years || years,
      ebtEbit: tl.ebt_ebit || tl.ebt || [],
      accountingDep: tl.accounting_dep || [],
      taxDep: tl.tax_dep || [],
      ebtAdjusted: tl.ebt_adjusted || [],
      nolOpening: tl.nol_opening || [],
      nolNew: tl.nol_new || [],
      nolUsed: tl.nol_used || [],
      nolEnding: tl.nol_ending || [],
      taxableIncome: tl.taxable_income || [],
      currentTax: tl.current_tax || [],
      totalTax: tl.total_tax || [],
      deferredTax: tl.deferred_tax || [],
    },
    taxUnlevered: {
      years: tu.years || years,
      ebtEbit: tu.ebt_ebit || tu.ebit || [],
      accountingDep: (tu.accounting_dep && tu.accounting_dep.length > 0) ? tu.accounting_dep : (tl.accounting_dep || []),
      taxDep: (tu.tax_dep && tu.tax_dep.length > 0) ? tu.tax_dep : (tl.tax_dep || []),
      ebtAdjusted: (tu.ebt_adjusted && tu.ebt_adjusted.length > 0) ? tu.ebt_adjusted : (tl.ebt_adjusted || []),
      nolOpening: (tu.nol_opening && tu.nol_opening.length > 0) ? tu.nol_opening : (tl.nol_opening || []),
      nolNew: (tu.nol_new && tu.nol_new.length > 0) ? tu.nol_new : (tl.nol_new || []),
      nolUsed: (tu.nol_used && tu.nol_used.length > 0) ? tu.nol_used : (tl.nol_used || []),
      nolEnding: (tu.nol_ending && tu.nol_ending.length > 0) ? tu.nol_ending : (tl.nol_ending || []),
      taxableIncome: (tu.taxable_income && tu.taxable_income.length > 0) ? tu.taxable_income : (tl.taxable_income || []),
      currentTax: tu.current_tax || [],
      totalTax: tu.total_tax || [],
      deferredTax: (tu.deferred_tax && tu.deferred_tax.length > 0) ? tu.deferred_tax : (tl.deferred_tax || []),
    },
    cashFlowStatement: {
      years: cfs.years || years,
      netIncome: cfs.net_income || [],
      deferredTaxes: cfs.deferred_taxes || [],
      depreciation: cfs.depreciation || [],
      cashFromAr: cfs.cash_from_ar || [],
      cashFromInventory: cfs.cash_from_inventory || [],
      cashFromAp: cfs.cash_from_ap || [],
      subtotalCfo: cfs.subtotal_cfo || [],
      capitalExpenditure: cfs.capital_expenditure || [],
      subtotalCfi: cfs.subtotal_cfi || [],
      changeInLtDebt: cfs.change_in_lt_debt || [],
      changeInCommonEquity: cfs.change_in_common_equity || [],
      dividends: cfs.dividends || [],
      revolvingCredit: cfs.revolving_credit || [],
      subtotalCff: cfs.subtotal_cff || [],
      beginningCash: cfs.beginning_cash || [],
      increaseDecrease: cfs.increase_decrease || [],
      endingCash: cfs.ending_cash || [],
    },
    balanceSheet: {
      years: bs.years || years,
      cash: bs.cash || [],
      accountsReceivable: bs.accounts_receivable || [],
      inventories: bs.inventories || [],
      otherShortTermInvestments: bs.other_short_term_investments || [],
      otherCurrentAssets: bs.other_current_assets || [],
      nonCurrentMarketableSecurities: bs.non_current_marketable_securities || [],
      otherNonCurrentAssets: bs.other_non_current_assets || [],
      nonCurrentDeferredAssets: bs.non_current_deferred_assets || [],
      totalCurrentAssets: bs.total_current_assets || [],
      ppeGross: bs.ppe_gross || [],
      accumulatedDepreciation: bs.accumulated_depreciation || [],
      ppeNet: bs.ppe_net || [],
      investmentsAndAdvances: bs.investments_and_advances || [],
      totalAssets: bs.total_assets || [],
      accountsPayable: bs.accounts_payable || [],
      currentAccruedExpenses: bs.current_accrued_expenses || [],
      currentDeferredLiabilities: bs.current_deferred_liabilities || [],
      otherCurrentLiabilities: bs.other_current_liabilities || [],
      currentDebt: bs.current_debt || [],
      revolvingCredit: bs.revolving_credit || [],
      totalCurrentLiabilities: bs.total_current_liabilities || [],
      tradeAndOtherPayablesNonCurrent: bs.trade_and_other_payables_non_current || [],
      deferredTaxLiabilities: bs.deferred_tax_liabilities || [],
      otherNonCurrentLiabilities: bs.other_non_current_liabilities || [],
      longTermDebt: bs.long_term_debt || [],
      totalLiabilities: bs.total_liabilities || [],
      commonStock: bs.common_stock || [],
      commonEquity: bs.common_equity || [],
      retainedEarnings: bs.retained_earnings || [],
      otherEquityAdjustments: bs.other_equity_adjustments || [],
      totalShareholdersEquity: bs.total_shareholders_equity || [],
      totalLiabilitiesEquity: bs.total_liabilities_equity || [],
      balanceCheck: bs.balance_check || [],
    },
    dcfPerpetuity: {
      fairValuePerShare: 0,
      enterpriseValue: 0,
      equityValue: 0,
      impliedPremium: 0,
    },
    dcfExitMultiple: {
      fairValuePerShare: 0,
      enterpriseValue: 0,
      equityValue: 0,
      impliedPremium: 0,
    },
    wacc: {
      wacc: wacc.wacc || 0,
      avgUnleveredBeta: wacc.avg_unlevered_beta || 0,
      leveredBeta: wacc.levered_beta || 0,
      costOfEquity: wacc.cost_of_equity || 0,
      afterTaxCostOfDebt: wacc.after_tax_cost_of_debt || 0,
    },
    // Full-period schedules from backend
    interestSchedule: intSched.years ? {
      years: intSched.years,
      ltInterestHistorical: intSched.lt_interest_historical || [],
      totalInterestExpenseHistorical: intSched.total_interest_expense_historical || [],
      interestIncomeHistorical: intSched.interest_income_historical || [],
      openingCash: intSched.opening_cash || [],
      cashInterestRate: intSched.cash_interest_rate || [],
      cashInterestIncome: intSched.cash_interest_income || [],
      ltDebtBalance: intSched.lt_debt_balance || [],
      ltDebtInterestRate: intSched.lt_debt_interest_rate || [],
      ltDebtInterestExpense: intSched.lt_debt_interest_expense || [],
      revolvingCreditBalance: intSched.revolving_credit_balance || [],
      revolvingCreditRate: intSched.revolving_credit_rate || [],
      revolvingInterestExpense: intSched.revolving_interest_expense || [],
      netInterestExpense: intSched.net_interest_expense || [],
      totalInterestExpense: intSched.total_interest_expense || [],
    } : undefined,
    historicalReferences: histRefs.years ? {
      years: histRefs.years,
      interestIncome: histRefs.interest_income || [],
      researchDevelopment: histRefs.research_development || [],
      otherIncomeExpense: histRefs.other_income_expense || [],
      taxPaid: histRefs.tax_paid || [],
      interestPaid: histRefs.interest_paid || [],
      shareBuybacks: histRefs.share_buybacks || [],
      debtIssuance: histRefs.debt_issuance || [],
      debtRepayments: histRefs.debt_repayments || [],
      dividendsPaid: histRefs.dividends_paid || [],
    } : undefined,
    fullWorkingCapital: fullWc.years ? {
      years: fullWc.years,
      arBalance: fullWc.ar_balance || [],
      inventoryBalance: fullWc.inventory_balance || [],
      apBalance: fullWc.ap_balance || [],
      nwc: fullWc.nwc || [],
      changeInNwc: fullWc.change_in_nwc || [],
      arDays: fullWc.ar_days || [],
      invDays: fullWc.inv_days || [],
      apDays: fullWc.ap_days || [],
    } : undefined,
    historicalYears: metadata.historical_years || [],
    forecastYears: metadata.forecast_years || [],
    allYears: metadata.all_years || [],
  } as unknown as DCFOutput;
}

// ─── Types ──────────────────────────────────────────────────────────────────

interface AssumptionsStepProps {
  forecastDrivers: any;
  dcfInputs: any;
  completeFinancialStatements: any;
  peerWaccData: any;
  marketData: any;
  selectedCompany?: any;
  ticker: string;
  companyName: string;
  currentPrice: number;
  selectedModel: string;
  selectedScenario: string;
  confirmedValues: Record<string, { value: any; source: string }>;
  onManualInput: (field: string, value: any) => void;
  onConfirmAssumptions: () => Promise<void>;
  onBackToForecastDrivers: () => void;
  loading: boolean;

  // Legacy props for backward compatibility
  historicalData?: any;
  peerData?: any;
  aiData?: any;
  aiError?: any;
  onUseAI?: (field: string, value: any) => void;
}

// ─── Percentage Normalization ────────────────────────────────────────────────

/**
 * Normalize a value that should be a decimal fraction (0-1) for percentage fields.
 * Some upstream data stores percentages as whole numbers (e.g., 456 for 4.56%)
 * instead of decimals (0.0456). This function detects and fixes that.
 */
function normalizeDecimal(value: number, min: number = 0, max: number = 1): number {
  if (value === null || value === undefined || isNaN(value)) return min;
  // If value is clearly outside decimal range (e.g., > max for a rate), normalize
  if (value > max && value <= max * 100) {
    return value / 100;
  }
  // If value is way outside range (e.g., 456 for risk-free rate), divide by 100
  if (value > max * 100) {
    return value / 10000; // Handle basis-point-like values
  }
  return value;
}

// ─── Period Labels (dynamic from data) ──────────────────────────────────────

const DEFAULT_HIST = ['FY2020', 'FY2021', 'FY2022'];
const DEFAULT_FC = ['FY2023', 'FY2024', 'FY2025', 'FY2026', 'FY2027'];

/**
 * Derive period labels from actual historical data periods.
 * Falls back to defaults if no periods found.
 */
function derivePeriods(
  historicalPeriods: string[] | undefined,
  forecastYears: number = 5,
): { histPeriods: string[]; fcPeriods: string[]; allPeriods: string[] } {
  let histPeriods: string[] = [];
  let lastHistoricalYear = 2022;

  if (historicalPeriods && historicalPeriods.length > 0) {
    // Show ALL available historical periods with their actual labels
    histPeriods = historicalPeriods.map(p => {
      // Extract 4-digit year from various formats: "2025-09-30", "2025-09", "FY2025", "2025"
      const yearMatch = p.match(/(\d{4})/);
      const year = yearMatch ? yearMatch[1] : null;
      // Try to extract month (MM) — look for pattern like "-09" or "-09-30"
      const monthMatch = p.match(/-(\d{2})(?:-\d{2})?$/);
      const month = monthMatch ? monthMatch[1] : null;
      if (year && month) return `${year}-${month}`; // e.g., "2025-09"
      if (year) return year; // e.g., "2025"
      return p;
    });
    // Extract last year from the first 4 digits of the last period
    const lastMatch = histPeriods[histPeriods.length - 1]?.match(/(\d{4})/);
    lastHistoricalYear = lastMatch ? parseInt(lastMatch[1], 10) : 2022;
  } else {
    histPeriods = DEFAULT_HIST;
  }

  const fcPeriods: string[] = [];
  for (let i = 1; i <= forecastYears; i++) {
    fcPeriods.push(`${lastHistoricalYear + i}`);
  }
  fcPeriods.push('Term');

  const allPeriods = [...histPeriods, ...fcPeriods];
  return { histPeriods, fcPeriods, allPeriods };
}

// ─── Editable Input Field ───────────────────────────────────────────────────

const EditableField: React.FC<{
  label: string;
  value: number;
  onChange: (val: number) => void;
  type?: 'number' | 'percent';
  min?: number;
  max?: number;
  warning?: string;
  disabled?: boolean;
  isDefault?: boolean;  // true if value is a default/fallback (not from Step 8 data)
}> = ({ label, value, onChange, type = 'number', min, max, warning, disabled, isDefault }) => {
  const displayValue = type === 'percent' ? (value * 100).toFixed(1) : value.toFixed(2);
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const raw = parseFloat(e.target.value);
    if (isNaN(raw)) return;
    const val = type === 'percent' ? raw / 100 : raw;
    onChange(val);
  };

  const [localValue, setLocalValue] = useState(
    type === 'percent' ? (value * 100).toFixed(1) : value.toFixed(2)
  );

  // Sync local value when external value changes (e.g., from recalculation)
  useEffect(() => {
    setLocalValue(type === 'percent' ? (value * 100).toFixed(1) : value.toFixed(2));
  }, [value, type]);

  const handleLocalChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setLocalValue(e.target.value);
  };

  const commitValue = () => {
    const raw = parseFloat(localValue);
    if (isNaN(raw)) {
      // Reset to current value on invalid input
      setLocalValue(type === 'percent' ? (value * 100).toFixed(1) : value.toFixed(2));
      return;
    }
    const val = type === 'percent' ? raw / 100 : raw;
    onChange(val);
  };

  return (
    <div className="flex flex-col gap-0.5">
      <label className="text-[10px] text-[var(--text-tertiary)] uppercase tracking-wide flex items-center gap-1">
        {label}
        {isDefault && (
          <span className="text-[8px] px-1 py-0 rounded bg-[var(--color-neutral-bg)] text-[var(--color-neutral)] border border-[var(--color-neutral)]" title="Default value — not from Step 8 data">
            DEFAULT
          </span>
        )}
      </label>
      <input
        type="number"
        value={localValue}
        onChange={handleLocalChange}
        onBlur={commitValue}
        onKeyDown={(e) => { if (e.key === 'Enter') { commitValue(); (e.target as HTMLInputElement).blur(); } }}
        step={type === 'percent' ? '0.1' : '0.01'}
        disabled={disabled}
        className={`w-full bg-[var(--canvas-surface-elevated)] border rounded px-2 py-1 text-xs font-mono text-[var(--text-primary)]
          ${isDefault ? 'border-amber-600/70 bg-amber-900/20' : warning ? 'border-amber-500' : 'border-[var(--border-default)]'}
          ${disabled ? 'opacity-50' : 'hover:border-blue-400 focus:border-blue-400 focus:outline-none'}`}
      />
      {(warning || isDefault) && (
        <span className="text-[9px]">
          {warning && <span className="text-[var(--color-neutral)]">{warning}</span>}
          {!warning && isDefault && <span className="text-[var(--color-neutral)]/70">⚠ default value</span>}
        </span>
      )}
    </div>
  );
};

// ─── Historical vs Calculated Threshold ─────────────────────────────────────

/**
 * Determine whether to show a calculated value below the historical actual.
 * Only shows when difference > 1 AND > 1% of the value.
 */
const showCalcDiff = (actual: number | undefined, calc: number | undefined): boolean => {
  if (calc == null || actual == null || isNaN(calc) || isNaN(actual)) return false;
  const diff = Math.abs(actual - calc);
  if (diff <= 1) return false;
  const pctDiff = diff / Math.max(Math.abs(actual), 1);
  return pctDiff > 0.01;
};

// ─── Schedule Table ─────────────────────────────────────────────────────────

const ScheduleTable: React.FC<{
  title: string;
  headers: string[];
  rows: { label: string; values: number[]; calculatedValues?: (number | null)[]; isHighlight?: boolean; isReference?: boolean; formula?: string; fieldId?: string }[];
  columnFilter?: number[];
  defaultExpanded?: boolean;
  onRecalculate?: () => void;
  histLen?: number;
  selectedFieldId?: string | null;
  upstreamFields?: Set<string>;
  downstreamFields?: Set<string>;
  onFieldClick?: (fieldId: string) => void;
}> = ({ title, headers, rows, columnFilter, defaultExpanded = false, onRecalculate, histLen, selectedFieldId, upstreamFields, downstreamFields, onFieldClick }) => {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [tableWidth, setTableWidth] = useState<number | null>(null);
  const resizeRef = useRef<HTMLDivElement>(null);
  const isDragging = useRef(false);
  const dragStartX = useRef(0);
  const dragStartWidth = useRef(0);

  const visibleIndices = columnFilter || headers.map((_, i) => i);
  const visibleHeaders = visibleIndices.map(i => headers[i]);

  // Auto-expand if any row is highlighted
  const hasHighlight = selectedFieldId && (upstreamFields?.size || downstreamFields?.size);

  // ── Resize handle logic ────────────────────────────────────────────────────
  const handleResizeMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    isDragging.current = true;
    dragStartX.current = e.clientX;
    dragStartWidth.current = resizeRef.current?.parentElement?.getBoundingClientRect().width ?? 600;

    const onMouseMove = (ev: MouseEvent) => {
      if (!isDragging.current) return;
      const delta = ev.clientX - dragStartX.current;
      const newWidth = Math.max(400, Math.min(window.innerWidth - 40, dragStartWidth.current + delta));
      setTableWidth(newWidth);
    };

    const onMouseUp = () => {
      isDragging.current = false;
      document.removeEventListener('mousemove', onMouseMove);
      document.removeEventListener('mouseup', onMouseUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };

    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', onMouseUp);
  }, []);

  // Reset width when exiting fullscreen
  const exitFullscreen = useCallback(() => {
    setIsFullscreen(false);
    setTableWidth(null);
  }, []);

  // ── Shared table content ───────────────────────────────────────────────────
  const tableContent = (
    <TooltipProvider>
    <div className="overflow-x-auto" style={{ overflow: 'clip' }}>
      <table className="w-full text-xs font-mono" style={tableWidth ? { minWidth: tableWidth } : undefined}>
        <thead className="sticky top-0 z-10">
          <tr className="bg-[var(--canvas-surface-elevated)]">
            <th className="text-left px-2 py-1.5 text-[var(--text-tertiary)] sticky left-0 bg-[var(--canvas-surface-elevated)]" style={{ minWidth: 160, maxWidth: 200, zIndex: 0 }}>Item</th>
            {visibleHeaders.map((h, i) => {
              const origIdx = (columnFilter ? columnFilter[i] : i) ?? i;
              const isHistorical = histLen !== undefined && origIdx < histLen;
              return (
                <th key={i} className={`text-right px-2 py-1.5 ${isHistorical ? 'text-[var(--accent-primary)]' : 'text-[var(--text-tertiary)]'}`}>{h}</th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, ri) => {
            const isSelected = row.fieldId && row.fieldId === selectedFieldId;
            const isUpstream = row.fieldId && upstreamFields?.has(row.fieldId);
            const isDownstream = row.fieldId && downstreamFields?.has(row.fieldId);
            const hasConnection = isSelected || isUpstream || isDownstream;

            // Determine row background color based on highlight state
            let rowBg = '';
            if (isSelected) rowBg = 'bg-[var(--accent-primary-subtle)]';
            else if (isUpstream) rowBg = 'bg-[var(--color-bullish-bg)]';
            else if (isDownstream) rowBg = 'bg-[var(--color-neutral-bg)]';
            else if (row.isReference) rowBg = 'bg-[var(--border-subtle)]';
            else if (row.isHighlight) rowBg = 'bg-[var(--accent-primary-subtle)]';

            // Determine label color
            let labelColor = row.isReference ? 'text-[var(--text-tertiary)] italic' : 'text-[var(--text-primary)]';
            if (isSelected) labelColor = 'text-[var(--accent-primary)] font-bold';
            else if (isUpstream) labelColor = 'text-[var(--color-bullish)]';
            else if (isDownstream) labelColor = 'text-[var(--color-neutral)]';

            return (
            <tr key={ri} className={`border-t border-[var(--border-default)] ${rowBg} ${row.fieldId ? 'cursor-pointer hover:bg-[var(--border-subtle)]' : ''}`}
                onClick={() => row.fieldId && onFieldClick?.(row.fieldId)}>
              <td className={`px-2 py-1 sticky left-0 bg-[var(--canvas-surface)] ${labelColor}`} style={{ minWidth: 160, maxWidth: 200, zIndex: 0 }}>
                <span className="flex items-center gap-1">
                  {/* Connection indicator */}
                  {isSelected && <span className="text-[8px] text-[var(--accent-primary)]">●</span>}
                  {isUpstream && <span className="text-[8px] text-[var(--color-bullish)]">◀</span>}
                  {isDownstream && <span className="text-[8px] text-[var(--color-neutral)]">▶</span>}
                  {row.label}
                  {row.formula && (
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <span className="inline-flex items-center justify-center w-3.5 h-3.5 rounded-full bg-[var(--border-strong)] hover:bg-[var(--border-default)] text-[8px] text-[var(--text-secondary)] cursor-help select-none flex-shrink-0">?</span>
                      </TooltipTrigger>
                      <TooltipContent side="right" className="max-w-xs text-[10px] leading-tight">
                        <div className="font-semibold text-[var(--accent-primary)] mb-0.5">{row.label}</div>
                        <div className="text-[var(--text-secondary)]">{row.formula}</div>
                      </TooltipContent>
                    </Tooltip>
                  )}
                </span>
              </td>
              {visibleIndices.map((idx, ci) => {
                const isHistorical = histLen !== undefined && idx < histLen;
                let valueColor = row.isReference ? 'text-[var(--text-tertiary)] italic' : isHistorical ? 'text-[var(--accent-primary)]' : 'text-[var(--text-primary)]';
                if (isSelected) valueColor = 'text-[var(--accent-primary)] font-bold';
                else if (isUpstream) valueColor = 'text-[var(--color-bullish)]';
                else if (isDownstream) valueColor = 'text-[var(--color-neutral)]';
                return (
                <td key={ci} className={`text-right px-2 py-1 tabular-nums ${valueColor}`}>
                  <div>{row.values[idx] !== undefined ? row.values[idx].toLocaleString(undefined, { maximumFractionDigits: 0 }) : '—'}</div>
                  {isHistorical && row.calculatedValues?.[idx] != null && (
                    <div className="text-[8px] text-[var(--color-bearish)]">
                      Calc: {row.calculatedValues[idx].toLocaleString(undefined, { maximumFractionDigits: 0 })}
                    </div>
                  )}
                </td>
                );
              })}
            </tr>
            );
          })}
        </tbody>
      </table>
    </div>
    </TooltipProvider>
  );

  // ── Title bar with action buttons ──────────────────────────────────────────
  const titleBar = (
    <div
      onClick={() => !isFullscreen && setExpanded(!expanded)}
      className={`w-full flex items-center justify-between px-3 py-2 bg-[var(--canvas-surface-elevated)] hover:bg-[var(--border-subtle)] text-xs font-semibold text-[var(--text-primary)] ${isFullscreen ? '' : 'cursor-pointer'}`}
    >
      <span>{title}</span>
      <div className="flex items-center gap-1.5">
        {onRecalculate && (
          <button
            onClick={(e) => { e.stopPropagation(); onRecalculate(); }}
            className="text-[9px] bg-[var(--accent-primary)] hover:bg-[var(--accent-primary-hover)] text-[var(--text-primary)] px-2 py-0.5 rounded"
          >
            🔄 Calculate
          </button>
        )}
        {/* Expand / collapse toggle */}
        <button
          onClick={(e) => {
            e.stopPropagation();
            if (isFullscreen) exitFullscreen();
            else setIsFullscreen(true);
          }}
          title={isFullscreen ? 'Exit fullscreen' : 'Expand to fullscreen'}
          className="w-7 h-7 flex items-center justify-center rounded border border-[var(--border-strong)] hover:bg-[var(--accent-primary-subtle)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] text-base font-bold"
        >
          {isFullscreen ? '✕' : '⊞'}
        </button>
        {!isFullscreen && (
          <span className="text-[var(--text-tertiary)] text-[10px]">{expanded ? '▼' : '▶'}</span>
        )}
      </div>
    </div>
  );

  // ── Fullscreen mode ────────────────────────────────────────────────────────
  if (isFullscreen) {
    return (
      <div className="fixed inset-0 z-50 flex flex-col bg-[var(--canvas-bg)]" style={{ opacity: 0.97 }}>
        {titleBar}
        <div className="flex-1 overflow-auto p-2">
          {tableContent}
        </div>
      </div>
    );
  }

  // ── Normal mode ────────────────────────────────────────────────────────────
  return (
    <div
      className="border border-[var(--border-default)] rounded mb-3 relative group"
      style={tableWidth ? { width: tableWidth } : undefined}
    >
      {titleBar}
      {(expanded || hasHighlight) && (
        <>
          {tableContent}
          {/* Horizontal resize handle — right edge */}
          <div
            ref={resizeRef}
            onMouseDown={handleResizeMouseDown}
            className="absolute top-0 right-0 bottom-0 w-2 cursor-col-resize opacity-0 group-hover:opacity-100 hover:bg-[var(--accent-primary-subtle)] z-30"
            title="Drag to resize"
          />
        </>
      )}
    </div>
  );
};

// ─── Main Component ─────────────────────────────────────────────────────────

const AssumptionsStep: React.FC<AssumptionsStepProps> = ({
  forecastDrivers,
  dcfInputs,
  completeFinancialStatements,
  peerWaccData,
  marketData,
  selectedCompany,
  ticker,
  companyName,
  currentPrice: propCurrentPrice,
  selectedModel,
  selectedScenario,
  confirmedValues,
  onManualInput,
  onConfirmAssumptions,
  onBackToForecastDrivers,
  loading,
  // Legacy fallbacks
  historicalData,
  peerData,
}) => {
  // ─── Build DCFInputs from store data ──────────────────────────────────────
  const { t } = useTranslation();
  // If forecastDrivers has categories (Step 8 backend format), parse them into base_case arrays
  const parsedDrivers = useMemo(() => {
    if (forecastDrivers?.base_case?.revenue_growth) return forecastDrivers; // Already has scenario data
    if (!forecastDrivers?.categories) return forecastDrivers; // No categories to parse

    // Parse Step 8 categories into scenario arrays
    const categories = forecastDrivers.categories;
    // Get trend values — for growth rates (revenue, inflation), compute YoY from absolute values
    // For level metrics (AR Days, Tax Rate, Capex), use the final_value or trend directly
    const getTrend = (catKey: string, metric: string, isGrowthRate: boolean = false): number[] | null => {
      const cat = categories[catKey];
      if (!cat?.assumptions) return null;
      // Flexible matching: try exact match first, then partial (case-insensitive)
      let assumption = cat.assumptions.find((a: any) => a.metric === metric);
      if (!assumption) {
        const lowerMetric = metric.toLowerCase();
        assumption = cat.assumptions.find((a: any) => {
          const m = (a.metric || '').toLowerCase();
          return m === lowerMetric || m.includes(lowerMetric) || lowerMetric.includes(m);
        });
      }
      if (!assumption) return null;

      // Resolve fallback value: final_value > AI suggestion > historical trendline CAGR/avg
      let finalVal = assumption.final_value ?? assumption.ai_suggestion?.suggested_value ?? null;
      // If still null/zero, fall back to historical trendline stats
      if (!finalVal) {
        const tl = assumption.historical_trendline;
        if (tl) {
          if (isGrowthRate) {
            // For growth rates, prefer average_yoy_growth, then CAGR
            finalVal = tl.average_yoy_growth || tl.cagr || null;
          }
          // For level metrics (days, rates, dollar changes), prefer latest or average
          // Use || (not ??) so that 0 values also cascade to the next fallback
          if (!finalVal) {
            finalVal = tl.latest_value || tl.average || null;
          }
        }
      }
      if (!finalVal && finalVal !== 0) finalVal = 0;

      // Priority 1: year_values (forecast year-by-year values — most reliable)
      if (assumption.year_values && Object.keys(assumption.year_values).length > 0) {
        const vals = Object.values(assumption.year_values).map(Number);
        while (vals.length < 6) vals.push(vals[vals.length - 1] ?? finalVal);
        return vals.slice(0, 6);
      }

      // Priority 2: Use resolved final_value for all years
      return Array(6).fill(finalVal);
    };
    const getScalar = (catKey: string, metric: string, fallback: number): number | null => {
      const cat = categories[catKey];
      if (!cat?.assumptions) return null;
      let assumption = cat.assumptions.find((a: any) => a.metric === metric);
      if (!assumption) {
        const lowerMetric = metric.toLowerCase();
        assumption = cat.assumptions.find((a: any) => {
          const m = (a.metric || '').toLowerCase();
          return m === lowerMetric || m.includes(lowerMetric) || lowerMetric.includes(m);
        });
      }
      if (!assumption) return null;
      let val = assumption.final_value ?? assumption.ai_suggestion?.suggested_value ?? null;
      // Fall back to historical trendline stats if no final_value or AI suggestion
      // Use || (not ??) so that 0 values also cascade to the next fallback
      if (!val) {
        const tl = assumption.historical_trendline;
        if (tl) {
          val = tl.latest_value || tl.average || fallback;
        }
      }
      return val ?? fallback;
    };

    // Helper: get first assumption from a category (for single-assumption categories)
    const getFirstAssumption = (catKey: string): number[] => {
      const cat = categories[catKey];
      if (!cat?.assumptions?.length) return Array(5).fill(0);
      const a = cat.assumptions[0];
      let finalVal = a.final_value ?? a.ai_suggestion?.suggested_value ?? null;
      // Fall back to historical trendline CAGR for growth rates
      // Use || (not ??) so that 0 values also cascade to the next fallback
      if (!finalVal) {
        const tl = a.historical_trendline;
        if (tl) {
          finalVal = tl.average_yoy_growth || tl.cagr || tl.latest_value || tl.average || 0;
        }
      }
      if (!finalVal && finalVal !== 0) finalVal = 0;
      // Try year_values first (most reliable for forecast data)
      if (a.year_values && Object.keys(a.year_values).length > 0) {
        const vals = Object.values(a.year_values).map(Number);
        while (vals.length < 5) vals.push(vals[vals.length - 1] ?? finalVal);
        return vals.slice(0, 5);
      }
      return Array(5).fill(finalVal);
    };

    // Helper: pick first non-null from a list of getTrend/getScalar results
    const firstOf = (...candidates: (number[] | number | null | undefined)[]): number[] => {
      for (const c of candidates) {
        if (Array.isArray(c) && c.length > 0) return c;
      }
      return Array(5).fill(0);
    };
    const firstScalar = (...candidates: (number | null | undefined)[]): number => {
      for (const c of candidates) {
        if (c != null) return c;
      }
      return 0;
    };

    return {
      base_case: {
        revenue_growth: firstOf(
          getTrend('REVENUE_DRIVERS', 'Revenue Growth', true),
          getTrend('REVENUE_DRIVERS', 'Volume Growth', true),
          getFirstAssumption('REVENUE_DRIVERS'),
        ),
        cogs_growth_rate: firstOf(
          getTrend('COST_MARGINS', 'COGS Growth Rate', true),
          getTrend('COST_MARGINS', 'COGS Growth Rate (%)', true),
        ),
        opex_growth_rate: firstOf(
          getTrend('COST_MARGINS', 'OpEx Growth'),
          getTrend('COST_MARGINS', 'OpEx Growth (%)'),
        ),
        inflation_rate: firstOf(
          getTrend('COST_MARGINS', 'Inflation Rate'),
          getTrend('COST_MARGINS', 'Inflation Rate (%)'),
          // Inflation rate is deprecated — use COGS Growth Rate as fallback
          getTrend('COST_MARGINS', 'COGS Growth Rate'),
          getTrend('COST_MARGINS', 'COGS Growth Rate (%)'),
        ),
        capital_expenditure: firstOf(
          getTrend('WORKING_CAPITAL', 'CapEx'),
          getTrend('WORKING_CAPITAL', 'Capital Expenditure'),
        ),
        receivables_days: firstOf(
          getTrend('WORKING_CAPITAL', 'Receivables Days'),
          getTrend('WORKING_CAPITAL', 'Accounts Receivable Days'),
          getTrend('WORKING_CAPITAL', 'AR Days'),
        ),
        inventory_days: firstOf(
          getTrend('WORKING_CAPITAL', 'Inventory Days'),
        ),
        payables_days: firstOf(
          getTrend('WORKING_CAPITAL', 'Payables Days'),
          getTrend('WORKING_CAPITAL', 'Accounts Payable Days'),
          getTrend('WORKING_CAPITAL', 'AP Days'),
        ),
        tax_rate: firstOf(
          getTrend('COST_MARGINS', 'Tax Rate'),
          getTrend('COST_MARGINS', 'Tax Rate (%)'),
          getTrend('COST_MARGINS', 'Effective Tax Rate'),
        ),
        change_in_lt_debt: firstOf(
          getTrend('FINANCING', 'Change in Long-Term Debt'),
          getTrend('FINANCING', 'LT Debt'),
        ),
        change_in_common_equity: firstOf(
          getTrend('FINANCING', 'Change in Common Equity'),
          getTrend('FINANCING', 'Common Equity'),
        ),
        dividend_payout_ratio: firstScalar(
          getScalar('FINANCING', 'Dividend Payout Ratio', 0),
          getScalar('FINANCING', 'Dividends', 0),
        ),
      },
    };
  }, [forecastDrivers]);

  const baseDrivers = parsedDrivers?.base_case || parsedDrivers?.[selectedScenario] || parsedDrivers || {};
  const baseDcf = dcfInputs || {};

  // Extract historical actuals from complete_financial_statements
  const historical: HistoricalActuals = useMemo(() => {
    if (completeFinancialStatements) {
      return extractHistoricalActuals(completeFinancialStatements);
    }
    // Fallback: construct from legacy props
    return {
      revenue: [0, 0, 0], cogs: [0, 0, 0], sga: [0, 0, 0], otherOpex: [0, 0, 0],
      grossProfit: [0, 0, 0], ebitda: [0, 0, 0], ebit: [0, 0, 0],
      netIncome: [0, 0, 0], taxProvision: [0, 0, 0], pretaxIncome: [0, 0, 0],
      capex: [0, 0, 0], depreciation: [0, 0, 0], interestExpense: [0, 0, 0],
      ar: [0, 0, 0], inventory: [0, 0, 0], ap: [0, 0, 0],
      ppe: [0, 0, 0], taxBasis: [0, 0, 0], taxLosses: [0, 0, 0],
      cash: [0, 0, 0], totalDebt: [0, 0, 0], longTermDebt: [0, 0, 0], currentDebt: [0, 0, 0],
      shortTermDebt: [0, 0, 0], totalAssets: [0, 0, 0], totalEquity: [0, 0, 0], commonEquity: [0, 0, 0], totalLiabilities: [0, 0, 0],
      currentAssets: [0, 0, 0], currentLiabilities: [0, 0, 0],
      deferredTax: [0, 0, 0], ppeNet: [0, 0, 0], accumulatedDepreciation: [0, 0, 0],
      retainedEarnings: [0, 0, 0], sharesOutstanding: [0, 0, 0],
      dividendsPaid: [0, 0, 0], marketCap: [0, 0, 0],
      interestIncome: [0, 0, 0], otherIncomeExpense: [0, 0, 0], researchDevelopment: [0, 0, 0],
      operatingCashFlow: [0, 0, 0], shareBuybacks: [0, 0, 0],
      debtRepayments: [0, 0, 0], debtIssuance: [0, 0, 0],
      taxPaid: [0, 0, 0], interestPaid: [0, 0, 0],
      // Institution-grade balance sheet items
      nonCurrentMarketableSecurities: [0, 0, 0],
      otherCurrentLiabilities: [0, 0, 0],
      deferredTaxLiabilities: [0, 0, 0],
      // New granularity balance sheet items
      currentAccruedExpenses: [0, 0, 0],
      currentDeferredLiabilities: [0, 0, 0],
      tradeAndOtherPayablesNonCurrent: [0, 0, 0],
      otherNonCurrentLiabilities: [0, 0, 0],
      otherShortTermInvestments: [0, 0, 0],
      otherCurrentAssets: [0, 0, 0],
      otherNonCurrentAssets: [0, 0, 0],
      commonStock: [0, 0, 0],
      otherEquityAdjustments: [0, 0, 0],
      periods: ['FY2020', 'FY2021', 'FY2022'],
    };
  }, [completeFinancialStatements]);

  // Derive dynamic period labels from actual historical data
  const { histPeriods: HIST_PERIODS, fcPeriods: FC_PERIODS, allPeriods: ALL_PERIODS } = useMemo(
    () => derivePeriods(historical.periods),
    [historical.periods],
  );

  // Build initial inputs from store + confirmed values
  const buildInputs = useCallback((): DCFInputs => {
    const getConfirmed = (key: string, fallback: number) => {
      const cv = confirmedValues[key];
      return cv?.value !== undefined ? Number(cv.value) : fallback;
    };

    // Normalize forecast driver arrays: Step 8 stores values as percentages (e.g., 1.88 = 1.88%)
    // but Step 9 display multiplies by 100. Convert to decimal if values are > 1.
    const normalizePctArray = (arr: number[] | undefined): number[] => {
      if (!arr) return [0, 0, 0, 0, 0];
      return arr.map(v => {
        if (v == null) return 0;
        // If value looks like a percentage (> 1), convert to decimal
        return Math.abs(v) > 1 ? v / 100 : v;
      });
    };

    // Read a 5-year forecast array from confirmedValues (user edits from Step 8),
    // falling back to baseDrivers (backend categories) if no edits found.
    // confirmedValues keys use snake_case: forecast_base_case_revenue_growth_0, etc.
    const FIELD_NAME_MAP: Record<string, string> = {
      revenueGrowth: 'revenue_growth',
      cogsGrowthRate: 'cogs_growth_rate',
      opexGrowthRate: 'opex_growth_rate',
      inflationRate: 'inflation_rate',
      capitalExpenditure: 'capital_expenditure',
      receivablesDays: 'receivables_days',
      inventoryDays: 'inventory_days',
      payablesDays: 'payables_days',
    };
    const getConfirmedForecastArray = (feField: string, backendField: string, fallback: number[]): number[] => {
      const scenario = selectedScenario || 'base_case';
      const snakeField = FIELD_NAME_MAP[feField] || backendField;
      const result: number[] = [];
      let hasAnyConfirmed = false;
      for (let i = 0; i < 6; i++) {
        const key = `forecast_${scenario}_${snakeField}_${i}`;
        const cv = confirmedValues[key];
        const val = cv?.value !== undefined ? Number(cv.value) : (typeof cv === 'number' ? cv : undefined);
        if (val !== undefined && !isNaN(val)) {
          result.push(val);
          hasAnyConfirmed = true;
        } else {
          result.push(fallback[i] ?? fallback[fallback.length - 1] ?? 0);
        }
      }
      return hasAnyConfirmed ? result : fallback;
    };

    return {
      // Forecast drivers: read from confirmedValues first (user edits from Step 8),
      // fall back to baseDrivers (backend categories) for unedited years.
      revenueGrowth: (() => {
        const fallback = normalizePctArray(baseDrivers.revenue_growth);
        while (fallback.length < 6) fallback.push(fallback[fallback.length - 1] ?? 0);
        return getConfirmedForecastArray('revenueGrowth', 'revenue_growth', fallback);
      })(),
      cogsGrowthRate: (() => {
        // Use cogs_growth_rate from Step 8; fall back to inflation_rate for backward compatibility
        const raw = baseDrivers.cogs_growth_rate || baseDrivers.inflation_rate;
        const fallback = normalizePctArray(raw);
        while (fallback.length < 6) fallback.push(fallback[fallback.length - 1] ?? 0);
        return getConfirmedForecastArray('cogsGrowthRate', 'cogs_growth_rate', fallback);
      })(),
      opexGrowthRate: (() => {
        // Use opex_growth_rate from Step 8; fall back to inflation_rate for backward compatibility
        const raw = baseDrivers.opex_growth_rate || baseDrivers.inflation_rate;
        const fallback = normalizePctArray(raw);
        while (fallback.length < 6) fallback.push(fallback[fallback.length - 1] ?? 0);
        return getConfirmedForecastArray('opexGrowthRate', 'opex_growth_rate', fallback);
      })(),
      inflationRate: (() => {
        const fallback = normalizePctArray(baseDrivers.inflation_rate);
        while (fallback.length < 6) fallback.push(fallback[fallback.length - 1] ?? 0);
        return getConfirmedForecastArray('inflationRate', 'inflation_rate', fallback);
      })(),
      taxRate: normalizeDecimal(getConfirmed('dcf_tax_rate', baseDrivers.tax_rate?.[0] || 0.21), 0.10, 0.50),
      arDays: getConfirmed('dcf_receivables_days', baseDrivers.receivables_days?.[0] || 45),
      invDays: getConfirmed('dcf_inventory_days', baseDrivers.inventory_days?.[0] || 30),
      apDays: getConfirmed('dcf_payables_days', baseDrivers.payables_days?.[0] || 40),
      capex: (() => {
        const fallback = baseDrivers.capital_expenditure || [0, 0, 0, 0, 0];
        while (fallback.length < 6) fallback.push(fallback[fallback.length - 1] ?? 0);
        return getConfirmedForecastArray('capitalExpenditure', 'capital_expenditure', fallback);
      })(),
      usefulLifeExisting: getConfirmed('dcf_useful_life_existing', baseDcf.useful_life_existing || 16),
      usefulLifeNew: getConfirmed('dcf_useful_life_new', baseDcf.useful_life_new || 20),
      firstYearDepreciationRate: getConfirmed('dcf_firstYearDepreciationRate', baseDcf.first_year_depreciation_rate || 50),

      // WACC — normalize percentage fields to decimal (0-1)
      wacc: normalizeDecimal(getConfirmed('dcf_wacc', baseDcf.wacc || 0.10), 0.03, 0.25),
      riskFreeRate: normalizeDecimal(getConfirmed('dcf_risk_free_rate', baseDcf.risk_free_rate || 0.04), 0.01, 0.15),
      equityRiskPremium: normalizeDecimal(getConfirmed('dcf_equity_risk_premium', baseDcf.equity_risk_premium || 0.06), 0.03, 0.15),
      beta: getConfirmed('dcf_beta', baseDcf.beta || 1.0),
      costOfDebt: normalizeDecimal(getConfirmed('dcf_cost_of_debt', baseDcf.cost_of_debt || 0.05), 0.01, 0.20),
      debtToEquity: getConfirmed('dcf_debt_to_equity', baseDcf.debt_to_equity || 0.3),

      // Terminal — normalize percentage fields
      terminalGrowthRate: normalizeDecimal(getConfirmed('dcf_terminal_growth_rate', baseDcf.terminal_growth_rate || 0.025), 0.00, 0.08),
      terminalEbitdaMultiple: getConfirmed('dcf_terminal_ebitda_multiple', baseDcf.terminal_ebitda_multiple || 10),

      // Financing assumptions
      changeInLtDebt: (() => { const a = baseDrivers.change_in_lt_debt || Array(5).fill(0); while (a.length < 6) a.push(a[a.length - 1] ?? 0); return a; })(),
      changeInCommonEquity: (() => { const a = baseDrivers.change_in_common_equity || Array(5).fill(0); while (a.length < 6) a.push(a[a.length - 1] ?? 0); return a; })(),
      dividendPayoutRatio: normalizeDecimal(getConfirmed('dcf_dividend_payout_ratio', baseDrivers.dividend_payout_ratio || 0), 0, 1),

      // Interest rate schedule inputs
      cashInterestRate: normalizeDecimal(getConfirmed('dcf_cash_interest_rate', baseDcf.cash_interest_rate || 0.01), 0, 0.10),
      revolvingCreditRate: normalizeDecimal(getConfirmed('dcf_revolving_credit_rate', baseDcf.revolving_credit_rate || 0.05), 0, 0.20),
      ltDebtInterestRate: normalizeDecimal(getConfirmed('dcf_lt_debt_interest_rate', baseDcf.lt_debt_interest_rate || 0.06), 0, 0.20),

      // Tax depreciation schedule inputs
      firstYearTaxDepRate: normalizeDecimal(getConfirmed('dcf_first_year_tax_dep_rate', baseDcf.first_year_tax_dep_rate || 0.50), 0, 1),
      blendedTaxDepRate: normalizeDecimal(getConfirmed('dcf_blended_tax_dep_rate', baseDcf.blended_tax_dep_rate || 0.15), 0, 1),
      firstYearAcctgDepRate: normalizeDecimal(getConfirmed('dcf_first_year_acctg_dep_rate', baseDcf.first_year_acctg_dep_rate || 0.50), 0, 1),

      // Market — read from confirmedValues, then DCF inputs, then company/market data, then complete_financial_statements
      currentPrice: getConfirmed('dcf_current_price', propCurrentPrice || baseDcf.current_price || 0),
      sharesOutstanding: getConfirmed('dcf_shares_outstanding', (() => {
        // Priority chain: confirmedValues > dcfInputs > selectedCompany > marketData > complete_financial_statements
        const fromDcf = baseDcf.shares_outstanding;
        if (fromDcf) return fromDcf;
        const fromCompany = selectedCompany?.sharesOutstanding || selectedCompany?.shares_outstanding;
        if (fromCompany) return fromCompany;
        const fromMarket = marketData?.shares_outstanding || marketData?.raw_info?.sharesOutstanding;
        if (fromMarket) return fromMarket;
        // Extract from complete_financial_statements balance_sheet
        if (completeFinancialStatements?.balance_sheet) {
          const bs = completeFinancialStatements.balance_sheet;
          const periods = Object.keys(bs).filter(k => typeof bs[k] === 'object' && bs[k]?.shares_outstanding != null);
          if (periods.length > 0) {
            const latest = periods[periods.length - 1];
            const val = bs[latest].shares_outstanding;
            return typeof val === 'number' ? val : parseFloat(val) || null;
          }
        }
        // Derive from market cap / price
        if (historical.marketCap && historical.marketCap.length > 0 && propCurrentPrice) {
          return historical.marketCap[historical.marketCap.length - 1] / propCurrentPrice;
        }
        return 0;
      })()),
      netDebt: getConfirmed('dcf_net_debt',
        baseDcf.net_debt ||
        (marketData?.total_debt || 0) - (marketData?.cash_and_equivalents || 0) ||
        (historical.totalDebt?.[historical.totalDebt.length - 1] || 0) - (historical.cash?.[historical.cash.length - 1] || 0)),

      // Historical
      historicalRevenue: historical.revenue,
      historicalCogs: historical.cogs,
      historicalSga: historical.sga,
      historicalOtherOpex: historical.otherOpex,
      historicalCapex: historical.capex,
      historicalDepreciation: historical.depreciation,
      historicalInterestExpense: historical.interestExpense,
      historicalAr: historical.ar,
      historicalInventory: historical.inventory,
      historicalAp: historical.ap,
      historicalPpe: historical.ppe,
      historicalTaxBasis: historical.taxBasis,
      historicalTaxLosses: historical.taxLosses,
      historicalAccumulatedDepreciation: historical.accumulatedDepreciation || [0, 0, 0],
      historicalPpeNet: historical.ppeNet || [0, 0, 0],
      historicalResearchDevelopment: historical.researchDevelopment || [0, 0, 0],
      historicalInterestIncome: historical.interestIncome || [0, 0, 0],
      historicalOtherIncomeExpense: historical.otherIncomeExpense || [0, 0, 0],
      historicalTaxPaid: historical.taxPaid || [0, 0, 0],
      historicalInterestPaid: historical.interestPaid || [0, 0, 0],
      historicalDebtIssuance: historical.debtIssuance || [0, 0, 0],
      historicalDebtRepayments: historical.debtRepayments || [0, 0, 0],
      historicalCurrentDebt: historical.currentDebt || [0, 0, 0],

      // DCF model parameters (hidden fields exposed for transparency)
      ppeGrossBook: historical.ppe?.[historical.ppe.length - 1] || 0,
      taxBasisPpe: historical.taxBasis?.[historical.taxBasis.length - 1] || 0,
      taxLossesNol: historical.taxLosses?.[historical.taxLosses.length - 1] || 0,
      revolvingCreditLine: 0,
      taxLossUtilizationLimit: 0.80,
      // Additional income statement items
      historicalGrossProfit: historical.grossProfit || [0, 0, 0],
      historicalEbitda: historical.ebitda || [0, 0, 0],
      historicalEbit: historical.ebit || [0, 0, 0],
      historicalNetIncome: historical.netIncome || [0, 0, 0],
      historicalTaxProvision: historical.taxProvision || [0, 0, 0],
      historicalPretaxIncome: historical.pretaxIncome || [0, 0, 0],
      // Additional balance sheet items
      historicalCash: historical.cash || [0, 0, 0],
      historicalTotalDebt: historical.totalDebt || [0, 0, 0],
      historicalTotalAssets: historical.totalAssets || [0, 0, 0],
      historicalTotalEquity: historical.totalEquity || [0, 0, 0],
      historicalTotalLiabilities: historical.totalLiabilities || [0, 0, 0],
      historicalCurrentAssets: historical.currentAssets || [0, 0, 0],
      historicalCurrentLiabilities: historical.currentLiabilities || [0, 0, 0],
      historicalDeferredTax: historical.deferredTax || [0, 0, 0],
      historicalRetainedEarnings: historical.retainedEarnings || [0, 0, 0],
      historicalDividendsPaid: historical.dividendsPaid || [0, 0, 0],
      historicalCommonEquity: historical.commonEquity || [0, 0, 0],
      historicalShareBuybacks: historical.shareBuybacks || [0, 0, 0],
      historicalMarketCap: historical.marketCap || [0, 0, 0],
      // Institution-grade balance sheet items
      historicalNonCurrentMarketableSecurities: historical.nonCurrentMarketableSecurities || [],
      historicalOtherCurrentLiabilities: historical.otherCurrentLiabilities || [],
      historicalDeferredTaxLiabilities: historical.deferredTaxLiabilities || [],
      // New granularity balance sheet items
      historicalCurrentAccruedExpenses: historical.currentAccruedExpenses || [],
      historicalCurrentDeferredLiabilities: historical.currentDeferredLiabilities || [],
      historicalTradeAndOtherPayablesNonCurrent: historical.tradeAndOtherPayablesNonCurrent || [],
      historicalOtherNonCurrentLiabilities: historical.otherNonCurrentLiabilities || [],
      historicalOtherShortTermInvestments: historical.otherShortTermInvestments || [],
      historicalOtherCurrentAssets: historical.otherCurrentAssets || [],
      historicalOtherNonCurrentAssets: historical.otherNonCurrentAssets || [],
      historicalCommonStock: historical.commonStock || [],
      historicalOtherEquityAdjustments: historical.otherEquityAdjustments || [],
    };
  }, [confirmedValues, baseDrivers, baseDcf, historical, propCurrentPrice, marketData]);

  const [inputs, setInputs] = useState<DCFInputs>(buildInputs);
  const [recalcKey, setRecalcKey] = useState(0);
  const prevInputsRef = useRef<string>('');

  // Track which fields are using default/fallback values (not from Step 8 data)
  const defaultFields = useMemo(() => {
    const defaults = new Set<string>();
    // Forecast drivers: default if all zeros or matches hardcoded fallback
    if (inputs.revenueGrowth.every(v => v === 0)) defaults.add('revenueGrowth');
    if (inputs.cogsGrowthRate.every(v => v === 0)) defaults.add('cogsGrowthRate');
    if (inputs.opexGrowthRate.every(v => v === 0)) defaults.add('opexGrowthRate');
    if (inputs.inflationRate.every(v => v === 0)) defaults.add('inflationRate');
    if (inputs.capex.every(v => v === 0)) defaults.add('capex');
    // Scalar fields: check if they match the hardcoded fallback
    if (inputs.taxRate === 0.21) defaults.add('taxRate');
    if (inputs.arDays === 45) defaults.add('arDays');
    if (inputs.invDays === 30) defaults.add('invDays');
    if (inputs.apDays === 40) defaults.add('apDays');
    if (inputs.usefulLifeExisting === 16) defaults.add('usefulLifeExisting');
    if (inputs.usefulLifeNew === 20) defaults.add('usefulLifeNew');
    if (inputs.firstYearDepreciationRate === 50) defaults.add('firstYearDepreciationRate');
    if (inputs.wacc === 0.10) defaults.add('wacc');
    if (inputs.riskFreeRate === 0.04) defaults.add('riskFreeRate');
    if (inputs.equityRiskPremium === 0.06) defaults.add('equityRiskPremium');
    if (inputs.beta === 1.0) defaults.add('beta');
    if (inputs.costOfDebt === 0.05) defaults.add('costOfDebt');
    if (inputs.debtToEquity === 0.3) defaults.add('debtToEquity');
    if (inputs.terminalGrowthRate === 0.025) defaults.add('terminalGrowthRate');
    if (inputs.terminalEbitdaMultiple === 10) defaults.add('terminalEbitdaMultiple');
    if (inputs.cashInterestRate === 0.01) defaults.add('cashInterestRate');
    if (inputs.revolvingCreditRate === 0.05) defaults.add('revolvingCreditRate');
    if (inputs.ltDebtInterestRate === 0.06) defaults.add('ltDebtInterestRate');
    if (inputs.firstYearTaxDepRate === 0.50) defaults.add('firstYearTaxDepRate');
    if (inputs.blendedTaxDepRate === 0.15) defaults.add('blendedTaxDepRate');
    if (inputs.firstYearAcctgDepRate === 0.50) defaults.add('firstYearAcctgDepRate');
    if (inputs.currentPrice === 0) defaults.add('currentPrice');
    if (inputs.sharesOutstanding === 0) defaults.add('sharesOutstanding');
    if (inputs.netDebt === 0) defaults.add('netDebt');
    if (inputs.dividendPayoutRatio === 0) defaults.add('dividendPayoutRatio');
    return defaults;
  }, [inputs]);

  // Rebuild inputs when confirmedValues or forecastDrivers change
  useEffect(() => {
    const newInputs = buildInputs();
    const serialized = JSON.stringify(newInputs);
    if (serialized !== prevInputsRef.current) {
      prevInputsRef.current = serialized;
      setInputs(newInputs);
    }
  }, [buildInputs]);

  // ─── Auto-calculate WACC from components ───────────────────────────────────
  // WACC = (D/V × Rd × (1-t)) + (E/V × (Rf + β × ERP))
  useEffect(() => {
    const de = inputs.debtToEquity || 0.3;
    const dv = de / (1 + de);
    const ev = 1 - dv;
    const afterTaxCostOfDebt = inputs.costOfDebt * (1 - inputs.taxRate);
    const costOfEquity = inputs.riskFreeRate + inputs.beta * inputs.equityRiskPremium;
    const calculatedWacc = dv * afterTaxCostOfDebt + ev * costOfEquity;
    // Only update if the calculated value differs significantly from current
    if (Math.abs(calculatedWacc - inputs.wacc) > 0.001) {
      setInputs(prev => ({ ...prev, wacc: calculatedWacc }));
    }
  }, [inputs.riskFreeRate, inputs.equityRiskPremium, inputs.beta, inputs.costOfDebt, inputs.debtToEquity, inputs.taxRate]);

  // NOTE: Interest expense is now computed dynamically in the backend DCF engine
  // from LT debt balance × lt_debt_interest_rate. No frontend auto-calc needed.

  // Per-section recalculate: forces useMemo to re-run all schedules
  const handleRecalc = useCallback(() => {
    setInputs(buildInputs());
    setRecalcKey(k => k + 1);
  }, [buildInputs]);

  // ─── Calculate DCF Output (backend API) ───────────────────────────────────
  const { sessionId, market } = useValuationStore();
  const [output, setOutput] = useState<DCFOutput | null>(null);
  const [backendCalc, setBackendCalc] = useState<Record<string, (number | null)[]>>({});
  const [apiLoading, setApiLoading] = useState(false);
  const [scheduleStatus, setScheduleStatus] = useState<Record<string, string>>({});
  const [allSchedulesOk, setAllSchedulesOk] = useState(false);
  const [apiWarnings, setApiWarnings] = useState<string[]>([]);

  // Send the ENTIRE inputs state to the backend.
  // The frontend has ALL data mapped from Steps 6/7/8 — the backend
  // builds DCFInputs directly from this, no session reads needed.
  const buildAssumptionOverrides = useCallback(() => {
    return { ...inputs } as Record<string, any>;
  }, [inputs]);

  // Calculate button: ALWAYS works. Sends current inputs as overrides.
  // Shows partial results with per-schedule status.
  const handleCalculateBuildingBlocks = useCallback(async () => {
    if (!sessionId) return;
    setApiLoading(true);
    try {
      const overrides = buildAssumptionOverrides();
      const res: any = await calculateBuildingBlocks(
        sessionId, selectedScenario || 'base_case', selectedModel || 'DCF', market, overrides,
      );
      if (res?.status === 'success' && res?.calculated_schedules) {
        const transformed = transformBackendToFrontend({
          supporting_schedules: res.calculated_schedules,
          wacc_calculation: res.wacc_calculation || res.calculated_schedules?.wacc_calculation || {},
          cash_flow_statement: res.cash_flow_statement || res.calculated_schedules?.cash_flow_statement || {},
          balance_sheet: res.balance_sheet || res.calculated_schedules?.balance_sheet || {},
          // Full-period schedules (historical + forecast) — top-level in backend to_dict()
          interest_schedule: res.interest_schedule || res.calculated_schedules?.interest_schedule || {},
          historical_references: res.historical_references || res.calculated_schedules?.historical_references || {},
          full_working_capital: res.full_working_capital || res.calculated_schedules?.full_working_capital || {},
          // Debt & Equity schedules
          debt_schedule_part1: res.debt_schedule_part1 || res.calculated_schedules?.debt_schedule_part1 || {},
          debt_schedule_part2: res.debt_schedule_part2 || res.calculated_schedules?.debt_schedule_part2 || {},
          equity_schedule: res.equity_schedule || res.calculated_schedules?.equity_schedule || {},
          // Period labels and metadata
          metadata: res.metadata || res.calculated_schedules?.metadata || {},
        });

        // Pad backend arrays (6 values: FY1-FY5 + Term) with historical data
        // to match frontend ALL_PERIODS layout (3 hist + 5 forecast + Term = 9)
        const histLen = HIST_PERIODS.length;
        const padWithHistorical = (backendArr: number[], histArr: number[]): number[] => {
          const padded: number[] = [];
          // Fill historical columns with actual historical data
          for (let i = 0; i < histLen; i++) {
            padded.push(histArr?.[i] ?? 0);
          }
          // Fill forecast + terminal columns with backend output
          padded.push(...backendArr);
          return padded;
        };

        const h = historical; // shorthand
        const pad = (arr: number[], histKey: keyof HistoricalActuals) =>
          padWithHistorical(arr, h[histKey] as number[] || []);

        // Store backend-calculated values for calculatedValues display.
        //
        // For HISTORICAL periods (indices 0..histLen-1):
        //   Compute calvalue by applying DCF cross-check formulas to historical data.
        //   Diff between calvalue and actual reveals missing/mismatched data items.
        //   e.g. EBT calvalue = EBIT - Interest; if actual EBT differs, there are
        //   unmodeled items like interest income or other income/expense.
        //
        // For FORECAST periods (indices histLen..end):
        //   Use raw backend engine values (same as padded `values`, so no diff shown).
        const hRev = h.revenue || [];
        const hCogs = h.cogs || [];
        const hSga = h.sga || [];
        const hRd = h.researchDevelopment || [];
        const hOtherOpex = h.otherOpex || [];
        const hGp = h.grossProfit || [];
        const hEbitda = h.ebitda || [];
        const hDep = h.depreciation || [];
        const hEbit = h.ebit || [];
        const hIntExp = h.interestExpense || [];
        const hIntInc = h.interestIncome || [];
        const hOtherIncExp = h.otherIncomeExpense || [];
        const hCurrTax = h.taxProvision || [];
        const hDefTax = h.deferredTax || [];

        // Helper: combine historical calvalue array + backend forecast array
        // into a single 9-element array for calculatedValues display.
        const combineHistCalAndForecast = (
          histCalArr: number[],
          forecastArr: number[],
        ): (number | null)[] => {
          const result: (number | null)[] = [];
          for (let i = 0; i < histLen; i++) {
            result.push(histCalArr[i] ?? null);
          }
          result.push(...forecastArr);
          return result;
        };

        // For lines with no meaningful formula cross-check, null-pad historical
        // and append backend forecast values.
        const nullPadHistAndAppendForecast = (forecastArr: number[]): (number | null)[] => {
          return [...new Array(histLen).fill(null), ...forecastArr];
        };

        // Historical calvalue arrays — correct formulas for YFinance data:
        //   GP = Rev − COGS
        //   EBIT = GP − OpEx (SG&A + R&D + OtherOpEx — these include depreciation in YFinance)
        //   EBITDA = EBIT + Depreciation (add back)
        //   EBT = EBIT − Other Income/Expense + Interest Income − Interest Expense
        //   Total Tax = Current Tax + Deferred Tax
        //   Net Income = EBT − Total Tax
        const histCalGrossProfit = hRev.map((rev, i) => (rev || 0) - (hCogs[i] || 0));
        // EBIT = GP − OpEx (OpEx includes depreciation in YFinance)
        const histCalEbit = histCalGrossProfit.map((gp, i) =>
          (gp || 0) - (hSga[i] || 0) - (hRd[i] || 0) - (hOtherOpex[i] || 0)
        );
        // EBITDA = EBIT + Depreciation (add back)
        const histCalEbitda = histCalEbit.map((ebit, i) => (ebit || 0) + (hDep[i] || 0));
        // Depreciation calvalue = EBITDA − EBIT
        const histCalDepreciation = histCalEbitda.map((ebitda, i) => (ebitda || 0) - (hEbit[i] || 0));
        const histCalEbt = histCalEbit.map((ebit, i) =>
          (ebit || 0) - (hOtherIncExp[i] || 0) + (hIntInc[i] || 0) - (hIntExp[i] || 0)
        );
        const histCalTotalTax = hCurrTax.map((ct, i) => (ct || 0) + (hDefTax[i] || 0));

        const backendCalcValues = {
          // Base inputs: no meaningful formula → null for historical
          revenue: nullPadHistAndAppendForecast(transformed.incomeStatement.revenue || []),
          cogs: nullPadHistAndAppendForecast(transformed.incomeStatement.cogs || []),
          sga: nullPadHistAndAppendForecast(transformed.incomeStatement.sga || []),
          otherOpex: nullPadHistAndAppendForecast(transformed.incomeStatement.otherOpex || []),
          interestExpense: nullPadHistAndAppendForecast(transformed.incomeStatement.interestExpense || []),
          currentTax: nullPadHistAndAppendForecast(transformed.incomeStatement.currentTax || []),
          deferredTax: nullPadHistAndAppendForecast(transformed.incomeStatement.deferredTax || []),
          // Derived items: historical calvalue = formula cross-check, forecast = engine output
          grossProfit: combineHistCalAndForecast(histCalGrossProfit, transformed.incomeStatement.grossProfit || []),
          ebitda: combineHistCalAndForecast(histCalEbitda, transformed.incomeStatement.ebitda || []),
          depreciation: combineHistCalAndForecast(histCalDepreciation, transformed.incomeStatement.depreciation || []),
          ebit: combineHistCalAndForecast(histCalEbit, transformed.incomeStatement.ebit || []),
          ebt: combineHistCalAndForecast(histCalEbt, transformed.incomeStatement.ebt || []),
          totalTax: combineHistCalAndForecast(histCalTotalTax, transformed.incomeStatement.totalTax || []),
          netIncome: combineHistCalAndForecast(
            histCalEbt.map((ebt, i) => (ebt || 0) - (histCalTotalTax[i] || 0)),
            transformed.incomeStatement.netIncome || [],
          ),
        };
        setBackendCalc(backendCalcValues);

        transformed.incomeStatement = {
          ...transformed.incomeStatement,
          revenue: pad(transformed.incomeStatement.revenue, 'revenue'),
          cogs: pad(transformed.incomeStatement.cogs, 'cogs'),
          grossProfit: pad(transformed.incomeStatement.grossProfit, 'grossProfit'),
          sga: pad(transformed.incomeStatement.sga, 'sga'),
          otherOpex: pad(transformed.incomeStatement.otherOpex, 'otherOpex'),
          ebitda: pad(transformed.incomeStatement.ebitda, 'ebitda'),
          depreciation: pad(transformed.incomeStatement.depreciation, 'depreciation'),
          ebit: pad(transformed.incomeStatement.ebit, 'ebit'),
          interestExpense: pad(transformed.incomeStatement.interestExpense, 'interestExpense'),
          ebt: pad(transformed.incomeStatement.ebt, 'pretaxIncome'),
          currentTax: pad(transformed.incomeStatement.currentTax, 'taxProvision'),
          deferredTax: pad(transformed.incomeStatement.deferredTax, 'deferredTax'),
          totalTax: pad(transformed.incomeStatement.totalTax, 'taxProvision'),
          netIncome: pad(transformed.incomeStatement.netIncome, 'netIncome'),
        };

        // ─── Working Capital: use backend full_working_capital (all periods) ───
        const fullWc = (transformed as any).fullWorkingCapital;
        if (fullWc?.arDays && fullWc.arDays.length >= ALL_PERIODS.length) {
          // Backend provides full-period WC — use directly
          transformed.workingCapital = {
            years: fullWc.years,
            arBalance: fullWc.arBalance || [],
            inventoryBalance: fullWc.inventoryBalance || [],
            apBalance: fullWc.apBalance || [],
            nwc: fullWc.nwc || [],
            changeInNwc: fullWc.changeInNwc || [],
            arDays: fullWc.arDays || [],
            invDays: fullWc.invDays || [],
            apDays: fullWc.apDays || [],
          };
        }

        // ─── Historical CFS components (from XBRL balance sheet data) ───
        const histCashFromAr = (historical.ar || []).map((ar, i, arr) => i === 0 ? 0 : (arr[i - 1] || 0) - (ar || 0));
        const histCashFromInv = (historical.inventory || []).map((inv, i, arr) => i === 0 ? 0 : (arr[i - 1] || 0) - (inv || 0));
        const histCashFromAp = (historical.ap || []).map((ap, i, arr) => i === 0 ? 0 : (ap || 0) - (arr[i - 1] || 0));
        const histCapexNeg = (h.capex || []).map((v: number) => -(v || 0));
        const histTotalDebt = h.totalDebt || [];
        const histTotalEquity = h.totalEquity || [];
        const histDividends = h.dividendsPaid || [];
        const histLTDelta = (h.longTermDebt || []).map((ltd: number, i: number) => i === 0 ? 0 : (ltd || 0) - ((h.longTermDebt || [])[i - 1] || 0));
        const histCff = histTotalDebt.map((debt: number, i: number) => {
          const debtChange = i === 0 ? 0 : (debt || 0) - (histTotalDebt[i - 1] || 0);
          const equityChange = i === 0 ? 0 : (histTotalEquity[i] || 0) - (histTotalEquity[i - 1] || 0);
          return debtChange + equityChange - (histDividends[i] || 0);
        });

        // Historical depreciation: we can't split into existing/new asset cohorts,
        // so Existing = total (all dep is on existing assets), New = 0
        // Backend may return arrays of varying length (6 forecast only, or 9 total).
        // We need exactly ALL_PERIODS.length elements: histLen historical + forecast + terminal.
        const histTotalDep = h.depreciation || [];
        const histZeroDep = histTotalDep.map(() => 0);

        // For each schedule, ensure we get the right slice:
        // - If backend has 6 elements (forecast only): pad with histLen historical values
        // - If backend has 9+ elements (includes historical): slice to forecast portion only, then pad
        const getForecastPortion = (arr: number[]): number[] => {
          if (arr.length > 6) return arr.slice(histLen); // strip historical, keep forecast+terminal
          return arr; // already forecast-only
        };

        transformed.depreciation = {
          ...transformed.depreciation,
          capex: pad(transformed.depreciation.capex, 'capex'),
          existingAssetDep: padWithHistorical(getForecastPortion(transformed.depreciation.existingAssetDep), histTotalDep),
          newAssetDep: padWithHistorical(getForecastPortion(transformed.depreciation.newAssetDep), histZeroDep),
          totalDepreciation: padWithHistorical(getForecastPortion(transformed.depreciation.totalDepreciation), histTotalDep),
          grossPpeEnding: pad(transformed.depreciation.grossPpeEnding, 'ppe'),
          taxBasisEnding: pad(transformed.depreciation.taxBasisEnding, 'taxBasis'),
          taxDepreciation: pad(transformed.depreciation.taxDepreciation, 'depreciation'),
        };

        transformed.taxLevered = {
          ...transformed.taxLevered,
          ebtEbit: pad(transformed.taxLevered.ebtEbit, 'pretaxIncome'),
          accountingDep: pad(transformed.taxLevered.accountingDep, 'depreciation'),
          taxDep: pad(transformed.taxLevered.taxDep, 'depreciation'),
          ebtAdjusted: pad(transformed.taxLevered.ebtAdjusted, 'pretaxIncome'),
          nolOpening: pad(transformed.taxLevered.nolOpening, 'taxLosses'),
          nolNew: pad(transformed.taxLevered.nolNew, 'taxLosses'),
          nolUsed: pad(transformed.taxLevered.nolUsed, 'taxLosses'),
          nolEnding: pad(transformed.taxLevered.nolEnding, 'taxLosses'),
          taxableIncome: pad(transformed.taxLevered.taxableIncome, 'pretaxIncome'),
          currentTax: pad(transformed.taxLevered.currentTax, 'taxProvision'),
          totalTax: pad(transformed.taxLevered.totalTax, 'taxProvision'),
          deferredTax: pad(transformed.taxLevered.deferredTax, 'deferredTax'),
        };

        transformed.taxUnlevered = {
          ...transformed.taxUnlevered,
          ebtEbit: pad(transformed.taxUnlevered.ebtEbit, 'ebit'),
          accountingDep: pad(transformed.taxUnlevered.accountingDep, 'depreciation'),
          taxDep: pad(transformed.taxUnlevered.taxDep, 'depreciation'),
          ebtAdjusted: pad(transformed.taxUnlevered.ebtAdjusted, 'ebit'),
          nolOpening: pad(transformed.taxUnlevered.nolOpening, 'taxLosses'),
          nolNew: pad(transformed.taxUnlevered.nolNew, 'taxLosses'),
          nolUsed: pad(transformed.taxUnlevered.nolUsed, 'taxLosses'),
          nolEnding: pad(transformed.taxUnlevered.nolEnding, 'taxLosses'),
          taxableIncome: pad(transformed.taxUnlevered.taxableIncome, 'ebit'),
          currentTax: pad(transformed.taxUnlevered.currentTax, 'taxProvision'),
          totalTax: pad(transformed.taxUnlevered.totalTax, 'taxProvision'),
          deferredTax: pad(transformed.taxUnlevered.deferredTax, 'deferredTax'),
        };

        transformed.cashFlowStatement = {
          ...transformed.cashFlowStatement,
          netIncome: pad(transformed.cashFlowStatement.netIncome, 'netIncome'),
          deferredTaxes: pad(transformed.cashFlowStatement.deferredTaxes, 'deferredTax'),
          depreciation: pad(transformed.cashFlowStatement.depreciation, 'depreciation'),
          cashFromAr: padWithHistorical(transformed.cashFlowStatement.cashFromAr, histCashFromAr),
          cashFromInventory: padWithHistorical(transformed.cashFlowStatement.cashFromInventory, histCashFromInv),
          cashFromAp: padWithHistorical(transformed.cashFlowStatement.cashFromAp, histCashFromAp),
          subtotalCfo: padWithHistorical(transformed.cashFlowStatement.subtotalCfo, h.operatingCashFlow || []),
          capitalExpenditure: padWithHistorical(transformed.cashFlowStatement.capitalExpenditure, histCapexNeg),
          subtotalCfi: padWithHistorical(transformed.cashFlowStatement.subtotalCfi, histCapexNeg),
          changeInLtDebt: padWithHistorical(transformed.cashFlowStatement.changeInLtDebt, histLTDelta),
          changeInCommonEquity: padWithHistorical(transformed.cashFlowStatement.changeInCommonEquity, histTotalEquity.map((eq: number, i: number) => i === 0 ? 0 : (eq || 0) - (histTotalEquity[i - 1] || 0))),
          dividends: padWithHistorical(transformed.cashFlowStatement.dividends, histDividends.map((d: number) => d > 0 ? -d : d)),
          revolvingCredit: pad(transformed.cashFlowStatement.revolvingCredit, 'totalDebt'),
          subtotalCff: padWithHistorical(getForecastPortion(transformed.cashFlowStatement.subtotalCff), histCff),
          // Historical beginning cash = prior period's ending cash (first period = 0)
          beginningCash: padWithHistorical(
            transformed.cashFlowStatement.beginningCash,
            h.cash.map((c: number, i: number) => i === 0 ? 0 : (h.cash[i - 1] || 0))
          ),
          // Historical change in cash = period-over-period delta
          increaseDecrease: padWithHistorical(
            transformed.cashFlowStatement.increaseDecrease,
            h.cash.map((c: number, i: number) => i === 0 ? 0 : (c || 0) - (h.cash[i - 1] || 0))
          ),
          endingCash: pad(transformed.cashFlowStatement.endingCash, 'cash'),
        };

        // Pad balance sheet with correct historical sources
        const histZeroArr = (h.totalAssets || []).map(() => 0);

        const paddedCash = pad(transformed.balanceSheet.cash, 'cash');
        const paddedAR = pad(transformed.balanceSheet.accountsReceivable, 'ar');
        const paddedInv = pad(transformed.balanceSheet.inventories, 'inventory');
        const paddedTCA = pad(transformed.balanceSheet.totalCurrentAssets, 'currentAssets');
        const paddedPPE = pad(transformed.balanceSheet.ppeGross, 'ppe');
        const paddedTA = pad(transformed.balanceSheet.totalAssets, 'totalAssets');
        const paddedAP = pad(transformed.balanceSheet.accountsPayable, 'ap');
        const paddedRevolver = padWithHistorical(getForecastPortion(transformed.balanceSheet.revolvingCredit), histZeroArr);
        const paddedTCL = pad(transformed.balanceSheet.totalCurrentLiabilities, 'currentLiabilities');
        const paddedLTD = padWithHistorical(getForecastPortion(transformed.balanceSheet.longTermDebt), histTotalDebt);
        const paddedTL = pad(transformed.balanceSheet.totalLiabilities, 'totalLiabilities');
        const paddedCE = pad(transformed.balanceSheet.commonEquity, 'totalEquity');
        const paddedRE = pad(transformed.balanceSheet.retainedEarnings, 'totalEquity');
        const paddedTSE = pad(transformed.balanceSheet.totalShareholdersEquity, 'totalEquity');
        const paddedTLE = pad(transformed.balanceSheet.totalLiabilitiesEquity, 'totalEquity');

        // Compute balance check: Assets - Liabilities - Equity (should be ~0)
        const paddedBC = paddedTA.map((a: number, i: number) =>
          a - (paddedTL[i] || 0) - (paddedTSE[i] || 0)
        );

        transformed.balanceSheet = {
          ...transformed.balanceSheet,
          cash: paddedCash,
          accountsReceivable: paddedAR,
          inventories: paddedInv,
          totalCurrentAssets: paddedTCA,
          ppeGross: paddedPPE,
          totalAssets: paddedTA,
          accountsPayable: paddedAP,
          revolvingCredit: paddedRevolver,
          totalCurrentLiabilities: paddedTCL,
          longTermDebt: paddedLTD,
          totalLiabilities: paddedTL,
          commonEquity: paddedCE,
          retainedEarnings: paddedRE,
          totalShareholdersEquity: paddedTSE,
          totalLiabilitiesEquity: paddedTLE,
          balanceCheck: paddedBC,
        };

        setOutput(transformed);
        setScheduleStatus(res.schedule_status || {});
        setAllSchedulesOk(res.all_schedules_ok || false);
        setApiWarnings(res.warnings || []);
      }
    } catch (err: any) {
      console.error('Backend building blocks calculation failed:', err);
      setApiWarnings([err?.response?.data?.detail || err.message || 'Calculation failed']);
    } finally {
      setApiLoading(false);
    }
  }, [recalcKey, sessionId, selectedScenario, selectedModel, market, buildAssumptionOverrides]);

  const validation = useMemo(() => validateDCFInputs(inputs), [inputs]);

  // ─── Field Change Handler ─────────────────────────────────────────────────
  const handleFieldChange = useCallback((field: keyof DCFInputs, value: number) => {
    setInputs(prev => ({ ...prev, [field]: value }));

    // Also propagate to store via onManualInput
    const storeKey = `dcf_${field}`;
    onManualInput(storeKey, value);
  }, [onManualInput]);

  const handleArrayFieldChange = useCallback((field: keyof DCFInputs, index: number, value: number) => {
    setInputs(prev => {
      const arr = [...(prev[field] as number[])];
      arr[index] = value;
      return { ...prev, [field]: arr };
    });

    const storeKey = `forecast_${selectedScenario}_${field}_${index}`;
    onManualInput(storeKey, value);
  }, [onManualInput, selectedScenario]);

  // ─── Confirm Handler ──────────────────────────────────────────────────────
  const handleConfirm = async () => {
    // Flush all current inputs to store with normalized decimal values
    const PCT_FIELDS = new Set([
      'wacc', 'riskFreeRate', 'equityRiskPremium', 'costOfDebt',
      'taxRate', 'terminalGrowthRate', 'dividendPayoutRatio',
      'cashInterestRate', 'revolvingCreditRate', 'ltDebtInterestRate',
      'firstYearDepreciationRate', 'firstYearTaxDepRate', 'blendedTaxDepRate', 'firstYearAcctgDepRate',
    ]);
    Object.keys(inputs).forEach(key => {
      const val = (inputs as any)[key];
      if (Array.isArray(val)) {
        val.forEach((v: number, i: number) => {
          onManualInput(`forecast_${selectedScenario}_${key}_${i}`, v);
        });
      } else if (typeof val === 'number') {
        // Ensure percentage fields are in decimal format before sending to backend
        const normalized = PCT_FIELDS.has(key) ? normalizeDecimal(val, 0, 1) : val;
        onManualInput(`dcf_${key}`, normalized);
      }
    });
    await onConfirmAssumptions();
  };

  // ─── Cross-Reference Highlight ─────────────────────────────────────────────
  const [selectedFieldId, setSelectedFieldId] = useState<string | null>(null);

  // Reference graph: fieldId → { from: [upstream fieldIds], to: [downstream fieldIds] }
  const referenceGraph = useMemo(() => ({
    // Income Statement
    revenue:               { from: [], to: ['grossProfit', 'arBalance', 'totalCurrentAssets'] },
    cogs:                  { from: [], to: ['grossProfit', 'invBalance', 'apBalance'] },
    grossProfit:           { from: ['revenue', 'cogs'], to: ['ebitda'] },
    sga:                   { from: [], to: ['ebitda'] },
    otherOpex:             { from: [], to: ['ebitda'] },
    ebitda:                { from: ['grossProfit', 'sga', 'otherOpex'], to: ['ebit'] },
    depreciation_is:       { from: [], to: ['ebit', 'depreciation_dep'] },
    ebit:                  { from: ['ebitda', 'depreciation_is'], to: ['ebt', 'taxUnlevered'] },
    interestExpense:       { from: ['ltInterest'], to: ['ebt'] },
    ebt:                   { from: ['ebit', 'interestExpense'], to: ['currentTax', 'taxableIncome'] },
    currentTax:            { from: ['taxableIncome'], to: ['netIncome'] },
    totalTax:              { from: ['ebt'], to: ['netIncome'] },
    netIncome:             { from: ['ebt', 'totalTax'], to: ['retainedEarnings', 'dividends', 'cfsNetIncome'] },
    // Working Capital
    arBalance:             { from: ['revenue'], to: ['nwc'] },
    invBalance:            { from: ['cogs'], to: ['nwc'] },
    apBalance:             { from: ['cogs'], to: ['nwc'] },
    nwc:                   { from: ['arBalance', 'invBalance', 'apBalance'], to: ['changeInNwc'] },
    changeInNwc:           { from: ['nwc'], to: ['cfo'] },
    // Depreciation
    capex:                 { from: [], to: ['existingAssetDep', 'newAssetDep', 'ppeEnding', 'taxBasisEnding', 'capitalExpenditure'] },
    existingAssetDep:      { from: ['capex'], to: ['totalDepreciation', 'depreciation_is'] },
    newAssetDep:           { from: ['capex'], to: ['totalDepreciation', 'depreciation_is'] },
    totalDepreciation:     { from: ['existingAssetDep', 'newAssetDep'], to: ['ppeEnding', 'depreciation_is'] },
    // Asset Schedule
    ppeEnding:             { from: ['capex', 'totalDepreciation'], to: ['totalAssets'] },
    taxBasisEnding:        { from: ['capex', 'taxDepreciation'], to: [] },
    taxDepreciation:       { from: ['taxBasisEnding', 'capex'], to: ['ebtAdjusted'] },
    // Tax Levered
    ebtEbit:               { from: ['ebt'], to: ['ebtAdjusted'] },
    ebtAdjusted:           { from: ['ebtEbit', 'accountingDep', 'taxDep'], to: ['taxableIncome'] },
    taxableIncome:         { from: ['ebtAdjusted', 'nolUsed'], to: ['currentTax'] },
    nolUsed:               { from: ['nolOpening'], to: ['taxableIncome'] },
    // CFS
    cfsNetIncome:          { from: ['netIncome'], to: ['cfo'] },
    deferredTaxes:         { from: [], to: ['cfo'] },
    cfo:                   { from: ['cfsNetIncome', 'totalDepreciation', 'deferredTaxes', 'changeInNwc'], to: ['fcf', 'endingCash'] },
    capitalExpenditure:    { from: ['capex'], to: ['cfi', 'fcf'] },
    cfi:                   { from: ['capitalExpenditure'], to: ['fcf', 'endingCash'] },
    cff:                   { from: [], to: ['endingCash'] },
    fcf:                   { from: ['cfo', 'cfi'], to: [] },
    endingCash:            { from: ['cfo', 'cfi', 'cff'], to: ['cash_bs', 'openingCash'] },
    // Balance Sheet
    cash_bs:               { from: ['endingCash'], to: ['totalCurrentAssets', 'totalAssets'] },
    ar_bs:                 { from: ['arBalance'], to: ['totalCurrentAssets', 'totalAssets'] },
    inv_bs:                { from: ['invBalance'], to: ['totalCurrentAssets', 'totalAssets'] },
    totalCurrentAssets:    { from: ['cash_bs', 'ar_bs', 'inv_bs'], to: ['totalAssets'] },
    totalAssets:           { from: ['totalCurrentAssets', 'ppeEnding'], to: ['balanceCheck'] },
    ap_bs:                 { from: ['apBalance'], to: ['totalCurrentLiabilities'] },
    totalCurrentLiab:      { from: ['ap_bs'], to: ['totalLiabilities'] },
    ltDebt_bs:             { from: ['ltDebtBalance'], to: ['totalLiabilities', 'totalAssets'] },
    totalLiabilities:      { from: ['totalCurrentLiab', 'ltDebt_bs'], to: ['balanceCheck'] },
    retainedEarnings:      { from: ['netIncome', 'dividends'], to: ['totalSE'] },
    totalSE:               { from: ['retainedEarnings'], to: ['balanceCheck'] },
    balanceCheck:          { from: ['totalAssets', 'totalLiabilities', 'totalSE'], to: [] },
    // Debt Part 1
    openingCash:           { from: ['endingCash'], to: ['cashInterestIncome'] },
    cashInterestIncome:    { from: ['openingCash'], to: [] },
    ltDebtBalance:         { from: [], to: ['ltInterest', 'netDebt', 'ltDebt_bs'] },
    netDebt:               { from: ['ltDebtBalance', 'openingCash'], to: [] },
    // Debt Part 2
    ltInterest:            { from: ['ltDebtBalance'], to: ['netInterest', 'interestExpense'] },
    netInterest:           { from: ['ltInterest'], to: ['totalInterestExpense'] },
    totalInterestExpense:  { from: ['netInterest'], to: ['interestExpense'] },
    // Equity
    commonEquity:          { from: [], to: ['totalSE'] },
    dividends:             { from: ['netIncome'], to: ['retainedEarnings', 'cff'] },
  }), []);

  // Compute upstream and downstream fields for selected field
  const { upstreamFields, downstreamFields } = useMemo(() => {
    if (!selectedFieldId) return { upstreamFields: new Set<string>(), downstreamFields: new Set<string>() };
    const upstream = new Set<string>();
    const downstream = new Set<string>();

    // BFS upstream
    const queueUp = [selectedFieldId];
    const visitedUp = new Set<string>();
    while (queueUp.length > 0) {
      const current = queueUp.shift()!;
      if (visitedUp.has(current)) continue;
      visitedUp.add(current);
      const node = referenceGraph[current as keyof typeof referenceGraph];
      if (node) {
        for (const dep of node.from) {
          if (!visitedUp.has(dep)) {
            upstream.add(dep);
            queueUp.push(dep);
          }
        }
      }
    }

    // BFS downstream
    const queueDown = [selectedFieldId];
    const visitedDown = new Set<string>();
    while (queueDown.length > 0) {
      const current = queueDown.shift()!;
      if (visitedDown.has(current)) continue;
      visitedDown.add(current);
      const node = referenceGraph[current as keyof typeof referenceGraph];
      if (node) {
        for (const dep of node.to) {
          if (!visitedDown.has(dep)) {
            downstream.add(dep);
            queueDown.push(dep);
          }
        }
      }
    }

    return { upstreamFields: upstream, downstreamFields: downstream };
  }, [selectedFieldId, referenceGraph]);

  const handleFieldClick = useCallback((fieldId: string) => {
    setSelectedFieldId(prev => prev === fieldId ? null : fieldId);
  }, []);

  // ─── Shared Equity Computation ───────────────────────────────────────────
  // Single source of truth for [3H] Balance Sheet and [3K] Equity Schedule
  const sharedEquity = useMemo(() => {
    if (!output?.incomeStatement) return { ceAll: [], reAll: [], totalEq: [], csOpening: [], csEnding: [], reOpening: [], reEnding: [] };
    const n = ALL_PERIODS.length;
    const hLen = HIST_PERIODS.length;

    const ceAll = new Array(n).fill(0);
    const reAll = new Array(n).fill(0);
    const csOpening = new Array(n).fill(0);
    const csEnding = new Array(n).fill(0);
    const reOpening = new Array(n).fill(0);
    const reEnding = new Array(n).fill(0);
    // Common Equity in the display = Contributed Capital (Total Equity − Retained Earnings).
    // The backend DCF engine's `common_equity` tracks total equity, NOT contributed capital,
    // so for historical periods we MUST use historical.commonEquity (which the backend now
    // correctly computes as shareholders_equity − retained_earnings).
    // For forecast periods, the DCF engine's value is fine since it's the projected balance.
    const totalEq = output.balanceSheet?.totalShareholdersEquity || new Array(n).fill(0);

    // Historical periods — use historical.commonEquity (contributed capital) for Common Equity
    for (let i = 0; i < hLen; i++) {
      ceAll[i] = historical.commonEquity?.[i] ?? 0;
      csOpening[i] = i === 0 ? ceAll[i] : csEnding[i - 1];
      csEnding[i] = csOpening[i]; // No SBC
      reOpening[i] = i === 0 ? (output.balanceSheet?.retainedEarnings?.[i] ?? historical.retainedEarnings[i] ?? 0) : reEnding[i - 1];
      reEnding[i] = reOpening[i] + (output.incomeStatement.netIncome?.[i] ?? 0) - (historical.dividendsPaid[i] ?? 0) + (historical.shareBuybacks?.[i] ?? 0);
      reAll[i] = reEnding[i];
    }

    // Forecast periods — use DCF engine's commonEquity (projected balance)
    for (let i = 0; i < 5; i++) {
      const p = hLen + i;
      ceAll[p] = output.balanceSheet?.commonEquity?.[p] ?? ceAll[hLen - 1];
      csOpening[p] = p > 0 ? csEnding[p - 1] : ceAll[hLen - 1];
      csEnding[p] = csOpening[p];
      const prevRe = p > 0 ? reAll[p - 1] : reAll[hLen - 1];
      const ni = output.incomeStatement.netIncome?.[p] ?? 0;
      const div = ni * (inputs.dividendPayoutRatio || 0);
      reAll[p] = output.balanceSheet?.retainedEarnings?.[p] ?? (prevRe + ni - div);
      reOpening[p] = prevRe;
      reEnding[p] = reAll[p];
    }

    // Terminal = last forecast
    const last = hLen + 4;
    ceAll[n - 1] = output.balanceSheet?.commonEquity?.[n - 1] ?? ceAll[last];
    csOpening[n - 1] = csEnding[last]; csEnding[n - 1] = csOpening[n - 1];
    reAll[n - 1] = output.balanceSheet?.retainedEarnings?.[n - 1] ?? reAll[last];
    reOpening[n - 1] = reEnding[last]; reEnding[n - 1] = reAll[n - 1];

    return { ceAll, reAll, totalEq, csOpening, csEnding, reOpening, reEnding };
  }, [output, historical, ALL_PERIODS.length, HIST_PERIODS.length, inputs]);

  // ─── Schedule Table Data ──────────────────────────────────────────────────

  // Helper: pad historical array to ALL_PERIODS.length with zeros for forecast years
  const padHistOnly = (histArr: number[]): number[] => {
    const result = [...histArr];
    while (result.length < ALL_PERIODS.length) result.push(0);
    return result;
  };

  const incomeStatementRows = useMemo(() => {
    if (!output?.incomeStatement) return [];
    const hLen = HIST_PERIODS.length;
    const n = ALL_PERIODS.length;
    const histRefs = (output as any)?.historicalReferences;

    // R&D: historical from backend historicalReferences, forecast = last hist × opex growth
    const histRnD = padHistOnly(histRefs?.researchDevelopment || []);
    const rdAll = new Array(n).fill(0);
    for (let i = 0; i < hLen; i++) rdAll[i] = histRnD[i] || 0;
    const lastRd = histRnD[hLen - 1] || 0;
    for (let i = 0; i < 6; i++) {
      const p = hLen + i;
      if (p < n) rdAll[p] = i === 0 ? lastRd : rdAll[p - 1] * (1 + (inputs.opexGrowthRate?.[i] || 0.05));
    }

    // Total OpEx = SG&A + R&D + Other OpEx (all periods)
    const totalOpEx = new Array(n).fill(0);
    for (let i = 0; i < n; i++) {
      totalOpEx[i] = (output.incomeStatement.sga?.[i] || 0) + rdAll[i] + (output.incomeStatement.otherOpex?.[i] || 0);
    }

    // Interest Income: from backend interest schedule (forecast periods)
    // For historical: may not be separately available — use Other Income/Expense as combined parent
    const intSched = (output as any)?.interestSchedule;
    const intIncomeForecast = intSched?.cashInterestIncome || [];
    // Interest Expense: from backend (forecast from debt schedules)
    const intExpForecast = output.incomeStatement.interestExpense || [];
    // Other Income/Expense: combined parent for historical (interest income + interest expense)
    const histOtherIncExp = padHistOnly(histRefs?.otherIncomeExpense || []);

    // Build combined rows: historical uses Other Income/Expense (combined),
    // forecast splits into Interest Income and Interest Expense from our schedules
    const combinedInterestRows = (() => {
      const n = ALL_PERIODS.length;
      const intIncomeAll = new Array(n).fill(0);
      const intExpAll = new Array(n).fill(0);
      const otherIncExpAll = new Array(n).fill(0);

      // Historical periods: use Other Income/Expense as the combined figure
      for (let i = 0; i < hLen; i++) {
        otherIncExpAll[i] = histOtherIncExp[i] ?? 0;
      }
      // Forecast periods: split into Interest Income and Interest Expense from debt schedules
      for (let i = hLen; i < n; i++) {
        const fIdx = i - hLen;
        intIncomeAll[i] = intIncomeForecast[fIdx] ?? 0;
        intExpAll[i] = intExpForecast[fIdx] ?? 0;
      }
      return { intIncomeAll, intExpAll, otherIncExpAll };
    })();

    return [
      { label: 'Revenue', values: output.incomeStatement.revenue, calculatedValues: backendCalc?.revenue, isHighlight: true, fieldId: 'revenue', formula: 'FY1 = Hist_Rev × (1 + G1)...' },
      { label: 'COGS', values: output.incomeStatement.cogs, calculatedValues: backendCalc?.cogs, fieldId: 'cogs', formula: 'FY1 = Hist_COGS × (1 + I1)...' },
      { label: 'Gross Profit', values: output.incomeStatement.grossProfit, calculatedValues: backendCalc?.grossProfit, fieldId: 'grossProfit', formula: 'Revenue − COGS' },
      { label: 'SG&A', values: output.incomeStatement.sga, calculatedValues: backendCalc?.sga, fieldId: 'sga', formula: 'Hist_SGA × (1 + OpEx Growth).' },
      { label: 'R&D Expense', values: rdAll, calculatedValues: rdAll, fieldId: 'rdExpense', formula: 'Hist from XBRL. Forecast: last hist × opex growth.' },
      { label: 'Total Operating Expenses', values: totalOpEx, calculatedValues: totalOpEx, isHighlight: true, formula: 'SG&A + R&D + Other OpEx.' },
      { label: 'Other OpEx', values: output.incomeStatement.otherOpex, calculatedValues: backendCalc?.otherOpex, fieldId: 'otherOpex', formula: 'Hist_Other × (1 + Inflation).' },
      { label: 'EBITDA', values: output.incomeStatement.ebitda, calculatedValues: backendCalc?.ebitda, isHighlight: true, fieldId: 'ebitda', formula: 'Gross Profit − Total OpEx' },
      { label: 'Depreciation', values: output.incomeStatement.depreciation, calculatedValues: backendCalc?.depreciation, fieldId: 'depreciation_is', formula: 'Existing Dep + New Dep. → [3D] Depreciation Schedule.' },
      { label: 'EBIT', values: output.incomeStatement.ebit, calculatedValues: backendCalc?.ebit, fieldId: 'ebit', formula: 'EBITDA − Depreciation' },
      // Other Income/Expense: historical = combined parent (interest income + interest expense)
      { label: 'Other Income/Expense', values: combinedInterestRows.otherIncExpAll, isReference: true, formula: 'Hist: combined interest income + expense. Forecast: split below.' },
      // Interest Income & Expense: forecast from our debt schedules [3I] [3J]
      { label: 'Interest Income', values: combinedInterestRows.intIncomeAll, formula: 'Forecast: Cash × Cash Rate → [3I]. Hist: from Other Income/Expense.' },
      { label: 'Interest Expense', values: combinedInterestRows.intExpAll, calculatedValues: backendCalc?.interestExpense, fieldId: 'interestExpense', formula: 'Forecast: LT Debt × Rate − Cash × Rate → [3J].' },
      { label: 'EBT', values: output.incomeStatement.ebt, calculatedValues: backendCalc?.ebt, fieldId: 'ebt', formula: 'EBIT − Net Interest (Interest Expense − Interest Income)' },
      { label: 'Current Tax', values: output.incomeStatement.currentTax, calculatedValues: backendCalc?.currentTax, fieldId: 'currentTax', formula: 'Taxable Income × Tax Rate.' },
      { label: 'Deferred Tax', values: output.incomeStatement.deferredTax, calculatedValues: backendCalc?.deferredTax, formula: 'Total Tax − Current Tax.' },
      { label: 'Total Tax', values: output.incomeStatement.totalTax, calculatedValues: backendCalc?.totalTax, fieldId: 'totalTax', formula: 'EBT Adjusted × Tax Rate.' },
      { label: 'Net Income', values: output.incomeStatement.netIncome, calculatedValues: backendCalc?.netIncome, isHighlight: true, fieldId: 'netIncome', formula: 'EBT − Total Tax' },
    ];
  }, [output, historical, HIST_PERIODS.length, ALL_PERIODS.length, inputs, backendCalc]);

  const workingCapitalRows = useMemo(() => {
    if (!output?.workingCapital) return [];
    const hLen = HIST_PERIODS.length;
    // For balance rows: show historical actuals (from XBRL) in hist columns,
    // engine-calculated values as calculatedValues for comparison
    const wcArHist = output.workingCapital.arBalance.map((v: number, i: number) => i < hLen ? (historical.ar?.[i] ?? v) : v);
    const wcInvHist = output.workingCapital.inventoryBalance.map((v: number, i: number) => i < hLen ? (historical.inventory?.[i] ?? v) : v);
    const wcApHist = output.workingCapital.apBalance.map((v: number, i: number) => i < hLen ? (historical.ap?.[i] ?? v) : v);
    // Use backend values directly — no frontend computation
    const wcNwcHist = output.workingCapital.nwc || wcArHist.map((ar: number, i: number) => (ar || 0) + (wcInvHist[i] || 0) - (wcApHist[i] || 0));
    const wcChangeNwc = output.workingCapital.changeInNwc || wcNwcHist.map((nwc: number, i: number) => i === 0 ? 0 : nwc - (wcNwcHist[i - 1] || 0));
    return [
      { label: 'AR Days', values: output.workingCapital.arDays, calculatedValues: output.workingCapital.arDays, formula: 'Constant from inputs. Hist: (AR/Rev)×365.' },
      { label: 'Inventory Days', values: output.workingCapital.invDays, calculatedValues: output.workingCapital.invDays, formula: 'Constant from inputs. Hist: (Inv/COGS)×365.' },
      { label: 'AP Days', values: output.workingCapital.apDays, calculatedValues: output.workingCapital.apDays, formula: 'Constant from inputs. Hist: (AP/COGS)×365.' },
      { label: 'AR Balance', values: wcArHist, calculatedValues: output.workingCapital.arBalance, fieldId: 'arBalance', formula: '(AR Days / 365) × Revenue' },
      { label: 'Inventory Balance', values: wcInvHist, calculatedValues: output.workingCapital.inventoryBalance, fieldId: 'invBalance', formula: '(Inv Days / 365) × COGS' },
      { label: 'AP Balance', values: wcApHist, calculatedValues: output.workingCapital.apBalance, fieldId: 'apBalance', formula: '(AP Days / 365) × COGS' },
      { label: 'Net Working Capital', values: wcNwcHist, calculatedValues: output.workingCapital.nwc, isHighlight: true, fieldId: 'nwc', formula: 'AR + Inventory − AP' },
      { label: 'Change in NWC', values: wcChangeNwc, calculatedValues: output.workingCapital.changeInNwc, isHighlight: true, fieldId: 'changeInNwc', formula: 'NWC[t] − NWC[t-1]. Positive = cash outflow.' },
    ];
  }, [output, historical, HIST_PERIODS.length]);

  // ─── Shared PP&E Gross & Accumulated Depreciation (single source of truth for [3C], [3D], [3H]) ──
  const sharedPpeGross = useMemo(() => {
    return output?.depreciation?.grossPpeEnding || output?.balanceSheet?.ppeGross || [];
  }, [output]);

  const sharedAccumDep = useMemo(() => {
    if (!output?.depreciation) return [];
    const n = ALL_PERIODS.length;
    const hLen = HIST_PERIODS.length;
    const arr = new Array(n).fill(0);
    for (let i = 0; i < hLen; i++) {
      const rawAD = historical.accumulatedDepreciation?.[i] ?? 0;
      arr[i] = rawAD <= 0 ? rawAD : -rawAD; // Ensure negative
    }
    // If all historical values are 0, compute from total depreciation
    const hasHistAD = arr.some((v, i) => i < hLen && v !== 0);
    if (!hasHistAD) {
      let running = 0;
      for (let i = 0; i < hLen; i++) {
        const dep = historical.depreciation?.[i] ?? 0;
        running = running - dep;
        arr[i] = running;
      }
    }
    let running = arr[hLen - 1] ?? 0;
    for (let i = hLen; i < n; i++) {
      const dep = output.depreciation?.totalDepreciation?.[i - hLen] ?? 0;
      running = running - dep;
      arr[i] = running;
    }
    return arr;
  }, [output, historical, ALL_PERIODS.length]);

  const depreciationRows = useMemo(() => {
    if (!output?.depreciation) return [];
    const allPeriodCount = ALL_PERIODS.length;
    const ppeGrossPadded = sharedPpeGross;
    const hLen = HIST_PERIODS.length;
    
    // Accumulated Depreciation — stored as NEGATIVE (contra-asset convention)
    // Formula: Prior Accum Dep − Current Total Depreciation (gets more negative each year)
    // Historical: yfinance returns negative values; use as-is
    const accumDepValues = sharedAccumDep;

    // Helper: extract a field from completeFinancialStatements (period-keyed → list)
    const extractFromComplete = (section: string, field: string): number[] => {
      if (!completeFinancialStatements) return [];
      const sec = completeFinancialStatements[section];
      if (!sec || typeof sec !== 'object') return [];
      // Try field-keyed first (after transpose): { field: { period: value } }
      if (sec[field] && typeof sec[field] === 'object' && !Array.isArray(sec[field])) {
        const periodData = sec[field];
        const periods = Object.keys(periodData).sort();
        return periods.map(p => {
          const v = periodData[p];
          if (typeof v === 'number') return v;
          if (typeof v === 'object' && v?.value !== undefined) return Number(v.value) || 0;
          return 0;
        }).filter(v => v !== 0);
      }
      // Try period-keyed: { period: { field: value } }
      const periods = Object.keys(sec).sort().filter(k => /^\d{4}/.test(k));
      if (periods.length > 0) {
        return periods.map(p => {
          const periodData = sec[p];
          const v = periodData?.[field];
          if (typeof v === 'number') return v;
          if (typeof v === 'object' && v?.value !== undefined) return Number(v.value) || 0;
          return 0;
        }).filter(v => v !== 0);
      }
      return [];
    };

    // Build full-period CapEx: historical from actuals + forecast from backend
    const histCapexFallback = extractFromComplete('cash_flow', 'capex');
    const histDepFallback = extractFromComplete('income_statement', 'depreciation');
    const allCapex = new Array(allPeriodCount).fill(0);
    for (let i = 0; i < hLen; i++) {
      allCapex[i] = historical.capex?.[i] ?? histCapexFallback[i] ?? 0;
    }
    for (let i = hLen; i < allPeriodCount; i++) {
      allCapex[i] = output.depreciation.capex?.[i - hLen] ?? 0;
    }
    // Build full-period Existing Asset Dep: historical from actuals + forecast from backend
    const allExistingDep = new Array(allPeriodCount).fill(0);
    for (let i = 0; i < hLen; i++) {
      // Historical: all depreciation is on existing assets (new = 0)
      allExistingDep[i] = historical.depreciation?.[i] ?? histDepFallback[i] ?? 0;
    }
    for (let i = hLen; i < allPeriodCount; i++) {
      allExistingDep[i] = output.depreciation.existingAssetDep?.[i - hLen] ?? 0;
    }
    // Build full-period New Asset Dep: 0 for historical, forecast from backend
    const allNewDep = new Array(allPeriodCount).fill(0);
    for (let i = hLen; i < allPeriodCount; i++) {
      allNewDep[i] = output.depreciation.newAssetDep?.[i - hLen] ?? 0;
    }
    // Build full-period Total Depreciation: historical from actuals + forecast from backend
    const allTotalDep = new Array(allPeriodCount).fill(0);
    for (let i = 0; i < hLen; i++) {
      allTotalDep[i] = historical.depreciation?.[i] ?? 0;
    }
    for (let i = hLen; i < allPeriodCount; i++) {
      allTotalDep[i] = output.depreciation.totalDepreciation?.[i - hLen] ?? 0;
    }

    return [
      // [3E] Depreciation Schedule (Excel rows 180-206)
      { label: 'Capital Expenditure', values: allCapex, calculatedValues: allCapex, isHighlight: true, fieldId: 'capex', formula: 'From Step 8 inputs. CHOOSE scenario capex. Terminal = Terminal Dep.' },
      { label: 'Useful Life — Existing (Ref)', values: new Array(allPeriodCount).fill(inputs.usefulLifeExisting), isReference: true, formula: 'Opening PPE / Useful Life (straight-line).' },
      { label: 'Useful Life — New (Ref)', values: new Array(allPeriodCount).fill(inputs.usefulLifeNew), isReference: true, formula: 'SL depreciation period for new asset cohorts.' },
      { label: 'First Year Acctg Dep Rate (Ref)', values: new Array(allPeriodCount).fill(inputs.firstYearDepreciationRate || 50), isReference: true, formula: 'Half-year convention: 50% first year.' },
      { label: 'Existing Asset Dep', values: allExistingDep, calculatedValues: allExistingDep, fieldId: 'existingAssetDep', formula: 'Opening PP&E / Useful Life. Decreases as assets fully depreciate.' },
      { label: 'New Asset Dep', values: allNewDep, calculatedValues: allNewDep, fieldId: 'newAssetDep', formula: 'CapEx cohorts: First=CapEx/Life×50%, Subsequent=CapEx/Life. Sum of all active cohorts.' },
      { label: 'Total Depreciation', values: allTotalDep, calculatedValues: allTotalDep, isHighlight: true, fieldId: 'totalDepreciation', formula: 'Existing Asset Dep + New Asset Dep → feeds IS Depreciation.' },
      // PP&E Roll
      { label: 'PP&E Gross', values: ppeGrossPadded, calculatedValues: output.depreciation.grossPpeEnding, fieldId: 'ppeEnding', formula: 'Hist from XBRL. Forecast: Prior + CapEx. Only increases with CapEx.' },
      { label: 'Accumulated Depreciation', values: accumDepValues, calculatedValues: accumDepValues, formula: 'Hist from XBRL. Forecast: Prior + Total Dep. Cumulative depreciation pool.' },
      { label: 'PP&E Net', values: ppeGrossPadded.map((g: number, i: number) => (g || 0) + (accumDepValues[i] || 0)), isHighlight: true, fieldId: 'ppeNet', formula: 'PP&E Gross + Accumulated Dep. (negative) → feeds BS.' },
    ];
  }, [output, inputs, ALL_PERIODS.length]);

  const assetRows = useMemo(() => {
    if (!output?.depreciation) return [];
    const allPeriodCount = ALL_PERIODS.length;
    const hLen = HIST_PERIODS.length;
    
    // PP&E Opening Balance — prior period's ending balance
    const ppeGrossData = sharedPpeGross;
    const ppeOpening = new Array(allPeriodCount).fill(0);
    // First historical period: compute from ending balance
    // Opening = Ending - CapEx + Depreciation (reversing the roll-forward)
    const firstEnd = ppeGrossData[0] ?? 0;
    const firstCapex = historical.capex?.[0] ?? 0;
    const firstDep = historical.depreciation?.[0] ?? 0;
    ppeOpening[0] = firstEnd - firstCapex + firstDep;
    for (let i = 1; i < allPeriodCount; i++) {
      ppeOpening[i] = ppeGrossData[i - 1] ?? 0;
    }
    
    // Helper: extract a field from completeFinancialStatements (period-keyed → list)
    const extractFromCS = (section: string, field: string): number[] => {
      if (!completeFinancialStatements) return [];
      const sec = completeFinancialStatements[section];
      if (!sec || typeof sec !== 'object') return [];
      if (sec[field] && typeof sec[field] === 'object' && !Array.isArray(sec[field])) {
        const periodData = sec[field];
        const periods = Object.keys(periodData).sort();
        return periods.map(p => {
          const v = periodData[p];
          if (typeof v === 'number') return v;
          if (typeof v === 'object' && v?.value !== undefined) return Number(v.value) || 0;
          return 0;
        }).filter(v => v !== 0);
      }
      const periods = Object.keys(sec).sort().filter(k => /^\d{4}/.test(k));
      if (periods.length > 0) {
        return periods.map(p => {
          const periodData = sec[p];
          const v = periodData?.[field];
          if (typeof v === 'number') return v;
          if (typeof v === 'object' && v?.value !== undefined) return Number(v.value) || 0;
          return 0;
        }).filter(v => v !== 0);
      }
      return [];
    };
    const histCapexCS = extractFromCS('cash_flow', 'capex');
    const histDepCS = extractFromCS('income_statement', 'depreciation');

    // PP&E CapEx — historical from actuals + forecast from backend
    const ppeCapex = new Array(allPeriodCount).fill(0);
    for (let i = 0; i < hLen; i++) {
      ppeCapex[i] = historical.capex?.[i] ?? histCapexCS[i] ?? 0;
    }
    for (let i = hLen; i < allPeriodCount; i++) {
      ppeCapex[i] = output.depreciation.capex?.[i - hLen] ?? 0;
    }
    
    // PP&E Accounting Depreciation — historical from actuals + forecast from backend
    const ppeAcctgDep = new Array(allPeriodCount).fill(0);
    for (let i = 0; i < hLen; i++) {
      ppeAcctgDep[i] = historical.depreciation?.[i] ?? histDepCS[i] ?? 0;
    }
    for (let i = hLen; i < allPeriodCount; i++) {
      ppeAcctgDep[i] = output.depreciation.totalDepreciation?.[i - hLen] ?? 0;
    }
    
    const ppeNetAsset = ppeGrossData.map((gross: number, i: number) => (gross || 0) + (sharedAccumDep[i] || 0));
    
    // Tax Basis Opening Balance
    const taxBasisOpening = new Array(allPeriodCount).fill(0);
    taxBasisOpening[0] = inputs.taxBasisPpe;
    for (let i = 1; i < allPeriodCount; i++) {
      taxBasisOpening[i] = output.depreciation.taxBasisEnding?.[i - 1] ?? 0;
    }
    
    // Tax Depreciation (forecast from backend)
    const taxDepArr = output.depreciation.taxDepreciation || [];
    
    return [
      // [3D] PP&E Roll — Opening + CapEx − Acctg Dep = Ending
      { label: 'PP&E Opening', values: ppeOpening, isReference: true, formula: 'Prior year ending PP&E Gross. First period = opening balance.' },
      { label: '+ CapEx', values: ppeCapex, calculatedValues: output.depreciation.capex, fieldId: 'capex', formula: 'Capital expenditure. From Depreciation Schedule [3C].' },
      { label: '− Acctg Dep', values: ppeAcctgDep.map((v: number) => -v), calculatedValues: output.depreciation.totalDepreciation?.map((v: number) => -v), formula: 'Accounting depreciation. From [3C] Total Depreciation.' },
      { label: 'PP&E Ending', values: ppeGrossData, calculatedValues: output.depreciation.grossPpeEnding, isHighlight: true, fieldId: 'ppeEnding', formula: 'Opening + CapEx − Acctg Dep. Rolls forward each year.' },
      { label: 'Accumulated Depreciation', values: sharedAccumDep, formula: 'Negative pool: Prior − Total Dep. → feeds BS.' },
      { label: 'PP&E Net', values: ppeNetAsset, isHighlight: true, fieldId: 'ppeNet', formula: 'PP&E Gross + Accumulated Dep. (negative) → feeds BS Total Assets.' },
      // Tax Basis Roll — Opening + CapEx − Tax Dep = Ending
      { label: 'Tax Basis Opening', values: taxBasisOpening, isReference: true, formula: 'Prior year ending tax basis. First period = opening balance.' },
      { label: '+ CapEx (Tax)', values: ppeCapex, formula: 'Same CapEx as accounting.' },
      { label: '− Tax Dep', values: taxDepArr.map((v: number) => -v), calculatedValues: output.depreciation.taxDepreciation?.map((v: number) => -v), formula: 'Tax depreciation deduction. From [3C] Tax Depreciation.' },
      { label: 'Tax Basis Ending', values: output.depreciation.taxBasisEnding, calculatedValues: output.depreciation.taxBasisEnding, isHighlight: true, fieldId: 'taxBasisEnding', formula: 'Opening + CapEx − Tax Dep. Declining balance.' },
    ];
  }, [output, inputs, ALL_PERIODS.length, historical]);

  const taxLeveredRows = useMemo(() => {
    if (!output?.taxLevered) return [];
    const n = ALL_PERIODS.length;
    // NOL Ending = Opening + New − Used
    const nolEnding = output.taxLevered.nolOpening.map((o: number, i: number) =>
      (o || 0) + (output.taxLevered.nolNew?.[i] || 0) - (output.taxLevered.nolUsed?.[i] || 0)
    );
    // Use backend values directly — no frontend computation
    const totalTax = output.taxLevered.totalTax || output.taxLevered.currentTax.map((ct: number, i: number) =>
      (ct || 0) + (output.taxLevered.deferredTax?.[i] || 0)
    );
    return [
      { label: 'EBT/EBIT', values: output.taxLevered.ebtEbit, calculatedValues: output.taxLevered.ebtEbit, fieldId: 'ebtEbit', formula: 'From IS. Starting point for tax calc.' },
      { label: 'Tax Rate (Ref)', values: new Array(n).fill(inputs.taxRate * 100), isReference: true, formula: 'Statutory tax rate applied to taxable income.' },
      { label: '+ Accounting Dep', values: output.taxLevered.accountingDep, calculatedValues: output.taxLevered.accountingDep, formula: 'Add back non-cash accounting dep.' },
      { label: '− Tax Dep', values: output.taxLevered.taxDep, calculatedValues: output.taxLevered.taxDep, formula: 'Subtract actual tax deduction.' },
      { label: 'EBT Adjusted', values: output.taxLevered.ebtAdjusted, calculatedValues: output.taxLevered.ebtAdjusted, fieldId: 'ebtAdjusted', formula: 'EBT + Acctg Dep − Tax Dep.' },
      { label: 'Taxable Income', values: output.taxLevered.taxableIncome, calculatedValues: output.taxLevered.taxableIncome, fieldId: 'taxableIncome', formula: 'max(EBT Adj − NOL Used, 0).' },
      { label: 'NOL Opening', values: output.taxLevered.nolOpening, formula: 'NOL carryforward at start of year.' },
      { label: 'NOL New', values: output.taxLevered.nolNew, formula: 'New NOL if EBT Adj < 0.' },
      { label: 'NOL Used', values: output.taxLevered.nolUsed, fieldId: 'nolUsed', formula: 'min(NOL Balance, EBT Adj × Limit).' },
      { label: 'NOL Ending', values: nolEnding, formula: 'Opening + New − Used. Carryforward to next year.' },
      { label: 'Current Tax', values: output.taxLevered.currentTax, calculatedValues: output.taxLevered.currentTax, isHighlight: true, fieldId: 'currentTax', formula: 'Taxable Income × Tax Rate.' },
      { label: 'Deferred Tax', values: output.taxLevered.deferredTax, calculatedValues: output.taxLevered.deferredTax, formula: 'Total Tax − Current Tax. Timing difference.' },
      { label: 'Total Tax', values: totalTax, calculatedValues: totalTax, isHighlight: true, formula: 'Current Tax + Deferred Tax. → IS Total Tax.' },
    ];
  }, [output, inputs, ALL_PERIODS.length]);

  const taxUnleveredRows = useMemo(() => {
    if (!output?.taxUnlevered) return [];
    const n = ALL_PERIODS.length;
    // NOL Ending = Opening + New − Used
    const nolEndingUn = output.taxUnlevered.nolOpening.map((o: number, i: number) =>
      (o || 0) + (output.taxUnlevered.nolNew?.[i] || 0) - (output.taxUnlevered.nolUsed?.[i] || 0)
    );
    // Use backend values directly — no frontend computation
    const totalTaxUn = output.taxUnlevered.totalTax || output.taxUnlevered.currentTax.map((ct: number, i: number) =>
      (ct || 0) + (output.taxUnlevered.deferredTax?.[i] || 0)
    );
    return [
      { label: 'EBT/EBIT (= EBIT)', values: output.taxUnlevered.ebtEbit, calculatedValues: output.taxUnlevered.ebtEbit, formula: 'Starts from EBIT (not EBT). Unlevered = before interest.' },
      { label: 'Tax Rate (Ref)', values: new Array(n).fill(inputs.taxRate * 100), isReference: true, formula: 'Statutory tax rate.' },
      { label: '+ Accounting Dep', values: output.taxUnlevered.accountingDep, calculatedValues: output.taxUnlevered.accountingDep, formula: 'Add back accounting depreciation.' },
      { label: '− Tax Dep', values: output.taxUnlevered.taxDep, calculatedValues: output.taxUnlevered.taxDep, formula: 'Subtract tax depreciation.' },
      { label: 'EBT Adjusted', values: output.taxUnlevered.ebtAdjusted, calculatedValues: output.taxUnlevered.ebtAdjusted, formula: 'EBIT + Accounting Dep − Tax Dep.' },
      { label: 'Taxable Income', values: output.taxUnlevered.taxableIncome, calculatedValues: output.taxUnlevered.taxableIncome, formula: 'max(EBT Adjusted − NOL Used, 0).' },
      { label: 'NOL Opening', values: output.taxUnlevered.nolOpening, formula: 'Separate NOL pool from levered schedule.' },
      { label: 'NOL New', values: output.taxUnlevered.nolNew, formula: 'New NOL from unlevered losses.' },
      { label: 'NOL Used', values: output.taxUnlevered.nolUsed, formula: 'NOL applied to unlevered taxable income.' },
      { label: 'NOL Ending', values: nolEndingUn, formula: 'Opening + New − Used. Carryforward to next year.' },
      { label: 'Current Tax (Unlevered)', values: output.taxUnlevered.currentTax, calculatedValues: output.taxUnlevered.currentTax, isHighlight: true, formula: 'Taxable Income × Tax Rate. Used in UFCF.' },
      { label: 'Deferred Tax', values: output.taxUnlevered.deferredTax, calculatedValues: output.taxUnlevered.deferredTax, formula: 'Total Tax − Current Tax (unlevered basis).' },
      { label: 'Total Tax', values: totalTaxUn, calculatedValues: totalTaxUn, isHighlight: true, formula: 'Current Tax + Deferred Tax.' },
    ];
  }, [output, inputs, ALL_PERIODS.length]);

  // ─── [3G] Cash Flow Statement ─────────────────────────────────────────────
  const cashFlowStatementRows = useMemo(() => {
    if (!output?.cashFlowStatement) return [];
    const cfs = output.cashFlowStatement;
    // Compute derived display fields inline (not stored in type)
    // WC Change = cash from AR + cash from Inv + cash from AP (positive = cash inflow)
    const workingCapitalChange = (cfs.cashFromAr || []).map((v: number, i: number) =>
      v + (cfs.cashFromInventory?.[i] || 0) + (cfs.cashFromAp?.[i] || 0)
    );
    // Interest expense after-tax: backend stores as positive, display as negative (cash outflow)
    // Use actual tax rate from inputs instead of hardcoded 0.7
    // Use backend values directly — no frontend computation
    const afterTaxRate = 1 - (inputs.taxRate || 0.30);
    const interestExpenseAfterTax = output.cashFlowStatement?.capitalExpenditure?.map((v: number, i: number) => {
      const ie = output.incomeStatement?.interestExpense?.[i] || 0;
      return -ie * afterTaxRate;
    }) || (output.incomeStatement?.interestExpense || []).map((v: number) => -v * afterTaxRate);
    // Use backend values directly — no frontend computation
    const freeCashFlow = (cfs.subtotalCfo || []).map((v: number, i: number) =>
      v + (cfs.subtotalCfi?.[i] || 0)
    );
    // Historical-only reference rows — use backend historicalReferences if available
    const histRefsCfs = (output as any)?.historicalReferences;
    const histShareBuybacks = histRefsCfs?.shareBuybacks?.length
      ? padHistOnly(histRefsCfs.shareBuybacks)
      : padHistOnly(historical.shareBuybacks || []);
    const histDebtIssuance = histRefsCfs?.debtIssuance?.length
      ? padHistOnly(histRefsCfs.debtIssuance)
      : padHistOnly(historical.debtIssuance || []);
    const histDebtRepayments = histRefsCfs?.debtRepayments?.length
      ? padHistOnly(histRefsCfs.debtRepayments)
      : padHistOnly(historical.debtRepayments || []);
    const histTaxPaid = histRefsCfs?.taxPaid?.length
      ? padHistOnly(histRefsCfs.taxPaid)
      : padHistOnly(historical.taxPaid || []);
    const histInterestPaid = histRefsCfs?.interestPaid?.length
      ? padHistOnly(histRefsCfs.interestPaid)
      : padHistOnly(historical.interestPaid || []);
    return [
      { label: 'Net Income', values: cfs.netIncome, calculatedValues: cfs.netIncome, fieldId: 'cfsNetIncome', formula: 'From IS. Starting point for CFO.' },
      { label: '+ Depreciation', values: cfs.depreciation, calculatedValues: cfs.depreciation, formula: 'Add back non-cash dep.' },
      { label: '+ Deferred Taxes', values: cfs.deferredTaxes, calculatedValues: cfs.deferredTaxes, formula: 'Add back deferred tax (non-cash).' },
      { label: '+/- WC Change', values: workingCapitalChange, calculatedValues: workingCapitalChange, formula: 'Cash from AR+Inv+AP. + = cash inflow.' },
      { label: 'Subtotal CFO', values: cfs.subtotalCfo, calculatedValues: cfs.subtotalCfo, isHighlight: true, fieldId: 'cfo', formula: 'NI + Dep + DefTax + WC Change' },
      { label: 'Capital Expenditure', values: cfs.capitalExpenditure, calculatedValues: cfs.capitalExpenditure, fieldId: 'capitalExpenditure', formula: '−CapEx. Cash outflow for PP&E.' },
      { label: 'Subtotal CFI', values: cfs.subtotalCfi, calculatedValues: cfs.subtotalCfi, fieldId: 'cfi', formula: '= Capital Expenditure' },
      { label: 'Interest Expense (after-tax)', values: interestExpenseAfterTax, calculatedValues: interestExpenseAfterTax, formula: '−Interest × (1 − Tax Rate). Ref only.' },
      { label: 'Tax Paid', values: histTaxPaid, isReference: true, formula: 'Historical only. Actual tax payments from CF statement.' },
      { label: 'Interest Paid', values: histInterestPaid, isReference: true, formula: 'Historical only. Actual interest payments from CF statement.' },
      { label: '+/- Change in LT Debt', values: cfs.changeInLtDebt, calculatedValues: cfs.changeInLtDebt, fieldId: 'changeInLtDebt', formula: 'Cash from issuing/repaying long-term debt. From Debt Schedule.' },
      { label: '- Dividends', values: cfs.dividends, calculatedValues: cfs.dividends, fieldId: 'dividends', formula: 'Cash paid to shareholders. Net Income × Payout Ratio.' },
      { label: '- Share Buybacks', values: histShareBuybacks.map((v: number) => v > 0 ? -v : v), calculatedValues: histShareBuybacks.map((v: number) => v > 0 ? -v : v), formula: 'Historical: from CF statement. Forecast: 0 (not modeled in DCF).' },
      { label: '+/- Revolving Credit', values: cfs.revolvingCredit, calculatedValues: cfs.revolvingCredit, fieldId: 'revolvingCredit', formula: 'Draws/repayments on revolving credit line. From Debt Schedule Part 2.' },
      { label: 'Subtotal CFF', values: cfs.subtotalCff, calculatedValues: cfs.subtotalCff, fieldId: 'cff', formula: 'IntExp + TaxPaid + ΔDebt + Dividends + Buybacks + Revolver.' },
      { label: 'Free Cash Flow', values: freeCashFlow, calculatedValues: freeCashFlow, isHighlight: true, fieldId: 'fcf', formula: 'CFO + CFI.' },
      { label: 'Beginning Cash', values: cfs.beginningCash, calculatedValues: cfs.beginningCash, fieldId: 'openingCash', formula: 'Prior year ending cash.' },
      // Change in Cash = CFO + CFI + CFF (dynamic computation, not padded backend value)
      { label: '+/- Change in Cash', values: (cfs.subtotalCfo || []).map((cfo: number, i: number) =>
        cfo + (cfs.subtotalCfi?.[i] || 0) + (cfs.subtotalCff?.[i] || 0)
      ), formula: 'CFO + CFI + CFF.' },
      { label: 'Ending Cash', values: cfs.endingCash, calculatedValues: cfs.endingCash, isHighlight: true, fieldId: 'endingCash', formula: 'Beg Cash + Change. → BS Cash, Debt Sched.' },
    ];
  }, [output, historical]);

  // ─── Shared WC & Cash values (single source of truth for [3B], [3G], [3H]) ──
  const sharedWcBalances = useMemo(() => {
    return {
      ar: output?.workingCapital?.arBalance || [],
      inv: output?.workingCapital?.inventoryBalance || [],
      ap: output?.workingCapital?.apBalance || [],
      cash: output?.balanceSheet?.cash || [],
    };
  }, [output]);

  // ─── [3H] Balance Sheet ───────────────────────────────────────────────────
  // Linked: Common Equity → [3K] CS&APIC; RE → [3K] RE; PP&E Net → [3D] PP&E Ending
  const balanceSheetRows = useMemo(() => {
    if (!output?.balanceSheet) return [];
    const hLen = HIST_PERIODS.length;
    const n = ALL_PERIODS.length;

    const accumDepArr = sharedAccumDep;
    
    const ppeGross = sharedPpeGross;
    // PP&E Net = PP&E Gross + Accumulated Depreciation (add negative = subtract)
    const ppeNet = ppeGross.map((gross: number, i: number) => (gross || 0) + (accumDepArr[i] || 0));

    // Use shared equity computation (single source of truth for [3H] and [3K])
    const { ceAll, reAll } = sharedEquity;

    // Recompute all derived rows from the displayed component values
    // This ensures A = L + E and all cross-schedule links are consistent
    // BS values = backend balance sheet; calculatedValues = WC/CFS schedule values (cross-check)
    const cashArr = sharedWcBalances.cash;
    const arArr = sharedWcBalances.ar;
    const invArr = sharedWcBalances.inv;
    // Non-Current Marketable Securities: use historical data for hist periods, backend for forecast
    // Backend stores as negative (yfinance); negate for positive display
    const ncmsArr = new Array(n).fill(0);
    for (let i = 0; i < hLen; i++) {
      ncmsArr[i] = historical.nonCurrentMarketableSecurities?.[i] ?? 0;
    }
    for (let i = hLen; i < n; i++) {
      ncmsArr[i] = output.balanceSheet.nonCurrentMarketableSecurities?.[i - hLen] ?? 0;
    }
    // Use backend values directly — no frontend computation
    const totalCA = output.balanceSheet.totalCurrentAssets || cashArr.map((c: number, i: number) => (c || 0) + (arArr[i] || 0) + (invArr[i] || 0));
    const totalTA = output.balanceSheet.totalAssets || totalCA.map((ca: number, i: number) => ca + (ppeNet[i] || 0) + (ncmsArr[i] || 0));
    
    const apArr = sharedWcBalances.ap;
    // Other Current Liabilities: use historical data for hist periods, backend for forecast
    const otherClArr = new Array(n).fill(0);
    for (let i = 0; i < hLen; i++) {
      otherClArr[i] = historical.otherCurrentLiabilities?.[i] ?? 0;
    }
    for (let i = hLen; i < n; i++) {
      otherClArr[i] = output.balanceSheet.otherCurrentLiabilities?.[i - hLen] ?? 0;
    }
    const revArr = output.balanceSheet.revolvingCredit || [];
    const cdArr = output.balanceSheet.currentDebt || new Array(n).fill(0);
    // Use backend values directly — no frontend computation
    const totalCL = output.balanceSheet.totalCurrentLiabilities || apArr.map((a: number, i: number) => (a || 0) + (otherClArr[i] || 0) + (revArr[i] || 0) + (cdArr[i] || 0));
    // Deferred Tax Liabilities: use historical data for hist periods, backend for forecast
    const dtlArr = new Array(n).fill(0);
    for (let i = 0; i < hLen; i++) {
      dtlArr[i] = historical.deferredTaxLiabilities?.[i] ?? 0;
    }
    for (let i = hLen; i < n; i++) {
      dtlArr[i] = output.balanceSheet.deferredTaxLiabilities?.[i - hLen] ?? 0;
    }
    const ltDebtArr = output.balanceSheet.longTermDebt || [];
    // Use backend values directly — no frontend computation
    const totalLiab = output.balanceSheet.totalLiabilities || totalCL.map((cl: number, i: number) => cl + (dtlArr[i] || 0) + (ltDebtArr[i] || 0));
    const totalSE = output.balanceSheet.totalShareholdersEquity || ceAll.map((c: number, i: number) => c + reAll[i]);
    const balanceCheck = output.balanceSheet.balanceCheck || totalTA.map((a: number, i: number) => a - ((totalLiab[i] || 0) + (totalSE[i] || 0)));

    // BS calculatedValues: use backend-calculated values (from engine output, before historical padding)
    const bsCashCalc = output.balanceSheet.cash || new Array(n).fill(0);
    const bsArCalc = output.balanceSheet.accountsReceivable || new Array(n).fill(0);
    const bsInvCalc = output.balanceSheet.inventories || new Array(n).fill(0);
    const bsApCalc = output.balanceSheet.accountsPayable || new Array(n).fill(0);
    const bsOtherClCalc = output.balanceSheet.otherCurrentLiabilities || new Array(n).fill(0);
    const bsRevCalc = output.balanceSheet.revolvingCredit || new Array(n).fill(0);
    const bsCdCalc = output.balanceSheet.currentDebt || new Array(n).fill(0);
    const bsDtlCalc = output.balanceSheet.deferredTaxLiabilities || new Array(n).fill(0);
    const bsLtDebtCalc = output.balanceSheet.longTermDebt || new Array(n).fill(0);
    const bsCeCalc = output.balanceSheet.commonEquity || new Array(n).fill(0);
    const bsReCalc = output.balanceSheet.retainedEarnings || new Array(n).fill(0);
    const bsCommonStockCalc = output.balanceSheet.commonStock || new Array(n).fill(0);
    const bsOtherEquityAdjCalc = output.balanceSheet.otherEquityAdjustments || new Array(n).fill(0);

    // Helper: pad array with historical data for hist periods, backend for forecast
    const padHistFc = (histArr: number[] | undefined, fcArr: number[] | undefined) => {
      const arr = new Array(n).fill(0);
      for (let i = 0; i < hLen; i++) arr[i] = histArr?.[i] ?? 0;
      for (let i = hLen; i < n; i++) arr[i] = fcArr?.[i - hLen] ?? 0;
      return arr;
    };

    // New granularity balance sheet arrays (historical + forecast)
    const otherStiArr = padHistFc(historical.otherShortTermInvestments, output.balanceSheet.otherShortTermInvestments);
    const otherCaArr = padHistFc(historical.otherCurrentAssets, output.balanceSheet.otherCurrentAssets);
    const otherNcaArr = padHistFc(historical.otherNonCurrentAssets, output.balanceSheet.otherNonCurrentAssets);
    const ncdArr = padHistFc([], output.balanceSheet.nonCurrentDeferredAssets);
    const iaArr = padHistFc([], output.balanceSheet.investmentsAndAdvances);
    const caExpArr = padHistFc(historical.currentAccruedExpenses, output.balanceSheet.currentAccruedExpenses);
    const cdlArr = padHistFc(historical.currentDeferredLiabilities, output.balanceSheet.currentDeferredLiabilities);
    const taPncArr = padHistFc(historical.tradeAndOtherPayablesNonCurrent, output.balanceSheet.tradeAndOtherPayablesNonCurrent);
    const onclArr = padHistFc(historical.otherNonCurrentLiabilities, output.balanceSheet.otherNonCurrentLiabilities);
    const csArr = padHistFc(historical.commonStock, output.balanceSheet.commonStock);
    const oeaArr = padHistFc(historical.otherEquityAdjustments, output.balanceSheet.otherEquityAdjustments);

    return [
      // ── Assets ──
      { label: 'Cash', values: bsCashCalc, calculatedValues: output.cashFlowStatement?.endingCash || cashArr, fieldId: 'cash_bs', formula: 'From CFS ending cash.' },
      { label: 'Accounts Receivable', values: bsArCalc, calculatedValues: arArr, fieldId: 'ar_bs', formula: 'From WC Schedule AR Balance.' },
      { label: 'Inventories', values: bsInvCalc, calculatedValues: invArr, fieldId: 'inv_bs', formula: 'From WC Schedule Inventory Balance.' },
      { label: 'Other Short-Term Investments', values: otherStiArr, fieldId: 'otherSti_bs', formula: 'Short-term investments (< 1 year).' },
      { label: 'Other Current Assets', values: otherCaArr, fieldId: 'otherCa_bs', formula: 'Prepaid expenses, deferred tax assets (current).' },
      { label: 'Non-Current Marketable Securities', values: ncmsArr, fieldId: 'ncms_bs', formula: 'Long-term bond portfolio. Critical for EV-to-Equity bridge.' },
      { label: 'Other Non-Current Assets', values: otherNcaArr, fieldId: 'otherNca_bs', formula: 'Goodwill, intangibles, long-term deposits.' },
      { label: 'Non-Current Deferred Assets', values: ncdArr, fieldId: 'ncd_bs', formula: 'Long-term deferred charges, prepaid expenses.' },
      { label: 'Total Current Assets', values: output.balanceSheet.totalCurrentAssets, calculatedValues: totalCA, isHighlight: true, fieldId: 'totalCurrentAssets', formula: 'Cash + AR + Inventories + Other.' },
      { label: 'PP&E (Gross)', values: output.depreciation?.grossPpeEnding, calculatedValues: ppeGross, fieldId: 'ppeEnding', formula: '→ [3D] Asset Schedule PP&E Ending.' },
      { label: 'Accumulated Depreciation', values: accumDepArr, formula: 'Negative pool. → [3D] PP&E Net.' },
      { label: 'PP&E Net', values: ppeNet, calculatedValues: ppeNet, isHighlight: true, fieldId: 'ppeNet', formula: 'PP&E Gross + Accumulated Dep. (negative) → feeds Total Assets.' },
      { label: 'Investments & Advances', values: iaArr, fieldId: 'ia_bs', formula: 'Long-term equity investments, joint ventures.' },
      { label: 'Total Assets', values: output.balanceSheet.totalAssets, calculatedValues: totalTA, isHighlight: true, fieldId: 'totalAssets', formula: 'Current Assets + PP&E Net + NCMS + Other.' },
      // ── Liabilities ──
      { label: 'Accounts Payable', values: bsApCalc, calculatedValues: apArr, fieldId: 'ap_bs', formula: 'From WC Schedule AP Balance.' },
      { label: 'Current Accrued Expenses', values: caExpArr, fieldId: 'caExp_bs', formula: 'Accrued expenses (component of other CL).' },
      { label: 'Current Deferred Liabilities', values: cdlArr, fieldId: 'cdl_bs', formula: 'Deferred revenue (component of other CL).' },
      { label: 'Other Current Liabilities', values: bsOtherClCalc, calculatedValues: otherClArr, fieldId: 'otherCl_bs', formula: 'Accrued Expenses + Deferred Revenue combined. Critical for ΔNWC.' },
      { label: 'Revolving Credit', values: bsRevCalc, calculatedValues: revArr, formula: '→ [3J] Debt Sched Part 2.' },
      { label: 'Current Debt', values: bsCdCalc, calculatedValues: cdArr, formula: 'Short-term borrowings.' },
      { label: 'Total Current Liabilities', values: output.balanceSheet.totalCurrentLiabilities, calculatedValues: totalCL, fieldId: 'totalCurrentLiab', formula: 'AP + Accrued + Deferred + Other CL + Revolver + Current Debt.' },
      { label: 'Trade & Other Payables Non-Current', values: taPncArr, fieldId: 'taPnc_bs', formula: 'Non-current operating payables.' },
      { label: 'Deferred Tax Liabilities', values: bsDtlCalc, calculatedValues: dtlArr, fieldId: 'dtl_bs', formula: 'Net DTA/DTL position. Non-cash timing differences.' },
      { label: 'Other Non-Current Liabilities', values: onclArr, fieldId: 'oncl_bs', formula: 'Other non-current liabilities beyond LT debt & DTL.' },
      { label: 'Long-Term Debt', values: bsLtDebtCalc, calculatedValues: ltDebtArr, fieldId: 'ltDebt_bs', formula: '→ [3I] Debt Sched Part 1.' },
      { label: 'Total Liabilities', values: output.balanceSheet.totalLiabilities, calculatedValues: totalLiab, isHighlight: true, fieldId: 'totalLiabilities', formula: 'Current Liab + Non-Current Liab + Deferred Tax Liab + LT Debt.' },
      // ── Equity ──
      { label: 'Common Stock', values: csArr, fieldId: 'cs_bs', formula: 'Par value of issued shares.' },
      { label: 'Common Equity', values: bsCeCalc, calculatedValues: ceAll, fieldId: 'commonEquity', formula: '→ [3K] CS&APIC (Ending). Hist from XBRL. Forecast: flat.' },
      { label: 'Retained Earnings', values: bsReCalc, calculatedValues: reAll, fieldId: 'retainedEarnings', formula: '→ [3K] RE (Ending). Opening + NI − Dividends.' },
      { label: 'Other Equity Adjustments', values: oeaArr, fieldId: 'oea_bs', formula: 'AOCI, treasury stock, translation adjustments.' },
      { label: "Total Shareholders' Equity", values: sharedEquity.totalEq, calculatedValues: totalSE, isHighlight: true, fieldId: 'totalSE', formula: 'CS&APIC + RE + Other Adjustments. → [3K] Total Equity.' },
      { label: 'Balance Check (A−L−E)', values: balanceCheck, fieldId: 'balanceCheck', formula: 'Total Assets − Total Liabilities − Total Equity ≈ 0.' },
    ];
  }, [output, historical, HIST_PERIODS.length, ALL_PERIODS.length, inputs]);

  // ─── [3I] Debt Schedule Part 1 — Cash + LT Debt ──────────────────────────
  const debtSchedulePart1Rows = useMemo(() => {
    const n = ALL_PERIODS.length;

    // Use backend interest_schedule (includes all periods)
    const intSched = (output as any)?.interestSchedule;

    const openingCash: number[] = intSched?.openingCash || new Array(n).fill(0);
    const cashInterestIncome: number[] = intSched?.cashInterestIncome || new Array(n).fill(0);
    const ltDebtBal: number[] = intSched?.ltDebtBalance || new Array(n).fill(0);
    const ltInterest: number[] = intSched?.ltDebtInterestExpense || new Array(n).fill(0);

    // Cash Change from CFS = Ending Cash − Opening Cash
    const cfsEndingCash = output?.cashFlowStatement?.endingCash || [];
    const cashChangeFromCfs = openingCash.map((oc: number, i: number) => {
      const endCash = cfsEndingCash[i] ?? 0;
      return i === 0 ? 0 : endCash - (cfsEndingCash[i - 1] ?? 0);
    });
    // Ending Cash = Opening Cash + Cash Change
    const endingCash = openingCash.map((oc: number, i: number) => oc + cashChangeFromCfs[i]);

    // LT Debt Opening = prior period's ending balance
    const ltDebtOpening = ltDebtBal.map((bal: number, i: number) => i === 0 ? 0 : (ltDebtBal[i - 1] ?? 0));
    // Change in LT Debt = Ending − Opening
    const changeInLtDebt = ltDebtBal.map((bal: number, i: number) => i === 0 ? 0 : (bal || 0) - (ltDebtBal[i - 1] ?? 0));

    // Debt Part 1 calculatedValues: engine values from interest schedule (full-period)
    const debtCalcLtBal = ltDebtBal;
    return [
      // Cash Section
      { label: 'Revolving Credit (Ref)', values: new Array(n).fill(inputs.revolvingCreditLine), isReference: true, formula: 'Revolving credit facility limit from inputs (default 0).' },
      { label: 'Opening Cash', values: openingCash, calculatedValues: openingCash, formula: 'Prior year ending cash. First period = opening balance.' },
      { label: '+ Cash Change from CFS', values: cashChangeFromCfs, formula: 'Linked from Cash Flow Statement increase/decrease in cash.' },
      { label: '= Ending Cash', values: endingCash, calculatedValues: endingCash, isHighlight: true, formula: 'Opening Cash + Cash Change. → BS Cash.' },
      { label: 'Cash Interest Rate', values: new Array(n).fill(inputs.cashInterestRate * 100), isReference: true, formula: 'Interest rate on cash balances (default 1%). From inputs.' },
      { label: 'Cash Interest Income', values: cashInterestIncome, calculatedValues: cashInterestIncome, formula: 'Ending Cash × Cash Interest Rate.' },
      // LT Debt Section
      { label: 'LT Debt Opening', values: ltDebtOpening, formula: 'Prior year ending LT Debt. First period = opening balance.' },
      { label: 'Change in LT Debt', values: changeInLtDebt, calculatedValues: changeInLtDebt, fieldId: 'changeInLtDebt', formula: 'From financing assumptions. Negative = repayment.' },
      { label: '= LT Debt Ending', values: ltDebtBal, calculatedValues: debtCalcLtBal, isHighlight: true, formula: 'Opening + Change. → BS Long-Term Debt.' },
      { label: 'LT Debt Interest Rate', values: new Array(n).fill(inputs.ltDebtInterestRate * 100), isReference: true, formula: 'Interest rate on long-term debt (default 6%). From inputs.' },
      { label: 'LT Debt Interest', values: ltInterest, calculatedValues: ltInterest, formula: 'LT Debt Ending × LT Debt Interest Rate.' },
      { label: 'Net Debt', values: ltDebtBal.map((d: number, i: number) => (d || 0) - (endingCash[i] || 0)), calculatedValues: ltDebtBal.map((d: number, i: number) => (d || 0) - (endingCash[i] || 0)), formula: 'LT Debt − Cash. From inputs/net debt.' },
    ];
  }, [ALL_PERIODS.length, inputs, output]);

  // ─── [3J] Debt Schedule Part 2 — Revolving + Net Interest ────────────────
  const debtSchedulePart2Rows = useMemo(() => {
    const n = ALL_PERIODS.length;

    // Use backend interest_schedule (includes all periods)
    const intSched = (output as any)?.interestSchedule;

    const revolvingCredit: number[] = intSched?.revolvingCreditBalance || new Array(n).fill(0);
    const revolvingInterest: number[] = intSched?.revolvingInterestExpense || new Array(n).fill(0);
    const ltInterest: number[] = intSched?.ltDebtInterestExpense || new Array(n).fill(0);
    const cashInterestIncome: number[] = intSched?.cashInterestIncome || new Array(n).fill(0);
    const netInterest: number[] = intSched?.netInterestExpense || new Array(n).fill(0);
    const totalInterestExpense: number[] = intSched?.totalInterestExpense || new Array(n).fill(0);

    // Cash Available section — from CFS
    const cfs: any = output?.cashFlowStatement || {};
    const cfo = cfs.subtotalCfo || [];
    const cfi = cfs.subtotalCfi || [];
    const changeInLtDebt = cfs.changeInLtDebt || [];
    const changeInEquity = cfs.changeInCommonEquity || [];
    const beginningCash = cfs.beginningCash || [];
    const cashAvailable = beginningCash.map((bc: number, i: number) =>
      (bc || 0) + (cfo[i] || 0) + (cfi[i] || 0) + (changeInLtDebt[i] || 0) + (changeInEquity[i] || 0)
    );

    return [
      // Cash Available section
      { label: 'Beginning Cash', values: beginningCash, calculatedValues: beginningCash, formula: 'From CFS. Prior year ending cash.' },
      { label: '+ Cash from Operations', values: cfo, calculatedValues: cfo, formula: 'From CFS Subtotal CFO.' },
      { label: '− Capital Expenditure', values: (cfi || []).map((v: number) => Math.abs(v || 0)), calculatedValues: (cfi || []).map((v: number) => Math.abs(v || 0)), formula: 'From CFS (absolute value for display).' },
      { label: '− Change in LT Debt', values: (changeInLtDebt || []).map((v: number) => -Math.abs(v || 0)), calculatedValues: (changeInLtDebt || []).map((v: number) => -Math.abs(v || 0)), formula: 'From CFS. Negative = repayment.' },
      { label: '− Change in Equity', values: (changeInEquity || []).map((v: number) => -Math.abs(v || 0)), calculatedValues: (changeInEquity || []).map((v: number) => -Math.abs(v || 0)), formula: 'From CFS. Negative = buybacks/dividends.' },
      { label: '= Cash Available', values: cashAvailable, calculatedValues: cashAvailable, isHighlight: true, formula: 'Beginning Cash + CFO + CFI + CFF changes.' },
      // Revolving Credit section
      { label: 'Revolving Credit Balance', values: revolvingCredit, calculatedValues: revolvingCredit, formula: 'From backend interest schedule.' },
      { label: 'Revolving Credit Rate', values: new Array(n).fill(inputs.revolvingCreditRate * 100), isReference: true, formula: 'Rate on revolver (default 5%).' },
      { label: 'Revolving Interest', values: revolvingInterest, calculatedValues: revolvingInterest, formula: 'Revolver × Rate.' },
      // Net Interest section
      { label: 'LT Debt Interest', values: ltInterest, calculatedValues: ltInterest, fieldId: 'ltInterest', formula: 'LT Debt Ending × Rate. From Part 1.' },
      { label: '− Cash Interest Income', values: cashInterestIncome.map((v: number) => -v), formula: 'From Part 1. Negative = income offset.' },
      { label: '= Net Interest Expense', values: netInterest, calculatedValues: netInterest, isHighlight: true, fieldId: 'netInterest', formula: 'LT Interest − Cash Interest Income.' },
      { label: 'Total Interest Expense', values: totalInterestExpense, calculatedValues: totalInterestExpense, isHighlight: true, fieldId: 'totalInterestExpense', formula: 'Total interest. → IS Interest Expense.' },
    ];
  }, [ALL_PERIODS.length, inputs, output]);

  // ─── [3K] Equity Schedule — Common + RE + Dividends ──────────────────────
  // ─── [3K] Equity Schedule — Common + RE + Dividends ──────────────────────
  // Correct accounting format:
  //   Common Stock & APIC: Opening + SBC/Issuances = Ending
  //   Retained Earnings: Opening + Net Income - Dividends - Buybacks = Ending
  //   Total Equity = Ending CS&APIC + Ending RE
  //   Buybacks reduce Retained Earnings (not Common Stock)
  const equityScheduleRows = useMemo(() => {
    if (!output?.incomeStatement) return [];
    const hLen = HIST_PERIODS.length;
    const n = ALL_PERIODS.length;

    // Use shared equity computation (single source of truth for [3H] and [3K])
    const { csOpening, csEnding, reOpening, reEnding, totalEq } = sharedEquity;
    const csSBC = new Array(n).fill(0); // No SBC in model
    const reNetIncome = new Array(n).fill(0);
    const reDividends = new Array(n).fill(0);
    const reBuybacks = new Array(n).fill(0);

    // Fill in detailed arrays from shared computation
    for (let i = 0; i < n; i++) {
      reNetIncome[i] = output.incomeStatement.netIncome?.[i] ?? 0;
      if (i < hLen) {
        reDividends[i] = historical.dividendsPaid[i] ?? 0;
        reBuybacks[i] = historical.shareBuybacks?.[i] ?? 0;
      } else {
        reDividends[i] = reNetIncome[i] * inputs.dividendPayoutRatio;
        reBuybacks[i] = 0;
      }
    }

    return [
      // Common Stock & APIC
      { label: 'Common Stock & APIC', values: csOpening, calculatedValues: sharedEquity.csOpening, isHighlight: true, formula: 'Prior year ending balance.' },
      { label: '+ SBC / New Issuances', values: csSBC, calculatedValues: csSBC, formula: 'Stock-based comp. Forecast: 0.' },
      { label: 'Common Stock & APIC (Ending)', values: csEnding, calculatedValues: sharedEquity.csEnding, isHighlight: true, formula: 'Prior + SBC = next period prior.' },
      // Retained Earnings
      { label: 'Retained Earnings', values: reOpening, calculatedValues: sharedEquity.reOpening, formula: 'Prior year ending RE.' },
      { label: '+ Net Income', values: reNetIncome, calculatedValues: output.incomeStatement?.netIncome, formula: 'From Income Statement.' },
      { label: '- Dividends Paid', values: reDividends.map(v => -v), calculatedValues: reDividends.map(v => -v), formula: 'NI × Payout Ratio.' },
      { label: '- Share Buybacks', values: reBuybacks, calculatedValues: reBuybacks, formula: 'Negative = reduces RE. Forecast: 0.' },
      { label: 'Retained Earnings (Ending)', values: reEnding, calculatedValues: sharedEquity.reEnding, isHighlight: true, formula: 'Prior + NI − Div − Buybacks.' },
      // Total Equity
      { label: "Total Shareholders' Equity", values: totalEq, calculatedValues: sharedEquity.totalEq, isHighlight: true, formula: 'CS&APIC (Ending) + RE (Ending).' },
    ];
  }, [inputs, output, ALL_PERIODS.length, HIST_PERIODS.length, historical]);

  // ─── Render ───────────────────────────────────────────────────────────────
  if (selectedModel !== 'DCF') {
    // Non-DCF models: show simple confirmation view
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-bold text-[var(--text-primary)]">{t('steps.step9')}</h2>
          <button onClick={onBackToForecastDrivers} className="text-xs text-[var(--text-tertiary)] hover:text-[var(--text-primary)]">← {t('common.back')}</button>
        </div>
        <div className="bg-[var(--canvas-surface-elevated)]/50 border border-[var(--border-default)] rounded p-4 text-xs text-[var(--text-primary)]">
          <p>Step 9 for <span className="text-[var(--accent-primary)] font-bold">{selectedModel}</span> model shows a summary review.</p>
          <p className="mt-2">Full schedule editing is available for the DCF model.</p>
        </div>
        <button
          onClick={handleConfirm}
          disabled={loading}
          className="w-full bg-[var(--color-bullish)] hover:bg-[var(--color-bullish)] text-[var(--text-primary)] font-bold py-3 rounded text-sm disabled:opacity-50"
        >
          {loading ? 'Processing...' : '✅ Confirm & Run Valuation →'}
        </button>
      </div>
    );
  }

  // DCF Model: Full building block schedule view
  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-bold text-[var(--text-primary)]">{t('sections.dcf_model_inputs')}</h2>
          <p className="text-[10px] text-[var(--text-tertiary)] mt-0.5">
            {companyName || ticker} — Edit inputs below, schedules recalculate instantly
          </p>
        </div>
        <button onClick={onBackToForecastDrivers} className="text-xs text-[var(--text-tertiary)] hover:text-[var(--text-primary)]">← Back to Forecast</button>
      </div>

      {/* ─── Valuation Summary Card (only after calculation) ─── */}
      {output && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="bg-emerald-900/30 border border-emerald-700 rounded p-3 text-center">
            <div className="text-[10px] text-[var(--color-bullish)] uppercase">Perpetuity Method</div>
            <div className="text-lg font-bold text-[var(--color-bullish)] font-mono mt-1">
              ${output.dcfPerpetuity.fairValuePerShare.toFixed(2)}
            </div>
            <div className="text-[9px] text-[var(--text-tertiary)] mt-0.5">
              EV: ${(output.dcfPerpetuity.enterpriseValue / 1e9).toFixed(1)}B
            </div>
          </div>
          <div className="bg-blue-900/30 border border-blue-700 rounded p-3 text-center">
            <div className="text-[10px] text-[var(--accent-primary)] uppercase">Exit Multiple Method</div>
            <div className="text-lg font-bold text-[var(--accent-primary)] font-mono mt-1">
              ${output.dcfExitMultiple.fairValuePerShare.toFixed(2)}
            </div>
            <div className="text-[9px] text-[var(--text-tertiary)] mt-0.5">
              EV: ${(output.dcfExitMultiple.enterpriseValue / 1e9).toFixed(1)}B
            </div>
          </div>
          <div className="bg-[var(--canvas-surface-elevated)]/50 border border-[var(--border-default)] rounded p-3 text-center">
            <div className="text-[10px] text-[var(--text-tertiary)] uppercase">Current Price</div>
            <div className="text-lg font-bold text-[var(--text-primary)] font-mono mt-1">
              ${inputs.currentPrice.toFixed(2)}
            </div>
            <div className="text-[9px] text-[var(--text-tertiary)] mt-0.5">
              WACC: {(inputs.wacc * 100).toFixed(1)}%
            </div>
          </div>
        </div>
      )}

      {/* ─── Validation Warnings ─── */}
      {(validation.warnings.length > 0 || validation.missingRequired.length > 0) && (
        <div className="bg-amber-900/20 border border-amber-700 rounded p-3">
          {validation.missingRequired.length > 0 && (
            <div className="text-[10px] text-[var(--color-bearish)] mb-1">
              ⚠ Missing {validation.missingRequired.length} required fields
            </div>
          )}
          {validation.warnings.map((w, i) => (
            <div key={i} className="text-[9px] text-[var(--color-neutral)]">
              ⚠ <strong>{w.field}:</strong> {w.message} (current: {w.value})
            </div>
          ))}
        </div>
      )}

      {/* ─── Editable Inputs Section ─── */}
      <div className="border border-[var(--border-default)] rounded">
        <div className="px-3 py-2 bg-[var(--canvas-surface-elevated)]/50 text-xs font-semibold text-[var(--text-primary)]">
          📝 Editable Inputs
        </div>
        <div className="p-3 space-y-4">
          {/* Forecast Drivers */}
          <div>
            <h4 className="text-[10px] text-[var(--accent-primary)] uppercase tracking-wide mb-2">Forecast Drivers (5yr)</h4>
            <div className="grid grid-cols-3 sm:grid-cols-6 gap-2">
              {FC_PERIODS.map((period, i) => (
                <div key={i} className="text-center text-[9px] text-[var(--text-tertiary)]">{period}</div>
              ))}
            </div>
            {/* Revenue Growth */}
            <div className="mt-1">
              <label className="text-[9px] text-[var(--text-tertiary)]">Revenue Growth</label>
              <div className="grid grid-cols-3 sm:grid-cols-6 gap-2 mt-0.5">
                {inputs.revenueGrowth.map((v, i) => (
                  <EditableField key={`rg-${i}`} label="" value={v} type="percent"
                    onChange={(val) => handleArrayFieldChange('revenueGrowth', i, val)} />
                ))}
              </div>
            </div>
            {/* COGS Growth Rate */}
            <div className="mt-1">
              <label className="text-[9px] text-[var(--text-tertiary)]">COGS Growth Rate</label>
              <div className="grid grid-cols-3 sm:grid-cols-6 gap-2 mt-0.5">
                {inputs.cogsGrowthRate.map((v, i) => (
                  <EditableField key={`cgr-${i}`} label="" value={v} type="percent"
                    onChange={(val) => handleArrayFieldChange('cogsGrowthRate', i, val)} />
                ))}
              </div>
            </div>
            {/* OpEx Growth Rate */}
            <div className="mt-1">
              <label className="text-[9px] text-[var(--text-tertiary)]">OpEx Growth Rate</label>
              <div className="grid grid-cols-3 sm:grid-cols-6 gap-2 mt-0.5">
                {inputs.opexGrowthRate.map((v, i) => (
                  <EditableField key={`oxgr-${i}`} label="" value={v} type="percent"
                    onChange={(val) => handleArrayFieldChange('opexGrowthRate', i, val)} />
                ))}
              </div>
            </div>
            {/* Capex (% of Revenue) */}
            <div className="mt-1">
              <label className="text-[9px] text-[var(--text-tertiary)]">Capex (% of Rev)</label>
              <div className="grid grid-cols-3 sm:grid-cols-6 gap-2 mt-0.5">
                {inputs.capex.map((v, i) => (
                  <EditableField key={`cx-${i}`} label="" value={v} type="percent"
                    onChange={(val) => handleArrayFieldChange('capex', i, val)} />
                ))}
              </div>
            </div>
          </div>

          {/* WACC Components */}
          <div>
            <h4 className="text-[10px] text-[var(--accent-primary)] uppercase tracking-wide mb-2">WACC Components</h4>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <EditableField label="Risk-Free Rate" value={inputs.riskFreeRate} type="percent"
                onChange={(v) => handleFieldChange('riskFreeRate', v)}  isDefault={defaultFields.has('riskFreeRate')} />
              <EditableField label="Equity Risk Premium" value={inputs.equityRiskPremium} type="percent"
                onChange={(v) => handleFieldChange('equityRiskPremium', v)}  isDefault={defaultFields.has('equityRiskPremium')} />
              <EditableField label="Beta" value={inputs.beta}
                onChange={(v) => handleFieldChange('beta', v)}  isDefault={defaultFields.has('beta')} />
              <EditableField label="Cost of Debt" value={inputs.costOfDebt} type="percent"
                onChange={(v) => handleFieldChange('costOfDebt', v)}  isDefault={defaultFields.has('costOfDebt')} />
              <EditableField label="D/E Ratio" value={inputs.debtToEquity}
                onChange={(v) => handleFieldChange('debtToEquity', v)}  isDefault={defaultFields.has('debtToEquity')} />
              <EditableField label="WACC" value={inputs.wacc} type="percent"
                onChange={(v) => handleFieldChange('wacc', v)}  isDefault={defaultFields.has('wacc')} />
            </div>
          </div>

          {/* Working Capital & Tax */}
          <div>
            <h4 className="text-[10px] text-[var(--accent-primary)] uppercase tracking-wide mb-2">Working Capital & Tax</h4>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <EditableField label="AR Days" value={inputs.arDays}
                onChange={(v) => handleFieldChange('arDays', v)}
                warning={inputs.arDays > 90 ? 'Slow collections' : undefined} />
              <EditableField label="Inventory Days" value={inputs.invDays}
                onChange={(v) => handleFieldChange('invDays', v)}
                warning={inputs.invDays > 60 ? 'Slow turnover' : undefined} />
              <EditableField label="AP Days" value={inputs.apDays}
                onChange={(v) => handleFieldChange('apDays', v)}
                warning={inputs.apDays > 120 ? 'Very slow payments' : undefined} />
              <EditableField label="Tax Rate" value={inputs.taxRate} type="percent"
                onChange={(v) => handleFieldChange('taxRate', v)}  isDefault={defaultFields.has('taxRate')} />
            </div>
          </div>

          {/* Terminal Value, Depreciation & Interest Rates */}
          <div>
            <h4 className="text-[10px] text-[var(--accent-primary)] uppercase tracking-wide mb-2">Terminal Value, Depreciation & Interest</h4>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <EditableField label="Terminal Growth" value={inputs.terminalGrowthRate} type="percent"
                onChange={(v) => handleFieldChange('terminalGrowthRate', v)}
                warning={inputs.terminalGrowthRate > 0.05 ? 'Aggressive' : undefined} />
              <EditableField label="EBITDA Multiple" value={inputs.terminalEbitdaMultiple}
                onChange={(v) => handleFieldChange('terminalEbitdaMultiple', v)}
                warning={inputs.terminalEbitdaMultiple > 20 ? 'Very high' : undefined} />
              <EditableField label="Useful Life (Existing)" value={inputs.usefulLifeExisting}
                onChange={(v) => handleFieldChange('usefulLifeExisting', v)}  isDefault={defaultFields.has('usefulLifeExisting')} />
              <EditableField label="Useful Life (New)" value={inputs.usefulLifeNew}
                onChange={(v) => handleFieldChange('usefulLifeNew', v)}  isDefault={defaultFields.has('usefulLifeNew')} />
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 mt-3">
              <EditableField label="Cash Interest Rate" value={inputs.cashInterestRate} type="percent"
                onChange={(v) => handleFieldChange('cashInterestRate', v)}  isDefault={defaultFields.has('cashInterestRate')} />
              <EditableField label="Revolving Credit Rate" value={inputs.revolvingCreditRate} type="percent"
                onChange={(v) => handleFieldChange('revolvingCreditRate', v)}  isDefault={defaultFields.has('revolvingCreditRate')} />
              <EditableField label="LT Debt Interest Rate" value={inputs.ltDebtInterestRate} type="percent"
                onChange={(v) => handleFieldChange('ltDebtInterestRate', v)}  isDefault={defaultFields.has('ltDebtInterestRate')} />
              <EditableField label="First Year Tax Dep %" value={inputs.firstYearTaxDepRate} type="percent"
                onChange={(v) => handleFieldChange('firstYearTaxDepRate', v)}  isDefault={defaultFields.has('firstYearTaxDepRate')} />
              <EditableField label="Blended Tax Dep %" value={inputs.blendedTaxDepRate} type="percent"
                onChange={(v) => handleFieldChange('blendedTaxDepRate', v)}  isDefault={defaultFields.has('blendedTaxDepRate')} />
              <EditableField label="First Year Acctg Dep %" value={inputs.firstYearAcctgDepRate} type="percent"
                onChange={(v) => handleFieldChange('firstYearAcctgDepRate', v)}  isDefault={defaultFields.has('firstYearAcctgDepRate')} />
            </div>
          </div>

          {/* DCF Model Parameters — moved to reference data within schedule tables (Asset, Depreciation, Tax, Debt) */}

          {/* Financing */}
          <div>
            <h4 className="text-[10px] text-[var(--accent-primary)] uppercase tracking-wide mb-2">Financing (5yr)</h4>
            <div className="grid grid-cols-3 sm:grid-cols-6 gap-2">
              {FC_PERIODS.map((period, i) => (
                <div key={i} className="text-center text-[9px] text-[var(--text-tertiary)]">{period}</div>
              ))}
            </div>
            {/* Change in LT Debt (displayed in $B for readability) */}
            <div className="mt-1">
              <label className="text-[9px] text-[var(--text-tertiary)]">Change in LT Debt ($B)</label>
              <div className="grid grid-cols-3 sm:grid-cols-6 gap-2 mt-0.5">
                {inputs.changeInLtDebt.map((v, i) => (
                  <EditableField key={`ltd-${i}`} label="" value={v / 1e9}
                    onChange={(val) => handleArrayFieldChange('changeInLtDebt', i, val * 1e9)} />
                ))}
              </div>
            </div>
            {/* Change in Common Equity (displayed in $B for readability) */}
            <div className="mt-1">
              <label className="text-[9px] text-[var(--text-tertiary)]">Change in Common Equity ($B)</label>
              <div className="grid grid-cols-3 sm:grid-cols-6 gap-2 mt-0.5">
                {inputs.changeInCommonEquity.map((v, i) => (
                  <EditableField key={`eq-${i}`} label="" value={v / 1e9}
                    onChange={(val) => handleArrayFieldChange('changeInCommonEquity', i, val * 1e9)} />
                ))}
              </div>
            </div>
            {/* Scalar financing inputs (displayed in $B for readability) */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-2">
              <EditableField label="Dividend Payout Ratio" value={inputs.dividendPayoutRatio} type="percent"
                onChange={(v) => handleFieldChange('dividendPayoutRatio', v)}  isDefault={defaultFields.has('dividendPayoutRatio')} />
            </div>
          </div>

          {/* Market Data */}
          <div>
            <h4 className="text-[10px] text-[var(--accent-primary)] uppercase tracking-wide mb-2">Market Data</h4>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <EditableField label="Current Price" value={inputs.currentPrice}
                onChange={(v) => handleFieldChange('currentPrice', v)}  isDefault={defaultFields.has('currentPrice')} />
              <EditableField label="Shares Outstanding ($B)" value={inputs.sharesOutstanding / 1e9}
                onChange={(v) => handleFieldChange('sharesOutstanding', v * 1e9)}  isDefault={defaultFields.has('sharesOutstanding')} />
              <EditableField label="Net Debt ($B)" value={inputs.netDebt / 1e9}
                onChange={(v) => handleFieldChange('netDebt', v * 1e9)}  isDefault={defaultFields.has('netDebt')} />
            </div>
          </div>
        </div>
      </div>

      {/* ─── Building Block Schedule Tables ─── */}
      {selectedFieldId && (
        <div className="flex items-center gap-3 px-3 py-2 bg-blue-900/30 border border-blue-700/50 rounded mb-3 text-[10px]">
          <span className="text-[var(--accent-primary)] font-semibold">🔗 Cross-Reference Mode</span>
          <span className="text-[var(--color-bullish)]">◀ Upstream (feeds into)</span>
          <span className="text-[var(--accent-primary)]">● Selected</span>
          <span className="text-[var(--color-neutral)]">▶ Downstream (used by)</span>
          <button onClick={() => setSelectedFieldId(null)} className="ml-auto text-[var(--text-tertiary)] hover:text-[var(--text-primary)] text-[9px] bg-[var(--canvas-surface-elevated)] px-2 py-0.5 rounded">✕ Clear</button>
        </div>
      )}

      <ScheduleTable title="[3A] Income Statement (Rows 21-41)" headers={ALL_PERIODS} histLen={HIST_PERIODS.length}
        rows={incomeStatementRows} defaultExpanded={true} onRecalculate={handleRecalc}
        selectedFieldId={selectedFieldId} upstreamFields={upstreamFields} downstreamFields={downstreamFields} onFieldClick={handleFieldClick} />

      <ScheduleTable title="[3B] Working Capital Schedule (Rows 45-76)" headers={ALL_PERIODS} histLen={HIST_PERIODS.length}
        rows={workingCapitalRows} onRecalculate={handleRecalc}
        selectedFieldId={selectedFieldId} upstreamFields={upstreamFields} downstreamFields={downstreamFields} onFieldClick={handleFieldClick} />

      <ScheduleTable title="[3C] Depreciation Schedule (Rows 80-118)" headers={ALL_PERIODS} histLen={HIST_PERIODS.length}
        rows={depreciationRows} onRecalculate={handleRecalc}
        selectedFieldId={selectedFieldId} upstreamFields={upstreamFields} downstreamFields={downstreamFields} onFieldClick={handleFieldClick} />

      <ScheduleTable title="[3D] Asset Schedule — PP&E + Tax Basis (Rows 126-151)" headers={ALL_PERIODS} histLen={HIST_PERIODS.length}
        rows={assetRows} onRecalculate={handleRecalc}
        selectedFieldId={selectedFieldId} upstreamFields={upstreamFields} downstreamFields={downstreamFields} onFieldClick={handleFieldClick} />

      <ScheduleTable title="[3E] Income Tax — Levered (Rows 155-193)" headers={ALL_PERIODS} histLen={HIST_PERIODS.length}
        rows={taxLeveredRows} onRecalculate={handleRecalc}
        selectedFieldId={selectedFieldId} upstreamFields={upstreamFields} downstreamFields={downstreamFields} onFieldClick={handleFieldClick} />

      <ScheduleTable title="[3F] Income Tax — Unlevered (Rows 197-235)" headers={ALL_PERIODS} histLen={HIST_PERIODS.length}
        rows={taxUnleveredRows} onRecalculate={handleRecalc}
        selectedFieldId={selectedFieldId} upstreamFields={upstreamFields} downstreamFields={downstreamFields} onFieldClick={handleFieldClick} />

      <ScheduleTable title="[3G] Cash Flow Statement (Rows 115-134)" headers={ALL_PERIODS} histLen={HIST_PERIODS.length}
        rows={cashFlowStatementRows} onRecalculate={handleRecalc}
        selectedFieldId={selectedFieldId} upstreamFields={upstreamFields} downstreamFields={downstreamFields} onFieldClick={handleFieldClick} />

      <ScheduleTable title="[3H] Balance Sheet (Rows 138-156)" headers={ALL_PERIODS} histLen={HIST_PERIODS.length}
        rows={balanceSheetRows} onRecalculate={handleRecalc}
        selectedFieldId={selectedFieldId} upstreamFields={upstreamFields} downstreamFields={downstreamFields} onFieldClick={handleFieldClick} />

      <ScheduleTable title="[3I] Debt Schedule Part 1 — Cash + LT Debt (Rows 331-345)" headers={ALL_PERIODS} histLen={HIST_PERIODS.length}
        rows={debtSchedulePart1Rows} onRecalculate={handleRecalc}
        selectedFieldId={selectedFieldId} upstreamFields={upstreamFields} downstreamFields={downstreamFields} onFieldClick={handleFieldClick} />

      <ScheduleTable title="[3J] Debt Schedule Part 2 — Revolving + Net Interest (Rows 347-368)" headers={ALL_PERIODS} histLen={HIST_PERIODS.length}
        rows={debtSchedulePart2Rows} onRecalculate={handleRecalc}
        selectedFieldId={selectedFieldId} upstreamFields={upstreamFields} downstreamFields={downstreamFields} onFieldClick={handleFieldClick} />

      <ScheduleTable title="[3K] Equity Schedule — Common + RE + Dividends (Rows 370-385)" headers={ALL_PERIODS} histLen={HIST_PERIODS.length}
        rows={equityScheduleRows} onRecalculate={handleRecalc}
        selectedFieldId={selectedFieldId} upstreamFields={upstreamFields} downstreamFields={downstreamFields} onFieldClick={handleFieldClick} />

      {/* ─── Action Buttons (Sticky Bottom Bar) ─── */}
      <div className="sticky bottom-0 bg-[var(--canvas-surface)] border-t border-[var(--border-default)] p-3 -mx-4 space-y-2" style={{ zIndex: 30 }}>
        {/* Schedule Status Indicators */}
        {Object.keys(scheduleStatus).length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {Object.entries(scheduleStatus).map(([name, status]) => (
              <span key={name} className={`text-[9px] px-2 py-0.5 rounded ${
                status === 'success' ? 'bg-[var(--color-bullish-bg)] text-[var(--color-bullish)]' :
                status === 'empty' ? 'bg-[var(--color-neutral-bg)] text-[var(--color-neutral)]' :
                'bg-[var(--color-bearish-bg)] text-[var(--color-bearish)]'
              }`}>
                {status === 'success' ? '✅' : status === 'empty' ? '⚠️' : '❌'} {name}
              </span>
            ))}
          </div>
        )}
        {/* Warnings */}
        {(validation.warnings.length > 0 || apiWarnings.length > 0) && (
          <div className="text-[9px] text-[var(--color-neutral)]">
            {validation.warnings.map((w, i) => (
              <div key={`v-${i}`}>⚠ {typeof w === 'string' ? w : (w as any)?.message || JSON.stringify(w)}</div>
            ))}
            {apiWarnings.map((w, i) => <div key={`a-${i}`}>⚠ {w}</div>)}
          </div>
        )}
        {/* Calculate Button — ALWAYS available */}
        <button
          onClick={handleCalculateBuildingBlocks}
          disabled={apiLoading}
          className="w-full bg-[var(--accent-primary)] hover:bg-[var(--accent-primary-hover)] text-[var(--text-primary)] font-bold py-2 rounded text-sm disabled:opacity-50"
        >
          {apiLoading ? '⏳ Calculating...' : '🧮 Calculate Building Block Schedules'}
        </button>
        {/* Continue to Step 10 — only when all schedules OK */}
        <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
          <button
            onClick={handleConfirm}
            disabled={!allSchedulesOk || loading}
            className="btn-next-step"
          >
            {loading ? 'Processing...' : !allSchedulesOk ? 'Calculate first to verify all schedules' : 'Continue to Step 10 →'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default AssumptionsStep;
