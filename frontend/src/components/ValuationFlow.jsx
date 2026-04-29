import React, { useState, useEffect, useCallback } from 'react';
import { searchCompanies, selectCompany, selectModels, prepareInputs, fetchData, generateAI, confirmAssumptions, runValuation } from '../services/api';
import SearchStep from './valuation-flow/SearchStep';
import ModelSelectionStep from './valuation-flow/ModelSelectionStep';
import RequirementsStep from './valuation-flow/RequirementsStep';
import AssumptionsStep from './valuation-flow/AssumptionsStep';
import RunValuationStep from './valuation-flow/RunValuationStep';
import ResultsStep from './valuation-flow/ResultsStep';

/**
 * ValuationFlow - Main Container Component
 * 
 * Orchestrates the 10-step valuation workflow:
 * 1. Search Company
 * 2-3. (Skipped in current implementation)
 * 4. Select Model
 * 5. Review Requirements
 * 6-7. (Data retrieval happens internally)
 * 8. Confirm Assumptions
 * 9. Run Valuation
 * 10. View Results
 * 
 * Architecture:
 * - Container component managing state and business logic
 * - Delegated rendering to specialized step components
 * - Centralized API communication via services/api.js
 */
const ValuationFlow = () => {
  // ==================== STATE MANAGEMENT ====================
  const [currentStep, setCurrentStep] = useState(1);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [selectedCompany, setSelectedCompany] = useState(null);
  const [selectedModel, setSelectedModel] = useState(null);
  const [sessionId, setSessionId] = useState(null);
  const [requiredFields, setRequiredFields] = useState([]);
  const [confirmedValues, setConfirmedValues] = useState({});
  const [selectedScenario, setSelectedScenario] = useState('base_case');
  const [valuationResults, setValuationResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [market, setMarket] = useState('international');
  
  // Enhanced data states
  const [historicalData, setHistoricalData] = useState(null);
  const [forecastDrivers, setForecastDrivers] = useState({
    best_case: { sales_volume_growth: [], inflation_rate: [], opex_growth: [], capital_expenditure: [], ar_days: [], inv_days: [], ap_days: [], tax_rate: [] },
    base_case: { sales_volume_growth: [], inflation_rate: [], opex_growth: [], capital_expenditure: [], ar_days: [], inv_days: [], ap_days: [], tax_rate: [] },
    worst_case: { sales_volume_growth: [], inflation_rate: [], opex_growth: [], capital_expenditure: [], ar_days: [], inv_days: [], ap_days: [], tax_rate: [] }
  });
  const [peerData, setPeerData] = useState([]);
  const [dupontResults, setDupontResults] = useState(null);
  const [compsResults, setCompsResults] = useState(null);
  const [dcfInputs, setDcfInputs] = useState(null);
  const [aiData, setAiData] = useState({});

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

  // ==================== STEP 3: SELECT COMPANY ====================
  const handleSelectCompany = useCallback(async (company) => {
    setLoading(true);
    try {
      const data = await selectCompany(sessionId || '', company.symbol, company.market || 'international');
      console.log('Select company response:', data);
      if (data.session_id) {
        setSessionId(data.session_id);
        setSelectedCompany(company);
        setCurrentStep(4);
      }
    } catch (err) {
      console.error('Select company error:', err);
      setError('Failed to select company');
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  // ==================== STEP 4: SELECT MODEL ====================
  const handleSelectModel = useCallback(async (modelType) => {
    setSelectedModel(modelType);
    setLoading(true);
    try {
      const data = await selectModels(sessionId, modelType);
      console.log('Select model response:', data);
      if (data.message) {
        setCurrentStep(5);
        await fetchRequiredInputs();
      }
    } catch (err) {
      console.error('Select model error:', err);
      setError('Failed to select model');
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  // ==================== BACK TO MODEL SELECTION ====================
  const handleBackToModelSelection = () => {
    setSelectedModel(null);
    setRequiredFields([]);
    setConfirmedValues({});
    setAiData({});
    setHistoricalData(null);
    setForecastDrivers({
      best_case: { sales_volume_growth: [], inflation_rate: [], opex_growth: [], capital_expenditure: [], ar_days: [], inv_days: [], ap_days: [], tax_rate: [] },
      base_case: { sales_volume_growth: [], inflation_rate: [], opex_growth: [], capital_expenditure: [], ar_days: [], inv_days: [], ap_days: [], tax_rate: [] },
      worst_case: { sales_volume_growth: [], inflation_rate: [], opex_growth: [], capital_expenditure: [], ar_days: [], inv_days: [], ap_days: [], tax_rate: [] }
    });
    setPeerData([]);
    setDupontResults(null);
    setCompsResults(null);
    setDcfInputs(null);
    setCurrentStep(4);
    setError(null);
  };

  // ==================== SHOW INPUTS (STEP 6) ====================
  const handleShowInputs = useCallback(() => {
    setCurrentStep(6);
  }, []);

  // ==================== CONTINUE TO ASSUMPTIONS (STEP 8) ====================
  const handleContinueToAssumptions = useCallback(() => {
    setCurrentStep(8);
  }, []);

  // ==================== BACK TO REQUIREMENTS (FROM STEP 6/8) ====================
  const handleBackToRequirements = useCallback(() => {
    setCurrentStep(5);
  }, []);

  // ==================== FETCH REQUIRED INPUTS ====================
  const fetchRequiredInputs = useCallback(async () => {
    try {
      const data = await prepareInputs(sessionId);
      console.log('Required inputs response:', data);
      if (data.status && data.required_inputs) {
        setRequiredFields(data.required_inputs);
      }
    } catch (err) {
      console.error('Prepare inputs error:', err);
    }
  }, [sessionId]);

  useEffect(() => {
    if (selectedModel && currentStep === 5 && sessionId) {
      fetchRequiredInputs();
    }
  }, [selectedModel, currentStep, sessionId, fetchRequiredInputs]);

  // ==================== STEP 7-8: RETRIEVE DATA ====================
  const handleRetrieveData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // Fetch financial data first
      let fetchDataResponse = null;
      try {
        fetchDataResponse = await fetchData(sessionId);
        console.log('Fetch data response:', fetchDataResponse);
      } catch (fetchErr) {
        console.error('Fetch data error:', fetchErr);
        setError('Failed to fetch financial data. Please try again.');
      }
      
      // Generate AI suggestions
      let aiDataResponse = null;
      try {
        aiDataResponse = await generateAI(sessionId);
        console.log('AI response:', aiDataResponse);
      } catch (aiErr) {
        console.error('Generate AI error:', aiErr);
        // Don't block - AI suggestions are optional for viewing inputs
        if (!error) {
          setError('Financial data loaded, but AI suggestions could not be generated.');
        }
      }
      
      // Set AI data if available
      if (aiDataResponse && aiDataResponse.suggestions) {
        setAiData(aiDataResponse.suggestions);
      }
      
      // Set financial data if available
      if (fetchDataResponse && fetchDataResponse.data) {
        const data = fetchDataResponse.data;
        
        if (data.historical_financials) {
          setHistoricalData(data.historical_financials);
        }
        if (data.forecast_drivers) {
          setForecastDrivers(data.forecast_drivers);
        }
        if (data.peers) {
          setPeerData(data.peers);
        }
        if (data.dcf_inputs) {
          setDcfInputs(data.dcf_inputs);
        }
        if (data.dupont_ratios) {
          setDupontResults(data.dupont_ratios);
        }
        if (data.comps_results) {
          setCompsResults(data.comps_results);
        }
      }
      
      // Clear error if we got at least some data
      if ((fetchDataResponse?.data || aiDataResponse?.suggestions) && error) {
        setError(null);
      }
    } catch (err) {
      console.error('Retrieve data error:', err);
      setError('Failed to retrieve data');
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  // ==================== MANUAL INPUT HANDLER ====================
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
  };

  // ==================== USE AI SUGGESTION ====================
  const handleUseAI = (field, aiValue) => {
    setConfirmedValues(prev => ({
      ...prev,
      [field]: { value: aiValue, source: 'ai', confidence: 0.8 }
    }));
  };

  // ==================== STEP 10: CONFIRM ASSUMPTIONS ====================
  const handleConfirmAssumptions = useCallback(async () => {
    setLoading(true);
    try {
      const data = await confirmAssumptions(sessionId, confirmedValues, selectedScenario);
      console.log('Confirm assumptions response:', data);
      if (data.status) {
        setCurrentStep(9);
      }
    } catch (err) {
      console.error('Confirm assumptions error:', err);
      setError('Failed to confirm assumptions');
    } finally {
      setLoading(false);
    }
  }, [sessionId, confirmedValues, selectedScenario]);

  // ==================== STEP 11-12: RUN VALUATION ====================
  const handleRunValuation = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await runValuation(sessionId, selectedModel, selectedScenario);
      console.log('Valuation response:', data);
      
      if (data.result) {
        setValuationResults(data.result);
        
        if (data.result.dcf_outputs) {
          // DCF results
        }
        if (data.result.dupont_outputs) {
          setDupontResults(data.result.dupont_outputs);
        }
        if (data.result.comps_outputs) {
          setCompsResults(data.result.comps_outputs);
        }
        
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
  }, [sessionId, selectedModel, selectedScenario]);

  // ==================== RESET ALL ====================
  const handleReset = () => {
    setCurrentStep(1);
    setSearchQuery('');
    setSearchResults([]);
    setSelectedCompany(null);
    setSelectedModel(null);
    setSessionId(null);
    setRequiredFields([]);
    setAiData({});
    setConfirmedValues({});
    setSelectedScenario('base_case');
    setValuationResults(null);
    setError(null);
    setMarket('international');
    setHistoricalData(null);
    setForecastDrivers({
      best_case: { sales_volume_growth: [], inflation_rate: [], opex_growth: [], capital_expenditure: [], ar_days: [], inv_days: [], ap_days: [], tax_rate: [] },
      base_case: { sales_volume_growth: [], inflation_rate: [], opex_growth: [], capital_expenditure: [], ar_days: [], inv_days: [], ap_days: [], tax_rate: [] },
      worst_case: { sales_volume_growth: [], inflation_rate: [], opex_growth: [], capital_expenditure: [], ar_days: [], inv_days: [], ap_days: [], tax_rate: [] }
    });
    setPeerData([]);
    setDupontResults(null);
    setCompsResults(null);
    setDcfInputs(null);
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
      case 4:
        return <ModelSelectionStep onSelectModel={handleSelectModel} />;
      case 5:
        return (
          <RequirementsStep
            selectedModel={selectedModel}
            onBackToModelSelection={handleBackToModelSelection}
            onRetrieveData={handleRetrieveData}
            loading={loading}
            historicalData={historicalData}
            forecastDrivers={forecastDrivers}
            peerData={peerData}
            dcfInputs={dcfInputs}
            dupontResults={dupontResults}
            compsResults={compsResults}
            aiData={aiData}
            requiredFields={requiredFields}
            onShowInputs={handleShowInputs}
          />
        );
      case 6:
        return (
          <AssumptionsStep
            historicalData={historicalData}
            peerData={peerData}
            aiData={aiData}
            confirmedValues={confirmedValues}
            selectedModel={selectedModel}
            onManualInput={handleManualInput}
            onUseAI={handleUseAI}
            showReviewOnly={true}
            onContinueToConfirm={handleContinueToAssumptions}
            onBackToRequirements={handleBackToRequirements}
            loading={loading}
          />
        );
      case 8:
        return (
          <AssumptionsStep
            historicalData={historicalData}
            peerData={peerData}
            aiData={aiData}
            confirmedValues={confirmedValues}
            selectedModel={selectedModel}
            onManualInput={handleManualInput}
            onUseAI={handleUseAI}
            onConfirmAssumptions={handleConfirmAssumptions}
            onBackToRequirements={handleBackToRequirements}
            loading={loading}
          />
        );
      case 9:
        return (
          <RunValuationStep
            selectedCompany={selectedCompany}
            selectedModel={selectedModel}
            selectedScenario={selectedScenario}
            confirmedValues={confirmedValues}
            loading={loading}
            onBackToModelSelection={handleBackToModelSelection}
            onRunValuation={handleRunValuation}
          />
        );
      case 10:
        return (
          <ResultsStep
            valuationResults={valuationResults}
            selectedModel={selectedModel}
            dupontResults={dupontResults}
            compsResults={compsResults}
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
        <div className="progress-indicator">
          {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map(step => (
            <div 
              key={step} 
              className={`step-dot ${currentStep >= step ? 'active' : ''}`}
              title={`Step ${step}`}
            />
          ))}
        </div>
        <div className="step-label">
          Step {currentStep} of 10: {' '}
          {
            currentStep === 1 ? 'Search Company' :
            currentStep === 4 ? 'Select Model' :
            currentStep === 5 ? 'Review Requirements' :
            currentStep === 6 ? 'View Retrieved Inputs' :
            currentStep === 8 ? 'Confirm Assumptions' :
            currentStep === 9 ? 'Run Valuation' :
            currentStep === 10 ? 'View Results' : 'In Progress'
          }
        </div>
      </header>
      
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
