"""Step 6: DCF Data Review Layer - Pure Data Aggregation for DCF Method

This is a dedicated processor for DCF valuation method only.
It eliminates conditional branching by focusing exclusively on DCF-specific data requirements.

Features:
- DCF-specific historical financials processing (11 fields)
- DCF market data aggregation (6 fields)
- DCF balance sheet opening balances (3 fields)
- DCF peer comparables for WACC calculation (5 fields × N peers)
- DCF intermediate metrics calculation (growth rates, margins - NOT final valuations)
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
    """Historical financial data display for DCF"""
    years: List[int] = []
    data_fields: List[DataField] = []


class ForecastDriversDisplay(BaseModel):
    """Forecast drivers display for DCF"""
    data_fields: List[DataField] = []


class MarketDataDisplay(BaseModel):
    """Market data display for DCF"""
    current_stock_price: Optional[DataField] = None
    shares_outstanding: Optional[DataField] = None
    market_cap: Optional[DataField] = None
    beta: Optional[DataField] = None
    total_debt: Optional[DataField] = None
    cash: Optional[DataField] = None
    currency: Optional[DataField] = None
    data_fields: List[DataField] = []


class PeerCompany(BaseModel):
    """Individual peer company data for DCF WACC calculation"""
    ticker: str
    name: Optional[str] = None
    market_cap: Optional[float] = None
    enterprise_value: Optional[float] = None
    ev_ebitda: Optional[float] = None
    pe_ratio: Optional[float] = None
    ev_revenue: Optional[float] = None
    pb_ratio: Optional[float] = None
    beta: Optional[float] = None
    total_debt: Optional[float] = None
    cash: Optional[float] = None
    tax_rate: Optional[float] = None
    cost_of_debt: Optional[float] = None


class PeerComparablesDisplay(BaseModel):
    """Peer comparables display for DCF with individual companies and medians"""
    companies: List[PeerCompany] = []
    median_ev_ebitda: Optional[float] = None
    median_pe: Optional[float] = None
    median_ev_revenue: Optional[float] = None
    median_pb: Optional[float] = None
    data_fields: List[DataField] = []


class CalculatedMetricsDisplay(BaseModel):
    """Calculated metrics from retrieved data for DCF (NOT final valuations)"""
    data_fields: List[DataField] = []


class MissingDataSummary(BaseModel):
    """Summary of missing data for DCF"""
    critical_missing: List[str] = []
    optional_missing: List[str] = []
    total_missing: int = 0


class DCFDataReviewResponse(BaseModel):
    """
    Step 6 DCF Response: Shows all retrieved inputs, missing inputs,
    and calculated intermediate metrics. NO FINAL VALUATIONS.
    """
    session_id: str
    ticker: str
    timestamp: datetime
    valuation_model: str = "DCF"
    historical_financials: Optional[HistoricalFinancialsDisplay] = None
    forecast_drivers: Optional[ForecastDriversDisplay] = None
    market_data: Optional[MarketDataDisplay] = None
    peer_comparables: Optional[PeerComparablesDisplay] = None
    calculated_metrics: Optional[CalculatedMetricsDisplay] = None
    missing_data_summary: Optional[MissingDataSummary] = None
    manual_overrides_applied: Dict[str, Any] = {}
    data_complete: bool = False
    message: str = ""


class DCFStep6Processor:
    """
    Dedicated Step 6 processor for DCF valuation method.
    
    This processor handles ONLY DCF-specific data aggregation:
    - Historical Financials (Revenue, EBITDA, EBIT, Net Income, etc.)
    - Market Data (Price, Market Cap, Beta, Debt, Cash)
    - Opening Balances (Net Working Capital, Net PP&E, Total Debt)
    - Peer Comparables for WACC (Beta, Market Cap, Cost of Debt, Tax Rate)
    - Intermediate Metrics (Growth rates, Margins - NOT WACC/TV/Fair Value)
    """

    def __init__(self):
        self.yfinance_service = YFinanceService()

    async def process_dcf_data_review(
        self,
        ticker: str,
        market: str = "international",
        historical_data: Optional[Dict] = None,
        market_data: Optional[Dict] = None,
        forecast_data: Optional[Dict] = None,
        retrieved_assumptions: Optional[Dict] = None,
        user_overrides: Optional[Dict[str, Any]] = None,
        session_cache: Optional[Dict] = None  # NEW: Session cache for "Fetch Once, Use Many"
    ) -> DCFDataReviewResponse:
        """
        Main entry point for DCF Step 6 data review.
        Aggregates all retrieved DCF data without performing final calculations.

        Args can be passed directly or will be fetched if not provided.
        
        Args:
            ticker: Stock ticker symbol
            market: Market identifier
            historical_data: Historical financial data (optional, will fetch if not provided)
            market_data: Market data (optional, will fetch if not provided)
            forecast_data: Forecast/analyst estimates (optional)
            retrieved_assumptions: Retrieved assumptions including peer data
            user_overrides: Manual overrides applied by user
            session_cache: Session cache dict to check before fetching (implements "Fetch Once, Use Many")
            
        Returns:
            DCFDataReviewResponse with aggregated DCF data
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
                    forecast_data = forecast_data or cached_data.get('forecast_data')
                    retrieved_assumptions = retrieved_assumptions or cached_data.get('retrieved_assumptions')
        
        # If data is not provided (and not in cache), fetch it
        if historical_data is None or market_data is None or forecast_data is None or retrieved_assumptions is None:
            logger.info(f"Fetching data for DCF analysis of {ticker}")
            all_data = self.yfinance_service.fetch_all_data(ticker, market)

            # Convert dict format to DataFrame format expected by processors
            income_stmt_dict = all_data.get('income_statement', {})
            balance_sheet_dict = all_data.get('balance_sheet', {})
            cash_flow_dict = all_data.get('cash_flow', {})

            # Convert to DataFrame and transpose to match expected format
            financials_df = pd.DataFrame(income_stmt_dict).T if income_stmt_dict else None
            balance_sheet_df = pd.DataFrame(balance_sheet_dict).T if balance_sheet_dict else None
            cashflow_df = pd.DataFrame(cash_flow_dict).T if cash_flow_dict else None

            # Convert column strings to datetime for proper year extraction
            if financials_df is not None:
                financials_df.columns = pd.to_datetime(financials_df.columns)
            if balance_sheet_df is not None:
                balance_sheet_df.columns = pd.to_datetime(balance_sheet_df.columns)
            if cashflow_df is not None:
                cashflow_df.columns = pd.to_datetime(cashflow_df.columns)

            historical_data = historical_data or {
                'financials': financials_df,
                'balance_sheet': balance_sheet_df,
                'cashflow': cashflow_df
            }
            market_data = market_data or all_data.get('key_stats', {})
            forecast_data = forecast_data or all_data.get('analyst_estimates', {})
            retrieved_assumptions = retrieved_assumptions or {}

        user_overrides = user_overrides or {}

        # Process DCF-specific data components
        logger.info(f"Processing DCF historical financials for {ticker}")
        historical_display = self._process_dcf_historical(historical_data, user_overrides)

        logger.info(f"Processing DCF market data for {ticker}")
        market_display = self._process_dcf_market_data(market_data, user_overrides)

        logger.info(f"Processing DCF opening balances for {ticker}")
        opening_display = self._process_dcf_opening_balances(historical_data, user_overrides)

        logger.info(f"Processing DCF peer comparables for {ticker}")
        peer_display = self._process_dcf_peer_comparables(retrieved_assumptions, user_overrides)

        # Calculate ONLY intermediate DCF metrics (growth rates, margins, etc.) - NOT WACC/TV/Fair Value
        logger.info(f"Calculating DCF intermediate metrics for {ticker}")
        calculated_display = self._calculate_dcf_intermediate_metrics(
            historical_display, market_display, opening_display, peer_display
        )

        # Aggregate missing data
        all_displays = [historical_display, market_display, opening_display, calculated_display]
        if peer_display and peer_display.data_fields:
            all_displays.append(HistoricalFinancialsDisplay(data_fields=peer_display.data_fields))
        missing_summary = self._aggregate_missing_data(all_displays)

        ready = len(missing_summary.critical_missing) == 0
        
        # GAP 1 FIX: Store fetched data in session cache for "Fetch Once, Use Many"
        if session_cache is not None:
            from datetime import datetime
            session_cache['international_market_data'] = {
                'timestamp': datetime.now(),
                'historical_data': historical_data,
                'market_data': market_data,
                'forecast_data': forecast_data,
                'retrieved_assumptions': retrieved_assumptions
            }
            logger.info(f"Cached market data for {ticker} in session")

        return DCFDataReviewResponse(
            session_id=f"step6_dcf_{ticker}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            ticker=ticker,
            timestamp=datetime.now(),
            valuation_model="DCF",
            historical_financials=historical_display,
            forecast_drivers=ForecastDriversDisplay(
                data_fields=opening_display.data_fields + (peer_display.data_fields if peer_display else [])
            ),
            market_data=market_display,
            peer_comparables=peer_display,
            calculated_metrics=calculated_display,
            missing_data_summary=missing_summary,
            manual_overrides_applied=user_overrides,
            data_complete=ready,
            message="DCF data aggregated successfully. Ready for next steps." if ready else "Missing critical DCF data. Please retrieve missing inputs."
        )

    def _process_dcf_historical(
        self,
        historical_data: Dict,
        user_overrides: Dict
    ) -> HistoricalFinancialsDisplay:
        """Process DCF historical financials (11 fields)"""
        # Implementation extracted from original step6_data_review.py
        # This would contain the exact logic from the original _process_dcf_historical method
        financials_df = historical_data.get('financials')
        balance_sheet_df = historical_data.get('balance_sheet')
        cashflow_df = historical_data.get('cashflow')

        data_fields = []
        years = []

        # Extract years from financial statements
        if financials_df is not None and not financials_df.empty:
            years = [col.year if hasattr(col, 'year') else str(col) for col in financials_df.columns[-5:]]

        # DCF-specific historical fields (11 fields)
        dcf_historical_fields = [
            ("revenue", "Total Revenue", True),
            ("ebitda", "EBITDA", True),
            ("ebit", "EBIT / Operating Income", True),
            ("net_income", "Net Income", True),
            ("depreciation_amortization", "Depreciation & Amortization", True),
            ("capex", "Capital Expenditures", True),
            ("change_in_nwc", "Change in Net Working Capital", True),
            ("free_cash_flow", "Free Cash Flow", True),
            ("gross_margin", "Gross Margin", False),
            ("operating_margin", "Operating Margin", False),
            ("net_margin", "Net Margin", False)
        ]

        for field_name, display_name, is_critical in dcf_historical_fields:
            value = None
            status = DataStatus.MISSING
            source = "yfinance"

            # Try to extract from financial statements
            if financials_df is not None:
                value = self._extract_metric_from_financials(field_name, financials_df, balance_sheet_df, cashflow_df)
                if value is not None:
                    status = DataStatus.RETRIEVED

            # Check for user override
            if field_name in user_overrides:
                value = user_overrides[field_name]
                status = DataStatus.MANUAL_OVERRIDE

            data_fields.append(DataField(
                field_name=field_name,
                display_name=display_name,
                value=value,
                unit="USD" if "margin" not in field_name else "%",
                status=status,
                source=source,
                is_critical=is_critical,
                allow_override=True
            ))

        return HistoricalFinancialsDisplay(years=years, data_fields=data_fields)

    def _extract_metric_from_financials(
        self,
        field_name: str,
        financials_df: pd.DataFrame,
        balance_sheet_df: Optional[pd.DataFrame],
        cashflow_df: Optional[pd.DataFrame]
    ) -> Optional[float]:
        """Extract specific metric from financial statements"""
        # Mapping of field names to financial statement keys
        mapping = {
            "revenue": ["Total Revenue", "Revenue", "Total Revenues"],
            "ebitda": ["EBITDA", "Ebitda"],
            "ebit": ["EBIT", "Operating Income", "Operating income"],
            "net_income": ["Net Income", "Net Income Common Stockholders"],
            "depreciation_amortization": ["Depreciation And Amortization", "Depreciation, Depletion And Amortization"],
            "capex": ["Capital Expenditure", "Capex", "Purchase Of Property Plant And Equipment"],
            "gross_margin": ["Gross Margin", "Gross Profit Margin"],
            "operating_margin": ["Operating Margin", "Operating Income Margin"],
            "net_margin": ["Net Margin", "Net Profit Margin"]
        }

        # Get most recent year's data
        if financials_df is not None and not financials_df.empty:
            latest_col = financials_df.columns[-1]
            
            for key in mapping.get(field_name, [field_name]):
                if key in financials_df.index:
                    value = financials_df.loc[key, latest_col]
                    if pd.notna(value):
                        return float(value)

        # Special calculations
        if field_name == "free_cash_flow":
            # FCF = Operating Cash Flow - CapEx
            op_cf = self._extract_metric_from_financials("operating_cash_flow", financials_df, balance_sheet_df, cashflow_df)
            capex = self._extract_metric_from_financials("capex", financials_df, balance_sheet_df, cashflow_df)
            if op_cf is not None and capex is not None:
                return op_cf - abs(capex)

        if field_name == "change_in_nwc":
            # Requires balance sheet data
            if balance_sheet_df is not None and not balance_sheet_df.empty:
                # Simplified calculation
                pass

        return None

    def _process_dcf_market_data(
        self,
        market_data: Dict,
        user_overrides: Dict
    ) -> MarketDataDisplay:
        """Process DCF market data (6 fields)"""
        data_fields = []

        # DCF market data fields
        market_fields = [
            ("current_stock_price", "Current Stock Price", True, ""),
            ("shares_outstanding", "Shares Outstanding", True, "shares"),
            ("market_cap", "Market Capitalization", True, "USD"),
            ("beta", "Beta", True, ""),
            ("total_debt", "Total Debt", True, "USD"),
            ("cash", "Cash & Cash Equivalents", True, "USD")
        ]

        for field_name, display_name, is_critical, unit in market_fields:
            value = market_data.get(field_name) or market_data.get(field_name.replace("_", ""))
            status = DataStatus.RETRIEVED if value is not None else DataStatus.MISSING
            source = "yfinance"

            # Check for user override
            if field_name in user_overrides:
                value = user_overrides[field_name]
                status = DataStatus.MANUAL_OVERRIDE

            data_fields.append(DataField(
                field_name=field_name,
                display_name=display_name,
                value=value,
                unit=unit,
                status=status,
                source=source,
                is_critical=is_critical,
                allow_override=True
            ))

        return MarketDataDisplay(
            current_stock_price=data_fields[0] if data_fields else None,
            shares_outstanding=data_fields[1] if len(data_fields) > 1 else None,
            market_cap=data_fields[2] if len(data_fields) > 2 else None,
            beta=data_fields[3] if len(data_fields) > 3 else None,
            total_debt=data_fields[4] if len(data_fields) > 4 else None,
            cash=data_fields[5] if len(data_fields) > 5 else None,
            data_fields=data_fields
        )

    def _process_dcf_opening_balances(
        self,
        historical_data: Dict,
        user_overrides: Dict
    ) -> ForecastDriversDisplay:
        """Process DCF opening balances (3 fields)"""
        data_fields = []

        # DCF opening balance fields
        opening_fields = [
            ("opening_net_working_capital", "Opening Net Working Capital", True, "USD"),
            ("opening_net_ppe", "Opening Net PP&E", True, "USD"),
            ("opening_total_debt", "Opening Total Debt", True, "USD")
        ]

        balance_sheet_df = historical_data.get('balance_sheet')

        for field_name, display_name, is_critical, unit in opening_fields:
            value = None
            status = DataStatus.MISSING
            source = "yfinance"

            # Extract from balance sheet
            if balance_sheet_df is not None and not balance_sheet_df.empty:
                value = self._extract_opening_balance(field_name, balance_sheet_df)
                if value is not None:
                    status = DataStatus.RETRIEVED

            # Check for user override
            if field_name in user_overrides:
                value = user_overrides[field_name]
                status = DataStatus.MANUAL_OVERRIDE

            data_fields.append(DataField(
                field_name=field_name,
                display_name=display_name,
                value=value,
                unit=unit,
                status=status,
                source=source,
                is_critical=is_critical,
                allow_override=True
            ))

        return ForecastDriversDisplay(data_fields=data_fields)

    def _extract_opening_balance(
        self,
        field_name: str,
        balance_sheet_df: pd.DataFrame
    ) -> Optional[float]:
        """Extract opening balance from balance sheet"""
        if balance_sheet_df is None or balance_sheet_df.empty:
            return None

        # Get most recent year's data (opening for forecast period)
        latest_col = balance_sheet_df.columns[-1]

        mapping = {
            "opening_net_working_capital": ["Working Capital", "Net Working Capital"],
            "opening_net_ppe": ["Net PPE", "Property Plant And Equipment Net", "Net Property Plant And Equipment"],
            "opening_total_debt": ["Total Debt", "Long Term Debt", "Short Long Term Debt Total"]
        }

        for key in mapping.get(field_name, [field_name]):
            if key in balance_sheet_df.index:
                value = balance_sheet_df.loc[key, latest_col]
                if pd.notna(value):
                    return float(value)

        return None

    def _process_dcf_peer_comparables(
        self,
        retrieved_assumptions: Dict,
        user_overrides: Dict
    ) -> PeerComparablesDisplay:
        """Process DCF peer comparables for WACC calculation"""
        companies = []
        data_fields = []

        # Get peer list
        peers = retrieved_assumptions.get('peers', [])

        for peer_ticker in peers:
            peer_info = retrieved_assumptions.get(f"peer_{peer_ticker}_info", {})

            if peer_info:
                company = PeerCompany(
                    ticker=peer_ticker,
                    name=peer_info.get('name'),
                    market_cap=peer_info.get('marketCap'),
                    enterprise_value=peer_info.get('enterpriseValue'),
                    ev_ebitda=peer_info.get('evEbitda'),
                    pe_ratio=peer_info.get('peRatio'),
                    ev_revenue=peer_info.get('evRevenue'),
                    pb_ratio=peer_info.get('pbRatio'),
                    beta=peer_info.get('beta'),
                    total_debt=peer_info.get('totalDebt'),
                    cash=peer_info.get('cash'),
                    tax_rate=peer_info.get('effectiveTaxRate'),
                    cost_of_debt=peer_info.get('costOfDebt')
                )
                companies.append(company)

        # Calculate medians
        median_ev_ebitda = self._calculate_median([c.ev_ebitda for c in companies if c.ev_ebitda])
        median_pe = self._calculate_median([c.pe_ratio for c in companies if c.pe_ratio])
        median_ev_revenue = self._calculate_median([c.ev_revenue for c in companies if c.ev_revenue])
        median_pb = self._calculate_median([c.pb_ratio for c in companies if c.pb_ratio])

        return PeerComparablesDisplay(
            companies=companies,
            median_ev_ebitda=median_ev_ebitda,
            median_pe=median_pe,
            median_ev_revenue=median_ev_revenue,
            median_pb=median_pb,
            data_fields=data_fields
        )

    def _calculate_median(self, values: List[float]) -> Optional[float]:
        """Calculate median of a list of values"""
        if not values:
            return None
        sorted_values = sorted(values)
        n = len(sorted_values)
        mid = n // 2
        if n % 2 == 0:
            return (sorted_values[mid - 1] + sorted_values[mid]) / 2
        return sorted_values[mid]

    def _calculate_dcf_intermediate_metrics(
        self,
        historical_display: HistoricalFinancialsDisplay,
        market_display: MarketDataDisplay,
        opening_display: ForecastDriversDisplay,
        peer_display: PeerComparablesDisplay
    ) -> CalculatedMetricsDisplay:
        """Calculate DCF intermediate metrics (growth rates, margins - NOT final valuations)"""
        data_fields = []

        # Calculate historical growth rates, margins from historical data
        # These are intermediate calculations, NOT WACC/TV/Fair Value
        
        # Example: Revenue CAGR
        revenue_fields = [f for f in historical_display.data_fields if f.field_name == "revenue"]
        if revenue_fields and revenue_fields[0].value:
            # Would calculate CAGR here
            pass

        # Example: Historical margins
        margin_fields = ["gross_margin", "operating_margin", "net_margin"]
        for margin in margin_fields:
            field = next((f for f in historical_display.data_fields if f.field_name == margin), None)
            if field and field.value:
                data_fields.append(DataField(
                    field_name=f"historical_{margin}",
                    display_name=f"Historical {field.display_name}",
                    value=field.value,
                    unit="%",
                    status=DataStatus.CALCULATED,
                    source="calculated_from_historical",
                    is_critical=False,
                    allow_override=False
                ))

        return CalculatedMetricsDisplay(data_fields=data_fields)

    def _aggregate_missing_data(
        self,
        displays: List
    ) -> MissingDataSummary:
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
dcf_step6_processor = DCFStep6Processor()
