import logging
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime, timedelta
import pandas as pd

from ..api_adapter import APIAdapter
from ..audit_logger import get_audit_logger
from ..data_versioning import get_versioning_service
from ...middleware.validation_middleware import ValidationMiddleware

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
    years: List[str] = []  # Changed from List[int] to List[str] to match UnifiedStep6Response.periods_covered
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
    """Aggregation metrics summarizing data completeness for frontend components"""
    total_fields: int = 0
    retrieved_count: int = 0
    calculated_count: int = 0
    missing_count: int = 0
    critical_missing: List[str] = []
    optional_missing: List[str] = []
    completion_percentage: float = 0.0
    data_quality_score: float = 0.0
    valuation_ready: bool = False
    estimated_count: int = 0
    manual_override_count: int = 0
    warnings: List[str] = []
    recommendations: List[str] = []


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

    INTEGRATION: Uses APIAdapter with audit logging and versioning support
    """

    def __init__(self):
        self.api_adapter = APIAdapter(provider="yfinance", enable_alphavantage=True)  # Target company: AV as gap-filler
        self.peer_adapter = APIAdapter(provider="yfinance", enable_alphavantage=False)  # Peers: yfinance-only
        self._audit_logger = None
        self._versioning_service = None
        self._validator = ValidationMiddleware(method="DCF")

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
        # Initialize audit logger and versioning service if session_id is available
        session_id = session_cache.get('session_id') if session_cache else None
        if session_id:
            self._audit_logger = get_audit_logger(session_id)
            self._versioning_service = get_versioning_service(session_id)

        # GAP 1 FIX: Check session cache before fetching - implements "Fetch Once, Use Many"
        if session_cache and 'international_market_data' in session_cache:
            cached_data = session_cache['international_market_data']
            # Check if cache is valid (not older than 5 minutes)
            cache_timestamp = cached_data.get('timestamp')
            if cache_timestamp:
                cache_age = datetime.now() - cache_timestamp
                if cache_age < timedelta(minutes=5):
                    logger.info(f"Using cached market data for {ticker} (age: {cache_age.seconds}s)")
                    historical_data = historical_data or cached_data.get('historical_data')
                    market_data = market_data or cached_data.get('market_data')
                    forecast_data = forecast_data or cached_data.get('forecast_data')
                    retrieved_assumptions = retrieved_assumptions or cached_data.get('retrieved_assumptions')

        # If data is not provided (and not in cache), fetch it using APIAdapter
        if historical_data is None or market_data is None or forecast_data is None or retrieved_assumptions is None:
            logger.info(f"Fetching data for DCF analysis of {ticker} using APIAdapter")

            # Get required metrics for DCF from metric registry
            from app.core.metric_registry import get_required_metrics_for_method
            required_metrics = get_required_metrics_for_method("DCF")

            # Fetch and map data using APIAdapter (includes audit logging + versioning)
            raw_result = self.api_adapter.fetch_raw_data(ticker, required_metrics)
            mapped_result = self.api_adapter.map_and_normalize(raw_result, ticker, session_id)

            # FIX: APIAdapter returns {"data": {...}, "missing": [...], ...} NOT {"mapped_data": ...}
            # Extract the actual data dict from the mapped_result
            api_data = mapped_result.get("data", {})  # Changed from mapped_result.get("mapped_data", {})
            missing_from_api = mapped_result.get("missing", [])

            logger.info(f"APIAdapter returned {len(api_data)} metrics for {ticker}, missing: {len(missing_from_api)}")

            # --- Build multi-year DataFrames from YFinanceService output ---
            # The enhanced APIAdapter passes through _multi_year data from YFinanceService
            # which has format: {"income_statement": {"periods": [...], "total_revenue": [...], ...}}
            
            multi_year = mapped_result.get("raw_data", {}).get("_multi_year", {})
            yfs_income = multi_year.get("income_statement", {})
            yfs_bs = multi_year.get("balance_sheet", {})
            yfs_cf = multi_year.get("cash_flow", {})
            
            # Mapping from MetricRegistry IDs to YFinanceService field names
            INCOME_FIELDS = {
                "revenue": "total_revenue",
                "cost_of_revenue": "cost_of_revenue",
                "gross_profit": "gross_profit",
                "operating_expenses": "operating_expenses",
                "sg_and_a": "sg_and_a",
                "research_development": "research_development",
                "interest_expense": "interest_expense",
                "other_income": "other_income_expense",
                "pretax_income": "pretax_income",
                "tax_provision": "tax_provision",
                "deferred_tax": "deferred_tax",
                "operating_income": "ebit",
                "net_income": "net_income",
                "ebitda": "ebitda",
                "depreciation_amortization": "depreciation_amortization",
                "interest_income": "interest_income",
            }
            BS_FIELDS = {
                "total_assets": "total_assets",
                "total_liabilities": "total_liabilities",
                "total_debt": "total_debt",
                "cash_and_equivalents": "cash_and_equivalents",
                "accounts_receivable": "accounts_receivable",
                "inventory": "inventory",
                "accounts_payable": "accounts_payable",
                "shareholders_equity": "total_equity",
                "shares_outstanding": "shares_outstanding",
                "retained_earnings": "retained_earnings",
                "ppe_gross": "ppe_gross",
                "accumulated_depreciation": "accumulated_depreciation",
                "net_ppe": "net_ppe",
                "total_current_assets": "total_current_assets",
                "total_current_liabilities": "total_current_liabilities",
                "long_term_debt": "long_term_debt",
                "current_debt": "current_debt",
                "net_debt": "net_debt",
                "working_capital": "working_capital",
                "non_current_marketable_securities": "non_current_marketable_securities",
                "other_current_liabilities": "other_current_liabilities",
                "deferred_tax_liabilities": "deferred_tax_liabilities",
                "current_accrued_expenses": "current_accrued_expenses",
                "current_deferred_liabilities": "current_deferred_liabilities",
                "trade_and_other_payables_non_current": "trade_and_other_payables_non_current",
                "other_non_current_liabilities": "other_non_current_liabilities",
                "other_short_term_investments": "other_short_term_investments",
                "other_current_assets": "other_current_assets",
                "other_non_current_assets": "other_non_current_assets",
                "common_stock": "common_stock",
                "other_equity_adjustments": "other_equity_adjustments",
            }
            CF_FIELDS = {
                "operating_cash_flow": "operating_cash_flow",
                "capex": "capital_expenditure",
                "free_cash_flow": "free_cash_flow",
                "working_capital_change": "working_capital_change",
                "interest_paid": "interest_paid",
                "tax_paid": "tax_paid",
                "share_buybacks": "share_buybacks",
                "debt_repayments": "debt_repayments",
                "debt_issuance": "debt_issuance",
                "dividends_paid": "dividends_paid",
            }
            
            # Additional key variants for balance sheet fields (yfinance CamelCase + snake_case)
            BS_KEY_VARIANTS = {
                "cash_and_equivalents": ["cash_and_equivalents",
                                          "CashCashEquivalentsAndShortTermInvestments",
                                          "CashAndCashEquivalents",
                                          "Cash Cash Equivalents And Short Term Investments",
                                          "Cash And Cash Equivalents",
                                          "Cash"],
                "retained_earnings": ["retained_earnings", "RetainedEarnings", "Retained Earnings",
                                       "RetainedEarningsAccumulatedDeficit"],
                "shares_outstanding": ["shares_outstanding", "OrdinarySharesNumber", "SharesOutstanding",
                                        "Ordinary Shares Number", "Share Outstanding"],
                "total_assets": ["total_assets", "TotalAssets", "Total Assets"],
                "total_debt": ["total_debt", "TotalDebt", "Total Debt"],
                "accounts_receivable": ["accounts_receivable", "AccountsReceivable", "Receivables"],
                "inventory": ["inventory", "Inventory", "Inventories"],
                "accounts_payable": ["accounts_payable", "AccountsPayable", "Payables"],
                "shareholders_equity": ["shareholders_equity", "StockholdersEquity", "TotalEquityGrossMinorityInterest",
                                         "CommonStockEquity"],
                "ppe_gross": ["ppe_gross", "GrossPPE", "Gross PPE", "PropertyPlantAndEquipmentGross",
                              "Properties", "NetPPE",
                              "PropertyPlantAndEquipmentNet", "Property Plant And Equipment Net"],
                "accumulated_depreciation": ["accumulated_depreciation", "AccumulatedDepreciation",
                                              "Accumulated Depreciation"],
                "net_ppe": ["net_ppe", "Net PPE", "NetPPE",
                            "PropertyPlantAndEquipmentNet", "Property Plant And Equipment Net"],
                "long_term_debt": ["long_term_debt", "LongTermDebt", "Long Term Debt",
                                    "LongTermDebtAndCapitalLeaseObligation",
                                    "Long Term Debt And Capital Lease Obligation"],
                "current_debt": ["current_debt", "CurrentDebt", "Current Debt",
                                  "CurrentDebtAndCapitalLeaseObligation",
                                  "Current Debt And Capital Lease Obligation",
                                  "Short Long Term Debt", "ShortLongTermDebt"],
                "interest_income": ["interest_income", "InterestIncome", "Interest Income", "InterestEarned"],
                "working_capital": ["working_capital", "WorkingCapital", "Working Capital"],
                "non_current_marketable_securities": ["non_current_marketable_securities", "NonCurrentMarketableSecurities",
                                                      "LongTermInvestments", "Other Long Term Investments",
                                                      "Non Current Available For Sale Securities", "Available For Sale Securities"],
                "other_current_liabilities": ["other_current_liabilities", "OtherCurrentLiabilities",
                                              "Other Current Liabilities"],
                "deferred_tax_liabilities": ["deferred_tax_liabilities", "DeferredTaxLiabilities",
                                             "Net Non Current Deferred Tax Liabilities",
                                             "Non Current Deferred Taxes Liabilities",
                                             "Deferred Tax Liabilities", "deferred_tax"],
                "current_accrued_expenses": ["current_accrued_expenses", "CurrentAccruedExpenses",
                                             "Current Accrued Expenses", "PayablesAndAccruedExpenses",
                                             "Payables And Accrued Expenses"],
                "current_deferred_liabilities": ["current_deferred_liabilities", "CurrentDeferredRevenue",
                                                 "Current Deferred Revenue", "DeferredRevenueCurrent",
                                                 "Deferred Revenue Current", "Current Deferred Liabilities"],
                "trade_and_other_payables_non_current": ["trade_and_other_payables_non_current",
                                                         "NonCurrentPayables", "Non Current Payables",
                                                         "Trade Payables Non Current", "Other Non Current Liabilities"],
                "other_non_current_liabilities": ["other_non_current_liabilities", "OtherNonCurrentLiabilities",
                                                  "Other Non Current Liabilities"],
                "other_short_term_investments": ["other_short_term_investments", "OtherShortTermInvestments",
                                                 "Other Short Term Investments", "AvailableForSaleSecurities",
                                                 "Available For Sale Securities", "ShortTermInvestments"],
                "other_current_assets": ["other_current_assets", "OtherCurrentAssets",
                                         "Other Current Assets"],
                "other_non_current_assets": ["other_non_current_assets", "OtherNonCurrentAssets",
                                             "Other Non Current Assets"],
                "common_stock": ["common_stock", "CommonStockEquity", "Common Stock Equity",
                                 "CommonStock", "Common Stock", "CommonStockValue"],
                "other_equity_adjustments": ["other_equity_adjustments", "OtherEquityAdjustments",
                                             "Other Equity Adjustments", "AccumulatedOtherComprehensiveIncome",
                                             "AOCI", "TreasuryStock"],
            }

            def build_multiyear_df(yfs_section, field_map):
                """Build multi-year DataFrame from YFinanceService output.
                
                YFS format: {"periods": ["2024-12-31", ...], "total_revenue": [176B, ...], ...}
                Returns DataFrame with MetricRegistry IDs as INDEX, periods as COLUMNS.
                Tries multiple key variants for each metric to handle yfinance naming differences.
                """
                if not yfs_section or not isinstance(yfs_section, dict):
                    return None
                periods = yfs_section.get("periods", [])
                if not periods:
                    return None
                sorted_periods = sorted(periods, reverse=True)[:4]
                
                metrics_data = {}
                for metric_id, yfs_key in field_map.items():
                    values = yfs_section.get(yfs_key)
                    # If primary key didn't work, try additional variants
                    if not (isinstance(values, list) and values):
                        variants = BS_KEY_VARIANTS.get(metric_id, [])
                        for alt_key in variants:
                            if alt_key != yfs_key:
                                values = yfs_section.get(alt_key)
                                if isinstance(values, list) and values:
                                    break
                    if isinstance(values, list) and values:
                        padded = values[:len(sorted_periods)]
                        while len(padded) < len(sorted_periods):
                            padded.append(None)
                        if any(v is not None for v in padded):
                            metrics_data[metric_id] = padded
                
                if metrics_data:
                    df = pd.DataFrame.from_dict(metrics_data, orient='index', columns=sorted_periods)
                    logger.info(f"[Step6DCF] Built multi-year DataFrame: {len(df)} metrics x {len(df.columns)} periods")
                    return df
                return None
            
            # Fallback: single-period DataFrame from APIAdapter mapped data
            def build_single_period_df(api_data_dict):
                if not api_data_dict:
                    return None
                metrics_data = {}
                for metric_id, metric_info in api_data_dict.items():
                    if isinstance(metric_info, dict) and "value" in metric_info:
                        metrics_data[metric_id] = metric_info["value"]
                    elif not isinstance(metric_info, dict):
                        metrics_data[metric_id] = metric_info
                if not metrics_data:
                    return None
                return pd.DataFrame.from_dict(metrics_data, orient='index', columns=["Latest"])
            
            # Build DataFrames: prefer multi-year, fallback to single-period
            financials_df = build_multiyear_df(yfs_income, INCOME_FIELDS)
            if financials_df is None:
                financials_df = build_single_period_df(api_data)
            balance_sheet_df = build_multiyear_df(yfs_bs, BS_FIELDS)
            cashflow_df = build_multiyear_df(yfs_cf, CF_FIELDS)
            
            logger.info(f"[Step6DCF] Built DataFrames: financials={financials_df is not None} ({len(financials_df) if financials_df is not None else 0} rows), "
                       f"balance_sheet={balance_sheet_df is not None}, cashflow={cashflow_df is not None}")

            logger.info(f"[Step6DCF] Built DataFrames: financials={financials_df is not None}, balance_sheet={balance_sheet_df is not None}, cashflow={cashflow_df is not None}")


            historical_data = historical_data or {
                'financials': financials_df,
                'balance_sheet': balance_sheet_df,
                'cashflow': cashflow_df
            }
            market_data = market_data or api_data
            # Merge raw info (key_stats) into market_data so _process_dcf_market_data can find totalCash, beta, etc.
            raw_info = mapped_result.get("raw_data", {}).get("info", {})
            if raw_info and isinstance(raw_info, dict):
                for k, v in raw_info.items():
                    if v is not None and k not in market_data:
                        market_data[k] = v
            forecast_data = forecast_data or {}
            
            # Fetch peer data if not provided (for WACC calculation)
            if not retrieved_assumptions:
                # Look for peer tickers in multiple session locations
                # SessionService stores peer data in session["data"]["peer_tickers"]
                # (because "peer_tickers" is not in shared_keys list)
                peer_tickers = []
                if session_cache:
                    # Check session["data"]["peer_tickers"] (where SessionService actually stores it)
                    data_dict = session_cache.get('data', {})
                    if isinstance(data_dict, dict):
                        peer_tickers = data_dict.get('peer_tickers', [])
                    # Also check top-level (backward compatibility)
                    if not peer_tickers:
                        peer_tickers = session_cache.get('peer_tickers', [])
                    # Also check selected_peers in data dict
                    if not peer_tickers and isinstance(data_dict, dict):
                        selected_peers = data_dict.get('selected_peers', [])
                        if selected_peers:
                            peer_tickers = [p.get('symbol', p.get('ticker', '')) if isinstance(p, dict) else str(p) for p in selected_peers]
                    # Also check top-level selected_peers
                    if not peer_tickers:
                        selected_peers = session_cache.get('selected_peers', [])
                        if selected_peers:
                            peer_tickers = [p.get('symbol', p.get('ticker', '')) if isinstance(p, dict) else str(p) for p in selected_peers]
                    # Also check peer_data.peers
                    if not peer_tickers:
                        peer_data_section = session_cache.get('peer_data', {})
                        if isinstance(peer_data_section, dict):
                            peer_tickers = peer_data_section.get('peers', [])
                    # Also check valuation track (nested structure)
                    if not peer_tickers:
                        valuations = session_cache.get('valuations', {})
                        if isinstance(valuations, dict):
                            for market_key, market_data in valuations.items():
                                if isinstance(market_data, dict):
                                    for method_key, method_data in market_data.items():
                                        if isinstance(method_data, dict):
                                            # Check data sub-dict first
                                            track_data = method_data.get('data', {})
                                            if isinstance(track_data, dict):
                                                peer_tickers = track_data.get('peer_tickers', [])
                                                if not peer_tickers:
                                                    sp = track_data.get('selected_peers', [])
                                                    if sp:
                                                        peer_tickers = [p.get('symbol', p.get('ticker', '')) if isinstance(p, dict) else str(p) for p in sp]
                                            if not peer_tickers:
                                                peer_tickers = method_data.get('peer_tickers', [])
                                            if peer_tickers:
                                                break
                                if peer_tickers:
                                    break

                logger.info(f"[Step6DCF] Found {len(peer_tickers)} peer tickers in session: {peer_tickers}")

                if peer_tickers:
                    logger.info(f"[Step6DCF] Fetching data for {len(peer_tickers)} peers: {peer_tickers}")
                    peer_data = {}
                    # Peer metrics: DCF-required + additional fields needed for multiples calculation
                    peer_metrics = list(set(required_metrics + [
                        "market_cap", "enterprise_value", "ebitda", "revenue",
                        "current_price", "book_value", "beta", "total_debt",
                        "cash_and_equivalents", "effective_tax_rate", "cost_of_debt",
                        "net_income", "shares_outstanding", "pe_ratio", "pb_ratio"
                    ]))
                    for peer_ticker in peer_tickers[:5]:  # Limit to 5 peers
                        try:
                            peer_raw = self.peer_adapter.fetch_raw_data(peer_ticker, peer_metrics)
                            peer_mapped = self.peer_adapter.map_and_normalize(peer_raw, peer_ticker)
                            # Extract plain values from mapped data format {metric_id: {value: ..., unit: ...}}
                            raw_mapped = peer_mapped.get("data", {})
                            peer_values = {}
                            for k, v in raw_mapped.items():
                                if isinstance(v, dict) and "value" in v:
                                    peer_values[k] = v["value"]
                                else:
                                    peer_values[k] = v
                            # Also merge raw info (key_stats) so totalCash, effectiveTaxRate, etc. are available
                            peer_info = peer_mapped.get("raw_data", {}).get("info", {})
                            if peer_info and isinstance(peer_info, dict):
                                for k, v in peer_info.items():
                                    if v is not None and k not in peer_values:
                                        peer_values[k] = v
                            peer_data[f"peer_{peer_ticker}_info"] = peer_values
                        except Exception as e:
                            logger.warning(f"[Step6DCF] Failed to fetch peer data for {peer_ticker}: {e}")
                    retrieved_assumptions = {"peers": peer_tickers, "peer_data": peer_data}
                    # Also include peer_market_data from session (populated by Step 4)
                    if session_cache and 'peer_market_data' in session_cache:
                        retrieved_assumptions["peer_market_data"] = session_cache['peer_market_data']
                    logger.info(f"[Step6DCF] Fetched peer data for {len(peer_data)} peers")
                else:
                    logger.warning(f"[Step6DCF] No peer tickers found in session for {ticker}")
                    retrieved_assumptions = {}
            else:
                retrieved_assumptions = retrieved_assumptions

        user_overrides = user_overrides or {}

        # Process DCF-specific data components
        logger.info(f"Processing DCF historical financials for {ticker}")
        historical_display = self._process_dcf_historical(historical_data, user_overrides)

        logger.info(f"Processing DCF market data for {ticker}")
        market_display = self._process_dcf_market_data(market_data, user_overrides)

        logger.info(f"Processing DCF opening balances for {ticker}")
        opening_display = await self._process_dcf_opening_balances(historical_data, user_overrides, ticker=ticker)

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

        # Create response object first to pass into _aggregate_missing_data
        response_obj = DCFDataReviewResponse(
            session_id=f"step6_dcf_{ticker}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            ticker=ticker,
            timestamp=datetime.now(),
            valuation_model="DCF",
            historical_financials=historical_display,
            forecast_drivers=ForecastDriversDisplay(
                data_fields=(
                    opening_display.data_fields +
                    (peer_display.data_fields if peer_display else []) +
                    # Add risk-free rate and equity risk premium from market_data
                    # (unified schema expects these in forecast_drivers, not market_data)
                    [f for f in market_display.data_fields if f.field_name in ("risk_free_rate", "equity_risk_premium")]
                )
            ),
            market_data=market_display,
            peer_comparables=peer_display,
            calculated_metrics=calculated_display,
            missing_data_summary=None,  # Will be set below
            manual_overrides_applied=user_overrides,
            data_complete=False,
            message=""
        )

        # Ensure mandatory placeholders exist before aggregating missing data
        self._ensure_mandatory_placeholders(response_obj)

        # Pass response_obj into _aggregate_missing_data to fix scope issue
        missing_summary = self._aggregate_missing_data_from_response(response_obj)

        ready = len(missing_summary.critical_missing) == 0

        # GAP 1 FIX: Store fetched data in session cache for "Fetch Once, Use Many"
        if session_cache is not None:
            session_cache['international_market_data'] = {
                'timestamp': datetime.now(),
                'historical_data': historical_data,
                'market_data': market_data,
                'forecast_data': forecast_data,
                'retrieved_assumptions': retrieved_assumptions
            }
            logger.info(f"Cached market data for {ticker} in session")

        response_obj.missing_data_summary = missing_summary
        response_obj.data_complete = ready
        response_obj.message = "DCF data aggregated successfully. Ready for next steps." if ready else "Missing critical DCF data. Please retrieve missing inputs."

        return response_obj

    def _process_dcf_historical(
        self,
        historical_data: Dict,
        user_overrides: Dict
    ) -> HistoricalFinancialsDisplay:
        """Process DCF historical financials (comprehensive field list)"""
        financials_df = historical_data.get('financials')
        balance_sheet_df = historical_data.get('balance_sheet')
        cashflow_df = historical_data.get('cashflow')

        data_fields = []
        years = []

        # Extract years from financial statements
        # NOTE: yfinance columns are newest-first, so [:4] gets the 4 most recent
        if financials_df is not None and not financials_df.empty:
            years = [str(col.year) if hasattr(col, 'year') else str(col) for col in financials_df.columns[:4]]

        # COMPREHENSIVE DCF historical fields (40+ fields to match frontend expectations)
        dcf_historical_fields = [
            # Income Statement
            ("revenue", "Total Revenue", True),
            ("cogs", "Cost of Revenue (COGS)", True),
            ("gross_profit", "Gross Profit", True),
            ("operating_expenses", "Operating Expenses", True),
            ("research_development", "Research & Development", False),
            ("ebitda", "EBITDA", True),
            ("ebit", "EBIT / Operating Income", True),
            ("interest_expense", "Interest Expense", True),
            ("other_income", "Other Income/Expense", False),
            ("pretax_income", "Pre-Tax Income", True),
            ("tax_provision", "Tax Provision", True),
            ("net_income", "Net Income", True),
            ("depreciation_amortization", "Depreciation & Amortization", True),

            # SG&A (separate from operating_expenses for DCF income statement)
            ("sg_and_a", "SG&A Expenses", False),

            # Deferred Tax (needed for tax schedule current/deferred split)
            ("deferred_tax", "Deferred Tax", False),

            # Cash Flow
            ("capex", "Capital Expenditures (CapEx)", True),
            ("operating_cash_flow", "Operating Cash Flow", True),
            ("free_cash_flow", "Free Cash Flow", True),
            ("working_capital_change", "Working Capital Changes", False),
            ("interest_paid", "Interest Paid (Cash)", False),
            ("tax_paid", "Income Tax Paid (Cash)", False),
            ("share_buybacks", "Share Buybacks", False),
            ("debt_repayments", "Debt Repayments", False),
            ("debt_issuance", "Debt Issuance", False),
            ("dividends_paid", "Dividends Paid", False),

            # Balance Sheet - Working Capital
            ("accounts_receivable", "Accounts Receivable", True),
            ("inventory", "Inventory", True),
            ("accounts_payable", "Accounts Payable", True),
            ("cash_and_equivalents", "Cash & Equivalents", True),

            # Balance Sheet - Long-term
            ("total_assets", "Total Assets", True),
            ("total_debt", "Total Debt", True),
            ("long_term_debt", "Long-Term Debt", False),
            ("current_debt", "Current Debt", False),
            ("shareholders_equity", "Shareholders Equity", True),
            ("retained_earnings", "Retained Earnings", False),
            ("shares_outstanding", "Shares Outstanding", True),
            ("interest_income", "Interest Income", False),
            ("working_capital", "Working Capital (Direct)", False),

            # Balance Sheet - Additional historical fields
            # NOTE: non_current_marketable_securities, other_current_liabilities,
            # and deferred_tax_liabilities are EXCLUDED here because they are
            # already in _process_dcf_opening_balances (forecast_drivers).
            # Including them here caused duplicates in the missing_data_summary.
            ("net_ppe", "PP&E (Net)", False),
            ("net_debt", "Net Debt", False),
            ("total_current_assets", "Total Current Assets", False),
            ("total_current_liabilities", "Total Current Liabilities", False),
            ("total_liabilities", "Total Liabilities", False),

            # Margins (calculated)
            ("gross_margin", "Gross Margin", False),
            ("operating_margin", "Operating Margin", False),
            ("net_margin", "Net Margin", False),

            # Additional metrics
            ("ebit_margin", "EBIT Margin", False),
            ("tax_rate", "Effective Tax Rate", False),
            ("change_in_nwc", "Change in Net Working Capital", True)
        ]

        for field_name, display_name, is_critical in dcf_historical_fields:
            value = None
            status = DataStatus.MISSING
            source = "yfinance"
            formula = None

            # Try to extract from financial statements
            if financials_df is not None:
                value = self._extract_metric_from_financials(field_name, financials_df, balance_sheet_df, cashflow_df)
                if value is not None:
                    # Check if this was calculated (not directly retrieved) and set formula
                    if field_name == "gross_profit":
                        status = DataStatus.CALCULATED
                        source = "Calculated from API data"
                        formula = "Revenue - COGS"
                    elif field_name == "free_cash_flow":
                        status = DataStatus.CALCULATED
                        source = "Calculated from API data"
                        formula = "Operating Cash Flow - CapEx"
                    elif field_name == "change_in_nwc":
                        status = DataStatus.CALCULATED
                        source = "Calculated from API data"
                        formula = "Δ(AR + Inventory - AP)"
                    elif field_name == "ebit":
                        status = DataStatus.CALCULATED
                        source = "Calculated from API data"
                        formula = "EBITDA - Depreciation & Amortization"
                    elif field_name == "operating_expenses":
                        status = DataStatus.CALCULATED
                        source = "Calculated from API data"
                        formula = "Gross Profit - EBIT"
                    elif field_name in ["pretax_income", "interest_expense", "other_income", "tax_provision",
                                        "working_capital_changes", "retained_earnings", "shares_outstanding"]:
                        status = DataStatus.CALCULATED
                        source = "Calculated from API data"
                    else:
                        status = DataStatus.RETRIEVED

            # Check for user override
            if field_name in user_overrides:
                value = user_overrides[field_name]
                status = DataStatus.MANUAL_OVERRIDE
                formula = None  # User override takes precedence

            data_fields.append(DataField(
                field_name=field_name,
                display_name=display_name,
                value=value,
                unit="USD" if "margin" not in field_name and "rate" not in field_name else "%",
                status=status,
                source=source,
                formula=formula,
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
    ) -> Optional[List[float]]:
        """Extract specific metric from financial statements - returns array of values for all periods

        Returns a list of values (one per period) instead of a single value to match DataField.value format.
        """
        # COMPREHENSIVE mapping of field names to financial statement keys
        # Covers Income Statement, Balance Sheet, and Cash Flow items
        # Note: yfinance v1.3.0+ returns CamelCase without spaces (e.g., TotalRevenue)
        # but our service converts them to snake_case (e.g., total_revenue)
        income_mapping = {
            "revenue": ["revenue", "TotalRevenue", "total_revenue", "OperatingRevenue"],
            "cogs": ["cost_of_revenue", "CostOfRevenue", "ReconciledCostOfRevenue"],
            # Note: gross_profit removed from mapping - it's now CALCULATED (Revenue - COGS)
            "operating_expenses": ["operating_expenses", "OperatingExpense", "TotalOperatingExpenses"],
            "research_development": ["research_development", "ResearchAndDevelopment", "R&D"],
            "ebitda": ["ebitda", "EBITDA", "NormalizedEBITDA"],
            "sg_and_a": ["sg_and_a", "SellingGeneralAndAdministration", "Selling General And Administration"],
            "deferred_tax": ["deferred_tax", "DeferredIncomeTax", "Deferred Tax", "Deferred Income Tax"],
            # Note: ebit removed from mapping - it's now CALCULATED (EBITDA - D&A)
            "interest_expense": ["interest_expense", "InterestExpense", "InterestAndDebtExpense"],
            "other_income": ["other_income", "OtherIncomeExpense", "OtherIncome/Expense"],
            "pretax_income": ["pretax_income", "PretaxIncome", "Pre-TaxIncome"],
            "tax_provision": ["tax_provision", "TaxProvision", "IncomeTaxExpense"],
            "net_income": ["net_income", "NetIncome", "NetIncomeCommonStockholders"],
            "depreciation_amortization": ["depreciation_amortization", "ReconciledDepreciation", "DepreciationAndAmortization"],
            "interest_income": ["interest_income", "InterestIncome", "Interest Income", "InterestEarned"],
        }

        # Add debug logging to see what's in the DataFrames
        logger.debug(f"Financials DF columns: {financials_df.columns.tolist() if financials_df is not None else 'None'}")
        logger.debug(f"Financials DF index (first 20): {list(financials_df.index)[:20] if financials_df is not None else 'None'}")
        logger.debug(f"Balance Sheet DF columns: {balance_sheet_df.columns.tolist() if balance_sheet_df is not None else 'None'}")
        logger.debug(f"Balance Sheet DF index (first 30): {list(balance_sheet_df.index)[:30] if balance_sheet_df is not None else 'None'}")
        logger.debug(f"Cash Flow DF columns: {cashflow_df.columns.tolist() if cashflow_df is not None else 'None'}")
        logger.debug(f"Cash Flow DF index (first 20): {list(cashflow_df.index)[:20] if cashflow_df is not None else 'None'}")

        balance_sheet_mapping = {
            "accounts_receivable": ["accounts_receivable", "AccountsReceivable", "Receivables"],
            "inventory": ["inventory", "Inventory", "Inventories"],
            "accounts_payable": ["accounts_payable", "AccountsPayable", "Payables", "PayablesAndAccruedExpenses"],
            # Cash: yfinance v1.3.0+ uses CamelCase WITHOUT spaces
            "cash_and_equivalents": ["cash_and_equivalents", "CashCashEquivalentsAndShortTermInvestments",
                                     "CashAndCashEquivalents", "CashCashEquivalents",
                                     "Cash And Cash Equivalents", "Cash"],
            "total_assets": ["total_assets", "TotalAssets", "Assets"],
            "total_debt": ["total_debt", "TotalDebt", "Debt"],
            "shareholders_equity": ["shareholders_equity", "StockholdersEquity",
                                    "TotalEquityGrossMinorityInterest", "CommonStockEquity"],
            "retained_earnings": ["retained_earnings", "RetainedEarnings"],
            "shares_outstanding": ["shares_outstanding", "OrdinarySharesNumber", "SharesOutstanding"],
            # PP&E: yfinance v1.3.0+ uses 'GrossPPE' (CamelCase no spaces)
            "ppe_gross": ["ppe_gross", "GrossPPE", "Gross PPE",
                          "PropertyPlantAndEquipmentGross", "Properties",
                          "NetPPE", "PropertyPlantAndEquipmentNet"],
            # Accumulated Depreciation: yfinance v1.3.0+ uses 'AccumulatedDepreciation'
            "accumulated_depreciation": ["accumulated_depreciation", "AccumulatedDepreciation",
                                         "Accumulated Depreciation", "accumulated_amortization"],
            # Long-term Debt: yfinance v1.3.0+ uses 'LongTermDebt'
            "long_term_debt": ["long_term_debt", "LongTermDebt", "Long Term Debt",
                               "LongTermDebtAndCapitalLeaseObligation"],
            # Current Debt: yfinance v1.3.0+ uses 'CurrentDebt'
            "current_debt": ["current_debt", "CurrentDebt", "Current Debt",
                             "CurrentDebtAndCapitalLeaseObligation", "ShortLongTermDebt"],
            "interest_income": ["interest_income", "InterestIncome", "Interest Income", "InterestEarned"],
            "working_capital": ["working_capital", "WorkingCapital", "Working Capital"],
            # Net PP&E: needed for Asset Schedule PP&E roll
            "net_ppe": ["net_ppe", "NetPPE", "Net PPE",
                        "PropertyPlantAndEquipmentNet", "Property Plant And Equipment Net"],
            # Net Debt: Total Debt - Cash (needed for equity bridge)
            "net_debt": ["net_debt", "NetDebt", "Net Debt"],
            # Total Current Assets: needed for Balance Sheet opening
            "total_current_assets": ["total_current_assets", "CurrentAssets", "Current Assets",
                                     "TotalCurrentAssets", "Total Current Assets"],
            # Total Current Liabilities: needed for Balance Sheet opening
            "total_current_liabilities": ["total_current_liabilities", "CurrentLiabilities", "Current Liabilities",
                                          "TotalCurrentLiabilities", "Total Current Liabilities"],
            # Total Liabilities: needed for Balance Sheet opening
            "total_liabilities": ["total_liabilities", "TotalLiabilitiesNetMinorityInterest",
                                  "Total Liabilities Net Minority Interest", "TotalLiabilities",
                                  "Total Liabilities"],
            "non_current_marketable_securities": ["non_current_marketable_securities", "NonCurrentMarketableSecurities",
                                                  "LongTermInvestments", "Other Long Term Investments",
                                                  "Non Current Available For Sale Securities"],
            "other_current_liabilities": ["other_current_liabilities", "OtherCurrentLiabilities",
                                          "Other Current Liabilities"],
            "deferred_tax_liabilities": ["deferred_tax_liabilities", "DeferredTaxLiabilities",
                                         "Net Non Current Deferred Tax Liabilities",
                                         "Non Current Deferred Taxes Liabilities"],
            "current_accrued_expenses": ["current_accrued_expenses", "CurrentAccruedExpenses",
                                         "Current Accrued Expenses", "PayablesAndAccruedExpenses"],
            "current_deferred_liabilities": ["current_deferred_liabilities", "CurrentDeferredRevenue",
                                             "Current Deferred Revenue", "DeferredRevenueCurrent"],
            "trade_and_other_payables_non_current": ["trade_and_other_payables_non_current",
                                                     "NonCurrentPayables", "Non Current Payables"],
            "other_non_current_liabilities": ["other_non_current_liabilities", "OtherNonCurrentLiabilities",
                                              "Other Non Current Liabilities"],
            "other_short_term_investments": ["other_short_term_investments", "OtherShortTermInvestments",
                                             "Other Short Term Investments", "AvailableForSaleSecurities"],
            "other_current_assets": ["other_current_assets", "OtherCurrentAssets",
                                     "Other Current Assets"],
            "other_non_current_assets": ["other_non_current_assets", "OtherNonCurrentAssets",
                                         "Other Non Current Assets"],
            "common_stock": ["common_stock", "CommonStockEquity", "Common Stock Equity",
                             "CommonStock", "Common Stock"],
            "other_equity_adjustments": ["other_equity_adjustments", "OtherEquityAdjustments",
                                         "AccumulatedOtherComprehensiveIncome", "AOCI", "TreasuryStock"],
        }

        # DEBUG: Log the mapping being used for troubleshooting
        logger.debug(f"[Step6DCF] Balance sheet mapping keys: {list(balance_sheet_mapping.keys())}")
        logger.debug(f"[Step6DCF] Looking for total_assets with variants: {balance_sheet_mapping['total_assets']}")
        logger.debug(f"[Step6DCF] Looking for shareholders_equity with variants: {balance_sheet_mapping['shareholders_equity']}")

        cash_flow_mapping = {
            "capex": ["capex", "capital_expenditure", "CapitalExpenditure", "PurchaseOfPropertyPlantAndEquipment", "Purchase Of PPE"],
            "operating_cash_flow": ["operating_cash_flow", "OperatingCashFlow", "CashFlowFromContinuingOperatingActivities"],
            "free_cash_flow": ["free_cash_flow", "FreeCashFlow"],
            "working_capital_change": ["working_capital_change", "working_capital_changes", "ChangeInWorkingCapital", "WorkingCapitalChanges"],
            "interest_paid": ["interest_paid", "InterestPaidSupplementalData", "Interest Paid Supplemental Data", "InterestPaid"],
            "tax_paid": ["tax_paid", "income_tax_paid", "IncomeTaxPaidSupplementalData", "Income Tax Paid Supplemental Data", "IncomeTaxPaid"],
            "share_buybacks": ["share_buybacks", "repurchase_of_capital_stock", "RepurchaseOfCapitalStock", "Repurchase Of Capital Stock", "RepurchaseOfCommonStock", "NetCommonStockIssuance"],
            "debt_repayments": ["debt_repayments", "repayment_of_debt", "RepaymentOfDebt", "Repayment Of Debt", "LongTermDebtPayments"],
            "debt_issuance": ["debt_issuance", "issuance_of_debt", "IssuanceOfDebt", "Issuance Of Debt", "LongTermDebtIssuance"],
            "dividends_paid": ["dividends_paid", "cash_dividends_paid", "CashDividendsPaid", "Cash Dividends Paid", "CommonStockDividendPaid"],
        }

        # STEP 1: Handle calculated fields FIRST (before trying to extract from DataFrames)
        # Helper: extract values directly from a DataFrame by trying multiple key variants
        def _extract_from_df(df, keys_to_try):
            """Extract values from DataFrame using multiple key variants"""
            if df is None or df.empty:
                return None
            for key in keys_to_try:
                if key in df.index:
                    series = df.loc[key]
                    values = [float(v) if pd.notna(v) else None for v in series.values]
                    return values if any(v is not None for v in values) else None
            return None

        if field_name == "gross_profit":
            # Gross Profit = Revenue - COGS (calculate for each period)
            revenue_values = _extract_from_df(financials_df, ["revenue", "TotalRevenue", "total_revenue", "OperatingRevenue"])
            cogs_values = _extract_from_df(financials_df, ["cost_of_revenue", "cogs", "CostOfRevenue", "ReconciledCostOfRevenue"])
            if revenue_values and cogs_values:
                gp_values = []
                for i in range(min(len(revenue_values), len(cogs_values))):
                    if revenue_values[i] is not None and cogs_values[i] is not None:
                        gp_values.append(revenue_values[i] - cogs_values[i])
                    else:
                        gp_values.append(None)
                return gp_values if gp_values else None
            return None

        if field_name == "free_cash_flow":
            # FCF = Operating Cash Flow - CapEx (calculate for each period)
            op_cf_values = _extract_from_df(cashflow_df, ["operating_cash_flow", "OperatingCashFlow", "CashFlowFromContinuingOperatingActivities"])
            capex_values = _extract_from_df(cashflow_df, ["capital_expenditure", "capex", "CapitalExpenditure", "PurchaseOfPropertyPlantAndEquipment"])
            if not op_cf_values:
                op_cf_values = _extract_from_df(financials_df, ["operating_cash_flow", "OperatingCashFlow"])
            if not capex_values:
                capex_values = _extract_from_df(financials_df, ["capital_expenditure", "capex"])
            if op_cf_values and capex_values:
                fcf_values = []
                for i in range(min(len(op_cf_values), len(capex_values))):
                    if op_cf_values[i] is not None and capex_values[i] is not None:
                        fcf_values.append(op_cf_values[i] - abs(capex_values[i]))
                    else:
                        fcf_values.append(None)
                return fcf_values if fcf_values else None
            return None

        if field_name == "change_in_nwc":
            # Change in NWC = (AR + Inventory - AP) change year over year
            ar_values = _extract_from_df(balance_sheet_df, ["accounts_receivable", "AccountsReceivable", "Receivables"])
            inv_values = _extract_from_df(balance_sheet_df, ["inventory", "Inventory", "Inventories"])
            ap_values = _extract_from_df(balance_sheet_df, ["accounts_payable", "AccountsPayable", "Payables"])
            if ar_values and inv_values and ap_values and len(ar_values) >= 2:
                nwc_changes = []
                for i in range(1, min(len(ar_values), len(inv_values), len(ap_values))):
                    if all(v is not None for v in [ar_values[i], inv_values[i], ap_values[i], ar_values[i-1], inv_values[i-1], ap_values[i-1]]):
                        nwc_current = ar_values[i] + inv_values[i] - ap_values[i]
                        nwc_prior = ar_values[i-1] + inv_values[i-1] - ap_values[i-1]
                        nwc_changes.append(nwc_current - nwc_prior)
                    else:
                        nwc_changes.append(None)
                return [None] + nwc_changes if nwc_changes else None
            return None

        if field_name == "ebit":
            # EBIT = EBITDA - Depreciation & Amortization
            ebitda_values = _extract_from_df(financials_df, ["ebitda", "EBITDA", "NormalizedEBITDA"])
            d_and_a_values = _extract_from_df(financials_df, ["depreciation_amortization", "ReconciledDepreciation", "DepreciationAndAmortization"])
            if ebitda_values and d_and_a_values:
                ebit_values = []
                for i in range(min(len(ebitda_values), len(d_and_a_values))):
                    if ebitda_values[i] is not None and d_and_a_values[i] is not None:
                        ebit_values.append(ebitda_values[i] - d_and_a_values[i])
                    else:
                        ebit_values.append(None)
                return ebit_values if ebit_values else None
            return None

        if field_name == "operating_expenses":
            # Operating Expenses = Revenue - COGS - EBIT (try direct calculation first)
            revenue_values = _extract_from_df(financials_df, ["revenue", "TotalRevenue", "total_revenue"])
            cogs_values = _extract_from_df(financials_df, ["cost_of_revenue", "cogs", "CostOfRevenue"])
            ebit_values = _extract_from_df(financials_df, ["ebitda", "EBITDA"])
            d_and_a_values = _extract_from_df(financials_df, ["depreciation_amortization", "ReconciledDepreciation"])
            if revenue_values and cogs_values:
                # Calculate EBIT if not directly available
                if not ebit_values or not d_and_a_values:
                    ebit_values = revenue_values  # fallback: use revenue as proxy
                    cogs_for_sub = cogs_values
                else:
                    ebit_calc = []
                    for i in range(min(len(ebit_values), len(d_and_a_values))):
                        if ebit_values[i] is not None and d_and_a_values[i] is not None:
                            ebit_calc.append(ebit_values[i] - d_and_a_values[i])
                        else:
                            ebit_calc.append(None)
                    ebit_values = ebit_calc
                    cogs_for_sub = cogs_values
                if ebit_values and cogs_for_sub:
                    opex_values = []
                    for i in range(min(len(revenue_values), len(cogs_for_sub), len(ebit_values))):
                        if all(v is not None for v in [revenue_values[i], cogs_for_sub[i], ebit_values[i]]):
                            opex_values.append(revenue_values[i] - cogs_for_sub[i] - ebit_values[i])
                        else:
                            opex_values.append(None)
                    return opex_values if opex_values else None
            return None

        if field_name == "pretax_income":
            # Pre-Tax Income = EBIT - Interest Expense
            ebit_values = _extract_from_df(financials_df, ["ebitda", "EBITDA"])
            d_and_a_values = _extract_from_df(financials_df, ["depreciation_amortization", "ReconciledDepreciation"])
            interest_values = _extract_from_df(financials_df, ["interest_expense", "InterestExpense", "InterestAndDebtExpense"])
            # Calculate EBIT from EBITDA - D&A
            if ebit_values and d_and_a_values:
                ebit_calc = []
                for i in range(min(len(ebit_values), len(d_and_a_values))):
                    if ebit_values[i] is not None and d_and_a_values[i] is not None:
                        ebit_calc.append(ebit_values[i] - d_and_a_values[i])
                    else:
                        ebit_calc.append(None)
                ebit_values = ebit_calc
            if ebit_values and interest_values:
                pretax_values = []
                for i in range(min(len(ebit_values), len(interest_values))):
                    if ebit_values[i] is not None and interest_values[i] is not None:
                        pretax_values.append(ebit_values[i] - interest_values[i])
                    else:
                        pretax_values.append(None)
                return pretax_values if pretax_values else None
            return None

        if field_name == "interest_expense":
            # Try income statement first (where interest_expense IS in DataFrame index),
            # then fall back to cash flow statement
            result = _extract_from_df(financials_df, ["interest_expense", "InterestExpense", "InterestAndDebtExpense"])
            if result:
                return result
            result = _extract_from_df(cashflow_df, ["interest_paid", "InterestPaid", "cash_paid_for_interest",
                                                     "interest_expense", "InterestExpense"])
            return result

        if field_name == "other_income":
            # Other Income/Expense - try multiple sources
            result = _extract_from_df(financials_df, ["other_income", "OtherIncomeExpense", "OtherIncome/Expense",
                                                      "non_operating_income", "OtherNonOperatingIncomeLossNet"])
            if result:
                return result
            # Try calculating as: Net Income - Pretax Income (if both available)
            return None

        if field_name == "tax_provision":
            # Tax Provision - try multiple sources
            result = _extract_from_df(financials_df, ["tax_provision", "TaxProvision", "IncomeTaxExpense",
                                                      "income_tax", "TaxProvisionForEquityInvestments",
                                                      "incomeTaxExpense", "taxExpense"])
            if result:
                return result
            # Try calculating as: Pretax Income - Net Income (extract directly from DataFrame)
            pretax_values = _extract_from_df(financials_df, ["pretax_income", "PretaxIncome", "IncomeBeforeTax"])
            net_income_values = _extract_from_df(financials_df, ["net_income", "NetIncome", "NetIncomeCommonStockholders"])
            if pretax_values and net_income_values:
                tax_values = []
                for i in range(min(len(pretax_values), len(net_income_values))):
                    if pretax_values[i] is not None and net_income_values[i] is not None:
                        tax_values.append(pretax_values[i] - net_income_values[i])
                    else:
                        tax_values.append(None)
                return tax_values if tax_values else None
            return None

        if field_name == "working_capital_changes":
            # Working Capital Changes - calculate from AR, Inventory, AP balance changes
            ar_values = _extract_from_df(balance_sheet_df, ["accounts_receivable", "AccountsReceivable", "Receivables"])
            inv_values = _extract_from_df(balance_sheet_df, ["inventory", "Inventory", "Inventories"])
            ap_values = _extract_from_df(balance_sheet_df, ["accounts_payable", "AccountsPayable", "Payables"])
            if ar_values and inv_values and ap_values and len(ar_values) >= 2:
                wc_changes = [None]  # First period has no prior
                for i in range(1, min(len(ar_values), len(inv_values), len(ap_values))):
                    if all(v is not None for v in [ar_values[i], inv_values[i], ap_values[i], ar_values[i-1], inv_values[i-1], ap_values[i-1]]):
                        nwc_curr = ar_values[i] + inv_values[i] - ap_values[i]
                        nwc_prior = ar_values[i-1] + inv_values[i-1] - ap_values[i-1]
                        wc_changes.append(nwc_curr - nwc_prior)
                    else:
                        wc_changes.append(None)
                return wc_changes if len(wc_changes) > 1 else None
            # Fallback: try cashflow_df for change_in_nwc
            result = _extract_from_df(cashflow_df, ["working_capital_change", "working_capital_changes",
                                                     "ChangeInWorkingCapital", "WorkingCapitalChanges"])
            return result

        if field_name == "retained_earnings":
            # Retained Earnings from Balance Sheet - try multiple key variants
            result = _extract_from_df(balance_sheet_df, [
                "retained_earnings", "RetainedEarnings", "accumulated_deficit",
                "AccumulatedDeficit", "Retained Earnings", "RetainedEarningsAccumulatedDeficit"
            ])
            return result

        if field_name == "shares_outstanding":
            # Shares Outstanding - try balance sheet, then market data
            result = _extract_from_df(balance_sheet_df, [
                "shares_outstanding", "OrdinarySharesNumber", "SharesOutstanding",
                "common_shares_outstanding", "CommonSharesOutstanding",
                "Ordinary Shares Number", "Share Outstanding"
            ])
            if result:
                return result
            # Also try cashflow_df (some companies report it there)
            result = _extract_from_df(cashflow_df, [
                "shares_outstanding", "OrdinarySharesNumber", "SharesOutstanding"
            ])
            return result

        # Calculate margins if requested
        if field_name == "gross_margin":
            revenue = self._extract_metric_from_financials("revenue", financials_df, balance_sheet_df, cashflow_df)
            gross_profit = self._extract_metric_from_financials("gross_profit", financials_df, balance_sheet_df, cashflow_df)
            if revenue and gross_profit:
                return [(gp / rev * 100) if rev and gp else None for gp, rev in zip(gross_profit, revenue)]

        if field_name == "operating_margin" or field_name == "ebit_margin":
            revenue = self._extract_metric_from_financials("revenue", financials_df, balance_sheet_df, cashflow_df)
            ebit = self._extract_metric_from_financials("ebit", financials_df, balance_sheet_df, cashflow_df)
            if revenue and ebit:
                return [(e / r * 100) if r and e else None for e, r in zip(ebit, revenue)]

        if field_name == "net_margin":
            revenue = self._extract_metric_from_financials("revenue", financials_df, balance_sheet_df, cashflow_df)
            net_income = self._extract_metric_from_financials("net_income", financials_df, balance_sheet_df, cashflow_df)
            if revenue and net_income:
                return [(ni / r * 100) if r and ni else None for ni, r in zip(net_income, revenue)]

        if field_name == "tax_rate":
            pretax = self._extract_metric_from_financials("pretax_income", financials_df, balance_sheet_df, cashflow_df)
            tax = self._extract_metric_from_financials("tax_provision", financials_df, balance_sheet_df, cashflow_df)
            if pretax and tax:
                return [(t / p * 100) if p and t else None for t, p in zip(tax, pretax)]

        # Handle total_assets and shareholders_equity from balance sheet
        if field_name == "total_assets":
            if balance_sheet_df is not None:
                asset_keys = ["total_assets", "TotalAssets", "Assets", "Total Assets"]
                for key in asset_keys:
                    if key in balance_sheet_df.index:
                        series = balance_sheet_df.loc[key]
                        values = [float(v) if pd.notna(v) else None for v in series.values]
                        logger.debug(f"[Step6DCF] Found total_assets using key '{key}': {values[:2]}...")
                        return values if values else None
            logger.debug("[Step6DCF] total_assets NOT FOUND in balance_sheet_df")
            return None

        if field_name == "shareholders_equity":
            if balance_sheet_df is not None:
                equity_keys = ["shareholders_equity", "StockholdersEquity", "TotalEquityGrossMinorityInterest",
                              "CommonStockEquity", "Stockholders Equity", "Total Equity Gross Minority Interest"]
                for key in equity_keys:
                    if key in balance_sheet_df.index:
                        series = balance_sheet_df.loc[key]
                        values = [float(v) if pd.notna(v) else None for v in series.values]
                        logger.debug(f"[Step6DCF] Found shareholders_equity using key '{key}': {values[:2]}...")
                        return values if values else None
            logger.debug("[Step6DCF] shareholders_equity NOT FOUND in balance_sheet_df")
            return None

        if field_name == "dividends_paid":
            # Dividends Paid - try cashflow_df first, then income statement
            result = _extract_from_df(cashflow_df, [
                "dividends_paid", "cash_dividends_paid", "CashDividendsPaid",
                "Cash Dividends Paid", "CommonStockDividendPaid",
                "dividends", "DividendsPaid", "Dividends Paid"
            ])
            if result:
                return result
            # Try income statement as fallback
            result = _extract_from_df(financials_df, [
                "dividends_paid", "dividends", "DividendsPaid", "Dividends"
            ])
            return result

        if field_name == "interest_income":
            # Interest Income - try income statement first, then cashflow
            result = _extract_from_df(financials_df, [
                "interest_income", "InterestIncome", "Interest Income",
                "InterestEarned", "interest_earned"
            ])
            if result:
                return result
            result = _extract_from_df(cashflow_df, [
                "interest_income", "InterestIncome", "InterestEarned"
            ])
            return result

        # If we reach here, try to extract from DataFrames using mappings
        # Determine which DataFrame to use based on field name
        df_to_use = None
        field_mapping = None

        if field_name in income_mapping:
            df_to_use = financials_df
            field_mapping = income_mapping
        elif field_name in balance_sheet_mapping:
            df_to_use = balance_sheet_df
            field_mapping = balance_sheet_mapping
        elif field_name in cash_flow_mapping:
            df_to_use = cashflow_df
            field_mapping = cash_flow_mapping
        else:
            # Try all DataFrames for unknown fields
            pass

        # Extract values for all periods (not just latest)
        if df_to_use is not None and not df_to_use.empty:
            keys_to_try = field_mapping.get(field_name, [field_name]) if field_mapping else [field_name]

            for key in keys_to_try:
                if key in df_to_use.index:
                    # Get all values across all periods
                    series = df_to_use.loc[key]
                    # Convert to list, handling NaN values
                    values = []
                    for v in series.values:
                        if pd.notna(v):
                            values.append(float(v))
                        else:
                            values.append(None)
                    logger.debug(f"[Step6DCF] Found {field_name} using key '{key}': {values}")
                    return values if values else None

            # DEBUG: Log which keys were tried but not found
            logger.debug(f"[Step6DCF] Tried keys {keys_to_try} for {field_name} but none found in df.index: {list(df_to_use.index)[:20]}...")

        return None

    def _process_dcf_market_data(
        self,
        market_data: Dict,
        user_overrides: Dict
    ) -> MarketDataDisplay:
        """Process DCF market data (6 fields)"""
        data_fields = []

        # Ensure market_data is a dict
        if not market_data:
            market_data = {}

        # DEBUG: Log what keys are actually in market_data
        logger.debug(f"[Step6DCF] market_data keys: {list(market_data.keys())[:30]}...")
        logger.debug(f"[Step6DCF] currentPrice={market_data.get('currentPrice')}, totalCash={market_data.get('totalCash')}, marketCap={market_data.get('marketCap')}")

        # DCF market data fields - handle both snake_case and camelCase keys
        market_fields = [
            ("current_stock_price", "Current Stock Price", True, ""),
            ("shares_outstanding", "Shares Outstanding", True, "shares"),
            ("market_cap", "Market Capitalization", True, "USD"),
            ("beta", "Beta", True, ""),
            ("total_debt", "Total Debt", True, "USD"),
            ("cash", "Cash & Cash Equivalents", True, "USD")
        ]

        for field_name, display_name, is_critical, unit in market_fields:
            # Try multiple key variations - expanded for yfinance v1.3.0+ compatibility
            value = None
            possible_keys = [
                field_name,  # snake_case: current_stock_price
                field_name.replace("_", ""),  # no underscore: currentstockprice
                "".join(word.capitalize() if i > 0 else word for i, word in enumerate(field_name.split("_"))),  # camelCase: currentStockPrice
            ]

            # Add yfinance v1.3.0+ specific key variations
            if field_name == "current_stock_price":
                possible_keys.extend(["currentPrice", "current_price", "price", "regularMarketPrice",
                                       "currentPriceRaw", "regularMarketPriceRaw"])
            elif field_name == "cash":
                possible_keys.extend(["totalCash", "total_cash", "cashAndEquivalents", "cash_and_equivalents",
                                       "CashAndCashEquivalents", "CashCashEquivalentsAndShortTermInvestments",
                                       "Cash Cash Equivalents And Short Term Investments",
                                       "totalCashRaw", "cashAndShortTermInvestments"])
            elif field_name == "total_debt":
                possible_keys.extend(["totalDebt", "total_debt", "debt", "TotalDebt",
                                       "total_debt_raw", "longTermDebt", "LongTermDebt",
                                       "long_term_debt", "shortLongTermDebtTotal"])
            elif field_name == "shares_outstanding":
                possible_keys.extend(["sharesOutstanding", "shares_outstanding", "OrdinarySharesNumber",
                                       "sharesOutstandingRaw", "impliedSharesOutstanding"])
            elif field_name == "market_cap":
                possible_keys.extend(["marketCap", "market_cap", "marketCapitalization", "marketCapRaw"])

            logger.debug(f"Looking for {field_name} with keys: {possible_keys}")

            for key in possible_keys:
                if key in market_data:
                    value = market_data[key]
                    logger.debug(f"Found {field_name} using key '{key}': {value}")
                    break

            # Also check if the value is nested in a dict with 'value' key (handle multiple levels)
            max_depth = 5
            current = value
            for _ in range(max_depth):
                if isinstance(current, dict) and 'value' in current:
                    current = current['value']
                else:
                    break
            value = current

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

        # Fetch Risk-Free Rate from 10Y Treasury (^TNX) via yfinance
        risk_free_rate = None
        risk_free_source = "yfinance"
        try:
            import yfinance as yf
            treasury = yf.Ticker("^TNX")
            treasury_hist = treasury.history(period="1d")
            if treasury_hist is not None and not treasury_hist.empty:
                rf_raw = treasury_hist['Close'].iloc[-1]
                risk_free_rate = rf_raw / 100  # yfinance returns as percentage (e.g. 4.25), convert to decimal
                risk_free_source = "yfinance (^TNX)"
                logger.info(f"[Step6DCF] Risk-Free Rate from ^TNX: {risk_free_rate:.4%}")
        except Exception as e:
            logger.warning(f"[Step6DCF] Failed to fetch risk-free rate from ^TNX: {e}")

        # Also try FRED as fallback
        if risk_free_rate is None:
            try:
                from app.services.international.fred_service import get_fred_service
                fred_service = get_fred_service()
                treasury_data = fred_service.get_10year_treasury_yield()
                if treasury_data and treasury_data.get('status') == 'RETRIEVED':
                    risk_free_rate = treasury_data.get('value')
                    if risk_free_rate is not None:
                        risk_free_rate = risk_free_rate / 100  # Convert from percentage to decimal
                        risk_free_source = "FRED"
                        logger.info(f"[Step6DCF] Risk-Free Rate from FRED: {risk_free_rate:.4%}")
            except Exception as e:
                logger.warning(f"[Step6DCF] Failed to fetch risk-free rate from FRED: {e}")

        # Add risk-free rate to data_fields
        rfr_status = DataStatus.RETRIEVED if risk_free_rate is not None else DataStatus.MISSING
        rfr_field = DataField(
            field_name="risk_free_rate",
            display_name="Risk-Free Rate",
            value=risk_free_rate,
            unit="%",
            status=rfr_status,
            source=risk_free_source,
            is_critical=True,
            allow_override=True
        )
        data_fields.append(rfr_field)

        # Fetch Equity Risk Premium (default 4.5% if not available)
        # ERP = Market Return - Risk-Free Rate; typical range 4-6%
        erp_value = 0.045  # 4.5% default
        erp_status = DataStatus.CALCULATED
        data_fields.append(DataField(
            field_name="equity_risk_premium",
            display_name="Equity Risk Premium",
            value=erp_value,
            unit="%",
            status=erp_status,
            source="estimated (historical average)",
            is_critical=True,
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

    async def _process_dcf_opening_balances(
        self,
        historical_data: Dict,
        user_overrides: Dict,
        ticker: str = "",
        sec_edgar_email: str = None
    ) -> ForecastDriversDisplay:
        """Process DCF opening balances (3 fields)"""
        # Get SEC EDGAR email using the standard priority chain:
        # 1. Explicit parameter (if provided)
        # 2. Request header (via SecEdgarService)
        # 3. Environment variable (via SecEdgarService)
        if not sec_edgar_email:
            from app.services.international.sec_edgar_service import SecEdgarService
            sec_edgar_email = SecEdgarService.get_email()
        data_fields = []

        # DCF opening balance fields - keys must match frontend expected keys
        # Balance Sheet identity items:
        #   Current Liabilities = Payables + Accrued Expenses + Other CL + Current Debt + Deferred Liabilities
        #   Non-Current Liabilities = LT Debt + Trade Payables NC + Other NC Liabilities
        #   Current Assets = Cash + ST Investments + Receivables + Inventory + Other CA
        #   Non-Current Assets = Net PPE + Accum Dep + Investments + Other NCA + Deferred Assets
        #   Equity = Common Stock + Retained Earnings + Other Equity Adjustments
        opening_fields = [
            ("net_debt_opening", "Net Debt", True, "USD"),
            ("ppe_gross", "PP&E (Gross)", True, "USD"),
            ("accumulated_depreciation", "Accumulated Depreciation", True, "USD"),
            ("non_current_marketable_securities", "Non-Current Marketable Securities", False, "USD"),
            ("other_current_liabilities", "Other Current Liabilities", False, "USD"),
            ("deferred_tax_liabilities", "Deferred Tax Liabilities", False, "USD"),
            # Current Liabilities sub-items (CL = Payables + Accrued + Other CL + Curr Debt + Deferred)
            ("current_accrued_expenses", "Current Accrued Expenses", False, "USD"),
            ("current_deferred_liabilities", "Current Deferred Liabilities", False, "USD"),
            # Non-Current Liabilities sub-items (NCL = LT Debt + Trade Payables NC + Other NC Liab)
            ("trade_and_other_payables_non_current", "Trade and Other Payables Non Current", False, "USD"),
            ("other_non_current_liabilities", "Other Non Current Liabilities", False, "USD"),
            # Current Assets sub-items (CA = Cash + ST Inv + Receivables + Inventory + Other CA)
            ("other_short_term_investments", "Other Short Term Investments", False, "USD"),
            ("other_current_assets", "Other Current Assets", False, "USD"),
            # Non-Current Assets sub-items (NCA = Net PPE + Accum Dep + Investments + Other NCA + Deferred)
            ("other_non_current_assets", "Other Non Current Assets", False, "USD"),
            # Equity sub-items (Equity = Common Stock + RE + Other Equity)
            ("common_stock", "Common Stock", False, "USD"),
            ("other_equity_adjustments", "Other Equity Adjustments", False, "USD"),
        ]

        balance_sheet_df = historical_data.get('balance_sheet')

        for field_name, display_name, is_critical, unit in opening_fields:
            value = None
            status = DataStatus.MISSING
            source = "yfinance"

            # Extract from balance sheet
            if balance_sheet_df is not None and not balance_sheet_df.empty:
                value = self._extract_opening_balance(field_name, balance_sheet_df, ticker=ticker, sec_edgar_email=sec_edgar_email)
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
        balance_sheet_df: pd.DataFrame,
        ticker: str = "",
        sec_edgar_email: str = None
    ) -> Optional[float]:
        """Extract opening balance from balance sheet.

        Handles:
        - net_debt_opening: Total Debt - Cash & Equivalents
        - ppe_gross: Property, Plant & Equipment (Gross) with yfinance-compatible key lookup
        - accumulated_depreciation: Accumulated Depreciation with yfinance-compatible key lookup
        """
        if balance_sheet_df is None or balance_sheet_df.empty:
            return None

        # Get most recent year's data (opening for forecast period)
        # DataFrame columns are sorted newest-first (2025, 2024, 2023, 2022, 2021)
        # So columns[0] is the latest, columns[-1] is the oldest
        latest_col = balance_sheet_df.columns[0]

        # Net Debt = Total Debt - Cash & Equivalents (calculated field)
        if field_name == "net_debt_opening":
            total_debt = None
            cash = None
            debt_keys = ["total_debt", "TotalDebt", "Debt",
                         "LongTermDebt", "LongTermDebtAndCapitalLeaseObligation",
                         "ShortLongTermDebt"]
            cash_keys = ["cash_and_equivalents", "CashCashEquivalentsAndShortTermInvestments",
                         "CashAndCashEquivalents", "CashCashEquivalents",
                         "Cash And Cash Equivalents", "Cash"]
            for key in debt_keys:
                if key in balance_sheet_df.index:
                    val = balance_sheet_df.loc[key, latest_col]
                    if pd.notna(val):
                        total_debt = float(val)
                        break
            for key in cash_keys:
                if key in balance_sheet_df.index:
                    val = balance_sheet_df.loc[key, latest_col]
                    if pd.notna(val):
                        cash = float(val)
                        break
            if total_debt is not None and cash is not None:
                return total_debt - cash
            elif total_debt is not None:
                return total_debt
            return None

        # PP&E Gross - try multiple yfinance key variants
        if field_name == "ppe_gross":
            # yfinance v1.3.0+ uses 'GrossPPE' (CamelCase no spaces)
            ppe_keys = ["ppe_gross", "GrossPPE", "Gross PPE",
                        "PropertyPlantAndEquipmentGross", "Properties",
                        "LandAndImprovements", "BuildingsAndImprovements",
                        "MachineryFurnitureEquipment",
                        "net_ppe", "NetPPE", "PropertyPlantAndEquipmentNet"]
            logger.info(f"[Step6DCF] Looking for ppe_gross in balance_sheet_df index (type={type(balance_sheet_df).__name__}, empty={balance_sheet_df.empty if hasattr(balance_sheet_df, 'empty') else 'N/A'})")
            logger.info(f"[Step6DCF] Balance sheet index sample: {list(balance_sheet_df.index)[:10] if hasattr(balance_sheet_df, 'index') else 'N/A'}")
            for key in ppe_keys:
                if key in balance_sheet_df.index:
                    val = balance_sheet_df.loc[key, latest_col]
                    if pd.notna(val):
                        logger.info(f"[Step6DCF] Found ppe_gross via key '{key}': {val:,.0f}")
                        return float(val)
            logger.warning(f"[Step6DCF] ppe_gross NOT FOUND in balance_sheet_df. Tried keys: {ppe_keys[:5]}...")
            # Fallback: try SEC EDGAR XBRL for Gross PP&E (synchronous)
            if sec_edgar_email:
                try:
                    import requests as sync_requests
                    # First get CIK from ticker
                    search_url = f"https://efts.sec.gov/LATEST/search-index?q={ticker}&dateRange=custom&startdt=2020-01-01&forms=10-K"
                    headers = {"User-Agent": f"ValuationPlatform {sec_edgar_email}", "Accept": "application/json"}
                    # Use company facts endpoint directly
                    # Need CIK first - use SEC EDGAR company search
                    cik_url = f"https://efts.sec.gov/LATEST/search-index?q=%22{ticker}%22&dateRange=custom&forms=10-K"
                    # Simpler: use the company tickers endpoint
                    tickers_url = "https://www.sec.gov/files/company_tickers.json"
                    resp = sync_requests.get(tickers_url, headers=headers, timeout=10)
                    if resp.status_code == 200:
                        tickers_data = resp.json()
                        cik = None
                        for key, info in tickers_data.items():
                            if info.get("ticker") == ticker:
                                cik = str(info["cik_str"]).zfill(10)
                                break
                        if cik:
                            facts_url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
                            facts_resp = sync_requests.get(facts_url, headers=headers, timeout=15)
                            if facts_resp.status_code == 200:
                                facts_data = facts_resp.json()
                                us_gaap = facts_data.get("facts", {}).get("us-gaap", {})
                                ppe_raw = us_gaap.get("PropertyPlantAndEquipmentGross", {}).get("units", {}).get("USD", [])
                                # Get latest value per fiscal year
                                ppe_yearly = {}
                                for item in ppe_raw:
                                    fy = item.get("fy")
                                    if fy and item.get("val") is not None:
                                        end = item.get("end", "")
                                        if fy not in ppe_yearly or end > ppe_yearly[fy].get("end", ""):
                                            ppe_yearly[fy] = {"value": item["val"], "end": end}
                                if ppe_yearly:
                                    latest = max(ppe_yearly.keys())
                                    logger.info(f"SEC EDGAR: Got PP&E Gross for {ticker}: ${ppe_yearly[latest]['value']:,.0f}")
                                    return float(ppe_yearly[latest]["value"])
                except Exception as e:
                    logger.warning(f"SEC EDGAR PP&E Gross fetch failed for {ticker}: {e}")
            return None

        # Accumulated Depreciation - try multiple yfinance key variants (multi-year)
        if field_name == "accumulated_depreciation":
            acc_dep_keys = ["accumulated_depreciation", "AccumulatedDepreciation",
                            "Accumulated Depreciation", "accumulated_amortization",
                            "Allowances", "allowances"]
            for key in acc_dep_keys:
                if key in balance_sheet_df.index:
                    # Read ALL periods, not just latest
                    values = []
                    for col in balance_sheet_df.columns:
                        val = balance_sheet_df.loc[key, col]
                        if pd.notna(val):
                            values.append(float(val))
                    if values:
                        return values
            # Fallback: try SEC EDGAR XBRL for Accumulated Depreciation (synchronous)
            if sec_edgar_email:
                try:
                    import requests as sync_requests
                    # Get CIK from company tickers endpoint
                    tickers_url = "https://www.sec.gov/files/company_tickers.json"
                    headers = {"User-Agent": f"ValuationPlatform {sec_edgar_email}", "Accept": "application/json"}
                    resp = sync_requests.get(tickers_url, headers=headers, timeout=10)
                    if resp.status_code == 200:
                        tickers_data = resp.json()
                        cik = None
                        for key, info in tickers_data.items():
                            if info.get("ticker") == ticker:
                                cik = str(info["cik_str"]).zfill(10)
                                break
                        if cik:
                            facts_url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
                            facts_resp = sync_requests.get(facts_url, headers=headers, timeout=15)
                            if facts_resp.status_code == 200:
                                facts_data = facts_resp.json()
                                us_gaap = facts_data.get("facts", {}).get("us-gaap", {})
                                acc_raw = us_gaap.get("PropertyPlantAndEquipmentAccumulatedDepreciation", {}).get("units", {}).get("USD", [])
                                acc_yearly = {}
                                for item in acc_raw:
                                    fy = item.get("fy")
                                    if fy and item.get("val") is not None:
                                        end = item.get("end", "")
                                        if fy not in acc_yearly or end > acc_yearly[fy].get("end", ""):
                                            acc_yearly[fy] = {"value": item["val"], "end": end}
                                if acc_yearly:
                                    # Return ALL years, sorted
                                    all_vals = [acc_yearly[y]["value"] for y in sorted(acc_yearly.keys())]
                                    logger.info(f"SEC EDGAR: Got Accumulated Depreciation for {ticker}: {len(all_vals)} years")
                                    return all_vals
                except Exception as e:
                    logger.warning(f"SEC EDGAR Accumulated Depreciation fetch failed for {ticker}: {e}")
            return None

        # Generic fallback for other opening balance fields
        # Maps field_name to list of yfinance DataFrame index keys to try
        generic_keys = {
            "opening_net_working_capital": ["working_capital", "WorkingCapital", "Net Working Capital",
                                             "TotalCurrentAssets", "Total Current Assets"],
            "opening_net_ppe": ["net_ppe", "NetPPE", "Net PPE", "PropertyPlantAndEquipmentNet",
                                "Property Plant And Equipment Net", "Net Property Plant And Equipment"],
            "opening_total_debt": ["total_debt", "TotalDebt", "Long Term Debt",
                                   "LongTermDebt", "Short Long Term Debt Total"],
            "non_current_marketable_securities": ["non_current_marketable_securities", "NonCurrentMarketableSecurities",
                                                  "LongTermInvestments", "Other Long Term Investments",
                                                  "AvailableForSaleSecurities"],
            "other_current_liabilities": ["other_current_liabilities", "OtherCurrentLiabilities",
                                          "Other Current Liabilities"],
            "deferred_tax_liabilities": ["deferred_tax_liabilities", "DeferredTaxLiabilities",
                                         "NonCurrentDeferredTaxesLiabilities",
                                         "Non Current Deferred Taxes Liabilities"],
            "current_accrued_expenses": ["current_accrued_expenses", "CurrentAccruedExpenses",
                                         "PayablesAndAccruedExpenses", "Payables And Accrued Expenses"],
            "current_deferred_liabilities": ["current_deferred_liabilities", "CurrentDeferredRevenue",
                                             "DeferredRevenueCurrent", "Current Deferred Revenue"],
            "trade_and_other_payables_non_current": ["trade_and_other_payables_non_current",
                                                     "NonCurrentPayables", "Non Current Payables"],
            "other_non_current_liabilities": ["other_non_current_liabilities", "OtherNonCurrentLiabilities",
                                              "Other Non Current Liabilities"],
            "other_short_term_investments": ["other_short_term_investments", "OtherShortTermInvestments",
                                             "AvailableForSaleSecurities", "ShortTermInvestments"],
            "other_current_assets": ["other_current_assets", "OtherCurrentAssets",
                                     "Other Current Assets"],
            "other_non_current_assets": ["other_non_current_assets", "OtherNonCurrentAssets",
                                         "Other Non Current Assets"],
            "common_stock": ["common_stock", "CommonStockEquity", "Common Stock Equity",
                             "CommonStock", "Common Stock"],
            "other_equity_adjustments": ["other_equity_adjustments", "OtherEquityAdjustments",
                                         "AccumulatedOtherComprehensiveIncome", "AOCI", "TreasuryStock"],
        }

        for key in generic_keys.get(field_name, [field_name]):
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

        # Get peer list - try multiple possible keys
        peers = retrieved_assumptions.get('peers', [])

        # If no peers found directly, check for nested structure
        if not peers and 'peer_data' in retrieved_assumptions:
            peers = retrieved_assumptions['peer_data'].get('peers', [])

        # Lazy-init yfinance service for fetching missing peer data
        yf_service = None

        for peer_ticker in peers:
            # Try multiple key patterns for peer info
            peer_info = None
            possible_keys = [
                f"peer_{peer_ticker}_info",
                f"peer_{peer_ticker}",
                f"{peer_ticker}_info",
                peer_ticker
            ]

            for key in possible_keys:
                if key in retrieved_assumptions:
                    peer_info = retrieved_assumptions[key]
                    break

            # Also check nested in peer_data
            if not peer_info and 'peer_data' in retrieved_assumptions:
                for key in possible_keys:
                    if key in retrieved_assumptions['peer_data']:
                        peer_info = retrieved_assumptions['peer_data'][key]
                        break

            # Also check peer_market_data (populated by Step 4 peer management service)
            if not peer_info and 'peer_market_data' in retrieved_assumptions:
                peer_market_data = retrieved_assumptions['peer_market_data']
                if peer_ticker in peer_market_data:
                    peer_info = peer_market_data[peer_ticker]

            # Note: peer_info may not have multiples if session data is stale
            # The key mapping fix (enterpriseToEbitda → evEbitda) handles the case
            # where multiples ARE present but with yfinance key names

            if peer_info:
                # Helper to get value with multiple key fallbacks (metric IDs + yfinance keys)
                def _peer_val(keys, default=None):
                    for k in keys:
                        v = peer_info.get(k)
                        if v is not None:
                            return v
                    return default

                mc = _peer_val(['market_cap', 'marketCap', 'marketCapitalization'])
                ev = _peer_val(['enterprise_value', 'enterpriseValue'])
                ebitda_val = _peer_val(['ebitda'])
                revenue_val = _peer_val(['revenue', 'total_revenue', 'totalRevenue'])
                eps_val = _peer_val(['eps', 'trailingEps', 'diluted_eps'])
                price_val = _peer_val(['current_price', 'currentPrice', 'price'])
                bvps = _peer_val(['book_value', 'bookValue', 'book_value_per_share'])
                beta_val = _peer_val(['beta'])
                debt_val = _peer_val(['total_debt', 'totalDebt'])
                cash_val = _peer_val(['cash_and_equivalents', 'cash', 'totalCash', 'CashAndCashEquivalents',
                                       'CashCashEquivalentsAndShortTermInvestments',
                                       'Cash And Cash Equivalents', 'cashAndShortTermInvestments'])
                tax_val = _peer_val(['effective_tax_rate', 'effectiveTaxRate', 'tax_rate',
                                      'taxRate', 'incomeTaxExpense', 'taxProvision'])
                # If tax_rate not directly available, compute from tax_provision / pretax_income
                if tax_val is None:
                    tax_prov = _peer_val(['tax_provision', 'TaxProvision', 'IncomeTaxExpense',
                                           'incomeTaxExpense', 'income_tax_expense'])
                    pretax = _peer_val(['pretax_income', 'PretaxIncome', 'incomeBeforeTax',
                                        'IncomeBeforeTax', 'income_before_tax'])
                    if tax_prov is not None and pretax is not None and pretax != 0:
                        tax_val = abs(tax_prov) / abs(pretax)
                cod_val = _peer_val(['cost_of_debt', 'costOfDebt'])

                # Compute EV if not available: Market Cap + Total Debt - Cash
                if ev is None and mc is not None:
                    d = debt_val or 0
                    c = cash_val or 0
                    ev = mc + d - c

                # Compute multiples from raw data
                ev_ebitda = None
                if ev and ebitda_val and ebitda_val > 0:
                    ev_ebitda = ev / ebitda_val

                pe_ratio = None
                if price_val and eps_val and eps_val > 0:
                    pe_ratio = price_val / eps_val

                ev_revenue = None
                if ev and revenue_val and revenue_val > 0:
                    ev_revenue = ev / revenue_val

                pb_ratio = None
                if price_val and bvps and bvps > 0:
                    pb_ratio = price_val / bvps

                company = PeerCompany(
                    ticker=peer_ticker,
                    name=_peer_val(['name', 'longName', 'shortName', 'company_name'], peer_ticker),
                    market_cap=mc,
                    enterprise_value=ev,
                    ev_ebitda=ev_ebitda,
                    pe_ratio=pe_ratio,
                    ev_revenue=ev_revenue,
                    pb_ratio=pb_ratio,
                    beta=beta_val,
                    total_debt=debt_val,
                    cash=cash_val,
                    tax_rate=tax_val,
                    cost_of_debt=cod_val
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

        # Calculate historical growth rates from historical data
        # These are intermediate calculations, NOT WACC/TV/Fair Value

        # 1. Revenue CAGR (3-year and 4-year if available)
        revenue_fields = [f for f in historical_display.data_fields if f.field_name == "revenue"]
        if revenue_fields and revenue_fields[0].value:
            revenue_data = revenue_fields[0].value
            # Check if revenue_data is a list/array with multiple years
            if isinstance(revenue_data, list) and len(revenue_data) >= 2:
                # Calculate CAGR
                n_years = len(revenue_data) - 1
                if revenue_data[-1] and revenue_data[0] and revenue_data[-1] > 0 and revenue_data[0] > 0:
                    cagr = ((revenue_data[-1] / revenue_data[0]) ** (1 / n_years)) - 1
                    data_fields.append(DataField(
                        field_name="revenue_cagr",
                        display_name=f"Revenue CAGR ({n_years}-year)",
                        value=cagr * 100,
                        unit="%",
                        status=DataStatus.CALCULATED,
                        source="calculated_from_historical",
                        formula=f"((Ending Revenue / Beginning Revenue) ^ (1/{n_years})) - 1",
                        is_critical=False,
                        allow_override=True
                    ))

        # 2. EBITDA CAGR
        ebitda_fields = [f for f in historical_display.data_fields if f.field_name == "ebitda"]
        if ebitda_fields and ebitda_fields[0].value:
            ebitda_data = ebitda_fields[0].value
            if isinstance(ebitda_data, list) and len(ebitda_data) >= 2:
                n_years = len(ebitda_data) - 1
                if ebitda_data[-1] and ebitda_data[0] and ebitda_data[-1] > 0 and ebitda_data[0] > 0:
                    ebitda_cagr = ((ebitda_data[-1] / ebitda_data[0]) ** (1 / n_years)) - 1
                    data_fields.append(DataField(
                        field_name="ebitda_cagr",
                        display_name=f"EBITDA CAGR ({n_years}-year)",
                        value=ebitda_cagr * 100,
                        unit="%",
                        status=DataStatus.CALCULATED,
                        source="calculated_from_historical",
                        formula=f"((Ending EBITDA / Beginning EBITDA) ^ (1/{n_years})) - 1",
                        is_critical=False,
                        allow_override=True
                    ))

        # 3. Net Income CAGR
        ni_fields = [f for f in historical_display.data_fields if f.field_name == "net_income"]
        if ni_fields and ni_fields[0].value:
            ni_data = ni_fields[0].value
            if isinstance(ni_data, list) and len(ni_data) >= 2:
                n_years = len(ni_data) - 1
                if ni_data[-1] and ni_data[0]:
                    # Handle negative net income
                    if ni_data[-1] > 0 and ni_data[0] > 0:
                        ni_cagr = ((ni_data[-1] / ni_data[0]) ** (1 / n_years)) - 1
                        data_fields.append(DataField(
                            field_name="net_income_cagr",
                            display_name=f"Net Income CAGR ({n_years}-year)",
                            value=ni_cagr * 100,
                            unit="%",
                            status=DataStatus.CALCULATED,
                            source="calculated_from_historical",
                            formula=f"((Ending NI / Beginning NI) ^ (1/{n_years})) - 1",
                            is_critical=False,
                            allow_override=True
                        ))

        # 4. Historical margins - BOTH latest AND average across all years
        margin_fields = ["gross_margin", "operating_margin", "net_margin"]
        for margin in margin_fields:
            field = next((f for f in historical_display.data_fields if f.field_name == margin), None)
            if field and field.value is not None:
                margin_value = field.value
                if isinstance(margin_value, list) and len(margin_value) > 0:
                    # Latest year
                    latest = margin_value[-1]
                    data_fields.append(DataField(
                        field_name=f"historical_{margin}",
                        display_name=f"Latest {field.display_name}",
                        value=latest,
                        unit="%",
                        status=DataStatus.CALCULATED,
                        source="calculated_from_historical",
                        is_critical=False,
                        allow_override=True
                    ))
                    # Average across all years (excluding None)
                    valid_margins = [v for v in margin_value if v is not None]
                    if valid_margins:
                        avg_margin = sum(valid_margins) / len(valid_margins)
                        data_fields.append(DataField(
                            field_name=f"avg_{margin}",
                            display_name=f"Average {field.display_name} ({len(valid_margins)}-year)",
                            value=avg_margin,
                            unit="%",
                            status=DataStatus.CALCULATED,
                            source="calculated_from_historical",
                            formula=f"Average of {len(valid_margins)} years of {field.display_name}",
                            is_critical=False,
                            allow_override=True
                        ))
                elif margin_value is not None:
                    # Single value
                    data_fields.append(DataField(
                        field_name=f"historical_{margin}",
                        display_name=f"Latest {field.display_name}",
                        value=margin_value,
                        unit="%",
                        status=DataStatus.CALCULATED,
                        source="calculated_from_historical",
                        is_critical=False,
                        allow_override=True
                    ))

        # 5. FCF Conversion Rate (FCF / EBITDA) - latest year
        fcf_fields = [f for f in historical_display.data_fields if f.field_name == "free_cash_flow"]
        if fcf_fields and fcf_fields[0].value and ebitda_fields and ebitda_fields[0].value:
            fcf_data = fcf_fields[0].value
            ebitda_data = ebitda_fields[0].value

            if isinstance(fcf_data, list):
                fcf_data = fcf_data[-1]
            if isinstance(ebitda_data, list):
                ebitda_data = ebitda_data[-1]

            if fcf_data and ebitda_data and ebitda_data > 0:
                fcf_conversion = fcf_data / ebitda_data
                data_fields.append(DataField(
                    field_name="fcf_conversion_rate",
                    display_name="FCF Conversion Rate (FCF/EBITDA)",
                    value=fcf_conversion * 100,
                    unit="%",
                    status=DataStatus.CALCULATED,
                    source="calculated_from_historical",
                    formula="Free Cash Flow / EBITDA",
                    is_critical=False,
                    allow_override=True
                ))

        # 6. Revenue Year-over-Year Growth Rates
        if revenue_fields and revenue_fields[0].value:
            revenue_data = revenue_fields[0].value
            if isinstance(revenue_data, list) and len(revenue_data) >= 2:
                yoy_growth_rates = []
                for i in range(1, len(revenue_data)):
                    if revenue_data[i] is not None and revenue_data[i-1] is not None and revenue_data[i-1] > 0:
                        growth = ((revenue_data[i] - revenue_data[i-1]) / abs(revenue_data[i-1])) * 100
                        yoy_growth_rates.append(growth)
                    else:
                        yoy_growth_rates.append(None)
                if yoy_growth_rates:
                    valid_rates = [r for r in yoy_growth_rates if r is not None]
                    if valid_rates:
                        data_fields.append(DataField(
                            field_name="revenue_yoy_growth",
                            display_name="Revenue YoY Growth Rates",
                            value=yoy_growth_rates,
                            unit="%",
                            status=DataStatus.CALCULATED,
                            source="calculated_from_historical",
                            formula="((Current Year - Prior Year) / Prior Year) * 100",
                            is_critical=False,
                            allow_override=True
                        ))
                        # Average YoY growth
                        avg_growth = sum(valid_rates) / len(valid_rates)
                        data_fields.append(DataField(
                            field_name="avg_revenue_growth",
                            display_name=f"Average Revenue Growth ({len(valid_rates)}-year)",
                            value=avg_growth,
                            unit="%",
                            status=DataStatus.CALCULATED,
                            source="calculated_from_historical",
                            formula=f"Average of {len(valid_rates)} years of YoY revenue growth",
                            is_critical=False,
                            allow_override=True
                        ))

        # 7. Working Capital Days (AR Days, Inventory Days, AP Days)
        ar_fields = [f for f in historical_display.data_fields if f.field_name == "accounts_receivable"]
        inv_fields = [f for f in historical_display.data_fields if f.field_name == "inventory"]
        ap_fields = [f for f in historical_display.data_fields if f.field_name == "accounts_payable"]

        if revenue_fields and revenue_fields[0].value:
            revenue_data = revenue_fields[0].value
            if isinstance(revenue_data, list):
                # AR Days = (Accounts Receivable / Revenue) * 365
                if ar_fields and ar_fields[0].value:
                    ar_data = ar_fields[0].value
                    if isinstance(ar_data, list) and len(ar_data) == len(revenue_data):
                        ar_days_list = []
                        for i in range(len(ar_data)):
                            if ar_data[i] is not None and revenue_data[i] is not None and revenue_data[i] > 0:
                                ar_days_list.append((ar_data[i] / revenue_data[i]) * 365)
                            else:
                                ar_days_list.append(None)
                        valid_ar_days = [d for d in ar_days_list if d is not None]
                        if valid_ar_days:
                            data_fields.append(DataField(
                                field_name="ar_days",
                                display_name=f"Average AR Days ({len(valid_ar_days)}-year)",
                                value=sum(valid_ar_days) / len(valid_ar_days),
                                unit="days",
                                status=DataStatus.CALCULATED,
                                source="calculated_from_historical",
                                formula="(Accounts Receivable / Revenue) * 365",
                                is_critical=False,
                                allow_override=True
                            ))

                # Inventory Days = (Inventory / COGS) * 365
                cogs_fields = [f for f in historical_display.data_fields if f.field_name == "cogs"]
                if inv_fields and inv_fields[0].value and cogs_fields and cogs_fields[0].value:
                    inv_data = inv_fields[0].value
                    cogs_data = cogs_fields[0].value
                    if isinstance(inv_data, list) and isinstance(cogs_data, list):
                        inv_days_list = []
                        for i in range(min(len(inv_data), len(cogs_data))):
                            if inv_data[i] is not None and cogs_data[i] is not None and cogs_data[i] > 0:
                                inv_days_list.append((inv_data[i] / cogs_data[i]) * 365)
                            else:
                                inv_days_list.append(None)
                        valid_inv_days = [d for d in inv_days_list if d is not None]
                        if valid_inv_days:
                            data_fields.append(DataField(
                                field_name="inv_days",
                                display_name=f"Average Inventory Days ({len(valid_inv_days)}-year)",
                                value=sum(valid_inv_days) / len(valid_inv_days),
                                unit="days",
                                status=DataStatus.CALCULATED,
                                source="calculated_from_historical",
                                formula="(Inventory / COGS) * 365",
                                is_critical=False,
                                allow_override=True
                            ))

                # AP Days = (Accounts Payable / COGS) * 365
                if ap_fields and ap_fields[0].value and cogs_fields and cogs_fields[0].value:
                    ap_data = ap_fields[0].value
                    cogs_data = cogs_fields[0].value
                    if isinstance(ap_data, list) and isinstance(cogs_data, list):
                        ap_days_list = []
                        for i in range(min(len(ap_data), len(cogs_data))):
                            if ap_data[i] is not None and cogs_data[i] is not None and cogs_data[i] > 0:
                                ap_days_list.append((ap_data[i] / cogs_data[i]) * 365)
                            else:
                                ap_days_list.append(None)
                        valid_ap_days = [d for d in ap_days_list if d is not None]
                        if valid_ap_days:
                            data_fields.append(DataField(
                                field_name="ap_days",
                                display_name=f"Average AP Days ({len(valid_ap_days)}-year)",
                                value=sum(valid_ap_days) / len(valid_ap_days),
                                unit="days",
                                status=DataStatus.CALCULATED,
                                source="calculated_from_historical",
                                formula="(Accounts Payable / COGS) * 365",
                                is_critical=False,
                                allow_override=True
                            ))

        # 6. Peer Comparables - Median & Mean Metrics for WACC
        if peer_display and peer_display.companies:
            companies = peer_display.companies

            # Calculate median and mean for Beta
            betas = [c.beta for c in companies if c.beta is not None]
            if betas:
                median_beta = self._calculate_median(betas)
                mean_beta = sum(betas) / len(betas)

                data_fields.append(DataField(
                    field_name="peer_median_beta",
                    display_name="Peer Median Beta",
                    value=median_beta,
                    unit="",
                    status=DataStatus.CALCULATED,
                    source="calculated_from_peers",
                    formula="Median of peer betas",
                    is_critical=True,
                    allow_override=True
                ))

                data_fields.append(DataField(
                    field_name="peer_mean_beta",
                    display_name="Peer Mean Beta",
                    value=mean_beta,
                    unit="",
                    status=DataStatus.CALCULATED,
                    source="calculated_from_peers",
                    formula="Average of peer betas",
                    is_critical=False,
                    allow_override=True
                ))

            # Calculate median EV/EBITDA for terminal value reference
            ev_ebitdas = [c.ev_ebitda for c in companies if c.ev_ebitda is not None]
            if ev_ebitdas:
                median_ev_ebitda = self._calculate_median(ev_ebitdas)
                mean_ev_ebitda = sum(ev_ebitdas) / len(ev_ebitdas)

                data_fields.append(DataField(
                    field_name="peer_median_ev_ebitda",
                    display_name="Peer Median EV/EBITDA",
                    value=median_ev_ebitda,
                    unit="x",
                    status=DataStatus.CALCULATED,
                    source="calculated_from_peers",
                    formula="Median of peer EV/EBITDA multiples",
                    is_critical=False,
                    allow_override=True
                ))

                data_fields.append(DataField(
                    field_name="peer_mean_ev_ebitda",
                    display_name="Peer Mean EV/EBITDA",
                    value=mean_ev_ebitda,
                    unit="x",
                    status=DataStatus.CALCULATED,
                    source="calculated_from_peers",
                    formula="Average of peer EV/EBITDA multiples",
                    is_critical=False,
                    allow_override=True
                ))

            # Calculate median P/E
            pe_ratios = [c.pe_ratio for c in companies if c.pe_ratio is not None]
            if pe_ratios:
                median_pe = self._calculate_median(pe_ratios)
                data_fields.append(DataField(
                    field_name="peer_median_pe",
                    display_name="Peer Median P/E",
                    value=median_pe,
                    unit="x",
                    status=DataStatus.CALCULATED,
                    source="calculated_from_peers",
                    formula="Median of peer P/E ratios",
                    is_critical=False,
                    allow_override=True
                ))

            # Calculate median EV/Revenue
            ev_revenues = [c.ev_revenue for c in companies if c.ev_revenue is not None]
            if ev_revenues:
                median_ev_revenue = self._calculate_median(ev_revenues)
                data_fields.append(DataField(
                    field_name="peer_median_ev_revenue",
                    display_name="Peer Median EV/Revenue",
                    value=median_ev_revenue,
                    unit="x",
                    status=DataStatus.CALCULATED,
                    source="calculated_from_peers",
                    formula="Median of peer EV/Revenue multiples",
                    is_critical=False,
                    allow_override=True
                ))

            # Calculate average tax rate from peers with outlier detection
            tax_rates = [c.tax_rate for c in companies if c.tax_rate is not None and 0 <= c.tax_rate <= 0.50]
            if tax_rates:
                avg_tax_rate = sum(tax_rates) / len(tax_rates)
                data_fields.append(DataField(
                    field_name="peer_avg_tax_rate",
                    display_name="Peer Average Tax Rate",
                    value=avg_tax_rate * 100 if avg_tax_rate <= 1 else avg_tax_rate,
                    unit="%",
                    status=DataStatus.CALCULATED,
                    source="calculated_from_peers",
                    formula="Average of peer effective tax rates (capped 0-50%)",
                    is_critical=True,
                    allow_override=True
                ))

            # Calculate average cost of debt from peers with outlier detection
            cost_of_debts = [c.cost_of_debt for c in companies if c.cost_of_debt is not None and 0 <= c.cost_of_debt <= 0.20]
            if cost_of_debts:
                avg_cost_of_debt = sum(cost_of_debts) / len(cost_of_debts)
                data_fields.append(DataField(
                    field_name="peer_avg_cost_of_debt",
                    display_name="Peer Average Cost of Debt",
                    value=avg_cost_of_debt * 100 if avg_cost_of_debt <= 1 else avg_cost_of_debt,
                    unit="%",
                    status=DataStatus.CALCULATED,
                    source="calculated_from_peers",
                    formula="Average of peer cost of debt (capped 0-20%)",
                    is_critical=True,
                    allow_override=True
                ))

            # Calculate D/E Ratio, Unlevered Beta, and Cost of Debt per peer
            de_ratios = []
            unlevered_betas = []
            cost_of_debts_from_peer = []
            for c in companies:
                # D/E Ratio = Total Debt / Market Cap (equity)
                if c.total_debt is not None and c.market_cap is not None and c.market_cap > 0:
                    de_ratio = c.total_debt / c.market_cap
                    c._de_ratio = de_ratio  # Store for unlevered beta calculation
                    de_ratios.append(de_ratio)
                # Unlevered Beta = Levered Beta / (1 + (1 - Tax Rate) × D/E)
                if c.beta is not None and hasattr(c, '_de_ratio') and c.tax_rate is not None:
                    tax_rate = c.tax_rate if c.tax_rate <= 1 else c.tax_rate / 100
                    unlevered_beta = c.beta / (1 + (1 - tax_rate) * c._de_ratio)
                    unlevered_betas.append(unlevered_beta)
                # Cost of Debt = Interest Expense / Total Debt (estimated from yield)
                if c.total_debt is not None and c.total_debt > 0 and c.cost_of_debt is None:
                    # If cost_of_debt not directly available, estimate from market data
                    # This is a fallback - yfinance doesn't always provide this
                    pass

            if de_ratios:
                median_de = self._calculate_median(de_ratios)
                avg_de = sum(de_ratios) / len(de_ratios)
                data_fields.append(DataField(
                    field_name="peer_median_de_ratio",
                    display_name="Peer Median D/E Ratio",
                    value=median_de,
                    unit="x",
                    status=DataStatus.CALCULATED,
                    source="calculated_from_peers",
                    formula="Median of peer Debt/Equity ratios (Total Debt / Market Cap)",
                    is_critical=True,
                    allow_override=True
                ))
                data_fields.append(DataField(
                    field_name="peer_mean_de_ratio",
                    display_name="Peer Mean D/E Ratio",
                    value=avg_de,
                    unit="x",
                    status=DataStatus.CALCULATED,
                    source="calculated_from_peers",
                    formula="Average of peer Debt/Equity ratios",
                    is_critical=False,
                    allow_override=True
                ))

            if unlevered_betas:
                median_unlevered_beta = self._calculate_median(unlevered_betas)
                avg_unlevered_beta = sum(unlevered_betas) / len(unlevered_betas)
                data_fields.append(DataField(
                    field_name="peer_median_unlevered_beta",
                    display_name="Peer Median Unlevered Beta",
                    value=median_unlevered_beta,
                    unit="",
                    status=DataStatus.CALCULATED,
                    source="calculated_from_peers",
                    formula="Median of Levered Beta / (1 + (1-Tax) × D/E)",
                    is_critical=True,
                    allow_override=True
                ))
                data_fields.append(DataField(
                    field_name="peer_mean_unlevered_beta",
                    display_name="Peer Mean Unlevered Beta",
                    value=avg_unlevered_beta,
                    unit="",
                    status=DataStatus.CALCULATED,
                    source="calculated_from_peers",
                    formula="Average of Levered Beta / (1 + (1-Tax) × D/E)",
                    is_critical=False,
                    allow_override=True
                ))

            # Calculate average market cap and enterprise value for sizing context
            market_caps = [c.market_cap for c in companies if c.market_cap is not None]
            if market_caps:
                median_market_cap = self._calculate_median(market_caps)
                data_fields.append(DataField(
                    field_name="peer_median_market_cap",
                    display_name="Peer Median Market Cap",
                    value=median_market_cap,
                    unit="USD",
                    status=DataStatus.CALCULATED,
                    source="calculated_from_peers",
                    formula="Median of peer market capitalizations",
                    is_critical=False,
                    allow_override=True
                ))

        # 7. CapEx as % of Revenue and CapEx as % of D&A (forecasting drivers)
        capex_fields = [f for f in historical_display.data_fields if f.field_name == "capex"]
        if capex_fields and capex_fields[0].value and revenue_fields and revenue_fields[0].value:
            capex_data = capex_fields[0].value
            rev_data = revenue_fields[0].value
            if isinstance(capex_data, list) and isinstance(rev_data, list):
                capex_rev_ratios = []
                for i in range(min(len(capex_data), len(rev_data))):
                    if capex_data[i] is not None and rev_data[i] is not None and rev_data[i] > 0:
                        capex_rev_ratios.append((abs(capex_data[i]) / rev_data[i]) * 100)
                    else:
                        capex_rev_ratios.append(None)
                valid_ratios = [r for r in capex_rev_ratios if r is not None]
                if valid_ratios:
                    avg_capex_rev = sum(valid_ratios) / len(valid_ratios)
                    data_fields.append(DataField(
                        field_name="capex_pct_of_revenue",
                        display_name=f"Average CapEx % of Revenue ({len(valid_ratios)}-year)",
                        value=avg_capex_rev,
                        unit="%",
                        status=DataStatus.CALCULATED,
                        source="calculated_from_historical",
                        formula="(|CapEx| / Revenue) × 100",
                        is_critical=False,
                        allow_override=True
                    ))

        if capex_fields and capex_fields[0].value:
            capex_data = capex_fields[0].value
            da_fields = [f for f in historical_display.data_fields if f.field_name == "depreciation_amortization" or f.field_name == "depreciation"]
            if da_fields and da_fields[0].value:
                da_data = da_fields[0].value
                if isinstance(capex_data, list) and isinstance(da_data, list):
                    capex_da_ratios = []
                    for i in range(min(len(capex_data), len(da_data))):
                        if capex_data[i] is not None and da_data[i] is not None and da_data[i] > 0:
                            capex_da_ratios.append((abs(capex_data[i]) / da_data[i]) * 100)
                        else:
                            capex_da_ratios.append(None)
                    valid_da_ratios = [r for r in capex_da_ratios if r is not None]
                    if valid_da_ratios:
                        avg_capex_da = sum(valid_da_ratios) / len(valid_da_ratios)
                        data_fields.append(DataField(
                            field_name="capex_pct_of_da",
                            display_name=f"Average CapEx % of D&A ({len(valid_da_ratios)}-year)",
                            value=avg_capex_da,
                            unit="%",
                            status=DataStatus.CALCULATED,
                            source="calculated_from_historical",
                            formula="(|CapEx| / Depreciation & Amortization) × 100",
                            is_critical=False,
                            allow_override=True
                        ))

        return CalculatedMetricsDisplay(data_fields=data_fields)

    def _ensure_mandatory_placeholders(self, response_obj: DCFDataReviewResponse):
        """
        Verifies that explicit mandatory lines exist as tracked properties
        so that models cannot execute projections blindly without them.
        Enforces existence of critical valuation anchors: CapEx, Operating Cash Flow, Risk-Free Rate.
        """
        hist = response_obj.historical_financials
        mkt = response_obj.market_data

        if not hist or not hist.data_fields:
            return

        if not mkt or not mkt.data_fields:
            return

        # Explicit CapEx check (Critical for calculating accurate reinvestment paths)
        capex_keys = ["capex", "capitalExpenditure", "capital_expenditure"]
        has_capex = any(f.field_name in capex_keys for f in hist.data_fields if f.value is not None)
        if not has_capex:
            hist.data_fields.append(DataField(
                field_name="capitalExpenditure",
                display_name="Capital Expenditure",
                value=None,
                status=DataStatus.MISSING,
                unit="USD",
                source="validation_check",
                is_critical=True,
                allow_override=True
            ))

        # Explicit Operating Cash Flow check (Critical for tracing Free Cash Flow to Firm)
        ocf_keys = ["operating_cash_flow", "operatingCashFlow", "ocf"]
        has_ocf = any(f.field_name in ocf_keys for f in hist.data_fields if f.value is not None)
        if not has_ocf:
            hist.data_fields.append(DataField(
                field_name="operatingCashFlow",
                display_name="Operating Cash Flow",
                value=None,
                status=DataStatus.MISSING,
                unit="USD",
                source="validation_check",
                is_critical=True,
                allow_override=True
            ))

        # Explicit Risk-Free Rate check (Critical for Cost of Equity / WACC parameters)
        rfr_keys = ["risk_free_rate", "riskFreeRate", "rfr"]
        has_rfr = any(f.field_name in rfr_keys for f in mkt.data_fields if f.value is not None)
        if not has_rfr:
            mkt.data_fields.append(DataField(
                field_name="risk_free_rate",
                display_name="Risk-Free Rate",
                value=None,
                status=DataStatus.MISSING,
                unit="%",
                source="validation_check",
                is_critical=True,
                allow_override=True
            ))

    def _aggregate_missing_data_from_response(self, response_obj: DCFDataReviewResponse) -> MissingDataSummary:
        """
        Evaluates field-level status metrics inside the response object to build a
        comprehensive data quality report for frontend validation and rendering.
        This method fixes the scope issue by explicitly accepting response_obj as parameter.
        """
        critical_missing = []
        optional_missing = []
        retrieved_count = 0
        calculated_count = 0

        # Scan each financial and macro parameter container inside the response object
        containers = [
            ("historical_financials", response_obj.historical_financials),
            ("market_data", response_obj.market_data),
            ("forecast_drivers", response_obj.forecast_drivers),
            ("calculated_metrics", response_obj.calculated_metrics),
            ("peer_comparables", response_obj.peer_comparables)
        ]

        for container_name, container in containers:
            if container is None:
                continue

            # Handle different container types
            data_fields = []
            if hasattr(container, 'data_fields'):
                data_fields = container.data_fields
            elif isinstance(container, dict) and 'data_fields' in container:
                data_fields = container['data_fields']

            for field in data_fields:
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

    def _aggregate_missing_data(
        self,
        displays: List
    ) -> MissingDataSummary:
        """Aggregate missing data from all displays and calculate statistics"""
        critical_missing = []
        optional_missing = []
        retrieved_count = 0
        calculated_count = 0

        for display in displays:
            if hasattr(display, 'data_fields'):
                for field in display.data_fields:
                    if field.status == DataStatus.MISSING:
                        if field.is_critical:
                            critical_missing.append(field.display_name or field.field_name)
                        else:
                            optional_missing.append(field.display_name or field.field_name)
                    elif field.status == DataStatus.RETRIEVED:
                        retrieved_count += 1
                    elif field.status == DataStatus.CALCULATED:
                        calculated_count += 1

        total_fields = retrieved_count + calculated_count + len(critical_missing) + len(optional_missing)
        completion_percentage = ((retrieved_count + calculated_count) / total_fields * 100) if total_fields > 0 else 0
        data_quality_score = (retrieved_count * 1.0 + calculated_count * 0.8) / total_fields * 100 if total_fields > 0 else 0

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
            warnings=[],
            recommendations=[]
        )


# Singleton instance
dcf_step6_processor = DCFStep6Processor()