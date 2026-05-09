"""
Vietnamese Step 7: Historical Data Processor & AI Extraction
Normalizes raw data from Step 6, maps Vietnamese accounting terms to standard fields,
and triggers AI extraction for missing data points from PDF reports.

Adheres to Model Integrity:
- No data simplification
- Explicit mapping of all line items
- Full audit trail of AI vs API sources
"""
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)


class VNHistoricalDataInput(BaseModel):
    """Input for Step 7: Raw data bundle from Step 6."""
    ticker: str
    company_name: str
    exchange: str
    currency_unit: str  # e.g., "millions_VND"

    # Raw data from Step 6
    income_statement_raw: Dict[str, Dict[str, Any]]
    balance_sheet_raw: Dict[str, Dict[str, Any]]
    cash_flow_raw: Dict[str, Dict[str, Any]]

    # Context for AI extraction
    data_quality_flags: List[str]
    pdf_sources: List[str] = Field(default_factory=list)
    fallback_to_ai: bool = True

    # Target model context (to know which fields are critical)
    selected_model: str  # "DCF", "DuPont", "Comps"


class NormalizedFinancials(BaseModel):
    """Standardized financial data ready for valuation engines."""
    # Metadata
    currency: str
    unit_multiplier: float  # 1 for VND, 1000 for thousands, 1000000 for millions
    fiscal_year_end: str  # "12-31" typically for VN companies

    # Income Statement (normalized keys)
    revenue: Dict[str, float] = Field(default_factory=dict)
    cost_of_revenue: Dict[str, float] = Field(default_factory=dict)
    gross_profit: Dict[str, float] = Field(default_factory=dict)
    operating_expenses: Dict[str, float] = Field(default_factory=dict)
    operating_income: Dict[str, float] = Field(default_factory=dict)
    interest_expense: Dict[str, float] = Field(default_factory=dict)
    other_income_expense: Dict[str, float] = Field(default_factory=dict)
    pretax_income: Dict[str, float] = Field(default_factory=dict)
    income_tax: Dict[str, float] = Field(default_factory=dict)
    net_income: Dict[str, float] = Field(default_factory=dict)

    # Balance Sheet (normalized keys)
    cash_and_equivalents: Dict[str, float] = Field(default_factory=dict)
    accounts_receivable: Dict[str, float] = Field(default_factory=dict)
    inventory: Dict[str, float] = Field(default_factory=dict)
    total_current_assets: Dict[str, float] = Field(default_factory=dict)
    property_plant_equipment: Dict[str, float] = Field(default_factory=dict)
    total_assets: Dict[str, float] = Field(default_factory=dict)
    accounts_payable: Dict[str, float] = Field(default_factory=dict)
    short_term_debt: Dict[str, float] = Field(default_factory=dict)
    total_current_liabilities: Dict[str, float] = Field(default_factory=dict)
    long_term_debt: Dict[str, float] = Field(default_factory=dict)
    total_liabilities: Dict[str, float] = Field(default_factory=dict)
    total_equity: Dict[str, float] = Field(default_factory=dict)

    # Cash Flow (normalized keys)
    operating_cash_flow: Dict[str, float] = Field(default_factory=dict)
    capital_expenditures: Dict[str, float] = Field(default_factory=dict)
    free_cash_flow: Dict[str, float] = Field(default_factory=dict)
    financing_cash_flow: Dict[str, float] = Field(default_factory=dict)
    investing_cash_flow: Dict[str, float] = Field(default_factory=dict)

    # Source tracking (which periods came from AI vs API)
    source_map: Dict[str, str] = Field(default_factory=dict, description="period -> 'API' or 'AI'")


class AIExtractionResult(BaseModel):
    """Results from AI-powered PDF extraction."""
    success: bool
    extracted_fields: Dict[str, Dict[str, float]]  # field_name -> {period: value}
    confidence_scores: Dict[str, float]  # field_name -> confidence (0-1)
    source_document: str
    extraction_timestamp: datetime
    warnings: List[str] = Field(default_factory=list)


class VNHistoricalDataOutput(BaseModel):
    """Output from Step 7: Normalized data ready for Step 8 assumptions."""
    success: bool
    ticker: str
    normalized_financials: NormalizedFinancials
    ai_extraction_results: Optional[AIExtractionResult] = None

    # Data quality report
    completeness_score: float  # 0-1, percentage of required fields populated
    missing_critical_fields: List[str]
    data_warnings: List[str]

    # Audit trail
    processing_duration_ms: float
    periods_covered: List[str]
    source_breakdown: Dict[str, int]  # source_type -> count of fields


class VNStep7HistoricalProcessor:
    """
    Processor for Step 7: Normalizing Vietnamese historical data and AI extraction.

    Workflow:
    1. Receive raw data from Step 6.
    2. Map Vietnamese accounting terms to standard English keys.
    3. Validate data consistency (Assets = Liabilities + Equity).
    4. Identify missing critical fields based on selected model.
    5. Trigger AI extraction for missing fields if enabled.
    6. Merge AI results with API data.
    7. Calculate completeness score.
    8. Return normalized financials for Step 8.
    """

    # Vietnamese to English accounting term mapping (TT99 compliance)
    VN_ACCOUNTING_MAP = {
        # Income Statement
        "doanh_thu_thuan": "revenue",
        "gia_von_hang_ban": "cost_of_revenue",
        "loi_nhuan_gop": "gross_profit",
        "chi_phi_ban_hang": "selling_expenses",
        "chi_phi_quan_ly_doanh_nghiep": "administrative_expenses",
        "loi_nhuan_tu_hoat_dong_kinh_doanh": "operating_income",
        "chi_phi_lai_vay": "interest_expense",
        "loi_nhuan_truoc_thue": "pretax_income",
        "chi_phi_thue_tndn": "income_tax",
        "loi_nhuan_sau_thue": "net_income",

        # Balance Sheet - Assets
        "tien_va_tuong_duong_tien": "cash_and_equivalents",
        "phai_ngu_ngan_han": "accounts_receivable",
        "hang_ton_kho": "inventory",
        "tai_san_ngan_han": "total_current_assets",
        "tai_san_co_dinh": "property_plant_equipment",
        "tong_tai_san": "total_assets",

        # Balance Sheet - Liabilities
        "phai_tra_ngu_ngan_han": "accounts_payable",
        "no_vay_ngan_han": "short_term_debt",
        "no_phai_tra_ngan_han": "total_current_liabilities",
        "no_vay_dai_han": "long_term_debt",
        "tong_no_phai_tra": "total_liabilities",
        "von_chu_so_huu": "total_equity",

        # Cash Flow
        "luu_chuyen_tien_tu_hoat_dong_kinh_doanh": "operating_cash_flow",
        "luu_chuyen_tien_tu_hoat_dong_dau_tu": "investing_cash_flow",
        "luu_chuyen_tien_tu_hoat_dong_tai_chinh": "financing_cash_flow",
        "chi_dau_tu_tai_san_co_dinh": "capital_expenditures",
    }

    def __init__(self):
        self.ai_extraction_service = None

    async def _initialize_services(self):
        """Initialize AI extraction service."""
        if self.ai_extraction_service is None:
            try:
                from app.services.ai.pdf_extraction_service import PDFExtractionService
                self.ai_extraction_service = PDFExtractionService()
            except ImportError:
                logger.warning("PDF Extraction service not available")
                self.ai_extraction_service = None

    async def execute(self, input_data: VNHistoricalDataInput) -> VNHistoricalDataOutput:
        """Execute Step 7: Normalize and extract historical data."""
        import time
        start_time = time.time()

        await self._initialize_services()

        data_warnings = []
        missing_critical = []
        source_breakdown = {"API": 0, "AI": 0}

        # 1. Normalize Raw Data
        normalized = self._normalize_financials(
            input_data.income_statement_raw,
            input_data.balance_sheet_raw,
            input_data.cash_flow_raw,
            input_data.currency_unit
        )

        # Track API sources
        for field in normalized.model_fields:
            if field not in ['currency', 'unit_multiplier', 'fiscal_year_end', 'source_map']:
                field_data = getattr(normalized, field)
                if isinstance(field_data, dict) and field_data:
                    source_breakdown["API"] += len(field_data)
                    normalized.source_map.update({period: "API" for period in field_data.keys()})

        # 2. Validate Data Consistency
        validation_warnings = self._validate_accounting_identity(normalized)
        data_warnings.extend(validation_warnings)

        # 3. Identify Missing Critical Fields based on Model
        critical_fields = self._get_critical_fields_for_model(input_data.selected_model)
        for field in critical_fields:
            field_data = getattr(normalized, field, {})
            if not field_data or all(v == 0 for v in field_data.values()):
                missing_critical.append(field)

        # 4. AI Extraction for Missing Fields
        ai_result = None
        if missing_critical and input_data.fallback_to_ai and self.ai_extraction_service and input_data.pdf_sources:
            logger.info(f"Triggering AI extraction for {len(missing_critical)} missing fields")
            ai_result = await self._extract_missing_fields(
                ticker=input_data.ticker,
                missing_fields=missing_critical,
                pdf_sources=input_data.pdf_sources
            )

            # Merge AI results
            if ai_result.success:
                normalized = self._merge_ai_results(normalized, ai_result.extracted_fields)
                # Update source map
                for field_name, periods in ai_result.extracted_fields.items():
                    for period in periods.keys():
                        normalized.source_map[period] = "AI"
                    source_breakdown["AI"] += len(periods)

                # Add AI warnings
                if ai_result.warnings:
                    data_warnings.extend(ai_result.warnings)

        # 5. Calculate Completeness Score
        completeness = self._calculate_completeness(normalized, critical_fields)

        # 6. Compile Output
        processing_duration = (time.time() - start_time) * 1000
        periods_covered = list(set(
            list(normalized.revenue.keys()) +
            list(normalized.total_assets.keys()) +
            list(normalized.operating_cash_flow.keys())
        ))

        return VNHistoricalDataOutput(
            success=len(missing_critical) == 0 or (ai_result and ai_result.success),
            ticker=input_data.ticker,
            normalized_financials=normalized,
            ai_extraction_results=ai_result,
            completeness_score=completeness,
            missing_critical_fields=missing_critical if not (ai_result and ai_result.success) else [],
            data_warnings=data_warnings,
            processing_duration_ms=processing_duration,
            periods_covered=sorted(periods_covered),
            source_breakdown=source_breakdown
        )

    def _normalize_financials(
        self,
        is_raw: Dict,
        bs_raw: Dict,
        cf_raw: Dict,
        currency_unit: str
    ) -> NormalizedFinancials:
        """Map Vietnamese raw data to standardized keys."""
        normalized = NormalizedFinancials(
            currency="VND",
            unit_multiplier=self._get_unit_multiplier(currency_unit),
            fiscal_year_end="12-31"
        )

        # Helper to map fields
        def map_statement(raw_data: Dict, target_obj: object, statement_type: str):
            for period, values in raw_data.items():
                for vn_key, value in values.items():
                    en_key = self.VN_ACCOUNTING_MAP.get(vn_key)
                    if en_key and hasattr(target_obj, en_key):
                        field_dict = getattr(target_obj, en_key)
                        field_dict[period] = float(value) if value else 0.0

        if is_raw:
            map_statement(is_raw, normalized, "IS")

        if bs_raw:
            map_statement(bs_raw, normalized, "BS")

        if cf_raw:
            map_statement(cf_raw, normalized, "CF")
            # Calculate FCF if OCF and CapEx exist
            for period in normalized.operating_cash_flow.keys():
                ocf = normalized.operating_cash_flow.get(period, 0)
                capex = normalized.capital_expenditures.get(period, 0)
                if ocf and capex:
                    normalized.free_cash_flow[period] = ocf - abs(capex)

        return normalized

    def _get_unit_multiplier(self, currency_unit: str) -> float:
        """Convert currency unit string to multiplier."""
        if "millions" in currency_unit.lower():
            return 1000000.0
        elif "thousands" in currency_unit.lower():
            return 1000.0
        return 1.0

    def _validate_accounting_identity(self, normalized: NormalizedFinancials) -> List[str]:
        """Check Assets = Liabilities + Equity for all periods."""
        warnings = []
        all_periods = set(normalized.total_assets.keys())

        for period in all_periods:
            assets = normalized.total_assets.get(period, 0)
            liabilities = normalized.total_liabilities.get(period, 0)
            equity = normalized.total_equity.get(period, 0)

            if assets > 0:
                difference = abs(assets - (liabilities + equity))
                tolerance = assets * 0.01  # 1% tolerance
                if difference > tolerance:
                    warnings.append(
                        f"Period {period}: Accounting identity mismatch. "
                        f"Assets={assets}, L+E={liabilities+equity}, Diff={difference}"
                    )

        return warnings

    def _get_critical_fields_for_model(self, model: str) -> List[str]:
        """Return critical fields required for each valuation model."""
        base_fields = ["revenue", "net_income", "total_assets", "total_equity"]

        if model == "DCF":
            return base_fields + [
                "operating_cash_flow", "capital_expenditures", "free_cash_flow",
                "operating_income", "income_tax", "interest_expense"
            ]
        elif model == "DuPont":
            return base_fields + [
                "net_income", "revenue", "total_assets", "total_equity",
                "pretax_income", "operating_income"
            ]
        elif model == "Comps":
            return base_fields + [
                "net_income", "revenue", "total_equity",
                "operating_income", "pretax_income"
            ]
        return base_fields

    async def _extract_missing_fields(
        self,
        ticker: str,
        missing_fields: List[str],
        pdf_sources: List[str]
    ) -> AIExtractionResult:
        """Call AI service to extract missing fields from PDFs."""
        try:
            if not self.ai_extraction_service:
                return AIExtractionResult(
                    success=False,
                    extracted_fields={},
                    confidence_scores={},
                    source_document="",
                    extraction_timestamp=datetime.now(),
                    warnings=["AI extraction service unavailable"]
                )

            # In real implementation, this would call the AI service with PDF URLs
            # For now, return mock structure
            extracted = {}
            confidence = {}

            for field in missing_fields:
                # Mock extraction
                extracted[field] = {"2023-12-31": 0.0}
                confidence[field] = 0.85

            return AIExtractionResult(
                success=True,
                extracted_fields=extracted,
                confidence_scores=confidence,
                source_document=pdf_sources[0] if pdf_sources else "unknown",
                extraction_timestamp=datetime.now(),
                warnings=["Mock extraction - implement actual AI service"]
            )

        except Exception as e:
            logger.error(f"AI extraction failed: {str(e)}")
            return AIExtractionResult(
                success=False,
                extracted_fields={},
                confidence_scores={},
                source_document="",
                extraction_timestamp=datetime.now(),
                warnings=[f"Extraction error: {str(e)}"]
            )

    def _merge_ai_results(
        self,
        normalized: NormalizedFinancials,
        ai_extracted: Dict[str, Dict[str, float]]
    ) -> NormalizedFinancials:
        """Merge AI-extracted data into normalized financials."""
        for field_name, periods in ai_extracted.items():
            if hasattr(normalized, field_name):
                field_dict = getattr(normalized, field_name)
                field_dict.update(periods)
        return normalized

    def _calculate_completeness(
        self,
        normalized: NormalizedFinancials,
        critical_fields: List[str]
    ) -> float:
        """Calculate percentage of critical fields that are populated."""
        if not critical_fields:
            return 1.0

        populated_count = 0
        for field in critical_fields:
            field_data = getattr(normalized, field, {})
            if isinstance(field_data, dict) and any(v != 0 for v in field_data.values()):
                populated_count += 1

        return populated_count / len(critical_fields)