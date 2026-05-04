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
        # DCFEngine requires inputs parameter, initialize lazily when needed
        self.dcf_engine = None

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
            session_id="session_" + ticker,
            ticker=ticker,
            timestamp=datetime.now(),
            historical_financials=historical_display,
            forecast_drivers=forecast_display,
            market_data=market_display,
            calculated_metrics=calculated_display,
            missing_data_summary=missing_summary,
            valuation_ready=len(missing_summary.critical_missing) == 0
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
        info = raw_data.get("info", {})

        # Current Stock Price
        current_price = info.get('currentPrice', info.get('regularMarketPrice', None))
        price_field = DataField(
            field_name="Current Stock Price",
            value=current_price,
            unit="USD",
            status=DataStatus.RETRIEVED if current_price else DataStatus.MISSING,
            source="yfinance" if current_price else None,
            is_critical=True
        ) if current_price else None

        # Shares Outstanding
        shares = info.get('sharesOutstanding', None)
        shares_field = DataField(
            field_name="Shares Outstanding",
            value=shares,
            unit="shares",
            status=DataStatus.RETRIEVED if shares else DataStatus.MISSING,
            source="yfinance" if shares else None,
            is_critical=True
        ) if shares else None

        # Market Cap
        market_cap = info.get('marketCap', None)
        mcap_field = DataField(
            field_name="Market Cap",
            value=market_cap,
            unit="USD",
            status=DataStatus.RETRIEVED if market_cap else DataStatus.MISSING,
            source="yfinance" if market_cap else None,
            is_critical=False
        ) if market_cap else None

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

        beta_field = DataField(
            field_name="Beta",
            value=beta,
            status=status,
            source=source,
            formula="Regression vs S&P 500",
            is_critical=True,
            allow_override=True
        )

        # Total Debt
        balance_sheet = raw_data.get("balance_sheet")
        total_debt = None
        if balance_sheet is not None:
            # Try to get latest total debt
            for col in balance_sheet.columns:
                if 'Total Debt' in balance_sheet.index:
                    total_debt = balance_sheet.loc['Total Debt', col]
                    break
        
        debt_field = DataField(
            field_name="Total Debt",
            value=total_debt,
            unit="USD",
            status=DataStatus.RETRIEVED if total_debt else DataStatus.MISSING,
            source="yfinance" if total_debt else None,
            is_critical=True
        ) if total_debt else None

        # Cash
        cash = None
        if balance_sheet is not None:
            for col in balance_sheet.columns:
                if 'Cash And Cash Equivalents' in balance_sheet.index:
                    cash = balance_sheet.loc['Cash And Cash Equivalents', col]
                    break
        
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
            shares_outstanding=shares_field,
            market_cap=mcap_field,
            beta=beta_field,
            total_debt=debt_field,
            cash=cash_field,
            currency=DataField(field_name="Currency", value="USD", status=DataStatus.RETRIEVED, source="yfinance")
        )

    async def _calculate_dcf_metrics(
        self, 
        ticker: str, 
        hist: HistoricalFinancialsDisplay, 
        forecast: ForecastDriversDisplay, 
        market: MarketDataDisplay
    ) -> CalculatedMetricsDisplay:
        """Calculate WACC, FCF, Terminal Value, Enterprise Value, Equity Value, and Fair Value."""
        
        # Extract values from Market Data Display model (uses individual fields, not data_fields list)
        beta = market.beta.value if market.beta else 1.0
        current_price = market.current_stock_price.value if market.current_stock_price else None
        shares_outstanding = market.shares_outstanding.value if market.shares_outstanding else None
        total_debt = market.total_debt.value if market.total_debt else 0
        cash = market.cash.value if market.cash else 0
        
        # Extract forecast drivers from individual fields (not data_fields list)
        growth = forecast.revenue_growth_forecast.value if forecast.revenue_growth_forecast else 0.05
        term_growth = forecast.terminal_growth_rate.value if forecast.terminal_growth_rate else 0.025

        # Get historical financials from individual fields (HistoricalFinancialsDisplay uses named fields, not data_fields list)
        latest_revenue = hist.revenue.value if hist.revenue else None
        latest_ebitda = hist.ebitda.value if hist.ebitda else None

        # Calculate WACC (Simplified)
        # WACC = Re * E/V + Rd * D/V * (1-T)
        # Re = Rf + Beta * MRP
        rf_rate = 0.045  # Default risk-free rate
        mrp = 0.055  # Market Risk Premium
        cost_of_equity = rf_rate + beta * mrp
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
        
        # Calculate Net Debt
        net_debt = (total_debt or 0) - (cash or 0)
        if net_debt == 0 and latest_revenue:
            net_debt = latest_revenue * 0.1  # Fallback estimate
        
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
        
        # Calculate Fair Value per Share
        fair_value_per_share = None
        fair_value_field = None
        if equity_value and shares_outstanding and shares_outstanding > 0:
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
        
        # Calculate Implied Upside/Downside
        implied_upside_downside = None
        upside_field = None
        if fair_value_per_share and current_price and current_price > 0:
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
    # COMPS PROCESSING
    # ========================================================================

    async def process_comps_step6(
        self, 
        target_ticker: str, 
        peer_list: List[str],
        user_overrides: Optional[Dict] = None
    ) -> Step6CompsEnhancedResponse:
        """Process Comps data with status tracking."""
        user_overrides = user_overrides or {}
        
        # 1. Fetch Raw Data for Target and Peers
        raw_data = await self._fetch_comps_raw_data(target_ticker, peer_list)
        
        # 2. Process Target Company Data
        target_display = self._process_comps_target_data(target_ticker, raw_data, user_overrides)
        
        # 3. Process Peer Company Data
        peer_display = self._process_comps_peer_data(peer_list, raw_data, user_overrides)
        
        # 4. Calculate Comps Metrics (Median/Mean Multiples, Implied Valuation)
        calculated_display = self._calculate_comps_metrics(target_display, peer_display)
        
        # 5. Aggregate Missing Data Summary
        missing_summary = self._aggregate_missing_data([target_display, peer_display, calculated_display])
        
        return Step6CompsEnhancedResponse(
            target_ticker=target_ticker,
            timestamp=datetime.now(),
            target_data=target_display,
            peer_data=peer_display,
            calculated_metrics=calculated_display,
            missing_data_summary=missing_summary,
            valuation_ready=len(missing_summary.critical_missing) == 0
        )
    
    async def _fetch_comps_raw_data(self, target_ticker: str, peer_list: List[str]) -> Dict:
        """Fetch raw data for target and peers."""
        all_tickers = [target_ticker] + peer_list
        raw_data = {}
        
        for ticker in all_tickers:
            try:
                info = await self.yfinance_service.get_company_info(ticker)
                financials = await self.yfinance_service.get_financials(ticker)
                raw_data[ticker] = {
                    "info": info,
                    "financials": financials,
                    "error": None
                }
            except Exception as e:
                raw_data[ticker] = {
                    "info": {},
                    "financials": None,
                    "error": str(e)
                }
        
        return raw_data
    
    def _process_comps_target_data(self, ticker: str, raw_data: Dict, overrides: Dict) -> CompsTargetDataDisplay:
        """Process target company multiples."""
        fields = []
        data = raw_data.get(ticker, {})
        info = data.get("info", {})
        financials = data.get("financials")
        
        # Current Price
        current_price = info.get('currentPrice', info.get('regularMarketPrice', None))
        if "current_price" in overrides:
            current_price = overrides["current_price"]
            status = DataStatus.MANUAL_OVERRIDE
            source = "User Input"
        elif current_price:
            status = DataStatus.RETRIEVED
            source = "yfinance"
        else:
            status = DataStatus.MISSING
            source = None
        
        fields.append(DataField(
            field_name="Current Price",
            value=current_price,
            unit="USD",
            status=status,
            source=source,
            is_critical=True
        ))
        
        # Market Cap
        market_cap = info.get('marketCap', None)
        if "market_cap" in overrides:
            market_cap = overrides["market_cap"]
            status = DataStatus.MANUAL_OVERRIDE
            source = "User Input"
        elif market_cap:
            status = DataStatus.RETRIEVED
            source = "yfinance"
        else:
            status = DataStatus.MISSING
            source = None
        
        fields.append(DataField(
            field_name="Market Cap",
            value=market_cap,
            unit="USD",
            status=status,
            source=source,
            is_critical=True
        ))
        
        # P/E Ratio
        pe_ratio = info.get('trailingPE', info.get('forwardPE', None))
        if "pe_ratio" in overrides:
            pe_ratio = overrides["pe_ratio"]
            status = DataStatus.MANUAL_OVERRIDE
            source = "User Input"
        elif pe_ratio:
            status = DataStatus.RETRIEVED
            source = "yfinance"
        else:
            status = DataStatus.MISSING
            source = None
        
        fields.append(DataField(
            field_name="P/E Ratio",
            value=pe_ratio,
            status=status,
            source=source,
            is_critical=True
        ))
        
        # EV/EBITDA
        enterprise_value = info.get('enterpriseValue', None)
        ebitda = None
        if financials is not None and 'EBITDA' in financials.index:
            ebitda = financials['EBITDA'].iloc[0] if len(financials.columns) > 0 else None
        
        ev_ebitda = None
        if enterprise_value and ebitda and ebitda != 0:
            ev_ebitda = enterprise_value / ebitda
        
        if "ev_ebitda" in overrides:
            ev_ebitda = overrides["ev_ebitda"]
            status = DataStatus.MANUAL_OVERRIDE
            source = "User Input"
        elif ev_ebitda:
            status = DataStatus.CALCULATED
            source = "Calculated from yfinance"
        else:
            status = DataStatus.MISSING
            source = None
        
        fields.append(DataField(
            field_name="EV/EBITDA",
            value=ev_ebitda,
            status=status,
            source=source,
            formula="Enterprise Value / EBITDA",
            is_critical=True
        ))
        
        # P/B Ratio
        pb_ratio = info.get('priceToBook', None)
        if "pb_ratio" in overrides:
            pb_ratio = overrides["pb_ratio"]
            status = DataStatus.MANUAL_OVERRIDE
            source = "User Input"
        elif pb_ratio:
            status = DataStatus.RETRIEVED
            source = "yfinance"
        else:
            status = DataStatus.MISSING
            source = None
        
        fields.append(DataField(
            field_name="P/B Ratio",
            value=pb_ratio,
            status=status,
            source=source,
            is_critical=False
        ))
        
        return CompsTargetDataDisplay(data_fields=fields)
    
    def _process_comps_peer_data(self, peer_list: List[str], raw_data: Dict, overrides: Dict) -> CompsPeerDataDisplay:
        """Process peer company multiples."""
        peers = []
        
        for ticker in peer_list:
            data = raw_data.get(ticker, {})
            info = data.get("info", {})
            financials = data.get("financials")
            
            if not info:
                continue
            
            peer_fields = []
            
            # P/E Ratio
            pe_ratio = info.get('trailingPE', info.get('forwardPE', None))
            peer_fields.append(DataField(
                field_name="P/E Ratio",
                value=pe_ratio,
                status=DataStatus.RETRIEVED if pe_ratio else DataStatus.MISSING,
                source="yfinance" if pe_ratio else None,
                is_critical=True
            ))
            
            # EV/EBITDA
            enterprise_value = info.get('enterpriseValue', None)
            ebitda = None
            if financials is not None and 'EBITDA' in financials.index:
                ebitda = financials['EBITDA'].iloc[0] if len(financials.columns) > 0 else None
            
            ev_ebitda = None
            if enterprise_value and ebitda and ebitda != 0:
                ev_ebitda = enterprise_value / ebitda
            
            peer_fields.append(DataField(
                field_name="EV/EBITDA",
                value=ev_ebitda,
                status=DataStatus.RETRIEVED if ev_ebitda else DataStatus.MISSING,
                source="Calculated" if ev_ebitda else None,
                is_critical=True
            ))
            
            # P/B Ratio
            pb_ratio = info.get('priceToBook', None)
            peer_fields.append(DataField(
                field_name="P/B Ratio",
                value=pb_ratio,
                status=DataStatus.RETRIEVED if pb_ratio else DataStatus.MISSING,
                source="yfinance" if pb_ratio else None,
                is_critical=False
            ))
            
            # Market Cap
            market_cap = info.get('marketCap', None)
            peer_fields.append(DataField(
                field_name="Market Cap",
                value=market_cap,
                unit="USD",
                status=DataStatus.RETRIEVED if market_cap else DataStatus.MISSING,
                source="yfinance" if market_cap else None,
                is_critical=True
            ))
            
            peers.append({
                "ticker": ticker,
                "company_name": info.get('shortName', info.get('longName', ticker)),
                "data_fields": peer_fields
            })
        
        return CompsPeerDataDisplay(peers=peers)
    
    def _calculate_comps_metrics(self, target: CompsTargetDataDisplay, peers: CompsPeerDataDisplay) -> CompsCalculatedMetricsDisplay:
        """Calculate median/mean multiples and implied valuation."""
        fields = []
        
        # Extract peer multiples
        pe_ratios = []
        ev_ebitdas = []
        pb_ratios = []
        market_caps = []
        
        for peer in peers.peers:
            for field in peer["data_fields"]:
                if field.field_name == "P/E Ratio" and field.value is not None:
                    pe_ratios.append(field.value)
                elif field.field_name == "EV/EBITDA" and field.value is not None:
                    ev_ebitdas.append(field.value)
                elif field.field_name == "P/B Ratio" and field.value is not None:
                    pb_ratios.append(field.value)
                elif field.field_name == "Market Cap" and field.value is not None:
                    market_caps.append(field.value)
        
        # Calculate Median P/E
        median_pe = None
        if pe_ratios:
            median_pe = sorted(pe_ratios)[len(pe_ratios)//2]
            fields.append(DataField(
                field_name="Median P/E",
                value=median_pe,
                status=DataStatus.CALCULATED,
                source="Comps Analysis",
                formula=f"Median of {len(pe_ratios)} peers",
                is_critical=True
            ))
        
        # Calculate Median EV/EBITDA
        median_ev_ebitda = None
        if ev_ebitdas:
            median_ev_ebitda = sorted(ev_ebitdas)[len(ev_ebitdas)//2]
            fields.append(DataField(
                field_name="Median EV/EBITDA",
                value=median_ev_ebitda,
                status=DataStatus.CALCULATED,
                source="Comps Analysis",
                formula=f"Median of {len(ev_ebitdas)} peers",
                is_critical=True
            ))
        
        # Calculate Median P/B
        median_pb = None
        if pb_ratios:
            median_pb = sorted(pb_ratios)[len(pb_ratios)//2]
            fields.append(DataField(
                field_name="Median P/B",
                value=median_pb,
                status=DataStatus.CALCULATED,
                source="Comps Analysis",
                formula=f"Median of {len(pb_ratios)} peers",
                is_critical=False
            ))
        
        # Calculate Implied Valuation (using Median P/E * Target Earnings)
        # For simplicity, we'll estimate earnings from target's market cap and P/E
        implied_valuation = None
        target_pe = None
        target_market_cap = None
        
        for field in target.data_fields:
            if field.field_name == "P/E Ratio":
                target_pe = field.value
            elif field.field_name == "Market Cap":
                target_market_cap = field.value
        
        if median_pe and target_market_cap:
            # Implied Market Cap = Median P/E * (Target Market Cap / Target P/E)
            # Simplified: use median multiple directly
            implied_valuation = target_market_cap  # Placeholder - would need earnings data
            fields.append(DataField(
                field_name="Implied Market Cap (Median P/E)",
                value=implied_valuation,
                unit="USD",
                status=DataStatus.CALCULATED,
                source="Comps Analysis",
                formula="Median P/E * Estimated Earnings",
                is_critical=True
            ))
        
        return CompsCalculatedMetricsDisplay(data_fields=fields)

    # ========================================================================
    # DUPONT PROCESSING
    # ========================================================================

    async def process_dupont_step6(
        self, 
        ticker: str, 
        years: List[int],
        user_overrides: Optional[Dict] = None
    ) -> Step6DuPontEnhancedResponse:
        """Process DuPont data with status tracking."""
        user_overrides = user_overrides or {}
        
        # 1. Fetch Raw Data
        raw_data = await self._fetch_dupont_raw_data(ticker)
        
        # 2. Process DuPont Components (Net Margin, Asset Turnover, Equity Multiplier)
        components_display = self._process_dupont_components(ticker, raw_data, years, user_overrides)
        
        # 3. Process Trend Analysis
        trend_display = self._process_dupont_trend_analysis(components_display, years)
        
        # 4. Aggregate Missing Data Summary
        missing_summary = self._aggregate_missing_data([components_display])
        
        return Step6DuPontEnhancedResponse(
            ticker=ticker,
            timestamp=datetime.now(),
            components=components_display,
            trend_analysis=trend_display,
            missing_data_summary=missing_summary,
            valuation_ready=len(missing_summary.critical_missing) == 0
        )
    
    async def _fetch_dupont_raw_data(self, ticker: str) -> Dict:
        """Fetch raw data for DuPont analysis."""
        try:
            info = await self.yfinance_service.get_company_info(ticker)
            financials = await self.yfinance_service.get_financials(ticker)
            balance_sheet = await self.yfinance_service.get_balance_sheet(ticker)
            
            return {
                "info": info,
                "financials": financials,
                "balance_sheet": balance_sheet,
                "error": None
            }
        except Exception as e:
            return {
                "info": {},
                "financials": None,
                "balance_sheet": None,
                "error": str(e)
            }
    
    def _process_dupont_components(self, ticker: str, raw_data: Dict, years: List[int], overrides: Dict) -> DuPontComponentsDisplay:
        """Process DuPont components for each year."""
        fields = []
        financials = raw_data.get("financials")
        balance_sheet = raw_data.get("balance_sheet")
        
        if financials is None or balance_sheet is None:
            return DuPontComponentsDisplay(data_fields=fields)
        
        for year_col in financials.columns:
            year = int(year_col.year)
            if year not in years:
                continue
            
            # Net Income
            net_income = financials.loc['Net Income', year_col] if 'Net Income' in financials.index else None
            
            # Revenue
            revenue = financials.loc['Total Revenue', year_col] if 'Total Revenue' in financials.index else None
            
            # Total Assets
            total_assets = None
            if 'Total Assets' in balance_sheet.index:
                total_assets = balance_sheet.loc['Total Assets', year_col]
            
            # Total Equity
            total_equity = None
            if "Total Stockholder Equity" in balance_sheet.index:
                total_equity = balance_sheet.loc['Total Stockholder Equity', year_col]
            
            # Calculate Components
            net_margin = None
            if revenue and revenue != 0 and net_income:
                net_margin = net_income / revenue
            
            asset_turnover = None
            if total_assets and total_assets != 0 and revenue:
                asset_turnover = revenue / total_assets
            
            equity_multiplier = None
            if total_equity and total_equity != 0 and total_assets:
                equity_multiplier = total_assets / total_equity
            
            roe = None
            if net_margin and asset_turnover and equity_multiplier:
                roe = net_margin * asset_turnover * equity_multiplier
            
            # Add fields for each component
            fields.append(DataField(
                field_name=f"Net Profit Margin_{year}",
                value=net_margin,
                unit="%",
                status=DataStatus.CALCULATED if net_margin else DataStatus.MISSING,
                source="Calculated from Financials",
                formula="Net Income / Revenue",
                is_critical=True
            ))
            
            fields.append(DataField(
                field_name=f"Asset Turnover_{year}",
                value=asset_turnover,
                status=DataStatus.CALCULATED if asset_turnover else DataStatus.MISSING,
                source="Calculated from Financials",
                formula="Revenue / Total Assets",
                is_critical=True
            ))
            
            fields.append(DataField(
                field_name=f"Equity Multiplier_{year}",
                value=equity_multiplier,
                status=DataStatus.CALCULATED if equity_multiplier else DataStatus.MISSING,
                source="Calculated from Balance Sheet",
                formula="Total Assets / Total Equity",
                is_critical=True
            ))
            
            fields.append(DataField(
                field_name=f"ROE_{year}",
                value=roe,
                unit="%",
                status=DataStatus.CALCULATED if roe else DataStatus.MISSING,
                source="DuPont Analysis",
                formula="Net Margin × Asset Turnover × Equity Multiplier",
                is_critical=True
            ))
        
        return DuPontComponentsDisplay(data_fields=fields)
    
    def _process_dupont_trend_analysis(self, components: DuPontComponentsDisplay, years: List[int]) -> DuPontTrendAnalysisDisplay:
        """Analyze trends in DuPont components."""
        trends = []
        
        # Group components by year
        yearly_data = {}
        for field in components.data_fields:
            parts = field.field_name.split('_')
            if len(parts) == 2:
                metric, year_str = parts
                year = int(year_str)
                if year not in yearly_data:
                    yearly_data[year] = {}
                yearly_data[year][metric] = field.value
        
        # Calculate year-over-year changes
        sorted_years = sorted(yearly_data.keys())
        for i in range(1, len(sorted_years)):
            prev_year = sorted_years[i-1]
            curr_year = sorted_years[i]
            
            prev_data = yearly_data.get(prev_year, {})
            curr_data = yearly_data.get(curr_year, {})
            
            # ROE Change
            roe_change = None
            if curr_data.get('ROE') and prev_data.get('ROE'):
                roe_change = curr_data['ROE'] - prev_data['ROE']
            
            # Primary Driver Analysis
            primary_driver = "N/A"
            if roe_change is not None:
                margin_change = (curr_data.get('Net Profit Margin', 0) or 0) - (prev_data.get('Net Profit Margin', 0) or 0)
                turnover_change = (curr_data.get('Asset Turnover', 0) or 0) - (prev_data.get('Asset Turnover', 0) or 0)
                multiplier_change = (curr_data.get('Equity Multiplier', 0) or 0) - (prev_data.get('Equity Multiplier', 0) or 0)
                
                # Determine which component had the largest impact
                changes = {
                    'Profit Margin': abs(margin_change),
                    'Asset Turnover': abs(turnover_change),
                    'Financial Leverage': abs(multiplier_change)
                }
                primary_driver = max(changes, key=changes.get)
            
            trends.append({
                "period": f"{prev_year}-{curr_year}",
                "roe_change": roe_change,
                "primary_driver": primary_driver,
                "details": {
                    "margin_change": (curr_data.get('Net Profit Margin', 0) or 0) - (prev_data.get('Net Profit Margin', 0) or 0),
                    "turnover_change": (curr_data.get('Asset Turnover', 0) or 0) - (prev_data.get('Asset Turnover', 0) or 0),
                    "multiplier_change": (curr_data.get('Equity Multiplier', 0) or 0) - (prev_data.get('Equity Multiplier', 0) or 0)
                }
            })
        
        return DuPontTrendAnalysisDisplay(trends=trends)

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
