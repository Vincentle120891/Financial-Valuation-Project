**Unified Schema Implementation Plan**  
   
 **Executive Summary**  
   
 This document outlines the comprehensive strategy to standardize data handling across the **3 Valuation Methods × 2 Market Versions** workflow. The goal is to eliminate mapping errors, ensure type safety, and create a maintainable codebase by enforcing a single source of truth for data structures in all 10 steps.  
   
 ![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANUlEQVR4nO3OMQ2AABAAsSNBCzpfFxNCmJHAjAU2QtIq6DIzW7UHAMBfnGt1V8fHEQAA3rsexO0F3jmX9Q8AAAAASUVORK5CYII=)  
   
 **1. Core Philosophy: "Contract-First" Architecture**  
   
 **The Problem**  
   
 Currently, the project suffers from:  
- **Double Mismatch**: International and Vietnamese backends return different structures.  
- **Frontend Fragility**: React components must guess data shapes or handle multiple formats.  
- **Silent Failures**: Missing fields or type mismatches cause runtime crashes instead of validation errors.  
- **Maintenance Nightmare**: Changing one field requires updating 6+ files (2 markets × 3 methods).  
 **The Solution**  
   
 Adopt a **Unified Schema Strategy** where:  
1. **Pydantic Models are King**: A single set of schema files defines the exact contract for every API step.  
2. **Backend Adapters**: Both International and Vietnamese services must transform their raw data to match these schemas *before* returning responses.  
3. **Frontend Certainty**: The React frontend consumes exactly one data shape per step, regardless of market or method.  
 ![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANElEQVR4nO3OQQmAUBBAwSd8jOHRnNvAkgaxgjcRZhLMNjNHdQUAwF/cq9qr8+sJAACvrQcthQNH2ZiTNQAAAABJRU5ErkJggg==)  
 **2. The Unified Data Structure Standards**  
   
 **2.1. The Golden Rule: Nested **DataField ** Pattern**  
   
 We reject flattened data. All financial metrics must be wrapped in a DataField object to preserve metadata (currency, unit, source, confidence).  
 **Standard Structure:**  
   
 // TypeScript Interface (Frontend)  
   
  interface DataField {  
   
    value: number | null;  
   
    currency?: string;  
   
    unit?: string;  
   
    source?: string;  
   
    is_calculated?: boolean;  
   
    note?: string;  
   
  }  
 interface HistoricalFinancials {  
   
    revenue: DataField[];      // Array of yearly values  
   
    ebitda: DataField[];  
   
    net_income: DataField[];  
   
    // ... all other metrics  
   
  }  
 interface StepResponse {  
   
    status: 'success' | 'error';  
   
    session_id: string;  
   
    historical_financials: HistoricalFinancials;  
   
    market_data?: Record<string, any>;  
   
    errors?: string[];  
   
  }  
**2.2. Why Nested?**  
- **Context Preservation**: Keeps currency/unit attached to the value.  
- **Time-Series Ready**: Arrays naturally handle multi-year history [2021, 2022, 2023].  
- **Type Safety**: Pydantic validates deep nesting; flat keys (revenue_2021) are prone to typos.  
- **Frontend Mapping**: React .map() works naturally with arrays of objects.  
   
 ![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANUlEQVR4nO3OYQ1AABSAwY8JIIKoL4Z8Eoiggn9mu0twy8wc1RkAAH9xbdVa7V9PAAB47X4A9DIEIm50tIwAAAAASUVORK5CYII=)  
   
 **3. Phase 1: Backend Standardization (International & Vietnam)**  
   
 **Step 3.1: Define Master Schemas**  
   
 **Location**: backend/app/schemas/unified_step_schemas.py  
- Create 10 master Pydantic models (UnifiedStep1Response through UnifiedStep10Response).  
- Define shared components: DataField, HistoricalBlock, MarketDataBlock.  
- **Action**: These files are read-only for business logic; they only define structure.  
   
 **Step 3.2: Refactor International Services**  
   
 **Target Files**: backend/app/services/international/step*_*.py  
- **Action**: Import DataField from master schema.  
- **Transformation**:  
- *Before*: {"revenue_2023": 100, "revenue_2022": 90}  
- *After*: {"revenue": [{"value": 100, "year": 2023}, {"value": 90, "year": 2022}]}  
- **Validation**: Wrap final return objects in UnifiedStepXResponse before sending to route.  
- **Scope**: Apply to DCF, DuPont, and Comps engines equally.  
   
 **Step 3.3: Refactor Vietnamese Services**  
   
 **Target Files**: backend/app/services/vietnamese/vietnamese_step*_*.py  
- **Action**: Mirror the International refactoring.  
- **Special Handling**: Ensure VND currency codes and TT99 accounting terms map to the standard English field names defined in the master schema (e.g., map Doanh_thu → revenue).  
- **Consistency**: The output JSON must be byte-for-byte identical in structure to the International output (only values differ).  
   
 **Step 3.4: Route Layer Cleanup**  
   
 **Target Files**: backend/app/api/routes/*.py  
- Remove all inline data manipulation.  
- Routes simply call service → receive validated Pydantic model → return .dict().  
- Add global exception handler to catch Pydantic validation errors and return clear 400 messages.  
   
 ![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANUlEQVR4nO3OYQ1AABSAwY8JIIKoL4Z8Eoiggn9mu0twy8wc1RkAAH9xbdVa7V9PAAB47X4A9DIEIm50tIwAAAAASUVORK5CYII=)  
   
 **4. Phase 2: Frontend Adaptation**  
   
 **Step 4.1: TypeScript Type Definitions**  
   
 **Location**: frontend/src/types/unified.ts  
- Mirror the Python Pydantic models exactly in TypeScript interfaces.  
- Generate these automatically if possible (using pydantic-to-typescript), or maintain manually as the single source of truth.  
   
 **Step 4.2: API Service Layer Refactoring**  
   
 **Location**: frontend/src/services/api.ts (and specific market services)  
- **Remove Market Branching for Structure**: The API caller no longer needs to check "Is this Vietnam?" to parse data.  
- **Unified Fetch Function**:  
- async function fetchStepData(step: number, market: string, method: string) {  
   
    const endpoint = getEndpoint(step, market, method);  
   
    const response = await axios.get(endpoint);  
   
    // Data is now guaranteed to match UnifiedStepXResponse  
   
    return response.data;  
   
  }  
- **Error Handling**: Standardize error toast messages based on the errors array in the unified response.  
   
 **Step 4.3: Component Updates (The "Dumb" Components)**  
   
 **Target**: frontend/src/components/steps/Step6*.jsx  
- **Prop Drilling**: Pass the entire historical_financials object down.  
- **Rendering Logic**:  
- // Before (Fragile)  
   
    
- {data.revenue_2023 || data.revenue?.[2]?.value}  
 // After (Robust)  
   
  {data.historical_financials.revenue.map((field, idx) => (  
   
     <Input  
   
       key={idx}  
   
       value={field.value}  
   
       currency={field.currency}  
   
       note={field.note}  
   
     />  
   
  ))}  
- **Benefit**: Components become "dumb" displayers. They don't know about market logic, only about displaying a DataField.  
   
 **Step 4.4: State Management Simplification**  
   
 **Location**: frontend/src/context/ValuationContext.jsx  
- Consolidate state keys. Instead of vietnam_dcf_revenue and intl_dcf_revenue, use a normalized store:  
- state = {  
   
    valuations: {  
   
      international: { dcf: { step6: {...} }, dupont: {...} },  
   
      vietnam: { dcf: { step6: {...} }, dupont: {...} }  
   
    }  
   
  }  
- Since structures are identical, utility functions (e.g., calculateGrowthRates) can be reused across markets.  
   
 ![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANklEQVR4nO3OQQmAABRAsScYxpg/jkFMYQKvNrCCNxG2BFtmZquOAAD4i3Ot7mr/egIAwGvXA4EGBc18GWY+AAAAAElFTkSuQmCC)  
   
 **5. Implementation Roadmap**  
   
 | | | | |  
   
 |-|-|-|-|  
   
 | **Phase** |  **Step** |  **Action Item** |  **Status** |  **Notes** |  
   
 | **1** | 1.1 | Create unified_step_schemas.py with all 10 steps | ✅ COMPLETE | Master schema file created with DataField wrappers |  
   
 | **1** | 1.2a | Refactor International Step 6 (DCF/DuPont/Comps) | ✅ COMPLETE | Transformer created, route updated, verified |  
   
 | **1** | 1.2b | Refactor International Step 7 (DCF/DuPont/Comps) | ✅ COMPLETE | Transformer created with trend analysis, route updated |  
   
 | **1** | 1.3 | Refactor Vietnamese Step 6 (All models) | ⏳ TODO | Map TT99 fields to unified schema |  
   
 | **1** | 1.3b | Refactor Vietnamese Step 7 (All models) | ⏳ TODO | Map historical data extraction to unified schema |  
   
 | **1** | 1.4 | Verify API responses match schema (Postman tests) | ⏳ TODO | Test all 6 combinations (3 methods × 2 markets) |  
   
 | **2** | 2.1 | Update Frontend TypeScript definitions | ⏳ TODO | Mirror Pydantic models in unified.ts |  
   
 | **2** | 2.2 | Refactor API Service layer to remove branching | ⏳ TODO | Remove market-specific parsing in api.js |  
   
 | **2** | 2.3 | Update Step 6 UI Components to use nested map | ⏳ TODO | Convert to generic DataField displayer |  
   
 | **2** | 2.3b | Update Step 7 UI Components to use nested map | ⏳ TODO | Convert to generic historical data table |  
   
 | **2** | 2.4 | Repeat for remaining Steps (1-5, 8-10) | ⏳ TODO | Apply same pattern to all steps |  
   
 | **3** | 3.1 | End-to-End Testing (Intl & VN, all 3 methods) | ⏳ TODO | Full regression testing |  
   
 | **3** | 3.2 | Performance profiling (ensure nesting doesn't bloat) | ⏳ TODO | Validate JSON size impact |  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANUlEQVR4nO3OMQ2AABAAsSPBCUZfDq7YGVDAgAU2QtIq6DIzW7UHAMBfHGt1V+fXEwAAXrseHCgGBJWaMWkAAAAASUVORK5CYII=)  
   
 **6. Risk Mitigation**  
   
 **Risk: Breaking Existing Functionality**  
- **Mitigation**: Keep old service files intact initially. Create new *_unified.py services. Switch routes one by one.  
- **Testing**: Run existing E2E tests against the new schema endpoints. Compare outputs.  
 **Risk: Frontend Regression**  
- **Mitigation**: Implement a "Adapter Pattern" in the frontend temporarily. If the backend isn't ready, a small utility function transforms the old flat data to the new nested shape so UI work can proceed in parallel.  
 **Risk: Performance Overhead**  
- **Mitigation**: Nesting adds minimal JSON overhead. The benefit of type safety outweighs the few bytes of extra key names. Use pagination for massive datasets (though financial statements are usually small).  
 ![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANUlEQVR4nO3OQQmAABRAsSd4tIF9zPWxpgGsYQVvImwJtszMXp0BAPAX91pt1fH1BACA164HhagENzj41xIAAAAASUVORK5CYII=)  
 **7. Detailed Example: Step 6 Transformation**  
 **Before (International - Flat/Mixed)**  
   
 {  
   
    "revenue": [100, 110, 120],  
   
    "revenue_growth": [null, 0.10, 0.09],  
   
    "currency": "USD"  
   
  }  
**Before (Vietnamese - Raw Bundle)**  
   
 {  
   
    "raw_data": {  
   
      "Doanh_thu_2023": 2500000,  
   
      "Ty_gia": 24000  
   
    }  
   
  }  
**After (Unified Schema - Both Markets)**  
   
 {  
   
    "status": "success",  
   
    "session_id": "abc-123",  
   
    "historical_financials": {  
   
      "revenue": [  
   
        { "value": 100, "year": 2021, "currency": "USD", "unit": "millions" },  
   
        { "value": 110, "year": 2022, "currency": "USD", "unit": "millions" },  
   
        { "value": 120, "year": 2023, "currency": "USD", "unit": "millions" }  
   
      ],  
   
      "revenue_growth": [  
   
        { "value": null, "year": 2021, "is_calculated": true },  
   
        { "value": 0.10, "year": 2022, "is_calculated": true },  
   
        { "value": 0.09, "year": 2023, "is_calculated": true }  
   
      ]  
   
    }  
   
  }  
*(Note: Vietnamese backend converts VND to USD or keeps VND with * * *currency: "VND"* * * but structure remains identical)*  
   
 ![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANUlEQVR4nO3OMQ2AABAAsSNhQgNa0PYLLpnRgQU2QtIq6DIze3UGAMBf3Gu1VcfXEwAAXrseaIUEMUQwY3IAAAAASUVORK5CYII=)  
   
 **8. Conclusion**  
   
 By enforcing this Unified Schema, we move from a fragile, dual-codebase nightmare to a robust, scalable platform. The "3 Valuation Methods × 2 Market Versions" matrix becomes easy to manage because **the data contract is constant**. Changes to one market do not break the other, and the frontend becomes stable and predictable.  
   
 **Next Immediate Action**: Execute Phase 1, Step 1.1 (Create Master Schemas) and Step 1.2 (Refactor International Step 6).  
