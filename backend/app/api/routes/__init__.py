"""
API Routes Package

RESTful API endpoints organized by market and functionality:

International Routes:
- /international/valuate - DCF valuation for international stocks
- /international/comps - Comparable company analysis
- /international/dupont - DuPont ROE decomposition

Vietnamese Routes:
- /vietnamese/vn-valuate - DCF valuation for Vietnamese stocks
- /vietnamese/vn-comps - Comparable company analysis (VNINDEX/VN30)
- /vietnamese/vn-dupont - DuPont ROE decomposition (TT99)

Utility Routes:
- /pdf/extract - PDF financial statement extraction
- /search - Ticker and company search
- /vietnamese/reports - Vietnamese annual report fetching
"""

# Route blueprints are registered in main.py
# This module documents available endpoints

__all__ = [
    # International routes (international_routes.py)
    # POST /international/valuate
    # POST /international/comps
    # POST /international/dupont
    
    # Vietnamese routes (vietnamese_routes.py)
    # POST /vietnamese/vn-valuate
    # POST /vietnamese/vn-comps
    # POST /vietnamese/vn-dupont
    # GET  /vietnamese/vn-info
    
    # PDF Extraction (pdf_extraction_routes.py)
    # POST /pdf/extract
    
    # Search (search_routes.py)
    # GET  /search/ticker
    # GET  /search/company
    
    # Vietnamese Reports (vietnamese_reports_routes.py)
    # GET  /vietnamese/reports/annual
]
