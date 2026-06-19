"""Step 6: Comps Data Review Layer - Pure Data Aggregation for Trading Comps Method

This is a dedicated processor for Trading Comps valuation method only.
It eliminates conditional branching by focusing exclusively on Comps-specific data requirements.
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
    RETRIEVED = "RETRIEVED"
    CALCULATED = "CALCULATED"
    MISSING = "MISSING"
    MANUAL_OVERRIDE = "MANUAL_OVERRIDE"


class DataField(BaseModel):
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
    years: List[str] = []  # Changed from List[int] to List[str] to match UnifiedStep6Response.periods_covered
    data_fields: List[DataField] = []


class MarketDataDisplay(BaseModel):
    current_stock_price: Optional[DataField] = None
    shares_outstanding: Optional[DataField] = None
    market_cap: Optional[DataField] = None
    enterprise_value: Optional[DataField] = None
    data_fields: List[DataField] = []


class PeerCompany(BaseModel):
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
    companies: List[PeerCompany] = []
    median_ev_ebitda: Optional[float] = None
    median_pe: Optional[float] = None
    median_ev_revenue: Optional[float] = None
    median_pb: Optional[float] = None
    data_fields: List[DataField] = []


class CalculatedMetricsDisplay(BaseModel):
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


class CompsDataReviewResponse(BaseModel):
    session_id: str
    ticker: str
    timestamp: datetime
    valuation_model: str = "COMPS"
    historical_financials: Optional[HistoricalFinancialsDisplay] = None
    market_data: Optional[MarketDataDisplay] = None
    peer_comparables: Optional[PeerComparablesDisplay] = None
    calculated_metrics: Optional[CalculatedMetricsDisplay] = None
    missing_data_summary: Optional[MissingDataSummary] = None
    manual_overrides_applied: Dict[str, Any] = {}
    data_complete: bool = False
    message: str = ""


class CompsStep6Processor:
    def __init__(self):
        self.yfinance_service = YFinanceService()

    async def process_comps_data_review(
        self,
        ticker: str,
        market: str = "international",
        historical_data: Optional[Dict] = None,
        market_data: Optional[Dict] = None,
        retrieved_assumptions: Optional[Dict] = None,
        user_overrides: Optional[Dict[str, Any]] = None,
        session_cache: Optional[Dict] = None  # NEW: Session cache for "Fetch Once, Use Many"
    ) -> CompsDataReviewResponse:
        """
        Main entry point for Comps Step 6 data review.
        Aggregates all retrieved Comps data without performing final calculations.

        Args:
            ticker: Stock ticker symbol
            market: Market identifier
            historical_data: Historical financial data (optional, will fetch if not provided)
            market_data: Market data (optional, will fetch if not provided)
            retrieved_assumptions: Retrieved assumptions including peer data
            user_overrides: Manual overrides applied by user
            session_cache: Session cache dict to check before fetching (implements "Fetch Once, Use Many")

        Returns:
            CompsDataReviewResponse with aggregated Comps data
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
        if historical_data is None or market_data is None or retrieved_assumptions is None:
            logger.info(f"Fetching data for Comps analysis of {ticker}")
            from ..api_adapter import APIAdapter
            adapter = APIAdapter(market="international", enable_alphavantage=True)  # Target company: AV as gap-filler

            required_metrics = ["revenue", "net_income", "ebitda", "total_assets", "shareholders_equity",
                               "current_stock_price", "shares_outstanding", "market_cap", "enterprise_value",
                               "total_debt", "cash_and_equivalents", "tax_rate"]
            raw_result = adapter.fetch_raw_data(ticker, required_metrics)
            mapped_result = adapter.map_and_normalize(raw_result, ticker)

            # --- Build multi-year DataFrames from YFinanceService output ---
            multi_year = mapped_result.get("raw_data", {}).get("_multi_year", {})
            yfs_income = multi_year.get("income_statement", {})
            yfs_bs = multi_year.get("balance_sheet", {})
            yfs_cf = multi_year.get("cash_flow", {})

            COMPS_INCOME = {
                "revenue": "total_revenue", "net_income": "net_income",
                "ebitda": "ebitda", "operating_income": "ebit",
            }
            COMPS_BS = {
                "total_assets": "total_assets", "shareholders_equity": "total_equity",
                "total_debt": "total_debt", "cash_and_equivalents": "cash_and_equivalents",
                "shares_outstanding": "shares_outstanding",
            }

            def build_multiyear_df(yfs_section, field_map):
                if not yfs_section or not isinstance(yfs_section, dict):
                    return None
                periods = yfs_section.get("periods", [])
                if not periods:
                    return None
                sorted_periods = sorted(periods, reverse=True)[:4]
                metrics_data = {}
                for metric_id, yfs_key in field_map.items():
                    values = yfs_section.get(yfs_key)
                    if isinstance(values, list) and values:
                        padded = values[:len(sorted_periods)]
                        while len(padded) < len(sorted_periods):
                            padded.append(None)
                        if any(v is not None for v in padded):
                            metrics_data[metric_id] = padded
                if metrics_data:
                    return pd.DataFrame.from_dict(metrics_data, orient='index', columns=sorted_periods)
                return None

            financials_df = build_multiyear_df(yfs_income, COMPS_INCOME)
            balance_sheet_df = build_multiyear_df(yfs_bs, COMPS_BS)
            cashflow_df = build_multiyear_df(yfs_cf, {"operating_cash_flow": "operating_cash_flow", "capex": "capital_expenditure", "free_cash_flow": "free_cash_flow"})

            logger.info(f"[Step6Comps] Built DataFrames: financials={financials_df is not None}, balance_sheet={balance_sheet_df is not None}, cashflow={cashflow_df is not None}")

            historical_data = historical_data or {
                'financials': financials_df,
                'balance_sheet': balance_sheet_df,
                'cashflow': cashflow_df
            }
            market_data = market_data or mapped_result.get('data', {})
            retrieved_assumptions = retrieved_assumptions or {}

        user_overrides = user_overrides or {}
        historical_display = self._process_comps_historical(historical_data, user_overrides)
        market_display = self._process_comps_market_data(market_data, user_overrides)
        peer_display = self._process_comps_peer_comparables(retrieved_assumptions, user_overrides)
        calculated_display = self._calculate_comps_intermediate_metrics(historical_display, market_display, peer_display)

        # Build response object first for scope encapsulation
        response_obj = CompsDataReviewResponse(
            session_id=f"step6_comps_{ticker}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            ticker=ticker,
            timestamp=datetime.now(),
            valuation_model="COMPS",
            historical_financials=historical_display,
            market_data=market_display,
            peer_comparables=peer_display,
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
        response_obj.message = "Comps data aggregated successfully." if missing_summary.valuation_ready else "Missing critical Comps data."

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

    def _process_comps_historical(self, historical_data: Dict, user_overrides: Dict) -> HistoricalFinancialsDisplay:
        """Process Trading Comps historical financials (5-year data for multiples calculation)"""
        financials_df = historical_data.get('financials')
        balance_sheet_df = historical_data.get('balance_sheet')
        cashflow_df = historical_data.get('cashflow')

        data_fields = []
        years = []

        # Extract years from financial statements
        # NOTE: yfinance columns are newest-first, so [:4] gets the 4 most recent
        if financials_df is not None and not financials_df.empty:
            years = [str(col.year) if hasattr(col, 'year') else str(col) for col in financials_df.columns[:4]]

        # Trading Comps-specific historical fields (critical for multiple calculations)
        comps_historical_fields = [
            ("revenue", "Total Revenue", True),
            ("ebitda", "EBITDA", True),
            ("ebit", "EBIT / Operating Income", True),
            ("net_income", "Net Income", True),
            ("gross_profit", "Gross Profit", False),
            ("operating_income", "Operating Income", False),
            ("total_assets", "Total Assets", False),
            ("total_equity", "Shareholders' Equity", False),
            ("shares_outstanding", "Shares Outstanding", False)
        ]

        for field_name, display_name, is_critical in comps_historical_fields:
            value = None
            status = DataStatus.MISSING
            source = "yfinance"

            # Try to extract from financial statements
            if financials_df is not None or balance_sheet_df is not None:
                value = self._extract_comps_metric_from_financials(
                    field_name, financials_df, balance_sheet_df, cashflow_df
                )
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
                unit="USD" if "margin" not in field_name and "ratio" not in field_name else "%",
                status=status,
                source=source,
                is_critical=is_critical,
                allow_override=True
            ))

        return HistoricalFinancialsDisplay(years=years, data_fields=data_fields)

    def _extract_comps_metric_from_financials(
        self,
        field_name: str,
        financials_df: Optional[pd.DataFrame],
        balance_sheet_df: Optional[pd.DataFrame],
        cashflow_df: Optional[pd.DataFrame]
    ) -> Optional[List[float]]:
        """Extract specific metric from financial statements for Comps (returns list of values for multiple years)"""
        mapping = {
            "revenue": ["revenue", "Total Revenue", "Revenue", "Total Revenues"],
            "ebitda": ["ebitda", "EBITDA", "Ebitda"],
            "ebit": ["operating_income", "EBIT", "Operating Income", "Operating income"],
            "net_income": ["net_income", "Net Income", "Net Income Common Stockholders"],
            "gross_profit": ["gross_profit", "Gross Profit", "Gross Profits"],
            "operating_income": ["operating_income", "Operating Income", "Operating income", "EBIT"],
            "total_assets": ["total_assets", "Total Assets", "Assets"],
            "total_equity": ["shareholders_equity", "total_equity", "Stockholders Equity", "Shareholders Equity", "Total Equity"],
            "shares_outstanding": ["shares_outstanding", "Shares Outstanding", "Diluted Shares Outstanding"]
        }

        values = []
        df_to_use = balance_sheet_df if field_name in ["total_assets", "total_equity"] else financials_df

        if df_to_use is not None and not df_to_use.empty:
            for col in df_to_use.columns[:4]:  # 4 most recent years (newest-first order)
                found = False
                for key in mapping.get(field_name, [field_name]):
                    if key in df_to_use.index:
                        value = df_to_use.loc[key, col]
                        if pd.notna(value):
                            values.append(float(value))
                            found = True
                            break
                if not found:
                    values.append(None)

        return values if values else None

    def _process_comps_market_data(self, market_data: Dict, user_overrides: Dict) -> MarketDataDisplay:
        """Process Trading Comps market data (current market metrics for multiples)"""
        data_fields = []

        # Trading Comps-specific market data fields
        comps_market_fields = [
            ("current_stock_price", "Current Stock Price", True, "USD"),
            ("shares_outstanding", "Shares Outstanding", True, "shares"),
            ("market_cap", "Market Capitalization", True, "USD"),
            ("enterprise_value", "Enterprise Value", True, "USD"),
            ("total_debt", "Total Debt", False, "USD"),
            ("cash_and_equivalents", "Cash & Equivalents", False, "USD"),
            ("book_value", "Book Value of Equity", False, "USD"),
            ("dividend_yield", "Dividend Yield", False, "%")
        ]

        for field_name, display_name, is_critical, unit in comps_market_fields:
            value = market_data.get(field_name) or market_data.get(field_name.replace('_', ' ').title())
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

        # Set individual fields for easier access
        current_price_field = next((f for f in data_fields if f.field_name == "current_stock_price"), None)
        shares_field = next((f for f in data_fields if f.field_name == "shares_outstanding"), None)
        market_cap_field = next((f for f in data_fields if f.field_name == "market_cap"), None)
        ev_field = next((f for f in data_fields if f.field_name == "enterprise_value"), None)

        return MarketDataDisplay(
            current_stock_price=current_price_field,
            shares_outstanding=shares_field,
            market_cap=market_cap_field,
            enterprise_value=ev_field,
            data_fields=data_fields
        )

    def _process_comps_peer_comparables(self, retrieved_assumptions: Dict, user_overrides: Dict) -> PeerComparablesDisplay:
        """Process Trading Comps peer comparables - fetch actual data for each peer company"""
        peers = retrieved_assumptions.get('peers', [])
        companies = []

        if not peers:
            logger.warning("No peer companies provided for Comps analysis")
            return PeerComparablesDisplay(companies=companies)

        # Fetch data for each peer company
        for peer_ticker in peers:
            try:
                logger.info(f"Fetching data for peer company: {peer_ticker}")

                # Use get_ticker_info which provides direct access to valuation multiples
                peer_info = self.yfinance_service.get_ticker_info(peer_ticker)

                if not peer_info:
                    logger.warning(f"No info available for peer {peer_ticker}")
                    companies.append(PeerCompany(
                        ticker=peer_ticker,
                        name="Data unavailable"
                    ))
                    continue

                # Extract valuation multiples directly from yfinance info
                # These are more reliable than calculating from financials
                trailing_pe = peer_info.get('trailingPE')
                forward_pe = peer_info.get('forwardPE')
                ev_to_ebitda = peer_info.get('enterpriseToEbitda')
                ev_to_revenue = peer_info.get('enterpriseToRevenue')
                price_to_book = peer_info.get('priceToBook')

                # Get market data
                market_cap = peer_info.get('marketCap')
                enterprise_value = peer_info.get('enterpriseValue')

                # Use direct multiples from yfinance as primary source
                # Fallback to calculation only if direct values not available
                pe_ratio = trailing_pe  # Use trailing PE as primary
                ev_ebitda = ev_to_ebitda
                ev_revenue = ev_to_revenue
                pb_ratio = price_to_book

                # If direct multiples not available, try to calculate from financials
                if pe_ratio is None and market_cap:
                    # Try to calculate P/E from net income
                    peer_financials = self.yfinance_service.get_financial_statements(peer_ticker)
                    if peer_financials and peer_financials.get('income_stmt') is not None:
                        income_stmt = peer_financials['income_stmt']
                        if not income_stmt.empty:
                            latest_col = income_stmt.columns[0]
                            net_income = income_stmt.loc['Net Income', latest_col] if 'Net Income' in income_stmt.index else None
                            if net_income and net_income != 0:
                                pe_ratio = market_cap / abs(net_income)

                if ev_ebitda is None and enterprise_value:
                    # Try to calculate EV/EBITDA from EBITDA
                    peer_financials = self.yfinance_service.get_financial_statements(peer_ticker)
                    if peer_financials and peer_financials.get('income_stmt') is not None:
                        income_stmt = peer_financials['income_stmt']
                        if not income_stmt.empty:
                            latest_col = income_stmt.columns[0]
                            ebitda = income_stmt.loc['EBITDA', latest_col] if 'EBITDA' in income_stmt.index else None
                            if ebitda and ebitda != 0:
                                ev_ebitda = enterprise_value / abs(ebitda)

                if ev_revenue is None and enterprise_value:
                    # Try to calculate EV/Revenue from revenue
                    peer_financials = self.yfinance_service.get_financial_statements(peer_ticker)
                    if peer_financials and peer_financials.get('income_stmt') is not None:
                        income_stmt = peer_financials['income_stmt']
                        if not income_stmt.empty:
                            latest_col = income_stmt.columns[0]
                            revenue = income_stmt.loc['Total Revenue', latest_col] if 'Total Revenue' in income_stmt.index else None
                            if revenue and revenue != 0:
                                ev_revenue = enterprise_value / abs(revenue)

                if pb_ratio is None and market_cap:
                    # Try to calculate P/B from book value
                    peer_financials = self.yfinance_service.get_financial_statements(peer_ticker)
                    if peer_financials and peer_financials.get('balance_sheet') is not None:
                        balance_sheet = peer_financials['balance_sheet']
                        if not balance_sheet.empty:
                            latest_col = balance_sheet.columns[0]
                            book_value = balance_sheet.loc['Stockholders Equity', latest_col] if 'Stockholders Equity' in balance_sheet.index else None
                            if book_value is None:
                                book_value = balance_sheet.loc['Total Equity Gross Minority Interest', latest_col] if 'Total Equity Gross Minority Interest' in balance_sheet.index else None
                            if book_value and book_value != 0:
                                pb_ratio = market_cap / abs(book_value)

                companies.append(PeerCompany(
                    ticker=peer_ticker,
                    name=peer_info.get('longName', peer_ticker),
                    market_cap=market_cap,
                    enterprise_value=enterprise_value,
                    ev_ebitda=ev_ebitda,
                    pe_ratio=pe_ratio,
                    ev_revenue=ev_revenue,
                    pb_ratio=pb_ratio,
                ))

            except Exception as e:
                logger.error(f"Error fetching data for peer {peer_ticker}: {str(e)}")
                # Add placeholder with error
                companies.append(PeerCompany(
                    ticker=peer_ticker,
                    name="Data unavailable"
                ))

        # Calculate median/mean multiples from peer data
        median_ev_ebitda = self._calculate_median([c.ev_ebitda for c in companies if c.ev_ebitda])
        median_pe = self._calculate_median([c.pe_ratio for c in companies if c.pe_ratio])
        median_ev_revenue = self._calculate_median([c.ev_revenue for c in companies if c.ev_revenue])
        median_pb = self._calculate_median([c.pb_ratio for c in companies if c.pb_ratio])

        # Create data fields for peer statistics
        peer_data_fields = []
        if median_ev_ebitda:
            peer_data_fields.append(DataField(
                field_name="median_ev_ebitda",
                display_name="Median EV/EBITDA",
                value=median_ev_ebitda,
                unit="x",
                status=DataStatus.CALCULATED,
                formula="Median of peer EV/EBITDA multiples",
                is_critical=True
            ))
        if median_pe:
            peer_data_fields.append(DataField(
                field_name="median_pe",
                display_name="Median P/E Ratio",
                value=median_pe,
                unit="x",
                status=DataStatus.CALCULATED,
                formula="Median of peer P/E ratios",
                is_critical=True
            ))
        if median_ev_revenue:
            peer_data_fields.append(DataField(
                field_name="median_ev_revenue",
                display_name="Median EV/Revenue",
                value=median_ev_revenue,
                unit="x",
                status=DataStatus.CALCULATED,
                formula="Median of peer EV/Revenue multiples",
                is_critical=False
            ))
        if median_pb:
            peer_data_fields.append(DataField(
                field_name="median_pb",
                display_name="Median P/B Ratio",
                value=median_pb,
                unit="x",
                status=DataStatus.CALCULATED,
                formula="Median of peer P/B ratios",
                is_critical=False
            ))

        return PeerComparablesDisplay(
            companies=companies,
            median_ev_ebitda=median_ev_ebitda,
            median_pe=median_pe,
            median_ev_revenue=median_ev_revenue,
            median_pb=median_pb,
            data_fields=peer_data_fields
        )

    def _calculate_comps_intermediate_metrics(
        self,
        historical_display: HistoricalFinancialsDisplay,
        market_display: MarketDataDisplay,
        peer_display: PeerComparablesDisplay
    ) -> CalculatedMetricsDisplay:
        """Calculate intermediate Trading Comps metrics from retrieved data"""
        data_fields = []

        # Get target company's latest financials
        latest_revenue = None
        latest_ebitda = None
        latest_net_income = None
        latest_book_value = None

        if historical_display and historical_display.data_fields:
            for field in historical_display.data_fields:
                if field.field_name == "revenue" and field.value:
                    # Get latest year value (last in list)
                    if isinstance(field.value, list):
                        latest_revenue = field.value[-1] if field.value else None
                    else:
                        latest_revenue = field.value
                elif field.field_name == "ebitda" and field.value:
                    if isinstance(field.value, list):
                        latest_ebitda = field.value[-1] if field.value else None
                    else:
                        latest_ebitda = field.value
                elif field.field_name == "net_income" and field.value:
                    if isinstance(field.value, list):
                        latest_net_income = field.value[-1] if field.value else None
                    else:
                        latest_net_income = field.value

        # Get target company's market data
        market_cap = None
        enterprise_value = None
        if market_display:
            if market_display.market_cap and market_display.market_cap.value:
                market_cap = market_display.market_cap.value
            if market_display.enterprise_value and market_display.enterprise_value.value:
                enterprise_value = market_display.enterprise_value.value

        # Calculate target company's implied multiples
        if latest_ebitda and enterprise_value:
            target_ev_ebitda = enterprise_value / latest_ebitda if latest_ebitda != 0 else None
            if target_ev_ebitda:
                data_fields.append(DataField(
                    field_name="target_ev_ebitda",
                    display_name="Target EV/EBITDA",
                    value=target_ev_ebitda,
                    unit="x",
                    status=DataStatus.CALCULATED,
                    formula="Enterprise Value / Latest EBITDA",
                    is_critical=False,
                    allow_override=False
                ))

        if latest_net_income and market_cap:
            target_pe = market_cap / latest_net_income if latest_net_income != 0 else None
            if target_pe:
                data_fields.append(DataField(
                    field_name="target_pe",
                    display_name="Target P/E Ratio",
                    value=target_pe,
                    unit="x",
                    status=DataStatus.CALCULATED,
                    formula="Market Cap / Latest Net Income",
                    is_critical=False,
                    allow_override=False
                ))

        if latest_revenue and enterprise_value:
            target_ev_revenue = enterprise_value / latest_revenue if latest_revenue != 0 else None
            if target_ev_revenue:
                data_fields.append(DataField(
                    field_name="target_ev_revenue",
                    display_name="Target EV/Revenue",
                    value=target_ev_revenue,
                    unit="x",
                    status=DataStatus.CALCULATED,
                    formula="Enterprise Value / Latest Revenue",
                    is_critical=False,
                    allow_override=False
                ))

        # Calculate premium/discount to peer median
        if peer_display:
            if target_ev_ebitda and peer_display.median_ev_ebitda:
                premium_discount_ebitda = ((target_ev_ebitda - peer_display.median_ev_ebitda) / peer_display.median_ev_ebitda) * 100
                data_fields.append(DataField(
                    field_name="premium_discount_ebitda",
                    display_name="Premium/(Discount) to Peer Median EV/EBITDA",
                    value=premium_discount_ebitda,
                    unit="%",
                    status=DataStatus.CALCULATED,
                    formula="((Target EV/EBITDA - Peer Median) / Peer Median) × 100",
                    is_critical=False,
                    allow_override=False
                ))

            if target_pe and peer_display.median_pe:
                premium_discount_pe = ((target_pe - peer_display.median_pe) / peer_display.median_pe) * 100
                data_fields.append(DataField(
                    field_name="premium_discount_pe",
                    display_name="Premium/(Discount) to Peer Median P/E",
                    value=premium_discount_pe,
                    unit="%",
                    status=DataStatus.CALCULATED,
                    formula="((Target P/E - Peer Median) / Peer Median) × 100",
                    is_critical=False,
                    allow_override=False
                ))

        # Calculate historical growth rates for context
        if historical_display and historical_display.data_fields:
            revenue_field = next((f for f in historical_display.data_fields if f.field_name == "revenue"), None)
            if revenue_field and isinstance(revenue_field.value, list) and len(revenue_field.value) >= 2:
                revenues = revenue_field.value
                if revenues[-1] and revenues[-2] and revenues[-2] != 0:
                    revenue_growth = ((revenues[-1] - revenues[-2]) / revenues[-2]) * 100
                    data_fields.append(DataField(
                        field_name="revenue_growth_yoy",
                        display_name="Revenue Growth (YoY)",
                        value=revenue_growth,
                        unit="%",
                        status=DataStatus.CALCULATED,
                        formula="((Latest Revenue - Prior Year Revenue) / Prior Year Revenue) × 100",
                        is_critical=False,
                        allow_override=False
                    ))

            ebitda_field = next((f for f in historical_display.data_fields if f.field_name == "ebitda"), None)
            if ebitda_field and isinstance(ebitda_field.value, list) and len(ebitda_field.value) >= 2:
                ebitdas = ebitda_field.value
                if ebitdas[-1] and ebitdas[-2] and ebitdas[-2] != 0:
                    ebitda_growth = ((ebitdas[-1] - ebitdas[-2]) / ebitdas[-2]) * 100
                    data_fields.append(DataField(
                        field_name="ebitda_growth_yoy",
                        display_name="EBITDA Growth (YoY)",
                        value=ebitda_growth,
                        unit="%",
                        status=DataStatus.CALCULATED,
                        formula="((Latest EBITDA - Prior Year EBITDA) / Prior Year EBITDA) × 100",
                        is_critical=False,
                        allow_override=False
                    ))

        return CalculatedMetricsDisplay(data_fields=data_fields)

    def _calculate_median(self, values: List[float]) -> Optional[float]:
        """Calculate median of a list of values"""
        if not values:
            return None
        sorted_values = sorted(values)
        n = len(sorted_values)
        if n % 2 == 0:
            return (sorted_values[n//2 - 1] + sorted_values[n//2]) / 2
        else:
            return sorted_values[n//2]

    def _aggregate_missing_data(self, response_obj: 'CompsDataReviewResponse') -> MissingDataSummary:
        """
        Evaluates field-level status metrics inside the response object to build a
        comprehensive data quality report for frontend validation and rendering.
        """
        critical_missing = []
        optional_missing = []
        retrieved_count = 0
        calculated_count = 0

        # Scan each financial and macro parameter container inside the response object
        for container_name in ["historical_financials", "market_data", "peer_comparables", "calculated_metrics"]:
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


comps_step6_processor = CompsStep6Processor()