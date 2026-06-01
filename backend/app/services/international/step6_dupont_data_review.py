"""Step 6: DuPont Data Review Layer - Pure Data Aggregation for DuPont Method

This is a dedicated processor for DuPont Analysis valuation method only.
It eliminates conditional branching by focusing exclusively on DuPont-specific data requirements.

Features:
- DuPont-specific historical financials processing (ROE decomposition inputs)
- DuPont market data aggregation
- DuPont intermediate metrics calculation (profit margin, asset turnover, equity multiplier)
"""
import logging
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime
import pandas as pd

from .yfinance_service import YFinanceService

logger = logging.getLogger(__name__)


class DataStatus(str, Enum):
    """Status of data field"""
    RETRIEVED = "RETRIEVED"
    CALCULATED = "CALCULATED"
    MISSING = "MISSING"
    MANUAL_OVERRIDE = "MANUAL_OVERRIDE"


class DataField(BaseModel):
    """A single data field with status tracking"""
    field_name: str
    display_name: Optional[str] = None
    value: Optional[Any] = None
    unit: str = ""
    status: DataStatus
    source: Optional[str] = None
    formula: Optional[str] = None
    is_critical: bool = False
    allow_override: bool = False


class HistoricalFinancialsDisplay(BaseModel):
    """Historical financial data display for DuPont"""
    years: List[str] = []  # Changed from List[int] to List[str] to match UnifiedStep6Response.periods_covered
    data_fields: List[DataField] = []


class MarketDataDisplay(BaseModel):
    """Market data display for DuPont"""
    current_stock_price: Optional[DataField] = None
    shares_outstanding: Optional[DataField] = None
    market_cap: Optional[DataField] = None
    book_value: Optional[DataField] = None
    data_fields: List[DataField] = []


class CalculatedMetricsDisplay(BaseModel):
    """Calculated metrics from retrieved data for DuPont (NOT final valuations)"""
    profit_margin: Optional[DataField] = None
    asset_turnover: Optional[DataField] = None
    equity_multiplier: Optional[DataField] = None
    roe: Optional[DataField] = None
    data_fields: List[DataField] = []


class MissingDataSummary(BaseModel):
    """Aggregation metrics summarizing data completeness for frontend components"""
    total_fields: int
    retrieved_count: int
    calculated_count: int
    missing_count: int
    critical_missing: List[str] = Field(default_factory=list)
    optional_missing: List[str] = Field(default_factory=list)
    completion_percentage: float
    data_quality_score: float
    valuation_ready: bool
    estimated_count: int = 0
    manual_override_count: int = 0
    warnings: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


class DuPontDataReviewResponse(BaseModel):
    """
    Step 6 DuPont Response: Shows all retrieved inputs, missing inputs,
    and calculated intermediate metrics. NO FINAL VALUATIONS.
    """
    session_id: str
    ticker: str
    timestamp: datetime
    valuation_model: str = "DUPONT"
    historical_financials: Optional[HistoricalFinancialsDisplay] = None
    market_data: Optional[MarketDataDisplay] = None
    calculated_metrics: Optional[CalculatedMetricsDisplay] = None
    missing_data_summary: Optional[MissingDataSummary] = None
    manual_overrides_applied: Dict[str, Any] = {}
    data_complete: bool = False
    message: str = ""


class DuPontStep6Processor:
    """
    Dedicated Step 6 processor for DuPont valuation method.

    This processor handles ONLY DuPont-specific data aggregation:
    - Historical Financials (Revenue, Net Income, Total Assets, Shareholders Equity)
    - Market Data (Price, Market Cap, Book Value)
    - Intermediate Metrics (Profit Margin, Asset Turnover, Equity Multiplier, ROE)
    """

    def __init__(self):
        self.yfinance_service = YFinanceService()

    async def process_dupont_data_review(
        self,
        ticker: str,
        market: str = "international",
        historical_data: Optional[Dict] = None,
        market_data: Optional[Dict] = None,
        retrieved_assumptions: Optional[Dict] = None,
        user_overrides: Optional[Dict[str, Any]] = None,
        session_cache: Optional[Dict] = None  # NEW: Session cache for "Fetch Once, Use Many"
    ) -> DuPontDataReviewResponse:
        """
        Main entry point for DuPont Step 6 data review.
        Aggregates all retrieved DuPont data without performing final calculations.

        Args:
            ticker: Stock ticker symbol
            market: Market identifier
            historical_data: Historical financial data (optional, will fetch if not provided)
            market_data: Market data (optional, will fetch if not provided)
            retrieved_assumptions: Retrieved assumptions including peer data
            user_overrides: Manual overrides applied by user
            session_cache: Session cache dict to check before fetching (implements "Fetch Once, Use Many")

        Returns:
            DuPontDataReviewResponse with aggregated DuPont data
        """
        # GAP 1 FIX: Check session cache before fetching - implements "Fetch Once, Use Many"
        if session_cache and 'international_market_data' in session_cache:
            cached_data = session_cache['international_market_data']
            # Check if cache is valid (not older than 5 minutes)
            cache_timestamp = cached_data.get('timestamp')
            if cache_timestamp:
                from datetime import datetime, timedelta
                cache_age = datetime.now() - cache_timestamp
                if cache_age < timedelta(minutes=5):
                    logger.info(f"Using cached market data for {ticker} (age: {cache_age.seconds}s)")
                    historical_data = historical_data or cached_data.get('historical_data')
                    market_data = market_data or cached_data.get('market_data')
                    retrieved_assumptions = retrieved_assumptions or cached_data.get('retrieved_assumptions')

        # If data is not provided (and not in cache), fetch it via APIAdapter (unified approach)
        if historical_data is None or market_data is None:
            logger.info(f"Fetching data for DuPont analysis of {ticker}")
            from ..api_adapter import APIAdapter
            adapter = APIAdapter()

            # GAP 2 FIX: Use correct two-step process (fetch_raw_data -> map_and_normalize) matching DCF pattern
            required_metrics = ["revenue", "net_income", "total_assets", "shareholders_equity",
                               "current_stock_price", "shares_outstanding", "market_cap", "book_value_per_share"]
            raw_result = adapter.fetch_raw_data(ticker, required_metrics)
            mapped_result = adapter.map_and_normalize(raw_result, ticker)
            raw_data = mapped_result.get("raw_data", {})

            # Build DataFrames from raw yfinance data (same pattern as DCF)
            def build_financials_from_api_data(api_data):
                """Build income statement DataFrame from APIAdapter response"""
                if not api_data:
                    return None
                periods = api_data.get('periods', [])
                data_rows = {k: v for k, v in api_data.items() if k != 'periods' and isinstance(v, list)}
                if not data_rows or not periods:
                    return None
                df = pd.DataFrame(data_rows, index=periods).T
                df.columns = pd.to_datetime(df.columns)
                return df

            def build_balance_sheet_df(raw_data):
                """Build balance sheet DataFrame from APIAdapter raw data"""
                bs_data = raw_data.get('balance_sheet', {})
                if not bs_data:
                    return None
                periods = bs_data.get('periods', [])
                data_rows = {k: v for k, v in bs_data.items() if k != 'periods' and isinstance(v, list)}
                if not data_rows or not periods:
                    return None
                df = pd.DataFrame(data_rows, index=periods).T
                df.columns = pd.to_datetime(df.columns)
                return df

            def build_cashflow_df(raw_data):
                """Build cash flow DataFrame from APIAdapter raw data"""
                cf_data = raw_data.get('cash_flow', {})
                if not cf_data:
                    return None
                periods = cf_data.get('periods', [])
                data_rows = {k: v for k, v in cf_data.items() if k != 'periods' and isinstance(v, list)}
                if not data_rows or not periods:
                    return None
                df = pd.DataFrame(data_rows, index=periods).T
                df.columns = pd.to_datetime(df.columns)
                return df

            financials_df = build_financials_from_api_data(raw_data.get('income_statement', {}))
            balance_sheet_df = build_balance_sheet_df(raw_data)
            cashflow_df = build_cashflow_df(raw_data)

            logger.info(f"[Step6DuPont] Built DataFrames: financials={financials_df is not None}, balance_sheet={balance_sheet_df is not None}, cashflow={cashflow_df is not None}")

            historical_data = historical_data or {
                'financials': financials_df,
                'balance_sheet': balance_sheet_df,
                'cashflow': cashflow_df
            }
            market_data = market_data or mapped_result.get('data', {})
            retrieved_assumptions = retrieved_assumptions or {}

        user_overrides = user_overrides or {}

        # Process DuPont-specific data components
        logger.info(f"Processing DuPont historical financials for {ticker}")
        historical_display = self._process_dupont_historical(historical_data, user_overrides)

        logger.info(f"Processing DuPont market data for {ticker}")
        market_display = self._process_dupont_market_data(market_data, user_overrides)

        # Calculate DuPont intermediate metrics (3-way decomposition)
        logger.info(f"Calculating DuPont intermediate metrics for {ticker}")
        calculated_display = self._calculate_dupont_intermediate_metrics(
            historical_display, market_display
        )

        # Build response object first for scope encapsulation
        response_obj = DuPontDataReviewResponse(
            session_id=f"step6_dupont_{ticker}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            ticker=ticker,
            timestamp=datetime.now(),
            valuation_model="DUPONT",
            historical_financials=historical_display,
            market_data=market_display,
            calculated_metrics=calculated_display,
            missing_data_summary=None,
            manual_overrides_applied=user_overrides,
            data_complete=False,
            message=""
        )

        # Aggregate missing data - pass response_obj to fix scope encapsulation
        missing_summary = self._aggregate_missing_data(response_obj)

        # Attach computed data quality parameters back onto the response instance
        response_obj.missing_data_summary = missing_summary
        response_obj.data_complete = missing_summary.valuation_ready
        response_obj.message = "DuPont data aggregated successfully. Ready for next steps." if missing_summary.valuation_ready else "Missing critical DuPont data. Please retrieve missing inputs."

        # GAP 1 FIX: Store fetched data in session cache for "Fetch Once, Use Many"
        if session_cache is not None:
            from datetime import datetime
            session_cache['international_market_data'] = {
                'timestamp': datetime.now(),
                'historical_data': historical_data,
                'market_data': market_data,
                'retrieved_assumptions': retrieved_assumptions
            }
            logger.info(f"Cached market data for {ticker} in session")

        return response_obj

    def _process_dupont_historical(
        self,
        historical_data: Dict,
        user_overrides: Dict
    ) -> HistoricalFinancialsDisplay:
        """Process DuPont historical financials (ROE decomposition inputs)"""
        financials_df = historical_data.get('financials')
        balance_sheet_df = historical_data.get('balance_sheet')

        data_fields = []
        years = []

        if financials_df is not None and not financials_df.empty:
            years = [str(col.year) if hasattr(col, 'year') else str(col) for col in financials_df.columns[-5:]]

        # DuPont-specific historical fields
        dupont_fields = [
            ("revenue", "Total Revenue", True),
            ("net_income", "Net Income", True),
            ("total_assets", "Total Assets", True),
            ("shareholders_equity", "Shareholders Equity", True),
            ("total_liabilities", "Total Liabilities", False),
            ("retained_earnings", "Retained Earnings", False)
        ]

        for field_name, display_name, is_critical in dupont_fields:
            value = None
            status = DataStatus.MISSING
            source = "yfinance"

            if financials_df is not None or balance_sheet_df is not None:
                value = self._extract_dupont_metric(field_name, financials_df, balance_sheet_df)
                if value is not None:
                    status = DataStatus.RETRIEVED

            if field_name in user_overrides:
                value = user_overrides[field_name]
                status = DataStatus.MANUAL_OVERRIDE

            data_fields.append(DataField(
                field_name=field_name,
                display_name=display_name,
                value=value,
                unit="USD",
                status=status,
                source=source,
                is_critical=is_critical,
                allow_override=True
            ))

        return HistoricalFinancialsDisplay(years=years, data_fields=data_fields)

    def _extract_dupont_metric(
        self,
        field_name: str,
        financials_df: Optional[pd.DataFrame],
        balance_sheet_df: Optional[pd.DataFrame]
    ) -> Optional[float]:
        """Extract specific metric for DuPont analysis"""
        mapping = {
            "revenue": (financials_df, ["Total Revenue", "Revenue"]),
            "net_income": (financials_df, ["Net Income", "Net Income Common Stockholders"]),
            "total_assets": (balance_sheet_df, ["Total Assets", "Assets"]),
            "shareholders_equity": (balance_sheet_df, ["Stockholders Equity", "Total Equity"]),
            "total_liabilities": (balance_sheet_df, ["Total Liabilities", "Liabilities"]),
            "retained_earnings": (balance_sheet_df, ["Retained Earnings"])
        }

        df, keys = mapping.get(field_name, (None, []))
        if df is None or df.empty:
            return None

        latest_col = df.columns[-1]
        for key in keys:
            if key in df.index:
                value = df.loc[key, latest_col]
                if pd.notna(value):
                    return float(value)

        return None

    def _process_dupont_market_data(
        self,
        market_data: Dict,
        user_overrides: Dict
    ) -> MarketDataDisplay:
        """Process DuPont market data"""
        data_fields = []

        market_fields = [
            ("current_stock_price", "Current Stock Price", True, ""),
            ("shares_outstanding", "Shares Outstanding", True, "shares"),
            ("market_cap", "Market Capitalization", True, "USD"),
            ("book_value_per_share", "Book Value Per Share", True, "USD")
        ]

        for field_name, display_name, is_critical, unit in market_fields:
            value = market_data.get(field_name)
            status = DataStatus.RETRIEVED if value is not None else DataStatus.MISSING

            if field_name in user_overrides:
                value = user_overrides[field_name]
                status = DataStatus.MANUAL_OVERRIDE

            data_fields.append(DataField(
                field_name=field_name,
                display_name=display_name,
                value=value,
                unit=unit,
                status=status,
                source="yfinance",
                is_critical=is_critical,
                allow_override=True
            ))

        return MarketDataDisplay(
            current_stock_price=data_fields[0] if data_fields else None,
            shares_outstanding=data_fields[1] if len(data_fields) > 1 else None,
            market_cap=data_fields[2] if len(data_fields) > 2 else None,
            book_value=data_fields[3] if len(data_fields) > 3 else None,
            data_fields=data_fields
        )

    def _calculate_dupont_intermediate_metrics(
        self,
        historical_display: HistoricalFinancialsDisplay,
        market_display: MarketDataDisplay
    ) -> CalculatedMetricsDisplay:
        """Calculate DuPont intermediate metrics (3-way decomposition)"""
        data_fields = []

        # Extract values
        revenue = next((f.value for f in historical_display.data_fields if f.field_name == "revenue"), None)
        net_income = next((f.value for f in historical_display.data_fields if f.field_name == "net_income"), None)
        total_assets = next((f.value for f in historical_display.data_fields if f.field_name == "total_assets"), None)
        shareholders_equity = next((f.value for f in historical_display.data_fields if f.field_name == "shareholders_equity"), None)

        # Calculate 3-way DuPont components
        profit_margin = None
        asset_turnover = None
        equity_multiplier = None
        roe = None

        if revenue and net_income:
            profit_margin = (net_income / revenue) * 100
            data_fields.append(DataField(
                field_name="profit_margin",
                display_name="Net Profit Margin",
                value=profit_margin,
                unit="%",
                status=DataStatus.CALCULATED,
                source="calculated",
                formula="Net Income / Revenue",
                is_critical=True,
                allow_override=False
            ))

        if revenue and total_assets:
            asset_turnover = revenue / total_assets
            data_fields.append(DataField(
                field_name="asset_turnover",
                display_name="Asset Turnover",
                value=asset_turnover,
                unit="x",
                status=DataStatus.CALCULATED,
                source="calculated",
                formula="Revenue / Total Assets",
                is_critical=True,
                allow_override=False
            ))

        if total_assets and shareholders_equity:
            equity_multiplier = total_assets / shareholders_equity
            data_fields.append(DataField(
                field_name="equity_multiplier",
                display_name="Equity Multiplier",
                value=equity_multiplier,
                unit="x",
                status=DataStatus.CALCULATED,
                source="calculated",
                formula="Total Assets / Shareholders Equity",
                is_critical=True,
                allow_override=False
            ))

        if profit_margin and asset_turnover and equity_multiplier:
            roe = profit_margin * asset_turnover * equity_multiplier
            data_fields.append(DataField(
                field_name="roe",
                display_name="Return on Equity (ROE)",
                value=roe,
                unit="%",
                status=DataStatus.CALCULATED,
                source="calculated",
                formula="Profit Margin × Asset Turnover × Equity Multiplier",
                is_critical=True,
                allow_override=False
            ))

        return CalculatedMetricsDisplay(
            profit_margin=data_fields[0] if len(data_fields) > 0 else None,
            asset_turnover=data_fields[1] if len(data_fields) > 1 else None,
            equity_multiplier=data_fields[2] if len(data_fields) > 2 else None,
            roe=data_fields[3] if len(data_fields) > 3 else None,
            data_fields=data_fields
        )

    def _aggregate_missing_data(self, response_obj: 'DuPontDataReviewResponse') -> MissingDataSummary:
        """
        Evaluates field-level status metrics inside the response object to build a
        comprehensive data quality report for frontend validation and rendering.
        """
        critical_missing = []
        optional_missing = []
        retrieved_count = 0
        calculated_count = 0

        # Scan each financial and macro parameter container inside the response object
        for container_name in ["historical_financials", "market_data", "calculated_metrics"]:
            container = getattr(response_obj, container_name, None)
            if container and hasattr(container, 'data_fields'):
                for field in container.data_fields:
                    if field and hasattr(field, "status"):
                        status_str = str(field.status)

                        # Process status and categorize missing data by criticality flags
                        if "MISSING" in status_str:
                            if getattr(field, "is_critical", False):
                                critical_missing.append(getattr(field, "display_name", None) or field.field_name)
                            else:
                                optional_missing.append(getattr(field, "display_name", None) or field.field_name)
                        elif "RETRIEVED" in status_str:
                            retrieved_count += 1
                        elif "CALCULATED" in status_str:
                            calculated_count += 1

        # Calculate metrics matching your application's schema requirements
        total_fields = retrieved_count + calculated_count + len(critical_missing) + len(optional_missing)
        completion_percentage = ((retrieved_count + calculated_count) / total_fields * 100) if total_fields > 0 else 0
        data_quality_score = (retrieved_count * 1.0 + calculated_count * 0.8) / total_fields * 100 if total_fields > 0 else 0

        # Generate warnings to prevent uncommunicative UI drops
        warnings = []
        recommendations = []
        if critical_missing:
            warnings.append(f"Missing {len(critical_missing)} critical financial field assets.")
            recommendations.append("Apply a manual user override configuration or re-verify vendor API connectivity.")

        return MissingDataSummary(
            total_fields=total_fields,
            retrieved_count=retrieved_count,
            calculated_count=calculated_count,
            missing_count=len(critical_missing) + len(optional_missing),
            critical_missing=critical_missing,
            optional_missing=optional_missing,
            completion_percentage=completion_percentage,
            data_quality_score=data_quality_score,
            valuation_ready=len(critical_missing) == 0,
            estimated_count=0,
            manual_override_count=0,
            warnings=warnings,
            recommendations=recommendations
        )


# Singleton instance
dupont_step6_processor = DuPontStep6Processor()