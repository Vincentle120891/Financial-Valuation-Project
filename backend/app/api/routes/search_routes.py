"""
Search and Ticker Routes

Handles ticker search and selection functionality.
"""

import logging
from typing import List, Dict
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.logging_config import get_logger
from app.api.schemas import SearchRequest, TickerSelectRequest, SearchResponse, SessionCreateResponse, SearchResult

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["Search & Ticker"])


def search_tickers_yahoo(query: str, market: str) -> List[Dict]:
    """Search tickers by symbol or company name"""
    import yfinance as yf
    
    results = []
    
    # Predefined mappings for company name search
    international_companies = {
        "APPLE": {"symbol": "AAPL", "name": "Apple Inc.", "exchange": "NASDAQ"},
        "MICROSOFT": {"symbol": "MSFT", "name": "Microsoft Corporation", "exchange": "NASDAQ"},
        "ALPHABET": {"symbol": "GOOGL", "name": "Alphabet Inc.", "exchange": "NASDAQ"},
        "GOOGLE": {"symbol": "GOOGL", "name": "Alphabet Inc.", "exchange": "NASDAQ"},
        "AMAZON": {"symbol": "AMZN", "name": "Amazon.com Inc.", "exchange": "NASDAQ"},
        "NVIDIA": {"symbol": "NVDA", "name": "NVIDIA Corporation", "exchange": "NASDAQ"},
        "META": {"symbol": "META", "name": "Meta Platforms Inc.", "exchange": "NASDAQ"},
        "FACEBOOK": {"symbol": "META", "name": "Meta Platforms Inc.", "exchange": "NASDAQ"},
        "TESLA": {"symbol": "TSLA", "name": "Tesla Inc.", "exchange": "NASDAQ"},
        "JPMORGAN": {"symbol": "JPM", "name": "JPMorgan Chase & Co.", "exchange": "NYSE"},
        "JPM": {"symbol": "JPM", "name": "JPMorgan Chase & Co.", "exchange": "NYSE"},
        "VISA": {"symbol": "V", "name": "Visa Inc.", "exchange": "NYSE"},
        "BERKSHIRE": {"symbol": "BRK.B", "name": "Berkshire Hathaway Inc.", "exchange": "NYSE"},
        "BRK": {"symbol": "BRK.B", "name": "Berkshire Hathaway Inc.", "exchange": "NYSE"},
    }
    
    vietnamese_companies = {
        "VNM": {"symbol": "VNM.VN", "name": "Vietnam Dairy Products JSC", "exchange": "HOSE"},
        "VINAMILK": {"symbol": "VNM.VN", "name": "Vietnam Dairy Products JSC", "exchange": "HOSE"},
        "VCB": {"symbol": "VCB.VN", "name": "Joint Stock Commercial Bank for Foreign Trade of Vietnam", "exchange": "HOSE"},
        "VIETCOMBANK": {"symbol": "VCB.VN", "name": "Joint Stock Commercial Bank for Foreign Trade of Vietnam", "exchange": "HOSE"},
        "HPG": {"symbol": "HPG.VN", "name": "Hoa Phat Group JSC", "exchange": "HOSE"},
        "VIC": {"symbol": "VIC.VN", "name": "Vingroup JSC", "exchange": "HOSE"},
        "VINGROUP": {"symbol": "VIC.VN", "name": "Vingroup JSC", "exchange": "HOSE"},
        "VRE": {"symbol": "VRE.VN", "name": "Vincom Retail JSC", "exchange": "HOSE"},
        "MSN": {"symbol": "MSN.VN", "name": "Masan Group Corporation", "exchange": "HOSE"},
        "MWG": {"symbol": "MWG.VN", "name": "Mobile World Investment Corporation", "exchange": "HOSE"},
        "FPT": {"symbol": "FPT.VN", "name": "FPT Corporation", "exchange": "HOSE"},
        "SAB": {"symbol": "SAB.VN", "name": "Sabeco - Saigon Beer Alcohol Beverage Corporation", "exchange": "HOSE"},
        "GAS": {"symbol": "GAS.VN", "name": "PetroVietnam Gas JSC", "exchange": "HOSE"},
    }
    
    query_upper = query.upper().strip()
    
    try:
        if market == "vietnamese":
            if query_upper in vietnamese_companies:
                company = vietnamese_companies[query_upper]
                results.append({
                    "symbol": company["symbol"],
                    "name": company["name"],
                    "exchange": company["exchange"],
                    "market": "vietnamese"
                })
            else:
                search_term = query if ".VN" in query else f"{query}.VN"
                ticker = yf.Ticker(search_term)
                if ticker.info and ticker.info.get('symbol'):
                    results.append({
                        "symbol": ticker.info.get('symbol'),
                        "name": ticker.info.get('longName', ticker.info.get('shortName', 'N/A')),
                        "exchange": ticker.info.get('exchange', 'HOSE/HNX'),
                        "market": "vietnamese"
                    })
        else:
            if query_upper in international_companies:
                company = international_companies[query_upper]
                results.append({
                    "symbol": company["symbol"],
                    "name": company["name"],
                    "exchange": company["exchange"],
                    "market": "international"
                })
            else:
                ticker = yf.Ticker(query)
                if ticker.info and ticker.info.get('symbol'):
                    results.append({
                        "symbol": ticker.info.get('symbol'),
                        "name": ticker.info.get('longName', ticker.info.get('shortName', 'N/A')),
                        "exchange": ticker.info.get('exchange', 'US'),
                        "market": "international"
                    })
        
    except Exception as e:
        logger.error(f"Search error for query='{query}', market='{market}': {str(e)}")
        
    return results[:10]


@router.post("/step-1-search", response_model=SearchResponse)
async def search_tickers(request: SearchRequest):
    """
    Step 1 & 2: Search for tickers by symbol or company name.
    
    Args:
        request: Search request with query and market parameters
        
    Returns:
        List of matching tickers
    """
    logger.info(f"Searching for tickers with query='{request.query}', market='{request.market}'")
    
    try:
        results = search_tickers_yahoo(request.query, request.market)
        
        if not results:
            logger.warning(f"No tickers found for query='{request.query}'")
            return SearchResponse(results=[], message="No tickers found. Try exact symbol.")
        
        logger.info(f"Found {len(results)} ticker(s) for query='{request.query}'")
        return SearchResponse(results=[SearchResult(**r) for r in results])
        
    except Exception as e:
        logger.error(f"Failed to search tickers: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.post("/step-3-select-ticker", response_model=SessionCreateResponse)
async def select_ticker(request: TickerSelectRequest):
    """
    Step 3: User chooses ticker and creates a session.
    
    Args:
        request: Ticker selection request
        
    Returns:
        New session ID and status
    """
    from uuid import uuid4
    from datetime import datetime
    
    logger.info(f"Creating session for ticker='{request.ticker}', market='{request.market}'")
    
    try:
        # Import sessions from main app
        from app.main import get_session_store
        
        session_id = str(uuid4())
        sessions = get_session_store()
        
        sessions[session_id] = {
            "status": "ticker_selected",
            "ticker": request.ticker,
            "market": request.market,
            "selected_model": None,
            "financial_data": None,
            "ai_suggestions": None,
            "confirmed_assumptions": None,
            "valuation_result": None,
            "created_at": datetime.now()
        }
        
        logger.info(f"Created session '{session_id}' for ticker='{request.ticker}'")
        return SessionCreateResponse(
            session_id=session_id,
            status="ready_for_model_selection",
            message="Session created successfully"
        )
        
    except Exception as e:
        logger.error(f"Failed to create session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Session creation failed: {str(e)}")
