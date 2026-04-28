import React, { useState, useEffect, useCallback } from 'react';
import { searchCompanies, selectCompany, selectModels, prepareInputs, fetchData, generateAI, confirmAssumptions, runValuation } from '../services/api';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, AreaChart, Area, ComposedChart, Scatter } from 'recharts';

const ValuationFlow = () => {
  // State Management
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
  
  // New states for enhanced data
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

  // Step 1: Search Company
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

  // Step 3: Select Company
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

  // Step 4: Select Model
  const handleSelectModel = useCallback(async (modelType) => {
    setSelectedModel(modelType);
    setLoading(true);
    try {
      const data = await selectModels(sessionId, modelType);
      console.log('Select model response:', data);
      if (data.message) {
        setCurrentStep(5);
        // Fetch required inputs
        await fetchRequiredInputs();
      }
    } catch (err) {
      console.error('Select model error:', err);
      setError('Failed to select model');
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  // Go back to model selection (Step 4)
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

  // Fetch Required Inputs
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

  // Step 7-8: Retrieve Data (API + AI)
  const handleRetrieveData = useCallback(async () => {
    setLoading(true);
    try {
      // Fetch API data
      const fetchDataResponse = await fetchData(sessionId);
      console.log('Fetch data response:', fetchDataResponse);
      
      // Fetch AI suggestions
      const aiDataResponse = await generateAI(sessionId);
      console.log('AI response:', aiDataResponse);
      
      if (fetchDataResponse.data && aiDataResponse.suggestions) {
        setAiData(aiDataResponse.suggestions);
        
        // Extract model-specific data
        if (fetchDataResponse.data.historical_financials) {
          setHistoricalData(fetchDataResponse.data.historical_financials);
        }
        if (fetchDataResponse.data.forecast_drivers) {
          setForecastDrivers(fetchDataResponse.data.forecast_drivers);
        }
        if (fetchDataResponse.data.peers) {
          setPeerData(fetchDataResponse.data.peers);
        }
        if (fetchDataResponse.data.dcf_inputs) {
          setDcfInputs(fetchDataResponse.data.dcf_inputs);
        }
        if (fetchDataResponse.data.dupont_ratios) {
          setDupontResults(fetchDataResponse.data.dupont_ratios);
        }
        if (fetchDataResponse.data.comps_results) {
          setCompsResults(fetchDataResponse.data.comps_results);
        }
        
        setCurrentStep(8);
      }
    } catch (err) {
      console.error('Retrieve data error:', err);
      setError('Failed to retrieve data');
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  // Auto-fill AI Values
  const handleGenerateAllAI = () => {
    const newConfirmed = { ...confirmedValues };
    
    // DCF fields
    if (aiData.wacc !== undefined) {
      newConfirmed.wacc = { value: aiData.wacc, source: 'ai', confidence: 0.8 };
    }
    if (aiData.terminal_growth !== undefined) {
      newConfirmed.terminal_growth = { value: aiData.terminal_growth, source: 'ai', confidence: 0.7 };
    }
    if (aiData.revenue_growth_forecast) {
      newConfirmed.revenue_growth_forecast = { 
        value: aiData.revenue_growth_forecast, 
        source: 'ai', 
        confidence: 0.75 
      };
    }
    if (aiData.ebitda_margin_forecast) {
      newConfirmed.ebitda_margin_forecast = { 
        value: aiData.ebitda_margin_forecast, 
        source: 'ai', 
        confidence: 0.7 
      };
    }
    if (aiData.capex_percent_revenue) {
      newConfirmed.capex_percent_revenue = { 
        value: aiData.capex_percent_revenue, 
        source: 'ai', 
        confidence: 0.7 
      };
    }
    
    // Comps fields
    if (aiData.terminal_ebitda_multiple !== undefined) {
      newConfirmed.terminal_ebitda_multiple = { 
        value: aiData.terminal_ebitda_multiple, 
        source: 'ai', 
        confidence: 0.75 
      };
    }
    
    setConfirmedValues(newConfirmed);
  };

  // Manual Input Handler
  const handleManualInput = (field, value) => {
    let parsedValue = value;
    
    // Parse array inputs (e.g., "0.05, 0.04, 0.03")
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

  // Step 10: Confirm Assumptions
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

  // Step 11-12: Run Valuation
  const handleRunValuation = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await runValuation(sessionId, selectedModel, selectedScenario);
      console.log('Valuation response:', data);
      
      if (data.result) {
        setValuationResults(data.result);
        
        // Extract model-specific results
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

  // Reset All
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

  // Render Functions for Each Step
  const renderStep1 = () => (
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

  const renderStep4 = () => (
    <div className="step-container">
      <h2>Step 4: Select Valuation Model</h2>
      <div className="model-options">
        {[
          { id: 'DCF', name: 'Discounted Cash Flow', desc: 'Intrinsic value based on projected free cash flows. Requires 3-year historical data + 6-period forecast.' },
          { id: 'DuPont', name: 'DuPont Analysis', desc: 'ROE decomposition into margins, turnover, and leverage. Analyzes 3-5 years of trends.' },
          { id: 'COMPS', name: 'Trading Comps', desc: 'Relative valuation using peer multiples. Automatically fetches 5+ comparable companies.' }
        ].map((model) => (
          <div key={model.id} className="model-card" onClick={() => handleSelectModel(model.id)}>
            <h3>{model.name}</h3>
            <p>{model.desc}</p>
          </div>
        ))}
      </div>
    </div>
  );

  const renderStep5 = () => (
    <div className="step-container">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h2>Step 5: Required Inputs</h2>
        <button onClick={handleBackToModelSelection} className="btn-secondary">← Change Model</button>
      </div>
      <div className="summary-box">
        <h3>Data Requirements by Model</h3>
        {selectedModel === 'DCF' && (
          <>
            <p><strong>Historical:</strong> 3 most recent fiscal years (FY-3, FY-2, FY-1)</p>
            <p><strong>Forecast:</strong> 6 periods (Year 1-5 + Terminal)</p>
            <p><strong>Key Drivers:</strong> Revenue growth, EBITDA margin, CapEx %, Working capital days, Tax rate</p>
          </>
        )}
        {selectedModel === 'DuPont' && (
          <>
            <p><strong>Historical:</strong> 3-5 years of P&L and Balance Sheet data</p>
            <p><strong>Ratios:</strong> Net margin, Asset turnover, Equity multiplier</p>
          </>
        )}
        {selectedModel === 'COMPS' && (
          <>
            <p><strong>Target:</strong> LTM financials for multiple calculation</p>
            <p><strong>Peers:</strong> Minimum 5 comparable companies auto-selected</p>
            <p><strong>Multiples:</strong> EV/EBITDA, EV/Sales, P/E, P/B, EV/FCF</p>
          </>
        )}
      </div>
      <table className="data-table">
        <thead>
          <tr>
            <th>Category</th>
            <th>Field</th>
            <th>Type</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {requiredFields.map((field, idx) => (
            <tr key={idx}>
              <td>{field.category || 'General'}</td>
              <td>{field.name}</td>
              <td>{field.requiresInput ? 'AI/Manual' : 'API Only'}</td>
              <td className="status-pending">Pending</td>
            </tr>
          ))}
        </tbody>
      </table>
      <button onClick={handleRetrieveData} disabled={loading} className="btn-primary btn-large">
        {loading ? 'Retrieving...' : 'Retrieve Data & Generate AI Suggestions'}
      </button>
    </div>
  );

  const renderStep8 = () => {
    // Helper function to prepare historical revenue data for charts
    const prepareHistoricalChartData = () => {
      if (!historicalData || !historicalData.financials) return [];
      const years = historicalData.financials.years || [];
      const revenues = historicalData.financials.revenue || [];
      return years.map((year, idx) => ({
        year,
        revenue: revenues[idx] || 0,
        formattedRevenue: revenues[idx] ? `$${(revenues[idx] / 1000).toFixed(1)}B` : 'N/A'
      }));
    };

    // Helper function to prepare forecast comparison data
    const prepareForecastComparisonData = () => {
      if (!aiData.revenue_growth_forecast || !historicalData) return [];
      const periods = aiData.revenue_growth_forecast.length;
      const baseRevenue = historicalData.financials?.revenue?.[historicalData.financials.revenue.length - 1] || 1000;
      let cumulativeRevenue = baseRevenue;
      
      return aiData.revenue_growth_forecast.map((growth, idx) => {
        cumulativeRevenue = cumulativeRevenue * (1 + growth);
        return {
          period: `Year ${idx + 1}`,
          growthRate: (growth * 100).toFixed(1),
          projectedRevenue: Math.round(cumulativeRevenue),
          formattedRevenue: `$${(cumulativeRevenue / 1000).toFixed(1)}B`
        };
      });
    };

    // Helper function to prepare EBITDA margin trend data
    const prepareEbitdaTrendData = () => {
      if (!historicalData || !aiData.ebitda_margin_forecast) return [];
      const historicalMargins = historicalData.ebitda_margins || [];
      const forecastMargins = aiData.ebitda_margin_forecast || [];
      const data = [];
      
      // Add historical margins
      if (historicalData.financials?.years) {
        historicalData.financials.years.forEach((year, idx) => {
          data.push({
            period: year.toString(),
            margin: historicalMargins[idx] ? (historicalMargins[idx] * 100).toFixed(1) : null,
            type: 'Historical',
            isHistorical: true
          });
        });
      }
      
      // Add forecast margins
      forecastMargins.forEach((margin, idx) => {
        data.push({
          period: `Y${idx + 1}`,
          margin: (margin * 100).toFixed(1),
          type: 'Forecast',
          isHistorical: false
        });
      });
      
      return data;
    };

    const historicalChartData = prepareHistoricalChartData();
    const forecastComparisonData = prepareForecastComparisonData();
    const ebitdaTrendData = prepareEbitdaTrendData();
    
    return (
    <div className="step-container">
      <h2>Step 8: Review & Confirm Assumptions</h2>
      
      {/* Benchmark Summary */}
      {historicalData && (
        <div className="summary-box">
          <h3>Historical Trends (Last 3 Years)</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px' }}>
            <div>
              <strong>Revenue CAGR:</strong>
              <p>{historicalData.revenue_cagr ? (historicalData.revenue_cagr * 100).toFixed(1) + '%' : 'N/A'}</p>
            </div>
            <div>
              <strong>Avg EBITDA Margin:</strong>
              <p>{historicalData.avg_ebitda_margin ? (historicalData.avg_ebitda_margin * 100).toFixed(1) + '%' : 'N/A'}</p>
            </div>
            <div>
              <strong>Avg ROE:</strong>
              <p>{historicalData.avg_roe ? (historicalData.avg_roe * 100).toFixed(1) + '%' : 'N/A'}</p>
            </div>
          </div>
          
          {/* Historical Revenue Chart */}
          {historicalChartData.length > 0 && (
            <div style={{ marginTop: '24px' }}>
              <h4 style={{ marginBottom: '12px', color: '#333' }}>Revenue Trend</h4>
              <ResponsiveContainer width="100%" height={250}>
                <AreaChart data={historicalChartData}>
                  <defs>
                    <linearGradient id="colorRevenue" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#667eea" stopOpacity={0.8}/>
                      <stop offset="95%" stopColor="#667eea" stopOpacity={0.1}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
                  <XAxis dataKey="year" stroke="#666" />
                  <YAxis stroke="#666" tickFormatter={(value) => `$${(value/1000).toFixed(0)}B`} />
                  <Tooltip 
                    formatter={(value) => [`$${(value/1000).toFixed(1)}B`, 'Revenue']}
                    contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}
                  />
                  <Area type="monotone" dataKey="revenue" stroke="#667eea" fillOpacity={1} fill="url(#colorRevenue)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      )}
      
      {peerData.length > 0 && (
        <div className="summary-box">
          <h3>Peer Benchmarking</h3>
          <p><strong>Peers Analyzed:</strong> {peerData.length} companies</p>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px', marginTop: '12px' }}>
            <div>
              <strong>Median EV/EBITDA:</strong>
              <p>{peerData.median_ev_ebitda ? peerData.median_ev_ebitda.toFixed(1) + 'x' : 'N/A'}</p>
            </div>
            <div>
              <strong>Median P/E:</strong>
              <p>{peerData.median_pe ? peerData.median_pe.toFixed(1) + 'x' : 'N/A'}</p>
            </div>
            <div>
              <strong>Peer Growth Avg:</strong>
              <p>{peerData.avg_revenue_growth ? (peerData.avg_revenue_growth * 100).toFixed(1) + '%' : 'N/A'}</p>
            </div>
          </div>
        </div>
      )}
      
      {/* AI Suggestion Visualizations */}
      {aiData && Object.keys(aiData).length > 0 && (
        <div className="summary-box" style={{ background: 'linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%)' }}>
          <h3 style={{ color: '#667eea' }}>🤖 AI Suggestions with Rationale</h3>
          <p style={{ marginBottom: '20px', color: '#666' }}>AI analyzes historical trends, peer benchmarks, and market conditions to provide data-driven recommendations</p>
          
          {/* Revenue Growth Forecast Visualization */}
          {forecastComparisonData.length > 0 && (
            <div style={{ marginBottom: '32px' }}>
              <h4 style={{ marginBottom: '12px', color: '#333' }}>
                📈 Revenue Growth Forecast vs Historical
                {aiData.revenue_growth_rationale && (
                  <span style={{ display: 'block', fontSize: '13px', fontWeight: 'normal', color: '#666', marginTop: '6px' }}>
                    💡 <strong>AI Reasoning:</strong> {aiData.revenue_growth_rationale}
                  </span>
                )}
              </h4>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
                <ResponsiveContainer width="100%" height={280}>
                  <ComposedChart data={forecastComparisonData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
                    <XAxis dataKey="period" stroke="#666" />
                    <YAxis yAxisId="left" stroke="#667eea" label={{ value: 'Growth Rate (%)', angle: -90, position: 'insideLeft' }} />
                    <YAxis yAxisId="right" orientation="right" stroke="#764ba2" label={{ value: 'Revenue ($B)', angle: 90, position: 'insideRight' }} />
                    <Tooltip 
                      formatter={(value, name) => {
                        if (name === 'Growth Rate') return [`${value}%`, 'Growth Rate'];
                        return [`$${(value/1000).toFixed(1)}B`, 'Projected Revenue'];
                      }}
                      contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}
                    />
                    <Legend />
                    <Bar yAxisId="left" dataKey="growthRate" fill="#667eea" name="Growth Rate (%)" barSize={30} />
                    <Line yAxisId="right" type="monotone" dataKey="projectedRevenue" stroke="#764ba2" strokeWidth={3} name="Projected Revenue" dot={{ r: 5 }} />
                  </ComposedChart>
                </ResponsiveContainer>
                
                <div style={{ padding: '16px', background: 'white', borderRadius: '8px' }}>
                  <h5 style={{ marginBottom: '12px', color: '#333' }}>Key Metrics</h5>
                  <div style={{ marginBottom: '12px' }}>
                    <strong style={{ color: '#666' }}>Avg Forecast Growth:</strong>
                    <p style={{ fontSize: '24px', color: '#667eea', fontWeight: 'bold' }}>
                      {(forecastComparisonData.reduce((sum, d) => sum + parseFloat(d.growthRate), 0) / forecastComparisonData.length).toFixed(1)}%
                    </p>
                  </div>
                  <div style={{ marginBottom: '12px' }}>
                    <strong style={{ color: '#666' }}>Final Year Revenue:</strong>
                    <p style={{ fontSize: '24px', color: '#764ba2', fontWeight: 'bold' }}>
                      {forecastComparisonData[forecastComparisonData.length - 1]?.formattedRevenue}
                    </p>
                  </div>
                  <div>
                    <strong style={{ color: '#666' }}>Trend:</strong>
                    <p style={{ fontSize: '16px', color: forecastComparisonData[0]?.growthRate > forecastComparisonData[forecastComparisonData.length - 1]?.growthRate ? '#28a745' : '#dc3545', fontWeight: 'bold' }}>
                      {forecastComparisonData[0]?.growthRate > forecastComparisonData[forecastComparisonData.length - 1]?.growthRate 
                        ? '📉 Decelerating (conservative approach)' 
                        : '📈 Accelerating (optimistic outlook)'}
                    </p>
                  </div>
                  {aiData.revenue_growth_sources && (
                    <div style={{ marginTop: '16px', paddingTop: '12px', borderTop: '1px solid #e0e0e0' }}>
                      <strong style={{ color: '#666', fontSize: '12px' }}>📊 Data Sources:</strong>
                      <p style={{ fontSize: '12px', color: '#888' }}>{aiData.revenue_growth_sources}</p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
          
          {/* EBITDA Margin Trend Visualization */}
          {ebitdaTrendData.length > 0 && (
            <div style={{ marginBottom: '32px' }}>
              <h4 style={{ marginBottom: '12px', color: '#333' }}>
                💰 EBITDA Margin Trend (Historical → Forecast)
                {aiData.ebitda_margin_rationale && (
                  <span style={{ display: 'block', fontSize: '13px', fontWeight: 'normal', color: '#666', marginTop: '6px' }}>
                    💡 <strong>AI Reasoning:</strong> {aiData.ebitda_margin_rationale}
                  </span>
                )}
              </h4>
              <ResponsiveContainer width="100%" height={280}>
                <LineChart data={ebitdaTrendData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
                  <XAxis dataKey="period" stroke="#666" />
                  <YAxis stroke="#666" label={{ value: 'Margin (%)', angle: -90, position: 'insideLeft' }} />
                  <Tooltip 
                    formatter={(value) => [`${value}%`, 'EBITDA Margin']}
                    contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}
                  />
                  <Legend />
                  <Line 
                    type="monotone" 
                    dataKey="margin" 
                    stroke="#28a745" 
                    strokeWidth={3} 
                    dot={(props) => {
                      const { cx, cy, payload } = props;
                      const color = payload.isHistorical ? '#667eea' : '#764ba2';
                      return <circle cx={cx} cy={cy} r={6} fill={color} stroke="white" strokeWidth={2} />;
                    }}
                    name="EBITDA Margin %"
                  />
                </LineChart>
              </ResponsiveContainer>
              <div style={{ display: 'flex', gap: '24px', marginTop: '12px', justifyContent: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <div style={{ width: '12px', height: '12px', borderRadius: '50%', background: '#667eea' }}></div>
                  <span style={{ fontSize: '13px', color: '#666' }}>Historical</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <div style={{ width: '12px', height: '12px', borderRadius: '50%', background: '#764ba2' }}></div>
                  <span style={{ fontSize: '13px', color: '#666' }}>AI Forecast</span>
                </div>
              </div>
              {aiData.ebitda_margin_sources && (
                <div style={{ marginTop: '12px', textAlign: 'center' }}>
                  <strong style={{ color: '#666', fontSize: '12px' }}>📊 Data Sources:</strong>
                  <span style={{ fontSize: '12px', color: '#888', marginLeft: '8px' }}>{aiData.ebitda_margin_sources}</span>
                </div>
              )}
            </div>
          )}
          
          {/* WACC Breakdown */}
          {aiData.wacc && (
            <div style={{ marginBottom: '32px' }}>
              <h4 style={{ marginBottom: '12px', color: '#333' }}>
                🎯 WACC (Weighted Average Cost of Capital)
                {aiData.wacc_rationale && (
                  <span style={{ display: 'block', fontSize: '13px', fontWeight: 'normal', color: '#666', marginTop: '6px' }}>
                    💡 <strong>AI Reasoning:</strong> {aiData.wacc_rationale}
                  </span>
                )}
              </h4>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px' }}>
                <div style={{ padding: '16px', background: 'white', borderRadius: '8px', textAlign: 'center' }}>
                  <div style={{ fontSize: '32px', fontWeight: 'bold', color: '#667eea' }}>
                    {(aiData.wacc * 100).toFixed(2)}%
                  </div>
                  <div style={{ fontSize: '13px', color: '#666', marginTop: '8px' }}>WACC</div>
                </div>
                <div style={{ padding: '16px', background: 'white', borderRadius: '8px', textAlign: 'center' }}>
                  <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#28a745' }}>
                    {aiData.risk_free_rate ? (aiData.risk_free_rate * 100).toFixed(2) + '%' : 'N/A'}
                  </div>
                  <div style={{ fontSize: '13px', color: '#666', marginTop: '8px' }}>Risk-Free Rate</div>
                </div>
                <div style={{ padding: '16px', background: 'white', borderRadius: '8px', textAlign: 'center' }}>
                  <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#ffc107' }}>
                    {aiData.beta ? aiData.beta.toFixed(2) : 'N/A'}
                  </div>
                  <div style={{ fontSize: '13px', color: '#666', marginTop: '8px' }}>Beta</div>
                </div>
                <div style={{ padding: '16px', background: 'white', borderRadius: '8px', textAlign: 'center' }}>
                  <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#dc3545' }}>
                    {aiData.market_risk_premium ? (aiData.market_risk_premium * 100).toFixed(2) + '%' : 'N/A'}
                  </div>
                  <div style={{ fontSize: '13px', color: '#666', marginTop: '8px' }}>Market Risk Premium</div>
                </div>
              </div>
              {aiData.wacc_sources && (
                <div style={{ marginTop: '12px', textAlign: 'center' }}>
                  <strong style={{ color: '#666', fontSize: '12px' }}>📊 Data Sources:</strong>
                  <span style={{ fontSize: '12px', color: '#888', marginLeft: '8px' }}>{aiData.wacc_sources}</span>
                </div>
              )}
            </div>
          )}
          
          {/* Terminal Value Assumptions */}
          {aiData.terminal_growth && (
            <div style={{ marginBottom: '32px' }}>
              <h4 style={{ marginBottom: '12px', color: '#333' }}>
                🔮 Terminal Value Assumptions
                {aiData.terminal_growth_rationale && (
                  <span style={{ display: 'block', fontSize: '13px', fontWeight: 'normal', color: '#666', marginTop: '6px' }}>
                    💡 <strong>AI Reasoning:</strong> {aiData.terminal_growth_rationale}
                  </span>
                )}
              </h4>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                <div style={{ padding: '20px', background: 'white', borderRadius: '8px' }}>
                  <div style={{ fontSize: '14px', color: '#666', marginBottom: '8px' }}>Terminal Growth Rate</div>
                  <div style={{ fontSize: '36px', fontWeight: 'bold', color: '#764ba2' }}>
                    {(aiData.terminal_growth * 100).toFixed(2)}%
                  </div>
                  <div style={{ fontSize: '12px', color: '#888', marginTop: '8px' }}>
                    Perpetual growth rate for terminal value calculation
                  </div>
                </div>
                <div style={{ padding: '20px', background: 'white', borderRadius: '8px' }}>
                  <div style={{ fontSize: '14px', color: '#666', marginBottom: '8px' }}>Terminal EBITDA Multiple</div>
                  <div style={{ fontSize: '36px', fontWeight: 'bold', color: '#667eea' }}>
                    {aiData.terminal_ebitda_multiple ? aiData.terminal_ebitda_multiple.toFixed(1) + 'x' : 'N/A'}
                  </div>
                  <div style={{ fontSize: '12px', color: '#888', marginTop: '8px' }}>
                    Exit multiple based on peer analysis
                  </div>
                </div>
              </div>
              {aiData.terminal_growth_sources && (
                <div style={{ marginTop: '12px', textAlign: 'center' }}>
                  <strong style={{ color: '#666', fontSize: '12px' }}>📊 Data Sources:</strong>
                  <span style={{ fontSize: '12px', color: '#888', marginLeft: '8px' }}>{aiData.terminal_growth_sources}</span>
                </div>
              )}
            </div>
          )}
        </div>
      )}
      
      <button onClick={handleGenerateAllAI} className="btn-primary" style={{ marginBottom: '20px' }}>
        Auto-Fill All AI Values
      </button>
      
      <table className="data-table enhanced">
        <thead>
          <tr>
            <th>Field</th>
            <th>AI Suggestion</th>
            <th>Rationale & Sources</th>
            <th>Your Input</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          {/* DCF Fields */}
          {(selectedModel === 'DCF' || !selectedModel) && (
            <>
              <tr>
                <td>WACC</td>
                <td>{aiData.wacc ? (aiData.wacc * 100).toFixed(2) + '%' : 'N/A'}</td>
                <td className="rationale-cell">
                  {aiData.wacc_rationale ? (
                    <div className="rationale-content">
                      <p><strong>Why:</strong> {aiData.wacc_rationale}</p>
                      <p><strong>Sources:</strong> {aiData.wacc_sources || 'CAPM Formula'}</p>
                    </div>
                  ) : 'AI explanation will appear here'}
                </td>
                <td>
                  <input 
                    type="number" 
                    step="0.001" 
                    placeholder="Enter WACC (e.g., 0.085)" 
                    onChange={(e) => handleManualInput('wacc', e.target.value)} 
                    className="manual-input" 
                  />
                </td>
                <td>
                  {!confirmedValues.wacc ? (
                    <button onClick={() => handleManualInput('wacc', aiData.wacc)} className="btn-small">Use AI</button>
                  ) : (
                    <span className="positive">✓ Confirmed</span>
                  )}
                </td>
              </tr>
              <tr>
                <td>Terminal Growth Rate</td>
                <td>{aiData.terminal_growth ? (aiData.terminal_growth * 100).toFixed(2) + '%' : 'N/A'}</td>
                <td className="rationale-cell">
                  {aiData.terminal_growth_rationale ? (
                    <div className="rationale-content">
                      <p><strong>Why:</strong> {aiData.terminal_growth_rationale}</p>
                      <p><strong>Sources:</strong> {aiData.terminal_growth_sources || 'Historical GDP'}</p>
                    </div>
                  ) : 'AI explanation will appear here'}
                </td>
                <td>
                  <input 
                    type="number" 
                    step="0.001" 
                    placeholder="Enter terminal growth (e.g., 0.02)" 
                    onChange={(e) => handleManualInput('terminal_growth', e.target.value)} 
                    className="manual-input" 
                  />
                </td>
                <td>
                  {!confirmedValues.terminal_growth ? (
                    <button onClick={() => handleManualInput('terminal_growth', aiData.terminal_growth)} className="btn-small">Use AI</button>
                  ) : (
                    <span className="positive">✓ Confirmed</span>
                  )}
                </td>
              </tr>
              <tr>
                <td>Terminal EBITDA Multiple</td>
                <td>{aiData.terminal_ebitda_multiple ? aiData.terminal_ebitda_multiple.toFixed(1) + 'x' : 'N/A'}</td>
                <td className="rationale-cell">
                  {aiData.terminal_ebitda_multiple_rationale ? (
                    <div className="rationale-content">
                      <p><strong>Why:</strong> {aiData.terminal_ebitda_multiple_rationale}</p>
                      <p><strong>Sources:</strong> {aiData.terminal_ebitda_multiple_sources || 'Peer Average'}</p>
                    </div>
                  ) : 'AI explanation will appear here'}
                </td>
                <td>
                  <input 
                    type="number" 
                    step="0.1" 
                    placeholder="Enter multiple (e.g., 8.0)" 
                    onChange={(e) => handleManualInput('terminal_ebitda_multiple', e.target.value)} 
                    className="manual-input" 
                  />
                </td>
                <td>
                  {!confirmedValues.terminal_ebitda_multiple ? (
                    <button onClick={() => handleManualInput('terminal_ebitda_multiple', aiData.terminal_ebitda_multiple)} className="btn-small">Use AI</button>
                  ) : (
                    <span className="positive">✓ Confirmed</span>
                  )}
                </td>
              </tr>
              <tr>
                <td>Revenue Growth Forecast (6 periods)</td>
                <td>
                  {aiData.revenue_growth_forecast 
                    ? aiData.revenue_growth_forecast.map(g => (g * 100).toFixed(1) + '%').join(', ') 
                    : 'N/A'}
                </td>
                <td className="rationale-cell">
                  {aiData.revenue_growth_rationale ? (
                    <div className="rationale-content">
                      <p><strong>Why:</strong> {aiData.revenue_growth_rationale}</p>
                      <p><strong>Sources:</strong> {aiData.revenue_growth_sources || 'Historical Trend'}</p>
                    </div>
                  ) : 'AI explanation will appear here'}
                </td>
                <td>
                  <input 
                    type="text" 
                    placeholder="e.g., 0.08, 0.06, 0.05, 0.04, 0.03, 0.02" 
                    onChange={(e) => handleManualInput('revenue_growth_forecast', e.target.value)} 
                    className="manual-input" 
                  />
                </td>
                <td>
                  {!confirmedValues.revenue_growth_forecast ? (
                    <button onClick={() => handleManualInput('revenue_growth_forecast', aiData.revenue_growth_forecast)} className="btn-small">Use AI</button>
                  ) : (
                    <span className="positive">✓ Confirmed</span>
                  )}
                </td>
              </tr>
              <tr>
                <td>EBITDA Margin Forecast (6 periods)</td>
                <td>
                  {aiData.ebitda_margin_forecast 
                    ? aiData.ebitda_margin_forecast.map(m => (m * 100).toFixed(1) + '%').join(', ') 
                    : 'N/A'}
                </td>
                <td className="rationale-cell">
                  {aiData.ebitda_margin_rationale ? (
                    <div className="rationale-content">
                      <p><strong>Why:</strong> {aiData.ebitda_margin_rationale}</p>
                      <p><strong>Sources:</strong> {aiData.ebitda_margin_sources || '3Y Average'}</p>
                    </div>
                  ) : 'AI explanation will appear here'}
                </td>
                <td>
                  <input 
                    type="text" 
                    placeholder="e.g., 0.15, 0.16, 0.17, 0.17, 0.17, 0.17" 
                    onChange={(e) => handleManualInput('ebitda_margin_forecast', e.target.value)} 
                    className="manual-input" 
                  />
                </td>
                <td>
                  {!confirmedValues.ebitda_margin_forecast ? (
                    <button onClick={() => handleManualInput('ebitda_margin_forecast', aiData.ebitda_margin_forecast)} className="btn-small">Use AI</button>
                  ) : (
                    <span className="positive">✓ Confirmed</span>
                  )}
                </td>
              </tr>
            </>
          )}
        </tbody>
      </table>
      
      <div style={{ marginTop: '20px' }}>
        <button onClick={handleConfirmAssumptions} disabled={loading} className="btn-primary btn-large">
          Confirm Assumptions & Proceed
        </button>
      </div>
    </div>
  );

  const renderStep9 = () => (
    <div className="step-container">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h2>Step 9: Run Valuation</h2>
        <button onClick={handleBackToModelSelection} className="btn-secondary">← Change Model</button>
      </div>
      <div className="summary-box">
        <h3>Configuration Summary</h3>
        <p><strong>Company:</strong> {selectedCompany?.name} ({selectedCompany?.symbol})</p>
        <p><strong>Model:</strong> {selectedModel === 'DCF' ? 'Discounted Cash Flow' : selectedModel === 'DuPont' ? 'DuPont Analysis' : 'Trading Comps'}</p>
        <p><strong>Scenario:</strong> {selectedScenario.replace('_', ' ').toUpperCase()}</p>
        <p><strong>Confirmed Inputs:</strong> {Object.keys(confirmedValues).length} fields</p>
      </div>
      <button onClick={handleRunValuation} disabled={loading} className="btn-primary btn-large">
        {loading ? 'Calculating...' : 'Run Valuation'}
      </button>
    </div>
  );

  const renderStep10 = () => {
    if (!valuationResults) return null;
    
    // Helper to prepare FCF projection data for DCF charts
    const prepareFcfChartData = () => {
      if (!valuationResults.dcf_outputs?.free_cash_flows) return [];
      const fcfArray = valuationResults.dcf_outputs.free_cash_flows;
      return fcfArray.map((fcf, idx) => ({
        period: idx === fcfArray.length - 1 ? 'Terminal' : `Year ${idx + 1}`,
        fcf: Math.round(fcf),
        formattedFcf: `$${(Math.abs(fcf) / 1000).toFixed(1)}B`,
        isNegative: fcf < 0
      }));
    };

    // Helper to prepare DuPont trend data
    const prepareDupontTrendData = () => {
      if (!valuationResults.dupont_outputs?.trends) return [];
      return valuationResults.dupont_outputs.trends.map((trend, idx) => ({
        year: trend.year || `Year ${idx + 1}`,
        roe: (trend.roe * 100).toFixed(1),
        netMargin: (trend.net_margin * 100).toFixed(1),
        assetTurnover: trend.asset_turnover?.toFixed(2),
        equityMultiplier: trend.equity_multiplier?.toFixed(2)
      }));
    };

    const fcfChartData = prepareFcfChartData();
    const dupontTrendData = prepareDupontTrendData();
    
    return (
      <div className="step-container">
        <h2>Valuation Results</h2>
        
        {/* DCF Results */}
        {selectedModel === 'DCF' && valuationResults.dcf_outputs && (
          <div className="results-dashboard">
            <div className="primary-result">
              <h3>DCF Valuation Summary</h3>
              <div className="result-highlight">
                <span className="label">Enterprise Value (Perpetuity)</span>
                <span className="value">${valuationResults.dcf_outputs.enterprise_value_perpetuity?.toLocaleString()}</span>
              </div>
              <div className="result-highlight">
                <span className="label">Enterprise Value (Multiple)</span>
                <span className="value">${valuationResults.dcf_outputs.enterprise_value_multiple?.toLocaleString()}</span>
              </div>
              <div className="result-highlight">
                <span className="label">Equity Value per Share</span>
                <span className="value">${valuationResults.dcf_outputs.equity_value_per_share_perpetuity?.toFixed(2)}</span>
              </div>
              <div className="result-highlight">
                <span className="label">Current Share Price</span>
                <span className="value">${valuationResults.dcf_outputs.current_stock_price?.toFixed(2)}</span>
              </div>
              <div className={`result-highlight ${valuationResults.dcf_outputs.upside_downside_perpetuity_pct >= 0 ? 'positive' : 'negative'}`}>
                <span className="label">Implied Upside/(Downside)</span>
                <span className="value">{valuationResults.dcf_outputs.upside_downside_perpetuity_pct?.toFixed(1)}%</span>
              </div>
            </div>
            
            {/* FCF Projection Chart */}
            {fcfChartData.length > 0 && (
              <div className="summary-box" style={{ marginTop: '24px' }}>
                <h3 style={{ marginBottom: '16px' }}>📊 Free Cash Flow Projections</h3>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={fcfChartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
                    <XAxis dataKey="period" stroke="#666" />
                    <YAxis stroke="#666" tickFormatter={(value) => `$${(Math.abs(value)/1000).toFixed(0)}B`} />
                    <Tooltip 
                      formatter={(value) => [`$${(Math.abs(value)/1000).toFixed(1)}B`, 'Free Cash Flow']}
                      contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}
                    />
                    <Bar 
                      dataKey="fcf" 
                      fill={(props) => props.payload.isNegative ? '#dc3545' : '#28a745'}
                      name="Free Cash Flow"
                      radius={[8, 8, 0, 0]}
                    />
                  </BarChart>
                </ResponsiveContainer>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px', marginTop: '20px' }}>
                  <div style={{ padding: '16px', background: 'white', borderRadius: '8px', textAlign: 'center' }}>
                    <div style={{ fontSize: '13px', color: '#666', marginBottom: '8px' }}>Total PV of FCF</div>
                    <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#667eea' }}>
                      ${valuationResults.dcf_outputs.pv_of_fcf ? (valuationResults.dcf_outputs.pv_of_fcf / 1000).toFixed(1) + 'B' : 'N/A'}
                    </div>
                  </div>
                  <div style={{ padding: '16px', background: 'white', borderRadius: '8px', textAlign: 'center' }}>
                    <div style={{ fontSize: '13px', color: '#666', marginBottom: '8px' }}>Terminal Value (PV)</div>
                    <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#764ba2' }}>
                      ${valuationResults.dcf_outputs.pv_of_terminal_value ? (valuationResults.dcf_outputs.pv_of_terminal_value / 1000).toFixed(1) + 'B' : 'N/A'}
                    </div>
                  </div>
                  <div style={{ padding: '16px', background: 'white', borderRadius: '8px', textAlign: 'center' }}>
                    <div style={{ fontSize: '13px', color: '#666', marginBottom: '8px' }}>WACC Used</div>
                    <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#667eea' }}>
                      {(valuationResults.dcf_outputs.wacc_used * 100)?.toFixed(2) + '%' || 'N/A'}
                    </div>
                  </div>
                </div>
              </div>
            )}
            
            {/* Sensitivity Tables */}
            {valuationResults.dcf_outputs.sensitivity_tables && (
              <div className="summary-box" style={{ marginTop: '24px' }}>
                <h3>Sensitivity Analysis</h3>
                <p>WACC vs Terminal Growth (EV in $M)</p>
                {/* Render sensitivity table here */}
              </div>
            )}
          </div>
        )}
        
        {/* DuPont Results with Trend Chart */}
        {selectedModel === 'DuPont' && valuationResults.dupont_outputs && (
          <div className="results-dashboard">
            <div className="primary-result">
              <h3>DuPont Analysis Summary</h3>
              <div className="result-highlight">
                <span className="label">ROE (Latest Year)</span>
                <span className="value">{(valuationResults.dupont_outputs.roe_latest * 100).toFixed(1)}%</span>
              </div>
              <div className="result-highlight">
                <span className="label">Net Profit Margin</span>
                <span className="value">{(valuationResults.dupont_outputs.net_margin_latest * 100).toFixed(1)}%</span>
              </div>
              <div className="result-highlight">
                <span className="label">Asset Turnover</span>
                <span className="value">{valuationResults.dupont_outputs.asset_turnover_latest.toFixed(2)}x</span>
              </div>
              <div className="result-highlight">
                <span className="label">Equity Multiplier</span>
                <span className="value">{valuationResults.dupont_outputs.equity_multiplier_latest.toFixed(2)}x</span>
              </div>
            </div>
            
            {/* ROE Trend Chart */}
            {dupontTrendData.length > 0 && (
              <div className="summary-box" style={{ marginTop: '24px' }}>
                <h3 style={{ marginBottom: '16px' }}>📈 5-Year ROE Decomposition Trend</h3>
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={dupontTrendData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
                    <XAxis dataKey="year" stroke="#666" />
                    <YAxis stroke="#666" label={{ value: 'ROE (%)', angle: -90, position: 'insideLeft' }} />
                    <Tooltip 
                      contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}
                    />
                    <Legend />
                    <Line type="monotone" dataKey="roe" stroke="#667eea" strokeWidth={3} name="ROE %" dot={{ r: 5 }} />
                    <Line type="monotone" dataKey="netMargin" stroke="#28a745" strokeWidth={2} name="Net Margin %" strokeDasharray="5 5" />
                  </LineChart>
                </ResponsiveContainer>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px', marginTop: '20px' }}>
                  <div style={{ padding: '12px', background: 'white', borderRadius: '8px' }}>
                    <strong style={{ color: '#666', fontSize: '12px' }}>Avg ROE</strong>
                    <p style={{ fontSize: '20px', fontWeight: 'bold', color: '#667eea' }}>
                      {(dupontTrendData.reduce((sum, d) => sum + parseFloat(d.roe), 0) / dupontTrendData.length).toFixed(1)}%
                    </p>
                  </div>
                  <div style={{ padding: '12px', background: 'white', borderRadius: '8px' }}>
                    <strong style={{ color: '#666', fontSize: '12px' }}>ROE Trend</strong>
                    <p style={{ fontSize: '20px', fontWeight: 'bold', color: parseFloat(dupontTrendData[dupontTrendData.length - 1]?.roe) > parseFloat(dupontTrendData[0]?.roe) ? '#28a745' : '#dc3545' }}>
                      {parseFloat(dupontTrendData[dupontTrendData.length - 1]?.roe) > parseFloat(dupontTrendData[0]?.roe) ? '📈 Improving' : '📉 Declining'}
                    </p>
                  </div>
                  <div style={{ padding: '12px', background: 'white', borderRadius: '8px' }}>
                    <strong style={{ color: '#666', fontSize: '12px' }}>Latest ROE</strong>
                    <p style={{ fontSize: '20px', fontWeight: 'bold', color: '#764ba2' }}>{dupontTrendData[dupontTrendData.length - 1]?.roe}%</p>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
        
        {/* Comps Results */}
        {selectedModel === 'COMPS' && valuationResults.comps_outputs && (
          <div className="results-dashboard">
            <div className="primary-result">
              <h3>Trading Comps Summary</h3>
              <div className="result-highlight">
                <span className="label">Implied Share Price (Median)</span>
                <span className="value">${valuationResults.comps_outputs.implied_share_price_median?.toFixed(2)}</span>
              </div>
              <div className="result-highlight">
                <span className="label">Current Share Price</span>
                <span className="value">${valuationResults.comps_outputs.current_share_price?.toFixed(2)}</span>
              </div>
              <div className={`result-highlight ${valuationResults.comps_outputs.upside_downside_pct >= 0 ? 'positive' : 'negative'}`}>
                <span className="label">Implied Upside/(Downside)</span>
                <span className="value">{valuationResults.comps_outputs.upside_downside_pct?.toFixed(1)}%</span>
              </div>
              <div className="result-highlight">
                <span className="label">Peers Analyzed</span>
                <span className="value">{valuationResults.comps_outputs.peer_count}</span>
              </div>
            </div>
            
            {/* Peer Multiples */}
            {valuationResults.comps_outputs.peer_statistics && (
              <div className="summary-box" style={{ marginTop: '24px' }}>
                <h3>Peer Multiples Statistics</h3>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px' }}>
                  <div>
                    <strong>EV/EBITDA Median</strong>
                    <p>{valuationResults.comps_outputs.peer_statistics.ev_ebitda?.median?.toFixed(1)}x</p>
                  </div>
                  <div>
                    <strong>P/E Median</strong>
                    <p>{valuationResults.comps_outputs.peer_statistics.pe?.median?.toFixed(1)}x</p>
                  </div>
                  <div>
                    <strong>EV/Sales Median</strong>
                    <p>{valuationResults.comps_outputs.peer_statistics.ev_sales?.median?.toFixed(1)}x</p>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
        
        <div style={{ marginTop: '24px', display: 'flex', gap: '12px' }}>
          <button onClick={handleBackToModelSelection} className="btn-secondary">← Change Model</button>
          <button onClick={handleReset} className="btn-secondary">Start New Valuation</button>
          <button className="btn-primary">Export Report</button>
        </div>
      </div>
    );
  };

  const renderStep = () => {
    switch (currentStep) {
      case 1: return renderStep1();
      case 4: return renderStep4();
      case 5: return renderStep5();
      case 8: return renderStep8();
      case 9: return renderStep9();
      case 10: return renderStep10();
      default: return <div>Step under construction</div>;
    }
  };

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
          Step {currentStep} of 10: {
            currentStep === 1 ? 'Search Company' :
            currentStep === 4 ? 'Select Model' :
            currentStep === 5 ? 'Review Requirements' :
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
