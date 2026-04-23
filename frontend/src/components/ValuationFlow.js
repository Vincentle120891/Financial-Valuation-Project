import React, { useState } from 'react';

const ValuationFlow = () => {
  const [currentStep, setCurrentStep] = useState(1);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [selectedCompany, setSelectedCompany] = useState(null);
  const [selectedModel, setSelectedModel] = useState(null);
  const [requiredFields, setRequiredFields] = useState([]);
  const [retrievedData, setRetrievedData] = useState(null);
  const [apiData, setApiData] = useState({});
  const [aiData, setAiData] = useState({});
  const [confirmedValues, setConfirmedValues] = useState({});
  const [selectedScenario, setSelectedScenario] = useState(null);
  const [valuationResults, setValuationResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Step 2: Search for tickers
  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`http://localhost:5000/api/search?q=${encodeURIComponent(searchQuery)}`);
      const data = await response.json();
      if (data.success) {
        setSearchResults(data.data);
        if (data.data.length === 0) {
          setError('No results found');
        }
      }
    } catch (err) {
      setError('Search failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  // Step 3: Select company
  const handleSelectCompany = (company) => {
    setSelectedCompany(company);
    setCurrentStep(4);
  };

  // Step 4: Select model
  const handleSelectModel = async (modelType) => {
    setSelectedModel(modelType);
    setLoading(true);
    try {
      const response = await fetch('http://localhost:5000/api/select-model', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ modelType })
      });
      const data = await response.json();
      if (data.success) {
        setCurrentStep(5);
      }
    } catch (err) {
      setError('Failed to select model');
    } finally {
      setLoading(false);
    }
  };

  // Step 5: Get required fields
  React.useEffect(() => {
    if (selectedModel && currentStep === 5) {
      fetch(`http://localhost:5000/api/required-fields?model=${selectedModel}`)
        .then(res => res.json())
        .then(data => {
          if (data.success) {
            setRequiredFields(data.data);
          }
        });
    }
  }, [selectedModel, currentStep]);

  // Step 6: Retrieve data - now separates API data (read-only) from AI data (generatable)
  const handleRetrieveData = async () => {
    setLoading(true);
    try {
      const response = await fetch('http://localhost:5000/api/retrieve-data', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ modelType: selectedModel })
      });
      const data = await response.json();
      if (data.success) {
        setRetrievedData(data.data);
        setApiData(data.data.apiData || {});
        setAiData(data.data.aiData || {});
        setCurrentStep(7);
      }
    } catch (err) {
      setError('Failed to retrieve data');
    } finally {
      setLoading(false);
    }
  };

  // Generate AI data for a specific field
  const handleGenerateAI = (field, category) => {
    const aiFields = retrievedData?.[category] || {};
    if (aiFields[field]) {
      setConfirmedValues(prev => ({
        ...prev,
        [field]: { value: aiFields[field].value, source: 'ai', confidence: aiFields[field].confidence }
      }));
    }
  };

  // Generate all AI data at once
  const handleGenerateAllAI = () => {
    const newConfirmed = { ...confirmedValues };
    
    // Add all AI data
    Object.entries(aiData).forEach(([key, data]) => {
      if (data.editable && data.value !== undefined) {
        newConfirmed[key] = { value: data.value, source: 'ai', confidence: data.confidence };
      }
    });
    
    // Add COMPS-specific AI data
    if (retrievedData?.compsData) {
      Object.entries(retrievedData.compsData).forEach(([key, data]) => {
        if (data.editable && data.value !== undefined) {
          newConfirmed[key] = { value: data.value, source: 'ai', confidence: data.confidence };
        }
      });
    }
    
    // Add DuPont-specific AI data
    if (retrievedData?.dupontData) {
      Object.entries(retrievedData.dupontData).forEach(([key, data]) => {
        if (data.editable && data.value !== undefined) {
          newConfirmed[key] = { value: data.value, source: 'ai', confidence: data.confidence };
        }
      });
    }
    
    // Add Real Estate-specific AI data
    if (retrievedData?.realEstateData) {
      Object.entries(retrievedData.realEstateData).forEach(([key, data]) => {
        if (data.editable && data.value !== undefined) {
          newConfirmed[key] = { value: data.value, source: 'ai', confidence: data.confidence };
        }
      });
    }
    
    setConfirmedValues(newConfirmed);
  };

  // Manual input for a field
  const handleManualInput = (field, value) => {
    setConfirmedValues(prev => ({
      ...prev,
      [field]: { value: parseFloat(value) || value, source: 'manual' }
    }));
  };

  // Step 7: Handle value confirmation
  const handleConfirmValue = (field, value, source) => {
    setConfirmedValues(prev => ({
      ...prev,
      [field]: { value, source }
    }));
  };

  // Step 8: Select scenario
  const handleSelectScenario = (scenarioType) => {
    setSelectedScenario(scenarioType);
    setCurrentStep(9);
  };

  // Step 9: Run valuation
  const handleRunValuation = async () => {
    setLoading(true);
    setError(null);
    try {
      console.log('Running valuation with:', {
        modelType: selectedModel,
        confirmedValues,
        scenario: selectedScenario
      });
      
      const response = await fetch('http://localhost:5000/api/run-valuation', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          modelType: selectedModel,
          confirmedValues,
          scenario: selectedScenario
        })
      });
      
      const data = await response.json();
      console.log('Valuation response:', data);
      
      if (data.success) {
        setValuationResults(data.data);
        setCurrentStep(10);
      } else {
        setError(data.error || 'Failed to run valuation');
      }
    } catch (err) {
      console.error('Valuation error:', err);
      setError('Failed to run valuation. Please ensure the backend server is running on port 5000.');
    } finally {
      setLoading(false);
    }
  };

  // Step 10: Reset
  const handleReset = () => {
    setCurrentStep(1);
    setSearchQuery('');
    setSearchResults([]);
    setSelectedCompany(null);
    setSelectedModel(null);
    setRequiredFields([]);
    setRetrievedData(null);
    setConfirmedValues({});
    setSelectedScenario(null);
    setValuationResults(null);
  };

  const renderStep = () => {
    switch (currentStep) {
      case 1:
        return (
          <div className="step-container">
            <h2>Step 1: Input Company Name or Ticker</h2>
            <div className="input-group">
              <input
                type="text"
                placeholder="Enter ticker (e.g., AAPL) or company name (e.g., Tesla)"
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
                  <div key={result.ticker} className="result-item">
                    <span>{result.name} ({result.ticker}) - {result.exchange}</span>
                    <button onClick={() => handleSelectCompany(result)} className="btn-secondary">
                      Select
                    </button>
                  </div>
                ))}
              </div>
            )}
            {error && <div className="error-message">{error}</div>}
          </div>
        );

      case 2:
        return (
          <div className="step-container">
            <h2>Step 2: Search Results</h2>
            {/* Combined with Step 1 for better UX */}
          </div>
        );

      case 3:
        return (
          <div className="step-container">
            <h2>Step 3: Company Selected</h2>
            <div className="confirmation-box">
              ✅ Selected: {selectedCompany?.name} ({selectedCompany?.ticker})
            </div>
            <button onClick={() => setCurrentStep(4)} className="btn-primary">
              Continue →
            </button>
          </div>
        );

      case 4:
        return (
          <div className="step-container">
            <h2>Step 4: Select Valuation Model</h2>
            <div className="model-options">
              {[
                { id: 'DCF', name: 'Discounted Cash Flow', desc: 'Intrinsic value based on projected free cash flows' },
                { id: 'COMPS', name: 'Trading Comps', desc: 'Relative valuation using peer company multiples' },
                { id: 'DUPONT', name: 'DuPont Analysis', desc: 'ROE decomposition into profit margin, asset turnover, and leverage' },
                { id: 'REALESTATE', name: 'Real Estate', desc: 'Property valuation using NOI and cap rates' }
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
            <h2>Step 5: Required Inputs Checklist</h2>
            <p className="step-description">Below are all the required inputs for the {selectedModel} model. Fields marked with ⚙️ require AI generation or manual input.</p>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Category</th>
                  <th>Field Name</th>
                  <th>Type</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {requiredFields.map((field, idx) => (
                  <tr key={idx}>
                    <td>{field.category || 'General'}</td>
                    <td>{field.name}</td>
                    <td>{field.requiresInput ? '⚙️ AI/Manual' : '📊 API Only'}</td>
                    <td className="status-pending">⏳ Pending Retrieval</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <button onClick={handleRetrieveData} disabled={loading} className="btn-primary">
              {loading ? 'Retrieving...' : 'Retrieve Data →'}
            </button>
          </div>
        );

      case 6:
        return (
          <div className="step-container">
            <h2>Step 6: Retrieving Data</h2>
            <div className="loading-spinner">Loading...</div>
          </div>
        );

      case 7:
        return (
          <div className="step-container">
            <h2>Step 7: Review Data + AI Suggestions</h2>
            <p className="step-description">
              <strong>📊 API Data:</strong> Read-only data pulled from financial APIs (Yahoo Finance, Alpha Vantage, etc.)<br/>
              <strong>🤖 AI Data:</strong> AI-generated forecasts and assumptions that can be auto-filled or manually edited
            </p>
            
            {/* Button to generate all AI data at once */}
            <button onClick={handleGenerateAllAI} className="btn-primary" style={{ marginBottom: '20px' }}>
              🤖 Generate All AI Data
            </button>
            
            {/* API Data Section - Read Only */}
            <h3>📊 API Data (Read-Only)</h3>
            <table className="data-table enhanced">
              <thead>
                <tr>
                  <th>Field</th>
                  <th>Value</th>
                  <th>Source</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {apiData && Object.entries(apiData).slice(0, 15).map(([key, data]) => (
                  <tr key={key}>
                    <td>{key}</td>
                    <td>{typeof data.value === 'number' ? data.value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 4 }) : data.value}</td>
                    <td>{data.source}</td>
                    <td>{data.status === 'found' ? '✓ Found' : '✗ Missing'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {Object.keys(apiData).length > 15 && (
              <p className="note">...and {Object.keys(apiData).length - 15} more API fields</p>
            )}
            
            {/* AI Data Section - Can be generated/edited */}
            <h3>🤖 AI-Generated Data (Editable)</h3>
            <table className="data-table enhanced">
              <thead>
                <tr>
                  <th>Field</th>
                  <th>AI Value</th>
                  <th>Confidence</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {aiData && Object.entries(aiData).map(([key, data]) => {
                  const isConfirmed = confirmedValues[key];
                  return (
                    <tr key={key}>
                      <td>{key}</td>
                      <td>{typeof data.value === 'number' ? (data.value * 100).toFixed(2) + '%' : data.value}</td>
                      <td>{data.confidence ? (data.confidence * 100).toFixed(0) + '%' : 'N/A'}</td>
                      <td>
                        {!isConfirmed ? (
                          <>
                            <button onClick={() => handleGenerateAI(key, 'aiData')} className="btn-small">🤖 Use AI</button>
                            <input 
                              type="number" 
                              placeholder="Manual input" 
                              onChange={(e) => handleManualInput(key, e.target.value)}
                              className="manual-input"
                              style={{ width: '100px', marginLeft: '5px' }}
                            />
                          </>
                        ) : (
                          <span className="status-confirmed">✓ Confirmed ({isConfirmed.source})</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            
            {/* Model-specific AI data sections */}
            {retrievedData?.compsData && (
              <>
                <h3>📈 COMPS-Specific AI Data</h3>
                <table className="data-table enhanced">
                  <thead>
                    <tr>
                      <th>Field</th>
                      <th>AI Value</th>
                      <th>Confidence</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(retrievedData.compsData).map(([key, data]) => {
                      const isConfirmed = confirmedValues[key];
                      return (
                        <tr key={key}>
                          <td>{key}</td>
                          <td>{typeof data.value === 'number' ? data.value.toFixed(2) : data.value}</td>
                          <td>{data.confidence ? (data.confidence * 100).toFixed(0) + '%' : 'N/A'}</td>
                          <td>
                            {!isConfirmed ? (
                              <button onClick={() => handleGenerateAI(key, 'compsData')} className="btn-small">🤖 Use AI</button>
                            ) : (
                              <span className="status-confirmed">✓ Confirmed ({isConfirmed.source})</span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </>
            )}
            
            {retrievedData?.dupontData && (
              <>
                <h3>📊 DuPont-Specific AI Data</h3>
                <table className="data-table enhanced">
                  <thead>
                    <tr>
                      <th>Field</th>
                      <th>AI Value</th>
                      <th>Confidence</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(retrievedData.dupontData).map(([key, data]) => {
                      const isConfirmed = confirmedValues[key];
                      return (
                        <tr key={key}>
                          <td>{key}</td>
                          <td>{typeof data.value === 'number' ? data.value.toFixed(2) : data.value}</td>
                          <td>{data.confidence ? (data.confidence * 100).toFixed(0) + '%' : 'N/A'}</td>
                          <td>
                            {!isConfirmed ? (
                              <button onClick={() => handleGenerateAI(key, 'dupontData')} className="btn-small">🤖 Use AI</button>
                            ) : (
                              <span className="status-confirmed">✓ Confirmed ({isConfirmed.source})</span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </>
            )}
            
            {retrievedData?.realEstateData && (
              <>
                <h3>🏢 Real Estate-Specific Data</h3>
                <table className="data-table enhanced">
                  <thead>
                    <tr>
                      <th>Field</th>
                      <th>Value</th>
                      <th>Editable</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(retrievedData.realEstateData).map(([key, data]) => {
                      const isConfirmed = confirmedValues[key];
                      return (
                        <tr key={key}>
                          <td>{key}</td>
                          <td>{typeof data.value === 'number' ? data.value.toLocaleString() : data.value}</td>
                          <td>{data.editable ? '✏️ Yes' : '🔒 No'}</td>
                          <td>
                            {data.editable && !isConfirmed ? (
                              <button onClick={() => handleGenerateAI(key, 'realEstateData')} className="btn-small">🤖 Use AI</button>
                            ) : isConfirmed ? (
                              <span className="status-confirmed">✓ Confirmed ({isConfirmed.source})</span>
                            ) : (
                              <span className="status-readonly">Read-only</span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </>
            )}
            
            <button 
              onClick={() => setCurrentStep(8)} 
              className="btn-primary"
              disabled={Object.keys(confirmedValues).length === 0}
              style={{ marginTop: '20px' }}
            >
              Review Assumptions →
            </button>
          </div>
        );

      case 8:
        return (
          <div className="step-container">
            <h2>Step 8: Select or Customize Assumption Scenarios</h2>
            <div className="scenario-options">
              <div className="scenario-card" onClick={() => handleSelectScenario('best')}>
                <h3>🚀 Best Case</h3>
                <p>Optimistic assumptions based on management guidance</p>
              </div>
              <div className="scenario-card" onClick={() => handleSelectScenario('base')}>
                <h3>📊 Base Case</h3>
                <p>Most likely scenario based on consensus estimates</p>
              </div>
              <div className="scenario-card" onClick={() => handleSelectScenario('worst')}>
                <h3>⚠️ Worst Case</h3>
                <p>Conservative assumptions considering downside risks</p>
              </div>
            </div>
          </div>
        );

      case 9:
        return (
          <div className="step-container">
            <h2>Step 9: Confirm & Run Valuation Model</h2>
            <div className="summary-box">
              <h3>Configuration Summary</h3>
              <p><strong>Company:</strong> {selectedCompany?.name} ({selectedCompany?.ticker})</p>
              <p><strong>Model:</strong> {selectedModel}</p>
              <p><strong>Scenario:</strong> {selectedScenario}</p>
              <p><strong>Confirmed Values:</strong> {Object.keys(confirmedValues).length} fields</p>
            </div>
            
            {/* Display confirmed values summary */}
            {Object.keys(confirmedValues).length > 0 && (
              <div className="confirmed-values-summary">
                <h4>Confirmed Inputs</h4>
                <table className="data-table small">
                  <thead>
                    <tr>
                      <th>Field</th>
                      <th>Value</th>
                      <th>Source</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(confirmedValues).slice(0, 10).map(([key, data]) => (
                      <tr key={key}>
                        <td>{key}</td>
                        <td>{typeof data.value === 'number' ? data.value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 4 }) : data.value}</td>
                        <td>{data.source === 'ai' ? '🤖 AI' : data.source === 'manual' ? '✏️ Manual' : '📊 API'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {Object.keys(confirmedValues).length > 10 && (
                  <p className="note">...and {Object.keys(confirmedValues).length - 10} more fields</p>
                )}
              </div>
            )}
            
            {error && <div className="error-message">{error}</div>}
            
            <button onClick={handleRunValuation} disabled={loading || Object.keys(confirmedValues).length === 0} className="btn-primary btn-large">
              {loading ? 'Running Model...' : '🚀 Run Valuation Model →'}
            </button>
          </div>
        );

      case 10:
        return (
          <div className="step-container results">
            <h2>Step 10: Valuation Results</h2>
            {valuationResults && (
              <div className="results-dashboard">
                <div className="primary-result">
                  <h3>Primary Result</h3>
                  <div className="result-highlight">
                    <span className="label">Implied Share Price:</span>
                    <span className="value">${valuationResults.primaryResult.impliedSharePrice.toFixed(2)}</span>
                  </div>
                  <div className="result-highlight">
                    <span className="label">Current Price:</span>
                    <span className="value">${valuationResults.primaryResult.currentValue.toFixed(2)}</span>
                  </div>
                  <div className={`result-highlight ${valuationResults.primaryResult.upside >= 0 ? 'positive' : 'negative'}`}>
                    <span className="label">Upside/(Downside):</span>
                    <span className="value">{(valuationResults.primaryResult.upside * 100).toFixed(1)}%</span>
                  </div>
                  <div className="recommendation">
                    Recommendation: <strong>{valuationResults.primaryResult.recommendation}</strong>
                  </div>
                </div>

                <div className="scenario-comparison">
                  <h3>Scenario Comparison</h3>
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Scenario</th>
                        <th>Implied Price</th>
                        <th>Upside/(Downside)</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(valuationResults.scenarioComparison).map(([key, data]) => (
                        <tr key={key}>
                          <td>{key.toUpperCase()}</td>
                          <td>${data.impliedSharePrice.toFixed(2)}</td>
                          <td className={data.upside >= 0 ? 'positive' : 'negative'}>
                            {(data.upside * 100).toFixed(1)}%
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                <div className="audit-trail">
                  <h3>Audit Trail</h3>
                  <p><strong>Data Sources:</strong></p>
                  <ul>
                    <li>✅ API: {valuationResults.auditTrail.dataSources.api.join(', ')}</li>
                    <li>🤖 AI: {valuationResults.auditTrail.dataSources.ai.join(', ')}</li>
                  </ul>
                  <p><strong>Overall Confidence Score:</strong> {(valuationResults.auditTrail.confidenceScores.overall * 100).toFixed(0)}%</p>
                </div>

                <button onClick={handleReset} className="btn-secondary">
                  🔄 New Valuation
                </button>
              </div>
            )}
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="valuation-flow-app">
      <header className="app-header">
        <h1>🔢 Financial Valuation Tool</h1>
        <div className="progress-indicator">
          {Array.from({ length: 10 }, (_, i) => (
            <div 
              key={i} 
              className={`step-dot ${i + 1 <= currentStep ? 'active' : ''}`}
              title={`Step ${i + 1}`}
            />
          ))}
        </div>
        <span className="step-label">Step {currentStep} of 10</span>
      </header>
      <main className="app-main">
        {renderStep()}
      </main>
      <footer className="app-footer">
        <p>10-Step Valuation Flow | DCF | Trading Comps | DuPont Analysis | Real Estate</p>
      </footer>
    </div>
  );
};

export default ValuationFlow;
