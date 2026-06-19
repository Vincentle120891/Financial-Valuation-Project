/**
 * valuationActions - Steps 10-11 handlers (Run Valuation, Reset)
 *
 * Plain async functions that import useValuationStore and call getState()/setState().
 */

import useValuationStore from '../useValuationStore';
import { runValuation } from '../../services/api';

// ─── Step 10: Run Valuation ─────────────────────────────────────────────────

export const handleRunValuation = async () => {
  const { sessionId, selectedModels, selectedScenario, market } =
    useValuationStore.getState();

  useValuationStore.setState({ loading: true, error: null });

  const method = selectedModels;
  if (!method) {
    useValuationStore.setState({
      error: 'No valuation method selected',
      loading: false,
    });
    return;
  }

  try {
    const data = await runValuation(sessionId, method, selectedScenario, market);
    console.log('Valuation response:', data);

    // Backend UnifiedStep10Response returns:
    //   valuation_summary, detailed_outputs, calculated_schedules,
    //   sensitivity_analysis, scenario_analysis, confidence_level, warnings
    // NOT data.result — map the correct fields to the store matrix.
    const { setResult } = useValuationStore.getState();

    // Store the full response in the matrix keyed by method
    if (method.toUpperCase() === 'DCF') {
      setResult('DCF', data);
    } else if (method.toUpperCase() === 'DUPONT') {
      setResult('DuPont', data);
    } else if (method.toUpperCase() === 'COMPS') {
      setResult('COMPS', data);
    }

    // Also store in legacy valuationResults matrix for backward compatibility
    useValuationStore.setState((state) => ({
      valuationResults: {
        ...state.valuationResults,
        [market]: {
          ...state.valuationResults[market],
          [method.toLowerCase()]: data,
        },
      },
    }));

    useValuationStore.setState({ loading: false });
    // No automatic step transition — caller controls navigation
    return;
  } catch (err) {
    console.error('Valuation error:', err);
    useValuationStore.setState({
      error: 'Failed to run valuation. Please ensure the backend server is running.',
    });
  } finally {
    useValuationStore.setState({ loading: false });
  }
};

// ─── Reset All ──────────────────────────────────────────────────────────────

function emptyMatrix() {
  return {
    international: { dcf: null, dupont: null, comps: null },
    vietnam: { dcf: null, dupont: null, comps: null },
  };
}

export const handleReset = () => {
  useValuationStore.setState({
    currentStep: 1,
    maxReachedStep: 1,
    searchQuery: '',
    searchResults: [],
    selectedCompany: null,
    suggestedPeers: [],
    selectedPeers: [],
    sessionId: null,
    selectedModels: '',
    selectedModel: '',
    requiredFields: [],
    confirmedValues: {},
    selectedScenario: 'base_case',
    error: null,
    aiError: null,
    market: 'international',
    marketValidation: {
      isValid: true,
      message: '',
      selectedMarket: 'international',
      isLocked: false,
    },
    valuationsData: emptyMatrix(),
    forecastDriversData: emptyMatrix(),
    dcfInputsData: emptyMatrix(),
    valuationResults: emptyMatrix(),
    peerData: null,
    calculatedMetrics: null,
    loading: false,
    validationErrors: [],
    manualPeerInput: '',
    manualPeerError: null,
    manualPeerLoading: false,
  });
};
