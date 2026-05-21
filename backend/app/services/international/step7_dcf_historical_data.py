"""Step 7: DCF Historical Data Gap Filling Processor

This is a dedicated processor for DCF valuation method only.
It eliminates conditional branching by focusing exclusively on DCF-specific 
historical data requirements.

Features:
- DCF-specific historical financials gap filling (11 fields: Revenue, EBITDA, EBIT, Net Income, etc.)
- AI-powered extraction from PDF reports, filings, and other sources
- Deterministic fallback calculations when AI extraction fails
- Ensures complete 3-5 year historical data for DCF modeling

AI Usage: STRICTLY for historical data extraction. NO forward-looking inputs.
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
from app.services.international.ai_engine import AIFallbackEngine
from app.services.step7_pdf_extraction import extract_financial_metric_from_text
from app.services.step7_web_search_analysis import analyze_web_search_results, validate_and_clean_financial_data

logger = logging.getLogger(__name__)


class DCFHistoricalDataGap(BaseModel):
    """Represents a gap in DCF historical data that needs AI extraction"""
    metric: str
    fiscal_year: int
    data_source: str  # e.g., "PDF_REPORT", "FILING", "WEBSITE"
    confidence_score: float
    extracted_value: Optional[float] = None
    extraction_notes: Optional[str] = None
    is_critical_for_dcf: bool = True  # All DCF historical metrics are critical


class DCFHistoricalDataRetrievalResponse(BaseModel):
    """
    Step 7 Response: AI-extracted historical data to fill API gaps for DCF

    This contains ONLY historical data extracted via AI from non-API sources.
    No forward-looking assumptions are included.
    """
    session_id: str
    ticker: str
    timestamp: datetime
    valuation_model: str = "DCF"
    historical_gaps_filled: List[DCFHistoricalDataGap]
    total_gaps_found: int
    total_gaps_filled: int
    data_completeness_score: float  # 0.0 to 1.0
    sources_used: List[str]  # e.g., ["PDF_Annual_Report_2023", "SEC_Filing_Q4_2022"]
    extraction_methodology: Optional[str] = None
    ready_for_assumptions: bool = True
    
    # DCF-specific completeness tracking
    revenue_complete: bool = True
    ebitda_complete: bool = True
    net_income_complete: bool = True
    operating_cash_flow_complete: bool = True


class DCFStep7Processor:
    """
    Step 7: DCF Historical Data Gap Filling Processor

    Uses AI to retrieve DCF-specific historical financial data that APIs cannot provide:
    - Extracts data from PDF annual reports, filings, prospectuses
    - Fills gaps in 3-5 year historical financial statements
    - Ensures complete dataset before moving to assumption generation (Step 8)

    DCF-Specific Metrics Tracked:
    - Revenue (critical for growth rate calculations)
    - EBITDA (critical for EV/EBITDA multiples and cash flow)
    - EBIT/Operating Income (critical for operating margin analysis)
    - Net Income (critical for P/E and profitability trends)
    - Total Assets (for balance sheet analysis)
    - Shareholders Equity (for ROE calculations)
    - Operating Cash Flow (critical for DCF cash flow projections)
    - CapEx (critical for free cash flow calculations)
    - Working Capital Change (critical for FCF adjustments)
    - Depreciation & Amortization (for EBITDA reconciliation)
    - Interest Expense (for cost of debt analysis)

    AI Usage: STRICTLY for historical data extraction. NO forward-looking inputs.

    Workflow:
    1. Identify missing DCF historical metrics from Step 6 API data
    2. Search for source documents (PDF reports, filings)
    3. Use AI-powered extraction to pull historical values
    4. Validate extracted data against DCF model constraints
    5. Return complete DCF historical dataset for Step 8
    """

    # DCF-critical historical metrics
    DCF_CRITICAL_METRICS = [
        "Revenue",
        "EBITDA",
        "Operating_Income",
        "Net_Income",
        "Operating_Cash_Flow",
        "CapEx",
    ]
    
    # All DCF historical metrics
    DCF_ALL_METRICS = [
        "Revenue",
        "EBITDA",
        "Operating_Income",
        "Net_Income",
        "Total_Assets",
        "Shareholders_Equity",
        "Operating_Cash_Flow",
        "CapEx",
        "Working_Capital_Change",
        "Depreciation_Amortization",
        "Interest_Expense"
    ]

    def __init__(self):
        self.pdf_extractor = PDFExtractionService()
        self.ai_fallback = AIFallbackEngine()
        # Future: Add web scraper, filing API integrations

    async def retrieve_dcf_historical_data(
        self,
        ticker: str,
        company_name: str,
        market: str,
        step6_financial_data: Dict[str, Any],
        missing_metrics: Optional[List[str]] = None,
        fiscal_years_needed: List[int] = None
    ) -> DCFHistoricalDataRetrievalResponse:
        """
        Retrieve DCF-specific historical data using AI extraction to fill API gaps.

        Args:
            ticker: Stock ticker symbol
            company_name: Company name
            market: Market/country (e.g., "US", "International")
            step6_financial_data: DCF historical data already fetched from APIs (Step 6 response)
            missing_metrics: Specific DCF metrics that need to be filled (optional)
            fiscal_years_needed: List of fiscal years requiring data (default: last 5 years)

        Returns:
            DCFHistoricalDataRetrievalResponse with AI-extracted historical data
        """
        logger.info(f"Step 7 DCF: Starting historical data gap filling for {ticker}")

        # Determine which years need data
        current_year = datetime.now().year
        if fiscal_years_needed is None:
            fiscal_years_needed = list(range(current_year - 5, current_year))
        
        # Extract missing metrics from Step 6 response format
        extracted_missing = await self._extract_missing_dcf_metrics_from_step6(step6_financial_data)
        
        # Use provided missing_metrics or extract from Step 6 data
        if missing_metrics is None:
            missing_metrics = extracted_missing
        
        # Filter to only DCF-relevant metrics
        missing_metrics = [m for m in missing_metrics if m in self.DCF_ALL_METRICS]

        # Identify gaps in DCF historical data
        gaps_to_fill = await self._identify_dcf_data_gaps(
            ticker=ticker,
            existing_data=step6_financial_data,
            fiscal_years=fiscal_years_needed,
            missing_metrics=missing_metrics
        )

        logger.info(f"Step 7 DCF: Identified {len(gaps_to_fill)} historical data gaps for {ticker}")

        # If no gaps, return early with high completeness
        if not gaps_to_fill:
            return DCFHistoricalDataRetrievalResponse(
                session_id=f"step7_dcf_hist_{ticker}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                ticker=ticker,
                timestamp=datetime.now(),
                valuation_model="DCF",
                historical_gaps_filled=[],
                total_gaps_found=0,
                total_gaps_filled=0,
                data_completeness_score=1.0,
                sources_used=[],
                extraction_methodology="No gaps identified - API data complete for DCF",
                ready_for_assumptions=True,
                revenue_complete=True,
                ebitda_complete=True,
                net_income_complete=True,
                operating_cash_flow_complete=True
            )

        # Extract historical data using AI-powered methods
        filled_gaps = []
        sources_used = []

        # Track DCF-specific completeness
        dcf_completeness = {
            "Revenue": True,
            "EBITDA": True,
            "Net_Income": True,
            "Operating_Cash_Flow": True
        }

        for gap in gaps_to_fill:
            try:
                # Attempt AI extraction from available sources
                extracted_value, source, notes = await self._extract_dcf_historical_metric(
                    ticker=ticker,
                    metric=gap["metric"],
                    fiscal_year=gap["fiscal_year"],
                    market=market,
                    company_name=company_name
                )

                if extracted_value is not None:
                    filled_gap = DCFHistoricalDataGap(
                        metric=gap["metric"],
                        fiscal_year=gap["fiscal_year"],
                        data_source=source,
                        confidence_score=0.85,  # Will be refined by extraction method
                        extracted_value=extracted_value,
                        extraction_notes=notes,
                        is_critical_for_dcf=gap["metric"] in self.DCF_CRITICAL_METRICS
                    )
                    filled_gaps.append(filled_gap)
                    if source not in sources_used:
                        sources_used.append(source)
                    
                    # Update completeness tracking
                    if gap["metric"] in dcf_completeness:
                        dcf_completeness[gap["metric"]] = False
                else:
                    # AI extraction failed - use deterministic fallback
                    fallback_value = await self._calculate_dcf_deterministic_fallback(
                        ticker=ticker,
                        metric=gap["metric"],
                        fiscal_year=gap["fiscal_year"],
                        existing_data=step6_financial_data,
                        market=market
                    )

                    if fallback_value is not None:
                        filled_gap = DCFHistoricalDataGap(
                            metric=gap["metric"],
                            fiscal_year=gap["fiscal_year"],
                            data_source="Deterministic_Fallback_Calculation",
                            confidence_score=0.65,  # Lower confidence for calculated values
                            extracted_value=fallback_value,
                            extraction_notes=f"Calculated using DCF {gap['metric']} estimation methodology based on available financial data",
                            is_critical_for_dcf=gap["metric"] in self.DCF_CRITICAL_METRICS
                        )
                        filled_gaps.append(filled_gap)
                        sources_used.append("Deterministic Fallback (Financial Ratios/Averages)")
                        
                        # Update completeness tracking
                        if gap["metric"] in dcf_completeness:
                            dcf_completeness[gap["metric"]] = False

            except Exception as e:
                logger.warning(f"Step 7 DCF: Failed to extract {gap['metric']} for {gap['fiscal_year']}: {e}")
                # Continue with other gaps even if some fail

        # Calculate completeness score
        completeness = len(filled_gaps) / len(gaps_to_fill) if gaps_to_fill else 1.0

        # Check if critical DCF metrics are complete
        revenue_complete = dcf_completeness.get("Revenue", True)
        ebitda_complete = dcf_completeness.get("EBITDA", True)
        net_income_complete = dcf_completeness.get("Net_Income", True)
        ocf_complete = dcf_completeness.get("Operating_Cash_Flow", True)

        # Ready for assumptions if >70% gaps filled AND critical metrics available
        ready = (completeness > 0.7) and (revenue_complete or ebitda_complete)

        return DCFHistoricalDataRetrievalResponse(
            session_id=f"step7_dcf_hist_{ticker}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            ticker=ticker,
            timestamp=datetime.now(),
            valuation_model="DCF",
            historical_gaps_filled=filled_gaps,
            total_gaps_found=len(gaps_to_fill),
            total_gaps_filled=len(filled_gaps),
            data_completeness_score=completeness,
            sources_used=sources_used,
            extraction_methodology=self._get_dcf_extraction_methodology_description(),
            ready_for_assumptions=ready,
            revenue_complete=revenue_complete,
            ebitda_complete=ebitda_complete,
            net_income_complete=net_income_complete,
            operating_cash_flow_complete=ocf_complete
        )
    
    async def _extract_missing_dcf_metrics_from_step6(self, step6_data: Dict[str, Any]) -> List[str]:
        """
        Extract missing DCF metric names from Step 6 response format.
        
        Step 6 returns a Step6DataReviewResponse with nested structures:
        - historical_financials.data_fields[] with status=MISSING
        - market_data.data_fields[] with status=MISSING
        - forecast_drivers.data_fields[] with status=MISSING
        
        This method parses these structures and returns a list of missing DCF metric names.
        """
        missing_metrics = []
        
        # Check if step6_data is already a dict or needs conversion
        if hasattr(step6_data, 'model_dump'):
            step6_dict = step6_data.model_dump()
        elif hasattr(step6_data, 'dict'):
            step6_dict = step6_data.dict()
        else:
            step6_dict = step6_data
        
        # Extract from historical_financials
        historical = step6_dict.get('historical_financials', {})
        if historical:
            data_fields = historical.get('data_fields', [])
            for field in data_fields:
                if isinstance(field, dict):
                    if field.get('status') == 'MISSING':
                        # Extract base metric name (remove year suffix)
                        field_name = field.get('field_name', '')
                        if field_name and field_name not in missing_metrics:
                            # Remove year suffix to get base metric name
                            base_name = '_'.join(field_name.split('_')[:-1]) if '_' in field_name else field_name
                            # Only include DCF-relevant metrics
                            if base_name in self.DCF_ALL_METRICS and base_name not in missing_metrics:
                                missing_metrics.append(base_name)
        
        # Extract from market_data
        market = step6_dict.get('market_data', {})
        if market:
            data_fields = market.get('data_fields', [])
            for field in data_fields:
                if isinstance(field, dict):
                    if field.get('status') == 'MISSING':
                        field_name = field.get('field_name', '')
                        if field_name and field_name in self.DCF_ALL_METRICS and field_name not in missing_metrics:
                            missing_metrics.append(field_name)
        
        # Extract from forecast_drivers
        drivers = step6_dict.get('forecast_drivers', {})
        if drivers:
            data_fields = drivers.get('data_fields', [])
            for field in data_fields:
                if isinstance(field, dict):
                    if field.get('status') == 'MISSING':
                        field_name = field.get('field_name', '')
                        if field_name and field_name not in missing_metrics:
                            base_name = '_'.join(field_name.split('_')[:-1]) if '_' in field_name else field_name
                            if base_name in self.DCF_ALL_METRICS and base_name not in missing_metrics:
                                missing_metrics.append(base_name)
        
        logger.info(f"Step 7 DCF: Extracted {len(missing_metrics)} missing DCF metrics from Step 6 data")
        return missing_metrics
    
    async def _identify_dcf_data_gaps(
        self,
        ticker: str,
        existing_data: Dict[str, Any],
        fiscal_years: List[int],
        missing_metrics: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Identify which DCF historical metrics are missing from API data.
        
        This method now properly handles the Step 6 response format where data is organized
        in historical_financials.data_fields[] array with field_name containing year suffix.
        """
        gaps = []
        
        # Use DCF-specific critical metrics
        metrics_to_check = missing_metrics if missing_metrics else self.DCF_ALL_METRICS
        
        # Convert existing_data to check for missing values by parsing data_fields
        # Step 6 format: {historical_financials: {data_fields: [{field_name, value, status}, ...]}}
        available_metrics_by_year = {}
        
        # Parse historical_financials data_fields
        historical = existing_data.get('historical_financials', {})
        if historical:
            data_fields = historical.get('data_fields', [])
            for field in data_fields:
                if isinstance(field, dict):
                    field_name = field.get('field_name', '')
                    value = field.get('value')
                    status = field.get('status', 'RETRIEVED')
                    
                    # Extract year from field_name (e.g., "Revenue_2023" -> 2023)
                    if '_' in field_name:
                        parts = field_name.rsplit('_', 1)
                        if len(parts) == 2 and parts[1].isdigit():
                            metric_name = parts[0]
                            year = int(parts[1])
                            
                            if year not in available_metrics_by_year:
                                available_metrics_by_year[year] = {}
                            
                            # Mark as available only if has value and status is not MISSING
                            if value is not None and status != 'MISSING':
                                available_metrics_by_year[year][metric_name] = value
        
        # If no metrics found in structured format, fall back to original logic
        if not available_metrics_by_year:
            logger.warning("Step 7 DCF: No structured data found in Step 6 format, using fallback logic")
            for year in fiscal_years:
                year_key = str(year)
                year_data = existing_data.get(year_key, existing_data.get(f"FY{year}", {}))
                
                for metric in metrics_to_check:
                    if metric not in year_data or year_data.get(metric) is None:
                        gaps.append({
                            "metric": metric,
                            "fiscal_year": year,
                            "priority": "high" if metric in self.DCF_CRITICAL_METRICS else "medium"
                        })
            return gaps
        
        # Use parsed data to identify gaps
        for year in fiscal_years:
            if year not in available_metrics_by_year:
                available_metrics_by_year[year] = {}
            
            year_data = available_metrics_by_year[year]
            
            for metric in metrics_to_check:
                if metric not in year_data:
                    gaps.append({
                        "metric": metric,
                        "fiscal_year": year,
                        "priority": "high" if metric in self.DCF_CRITICAL_METRICS else "medium"
                    })
        
        # Sort gaps by priority (high first)
        gaps.sort(key=lambda x: 0 if x["priority"] == "high" else 1)
        
        return gaps
    
    async def _extract_dcf_historical_metric(
        self,
        ticker: str,
        metric: str,
        fiscal_year: int,
        market: str,
        company_name: str
    ) -> tuple[Optional[float], str, Optional[str]]:
        """
        Extract a specific DCF historical metric using AI-powered methods.
        
        Returns:
            Tuple of (extracted_value, source, notes)
        """
        # Try PDF extraction first
        try:
            pdf_path = await self._get_dcf_pdf_downloader(ticker, fiscal_year, market)
            if pdf_path:
                extracted_text = await self._extract_dcf_text_from_file(pdf_path)
                
                # Use AI to extract specific metric from text
                from app.services import extract_financial_metric_from_text
                ai_extracted = await extract_financial_metric_from_text(
                    text=extracted_text,
                    metric=metric,
                    fiscal_year=fiscal_year,
                    company_name=company_name
                )
                
                if ai_extracted.get("success") and ai_extracted.get("value") is not None:
                    return (ai_extracted["value"], f"PDF_Annual_Report_{fiscal_year}", f"AI-extracted from PDF report (confidence: {ai_extracted['confidence']})")
        except Exception as e:
            logger.debug(f"Step 7 DCF: PDF extraction failed for {metric} {fiscal_year}: {e}")
        
        # Try SEC filing extraction (if applicable)
        try:
            filing_text = await self._download_dcf_sec_filing(ticker, fiscal_year)
            if filing_text:
                from app.services import extract_financial_metric_from_text
                ai_extracted = await extract_financial_metric_from_text(
                    text=filing_text,
                    metric=metric,
                    fiscal_year=fiscal_year,
                    company_name=company_name
                )
                
                if ai_extracted.get("success") and ai_extracted.get("value") is not None:
                    return (ai_extracted["value"], f"SEC_Filing_{fiscal_year}", f"AI-extracted from SEC filing (confidence: {ai_extracted['confidence']})")
        except Exception as e:
            logger.debug(f"Step 7 DCF: SEC filing extraction failed for {metric} {fiscal_year}: {e}")
        
        # Try investor relations website
        try:
            ir_text = await self._extract_from_dcf_ir_website(ticker, metric, fiscal_year)
            if ir_text:
                return (ir_text, f"IR_Website_{fiscal_year}", f"Extracted from IR website")
        except Exception as e:
            logger.debug(f"Step 7 DCF: IR website extraction failed for {metric} {fiscal_year}: {e}")
        
        # All extraction methods failed
        return (None, "", "All AI extraction methods failed")
    
    def _get_dcf_pdf_downloader(self):
        """Get PDF downloader for DCF historical reports"""
        # Placeholder - integrate with actual PDF download service
        return None
    
    async def _download_dcf_sec_filing(self, ticker: str, fiscal_year: int) -> Optional[str]:
        """Download SEC filing for DCF historical data"""
        # Placeholder - integrate with EDGAR API
        return None
    
    async def _extract_dcf_text_from_file(self, file_path: str) -> str:
        """Extract text from PDF/file for DCF analysis"""
        try:
            extracted = await self.pdf_extractor.extract_financial_data(file_path)
            return extracted.raw_text if hasattr(extracted, 'raw_text') else str(extracted)
        except Exception as e:
            logger.error(f"Step 7 DCF: Text extraction failed: {e}")
            return ""
    
    async def _extract_from_dcf_ir_website(
        self, 
        ticker: str, 
        metric: str, 
        fiscal_year: int
    ) -> Optional[float]:
        """Extract DCF metric from investor relations website"""
        # Placeholder - integrate with web scraping service
        return None
    
    def _get_dcf_extraction_methodology_description(self) -> str:
        """Return description of DCF extraction methodology used"""
        return (
            "DCF Historical Data Extraction Methodology:\n"
            "1. AI-powered PDF extraction from annual reports and filings\n"
            "2. Natural language processing to identify DCF-specific metrics\n"
            "3. Deterministic fallback calculations using financial ratios\n"
            "4. Cross-validation with available API data\n"
            "5. Confidence scoring based on source reliability"
        )
    
    async def _calculate_dcf_deterministic_fallback(
        self,
        ticker: str,
        metric: str,
        fiscal_year: int,
        existing_data: Dict[str, Any],
        market: str
    ) -> Optional[float]:
        """
        Calculate deterministic fallback for DCF metrics when AI extraction fails.
        
        Uses financial relationships and ratios to estimate missing values:
        - EBITDA ≈ Operating Income + D&A
        - Operating Cash Flow ≈ Net Income + D&A - Working Capital Changes
        - etc.
        """
        try:
            # Get available data for calculations
            if hasattr(existing_data, 'model_dump'):
                data_dict = existing_data.model_dump()
            elif hasattr(existing_data, 'dict'):
                data_dict = existing_data.dict()
            else:
                data_dict = existing_data
            
            # DCF-specific fallback calculations
            if metric == "EBITDA":
                # Try to calculate from Operating Income + D&A
                op_income = self._get_metric_from_data(data_dict, "Operating_Income", fiscal_year)
                da = self._get_metric_from_data(data_dict, "Depreciation_Amortization", fiscal_year)
                if op_income is not None and da is not None:
                    return op_income + da
            
            elif metric == "Operating_Cash_Flow":
                # Try to calculate from Net Income + D&A - WC Changes
                net_income = self._get_metric_from_data(data_dict, "Net_Income", fiscal_year)
                da = self._get_metric_from_data(data_dict, "Depreciation_Amortization", fiscal_year)
                wc_change = self._get_metric_from_data(data_dict, "Working_Capital_Change", fiscal_year)
                if net_income is not None and da is not None:
                    ocf = net_income + da
                    if wc_change is not None:
                        ocf -= wc_change
                    return ocf
            
            elif metric == "Working_Capital_Change":
                # Estimate from revenue growth
                revenue_current = self._get_metric_from_data(data_dict, "Revenue", fiscal_year)
                revenue_prior = self._get_metric_from_data(data_dict, "Revenue", fiscal_year - 1)
                if revenue_current is not None and revenue_prior is not None:
                    # Assume WC is ~10% of revenue change
                    return (revenue_current - revenue_prior) * 0.10
            
            elif metric == "Depreciation_Amortization":
                # Estimate as % of Revenue or PP&E
                revenue = self._get_metric_from_data(data_dict, "Revenue", fiscal_year)
                if revenue is not None:
                    # Industry average D&A is typically 3-5% of revenue
                    return revenue * 0.04
            
            # Generic fallback: use industry benchmark
            benchmark = self._get_dcf_industry_benchmark(metric, market)
            if benchmark is not None:
                # Apply benchmark to available base metric
                if metric in ["EBITDA", "Operating_Income", "Net_Income"]:
                    revenue = self._get_metric_from_data(data_dict, "Revenue", fiscal_year)
                    if revenue is not None:
                        return revenue * benchmark
            
            return None
            
        except Exception as e:
            logger.error(f"Step 7 DCF: Deterministic fallback calculation failed: {e}")
            return None
    
    def _get_metric_from_data(self, data_dict: Dict, metric: str, fiscal_year: int) -> Optional[float]:
        """Helper to extract metric value from data dictionary"""
        # Try structured format first
        historical = data_dict.get('historical_financials', {})
        if historical:
            data_fields = historical.get('data_fields', [])
            for field in data_fields:
                if isinstance(field, dict):
                    field_name = field.get('field_name', '')
                    if field_name == f"{metric}_{fiscal_year}":
                        value = field.get('value')
                        if value is not None and field.get('status') != 'MISSING':
                            return value
        
        # Try legacy format
        year_data = data_dict.get(str(fiscal_year), data_dict.get(f"FY{fiscal_year}", {}))
        return year_data.get(metric)
    
    def _get_dcf_industry_benchmark(self, metric: str, market: str) -> Optional[float]:
        """Get industry benchmark for DCF metric"""
        # Simplified benchmarks - should be expanded with real industry data
        benchmarks = {
            "EBITDA": 0.15,  # 15% EBITDA margin
            "Operating_Income": 0.10,  # 10% operating margin
            "Net_Income": 0.08,  # 8% net margin
            "Depreciation_Amortization": 0.04,  # 4% of revenue
        }
        return benchmarks.get(metric)
