# Workflow Alignment Decision Record

**⚠️ CURRENT DEVELOPMENT STATUS: INTERNATIONAL MARKET ONLY**  
Vietnamese market support is planned for **Version 2** (future release). All documentation references to the 3×2 matrix represent the target architecture, but current implementation focuses exclusively on International markets (IFRS/US GAAP).

## Executive Summary

**Decision**: Backend unified schemas define the official workflow. Frontend uses 11 steps for better UX granularity, with Step 11 reserved for future export/reporting functionality. The backend remains at 10 unified steps.

## Final Workflow Structure

### Frontend 11 Steps → Backend 10 Steps Mapping

| Frontend Step | Frontend Name | Backend Step | Backend Name | Status |
|---------------|---------------|--------------|--------------|--------|
| 1 | Search Company | 1 | Company Search | ✓ |
| 2 | Company Overview | 2 | Market Confirmation | ✓ |
| 3 | Select Model | 3 | Method Selection | ✓ |
| 4 | Peer Selection | 4 | Peer Selection | ✓ |
| 5 | Requirements Review | 5 | Assumptions Preparation | ✓ |
| 6 | API Data Review | 6 | Data Fetching | ✓ |
| 7 | Historical Data Extraction | 7 | Historical Data Processing | ✓ |
| 8 | Assumption & AI Suggestion | 8 | Assumptions & AI Suggestion | ✓ |
| 9 | Confirm Assumptions | 9 | Assumptions Confirmation | ✓ |
| 10 | Run Valuation | 10 | Valuation Execution | ✓ |
| 11 | View Results + Export | N/A | UI-only (Step 10 response) | ✓ |

## Critical Workflow Decisions

1. **Steps 3-4 Order**: Model Selection (Step 3) comes BEFORE Peer Selection (Step 4). This ensures the backend knows which valuation method to use when fetching peer-relevant data.

2. **Step 11 Reserved for Export (FUTURE)**: Currently displays results from Step 10 backend response. Future implementation will add PDF/Excel export functionality. No backend changes needed.

3. **Step 8 Naming**: "Assumption & AI Suggestion" - Review AI-suggested assumptions with confidence scores. Maps directly to Backend Step 8.

## Backend Endpoint Mapping

| Endpoint | Frontend Step | Purpose |
|----------|---------------|---------|
| /step-1-search | 1 | Company search |
| /step-2-confirm-market | 2 | Market confirmation |
| /step-3-select-method | 3 | Method/model selection |
| /step-4-select-models | 4 | Peer selection |
| /step-5-prepare-assumptions | 5 | Requirements review |
| /step-6-fetch-api-data | 6 | API data review |
| /step-7-retrieve-historical | 7 | Historical data extraction |
| /step-8-initialize | 8 | Assumption & AI suggestion |
| /step-9-confirm-assumptions | 9 | Confirm assumptions |
| /step-10-valuate | 10 | Run valuation |

**Note**: Backend Step 8 has multiple sub-endpoints:
- /step-8-initialize - Load assumptions
- /step-8-generate-ai-suggestion - AI generation
- Both called from Frontend Step 8

## Implementation Status

**Status**: ✅ COMPLETE

- Frontend uses 11 steps for better UX granularity
- Backend uses 10 unified step schemas
- Step 11 reserved for future export functionality
- All step names aligned between frontend and backend
