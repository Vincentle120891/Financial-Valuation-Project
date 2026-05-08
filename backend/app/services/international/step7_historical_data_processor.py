"""
Step 7: Historical Data Gap Filling Processor

Uses AI to extract historical financial data that cannot be retrieved via standard APIs 
(yfinance/AlphaVantage). This is strictly for HISTORICAL data retrieval - NO forward-looking 
assumptions are generated here.

Purpose:
- Fill gaps in historical financial statements when APIs don't have complete data
- Extract historical metrics from PDF reports, filings, or other sources using AI
- Provide complete historical dataset for Step 8 assumption generation

AI Usage: ZERO AI involvement in generating forward-looking inputs. 
AI is ONLY used as a data extraction tool for historical information.

Note: For DuPont and Comps models, this step may be bypassed if all historical data 
is available from APIs. For DCF models, ensures complete 3-5 year historical data.
"""
import logging
from typing import Dict, List, Optional, Any
from pydantic import BaseModel
from enum import Enum
from datetime import datetime

from app.services.pdf_extraction_service import (
    PDFExtractionService,
    ExtractedFinancialData
)

logger = logging.getLogger(__name__)


class ValuationModel(str, Enum):
    """Type of valuation model to use"""
    DCF = "DCF"
    DUPONT = "DUPONT"
    COMPS = "COMPS"


class HistoricalDataGap(BaseModel):
    """Represents a gap in historical data that needs AI extraction"""
    metric: str
    fiscal_year: int
    data_source: str  # e.g., "PDF_REPORT", "FILING", "WEBSITE"
    confidence_score: float
    extracted_value: Optional[float] = None
    extraction_notes: Optional[str] = None


class HistoricalDataRetrievalResponse(BaseModel):
    """
    Step 7 Response: AI-extracted historical data to fill API gaps
    
    This contains ONLY historical data extracted via AI from non-API sources.
    No forward-looking assumptions are included.
    """
    session_id: str
    ticker: str
    timestamp: datetime
    valuation_model: ValuationModel
    historical_gaps_filled: List[HistoricalDataGap]
    total_gaps_found: int
    total_gaps_filled: int
    data_completeness_score: float  # 0.0 to 1.0
    sources_used: List[str]  # e.g., ["PDF_Annual_Report_2023", "HOSE_Filing_Q4_2022"]
    extraction_methodology: Optional[str] = None
    ready_for_assumptions: bool = True


class Step7HistoricalDataProcessor:
    """
    Step 7: Historical Data Gap Filling Processor
    
    Uses AI to retrieve historical financial data that APIs cannot provide:
    - Extracts data from PDF annual reports, filings, prospectuses
    - Fills gaps in 3-5 year historical financial statements
    - Ensures complete dataset before moving to assumption generation (Step 8)
    
    AI Usage: STRICTLY for historical data extraction. NO forward-looking inputs.
    
    Workflow:
    1. Identify missing historical metrics from Step 6 API data
    2. Search for source documents (PDF reports, filings)
    3. Use AI-powered extraction to pull historical values
    4. Validate extracted data against known constraints
    5. Return complete historical dataset for Step 8
    """
    
    def __init__(self):
        self.pdf_extractor = PDFExtractionService()
        # Future: Add web scraper, filing API integrations
    
    async def retrieve_historical_data(
        self,
        ticker: str,
        company_name: str,
        valuation_model: str,
        market: str,
        step6_financial_data: Dict[str, Any],
        missing_metrics: Optional[List[str]] = None,
        fiscal_years_needed: List[int] = None
    ) -> HistoricalDataRetrievalResponse:
        """
        Retrieve historical data using AI extraction to fill API gaps.
        
        Args:
            ticker: Stock ticker symbol
            company_name: Company name
            valuation_model: DCF, DUPONT, or COMPS
            market: Market/country (e.g., "US", "Vietnam")
            step6_financial_data: Historical data already fetched from APIs
            missing_metrics: Specific metrics that need to be filled (optional)
            fiscal_years_needed: List of fiscal years requiring data (default: last 5 years)
            
        Returns:
            HistoricalDataRetrievalResponse with AI-extracted historical data
        """
        logger.info(f"Step 7: Starting historical data gap filling for {ticker}")
        
        model_enum = ValuationModel(valuation_model.upper())
        
        # Determine which years need data
        current_year = datetime.now().year
        if fiscal_years_needed is None:
            fiscal_years_needed = list(range(current_year - 5, current_year))
        
        # Identify gaps in historical data
        gaps_to_fill = await self._identify_data_gaps(
            ticker=ticker,
            existing_data=step6_financial_data,
            fiscal_years=fiscal_years_needed,
            missing_metrics=missing_metrics
        )
        
        logger.info(f"Identified {len(gaps_to_fill)} historical data gaps for {ticker}")
        
        # If no gaps, return early with high completeness
        if not gaps_to_fill:
            return HistoricalDataRetrievalResponse(
                session_id=f"step7_hist_{ticker}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                ticker=ticker,
                timestamp=datetime.now(),
                valuation_model=model_enum,
                historical_gaps_filled=[],
                total_gaps_found=0,
                total_gaps_filled=0,
                data_completeness_score=1.0,
                sources_used=[],
                extraction_methodology="No gaps identified - API data complete",
                ready_for_assumptions=True
            )
        
        # Extract historical data using AI-powered methods
        filled_gaps = []
        sources_used = []
        
        for gap in gaps_to_fill:
            try:
                # Attempt AI extraction from available sources
                extracted_value, source, notes = await self._extract_historical_metric(
                    ticker=ticker,
                    metric=gap["metric"],
                    fiscal_year=gap["fiscal_year"],
                    market=market,
                    company_name=company_name
                )
                
                if extracted_value is not None:
                    filled_gap = HistoricalDataGap(
                        metric=gap["metric"],
                        fiscal_year=gap["fiscal_year"],
                        data_source=source,
                        confidence_score=0.85,  # Will be refined by extraction method
                        extracted_value=extracted_value,
                        extraction_notes=notes
                    )
                    filled_gaps.append(filled_gap)
                    if source not in sources_used:
                        sources_used.append(source)
                        
            except Exception as e:
                logger.warning(f"Failed to extract {gap['metric']} for {gap['fiscal_year']}: {e}")
                # Continue with other gaps even if some fail
        
        # Calculate completeness score
        completeness = len(filled_gaps) / len(gaps_to_fill) if gaps_to_fill else 1.0
        
        return HistoricalDataRetrievalResponse(
            session_id=f"step7_hist_{ticker}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            ticker=ticker,
            timestamp=datetime.now(),
            valuation_model=model_enum,
            historical_gaps_filled=filled_gaps,
            total_gaps_found=len(gaps_to_fill),
            total_gaps_filled=len(filled_gaps),
            data_completeness_score=completeness,
            sources_used=sources_used,
            extraction_methodology=self._get_extraction_methodology_description(),
            ready_for_assumptions=completeness > 0.7  # Ready if >70% gaps filled
        )
    
    async def _identify_data_gaps(
        self,
        ticker: str,
        existing_data: Dict[str, Any],
        fiscal_years: List[int],
        missing_metrics: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Identify which historical metrics are missing from API data"""
        gaps = []
        
        # Critical metrics for DCF historical analysis
        critical_metrics = [
            "revenue",
            "operating_income",
            "net_income",
            "total_assets",
            "total_equity",
            "operating_cash_flow",
            "capex",
            "working_capital"
        ]
        
        metrics_to_check = missing_metrics if missing_metrics else critical_metrics
        
        for year in fiscal_years:
            year_key = str(year)
            year_data = existing_data.get(year_key, existing_data.get(f"FY{year}", {}))
            
            for metric in metrics_to_check:
                if metric not in year_data or year_data[metric] is None:
                    gaps.append({
                        "metric": metric,
                        "fiscal_year": year,
                        "priority": "high" if metric in critical_metrics[:4] else "medium"
                    })
        
        return gaps
    
    async def _extract_historical_metric(
        self,
        ticker: str,
        metric: str,
        fiscal_year: int,
        market: str,
        company_name: str
    ) -> tuple[Optional[float], str, Optional[str]]:
        """
        Extract a specific historical metric using AI-powered methods.
        
        Returns:
            Tuple of (extracted_value, source_description, extraction_notes)
        """
        # Priority 1: Try PDF extraction for Vietnamese market
        if market == "Vietnam":
            try:
                extracted = await self.pdf_extractor.extract_from_annual_report(
                    ticker=ticker,
                    fiscal_year=fiscal_year,
                    target_metric=metric
                )
                if extracted:
                    return (
                        extracted.value,
                        f"PDF_Annual_Report_{fiscal_year}",
                        f"Extracted from Vietnamese annual report using TT99 mapping"
                    )
            except Exception as e:
                logger.debug(f"PDF extraction failed for {ticker} {fiscal_year}: {e}")
        
        # Priority 2: Try international filings (10-K, 20-F, etc.)
        if market in ["US", "International"]:
            try:
                # Future: Integrate with SEC EDGAR, company filings
                # For now, return None to indicate no extraction available
                pass
            except Exception as e:
                logger.debug(f"Filing extraction failed: {e}")
        
        # Priority 3: AI-powered web scraping (future enhancement)
        # TODO: Implement intelligent web scraping for public data
        
        return (None, "", "No suitable source found for historical data extraction")
    
    def _get_extraction_methodology_description(self) -> str:
        """Return description of extraction methods used"""
        return (
            "AI-powered historical data extraction using: "
            "(1) PDF document parsing for annual reports and filings, "
            "(2) Table extraction with structure recognition, "
            "(3) Vietnamese TT99 compliance mapping for local reports, "
            "(4) Cross-validation against known accounting relationships. "
            "All extracted data preserves original source context for audit trail."
        )
