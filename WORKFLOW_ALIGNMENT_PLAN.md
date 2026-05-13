**Workflow Alignment Decision Record**  

**⚠️ CURRENT DEVELOPMENT STATUS: INTERNATIONAL MARKET ONLY**  
Vietnamese market support is planned for **Version 2** (future release). All documentation references to the 3×2 matrix represent the target architecture, but current implementation focuses exclusively on International markets (IFRS/US GAAP).

**Executive Summary**  
**Decision**: Implement Option A - Align frontend to match backend's unified schema structure.  
**UPDATE**: We will maintain  **11 steps in the frontend** for better UX granularity, with Step 11 reserved for future export/reporting functionality. The backend remains at 10 unified steps.  
**Rationale**: Backend unified schemas are the single source of truth for data processing. Frontend uses 11 steps for better user guidance, with clear mapping to backend's 10 steps.  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANklEQVR4nO3OMQ2AABAAsSNBCkJfFEIwwIgHRiywEZJWQZeZ2ao9AAD+4lyruzq+ngAA8Nr1AOHsBegrsOrIAAAAAElFTkSuQmCC)  
**Final Workflow Structure (As Implemented)**  
**Frontend 11 Steps → Backend 10 Steps Mapping**  
Frontend Step 1: Search Company           → Backend Step 1: Company Search ✓  
 Frontend Step 2: Company Overview         → Backend Step 2: Market Confirmation ✓  
 Frontend Step 3: Select Model             → Backend Step 3: Method Selection ✓ (SWAPPED from peer selection)  
 Frontend Step 4: Peer Selection           → Backend Step 4: Peer Selection ✓ (SWAPPED from model selection)  
 Frontend Step 5: Review Requirements      → Backend Step 5: Assumptions Preparation ✓  
 Frontend Step 6: View Retrieved Inputs    → Backend Step 6: Data Fetching ✓  
 Frontend Step 7: Historical Data Extract  → Backend Step 7: Historical Data Processing ✓  
 Frontend Step 8: Assumption & AI Suggest  → Backend Step 8: Assumptions & AI Suggestion ✓  
 Frontend Step 9: Confirm Assumptions      → Backend Step 9: Assumptions Confirmation ✓  
 Frontend Step 10: Run Valuation           → Backend Step 10: Valuation Execution ✓  
 Frontend Step 11: View Results + Export   → Backend Step 10 Response (UI-only display + future export) ✓  
   
**Critical Changes Implemented**  
1. **Steps 3-4 Order Swap (FIXED)**:  
- **Before**: Peer Selection (3) → Model Selection (4)  
- **After**: Model Selection (3) → Peer Selection (4)  
- **Reason**: Backend needs to know the valuation method BEFORE selecting peers to fetch relevant data  
- **Impact**: Perfect alignment with backend workflow  
2. **Step 11 Reserved for Export (FUTURE)**:  
- Current: Displays results from Step 10 backend response  
- Future: Will add PDF/Excel export functionality  
- **No backend changes needed**: Export will be client-side or separate endpoint  
3. **Step 8 Clarified**:  
- Name: "Assumption & AI Suggestion" (clearer than "Forecast Drivers")  
- Functionality: Review AI-suggested assumptions with confidence scores  
- Maps directly to Backend Step 8  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANUlEQVR4nO3OMQ2AABAAsSPBCj7fFjsymJHAjAU2QtIq6DIzW7UHAMBfnGt1V8fXEwAAXrsexNkF4H1/HJoAAAAASUVORK5CYII=)  
**Historical Context: Previous Mismatch (RESOLVED)**  
The following issues were identified and **resolved** through Option A implementation:  
**Original Frontend 11-Step Workflow (BEFORE FIX)**  
Step 1: Search Company          → Backend Step 1: Company Search ✓  
 Step 2: Company Overview        → Backend Step 2: Market Confirmation ✓  
 Step 3: Peer Selection          → Backend Step 4: Peer Selection ✗ (SKIP 3)  
 Step 4: Select Model            → Backend Step 3: Method Selection ✗ (ORDER SWAPPED)  
 Step 5: Review Requirements     → Backend Step 5: Assumptions Preparation ✓  
 Step 6: View Retrieved Inputs   → Backend Step 6: Data Fetching ✓  
 Step 7: Historical Data Extract → Backend Step 7: Historical Data Processing ✓  
 Step 8: Forecast Drivers        → Backend Step 8: Assumptions & AI Suggestion ✗ (DIFFERENT)  
 Step 9: Confirm Assumptions     → Backend Step 9: Assumptions Confirmation ✓  
 Step 10: Run Valuation          → Backend Step 10: Valuation Execution ✓  
 Step 11: View Results           → NO BACKEND STEP ✗ (UI-ONLY)  
   
**Issues That Were Fixed**  
1. **Steps 3-4 Order Swap (FIXED)**:  
- **Before**: Peer Selection (3) → Model Selection (4)  
- **After**: Model Selection (3) → Peer Selection (4)  
- **Reason**: Backend needs to know the valuation method BEFORE selecting peers  
2. **Step 8 Naming (CLARIFIED)**:  
- **Before**: "Forecast Drivers & DCF Inputs" (confusing, DCF-specific)  
- **After**: "Assumption & AI Suggestion" (method-agnostic)  
3. **Step 11 Purpose (DEFINED)**:  
- **Before**: Just "View Results" (redundant)  
- **After**: "View Results + Export" (reserved for future export functionality)  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANklEQVR4nO3OQQmAABRAsScYxpg/h5VMYARvRrCCNxG2BFtmZquOAAD4i3Ot7mr/egIAwGvXA224BcUMk6pDAAAAAElFTkSuQmCC)  
**Implementation Details (COMPLETED)**  
**Final Frontend Structure (11 Steps Maintained)**  
**Implemented Flow**:  
case 1: <SearchCompanyStep />         // Search Company  
 case 2: <CompanyOverviewStep />       // Company Overview  
 case 3: <ModelSelectionStep />        // Select Model (SWAPPED - was Step 4)  
 case 4: <PeerSelectionStep />         // Peer Selection (SWAPPED - was Step 3)  
 case 5: <ReviewRequirementsStep />    // Review Requirements  
 case 6: <ViewRetrievedInputsStep />   // View Retrieved Inputs  
 case 7: <HistoricalDataExtractStep /> // Historical Data Extraction  
 case 8: <AssumptionAISuggestStep />   // Assumption & AI Suggestion (RENAMED)  
 case 9: <ConfirmAssumptionsStep />    // Confirm Assumptions  
 case 10: <RunValuationStep />         // Run Valuation  
 case 11: <ViewResultsExportStep />    // View Results + Export (FUTURE)  
   
**Key Decisions**:  
1. ✅ **Steps 3-4 Swapped**: Model Selection now comes before Peer Selection  
2. ✅ **11 Steps Maintained**: Step 11 reserved for future export functionality  
3. ✅ **Step 8 Renamed**: "Assumption & AI Suggestion" (method-agnostic)  
4. ✅ **Backend Mapping**: Clear 11→10 mapping documented  
**Progress Indicator (Final Implementation)**  
currentStep === 1 ? 'Search Company' :  
 currentStep === 2 ? 'Company Overview' :  
 currentStep === 3 ? 'Select Model' :             // SWAPPED  
 currentStep === 4 ? 'Peer Selection' :           // SWAPPED  
 currentStep === 5 ? 'Review Requirements' :  
 currentStep === 6 ? 'View Retrieved Inputs' :  
 currentStep === 7 ? 'Historical Data Extraction' :  
 currentStep === 8 ? 'Assumption & AI Suggestion' : // RENAMED  
 currentStep === 9 ? 'Confirm Assumptions' :  
 currentStep === 10 ? 'Run Valuation' :  
 currentStep === 11 ? 'View Results' : 'In Progress'  
   
**Navigation Functions (Updated)**  
// Step 2 → Step 3 (Model Selection, NOT Peer Selection)  
 const handleCompanySelect = async (company) => {  
   // ... create session ...  
   setCurrentStep(3);  // ✅ Go to Model Selection  
 };  
   
 // Step 3 → Step 4 (Peer Selection, after model selected)  
 const handleModelSelect = async (model) => {  
   // ... save model to session ...  
   setCurrentStep(4);  // ✅ Go to Peer Selection  
 };  
   
 // Step 4 → Step 5 (Review Requirements)  
 const handleFindPeers = async (peers) => {  
   // ... save peers ...  
   setCurrentStep(5);  // ✅ Go to Review Requirements  
 };  
   
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANUlEQVR4nO3OMQ2AABAAsSPBCUZfEnoYmFDBhAU2QtIq6DIzW7UHAMBfnGt1V8fXEwAAXrse/wcF74lXkIsAAAAASUVORK5CYII=)  
**Backend Endpoint Mapping (FINAL MAPPING)**  
Backend uses 10 unified steps, Frontend uses 11 steps for better UX:  
# Backend Step → Frontend Step Mapping  
 /step-1-search              → Frontend Step 1 ✓  
 /step-2-confirm-market      → Frontend Step 2 ✓  
 /step-3-select-method       → Frontend Step 3 ✓  
 /step-4-select-models       → Frontend Step 4 ✓  
 /step-5-prepare-assumptions → Frontend Step 5 ✓  
 /step-6-fetch-api-data      → Frontend Step 6 ✓  
 /step-7-retrieve-historical → Frontend Step 7 ✓  
 /step-8-initialize          → Frontend Step 8 ✓  
 /step-9-confirm-assumptions → Frontend Step 9 ✓  
 /step-10-valuate            → Frontend Step 10 ✓  
                             → Frontend Step 11 (Results Display - UI only) ✓  
   
**Note**: Backend Step 8 has multiple sub-endpoints:  
- /step-8-initialize - Load assumptions  
- /step-8-generate-ai-suggestion - AI generation  
- Both called from Frontend Step 8  
**Step 11 (Export)**: Future feature - will use client-side export or separate /api/export-report endpoint  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANUlEQVR4nO3OQQmAABRAsSd49m4v6wg/pwmMYQVvImwJtszMXp0BAPAX91pt1fH1BACA164Hoq8EQMMPmF8AAAAASUVORK5CYII=)  
**Benefits Achieved**  
✅ **Single Source of Truth**: Backend schemas drive workflow structure  
   
 ✅ **Developer Clarity**: Clear mapping between frontend and backend steps  
   
 ✅ **UX Granularity**: 11 frontend steps provide better user guidance  
   
 ✅ **Future-Proof**: Step 11 reserved for export functionality  
   
 ✅ **Consistent with Unified Schema Philosophy**: One workflow, two markets  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANUlEQVR4nO3OMQ2AABAAsSPBCj7fFwtCmJHAjAU2QtIq6DIzW7UHAMBfnGt1V8fHEQAA3rsexOkF3va0dq8AAAAASUVORK5CYII=)  
**Implementation Status (COMPLETED)**  
**Frontend Changes ✅ COMPLETED**  
- Swap Step 3 and Step 4 component rendering order  
- Update navigation functions (handleCompanySelect, handleModelSelect, handleFindPeers)  
- Rename Step 8 to "Assumption & AI Suggestion"  
- Keep 11 steps (Step 11 reserved for future export)  
- Update progress indicator labels  
- Update all back button navigations  
- Test all navigation paths (forward/back)  
**Backend Changes Required**  
- NONE - Backend already follows correct 10-step structure  
**Documentation Updates ✅ COMPLETED**  
- Update WORKFLOW_ALIGNMENT_PLAN.md (this file)  
- Update README.md workflow diagram  
- Update UNIFIED_SCHEMAS_GUIDE.md step references (if exists)  
- Update frontend component comments (ongoing)  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANUlEQVR4nO3OsQ1AABRAwSdRaPXGMOCv7WkPK+hEcjfBLTNzVFcAAPzFvVZbdX49AQDgtf0BSpoDXv5TGXgAAAAASUVORK5CYII=)  
**Risk Assessment (MITIGATED)**  
**Low Risk Changes** (Completed):  
- Step renumbering (cosmetic, no logic changes)  
- Progress indicator updates (UI-only)  
- Navigation function updates (straightforward)  
**Medium Risk Changes** (Avoided):  
- ~~Merging Steps 7-8~~ - NOT DONE, kept separate for clarity  
- ~~Combining Run Valuation + View Results~~ - NOT DONE, Step 11 reserved for export  
**Mitigation Applied**:  
- Thorough testing of each navigation path  
- Verified state persistence across step changes  
- Confirmed matrix data structure access patterns remain valid  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANUlEQVR4nO3OMQ2AABAAsSPBCj7fFwtCmJHAjAU2QtIq6DIzW7UHAMBfnGt1V8fHEQAA3rsexOkF3va0dq8AAAAASUVORK5CYII=)  
**Conclusion (ACHIEVED)**  
Option A implementation provides optimal alignment between frontend UX and backend architecture:  
- **Conceptual clarity**: Clear 11→10 mapping documented  
- **Developer efficiency**: No mental translation needed  
- **User experience**: 11 steps provide better guidance than 10  
- **Maintainability**: Changes to backend steps clearly mapped to frontend  
- **Philosophical consistency**: Upholds "unified schemas as single source of truth" principle  
- **Future-ready**: Step 11 reserved for export/reporting functionality  
**Implementation Date**: 2024  
   
 **Status**: ✅ COMPLETE  
**Recommended Implementation Timeline**: 2-3 days for careful refactoring + testing  
