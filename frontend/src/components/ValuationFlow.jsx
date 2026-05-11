import React, { useState, useEffect, useCallback } from 'react';
import {
  searchCompanies,
  suggestPeers,
  selectCompany,
  savePeers,
  selectModels,
  prepareInputs,
  fetchApiData,
  retrieveHistoricalData,
  initializeStep8Assumptions,
  generateAISuggestion,
  confirmAssumptions,
  runValuation,
  runValuationMulti
} from '../services/api';
import SearchStep from './valuation-flow/SearchStep';
import CompanySelectionStep from './valuation-flow/CompanySelectionStep';
import PeerSelectionStep from './valuation-flow/PeerSelectionStep';
import ModelSelectionStep from './valuation-flow/ModelSelectionStep';
import RequirementsStep from './valuation-flow/RequirementsStep';
import ApiDataStep from './valuation-flow/ApiDataStep';
import HistoricalDataExtractionStep from './valuation-flow/HistoricalDataExtractionStep';
import ForecastDriversStep from './valuation-flow/ForecastDriversStep';
import AssumptionsStep from './valuation-flow/AssumptionsStep';
import RunValuationStep from './valuation-flow/RunValuationStep';
import ResultsStep from './valuation-flow/ResultsStep';

// Debounce utility function for auto-save
const useDebounce = (callback, delay) => {
  const timeoutRef = React.useRef(null);
  
  const debouncedCallback = useCallback((...args) => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
    timeoutRef.current = setTimeout(() => {
      callback(...args);
    }, delay);
  }, [callback, delay]);
  
  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);
  
  return debouncedCallback;
};

/**
 * ValuationFlow - Main Container Component
 *
 * Orchestrates the 11-step valuation workflow:
 * 1. Search Company (Input ticker/name)
 * 2-3. Select Company (get session_id) - Merged
 * 4. Select Valuation Model (DCF/DuPont/Comps)
 * 5. Review Required Inputs (Show data requirements + Retrieve button)
 * 6. Review Retrieved Financial Data (Display all API-fetched inputs)
 * 7. Review AI-Generated Assumptions (AI suggestions with manual override)
 * 8. Modify Forecast Drivers (Fine-tune growth rates, margins, scenarios)
 * 9. Review & Confirm All Assumptions (Final confirmation before calculation)
 * 10. Run Valuation Calculation (Execute DCF/DuPont/Comps models)
 * 11. View Valuation Results & Analysis (Intrinsic value, sensitivity, charts)
 *
 * Architecture:
 * - Container component managing state and business logic
 * - Delegated rendering to specialized step components
 * - Centralized API communication via services/valuationApi.js
 */
const ValuationFlow = () => {
  // ==================== STATE MANAGEMENT ====================
  const [currentStep, setCurrentStep] = useState(1);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [selectedCompany, setSelectedCompany] = useState(null);
  const [suggestedPeers, setSuggestedPeers] = useState([]);
  const [selectedPeers, setSelectedPeers] = useState([]);
  const [selectedModels, setSelectedModels] = useState(''); // GAP 2 FIX: Single model string instead of array (radio button behavior)
  const [sessionId, setSessionId] = useState(null);
  const [forecastYears, setForecastYears] = useState(5);

  // Step 5: Required inputs
  const [requiredInputs, setRequiredInputs] = useState(null);
  const [requiredFields, setRequiredFields] = useState(null);

  // Financial Data State - Matrix structure: valuationsData[market][method]
  // This enables "3 Valuation Methods × 2 Market Versions" architecture
  const [valuationsData, setValuationsData] = useState({
    international: {
      dcf: null,
      dupont: null,
      comps: null
    },
    vietnam: {
      dcf: null,
      dupont: null,
      comps: null
    }
  });
  
  // Helper to get/set data for current market + method
  const getValuationData = (method) => {
    return valuationsData[market]?.[method?.toLowerCase()] || null;
  };
  
  const setValuationData = (method, data) => {
    setValuationsData(prev => deepMergeValuations(prev, market, method, data));
  };
  
  // Note: aiAssumptions was never a separate state - it's part of the matrix structure via getValuationData()
  // All data access should use getValuationData(method) directly instead of legacy aliases

  // Assumption Management
  const [confirmedValues, setConfirmedValues] = useState({});
  const [selectedScenario, setSelectedScenario] = useState('base_case');
  const [validationErrors, setValidationErrors] = useState([]);

  // Step 8-9: Forecast Drivers & DCF Inputs - Matrix structure: forecastDriversData[market][method]
  // This enables "3 Valuation Methods × 2 Market Versions" architecture
  const [forecastDriversData, setForecastDriversData] = useState({
    international: {
      dcf: null,
      dupont: null,
      comps: null
    },
    vietnam: {
      dcf: null,
      dupont: null,
      comps: null
    }
  });
  
  const [dcfInputsData, setDcfInputsData] = useState({
    international: {
      dcf: null,
      dupont: null,
      comps: null
    },
    vietnam: {
      dcf: null,
      dupont: null,
      comps: null
    }
  });
  
  // Helper to get/set forecast drivers for current market + method
  const getForecastDrivers = (method) => {
    return forecastDriversData[market]?.[method?.toLowerCase()] || null;
  };
  
  const setForecastDrivers = (method, data) => {
    setForecastDriversData(prev => deepMergeForecastDrivers(prev, market, method, data));
  };
  
  // Helper to get/set DCF inputs for current market + method
  const getDcfInputs = (method) => {
    return dcfInputsData[market]?.[method?.toLowerCase()] || null;
  };
  
  const setDcfInputs = (method, data) => {
    setDcfInputsData(prev => deepMergeDcfInputs(prev, market, method, data));
  };
  
  // All data access should use getForecastDrivers(method) or getDcfInputs(method) directly
  
  // Step 6-7: Data Storage (using matrix structure primarily)
  const [peerData, setPeerData] = useState(null);
  const [calculatedMetrics, setCalculatedMetrics] = useState(null);

  // Step 9-10: Results - Using matrix structure: valuationResults[market][method]
  const [valuationResults, setValuationResults] = useState({
    international: {
      dcf: null,
      dupont: null,
      comps: null
    },
    vietnam: {
      dcf: null,
      dupont: null,
      comps: null
    }
  });

  // Helper to get/set results for current market + method
  const getResult = (method) => {
    return valuationResults[market]?.[method?.toLowerCase()] || null;
  };
  
  const setResult = (method, data) => {
    setValuationResults(prev => ({
      ...prev,
      [market]: {
        ...prev[market],
        [method?.toLowerCase()]: data
      }
    }));
  };

  // UI State
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [market, setMarket] = useState('international');
  
  // AI-related state for error/warning messages (non-blocking)
  const [aiError, setAiError] = useState(null);

  // ==================== STEP 1: SEARCH COMPANY ====================
  const handleSearch = useCallback(async () => {
    if (!searchQuery.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const data = await searchCompanies(searchQuery, market);
      console.log('Search response:', data);
      if (data.results && data.results.length > 0) {
        setSearchResults(data.results);
        setError(null);
      } else {
        setSearchResults([]);
        setError('No results found. Try an exact ticker symbol.');
      }
    } catch (err) {
      console.error('Search error:', err);
      setError('Search failed. Please ensure the backend server is running on port 8000.');
      setSearchResults([]);
    } finally {
      setLoading(false);
    }
  }, [searchQuery, market]);

  // ==================== STEP 2: FIND PEERS ====================
  const handleFindPeers = useCallback(async (company) => {
    setLoading(true);
    setError(null);
    try {
      const data = await suggestPeers(company.symbol, company.market || market, 10);
      console.log('Suggest peers response:', data);
      if (data.peers && data.peers.length > 0) {
        setSuggestedPeers(data.peers);

        // Auto-select top 5 peers with highest scores
        const sortedPeers = [...data.peers].sort((a, b) => b.score - a.score);
        const topPeers = sortedPeers.slice(0, Math.min(5, sortedPeers.length));
        setSelectedPeers(topPeers);

        console.log(`Auto-selected ${topPeers.length} peers with highest scores:`, topPeers.map(p => p.symbol));

        // Move to Step 3: Peer Selection
        setCurrentStep(3);
      } else {
        setError('No peers found for this company. Try a different company or manually add peers later.');
      }
    } catch (err) {
      console.error('Suggest peers error:', err);
      setError('Failed to find peers. Please ensure the backend server is running.');
    } finally {
      setLoading(false);
    }
  }, [market]);

  // ==================== STEP 3: TOGGLE PEER SELECTION ====================
  const handleTogglePeer = useCallback((peer) => {
    setSelectedPeers(prev => {
      const exists = prev.find(p => p.symbol === peer.symbol);
      if (exists) {
        return prev.filter(p => p.symbol !== peer.symbol);
      } else {
        return [...prev, peer];
      }
    });
  }, []);

  // ==================== STEP 3: CONTINUE TO MODEL SELECTION ====================
  const handleContinueToModelSelection = useCallback(async () => {
    if (!sessionId || selectedPeers.length === 0) {
      setError('No session or peers selected');
      return;
    }

    setLoading(true);
    try {
      // Save selected peers to backend session and fetch peer data
      const saveResponse = await savePeers(sessionId, selectedPeers);
      console.log('Save peers response:', saveResponse);

      if (saveResponse.status === 'success') {
        console.log(`✅ Saved ${saveResponse.peers_saved} peers to session with auto-fetched market data`);
        setCurrentStep(4);
      } else {
        setError('Failed to save peers');
      }
    } catch (err) {
      console.error('Save peers error:', err);
      setError('Failed to save peers. Please try again.');
    } finally {
      setLoading(false);
    }
  }, [sessionId, selectedPeers]);

  // ==================== STEP 1: SELECT COMPANY ====================
  const handleSelectCompany = useCallback(async (company) => {
    setLoading(true);
    try {
      // Call backend to create session and get session_id
      const data = await selectCompany('', company.symbol, company.market || 'international');
      console.log('Select company response:', data);
      if (data.session_id) {
        setSessionId(data.session_id);
                // Merge backend company data with search results
        const enrichedCompany = { ...company };
        if (data.company_data) {
          // Merge company_data fields into selectedCompany
          if (data.company_data.current_price !== undefined) {
            enrichedCompany.currentPrice = data.company_data.current_price;
          }
          if (data.company_data.market_cap !== undefined) {
            enrichedCompany.marketCap = data.company_data.market_cap;
          }
          if (data.company_data.beta !== undefined) {
            enrichedCompany.beta = data.company_data.beta;
          }
          if (data.company_data.risk_free_rate !== undefined) {
            enrichedCompany.riskFreeRate = data.company_data.risk_free_rate;
          }
          if (data.company_data.market_risk_premium !== undefined) {
            enrichedCompany.marketRiskPremium = data.company_data.market_risk_premium;
          }
          if (data.company_data.sector !== undefined) {
            enrichedCompany.sector = data.company_data.sector;
          }
          if (data.company_data.industry !== undefined) {
            enrichedCompany.industry = data.company_data.industry;
          }
          if (data.company_data.country !== undefined) {
            enrichedCompany.country = data.company_data.country;
          }
        }

        setSelectedCompany(enrichedCompany);
        setCurrentStep(2); // Move to Step 2: Company Overview
      }
    } catch (err) {
      console.error('Select company error:', err);
      setError('Failed to select company');
    } finally {
      setLoading(false);
    }
  }, []);

  // ==================== HANDLE MODEL SWITCH (Preserve all models' data) ====================
  const handleSelectModel = useCallback(async (modelType) => {
    // GAP 2 & GAP 3 FIX: Update selected model first, then deep merge to preserve other models' data
    // Single selection (radio button behavior) - modelType is a string, not array
    setSelectedModels(modelType);
    
    setLoading(true);
    try {
      // Always use single model endpoint (multi-select is now forbidden per documentation)
      const data = await selectModels(sessionId, modelType, market);
      console.log('Select model response:', data);
      if (data.message) {
        setCurrentStep(5);
      }
    } catch (err) {
      console.error('Select model error:', err);
      setError('Failed to select model');
    } finally {
      setLoading(false);
    }
  }, [sessionId, market]);
  
  // ==================== DEEP MERGE UTILITY FOR MATRIX STATE ====================
  // Prevents data loss when switching between models by preserving all models' data
  const deepMergeValuations = (prev, market, method, newData) => {
    return {
      ...prev,
      [market]: {
        ...prev[market],
        [method?.toLowerCase()]: newData
      }
    };
  };
  
  const deepMergeForecastDrivers = (prev, market, method, newData) => {
    return {
      ...prev,
      [market]: {
        ...prev[market],
        [method?.toLowerCase()]: newData
      }
    };
  };
  
  const deepMergeDcfInputs = (prev, market, method, newData) => {
    return {
      ...prev,
      [market]: {
        ...prev[market],
        [method?.toLowerCase()]: newData
      }
    };
  };
  
  // ==================== HANDLE MULTI-METHOD VALUATION ====================
  const handleRunMultiMethodValuation = useCallback(async () => {
    // Multi-select is now forbidden per documentation - this function is deprecated
    // Fall back to single method valuation
    return handleRunValuation();
  }, []);

  // ==================== BACK TO MODEL SELECTION ====================
  const handleBackToModelSelection = () => {
    const currentMethod = selectedModels?.toLowerCase();
    
    // Only clear data for the method being switched FROM, preserve other methods' data
    // This maintains "Fetch Once, Use Many" principle - data stays cached for reuse
    setValuationsData(prev => ({
      ...prev,
      [market]: {
        ...prev[market],
        [currentMethod]: null
      }
    }));
    setForecastDriversData(prev => ({
      ...prev,
      [market]: {
        ...prev[market],
        [currentMethod]: null
      }
    }));
    setDcfInputsData(prev => ({
      ...prev,
      [market]: {
        ...prev[market],
        [currentMethod]: null
      }
    }));
    setAiError(null); // Clear AI errors
    setPeerData(null);
    // Reset only the current method's results, preserve others
    setValuationResults(prev => ({
      ...prev,
      [market]: {
        ...prev[market],
        [currentMethod]: null
      }
    }));
    
    // Reset selection and navigation
    setSelectedModels('');
    setRequiredFields([]);
    setConfirmedValues({});
    setCurrentStep(4);
    setError(null);
  };

  // ==================== SHOW API DATA (STEP 6) ====================
  const handleShowApiData = useCallback(() => {
    setCurrentStep(6);
  }, []);

  // ==================== CONTINUE TO HISTORICAL DATA RETRIEVAL (STEP 7) ====================
  const handleContinueToHistoricalDataRetrieval = useCallback(async () => {
    setLoading(true);
    // Use selected model (single string, not array)
    const method = selectedModels;
    if (!method) {
      setError('No valuation method selected');
      setLoading(false);
      return;
    }
    
    try {
      // Retrieve historical data using AI extraction when user explicitly clicks to go to Step 7
      console.log('📊 Starting historical data retrieval with AI extraction...');
      const historicalDataResponse = await retrieveHistoricalData(sessionId, method, market);
      console.log('Historical data response:', historicalDataResponse);

      if (historicalDataResponse.suggestions) {
        // Store historical gap-filling results in matrix structure
        setValuationData(method, historicalDataResponse.suggestions);

        // Check for timeout status
        if (historicalDataResponse.status === 'historical_data_timeout') {
          setAiError('⏱️ Historical data extraction timed out. Using available API data only.');
        } else {
          // Extract gap-filling information from response
          const gapsFilled = historicalDataResponse.suggestions.total_gaps_filled || 0;
          const completeness = historicalDataResponse.suggestions.data_completeness_score || 1.0;

          if (gapsFilled > 0) {
            setAiError(`✅ Successfully filled ${gapsFilled} historical data gaps with ${(completeness * 100).toFixed(0)}% completeness.`);
          } else {
            // No gaps found - API data was complete
            setAiError(null);
          }

          // Check for fallback metadata
          const metadata = historicalDataResponse.metadata || {};
          if (metadata?.used_fallback) {
            let errorMsg = '';
            if (metadata.fallback_reason) {
              errorMsg += `Reason: ${metadata.fallback_reason}. `;
            }

            if (metadata.provider_errors && Object.keys(metadata.provider_errors).length > 0) {
              errorMsg += 'Provider errors: ';
              const errorDetails = Object.entries(metadata.provider_errors)
                .map(([provider, error]) => `${provider}: ${error}`)
                .join('; ');
              errorMsg += errorDetails;
            } else if (!metadata.available_providers || metadata.available_providers.length === 0) {
              errorMsg += 'No AI providers configured. Please add API keys for Groq, Gemini, or Qwen.';
            }

            errorMsg += ' Using deterministic fallback - assumptions generated from CAPM formula and historical averages.';
            setAiError(errorMsg);
          } else {
            setAiError(null); // Clear any previous AI error
          }
        }
      } else if (historicalDataResponse.detail) {
        setAiError(historicalDataResponse.detail);
      }
    } catch (aiErr) {
      console.error('AI generation failed:', aiErr);
      setAiError(aiErr.message || 'AI suggestions could not be generated. You can still proceed with manual inputs.');
    } finally {
      setLoading(false);
      setCurrentStep(7);
    }
  }, [sessionId, selectedModels, market]);

  // ==================== CONTINUE TO FORECAST DRIVERS (STEP 8) ====================
  const handleContinueToForecastDrivers = useCallback(async () => {
    setLoading(true);
    // Use selected model (single string, not array)
    const method = selectedModels;
    if (!method) {
      setError('No valuation method selected');
      setLoading(false);
      return;
    }
    
    try {
      // Initialize Step 8 with historical trendlines before showing the step
      console.log('📊 Initializing Step 8 assumptions with historical data...');
      const step8Response = await initializeStep8Assumptions(sessionId, method, market);
      console.log('Step 8 initialization response:', step8Response);

      if (step8Response && step8Response.categories) {
        // Store the initialized assumptions in matrix structure
        setValuationData(method, step8Response);
        
        // Also store in component state for backward compatibility
        setForecastDrivers(method, step8Response);
      }
    } catch (err) {
      console.error('Failed to initialize Step 8:', err);
      // Continue anyway - user can still manually input data
    } finally {
      setLoading(false);
      setCurrentStep(8);
    }
  }, [sessionId, selectedModels, market]);

  // ==================== CONTINUE TO ASSUMPTIONS (STEP 7) ====================
  const handleContinueToAssumptions = useCallback(() => {
    setCurrentStep(7);
  }, []);

  // ==================== BACK TO REQUIREMENTS (FROM STEP 6/8) ====================
  const handleBackToRequirements = useCallback(() => {
    setCurrentStep(5);
  }, []);

  // ==================== BACK TO API DATA (FROM STEP 7) ====================
  const handleBackToApiData = useCallback(() => {
    setCurrentStep(6);
  }, []);

  // ==================== FETCH REQUIRED INPUTS ====================
  const fetchRequiredInputs = useCallback(async (method) => {
    try {
      const targetMethod = method || selectedModels;
      const data = await prepareInputs(sessionId, targetMethod, market);
      console.log('Required inputs response:', data);
      if (data.status && data.required_inputs) {
        setRequiredFields(data.required_inputs);
      }
    } catch (err) {
      console.error('Prepare inputs error:', err);
    }
  }, [sessionId, selectedModels, market]);

  useEffect(() => {
    const method = selectedModels;
    if (method && currentStep === 5 && sessionId) {
      fetchRequiredInputs(method);
    }
  }, [selectedModels, currentStep, sessionId, market, fetchRequiredInputs]);

  // ==================== STEP 6: RETRIEVE API DATA ONLY ====================

  const handleRetrieveData = useCallback(async () => {
    setLoading(true);
    // Use selected model (single string, not array)
    const method = selectedModels;
    if (!method) {
      setError('No valuation method selected');
      setLoading(false);
      return;
    }
    
    try {
      // Only fetch API data - do NOT generate AI yet
      const fetchDataResponse = await fetchApiData(sessionId, method, market);
      console.log('Fetch API data response:', fetchDataResponse);

      // Set financial data first - handle both old and new backend formats
      if (fetchDataResponse.data) {
        // Store in matrix structure
        setValuationData(method, fetchDataResponse.data);
        
        // Also store in individual state variables for backward compatibility
        if (fetchDataResponse.data.historical_financials) {
          // Step 6 API data is now stored in valuationsData matrix via setValuationData above
          // No need for separate step6ApiData state
        }
        if (fetchDataResponse.data.forecast_drivers) {
          setForecastDrivers(method, fetchDataResponse.data.forecast_drivers);
        }
        if (fetchDataResponse.data.peer_comparables) {
          setPeerData(fetchDataResponse.data.peer_comparables);
        }
        if (fetchDataResponse.data.dcf_inputs) {
          setDcfInputs(method, fetchDataResponse.data.dcf_inputs);
        }
        // Store DuPont and Comps data in matrix (not separate state)
        if (fetchDataResponse.data.dupont_ratios) {
          setResult('DuPont', fetchDataResponse.data.dupont_ratios);
        }
        if (fetchDataResponse.data.comps_results) {
          setResult('COMPS', fetchDataResponse.data.comps_results);
        }
        // Set calculated metrics from Step 6 backend response
        if (fetchDataResponse.data.calculated_metrics) {
          setCalculatedMetrics(fetchDataResponse.data.calculated_metrics);
        }

        // Auto-navigate to Step 6 to show retrieved data
        setCurrentStep(6);
      }

    } catch (err) {
      console.error('Retrieve data error:', err);
      setError('Failed to retrieve data');
    } finally {
      setLoading(false);
    }
  }, [sessionId, selectedModels, market]);

  // ==================== MANUAL INPUT HANDLER (with auto-save) ====================
  const handleManualInput = (field, value) => {
    let parsedValue = value;

    if (typeof value === 'string' && value.includes(',')) {
      parsedValue = value.split(',').map(v => parseFloat(v.trim()));
    } else {
      parsedValue = parseFloat(value) || value;
    }

    setConfirmedValues(prev => ({
      ...prev,
      [field]: { value: parsedValue, source: 'manual' }
    }));
    
    // Also update forecastDrivers or dcfInputs state for Step 8 persistence
    if (field.startsWith('forecast_')) {
      // Parse field format: forecast_scenario_field_yearIndex
      const parts = field.split('_');
      if (parts.length >= 4) {
        const scenario = parts[1];
        const driverField = parts[2];
        const yearIndex = parseInt(parts[3], 10);
        
        setForecastDrivers(prev => {
          if (!prev || !prev[scenario]) return prev;
          return {
            ...prev,
            [scenario]: {
              ...prev[scenario],
              [driverField]: prev[scenario][driverField].map((v, idx) => 
                idx === yearIndex ? parsedValue : v
              )
            }
          };
        });
      }
    } else if (field.startsWith('dcf_')) {
      const dcfField = field.replace('dcf_', '');
      setDcfInputs(prev => ({
        ...prev,
        [dcfField]: parsedValue
      }));
    }
  };

  // Debounced auto-save handler for forecast drivers (500ms delay)
  const handleAutoSaveForecastDrivers = useDebounce((field, value) => {
    console.log('[Auto-Save] Forecast driver saved:', field, value);
    // The actual save happens in handleManualInput, this is for logging/debugging
  }, 500);

  // Debounced auto-save handler for DCF inputs (500ms delay)
  const handleAutoSaveDcfInputs = useDebounce((field, value) => {
    console.log('[Auto-Save] DCF input saved:', field, value);
    // The actual save happens in handleManualInput, this is for logging/debugging
  }, 500);

  // ==================== USE AI SUGGESTION ====================
  const handleUseAI = (field, aiValue) => {
    setConfirmedValues(prev => ({
      ...prev,
      [field]: { value: aiValue, source: 'ai', confidence: 0.8 }
    }));
  };

  // ==================== STEP 10: CONFIRM ASSUMPTIONS ====================
  const handleConfirmAssumptions = useCallback(async () => {
    // Use selected model (single string, not array)
    const method = selectedModels;
    if (!method) {
      setError('No valuation method selected');
      return;
    }
    
    // Validate required DCF inputs before proceeding
    if (method === 'DCF') {
      const errors = [];

      // Check critical DCF inputs
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
        setValidationErrors(errors);
        setError('Please fix the following validation errors:\n• ' + errors.join('\n• '));
        return;
      }
    }

    // Clear any previous validation errors
    setValidationErrors([]);
    setError(null);

    setLoading(true);
    try {
      const data = await confirmAssumptions(sessionId, confirmedValues, selectedScenario, method, market);
      console.log('Confirm assumptions response:', data);
      if (data.status) {
        setCurrentStep(9);
      }
    } catch (err) {
      console.error('Confirm assumptions error:', err);
      setError('Failed to confirm assumptions: ' + (err.message || 'Unknown error'));
    } finally {
      setLoading(false);
    }
  }, [sessionId, confirmedValues, selectedScenario, selectedModels, dcfInputs, market]);

  // ==================== STEP 11-12: RUN VALUATION ====================
  const handleRunValuation = useCallback(async () => {
    // Multi-select is now forbidden per documentation - always use single method
    setLoading(true);
    setError(null);
    // Use selected model (single string, not array)
    const method = selectedModels;
    if (!method) {
      setError('No valuation method selected');
      setLoading(false);
      return;
    }
    
    try {
      const data = await runValuation(sessionId, method, selectedScenario, market);
      console.log('Valuation response:', data);

      if (data.result) {
        // Store results in matrix structure
        if (data.result.dcf_outputs) {
          setResult('DCF', data.result.dcf_outputs);
        }
        if (data.result.dupont_outputs) {
          setResult('DuPont', data.result.dupont_outputs);
        }
        if (data.result.comps_outputs) {
          setResult('COMPS', data.result.comps_outputs);
        }
        
        // Also store full result object for backward compatibility
        setValuationResults(prev => ({
          ...prev,
          [market]: {
            ...prev[market],
            dcf: data.result.dcf_outputs || prev[market].dcf,
            dupont: data.result.dupont_outputs || prev[market].dupont,
            comps: data.result.comps_outputs || prev[market].comps
          }
        }));

        setCurrentStep(10);
      } else {
        setError(data.detail || 'Failed to run valuation');
      }
    } catch (err) {
      console.error('Valuation error:', err);
      setError('Failed to run valuation. Please ensure the backend server is running.');
    } finally {
      setLoading(false);
    }
  }, [sessionId, selectedModels, selectedScenario, market, handleRunMultiMethodValuation]);

  // ==================== RESET ALL ====================
  const handleReset = () => {
    setCurrentStep(1);
    setSearchQuery('');
    setSearchResults([]);
    setSelectedCompany(null);
    setSelectedModels(''); // GAP 2 FIX: Reset to empty string (single selection)
    setSessionId(null);
    setRequiredFields([]);
    setConfirmedValues({});
    setSelectedScenario('base_case');
    setError(null);
    setAiError(null); // Clear AI errors on reset
    setMarket('international');
    // Reset all matrix structures
    setValuationsData({
      international: {
        dcf: null,
        dupont: null,
        comps: null
      },
      vietnam: {
        dcf: null,
        dupont: null,
        comps: null
      }
    });
    setForecastDriversData({
      international: {
        dcf: null,
        dupont: null,
        comps: null
      },
      vietnam: {
        dcf: null,
        dupont: null,
        comps: null
      }
    });
    setDcfInputsData({
      international: {
        dcf: null,
        dupont: null,
        comps: null
      },
      vietnam: {
        dcf: null,
        dupont: null,
        comps: null
      }
    });
    setValuationResults({
      international: {
        dcf: null,
        dupont: null,
        comps: null
      },
      vietnam: {
        dcf: null,
        dupont: null,
        comps: null
      }
    });
    setPeerData(null);
    setCalculatedMetrics(null);
  };

  // ==================== RENDER STEP ====================
  const renderStep = () => {
    switch (currentStep) {
      case 1:
        return (
          <SearchStep
            searchQuery={searchQuery}
            setSearchQuery={setSearchQuery}
            searchResults={searchResults}
            loading={loading}
            error={error}
            market={market}
            setMarket={setMarket}
            onSearch={handleSearch}
            onSelectCompany={handleSelectCompany}
          />
        );
      case 2:
        return (
          <CompanySelectionStep
            selectedCompany={selectedCompany}
            onFindPeers={handleFindPeers}
            onContinue={() => setCurrentStep(3)}
            onBack={() => setCurrentStep(1)}
            loading={loading}
            hasPeers={suggestedPeers.length > 0}
          />
        );
      case 3:
        return (
          <PeerSelectionStep
            suggestedPeers={suggestedPeers}
            selectedPeers={selectedPeers}
            onTogglePeer={handleTogglePeer}
            onContinue={handleContinueToModelSelection}
            onBack={() => setCurrentStep(2)}
            loading={loading}
          />
        );
      case 4:
        return <ModelSelectionStep onSelectModel={handleSelectModel} selectedModels={selectedModels} />;
      case 5:
        return (
          <RequirementsStep
            selectedModel={selectedModels}
            onBackToModelSelection={handleBackToModelSelection}
            onRetrieveData={handleRetrieveData}
            loading={loading}
            historicalData={getValuationData(selectedModels)}
            forecastDrivers={getForecastDrivers(selectedModels)}
            peerData={peerData}
            dcfInputs={getDcfInputs(selectedModels)}
            dupontResults={getResult('DuPont')}
            compsResults={getResult('COMPS')}
            aiData={getValuationData(selectedModels)}
            aiError={aiError}
            requiredFields={requiredFields}
            onShowInputs={handleShowApiData}
          />
        );
      case 6:
        return (
          <ApiDataStep
            historicalData={getValuationData(selectedModels)}
            forecastDrivers={getForecastDrivers(selectedModels)}
            peerData={peerData}
            dcfInputs={getDcfInputs(selectedModels)}
            dupontResults={getResult('DuPont')}
            compsResults={getResult('COMPS')}
            calculatedMetrics={calculatedMetrics}
            onBackToRequirements={handleBackToRequirements}
            onContinueToAiAssumptions={handleContinueToHistoricalDataRetrieval}
            loading={loading}
          />
        );
      case 7:
        return (
          <HistoricalDataExtractionStep
            historicalGapsData={getValuationData(selectedModels)}
            aiError={aiError}
            confirmedValues={confirmedValues}
            selectedModel={selectedModels}
            market={market}
            historicalData={getValuationData(selectedModels)}
            apiData={calculatedMetrics}
            onManualInput={handleManualInput}
            onUseAI={handleUseAI}
            onBackToApiData={handleBackToApiData}
            onContinueToForecastDrivers={handleContinueToForecastDrivers}
            onRetryAiExtraction={handleContinueToHistoricalDataRetrieval}
            loading={loading}
          />
        );
      case 8:
        return (
          <ForecastDriversStep
            sessionId={sessionId}
            forecastDrivers={getForecastDrivers(selectedModels)}
            dcfInputs={getDcfInputs(selectedModels)}
            step6Data={calculatedMetrics}
            step7Data={getValuationData(selectedModels)}
            market={market}
            selectedModel={selectedModels}
            onManualInput={handleManualInput}
            onAutoSave={handleAutoSaveForecastDrivers}
            onConfirmDrivers={handleConfirmAssumptions}
            onBackToRequirements={handleBackToRequirements}
            onContinueToAssumptions={handleContinueToAssumptions}
            loading={loading}
          />
        );
      case 9:
        return (
          <AssumptionsStep
            historicalData={getValuationData(selectedModels)}
            peerData={peerData}
            aiData={getValuationData(selectedModels)}
            aiError={aiError}
            confirmedValues={confirmedValues}
            selectedModel={selectedModels}
            onManualInput={handleManualInput}
            onUseAI={handleUseAI}
            onConfirmAssumptions={handleConfirmAssumptions}
            onBackToRequirements={handleBackToRequirements}
            loading={loading}
          />
        );
      case 10:
        return (
          <RunValuationStep
            selectedCompany={selectedCompany}
            selectedModel={selectedModels}
            selectedScenario={selectedScenario}
            confirmedValues={confirmedValues}
            loading={loading}
            onBackToModelSelection={handleBackToModelSelection}
            onRunValuation={handleRunValuation}
          />
        );
      case 11:
        return (
          <ResultsStep
            valuationMatrix={valuationsData}
            selectedMarket={market}
            selectedModels={selectedModels}
            onBackToModelSelection={handleBackToModelSelection}
            onReset={handleReset}
          />
        );
      default:
        return <div>Step under construction</div>;
    }
  };

  // ==================== MAIN RENDER ====================
  return (
    <div className="valuation-flow-app">
      <header className="app-header">
        <h1>Unified Valuation Platform</h1>

        {/* Progress Indicator with Step Counter */}
        <div className="progress-indicator" role="progressbar" aria-valuenow={currentStep} aria-valuemin="1" aria-valuemax="11">
          {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11].map(step => (
            <div
              key={step}
              className={`step-dot ${currentStep >= step ? 'active' : ''} ${currentStep === step ? 'current' : ''}`}
              title={`Step ${step}`}
              aria-label={`Step ${step}`}
            />
          ))}
        </div>

        {/* Enhanced Step Label with Progress */}
        <div className="step-label">
          <span className="step-counter">Step {currentStep} of 11</span>
          <span className="step-name">
            {currentStep === 1 ? 'Search Company' :
             currentStep === 2 ? 'Company Overview' :
             currentStep === 3 ? 'Peer Selection' :
             currentStep === 4 ? 'Select Model' :
             currentStep === 5 ? 'Review Requirements' :
             currentStep === 6 ? 'View Retrieved Inputs' :
             currentStep === 7 ? 'Historical Data Extraction' :
             currentStep === 8 ? 'Forecast Drivers & DCF Inputs' :
             currentStep === 9 ? 'Confirm Assumptions' :
             currentStep === 10 ? 'Run Valuation' :
             currentStep === 11 ? 'View Results' : 'In Progress'}
          </span>
          <span className="step-progress">{Math.round((currentStep / 11) * 100)}% Complete</span>
        </div>
      </header>

      {/* Error Display - Consistent Error Handling */}
      {error && (
        <div className="error-banner" role="alert">
          <div className="error-content">
            <span className="error-icon">⚠️</span>
            <div className="error-message">
              <strong>Error:</strong> {error}
            </div>
            <button
              className="error-dismiss"
              onClick={() => setError(null)}
              aria-label="Dismiss error"
            >
              ✕
            </button>
          </div>
        </div>
      )}

      {/* Loading Overlay */}
      {loading && (
        <div className="loading-overlay" aria-live="polite">
          <div className="loading-spinner"></div>
          <p>Processing...</p>
        </div>
      )}

      <main className="app-main">
        {renderStep()}
      </main>

      <footer className="app-footer">
        <p>Powered by yfinance, Alpha Vantage & AI Analysis | DCF • DuPont • Trading Comps</p>
      </footer>
    </div>
  );
};

export default ValuationFlow;
