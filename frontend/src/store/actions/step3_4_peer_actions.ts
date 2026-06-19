/**
 * peerActions - Steps 3-5 handlers (Peers, Model Selection, Requirements)
 *
 * Plain async functions that import useValuationStore and call getState()/setState().
 */

import useValuationStore from '../useValuationStore';
import { suggestPeers, savePeers, selectModels } from '../../services/api';

// ─── Step 4: Handle Find Peers ──────────────────────────────────────────────

export const handleFindPeers = async (company: any) => {
  const { market, selectedModels, sessionId } = useValuationStore.getState();

  useValuationStore.setState({ loading: true, error: null });

  // Validate model selection first
  if (!selectedModels) {
    useValuationStore.setState({
      error: 'Please select a valuation model in Step 3 first before finding peers',
      loading: false,
    });
    return;
  }

  // Validate session exists
  if (!sessionId) {
    useValuationStore.setState({
      error: 'No session found. Please select a company first.',
      loading: false,
    });
    return;
  }

  // Validate market selection
  if (!['international', 'vietnam'].includes(market)) {
    useValuationStore.setState({
      marketValidation: {
        isValid: false,
        message: 'Invalid market selection. Please select either International or Vietnam market.',
        selectedMarket: market,
        isLocked: useValuationStore.getState().marketValidation.isLocked,
      },
      error: 'Invalid market selection',
      loading: false,
    });
    return;
  }

  try {
    const ticker = company.ticker || company.symbol;
    const data = await suggestPeers(ticker, market, 10, selectedModels, sessionId);
    console.log('Suggest peers response:', data);

    if (data.suggested_peers && data.suggested_peers.length > 0) {
      // Auto-select top 5 peers with highest scores
      const sortedPeers = [...data.suggested_peers].sort((a: any, b: any) => {
        const scoreA = a.match_score || a.score || 0;
        const scoreB = b.match_score || b.score || 0;
        return scoreB - scoreA;
      });
      const topPeers = sortedPeers.slice(0, Math.min(5, sortedPeers.length));

      useValuationStore.setState({
        suggestedPeers: data.suggested_peers,
        selectedPeers: topPeers.map((p: any) => p.ticker || p.symbol),
      });

      console.log(
        `Auto-selected ${topPeers.length} peers with highest scores:`,
        topPeers.map((p: any) => p.symbol || p.ticker)
      );
    } else {
      useValuationStore.setState({
        error: 'No peers found for this company. Please try searching for a different company.',
      });
    }
  } catch (err) {
    console.error('Suggest peers error:', err);
    useValuationStore.setState({
      error: 'Failed to find peers. Please ensure the backend server is running.',
    });
  } finally {
    useValuationStore.setState({ loading: false });
  }
};

// ─── Step 5: Toggle Peer Selection ──────────────────────────────────────────

export const handleTogglePeer = (ticker: string) => {
  useValuationStore.setState((state) => ({
    selectedPeers: state.selectedPeers.includes(ticker)
      ? state.selectedPeers.filter((p) => p !== ticker)
      : [...state.selectedPeers, ticker],
  }));
};

// ─── Step 5: Continue to Requirements Review ────────────────────────────────

export const handleContinueToRequirementsReview = async () => {
  const { sessionId, selectedPeers, suggestedPeers } = useValuationStore.getState();

  if (!sessionId || selectedPeers.length === 0) {
    useValuationStore.setState({ error: 'No session or peers selected' });
    return;
  }

  useValuationStore.setState({ loading: true });

  try {
    const peerObjects = selectedPeers
      .map((ticker) =>
        suggestedPeers.find((p: any) => (p.ticker || p.symbol) === ticker)
      )
      .filter(Boolean);
    const saveResponse = await savePeers(sessionId, peerObjects);
    console.log('Save peers response:', saveResponse);

    if (saveResponse.status === 'success') {
      console.log(
        `✅ Saved ${saveResponse.peers_saved} peers to session with auto-fetched market data`
      );

      useValuationStore.setState({
        peerData: saveResponse.peer_data || null,
        // Step transition handled by button callback in ValuationFlow
      });
    } else {
      useValuationStore.setState({ error: 'Failed to save peers' });
    }
  } catch (err) {
    console.error('Save peers error:', err);
    useValuationStore.setState({
      error: 'Failed to save peers. Please try again.',
    });
  } finally {
    useValuationStore.setState({ loading: false });
  }
};

// ─── Step 3: Select Model ───────────────────────────────────────────────────

export const handleSelectModel = async (modelType: string) => {
  const { sessionId, market, loading: currentLoading } = useValuationStore.getState();

  useValuationStore.setState({
    selectedModels: modelType,
    selectedModel: modelType,
    loading: true,
  });

  try {
    const data = await selectModels(sessionId, modelType, market);
    console.log('Select model response:', data);

    if (data.message) {
      useValuationStore.setState({ loading: false });
      // Step transition handled by button callback in ValuationFlow
      return;
    }
  } catch (err) {
    console.error('Select model error:', err);
    useValuationStore.setState({ error: 'Failed to select model' });
  } finally {
    // Only run finally if we didn't already set loading to false above
    if (useValuationStore.getState().loading) {
      useValuationStore.setState({ loading: false });
    }
  }
};

// ─── Back to Model Selection (from Step 4+) ─────────────────────────────────

export const handleBackToModelSelection = () => {
  const { market, selectedModels } = useValuationStore.getState();
  const currentMethod = selectedModels?.toLowerCase();

  // Clear data for the method being switched FROM only (preserve other methods)
  useValuationStore.setState((state) => ({
    valuationsData: {
      ...state.valuationsData,
      [market]: {
        ...state.valuationsData[market],
        [currentMethod]: null,
      },
    },
    forecastDriversData: {
      ...state.forecastDriversData,
      [market]: {
        ...state.forecastDriversData[market],
        [currentMethod]: null,
      },
    },
    dcfInputsData: {
      ...state.dcfInputsData,
      [market]: {
        ...state.dcfInputsData[market],
        [currentMethod]: null,
      },
    },
    valuationResults: {
      ...state.valuationResults,
      [market]: {
        ...state.valuationResults[market],
        [currentMethod]: null,
      },
    },
    aiError: null,
    peerData: null,
    selectedModels: '',
    selectedModel: '',
    requiredFields: [],
    confirmedValues: {},
    currentStep: 3,
    error: null,
  }));
};
