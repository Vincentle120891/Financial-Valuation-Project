"""Step 6: Data Review Layer - Pure Data Aggregation (No Calculations)"""
import logging
from typing import Dict, List, Optional, Any
from pydantic import BaseModel
from enum import Enum
from datetime import datetime

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
        valuation_model: str,
        historical_data: Dict,
        market_data: Dict,
        forecast_data: Dict,
        retrieved_assumptions: Dict,
        user_overrides: Optional[Dict[str, Any]] = None
    ) -> Step6DataReviewResponse:
        """
        Main entry point for Step 6 data review.
        Aggregates all retrieved data without performing final calculations.
        """
        user_overrides = user_overrides or {}
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
        
        # Process Historical Financials
        historical_display = self._process_dcf_historical(historical_data, user_overrides)
        
        # Process Market Data
        market_display = self._process_dcf_market_data(market_data, user_overrides)
        
        # Process Forecast Drivers (from retrieved data only)
        forecast_display = self._process_dcf_forecast_drivers(forecast_data, retrieved_assumptions, user_overrides)
        
        # Calculate ONLY intermediate metrics (growth rates, margins, etc.) - NOT WACC/TV/Fair Value
        calculated_display = self._calculate_dcf_intermediate_metrics(
            historical_display, market_display, forecast_display
        )
        
        # Aggregate missing data
        missing_summary = self._aggregate_missing_data([
            historical_display, forecast_display, market_display, calculated_display
        ])
        
        ready = len(missing_summary.critical_missing) == 0
        
        return Step6DataReviewResponse(
            session_id=f"step6_{ticker}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            ticker=ticker,
            timestamp=datetime.now(),
            valuation_model=ValuationModel.DCF,
            historical_financials=historical_display,
            forecast_drivers=forecast_display,
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
        """Process historical financials for DCF"""
        years = []
        data_fields = []
        
        financials = historical_data.get("financials")
        if financials is not None:
            for col in financials.columns:
                year = int(col.year)
                years.append(year)
                
                # Revenue
                rev_val = financials.loc['Total Revenue', col] if 'Total Revenue' in financials.index else None
                data_fields.append(DataField(
                    field_name=f"Revenue_{year}",
                    value=rev_val,
                    unit="USD",
                    status=DataStatus.RETRIEVED if rev_val else DataStatus.MISSING,
                    source="yfinance" if rev_val else None,
                    is_critical=True
                ))
                
                # EBITDA
                ebitda_val = financials.loc['EBITDA', col] if 'EBITDA' in financials.index else None
                data_fields.append(DataField(
                    field_name=f"EBITDA_{year}",
                    value=ebitda_val,
                    unit="USD",
                    status=DataStatus.RETRIEVED if ebitda_val else DataStatus.MISSING,
                    source="yfinance" if ebitda_val else None,
                    is_critical=True
                ))
        
        return HistoricalFinancialsDisplay(years=years, data_fields=data_fields)
    
    def _process_dcf_market_data(self, market_data: Dict, overrides: Dict) -> MarketDataDisplay:
        """Process market data for DCF"""
        info = market_data.get("info", {})
        
        # Current Stock Price
        current_price = info.get('currentPrice', info.get('regularMarketPrice'))
        price_field = DataField(
            field_name="Current Stock Price",
            value=current_price,
            unit="USD",
            status=DataStatus.RETRIEVED if current_price else DataStatus.MISSING,
            source="yfinance" if current_price else None,
            is_critical=True
        ) if current_price else None
        
        # Beta
        beta = overrides.get("beta", info.get('beta', 1.0))
        beta_field = DataField(
            field_name="Beta",
            value=beta,
            status=DataStatus.MANUAL_OVERRIDE if "beta" in overrides else DataStatus.RETRIEVED,
            source="User Input" if "beta" in overrides else "yfinance",
            is_critical=True,
            allow_override=True
        )
        
        # Total Debt
        total_debt = market_data.get("total_debt")
        debt_field = DataField(
            field_name="Total Debt",
            value=total_debt,
            unit="USD",
            status=DataStatus.RETRIEVED if total_debt else DataStatus.MISSING,
            source="yfinance" if total_debt else None,
            is_critical=True
        ) if total_debt else None
        
        # Cash
        cash = market_data.get("cash")
        cash_field = DataField(
            field_name="Cash",
            value=cash,
            unit="USD",
            status=DataStatus.RETRIEVED if cash else DataStatus.MISSING,
            source="yfinance" if cash else None,
            is_critical=True
        ) if cash else None
        
        return MarketDataDisplay(
            current_stock_price=price_field,
            beta=beta_field,
            total_debt=debt_field,
            cash=cash_field,
            currency=DataField(field_name="Currency", value="USD", status=DataStatus.RETRIEVED, source="yfinance")
        )
    
    def _process_dcf_forecast_drivers(self, forecast_data: Dict, retrieved_assumptions: Dict, overrides: Dict) -> ForecastDriversDisplay:
        """Process forecast drivers from retrieved data"""
        fields = []
        
        # Revenue Growth (from historical calculation or override)
        default_growth = retrieved_assumptions.get("revenue_growth", 0.05)
        if "revenue_growth" in overrides:
            default_growth = overrides["revenue_growth"]
            status = DataStatus.MANUAL_OVERRIDE
            source = "User Input"
        else:
            status = DataStatus.CALCULATED
            source = "Historical CAGR"
        
        fields.append(DataField(
            field_name="Revenue Growth Rate",
            value=default_growth,
            unit="%",
            status=status,
            source=source,
            formula="Historical CAGR or User Input",
            is_critical=True,
            allow_override=True
        ))
        
        return ForecastDriversDisplay(data_fields=fields)
    
    def _calculate_dcf_intermediate_metrics(self, hist: HistoricalFinancialsDisplay, market: MarketDataDisplay, forecast: ForecastDriversDisplay) -> CalculatedMetricsDisplay:
        """Calculate ONLY intermediate metrics (margins, growth rates) - NOT WACC/TV/Fair Value"""
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
        
        return CalculatedMetricsDisplay(data_fields=fields)
    
    # === Helper Methods for DuPont ===
    
    def _process_dupont_income_data(self, historical_data: Dict, overrides: Dict) -> HistoricalFinancialsDisplay:
        """Process income statement data for DuPont"""
        years = []
        data_fields = []
        
        financials = historical_data.get("financials")
        if financials is not None:
            for col in financials.columns:
                year = int(col.year)
                years.append(year)
                
                # Net Income
                ni_val = financials.loc['Net Income', col] if 'Net Income' in financials.index else None
                data_fields.append(DataField(
                    field_name=f"Net Income_{year}",
                    value=ni_val,
                    unit="USD",
                    status=DataStatus.RETRIEVED if ni_val else DataStatus.MISSING,
                    source="yfinance" if ni_val else None,
                    is_critical=True
                ))
                
                # Revenue
                rev_val = financials.loc['Total Revenue', col] if 'Total Revenue' in financials.index else None
                data_fields.append(DataField(
                    field_name=f"Revenue_{year}",
                    value=rev_val,
                    unit="USD",
                    status=DataStatus.RETRIEVED if rev_val else DataStatus.MISSING,
                    source="yfinance" if rev_val else None,
                    is_critical=True
                ))
        
        return HistoricalFinancialsDisplay(years=years, data_fields=data_fields)
    
    def _process_dupont_balance_data(self, historical_data: Dict, overrides: Dict) -> MarketDataDisplay:
        """Process balance sheet data for DuPont"""
        balance_sheet = historical_data.get("balance_sheet")
        
        # Total Assets
        total_assets = None
        if balance_sheet is not None:
            for col in balance_sheet.columns:
                if 'Total Assets' in balance_sheet.index:
                    total_assets = balance_sheet.loc['Total Assets', col]
                    break
        
        assets_field = DataField(
            field_name="Total Assets",
            value=total_assets,
            unit="USD",
            status=DataStatus.RETRIEVED if total_assets else DataStatus.MISSING,
            source="yfinance" if total_assets else None,
            is_critical=True
        ) if total_assets else None
        
        # Shareholders Equity
        equity = None
        if balance_sheet is not None:
            for col in balance_sheet.columns:
                if 'Stockholders Equity' in balance_sheet.index:
                    equity = balance_sheet.loc['Stockholders Equity', col]
                    break
        
        equity_field = DataField(
            field_name="Shareholders Equity",
            value=equity,
            unit="USD",
            status=DataStatus.RETRIEVED if equity else DataStatus.MISSING,
            source="yfinance" if equity else None,
            is_critical=True
        ) if equity else None
        
        return MarketDataDisplay(
            market_cap=assets_field,
            shares_outstanding=equity_field
        )
    
    def _calculate_dupont_intermediate_metrics(self, income: HistoricalFinancialsDisplay, balance: MarketDataDisplay) -> CalculatedMetricsDisplay:
        """Calculate ONLY intermediate metrics for DuPont - NOT final ROE"""
        fields = []
        
        # Placeholder for intermediate calculations
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
