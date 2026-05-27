# API Key Handling Architecture

## Overview

The project implements a **dual-layer API key management system** that supports both:
1. **Server-side defaults** (environment variables) - for admin/deployment configuration
2. **Per-request user keys** (HTTP headers) - for end-user flexibility

This architecture enables users to bring their own API keys while maintaining fallback defaults for deployed instances.

---

## Supported API Keys

### Step 1 Configuration Modal (Frontend)

| Service | Purpose | Priority | Storage Key | Header Name |
|---------|---------|----------|-------------|-------------|
| **Financial Modeling Prep (FMP)** | Peer discovery, financial statements, market data | REQUIRED | `fmp_api_key` | `X-API-Key-FMP` |
| **Alpha Vantage** | Additional market data, technical indicators | REQUIRED | `alpha_vantage_api_key` | `X-API-Key-AlphaVantage` |
| **FRED API** | US Treasury yields (Risk-Free Rate) | OPTIONAL | `fred_api_key` | `X-API-Key-FRED` |
| **SEC EDGAR** | SEC filings (email identifier) | OPTIONAL* | `sec_edgar_email` | `X-API-Key-SECEdgar` |

\* SEC EDGAR is hidden in Step 1, shown only at Step 7 when fetching filings

### AI/LLM Keys (Step 6+)

| Service | Purpose | Storage Location |
|---------|---------|------------------|
| **OpenRouter** | Primary AI provider for Steps 7-8 | Session storage |
| **Groq** | Alternative AI provider | Session storage |
| **Gemini** | Alternative AI provider | Session storage |
| **Qwen/DashScope** | Alternative AI provider | Session storage |

---

## Data Flow Architecture

### 1. Frontend Storage (Browser localStorage)

```javascript
// frontend/src/services/api.js
const getStoredApiKeys = () => ({
  alphaVantage: localStorage.getItem('alpha_vantage_api_key') || '',
  fmp: localStorage.getItem('fmp_api_key') || '',
  fred: localStorage.getItem('fred_api_key') || '',
  secEdgar: localStorage.getItem('sec_edgar_email') || ''
});
```

**Keys stored in localStorage:**
- `alpha_vantage_api_key`
- `fmp_api_key`
- `fred_api_key`
- `sec_edgar_email`

### 2. Request Interceptor (Automatic Injection)

```javascript
// frontend/src/services/api.js - Lines 14-31
const injectApiKeys = (headers = {}) => {
  const apiKeys = getStoredApiKeys();
  
  if (apiKeys.alphaVantage) {
    headers['X-API-Key-AlphaVantage'] = apiKeys.alphaVantage;
  }
  if (apiKeys.fmp) {
    headers['X-API-Key-FMP'] = apiKeys.fmp;
  }
  if (apiKeys.fred) {
    headers['X-API-Key-FRED'] = apiKeys.fred;
  }
  if (apiKeys.secEdgar) {
    headers['X-API-Key-SECEdgar'] = apiKeys.secEdgar;
  }
  
  return headers;
};

// Applied to all requests via axios interceptor (Lines 43-49)
api.interceptors.request.use(
  (config) => {
    config.headers = injectApiKeys(config.headers);
    return config;
  },
  (error) => Promise.reject(error)
);
```

**All API calls automatically include user-provided keys in headers.**

### 3. Backend Middleware (Header Extraction)

```python
# backend/app/middleware/api_key_middleware.py
class APIKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Extract API keys from headers (lowercase as per HTTP/2 spec)
        api_keys = {
            'alpha_vantage': request.headers.get('x-api-key-alphavantage'),
            'fmp': request.headers.get('x-api-key-fmp'),
            'fred': request.headers.get('x-api-key-fred'),
            'sec_edgar': request.headers.get('x-api-key-secedgar'),
        }
        
        # Filter out None values
        api_keys = {k: v for k, v in api_keys.items() if v}
        
        # Attach to request state for downstream access
        request.state.api_keys = api_keys
        
        response = await call_next(request)
        return response
```

**Middleware registered in `backend/app/main.py`:**
```python
app.add_middleware(APIKeyMiddleware)
```

### 4. Service Layer (Key Retrieval with Priority)

Each service implements a **static method** `get_api_key(request)` with this priority:

```
Priority Order:
1. Request header (user-provided) - HIGHEST
2. Environment variable (server default) - FALLBACK
3. None - DEGRADED FUNCTIONALITY
```

#### Example: AlphaVantage Service

```python
# backend/app/services/international/alphavantage_service.py
@staticmethod
def get_api_key(request: Optional[Request] = None) -> Optional[str]:
    # Priority 1: Check request state (from header)
    if request:
        api_keys = getattr(request.state, 'api_keys', {})
        request_key = api_keys.get('alpha_vantage')
        if request_key:
            logger.debug("Using AlphaVantage API key from request header")
            return request_key
    
    # Priority 2: Fallback to environment variable
    env_key = os.getenv('ALPHAVANTAGE_API_KEY') or os.getenv('ALPHA_VANTAGE_API_KEY')
    if env_key:
        logger.debug("Using AlphaVantage API key from environment variable")
        return env_key
    
    # No key available
    logger.warning("AlphaVantage API key not configured")
    return None
```

#### Example: FRED Service

```python
# backend/app/services/international/fred_service.py
@staticmethod
def get_api_key(request: Optional[Request] = None) -> Optional[str]:
    # Priority 1: Check request state (from header)
    if request:
        api_keys = getattr(request.state, 'api_keys', {})
        request_key = api_keys.get('fred')
        if request_key:
            return request_key
    
    # Priority 2: Fallback to environment variable
    env_key = os.getenv('FRED_API_KEY')
    if env_key and env_key != 'your_fred_api_key_here':
        return env_key
    
    return None
```

#### Example: SEC EDGAR Service (Email-based)

```python
# backend/app/services/international/sec_edgar_service.py
@staticmethod
def get_email(request: Optional[Request] = None) -> Optional[str]:
    # Priority 1: Check request state (from header)
    if request:
        api_keys = getattr(request.state, 'api_keys', {})
        request_email = api_keys.get('sec_edgar')
        if request_email:
            return request_email
    
    # Priority 2: Fallback to environment variable
    env_email = os.getenv('SEC_EDGAR_EMAIL')
    if env_email:
        return env_email
    
    return None
```

---

## Server-Side Configuration (.env)

### Required Environment Variables

```bash
# backend/.env

# Alpha Vantage
ALPHAVANTAGE_API_KEY=your_alpha_vantage_key
# OR
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_key

# FRED (Federal Reserve Economic Data)
FRED_API_KEY=your_fred_key

# SEC EDGAR (email for User-Agent header)
SEC_EDGAR_EMAIL=your-email@company.com

# AI Providers (for Steps 7-8)
GROQ_API_KEY=your_groq_key
GEMINI_API_KEY=your_gemini_key
QWEN_API_KEY=your_qwen_key
OPENROUTER_API_KEY=your_openrouter_key
DASHSCOPE_API_KEY=your_dashscope_key
```

### Config Class Implementation

```python
# backend/app/core/config.py
class Settings(BaseSettings):
    # API KEYS section
    groq_api_key: Optional[str] = Field(default=None)
    gemini_api_key: Optional[str] = Field(default=None)
    qwen_api_key: Optional[str] = Field(default=None)
    openrouter_api_key: Optional[str] = Field(default=None)
    alpha_vantage_key: Optional[str] = Field(default=None)
    
    # Aliases for different env var naming conventions
    google_gemini_api_key: Optional[str] = Field(default=None)
    dashscope_api_key: Optional[str] = Field(default=None)
    alpha_vantage_api_key: Optional[str] = Field(default=None)
    alphavantage_api_key: Optional[str] = Field(default=None)
    
    @property
    def effective_alpha_vantage_key(self) -> Optional[str]:
        """Get effective Alpha Vantage API key from multiple possible env vars."""
        return self.alpha_vantage_key or self.alpha_vantage_api_key or self.alphavantage_api_key
```

---

## Session-Based API Key Storage (Steps 6+)

For AI operations (Steps 7-8), API keys are stored **per-session** in addition to header injection:

### Save API Keys Endpoint

```python
# backend/app/api/routes/valuation_routes.py - Line 1376
@router.post("/save-api-keys")
async def save_api_keys(request: SaveApiKeysRequest):
    """
    Step 6: Save API keys to session for AI tools.
    
    Stores API keys securely in the session for use in Step 7+ AI operations.
    Keys are encrypted and stored per-session.
    """
    # Build keys dictionary from request
    api_keys = {}
    if request.openrouter_api_key:
        api_keys["openrouter_api_key"] = request.openrouter_api_key
    if request.alpha_vantage_key:
        api_keys["alpha_vantage_key"] = request.alpha_vantage_key
    if request.groq_api_key:
        api_keys["groq_api_key"] = request.groq_api_key
    if request.gemini_api_key:
        api_keys["gemini_api_key"] = request.gemini_api_key
    if request.qwen_api_key:
        api_keys["qwen_api_key"] = request.qwen_api_key
    
    # Store keys in session under dedicated 'api_keys' section
    session_service.update_session_data(
        request.session_id,
        "api_keys",
        api_keys
    )
```

### Check API Keys Endpoint

```python
# backend/app/api/routes/valuation_routes.py - Line 1442
@router.get("/check-api-keys")
async def check_api_keys(session_id: str):
    """
    Step 6: Check which API keys are configured for a session.
    
    Returns the status of all API keys stored in the session.
    Used by frontend to show configuration status.
    """
    session = session_service.get_session_data(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    api_keys = session.get("api_keys", {})
    
    return {
        "openrouter": api_keys.get("openrouter_api_key") is not None,
        "alpha_vantage": api_keys.get("alpha_vantage_key") is not None,
        "groq": api_keys.get("groq_api_key") is not None,
        "gemini": api_keys.get("gemini_api_key") is not None,
        "qwen": api_keys.get("qwen_api_key") is not None,
    }
```

---

## Frontend Component: ApiKeyModal

### File: `frontend/src/components/ApiKeyModal.jsx`

**Features:**
- Displays all required and optional API keys
- Shows configuration status (✓ Configured / ⚠ Missing)
- Password visibility toggle
- Direct links to obtain API keys
- Saves to localStorage on confirmation
- SEC EDGAR email hidden until Step 7

**UI Structure:**
```jsx
<ApiKeyModal 
  isOpen={boolean}
  onClose={() => {}}
  onSave={(apiKeys) => {}}
/>
```

**Required APIs Section:**
- Financial Modeling Prep (FMP) 🔑
- Alpha Vantage 📊

**Optional APIs Section:**
- FRED API 🏛️
- SEC EDGAR Email 📄 (hidden: true - shown at Step 7)

---

## Usage in Valuation Steps

### Step 1: Search Company
- **User Action:** Opens ApiKeyModal to configure keys
- **Storage:** localStorage
- **Injection:** Automatic via axios interceptor

### Step 4: Peer Discovery
- **Services Used:** 
  - `InstitutionalPeerDiscoveryService` (requires FMP/AlphaVantage)
  - `step4_dcf_discovery`, `step4_dupont_discovery`, `step4_comps_discovery`
- **Key Retrieval:** Via `request.state.api_keys`

### Step 6: Fetch API Data
- **Endpoint:** `POST /api/step-6-fetch-api-data`
- **Data Fields:** 94+ fields with DataField wrappers
- **Key Usage:** AlphaVantage, FMP for market data

### Step 7: Historical Data Extraction
- **Endpoint:** `POST /api/step-7-retrieve-historical-data`
- **Services Used:**
  - `SecEdgarService` (requires email for User-Agent)
  - `Step7DataEnrichmentService`
  - AI web search engines
- **Key Retrieval:** `SecEdgarService.get_email(request)`

### Step 8: AI Assumptions Generation
- **Endpoints:**
  - `POST /api/step-8-initialize`
  - `POST /api/step-8-generate-ai-suggestion`
- **AI Providers:** OpenRouter, Groq, Gemini, Qwen
- **Key Storage:** Session-based + header injection

---

## Security Considerations

### 1. Client-Side Storage
- Keys stored in **browser localStorage** (not cookies)
- Not transmitted unless user explicitly configures them
- Cleared when user clears browser data

### 2. Transmission Security
- All keys sent via **HTTPS headers** (never in URL or body)
- Header names follow convention: `X-API-Key-{ServiceName}`
- Keys logged only in debug mode (without actual values)

### 3. Server-Side Handling
- Keys attached to `request.state` (not global)
- Per-request isolation (no cross-request contamination)
- Session-based storage for AI keys (encrypted in production)

### 4. Priority System Benefits
- **Users can override** server defaults with their own keys
- **Server maintains functionality** even if user doesn't provide keys
- **Graceful degradation** when keys are missing (warnings logged)

---

## Error Handling & Warnings

### Missing Key Scenarios

```python
# AlphaVantage Service
if not self.api_key:
    logger.warning("AlphaVantage API key not provided. Set ALPHAVANTAGE_API_KEY environment variable, or provide via request header.")

# FRED Service
if not self.api_key:
    logger.warning("FRED API key not configured. Risk-free rate data will be unavailable.")

# SEC EDGAR Service
if not email:
    logger.warning("SEC EDGAR email not configured. Filing searches may be rate-limited.")
```

### Frontend Validation

```jsx
// ApiKeyModal.jsx - Lines 124-139
const getPriorityBadge = (service) => {
  const config = getServiceConfig(service);
  if (config.priority === 'required') {
    return <span className="bg-red-100 text-red-800">REQUIRED</span>;
  } else {
    return <span className="bg-blue-100 text-blue-800">OPTIONAL</span>;
  }
};
```

---

## Testing & Debugging

### Check API Key Status

**Frontend Console:**
```javascript
console.log(localStorage.getItem('alpha_vantage_api_key'));
console.log(localStorage.getItem('fmp_api_key'));
console.log(localStorage.getItem('fred_api_key'));
```

**Backend Logs:**
```bash
# Enable debug logging to see key usage
LOG_LEVEL=DEBUG

# Look for these log messages:
"Using AlphaVantage API key from request header"
"Using FRED API key from environment variable"
"SEC EDGAR email not configured"
```

### API Endpoint Testing

```bash
# Check session API keys
curl http://localhost:8000/api/check-api-keys?session_id=your-session-id

# Save API keys to session
curl -X POST http://localhost:8000/api/save-api-keys \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "your-session-id",
    "openrouter_api_key": "your-key",
    "alpha_vantage_key": "your-key"
  }'
```

---

## Summary

The API key handling system follows these principles:

1. **User Control:** Users can provide their own keys via browser UI
2. **Server Fallback:** Admin can set default keys via environment variables
3. **Automatic Injection:** Axios interceptors add keys to all requests
4. **Middleware Extraction:** FastAPI middleware extracts keys to request state
5. **Service Access:** Services retrieve keys via static `get_api_key(request)` methods
6. **Session Storage:** AI keys stored per-session for Steps 7-8
7. **Security:** HTTPS headers, per-request isolation, no logging of actual keys
8. **Graceful Degradation:** System functions with warnings when keys are missing

This architecture supports the **International Market** (current focus) and is ready for **Vietnam Market Version 2** with unified schemas preventing backend-frontend miss-mapping.
