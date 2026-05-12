"""
API Routes Package

RESTful API endpoints organized by market and functionality:

International Routes (Step-based Workflow):
- /step-1-search - Search for companies
- /step-2-suggest-peers - Suggest peer companies
- /step-3-select-ticker - Select target company
- /step-3-save-peers - Save selected peers
- /step-4-select-models - Select valuation models
- /step-5-prepare-assumptions - Prepare assumptions
- /step-6-fetch-api-data - Fetch financial data
- /step-7-retrieve-historical-data - Retrieve historical data
- /step-8-initialize - Initialize AI assumptions
- /step-9-confirm-assumptions - Confirm assumptions
- /step-10-valuate - Run valuation

Vietnamese Routes (Step-based Workflow):
- /vietnamese/vn-step-5-prepare-assumptions - Prepare assumptions
- /vietnamese/vn-step-6-fetch-data - Fetch financial data
- /vietnamese/vn-step-7-retrieve-historical - Retrieve historical data
- /vietnamese/vn-step-8-initialize - Initialize AI assumptions
- /vietnamese/vn-step-9-confirm-assumptions - Confirm assumptions
- /vietnamese/vn-step-10-run-valuation - Run valuation

Deprecated Legacy Endpoints (DO NOT USE):
- /vietnamese/vn-valuate - DEPRECATED: Use step-based workflow
- /vietnamese/vn-comps - DEPRECATED: Use step-based workflow
- /vietnamese/vn-dupont - DEPRECATED: Use step-based workflow

Utility Routes:
- /pdf/extract - PDF financial statement extraction
- /search - Ticker and company search
- /vietnamese/reports - Vietnamese annual report fetching
"""

# Route blueprints are registered in main.py
# This module documents available endpoints

__all__ = [
    # International step-based workflow routes
    # POST /step-1-search
    # POST /step-2-suggest-peers
    # POST /step-3-select-ticker
    # POST /step-3-save-peers
    # POST /step-4-select-models
    # POST /step-5-prepare-assumptions
    # POST /step-6-fetch-api-data
    # POST /step-7-retrieve-historical-data
    # POST /step-8-initialize
    # POST /step-9-confirm-assumptions
    # POST /step-10-valuate
    
    # Vietnamese step-based workflow routes
    # POST /vietnamese/vn-step-5-prepare-assumptions
    # POST /vietnamese/vn-step-6-fetch-data
    # POST /vietnamese/vn-step-7-retrieve-historical
    # POST /vietnamese/vn-step-8-initialize
    # POST /vietnamese/vn-step-9-confirm-assumptions
    # POST /vietnamese/vn-step-10-run-valuation
    
    # DEPRECATED: Legacy Vietnamese endpoints (DO NOT USE)
    # POST /vietnamese/vn-valuate - DEPRECATED
    # POST /vietnamese/vn-comps - DEPRECATED
    # POST /vietnamese/vn-dupont - DEPRECATED
    
    # Utility routes
    # GET  /vietnamese/vn-info
    # POST /pdf/extract
    # GET  /search/ticker
    # GET  /search/company
    # GET  /vietnamese/reports/annual
]
