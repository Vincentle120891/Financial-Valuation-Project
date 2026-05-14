import React, { useState, useEffect, useCallback } from 'react';
import {
  searchCompanies,
  suggestPeers,
  selectCompany,
  savePeers,
  validateManualPeers,
  selectModels,
  confirmAssumptions,
  runValuation
} from '../services/api';
import {
  retrieveData,
  initializeAssumptions,
  prepareRequirements,
  generateAISuggestion,
  deepMergeMatrix
} from '../services/valuationService';
import SearchStep from './valuation-flow/SearchStep';
import CompanySelectionStep from './valuation-flow/CompanySelectionStep';
import ModelSelectionStep from './valuation-flow/ModelSelectionStep';
import PeerSelectionStep from './valuation-flow/PeerSelectionStep';
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
 * Orchestrates the 12-step valuation workflow (ALIGNED WITH BACKEND):
 * Step 1: Search Company (Input ticker/name)
 * Step 2: Company Overview (View selected company data ONLY - no peers, no models)
 * Step 3: Select Valuation Model (DCF/DuPont/Comps) -> Determines peer criteria
 * Step 4: Find Peers (Click "Find Peers" using model-specific criteria)
 * Step 5: Select Peers (Review peer table with similarity scores, toggle selections)
 * Step 6: Requirements Review (Review required input fields based on Model + Peers)
 * Step 7: Fetch API Data (Retrieve all financial inputs - "Fetch Once, Use Many")
 * Step 8: Historical Data Processing (AI extraction & trendlines)
 * Step 9: Forecast Drivers (Manual overrides & assumption adjustment)
 * Step 10: Confirm Assumptions (Final confirmation before calculation)
 * Step 11: Execute Valuation (Run models)
 * Step 12: View Results (Display valuation results)
 *
 * Architecture:
 * - Container component managing state and business logic
 * - Delegated rendering to specialized step components
 * - Centralized API communication via services/api.js
 * - Aligned with backend unified schemas (Steps 1-12)
 * - Single model execution enforced (radio buttons prevent multi-model race conditions)
 * - MODEL FIRST, THEN PEERS: Peer discovery requires model selection to use method-specific criteria
 */
const ValuationFlow = () => {
  // ==================== STATE MANAGEMENT ====================
  const [currentStep, setCurrentStep] = useState(1);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [selectedCompany, setSelectedCompany] = useState(null);
  const [suggestedPeers, setSuggestedPeers] = useState([]);
  const [selectedPeers, setSelectedPeers] = useState([]);
  const [sessionId, setSessionId] = useState(null);
  const [selectedModels, setSelectedModels] = useState(''); // Single model string (radio button behavior)
  const [forecastYears, setForecastYears] = useState(5);
  const [manualPeerInput, setManualPeerInput] = useState('');
  const [manualPeerError, setManualPeerError] = useState(null);
  const [manualPeerLoading, setManualPeerLoading] = useState(false);

  // Market validation state - ensures market selection is consistent throughout workflow
  const [marketValidation, setMarketValidation] = useState({
    isValid: true,
    message: '',
    selectedMarket: 'international',
    isLocked: false // Lock market after Step 1 to prevent mid-workflow switching
  });

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
    setValuationsData(prev => deepMergeMatrix(prev, market, method, data));
  };

  // Note: aiAssumptions was never a separate state - it's part of the matrix structure via getValuationData()
  // All data access should use getValuationData(method) directly instead of legacy aliases

  // Assumption Management
  const [confirmedValues, setConfirmedValues] = useState({});
  const [selectedScenario, setSelectedScenario] = useState('base_case');
  const [validationErrors, setValidationErrors] = useState([]);

  // Step 8-9: Assumption & AI Suggestion - Matrix structure: forecastDriversData[market][method]
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
    setForecastDriversData(prev => deepMergeMatrix(prev, market, method, data));
  };

  // Helper to get/set DCF inputs for current market + method
  const getDcfInputs = (method) => {
    return dcfInputsData[market]?.[method?.toLowerCase()] || null;
  };

  const setDcfInputs = (method, data) => {
    setDcfInputsData(prev => deepMergeMatrix(prev, market, method, data));
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

    // Validate market selection before search
    if (!['international', 'vietnam'].includes(market)) {
      setMarketValidation({
        isValid: false,
        message: 'Invalid market selection. Please select either International or Vietnam market.',
        selectedMarket: market
      });
      setError('Invalid market selection');
      return;
    }

    // Update validation state
    setMarketValidation({
      isValid: true,
      message: `Searching in ${market === 'international' ? 'International' : 'Vietnamese'} market`,
      selectedMarket: market
    });

    setLoading(true);
    setError(null);
    try {
      const data = await searchCompanies(searchQuery, market);
      console.log('Search response:', data);

      // Unified response handling - both markets now return the same format
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

  // ==================== STEP 4: FIND PEERS (After Model Selection - Method Specific) ====================
  const handleFindPeers = useCallback(async (company) => {
    setLoading(true);
    setError(null);

    // Validate model selection first - peer discovery requires model-specific criteria
    if (!selectedModels) {
      setError('Please select a valuation model in Step 3 first before finding peers');
      setLoading(false);
      return;
    }

    // Validate market selection before finding peers
    if (!['international', 'vietnam'].includes(market)) {
      setMarketValidation({
        isValid: false,
        message: 'Invalid market selection. Please select either International or Vietnam market.',
        selectedMarket: market
      });
      setError('Invalid market selection');
      setLoading(false);
      return;
    }

    try {
      const ticker = company.ticker || company.symbol;
      // Pass the selected model for method-specific peer discovery
      const data = await suggestPeers(ticker, company.market || market, 10, selectedModels);
      console.log('Suggest peers response:', data);
      if (data.peers && data.peers.length > 0) {
        setSuggestedPeers(data.peers);

        // Auto-select top 5 peers with highest scores
        const sortedPeers = [...data.peers].sort((a, b) => b.score - a.score);
        const topPeers = sortedPeers.slice(0, Math.min(5, sortedPeers.length));
        setSelectedPeers(topPeers);

        console.log(`Auto-selected ${topPeers.length} peers with highest scores:`, topPeers.map(p => p.symbol));

        // Stay on Step 4 to review peers - user clicks Continue to go to Step 5
        // Do NOT auto-advance to Step 5
      } else {
        setError('No peers found for this company. Try a different company or manually add peers later.');
      }
    } catch (err) {
      console.error('Suggest peers error:', err);
      setError('Failed to find peers. Please ensure the backend server is running.');
    } finally {
      setLoading(false);
    }
  }, [market, selectedModels]);

  // ==================== STEP 5: TOGGLE PEER SELECTION ====================
  const handleTogglePeer = useCallback((peer) => {
    setSelectedPeers(prev => {
      // Use ticker or symbol as the unique identifier for consistency
      const peerId = peer.ticker || peer.symbol;
      const exists = prev.find(p => (p.ticker || p.symbol) === peerId);
      if (exists) {
        return prev.filter(p => (p.ticker || p.symbol) !== peerId);
      } else {
        return [...prev, peer];
      }
    });
  }, []);

  // ==================== STEP 5: CONTINUE TO REQUIREMENTS REVIEW (After peer selection) ====================
  const handleContinueToRequirementsReview = useCallback(async () => {
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

        // Store peer data from the response for later steps
        if (saveResponse.peer_data) {
          setPeerData(saveResponse.peer_data);
        }

        setCurrentStep(5);  // Move to Step 5: Requirements Review
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

  // ==================== STEP 2: SELECT COMPANY (No peer finding yet) ====================
  const handleSelectCompany = useCallback(async (company) => {
    setLoading(true);

    // Validate market selection before selecting company
    if (!['international', 'vietnam'].includes(market)) {
      setMarketValidation({
        isValid: false,
        message: 'Invalid market selection. Please select either International or Vietnam market.',
        selectedMarket: market
      });
      setError('Invalid market selection');
      setLoading(false);
      return;
    }

    try {
      // Call backend to create session and get session_id
      // Use the explicitly selected market from Step 1 radio button
      const ticker = company.ticker || company.symbol;
      const data = await selectCompany('', ticker, company.market || market);
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

        // Lock market after successful company selection to prevent mid-workflow switching
        const ticker = company.ticker || company.symbol;
        setMarketValidation({
          isValid: true,
          message: `Company ${ticker} selected in ${market === 'international' ? 'International' : 'Vietnamese'} market`,
          selectedMarket: market,
          isLocked: true // Market is now locked - cannot be changed after Step 1
        });

        setCurrentStep(2); // Move to Step 2: Company Overview (view company data before model selection)
      }
    } catch (err) {
      console.error('Select company error:', err);
      setError('Failed to select company');
    } finally {
      setLoading(false);
    }
  }, [market]);

  // ==================== STEP 3: SELECT MODEL ====================
  const handleSelectModel = useCallback(async (modelType) => {
    // GAP 2 & GAP 3 FIX: Update selected model first, then deep merge to preserve other models' data
    // Single selection (radio button behavior) - modelType is a string, not array

    setSelectedModels(modelType);

    setLoading(true);
    try {
      // Always use single model endpoint (multi-select is now forbidden per documentation)
      // Pass undefined for peers - peers will be discovered in Step 4
      const data = await selectModels(sessionId, modelType, market, undefined, undefined);
      console.log('Select model response:', data);
      if (data.message) {
        // After selecting model, move to Step 4: Find & Review Peers
        // User will click "Find Peers" button in Step 4 to discover peers using model-specific criteria
        setCurrentStep(4);
      }
    } catch (err) {
      console.error('Select model error:', err);
      setError('Failed to select model');
    } finally {
      setLoading(false);
    }
  }, [sessionId, market]);

  // ==================== BACK TO MODEL SELECTION (STEP 4) ====================
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
    // Keep peers when going back to model selection - they are method-agnostic
    // setSuggestedPeers([]); 
    // setSelectedPeers([]);
    // Reset only the current method's results, preserve others
    setValuationResults(prev => ({
      ...prev,
      [market]: {
        ...prev[market],
        [currentMethod]: null
      }
    }));

    // Reset selection and navigation - go back to Step 4: Model Selection
    setSelectedModels('');
    setRequiredFields([]);
    setConfirmedValues({});
    setCurrentStep(4);  // Go back to Step 4: Model Selection
    setError(null);
    // Keep market locked - user selected company already, just switching models
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

    // Market validation: Ensure market is locked and matches session
    if (!marketValidation?.isLocked) {
      setError('⚠️ Market must be locked before retrieving historical data. Please select a company first.');
      setLoading(false);
      return;
    }

    try {
      // Use valuationService.retrieveData with AI gap-filling enabled
      const result = await retrieveData({
        sessionId,
        method,
        market,
        includeHistoricalAI: true
      });

      console.log('Historical data retrieval result:', result);

      if (result.success && result.data) {
        // Store historical gap-filling results in matrix structure
        setValuationData(method, result.data);

        // Handle AI metadata for user feedback
        const aiMetadata = result.data.ai_metadata || {};
        
        if (aiMetadata.error) {
          setAiError(aiMetadata.error);
        } else if (aiMetadata.gaps_filled > 0) {
          setAiError(`✅ Successfully filled ${aiMetadata.gaps_filled} historical data gaps with ${(aiMetadata.completeness_score * 100).toFixed(0)}% completeness.`);
        } else {
          setAiError(null);
        }
      }
    } catch (aiErr) {
      console.error('AI generation failed:', aiErr);
      setAiError(aiErr.message || 'AI suggestions could not be generated. You can still proceed with manual inputs.');
    } finally {
      setLoading(false);
      setCurrentStep(7);
    }
  }, [sessionId, selectedModels, market, marketValidation]);

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
      // Use valuationService.initializeAssumptions wrapper
      const result = await initializeAssumptions(sessionId, method, market);
      console.log('Step 8 initialization response:', result);

      if (result.success && result.data) {
        const step8Response = result.data;
        
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
    setCurrentStep(6);
  }, []);

  // ==================== BACK TO API DATA (FROM STEP 8) ====================
  const handleBackToApiData = useCallback(() => {
    setCurrentStep(7);
  }, []);

  // ==================== BACK TO FORECAST DRIVERS (FROM STEP 10) ====================
  const handleBackToForecastDrivers = useCallback(() => {
    setCurrentStep(9);
  }, []);

  // ==================== FETCH REQUIRED INPUTS ====================
  const fetchRequiredInputs = useCallback(async (method) => {
    try {
      // Market validation: Ensure market is locked and matches session
      if (!marketValidation?.isLocked) {
        console.warn('⚠️ Market not locked when fetching required inputs - this may indicate workflow issue');
        return;
      }

      const targetMethod = method || selectedModels;
      // Use valuationService.prepareRequirements instead of direct API call
      const result = await prepareRequirements(sessionId, targetMethod, market);
      console.log('Required inputs response:', result);

      if (result.success && result.fields) {
        setRequiredFields(result.fields);
      }
    } catch (err) {
      console.error('Prepare inputs error:', err);
    }
  }, [sessionId, selectedModels, market, marketValidation]);

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

    // Market validation: Ensure market is locked and matches session
    if (!marketValidation?.isLocked) {
      setError('⚠️ Market must be locked before retrieving data. Please select a company first.');
      setLoading(false);
      return;
    }

    try {
      // Use valuationService.retrieveData - handles all transformation logic internally
      const result = await retrieveData({
        sessionId,
        method,
        market,
        includeHistoricalAI: false // Only fetch API data, no AI gap-filling yet
      });
      
      console.log('Retrieve data result:', result);

      if (result.success && result.data) {
        const financialData = result.data;

        // Store in matrix structure using imported helper
        setValuationData(method, financialData);

        // Also store in individual state variables for backward compatibility
        if (financialData.historical_financials) {
          // Step 6 API data is now stored in valuationsData matrix via setValuationData above
          // No need for separate step6ApiData state
        }
        if (financialData.forecast_drivers) {
          setForecastDrivers(method, financialData.forecast_drivers);
        }
        if (financialData.peer_comparables) {
          setPeerData(financialData.peer_comparables);
        }
        if (financialData.dcf_inputs) {
          setDcfInputs(method, financialData.dcf_inputs);
        }
        // Store DuPont and Comps data in matrix (not separate state)
        if (financialData.dupont_ratios) {
          setResult('DuPont', financialData.dupont_ratios);
        }
        if (financialData.comps_results) {
          setResult('COMPS', financialData.comps_results);
        }
        // Set calculated metrics from Step 6 backend response
        if (financialData.calculated_metrics) {
          setCalculatedMetrics(financialData.calculated_metrics);
        }

        // Auto-navigate to Step 6 to show retrieved data
        setCurrentStep(6);
      } else if (!result.success) {
        setError(result.error || 'Failed to retrieve data');
      }

    } catch (err) {
      console.error('Retrieve data error:', err);
      // Provide more specific error message based on the error type
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to retrieve data';
      setError(errorMessage);

      // Log additional debug info
      console.error('Error details:', {
        message: err.message,
        response: err.response?.data,
        status: err.response?.status
      });
    } finally {
      setLoading(false);
    }
  }, [sessionId, selectedModels, market, marketValidation]);

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

        const currentDrivers = getForecastDrivers(selectedModels);
        if (currentDrivers && currentDrivers[scenario]) {
          const updatedScenario = {
            ...currentDrivers[scenario],
            [driverField]: currentDrivers[scenario][driverField].map((v, idx) =>
              idx === yearIndex ? parsedValue : v
            )
          };
          setForecastDrivers(selectedModels, {
            ...currentDrivers,
            [scenario]: updatedScenario
          });
        }
      }
    } else if (field.startsWith('dcf_')) {
      const dcfField = field.replace('dcf_', '');
      const currentInputs = getDcfInputs(selectedModels) || {};
      setDcfInputs(selectedModels, {
        ...currentInputs,
        [dcfField]: parsedValue
      });
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
      const dcfInputs = getDcfInputs(method);

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
  }, [sessionId, confirmedValues, selectedScenario, selectedModels, dcfInputsData, market]);

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
  }, [sessionId, selectedModels, selectedScenario, market]);

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
    // Reset market validation and unlock market for new workflow
    setMarketValidation({
      isValid: true,
      message: '',
      selectedMarket: 'international',
      isLocked: false // Unlock market for new workflow
    });
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
            marketValidation={marketValidation}
          />
        );
      case 2:
        // Step 2: Company Overview - Only display company data, no peers, no models
        // User reviews company data, then clicks Continue to go to Step 3 (Model Selection)
        return (
          <CompanySelectionStep
            selectedCompany={selectedCompany}
            onFindPeers={() => {}} // Disabled in Step 2 - peer finding moved to Step 4
            onContinue={() => setCurrentStep(3)}
            onBack={() => setCurrentStep(1)}
            loading={loading}
            hasPeers={false} // No peers yet - will be found in Step 4 after model selection
            market={market}
            showFindPeersButton={false} // Hide Find Peers button in Step 2
            currentStep={2}
          />
        );
      case 3:
        // Step 3: Model Selection - Select valuation model (DCF/DuPont/Comps)
        // Model selection determines the criteria for peer discovery in Step 4
        // Auto-advance to Step 4 after model selection
        return (
          <ModelSelectionStep 
            onSelectModel={handleSelectModel} 
            selectedModels={selectedModels} 
          />
        );
      case 4:
        // Step 4: Find & Review Peers - Click "Find Peers" using model-specific criteria
        // User discovers peers based on the selected model, then reviews and selects them
        // Reuse CompanySelectionStep with peer finding ENABLED (hasPeers shows success message after finding)
        // After clicking Continue, user goes to Step 5 to review/select peers in table format
        return (
          <CompanySelectionStep
            selectedCompany={selectedCompany}
            onFindPeers={handleFindPeers}
            onContinue={() => setCurrentStep(5)}
            onBack={() => setCurrentStep(3)}
            loading={loading}
            hasPeers={suggestedPeers && suggestedPeers.length > 0}
            market={market}
            showFindPeersButton={true} // Show Find Peers button in Step 4
            currentStep={4}
          />
        );
      case 5:
        // Step 5: Peer Selection Table - Review and select/deselect individual peers
        // User sees peer table with similarity scores and can toggle selections
        return (
          <PeerSelectionStep
            suggestedPeers={suggestedPeers}
            selectedPeers={selectedPeers}
            onTogglePeer={handleTogglePeer}
            onContinue={handleContinueToRequirementsReview}
            onBack={() => setCurrentStep(4)}
            loading={loading}
          />
        );
      case 6:
        // Step 6: Requirements Review
        // Note: valuationData is not passed to Step 6 because data hasn't been fetched yet
        // Step 6 only shows requirements from requiredFields (prepared by prepareAssumptions)
        // Unified schema data (valuationData) is only available after Step 7 fetches it
        return (
          <RequirementsStep
            selectedModel={selectedModels}
            onBackToPeerSelection={() => setCurrentStep(5)}
            onRetrieveData={handleRetrieveData}
            loading={loading}
            historicalData={null}
            forecastDrivers={null}
            peerData={null}
            dcfInputs={null}
            dupontResults={null}
            compsResults={null}
            aiData={null}
            aiError={aiError}
            requiredFields={requiredFields}
            onShowInputs={handleShowApiData}
          />
        );
      case 7:
        const valuationData = getValuationData(selectedModels);
        return (
          <ApiDataStep
            historicalData={valuationData}
            forecastDrivers={valuationData?.forecast_drivers}
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
      case 8:
        return (
          <HistoricalDataExtractionStep
            sessionId={sessionId}
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
      case 9:
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
            onBackToApiData={handleBackToApiData}
            onContinueToAssumptions={handleContinueToAssumptions}
            loading={loading}
          />
        );
      case 10:
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
            onBackToForecastDrivers={handleBackToForecastDrivers}
            loading={loading}
          />
        );
      case 11:
        return (
          <RunValuationStep
            selectedCompany={selectedCompany}
            selectedModel={selectedModels}
            selectedScenario={selectedScenario}
            confirmedValues={confirmedValues}
            loading={loading}
            onBackToAssumptions={() => setCurrentStep(10)}
            onRunValuation={handleRunValuation}
          />
        );
      case 12:
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
        <div className="progress-indicator" role="progressbar" aria-valuenow={currentStep} aria-valuemin="1" aria-valuemax="12">
          {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12].map(step => (
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
          <span className="step-counter">Step {currentStep} of 12</span>
          <span className="step-name">
            {currentStep === 1 ? 'Search Company' :
             currentStep === 2 ? 'Company Overview' :
             currentStep === 3 ? 'Select Model' :
             currentStep === 4 ? 'Find Peers' :
             currentStep === 5 ? 'Select Peers' :
             currentStep === 6 ? 'Requirements Review' :
             currentStep === 7 ? 'Fetch API Data' :
             currentStep === 8 ? 'Historical Data Extraction' :
             currentStep === 9 ? 'Forecast Drivers' :
             currentStep === 10 ? 'Confirm Assumptions' :
             currentStep === 11 ? 'Run Valuation' :
             currentStep === 12 ? 'View Results' : 'In Progress'}
          </span>
          <span className="step-progress">{Math.round((currentStep / 12) * 100)}% Complete</span>
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
