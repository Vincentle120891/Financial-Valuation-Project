**Unified Schemas Implementation Guide**  

**⚠️ CURRENT STATUS: INTERNATIONAL MARKET ONLY**  
Vietnamese market support is planned for **Version 2** (future release). All current development focuses on International markets (IFRS/US GAAP). The unified schema architecture supports both markets, but only International is production-ready.

**Overview**  
This directory now contains the **single source of truth** for all API request/response schemas across the entire valuation platform.  
**Target Architecture: 3 Valuation Methods × 2 Market Versions**  
                    International          Vietnam  
 DCF            ┌─────────────────────┬──────────────────┐  
                │  UnifiedStep6       │  UnifiedStep6    │  
                │  Response           │  Response        │  
                │  (Same Structure)   │  (Same Structure)│  
                └─────────────────────┴──────────────────┘  
   
 DuPont         ┌─────────────────────┬──────────────────┐  
                │  UnifiedStep6       │  UnifiedStep6    │  
                │  Response           │  Response        │  
                │  (Same Structure)   │  (Same Structure)│  
                └─────────────────────┴──────────────────┘  
   
 Comps          ┌─────────────────────┬──────────────────┐  
                │  UnifiedStep6       │  UnifiedStep6    │  
                │  Response           │  Response        │  
                │  (Same Structure)   │  (Same Structure)│  
                └─────────────────────┴──────────────────┘  
   
**Key Files**  
**1. **unified_step_schemas.py ** (MASTER FILE)**  
Contains ALL unified schemas for Steps 1-10:  
- **Core Types**: DataField, DataStatus, ValuationMethod, MarketType, MissingDataSummary  
- **Step 1**: Company Search (UnifiedStep1Request, UnifiedStep1Response)  
- **Step 2**: Company Overview - Display details (NO Find Peers button) (UnifiedStep2Request, UnifiedStep2Response)  
- **Step 3**: Method Selection (UnifiedStep3Request, UnifiedStep3Response)  
- **Step 4**: Find Peers - Click button → Auto-fetch & save top 5 peers (UnifiedStep4Request, UnifiedStep4Response)  
- **Step 5**: Requirements Review - Click "Retrieve Data" button (fetch silently) (UnifiedStep5Request, UnifiedStep5Response)  
- **Step 6**: API Data Review - Auto-calculates all possible inputs, identifies missing inputs (UnifiedStep6Request, UnifiedStep6Response) ⭐ CRITICAL  
- **Step 7**: Historical Data Extraction - Display/review trends, fill remaining gaps (UnifiedStep7Request, UnifiedStep7Response)  
- **Step 8**: Manual Overrides (UnifiedStep8Request, UnifiedStep8Response)  
- **Step 9**: Assumptions Confirmation (UnifiedStep9Request, UnifiedStep9Response)  
- **Step 10**: Valuation Execution (UnifiedStep10Request, UnifiedStep10Response)  
**2. **__init__.py ** (EXPORTS)**  
Re-exports all unified schemas for easy importing throughout the codebase.  
**Core Design Principles**  
**1. Nested Data Structures (NOT Flattened)**  
✅ **CORRECT** - Nested with DataField wrappers:  
historical_financials=HistoricalFinancialsData(  
     revenue=DataField(value=1000000, status="RETRIEVED", source="yfinance"),  
     ebitda=DataField(value=250000, status="CALCULATED", formula="revenue - cogs")  
 )  
   
❌ **WRONG** - Flattened dictionary:  
{  
     "revenue": 1000000,  
     "ebitda": 250000  
 }  
   
**Why Nested?**  
- Preserves context and grouping  
- Enables status tracking per field  
- Supports metadata (source, formula, confidence)  
- Type-safe with Pydantic validation  
- Frontend can directly render tables without transformation  
**2. DataField Wrapper for ALL Values**  
Every numerical or categorical value MUST be wrapped in DataField:  
class DataField(BaseModel):  
     value: Optional[Any]              # The actual value  
     status: DataStatus                # RETRIEVED, CALCULATED, MISSING, etc.  
     source: Optional[str]             # yfinance, vietstock, calculated, user_input  
     formula: Optional[str]            # If calculated  
     confidence_score: Optional[float] # 0-100  
     is_missing: bool                  # Explicit missing flag  
     can_override: bool                # User can modify?  
     unit: Optional[str]               # USD, VND, %, days  
     currency: Optional[str]           # USD, VND  
     reporting_period: Optional[str]   # FY2023, Q1-2024  
     last_updated: Optional[datetime]  # Timestamp  
   
**3. Market Agnostic Structure**  
Both International and Vietnamese markets return THE EXACT SAME structure:  
# International (Apple Inc.)  
 UnifiedStep6Response(  
     ticker="AAPL",  
     market="international",  
     historical_financials=HistoricalFinancialsData(  
         revenue=DataField(value=383285000000, currency="USD", ...)  
     )  
 )  
   
 # Vietnamese (Vinamilk)  
 UnifiedStep6Response(  
     ticker="VNM",  
     market="vietnam",  
     historical_financials=HistoricalFinancialsData(  
         revenue=DataField(value=59000000000000, currency="VND", ...)  
     )  
 )  
   
**Differences handled through field values, NOT structure:**  
- Currency: DataField.currency = "USD" vs "VND"  
- Accounting: Different data sources, same fields  
- Tax rates: Different values, same field names  
**Implementation Checklist**  
**For Backend Developers**  
***Step 6 Implementation - API Data Review (Most Critical)***  
**International Market** (/workspace/backend/app/api/routes/international_market_data_routes.py):  
@router.post("/step-6-fetch-api-data", response_model=UnifiedStep6Response)  
 async def fetch_api_data(request: UnifiedStep6Request):  
     # 1. Fetch from yFinance  
     raw_data = yfinance_service.fetch_ticker_data(ticker)  
   
     # 2. Transform to unified structure  
     response = UnifiedStep6Response(  
         status="success",  
         ticker=ticker,  
         market="international",  
         method=request.method,  
         historical_financials=HistoricalFinancialsData(  
             revenue=DataField(  
                 value=raw_data['revenue'],  
                 status=DataStatus.RETRIEVED,  
                 source="yfinance",  
                 currency="USD"  
             ),  
             # ... all other fields  
         ),  
         data_source="yfinance",  
         fetch_timestamp=datetime.now(),  
         message="Data fetched successfully"  
     )  
   
     return response  
   
**Vietnamese Market** (/workspace/backend/app/api/routes/vietnamese_market_data_routes.py):  
@router.post("/vn-step-6-fetch-data", response_model=UnifiedStep6Response)  
 async def fetch_vn_data(request: UnifiedStep6Request):  
     # 1. Fetch from Vietstock/PDF extraction  
     raw_bundle = vietnamese_service.fetch_raw_data(ticker)  
   
     # 2. TRANSFORM raw bundle to unified structure (CRITICAL!)  
     response = UnifiedStep6Response(  
         status="success",  
         ticker=ticker,  
         market="vietnam",  
         method=request.method,  
         historical_financials=HistoricalFinancialsData(  
             revenue=DataField(  
                 value=raw_bundle['doanh_thu'],  # Map Vietnamese field  
                 status=DataStatus.RETRIEVED,  
                 source="vietstock",  
                 currency="VND"  # Vietnamese currency  
             ),  
             # ... transform ALL fields to match unified structure  
         ),  
         data_source="vietstock",  
         fetch_timestamp=datetime.now(),  
         message="Data fetched successfully"  
     )  
   
     return response  
   
**Key Point**: Vietnamese backend MUST transform its raw data into the unified structure. Do NOT return raw bundles!  
**For Frontend Developers**  
***Step 6 Integration - API Data Review***  
// BEFORE (Broken - different handling per market)  
 if (market === 'vietnam') {  
   const data = await fetch('/vietnamese/vn-step-6-fetch-data', {...});  
   // Parse raw bundle differently  
 } else {  
   const data = await fetch('/step-6-fetch-api-data', {...});  
   // Parse structured data  
 }  
   
 // AFTER (Fixed - unified handling)  
 const response = await fetch(`/api/step-6-fetch-api-data`, {  
   method: 'POST',  
   body: JSON.stringify({  
     session_id,  
     market, // 'international' or 'vietnam'  
     method, // 'DCF', 'DUPONT', or 'COMPS'  
   })  
 });  
   
 const data: UnifiedStep6Response = await response.json();  
   
 // Access data uniformly regardless of market  
 const revenue = data.historical_financials?.revenue?.value;  
 const currency = data.historical_financials?.revenue?.currency;  
 const status = data.historical_financials?.revenue?.status;  
   
**Migration Path**  
**Phase 1: Schema Creation ✅ COMPLETE**  
- Created unified_step_schemas.py with all Step 1-10 schemas  
- Updated __init__.py to export unified schemas  
- Validated imports work correctly  
**Phase 2: Backend Route Updates 🔄 IN PROGRESS**  
***✅ Step 6 - International Market (COMPLETE)***  
1. ✅ Created step6_unified_transformer.py with DCF/DuPont/Comps transformers  
2. ✅ Updated valuation_routes.py/step-6-fetch-api-data endpoint  
3. ✅ Response model changed to UnifiedStep6Response  
4. ✅ All 94+ data fields preserved with DataField wrappers  
***✅ Step 7 - International Market (COMPLETE)***  
1. ✅ Created step7_unified_transformer.py with DCF/DuPont/Comps transformers  
2. ✅ Updated valuation_routes.py/step-7-retrieve-historical-data endpoint  
3. ✅ Response model changed to UnifiedStep7Response  
4. ✅ Added automatic trend analysis (CAGR, avg growth rates)  
5. ✅ Generated comprehensive MissingDataSummary with data quality scoring  
***⏳ Step 6-7 - Vietnamese Market (TODO)***  
1. ⏳ Create Vietnamese transformer for Step 6 (map TT99 fields)  
2. ⏳ Create Vietnamese transformer for Step 7 (map historical extraction)  
3. ⏳ Update vietnamese_market_data_routes.py endpoints  
4. ⏳ Add transformation layer to convert raw bundles → unified structure  
***⏳ Steps 1-5, 8-10 (TODO)***  
1. ⏳ Repeat transformer pattern for remaining steps  
2. ⏳ Update all route endpoints to use unified schemas  
**Phase 3: Frontend Integration (TODO)**  
1. ⏳ Update TypeScript types to match unified schemas (frontend/src/types/unified.ts)  
2. ⏳ Refactor api.js to remove market-branching logic (lines 80-103)  
3. ⏳ Update ApiDataStep.jsx pattern matching to use unified structure  
4. ⏳ Create generic table components for DataField arrays  
5. ⏳ Test all 6 combinations (3 methods × 2 markets)  
**Phase 4: Validation & Testing (TODO)**  
1. ⏳ Add Pydantic validation to all routes  
2. ⏳ Create integration tests for each step  
3. ⏳ Verify data completeness for all methods  
4. ⏳ Test edge cases (missing data, cache hits, etc.)  
5. ⏳ Performance profiling (JSON size impact)  
**Common Pitfalls to Avoid**  
**❌ DON'T: Return Raw Dictionaries**  
# WRONG - No type safety, no structure  
 return {"revenue": 1000000, "ebitda": 250000}  
   
**✅ DO: Use Unified Response Models**  
# CORRECT - Type-safe, validated, structured  
 return UnifiedStep6Response(  
     historical_financials=HistoricalFinancialsData(  
         revenue=DataField(value=1000000, ...),  
         ebitda=DataField(value=250000, ...)  
     )  
 )  
   
**❌ DON'T: Create Market-Specific Structures**  
# WRONG - Causes mapping issues  
 class InternationalResponse(BaseModel): ...  
 class VietnameseResponse(BaseModel): ...  # Different structure!  
   
**✅ DO: Use Single Unified Structure**  
# CORRECT - Same structure, different data  
 class UnifiedStep6Response(BaseModel): ...  # Used by both markets  
   
**❌ DON'T: Flatten Data**  
# WRONG - Loses context, hard to maintain  
 {  
     "revenue_2023": 1000000,  
     "revenue_2022": 950000,  
     "ebitda_2023": 250000  
 }  
   
**✅ DO: Preserve Nested Structure**  
# CORRECT - Maintains grouping and context  
 HistoricalFinancialsData(  
     revenue=DataField(value={2023: 1000000, 2022: 950000}, ...)  
 )  
   
**Benefits**  
1. **No More Mapping Issues**: Single contract prevents mismatches  
2. **Type Safety**: Pydantic validates all inputs/outputs  
3. **Easier Testing**: Same tests work for both markets  
4. **Frontend Simplicity**: One parsing logic for all cases  
5. **Maintainability**: Change schema once, affects all markets  
6. **Extensibility**: Easy to add new markets (China, Thailand, etc.)  
7. **Documentation**: Self-documenting through Pydantic models  
**Support**  
For questions or issues:  
1. Check this guide first  
2. Review unified_step_schemas.py for schema definitions  
3. Look at existing implementations in routes  
4. Consult MODEL_INTEGRITY_CONFIG.md for calculation rules  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANUlEQVR4nO3OMQ2AABAAsSNBCUrfDqrYGVDAgAU2QtIq6DIzW7UHAMBfHGt1V+fXEwAAXrseHCQGBEuErVgAAAAASUVORK5CYII=)  
**Last Updated**: 2024  
   
 **Version**: 1.1  
   
 **Status**: Phase 2 In Progress - Step 6 & 7 International Complete  
**Implementation Summary**  
**Completed Work**  
- ✅ **Phase 1.1**: Master schema file with all 10 steps  
- ✅ **Phase 1.2a**: International Step 6 transformer (DCF/DuPont/Comps)  
- ✅ **Phase 1.2b**: International Step 7 transformer (DCF/DuPont/Comps)  
**Key Features Implemented**  
- **Step 6**: API Data Review - Unified response with 94+ data fields, auto-calculated metrics, and identified missing inputs  
- **Step 7**: Historical data processing with automatic trend analysis (CAGR, growth rates)  
- **Data Quality**: MissingDataSummary with completeness scoring  
- **Backward Compatibility**: Legacy processors preserved, transformation layer added  
**Next Steps**  
1. ⏳ Vietnamese market transformers (Step 6 & 7)  
2. ⏳ Frontend TypeScript definitions  
3. ⏳ API service layer refactoring  
4. ⏳ UI component updates for generic DataField rendering  
