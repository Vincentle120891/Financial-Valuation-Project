"""
Vietnamese Financial Report Auto-Fetch API Routes
Provides endpoints to automatically search, download, and extract 
Vietnamese BCTC (Báo cáo tài chính) from official sources.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import logging

from app.services.vietnamese.vietnamese_report_scraper import VietnameseReportScraper
from app.services.pdf_extraction_service import VietnamesePDFExtractor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/vietnamese-reports", tags=["Vietnamese Reports"])


class ReportSearchRequest(BaseModel):
    ticker: str = Field(..., description="Stock ticker (e.g., VNM, VCB)")
    year: int = Field(..., ge=2015, le=2030, description="Fiscal year")
    report_type: str = Field(default="annual", description="annual or quarterly")


class ReportFetchRequest(BaseModel):
    ticker: str = Field(..., description="Stock ticker")
    year: int = Field(..., ge=2015, le=2030, description="Fiscal year")
    report_type: str = Field(default="annual", description="annual or quarterly")
    extract_data: bool = Field(default=True, description="Whether to extract financial data")


@router.post("/search")
async def search_reports(request: ReportSearchRequest):
    """
    Search for available Vietnamese financial reports.
    
    Searches multiple sources:
    - Company official websites
    - HOSE/HNX portals
    - Cafef/Vietstock (fallback)
    
    Returns metadata about found reports without downloading.
    """
    try:
        scraper = VietnameseReportScraper()
        results = scraper.search_reports(
            ticker=request.ticker,
            year=request.year,
            report_type=request.report_type
        )
        
        if not results:
            return {
                "success": False,
                "message": "No reports found",
                "ticker": request.ticker,
                "year": request.year,
                "reports": []
            }
            
        return {
            "success": True,
            "ticker": request.ticker,
            "year": request.year,
            "count": len(results),
            "reports": results
        }
        
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.post("/fetch")
async def fetch_report(request: ReportFetchRequest):
    """
    Fetch (download) a Vietnamese financial report.
    
    Downloads the first available report from search results.
    Optionally extracts financial data using TT99-compliant PDF extraction.
    """
    try:
        scraper = VietnameseReportScraper()
        
        # Search first
        reports = scraper.search_reports(
            ticker=request.ticker,
            year=request.year,
            report_type=request.report_type
        )
        
        if not reports:
            raise HTTPException(
                status_code=404,
                detail=f"No reports found for {request.ticker} ({request.year})"
            )
        
        # Download
        report_info = reports[0]
        filepath = scraper.download_report(report_info)
        
        if not filepath:
            raise HTTPException(
                status_code=500,
                detail="Failed to download report"
            )
        
        result = {
            "success": True,
            "file_path": str(filepath),
            "report_info": report_info,
            "message": "Report downloaded successfully"
        }
        
        # Extract if requested
        if request.extract_data:
            extractor = VietnamesePDFExtractor(extraction_method="auto")
            try:
                extraction_result = extractor.extract_from_file(str(filepath))
                result["extraction"] = {
                    "success": True,
                    "data": extraction_result.to_dict() if hasattr(extraction_result, 'to_dict') else extraction_result
                }
            except Exception as e:
                result["extraction"] = {
                    "success": False,
                    "error": str(e)
                }
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Fetch failed: {e}")
        raise HTTPException(status_code=500, detail=f"Fetch failed: {str(e)}")


@router.post("/auto-fetch-extract")
async def auto_fetch_extract(request: ReportFetchRequest):
    """
    Complete automated workflow: Search → Download → Extract
    
    Single endpoint that performs the entire pipeline.
    Returns extracted financial data in TT99 format.
    """
    try:
        scraper = VietnameseReportScraper()
        extractor = VietnamesePDFExtractor(extraction_method="auto")
        
        result = scraper.auto_fetch_and_extract(
            ticker=request.ticker,
            year=request.year,
            report_type=request.report_type,
            extractor_service=extractor
        )
        
        if not result.get('success'):
            raise HTTPException(
                status_code=404 if 'No reports' in result.get('error', '') else 500,
                detail=result.get('error', 'Unknown error')
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Auto-fetch-extract failed: {e}")
        raise HTTPException(status_code=500, detail=f"Pipeline failed: {str(e)}")


@router.get("/supported-tickers")
async def get_supported_tickers():
    """Get list of Vietnamese tickers with known company websites."""
    supported = {
        "HOSE": [
            "VNM", "VCB", "HPG", "VIC", "VRE", "MSN", "MWG", "FPT", 
            "SAB", "GAS", "VHM", "ACB", "TCB", "MBB", "STB"
        ],
        "HNX": [],
        "UPCOM": []
    }
    
    return {
        "supported_tickers": supported,
        "note": "Additional tickers can be searched via HOSE/HNX portals"
    }


@router.get("/report-types")
async def get_report_types():
    """Get information about Vietnamese report types."""
    return {
        "types": {
            "annual": {
                "vietnamese": "Báo cáo thường niên",
                "description": "Annual report with full financial statements",
                "includes": ["B01 (Balance Sheet)", "B02 (Income Statement)", "B03 (Cash Flow)"]
            },
            "quarterly": {
                "vietnamese": "Báo cáo tài chính quý",
                "description": "Quarterly financial statements",
                "includes": ["B01", "B02", "B03 (optional)"]
            }
        },
        "standards": "Thông Tư 99/2025/TT-BTC (TT99)"
    }
