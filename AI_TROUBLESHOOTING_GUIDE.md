# AI Provider Status & Troubleshooting Guide

## Current Status (As of Test Run)

### Provider Configuration
- ✅ **Groq**: Configured (API key present)
- ✅ **Gemini**: Configured (API key present)  
- ❌ **Qwen**: Not configured (no API key)

### Test Results
```
❌ GROQ: Error code: 401 - Invalid API Key
❌ GEMINI: 404 - Model 'gemini-pro' not found for API version v1beta
⚠️ All AI providers failed. Using deterministic fallback rules.
```

## Root Causes

### 1. Groq API Key Invalid (401 Error)
**Problem**: The Groq API key `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` is expired or invalid.

**Solution**:
1. Go to https://console.groq.com/keys
2. Revoke the old key immediately (it's exposed in logs)
3. Generate a new API key
4. Update `/workspace/backend/.env`:
   ```
   GROQ_API_KEY=your_new_groq_key_here
   ```
5. Restart the backend server

### 2. Gemini Model Not Found (404 Error)
**Problem**: The model `gemini-pro` is not available with the current API key/version.

**Possible Causes**:
- API key doesn't have access to this model
- Model name is incorrect for the API version
- The deprecated `google.generativeai` package needs updating

**Solutions**:

#### Option A: Use correct model name
Update `.env`:
```
GEMINI_MODEL=gemini-1.5-pro
```

#### Option B: Check available models
Run this test script:
```python
import google.generativeai as genai
genai.configure(api_key='YOUR_GEMINI_KEY')
for model in genai.list_models():
    if 'generateContent' in str(model.supported_generation_methods):
        print(model.name)
```

#### Option C: Switch to new SDK
The warning shows the old SDK is deprecated. Consider migrating to `google.genai`.

### 3. Fallback System Working Correctly ✅
When all AI providers fail, the system correctly:
- Tracks detailed error messages from each provider
- Falls back to deterministic rule-based calculations
- Returns complete assumption data with clear sourcing
- Provides transparency about using fallback mode

## Error Handling Improvements Made

### Backend (`ai_engine.py`)
✅ Multi-tier fallback: Groq → Gemini → Qwen
✅ Detailed error tracking per provider in `provider_errors` dict
✅ Clear fallback reason in response metadata
✅ Deterministic fallback with rationale and sources

### Frontend (`RequirementsStep.jsx`)
✅ Displays detailed provider-specific errors
✅ Shows which providers failed and why
✅ Provides clear next steps for users
✅ Explains fallback mode usage

## Recommended Actions

### Immediate (Required)
1. **Revoke and regenerate Groq API key** - The current key is compromised
2. **Verify Gemini API key permissions** - Ensure it has access to generative models
3. **Test with valid credentials** before production use

### Short-term Improvements
1. Add environment variable validation on startup
2. Implement API key health check endpoint
3. Add retry logic with exponential backoff
4. Cache successful AI responses to reduce API calls

### Long-term Enhancements
1. Migrate Gemini to new `google.genai` SDK
2. Add Qwen as third-tier fallback
3. Implement request rate limiting
4. Add monitoring/alerting for AI failures

## Testing Valid Credentials

After updating API keys, test with:

```bash
cd /workspace/backend
python -c "
from app.engines.ai_engine import AIFallbackEngine
import json

engine = AIFallbackEngine()
print('Providers:', engine.get_provider_status())

test_data = {
    'ticker': 'AAPL',
    'financials': {'revenue_ttm': 383e9, 'ebitda_margin_avg': 30.5},
    'market_data': {'beta': 1.25, 'risk_free_rate': 4.5}
}

result = engine.generate_assumptions(test_data, 'dcf')
print('Success:', result['_ai_status']['success'])
print('Provider:', result['_ai_status'].get('provider_used'))
"
```

## Current Fallback Quality

Even without AI, the system provides high-quality assumptions:
- **WACC**: Calculated via CAPM formula with configurable inputs
- **Growth Rates**: Based on historical trends with gradual moderation
- **Margins**: Industry averages and historical performance
- **Working Capital**: Standard industry norms (AR: 45 days, Inv: 60 days, AP: 30 days)
- **Terminal Values**: Conservative estimates based on Fed targets and sector comparables

All fallback values include:
- Clear rationale explaining the calculation
- Source attribution (e.g., "Historical Trend Adj.", "Industry Average")
- Transparent formulas where applicable

## Security Notice

⚠️ **CRITICAL**: The API keys currently in `.env` are exposed in conversation logs and must be revoked immediately:
- Groq: `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`
- Gemini: `AIzaSyC2lANxt0DEUjDY-wiajpu__sGe2Qc9sfA`

Generate new keys and never share them publicly.
