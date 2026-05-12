**Vietnamese Market Unified Schema Transformers**  
**Overview**  
This directory contains transformation layers that convert Vietnamese market processor outputs to the unified schema format defined in app/api/schemas/unified_step_schemas.py.  
**Architecture**  
**Transformation Flow**  
Vietnamese Processor Output → Unified Transformer → Unified Schema Response  
      (Legacy Format)         (Transformation Layer)   (Frontend Contract)  
   
**Files Created**  
1. **vn_step6_unified_transformer.py** - Step 6: Data Fetch  
- Transforms: vn_DataFetchOutput → UnifiedStep6Response  
- Converts raw time-series dictionaries to HistoricalFinancialsData with DataField wrappers  
- Maps Vietnamese accounting fields to unified field names  
2. **vn_step7_unified_transformer.py** - Step 7: Historical Processing  
- Transforms: vn_HistoricalDataOutput → UnifiedStep7Response  
- Creates ProcessedHistoricalPeriod list with trend analysis  
- Calculates growth rates, margins, and trend directions  
3. **vn_step8_unified_transformer.py** - Step 8: AI Assumptions  
- Transforms: vn_AIAssumptionsOutput → UnifiedStep8Response  
- Groups assumptions by category (Revenue Drivers, Cost & Margins, WACC, etc.)  
- Creates AssumptionInput with historical trendlines and AI suggestions  
4. **vn_step9_10_unified_transformer.py** - Steps 9 & 10: Confirmation & Valuation  
- Transforms: vn_ConfirmationOutput → UnifiedStep9Response  
- Transforms: vn_ValuationOutput → UnifiedStep10Response  
- Creates valuation summaries with sensitivity analysis  
**Key Design Principles**  
**1. Model Integrity**  
- **NO simplification** of calculations or removal of inputs  
- ALL original data preserved exactly as-is  
- Only wrapping structure changes to match unified contract  
**2. DataField Wrapping**  
Vietnamese legacy format uses raw dictionaries:  
{"revenue": {"2023": 1000, "2022": 900, "2021": 800}}  
   
Unified format wraps each field with metadata:  
DataField(  
     value=1000,  
     status=DataStatus.RETRIEVED,  
     source="vietstock",  
     unit="millions_VND",  
     currency="VND",  
     reporting_period="2023",  
     confidence_score=95.0  
 )  
   
**3. Category Mapping**  
Assumptions are grouped into standardized categories:  
- REVENUE_DRIVERS - Growth rates, volume/price splits  
- COST_MARGINS - EBITDA margin, tax rate, operating margin  
- WORKING_CAPITAL - AR days, inventory days, AP days  
- WACC_COMPONENTS - Risk-free rate, beta, cost of debt  
- TERMINAL_VALUE - Terminal growth, exit multiple  
- DUPONT_TARGETS - ROE, ROA, asset turnover targets  
- COMPS_MULTIPLES - EV/EBITDA, P/E, P/B ratios  
**4. Status Tracking**  
Each DataField includes status tracking:  
- RETRIEVED - Data fetched from source (Vietstock, API)  
- CALCULATED - Derived from other fields  
- ESTIMATED - AI-extracted or interpolated  
- MISSING - Not available  
- MANUAL_OVERRIDE - User-provided value  
**Usage Example**  
**Step 6 Transformation**  
from app.services.vietnamese.vn_step6_unified_transformer import VNStep6UnifiedTransformer  
 from app.services.vietnamese.vn_step6_data_fetch_processor import vn_Step6DataFetchProcessor  
   
 # Execute Vietnamese processor  
 processor = vn_Step6DataFetchProcessor()  
 vn_output = await processor.execute(vn_input, session_cache=session)  
   
 # Transform to unified schema  
 transformer = VNStep6UnifiedTransformer()  
 unified_response = transformer.transform(  
     vn_output=vn_output,  
     session_id=session_id,  
     ticker="VCB",  
     market="vietnam",  
     method="DCF",  
     session_cache=session  
 )  
   
 # Return unified response to frontend  
 return unified_response  
   
**Step 8 Transformation**  
from app.services.vietnamese.vn_step8_unified_transformer import VNStep8UnifiedTransformer  
   
 # After generating AI assumptions  
 transformer = VNStep8UnifiedTransformer()  
 unified_response = transformer.transform(  
     vn_output=ai_assumptions_output,  
     session_id=session_id,  
     method="DCF",  
     market="vietnam",  
     ticker="VCB",  
     operation_type="generate_ai"  
 )  
   
**Integration Points**  
**Backend Routes (To Be Updated)**  
The Vietnamese routes in vietnamese_market_data_routes.py need to be updated to:  
1. Call existing Vietnamese processors (unchanged)  
2. Pass outputs through unified transformers  
3. Return unified schema responses  
Example route update pattern:  
@router.post("/vn-step-6-fetch-data", response_model=UnifiedStep6Response)  
 async def fetch_vn_data_unified(request: UnifiedStep6Request):  
     # 1. Get session data  
     session = session_service.get_session_data(request.session_id)  
   
     # 2. Execute Vietnamese processor (existing code)  
     vn_input = vn_DataFetchInput(...)  
     processor = vn_Step6DataFetchProcessor()  
     vn_output = await processor.execute(vn_input, session_cache=session)  
   
     # 3. Transform to unified schema (NEW)  
     transformer = VNStep6UnifiedTransformer()  
     unified_response = transformer.transform(  
         vn_output=vn_output,  
         session_id=request.session_id,  
         ticker=ticker,  
         market="vietnam",  
         method=request.method,  
         session_cache=session  
     )  
   
     # 4. Return unified response  
     return unified_response  
   
**Testing Strategy**  
**Unit Tests**  
Test each transformer independently:  
- Mock Vietnamese processor outputs  
- Verify transformation to unified schema  
- Validate all required fields populated  
- Check DataField wrapper metadata  
**Integration Tests**  
Test full workflow:  
- End-to-end Step 6 → Step 10 flow  
- Verify session cache integration  
- Test all three methods (DCF, DuPont, Comps)  
**Frontend Compatibility**  
Verify unified schemas match frontend expectations:  
- Type safety with Pydantic validation  
- Consistent field naming across markets  
- Proper error handling and missing data flags  
**Migration Path**  
**Phase 1: Create Transformers ✓**  
- Step 6 transformer  
- Step 7 transformer  
- Step 8 transformer  
- Step 9 & 10 transformers  
**Phase 2: Update Routes (Next)**  
- Update Vietnamese routes to use transformers  
- Keep existing processors unchanged  
- Add unified schema response models  
**Phase 3: Frontend Integration (Later)**  
- Update frontend to consume unified schemas  
- Single codebase for both markets  
- Remove market-specific frontend logic  
**Phase 4: Cleanup (Final)**  
- Deprecate legacy response schemas  
- Remove duplicate code paths  
- Consolidate error handling  
**Benefits**  
1. **Single Frontend Codebase** - One UI implementation for both markets  
2. **Type Safety** - Pydantic validation ensures schema compliance  
3. **Maintainability** - Clear separation between business logic and presentation  
4. **Extensibility** - Easy to add new markets following same pattern  
5. **Data Quality** - Consistent status tracking and confidence scoring  
**Notes**  
- Transformers are **pure transformation layers** - no business logic changes  
- All Vietnamese-specific logic remains in existing processors  
- Unified schemas serve as the **single source of truth** for frontend integration  
- Follows the same pattern as International market transformers  
