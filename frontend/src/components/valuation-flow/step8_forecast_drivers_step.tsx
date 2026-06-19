import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { LineChart, Line, ResponsiveContainer, Tooltip, XAxis } from 'recharts';
import { generateAISuggestion, generateScenarios } from '../../services/step8_10_valuation_service';
import { getCompleteFinancialStatements } from '../../services/api';
import DataFieldDisplay from './DataFieldDisplay';
import HistoricalStatements from './HistoricalStatements';

// ─── Helpers for backend category extraction ──────────────────────────────────

/**
 * Convert a scalar value to a 5-element array for forecast drivers.
 * If value is null/undefined, fills with fallback for each year.
 */
const toSixYearArray = (value: number | null | undefined, fallback: number = 0): number[] =>
  Array(6).fill(value != null ? value : fallback);

/**
 * Extract the best available value from a backend category assumption.
 * Priority: final_value > user_value > historical_trendline.average > historical_trendline.latest_value
 */
const getAssumptionValue = (
  categories: Record<string, any>,
  categoryKey: string,
  metricName: string,
): number | null => {
  const category = categories[categoryKey];
  if (!category?.assumptions) return null;
  const assumption = category.assumptions.find((a: any) => a.metric === metricName);
  if (!assumption) return null;

  // Priority: final_value > user_value > trendline average/latest
  // Unwrap DataField objects: {value: 0.05, status: "RETRIEVED"} → 0.05
  const unwrap = (v: any): number | null => {
    if (v == null) return null;
    if (typeof v === 'number') return v;
    if (typeof v === 'object' && 'value' in v && typeof v.value === 'number') return v.value;
    return null;
  };
  const fv = unwrap(assumption.final_value);
  if (fv != null) return fv;
  const uv = unwrap(assumption.user_value);
  if (uv != null) return uv;
  if (assumption.historical_trendline) {
    const tl = assumption.historical_trendline;
    return unwrap(tl.average) ?? unwrap(tl.latest_value) ?? null;
  }
  return null;
};

/**
 * Build a 5-year array from a backend category assumption.
 * Prefers year_values (trend-based projection) when available from backend.
 * Falls back to scalar final_value repeated across 5 years.
 */
const getAssumptionFiveYearArray = (
  categories: Record<string, any>,
  categoryKey: string,
  metricName: string,
  fallback: number = 0,
): number[] => {
  const category = categories[categoryKey];
  if (!category?.assumptions) return Array(5).fill(fallback);
  const assumption = category.assumptions.find((a: any) => a.metric === metricName);
  if (!assumption) return Array(5).fill(fallback);

  // Prefer year_values (5-year trend projection from backend)
  if (assumption.year_values && Object.keys(assumption.year_values).length > 0) {
    // Sort by numeric key to ensure Year 1-5 order
    const sorted = Object.entries(assumption.year_values)
      .sort(([a], [b]) => Number(a) - Number(b));
    const vals = sorted.map(([, v]) => Number(v));
    // Ensure exactly 5 elements
    while (vals.length < 5) vals.push(vals[vals.length - 1] ?? fallback);
    return vals.slice(0, 5);
  }

  // Fallback: repeat scalar value across 5 years
  const value = getAssumptionValue(categories, categoryKey, metricName);
  return toSixYearArray(value, fallback);
};

// --- Sparkline Chart -----------------------------------------------------------

/** Maps forecast driver field names to backend category + metric for trendline lookup */
const FIELD_TO_METRIC: Record<string, { category: string; metric: string; isPercentage: boolean }> = {
  sales_volume_growth: { category: "REVENUE_DRIVERS", metric: "Revenue Growth", isPercentage: true },
  cogs_growth_rate: { category: "COST_MARGINS", metric: "COGS Growth Rate", isPercentage: true },
  opex_growth: { category: "COST_MARGINS", metric: "OpEx Growth", isPercentage: true },
  capital_expenditure: { category: "WORKING_CAPITAL", metric: "Capital Expenditure", isPercentage: true },
  receivables_days: { category: "WORKING_CAPITAL", metric: "Accounts Receivable Days", isPercentage: false },
  inventory_days: { category: "WORKING_CAPITAL", metric: "Inventory Days", isPercentage: false },
  payables_days: { category: "WORKING_CAPITAL", metric: "Accounts Payable Days", isPercentage: false },
  tax_rate: { category: "COST_MARGINS", metric: "Effective Tax Rate", isPercentage: true },
};

const DCF_FIELD_TO_METRIC: Record<string, { category: string; metric: string; isPercentage: boolean }> = {
  risk_free_rate: { category: "WACC_COMPONENTS", metric: "Risk-Free Rate", isPercentage: true },
  equity_risk_premium: { category: "WACC_COMPONENTS", metric: "Market Risk Premium", isPercentage: true },
  beta: { category: "WACC_COMPONENTS", metric: "Beta", isPercentage: false },
  cost_of_debt: { category: "WACC_COMPONENTS", metric: "Pre-Tax Cost of Debt", isPercentage: true },
  wacc: { category: "WACC_COMPONENTS", metric: "WACC", isPercentage: true },
  terminal_growth_rate: { category: "TERMINAL_VALUE", metric: "Terminal Growth Rate", isPercentage: true },
  terminal_ebitda_multiple: { category: "TERMINAL_VALUE", metric: "Terminal EBITDA Multiple", isPercentage: false },
  useful_life_existing: { category: "MODEL_PARAMETERS", metric: "Useful Life Existing Assets", isPercentage: false },
};

/**
 * Extract the data_source string from a backend category assumption.
 */
const getDataSource = (
  categories: Record<string, any>,
  categoryKey: string,
  metricName: string,
): string | null => {
  const category = categories[categoryKey];
  if (!category?.assumptions) return null;
  const assumption = category.assumptions.find((a: any) => a.metric === metricName);
  return assumption?.data_source || null;
};

/** Color coding for source badges based on source type */
const getSourceBadgeStyle = (source: string | null): { bg: string; color: string; icon: string } => {
  if (!source) return { bg: "var(--canvas-bg)", color: "var(--text-secondary)", icon: "ℹ️" };
  if (source.startsWith("Market data")) return { bg: "var(--accent-primary-subtle)", color: "var(--accent-primary)", icon: "📈" };
  if (source.startsWith("Peer")) return { bg: "var(--color-bearish-bg)", color: "var(--color-bearish)", icon: "👥" };
  if (source.startsWith("Calculated")) return { bg: "var(--color-neutral-bg)", color: "var(--color-neutral)", icon: "🧮" };
  if (source.startsWith("Historical")) return { bg: "var(--color-bullish-bg)", color: "var(--color-bullish)", icon: "📊" };
  if (source.startsWith("Industry default")) return { bg: "rgba(124, 58, 237, 0.08)", color: "var(--color-manual)", icon: "🏭" };
  if (source.startsWith("AI")) return { bg: "var(--accent-primary-subtle)", color: "var(--accent-primary)", icon: "🤖" };
  return { bg: "var(--canvas-bg)", color: "var(--text-secondary)", icon: "ℹ️" };
};

/**
 * Mini sparkline chart showing historical trend data for a forecast driver.
 */
const SparklineChart: React.FC<{ categories: any; field: string; height?: number }> = ({ categories, field, height = 64 }) => {
  const mapping = FIELD_TO_METRIC[field];
  if (!mapping) return null;
  const category = categories[mapping.category];
  if (!category?.assumptions) return null;
  const assumption = category.assumptions.find((a: any) => a.metric === mapping.metric);
  const trendline = assumption?.historical_trendline;
  if (!trendline?.trend_points || trendline.trend_points.length < 2) return null;
  const data = trendline.trend_points.map((p: any) => ({
    year: String(p.year).slice(-2),
    value: mapping.isPercentage ? p.value * 100 : p.value,
  }));
  const avg = mapping.isPercentage ? (trendline.average ?? 0) * 100 : (trendline.average ?? 0);
  const median = mapping.isPercentage ? (trendline.median ?? 0) * 100 : (trendline.median ?? 0);
  const cagr = mapping.isPercentage ? (trendline.cagr ?? 0) * 100 : (trendline.cagr ?? 0);
  const fmt = (v: number) => v.toFixed(mapping.isPercentage ? 1 : 1);
  const unit = mapping.isPercentage ? "%" : "";
  return (
    <div style={{ borderLeft: "2px solid var(--accent-primary)", paddingLeft: 8 }}>
      <div style={{ fontSize: 10, color: "var(--text-secondary)", marginBottom: 4, lineHeight: 1.4 }}>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <span>CAGR <strong style={{ color: "var(--accent-primary)" }}>{fmt(cagr)}{unit}</strong></span>
          <span>Mean <strong style={{ color: "var(--color-bullish)" }}>{fmt(avg)}{unit}</strong></span>
          <span>Med <strong style={{ color: "var(--color-neutral)" }}>{fmt(median)}{unit}</strong></span>
        </div>
      </div>
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: 4 }}>
          <XAxis dataKey="year" tick={{ fontSize: 9, fill: "#999" }} axisLine={false} tickLine={false} />
          <Tooltip
            formatter={(value: number) => [`${value.toFixed(2)}${unit}`, mapping.metric]}
            contentStyle={{ fontSize: 11, padding: "4px 8px" }}
          />
          <Line type="monotone" dataKey="value" stroke="#667eea" strokeWidth={2} dot={{ r: 3, fill: "#667eea" }} activeDot={{ r: 4 }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

/**
 * DCF-specific right-panel display.
 * WACC fields → peer comparable stats (mean/median/max from peer_wacc_data)
 * Terminal fields → historical trend chart
 */
const DcfRightPanel: React.FC<{ categories: any; field: string; peerWaccData?: any[]; height?: number }> = ({ categories, field, peerWaccData, height = 64 }) => {
  const mapping = DCF_FIELD_TO_METRIC[field];
  if (!mapping) return null;
  const isWaccField = mapping.category === "WACC_COMPONENTS";

  // ── WACC fields: show peer comparable stats ──
  if (isWaccField && peerWaccData && peerWaccData.length > 0) {
    // Map DCF field to peer data key
    const peerKeyMap: Record<string, string | null> = {
      beta: "levered_beta",
      cost_of_debt: "tax_rate", // cost of debt not per-peer, show tax rate as proxy
      risk_free_rate: null, // market rate, no peer comparison
      equity_risk_premium: null, // market consensus
      wacc: null, // calculated
    };
    const peerKey = peerKeyMap[field];
    if (!peerKey) {
      // For fields without peer data, show the single fetched value
      const val = categories[mapping.category]?.assumptions?.find((a: any) => a.metric === mapping.metric);
      const fv = val?.final_value ?? val?.user_value;
      if (fv == null) return null;
      const displayVal = mapping.isPercentage ? fv * 100 : fv;
      return (
        <div style={{ borderLeft: "2px solid var(--color-manual)", paddingLeft: 8 }}>
          <div style={{ fontSize: 10, color: "var(--text-secondary)", lineHeight: 1.4 }}>
            <span>Fetched: <strong style={{ color: "var(--color-manual)" }}>{displayVal.toFixed(mapping.isPercentage ? 2 : 2)}{mapping.isPercentage ? "%" : ""}</strong></span>
          </div>
        </div>
      );
    }
    const values = peerWaccData.map((p: any) => p[peerKey]).filter((v: any) => v != null && v > 0);
    if (values.length === 0) return null;
    const sorted = [...values].sort((a, b) => a - b);
    const mean = values.reduce((s, v) => s + v, 0) / values.length;
    const median = sorted.length % 2 === 0 ? (sorted[sorted.length / 2 - 1] + sorted[sorted.length / 2]) / 2 : sorted[Math.floor(sorted.length / 2)];
    const max = sorted[sorted.length - 1];
    const fmt = (v: number) => (mapping.isPercentage ? v * 100 : v).toFixed(2);
    const unit = mapping.isPercentage ? "%" : "";
    return (
      <div style={{ borderLeft: "2px solid var(--color-manual)", paddingLeft: 8 }}>
        <div style={{ fontSize: 10, color: "var(--text-secondary)", lineHeight: 1.4 }}>
          <div style={{ marginBottom: 2, fontWeight: 600, color: "var(--color-manual)" }}>Peer Comps ({values.length})</div>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <span>Mean <strong style={{ color: "var(--color-bullish)" }}>{fmt(mean)}{unit}</strong></span>
            <span>Med <strong style={{ color: "var(--color-neutral)" }}>{fmt(median)}{unit}</strong></span>
            <span>Max <strong style={{ color: "var(--color-bearish)" }}>{fmt(max)}{unit}</strong></span>
          </div>
        </div>
      </div>
    );
  }

  // ── Terminal / other fields: show historical trend chart ──
  const category = categories[mapping.category];
  if (!category?.assumptions) return null;
  const assumption = category.assumptions.find((a: any) => a.metric === mapping.metric);
  const trendline = assumption?.historical_trendline;
  if (!trendline?.trend_points || trendline.trend_points.length < 2) return null;
  const data = trendline.trend_points.map((p: any) => ({
    year: String(p.year).slice(-2),
    value: mapping.isPercentage ? p.value * 100 : p.value,
  }));
  const avg = mapping.isPercentage ? (trendline.average ?? 0) * 100 : (trendline.average ?? 0);
  const median = mapping.isPercentage ? (trendline.median ?? 0) * 100 : (trendline.median ?? 0);
  const cagr = mapping.isPercentage ? (trendline.cagr ?? 0) * 100 : (trendline.cagr ?? 0);
  const fmt = (v: number) => v.toFixed(1);
  const unit = mapping.isPercentage ? "%" : "";
  return (
    <div style={{ borderLeft: "2px solid var(--color-neutral)", paddingLeft: 8 }}>
      <div style={{ fontSize: 10, color: "var(--text-secondary)", marginBottom: 4, lineHeight: 1.4 }}>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <span>CAGR <strong style={{ color: "var(--color-neutral)" }}>{fmt(cagr)}{unit}</strong></span>
          <span>Mean <strong style={{ color: "var(--color-bullish)" }}>{fmt(avg)}{unit}</strong></span>
          <span>Med <strong style={{ color: "var(--accent-primary)" }}>{fmt(median)}{unit}</strong></span>
        </div>
      </div>
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: 4 }}>
          <XAxis dataKey="year" tick={{ fontSize: 9, fill: "#999" }} axisLine={false} tickLine={false} />
          <Tooltip
            formatter={(value: number) => [`${value.toFixed(2)}${unit}`, mapping.metric]}
            contentStyle={{ fontSize: 11, padding: "4px 8px" }}
          />
          <Line type="monotone" dataKey="value" stroke="#ff9800" strokeWidth={2} dot={{ r: 3, fill: "#ff9800" }} activeDot={{ r: 4 }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

interface ForecastDriversStepProps {
  [key: string]: any;
}

/**
 * ForecastDriversStep Component
 * Step 8: Assumption & AI Suggestion Studio
 * 
 * Features:
 * - Edit all forecast driver assumptions (Revenue Growth, Volume vs Price, Inflation, etc.)
 * - Edit DCF model inputs (Risk-Free Rate, Beta, WACC, Terminal Growth, etc.)
 * - Generate AI suggestions for each category
 * - Support for multiple scenarios (Best Case, Base Case, Worst Case)
 * - Real-time validation and feedback
 */
const ForecastDriversStep: React.FC<ForecastDriversStepProps> = ({
  sessionId,
  forecastDrivers: initialForecastDrivers,
  dcfInputs: initialDcfInputs,
  step6Data,
  step7Data,
  onManualInput,
  onAutoSave,
  onConfirmDrivers,
  onBackToHistoricalData,
  onContinueToAssumptions,
  loading,
  market = 'international',
  selectedModel = 'DCF'
}) => {
  const { t } = useTranslation();
  // ─── Historical Financial Statements State ──────────────────────────────────
  const [historicalData, setHistoricalData] = useState<any>(null);
  const [historicalLoading, setHistoricalLoading] = useState(false);

  useEffect(() => {
    const fetchHistoricals = async () => {
      if (!sessionId) return;
      // Prefer data from Step 8 response
      if (initialForecastDrivers?.complete_financial_statements) {
        setHistoricalData(initialForecastDrivers.complete_financial_statements);
        return;
      }
      // Fallback: fetch from API
      setHistoricalLoading(true);
      try {
        const result = await getCompleteFinancialStatements(sessionId, market, selectedModel);
        if (result?.status === 'success' && result?.data) {
          setHistoricalData(result.data);
        }
      } catch (err) {
        console.warn('Failed to load historical financial statements:', err);
      } finally {
        setHistoricalLoading(false);
      }
    };
    fetchHistoricals();
  }, [sessionId, market, selectedModel, initialForecastDrivers]);

  // Extract Step 8 categories from the backend response
  const step8Categories = initialForecastDrivers?.categories || {};
  
  // Helper: Get trendline average or latest value for a category+metric
  const getTrendValue = (categoryKey, metricName, fallback = null) => {
    const category = step8Categories[categoryKey];
    if (!category?.assumptions) return fallback;
    const assumption = category.assumptions.find(a => a.metric === metricName);
    if (!assumption?.historical_trendline) return fallback;
    const tl = assumption.historical_trendline;
    return tl.average || tl.latest_value || fallback;
  };

  // Helper: Get full trendline data for a category+metric
  const getTrendline = (categoryKey, metricName) => {
    const category = step8Categories[categoryKey];
    if (!category?.assumptions) return null;
    const assumption = category.assumptions.find(a => a.metric === metricName);
    return assumption?.historical_trendline || null;
  };

  // Initialize local state for forecast drivers from Step 8 categories
  // Uses 5-element arrays (one per forecast year) and correct metric names matching backend DCF_CATEGORIES
  const [localForecastDrivers, setLocalForecastDrivers] = useState(() => {
    const dv = initialForecastDrivers;
    if (dv?.categories) {
      const cats = dv.categories;
      // Backend metric names (from step8_manual_overrides.py DCF_CATEGORIES):
      // REVENUE_DRIVERS: "Revenue Growth"
      // COST_MARGINS: "COGS Growth Rate", "Inflation Rate", "OpEx Growth", "COGS % of Revenue", "Effective Tax Rate"
      // WORKING_CAPITAL: "Accounts Receivable Days", "Inventory Days", "Accounts Payable Days", "Capital Expenditure"
      const baseCase = {
        sales_volume_growth: getAssumptionFiveYearArray(cats, 'REVENUE_DRIVERS', 'Revenue Growth', 0.05),
        cogs_growth_rate: getAssumptionFiveYearArray(cats, 'COST_MARGINS', 'COGS Growth Rate', 0.03),
        opex_growth: getAssumptionFiveYearArray(cats, 'COST_MARGINS', 'OpEx Growth', 0.05),
        capital_expenditure: getAssumptionFiveYearArray(cats, 'WORKING_CAPITAL', 'Capital Expenditure', 0.05),
        receivables_days: getAssumptionFiveYearArray(cats, 'WORKING_CAPITAL', 'Accounts Receivable Days', 45),
        inventory_days: getAssumptionFiveYearArray(cats, 'WORKING_CAPITAL', 'Inventory Days', 25),
        payables_days: getAssumptionFiveYearArray(cats, 'WORKING_CAPITAL', 'Accounts Payable Days', 30),
        tax_rate: getAssumptionFiveYearArray(cats, 'COST_MARGINS', 'Effective Tax Rate', 0.21),
      };
      return {
        base_case: baseCase,
        best_case: { ...baseCase },
        worst_case: { ...baseCase },
      };
    }
    // Fallback: 5-element arrays with defaults
    const baseCase = dv?.base_case ? {
      sales_volume_growth: toSixYearArray(dv.base_case.sales_volume_growth, 0.05),
      cogs_growth_rate: toSixYearArray(dv.base_case.cogs_growth_rate, 0.03),
      opex_growth: toSixYearArray(dv.base_case.opex_growth, 0.05),
      capital_expenditure: toSixYearArray(dv.base_case.capital_expenditure, 0.05),
      receivables_days: toSixYearArray(dv.base_case.receivables_days, 45),
      inventory_days: toSixYearArray(dv.base_case.inventory_days, 25),
      payables_days: toSixYearArray(dv.base_case.payables_days, 30),
      tax_rate: toSixYearArray(dv.base_case.tax_rate, 0.21),
    } : {
      sales_volume_growth: Array(5).fill(0.05),
      cogs_growth_rate: Array(5).fill(0.03),
      opex_growth: Array(5).fill(0.05),
      capital_expenditure: Array(5).fill(0.05),
      receivables_days: Array(5).fill(45),
      inventory_days: Array(5).fill(25),
      payables_days: Array(5).fill(30),
      tax_rate: Array(5).fill(0.21),
    };
    return {
      base_case: baseCase,
      best_case: { ...baseCase },
      worst_case: { ...baseCase },
    };
  });

  // Initialize local state for DCF inputs from Step 8 WACC categories
  // Uses getAssumptionValue which reads final_value/user_value (pre-populated by backend from market data + peers)
  // Falls back to market-specific defaults
  const [localDcfInputs, setLocalDcfInputs] = useState(() => {
    const marketDefaults = market === 'vietnam'
      ? { risk_free_rate: 0.065, equity_risk_premium: 0.075, beta: 1.0, cost_of_debt: 0.08, wacc: 0.11, terminal_growth_rate: 0.05, terminal_ebitda_multiple: 10.0 }
      : { risk_free_rate: 0.045, equity_risk_premium: 0.06, beta: 1.0, cost_of_debt: 0.05, wacc: 0.085, terminal_growth_rate: 0.02, terminal_ebitda_multiple: 10.0 };

    if (initialForecastDrivers?.categories) {
      const cats = initialForecastDrivers.categories;
      return {
        risk_free_rate: getAssumptionValue(cats, 'WACC_COMPONENTS', 'Risk-Free Rate') ?? marketDefaults.risk_free_rate,
        equity_risk_premium: getAssumptionValue(cats, 'WACC_COMPONENTS', 'Market Risk Premium') ?? marketDefaults.equity_risk_premium,
        beta: getAssumptionValue(cats, 'WACC_COMPONENTS', 'Beta') ?? marketDefaults.beta,
        cost_of_debt: getAssumptionValue(cats, 'WACC_COMPONENTS', 'Pre-Tax Cost of Debt') ?? marketDefaults.cost_of_debt,
        wacc: getAssumptionValue(cats, 'WACC_COMPONENTS', 'WACC') ?? marketDefaults.wacc,
        terminal_growth_rate: getAssumptionValue(cats, 'TERMINAL_VALUE', 'Terminal Growth Rate') ?? marketDefaults.terminal_growth_rate,
        terminal_ebitda_multiple: getAssumptionValue(cats, 'TERMINAL_VALUE', 'Terminal EBITDA Multiple') ?? marketDefaults.terminal_ebitda_multiple,
        useful_life_existing: 10,
        useful_life_new: 10
      };
    }
    return initialDcfInputs || { ...marketDefaults, useful_life_existing: 10, useful_life_new: 10 };
  });

  const [activeScenario, setActiveScenario] = useState('base_case');
  const [editMode, setEditMode] = useState({
    forecastDrivers: false,
    dcfInputs: false
  });

  // Sync initial DCF inputs to the store so validation can read them
  useEffect(() => {
    if (localDcfInputs && onManualInput) {
      Object.entries(localDcfInputs).forEach(([field, value]) => {
        onManualInput(`dcf_${field}`, value);
      });
    }
  }, []); // Only on mount
  const [aiLoading, setAiLoading] = useState<any>({});
  const [aiSuggestions, setAiSuggestions] = useState<any>({});
  const [scenarioLoading, setScenarioLoading] = useState(false);
  const [scenariosGenerated, setScenariosGenerated] = useState(false);
  const [validationErrors, setValidationErrors] = useState<{field: string; message: string; section: 'forecast' | 'dcf'}[]>([]);

  // ─── Input Validation ─────────────────────────────────────────────────────
  const validateInputs = (): {field: string; message: string; section: 'forecast' | 'dcf'}[] => {
    const errors: {field: string; message: string; section: 'forecast' | 'dcf'}[] = [];

    // Validate Forecast Drivers Year 1 values
    const base = localForecastDrivers.base_case;
    if (base) {
      const forecastChecks: {field: string; label: string; min: number; max: number; isPct: boolean}[] = [
        { field: 'sales_volume_growth', label: 'Revenue Growth', min: -0.5, max: 1.0, isPct: true },
        { field: 'cogs_growth_rate', label: 'COGS Growth Rate', min: -0.1, max: 0.5, isPct: true },
        { field: 'opex_growth', label: 'OpEx Growth', min: -0.5, max: 1.0, isPct: true },
        { field: 'capital_expenditure', label: 'Capital Expenditure', min: 0, max: 1.0, isPct: true },
        { field: 'receivables_days', label: 'Receivable Days', min: 0, max: 365, isPct: false },
        { field: 'inventory_days', label: 'Inventory Days', min: 0, max: 365, isPct: false },
        { field: 'payables_days', label: 'Payable Days', min: 0, max: 365, isPct: false },
        { field: 'tax_rate', label: 'Tax Rate', min: 0, max: 0.6, isPct: true },
      ];
      for (const check of forecastChecks) {
        const values = base[check.field];
        const y1 = Array.isArray(values) ? values[0] : values;
        if (y1 == null || isNaN(y1)) {
          errors.push({ field: check.field, message: `${check.label} Year 1 is required`, section: 'forecast' });
        } else if (y1 < check.min || y1 > check.max) {
          const minDisp = check.isPct ? `${(check.min * 100).toFixed(0)}%` : check.min.toString();
          const maxDisp = check.isPct ? `${(check.max * 100).toFixed(0)}%` : check.max.toString();
          errors.push({ field: check.field, message: `${check.label} must be between ${minDisp} and ${maxDisp}`, section: 'forecast' });
        }
      }
    }

    // Validate DCF Model Inputs
    const dcfChecks: {field: string; label: string; min: number; max: number; isPct: boolean}[] = [
      { field: 'risk_free_rate', label: 'Risk-Free Rate', min: 0.001, max: 0.20, isPct: true },
      { field: 'equity_risk_premium', label: 'Equity Risk Premium', min: 0.001, max: 0.15, isPct: true },
      { field: 'beta', label: 'Beta', min: 0.01, max: 5.0, isPct: false },
      { field: 'cost_of_debt', label: 'Cost of Debt', min: 0.001, max: 0.30, isPct: true },
      { field: 'wacc', label: 'WACC', min: 0.001, max: 0.25, isPct: true },
      { field: 'terminal_growth_rate', label: 'Terminal Growth Rate', min: 0, max: 0.10, isPct: true },
      { field: 'terminal_ebitda_multiple', label: 'Terminal EBITDA Multiple', min: 0.1, max: 50, isPct: false },
    ];
    for (const check of dcfChecks) {
      const rawVal = localDcfInputs[check.field];
      const val = typeof rawVal === 'object' && rawVal !== null ? rawVal.value : rawVal;
      if (val == null || isNaN(val)) {
        errors.push({ field: check.field, message: `${check.label} is required`, section: 'dcf' });
      } else if (val < check.min || val > check.max) {
        const minDisp = check.isPct ? `${(check.min * 100).toFixed(1)}%` : check.min.toString();
        const maxDisp = check.isPct ? `${(check.max * 100).toFixed(1)}%` : check.max.toString();
        errors.push({ field: check.field, message: `${check.label} must be between ${minDisp} and ${maxDisp}`, section: 'dcf' });
      }
    }

    return errors;
  };

  // Generate Best/Worst scenarios from Base Case using historical volatility
  const handleGenerateScenarios = async () => {
    if (!sessionId) return;

    // Validate all required inputs before generating scenarios
    const errors = validateInputs();
    setValidationErrors(errors);
    if (errors.length > 0) {
      // Scroll to the first error section
      const firstForecastError = errors.find(e => e.section === 'forecast');
      const firstDcfError = errors.find(e => e.section === 'dcf');
      if (firstForecastError) {
        const el = document.querySelector(`[data-field="${firstForecastError.field}"]`);
        if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      } else if (firstDcfError) {
        const el = document.querySelector(`[data-field="${firstDcfError.field}"]`);
        if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
      return;
    }

    setScenarioLoading(true);
    try {
      // Collect full 5-year base case arrays for year-by-year scenario generation
      const baseCase: Record<string, any> = {};
      const base = localForecastDrivers.base_case;
      if (base) {
        for (const [field, values] of Object.entries(base)) {
          if (Array.isArray(values) && values.length > 0) {
            baseCase[field] = values; // Send full 5-year array
          }
        }
      }
      const result = await generateScenarios(sessionId, selectedModel, market, baseCase);
      if (result.success && result.data) {
        const { best_case, worst_case } = result.data;
        // Backend returns either a single number or a 5-year array per metric
        // Normalize to 6-element array (Year 1-5 + Term)
        const normalizeToSixArray = (val: any): number[] => {
          if (Array.isArray(val)) {
            // Pad to 6 elements if needed, last element = Term (repeat last value)
            const arr = val.map(Number);
            while (arr.length < 6) arr.push(arr[arr.length - 1] ?? 0);
            return arr.slice(0, 6);
          }
          if (typeof val === 'number') return Array(6).fill(val);
          if (typeof val === 'object' && val?.value != null) return Array(6).fill(Number(val.value));
          return Array(6).fill(0);
        };
        const bestCaseArrays: Record<string, number[]> = {};
        const worstCaseArrays: Record<string, number[]> = {};
        for (const [key, val] of Object.entries(best_case || {})) {
          bestCaseArrays[key] = normalizeToSixArray(val);
        }
        for (const [key, val] of Object.entries(worst_case || {})) {
          worstCaseArrays[key] = normalizeToSixArray(val);
        }
        setLocalForecastDrivers((prev: any) => ({
          ...prev,
          best_case: { ...prev.best_case, ...bestCaseArrays },
          worst_case: { ...prev.worst_case, ...worstCaseArrays },
        }));
        setScenariosGenerated(true);
      }
    } catch (err) {
      console.error('Failed to generate scenarios:', err);
    } finally {
      setScenarioLoading(false);
    }
  };

  // Generate AI suggestion for a specific category
  const handleGenerateAISuggestion = async (category) => {
    if (!sessionId) {
      alert('Session ID not available. Please go back and restart the valuation.');
      return;
    }

    setAiLoading(prev => ({ ...prev, [category]: true }));
    try {
      const response = await generateAISuggestion(sessionId, category, selectedModel, market);
      if (response.status === 'success' && response.suggestion) {
        setAiSuggestions(prev => ({ ...prev, [category]: response.suggestion }));
        
        // Auto-apply the suggestion to the current state
        const suggestion = response.suggestion;
        if (category === 'REVENUE_DRIVERS') {
          // Apply volume growth and price increase to forecast drivers
          if (suggestion.volume_growth !== undefined) {
            setLocalForecastDrivers(prev => ({
              ...prev,
              [activeScenario]: {
                ...prev[activeScenario],
                sales_volume_growth: prev[activeScenario].sales_volume_growth.map(() => suggestion.volume_growth)
              }
            }));
          }
          if (suggestion.price_increase !== undefined) {
            // Price increase affects COGS growth rate
            setLocalForecastDrivers(prev => ({
              ...prev,
              [activeScenario]: {
                ...prev[activeScenario],
                cogs_growth_rate: (prev[activeScenario].cogs_growth_rate || Array(5).fill(0.03)).map(() => suggestion.price_increase)
              }
            }));
          }
        } else if (category === 'COST_MARGINS') {
          if (suggestion.cogs_percent !== undefined) {
            // COGS % affects gross margin
          }
          if (suggestion.sgna_percent !== undefined) {
            // SG&A % affects opex
            setLocalForecastDrivers(prev => ({
              ...prev,
              [activeScenario]: {
                ...prev[activeScenario],
                opex_growth: prev[activeScenario].opex_growth.map(() => suggestion.sgna_percent)
              }
            }));
          }
          if (suggestion.tax_rate !== undefined) {
            setLocalForecastDrivers(prev => ({
              ...prev,
              [activeScenario]: {
                ...prev[activeScenario],
                tax_rate: prev[activeScenario].tax_rate.map(() => suggestion.tax_rate)
              }
            }));
          }
        } else if (category === 'WORKING_CAPITAL') {
          if (suggestion.receivables_days !== undefined) {
            setLocalForecastDrivers(prev => ({
              ...prev,
              [activeScenario]: {
                ...prev[activeScenario],
                receivables_days: prev[activeScenario].receivables_days.map(() => suggestion.receivables_days)
              }
            }));
          }
          if (suggestion.inventory_days !== undefined) {
            setLocalForecastDrivers(prev => ({
              ...prev,
              [activeScenario]: {
                ...prev[activeScenario],
                inventory_days: prev[activeScenario].inventory_days.map(() => suggestion.inventory_days)
              }
            }));
          }
          if (suggestion.payables_days !== undefined) {
            setLocalForecastDrivers(prev => ({
              ...prev,
              [activeScenario]: {
                ...prev[activeScenario],
                payables_days: prev[activeScenario].payables_days.map(() => suggestion.payables_days)
              }
            }));
          }
        } else if (category === 'WACC_COMPONENTS') {
          if (suggestion.risk_free_rate !== undefined) {
            setLocalDcfInputs(prev => ({ ...prev, risk_free_rate: suggestion.risk_free_rate }));
          }
          if (suggestion.market_risk_premium !== undefined) {
            setLocalDcfInputs(prev => ({ ...prev, equity_risk_premium: suggestion.market_risk_premium }));
          }
          if (suggestion.country_risk_premium !== undefined) {
            // CRP would need to be added to DCF inputs
          }
          if (suggestion.cost_of_debt !== undefined) {
            setLocalDcfInputs(prev => ({ ...prev, cost_of_debt: suggestion.cost_of_debt }));
          }
          if (suggestion.de_equity_ratio !== undefined) {
            // D/E ratio affects WACC calculation
          }
        } else if (category === 'TERMINAL_VALUE') {
          if (suggestion.terminal_growth_rate !== undefined) {
            setLocalDcfInputs(prev => ({ ...prev, terminal_growth_rate: suggestion.terminal_growth_rate }));
          }
          if (suggestion.terminal_ebitda_multiple !== undefined) {
            setLocalDcfInputs(prev => ({ ...prev, terminal_ebitda_multiple: suggestion.terminal_ebitda_multiple }));
          }
        }
      }
    } catch (error) {
      // Error handled silently
      alert(`Failed to generate AI suggestion: ${error.message}`);
    } finally {
      setAiLoading(prev => ({ ...prev, [category]: false }));
    }
  };

  // Handle forecast driver input change with auto-save
  const handleForecastDriverChange = (scenario, field, yearIndex, value) => {
    // FIX Issue #11: Explicit NaN checking instead of silent || 0
    const parsedValue = parseFloat(value);
    let numValue = isNaN(parsedValue) ? 0 : parsedValue;
    
    // Range validation for forecast drivers (-100% to 1000% for percentages)
    if (isPercentageField(field)) {
      if (numValue < -1.0 || numValue > 10.0) {
        console.warn(`[Validation] ${field} value ${numValue} out of range [-1.0, 10.0], clamping to bounds`);
        numValue = Math.max(-1.0, Math.min(10.0, numValue));
      }
    }
    
    setLocalForecastDrivers(prev => ({
      ...prev,
      [scenario]: {
        ...prev[scenario],
        [field]: prev[scenario][field].map((v, idx) => idx === yearIndex ? numValue : v)
      }
    }));

    // Notify parent component for confirmed values (immediate)
    if (onManualInput) {
      onManualInput(`forecast_${scenario}_${field}_${yearIndex}`, numValue);
    }
    
    // Trigger debounced auto-save for persistence
    if (onAutoSave) {
      onAutoSave(`forecast_${scenario}_${field}_${yearIndex}`, numValue);
    }
  };

  // Helper function to check if a field is percentage-based
  const isPercentageField = (field) => {
    const percentageFields = [
      'sales_volume_growth', 'cogs_growth_rate', 'opex_growth',
      'tax_rate', 'capital_expenditure'
    ];
    return percentageFields.includes(field);
  };

  // Handle DCF input change with auto-save
  const handleDcfInputChange = (field, value) => {
    // FIX Issue #11: Explicit NaN checking instead of silent || 0
    const parsedValue = parseFloat(value);
    let numValue = isNaN(parsedValue) ? 0 : parsedValue;
    
    // Market-specific DCF input validation with reasonable ranges
    const dcfRanges = {
      risk_free_rate: { min: 0.01, max: 0.20 }, // 1% - 20%
      equity_risk_premium: { min: 0.03, max: 0.15 }, // 3% - 15%
      beta: { min: 0.1, max: 3.0 },
      cost_of_debt: { min: 0.01, max: 0.30 }, // 1% - 30%
      wacc: { min: 0.05, max: 0.25 }, // 5% - 25%
      terminal_growth_rate: { min: 0.0, max: 0.10 }, // 0% - 10%
      terminal_ebitda_multiple: { min: 1.0, max: 50.0 },
      useful_life_existing: { min: 1, max: 50 },
      useful_life_new: { min: 1, max: 50 }
    };
    
    if (dcfRanges[field]) {
      const { min, max } = dcfRanges[field];
      if (numValue < min || numValue > max) {
        console.warn(`[Validation] DCF ${field} value ${numValue} out of range [${min}, ${max}], clamping to bounds`);
        numValue = Math.max(min, Math.min(max, numValue));
      }
    }
    
    setLocalDcfInputs(prev => ({
      ...prev,
      [field]: numValue
    }));

    // Notify parent component for confirmed values (immediate)
    if (onManualInput) {
      onManualInput(`dcf_${field}`, numValue);
    }
    
    // Trigger debounced auto-save for persistence
    if (onAutoSave) {
      onAutoSave(`dcf_${field}`, numValue);
    }
  };

  // Generate array of years for forecast (5-10 years)
  const forecastYears = Array.from({ length: 6 }, (_, i) => i < 5 ? `Year ${i + 1}` : 'Term');

  // Render forecast driver input row with AI suggestions using DataFieldDisplay
  const renderForecastDriverRow = (scenario, field, label, step = 0.01, isPercentage = true) => {
    const values = localForecastDrivers[scenario]?.[field] || [];
    
    const hasError = validationErrors.some(e => e.field === field);
    const errorMsg = validationErrors.find(e => e.field === field)?.message;
    return (
      <div key={`${scenario}_${field}`} data-field={field} className="driver-row" style={{ marginBottom: '12px', padding: '8px 12px', background: hasError ? 'var(--color-bearish-bg)' : 'var(--canvas-bg)', borderRadius: '6px', display: 'flex', gap: '12px', alignItems: 'stretch', border: hasError ? '1px solid var(--color-bearish)' : '1px solid transparent' }}>
        {/* Left: compact inputs grid */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
            <label style={{ fontWeight: 'bold', color: hasError ? 'var(--color-bearish)' : 'var(--text-primary)', fontSize: '13px' }}>
           {label} {isPercentage && '(%)'}
           {hasError && <span style={{ color: 'var(--color-bearish)', marginLeft: '4px', fontSize: '11px' }}>⚠</span>}
         </label>
         {hasError && errorMsg && (
           <div style={{ fontSize: '11px', color: 'var(--color-bearish)', marginTop: '2px', marginBottom: '4px' }}>{errorMsg}</div>
         )}
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: '4px' }}>
            {forecastYears.map((year, idx) => {
              const rawVal = values[idx];
              const aiSuggestion = typeof rawVal === 'number' ? rawVal : (typeof rawVal === 'object' && rawVal?.value != null ? Number(rawVal.value) : undefined);
              const displayValue = aiSuggestion !== undefined && !isNaN(aiSuggestion) ? (isPercentage ? (aiSuggestion * 100).toFixed(2) : aiSuggestion.toFixed(2)) : '';
              
              // Create DataField object for DataFieldDisplay
              const dataFieldObj = {
                value: aiSuggestion !== undefined ? aiSuggestion : null,
                status: aiSuggestion !== undefined ? 'CALCULATED' : 'MISSING',
                source: 'historical_trendline',
                confidence: 0.9,
                periods: [{ period: year, value: aiSuggestion }]
              };
              
              return (
                <div key={idx}>
                  <label style={{ fontSize: '10px', color: 'var(--text-tertiary)', display: 'block', marginBottom: '2px' }}>{year}</label>
                  <input
                        type="number"
                        step={step}
                        defaultValue={displayValue}
                        key={`${field}-${idx}`}
                        onBlur={(e) => {
                          const raw = parseFloat(e.target.value);
                          if (!isNaN(raw)) {
                            handleForecastDriverChange(scenario, field, idx, isPercentage ? raw / 100 : raw);
                          }
                        }}
                        onKeyDown={(e) => { if (e.key === 'Enter') (e.target as HTMLInputElement).blur(); }}
                        disabled={!editMode.forecastDrivers}
                        style={{
                          width: '100%',
                          padding: '4px 6px',
                          border: hasError ? '1.5px solid var(--color-bearish)' : '1px solid var(--border-default)',
                          borderRadius: '4px',
                          fontSize: '12px',
                          fontVariantNumeric: 'tabular-nums',
                          color: 'var(--text-primary)',
                          background: hasError ? 'var(--color-bearish-bg)' : 'var(--canvas-surface)',
                        }}
                      />
                </div>
              );
            })}
          </div>
        </div>
        {/* Right: historical trend chart + stats */}
        <div style={{ width: '200px', flexShrink: 0, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
          <SparklineChart categories={step8Categories} field={field} />
        </div>
      </div>
    );
  };

  // Render DCF input field with source provenance badge
  const renderDcfInputField = (field, label, step = 0.001, isPercentage = true, min = 0, max = 1) => {
    const valueObj = localDcfInputs[field];
    const value = typeof valueObj === 'object' && valueObj !== null ? valueObj.value : valueObj;
    const displayValue = value != null ? (isPercentage ? (value * 100).toFixed(2) : value.toFixed(2)) : '';
    
    // Look up data_source from backend categories
    const mapping = DCF_FIELD_TO_METRIC[field];
    const dataSource = mapping ? getDataSource(step8Categories, mapping.category, mapping.metric) : null;
    const badgeStyle = getSourceBadgeStyle(dataSource);
    
    const hasDcfError = validationErrors.some(e => e.field === field);
    const dcfErrorMsg = validationErrors.find(e => e.field === field)?.message;
    return (
      <div key={field} data-field={field} className="dcf-input-row" style={{ marginBottom: '10px', padding: '8px 12px', background: hasDcfError ? 'var(--color-bearish-bg)' : 'var(--canvas-bg)', borderRadius: '6px', display: 'flex', gap: '12px', alignItems: 'center', border: hasDcfError ? '1px solid var(--color-bearish)' : '1px solid transparent' }}>
        {/* Left: input + source badge */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <label style={{ display: 'block', fontWeight: 'bold', marginBottom: '2px', color: 'var(--text-primary)', fontSize: '13px' }}>
            {label} {isPercentage && '(%)'}
          </label>
          <input
            type="number"
            step={step}
            min={min}
            max={max}
            defaultValue={displayValue}
            key={field}
            onBlur={(e) => {
              const raw = parseFloat(e.target.value);
              if (!isNaN(raw)) {
                handleDcfInputChange(field, isPercentage ? raw / 100 : raw);
              }
            }}
            onKeyDown={(e) => { if (e.key === 'Enter') (e.target as HTMLInputElement).blur(); }}
            disabled={!editMode.dcfInputs}
            style={{
              width: '100%',
              padding: '4px 8px',
              border: hasDcfError ? '1.5px solid var(--color-bearish)' : '1px solid var(--border-default)',
              borderRadius: '4px',
              fontSize: '13px',
              fontVariantNumeric: 'tabular-nums',
              color: 'var(--text-primary)',
              background: hasDcfError ? 'var(--color-bearish-bg)' : 'var(--canvas-surface)',
            }}
          />
          {/* Source provenance badge */}
          {dataSource && (
            <div style={{
              marginTop: '4px',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              padding: '2px 8px',
              borderRadius: '10px',
              fontSize: '10px',
              fontWeight: 500,
              lineHeight: '16px',
              background: badgeStyle.bg,
              color: badgeStyle.color,
              maxWidth: '100%',
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
            }}>
              <span style={{ flexShrink: 0 }}>{badgeStyle.icon}</span>
              <span title={dataSource} style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>{dataSource}</span>
            </div>
          )}
        </div>
        {/* Right: historical trend chart + stats */}
        <div style={{ width: '200px', flexShrink: 0 }}>
          <DcfRightPanel categories={step8Categories} field={field} peerWaccData={initialForecastDrivers?.peer_wacc_data} />
        </div>
      </div>
    );
  };

  return (
    <div className="step-container">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <div>
          <h2>{t('steps.step8')}</h2>
          <p style={{ color: 'var(--text-secondary)', marginTop: '8px' }}>{t('stepDescriptions.step8')}</p>
        </div>
        <button onClick={onBackToHistoricalData} className="btn-secondary">
          ← Back to Historical Data
        </button>
      </div>

      {/* Historical Financial Statements — always visible at the top */}
      <HistoricalStatements
        completeFinancialStatements={historicalData}
        market={market}
        loading={historicalLoading}
      />

      {/* Scenario Selector */}
      <div className="summary-box" style={{ marginBottom: '24px' }}>
        <h3>{t('buttons.select')} Scenario</h3>
        <div style={{ display: 'flex', gap: '12px', marginTop: '12px', alignItems: 'center' }}>
          {['best_case', 'base_case', 'worst_case'].map(scenario => (
            <button
              key={scenario}
              onClick={() => setActiveScenario(scenario)}
              style={{
                padding: '10px 20px',
                border: 'none',
                borderRadius: '6px',
                cursor: 'pointer',
                fontWeight: 'bold',
                background: activeScenario === scenario ? 'var(--accent-primary)' : '#e0e0e0',
                color: activeScenario === scenario ? 'white' : 'var(--text-primary)'
              }}
            >
              {scenario.replace('_', ' ').toUpperCase()}
            </button>
          ))}
          {/* Generate button moved to bottom action area (mandatory prerequisite) */}
        </div>
      </div>

      {/* Assumption Categories — auto-populated from historical statistics */}
      <div className="summary-box" style={{ marginBottom: '24px', background: 'linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <h3>📊 {t('sections.assumptions_inputs')}</h3>
          <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>Auto-calculated from historical trendlines, CAGR, mean and median</span>
        </div>
        
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px' }}>
          {/* Revenue Drivers — auto-calculated */}
          <div style={{ background: 'var(--canvas-surface)', padding: '16px', borderRadius: '8px', border: '1px solid #4caf50' }}>
            <h4 style={{ margin: '0 0 8px 0', color: 'var(--color-bullish)' }}>📈 Revenue Drivers</h4>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '12px' }}>Volume Growth & Price Increase — calculated from historical revenue trends</p>
            <div style={{ padding: '8px', background: 'var(--color-bullish-bg)', borderRadius: '4px', fontSize: '12px', color: 'var(--color-bullish)' }}>
              ✓ Auto-calculated from historical data (CAGR, YoY growth, mean)
            </div>
          </div>

          {/* Cost & Margins — auto-calculated */}
          <div style={{ background: 'var(--canvas-surface)', padding: '16px', borderRadius: '8px', border: '1px solid #4caf50' }}>
            <h4 style={{ margin: '0 0 8px 0', color: 'var(--color-bullish)' }}>💰 Cost & Margins</h4>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '12px' }}>COGS %, OpEx %, and Tax Rate — calculated from historical margins</p>
            <div style={{ padding: '8px', background: 'var(--color-bullish-bg)', borderRadius: '4px', fontSize: '12px', color: 'var(--color-bullish)' }}>
              ✓ Auto-calculated from historical data (median, average ratios)
            </div>
          </div>

          {/* Working Capital — auto-calculated */}
          <div style={{ background: 'var(--canvas-surface)', padding: '16px', borderRadius: '8px', border: '1px solid #4caf50' }}>
            <h4 style={{ margin: '0 0 8px 0', color: 'var(--color-bullish)' }}>🔄 Working Capital</h4>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '12px' }}>AR Days, Inventory Days, AP Days — calculated from historical efficiency</p>
            <div style={{ padding: '8px', background: 'var(--color-bullish-bg)', borderRadius: '4px', fontSize: '12px', color: 'var(--color-bullish)' }}>
              ✓ Auto-calculated from historical data (days-based metrics)
            </div>
          </div>

          {/* WACC Components — auto-calculated */}
          <div style={{ background: 'var(--canvas-surface)', padding: '16px', borderRadius: '8px', border: '1px solid #4caf50' }}>
            <h4 style={{ margin: '0 0 8px 0', color: 'var(--color-bullish)' }}>📊 WACC Components</h4>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '12px' }}>Risk-Free Rate, Beta, Cost of Debt — from market data & peer analysis</p>
            <div style={{ padding: '8px', background: 'var(--color-bullish-bg)', borderRadius: '4px', fontSize: '12px', color: 'var(--color-bullish)' }}>
              ✓ Auto-calculated from market data + peer benchmarks
            </div>
          </div>

          {/* Terminal Value — AI suggestion */}
          <div style={{ background: 'var(--canvas-surface)', padding: '16px', borderRadius: '8px', border: '1px solid #2196f3' }}>
            <h4 style={{ margin: '0 0 8px 0', color: 'var(--accent-primary)' }}>🎯 Terminal Value</h4>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '12px' }}>Terminal Growth Rate and EBITDA Multiple — AI-powered from news & analysis</p>
            <button
              onClick={() => handleGenerateAISuggestion('TERMINAL_VALUE')}
              disabled={aiLoading.TERMINAL_VALUE}
              style={{
                width: '100%',
                padding: '10px',
                background: aiLoading.TERMINAL_VALUE ? '#ccc' : 'var(--accent-primary)',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                cursor: aiLoading.TERMINAL_VALUE ? 'not-allowed' : 'pointer',
                fontWeight: 'bold'
              }}
            >
              {aiLoading.TERMINAL_VALUE ? '⏳ Generating...' : '✨ Generate AI Suggestion'}
            </button>
            {aiSuggestions.terminal_value && (
              <div style={{ marginTop: '12px', padding: '8px', background: 'var(--accent-primary-subtle)', borderRadius: '4px', fontSize: '12px' }}>
                <strong>✓ Applied:</strong>
                {aiSuggestions.terminal_value.terminal_growth_rate && (
                  <div>Terminal Growth: {(aiSuggestions.terminal_value.terminal_growth_rate * 100).toFixed(1)}%</div>
                )}
                {aiSuggestions.terminal_value.terminal_ebitda_multiple && (
                  <div>EBITDA Multiple: {aiSuggestions.terminal_value.terminal_ebitda_multiple.toFixed(1)}x</div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Forecast Drivers Section */}
      <div className="summary-box" style={{ marginBottom: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <h3>📊 {t('sections.forecast_drivers')}</h3>
          <button
            onClick={() => setEditMode(prev => ({ ...prev, forecastDrivers: !prev.forecastDrivers }))}
            className="btn-small"
            style={{
              background: editMode.forecastDrivers ? 'var(--color-bullish)' : 'var(--color-neutral)',
              color: 'white'
            }}
          >
            {editMode.forecastDrivers ? '✓ Editing' : '✏️ Edit'}
          </button>
        </div>
        
        {renderForecastDriverRow(activeScenario, 'sales_volume_growth', 'Volume Growth', 0.01, true)}
        {renderForecastDriverRow(activeScenario, 'cogs_growth_rate', 'COGS Growth Rate', 0.001, true)}
        {renderForecastDriverRow(activeScenario, 'opex_growth', 'OpEx Growth', 0.01, true)}
        {renderForecastDriverRow(activeScenario, 'capital_expenditure', 'CapEx (% of Revenue)', 0.01, true)}
        {renderForecastDriverRow(activeScenario, 'receivables_days', 'Receivables Days', 1, false)}
        {renderForecastDriverRow(activeScenario, 'inventory_days', 'Inventory Days', 1, false)}
        {renderForecastDriverRow(activeScenario, 'payables_days', 'Payables Days', 1, false)}
        {renderForecastDriverRow(activeScenario, 'tax_rate', 'Tax Rate', 0.01, true)}
      </div>

      {/* DCF Model Inputs Section */}
      <div className="summary-box" style={{ marginBottom: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <h3>💰 {t('sections.dcf_model_inputs')}</h3>
          <button
            onClick={() => setEditMode(prev => ({ ...prev, dcfInputs: !prev.dcfInputs }))}
            className="btn-small"
            style={{
              background: editMode.dcfInputs ? 'var(--color-bullish)' : 'var(--color-neutral)',
              color: 'white'
            }}
          >
            {editMode.dcfInputs ? '✓ Editing' : '✏️ Edit'}
          </button>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '0' }}>
          {renderDcfInputField('risk_free_rate', 'Risk-Free Rate', 0.001, true, 0, 0.2)}
          {renderDcfInputField('equity_risk_premium', 'Equity Risk Premium', 0.001, true, 0, 0.2)}
          {renderDcfInputField('beta', 'Beta', 0.01, false, 0, 3)}
          {renderDcfInputField('cost_of_debt', 'Cost of Debt', 0.001, true, 0, 0.2)}
          {renderDcfInputField('wacc', 'WACC', 0.001, true, 0, 0.2)}
          {renderDcfInputField('terminal_growth_rate', 'Terminal Growth Rate', 0.001, true, 0, 0.1)}
          {renderDcfInputField('terminal_ebitda_multiple', 'Terminal EBITDA Multiple', 0.1, false, 1, 50)}
          {renderDcfInputField('useful_life_existing', 'Useful Life (Existing Assets)', 1, false, 1, 50)}
        </div>
      </div>

      {/* Action Buttons — Generate Scenarios is a mandatory prerequisite */}
      <div style={{ marginTop: '24px' }}>
        {/* Step 1: Generate Scenarios — MUST be done first */}
        <div style={{
          padding: '20px',
          background: scenariosGenerated ? 'linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%)' : 'linear-gradient(135deg, #fff3e0 0%, var(--color-neutral-bg) 100%)',
          borderRadius: '8px',
          border: `2px solid ${scenariosGenerated ? 'var(--color-bullish)' : 'var(--color-neutral)'}`,
          marginBottom: '16px',
          textAlign: 'center',
        }}>
          <div style={{ fontSize: '14px', fontWeight: 600, marginBottom: '8px', color: scenariosGenerated ? '#2e7d32' : 'var(--color-neutral)' }}>
            {scenariosGenerated
              ? '✅ Best/Worst scenarios generated'
              : '⚠️ Step 1 of 2: Generate Best/Worst scenarios from your Base Case'}
          </div>
          <button
            onClick={handleGenerateScenarios}
            disabled={scenarioLoading || scenariosGenerated}
            style={{
              padding: '12px 32px',
              border: 'none',
              borderRadius: '8px',
              cursor: scenarioLoading || scenariosGenerated ? 'not-allowed' : 'pointer',
              fontWeight: 'bold',
              fontSize: '15px',
              background: scenariosGenerated ? 'var(--color-bullish)' : scenarioLoading ? '#ccc' : 'var(--color-neutral)',
              color: 'white',
              boxShadow: scenariosGenerated ? 'none' : '0 2px 8px rgba(255, 152, 0, 0.3)',
            }}
          >
            {scenarioLoading ? '⏳ Generating...' : scenariosGenerated ? '✅ Generated' : '🔄 Generate Best / Worst Scenarios'}
          </button>
          {/* Inline validation errors */}
          {validationErrors.length > 0 && (
            <div style={{ marginTop: '12px', padding: '12px 16px', background: 'var(--color-bearish-bg)', border: '1px solid var(--color-bearish)', borderRadius: '8px', textAlign: 'left', maxWidth: '600px', margin: '12px auto 0' }}>
              <div style={{ fontWeight: 600, color: 'var(--color-bearish)', fontSize: '13px', marginBottom: '6px' }}>
                ⚠️ Please fix {validationErrors.length} issue{validationErrors.length > 1 ? 's' : ''} before generating scenarios:
              </div>
              <ul style={{ margin: 0, paddingLeft: '18px', fontSize: '12px', color: '#991b1b' }}>
                {validationErrors.map((err, i) => (
                  <li key={i} style={{ marginBottom: '3px' }}>
                    <strong>{err.section === 'forecast' ? 'Forecast' : 'DCF'}</strong>: {err.message}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Step 2: Continue — only enabled after scenario generation */}
        <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
          <button
            onClick={onBackToHistoricalData}
            className="btn-secondary btn-large"
            disabled={loading}
          >
            ← Back to Historical Data
          </button>
          <button
            onClick={() => {
              if (onConfirmDrivers) {
                onConfirmDrivers();
              } else {
                onContinueToAssumptions();
              }
            }}
            className="btn-next-step"
            disabled={loading || !scenariosGenerated}
            title={!scenariosGenerated ? 'Generate Best/Worst scenarios first (required)' : ''}
          >
            {loading ? 'Processing...' : 'Continue to Confirm Assumptions →'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ForecastDriversStep;
