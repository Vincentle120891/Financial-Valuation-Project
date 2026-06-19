import React from 'react';
import { useTranslation } from 'react-i18next';
import useValuationStore from '../../store/useValuationStore';
import FootballFieldChart from './FootballFieldChart';
import SensitivityHeatmap from './SensitivityHeatmap';
import ForecastHorizonChart from './ForecastHorizonChart';
import PeerScatterGrid from './PeerScatterGrid';
import { formatSharePrice } from '../../utils/formatters';
// NOTE: calculateDCFOutput import removed — building block calculations are now
// handled by the backend DCFEngine (POST /step-9-calculate-building-blocks).
// See plans/dcf-engine-phase-split-plan.md for details.

/**
 * RunValuationStep — Step 10: Terminal-Style Valuation Dashboard
 *
 * Dense multi-pane layout displaying:
 * 1. Key metrics bar (monospace numerals, dark background)
 * 2. Football Field Chart (horizontal bar ranges, dark theme)
 * 3. Sensitivity Matrix (raw HTML table with terminal grid)
 * 4. Forecast Horizon Chart (dark theme)
 * 5. Peer Scatter Grid (dark theme)
 * 6. Action bar with Back + Run + Export buttons
 */

interface RunValuationStepProps {
  selectedCompany?: any;
  selectedModel?: string;
  selectedScenario?: string;
  confirmedValues?: Record<string, any>;
  loading: boolean;
  onBackToModelSelection?: () => void;
  onBackToAssumptions?: () => void;
  onRunValuation: () => void;
  onViewResults?: () => void;
}

const RunValuationStep: React.FC<RunValuationStepProps> = ({
  selectedCompany,
  selectedModel,
  selectedScenario,
  confirmedValues,
  loading,
  onBackToModelSelection,
  onBackToAssumptions,
  onRunValuation,
  onViewResults,
}) => {
  const { t } = useTranslation();
  const { market, valuationResults, sessionId } = useValuationStore();

  // Get current method results if available (after valuation has run)
  const currentResults = valuationResults[market]?.[selectedModel?.toLowerCase() || 'dcf'] || null;

  const [pdfLoading, setPdfLoading] = React.useState(false);

  const handleExportPdf = async () => {
    if (!sessionId || !selectedModel) return;
    setPdfLoading(true);
    try {
      const API_BASE = (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000/api';
      const response = await fetch(`${API_BASE}/session/${sessionId}/export-pdf`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          methods: [selectedModel],
          market,
          include_sensitivity: true,
          include_peer_comparison: true,
        }),
      });
      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || 'PDF export failed');
      }
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${selectedCompany?.ticker || 'valuation'}_investment_memorandum.pdf`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (err: any) {
      console.warn('PDF export failed:', err.message);
    } finally {
      setPdfLoading(false);
    }
  };

  const getModelName = () => {
    switch (selectedModel) {
      case 'DCF': return 'Discounted Cash Flow';
      case 'DuPont': return 'DuPont Analysis';
      case 'COMPS': return 'Trading Comps';
      default: return 'Unknown';
    }
  };

  // Derive data for charts from store results
  const footballRanges = deriveFootballRanges(currentResults, selectedModel);
  const sensitivityData = deriveSensitivityData(currentResults);
  const forecastData = deriveForecastData(currentResults);
  const peerData = derivePeerData(currentResults, selectedCompany?.ticker);
  
  // Projected schedules from Step 10 calculation
  const calcSchedules = currentResults?.calculated_schedules || currentResults?.detailed_outputs?.supporting_schedules ? {
    ...currentResults?.detailed_outputs,
    ...currentResults?.calculated_schedules,
  } : null;
  const [activeScheduleTab, setActiveScheduleTab] = React.useState('income_statement');

  const currency = market === 'vietnam' ? 'VND' : 'USD';
  const currencySymbol = market === 'vietnam' ? '₫' : '$';

  return (
    <div className="space-y-3">
      {/* ─── Summary Header ─── */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-[14px] font-bold text-[var(--text-primary)]">
            📊 {t('sections.valuation_results')}
          </h2>
          <p className="text-[11px] text-[var(--text-tertiary)] mt-0.5">
            {getModelName()} — {selectedCompany?.name || selectedCompany?.ticker || 'N/A'}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={onBackToModelSelection}
            className="btn-terminal text-[11px]"
          >
            ← Change Model
          </button>
          <button
            onClick={onRunValuation}
            disabled={loading}
            className="btn-terminal primary text-[11px]"
          >
            {loading ? '⏳ Calculating...' : '▶ Run Valuation'}
          </button>
        </div>
      </div>

      {/* ─── Key Metrics Bar (monospace) ─── */}
      <div className="grid grid-cols-3 sm:grid-cols-5 gap-px bg-[var(--canvas-surface-elevated)] rounded-lg overflow-hidden">
        <MetricCell label="TICKER" value={selectedCompany?.ticker || '—'} accent />
        <MetricCell
          label="MARKET PRICE"
          value={selectedCompany?.currentPrice
            ? `${currencySymbol} ${selectedCompany.currentPrice.toLocaleString()}`
            : '—'}
        />
        <MetricCell
          label="MARKET CAP"
          value={selectedCompany?.marketCap
            ? `${currencySymbol} ${(selectedCompany.marketCap / 1_000_000_000).toFixed(1)}B`
            : '—'}
        />
        <MetricCell
          label="SCENARIO"
          value={(selectedScenario || 'base_case').replace('_', ' ').toUpperCase()}
        />
        <MetricCell
          label="CONFIDENCE"
          value={currentResults ? 'HIGH' : 'PENDING'}
          highlight={!!currentResults}
        />
      </div>

      {/* ─── Projected Financial Schedules (from DCFEngine) ─── */}
      {calcSchedules && selectedModel === 'DCF' && (
        <div className="football-field-terminal">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-[11px] uppercase tracking-widest text-[var(--text-tertiary)] font-semibold">
              📋 {t('financialStatements.income_statement')}
            </h3>
          </div>
          {/* Tab bar */}
          <div className="flex flex-wrap gap-1 mb-3">
            {SCHEDULE_TABS.map(tab => (
              <button
                key={tab.key}
                onClick={() => setActiveScheduleTab(tab.key)}
                className={`text-[10px] px-2 py-1 rounded ${
                  activeScheduleTab === tab.key
                    ? 'bg-blue-600 text-[var(--text-primary)]'
                    : 'bg-[var(--canvas-surface-elevated)] text-[var(--text-tertiary)] hover:bg-[var(--canvas-surface-elevated)]'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
          {/* Schedule table */}
          <div className="overflow-x-auto max-h-[300px] overflow-y-auto">
            <ScheduleTable
              schedule={getScheduleData(calcSchedules, activeScheduleTab)}
              currency={currency}
              currencySymbol={currencySymbol}
            />
          </div>
        </div>
      )}

      {/* ─── UFCF & DCF Valuation Schedules ─── */}
      {selectedModel === 'DCF' && (
        <DcfValuationSchedules confirmedValues={confirmedValues} currentResults={currentResults} currency={currency} currencySymbol={currencySymbol} />
      )}

      {/* ─── Football Field Chart (Valuation Range) ─── */}
      <div className="football-field-terminal overflow-hidden">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-[11px] uppercase tracking-widest text-[var(--text-tertiary)] font-semibold">
            📈 {t('sections.calculated_metrics')} ({currency} / Share)
          </h3>
          {currentResults?.valuation_summary?.fair_value_per_share?.value && (
            <span className="text-[11px] font-tabular text-[var(--color-bullish)]">
              Baseline: {currencySymbol} {currentResults.valuation_summary.fair_value_per_share.value.toLocaleString()}
            </span>
          )}
        </div>
        <div className="h-[180px]">
          <FootballFieldChart
            ranges={footballRanges}
            marketPrice={selectedCompany?.currentPrice}
            currency={currency}
          />
        </div>
      </div>

      {/* ─── Sensitivity Matrix (Raw Terminal Table) ─── */}
      <div className="football-field-terminal overflow-hidden">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-[11px] uppercase tracking-widest text-[var(--text-tertiary)] font-semibold">
            🎯 WACC × {t('sections.growth_rate')} ({currency})
          </h3>
        </div>
        <div className="overflow-x-auto">
          <table className="terminal-table">
            <thead>
              <tr>
                <th>WACC ╲ g</th>
                {sensitivityData.tgrValues.map((tgr, idx) => (
                  <th
                    key={idx}
                    className={idx === sensitivityData.baseCaseCol ? 'text-[var(--color-bullish)]' : ''}
                  >
                    {(tgr / 100).toFixed(1)}%
                    {idx === sensitivityData.baseCaseCol ? ' [Base]' : ''}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {sensitivityData.waccValues.map((wacc, rowIdx) => (
                <tr key={rowIdx}>
                  <td>
                    {(wacc / 100).toFixed(1)}%
                    {rowIdx === sensitivityData.baseCaseRow ? ' [Base]' : ''}
                  </td>
                  {sensitivityData.prices[rowIdx]?.map((price, colIdx) => {
                    const isBaseline =
                      rowIdx === sensitivityData.baseCaseRow &&
                      colIdx === sensitivityData.baseCaseCol;
                    return (
                      <td
                        key={colIdx}
                        className={isBaseline ? 'baseline-cell' : ''}
                      >
                        {isBaseline ? '🌟 ' : ''}
                        {currencySymbol} {price.toLocaleString()}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* ─── Forecast Horizon + Peer Scatter (side by side) ─── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        <div className="football-field-terminal overflow-hidden">
          <h3 className="text-[11px] uppercase tracking-widest text-[var(--text-tertiary)] mb-3 font-semibold">
            📊 {t('sections.forecast_drivers')}
          </h3>
          <div className="h-[180px] overflow-hidden">
            <ForecastHorizonChart
              historicalPeriods={forecastData.historical}
              forecastPeriods={forecastData.forecast}
              lastHistoricalPeriod={forecastData.lastHistorical}
            />
          </div>
        </div>

        <div className="football-field-terminal overflow-hidden">
          <h3 className="text-[11px] uppercase tracking-widest text-[var(--text-tertiary)] mb-3 font-semibold">
            🎯 {t('sections.peer_comparison')}
          </h3>
          <div className="h-[180px] overflow-hidden">
            <PeerScatterGrid
              peers={peerData}
              targetTicker={selectedCompany?.ticker}
            />
          </div>
        </div>
      </div>

      {/* ─── Action Bar ─── */}
      <div className="flex items-center justify-between pt-2 border-t border-[var(--border-default)]">
        <button
          onClick={onBackToAssumptions}
          className="btn-terminal text-[11px]"
        >
          ⬅ Back to Assumptions
        </button>
        <div className="flex items-center gap-2">
          <button
            className="btn-terminal text-[11px]"
            onClick={handleExportPdf}
            disabled={pdfLoading || !sessionId}
            title={pdfLoading ? 'Generating PDF...' : 'Download valuation report as PDF'}
          >
            {pdfLoading ? '📄 Generating...' : '📄 Export Memorandum'}
          </button>
          <button
            onClick={onRunValuation}
            disabled={loading}
            className="btn-terminal primary text-[11px]"
          >
            {loading ? '⏳ Calculating...' : '▶ Execute Valuation'}
          </button>
          {currentResults && onViewResults && (
            <button
              onClick={onViewResults}
              className="btn-terminal text-[11px] bg-emerald-700 hover:bg-[var(--color-bullish)]"
            >
              📊 View Results →
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

// ─── DCF Valuation Schedules (UFCF + DCF Perpetuity + DCF Exit Multiple) ──

const DcfValuationSchedules: React.FC<{
  confirmedValues: Record<string, any>;
  currentResults: any;
  currency: string;
  currencySymbol: string;
}> = ({ confirmedValues, currentResults, currency, currencySymbol }) => {
  const { t } = useTranslation();
  const [expanded, setExpanded] = React.useState<Record<string, boolean>>({});

  // Build minimal inputs from confirmed values (no longer used for calculation)
  const inputs = React.useMemo((): any => {
    const get = (key: string, fallback: number) => {
      const cv = confirmedValues[key];
      return cv?.value !== undefined ? Number(cv.value) : fallback;
    };
    return {
      revenueGrowth: Array(5).fill(0),
      inflationRate: Array(5).fill(0),
      taxRate: get('dcf_tax_rate', 0.21),
      arDays: get('dcf_receivables_days', 45),
      invDays: get('dcf_inventory_days', 30),
      apDays: get('dcf_payables_days', 40),
      capex: Array(5).fill(0),
      usefulLifeExisting: get('dcf_useful_life_existing', 16),
      usefulLifeNew: get('dcf_useful_life_new', 20),
      firstYearDepreciationRate: get('dcf_first_year_dep_rate', 50),
      wacc: get('dcf_wacc', 0.10),
      riskFreeRate: get('dcf_risk_free_rate', 0.04),
      equityRiskPremium: get('dcf_equity_risk_premium', 0.06),
      beta: get('dcf_beta', 1.0),
      costOfDebt: get('dcf_cost_of_debt', 0.05),
      debtToEquity: get('dcf_debt_to_equity', 0.3),
      terminalGrowthRate: get('dcf_terminal_growth_rate', 0.025),
      terminalEbitdaMultiple: get('dcf_terminal_ebitda_multiple', 10),
      changeInLtDebt: Array(5).fill(0),
      changeInCommonEquity: Array(5).fill(0),
      dividendPayoutRatio: get('dcf_dividend_payout_ratio', 0),
      cashInterestRate: get('dcf_cash_interest_rate', 0.01),
      revolvingCreditRate: get('dcf_revolving_credit_rate', 0.05),
      ltDebtInterestRate: get('dcf_lt_debt_interest_rate', 0.06),
      firstYearTaxDepRate: get('dcf_first_year_tax_dep_rate', 0.50),
      blendedTaxDepRate: get('dcf_blended_tax_dep_rate', 0.15),
      firstYearAcctgDepRate: get('dcf_first_year_acctg_dep_rate', 0.50),
      currentPrice: get('dcf_current_price', 0),
      sharesOutstanding: get('dcf_shares_outstanding', 0),
      netDebt: get('dcf_net_debt', 0),
      historicalRevenue: [0, 0, 0],
      historicalCogs: [0, 0, 0],
      historicalSga: [0, 0, 0],
      historicalOtherOpex: [0, 0, 0],
      historicalCapex: [0, 0, 0],
      historicalDepreciation: [0, 0, 0],
      historicalInterestExpense: [0, 0, 0],
      historicalAr: [0, 0, 0],
      historicalInventory: [0, 0, 0],
      historicalAp: [0, 0, 0],
      historicalPpe: [0, 0, 0],
      historicalTaxBasis: [0, 0, 0],
      historicalTaxLosses: [0, 0, 0],
    };
  }, [confirmedValues]);

  // Extract DCF valuation data from backend results (after valuation has run)
  // currentResults comes from valuationResults[market]['dcf'] — the full backend response
  const output: any = React.useMemo(() => {
    if (!currentResults) {
      return {
        ufcf: { years: [], ebitda: [], currentTaxUnlevered: [], capex: [], wcChange: [], ufcfEbitdaMethod: [], ufcfNetIncomeMethod: [], reconciliation: [] },
        dcfPerpetuity: { years: [], terminalUfcf: 0, terminalValue: 0, pvDiscreteCfs: 0, pvTerminalValue: 0, enterpriseValue: 0, equityValue: 0, fairValuePerShare: 0 },
        dcfExitMultiple: { years: [], terminalEbitda: 0, terminalValue: 0, pvDiscreteCfs: 0, pvTerminalValue: 0, enterpriseValue: 0, equityValue: 0, fairValuePerShare: 0 },
      };
    }

    // Backend ValuationOutput.to_dict() structure:
    //   main_outputs: { perpetuity_method: {...}, exit_multiple_method: {...} }
    //   supporting_schedules: { ufcf: { ebitda, current_tax_unlevered, capex, change_in_nwc, ufcf, ... } }
    //   dcf_details: { perpetuity_method: { terminal_value, pv_terminal_value, enterprise_value, ... }, exit_multiple_method: {...} }
    // Step 10 endpoint wraps these in calculated_schedules:
    //   calculated_schedules.ufcf = supporting_schedules.ufcf
    //   calculated_schedules.dcf_details = dcf_details
    //   calculated_schedules.main_outputs = main_outputs
    const vs = currentResults.valuation_summary || {};
    const schedules = currentResults.calculated_schedules || {};
    const details = currentResults.detailed_outputs || {};

    // UFCF schedule — from calculated_schedules.ufcf (which is supporting_schedules.ufcf)
    const ufcfData = schedules.ufcf || details.supporting_schedules?.ufcf || {};
    // DCF details — from calculated_schedules.dcf_details
    const dcfDetails = schedules.dcf_details || details.dcf_details || {};
    // Main outputs — from calculated_schedules.main_outputs
    const mainOutputs = schedules.main_outputs || details.main_outputs || {};

    // Perpetuity method data
    const perpDetails = dcfDetails.perpetuity_method || dcfDetails.perpetuity || {};
    const perpMain = mainOutputs.perpetuity_method || mainOutputs.perpetuity || {};
    // Exit multiple method data
    const exitDetails = dcfDetails.exit_multiple_method || dcfDetails.multiple || {};
    const exitMain = mainOutputs.exit_multiple_method || mainOutputs.multiple || {};

    return {
      ufcf: {
        years: ufcfData.years || [],
        ebitda: ufcfData.ebitda || [],
        currentTaxUnlevered: ufcfData.current_tax_unlevered || ufcfData.currentTaxUnlevered || [],
        capex: ufcfData.capex || [],
        wcChange: ufcfData.change_in_nwc || ufcfData.wcChange || [],
        ufcfEbitdaMethod: ufcfData.ufcf || ufcfData.ufcfEbitdaMethod || [],
        ufcfNetIncomeMethod: ufcfData.ufcf_net_income || ufcfData.ufcfNetIncomeMethod || [],
        reconciliation: ufcfData.reconciliation || [],
      },
      dcfPerpetuity: {
        years: perpDetails.years || [],
        terminalUfcf: Array.isArray(perpDetails.ufcf) ? perpDetails.ufcf[perpDetails.ufcf.length - 1] || 0 : 0,
        terminalValue: perpDetails.terminal_value || 0,
        pvDiscreteCfs: perpDetails.pv_discrete_cf || 0,
        pvTerminalValue: perpDetails.pv_terminal_value || 0,
        enterpriseValue: perpMain.enterprise_value || vs.enterprise_value?.value || 0,
        equityValue: perpMain.equity_value || vs.equity_value?.value || 0,
        fairValuePerShare: perpMain.equity_value_per_share || vs.fair_value_per_share?.value || 0,
      },
      dcfExitMultiple: {
        years: exitDetails.years || [],
        terminalEbitda: exitDetails.terminal_ebitda || 0,
        terminalValue: exitDetails.terminal_value || 0,
        pvDiscreteCfs: exitDetails.pv_discrete_cf || 0,
        pvTerminalValue: exitDetails.pv_terminal_value || 0,
        enterpriseValue: exitMain.enterprise_value || 0,
        equityValue: exitMain.equity_value || 0,
        fairValuePerShare: exitMain.equity_value_per_share || 0,
      },
    };
  }, [currentResults]);

  const toggle = (key: string) => setExpanded(prev => ({ ...prev, [key]: !prev[key] }));

  // Derive year headers from backend data
  const ufcfYears = output.ufcf.years || [];
  const dcfPerpYears = output.dcfPerpetuity.years || [];
  const dcfExitYears = output.dcfExitMultiple.years || [];

  const sections = [
    {
      key: 'ufcf',
      title: '[3G] UFCF Schedule',
      headers: ufcfYears.length > 0 ? ufcfYears : ['FY2023', 'FY2024', 'FY2025', 'FY2026', 'FY2027', 'FY2028'],
      rows: [
        { label: 'EBITDA', values: output.ufcf.ebitda },
        { label: '- Unlevered Tax', values: output.ufcf.currentTaxUnlevered.map(v => -v) },
        { label: '- Capex', values: (output.ufcf.capex || []).map((v: number) => -Math.abs(v)) },
        { label: '+/- WC Change', values: output.ufcf.wcChange },
        { label: 'UFCF (EBITDA Method)', values: output.ufcf.ufcfEbitdaMethod, isHighlight: true },
        { label: 'UFCF (NI Method)', values: output.ufcf.ufcfNetIncomeMethod },
        { label: 'Reconciliation', values: output.ufcf.reconciliation },
      ],
    },
    {
      key: 'dcf_perp',
      title: '[3H] DCF — Perpetuity Method',
      headers: ['Value'],
      rows: [
        { label: 'Terminal UFCF', values: [output.dcfPerpetuity.terminalUfcf] },
        { label: 'Terminal Value', values: [output.dcfPerpetuity.terminalValue] },
        { label: 'PV Discrete CFs', values: [Array.isArray(output.dcfPerpetuity.pvDiscreteCfs) ? output.dcfPerpetuity.pvDiscreteCfs.reduce((a: number, b: number) => a + b, 0) : output.dcfPerpetuity.pvDiscreteCfs] },
        { label: 'PV Terminal Value', values: [output.dcfPerpetuity.pvTerminalValue] },
        { label: 'Enterprise Value', values: [output.dcfPerpetuity.enterpriseValue], isHighlight: true },
        { label: 'Equity Value', values: [output.dcfPerpetuity.equityValue], isHighlight: true },
        { label: 'Fair Value / Share', values: [output.dcfPerpetuity.fairValuePerShare], isHighlight: true },
      ],
    },
    {
      key: 'dcf_exit',
      title: '[3I] DCF — Exit Multiple Method',
      headers: ['Value'],
      rows: [
        { label: 'Terminal EBITDA', values: [output.dcfExitMultiple.terminalEbitda] },
        { label: 'Terminal Value', values: [output.dcfExitMultiple.terminalValue] },
        { label: 'PV Discrete CFs', values: [Array.isArray(output.dcfExitMultiple.pvDiscreteCfs) ? output.dcfExitMultiple.pvDiscreteCfs.reduce((a: number, b: number) => a + b, 0) : output.dcfExitMultiple.pvDiscreteCfs] },
        { label: 'PV Terminal Value', values: [output.dcfExitMultiple.pvTerminalValue] },
        { label: 'Enterprise Value', values: [output.dcfExitMultiple.enterpriseValue], isHighlight: true },
        { label: 'Equity Value', values: [output.dcfExitMultiple.equityValue], isHighlight: true },
        { label: 'Fair Value / Share', values: [output.dcfExitMultiple.fairValuePerShare], isHighlight: true },
      ],
    },
  ];

  return (
    <div className="football-field-terminal">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-[11px] uppercase tracking-widest text-[var(--text-tertiary)] font-semibold">
          💰 {t('sections.dcf_model_inputs')}
        </h3>
      </div>
      {sections.map((section) => (
        <div key={section.key} className="border border-[var(--border-default)] rounded mb-2">
          <button
            onClick={() => toggle(section.key)}
            className="w-full flex items-center justify-between px-3 py-2 bg-[var(--canvas-surface-elevated)]/50 hover:bg-[var(--canvas-surface-elevated)] text-[10px] font-semibold text-[var(--text-primary)]"
          >
            <span>{section.title}</span>
            <span className="text-[var(--text-tertiary)]">{expanded[section.key] ? '▼' : '▶'}</span>
          </button>
          {expanded[section.key] && (
            <div className="overflow-x-auto">
              <table className="w-full text-[10px] font-mono">
                <thead>
                  <tr className="bg-[var(--canvas-surface-elevated)]/30">
                    <th className="text-left px-2 py-1 text-[var(--text-tertiary)]">Item</th>
                    {section.headers.map((h, i) => (
                      <th key={i} className="text-right px-2 py-1 text-[var(--text-tertiary)]">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {section.rows.map((row, ri) => (
                    <tr key={ri} className={`border-t border-[var(--border-default)] ${row.isHighlight ? 'bg-[var(--accent-primary-subtle)] font-bold' : ''}`}>
                      <td className="px-2 py-1 text-[var(--text-primary)]">{row.label}</td>
                      {row.values.map((val, vi) => (
                        <td key={vi} className="text-right px-2 py-1 text-[var(--text-primary)] tabular-nums">
                          {val !== undefined ? val.toLocaleString(undefined, { maximumFractionDigits: 0 }) : '—'}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      ))}
    </div>
  );
};

// ─── Metric Cell sub-component ─────────────────────────────────────────
const MetricCell: React.FC<{
  label: string;
  value: string;
  accent?: boolean;
  highlight?: boolean;
}> = ({ label, value, accent, highlight }) => (
  <div className={`bg-[var(--canvas-bg)] p-3 ${highlight ? 'bg-emerald-950/30' : accent ? 'bg-blue-950/30' : ''}`}>
    <p className="text-[9px] font-medium text-[var(--text-tertiary)] uppercase tracking-widest mb-0.5">
      {label}
    </p>
    <p
      className={`text-[13px] font-bold font-tabular truncate ${
        highlight ? 'text-[var(--color-bullish)]' : accent ? 'text-[var(--accent-primary)]' : 'text-[var(--text-primary)]'
      }`}
    >
      {value}
    </p>
  </div>
);

// ─── Data derivation functions ─────────────────────────────────────────

interface ChartRange {
  method: string;
  label: string;
  low: number;
  base: number;
  high: number;
  color: string;
}

function deriveFootballRanges(results: any, model?: string): ChartRange[] {
  if (!results) {
    return [
      { method: 'DCF', label: 'DCF Engine', low: 0, base: 0, high: 0, color: 'var(--accent-primary)' },
      { method: 'COMPS', label: 'Trading Comps', low: 0, base: 0, high: 0, color: 'var(--accent-primary)' },
      { method: 'DUPONT', label: 'DuPont Analysis', low: 0, base: 0, high: 0, color: 'var(--color-manual)' },
    ];
  }

  const summary = results.valuation_summary || {};
  const detailed = results.detailed_outputs || {};
  const scenarioAnalysis = results.scenario_analysis || {};
  const ranges: ChartRange[] = [];

  // Extract per-share fair value from valuation_summary
  const fairValue = summary.fair_value_per_share?.value;

  // Try to get actual Bull/Bear per-share values from scenario_analysis
  const bullValue = scenarioAnalysis['Bull Case']?.fair_value_per_share?.value;
  const bearValue = scenarioAnalysis['Bear Case']?.fair_value_per_share?.value;

  if (fairValue && fairValue > 0) {
    const base = fairValue;
    // Always compute range from base ±15% to ensure per-share scale
    // Only use scenario values if they're within reasonable per-share range
    const low = (bearValue && bearValue > 0 && bearValue < base * 2) ? bearValue : base * 0.85;
    const high = (bullValue && bullValue > 0 && bullValue < base * 5) ? bullValue : base * 1.15;

    // Determine method label from detailed_outputs
    if (detailed.dcf_analysis || detailed.main_outputs) {
      // DCF result
      ranges.push({ method: 'DCF', label: 'DCF Engine', low, base, high, color: 'var(--accent-primary)' });
    } else if (detailed.comps_analysis) {
      // Comps result
      ranges.push({ method: 'COMPS', label: 'Trading Comps', low, base, high, color: 'var(--accent-primary)' });
    } else if (detailed.dupont_analysis) {
      // DuPont result (no share price, but show if available)
      ranges.push({ method: 'DUPONT', label: 'DuPont Analysis', low, base, high, color: 'var(--color-manual)' });
    } else {
      // Generic — use model prop to label
      const label = model === 'DCF' ? 'DCF Engine' : model === 'COMPS' ? 'Trading Comps' : 'DuPont Analysis';
      const color = model === 'DCF' ? 'var(--accent-primary)' : model === 'COMPS' ? 'var(--accent-primary)' : 'var(--color-manual)';
      ranges.push({ method: model || 'DCF', label, low, base, high, color });
    }
  }

  // Also check for DCF-specific perpetuity vs exit multiple ranges
  if (detailed.main_outputs) {
    const perp = detailed.main_outputs.perpetuity_method;
    const mult = detailed.main_outputs.exit_multiple_method;
    if (perp?.equity_value_per_share && !ranges.find(r => r.method === 'DCF')) {
      ranges.push({
        method: 'DCF',
        label: 'DCF (Perpetuity)',
        low: perp.equity_value_per_share * 0.85,
        base: perp.equity_value_per_share,
        high: perp.equity_value_per_share * 1.15,
        color: 'var(--accent-primary)',
      });
    }
    if (mult?.equity_value_per_share && !ranges.find(r => r.method === 'DCF_MULT')) {
      ranges.push({
        method: 'DCF_MULT',
        label: 'DCF (Exit Multiple)',
        low: mult.equity_value_per_share * 0.85,
        base: mult.equity_value_per_share,
        high: mult.equity_value_per_share * 1.15,
        color: 'var(--accent-primary)',
      });
    }
  }

  // Fallback if no ranges found
  if (ranges.length === 0) {
    return [
      { method: 'DCF', label: 'DCF Engine', low: 0, base: 0, high: 0, color: 'var(--accent-primary)' },
      { method: 'COMPS', label: 'Trading Comps', low: 0, base: 0, high: 0, color: 'var(--accent-primary)' },
      { method: 'DUPONT', label: 'DuPont Analysis', low: 0, base: 0, high: 0, color: 'var(--color-manual)' },
    ];
  }

  return ranges;
}

function deriveSensitivityData(results: any) {
  // Use backend sensitivity_analysis if available
  const sensAnalysis = results?.sensitivity_analysis;
  if (sensAnalysis?.ranges?.wacc && sensAnalysis?.ranges?.growth && sensAnalysis?.results_matrix) {
    // Convert from decimal to basis points for display
    const waccValues = sensAnalysis.ranges.wacc.map((w: number) => Math.round(w * 10000));
    const tgrValues = sensAnalysis.ranges.growth.map((g: number) => Math.round(g * 10000));

    // Find base case indices (where wacc/growth are closest to median values)
    const baseCaseCol = Math.floor(tgrValues.length / 2);
    const baseCaseRow = Math.floor(waccValues.length / 2);

    // Convert results_matrix prices (enterprise values) to per-share prices
    // The matrix values are EVs, divide by shares to get per-share
    const fairValue = results?.valuation_summary?.fair_value_per_share?.value || 1;
    const basePrice = fairValue;

    // Scale the matrix to per-share values relative to base
    const baseEV = sensAnalysis.results_matrix[baseCaseRow]?.[baseCaseCol] || 1;
    const prices = sensAnalysis.results_matrix.map((row: number[]) =>
      row.map((val: number) => {
        if (!val || val === 0) return 0;
        // Scale: if baseEV maps to basePrice, scale others proportionally
        return Math.round((val / baseEV) * basePrice) || 0;
      })
    );

    return {
      waccValues,
      tgrValues,
      prices,
      baseCaseRow,
      baseCaseCol,
    };
  }

  // Fallback: generate synthetic sensitivity from fair value
  const fairValue = results?.valuation_summary?.fair_value_per_share?.value;
  const waccValues = [750, 800, 850, 900, 950];   // basis points (7.5% - 9.5%)
  const tgrValues = [150, 175, 200, 225, 250];     // basis points (1.5% - 2.5%)
  const basePrice = fairValue || 100;

  // Generate sensitivity matrix
  const prices = tgrValues.map((tgr, rowIdx) =>
    waccValues.map((wacc, colIdx) => {
      const tgrEffect = ((tgr - 200) / 100) * 8 * (basePrice / 100);
      const waccEffect = ((850 - wacc) / 100) * 12 * (basePrice / 100);
      return Math.round(basePrice + tgrEffect + waccEffect);
    })
  );

  return {
    waccValues,
    tgrValues,
    prices,
    baseCaseRow: 2,
    baseCaseCol: 2,
  };
}

function deriveForecastData(results: any) {
  const detailed = results?.detailed_outputs || {};

  // Try to extract forecast data from DCF engine output
  if (detailed.supporting_schedules?.income_statement) {
    const is = detailed.supporting_schedules.income_statement;
    const ufcf = detailed.supporting_schedules.ufcf;
    const years = is.years || [];

    const forecast = years.map((yr: string, i: number) => ({
      period: yr,
      revenue: is.revenue?.[i] || 0,
      fcf: ufcf?.ufcf?.[i] || 0,
      ebitda: is.ebitda?.[i] || 0,
      isForecast: true,
    }));

    // Extract historical from DCF inputs if available
    const hist = detailed.metadata || {};
    const historical = [
      { period: 'FY-2', revenue: 0, fcf: 0 },
      { period: 'FY-1', revenue: 0, fcf: 0 },
      { period: 'FY0', revenue: 0, fcf: 0 },
    ];

    return {
      historical,
      forecast,
      lastHistorical: historical[historical.length - 1]?.period,
    };
  }

  // Try DuPont trend analysis for historical ratios
  if (detailed.dupont_analysis?.trend_analysis?.length > 0) {
    const trend = detailed.dupont_analysis.trend_analysis;
    const historical = trend.map((t: any) => ({
      period: t.year,
      revenue: 0,
      fcf: 0,
      roe: t.roe,
      netMargin: t.net_margin,
    }));

    return {
      historical,
      forecast: [],
      lastHistorical: historical[historical.length - 1]?.period,
    };
  }

  // Fallback: default data
  const historical = [
    { period: 'FY2021', revenue: 0, fcf: 0 },
    { period: 'FY2022', revenue: 0, fcf: 0 },
    { period: 'FY2023', revenue: 0, fcf: 0 },
  ];

  const forecast = [
    { period: 'FY2024', revenue: 0, fcf: 0, isForecast: true },
    { period: 'FY2025', revenue: 0, fcf: 0, isForecast: true },
    { period: 'FY2026', revenue: 0, fcf: 0, isForecast: true },
  ];

  return {
    historical,
    forecast,
    lastHistorical: historical[historical.length - 1]?.period,
  };
}

function derivePeerData(results: any, targetTicker?: string) {
  const detailed = results?.detailed_outputs || {};

  // Check for peer scatter data from comps analysis
  if (detailed.comps_analysis?.peer_scatter?.length > 0) {
    return detailed.comps_analysis.peer_scatter.map((peer: any) => ({
      ticker: peer.ticker,
      x: peer.ebitda_margin ? peer.ebitda_margin * 100 : (peer.ev_to_ebitda || 0),
      y: peer.ev_to_ebitda || peer.pe_ratio || 0,
      isTarget: peer.ticker === targetTicker || peer.is_target,
    }));
  }

  // Check for peer multiples from comps analysis
  if (detailed.comps_analysis?.peer_multiples?.length > 0) {
    return detailed.comps_analysis.peer_multiples.map((peer: any) => ({
      ticker: peer.ticker,
      x: peer.pe_ltm || 0,
      y: peer.ev_ebitda_ltm || 0,
      isTarget: peer.ticker === targetTicker || peer.is_primary,
    }));
  }

  // Fallback: empty
  return [];
}

// ─── Projected Schedules Constants ───────────────────────────────────

const SCHEDULE_TABS = [
  { key: 'income_statement', label: 'Income Stmt' },
  { key: 'cash_flow_statement', label: 'Cash Flow' },
  { key: 'balance_sheet', label: 'Balance Sheet' },
  { key: 'working_capital', label: 'Working Cap' },
  { key: 'depreciation', label: 'Depreciation' },
  { key: 'tax_levered', label: 'Tax (Levered)' },
  { key: 'ufcf', label: 'UFCF' },
  { key: 'ufcf_3_methods', label: 'UFCF×3' },
  { key: 'npv_xnpv', label: 'NPV/XNPV' },
];

function getScheduleData(schedules: any, tab: string): { title: string; headers: string[]; rows: string[][] } | null {
  if (!schedules) return null;

  const formatVal = (v: any) => {
    if (v === null || v === undefined) return '—';
    if (typeof v === 'number') return v.toLocaleString(undefined, { maximumFractionDigits: 1 });
    return String(v);
  };

  const buildTable = (title: string, data: any, fieldMap: Record<string, string>) => {
    if (!data) return null;
    const years = data.years || [];
    const headers = ['Metric', ...years];
    const rows = Object.entries(fieldMap).map(([label, key]) => [
      label,
      ...(data[key] || []).map((v: any) => formatVal(v)),
    ]);
    return { title, headers, rows };
  };

  switch (tab) {
    case 'income_statement': {
      const s = schedules.supporting_schedules?.income_statement;
      return buildTable('Income Statement', s, {
        'Revenue': 'revenue',
        'COGS': 'cogs',
        'Gross Profit': 'gross_profit',
        'SG&A': 'sga',
        'Other OpEx': 'other_opex',
        'EBITDA': 'ebitda',
        'Depreciation': 'depreciation',
        'EBIT': 'ebit',
        'Interest Expense': 'interest_expense',
        'EBT': 'ebt',
        'Current Tax': 'current_tax',
        'Deferred Tax': 'deferred_tax',
        'Total Tax': 'total_tax',
        'Net Income': 'net_income',
      });
    }
    case 'cash_flow_statement': {
      const s = schedules.cash_flow_statement;
      return buildTable('Cash Flow Statement', s, {
        'Net Income': 'net_income',
        'Deferred Taxes': 'deferred_taxes',
        'Depreciation': 'depreciation',
        'Cash from AR': 'cash_from_ar',
        'Cash from Inventory': 'cash_from_inventory',
        'Cash from AP': 'cash_from_ap',
        'Subtotal CFO': 'subtotal_cfo',
        'Capital Expenditure': 'capital_expenditure',
        'Subtotal CFI': 'subtotal_cfi',
        'Change in LT Debt': 'change_in_lt_debt',
        'Change in Equity': 'change_in_common_equity',
        'Dividends': 'dividends',
        'Revolving Credit': 'revolving_credit',
        'Subtotal CFF': 'subtotal_cff',
        'Beginning Cash': 'beginning_cash',
        'Increase/Decrease': 'increase_decrease',
        'Ending Cash': 'ending_cash',
      });
    }
    case 'balance_sheet': {
      const s = schedules.balance_sheet;
      return buildTable('Balance Sheet', s, {
        'Cash': 'cash',
        'Accounts Receivable': 'accounts_receivable',
        'Inventories': 'inventories',
        'Non-Current Marketable Securities': 'non_current_marketable_securities',
        'Total Current Assets': 'total_current_assets',
        'PP&E Gross': 'ppe_gross',
        'Accumulated Depreciation': 'accumulated_depreciation',
        'PP&E Net': 'ppe_net',
        'Total Assets': 'total_assets',
        'Accounts Payable': 'accounts_payable',
        'Other Current Liabilities': 'other_current_liabilities',
        'Current Debt': 'current_debt',
        'Revolving Credit': 'revolving_credit',
        'Total Current Liabilities': 'total_current_liabilities',
        'Deferred Tax Liabilities': 'deferred_tax_liabilities',
        'Long-Term Debt': 'long_term_debt',
        'Total Liabilities': 'total_liabilities',
        'Common Equity': 'common_equity',
        'Retained Earnings': 'retained_earnings',
        "Total Shareholders' Equity": 'total_shareholders_equity',
        'Total L+E': 'total_liabilities_equity',
        'Balance Check': 'balance_check',
      });
    }
    case 'working_capital': {
      const s = schedules.supporting_schedules?.working_capital;
      return buildTable('Working Capital', s, {
        'AR Balance': 'ar_balance',
        'Inventory Balance': 'inventory_balance',
        'AP Balance': 'ap_balance',
        'Net Working Capital': 'nwc',
        'Change in NWC': 'change_in_nwc',
        'AR Days': 'ar_days',
        'Inventory Days': 'inv_days',
        'AP Days': 'ap_days',
      });
    }
    case 'depreciation': {
      const s = schedules.supporting_schedules?.depreciation;
      return buildTable('Depreciation Schedule', s, {
        'CapEx': 'capex',
        'Existing Asset Dep': 'existing_asset_dep',
        'New Asset Dep': 'new_asset_dep',
        'Total Depreciation': 'total_depreciation',
        'Gross PPE Ending': 'gross_ppe_ending',
        'Tax Basis Ending': 'tax_basis_ending',
      });
    }
    case 'tax_levered': {
      const s = schedules.supporting_schedules?.tax_levered;
      return buildTable('Tax Schedule (Levered)', s, {
        'EBT': 'ebt',
        'Accounting Dep': 'accounting_dep',
        'Tax Dep': 'tax_dep',
        'EBT Adjusted': 'ebt_adjusted',
        'NOL Opening': 'nol_opening',
        'NOL New': 'nol_new',
        'NOL Used': 'nol_used',
        'NOL Ending': 'nol_ending',
        'Taxable Income': 'taxable_income',
        'Current Tax': 'current_tax',
        'Total Tax': 'total_tax',
        'Deferred Tax': 'deferred_tax',
      });
    }
    case 'ufcf': {
      const s = schedules.supporting_schedules?.ufcf;
      return buildTable('Unlevered Free Cash Flow', s, {
        'EBITDA': 'ebitda',
        'Current Tax (Unlevered)': 'current_tax_unlevered',
        'CapEx': 'capex',
        'Change in NWC': 'change_in_nwc',
        'UFCF': 'ufcf',
        'Tax Shield': 'tax_shield',
      });
    }
    case 'ufcf_3_methods': {
      const s = schedules.ufcf_3_methods;
      if (!s) return null;
      const years = s.years || [];
      return {
        title: 'UFCF — 3 Methods Cross-Check',
        headers: ['Method', ...years],
        rows: [
          ['EBIT Method', ...(s.ebit_method || []).map((v: any) => formatVal(v))],
          ['Net Income Method', ...(s.net_income_method || []).map((v: any) => formatVal(v))],
          ['EBITDA Method', ...(s.ebitda_method || []).map((v: any) => formatVal(v))],
          ['Reconcile?', s.methods_reconcile ? '✅ Yes' : '❌ No'],
        ],
      };
    }
    case 'npv_xnpv': {
      const s = schedules.npv_xnpv;
      if (!s) return null;
      return {
        title: 'NPV / XNPV / IRR',
        headers: ['Metric', 'Value'],
        rows: [
          ['NPV (End-of-Period)', formatVal(s.npv_end_of_period)],
          ['XNPV (End-of-Period)', formatVal(s.xnpv_end_of_period)],
          ['Equity/Share (End)', formatVal(s.equity_per_share_end)],
          ['NPV (Mid-Period)', formatVal(s.npv_mid_period)],
          ['XNPV (Mid-Period)', formatVal(s.xnpv_mid_period)],
          ['Equity/Share (Mid)', formatVal(s.equity_per_share_mid)],
          ['IRR', s.irr != null ? `${(s.irr * 100).toFixed(2)}%` : '—'],
          ['XIRR (End)', s.xirr_end_of_period != null ? `${(s.xirr_end_of_period * 100).toFixed(2)}%` : '—'],
          ['XIRR (Mid)', s.xirr_mid_period != null ? `${(s.xirr_mid_period * 100).toFixed(2)}%` : '—'],
        ],
      };
    }
    default:
      return null;
  }
}

// ─── Schedule Table Component ────────────────────────────────────────

const ScheduleTable: React.FC<{
  schedule: { title: string; headers: string[]; rows: string[][] } | null;
  currency: string;
  currencySymbol: string;
}> = ({ schedule, currencySymbol }) => {
  if (!schedule) {
    return <p className="text-[11px] text-[var(--text-tertiary)]">No data available for this schedule.</p>;
  }

  return (
    <div>
      <h4 className="text-[11px] font-semibold text-[var(--text-primary)] mb-2">{schedule.title}</h4>
      <table className="terminal-table text-[10px]">
        <thead>
          <tr>
            {schedule.headers.map((h, i) => (
              <th key={i} className={i === 0 ? 'text-left' : 'text-right'}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {schedule.rows.map((row, ri) => (
            <tr key={ri} className={ri % 2 === 0 ? 'bg-[var(--canvas-bg)]/50' : ''}>
              {row.map((cell, ci) => (
                <td key={ci} className={ci === 0 ? 'text-left text-[var(--text-primary)]' : 'text-right font-tabular'}>
                  {ci > 0 && cell !== '—' ? `${currencySymbol} ${cell}` : cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default RunValuationStep;
