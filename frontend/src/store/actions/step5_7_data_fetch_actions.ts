/**
 * dataFetchActions - Steps 6-7 handlers (Data Retrieval, Historical Data)
 *
 * Plain async functions that import useValuationStore and call getState()/setState().
 */

import useValuationStore from '../useValuationStore';
import { retrieveData, prepareRequirements, initializeAssumptions } from '../../services/step8_10_valuation_service';

// ─── Fetch Required Inputs (Step 5 pre-fetch) ──────────────────────────────

export const fetchRequiredInputs = async (method?: string) => {
  const { sessionId, selectedModels, market, marketValidation } =
    useValuationStore.getState();

  try {
    if (!marketValidation?.isLocked) {
      console.warn(
        '⚠️ Market not locked when fetching required inputs - this may indicate workflow issue'
      );
      return;
    }

    const targetMethod = method || selectedModels;
    const result = await prepareRequirements(sessionId, targetMethod, market);
    console.log('Required inputs response:', result);

    if (result.success && result.fields) {
      useValuationStore.setState({ requiredFields: result.fields });
    }
  } catch (err) {
    console.error('Prepare inputs error:', err);
  }
};

// ─── Step 6: Retrieve API Data ──────────────────────────────────────────────

export const handleRetrieveData = async () => {
  const { sessionId, selectedModels, market, marketValidation } =
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

  if (!marketValidation?.isLocked) {
    useValuationStore.setState({
      error: '⚠️ Market must be locked before retrieving data. Please select a company first.',
      loading: false,
    });
    return;
  }

  try {
    const result = await retrieveData({
      sessionId,
      method,
      market,
      includeHistoricalAI: false,
    });

    console.log('Retrieve data result:', result);

    if (result.success && result.data) {
      const financialData = result.data;
      const { setValuationData, setForecastDrivers, setDcfInputs, setResult } =
        useValuationStore.getState();

      // Store in matrix structure
      setValuationData(method, financialData);

      if (financialData.forecast_drivers) {
        setForecastDrivers(method, financialData.forecast_drivers);
      }

      // Store peer data from the response
      if (financialData.peer_comparables) {
        const peerComparables = financialData.peer_comparables;
        const companies = financialData.comps_multiples?.companies || [];
        useValuationStore.setState({
          peerData: {
            companies: companies,
            peer_market_caps: peerComparables.peer_market_caps?.value || [],
            peer_betas: peerComparables.peer_betas?.value || [],
            peer_total_debt: peerComparables.peer_total_debt?.value || [],
            peer_cash: peerComparables.peer_cash?.value || [],
            peer_tax_rates: peerComparables.peer_tax_rates?.value || [],
            median_ev_ebitda: financialData.comps_multiples?.ev_to_ebitda?.value,
            median_pe: financialData.comps_multiples?.p_to_e?.value,
            median_ev_revenue: financialData.comps_multiples?.ev_to_sales?.value,
            median_pb: financialData.comps_multiples?.p_to_b?.value,
          },
        });
      } else if (financialData.comps_multiples) {
        useValuationStore.setState({
          peerData: {
            companies: financialData.comps_multiples.companies || [],
            median_ev_ebitda: financialData.comps_multiples.ev_to_ebitda?.value,
            median_pe: financialData.comps_multiples.p_to_e?.value,
            median_ev_revenue: financialData.comps_multiples.ev_to_sales?.value,
            median_pb: financialData.comps_multiples.p_to_b?.value,
          },
        });
      }

      if (financialData.dcf_inputs) {
        setDcfInputs(method, financialData.dcf_inputs);
      }

      if (financialData.dupont_ratios) {
        setResult('DuPont', financialData.dupont_ratios);
      }
      if (financialData.comps_results) {
        setResult('COMPS', financialData.comps_results);
      }

      if (financialData.calculated_metrics) {
        useValuationStore.setState({
          calculatedMetrics: financialData.calculated_metrics,
        });
      }

      useValuationStore.setState({ loading: false });
      // Step transition handled by button callback in ValuationFlow
      return;
    } else if (!result.success) {
      useValuationStore.setState({ error: result.error || 'Failed to retrieve data' });
    }
  } catch (err: any) {
    console.error('Retrieve data error:', err);
    const errorMessage =
      err.response?.data?.detail || err.message || 'Failed to retrieve data';
    useValuationStore.setState({ error: errorMessage });
    console.error('Error details:', {
      message: err.message,
      response: err.response?.data,
      status: err.response?.status,
    });
  } finally {
    useValuationStore.setState({ loading: false });
  }
};

// ─── Step 6 → Step 7: Continue to Historical Data Retrieval ─────────────────

export const handleContinueToHistoricalDataRetrieval = async () => {
  // Step transition handled by button callback in ValuationFlow
  useValuationStore.setState({ loading: false });
};

// ─── Step 7 → Step 8: Initialize Step 8 Assumptions ─────────────────────────
// NOTE: retrieveHistoricalData() removed — Step 7 data is already in session
// from the AI web search. FinancialStatementsMerger runs inside step-8-initialize.

export const handleStep7ContinueToForecastDrivers = async () => {
  const { sessionId, selectedModels, market } = useValuationStore.getState();

  useValuationStore.setState({ loading: true });

  const method = selectedModels;
  if (!method) {
    useValuationStore.setState({
      error: 'No valuation method selected',
      loading: false,
    });
    return;
  }

  // Step 8: Initialize assumptions with trendlines from merged data
  // FinancialStatementsMerger runs inside step-8-initialize endpoint
  try {
    const step8Result = await initializeAssumptions(sessionId, method, market);
    console.log('Step 8 initialization result:', step8Result);

    if (step8Result.success && step8Result.data) {
      const { setValuationData, setForecastDrivers } = useValuationStore.getState();
      setValuationData(method, step8Result.data);
      setForecastDrivers(method, step8Result.data);
    }
  } catch (err: any) {
    console.warn('Step 8 initialization failed:', err.message);
  }

  useValuationStore.setState({ loading: false });
  // Step transition handled by button callback in ValuationFlow
};
