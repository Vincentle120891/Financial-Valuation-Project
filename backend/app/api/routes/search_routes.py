"""
Search Routes - Step 1 Only

Handles ticker search functionality using Step1 processor.
Uses unified schemas for consistent API contracts.

Single Responsibility: Only handles Step 1 - Search for tickers by symbol or company name.
"""

import logging
from typing import List
from fastapi import APIRouter, HTTPException

from app.core.logging_config import get_logger
from app.api.schemas import (
    UnifiedStep1Request,
    UnifiedStep1Response,
    CompanySearchResult,
    MarketType,
)
from app.services.international.step1_ticker_processor import Step1TickerProcessor

logger = get_logger(__name__)

router = APIRouter(tags=["Step 1 - Search"])

# Initialize processor
step1_processor = Step1TickerProcessor()


@router.post("/step-1-search", response_model=UnifiedStep1Response)
async def search_tickers(request: UnifiedStep1Request):
    """
    Step 1: Search for tickers by symbol or company name.
    Uses Step1TickerProcessor for consistent search logic.
    Returns unified schema response with proper status tracking.

    Args:
        request: UnifiedStep1Request with query, market, and limit parameters

    Returns:
        UnifiedStep1Response with search results and metadata
    """
    logger.info(f"Searching for tickers with query='{request.query}', market='{request.market.value if isinstance(request.market, MarketType) else request.market}'")

    try:
        # Convert market enum to string if needed
        market_str = request.market.value if isinstance(request.market, MarketType) else request.market
        
        results = await step1_processor.search_tickers(query=request.query, market=market_str)

        if not results:
            logger.warning(f"No tickers found for query='{request.query}'")
            return UnifiedStep1Response(
                status="no_results",
                query=request.query,
                market=market_str,
                results=[],
                total_results=0,
                message="No tickers found. Try exact symbol or company name."
            )

        # Convert raw results to CompanySearchResult format
        # FIX Issue #2: Ensure field names match CompanySearchResult schema (ticker, company_name)
        company_results = []
        for r in results:
            company_results.append(CompanySearchResult(
                ticker=r.get('ticker', r.get('symbol', '')),  # Prefer 'ticker', fallback to 'symbol'
                company_name=r.get('company_name', r.get('name', '')),  # Prefer 'company_name', fallback to 'name'
                exchange=r.get('exchange', ''),
                market=r.get('market', market_str),
                sector=r.get('sector'),
                industry=r.get('industry'),
                currency=r.get('currency'),
                country=r.get('country')
            ))

        logger.info(f"Found {len(company_results)} ticker(s) for query='{request.query}'")
        return UnifiedStep1Response(
            status="success",
            query=request.query,
            market=market_str,
            results=company_results,
            total_results=len(company_results),
            message=f"Found {len(company_results)} matching companies"
        )

    except Exception as e:
        logger.error(f"Failed to search tickers: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")
