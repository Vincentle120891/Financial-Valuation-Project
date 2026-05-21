"""
Step 6 Unified Schema Transformer - International Market

This module transforms International market Step 6 outputs from method-specific
schemas to the unified schema format (UnifiedStep6Response).

Transformation Strategy:
- DCF: Map DCFDataReviewResponse → UnifiedStep6Response
- DuPont: Map DuPontDataReviewResponse → UnifiedStep6Response
- Comps: Map CompsDataReviewResponse → UnifiedStep6Response

Key Differences:
- Legacy: Flat DataField lists with field_name, display_name, value, unit, status
- Unified: Nested structures (HistoricalFinancialsData, ForecastDriversData, etc.)
           where each field is a DataField wrapper with additional metadata

IMPORTANT: This transformer preserves ALL original data and calculations.
It only changes the wrapping structure to match the unified contract.
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from app.api.schemas.unified_step_schemas import (
    UnifiedStep6Response,
    HistoricalFinancialsData,
    ForecastDriversData,
    MarketDataBase,
    DuPontMetricsData,
    CompsMultiplesData,
    MissingDataSummary as UnifiedMissingDataSummary,
    DataField as UnifiedDataField,
    DataStatus as UnifiedDataStatus,
)

from app.services.international.step6_data_review_models import (
    Step6DataReviewResponse,
    DataStatus as LegacyDataStatus,
    DataField as LegacyDataField,
    HistoricalFinancialsDisplay,
    MarketDataDisplay,
    PeerComparablesDisplay,
    CalculatedMetricsDisplay,
)

from app.services.international.step6_dcf_data_review import DCFDataReviewResponse
from app.services.international.step6_dupont_data_review import DuPontDataReviewResponse
from app.services.international.step6_comps_data_review import CompsDataReviewResponse

logger = logging.getLogger(__name__)


class Step6UnifiedTransformer:
    """
    Transforms International Step 6 method-specific responses to unified schema.

    This is a pure transformation layer - no business logic modification.
    All calculations and data values are preserved exactly as-is.
    """

    @staticmethod
    def transform_legacy_status_to_unified(legacy_status: LegacyDataStatus) -> UnifiedDataStatus:
        """Convert legacy DataStatus enum to unified DataStatus enum"""
        mapping = {
            LegacyDataStatus.RETRIEVED: UnifiedDataStatus.RETRIEVED,
            LegacyDataStatus.CALCULATED: UnifiedDataStatus.CALCULATED,
            LegacyDataStatus.MISSING: UnifiedDataStatus.MISSING,
            LegacyDataStatus.MANUAL_OVERRIDE: UnifiedDataStatus.MANUAL_OVERRIDE,
        }
        return mapping.get(legacy_status, UnifiedDataStatus.RETRIEVED)

    @staticmethod
    def transform_legacy_datafield_to_unified(
        legacy_field: LegacyDataField,
        currency: Optional[str] = "USD",
        reporting_period: Optional[str] = None
    ) -> UnifiedDataField:
        """
        Convert legacy DataField to unified DataField format.

        Legacy format: field_name, display_name, value, unit, status, source, formula, is_critical, allow_override
        Unified format: value, status, source, formula, confidence_score, is_missing, can_override,
                       unit, currency, reporting_period, last_updated
        """
        if legacy_field is None:
            return UnifiedDataField(value=None, status=UnifiedDataStatus.MISSING, is_missing=True)

        return UnifiedDataField(
            value=legacy_field.value,
            status=Step6UnifiedTransformer.transform_legacy_status_to_unified(legacy_field.status),
            source=legacy_field.source,
            formula=legacy_field.formula,
            confidence_score=95.0 if legacy_field.status == LegacyDataStatus.RETRIEVED else
                            85.0 if legacy_field.status == LegacyDataStatus.CALCULATED else
                            50.0 if legacy_field.status == LegacyDataStatus.MISSING else 90.0,
            is_missing=(legacy_field.status == LegacyDataStatus.MISSING),
            can_override=legacy_field.allow_override,
            unit=legacy_field.unit,
            currency=currency if legacy_field.unit in ["USD", "VND", ""] else None,
            reporting_period=reporting_period,
            last_updated=datetime.now()
        )

    @staticmethod
    def transform_historical_financials_dcf(
        historical_display: Optional[HistoricalFinancialsDisplay]
    ) -> HistoricalFinancialsData:
        """Transform DCF historical financials to unified format

        IMPORTANT: Creates DataField objects for ALL expected fields, even if missing.
        This ensures frontend can display \"N/A\" instead of crashing or showing empty.
        """
        if not historical_display:
            # Return empty structure with all fields as MISSING
            result = HistoricalFinancialsData()
            # All fields will be None, which frontend interprets as MISSING
            return result

        # Create mapping from field_name to LegacyDataField
        field_map = {f.field_name: f for f in historical_display.data_fields}

        # Get reporting period from first available year
        reporting_period = f"FY{historical_display.years[-1]}" if historical_display.years else None

        result = HistoricalFinancialsData()

        # Income Statement fields - ALWAYS create DataField objects (even if MISSING)
        income_fields = [
            "revenue", "ebitda", "net_income", "depreciation",
            "cogs", "operating_expenses", "sg_and_a"
        ]

        for field_name in income_fields:
            # Map DCF field names to unified schema names
            legacy_key = field_name
            if field_name == "depreciation":
                legacy_key = "depreciation_amortization"

            if legacy_key in field_map:
                legacy_field = field_map[legacy_key]
                setattr(result, field_name, Step6UnifiedTransformer.transform_legacy_datafield_to_unified(
                    legacy_field, currency="USD", reporting_period=reporting_period
                ))
            else:
                # Create MISSING DataField for fields not in DCF response
                setattr(result, field_name, UnifiedDataField(
                    value=None,
                    status=UnifiedDataStatus.MISSING,
                    is_missing=True,
                    source=None,
                    confidence_score=0.0,
                    unit="USD",
                    reporting_period=reporting_period
                ))

        # Cash Flow fields - ALWAYS create DataField objects
        cashflow_fields = ["capex", "free_cash_flow", "operating_cash_flow"]
        for field_name in cashflow_fields:
            legacy_key = field_name  # DCF uses same names

            if legacy_key in field_map:
                legacy_field = field_map[legacy_key]
                setattr(result, field_name, Step6UnifiedTransformer.transform_legacy_datafield_to_unified(
                    legacy_field, currency="USD", reporting_period=reporting_period
                ))
            else:
                # Create MISSING DataField
                setattr(result, field_name, UnifiedDataField(
                    value=None,
                    status=UnifiedDataStatus.MISSING,
                    is_missing=True,
                    source=None,
                    confidence_score=0.0,
                    unit="USD",
                    reporting_period=reporting_period
                ))

        # Balance Sheet fields - ALWAYS create DataField objects
        balance_fields = [
            "total_assets", "total_debt", "cash_and_equivalents",
            "inventory", "accounts_receivable", "accounts_payable", "shareholders_equity"
        ]
        for field_name in balance_fields:
            if field_name in field_map:
                legacy_field = field_map[field_name]
                setattr(result, field_name, Step6UnifiedTransformer.transform_legacy_datafield_to_unified(
                    legacy_field, currency="USD", reporting_period=reporting_period
                ))
            else:
                # Create MISSING DataField
                setattr(result, field_name, UnifiedDataField(
                    value=None,
                    status=UnifiedDataStatus.MISSING,
                    is_missing=True,
                    source=None,
                    confidence_score=0.0,
                    unit="USD",
                    reporting_period=reporting_period
                ))

        # Calculated Metrics - ALWAYS create DataField objects
        calculated_fields = ["revenue_cagr", "avg_ebitda_margin", "avg_roe", "avg_roa"]
        for field_name in calculated_fields:
            if field_name in field_map:
                legacy_field = field_map[field_name]
                setattr(result, field_name, Step6UnifiedTransformer.transform_legacy_datafield_to_unified(
                    legacy_field, currency=None, reporting_period=reporting_period
                ))
            else:
                # Create MISSING DataField
                setattr(result, field_name, UnifiedDataField(
                    value=None,
                    status=UnifiedDataStatus.MISSING,
                    is_missing=True,
                    source=None,
                    confidence_score=0.0,
                    unit="%",
                    reporting_period=reporting_period
                ))

        return result

    @staticmethod
    def transform_market_data_dcf(
        market_display: Optional[MarketDataDisplay]
    ) -> MarketDataBase:
        """Transform DCF market data to unified format"""
        if not market_display:
            return MarketDataBase()

        reporting_period = "Current"
        result = MarketDataBase()

        # Map individual fields
        field_mappings = {
            "current_stock_price": market_display.current_stock_price,
            "shares_outstanding": market_display.shares_outstanding,
            "market_cap": market_display.market_cap,
            "beta": market_display.beta,
            "total_debt": market_display.total_debt,
            "cash": market_display.cash,
            "currency": market_display.currency,
        }

        for unified_field, legacy_field in field_mappings.items():
            if legacy_field is not None:
                setattr(result, unified_field, Step6UnifiedTransformer.transform_legacy_datafield_to_unified(
                    legacy_field,
                    currency="USD" if unified_field not in ["beta", "shares_outstanding"] else None,
                    reporting_period=reporting_period
                ))

        return result

    @staticmethod
    def transform_missing_data_summary(
        legacy_summary: Optional[Any]
    ) -> UnifiedMissingDataSummary:
        """Transform legacy missing data summary to unified format"""
        if not legacy_summary:
            return UnifiedMissingDataSummary(
                total_fields=0,
                retrieved_count=0,
                calculated_count=0,
                estimated_count=0,
                missing_count=0,
                manual_override_count=0,
                completion_percentage=0.0,
                valuation_ready=False,
                data_quality_score=0.0
            )

        critical_count = len(getattr(legacy_summary, 'critical_missing', []))
        optional_count = len(getattr(legacy_summary, 'optional_missing', []))
        total_missing = getattr(legacy_summary, 'total_missing', critical_count + optional_count)

        # Estimate completion percentage (assuming ~40 total fields for DCF)
        total_fields = 40
        retrieved_count = max(0, total_fields - total_missing)
        completion_pct = (retrieved_count / total_fields * 100) if total_fields > 0 else 0.0

        return UnifiedMissingDataSummary(
            total_fields=total_fields,
            retrieved_count=retrieved_count,
            calculated_count=0,  # Will be populated by calculation layer
            estimated_count=0,
            missing_count=total_missing,
            manual_override_count=0,
            completion_percentage=completion_pct,
            critical_missing=getattr(legacy_summary, 'critical_missing', []),
            optional_missing=getattr(legacy_summary, 'optional_missing', []),
            valuation_ready=(critical_count == 0),
            data_quality_score=completion_pct * 0.9,  # Quality score slightly lower than completion
            warnings=[],
            recommendations=[]
        )

    @classmethod
    def transform_dcf_response(cls, dcf_response: DCFDataReviewResponse) -> UnifiedStep6Response:
        """
        Transform DCF-specific response to unified schema.

        This is the main entry point for DCF transformation.
        """
        logger.info(f"Transforming DCF Step 6 response for {dcf_response.ticker} to unified schema")

        # Transform each section
        historical_financials = cls.transform_historical_financials_dcf(
            dcf_response.historical_financials
        )

        market_data = cls.transform_market_data_dcf(
            dcf_response.market_data
        )

        # For DCF, forecast drivers come from the forecast_drivers field
        forecast_drivers = None
        if dcf_response.forecast_drivers and dcf_response.forecast_drivers.data_fields:
            forecast_drivers = ForecastDriversData()
            # Map available forecast fields
            field_map = {f.field_name: f for f in dcf_response.forecast_drivers.data_fields}

            forecast_field_mappings = [
                "revenue_growth_forecast", "ebitda_margin_forecast", "tax_rate",
                "ar_days", "inv_days", "ap_days", "capex_pct_of_revenue",
                "risk_free_rate", "equity_risk_premium", "beta", "cost_of_debt",
                "wacc", "terminal_growth_rate", "terminal_ebitda_multiple"
            ]

            for field_name in forecast_field_mappings:
                if field_name in field_map:
                    legacy_field = field_map[field_name]
                    setattr(forecast_drivers, field_name, cls.transform_legacy_datafield_to_unified(
                        legacy_field, currency=None, reporting_period="Forecast"
                    ))

        # DCF doesn't use dupont_metrics or comps_multiples
        dupont_metrics = None
        comps_multiples = None

        missing_summary = cls.transform_missing_data_summary(dcf_response.missing_data_summary)

        return UnifiedStep6Response(
            status="success" if dcf_response.data_complete else "partial",
            session_id=dcf_response.session_id,
            ticker=dcf_response.ticker,
            market="international",
            method="DCF",
            historical_financials=historical_financials,
            forecast_drivers=forecast_drivers,
            market_data=market_data,
            dupont_metrics=dupont_metrics,
            comps_multiples=comps_multiples,
            data_source="yfinance",
            fetch_timestamp=datetime.now(),
            cache_used=False,
            periods_covered=dcf_response.historical_financials.years if dcf_response.historical_financials else [],
            missing_data_summary=missing_summary,
            data_quality_flags=[],
            warnings=[],
            message=dcf_response.message
        )

    @classmethod
    def transform_dupont_response(cls, dupont_response: DuPontDataReviewResponse) -> UnifiedStep6Response:
        """
        Transform DuPont-specific response to unified schema.

        This is the main entry point for DuPont transformation.
        """
        logger.info(f"Transforming DuPont Step 6 response for {dupont_response.ticker} to unified schema")

        # DuPont uses simpler historical financials (ROE decomposition inputs)
        historical_financials = HistoricalFinancialsData()
        if dupont_response.historical_financials and dupont_response.historical_financials.data_fields:
            field_map = {f.field_name: f for f in dupont_response.historical_financials.data_fields}
            reporting_period = f"FY{dupont_response.historical_financials.years[-1]}" if dupont_response.historical_financials.years else None

            # Map DuPont-specific fields
            dupont_fields = ["revenue", "net_income", "total_assets", "shareholders_equity",
                           "total_liabilities", "retained_earnings"]

            for field_name in dupont_fields:
                if field_name in field_map:
                    legacy_field = field_map[field_name]
                    setattr(historical_financials, field_name, cls.transform_legacy_datafield_to_unified(
                        legacy_field, currency="USD", reporting_period=reporting_period
                    ))

        # Transform market data
        market_data = MarketDataBase()
        if dupont_response.market_data:
            field_mappings = {
                "current_stock_price": dupont_response.market_data.current_stock_price,
                "shares_outstanding": dupont_response.market_data.shares_outstanding,
                "market_cap": dupont_response.market_data.market_cap,
            }

            for unified_field, legacy_field in field_mappings.items():
                if legacy_field is not None:
                    setattr(market_data, unified_field, cls.transform_legacy_datafield_to_unified(
                        legacy_field, currency="USD", reporting_period="Current"
                    ))

        # DuPont metrics from calculated_metrics
        dupont_metrics = DuPontMetricsData()
        if dupont_response.calculated_metrics:
            field_map = {f.field_name: f for f in dupont_response.calculated_metrics.data_fields}

            # Map DuPont decomposition metrics
            if "profit_margin" in field_map:
                dupont_metrics.net_profit_margin = cls.transform_legacy_datafield_to_unified(
                    field_map["profit_margin"], currency=None, reporting_period="Calculated"
                )
            if "asset_turnover" in field_map:
                dupont_metrics.asset_turnover = cls.transform_legacy_datafield_to_unified(
                    field_map["asset_turnover"], currency=None, reporting_period="Calculated"
                )
            if "equity_multiplier" in field_map:
                dupont_metrics.equity_multiplier = cls.transform_legacy_datafield_to_unified(
                    field_map["equity_multiplier"], currency=None, reporting_period="Calculated"
                )
            if "roe" in field_map:
                dupont_metrics.return_on_equity = cls.transform_legacy_datafield_to_unified(
                    field_map["roe"], currency=None, reporting_period="Calculated"
                )

        missing_summary = cls.transform_missing_data_summary(dupont_response.missing_data_summary)

        return UnifiedStep6Response(
            status="success" if dupont_response.data_complete else "partial",
            session_id=dupont_response.session_id,
            ticker=dupont_response.ticker,
            market="international",
            method="DUPONT",
            historical_financials=historical_financials,
            forecast_drivers=None,  # Not used in DuPont
            market_data=market_data,
            dupont_metrics=dupont_metrics,
            comps_multiples=None,  # Not used in DuPont
            data_source="yfinance",
            fetch_timestamp=datetime.now(),
            cache_used=False,
            periods_covered=dupont_response.historical_financials.years if dupont_response.historical_financials else [],
            missing_data_summary=missing_summary,
            data_quality_flags=[],
            warnings=[],
            message=dupont_response.message
        )

    @classmethod
    def transform_comps_response(cls, comps_response: CompsDataReviewResponse) -> UnifiedStep6Response:
        """
        Transform Comps-specific response to unified schema.

        This is the main entry point for Trading Comps transformation.
        """
        logger.info(f"Transforming Comps Step 6 response for {comps_response.ticker} to unified schema")

        # Comps historical financials (for multiple calculations)
        historical_financials = HistoricalFinancialsData()
        if comps_response.historical_financials and comps_response.historical_financials.data_fields:
            field_map = {f.field_name: f for f in comps_response.historical_financials.data_fields}
            reporting_period = f"FY{comps_response.historical_financials.years[-1]}" if comps_response.historical_financials.years else None

            comps_fields = ["revenue", "ebitda", "ebit", "net_income"]
            for field_name in comps_fields:
                if field_name in field_map:
                    legacy_field = field_map[field_name]
                    setattr(historical_financials, field_name, cls.transform_legacy_datafield_to_unified(
                        legacy_field, currency="USD", reporting_period=reporting_period
                    ))

        # Comps market data
        market_data = MarketDataBase()
        if comps_response.market_data:
            field_mappings = {
                "current_stock_price": comps_response.market_data.current_stock_price,
                "shares_outstanding": comps_response.market_data.shares_outstanding,
                "market_cap": comps_response.market_data.market_cap,
            }

            for unified_field, legacy_field in field_mappings.items():
                if legacy_field is not None:
                    setattr(market_data, unified_field, cls.transform_legacy_datafield_to_unified(
                        legacy_field, currency="USD", reporting_period="Current"
                    ))

        # Comps multiples from peer comparables
        comps_multiples = CompsMultiplesData()
        if comps_response.peer_comparables:
            # Set median multiples
            if comps_response.peer_comparables.median_ev_ebitda is not None:
                comps_multiples.ev_to_ebitda = UnifiedDataField(
                    value=comps_response.peer_comparables.median_ev_ebitda,
                    status=UnifiedDataStatus.CALCULATED,
                    source="calculated_from_peers",
                    formula="Median(Enterprise Value / EBITDA) across peer group",
                    confidence_score=85.0,
                    is_missing=False,
                    can_override=True,
                    unit="x",
                    reporting_period="TTM"
                )

            if comps_response.peer_comparables.median_pe is not None:
                comps_multiples.p_to_e = UnifiedDataField(
                    value=comps_response.peer_comparables.median_pe,
                    status=UnifiedDataStatus.CALCULATED,
                    source="calculated_from_peers",
                    formula="Median(Price / Earnings) across peer group",
                    confidence_score=85.0,
                    is_missing=False,
                    can_override=True,
                    unit="x",
                    reporting_period="TTM"
                )

            if comps_response.peer_comparables.median_ev_revenue is not None:
                comps_multiples.ev_to_sales = UnifiedDataField(
                    value=comps_response.peer_comparables.median_ev_revenue,
                    status=UnifiedDataStatus.CALCULATED,
                    source="calculated_from_peers",
                    formula="Median(Enterprise Value / Revenue) across peer group",
                    confidence_score=85.0,
                    is_missing=False,
                    can_override=True,
                    unit="x",
                    reporting_period="TTM"
                )

            if comps_response.peer_comparables.median_pb is not None:
                comps_multiples.p_to_b = UnifiedDataField(
                    value=comps_response.peer_comparables.median_pb,
                    status=UnifiedDataStatus.CALCULATED,
                    source="calculated_from_peers",
                    formula="Median(Price / Book Value) across peer group",
                    confidence_score=85.0,
                    is_missing=False,
                    can_override=True,
                    unit="x",
                    reporting_period="Current"
                )

            # CRITICAL FIX: Transform peer companies list to unified format
            # The frontend expects comps_multiples.companies array to display peer data
            if comps_response.peer_comparables.companies:
                comps_multiples.companies = [
                    {
                        "ticker": company.ticker,
                        "company_name": company.name or "",
                        "sector": "",
                        "industry": "",
                        "market_cap": company.market_cap,
                        "enterprise_value": company.enterprise_value,
                        "ev_ebitda": company.ev_ebitda,
                        "pe_ratio": company.pe_ratio,
                        "ev_revenue": company.ev_revenue,
                        "pb_ratio": company.pb_ratio,
                        "beta": company.beta,
                        "total_debt": company.total_debt,
                        "cash": company.cash,
                        "tax_rate": company.tax_rate,
                        "cost_of_debt": company.cost_of_debt,
                    }
                    for company in comps_response.peer_comparables.companies
                ]

        missing_summary = cls.transform_missing_data_summary(comps_response.missing_data_summary)

        return UnifiedStep6Response(
            status="success" if comps_response.data_complete else "partial",
            session_id=comps_response.session_id,
            ticker=comps_response.ticker,
            market="international",
            method="COMPS",
            historical_financials=historical_financials,
            forecast_drivers=None,  # Not used in Comps
            market_data=market_data,
            dupont_metrics=None,  # Not used in Comps
            comps_multiples=comps_multiples,
            data_source="yfinance",
            fetch_timestamp=datetime.now(),
            cache_used=False,
            periods_covered=comps_response.historical_financials.years if comps_response.historical_financials else [],
            missing_data_summary=missing_summary,
            data_quality_flags=[],
            warnings=[],
            message=comps_response.message
        )

    @classmethod
    def transform_any_response(
        cls,
        response: Any,
        valuation_model: str
    ) -> UnifiedStep6Response:
        """
        Universal transformer that routes to appropriate method-specific transformer.

        Args:
            response: The Step 6 response object (any method type)
            valuation_model: The valuation method ("DCF", "DUPONT", or "COMPS")

        Returns:
            UnifiedStep6Response in standardized format
        """
        model_upper = valuation_model.upper()

        if model_upper == "DCF":
            if isinstance(response, DCFDataReviewResponse):
                return cls.transform_dcf_response(response)
            else:
                logger.warning(f"Expected DCFDataReviewResponse but got {type(response)}")
                # Attempt generic transformation
                return cls.transform_dcf_response(response)

        elif model_upper == "DUPONT":
            if isinstance(response, DuPontDataReviewResponse):
                return cls.transform_dupont_response(response)
            else:
                logger.warning(f"Expected DuPontDataReviewResponse but got {type(response)}")
                return cls.transform_dupont_response(response)

        elif model_upper == "COMPS":
            if isinstance(response, CompsDataReviewResponse):
                return cls.transform_comps_response(response)
            else:
                logger.warning(f"Expected CompsDataReviewResponse but got {type(response)}")
                return cls.transform_comps_response(response)

        else:
            raise ValueError(f"Unknown valuation model: {valuation_model}. "
                           f"Supported models: DCF, DUPONT, COMPS")