**Step 6 Mapping Analysis - International Market**  
**Current State Assessment**  
**Schema Definitions**  
- **Unified Schema**: /workspace/backend/app/api/schemas/unified_step_schemas.py  
- UnifiedStep6Response with nested structures  
- HistoricalFinancialsData, ForecastDriversData, MarketDataBase, etc.  
- All fields use DataField wrapper with status tracking  
- **Legacy Schema**: /workspace/backend/app/api/schemas/__init__.py  
- FetchDataResponse with simple Dict[str, Any] data field  
- No type safety, no nested structure enforcement  
**Backend Implementation**  
- **Route**: /workspace/backend/app/api/routes/valuation_routes.py  
- Endpoint: POST /step-6-fetch-api-data  
- Returns: FetchDataResponse (legacy schema)  
- Stores in session under financial_data  
- **Processor**: /workspace/backend/app/services/international/step6_dcf_data_review.py  
- Uses local DataField definition (different from unified schema!)  
- Returns Step6DataReviewResponse with different structure  
- Structure: historical_financials.years[] + data_fields[] vs unified's named fields  
**Critical Mismatches Identified**  
***1. *** ***DataField Definition Duplication***  
# In step6_dcf_data_review.py (line 33-44)  
 class DataField(BaseModel):  
     field_name: str  # ← Required!  
     display_name: Optional[str] = None  
     value: Optional[Any] = None  
     unit: str = ""  
     status: DataStatus  
     source: Optional[str] = None  
     formula: Optional[str] = None  
     is_critical: bool = False  
     allow_override: bool = False  
   
 # In unified_step_schemas.py (line 51-73)  
 class DataField(BaseModel):  
     value: Optional[Any] = Field(None, description="Field value")  
     status: DataStatus = Field(DataStatus.RETRIEVED, ...)  
     source: Optional[str] = Field(None, ...)  
     formula: Optional[str] = Field(None, ...)  
     confidence_score: Optional[float] = Field(None, ge=0, le=100, ...)  
     is_missing: bool = Field(False, ...)  
     can_override: bool = Field(True, ...)  
     unit: Optional[str] = Field(None, ...)  
     currency: Optional[str] = Field(None, ...)  
     reporting_period: Optional[str] = Field(None, ...)  
     last_updated: Optional[datetime] = Field(None, ...)  
   
**Problem**: Two incompatible DataField definitions!  
- Legacy requires field_name and status  
- Unified makes value optional, adds metadata fields  
***2. *** ***Historical Financials Structure Mismatch***  
# Legacy (step6_dcf_data_review.py)  
 class HistoricalFinancialsDisplay(BaseModel):  
     years: List[int] = []  
     data_fields: List[DataField] = []  # Flat list with year embedded  
   
 # Unified (unified_step_schemas.py)  
 class HistoricalFinancialsData(BaseModel):  
     revenue: Optional[DataField] = None  
     cogs: Optional[DataField] = None  
     ebitda: Optional[DataField] = None  
     net_income: Optional[DataField] = None  
     # ... named fields for each metric  
   
**Problem**: Completely different data organization!  
- Legacy: Time-series format with years array  
- Unified: Named field format with DataField wrappers  
***3. *** ***Response Schema Mismatch***  
# Legacy returns  
 class Step6DataReviewResponse(BaseModel):  
     historical_financials: HistoricalFinancialsDisplay  
     forecast_drivers: ForecastDriversDisplay  
     market_data: MarketDataDisplay  
     peer_comparables: PeerComparablesDisplay  
     calculated_metrics: CalculatedMetricsDisplay  
     missing_data_summary: MissingDataSummary  
   
 # Unified expects  
 class UnifiedStep6Response(BaseModel):  
     historical_financials: Optional[HistoricalFinancialsData] = None  
     forecast_drivers: Optional[ForecastDriversData] = None  
     market_data: Optional[MarketDataBase] = None  
     dupont_metrics: Optional[DuPontMetricsData] = None  
     comps_multiples: Optional[CompsMultiplesData] = None  
     missing_data_summary: Optional[MissingDataSummary] = None  
   
***4. *** ***Frontend Expectation Gap***  
Frontend components expect:  
- Nested structure with named fields  
- DataField wrappers with value, status, source  
- Consistent structure across all markets  
But receives:  
- Mixed structures depending on which processor runs  
- Different DataField formats  
- No guarantee of field presence  
**Refactoring Strategy**  
**Phase 1: Unify DataField Definition**  
1. Import DataField from unified_step_schemas.py in ALL step 6 processors  
2. Remove local DataField definitions  
3. Update all field creation to use unified format  
**Phase 2: Transform Historical Financials**  
1. Convert from years[] + data_fields[] format to named field format  
2. Each metric becomes a DataField with period metadata  
3. Maintain backward compatibility through transformation layer  
**Phase 3: Update Response Models**  
1. Replace Step6DataReviewResponse with UnifiedStep6Response  
2. Map legacy fields to unified structure  
3. Add transformation logic for complex conversions  
**Phase 4: Update Routes**  
1. Change endpoint to return UnifiedStep6Response  
2. Update session storage to use unified format  
3. Ensure frontend receives consistent structure  
**Files to Modify (International Market)**  
1. /workspace/backend/app/services/international/step6_dcf_data_review.py  
2. /workspace/backend/app/services/international/step6_dupont_data_review.py  
3. /workspace/backend/app/services/international/step6_comps_data_review.py  
4. /workspace/backend/app/services/international/step6_data_review.py  
5. /workspace/backend/app/services/international/step6_data_review_models.py  
6. /workspace/backend/app/api/routes/valuation_routes.py (response model)  
**Testing Checklist**  
- DataField imports work correctly  
- Historical financials transform properly  
- All 3 valuation methods return unified structure  
- Frontend can parse responses without errors  
- Session storage maintains correct format  
- Vietnamese market can implement same pattern  
