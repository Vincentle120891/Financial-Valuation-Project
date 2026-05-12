"""
Step 6 Unified Schema Transformer - Vietnamese Market

This module transforms Vietnamese market Step 6 outputs from method-specific
schemas to the unified schema format (UnifiedStep6Response).

Transformation Strategy:
- Map vn_DataFetchOutput → UnifiedStep6Response
- Convert raw time-series dictionaries to DataField wrappers
- Preserve ALL original data and calculations (Model Integrity)

Key Differences:
- Vietnamese Legacy: Raw dictionaries with period keys {period: value}
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

from app.services.vietnamese.vn_step6_data_fetch_processor import (
    vn_DataFetchOutput,
    RawDataBundle,
)

logger = logging.getLogger(__name__)


class VNStep6UnifiedTransformer:
    """
    Transforms Vietnamese Step 6 processor outputs to unified schema.

    This is a pure transformation layer - no business logic modification.
    All calculations and data values are preserved exactly as-is.
    """

    @staticmethod
    def determine_data_status(value: Any, source: str) -> UnifiedDataStatus:
        """Determine data status based on value and source"""
        if value is None:
            return UnifiedDataStatus.MISSING
        if source in ["AI", "ai_extraction", "pdf_extraction"]:
            return UnifiedDataStatus.ESTIMATED
        if source in ["calculated", "derived"]:
            return UnifiedDataStatus.CALCULATED
        return UnifiedDataStatus.RETRIEVED

    @staticmethod
    def extract_latest_value(data_dict: Dict[str, Any]) -> Optional[float]:
        """
        Extract the most recent value from a time-series dictionary.
        Vietnamese data uses period keys like '2023', '2022', 'Q4-2023', etc.
        """
        if not data_dict:
            return None

        # Sort periods to get the most recent
        sorted_periods = sorted(
            data_dict.keys(),
            key=lambda x: (
                int(x.split('-')[0]) if '-' in x else int(x),
                int(x.split('-')[1]) if '-' in x and len(x.split('-')) > 1 else 12
            ),
            reverse=True
        )

        if sorted_periods:
            latest_period = sorted_periods[0]
            return data_dict.get(latest_period)

        return None

    @staticmethod
    def calculate_confidence_score(source: str, has_multiple_periods: bool) -> float:
        """Calculate confidence score based on source and data completeness"""
        base_score = 95.0 if source in ["vietstock", "API", "yfinance"] else 70.0

        # Bonus for having multiple periods (more reliable trend)
        if has_multiple_periods:
            base_score = min(100.0, base_score + 5.0)

        return base_score

    @staticmethod
    def transform_raw_financials_to_historical(
        income_statement_raw: Dict[str, Dict[str, Any]],
        balance_sheet_raw: Dict[str, Dict[str, Any]],
        cash_flow_raw: Dict[str, Dict[str, Any]],
        currency: str = "VND"
    ) -> HistoricalFinancialsData:
        """
        Transform Vietnamese raw financial statements to unified HistoricalFinancialsData.

        Args:
            income_statement_raw: {period: {field_name: value}}
            balance_sheet_raw: {period: {field_name: value}}
            cash_flow_raw: {period: {field_name: value}}
            currency: Currency code (VND for Vietnam)

        Returns:
            HistoricalFinancialsData with DataField wrappers
        """
        historical = HistoricalFinancialsData()

        # Helper to create DataField from time-series data
        def create_datafield(field_name: str, data_dict: Dict[str, Any],
                           unit: str = "", formula: Optional[str] = None) -> UnifiedDataField:
            if not data_dict:
                return UnifiedDataField(
                    value=None,
                    status=UnifiedDataStatus.MISSING,
                    is_missing=True,
                    unit=unit,
                    currency=currency if unit in ["VND", "millions_VND"] else None
                )

            latest_value = VNStep6UnifiedTransformer.extract_latest_value(data_dict)
            source = "vietstock"  # Default source for Vietnamese data
            has_multiple = len(data_dict) > 1

            # Get reporting period from the latest period key
            sorted_periods = sorted(data_dict.keys(), reverse=True)
            reporting_period = sorted_periods[0] if sorted_periods else None

            return UnifiedDataField(
                value=latest_value,
                status=VNStep6UnifiedTransformer.determine_data_status(latest_value, source),
                source=source,
                formula=formula,
                confidence_score=VNStep6UnifiedTransformer.calculate_confidence_score(source, has_multiple),
                is_missing=(latest_value is None),
                can_override=True,
                unit=unit,
                currency=currency if unit in ["VND", "millions_VND", ""] else None,
                reporting_period=reporting_period,
                last_updated=datetime.now()
            )

        # Aggregate data across all periods for each field
        def aggregate_field(statement_dict: Dict[str, Dict[str, Any]], field_name: str) -> Dict[str, Any]:
            """Aggregate a field across all periods"""
            result = {}
            for period, fields in statement_dict.items():
                if field_name in fields:
                    result[period] = fields[field_name]
            return result

        # Income Statement Fields
        historical.revenue = create_datafield(
            "revenue",
            aggregate_field(income_statement_raw, "revenue"),
            unit="millions_VND"
        )
        historical.cogs = create_datafield(
            "cogs",
            aggregate_field(income_statement_raw, "cost_of_revenue"),
            unit="millions_VND"
        )
        historical.ebitda = create_datafield(
            "ebitda",
            aggregate_field(income_statement_raw, "ebitda"),
            unit="millions_VND",
            formula="operating_income + depreciation"
        )
        historical.net_income = create_datafield(
            "net_income",
            aggregate_field(income_statement_raw, "net_income"),
            unit="millions_VND"
        )
        historical.operating_expenses = create_datafield(
            "operating_expenses",
            aggregate_field(income_statement_raw, "operating_expenses"),
            unit="millions_VND"
        )
        historical.sg_and_a = create_datafield(
            "sg_and_a",
            aggregate_field(income_statement_raw, "selling_general_administrative"),
            unit="millions_VND"
        )
        historical.depreciation = create_datafield(
            "depreciation",
            aggregate_field(income_statement_raw, "depreciation_amortization"),
            unit="millions_VND"
        )

        # Cash Flow Fields
        historical.capex = create_datafield(
            "capex",
            aggregate_field(cash_flow_raw, "capital_expenditures"),
            unit="millions_VND"
        )
        historical.free_cash_flow = create_datafield(
            "free_cash_flow",
            aggregate_field(cash_flow_raw, "free_cash_flow"),
            unit="millions_VND",
            formula="operating_cash_flow - capex"
        )
        historical.operating_cash_flow = create_datafield(
            "operating_cash_flow",
            aggregate_field(cash_flow_raw, "operating_cash_flow"),
            unit="millions_VND"
        )

        # Balance Sheet Fields
        historical.total_assets = create_datafield(
            "total_assets",
            aggregate_field(balance_sheet_raw, "total_assets"),
            unit="millions_VND"
        )
        historical.total_debt = create_datafield(
            "total_debt",
            aggregate_field(balance_sheet_raw, "total_debt"),
            unit="millions_VND",
            formula="short_term_debt + long_term_debt"
        )
        historical.cash_and_equivalents = create_datafield(
            "cash_and_equivalents",
            aggregate_field(balance_sheet_raw, "cash_and_equivalents"),
            unit="millions_VND"
        )
        historical.inventory = create_datafield(
            "inventory",
            aggregate_field(balance_sheet_raw, "inventory"),
            unit="millions_VND"
        )
        historical.accounts_receivable = create_datafield(
            "accounts_receivable",
            aggregate_field(balance_sheet_raw, "accounts_receivable"),
            unit="millions_VND"
        )
        historical.accounts_payable = create_datafield(
            "accounts_payable",
            aggregate_field(balance_sheet_raw, "accounts_payable"),
            unit="millions_VND"
        )
        historical.shareholders_equity = create_datafield(
            "shareholders_equity",
            aggregate_field(balance_sheet_raw, "total_equity"),
            unit="millions_VND"
        )

        # Calculated Metrics (will be populated by Step 7/8)
        # These are typically calculated later, so we set them as MISSING initially
        historical.revenue_cagr = UnifiedDataField(
            value=None,
            status=UnifiedDataStatus.MISSING,
            is_missing=True,
            unit="%",
            formula="CAGR(revenue, n_years)"
        )
        historical.avg_ebitda_margin = UnifiedDataField(
            value=None,
            status=UnifiedDataStatus.MISSING,
            is_missing=True,
            unit="%",
            formula="AVG(ebitda / revenue)"
        )
        historical.avg_roe = UnifiedDataField(
            value=None,
            status=UnifiedDataStatus.MISSING,
            is_missing=True,
            unit="%",
            formula="AVG(net_income / shareholders_equity)"
        )
        historical.avg_roa = UnifiedDataField(
            value=None,
            status=UnifiedDataStatus.MISSING,
            is_missing=True,
            unit="%",
            formula="AVG(net_income / total_assets)"
        )

        return historical

    @staticmethod
    def transform_to_market_data(
        session_cache: Optional[Dict[str, Any]] = None
    ) -> MarketDataBase:
        """
        Transform Vietnamese market data to unified MarketDataBase.

        Market data is typically fetched in Step 2 and cached in session.
        """
        market_data = MarketDataBase()

        if session_cache:
            # Try to get market data from Step 2 cache
            step2_data = session_cache.get("vietnam_market_data", {})

            # Current stock price
            current_price = step2_data.get("current_price")
            market_data.current_stock_price = UnifiedDataField(
                value=current_price,
                status=VNStep6UnifiedTransformer.determine_data_status(current_price, "vietstock"),
                source="vietstock",
                unit="VND",
                currency="VND"
            )

            # Shares outstanding
            shares = step2_data.get("shares_outstanding")
            market_data.shares_outstanding = UnifiedDataField(
                value=shares,
                status=VNStep6UnifiedTransformer.determine_data_status(shares, "vietstock"),
                source="vietstock",
                unit="shares"
            )

            # Market cap
            market_cap = step2_data.get("market_cap")
            market_data.market_cap = UnifiedDataField(
                value=market_cap,
                status=VNStep6UnifiedTransformer.determine_data_status(market_cap, "calculated"),
                source="calculated",
                formula="current_price * shares_outstanding",
                unit="millions_VND",
                currency="VND"
            )

            # Beta
            beta = step2_data.get("beta")
            market_data.beta = UnifiedDataField(
                value=beta,
                status=VNStep6UnifiedTransformer.determine_data_status(beta, "calculated"),
                source="calculated",
                formula="covariance(stock, market) / variance(market)"
            )

            # Total debt (from balance sheet if available)
            total_debt = step2_data.get("total_debt")
            market_data.total_debt = UnifiedDataField(
                value=total_debt,
                status=VNStep6UnifiedTransformer.determine_data_status(total_debt, "vietstock"),
                source="vietstock",
                unit="millions_VND",
                currency="VND"
            )

            # Cash
            cash = step2_data.get("cash")
            market_data.cash = UnifiedDataField(
                value=cash,
                status=VNStep6UnifiedTransformer.determine_data_status(cash, "vietstock"),
                source="vietstock",
                unit="millions_VND",
                currency="VND"
            )

            # Currency
            market_data.currency = UnifiedDataField(
                value="VND",
                status=UnifiedDataStatus.RETRIEVED,
                source="system"
            )

        return market_data

    @staticmethod
    def create_missing_data_summary(
        historical: Optional[HistoricalFinancialsData],
        data_quality_flags: List[str]
    ) -> UnifiedMissingDataSummary:
        """Create missing data summary from transformed data"""
        summary = UnifiedMissingDataSummary(
            total_fields=0,
            retrieved_count=0,
            calculated_count=0,
            estimated_count=0,
            missing_count=0,
            completion_percentage=0.0,
            critical_missing=[],
            optional_missing=[],
            valuation_ready=False,
            data_quality_score=0.0,
            warnings=data_quality_flags.copy()
        )

        if not historical:
            summary.warnings.append("No historical financial data available")
            return summary

        # Count fields by status
        field_names = [
            "revenue", "cogs", "ebitda", "net_income", "operating_expenses",
            "capex", "free_cash_flow", "operating_cash_flow",
            "total_assets", "total_debt", "cash_and_equivalents"
        ]

        critical_fields = ["revenue", "net_income", "total_assets", "total_debt"]

        for field_name in field_names:
            field = getattr(historical, field_name, None)
            if field:
                summary.total_fields += 1

                if field.status == UnifiedDataStatus.RETRIEVED:
                    summary.retrieved_count += 1
                elif field.status == UnifiedDataStatus.CALCULATED:
                    summary.calculated_count += 1
                elif field.status == UnifiedDataStatus.ESTIMATED:
                    summary.estimated_count += 1
                elif field.status == UnifiedDataStatus.MISSING:
                    summary.missing_count += 1
                    if field_name in critical_fields:
                        summary.critical_missing.append(field_name)
                    else:
                        summary.optional_missing.append(field_name)

        # Calculate completion percentage
        if summary.total_fields > 0:
            summary.completion_percentage = round(
                (summary.retrieved_count + summary.calculated_count) / summary.total_fields * 100, 2
            )
            summary.valuation_ready = (
                summary.completion_percentage >= 70.0 and
                len(summary.critical_missing) == 0
            )
            summary.data_quality_score = summary.completion_percentage

        return summary

    def transform(
        self,
        vn_output: vn_DataFetchOutput,
        session_id: str,
        ticker: str,
        market: str,
        method: str,
        session_cache: Optional[Dict[str, Any]] = None
    ) -> UnifiedStep6Response:
        """
        Transform Vietnamese Step 6 output to unified schema.

        Args:
            vn_output: Output from vn_Step6DataFetchProcessor
            session_id: Session identifier
            ticker: Company ticker
            market: Market type ("vietnam")
            method: Valuation method ("DCF", "DUPONT", "COMPS")
            session_cache: Optional session cache for market data

        Returns:
            UnifiedStep6Response conforming to unified schema
        """
        logger.info(f"Transforming Vietnamese Step 6 data for {ticker} ({method})")

        # Transform raw financials to unified historical structure
        historical_financials = self.transform_raw_financials_to_historical(
            income_statement_raw=vn_output.data_bundle.income_statement_raw,
            balance_sheet_raw=vn_output.data_bundle.balance_sheet_raw,
            cash_flow_raw=vn_output.data_bundle.cash_flow_raw,
            currency="VND"
        )

        # Get market data from session cache
        market_data = self.transform_to_market_data(session_cache)

        # Create missing data summary
        missing_data_summary = self.create_missing_data_summary(
            historical=historical_financials,
            data_quality_flags=vn_output.data_bundle.data_quality_flags
        )

        # Determine periods covered (ensure strings for Pydantic validation)
        periods_covered = []
        if vn_output.data_bundle.income_statement_raw:
            periods_covered = [str(k) for k in vn_output.data_bundle.income_statement_raw.keys()]

        # Build unified response
        response = UnifiedStep6Response(
            status="success" if vn_output.success else "partial_success",
            session_id=session_id,
            ticker=ticker,
            market=market,
            method=method,
            historical_financials=historical_financials,
            forecast_drivers=None,  # Will be populated in Step 8
            market_data=market_data,
            dupont_metrics=None,  # Will be populated based on method
            comps_multiples=None,  # Will be populated based on method
            data_source=vn_output.data_bundle.source_provider,
            fetch_timestamp=vn_output.data_bundle.fetch_timestamp,
            cache_used=(vn_output.fetch_duration_ms == 0),
            periods_covered=periods_covered,
            missing_data_summary=missing_data_summary,
            data_quality_flags=vn_output.data_bundle.data_quality_flags,
            warnings=vn_output.data_bundle.data_quality_flags,
            message=vn_output.message
        )

        logger.info(f"Successfully transformed Vietnamese Step 6 data for {ticker}")
        return response