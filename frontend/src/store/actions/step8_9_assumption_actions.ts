/**
 * assumptionActions - Steps 8-9 handlers (Forecast Drivers, Assumptions, AI)
 *
 * Plain async functions that import useValuationStore and call getState()/setState().
 */

import useValuationStore from '../useValuationStore';
import { confirmAssumptions } from '../../services/api';
import { initializeAssumptions } from '../../services/step8_10_valuation_service';

// ─── Step 8: Continue to Forecast Drivers ───────────────────────────────────

export const handleContinueToForecastDrivers = async () => {
  const { sessionId, selectedModels, market, loading: currentLoading } =
    useValuationStore.getState();

  useValuationStore.setState({ loading: true });

  const method = selectedModels;
  if (!method) {
    useValuationStore.setState({
      error: 'No valuation method selected',
      loading: false,
    });
    return;
  }

  try {
    const result = await initializeAssumptions(sessionId, method, market);
    console.log('Step 8 initialization response:', result);

    if (result.success && result.data) {
      const step8Response = result.data;
      const { setValuationData, setForecastDrivers } = useValuationStore.getState();

      setValuationData(method, step8Response);
      setForecastDrivers(method, step8Response);

      useValuationStore.setState({ loading: false });
      // Step transition handled by button callback in ValuationFlow
      return;
    }
  } catch (err) {
    console.error('Failed to initialize Step 8:', err);
  } finally {
    if (useValuationStore.getState().loading) {
      useValuationStore.setState({ loading: false });
    }
    // Step transition handled by button callback in ValuationFlow
  }
};

// ─── Step 9: Continue to Assumptions ────────────────────────────────────────

export const handleContinueToAssumptions = () => {
  // Step transition handled by button callback in ValuationFlow
  // This function is kept for backward compatibility
};

// ─── Manual Input Handler (with forecast drivers / DCF persistence) ─────────

export const handleManualInput = (field: string, value: any) => {
  let parsedValue = value;

  if (typeof value === 'string' && value.includes(',')) {
    parsedValue = value.split(',').map((v) => parseFloat(v.trim()));
  } else {
    parsedValue = parseFloat(value) || value;
  }

  const { selectedModels } = useValuationStore.getState();
  const { getForecastDrivers, setForecastDrivers, getDcfInputs, setDcfInputs } =
    useValuationStore.getState();

  // Update confirmedValues
  useValuationStore.setState((state) => ({
    confirmedValues: {
      ...state.confirmedValues,
      [field]: { value: parsedValue, source: 'manual' },
    },
  }));

  // Also update forecastDrivers or dcfInputs for Step 8 persistence
  if (field.startsWith('forecast_')) {
    const parts = field.split('_');
    if (parts.length >= 4) {
      const scenario = parts[1];
      // Convert camelCase field name from Step 9 to snake_case for store keys
      // e.g., "revenueGrowth" → "revenue_growth", "cogsGrowthRate" → "cogs_growth_rate"
      const CAMEL_TO_SNAKE: Record<string, string> = {
        revenueGrowth: 'revenue_growth',
        salesVolumeGrowth: 'sales_volume_growth',
        cogsGrowthRate: 'cogs_growth_rate',
        opexGrowthRate: 'opex_growth_rate',
        inflationRate: 'inflation_rate',
        capitalExpenditure: 'capital_expenditure',
        receivablesDays: 'receivables_days',
        inventoryDays: 'inventory_days',
        payablesDays: 'payables_days',
      };
      const camelField = parts[2];
      const driverField = CAMEL_TO_SNAKE[camelField] || camelField;
      const yearIndex = parseInt(parts[3], 10);

      const currentDrivers = getForecastDrivers(selectedModels);
      if (currentDrivers && currentDrivers[scenario]) {
        const updatedScenario = {
          ...currentDrivers[scenario],
          [driverField]: currentDrivers[scenario][driverField].map(
            (v: any, idx: number) => (idx === yearIndex ? parsedValue : v)
          ),
        };
        setForecastDrivers(selectedModels, {
          ...currentDrivers,
          [scenario]: updatedScenario,
        });
      }
    }
  } else if (field.startsWith('dcf_')) {
    const dcfField = field.replace('dcf_', '');
    const currentInputs = getDcfInputs(selectedModels) || {};
    setDcfInputs(selectedModels, {
      ...currentInputs,
      [dcfField]: parsedValue,
    });
  }
};

// ─── Auto-Save Forecast Drivers (persists to backend session) ───────────────

let _autoSaveTimer: ReturnType<typeof setTimeout> | null = null;

const _persistConfirmedValues = (confirmedValues: any) => {
  const { sessionId, selectedModels, market } = useValuationStore.getState();
  if (!sessionId || !selectedModels) return;
  const API_BASE = (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000/api';
  fetch(`${API_BASE}/step-8-save-overrides`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: sessionId,
      confirmed_assumptions: confirmedValues,
      method: selectedModels.toUpperCase(),
      market: market.toLowerCase(),
    }),
  }).catch((err: any) => console.warn('[Auto-Save] Failed to persist:', err.message));
};

export const handleAutoSaveForecastDrivers = (field: string, value: any) => {
  const { confirmedValues } = useValuationStore.getState();
  if (_autoSaveTimer) clearTimeout(_autoSaveTimer);
  _autoSaveTimer = setTimeout(() => _persistConfirmedValues(confirmedValues), 500);
};

// ─── Auto-Save DCF Inputs (persists to backend session) ────────────────────

let _autoSaveDcfTimer: ReturnType<typeof setTimeout> | null = null;

export const handleAutoSaveDcfInputs = (field: string, value: any) => {
  const { confirmedValues } = useValuationStore.getState();
  if (_autoSaveDcfTimer) clearTimeout(_autoSaveDcfTimer);
  _autoSaveDcfTimer = setTimeout(() => _persistConfirmedValues(confirmedValues), 500);
};

// ─── Use AI Suggestion ──────────────────────────────────────────────────────

export const handleUseAI = (field: string, aiValue: any) => {
  useValuationStore.setState((state) => ({
    confirmedValues: {
      ...state.confirmedValues,
      [field]: { value: aiValue, source: 'ai', confidence: 0.8 },
    },
  }));
};

// ─── Step 10: Confirm Assumptions ───────────────────────────────────────────

export const handleConfirmAssumptions = async () => {
  const {
    sessionId,
    confirmedValues,
    selectedScenario,
    selectedModels,
    dcfInputsData,
    market,
  } = useValuationStore.getState();

  const method = selectedModels;
  if (!method) {
    useValuationStore.setState({ error: 'No valuation method selected' });
    return;
  }

  // Validate required DCF inputs before proceeding
  if (method === 'DCF') {
    const errors: string[] = [];
    const { getDcfInputs } = useValuationStore.getState();
    const dcfInputs = getDcfInputs(method);

    if (!dcfInputs?.wacc || dcfInputs.wacc <= 0) {
      errors.push('WACC must be greater than 0');
    }
    if (!dcfInputs?.terminal_growth_rate || dcfInputs.terminal_growth_rate < 0) {
      errors.push('Terminal growth rate must be non-negative');
    }
    if (!dcfInputs?.risk_free_rate || dcfInputs.risk_free_rate < 0) {
      errors.push('Risk-free rate must be non-negative');
    }

    if (errors.length > 0) {
      useValuationStore.setState({
        validationErrors: errors,
        error:
          'Please fix the following validation errors:\n• ' + errors.join('\n• '),
      });
      return;
    }
  }

  useValuationStore.setState({ validationErrors: [], error: null, loading: true });

  try {
    const data = await confirmAssumptions(
      sessionId,
      confirmedValues,
      selectedScenario,
      method,
      market
    );
    console.log('Confirm assumptions response:', data);

    if (data.status) {
      useValuationStore.setState({ loading: false });
      // Step transition handled by button callback in ValuationFlow
      return;
    }
  } catch (err: any) {
    console.error('Confirm assumptions error:', err);
    useValuationStore.setState({
      error:
        'Failed to confirm assumptions: ' + (err.message || 'Unknown error'),
    });
  } finally {
    useValuationStore.setState({ loading: false });
  }
};
