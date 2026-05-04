"""
PDF Extraction Routes for Vietnamese Market Reports

API endpoints for:
- Uploading PDF reports
- Extracting financial data from PDFs
- Processing multiple reports
- Downloading reports from Vietnamese sources
"""

import os
import logging
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Form, Query
from pydantic import BaseModel, Field

from app.core.logging_config import get_logger
from app.services.pdf_extraction_service import (
    VietnamesePDFExtractor,
    VietnameseReportDownloader,
    extract_financials_from_pdf,
    process_vietnamese_reports,
    ExtractedFinancialData,
)

logger = get_logger(__name__)

router = APIRouter(tags=["PDF Extraction"])


class ExtractionRequest(BaseModel):
    """Request model for PDF extraction parameters"""
    method: str = Field(default="auto", description="Extraction method: auto, pdfplumber, camelot, tabula, ocr")
    include_raw_tables: bool = Field(default=False, description="Include raw table data in response")


class ExtractionResponse(BaseModel):
    """Response model for PDF extraction"""
    success: bool
    company_name: Optional[str] = None
    ticker: Optional[str] = None
    fiscal_year: Optional[int] = None
    currency: str = "VND"
    report_type: Optional[str] = None
    
    # Income Statement
    revenue: Optional[float] = None
    net_income: Optional[float] = None
    ebitda: Optional[float] = None
    
    # Balance Sheet
    total_assets: Optional[float] = None
    total_equity: Optional[float] = None
    total_debt: Optional[float] = None
    
    # Cash Flow
    operating_cash_flow: Optional[float] = None
    free_cash_flow: Optional[float] = None
    
    # Metadata
    extraction_method: str
    confidence_score: float
    notes: List[str] = []
    
    # Full data (optional)
    full_data: Optional[Dict[str, Any]] = None


class DownloadRequest(BaseModel):
    """Request model for downloading reports"""
    ticker: str = Field(..., description="Stock ticker (e.g., VNM, VCB)")
    year: int = Field(..., description="Fiscal year")
    sources: List[str] = Field(default=["all"], description="Sources to try: hose, cafef, vietstock, all")


class DownloadResponse(BaseModel):
    """Response model for download results"""
    success: bool
    ticker: str
    year: int
    results: List[Dict[str, Any]]


@router.post("/extract", response_model=ExtractionResponse)
async def extract_pdf(
    file: UploadFile = File(..., description="PDF file to extract"),
    method: str = Form(default="auto", description="Extraction method"),
    include_raw_tables: bool = Form(default=False, description="Include raw tables")
):
    """
    Extract financial data from uploaded Vietnamese PDF report.
    
    Supported report types:
    - Annual Reports (Báo cáo thường niên)
    - Financial Statements (Báo cáo tài chính)
    - Prospectus (Bản cáo bạch)
    
    Extraction methods:
    - auto: Automatically detect best method
    - pdfplumber: Best for text-based PDFs with tables
    - camelot: Best for structured table extraction
    - tabula: Alternative table extraction
    - ocr: For scanned documents (requires tesseract)
    """
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    try:
        # Read file content
        content = await file.read()
        
        # Save to temporary location
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        
        try:
            # Extract data
            extractor = VietnamesePDFExtractor(extraction_method=method)
            result = extractor.extract_from_file(tmp_path)
            
            # Convert to dict
            data_dict = extractor.to_dict(result)
            
            # Build response
            response = ExtractionResponse(
                success=True,
                company_name=result.company_name,
                ticker=result.ticker,
                fiscal_year=result.fiscal_year,
                currency=result.currency,
                report_type=result.report_type,
                revenue=result.revenue,
                net_income=result.net_income,
                ebitda=result.ebitda,
                total_assets=result.total_assets,
                total_equity=result.total_equity,
                total_debt=result.total_debt,
                operating_cash_flow=result.operating_cash_flow,
                free_cash_flow=result.free_cash_flow,
                extraction_method=result.extraction_method,
                confidence_score=result.confidence_score,
                notes=result.notes,
            )
            
            if include_raw_tables:
                response.full_data = data_dict
            
            logger.info(f"Successfully extracted data from {file.filename}")
            return response
            
        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
                
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        logger.error(f"Extraction runtime error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")


@router.post("/extract/batch", response_model=List[ExtractionResponse])
async def extract_pdf_batch(
    files: List[UploadFile] = File(..., description="Multiple PDF files"),
    method: str = Form(default="auto", description="Extraction method")
):
    """
    Extract financial data from multiple PDF reports at once.
    
    Useful for processing:
    - Multiple years of annual reports
    - Reports from multiple companies
    - Quarterly financial statements
    """
    results = []
    
    for file in files:
        if not file.filename.lower().endswith('.pdf'):
            results.append(ExtractionResponse(
                success=False,
                extraction_method=method,
                confidence_score=0.0,
                notes=[f"Skipped: {file.filename} is not a PDF"]
            ))
            continue
        
        try:
            content = await file.read()
            
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                tmp.write(content)
                tmp_path = tmp.name
            
            try:
                extractor = VietnamesePDFExtractor(extraction_method=method)
                result = extractor.extract_from_file(tmp_path)
                
                results.append(ExtractionResponse(
                    success=True,
                    company_name=result.company_name,
                    ticker=result.ticker,
                    fiscal_year=result.fiscal_year,
                    revenue=result.revenue,
                    net_income=result.net_income,
                    extraction_method=result.extraction_method,
                    confidence_score=result.confidence_score,
                    notes=result.notes,
                ))
            finally:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                    
        except Exception as e:
            logger.error(f"Failed to process {file.filename}: {e}")
            results.append(ExtractionResponse(
                success=False,
                extraction_method=method,
                confidence_score=0.0,
                notes=[f"Error: {str(e)}"]
            ))
    
    return results


@router.post("/download", response_model=DownloadResponse)
async def download_report(request: DownloadRequest):
    """
    Download Vietnamese financial report from various sources.
    
    Sources:
    - HOSE (Ho Chi Minh Stock Exchange)
    - Cafef.vn
    - Vietstock.vn
    
    Note: Actual downloading depends on source availability and may require
    additional authentication or web scraping implementation.
    """
    downloader = VietnameseReportDownloader()
    
    if not downloader.session:
        raise HTTPException(
            status_code=503,
            detail="Report downloading service unavailable (requests library not installed)"
        )
    
    sources_to_try = request.sources
    if "all" in sources_to_try:
        sources_to_try = ["hose", "cafef", "vietstock"]
    
    results = []
    
    for source in sources_to_try:
        try:
            file_path = None
            
            if source.lower() == "hose":
                file_path = downloader.download_from_hose(request.ticker, request.year)
            elif source.lower() == "cafef":
                file_path = downloader.download_from_cafef(request.ticker, request.year)
            elif source.lower() == "vietstock":
                file_path = downloader.download_from_vietstock(request.ticker, request.year)
            
            results.append({
                'source': source,
                'success': file_path is not None,
                'file_path': file_path,
            })
        except Exception as e:
            results.append({
                'source': source,
                'success': False,
                'error': str(e),
            })
    
    any_success = any(r.get('success', False) for r in results)
    
    return DownloadResponse(
        success=any_success,
        ticker=request.ticker,
        year=request.year,
        results=results
    )


@router.get("/sources")
async def list_sources():
    """
    List available data sources for Vietnamese market reports.
    """
    return {
        "exchanges": [
            {
                "name": "HOSE",
                "full_name": "Ho Chi Minh Stock Exchange",
                "url": "https://hsx.vn",
                "description": "Main stock exchange in Southern Vietnam"
            },
            {
                "name": "HNX",
                "full_name": "Hanoi Stock Exchange",
                "url": "https://hnx.vn",
                "description": "Stock exchange in Northern Vietnam"
            }
        ],
        "financial_portals": [
            {
                "name": "Cafef",
                "url": "https://finance.cafef.vn",
                "description": "Popular financial news and data portal"
            },
            {
                "name": "Vietstock",
                "url": "https://finance.vietstock.vn",
                "description": "Comprehensive financial data provider"
            },
            {
                "name": "FiinPro",
                "url": "https://fiinpro.com",
                "description": "Professional financial data platform"
            }
        ],
        "report_types": [
            {
                "type": "annual_report",
                "vietnamese": "Báo cáo thường niên",
                "description": "Annual report with comprehensive financial data"
            },
            {
                "type": "financial_statement",
                "vietnamese": "Báo cáo tài chính",
                "description": "Quarterly or annual financial statements"
            },
            {
                "type": "prospectus",
                "vietnamese": "Bản cáo bạch",
                "description": "IPO prospectus with detailed company information"
            }
        ],
        "extraction_methods": [
            {
                "method": "auto",
                "description": "Automatically detect best extraction method"
            },
            {
                "method": "pdfplumber",
                "description": "Best for text-based PDFs with tables"
            },
            {
                "method": "camelot",
                "description": "Best for structured table extraction"
            },
            {
                "method": "tabula",
                "description": "Alternative table extraction tool"
            },
            {
                "method": "ocr",
                "description": "For scanned documents (requires tesseract-ocr)"
            }
        ]
    }


@router.get("/supported-companies")
async def list_supported_companies():
    """
    List predefined Vietnamese companies supported by the system.
    """
    vietnamese_companies = {
        "HOSE": [
            {"ticker": "VNM.VN", "name": "Vinamilk", "sector": "Consumer Goods"},
            {"ticker": "VCB.VN", "name": "Vietcombank", "sector": "Banking"},
            {"ticker": "HPG.VN", "name": "Hoa Phat Group", "sector": "Steel"},
            {"ticker": "VIC.VN", "name": "Vingroup", "sector": "Conglomerate"},
            {"ticker": "VRE.VN", "name": "Vincom Retail", "sector": "Real Estate"},
            {"ticker": "MSN.VN", "name": "Masan Group", "sector": "Consumer Goods"},
            {"ticker": "MWG.VN", "name": "Mobile World", "sector": "Retail"},
            {"ticker": "FPT.VN", "name": "FPT Corporation", "sector": "Technology"},
            {"ticker": "SAB.VN", "name": "Sabeco", "sector": "Beverages"},
            {"ticker": "GAS.VN", "name": "PV Gas", "sector": "Energy"},
        ],
        "HNX": [
            # Add HNX-listed companies as needed
        ]
    }
    
    return {
        "total_companies": len(vietnamese_companies["HOSE"]) + len(vietnamese_companies["HNX"]),
        "exchanges": vietnamese_companies,
        "note": "Add .VN suffix when using with yFinance for Vietnamese stocks"
    }
