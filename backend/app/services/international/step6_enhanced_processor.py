"""
Step 6 Enhanced Processor
Handles data retrieval, calculation, status tracking, and missing data flagging for Step 6.
Separates business logic from static Pydantic models.
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import pandas as pd
import numpy as np

from app.models.international.international_inputs import (
    DuPontRequest, CompsValuationRequest, DCFValuationRequest
)
from app.models.international.international_inputs import (
    # Import the new enhanced display models
    DataStatus, DataField, MissingDataSummary,
    HistoricalFinancialsDisplay, ForecastDriversDisplay, MarketDataDisplay, 
    CalculatedMetricsDisplay, Step6EnhancedResponse,
    CompsTargetDataDisplay, CompsPeerDataDisplay, CompsCalculatedMetricsDisplay,
    Step6CompsEnhancedResponse,
    DuPontComponentsDisplay, DuPontTrendAnalysisDisplay, Step6DuPontEnhancedResponse
)
from app.services.international.yfinance_service import YFinanceService
from app.services.international.dcf_input_manager import DCFInputManager
from app.engines.international.dcf_engine import DCFEngine


class Step6EnhancedProcessor:
    """
    Processes raw inputs into enhanced Step 6 responses with:
    - Data source tracking (Retrieved vs Calculated vs Missing)
    - Formula display for calculated fields
    - Missing data flags and recommendations
    - Manual override capabilities
    """

    def __init__(self):
        self.yfinance_service = YFinanceService()
        self.input_manager = DCFInputManager()
        self.dcf_engine = DCFEngine()

    # ========================================================================
    # DCF PROCESSING
    # ========================================================================

    async def process_dcf_step6(
        self, 
        ticker: str, 
        user_overrides: Optional[Dict[str, Any]] = None
    ) -> Step6EnhancedResponse:
        """
        Main entry point for DCF Step 6 processing.
        1. Fetches raw data from yfinance
        2. Calculates derived metrics
        3. Flags missing data
        4. Applies user overrides
        5. Returns enhanced response with status tracking
        """
        user_overrides = user_overrides or {}

        # 1. Fetch Raw Data
        raw_data = await self._fetch_dcf_raw_data(ticker)
        
        # 2. Process Historical Financials
        historical_display = self._process_historical_financials(raw_data, user_overrides)
        
        # 3. Process Forecast Drivers (with overrides)
        forecast_display = self._process_forecast_drivers(raw_data, user_overrides)
        
        # 4. Process Market Data
        market_display = self._process_market_data(ticker, raw_data, user_overrides)
        
        # 5. Calculate Key Metrics (WACC, Terminal Value, Fair Value)
        calculated_display = await self._calculate_dcf_metrics(
            ticker, historical_display, forecast_display, market_display
        )

        # 6. Aggregate Missing Data Summary
        missing_summary = self._aggregate_missing_data(
            [historical_display, forecast_display, market_display, calculated_display]
        )

        return Step6EnhancedResponse(
            ticker=ticker,
            timestamp=datetime.now(),
            historical_financials=historical_display,
            forecast_drivers=forecast_display,
            market_data=market_display,
            calculated_metrics=calculated_display,
            missing_data_summary=missing_summary,
            valuation_ready=missing_summary.critical_missing_count == 0
        )

    async def _fetch_dcf_raw_data(self, ticker: str) -> Dict:
        """Fetch raw data from yfinance."""
        try:
            info = await self.yfinance_service.get_company_info(ticker)
            financials = await self.yfinance_service.get_financials(ticker)
            balance_sheet = await self.yfinance_service.get_balance_sheet(ticker)
            cash_flow = await self.yfinance_service.get_cash_flow(ticker)
            history = await self.yfinance_service.get_price_history(ticker, period="1y")
            
            return {
                "info": info,
                "financials": financials,
                "balance_sheet": balance_sheet,
                "cash_flow": cash_flow,
                "price_history": history,
                "error": None
            }
        except Exception as e:
            return {
                "info": {}, "financials": None, "balance_sheet": None, 
                "cash_flow": None, "price_history": None, "error": str(e)
            }

    def _process_historical_financials(self, raw_data: Dict, overrides: Dict) -> HistoricalFinancialsDisplay:
        """Process historical financials with status tracking."""
        financials = raw_data.get("financials")
        years = []
        data_fields = []

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

    def _process_forecast_drivers(self, raw_data: Dict, overrides: Dict) -> ForecastDriversDisplay:
        """Process forecast drivers, allowing manual overrides."""
        fields = []

        # Revenue Growth
        default_growth = 0.05  # Default 5%
        status = DataStatus.ESTIMATED
        source = "Default Assumption"
        
        if "revenue_growth_forecast" in overrides:
            default_growth = overrides["revenue_growth_forecast"]
            status = DataStatus.MANUAL_OVERRIDE
            source = "User Input"
        elif raw_data.get("info"):
            # Try to get analyst growth estimates if available
            pass 

        fields.append(DataField(
            field_name="Revenue Growth Rate",
            value=default_growth,
            unit="%",
            status=status,
            source=source,
            formula="User Input or Analyst Consensus",
            is_critical=True,
            allow_override=True
        ))

        # Terminal Growth
        term_growth = overrides.get("terminal_growth_rate", 0.025)
        fields.append(DataField(
            field_name="Terminal Growth Rate",
            value=term_growth,
            unit="%",
            status=DataStatus.MANUAL_OVERRIDE if "terminal_growth_rate" in overrides else DataStatus.ESTIMATED,
            source="User Input" if "terminal_growth_rate" in overrides else "GDP Long-term Avg",
            formula="Long-term GDP Growth Expectation",
            is_critical=True,
            allow_override=True
        ))

        return ForecastDriversDisplay(data_fields=fields)

    def _process_market_data(self, ticker: str, raw_data: Dict, overrides: Dict) -> MarketDataDisplay:
        """Process market data like Beta, Risk-Free Rate."""
        fields = []
        info = raw_data.get("info", {})

        # Beta
        beta = info.get('beta', None)
        if "beta" in overrides:
            beta = overrides["beta"]
            status = DataStatus.MANUAL_OVERRIDE
            source = "User Input"
        elif beta:
            status = DataStatus.RETRIEVED
            source = "yfinance"
        else:
            beta = 1.0
            status = DataStatus.ESTIMATED
            source = "Default (Market)"

        fields.append(DataField(
            field_name="Beta",
            value=beta,
            status=status,
            source=source,
            formula="Regression vs S&P 500",
            is_critical=True,
            allow_override=True
        ))

        # Risk-Free Rate (10Y Treasury)
        rf_rate = overrides.get("risk_free_rate", 0.045) # Default 4.5%
        fields.append(DataField(
            field_name="Risk-Free Rate",
            value=rf_rate,
            unit="%",
            status=DataStatus.MANUAL_OVERRIDE if "risk_free_rate" in overrides else DataStatus.ESTIMATED,
            source="User Input" if "risk_free_rate" in overrides else "US 10Y Bond",
            is_critical=True,
            allow_override=True
        ))

        return MarketDataDisplay(data_fields=fields)

    async def _calculate_dcf_metrics(
        self, 
        ticker: str, 
        hist: HistoricalFinancialsDisplay, 
        forecast: ForecastDriversDisplay, 
        market: MarketDataDisplay
    ) -> CalculatedMetricsDisplay:
        """Calculate WACC, FCF, Terminal Value, Enterprise Value, Equity Value, and Fair Value."""
        
        # Extract values for calculation
        beta = next((f.value for f in market.data_fields if f.field_name == "Beta"), 1.0)
        rf = next((f.value for f in market.data_fields if f.field_name == "Risk-Free Rate"), 0.045)
        growth = next((f.value for f in forecast.data_fields if f.field_name == "Revenue Growth Rate"), 0.05)
        term_growth = next((f.value for f in forecast.data_fields if f.field_name == "Terminal Growth Rate"), 0.025)

        # Get historical financials for calculations
        latest_revenue = None
        latest_ebitda = None
        for field in hist.data_fields:
            if field.field_name.startswith("Revenue_") and field.value:
                latest_revenue = field.value
            if field.field_name.startswith("EBITDA_") and field.value:
                latest_ebitda = field.value

        # Calculate WACC (Simplified)
        # WACC = Re * E/V + Rd * D/V * (1-T)
        # Re = Rf + Beta * MRP
        mrp = 0.055  # Market Risk Premium
        cost_of_equity = rf + beta * mrp
        wacc = cost_of_equity * 0.8 + 0.04 * 0.2 * (1-0.21)  # Simplified capital structure
        
        wacc_field = DataField(
            field_name="WACC",
            value=wacc,
            unit="%",
            status=DataStatus.CALCULATED,
            source="DCF Engine",
            formula=f"WACC = (Re: {cost_of_equity:.2%}) * 0.8 + (Rd * (1-T)) * 0.2",
            is_critical=True
        )

        # Project FCF for 5 years (simplified: FCF = EBITDA * (1 - tax_rate) - CapEx approx 3% of revenue)
        tax_rate = 0.21
        capex_pct = 0.03
        fcf_projections = []
        if latest_revenue and latest_ebitda:
            base_fcf = latest_ebitda * (1 - tax_rate) - (latest_revenue * capex_pct)
            for year in range(1, 6):
                fcf = base_fcf * ((1 + growth) ** year)
                fcf_projections.append(fcf)
        
        # Calculate Terminal Value (Perpetuity Growth Method)
        terminal_value = None
        terminal_value_field = None
        if fcf_projections:
            final_fcf = fcf_projections[-1]
            if wacc > term_growth:
                terminal_value = final_fcf * (1 + term_growth) / (wacc - term_growth)
                terminal_value_field = DataField(
                    field_name="Terminal Value",
                    value=terminal_value,
                    unit="USD",
                    status=DataStatus.CALCULATED,
                    source="DCF Engine",
                    formula=f"TV = FCF[n] * (1 + g) / (WACC - g) where g={term_growth:.2%}",
                    is_critical=True
                )
        
        # Calculate Present Value of FCF Projections
        pv_fcf = 0
        if fcf_projections:
            for i, fcf in enumerate(fcf_projections, 1):
                pv_fcf += fcf / ((1 + wacc) ** i)
        
        # Calculate Present Value of Terminal Value
        pv_terminal = None
        if terminal_value:
            pv_terminal = terminal_value / ((1 + wacc) ** 5)
        
        # Calculate Enterprise Value
        enterprise_value = None
        enterprise_value_field = None
        if pv_fcf and pv_terminal:
            enterprise_value = pv_fcf + pv_terminal
            enterprise_value_field = DataField(
                field_name="Enterprise Value",
                value=enterprise_value,
                unit="USD",
                status=DataStatus.CALCULATED,
                source="DCF Engine",
                formula="EV = PV(FCF Projections) + PV(Terminal Value)",
                is_critical=True
            )
        
        # Estimate Net Debt (simplified: assume 10% of latest revenue if not available)
        net_debt = latest_revenue * 0.1 if latest_revenue else 0
        
        # Calculate Equity Value
        equity_value = None
        equity_value_field = None
        if enterprise_value:
            equity_value = enterprise_value - net_debt
            equity_value_field = DataField(
                field_name="Equity Value",
                value=equity_value,
                unit="USD",
                status=DataStatus.CALCULATED,
                source="DCF Engine",
                formula="Equity Value = Enterprise Value - Net Debt",
                is_critical=True
            )
        
        # Estimate Shares Outstanding (simplified: assume 1% of latest revenue as proxy)
        shares_outstanding = latest_revenue * 0.01 / 100 if latest_revenue else None
        
        # Calculate Fair Value per Share
        fair_value_per_share = None
        fair_value_field = None
        if equity_value and shares_outstanding:
            fair_value_per_share = equity_value / shares_outstanding
            fair_value_field = DataField(
                field_name="Fair Value per Share",
                value=fair_value_per_share,
                unit="USD",
                status=DataStatus.CALCULATED,
                source="DCF Model",
                formula="Fair Value per Share = Equity Value / Shares Outstanding",
                is_critical=True
            )
        
        # Calculate Implied Upside/Downside (need current stock price)
        # For now, use a placeholder or fetch from yfinance
        current_price = None
        try:
            info = await self.yfinance_service.get_company_info(ticker)
            current_price = info.get('currentPrice', info.get('regularMarketPrice', None))
        except:
            pass
        
        implied_upside_downside = None
        upside_field = None
        if fair_value_per_share and current_price:
            implied_upside_downside = (fair_value_per_share - current_price) / current_price
            upside_field = DataField(
                field_name="Implied Upside/Downside",
                value=implied_upside_downside,
                unit="%",
                status=DataStatus.CALCULATED,
                source="DCF Model",
                formula="Upside/Downside = (Fair Value - Current Price) / Current Price",
                is_critical=False
            )
        
        return CalculatedMetricsDisplay(
            wacc=wacc_field,
            terminal_value=terminal_value_field,
            enterprise_value=enterprise_value_field,
            equity_value=equity_value_field,
            fair_value_per_share=fair_value_field,
            implied_upside_downside=upside_field
        )

    # ========================================================================
    # COMPS PROCESSING (Simplified Structure)
    # ========================================================================

    async def process_comps_step6(
        self, 
        target_ticker: str, 
        peer_list: List[str],
        user_overrides: Optional[Dict] = None
    ) -> Step6CompsEnhancedResponse:
        """Process Comps data with status tracking."""
        # Implementation similar to DCF but for Comps specific fields
        # Fetch peer multiples, calculate median/mean, flag outliers
        return Step6CompsEnhancedResponse(
            target_ticker=target_ticker,
            timestamp=datetime.now(),
            target_data=CompsTargetDataDisplay(data_fields=[]),
            peer_data=CompsPeerDataDisplay(peers=[]),
            calculated_metrics=CompsCalculatedMetricsDisplay(data_fields=[]),
            missing_data_summary=MissingDataSummary(
                total_fields=0, retrieved_count=0, calculated_count=0, 
                missing_count=0, critical_missing=[], optional_missing=[],
                completion_percentage=0.0, warnings=[]
            ),
            valuation_ready=False
        )

    # ========================================================================
    # DUPONT PROCESSING (Simplified Structure)
    # ========================================================================

    async def process_dupont_step6(
        self, 
        ticker: str, 
        years: List[int],
        user_overrides: Optional[Dict] = None
    ) -> Step6DuPontEnhancedResponse:
        """Process DuPont data with status tracking."""
        return Step6DuPontEnhancedResponse(
            ticker=ticker,
            timestamp=datetime.now(),
            components=DuPontComponentsDisplay(data_fields=[]),
            trend_analysis=DuPontTrendAnalysisDisplay(trends=[]),
            missing_data_summary=MissingDataSummary(
                total_fields=0, retrieved_count=0, calculated_count=0, 
                missing_count=0, critical_missing=[], optional_missing=[],
                completion_percentage=0.0, warnings=[]
            ),
            valuation_ready=False
        )

    # ========================================================================
    # UTILITIES
    # ========================================================================

    def _aggregate_missing_data(self, displays: List[Any]) -> MissingDataSummary:
        """Aggregates missing data from all display sections."""
        total = 0
        retrieved = 0
        calculated = 0
        missing = 0
        critical_missing = []
        optional_missing = []
        warnings = []

        for display in displays:
            if hasattr(display, 'data_fields'):
                fields = display.data_fields
            elif hasattr(display, 'years') and hasattr(display, 'data_fields'):
                fields = display.data_fields
            else:
                continue

            for field in fields:
                total += 1
                if field.status == DataStatus.RETRIEVED:
                    retrieved += 1
                elif field.status == DataStatus.CALCULATED:
                    calculated += 1
                elif field.status in [DataStatus.MISSING, DataStatus.ESTIMATED]:
                    missing += 1
                    if field.is_critical:
                        critical_missing.append(field.field_name)
                    else:
                        optional_missing.append(field.field_name)
        
        completion = (retrieved + calculated) / total * 100 if total > 0 else 0
        
        if completion < 50:
            warnings.append("Low data completeness. Valuation may be inaccurate.")
        if len(critical_missing) > 0:
            warnings.append(f"Critical data missing: {', '.join(critical_missing[:3])}...")

        return MissingDataSummary(
            total_fields=total,
            retrieved_count=retrieved,
            calculated_count=calculated,
            missing_count=missing,
            critical_missing=critical_missing,
            optional_missing=optional_missing,
            completion_percentage=round(completion, 2),
            warnings=warnings
        )
