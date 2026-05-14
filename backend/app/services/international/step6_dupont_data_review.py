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
from pydantic import BaseModel
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
    """Summary of missing data for DuPont"""
    critical_missing: List[str] = []
    optional_missing: List[str] = []
    total_missing: int = 0


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
        
        # If data is not provided (and not in cache), fetch it
        if historical_data is None or market_data is None:
            logger.info(f"Fetching data for DuPont analysis of {ticker}")
            all_data = self.yfinance_service.fetch_all_data(ticker, market)

            income_stmt_dict = all_data.get('income_statement', {})
            balance_sheet_dict = all_data.get('balance_sheet', {})

            # FIX: Properly construct DataFrames using 'periods' as index, then transpose
            # This prevents the "1970" year issue caused by converting integer column indices to datetime
            def build_financials_df(data_dict):
                """Build DataFrame from yfinance dict format with periods as columns"""
                if not data_dict:
                    return None
                periods = data_dict.get('periods', [])
                data_rows = {k: v for k, v in data_dict.items() if k != 'periods' and isinstance(v, list)}
                if not data_rows or not periods:
                    return None
                df = pd.DataFrame(data_rows, index=periods).T
                df.columns = pd.to_datetime(df.columns)
                return df
            
            financials_df = build_financials_df(income_stmt_dict)
            balance_sheet_df = build_financials_df(balance_sheet_dict)

            historical_data = historical_data or {
                'financials': financials_df,
                'balance_sheet': balance_sheet_df
            }
            market_data = market_data or all_data.get('key_stats', {})
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

        # Aggregate missing data
        all_displays = [historical_display, market_display]
        if calculated_display.data_fields:
            all_displays.append(HistoricalFinancialsDisplay(data_fields=calculated_display.data_fields))
        missing_summary = self._aggregate_missing_data(all_displays)

        ready = len(missing_summary.critical_missing) == 0
        
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

        return DuPontDataReviewResponse(
            session_id=f"step6_dupont_{ticker}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            ticker=ticker,
            timestamp=datetime.now(),
            valuation_model="DUPONT",
            historical_financials=historical_display,
            market_data=market_display,
            calculated_metrics=calculated_display,
            missing_data_summary=missing_summary,
            manual_overrides_applied=user_overrides,
            data_complete=ready,
            message="DuPont data aggregated successfully. Ready for next steps." if ready else "Missing critical DuPont data. Please retrieve missing inputs."
        )

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

    def _aggregate_missing_data(self, displays: List) -> MissingDataSummary:
        """Aggregate missing data from all displays"""
        critical_missing = []
        optional_missing = []

        for display in displays:
            if hasattr(display, 'data_fields'):
                for field in display.data_fields:
                    if field.status == DataStatus.MISSING:
                        if field.is_critical:
                            critical_missing.append(field.display_name or field.field_name)
                        else:
                            optional_missing.append(field.display_name or field.field_name)

        return MissingDataSummary(
            critical_missing=critical_missing,
            optional_missing=optional_missing,
            total_missing=len(critical_missing) + len(optional_missing)
        )


# Singleton instance
dupont_step6_processor = DuPontStep6Processor()
