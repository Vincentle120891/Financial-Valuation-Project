# ⚠️ CRITICAL DEVELOPER GUIDELINES

**READ BEFORE MODIFYING ANY CODE**

This document contains non-negotiable architectural principles for the Financial Valuation Platform. Violating these guidelines will cause system failures, data corruption, and AI hallucination.

---

## 1. Market Separation (DO NOT MERGE MARKETS)

### 🚫 NEVER Create "Generic Displayer" Components

**Problem:** Attempting to merge Vietnamese and International market data into generic components.

**Why It Fails:**
- **Accounting Standards:** VAS/TT99 (Vietnam) vs IFRS/US GAAP (International) - fundamentally different reporting rules
- **Currency Magnitude:** VND is ~25,000x USD - formatting and display logic cannot be unified
- **Market Mechanics:** 
  - Vietnam: Foreign ownership limits, board types (HOSE/HNX/UPCoM), T+2 settlement
  - International: Different exchanges, regulatory frameworks, trading mechanisms

**Correct Approach:**
```jsx
// ✅ CORRECT - Keep separate components
<VietnameseMarketData data={vnData} />
<InternationalMarketData data={intlData} />

// ❌ WRONG - Never do this
<GenericMarketData data={mergedData} market={market} />
```

**Service Layer Exception:**
- Use `UnifiedTransformer` services ONLY for temporary normalization during peer comparison
- Never persist normalized data - always keep original market-specific data intact

---

## 2. Thin Routes, Fat Services

### 🚫 Route Handlers Must NOT Contain Business Logic

**Problem:** Route handlers in `valuation_routes.py` directly fetching data or processing logic.

**Violation Example:**
```python
# ❌ WRONG - Don't do this in valuation_routes.py
@router.post("/step-3-save-peers")
def save_peers(data):
    # Direct data fetching in route handler
    peers = []
    for ticker in data.tickers:
        stock = yf.Ticker(ticker)
        info = stock.info
        peers.append(info)
    return {"peers": peers}
```

**Correct Pattern:**
```python
# ✅ CORRECT - Delegate to service
@router.post("/step-3-save-peers")
def save_peers(data):
    # Only validate and delegate
    result = PeerDiscoveryService.discover_peers(data.tickers, data.market)
    return result
```

**Files to Audit:**
- ✅ `search_routes.py` - Already correctly implemented
- ⚠️ `valuation_routes.py` - Check for direct data fetching (lines 92-161)

---

## 3. Workflow Step Integrity

### 🚫 File Names MUST Match Their Purpose

**Problem:** Files named `step3_historical_processor.py` when they don't handle Step 3's actual purpose (Peer Selection).

**Correct Mapping:**

| Step | Purpose | Correct File | Mismatched Files |
|------|---------|--------------|------------------|
| **3** | Peer Company Selection | `peer_discovery_service.py` | `step3_historical_processor.py` → rename to `mismatch_step3_historical_processor.py` |
| **4** | Model Selection | `step4_selected_models_processor.py` | `step4_forecast_processor.py` → rename to `mismatch_step4_forecast_processor.py` |
| **5** | Required Inputs Display | `step5_required_inputs_processor.py` | `step5_assumptions_processor.py` → rename to `mismatch_step5_assumptions_processor.py` |

**Rule:** If a file name suggests a different purpose than its step number, rename it with `mismatch_` prefix to prevent accidental usage.

**Frontend Impact:**
- Step 5 (`RequirementsStep.jsx`) should ONLY show required inputs list
- Retrieved data tables belong in Step 6 (`ApiDataStep.jsx`)
- Never mix concerns between steps

---

## 4. Single Model Execution

### 🚫 NEVER Run Multiple Models in Parallel

**Problem:** Allowing users to select DCF + DuPont + Comps simultaneously through Steps 7-9.

**Why It Fails:**
- **AI Context Hallucination:** LLMs lose track of which model context they're processing
- **State Race Conditions:** Shared session data gets corrupted by concurrent modifications
- **Data Inconsistency:** Different models require different assumptions for the same fields

**Correct Implementation:**
```jsx
// ✅ CORRECT - Radio buttons enforce single-select
<input 
  type="radio" 
  name="model" 
  value="DCF" 
  checked={selectedModel === 'DCF'}
  onChange={(e) => setSelectedModel(e.target.value)}
/>

// ❌ WRONG - Never use checkboxes
<input 
  type="checkbox" 
  name="model" 
  value="DCF"
/>
```

**Workflow:**
1. User selects ONE model at Step 4 (Radio buttons)
2. Step 6 fetches ALL data for ANY model into shared cache
3. Steps 7-9 process ONLY the selected model
4. User can change model, but must complete full flow for each

---

## 5. Component Responsibilities

### 🚫 UI Components Should NOT Process Data

**Problem:** React components containing business logic or direct API calls.

**Violation Example:**
```jsx
// ❌ WRONG - Component handling logic
function MarketDataDisplay({ ticker }) {
    const [data, setData] = useState(null);
    
    useEffect(() => {
        // Direct API call in component
        const fetchData = async () => {
            const response = await axios.get(`/api/market-data/${ticker}`);
            const processed = calculateMetrics(response.data); // Business logic in UI
            setData(processed);
        };
        fetchData();
    }, [ticker]);
    
    return <div>{/* render */}</div>;
}
```

**Correct Pattern:**
```jsx
// ✅ CORRECT - Component only displays
function MarketDataDisplay({ data }) {
    return (
        <div className="market-data">
            <h3>{data.companyName}</h3>
            <p>P/E: {data.peRatio}</p>
            {/* Pure presentation */}
        </div>
    );
}

// Parent component handles data fetching
function ValuationFlow() {
    const [marketData, setMarketData] = useState(null);
    
    const loadMarketData = async (ticker) => {
        const response = await api.fetchMarketData(ticker);
        setMarketData(response.data);
    };
    
    return <MarketDataDisplay data={marketData} />;
}
```

---

## 6. 3×2 Matrix Architecture

### System Supports: 3 Valuation Methods × 2 Markets

| | **International** | **Vietnam** |
|---|---|---|
| **DCF** | `services/international/dcf_engine.py` | `services/vietnamese/vietnamese_dcf_engine.py` |
| **DuPont** | `services/international/dupont_engine.py` | `services/vietnamese/vietnamese_dupont_engine.py` |
| **Comps** | `services/international/comps_engine.py` | `services/vietnamese/vietnamese_comps_engine.py` |

**Implementation:**
```python
# Data structure ensures strict separation
valuations_data = {
    'international': {
        'DCF': {...},
        'DuPont': {...},
        'Comps': {...}
    },
    'vietnam': {
        'DCF': {...},
        'DuPont': {...},
        'Comps': {...}
    }
}
```

**Never cross-contaminate markets.** Each market has its own:
- Accounting standards
- Currency formatting
- Risk-free rates
- Tax rates
- Data sources

---

## Quick Reference Checklist

Before submitting any PR, verify:

- [ ] No "Generic Displayer" components created
- [ ] Route handlers only validate and delegate
- [ ] File names match their workflow step purpose
- [ ] No parallel model execution enabled
- [ ] Components only display, not process
- [ ] Market separation maintained throughout
- [ ] Mismatched files renamed with `mismatch_` prefix

---

## Related Documentation

- [README.md](../README.md) - Overview and quick start
- [backend/docs/ARCHITECTURE.md](../backend/docs/ARCHITECTURE.md) - Backend architecture details
- [frontend/ARCHITECTURE.md](../frontend/ARCHITECTURE.md) - Frontend architecture details
- [MODEL_INTEGRITY_CONFIG.md](../backend/MODEL_INTEGRITY_CONFIG.md) - Model completeness guidelines

---

**Last Updated:** 2024
**Version:** 2.0
