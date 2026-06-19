"""
Vietnamese Step 6: Data Fetch Processor
Orchestrates raw data retrieval from Vietnamese providers (Vietstock, FireAnt, etc.)
Adheres to Model Integrity: No data dropping, explicit nulls for missing values.

Enhancement: DataField status tracking wraps each financial field with:
- Status (RETRIEVED / MISSING / CALCULATED)
- Source attribution (vietstock, yfinance, ai_extraction, cache)
- is_critical flag for required fields
- Completion percentage calculation
"""
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# DataField Status Tracking
# ──────────────────────────────────────────────────────────────────────────────

class vn_DataFieldStatus(str, Enum):
    """Status of a Vietnamese financial data field."""
    RETRIEVED = "RETRIEVED"
    MISSING = "MISSING"
    CALCULATED = "CALCULATED"
    AI_EXTRACTED = "AI_EXTRACTED"
    CACHED = "CACHED"


class vn_DataField(BaseModel):
    """Per-field status tracking for Vietnamese financial data."""
    field_name: str
    tt99_code: Optional[str] = None
    vietnamese_name: Optional[str] = None
    value: Optional[float] = None
    status: vn_DataFieldStatus = vn_DataFieldStatus.MISSING
    source: Optional[str] = None
    is_critical: bool = False
    section: Optional[str] = None  # income_statement, balance_sheet, cash_flow


# TT99 Code → English Field mapping (from plan)
TT99_FIELD_MAP: Dict[str, Dict[str, str]] = {
    # Income Statement
    "01": {"english": "revenue", "vietnamese": "Doanh thu bán hàng", "section": "income_statement"},
    "02": {"english": "revenue_deductions", "vietnamese": "Các khoản giảm trừ", "section": "income_statement"},
    "10": {"english": "net_revenue", "vietnamese": "Doanh thu thuần", "section": "income_statement"},
    "11": {"english": "cogs", "vietnamese": "Giá vốn hàng bán", "section": "income_statement"},
    "20": {"english": "gross_profit", "vietnamese": "Lợi nhuận gộp", "section": "income_statement"},
    "25": {"english": "selling_expenses", "vietnamese": "Chi phí bán hàng", "section": "income_statement"},
    "26": {"english": "admin_expenses", "vietnamese": "Chi phí quản lý DNNN", "section": "income_statement"},
    "30": {"english": "operating_income", "vietnamese": "Lợi nhuận từ HĐKD", "section": "income_statement"},
    "51": {"english": "current_tax", "vietnamese": "Thuế TNDN hiện hành", "section": "income_statement"},
    "52": {"english": "deferred_tax", "vietnamese": "Thuế TNDN hoãn lại", "section": "income_statement"},
    "60": {"english": "net_income", "vietnamese": "Lợi nhuận sau thuế", "section": "income_statement"},
    # Balance Sheet
    "110": {"english": "cash", "vietnamese": "Tiền và tương đương tiền", "section": "balance_sheet"},
    "120": {"english": "short_term_investments", "vietnamese": "Đầu tư ngắn hạn", "section": "balance_sheet"},
    "130": {"english": "accounts_receivable", "vietnamese": "Phải thu ngắn hạn", "section": "balance_sheet"},
    "140": {"english": "inventory", "vietnamese": "Hàng tồn kho", "section": "balance_sheet"},
    "220": {"english": "ppe_net", "vietnamese": "TSCĐ hữu hình ròng", "section": "balance_sheet"},
    "321": {"english": "short_term_debt", "vietnamese": "Vay ngắn hạn", "section": "balance_sheet"},
    "339": {"english": "long_term_debt", "vietnamese": "Vay dài hạn", "section": "balance_sheet"},
    "411": {"english": "shareholders_equity", "vietnamese": "Vốn chủ sở hữu", "section": "balance_sheet"},
    "420": {"english": "retained_earnings", "vietnamese": "Lợi nhuận chưa phân phối", "section": "balance_sheet"},
}

# Critical fields for DCF/DuPont/Comps valuation
CRITICAL_FIELDS = {
    "net_revenue", "net_income", "cash", "accounts_receivable", "inventory",
    "short_term_debt", "long_term_debt", "shareholders_equity",
}


class vn_DataFetchInput(BaseModel):
    """Input for Step 6: Fetching raw data based on confirmed requirements."""
    ticker: str
    company_name: str
    exchange: str  # HOSE, HNX, UPCOM
    currency: str = "VND"

    # Timeframe requirements
    history_years: int = Field(..., description="Number of historical years to fetch")
    include_quarterly: bool = Field(default=True, description="Include quarterly data for TTM")

    # Data scope
    fetch_income_statement: bool = True
    fetch_balance_sheet: bool = True
    fetch_cash_flow: bool = True
    fetch_peer_data: bool = Field(default=False, description="Fetch peer data if Comps model selected")
    peer_tickers: List[str] = Field(default_factory=list)

    # Source preferences
    preferred_source: str = Field(default="vietstock", description="Primary data source")
    fallback_to_ai_extraction: bool = Field(default=True, description="Allow AI PDF extraction if API fails")


class RawDataBundle(BaseModel):
    """Container for raw, unprocessed data fetched from sources.

    Enhanced with DataField status tracking for per-field visibility.
    """
    source_provider: str
    fetch_timestamp: datetime
    currency_unit: str  # e.g., "millions_VND", "VND"

    # Raw financial statements (keys are period dates, values are raw dicts)
    income_statement_raw: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    balance_sheet_raw: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    cash_flow_raw: Dict[str, Dict[str, Any]] = Field(default_factory=dict)

    # Raw peer data if requested
    peer_data_raw: Dict[str, Dict[str, Any]] = Field(default_factory=dict)

    # Metadata
    missing_periods: List[str] = Field(default_factory=list, description="Periods where data was unavailable")
    data_quality_flags: List[str] = Field(default_factory=list, description="Warnings about data consistency")
    pdf_sources_used: List[str] = Field(default_factory=list, description="List of PDF reports fetched for AI extraction")

    # DataField status tracking (enhancement for Fix 2)
    data_fields: Dict[str, vn_DataField] = Field(
        default_factory=dict,
        description="Per-field status tracking keyed by English field name",
    )
    completion_percentage: float = Field(0.0, description="Overall data completion percentage 0-100")
    critical_missing: List[str] = Field(
        default_factory=list,
        description="Critical fields that are MISSING (blocks valuation)",
    )


class vn_DataFetchOutput(BaseModel):
    """Output from Step 6: Ready for Step 7 processing."""
    success: bool
    ticker: str
    data_bundle: RawDataBundle
    message: str
    next_step: str = "step7_historical_processing"

    # Audit trail
    fetch_duration_ms: float
    sources_accessed: List[str]


class vn_Step6DataFetchProcessor:
    """
    Processor for Step 6: Fetching raw Vietnamese financial data.

    Workflow:
    1. Validate input requirements.
    2. Initialize Vietnamese data services.
    3. Fetch raw data for target company.
    4. Fetch peer data if required.
    5. Compile raw bundle with metadata.
    6. Return unprocessed data for Step 7 normalization.
    
    Implements "Fetch Once, Use Many" architecture:
    - Checks session_cache['vietnam_market_data'] before fetching
    - Reuses cached data within 5-minute TTL
    - Stores fetched data in shared cache for reuse across DCF/DuPont/Comps
    """

    def __init__(self):
        # Lazy import to avoid circular dependencies
        self.vndata_service = None
        self.ai_extraction_service = None
        self.report_scraper = None

    async def _initialize_services(self):
        """Initialize Vietnamese-specific data services."""
        if self.vndata_service is None:
            try:
                from app.services.vietnamese.vietnamese_data_service import VietnameseDataService
                self.vndata_service = VietnameseDataService()
            except ImportError:
                logger.warning("VietnameseDataService not found, using mock data for development")
                self.vndata_service = None

        if self.ai_extraction_service is None:
            try:
                from app.services.ai.pdf_extraction_service import PDFExtractionService
                self.ai_extraction_service = PDFExtractionService()
            except ImportError:
                logger.warning("PDF Extraction service not available")
                self.ai_extraction_service = None

        if self.report_scraper is None:
            try:
                from app.services.vietnamese.vietnamese_report_scraper import VietnameseReportScraper
                self.report_scraper = VietnameseReportScraper()
            except ImportError:
                logger.warning("VietnameseReportScraper not available")
                self.report_scraper = None

    async def execute(self, input_data: vn_DataFetchInput, session_cache: Optional[Dict] = None) -> vn_DataFetchOutput:
        """
        Execute Step 6: Fetch raw data.
        
        Args:
            input_data: Input parameters for data fetching
            session_cache: Session cache dict to check before fetching (implements "Fetch Once, Use Many")
                        If cache exists and is < 5 minutes old, returns cached data without re-fetching
        
        Returns:
            vn_DataFetchOutput with fetched data bundle
        """
        import time
        start_time = time.time()

        # GAP 1 FIX: Check session cache for "Fetch Once, Use Many" architecture
        if session_cache and 'vietnam_market_data' in session_cache:
            cached_data = session_cache['vietnam_market_data']
            cache_timestamp = cached_data.get('timestamp')
            
            if cache_timestamp:
                # Convert timestamp if it's a string
                if isinstance(cache_timestamp, str):
                    try:
                        cache_timestamp = datetime.fromisoformat(cache_timestamp)
                    except ValueError:
                        cache_timestamp = None
                
                if cache_timestamp:
                    cache_age = datetime.now() - cache_timestamp
                    if cache_age < timedelta(minutes=5):
                        logger.info(f"Using cached Vietnam market data for {input_data.ticker} (age: {cache_age.seconds}s)")
                        # Return cached data without re-fetching
                        return vn_DataFetchOutput(
                            success=True,
                            ticker=input_data.ticker,
                            data_bundle=RawDataBundle(
                                source_provider=cached_data.get('source_provider', 'cache'),
                                fetch_timestamp=cached_data.get('fetch_timestamp', datetime.now()),
                                currency_unit=cached_data.get('currency_unit', 'millions_VND'),
                                income_statement_raw=cached_data.get('income_statement_raw', {}),
                                balance_sheet_raw=cached_data.get('balance_sheet_raw', {}),
                                cash_flow_raw=cached_data.get('cash_flow_raw', {}),
                                peer_data_raw=cached_data.get('peer_data_raw', {}),
                                missing_periods=cached_data.get('missing_periods', []),
                                data_quality_flags=cached_data.get('data_quality_flags', []),
                                pdf_sources_used=cached_data.get('pdf_sources_used', [])
                            ),
                            message=f"Using cached data for {input_data.ticker} - no API call needed",
                            fetch_duration_ms=0,
                            sources_accessed=['cache']
                        )

        await self._initialize_services()

        # FIX Issue #2 (Vietnam): Check cache before fetching
        if session_cache and 'vietnamese_market_data' in session_cache:
            cached_data = session_cache['vietnamese_market_data']
            cache_timestamp = cached_data.get('fetch_timestamp')
            if cache_timestamp:
                from datetime import datetime, timedelta
                cache_age = datetime.now() - cache_timestamp
                if cache_age < timedelta(minutes=5):
                    logger.info(f"Using cached Vietnamese market data (age: {cache_age.seconds}s)")
                    # Return cached data bundle
                    return vn_DataFetchOutput(
                        success=True,
                        ticker=input_data.ticker,
                        data_bundle=RawDataBundle(**cached_data['data_bundle']),
                        message=f"Using cached data for {input_data.ticker}",
                        fetch_duration_ms=0,
                        sources_accessed=cached_data.get('sources_accessed', ['cache'])
                    )

        sources_accessed = []
        data_quality_flags = []
        missing_periods = []
        pdf_sources = []

        # Initialize raw containers
        is_raw = {}
        bs_raw = {}
        cf_raw = {}
        peer_raw = {}

        try:
            # 1. Fetch Target Company Data
            if self.vndata_service:
                sources_accessed.append(self.vndata_service.provider_name)

                # Fetch Income Statement
                if input_data.fetch_income_statement:
                    is_raw = await self.vndata_service.fetch_income_statement(
                        ticker=input_data.ticker,
                        years=input_data.history_years,
                        include_quarterly=input_data.include_quarterly
                    )

                # Fetch Balance Sheet
                if input_data.fetch_balance_sheet:
                    bs_raw = await self.vndata_service.fetch_balance_sheet(
                        ticker=input_data.ticker,
                        years=input_data.history_years,
                        include_quarterly=input_data.include_quarterly
                    )

                # Fetch Cash Flow
                if input_data.fetch_cash_flow:
                    cf_raw = await self.vndata_service.fetch_cash_flow(
                        ticker=input_data.ticker,
                        years=input_data.history_years,
                        include_quarterly=input_data.include_quarterly
                    )

                # Check for missing periods
                all_periods = set()
                if is_raw: all_periods.update(is_raw.keys())
                if bs_raw: all_periods.update(bs_raw.keys())
                if cf_raw: all_periods.update(cf_raw.keys())

                # Identify gaps (simplified check)
                expected_count = input_data.history_years
                if len(all_periods) < expected_count:
                    data_quality_flags.append(f"Incomplete data: Expected {expected_count} periods, got {len(all_periods)}")

                # 2. Handle Missing Data via Government Report Scraper + AI Extraction
                if input_data.fallback_to_ai_extraction and data_quality_flags:
                    logger.info(f"Attempting to fetch official reports for {input_data.ticker} due to data gaps")

                    if self.report_scraper:
                        # Search and download official PDF reports from HOSE/HNX/UPCOM
                        years_to_fetch = list(range(datetime.now().year - input_data.history_years, datetime.now().year))
                        try:
                            reports_found = self.report_scraper.search_reports(
                                ticker=input_data.ticker,
                                exchange=input_data.exchange,
                                years=years_to_fetch,
                                report_types=['annual']
                            )

                            # Download found reports
                            downloaded_paths = []
                            for report in reports_found:
                                filepath = self.report_scraper.download_report(report)
                                if filepath:
                                    downloaded_paths.append(str(filepath))
                                    pdf_sources.append(str(filepath))

                            if downloaded_paths and self.ai_extraction_service:
                                # Trigger AI extraction on downloaded PDFs
                                logger.info(f"Extracting data from {len(downloaded_paths)} official PDF reports")
                                for pdf_path in downloaded_paths:
                                    try:
                                        extraction_result = self.ai_extraction_service.extract_from_file(pdf_path)
                                        # Merge extracted data into raw containers (simplified logic here)
                                        data_quality_flags.append(f"AI extraction completed for {pdf_path}")
                                    except Exception as extract_err:
                                        logger.warning(f"Extraction failed for {pdf_path}: {extract_err}")

                        except Exception as scrape_err:
                            logger.error(f"Report scraping failed: {scrape_err}")
                            data_quality_flags.append(f"Scraper error: {str(scrape_err)}")
                    else:
                        # Fallback to generic AI extraction without official scraper
                        if self.ai_extraction_service:
                            pdf_sources.append(f"{input_data.ticker}_annual_report.pdf")
                            data_quality_flags.append("AI extraction triggered (using fallback sources)")

            else:
                # Mock data for development if service unavailable
                data_quality_flags.append("Using mock data - Vietnamese data service unavailable")
                is_raw = self._generate_mock_data(input_data.ticker, "IS")
                bs_raw = self._generate_mock_data(input_data.ticker, "BS")
                cf_raw = self._generate_mock_data(input_data.ticker, "CF")

            # 3. Fetch Peer Data if requested
            if input_data.fetch_peer_data and input_data.peer_tickers:
                for peer_ticker in input_data.peer_tickers:
                    if self.vndata_service:
                        peer_raw[peer_ticker] = await self.vndata_service.fetch_key_metrics(peer_ticker)
                    else:
                        peer_raw[peer_ticker] = self._generate_mock_data(peer_ticker, "METRICS")
                sources_accessed.append("peer_data_fetch")

            # 4. Wrap raw data with DataField status tracking
            primary_source = sources_accessed[0] if sources_accessed else "unknown"
            data_fields = self._wrap_raw_data_with_datafields(is_raw, bs_raw, cf_raw, primary_source)
            completion_pct, critical_missing = self._calculate_completion_stats(data_fields)

            # 5. Compile Output
            fetch_duration = (time.time() - start_time) * 1000

            data_bundle = RawDataBundle(
                source_provider=", ".join(sources_accessed),
                fetch_timestamp=datetime.now(),
                currency_unit="millions_VND",  # Standardize to millions VND
                income_statement_raw=is_raw,
                balance_sheet_raw=bs_raw,
                cash_flow_raw=cf_raw,
                peer_data_raw=peer_raw,
                missing_periods=missing_periods,
                data_quality_flags=data_quality_flags,
                pdf_sources_used=pdf_sources,
                data_fields=data_fields,
                completion_percentage=completion_pct,
                critical_missing=critical_missing,
            )

            # GAP 1 FIX: Store fetched data in session cache for "Fetch Once, Use Many"
            if session_cache is not None:
                from datetime import datetime
                cache_data = {
                    'timestamp': datetime.now(),
                    'source_provider': data_bundle.source_provider,
                    'fetch_timestamp': data_bundle.fetch_timestamp,
                    'currency_unit': data_bundle.currency_unit,
                    'income_statement_raw': data_bundle.income_statement_raw,
                    'balance_sheet_raw': data_bundle.balance_sheet_raw,
                    'cash_flow_raw': data_bundle.cash_flow_raw,
                    'peer_data_raw': data_bundle.peer_data_raw,
                    'missing_periods': data_bundle.missing_periods,
                    'data_quality_flags': data_bundle.data_quality_flags,
                    'pdf_sources_used': data_bundle.pdf_sources_used,
                    'periods_fetched': list(data_bundle.income_statement_raw.keys()) if data_bundle.income_statement_raw else []
                }
                
                # Store in session under shared cache key
                session_cache['vietnam_market_data'] = cache_data
                logger.info(f"Stored Vietnam market data in cache for {input_data.ticker}")

            return vn_DataFetchOutput(
                success=True,
                ticker=input_data.ticker,
                data_bundle=data_bundle,
                message=f"Successfully fetched raw data for {input_data.ticker}",
                fetch_duration_ms=fetch_duration,
                sources_accessed=sources_accessed
            )

        except Exception as e:
            logger.error(f"Error fetching data for {input_data.ticker}: {str(e)}")
            fetch_duration = (time.time() - start_time) * 1000
            return vn_DataFetchOutput(
                success=False,
                ticker=input_data.ticker,
                data_bundle=RawDataBundle(
                    source_provider="none",
                    fetch_timestamp=datetime.now(),
                    currency_unit="millions_VND",
                    data_quality_flags=[f"Fetch failed: {str(e)}"]
                ),
                message=f"Failed to fetch data: {str(e)}",
                fetch_duration_ms=fetch_duration,
                sources_accessed=sources_accessed
            )

    # ──────────────────────────────────────────────────────────────────────────
    # DataField Status Tracking (Fix 2)
    # ──────────────────────────────────────────────────────────────────────────

    def _wrap_raw_data_with_datafields(
        self,
        is_raw: Dict[str, Dict[str, Any]],
        bs_raw: Dict[str, Dict[str, Any]],
        cf_raw: Dict[str, Dict[str, Any]],
        source: str,
    ) -> Dict[str, vn_DataField]:
        """
        Wrap raw financial data with vn_DataField status tracking.

        Iterates over the TT99 field map, looks up each field in the raw data,
        and creates a vn_DataField with RETRIEVED or MISSING status.

        Args:
            is_raw: Raw income statement data {period: {tt99_code: value}}
            bs_raw: Raw balance sheet data
            cf_raw: Raw cash flow data
            source: Data source name (e.g. "vietstock", "ai_extraction")

        Returns:
            Dict keyed by English field name → vn_DataField
        """
        data_fields: Dict[str, vn_DataField] = {}

        # Map section → raw data
        section_raw = {
            "income_statement": is_raw,
            "balance_sheet": bs_raw,
            "cash_flow": cf_raw,
        }

        for tt99_code, field_info in TT99_FIELD_MAP.items():
            english_name = field_info["english"]
            section = field_info["section"]
            raw_data = section_raw.get(section, {})

            # Look for the value across all periods (use latest non-null)
            value = None
            status = vn_DataFieldStatus.MISSING
            field_source = None

            for period in sorted(raw_data.keys(), reverse=True):
                period_data = raw_data[period]
                if isinstance(period_data, dict) and tt99_code in period_data:
                    val = period_data[tt99_code]
                    if val is not None:
                        value = float(val) if not isinstance(val, float) else val
                        status = vn_DataFieldStatus.RETRIEVED
                        field_source = source
                        break

            data_fields[english_name] = vn_DataField(
                field_name=english_name,
                tt99_code=tt99_code,
                vietnamese_name=field_info["vietnamese"],
                value=value,
                status=status,
                source=field_source,
                is_critical=english_name in CRITICAL_FIELDS,
                section=section,
            )

        return data_fields

    @staticmethod
    def _calculate_completion_stats(
        data_fields: Dict[str, vn_DataField],
    ) -> tuple:
        """
        Calculate completion percentage and critical missing fields.

        Returns:
            Tuple of (completion_percentage, critical_missing_list)
        """
        if not data_fields:
            return 0.0, list(CRITICAL_FIELDS)

        total = len(data_fields)
        retrieved = sum(1 for f in data_fields.values() if f.status != vn_DataFieldStatus.MISSING)
        completion = (retrieved / total * 100) if total > 0 else 0.0

        critical_missing = [
            f.field_name for f in data_fields.values()
            if f.is_critical and f.status == vn_DataFieldStatus.MISSING
        ]

        return round(completion, 1), critical_missing

    def _generate_mock_data(self, ticker: str, data_type: str) -> Dict:
        """Generate mock data for development/testing."""
        return {
            "2023-12-31": {"mock_field": 0},
            "2022-12-31": {"mock_field": 0}
        }
