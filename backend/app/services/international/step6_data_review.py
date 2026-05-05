"""Step 6: Data Review Layer - Pure Data Aggregation (No Final Calculations)"""
import logging
from typing import Dict, List, Optional, Any
from pydantic import BaseModel
from enum import Enum
from datetime import datetime

from .yfinance_service import YFinanceService

logger = logging.getLogger(__name__)

class ValuationModel(str, Enum):
    """Type of valuation model to use"""
    DCF = "DCF"
    DUPONT = "DUPONT"
    COMPS = "COMPS"

class DataStatus(str, Enum):
    """Status of data field"""
    RETRIEVED = "RETRIEVED"
    CALCULATED = "CALCULATED"
    MISSING = "MISSING"
    MANUAL_OVERRIDE = "MANUAL_OVERRIDE"

class DataField(BaseModel):
    """A single data field with status tracking"""
    field_name: str
    value: Optional[Any] = None
    unit: str = ""
    status: DataStatus
    source: Optional[str] = None
    formula: Optional[str] = None
    is_critical: bool = False
    allow_override: bool = False

class HistoricalFinancialsDisplay(BaseModel):
    """Historical financial data display"""
    years: List[int] = []
    data_fields: List[DataField] = []

class ForecastDriversDisplay(BaseModel):
    """Forecast drivers display"""
    data_fields: List[DataField] = []

class MarketDataDisplay(BaseModel):
    """Market data display"""
    current_stock_price: Optional[DataField] = None
    shares_outstanding: Optional[DataField] = None
    market_cap: Optional[DataField] = None
    beta: Optional[DataField] = None
    total_debt: Optional[DataField] = None
    cash: Optional[DataField] = None
    currency: Optional[DataField] = None
    data_fields: List[DataField] = []

class CalculatedMetricsDisplay(BaseModel):
    """Calculated metrics from retrieved data (NOT final valuations)"""
    data_fields: List[DataField] = []

class MissingDataSummary(BaseModel):
    """Summary of missing data"""
    critical_missing: List[str] = []
    optional_missing: List[str] = []
    total_missing: int = 0

class Step6DataReviewResponse(BaseModel):
    """
    Step 6 Response: Shows all retrieved inputs, missing inputs,
    and calculated intermediate metrics. NO FINAL VALUATIONS.
    """
    session_id: str
    ticker: str
    timestamp: datetime
    valuation_model: ValuationModel
    historical_financials: Optional[HistoricalFinancialsDisplay] = None
    forecast_drivers: Optional[ForecastDriversDisplay] = None
    market_data: Optional[MarketDataDisplay] = None
    calculated_metrics: Optional[CalculatedMetricsDisplay] = None
    missing_data_summary: Optional[MissingDataSummary] = None
    manual_overrides_applied: Dict[str, Any] = {}
    ready_for_ai_suggestions: bool = False
    message: str = ""


class Step6DataReviewProcessor:
    """
    Step 6: Data Review Layer
    - Collects Historical Financials (Step 3)
    - Collects Market Data (Step 2)
    - Collects Forecast Drivers (Step 4)
    - Collects Assumptions (Step 5 - retrieved data only)
    - Calculates ONLY intermediate metrics that can be derived from retrieved data
    - NO WACC, NO Terminal Value, NO Enterprise Value, NO Fair Value calculations
    """
    
    def __init__(self):
        pass
    
    async def process_data_review(
        self,
        ticker: str,
        market: str = "international",
        historical_data: Optional[Dict] = None,
        market_data: Optional[Dict] = None,
        forecast_data: Optional[Dict] = None,
        retrieved_assumptions: Optional[Dict] = None,
        user_overrides: Optional[Dict[str, Any]] = None,
        valuation_model: Optional[str] = None
    ) -> Step6DataReviewResponse:
        """
        Main entry point for Step 6 data review.
        Aggregates all retrieved data without performing final calculations.
        
        Args can be passed directly or will be fetched if not provided.
        """
        # If data is not provided, fetch it
        if historical_data is None or market_data is None or forecast_data is None or retrieved_assumptions is None:
            # Fetch all required data
            yfinance_service = YFinanceService()
            all_data = yfinance_service.fetch_all_data(ticker, market)
            
            historical_data = historical_data or all_data.get('historical', {})
            market_data = market_data or all_data.get('key_stats', {})
            forecast_data = forecast_data or all_data.get('analyst_estimates', {})
            retrieved_assumptions = retrieved_assumptions or {}
        
        user_overrides = user_overrides or {}
        valuation_model = valuation_model or "DCF"
        model_enum = ValuationModel(valuation_model.upper())
        
        if model_enum == ValuationModel.DCF:
            return await self._process_dcf_data_review(
                ticker, historical_data, market_data, forecast_data, retrieved_assumptions, user_overrides
            )
        elif model_enum == ValuationModel.DUPONT:
            return await self._process_dupont_data_review(
                ticker, historical_data, market_data, retrieved_assumptions, user_overrides
            )
        elif model_enum == ValuationModel.COMPS:
            return await self._process_comps_data_review(
                ticker, historical_data, market_data, retrieved_assumptions, user_overrides
            )
        else:
            raise ValueError(f"Unknown valuation model: {valuation_model}")
    
    async def _process_dcf_data_review(
        self,
        ticker: str,
        historical_data: Dict,
        market_data: Dict,
        forecast_data: Dict,
        retrieved_assumptions: Dict,
        user_overrides: Dict
    ) -> Step6DataReviewResponse:
        """Process DCF data review - aggregate only, no final calculations"""
        
        # Process Historical Financials (11 fields)
        historical_display = self._process_dcf_historical(historical_data, user_overrides)
        
        # Process Market Data (6 fields)
        market_display = self._process_dcf_market_data(market_data, user_overrides)
        
        # Process Balance Sheet Opening Balances (3 fields)
        opening_display = self._process_dcf_opening_balances(historical_data, user_overrides)
        
        # Process Peer Comparables for WACC (5 fields × N peers)
        peer_display = self._process_dcf_peer_comparables(retrieved_assumptions, user_overrides)
        
        # Calculate ONLY intermediate metrics (growth rates, margins, etc.) - NOT WACC/TV/Fair Value
        calculated_display = self._calculate_dcf_intermediate_metrics(
            historical_display, market_display, opening_display, peer_display
        )
        
        # Aggregate missing data
        all_displays = [historical_display, market_display, opening_display, peer_display, calculated_display]
        missing_summary = self._aggregate_missing_data(all_displays)
        
        ready = len(missing_summary.critical_missing) == 0
        
        return Step6DataReviewResponse(
            session_id=f"step6_{ticker}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            ticker=ticker,
            timestamp=datetime.now(),
            valuation_model=ValuationModel.DCF,
            historical_financials=historical_display,
            forecast_drivers=ForecastDriversDisplay(data_fields=opening_display.data_fields + peer_display.data_fields),
            market_data=market_display,
            calculated_metrics=calculated_display,
            missing_data_summary=missing_summary,
            manual_overrides_applied=user_overrides,
            ready_for_ai_suggestions=ready,
            message="Data aggregated successfully. Ready for AI suggestions in Step 7." if ready else "Missing critical data. Please retrieve missing inputs."
        )
    
    async def _process_dupont_data_review(
        self,
        ticker: str,
        historical_data: Dict,
        market_data: Dict,
        retrieved_assumptions: Dict,
        user_overrides: Dict
    ) -> Step6DataReviewResponse:
        """Process DuPont data review - aggregate only, no ROE calculations"""
        
        # Process Income Statement Data
        income_display = self._process_dupont_income_data(historical_data, user_overrides)
        
        # Process Balance Sheet Data
        balance_display = self._process_dupont_balance_data(historical_data, user_overrides)
        
        # Calculate ONLY intermediate ratios (not final ROE decomposition)
        calculated_display = self._calculate_dupont_intermediate_metrics(income_display, balance_display)
        
        # Aggregate missing data
        missing_summary = self._aggregate_missing_data([income_display, balance_display, calculated_display])
        
        ready = len(missing_summary.critical_missing) == 0
        
        return Step6DataReviewResponse(
            session_id=f"step6_{ticker}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            ticker=ticker,
            timestamp=datetime.now(),
            valuation_model=ValuationModel.DUPONT,
            historical_financials=income_display,
            market_data=balance_display,
            calculated_metrics=calculated_display,
            missing_data_summary=missing_summary,
            manual_overrides_applied=user_overrides,
            ready_for_ai_suggestions=ready,
            message="Data aggregated successfully. Ready for AI suggestions in Step 7." if ready else "Missing critical data. Please retrieve missing inputs."
        )
    
    async def _process_comps_data_review(
        self,
        ticker: str,
        historical_data: Dict,
        market_data: Dict,
        retrieved_assumptions: Dict,
        user_overrides: Dict
    ) -> Step6DataReviewResponse:
        """Process Comps data review - aggregate only, no valuation calculations"""
        
        # Process Target Company Data
        target_display = self._process_comps_target_data(historical_data, market_data, user_overrides)
        
        # Process Peer Data
        peer_display = self._process_comps_peer_data(retrieved_assumptions, user_overrides)
        
        # Calculate ONLY intermediate metrics (not median/mean multiples or implied valuation)
        calculated_display = self._calculate_comps_intermediate_metrics(target_display, peer_display)
        
        # Aggregate missing data
        missing_summary = self._aggregate_missing_data([target_display, peer_display, calculated_display])
        
        ready = len(missing_summary.critical_missing) == 0
        
        return Step6DataReviewResponse(
            session_id=f"step6_{ticker}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            ticker=ticker,
            timestamp=datetime.now(),
            valuation_model=ValuationModel.COMPS,
            historical_financials=target_display,
            market_data=peer_display,
            calculated_metrics=calculated_display,
            missing_data_summary=missing_summary,
            manual_overrides_applied=user_overrides,
            ready_for_ai_suggestions=ready,
            message="Data aggregated successfully. Ready for AI suggestions in Step 7." if ready else "Missing critical data. Please retrieve missing inputs."
        )
    
    # === Helper Methods for DCF ===
    
    def _process_dcf_historical(self, historical_data: Dict, overrides: Dict) -> HistoricalFinancialsDisplay:
        """Process historical financials for DCF (11 fields)"""
        years = []
        data_fields = []
        
        financials = historical_data.get("financials")
        cashflow = historical_data.get("cashflow")
        balance_sheet = historical_data.get("balance_sheet")
        
        if financials is not None:
            for col in financials.columns:
                year = int(col.year)
                years.append(year)
                
                # 1. Total Revenue
                rev_val = financials.loc['Total Revenue', col] if 'Total Revenue' in financials.index else None
                data_fields.append(DataField(
                    field_name=f"Revenue_{year}",
                    value=rev_val,
                    unit="USD",
                    status=DataStatus.RETRIEVED if rev_val else DataStatus.MISSING,
                    source="yfinance" if rev_val else None,
                    is_critical=True
                ))
                
                # 2. EBITDA
                ebitda_val = financials.loc['EBITDA', col] if 'EBITDA' in financials.index else None
                data_fields.append(DataField(
                    field_name=f"EBITDA_{year}",
                    value=ebitda_val,
                    unit="USD",
                    status=DataStatus.RETRIEVED if ebitda_val else DataStatus.MISSING,
                    source="yfinance" if ebitda_val else None,
                    is_critical=True
                ))
                
                # 3. Depreciation & Amortization
                da_val = cashflow.loc['Depreciation', col] if cashflow is not None and 'Depreciation' in cashflow.index else None
                data_fields.append(DataField(
                    field_name=f"Depreciation_Amortization_{year}",
                    value=da_val,
                    unit="USD",
                    status=DataStatus.RETRIEVED if da_val else DataStatus.MISSING,
                    source="yfinance" if da_val else None,
                    is_critical=False
                ))
                
                # 4. Capital Expenditures
                capex_val = cashflow.loc['Capital Expenditure', col] * -1 if cashflow is not None and 'Capital Expenditure' in cashflow.index else None
                data_fields.append(DataField(
                    field_name=f"CapEx_{year}",
                    value=capex_val,
                    unit="USD",
                    status=DataStatus.RETRIEVED if capex_val else DataStatus.MISSING,
                    source="yfinance" if capex_val else None,
                    is_critical=True
                ))
                
                # 5. Working Capital Changes
                wc_val = cashflow.loc['Change In Working Capital', col] if cashflow is not None and 'Change In Working Capital' in cashflow.index else None
                data_fields.append(DataField(
                    field_name=f"Working_Capital_Change_{year}",
                    value=wc_val,
                    unit="USD",
                    status=DataStatus.RETRIEVED if wc_val else DataStatus.MISSING,
                    source="yfinance" if wc_val else None,
                    is_critical=False
                ))
                
                # 6. Accounts Receivable (for AR Days)
                ar_val = balance_sheet.loc['Accounts Receivable', col] if balance_sheet is not None and 'Accounts Receivable' in balance_sheet.index else None
                data_fields.append(DataField(
                    field_name=f"Accounts_Receivable_{year}",
                    value=ar_val,
                    unit="USD",
                    status=DataStatus.RETRIEVED if ar_val else DataStatus.MISSING,
                    source="yfinance" if ar_val else None,
                    is_critical=False
                ))
                
                # 7. Inventory (for Inventory Days)
                inv_val = balance_sheet.loc['Inventory', col] if balance_sheet is not None and 'Inventory' in balance_sheet.index else None
                data_fields.append(DataField(
                    field_name=f"Inventory_{year}",
                    value=inv_val,
                    unit="USD",
                    status=DataStatus.RETRIEVED if inv_val else DataStatus.MISSING,
                    source="yfinance" if inv_val else None,
                    is_critical=False
                ))
                
                # 8. Accounts Payable (for AP Days)
                ap_val = balance_sheet.loc['Accounts Payable', col] if balance_sheet is not None and 'Accounts Payable' in balance_sheet.index else None
                data_fields.append(DataField(
                    field_name=f"Accounts_Payable_{year}",
                    value=ap_val,
                    unit="USD",
                    status=DataStatus.RETRIEVED if ap_val else DataStatus.MISSING,
                    source="yfinance" if ap_val else None,
                    is_critical=False
                ))
                
                # 9. Interest Expense
                int_val = financials.loc['Interest Expense', col] if 'Interest Expense' in financials.index else None
                data_fields.append(DataField(
                    field_name=f"Interest_Expense_{year}",
                    value=int_val,
                    unit="USD",
                    status=DataStatus.RETRIEVED if int_val else DataStatus.MISSING,
                    source="yfinance" if int_val else None,
                    is_critical=False
                ))
                
                # 10. Tax Provision (for effective tax rate)
                tax_val = financials.loc['Tax Effect Of Unusual Items', col] if 'Tax Effect Of Unusual Items' in financials.index else None
                if tax_val is None:
                    tax_val = financials.loc['Income Tax', col] if 'Income Tax' in financials.index else None
                data_fields.append(DataField(
                    field_name=f"Tax_Provision_{year}",
                    value=tax_val,
                    unit="USD",
                    status=DataStatus.RETRIEVED if tax_val else DataStatus.MISSING,
                    source="yfinance" if tax_val else None,
                    is_critical=False
                ))
                
                # 11. Pre-Tax Income (for effective tax rate)
                pretax_val = financials.loc['Pretax Income', col] if 'Pretax Income' in financials.index else None
                data_fields.append(DataField(
                    field_name=f"Pre_Tax_Income_{year}",
                    value=pretax_val,
                    unit="USD",
                    status=DataStatus.RETRIEVED if pretax_val else DataStatus.MISSING,
                    source="yfinance" if pretax_val else None,
                    is_critical=False
                ))
        
        return HistoricalFinancialsDisplay(years=years, data_fields=data_fields)
    
    def _process_dcf_market_data(self, market_data: Dict, overrides: Dict) -> MarketDataDisplay:
        """Process market data for DCF (6 fields)"""
        info = market_data.get("info", {})
        data_fields = []
        
        # 1. Current Stock Price
        current_price = info.get('currentPrice', info.get('regularMarketPrice'))
        price_field = DataField(
            field_name="Current Stock Price",
            value=current_price,
            unit="USD",
            status=DataStatus.RETRIEVED if current_price else DataStatus.MISSING,
            source="yfinance" if current_price else None,
            is_critical=True
        ) if current_price else None
        data_fields.append(price_field) if price_field else None
        
        # 2. Shares Outstanding
        shares = info.get('sharesOutstanding')
        shares_field = DataField(
            field_name="Shares Outstanding",
            value=shares,
            unit="shares",
            status=DataStatus.RETRIEVED if shares else DataStatus.MISSING,
            source="yfinance" if shares else None,
            is_critical=True
        ) if shares else None
        data_fields.append(shares_field) if shares_field else None
        
        # 3. Beta
        beta = overrides.get("beta", info.get('beta', 1.0))
        beta_field = DataField(
            field_name="Beta",
            value=beta,
            status=DataStatus.MANUAL_OVERRIDE if "beta" in overrides else DataStatus.RETRIEVED,
            source="User Input" if "beta" in overrides else "yfinance",
            is_critical=True,
            allow_override=True
        )
        data_fields.append(beta_field)
        
        # 4. Total Debt
        total_debt = market_data.get("total_debt")
        debt_field = DataField(
            field_name="Total Debt",
            value=total_debt,
            unit="USD",
            status=DataStatus.RETRIEVED if total_debt else DataStatus.MISSING,
            source="yfinance" if total_debt else None,
            is_critical=True
        ) if total_debt else None
        data_fields.append(debt_field) if debt_field else None
        
        # 5. Cash & Equivalents
        cash = market_data.get("cash")
        cash_field = DataField(
            field_name="Cash & Equivalents",
            value=cash,
            unit="USD",
            status=DataStatus.RETRIEVED if cash else DataStatus.MISSING,
            source="yfinance" if cash else None,
            is_critical=True
        ) if cash else None
        data_fields.append(cash_field) if cash_field else None
        
        # 6. Market Cap
        mcap = info.get('marketCap')
        mcap_field = DataField(
            field_name="Market Cap",
            value=mcap,
            unit="USD",
            status=DataStatus.RETRIEVED if mcap else DataStatus.MISSING,
            source="yfinance" if mcap else None,
            is_critical=True
        ) if mcap else None
        data_fields.append(mcap_field) if mcap_field else None
        
        return MarketDataDisplay(
            current_stock_price=price_field,
            shares_outstanding=shares_field,
            beta=beta_field,
            total_debt=debt_field,
            cash=cash_field,
            market_cap=mcap_field,
            currency=DataField(field_name="Currency", value="USD", status=DataStatus.RETRIEVED, source="yfinance"),
            data_fields=data_fields
        )
    
    def _process_dcf_opening_balances(self, historical_data: Dict, overrides: Dict) -> HistoricalFinancialsDisplay:
        """Process opening balances for DCF (3 fields)"""
        years = []
        data_fields = []
        
        balance_sheet = historical_data.get("balance_sheet")
        if balance_sheet is not None:
            # Get most recent year for opening balances
            if len(balance_sheet.columns) > 0:
                latest_col = balance_sheet.columns[0]
                year = int(latest_col.year)
                years.append(year)
                
                # 1. Net Debt Opening Balance (calculated from Debt - Cash)
                total_debt = balance_sheet.loc['Total Debt', latest_col] if 'Total Debt' in balance_sheet.index else None
                if total_debt is None:
                    total_debt = balance_sheet.loc['Long Term Debt', latest_col] if 'Long Term Debt' in balance_sheet.index else None
                cash = balance_sheet.loc['Cash And Cash Equivalents', latest_col] if 'Cash And Cash Equivalents' in balance_sheet.index else None
                if cash is None:
                    cash = balance_sheet.loc['Cash', latest_col] if 'Cash' in balance_sheet.index else None
                
                net_debt = (total_debt - cash) if (total_debt and cash) else None
                data_fields.append(DataField(
                    field_name=f"Net_Debt_Opening_{year}",
                    value=net_debt,
                    unit="USD",
                    status=DataStatus.CALCULATED if net_debt else DataStatus.MISSING,
                    source="Calculated from Balance Sheet",
                    formula="Total Debt - Cash",
                    is_critical=False
                ))
                
                # 2. PP&E (Gross) Opening Balance
                ppe_val = balance_sheet.loc['Property Plant Equipment', latest_col] if 'Property Plant Equipment' in balance_sheet.index else None
                data_fields.append(DataField(
                    field_name=f"PPnE_Gross_Opening_{year}",
                    value=ppe_val,
                    unit="USD",
                    status=DataStatus.RETRIEVED if ppe_val else DataStatus.MISSING,
                    source="yfinance" if ppe_val else None,
                    is_critical=False
                ))
                
                # 3. Accumulated Depreciation
                accum_dep_val = balance_sheet.loc['Accumulated Depreciation', latest_col] if 'Accumulated Depreciation' in balance_sheet.index else None
                data_fields.append(DataField(
                    field_name=f"Accumulated_Depreciation_Opening_{year}",
                    value=accum_dep_val,
                    unit="USD",
                    status=DataStatus.RETRIEVED if accum_dep_val else DataStatus.MISSING,
                    source="yfinance" if accum_dep_val else None,
                    is_critical=False
                ))
        
        return HistoricalFinancialsDisplay(years=years, data_fields=data_fields)
    
    def _process_dcf_peer_comparables(self, retrieved_assumptions: Dict, overrides: Dict) -> HistoricalFinancialsDisplay:
        """Process peer comparables for WACC calculation (5 fields × N peers)"""
        years = [2024]  # Current year for peer data
        data_fields = []
        
        peers = retrieved_assumptions.get("peers", [])
        if not peers:
            peers = overrides.get("peers", [])
        
        for i, peer_ticker in enumerate(peers[:5]):  # Limit to 5 peers
            peer_info = retrieved_assumptions.get(f"peer_{peer_ticker}_info", {})
            
            # 1. Peer Market Cap
            peer_mcap = peer_info.get('marketCap')
            data_fields.append(DataField(
                field_name=f"Peer_{peer_ticker}_MarketCap",
                value=peer_mcap,
                unit="USD",
                status=DataStatus.RETRIEVED if peer_mcap else DataStatus.MISSING,
                source="yfinance" if peer_mcap else None,
                is_critical=False
            ))
            
            # 2. Peer Beta
            peer_beta = peer_info.get('beta')
            data_fields.append(DataField(
                field_name=f"Peer_{peer_ticker}_Beta",
                value=peer_beta,
                status=DataStatus.RETRIEVED if peer_beta else DataStatus.MISSING,
                source="yfinance" if peer_beta else None,
                is_critical=False
            ))
            
            # 3. Peer Total Debt
            peer_debt = peer_info.get('totalDebt')
            data_fields.append(DataField(
                field_name=f"Peer_{peer_ticker}_TotalDebt",
                value=peer_debt,
                unit="USD",
                status=DataStatus.RETRIEVED if peer_debt else DataStatus.MISSING,
                source="yfinance" if peer_debt else None,
                is_critical=False
            ))
            
            # 4. Peer Cash
            peer_cash = peer_info.get('cash')
            data_fields.append(DataField(
                field_name=f"Peer_{peer_ticker}_Cash",
                value=peer_cash,
                unit="USD",
                status=DataStatus.RETRIEVED if peer_cash else DataStatus.MISSING,
                source="yfinance" if peer_cash else None,
                is_critical=False
            ))
            
            # 5. Peer Tax Rate (calculated from financials)
            peer_tax_rate = peer_info.get('effectiveTaxRate')
            data_fields.append(DataField(
                field_name=f"Peer_{peer_ticker}_TaxRate",
                value=peer_tax_rate,
                unit="%",
                status=DataStatus.CALCULATED if peer_tax_rate else DataStatus.MISSING,
                source="Calculated from yfinance" if peer_tax_rate else None,
                formula="Tax Provision / Pre-Tax Income",
                is_critical=False
            ))
        
        return HistoricalFinancialsDisplay(years=years, data_fields=data_fields)
    
    def _calculate_dcf_intermediate_metrics(self, hist: HistoricalFinancialsDisplay, market: MarketDataDisplay, opening: HistoricalFinancialsDisplay, peers: HistoricalFinancialsDisplay) -> CalculatedMetricsDisplay:
        """Calculate ONLY intermediate metrics (margins, growth rates, ratios) - NOT WACC/TV/Fair Value"""
        fields = []
        
        # Calculate historical EBITDA margins (if data available)
        if hist.data_fields:
            revenues = [f.value for f in hist.data_fields if 'Revenue' in f.field_name and f.value]
            ebitdas = [f.value for f in hist.data_fields if 'EBITDA' in f.field_name and f.value]
            
            if revenues and ebitdas and len(revenues) == len(ebitdas):
                avg_margin = sum(e/r for e, r in zip(ebitdas, revenues)) / len(revenues)
                fields.append(DataField(
                    field_name="Average EBITDA Margin",
                    value=avg_margin,
                    unit="%",
                    status=DataStatus.CALCULATED,
                    source="Step 6 Calculation",
                    formula="Avg(EBITDA / Revenue)",
                    is_critical=False
                ))
        
        # Calculate Net Debt (if debt and cash available)
        if market.total_debt and market.cash:
            net_debt = market.total_debt.value - market.cash.value
            fields.append(DataField(
                field_name="Net Debt",
                value=net_debt,
                unit="USD",
                status=DataStatus.CALCULATED,
                source="Step 6 Calculation",
                formula="Total Debt - Cash",
                is_critical=False
            ))
        
        # Calculate Enterprise Value (if market cap and net debt available)
        if market.market_cap and market.total_debt and market.cash:
            ev = market.market_cap.value + net_debt
            fields.append(DataField(
                field_name="Enterprise Value",
                value=ev,
                unit="USD",
                status=DataStatus.CALCULATED,
                source="Step 6 Calculation",
                formula="Market Cap + Net Debt",
                is_critical=False
            ))
        
        # Calculate historical growth rates (YoY)
        if len(revenues) >= 2:
            revenue_growth = (revenues[-1] - revenues[0]) / revenues[0]
            fields.append(DataField(
                field_name="Revenue Growth Rate (Period)",
                value=revenue_growth,
                unit="%",
                status=DataStatus.CALCULATED,
                source="Step 6 Calculation",
                formula="(Latest Revenue - Earliest Revenue) / Earliest Revenue",
                is_critical=False
            ))
        
        # Calculate D&A % of Revenue
        if hist.data_fields:
            da_values = [f.value for f in hist.data_fields if 'Depreciation_Amortization' in f.field_name and f.value]
            if da_values and revenues and len(da_values) == len(revenues):
                avg_da_pct = sum(d/r for d, r in zip(da_values, revenues)) / len(revenues)
                fields.append(DataField(
                    field_name="Average D&A % of Revenue",
                    value=avg_da_pct,
                    unit="%",
                    status=DataStatus.CALCULATED,
                    source="Step 6 Calculation",
                    formula="Avg(D&A / Revenue)",
                    is_critical=False
                ))
        
        # Calculate CapEx % of Revenue
        if hist.data_fields:
            capex_values = [f.value for f in hist.data_fields if 'CapEx' in f.field_name and f.value]
            if capex_values and revenues and len(capex_values) == len(revenues):
                avg_capex_pct = sum(c/r for c, r in zip(capex_values, revenues)) / len(revenues)
                fields.append(DataField(
                    field_name="Average CapEx % of Revenue",
                    value=avg_capex_pct,
                    unit="%",
                    status=DataStatus.CALCULATED,
                    source="Step 6 Calculation",
                    formula="Avg(CapEx / Revenue)",
                    is_critical=False
                ))
        
        # Calculate Working Capital % of Revenue
        if hist.data_fields:
            wc_values = [f.value for f in hist.data_fields if 'Working_Capital_Change' in f.field_name and f.value]
            if wc_values and revenues and len(wc_values) == len(revenues):
                avg_wc_pct = sum(w/r for w, r in zip(wc_values, revenues)) / len(revenues)
                fields.append(DataField(
                    field_name="Average WC Change % of Revenue",
                    value=avg_wc_pct,
                    unit="%",
                    status=DataStatus.CALCULATED,
                    source="Step 6 Calculation",
                    formula="Avg(WC Change / Revenue)",
                    is_critical=False
                ))
        
        # Calculate implied effective tax rate
        if hist.data_fields:
            tax_values = [f.value for f in hist.data_fields if 'Tax_Provision' in f.field_name and f.value]
            pretax_values = [f.value for f in hist.data_fields if 'Pre_Tax_Income' in f.field_name and f.value]
            if tax_values and pretax_values and len(tax_values) == len(pretax_values):
                avg_tax_rate = sum(t/p for t, p in zip(tax_values, pretax_values) if p != 0) / len(tax_values)
                fields.append(DataField(
                    field_name="Average Effective Tax Rate",
                    value=avg_tax_rate,
                    unit="%",
                    status=DataStatus.CALCULATED,
                    source="Step 6 Calculation",
                    formula="Avg(Tax Provision / Pre-Tax Income)",
                    is_critical=False
                ))
        
        return CalculatedMetricsDisplay(data_fields=fields)
    
    # === Helper Methods for DuPont ===
    
    def _process_dupont_income_data(self, historical_data: Dict, overrides: Dict) -> HistoricalFinancialsDisplay:
        """Process income statement data for DuPont (6 fields)"""
        years = []
        data_fields = []
        
        financials = historical_data.get("financials")
        if financials is not None:
            for col in financials.columns:
                year = int(col.year)
                years.append(year)
                
                # 1. Net Income
                ni_val = financials.loc['Net Income', col] if 'Net Income' in financials.index else None
                data_fields.append(DataField(
                    field_name=f"Net_Income_{year}",
                    value=ni_val,
                    unit="USD",
                    status=DataStatus.RETRIEVED if ni_val else DataStatus.MISSING,
                    source="yfinance" if ni_val else None,
                    is_critical=True
                ))
                
                # 2. Total Revenue
                rev_val = financials.loc['Total Revenue', col] if 'Total Revenue' in financials.index else None
                data_fields.append(DataField(
                    field_name=f"Total_Revenue_{year}",
                    value=rev_val,
                    unit="USD",
                    status=DataStatus.RETRIEVED if rev_val else DataStatus.MISSING,
                    source="yfinance" if rev_val else None,
                    is_critical=True
                ))
                
                # 3. Operating Income (EBIT)
                op_val = financials.loc['Operating Income', col] if 'Operating Income' in financials.index else None
                data_fields.append(DataField(
                    field_name=f"Operating_Income_{year}",
                    value=op_val,
                    unit="USD",
                    status=DataStatus.RETRIEVED if op_val else DataStatus.MISSING,
                    source="yfinance" if op_val else None,
                    is_critical=True
                ))
                
                # 4. Interest Expense
                int_val = financials.loc['Interest Expense', col] if 'Interest Expense' in financials.index else None
                data_fields.append(DataField(
                    field_name=f"Interest_Expense_{year}",
                    value=int_val,
                    unit="USD",
                    status=DataStatus.RETRIEVED if int_val else DataStatus.MISSING,
                    source="yfinance" if int_val else None,
                    is_critical=False
                ))
                
                # 5. Tax Provision
                tax_val = financials.loc['Tax Provision', col] if 'Tax Provision' in financials.index else None
                data_fields.append(DataField(
                    field_name=f"Tax_Provision_{year}",
                    value=tax_val,
                    unit="USD",
                    status=DataStatus.RETRIEVED if tax_val else DataStatus.MISSING,
                    source="yfinance" if tax_val else None,
                    is_critical=False
                ))
                
                # 6. Pre-Tax Income
                pretax_val = financials.loc['Pretax Income', col] if 'Pretax Income' in financials.index else None
                data_fields.append(DataField(
                    field_name=f"Pre_Tax_Income_{year}",
                    value=pretax_val,
                    unit="USD",
                    status=DataStatus.RETRIEVED if pretax_val else DataStatus.MISSING,
                    source="yfinance" if pretax_val else None,
                    is_critical=False
                ))
        
        return HistoricalFinancialsDisplay(years=years, data_fields=data_fields)
    
    def _process_dupont_balance_data(self, historical_data: Dict, overrides: Dict) -> HistoricalFinancialsDisplay:
        """Process balance sheet data for DuPont (6 fields)"""
        years = []
        data_fields = []
        
        balance_sheet = historical_data.get("balance_sheet")
        if balance_sheet is not None:
            for col in balance_sheet.columns:
                year = int(col.year)
                years.append(year)
                
                # 1. Total Assets
                assets_val = balance_sheet.loc['Total Assets', col] if 'Total Assets' in balance_sheet.index else None
                data_fields.append(DataField(
                    field_name=f"Total_Assets_{year}",
                    value=assets_val,
                    unit="USD",
                    status=DataStatus.RETRIEVED if assets_val else DataStatus.MISSING,
                    source="yfinance" if assets_val else None,
                    is_critical=True
                ))
                
                # 2. Shareholders Equity
                equity_val = balance_sheet.loc['Stockholders Equity', col] if 'Stockholders Equity' in balance_sheet.index else None
                data_fields.append(DataField(
                    field_name=f"Shareholders_Equity_{year}",
                    value=equity_val,
                    unit="USD",
                    status=DataStatus.RETRIEVED if equity_val else DataStatus.MISSING,
                    source="yfinance" if equity_val else None,
                    is_critical=True
                ))
                
                # 3. Total Liabilities
                liab_val = balance_sheet.loc['Total Liabilities Net Minority Interest', col] if 'Total Liabilities Net Minority Interest' in balance_sheet.index else None
                data_fields.append(DataField(
                    field_name=f"Total_Liabilities_{year}",
                    value=liab_val,
                    unit="USD",
                    status=DataStatus.RETRIEVED if liab_val else DataStatus.MISSING,
                    source="yfinance" if liab_val else None,
                    is_critical=False
                ))
                
                # 4. Long-Term Debt
                ltd_val = balance_sheet.loc['Long Term Debt', col] if 'Long Term Debt' in balance_sheet.index else None
                data_fields.append(DataField(
                    field_name=f"Long_Term_Debt_{year}",
                    value=ltd_val,
                    unit="USD",
                    status=DataStatus.RETRIEVED if ltd_val else DataStatus.MISSING,
                    source="yfinance" if ltd_val else None,
                    is_critical=False
                ))
                
                # 5. Short-Term Debt
                std_val = balance_sheet.loc['Current Debt', col] if 'Current Debt' in balance_sheet.index else None
                data_fields.append(DataField(
                    field_name=f"Short_Term_Debt_{year}",
                    value=std_val,
                    unit="USD",
                    status=DataStatus.RETRIEVED if std_val else DataStatus.MISSING,
                    source="yfinance" if std_val else None,
                    is_critical=False
                ))
                
                # 6. Cash & Equivalents
                cash_val = balance_sheet.loc['Cash And Cash Equivalents', col] if 'Cash And Cash Equivalents' in balance_sheet.index else None
                data_fields.append(DataField(
                    field_name=f"Cash_And_Equivalents_{year}",
                    value=cash_val,
                    unit="USD",
                    status=DataStatus.RETRIEVED if cash_val else DataStatus.MISSING,
                    source="yfinance" if cash_val else None,
                    is_critical=False
                ))
        
        return HistoricalFinancialsDisplay(years=years, data_fields=data_fields)
    
    def _calculate_dupont_intermediate_metrics(self, income: HistoricalFinancialsDisplay, balance: HistoricalFinancialsDisplay) -> CalculatedMetricsDisplay:
        """Calculate ONLY intermediate metrics for DuPont - NOT final ROE"""
        fields = []
        
        # Extract data by year for calculations
        income_by_year = {}
        for field in income.data_fields:
            year = field.field_name.split('_')[-1]
            if year not in income_by_year:
                income_by_year[year] = {}
            income_by_year[year][field.field_name.rsplit('_', 1)[0]] = field.value
        
        balance_by_year = {}
        for field in balance.data_fields:
            year = field.field_name.split('_')[-1]
            if year not in balance_by_year:
                balance_by_year[year] = {}
            balance_by_year[year][field.field_name.rsplit('_', 1)[0]] = field.value
        
        years = sorted(income_by_year.keys())
        
        # Calculate trends for each year (where prior year data exists)
        for i, year in enumerate(years):
            curr = income_by_year.get(year, {})
            prev = income_by_year.get(str(int(year)-1), {}) if i > 0 else {}
            
            # Net Profit Margin
            ni = curr.get('Net_Income')
            rev = curr.get('Total_Revenue')
            if ni and rev and rev != 0:
                margin = ni / rev
                fields.append(DataField(
                    field_name=f"Net_Profit_Margin_{year}",
                    value=margin,
                    unit="%",
                    status=DataStatus.CALCULATED,
                    formula="Net Income / Revenue",
                    is_critical=False
                ))
            
            # Operating Margin
            op = curr.get('Operating_Income')
            if op and rev and rev != 0:
                op_margin = op / rev
                fields.append(DataField(
                    field_name=f"Operating_Margin_{year}",
                    value=op_margin,
                    unit="%",
                    status=DataStatus.CALCULATED,
                    formula="Operating Income / Revenue",
                    is_critical=False
                ))
            
            # Asset Turnover (requires average assets)
            if i > 0:
                curr_assets = balance_by_year.get(year, {}).get('Total_Assets')
                prev_assets = balance_by_year.get(str(int(year)-1), {}).get('Total_Assets')
                if curr_assets and prev_assets:
                    avg_assets = (curr_assets + prev_assets) / 2
                    if avg_assets != 0:
                        turnover = rev / avg_assets
                        fields.append(DataField(
                            field_name=f"Asset_Turnover_{year}",
                            value=turnover,
                            unit="x",
                            status=DataStatus.CALCULATED,
                            formula="Revenue / Average Total Assets",
                            is_critical=False
                        ))
                
                # Equity Multiplier
                curr_equity = balance_by_year.get(year, {}).get('Shareholders_Equity')
                prev_equity = balance_by_year.get(str(int(year)-1), {}).get('Shareholders_Equity')
                if curr_equity and prev_equity:
                    avg_equity = (curr_equity + prev_equity) / 2
                    if avg_equity != 0:
                        multiplier = avg_assets / avg_equity
                        fields.append(DataField(
                            field_name=f"Equity_Multiplier_{year}",
                            value=multiplier,
                            unit="x",
                            status=DataStatus.CALCULATED,
                            formula="Average Total Assets / Average Shareholders Equity",
                            is_critical=False
                        ))
                
                # Debt-to-Equity Ratio
                curr_debt = (balance_by_year.get(year, {}).get('Long_Term_Debt') or 0) + \
                           (balance_by_year.get(year, {}).get('Short_Term_Debt') or 0)
                if curr_equity and curr_equity != 0:
                    dte = curr_debt / curr_equity
                    fields.append(DataField(
                        field_name=f"Debt_to_Equity_{year}",
                        value=dte,
                        unit="x",
                        status=DataStatus.CALCULATED,
                        formula="(Long Term Debt + Short Term Debt) / Shareholders Equity",
                        is_critical=False
                    ))
            
            # Interest Burden
            ebit = curr.get('Operating_Income')
            pretax = curr.get('Pre_Tax_Income')
            if ebit and pretax and ebit != 0:
                interest_burden = pretax / ebit
                fields.append(DataField(
                    field_name=f"Interest_Burden_{year}",
                    value=interest_burden,
                    unit="x",
                    status=DataStatus.CALCULATED,
                    formula="Pre-Tax Income / Operating Income",
                    is_critical=False
                ))
            
            # Tax Burden
            if pretax and ni and pretax != 0:
                tax_burden = ni / pretax
                fields.append(DataField(
                    field_name=f"Tax_Burden_{year}",
                    value=tax_burden,
                    unit="x",
                    status=DataStatus.CALCULATED,
                    formula="Net Income / Pre-Tax Income",
                    is_critical=False
                ))
        
        return CalculatedMetricsDisplay(data_fields=fields)
    
    # === Helper Methods for Comps ===
    
    def _process_comps_target_data(self, historical_data: Dict, market_data: Dict, overrides: Dict) -> HistoricalFinancialsDisplay:
        """Process target company data for Comps"""
        years = []
        data_fields = []
        
        info = market_data.get("info", {})
        
        # Market Cap
        mcap = info.get('marketCap')
        data_fields.append(DataField(
            field_name="Market Cap",
            value=mcap,
            unit="USD",
            status=DataStatus.RETRIEVED if mcap else DataStatus.MISSING,
            source="yfinance" if mcap else None,
            is_critical=True
        ))
        
        # Enterprise Value
        ev = info.get('enterpriseValue')
        data_fields.append(DataField(
            field_name="Enterprise Value",
            value=ev,
            unit="USD",
            status=DataStatus.RETRIEVED if ev else DataStatus.MISSING,
            source="yfinance" if ev else None,
            is_critical=True
        ))
        
        return HistoricalFinancialsDisplay(years=years, data_fields=data_fields)
    
    def _process_comps_peer_data(self, retrieved_assumptions: Dict, overrides: Dict) -> MarketDataDisplay:
        """Process peer company data for Comps"""
        # Placeholder for peer data processing
        return MarketDataDisplay()
    
    def _calculate_comps_intermediate_metrics(self, target: HistoricalFinancialsDisplay, peers: MarketDataDisplay) -> CalculatedMetricsDisplay:
        """Calculate ONLY intermediate metrics for Comps - NOT median/mean multiples"""
        fields = []
        
        # Placeholder for intermediate calculations
        return CalculatedMetricsDisplay(data_fields=fields)
    
    # === Common Helper Methods ===
    
    def _aggregate_missing_data(self, displays: List) -> MissingDataSummary:
        """Aggregate missing data from all displays"""
        critical_missing = []
        optional_missing = []
        
        for display in displays:
            if hasattr(display, 'data_fields'):
                for field in display.data_fields:
                    if field.status == DataStatus.MISSING:
                        if field.is_critical:
                            critical_missing.append(field.field_name)
                        else:
                            optional_missing.append(field.field_name)
        
        return MissingDataSummary(
            critical_missing=critical_missing,
            optional_missing=optional_missing,
            total_missing=len(critical_missing) + len(optional_missing)
        )
