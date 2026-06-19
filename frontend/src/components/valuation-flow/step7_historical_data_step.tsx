import React, { useState, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import DataFieldDisplay from './DataFieldDisplay';
import ProcessingOverlay from '../ui/ProcessingOverlay';

interface HistoricalDataExtractionStepProps {
  [key: string]: any;
}

/**
 * HistoricalDataExtractionStep Component
 * Step 7: Historical Data Extraction Results (3 Valuation Methods × 2 Markets)
 *
 * CORRECTED LOGIC:
 * - Step 7 uses AI to extract HISTORICAL financial data that APIs cannot provide
 * - Displays extracted historical data gaps, sources, and completeness score
 * - NO forward-looking assumptions are generated here (that's Step 8)
 * - Works for ALL 3 valuation models (DCF, DuPont, Comps) and BOTH markets
 * - NEW: Supports PDF upload for manual document submission
 *
 * Workflow:
 * 1. Compare model requirements vs. apiData from Step 6
 * 2. Identify GAPS (missing historical inputs)
 * 3. Display gaps to user with "Generate AI Suggestions" button
 * 4. AI searches public reports/filings to fill gaps
 * 5. Show extraction results with confidence scores and sources
 * 6. NEW: Users can upload PDF reports directly for extraction
 */
const HistoricalDataExtractionStep: React.FC<HistoricalDataExtractionStepProps> = ({
  historicalGapsData,
  aiError,
  confirmedValues,
  selectedModel,
  market = 'international',
  historicalData,
  apiData,
  sessionId,
  onManualInput,
  onUseAI,
  onBackToApiData,
  onContinueToForecastDrivers,
  onRetryAiExtraction,
  loading
}) => {
  const { t } = useTranslation();
  // FIX Issue #5: Use only historicalGapsData as per UnifiedStep7Response (no legacy fallback)
  const data = historicalGapsData;

  // Extract missing data summary from Step 6 response
  const missingSummary = data?.missing_data_summary || data?.calculated_metrics?.missing_data_summary || null;
  const criticalMissing = missingSummary?.critical_missing || [];
  const optionalMissing = missingSummary?.optional_missing || [];
  const rawCompletionPct = missingSummary?.completion_percentage || 0;
  // Handle both decimal (0.6) and percentage (60.0) formats from backend
  const completionPct = rawCompletionPct > 1 ? rawCompletionPct : rawCompletionPct * 100;

  // PDF Upload state
  const [uploadingPdf, setUploadingPdf] = useState(false);
  const [uploadResult, setUploadResult] = useState(null);
  const [uploadError, setUploadError] = useState(null);
  const fileInputRef = useRef(null);

  // AI Web Search state
  const [searchingWithAi, setSearchingWithAi] = useState(false);
  const [aiSearchResult, setAiSearchResult] = useState(null);
  const [aiSearchError, setAiSearchError] = useState(null);
  const [showPromptEditor, setShowPromptEditor] = useState(false);
  const [customPrompt, setCustomPrompt] = useState('');
  
  // SEC EDGAR Modal state
  const [showSecEdgarModal, setShowSecEdgarModal] = useState(false);
  const [secEdgarEmail, setSecEdgarEmail] = useState('');
  const [fetchingSecData, setFetchingSecData] = useState(false);
  const [secFetchResult, setSecFetchResult] = useState(null);
  const [secFetchError, setSecFetchError] = useState(null);

  // Handle using AI suggestion for historical data
  const handleUseAiSuggestion = (field, value) => {
    if (onUseAI) {
      onUseAI(field, value);
    }
  };

  // Handle manual input for historical data
  const handleManualInputChange = (field, value) => {
    if (onManualInput) {
      onManualInput(field, value);
    }
  };

  // PDF Upload handler
  const handlePdfUpload = async (event) => {
    const file = event.target.files[0];
    if (!file || !sessionId) return;

    setUploadingPdf(true);
    setUploadError(null);
    setUploadResult(null);

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('session_id', sessionId);
      formData.append('method', selectedModel || 'DCF');
      formData.append('market', market.toLowerCase());

      const response = await fetch('/api/step-7-upload-pdf', {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Upload failed');
      }

      const result = await response.json();
      setUploadResult(result);

      // Notify parent component of successful upload
      if (onRetryAiExtraction) {
        // Trigger a refresh of the historical data
        onRetryAiExtraction();
      }
    } catch (error) {
      setUploadError(error.message);
    } finally {
      setUploadingPdf(false);
    }
  };

  // Trigger file input click
  const triggerFileUpload = () => {
    if (fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  // AI Web Search handler — accepts optional custom prompt
  const handleAiWebSearch = async (promptText) => {
    if (!sessionId || !ticker) return;

    setSearchingWithAi(true);
    setAiSearchError(null);
    setAiSearchResult(null);

    try {
      const params = new URLSearchParams({
        session_id: sessionId,
        ticker: ticker,
        company_name: companyName || ticker,
        method: selectedModel || 'DCF',
        market: market.toLowerCase()
      });
      // Send custom prompt if provided
      if (promptText && promptText.trim()) {
        params.append('custom_prompt', promptText.trim());
      }
      // Build headers with API keys from localStorage (same as axios interceptor)
      const apiHeaders = {};
      const getKey = (name) => {
        const raw = localStorage.getItem(`${name}_api_key`) || '';
        return raw.split('\n').find(k => k.trim()) || '';
      };
      const openrouterKey = getKey('openrouter');
      const groqKey = getKey('groq');
      const geminiKey = getKey('gemini');
      const qwenKey = getKey('qwen');
      if (openrouterKey) apiHeaders['X-API-Key-openrouter'] = openrouterKey;
      if (groqKey) apiHeaders['X-API-Key-groq'] = groqKey;
      if (geminiKey) apiHeaders['X-API-Key-gemini'] = geminiKey;
      if (qwenKey) apiHeaders['X-API-Key-qwen'] = qwenKey;

      const response = await fetch(`/api/step-7-ai-web-search?${params.toString()}`, {
        method: 'POST',
        headers: apiHeaders
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'AI web search failed');
      }

      const result = await response.json();
      setAiSearchResult(result);
      // Do NOT call onRetryAiExtraction here — it navigates to Step 8
      // User should manually click "Continue to Step 8" after reviewing results
    } catch (error) {
      setAiSearchError(error.message);
    } finally {
      setSearchingWithAi(false);
    }
  };

  // SEC EDGAR Fetch handler
  const handleSecEdgarFetch = async () => {
    if (!sessionId || !ticker || !secEdgarEmail) return;

    setFetchingSecData(true);
    setSecFetchError(null);
    setSecFetchResult(null);

    try {
      // Save email to localStorage for future use
      localStorage.setItem('sec_edgar_email', secEdgarEmail);

      const response = await fetch('/api/step-7-fetch-sec-edgar', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key-SecEdgar': secEdgarEmail
        },
        body: JSON.stringify({
          session_id: sessionId,
          ticker: ticker,
          company_name: companyName || ticker,
          email: secEdgarEmail,
          method: selectedModel || 'DCF',
          market: market.toLowerCase()
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'SEC EDGAR fetch failed');
      }

      const result = await response.json();
      console.log('SEC EDGAR response:', JSON.stringify(result, null, 2));
      console.log('xbrl_data:', result.xbrl_data);
      console.log('xbrl_data_years:', result.xbrl_data_years);
      setSecFetchResult(result);

      // Do NOT call onRetryAiExtraction here — it navigates to Step 8
      // User should manually click "Continue to Step 8" after reviewing results
      // (Same as AI Web Search behavior)

      // Close modal after success
      setShowSecEdgarModal(false);
    } catch (error) {
      setSecFetchError(error.message);
    } finally {
      setFetchingSecData(false);
    }
  };

  // Load saved SEC EDGAR email on mount
  React.useEffect(() => {
    const savedEmail = localStorage.getItem('sec_edgar_email');
    if (savedEmail) {
      setSecEdgarEmail(savedEmail);
    }
  }, [showSecEdgarModal]);

  // Get ticker and company name from props or session
  // Backend response has ticker at metadata.ticker (Step 6 response) or top-level ticker
  const ticker = historicalData?.ticker || historicalData?.metadata?.ticker || apiData?.ticker || '';
  const companyName = historicalData?.company_name || historicalData?.metadata?.ticker || apiData?.company_name || '';

  // Render AI error/warning message for historical data extraction
  const renderAiError = () => {
    if (!aiError) return null;

    return (
      <div className="summary-box" style={{ background: 'var(--color-neutral-bg)', border: '2px solid var(--color-neutral)', marginBottom: '20px' }}>
        <h3 style={{ color: 'var(--color-neutral)' }}>⚠️ Historical Data Extraction Issue</h3>
        <p style={{ marginBottom: '12px', color: 'var(--color-neutral)' }}>{aiError}</p>
        <div style={{ background: 'var(--canvas-surface)', padding: '12px', borderRadius: '6px', marginTop: '12px' }}>
          <strong>💡 What this means:</strong>
          <p style={{ margin: '8px 0', color: 'var(--text-primary)' }}>
            AI-powered historical data extraction encountered an issue. You can still proceed with the available API data.
          </p>
          <strong>📋 Next Steps:</strong>
          <ol style={{ margin: '8px 0', paddingLeft: '20px', color: 'var(--text-primary)' }}>
            <li>Review the extracted historical data below</li>
            <li>Click "Retry AI Extraction" to attempt again</li>
            <li>Proceed to Step 8 for assumption generation</li>
          </ol>
        </div>
      </div>
    );
  };

  // Render "No Historical Gaps" message when all data is complete
  const renderNoGapsMessage = () => {
    const modelText = selectedModel === 'DCF'
      ? 'DCF requires 4 years of historical income statement, balance sheet, and cash flow data.'
      : selectedModel === 'DuPont'
        ? 'DuPont Analysis requires 4 years of Net Income, Revenue, Assets, and Equity.'
        : 'Trading Comps requires current peer company multiples and financial metrics.';

    return (
      <div style={{ background: 'var(--color-bullish-bg)', border: '2px solid var(--color-bullish)', padding: '20px', borderRadius: '8px', marginBottom: '20px' }}>
        <h3 style={{ color: 'var(--color-bullish)', margin: '0 0 12px 0' }}>✅ All Historical Data Retrieved</h3>
        <p style={{ margin: '0 0 12px 0', color: 'var(--color-bullish)', lineHeight: '1.6' }}>
          API data retrieval was 100% successful. No AI extraction was needed for the {selectedModel} model.
        </p>
        <div style={{ background: 'var(--canvas-surface)', padding: '12px', borderRadius: '6px', marginTop: '12px' }}>
          <strong>📊 Data Requirements Met:</strong>
          <p style={{ margin: '8px 0', color: 'var(--text-primary)', fontSize: '14px' }}>{modelText}</p>
          <strong>✓ Next Step:</strong>
          <p style={{ margin: '8px 0 0 0', color: 'var(--text-primary)', fontSize: '14px' }}>
            Proceed to Step 8 to generate forward-looking assumptions (DCF) or run calculations directly (DuPont/Comps).
          </p>
        </div>
      </div>
    );
  };

  // Render historical data gaps table - PRIMARY DISPLAY for Step 7
  const renderHistoricalDataGaps = () => {
    // Check if we have historical gaps filled data (using renamed 'data' variable)
    const hasGaps = data && data.historical_gaps_filled && data.historical_gaps_filled.length > 0;
    const rawCompleteness = data?.data_completeness_score ?? data?.missing_data_summary?.completion_percentage ?? data?.calculated_metrics?.missing_data_summary?.completion_percentage ?? 1.0;
    // Handle both decimal (0.6) and percentage (60.0) formats from backend
    const completeness = rawCompleteness > 1 ? rawCompleteness / 100 : rawCompleteness;
    const sourcesUsed = data?.sources_used || [];
    const totalGapsFound = data?.total_gaps_found || 0;
    const totalGapsFilled = data?.total_gaps_filled || 0;

    // No gaps case - all data retrieved successfully
    if (!hasGaps && completeness >= 0.99) {
      return renderNoGapsMessage();
    }

    // Gaps exist - show extraction results
    const gaps = data?.historical_gaps_filled || [];

    return (
      <>
        {/* Historical Data Gaps Table */}
        {gaps.length > 0 && (
          <div style={{ background: 'var(--canvas-surface)', padding: '20px', borderRadius: '8px', marginBottom: '20px', border: '1px solid var(--border-default)' }}>
            <h3 style={{ color: 'var(--accent-primary)', margin: '0 0 16px 0' }}>📊 Extracted Historical Data</h3>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '14px' }}>
              <thead>
                <tr style={{ background: 'var(--canvas-bg)', borderBottom: '2px solid var(--border-default)' }}>
                  <th style={{ padding: '12px', textAlign: 'left', color: 'var(--text-primary)' }}>Metric</th>
                  <th style={{ padding: '12px', textAlign: 'center', color: 'var(--text-primary)' }}>Fiscal Year</th>
                  <th style={{ padding: '12px', textAlign: 'right', color: 'var(--text-primary)' }}>Extracted Value</th>
                  <th style={{ padding: '12px', textAlign: 'left', color: 'var(--text-primary)' }}>Source</th>
                  <th style={{ padding: '12px', textAlign: 'center', color: 'var(--text-primary)' }}>Confidence</th>
                </tr>
              </thead>
              <tbody>
                {gaps.map((gap, idx) => (
                  <tr key={idx} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                    <td style={{ padding: '12px', color: 'var(--text-primary)', fontWeight: 500 }}>{gap.metric}</td>
                    <td style={{ padding: '12px', textAlign: 'center', color: 'var(--text-secondary)' }}>{gap.fiscal_year}</td>
                    <td style={{ padding: '12px', textAlign: 'right', color: 'var(--accent-primary)', fontWeight: 600 }}>
                      {gap.extracted_value !== null ? gap.extracted_value.toLocaleString() : 'N/A'}
                    </td>
                    <td style={{ padding: '12px', color: 'var(--text-secondary)', fontSize: '13px' }}>{gap.data_source}</td>
                    <td style={{ padding: '12px', textAlign: 'center' }}>
                      <DataFieldDisplay 
                        dataField={{
                          key: `${gap.metric}_${gap.fiscal_year}`,
                          value: gap.extracted_value,
                          status: 'RETRIEVED',
                          source: gap.data_source,
                          confidence_score: gap.confidence_score,
                          periods: [gap.fiscal_year]
                        }}
                        showMetadata={true}
                        compact={true}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Extraction Methodology */}
        {data?.extraction_methodology && (
          <div style={{ background: 'var(--canvas-bg)', padding: '16px', borderRadius: '8px', marginBottom: '20px', border: '1px solid var(--border-default)' }}>
            <h4 style={{ margin: '0 0 8px 0', color: 'var(--text-primary)' }}>🔍 Extraction Methodology</h4>
            <p style={{ margin: 0, fontSize: '14px', lineHeight: '1.6', color: 'var(--text-secondary)' }}>{data.extraction_methodology}</p>
          </div>
        )}

        {/* Retry Button */}
        {completeness < 1.0 && onRetryAiExtraction && (
          <button
            onClick={onRetryAiExtraction}
            className="btn-secondary"
            disabled={loading}
            style={{ marginTop: '10px' }}
          >
            🔄 Retry AI Extraction
          </button>
        )}
      </>
    );
  };

  // Determine rendering based on model type and market
  // ALL models use this step for historical gap filling
  const isVietnamMarket = market === 'vietnam' || market === 'Vietnam';

  // Determine which overlay to show (priority: searchingWithAi > uploadingPdf > fetchingSecData > loading)
  const overlayIsOpen = searchingWithAi || uploadingPdf || fetchingSecData || loading;
  const overlayTitle = searchingWithAi
    ? 'AI Web Search'
    : uploadingPdf
      ? 'Extracting PDF Data'
      : fetchingSecData
        ? 'Fetching SEC Filings'
        : 'Processing';
  const overlaySubtitle = searchingWithAi
    ? 'Searching for historical financial data...'
    : uploadingPdf
      ? 'Analyzing your PDF document...'
      : fetchingSecData
        ? 'Connecting to SEC EDGAR database...'
        : 'Preparing historical data...';
  const overlayMessages = searchingWithAi
    ? [
        'Querying AI models for financial data...',
        'Searching Yahoo Finance, Bloomberg, Reuters...',
        'Extracting revenue, earnings, and cash flow data...',
        'Cross-referencing multiple data sources...',
        'Merging results with existing API data...',
        'Validating extracted figures...',
      ]
    : uploadingPdf
      ? [
          'Uploading your PDF document...',
          'Parsing financial statements...',
          'Extracting line items and metrics...',
          'Normalizing data to standard format...',
          'Validating extracted values...',
        ]
      : fetchingSecData
        ? [
            'Connecting to SEC EDGAR...',
            'Searching for 10-K and 10-Q filings...',
            'Downloading XBRL data...',
            'Extracting balance sheet items...',
            'Processing filing data...',
          ]
        : [
            'Loading historical data...',
            'Preparing data for display...',
            'Organizing financial information...',
          ];

  return (
    <>
    <ProcessingOverlay
      isOpen={overlayIsOpen}
      title={overlayTitle}
      subtitle={overlaySubtitle}
      messages={overlayMessages}
      accentColor={searchingWithAi ? 'green' : uploadingPdf ? 'purple' : 'orange'}
    />
    <div className="step-container">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <div>
          <h2>{t('steps.step7')}</h2>
          <p style={{ color: 'var(--text-secondary)', marginTop: '8px' }}>
            Review AI-extracted historical financial data that APIs could not retrieve.
            AI searched public filings, annual reports, and financial statements to fill data gaps.
          </p>
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
        background: isVietnamMarket
          ? 'linear-gradient(135deg, var(--color-neutral-bg))'
          : 'linear-gradient(135deg, var(--accent-primary-subtle))',
        border: isVietnamMarket
          ? '2px solid var(--color-neutral)'
          : '2px solid var(--accent-primary)'
      }}>
        <p style={{ margin: 0, color: isVietnamMarket ? 'var(--color-neutral)' : 'var(--accent-primary)' }}>
          <strong>📋 What happened:</strong> Step 6 retrieved data from APIs. This step shows any missing historical data that AI extracted from public documents.
          {selectedModel === 'DCF' && ' DCF requires 4 years of historical financials for accurate projections.'}
          {selectedModel === 'DuPont' && ' DuPont Analysis needs 4 years of balance sheet and income statement data.'}
          {selectedModel === 'COMPS' && ' Trading Comps requires current peer multiples and financial metrics.'}
        </p>
      </div>

      {/* Options Banner - Clear guidance for users */}
      <div style={{
        marginBottom: '20px',
        padding: '20px',
        borderRadius: '8px',
        background: 'var(--accent-primary-subtle)',
        border: '2px solid var(--accent-primary)'
      }}>
        <h3 style={{ color: 'var(--accent-primary)', margin: '0 0 16px 0', fontSize: '18px' }}>
          🎯 How to Retrieve Historical Data
        </h3>
        <p style={{ margin: '0 0 16px 0', color: 'var(--accent-primary)', fontSize: '14px', lineHeight: '1.6' }}>
          To ensure accurate valuation, you need precise historical financial data.
          Since automatic API data can be incomplete, please choose one of these options:
        </p>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '16px' }}>
          {/* Option 1 */}
          <div style={{
            background: 'var(--canvas-surface)',
            padding: '16px',
            borderRadius: '6px',
            border: '2px solid var(--color-manual)'
          }}>
            <h4 style={{ color: 'var(--color-manual)', margin: '0 0 8px 0', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '20px' }}>📤</span> Option 1: Upload PDF Reports
            </h4>
            <p style={{ margin: '0 0 12px 0', fontSize: '13px', color: 'var(--text-secondary)', lineHeight: '1.5' }}>
              Upload the company's annual reports (10-K, Annual Report, or Financial Statements).
              Our AI will automatically extract and normalize the data.
            </p>
            <ul style={{ margin: '0', paddingLeft: '20px', fontSize: '12px', color: 'var(--text-tertiary)', lineHeight: '1.8' }}>
              <li><strong>Best for:</strong> Precise line items (NWC, CapEx, D&A)</li>
              <li><strong>Formats:</strong> PDF only</li>
              <li><strong>Standards:</strong> US GAAP, IFRS, Vietnamese</li>
            </ul>
          </div>

          {/* Option 2 - AI Web Search */}
          <div style={{
            background: 'var(--canvas-surface)',
            padding: '16px',
            borderRadius: '6px',
            border: '2px solid var(--color-bullish)'
          }}>
            <h4 style={{ color: 'var(--color-bullish)', margin: '0 0 8px 0', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '20px' }}>⚡</span> Option 2: AI Web Search (Powered by OpenRouter/Groq/Gemini/Qwen)
            </h4>
            <p style={{ margin: '0 0 12px 0', fontSize: '13px', color: 'var(--text-secondary)', lineHeight: '1.5' }}>
              Let our AI automatically search the web to extract historical financial data.
              The system tries multiple AI providers and merges results with existing API data.
            </p>
            <ul style={{ margin: '0', paddingLeft: '20px', fontSize: '12px', color: 'var(--text-tertiary)', lineHeight: '1.8' }}>
              <li><strong>Primary:</strong> OpenRouter (auto-fallback to Groq → Gemini → Qwen)</li>
              <li><strong>Sources:</strong> Yahoo Finance, Bloomberg, Reuters, IR sites</li>
              <li><strong>Output:</strong> Structured JSON with confidence scores</li>
            </ul>
            {/* Prompt Editor Toggle */}
            <button
              onClick={() => {
                setShowPromptEditor(!showPromptEditor);
                if (!showPromptEditor && !customPrompt) {
                  // Use the missing data summary from Step 6 to build a comprehensive prompt
                  const critMissing = criticalMissing || [];
                  const optMissing = optionalMissing || [];
                  const allMissing = [...new Set([...critMissing, ...optMissing])];
                  
                  if (allMissing.length > 0) {
                    const metricList = allMissing.map(m => `- ${m}`).join('\n');
                    setCustomPrompt(`Extract 4-year historical financial data for ${companyName || ticker} (${ticker}):\n${metricList}\n\nReturn as JSON with fiscal_years array containing year-by-year values for each metric. Include source URLs and confidence scores.`);
                  } else {
                    // Fallback if no missing data summary available
                    setCustomPrompt(`Extract 4-year historical financial data for ${companyName || ticker} (${ticker}):\n- Revenue\n- Net Income\n- EBITDA\n- Operating Cash Flow\n- CapEx\n- Total Assets\n- Total Equity\n- Working Capital\n- Free Cash Flow\n\nReturn as JSON with fiscal_years array.`);
                  }
                }
              }}
              style={{
                marginTop: '12px',
                width: '100%',
                padding: '8px',
                background: 'transparent',
                border: '1px solid var(--color-bullish)',
                borderRadius: '4px',
                color: 'var(--color-bullish)',
                cursor: 'pointer',
                fontSize: '13px'
              }}
            >
              {showPromptEditor ? '▲ Hide Prompt Editor' : '✏️ Edit AI Prompt Before Sending'}
            </button>

            {/* Prompt Editor */}
            {showPromptEditor && (
              <div style={{ marginTop: '12px' }}>
                <textarea
                  value={customPrompt}
                  onChange={(e) => setCustomPrompt(e.target.value)}
                  rows={12}
                  style={{
                    width: '100%',
                    padding: '12px',
                    border: '1px solid var(--border-strong)',
                    borderRadius: '4px',
                    fontFamily: 'var(--font-mono)',
                    fontSize: '13px',
                    lineHeight: '1.5',
                    resize: 'vertical',
                    background: 'var(--canvas-bg)'
                  }}
                  placeholder="Enter your custom prompt for the AI..."
                />
                <p style={{ marginTop: '4px', fontSize: '11px', color: 'var(--text-secondary)' }}>
                  Edit the prompt above to customize what data the AI extracts. The AI will search the web and return structured JSON.
                </p>
              </div>
            )}

            <button
              onClick={() => handleAiWebSearch(customPrompt)}
              disabled={searchingWithAi || !ticker}
              className="btn-primary"
              style={{
                marginTop: '12px',
                width: '100%',
                background: searchingWithAi ? 'var(--color-bullish-bg)' : 'var(--color-bullish)',
                color: 'white',
                border: 'none'
              }}
            >
              {searchingWithAi ? '🔍 Searching with AI...' : '🚀 Start AI Web Search'}
            </button>
            {!ticker && (
              <p style={{ marginTop: '8px', fontSize: '12px', color: 'var(--color-bearish)' }}>
                ⚠️ Ticker symbol required for AI search
              </p>
            )}
          </div>

          {/* Option 3 - SEC EDGAR Fetch */}
          <div style={{
            background: 'var(--canvas-surface)',
            padding: '16px',
            borderRadius: '6px',
            border: '2px solid var(--color-neutral)'
          }}>
            <h4 style={{ color: 'var(--color-neutral)', margin: '0 0 8px 0', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '20px' }}>🏛️</span> Option 3: Fetch from SEC EDGAR (US Companies Only)
            </h4>
            <p style={{ margin: '0 0 12px 0', fontSize: '13px', color: 'var(--text-secondary)', lineHeight: '1.5' }}>
              Automatically fetch 10-K and 10-Q filings directly from SEC EDGAR database.
              Requires email address for rate limit compliance.
            </p>
            <ul style={{ margin: '0', paddingLeft: '20px', fontSize: '12px', color: 'var(--text-tertiary)', lineHeight: '1.8' }}>
              <li><strong>Best for:</strong> US publicly traded companies</li>
              <li><strong>Forms:</strong> 10-K (Annual), 10-Q (Quarterly)</li>
              <li><strong>Requirement:</strong> Valid email address</li>
            </ul>
            <button
              onClick={() => setShowSecEdgarModal(true)}
              disabled={!ticker}
              className="btn-primary"
              style={{
                marginTop: '12px',
                width: '100%',
                background: 'var(--color-neutral)',
                color: 'white',
                border: 'none'
              }}
            >
              📥 Fetch SEC Filings
            </button>
            {!ticker && (
              <p style={{ marginTop: '8px', fontSize: '12px', color: 'var(--color-bearish)' }}>
                ⚠️ Ticker symbol required for SEC fetch
              </p>
            )}
          </div>
        </div>

        {/* Important Note */}
        <div style={{
          marginTop: '16px',
          padding: '12px',
          background: 'var(--color-neutral-bg)',
          border: '1px solid var(--color-neutral)',
          borderRadius: '6px',
          fontSize: '13px',
          color: 'var(--color-neutral)'
        }}>
          <strong>⚠️ Note:</strong> Automatic document fetching is currently disabled. For the most accurate results,
          we strongly recommend uploading official PDF reports using Option 1 above.
        </div>
      </div>

      {renderAiError()}

      {/* Missing Data Summary from Step 6 */}
      {criticalMissing.length > 0 || optionalMissing.length > 0 ? (
        <div style={{
          marginBottom: '20px',
          padding: '20px',
          borderRadius: '8px',
          background: 'var(--color-neutral-bg)',
          border: '2px solid var(--color-neutral)'
        }}>
          <h3 style={{ color: 'var(--color-neutral)', margin: '0 0 12px 0', fontSize: '18px' }}>
            📋 Missing Data Fields ({completionPct.toFixed(0)}% complete)
          </h3>
          <p style={{ margin: '0 0 12px 0', color: 'var(--color-bearish)', fontSize: '14px', lineHeight: '1.5' }}>
            The following data points are missing from Step 6 API retrieval. Use the options above to fill these gaps.
          </p>
          {criticalMissing.length > 0 && (
            <div style={{ marginBottom: '12px' }}>
              <strong style={{ color: 'var(--color-bearish)' }}>🔴 Critical Missing ({criticalMissing.length}):</strong>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginTop: '8px' }}>
                {criticalMissing.map((field, idx) => (
                  <span key={idx} style={{
                    padding: '4px 10px',
                    background: 'var(--color-bearish-bg)',
                    border: '1px solid var(--color-bearish-bg)',
                    borderRadius: '4px',
                    fontSize: '13px',
                    color: 'var(--color-bearish)'
                  }}>{field}</span>
                ))}
              </div>
            </div>
          )}
          {optionalMissing.length > 0 && (
            <div>
              <strong style={{ color: 'var(--color-neutral)' }}>🟡 Optional Missing ({optionalMissing.length}):</strong>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginTop: '8px' }}>
                {optionalMissing.map((field, idx) => (
                  <span key={idx} style={{
                    padding: '4px 10px',
                    background: 'var(--color-neutral-bg)',
                    border: '1px solid var(--color-neutral-bg)',
                    borderRadius: '4px',
                    fontSize: '13px',
                    color: 'var(--color-neutral)'
                  }}>{field}</span>
                ))}
              </div>
            </div>
          )}
        </div>
      ) : null}

      {/* PDF Upload Section */}
      <div style={{
        background: 'rgba(124, 58, 237, 0.08)',
        border: '2px solid var(--color-manual)',
        padding: '20px',
        borderRadius: '8px',
        marginBottom: '20px'
      }}>
        <h3 style={{ color: 'var(--color-manual)', margin: '0 0 12px 0' }}>📄 Upload Financial Report (PDF)</h3>
        <p style={{ margin: '0 0 16px 0', color: 'var(--color-manual)', fontSize: '14px' }}>
          Upload annual reports, 10-K filings, or financial statements to extract missing historical data.
          AI will automatically extract key metrics and fill gaps in your valuation model.
        </p>

        {/* Hidden file input */}
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf"
          onChange={handlePdfUpload}
          style={{ display: 'none' }}
        />

        {/* Upload button and status */}
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          <button
            onClick={triggerFileUpload}
            disabled={uploadingPdf}
            className="btn-secondary"
            style={{
              background: uploadingPdf ? 'var(--border-default)' : 'var(--color-manual)',
              color: 'white',
              border: 'none'
            }}
          >
            {uploadingPdf ? '⏳ Uploading & Extracting...' : '📎 Upload PDF Report'}
          </button>

          {uploadResult && (
            <span style={{ color: 'var(--color-bullish)', fontWeight: 600 }}>
              ✓ Extracted {Object.keys(uploadResult.extracted_metrics || {}).length} metrics from {uploadResult.fiscal_year}
            </span>
          )}
        </div>

        {/* Upload error */}
        {uploadError && (
          <div style={{
            marginTop: '12px',
            padding: '12px',
            background: 'var(--color-bearish-bg)',
            border: '1px solid var(--color-bearish)',
            borderRadius: '6px',
            color: 'var(--color-bearish)'
          }}>
            ❌ Upload failed: {uploadError}
          </div>
        )}

        {/* Upload success details */}
        {uploadResult && uploadResult.extracted_metrics && (
          <div style={{
            marginTop: '16px',
            padding: '12px',
            background: 'var(--canvas-surface)',
            borderRadius: '6px',
            border: '1px solid var(--color-bullish-bg)'
          }}>
            <strong style={{ color: 'var(--color-bullish)' }}>Extracted Metrics:</strong>
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
              gap: '8px',
              marginTop: '8px'
            }}>
              {Object.entries(uploadResult.extracted_metrics).map(([key, value]) => (
                <div key={key} style={{
                  padding: '8px',
                  background: 'var(--color-bullish-bg)',
                  borderRadius: '4px',
                  fontSize: '13px'
                }}>
                  <strong>{key}:</strong> {typeof value === 'number' ? value.toLocaleString() : String(value ?? '')}
                </div>
              ))}
            </div>
            {uploadResult.confidence_score && (
              <p style={{ marginTop: '8px', fontSize: '13px', color: 'var(--text-secondary)' }}>
                <strong>Confidence:</strong> {(uploadResult.confidence_score * 100).toFixed(0)}% |
                <strong> Method:</strong> {uploadResult.extraction_method}
              </p>
            )}
            {uploadResult.trend_analysis && (
              <div style={{
                marginTop: '12px',
                padding: '12px',
                background: 'var(--accent-primary-subtle)',
                borderRadius: '6px',
                border: '1px solid var(--accent-primary-subtle)'
              }}>
                <strong style={{ color: 'var(--accent-primary)', display: 'block', marginBottom: '8px' }}>📈 Historical Trend Analysis (Passed to Step 8)</strong>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '8px' }}>
                  {uploadResult.trend_analysis.growth_rates && (
                    <div>
                      <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '4px' }}>Revenue CAGR</div>
                      <div style={{ fontWeight: 600, color: 'var(--accent-primary)' }}>
                        {uploadResult.trend_analysis.growth_rates.revenue_cagr !== null ? `${(uploadResult.trend_analysis.growth_rates.revenue_cagr * 100).toFixed(2)}%` : 'N/A'}
                      </div>
                    </div>
                  )}
                  {uploadResult.trend_analysis.averages && (
                    <div>
                      <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '4px' }}>Avg Net Margin</div>
                      <div style={{ fontWeight: 600, color: 'var(--accent-primary)' }}>
                        {uploadResult.trend_analysis.averages.net_margin_avg !== null ? `${(uploadResult.trend_analysis.averages.net_margin_avg * 100).toFixed(2)}%` : 'N/A'}
                      </div>
                    </div>
                  )}
                  {uploadResult.trend_analysis.trend_direction && (
                    <div>
                      <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '4px' }}>Trend</div>
                      <div style={{ fontWeight: 600, color: 'var(--accent-primary)' }}>
                        Revenue: {uploadResult.trend_analysis.trend_direction.revenue === 'up' ? '↑' : uploadResult.trend_analysis.trend_direction.revenue === 'down' ? '↓' : '→'}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* AI Web Search Results Display */}
      {aiSearchResult && (
        <div style={{
          background: 'var(--color-bullish-bg)',
          border: '2px solid var(--color-bullish)',
          padding: '20px',
          borderRadius: '8px',
          marginBottom: '20px'
        }}>
          <h3 style={{ color: 'var(--color-bullish)', margin: '0 0 12px 0' }}>✅ AI Web Search Results</h3>
          <p style={{ margin: '0 0 16px 0', color: 'var(--color-bullish)', fontSize: '14px' }}>
            Successfully extracted data using <strong>{aiSearchResult.provider_used}</strong>.
            Confidence: {(aiSearchResult.confidence_score * 100).toFixed(0)}%
          </p>

          {aiSearchResult.sources && aiSearchResult.sources.length > 0 && (
            <div style={{
              marginTop: '12px',
              padding: '12px',
              background: 'var(--canvas-surface)',
              borderRadius: '6px',
              border: '1px solid var(--color-bullish-bg)'
            }}>
              <strong style={{ color: 'var(--color-bullish)' }}>📚 Sources:</strong>
              <ul style={{ margin: '8px 0', paddingLeft: '20px', fontSize: '13px', color: 'var(--text-primary)' }}>
                {aiSearchResult.sources.map((source, idx) => (
                  <li key={idx}>{source}</li>
                ))}
              </ul>
            </div>
          )}

          {aiSearchResult.time_series && Object.keys(aiSearchResult.time_series).length > 0 && (
            <div style={{
              marginTop: '16px',
              padding: '12px',
              background: 'var(--canvas-surface)',
              borderRadius: '6px',
              border: '1px solid var(--color-bullish-bg)'
            }}>
              <strong style={{ color: 'var(--color-bullish)' }}>📊 Extracted Time Series:</strong>
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))',
                gap: '12px',
                marginTop: '12px'
              }}>
                {Object.entries(aiSearchResult.time_series).map(([year, metrics]) => (
                  <div key={year} style={{
                    padding: '12px',
                    background: 'var(--color-bullish-bg)',
                    borderRadius: '6px',
                    border: '1px solid var(--color-bullish-bg)'
                  }}>
                    <strong style={{ color: 'var(--color-bullish)', display: 'block', marginBottom: '8px' }}>{year}</strong>
                    {Object.entries(metrics).map(([metric, value]) => (
                      <div key={metric} style={{
                        fontSize: '13px',
                        marginBottom: '4px',
                        display: 'flex',
                        justifyContent: 'space-between'
                      }}>
                        <span style={{ color: 'var(--text-secondary)' }}>{metric}:</span>
                        <span style={{ fontWeight: 600, color: 'var(--accent-primary)' }}>
                          {typeof value === 'number' ? value.toLocaleString() : value}
                        </span>
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            </div>
          )}

          {aiSearchResult.notes && (
            <div style={{
              marginTop: '12px',
              padding: '12px',
              background: 'var(--color-neutral-bg)',
              borderRadius: '6px',
              border: '1px solid var(--color-neutral-bg)',
              fontSize: '13px',
              color: 'var(--color-neutral)'
            }}>
              <strong>📝 Notes:</strong> {aiSearchResult.notes}
            </div>
          )}

          {aiSearchResult.trend_analysis && (
            <div style={{
              marginTop: '16px',
              padding: '12px',
              background: 'var(--canvas-surface)',
              borderRadius: '6px',
              border: '1px solid var(--color-bullish-bg)'
            }}>
              <strong style={{ color: 'var(--color-bullish)' }}>📈 Historical Trend Analysis (Passed to Step 8):</strong>
              <div style={{ marginTop: '12px', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px' }}>
                {aiSearchResult.trend_analysis.growth_rates && (
                  <div style={{ padding: '12px', background: 'var(--accent-primary-subtle)', borderRadius: '6px' }}>
                    <strong style={{ color: 'var(--accent-primary)', display: 'block', marginBottom: '8px' }}>Growth Rates (CAGR)</strong>
                    {aiSearchResult.trend_analysis.growth_rates.revenue_cagr !== null && (
                      <div style={{ fontSize: '13px', marginBottom: '4px' }}>
                        Revenue: {(aiSearchResult.trend_analysis.growth_rates.revenue_cagr * 100).toFixed(2)}%
                      </div>
                    )}
                    {aiSearchResult.trend_analysis.growth_rates.net_income_cagr !== null && (
                      <div style={{ fontSize: '13px', marginBottom: '4px' }}>
                        Net Income: {(aiSearchResult.trend_analysis.growth_rates.net_income_cagr * 100).toFixed(2)}%
                      </div>
                    )}
                    {aiSearchResult.trend_analysis.growth_rates.ebitda_cagr !== null && (
                      <div style={{ fontSize: '13px' }}>
                        EBITDA: {(aiSearchResult.trend_analysis.growth_rates.ebitda_cagr * 100).toFixed(2)}%
                      </div>
                    )}
                  </div>
                )}
                {aiSearchResult.trend_analysis.averages && (
                  <div style={{ padding: '12px', background: 'rgba(124, 58, 237, 0.08)', borderRadius: '6px' }}>
                    <strong style={{ color: 'var(--color-manual)', display: 'block', marginBottom: '8px' }}>Historical Averages</strong>
                    {aiSearchResult.trend_analysis.averages.revenue_avg !== null && (
                      <div style={{ fontSize: '13px', marginBottom: '4px' }}>
                        Revenue: {aiSearchResult.trend_analysis.averages.revenue_avg.toLocaleString(undefined, { notation: 'compact' })}
                      </div>
                    )}
                    {aiSearchResult.trend_analysis.averages.net_margin_avg !== null && (
                      <div style={{ fontSize: '13px' }}>
                        Net Margin: {(aiSearchResult.trend_analysis.averages.net_margin_avg * 100).toFixed(2)}%
                      </div>
                    )}
                  </div>
                )}
                {aiSearchResult.trend_analysis.trend_direction && (
                  <div style={{ padding: '12px', background: 'var(--color-bullish-bg)', borderRadius: '6px' }}>
                    <strong style={{ color: 'var(--color-bullish)', display: 'block', marginBottom: '8px' }}>Trend Direction</strong>
                    <div style={{ fontSize: '13px', marginBottom: '4px' }}>
                      Revenue: {aiSearchResult.trend_analysis.trend_direction.revenue === 'up' ? '↑' : aiSearchResult.trend_analysis.trend_direction.revenue === 'down' ? '↓' : '→'}
                    </div>
                    <div style={{ fontSize: '13px' }}>
                      Net Income: {aiSearchResult.trend_analysis.trend_direction.net_income === 'up' ? '↑' : aiSearchResult.trend_analysis.trend_direction.net_income === 'down' ? '↓' : '→'}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* AI Web Search Error */}
      {aiSearchError && (
        <div style={{
          background: 'var(--color-bearish-bg)',
          border: '2px solid var(--color-bearish)',
          padding: '20px',
          borderRadius: '8px',
          marginBottom: '20px'
        }}>
          <h3 style={{ color: 'var(--color-bearish)', margin: '0 0 12px 0' }}>❌ AI Web Search Failed</h3>
          <p style={{ margin: '0', color: 'var(--color-bearish)' }}>{aiSearchError}</p>
          <button
            onClick={() => handleAiWebSearch(null)}
            className="btn-secondary"
            style={{ marginTop: '12px' }}
          >
            🔄 Retry AI Search
          </button>
        </div>
      )}

      {/* SEC EDGAR Fetch Error */}
      {secFetchError && (
        <div style={{
          background: 'var(--color-bearish-bg)',
          border: '2px solid var(--color-bearish)',
          padding: '20px',
          borderRadius: '8px',
          marginBottom: '20px'
        }}>
          <h3 style={{ color: 'var(--color-bearish)', margin: '0 0 12px 0' }}>❌ SEC EDGAR Fetch Failed</h3>
          <p style={{ margin: '0', color: 'var(--color-bearish)' }}>{secFetchError}</p>
          <button
            onClick={() => setShowSecEdgarModal(true)}
            className="btn-secondary"
            style={{ marginTop: '12px' }}
          >
            🔄 Retry SEC Fetch
          </button>
        </div>
      )}

      {/* SEC EDGAR Modal */}
      {showSecEdgarModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full">
            <div className="p-6 border-b border-gray-200">
              <h3 className="text-xl font-bold text-gray-800">🏛️ SEC EDGAR Configuration</h3>
              <p className="mt-2 text-sm text-gray-600">
                Enter your email address to fetch SEC filings. This is required for rate limit compliance.
              </p>
            </div>
            
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Email Address
                </label>
                <input
                  type="email"
                  value={secEdgarEmail}
                  onChange={(e) => setSecEdgarEmail(e.target.value)}
                  placeholder="your-email@company.com"
                  className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
                <p className="mt-1 text-xs text-gray-500">
                  Format: Company Name (email@domain.com) - e.g., "Acme Corp (admin@acme.com)"
                </p>
              </div>

              {secFetchError && (
                <div className="bg-red-50 border border-red-200 rounded-md p-3">
                  <p className="text-sm text-red-700">{secFetchError}</p>
                </div>
              )}

              {secFetchResult && (
                <div className="bg-green-50 border border-green-200 rounded-md p-3 space-y-2">
                  <p className="text-sm text-green-700 font-medium">✓ Successfully fetched {secFetchResult.filings_count} SEC filings</p>
                  {secFetchResult.xbrl_data && secFetchResult.xbrl_data_years > 0 && (
                    <div className="text-xs text-green-600">
                      <p className="font-semibold">XBRL Balance Sheet Data Extracted ({secFetchResult.xbrl_data_years} years):</p>
                      <ul className="mt-1 ml-4 list-disc">
                        {secFetchResult.xbrl_data.ppe_gross && Object.keys(secFetchResult.xbrl_data.ppe_gross).length > 0 && (
                          <li>PP&E Gross: {Object.keys(secFetchResult.xbrl_data.ppe_gross).sort().reverse().join(', ')}</li>
                        )}
                        {secFetchResult.xbrl_data.accumulated_depreciation && Object.keys(secFetchResult.xbrl_data.accumulated_depreciation).length > 0 && (
                          <li>Accumulated Depreciation: {Object.keys(secFetchResult.xbrl_data.accumulated_depreciation).sort().reverse().join(', ')}</li>
                        )}
                      </ul>
                    </div>
                  )}
                  {!secFetchResult.xbrl_data && (
                    <p className="text-xs text-amber-600">⚠️ XBRL extraction unavailable — only filing metadata retrieved</p>
                  )}
                </div>
              )}
            </div>

            <div className="p-6 border-t border-gray-200 bg-gray-50 rounded-b-lg flex justify-between items-center">
              <button
                onClick={() => setShowSecEdgarModal(false)}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleSecEdgarFetch}
                disabled={fetchingSecData || !secEdgarEmail || !ticker}
                className="px-4 py-2 text-sm font-medium text-white bg-orange-600 rounded-md hover:bg-orange-700 disabled:bg-gray-400"
              >
                {fetchingSecData ? '⏳ Fetching...' : '📥 Fetch SEC Filings'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* SEC EDGAR Results Display (on main page, outside modal) */}
      {secFetchResult && (
        <div style={{
          background: 'var(--color-neutral-bg)',
          border: '2px solid var(--color-neutral)',
          padding: '20px',
          borderRadius: '8px',
          marginBottom: '20px'
        }}>
          <h3 style={{ color: 'var(--color-neutral)', margin: '0 0 12px 0' }}>🏛️ SEC EDGAR Extraction Results</h3>
          
          {/* Filing metadata */}
          {secFetchResult.filings_count > 0 && (
            <div style={{ marginBottom: '12px' }}>
              <p style={{ fontSize: '14px', color: 'var(--color-bearish)' }}>
                ✓ Found <strong>{secFetchResult.filings_count}</strong> SEC filings (10-K/10-Q)
              </p>
              <div style={{ marginTop: '8px', maxHeight: '120px', overflowY: 'auto' }}>
                {secFetchResult.filings?.slice(0, 5).map((f, i) => (
                  <div key={i} style={{ fontSize: '12px', color: 'var(--text-secondary)', padding: '2px 0' }}>
                    • {f.form_type} — Filed: {f.filing_date} {f.report_date ? `(Report: ${f.report_date})` : ''}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* XBRL data — show which missing fields were filled */}
          {secFetchResult.xbrl_data && (
            <div style={{ marginBottom: '12px' }}>
              {secFetchResult.xbrl_data_years > 0 ? (
                <p style={{ fontSize: '14px', color: 'var(--color-bullish)', fontWeight: 600 }}>
                  ✓ XBRL Data Extracted — {secFetchResult.xbrl_data_years} years
                </p>
              ) : secFetchResult.xbrl_fields_extracted > 0 ? (
                <p style={{ fontSize: '14px', color: 'var(--color-bullish)', fontWeight: 600 }}>
                  ✓ XBRL Data Extracted — {secFetchResult.xbrl_fields_extracted} fields (no yearly breakdown)
                </p>
              ) : (
                <p style={{ fontSize: '14px', color: 'var(--color-neutral)', fontWeight: 600 }}>
                  ⚠️ XBRL extraction attempted — no balance sheet data found for this company
                </p>
              )}
              
              {secFetchResult.xbrl_data_years > 0 && (
                <div style={{ marginTop: '8px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  {secFetchResult.xbrl_data.ppe_gross && Object.keys(secFetchResult.xbrl_data.ppe_gross).length > 0 && (
                    <div style={{ padding: '8px 12px', background: 'var(--canvas-surface)', borderRadius: '4px', border: '1px solid var(--color-bullish-bg)' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--color-bullish)' }}>PP&E Gross</span>
                        {criticalMissing.some(m => { const l = m.toLowerCase().replace(/[^a-z]/g, ''); return l.includes('ppe') || l.includes('property'); }) && (
                          <span style={{ fontSize: '11px', background: 'var(--color-bullish-bg)', color: 'var(--color-bullish)', padding: '2px 6px', borderRadius: '3px' }}>Fills missing input</span>
                        )}
                      </div>
                      <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px' }}>
                        {Object.entries(secFetchResult.xbrl_data.ppe_gross).sort(([a], [b]) => b.localeCompare(a)).slice(0, 5).map(([year, val]) => `${year}: $${(val as number).toLocaleString()}`).join(' | ')}
                      </div>
                    </div>
                  )}
                  {secFetchResult.xbrl_data.accumulated_depreciation && Object.keys(secFetchResult.xbrl_data.accumulated_depreciation).length > 0 && (
                    <div style={{ padding: '8px 12px', background: 'var(--canvas-surface)', borderRadius: '4px', border: '1px solid var(--color-bullish-bg)' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--color-bullish)' }}>Accumulated Depreciation</span>
                        {criticalMissing.some(m => m.toLowerCase().includes('accumulated') || m.toLowerCase().includes('depreciation')) && (
                          <span style={{ fontSize: '11px', background: 'var(--color-bullish-bg)', color: 'var(--color-bullish)', padding: '2px 6px', borderRadius: '3px' }}>Fills missing input</span>
                        )}
                      </div>
                      <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px' }}>
                        {Object.entries(secFetchResult.xbrl_data.accumulated_depreciation).sort(([a], [b]) => b.localeCompare(a)).slice(0, 5).map(([year, val]) => `${year}: $${(val as number).toLocaleString()}`).join(' | ')}
                      </div>
                    </div>
                  )}
                  {secFetchResult.xbrl_data.total_assets && Object.keys(secFetchResult.xbrl_data.total_assets).length > 0 && (
                    <div style={{ padding: '8px 12px', background: 'var(--canvas-surface)', borderRadius: '4px', border: '1px solid var(--accent-primary-subtle)' }}>
                      <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--accent-primary)' }}>Total Assets</span>
                      <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px' }}>
                        {Object.entries(secFetchResult.xbrl_data.total_assets).sort(([a], [b]) => b.localeCompare(a)).slice(0, 5).map(([year, val]) => `${year}: $${(val as number).toLocaleString()}`).join(' | ')}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Mapping summary */}
              {secFetchResult.xbrl_data_years > 0 && (
                <div style={{ marginTop: '10px', padding: '8px', background: 'var(--color-neutral-bg)', borderRadius: '4px', border: '1px solid var(--color-neutral-bg)' }}>
                  <p style={{ fontSize: '12px', color: 'var(--color-neutral)', margin: 0 }}>
                    <strong>Mapping to missing inputs:</strong>
                    {criticalMissing.some(m => m.toLowerCase().includes('accumulated') || m.toLowerCase().includes('depreciation')) && secFetchResult.xbrl_data.accumulated_depreciation && Object.keys(secFetchResult.xbrl_data.accumulated_depreciation).length > 0 && (
                      <span> ✅ Accumulated Depreciation — <strong>filled from XBRL</strong></span>
                    )}
                    {criticalMissing.some(m => { const l = m.toLowerCase().replace(/[^a-z]/g, ''); return l.includes('ppe') || l.includes('property'); }) && secFetchResult.xbrl_data.ppe_gross && Object.keys(secFetchResult.xbrl_data.ppe_gross).length > 0 && (
                      <span> ✅ PP&E Gross — <strong>filled from XBRL</strong></span>
                    )}
                    {(!secFetchResult.xbrl_data.accumulated_depreciation || Object.keys(secFetchResult.xbrl_data.accumulated_depreciation).length === 0) && criticalMissing.some(m => m.toLowerCase().includes('accumulated') || m.toLowerCase().includes('depreciation')) && (
                      <span> ⚠️ Accumulated Depreciation — <strong>not available in XBRL</strong></span>
                    )}
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Validation status */}
          {(!secFetchResult.xbrl_data) && secFetchResult.filings_count === 0 && (
            <p style={{ fontSize: '13px', color: 'var(--color-neutral)' }}>
              ⚠️ No usable data extracted. SEC EDGAR only covers US publicly traded companies.
            </p>
          )}
        </div>
      )}

      {/* PRIMARY DISPLAY: Historical Data Gaps (works for all 3×2 matrix) */}
      {renderHistoricalDataGaps()}

      {/* No data extracted warning */}
      {(!data || Object.keys(data).length === 0) && !aiError && (
        <div className="summary-box" style={{ background: 'var(--canvas-bg)', marginBottom: '20px' }}>
          <h3>⚠️ No AI Extraction Performed</h3>
          <p>AI extraction has not been triggered yet. Click the button below to search for missing historical data.</p>
          {onRetryAiExtraction && (
            <button
              onClick={onRetryAiExtraction}
              className="btn-primary"
              style={{ marginTop: '10px' }}
            >
              🔍 Generate AI Suggestions
            </button>
          )}
        </div>
      )}

      <div style={{ marginTop: '20px', display: 'flex', justifyContent: 'flex-end' }}>
        <button
          onClick={onContinueToForecastDrivers}
          className="btn-next-step"
        >
          Continue to Step 8: Forecast Drivers →
        </button>
      </div>
    </div>
    </>
  );
};

export default HistoricalDataExtractionStep;