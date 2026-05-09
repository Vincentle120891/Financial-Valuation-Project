import React from 'react';

/**
 * AiAssumptionsStep Component
 * Step 7: Historical Data Retrieval (International Market Only)
 *
 * UPDATED LOGIC:
 * - Step 7 uses AI to extract HISTORICAL financial data that APIs cannot provide
 * - Displays extracted historical data gaps, sources, and completeness score
 * - NO forward-looking assumptions are generated here
 * - Forward-looking assumptions happen in Step 8
 *
 * Market Segregation:
 * - International Market: Shows historical data extraction results
 * - Vietnam Market: Separate implementation (not handled here)
 * - DuPont/Comps: May bypass this step if API data is complete
 */
const AiAssumptionsStep = ({
  aiData,
  aiError,
  confirmedValues,
  selectedModel,
  market = 'US',
  onManualInput,
  onUseAI,
  onBackToApiData,
  onContinueToForecastDrivers,
  loading
}) => {
  // Handle using AI suggestion
  const handleUseAiSuggestion = (field, value) => {
    if (onUseAI) {
      onUseAI(field, value);
    }
  };

  // Handle manual input


// Handle manual input
const handleManualInputChange = (field, value) => {
  if (onManualInput) {
    onManualInput(field, value);
  }
};

// Render AI error/warning message for historical data extraction
const renderAiError = () => {
  if (!aiError) return null;

  return (
    <div className="summary-box" style={{ background: 'linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%)', border: '2px solid #ff9800', marginBottom: '20px' }}>
      <h3 style={{ color: '#e65100' }}>⚠️ Historical Data Extraction Issue</h3>
      <p style={{ marginBottom: '12px', color: '#e65100' }}>{aiError}</p>
      <div style={{ background: 'white', padding: '12px', borderRadius: '6px', marginTop: '12px' }}>
        <strong>💡 What this means:</strong>
        <p style={{ margin: '8px 0', color: '#333' }}>
          AI-powered historical data extraction encountered an issue. You can still proceed with the available API data.
        </p>
        <strong>📋 Next Steps:</strong>
        <ol style={{ margin: '8px 0', paddingLeft: '20px', color: '#333' }}>
          <li>Review the extracted historical data below</li>
          <li>Proceed to Step 8 for assumption generation</li>
          <li>Optionally go back and retry historical data extraction</li>
        </ol>
      </div>
    </div>
  );
};

// Helper to extract value from AI data structure
const getAiValue = (field) => {
  // Check multiple possible field names
  const possibleKeys = [
    field,
    `${field}_value`,
    `${field}_percent`,
    `${field}_rate`
  ];

  for (const key of possibleKeys) {
    if (aiData?.[key]) {
      const item = aiData[key];
      if (typeof item === 'object' && 'value' in item) {
        return item.value;
      }
      return item;
    }
  }
  return undefined;
};

// Helper to extract rationale from AI data structure
const getAiRationale = (field) => {
  const item = aiData?.[field];
  if (item && typeof item === 'object' && 'rationale' in item) {
    return item.rationale;
  }
  return aiData?.[`${field}_rationale`];
};

// Render single assumption field with enhanced AI explanation
const renderAssumptionField = ({
  fieldKey,
  label,
  step = 0.01,
  isPercentage = true,
  min,
  max,
  description,
  industryBenchmark,
  methodology,
  showRationale = false  // Only show rationale in the first field
}) => {
  const aiValue = getAiValue(fieldKey);
  const confirmedValue = confirmedValues?.[fieldKey]?.value;
  const displayValue = confirmedValue !== undefined ? confirmedValue : aiValue;
  const rationale = showRationale ? (getAiRationale(fieldKey) || aiData?.ai_rationale?.value) : null;

  // Convert to percentage for display if needed
  const displayPercent = displayValue !== undefined
    ? (displayValue > 1 ? displayValue / 100 : displayValue) * 100
    : '';

  return (
    <div style={{ background: 'white', padding: '16px', borderRadius: '8px', marginBottom: '16px', border: '1px solid #ddd' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
        <h4 style={{ margin: 0, color: '#1976d2' }}>{label}</h4>
        {aiValue !== undefined && (
          <span style={{ fontSize: '12px', padding: '4px 8px', background: '#e3f2fd', borderRadius: '4px', color: '#1565c0' }}>
            🤖 AI Suggested
          </span>
        )}
      </div>

      {description && (
        <p style={{ fontSize: '13px', color: '#666', marginBottom: '12px' }}>{description}</p>
      )}

      <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
        <input
          type="number"
          step={step}
          min={min}
          max={max}
          value={displayPercent || ''}
          onChange={(e) => {
            const val = parseFloat(e.target.value);
            const rawValue = isPercentage ? val / 100 : val;
            handleManualInputChange(fieldKey, rawValue);
          }}
          placeholder={`Enter ${label}`}
          style={{ flex: 1, padding: '10px', borderRadius: '6px', border: '1px solid #ccc', fontSize: '14px' }}
        />
        {isPercentage && <span style={{ fontWeight: 600, color: '#333' }}>%</span>}

        {aiValue !== undefined && (
          <button
            onClick={() => handleUseAiSuggestion(fieldKey, aiValue)}
            style={{
              padding: '10px 16px',
              background: confirmedValues?.[fieldKey]?.source === 'ai' ? '#4caf50' : '#2196f3',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
              fontWeight: 600
            }}
          >
            {confirmedValues?.[fieldKey]?.source === 'ai' ? '✓ Using AI' : 'Use AI'}
          </button>
        )}
      </div>

      {/* Enhanced AI Explanation Section */}
      {(rationale || industryBenchmark || methodology) && (
        <div style={{ marginTop: '12px', padding: '12px', background: '#f5f5f5', borderRadius: '6px', borderLeft: '4px solid #2196f3' }}>
          <strong style={{ color: '#1976d2', display: 'block', marginBottom: '8px' }}>💡 AI Analysis & Reasoning:</strong>

          {methodology && (
            <div style={{ marginBottom: '8px' }}>
              <strong style={{ fontSize: '12px', color: '#555' }}>Methodology:</strong>
              <p style={{ margin: '4px 0 0 0', fontSize: '13px', color: '#333', lineHeight: '1.5' }}>{methodology}</p>
            </div>
          )}

          {industryBenchmark && (
            <div style={{ marginBottom: '8px' }}>
              <strong style={{ fontSize: '12px', color: '#555' }}>Industry Benchmark:</strong>
              <p style={{ margin: '4px 0 0 0', fontSize: '13px', color: '#333', lineHeight: '1.5' }}>{industryBenchmark}</p>
            </div>
          )}

          {rationale && (
            <div>
              <strong style={{ fontSize: '12px', color: '#555' }}>Rationale:</strong>
              <p style={{ margin: '4px 0 0 0', fontSize: '13px', color: '#333', lineHeight: '1.5' }}>{rationale}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

// Render the 4 AI-only inputs for standard DCF (US/International)
const renderAiOnlyInputs = () => {
  return (
    <>
      {renderAssumptionField({
        fieldKey: 'equity_risk_premium',
        label: 'Equity Risk Premium (ERP)',
        description: 'Expected excess return of the market over the risk-free rate. Typical range: 4.5% - 6.5% for developed markets.',
        min: 0,
        max: 15,
        showRationale: true
      })}

      {renderAssumptionField({
        fieldKey: 'country_risk_premium',
        label: 'Country Risk Premium (CRP)',
        description: 'Additional risk premium for the company\'s primary operating country. 0% for stable developed markets like US.',
        min: 0,
        showRationale: false,
        max: 10
      })}

      {renderAssumptionField({
        fieldKey: 'terminal_growth_rate',
        label: 'Terminal Growth Rate',
        description: 'Perpetual growth rate for terminal value calculation. Should not exceed long-term GDP growth (typically 2-3%).',
        showRationale: false,
        min: 0,
        max: 5
      })}

      {renderAssumptionField({
        fieldKey: 'terminal_ebitda_multiple',
        label: 'Terminal EBITDA Multiple',
        description: 'Expected exit multiple at end of forecast period. Varies by sector: Tech (10-15x), Consumer (10-14x), Industrials (8-12x).',
        isPercentage: false,
        step: 0.5,
        showRationale: false,
        min: 0,
        max: 30
      })}
    </>
  );
};

// Render the 4 AI-only inputs for International DCF with market-specific guidance
const renderInternationalAiInputs = () => {
  return (
    <>
      {renderAssumptionField({
        fieldKey: 'equity_risk_premium',
        label: 'Equity Risk Premium (ERP)',
        description: 'Expected excess return of the market over the risk-free rate. Typical range: 4.5% - 6.5% for developed markets.',
        min: 0,
        max: 15,
        showRationale: true
      })}

      {renderAssumptionField({
        fieldKey: 'country_risk_premium',
        label: 'Country Risk Premium (CRP)',
        description: 'Additional risk premium for the company\'s primary operating country. 0% for stable developed markets like US.',
        min: 0,
        max: 10,
        showRationale: false
      })}

      {renderAssumptionField({
        fieldKey: 'terminal_growth_rate',
        label: 'Terminal Growth Rate',
        description: 'Perpetual growth rate for terminal value calculation. Should not exceed long-term GDP growth (typically 2-3%).',
        min: 0,
        max: 5,
        showRationale: false
      })}

      {renderAssumptionField({
        fieldKey: 'terminal_ebitda_multiple',
        label: 'Terminal EBITDA Multiple',
        description: 'Expected exit multiple at end of forecast period. Varies by sector: Tech (10-15x), Consumer (10-14x), Industrials (8-12x).',
        isPercentage: false,
        step: 0.5,
        min: 0,
        max: 30
      })}
    </>
  );
};

// Render "No AI Assumptions" message for DuPont/Comps models
const renderNoAiAssumptionsMessage = () => {
  const modelExplanation = selectedModel === 'DuPont'
    ? 'DuPont Analysis decomposes ROE into Net Profit Margin, Asset Turnover, and Equity Multiplier - all calculated from historical financial statements.'
    : 'Comparable Company Analysis calculates valuation multiples (EV/EBITDA, P/E, EV/Revenue, P/B) directly from peer company data fetched from yfinance.';

  return (
    <div style={{ background: 'linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%)', border: '2px solid #4caf50', padding: '20px', borderRadius: '8px', marginBottom: '20px' }}>
      <h3 style={{ color: '#2e7d32', margin: '0 0 12px 0' }}>✅ No AI Assumptions Required</h3>
      <p style={{ margin: '0 0 12px 0', color: '#1b5e20', lineHeight: '1.6' }}>
        For the <strong>{selectedModel}</strong> model, all inputs are <strong>100% calculated or fetched from financial data</strong>.
        The AI does not generate any assumptions for this model type.
      </p>
      <div style={{ background: 'white', padding: '12px', borderRadius: '6px', marginTop: '12px' }}>
        <strong>📊 How it works:</strong>
        <p style={{ margin: '8px 0', color: '#333', fontSize: '14px' }}>{modelExplanation}</p>
        <strong>🔒 No-Hallucination Guarantee:</strong>
        <p style={{ margin: '8px 0', color: '#333', fontSize: '14px' }}>
          If data exists in yfinance or can be calculated from financial statements, the AI never touches it.
          This ensures complete accuracy and eliminates hallucination risks.
        </p>
      </div>
    </div>
  );
};

// Render AI rationale summary
const renderAiRationaleSummary = () => {
  const rationale = aiData?.ai_rationale?.value || aiData?.rationale;
  if (!rationale) return null;

  return (
    <div style={{ background: '#f5f5f5', padding: '16px', borderRadius: '8px', marginBottom: '20px', border: '1px solid #ddd' }}>
      <h4 style={{ margin: '0 0 8px 0', color: '#333' }}>🤖 AI Analysis Summary</h4>
      <p style={{ margin: 0, fontSize: '14px', lineHeight: '1.6', color: '#555' }}>{rationale}</p>
    </div>
  );
};

// Render historical data gaps table for International DCF
const renderHistoricalDataGaps = () => {
  if (!aiData || !aiData.historical_gaps_filled) {
    return (
      <div style={{ background: 'linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%)', border: '2px solid #4caf50', padding: '20px', borderRadius: '8px', marginBottom: '20px' }}>
        <h3 style={{ color: '#2e7d32', margin: '0 0 12px 0' }}>✅ Historical Data Complete</h3>
        <p style={{ margin: 0, color: '#1b5e20', lineHeight: '1.6' }}>
          All historical financial data was successfully retrieved from APIs. No AI extraction was needed.
        </p>
      </div>
    );
  }

  const gaps = aiData.historical_gaps_filled;
  const completeness = aiData.data_completeness_score || 0;
  const sourcesUsed = aiData.sources_used || [];

  return (
    <>
      {/* Completeness Summary */}
      <div style={{
        background: completeness >= 0.8
          ? 'linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%)'
          : 'linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%)',
        border: completeness >= 0.8 ? '2px solid #4caf50' : '2px solid #ff9800',
        padding: '20px',
        borderRadius: '8px',
        marginBottom: '20px'
      }}>
        <h3 style={{ color: completeness >= 0.8 ? '#2e7d32' : '#e65100', margin: '0 0 12px 0' }}>
          {completeness >= 0.8 ? '✅ Historical Data Extraction Complete' : '⚠️ Partial Historical Data Extraction'}
        </h3>
        <p style={{ margin: '0 0 12px 0', color: completeness >= 0.8 ? '#1b5e20' : '#e65100', lineHeight: '1.6' }}>
          <strong>Completeness Score:</strong> {(completeness * 100).toFixed(0)}% |
          <strong> Gaps Filled:</strong> {aiData.total_gaps_filled} / {aiData.total_gaps_found}
        </p>
        {sourcesUsed.length > 0 && (
          <div style={{ background: 'white', padding: '12px', borderRadius: '6px', marginTop: '12px' }}>
            <strong>📚 Sources Used:</strong>
            <ul style={{ margin: '8px 0', paddingLeft: '20px', color: '#333', fontSize: '14px' }}>
              {sourcesUsed.map((source, idx) => (
                <li key={idx}>{source}</li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Historical Data Gaps Table */}
      <div style={{ background: 'white', padding: '20px', borderRadius: '8px', marginBottom: '20px', border: '1px solid #ddd' }}>
        <h3 style={{ color: '#1976d2', margin: '0 0 16px 0' }}>📊 Extracted Historical Data</h3>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '14px' }}>
          <thead>
            <tr style={{ background: '#f5f5f5', borderBottom: '2px solid #ddd' }}>
              <th style={{ padding: '12px', textAlign: 'left', color: '#333' }}>Metric</th>
              <th style={{ padding: '12px', textAlign: 'center', color: '#333' }}>Fiscal Year</th>
              <th style={{ padding: '12px', textAlign: 'right', color: '#333' }}>Extracted Value</th>
              <th style={{ padding: '12px', textAlign: 'left', color: '#333' }}>Source</th>
              <th style={{ padding: '12px', textAlign: 'center', color: '#333' }}>Confidence</th>
            </tr>
          </thead>
          <tbody>
            {gaps.map((gap, idx) => (
              <tr key={idx} style={{ borderBottom: '1px solid #eee' }}>
                <td style={{ padding: '12px', color: '#333', fontWeight: 500 }}>{gap.metric}</td>
                <td style={{ padding: '12px', textAlign: 'center', color: '#666' }}>{gap.fiscal_year}</td>
                <td style={{ padding: '12px', textAlign: 'right', color: '#1976d2', fontWeight: 600 }}>
                  {gap.extracted_value !== null ? gap.extracted_value.toLocaleString() : 'N/A'}
                </td>
                <td style={{ padding: '12px', color: '#666', fontSize: '13px' }}>{gap.data_source}</td>
                <td style={{ padding: '12px', textAlign: 'center' }}>
                  <span style={{
                    padding: '4px 8px',
                    borderRadius: '4px',
                    fontSize: '12px',
                    background: gap.confidence_score >= 0.8 ? '#e8f5e9' : gap.confidence_score >= 0.6 ? '#fff3e0' : '#ffebee',
                    color: gap.confidence_score >= 0.8 ? '#2e7d32' : gap.confidence_score >= 0.6 ? '#e65100' : '#c62828',
                    fontWeight: 600
                  }}>
                    {(gap.confidence_score * 100).toFixed(0)}%
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Extraction Methodology */}
      {aiData.extraction_methodology && (
        <div style={{ background: '#f5f5f5', padding: '16px', borderRadius: '8px', marginBottom: '20px', border: '1px solid #ddd' }}>
          <h4 style={{ margin: '0 0 8px 0', color: '#333' }}>🔍 Extraction Methodology</h4>
          <p style={{ margin: 0, fontSize: '14px', lineHeight: '1.6', color: '#555' }}>{aiData.extraction_methodology}</p>
        </div>
      )}
    </>
  );
};


// Determine rendering based on model type and market
const isAiBypassed = ['DuPont', 'Comps'].includes(selectedModel);
const isInternationalDcf = selectedModel === 'DCF' && market !== 'Vietnam';
const isVietnamMarket = market === 'Vietnam';

return (
  <div className="step-container">
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
      <div>
        <h2>Step 7: Review AI-Generated Assumptions</h2>
        <p style={{ color: '#666', marginTop: '8px' }}>Review AI-suggested valuation assumptions based on historical data, peer analysis, and market conditions. Accept or override each assumption.</p>
      </div>
      <button onClick={onBackToApiData} className="btn-secondary">
        ← Back to API Data
      </button>
    </div>

    {/* Model-specific info banner */}
    <div style={{
      marginBottom: '20px',
      padding: '16px',
      borderRadius: '8px',
      background: isAiBypassed
        ? 'linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%)'
        : isVietnamMarket
          ? 'linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%)'
          : 'linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%)',
      border: isAiBypassed
        ? '2px solid #4caf50'
        : isVietnamMarket
          ? '2px solid #ff9800'
          : '2px solid #2196f3'
    }}>
      <p style={{ margin: 0, color: isAiBypassed ? '#1b5e20' : isVietnamMarket ? '#e65100' : '#1565c0' }}>
        {isAiBypassed && (
          <><strong>✅ No AI Required:</strong> For {selectedModel} model, all inputs are 100% calculated from financial data. No AI assumptions needed.</>
        )}
        {isVietnamMarket && (
          <><strong>🇻🇳 Vietnam DCF:</strong> Uses a separate pipeline with different data sources and compliance requirements.</>
        )}
        {isInternationalDcf && (
          <><strong>ℹ️ About this step:</strong> AI generates ONLY 4 forward-looking assumptions (ERP, CRP, Terminal Growth, Terminal Multiple). All other inputs are calculated from API data.</>
        )}
      </p>
    </div>

    {renderAiError()}

    {/* Dynamic rendering based on model type */}
    {isAiBypassed ? (
      renderNoAiAssumptionsMessage()
    ) : isVietnamMarket ? (
      <div style={{ background: 'linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%)', border: '2px solid #ff9800', padding: '20px', borderRadius: '8px', marginBottom: '20px' }}>
        <h3 style={{ color: '#e65100', margin: '0 0 12px 0' }}>🇻🇳 Vietnam Market - Separate Pipeline</h3>
        <p style={{ margin: 0, color: '#e65100', lineHeight: '1.6' }}>
          Vietnamese market uses a separate pipeline with different data sources and compliance requirements.
        </p>
      </div>
    ) : isInternationalDcf ? (
      <>
        {renderHistoricalDataGaps()}
        {renderAiRationaleSummary()}
      </>
    ) : null}

    {!isAiBypassed && isInternationalDcf && (!aiData || Object.keys(aiData).length === 0) && (
      <div className="summary-box" style={{ background: 'linear-gradient(135deg, #f5f5f5 0%, #e0e0e0 100%)' }}>
        <h3>⚠️ No Historical Data Extracted</h3>
        <p>AI extraction did not find any additional historical data. Proceed with available API data or go back to retry.</p>
      </div>
    )}

    <div style={{ marginTop: '20px', display: 'flex', gap: '10px' }}>
      <button
        onClick={onContinueToForecastDrivers}
        className="btn-primary"
        disabled={loading}
      >
        Continue to Step 8: Assumptions →
      </button>
    </div>
  </div>
);
};

export default AiAssumptionsStep;
