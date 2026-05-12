"""
Step 7 Historical Data Enrichment Service

Handles PDF upload extraction and AI web search for historical data.
Keeps routes thin by encapsulating all business logic here.
"""

import logging
import tempfile
import os
from typing import Dict, Any, Optional
from datetime import datetime

from app.core.session_service import session_service
from app.services.pdf_extraction_service import VietnamesePDFExtractor
from app.services.international.step7_ai_web_search import (
    AIWebSearchExtractor,
    calculate_historical_trends
)

logger = logging.getLogger(__name__)


class Step7DataEnrichmentService:
    """
    Service for enriching historical data in Step 7.
    
    Responsibilities:
    - Extract data from uploaded PDF financial reports
    - Perform AI web search for historical data
    - Merge extracted data with existing Step 6 data
    - Calculate historical trends and averages
    - Store enriched data in session
    """
    
    def __init__(self):
        """Initialize the service."""
        self.pdf_extractor = VietnamesePDFExtractor(extraction_method="auto")
        self.ai_extractor = AIWebSearchExtractor()
    
    def extract_from_pdf(
        self,
        session_id: str,
        file_content: bytes,
        filename: str,
        method: str,
        market: str = "international"
    ) -> Dict[str, Any]:
        """
        Extract financial data from uploaded PDF.
        
        Workflow:
        1. Save file temporarily
        2. Extract data using VietnamesePDFExtractor
        3. Get existing Step 6 data
        4. Merge extracted data with Step 6 data (PDF takes priority)
        5. Calculate historical trends
        6. Store results in session
        
        Args:
            session_id: Session identifier
            file_content: PDF file content as bytes
            filename: Original filename
            method: Valuation method (DCF, DUPONT, COMPS)
            market: Market type (international, vietnamese)
            
        Returns:
            Extraction results with metrics and confidence scores
            
        Raises:
            HTTPException: If session not found or extraction fails
        """
        from fastapi import HTTPException
        
        # Validate session
        session = session_service.get_session_data(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Save file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            tmp.write(file_content)
            tmp_path = tmp.name
        
        try:
            # Extract data from PDF
            result = self.pdf_extractor.extract_from_file(tmp_path)
            
            # Convert to dict
            extracted_data = self.pdf_extractor.to_dict(result)
            
            # Get existing Step 6 data
            method_lower = method.lower()
            market_lower = market.lower()
            
            step6_data = session_service.get_session_value(
                session_id,
                "financial_data",
                market=market_lower,
                method=method_lower
            )
            
            if not step6_data:
                step6_data = session_service.get_session_value(session_id, "financial_data")
            
            # Merge extracted data with Step 6 data
            # Priority: PDF extraction > API data
            merged_historical = {}
            
            # Map extracted fields to Step 6 format
            if result.revenue:
                merged_historical['revenue'] = result.revenue
            if result.net_income:
                merged_historical['net_income'] = result.net_income
            if result.ebitda:
                merged_historical['ebitda'] = result.ebitda
            if result.total_assets:
                merged_historical['total_assets'] = result.total_assets
            if result.total_equity:
                merged_historical['total_equity'] = result.total_equity
            if result.operating_cash_flow:
                merged_historical['operating_cash_flow'] = result.operating_cash_flow
            if result.capex:
                merged_historical['capex'] = result.capex
            
            # Build extraction metadata
            extraction_metadata = {
                'source': f'PDF_{filename}',
                'fiscal_year': result.fiscal_year,
                'company_name': result.company_name,
                'extraction_method': result.extraction_method,
                'confidence_score': result.confidence_score,
                'upload_timestamp': datetime.now().isoformat(),
                'extracted_metrics': list(merged_historical.keys())
            }
            
            # Store extracted data in session
            session_service.update_session_data(
                session_id,
                "pdf_extraction_results",
                {
                    **extracted_data,
                    'metadata': extraction_metadata
                },
                market=market_lower,
                method=method_lower
            )
            
            # Update historical data with extracted values
            if step6_data and 'historical_financials' in step6_data:
                # Merge into existing structure
                for key, value in merged_historical.items():
                    step6_data['historical_financials'][key] = value
            
            # Calculate historical trends and averages
            trend_analysis = calculate_historical_trends(
                step6_data.get('historical_financials', {}) if step6_data else merged_historical
            )
            
            # Save updated financial data
            session_service.update_session_data(
                session_id,
                "financial_data",
                step6_data,
                market=market_lower,
                method=method_lower
            )
            
            # Store trend analysis for Step 8
            session_service.update_session_data(
                session_id,
                "historical_trend_analysis",
                trend_analysis,
                market=market_lower,
                method=method_lower
            )
            
            logger.info(
                f"Successfully extracted {len(merged_historical)} metrics from {filename} "
                f"for {session.get('ticker', 'UNKNOWN')} ({method})"
            )
            
            return {
                "success": True,
                "message": f"Extracted {len(merged_historical)} financial metrics from PDF",
                "fiscal_year": result.fiscal_year,
                "company_name": result.company_name,
                "extraction_method": result.extraction_method,
                "confidence_score": result.confidence_score,
                "extracted_metrics": merged_historical,
                "trend_analysis": trend_analysis,
                "notes": result.notes
            }
            
        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    async def extract_from_web_search(
        self,
        session_id: str,
        ticker: str,
        company_name: str,
        method: str,
        market: str = "international"
    ) -> Dict[str, Any]:
        """
        Extract historical data using AI web search.
        
        Workflow:
        1. Get existing Step 6 data for context
        2. Use AIFallbackEngine to query AI providers (Groq → Gemini → Qwen)
        3. Validate and format extracted data
        4. Merge AI data with Step 6 data
        5. Calculate historical trends
        6. Store results in session
        
        Args:
            session_id: Session identifier
            ticker: Stock ticker symbol
            company_name: Full company name
            method: Valuation method (DCF, DUPONT, COMPS)
            market: Market type (international, vietnamese)
            
        Returns:
            Extraction results with time series data, metadata, and source URLs
            
        Raises:
            HTTPException: If session not found or AI search fails
        """
        from fastapi import HTTPException
        
        # Validate session
        session = session_service.get_session_data(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get existing Step 6 data for merging
        method_lower = method.lower()
        market_lower = market.lower()
        
        step6_data = session_service.get_session_value(
            session_id,
            "financial_data",
            market=market_lower,
            method=method_lower
        )
        
        if not step6_data:
            step6_data = session_service.get_session_value(session_id, "financial_data")
        
        # Perform AI web search and extraction
        result = await self.ai_extractor.extract_data(
            ticker=ticker,
            company_name=company_name,
            market=market,
            context_data=step6_data
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "AI web search failed")
            )
        
        # Build extraction metadata
        extraction_metadata = {
            'source': 'AI Web Search',
            'provider_used': result['metadata']['provider_used'],
            'confidence_score': result['metadata']['confidence_score'],
            'sources': result['metadata'].get('sources', []),
            'notes': result['metadata'].get('notes', ''),
            'search_timestamp': datetime.now().isoformat(),
            'extracted_metrics': list(result['data'].keys()) if result['data'] else []
        }
        
        # Store results in session
        session_service.update_session_data(
            session_id,
            "ai_web_search_results",
            {
                'time_series': result['data'],
                'metadata': extraction_metadata
            },
            market=market_lower,
            method=method_lower
        )
        
        # Update historical data with AI-extracted values
        if step6_data:
            if 'historical_financials' not in step6_data:
                step6_data['historical_financials'] = {}
            
            # Merge AI data into existing structure
            for date_key, metrics in result['data'].items():
                if date_key not in step6_data['historical_financials']:
                    step6_data['historical_financials'][date_key] = metrics
                else:
                    # Fill gaps in existing data with AI data
                    for metric, value in metrics.items():
                        if step6_data['historical_financials'][date_key].get(metric) is None and value is not None:
                            step6_data['historical_financials'][date_key][metric] = value
        
        # Calculate historical trends and averages
        trend_analysis = calculate_historical_trends(
            step6_data.get('historical_financials', {}) if step6_data else result['data']
        )
        
        # Save updated financial data
        session_service.update_session_data(
            session_id,
            "financial_data",
            step6_data,
            market=market_lower,
            method=method_lower
        )
        
        # Store trend analysis for Step 8
        session_service.update_session_data(
            session_id,
            "historical_trend_analysis",
            trend_analysis,
            market=market_lower,
            method=method_lower
        )
        
        logger.info(
            f"Successfully extracted data via AI web search for {ticker} ({company_name}) "
            f"using {result['metadata']['provider_used']}"
        )
        
        return {
            "success": True,
            "message": f"Successfully extracted data using {result['metadata']['provider_used']}",
            "provider_used": result['metadata']['provider_used'],
            "confidence_score": result['metadata']['confidence_score'],
            "sources": result['metadata'].get('sources', []),
            "time_series": result['data'],
            "trend_analysis": trend_analysis,
            "notes": result['metadata'].get('notes', '')
        }
