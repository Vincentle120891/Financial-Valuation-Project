import React, { useState } from 'react';

const ValuationFlow = () => {
  const [currentStep, setCurrentStep] = useState(1);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [_selectedCompany, setSelectedCompany] = useState(null);
  const [selectedModel, setSelectedModel] = useState(null);
  const [sessionId, setSessionId] = useState(null);
  const [requiredFields, setRequiredFields] = useState([]);
  const [_retrievedData, setRetrievedData] = useState(null);
  const [_apiData, setApiData] = useState({});
  const [aiData, setAiData] = useState({});
  const [confirmedValues, setConfirmedValues] = useState({});
  const [_selectedScenario, setSelectedScenario] = useState(null);
  const [valuationResults, setValuationResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [market, setMarket] = useState('international'); // 'international' or 'vietnamese'

  const API_BASE_URL = 'http://localhost:8000/api';

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(API_BASE_URL + '/step-1-search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: searchQuery, market: market })
      });
      const data = await response.json();
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
  };

  const handleSelectCompany = async (company) => {
    setLoading(true);
    try {
      const response = await fetch(API_BASE_URL + '/step-3-select-ticker', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId || '', ticker: company.symbol, market: company.market || 'international' })
      });
      const data = await response.json();
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
  };

  const handleSelectModel = async (modelType) => {
    setSelectedModel(modelType);
    setLoading(true);
    try {
      const response = await fetch(API_BASE_URL + '/step-4-select-models', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, models: [modelType] })
      });
      const data = await response.json();
      console.log('Select model response:', data);
      if (data.message) {
        setCurrentStep(5);
        // Immediately fetch required inputs after moving to step 5
        const inputsResponse = await fetch(API_BASE_URL + '/step-5-6-prepare-inputs', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ session_id: sessionId })
        });
        const inputsData = await inputsResponse.json();
        console.log('Required inputs response:', inputsData);
        if (inputsData.status && inputsData.required_inputs) {
          setRequiredFields(inputsData.required_inputs);
        }
      }
    } catch (err) {
      console.error('Select model error:', err);
      setError('Failed to select model');
    } finally {
      setLoading(false);
    }
  };

  React.useEffect(() => {
    if (selectedModel && currentStep === 5) {
      fetch(API_BASE_URL + '/step-5-6-prepare-inputs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId })
      })
        .then(res => res.json())
        .then(data => {
          console.log('UseEffect required inputs response:', data);
          if (data.status && data.required_inputs) {
            setRequiredFields(data.required_inputs);
          }
        })
        .catch(err => console.error('Prepare inputs error:', err));
    }
  }, [selectedModel, currentStep, sessionId]);

  const handleRetrieveData = async () => {
    setLoading(true);
    try {
      const fetchResponse = await fetch(API_BASE_URL + '/step-7-8-fetch-data', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId })
      });
      const fetchData = await fetchResponse.json();
      console.log('Fetch data response:', fetchData);
      
      const aiResponse = await fetch(API_BASE_URL + '/step-9-generate-ai', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId })
      });
      const aiData_response = await aiResponse.json();
      console.log('AI response:', aiData_response);
      
      if (fetchData.data && aiData_response.suggestions) {
        setApiData(fetchData.data.profile || {});
        setAiData(aiData_response.suggestions);
        setRetrievedData(fetchData.data);
        setCurrentStep(8);
      }
    } catch (err) {
      console.error('Retrieve data error:', err);
      setError('Failed to retrieve data');
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateAllAI = () => {
    const newConfirmed = { ...confirmedValues };
    if (aiData.wacc !== undefined) {
      newConfirmed.wacc = { value: aiData.wacc, source: 'ai', confidence: 0.8 };
    }
    if (aiData.terminal_growth !== undefined) {
      newConfirmed.terminal_growth = { value: aiData.terminal_growth, source: 'ai', confidence: 0.7 };
    }
    if (aiData.revenue_growth_forecast) {
      newConfirmed.revenue_growth_forecast = { value: aiData.revenue_growth_forecast, source: 'ai', confidence: 0.75 };
    }
    setConfirmedValues(newConfirmed);
  };

  const handleManualInput = (field, value) => {
    setConfirmedValues(prev => ({
      ...prev,
      [field]: { value: parseFloat(value) || value, source: 'manual' }
    }));
  };

  const handleConfirmAssumptions = async () => {
    setLoading(true);
    try {
      const response = await fetch(API_BASE_URL + '/step-10-confirm-assumptions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, assumptions: confirmedValues })
      });
      const data = await response.json();
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
  };

  const handleRunValuation = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(API_BASE_URL + '/step-11-12-valuate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId })
      });
      const data = await response.json();
      console.log('Valuation response:', data);
      if (data.result) {
        setValuationResults(data.result);
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
  };

  const handleReset = () => {
    setCurrentStep(1);
    setSearchQuery('');
    setSearchResults([]);
    setSelectedCompany(null);
    setSelectedModel(null);
    setSessionId(null);
    setRequiredFields([]);
    setRetrievedData(null);
    setApiData({});
    setAiData({});
    setConfirmedValues({});
    setSelectedScenario(null);
    setValuationResults(null);
    setError(null);
    setMarket('international');
  };

  const renderStep = () => {
    switch (currentStep) {
      case 1:
        return (
          <div className="step-container">
            <h2>Step 1: Input Company Name or Ticker</h2>
            <div className="market-toggle" style={{ marginBottom: '20px' }}>
              <label style={{ marginRight: '20px' }}>
                <input
                  type="radio"
                  value="international"
                  checked={market === 'international'}
                  onChange={(e) => setMarket(e.target.value)}
                />
                International Company
              </label>
              <label>
                <input
                  type="radio"
                  value="vietnamese"
                  checked={market === 'vietnamese'}
                  onChange={(e) => setMarket(e.target.value)}
                />
                Vietnamese Company
              </label>
            </div>
            <div className="input-group">
              <input
                type="text"
                placeholder={market === 'vietnamese' ? "Enter ticker (e.g., VNM) or company name" : "Enter ticker (e.g., AAPL) or company name"}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                className="search-input"
              />
              <button onClick={handleSearch} disabled={loading} className="btn-primary">
                {loading ? 'Searching...' : 'Search'}
              </button>
            </div>
            {searchResults.length > 0 && (
              <div className="search-results">
                {searchResults.map((result) => (
                  <div key={result.symbol} className="result-item">
                    <span>{result.name} ({result.symbol}) - {result.exchange}</span>
                    <button onClick={() => handleSelectCompany(result)} className="btn-secondary">Select</button>
                  </div>
                ))}
              </div>
            )}
            {error && <div className="error-message">{error}</div>}
          </div>
        );
      case 4:
        return (
          <div className="step-container">
            <h2>Step 4: Select Valuation Model</h2>
            <div className="model-options">
              {[
                { id: 'DCF', name: 'Discounted Cash Flow', desc: 'Intrinsic value based on projected free cash flows' },
                { id: 'DuPont', name: 'DuPont Analysis', desc: 'ROE decomposition analysis' },
                { id: 'COMPS', name: 'Trading Comps', desc: 'Relative valuation using peer multiples' }
              ].map((model) => (
                <div key={model.id} className="model-card" onClick={() => handleSelectModel(model.id)}>
                  <h3>{model.name}</h3>
                  <p>{model.desc}</p>
                </div>
              ))}
            </div>
          </div>
        );
      case 5:
        return (
          <div className="step-container">
            <h2>Step 5: Required Inputs</h2>
            <table className="data-table">
              <thead><tr><th>Category</th><th>Field</th><th>Type</th><th>Status</th></tr></thead>
              <tbody>
                {requiredFields.map((field, idx) => (
                  <tr key={idx}>
                    <td>{field.category || 'General'}</td>
                    <td>{field.name}</td>
                    <td>{field.requiresInput ? 'AI/Manual' : 'API Only'}</td>
                    <td>Pending</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <button onClick={handleRetrieveData} disabled={loading} className="btn-primary">
              {loading ? 'Retrieving...' : 'Retrieve Data'}
            </button>
          </div>
        );
      case 8:
        return (
          <div className="step-container">
            <h2>Step 8: Review AI Suggestions</h2>
            <button onClick={handleGenerateAllAI} className="btn-primary" style={{ marginBottom: '20px' }}>Auto-Fill All AI Values</button>
            <table className="data-table enhanced">
              <thead><tr><th>Field</th><th>AI Value</th><th>Your Value</th><th>Action</th></tr></thead>
              <tbody>
                <tr>
                  <td>WACC</td>
                  <td>{aiData.wacc ? (aiData.wacc * 100).toFixed(2) + '%' : 'N/A'}</td>
                  <td><input type="number" step="0.01" placeholder="Enter WACC" onChange={(e) => handleManualInput('wacc', e.target.value)} className="manual-input" /></td>
                  <td>{!confirmedValues.wacc ? (<button onClick={() => handleManualInput('wacc', aiData.wacc)} className="btn-small">Use AI</button>) : (<span>Confirmed</span>)}</td>
                </tr>
                <tr>
                  <td>Terminal Growth</td>
                  <td>{aiData.terminal_growth ? (aiData.terminal_growth * 100).toFixed(2) + '%' : 'N/A'}</td>
                  <td><input type="number" step="0.01" placeholder="Enter Terminal Growth" onChange={(e) => handleManualInput('terminal_growth', e.target.value)} className="manual-input" /></td>
                  <td>{!confirmedValues.terminal_growth ? (<button onClick={() => handleManualInput('terminal_growth', aiData.terminal_growth)} className="btn-small">Use AI</button>) : (<span>Confirmed</span>)}</td>
                </tr>
                <tr>
                  <td>Revenue Growth Forecast</td>
                  <td>{aiData.revenue_growth_forecast ? aiData.revenue_growth_forecast.map(g => (g * 100).toFixed(1) + '%').join(', ') : 'N/A'}</td>
                  <td><input type="text" placeholder="e.g., 0.05, 0.04, 0.03" onChange={(e) => handleManualInput('revenue_growth_forecast', e.target.value)} className="manual-input" /></td>
                  <td>{!confirmedValues.revenue_growth_forecast ? (<button onClick={() => handleManualInput('revenue_growth_forecast', aiData.revenue_growth_forecast)} className="btn-small">Use AI</button>) : (<span>Confirmed</span>)}</td>
                </tr>
              </tbody>
            </table>
            <div style={{ marginTop: '20px' }}><button onClick={handleConfirmAssumptions} disabled={loading} className="btn-primary">Confirm Assumptions</button></div>
          </div>
        );
      case 9:
        return (
          <div className="step-container">
            <h2>Step 9: Run Valuation</h2>
            <button onClick={handleRunValuation} disabled={loading} className="btn-primary">{loading ? 'Calculating...' : 'Run Valuation'}</button>
          </div>
        );
      case 10:
        return (
          <div className="step-container">
            <h2>Valuation Results</h2>
            {valuationResults && (
              <div className="results-container">
                <div className="result-card"><h3>Enterprise Value</h3><p className="result-value">${valuationResults.enterprise_value?.toLocaleString()}</p></div>
                <div className="result-card"><h3>Equity Value</h3><p className="result-value">${valuationResults.equity_value?.toLocaleString()}</p></div>
                <div className="result-card highlight"><h3>Implied Share Price</h3><p className="result-value">${valuationResults.implied_share_price?.toFixed(2)}</p></div>
                <div className="result-card"><h3>Current Price</h3><p className="result-value">${valuationResults.current_price?.toFixed(2)}</p></div>
                <div className={'result-card ' + (valuationResults.upside_downside?.includes('-') ? 'negative' : 'positive')}><h3>Upside/Downside</h3><p className="result-value">{valuationResults.upside_downside}</p></div>
                {valuationResults.scenario_analysis && (
                  <div className="scenario-section">
                    <h3>Scenario Analysis</h3>
                    <div className="scenario-cards">
                      <div className="scenario-card bull"><h4>Bull Case</h4><p>${valuationResults.scenario_analysis.bull_case?.toFixed(2)}</p></div>
                      <div className="scenario-card base"><h4>Base Case</h4><p>${valuationResults.scenario_analysis.base_case?.toFixed(2)}</p></div>
                      <div className="scenario-card bear"><h4>Bear Case</h4><p>${valuationResults.scenario_analysis.bear_case?.toFixed(2)}</p></div>
                    </div>
                  </div>
                )}
              </div>
            )}
            <button onClick={handleReset} className="btn-secondary" style={{ marginTop: '20px' }}>Start New Valuation</button>
          </div>
        );
      default:
        return <div className="step-container"><h2>Step {currentStep}</h2><p>Continue...</p><button onClick={() => setCurrentStep(prev => Math.min(prev + 1, 10))} className="btn-primary">Next</button></div>;
    }
  };

  return (
    <div className="valuation-flow">
      <div className="progress-bar">
        {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map(step => (
          <div key={step} className={'progress-step ' + (currentStep >= step ? 'active' : '')}>{step}</div>
        ))}
      </div>
      {renderStep()}
    </div>
  );
};

export default ValuationFlow;
