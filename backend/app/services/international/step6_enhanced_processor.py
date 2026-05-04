"""
Step 6 Enhanced Input Processing Service
Processes retrieved inputs, calculates derived values, flags missing data, and enables manual overrides
"""

from typing import Dict, Any, List, Optional, Tuple
from app.models.international.international_inputs import (
    DCFValuationRequest,
    DCFHistoricalFinancials,
    DCFForecastDrivers,
    DCFMarketData,
    CompsValuationRequest,
    PeerMultiple,
    DuPontRequest,
)
from app.models.international.step6_enhanced_models import (
    Step6EnhancedResponse,
    Step6CompsEnhancedResponse,
    Step6DuPontEnhancedResponse,
    DataField,
    DataStatus,
    HistoricalFinancialsDisplay,
    ForecastDriversDisplay,
    MarketDataDisplay,
    CalculatedMetricsDisplay,
    MissingDataSummary,
    CompsTargetDataDisplay,
    CompsPeerDataDisplay,
    CompsCalculatedMetricsDisplay,
    DuPontComponentsDisplay,
    DuPontTrendAnalysisDisplay,
)


class Step6EnhancedProcessor:
    """
    Processes financial inputs for Step 6 display:
    1. Tracks data retrieval status
    2. Calculates derived metrics with formulas
    3. Flags missing data
    4. Enables manual input overrides
    """
    
    # Critical fields required for valuation
    CRITICAL_DCF_FIELDS = [
        "revenue", "ebitda", "net_income", "capex", 
        "total_debt", "cash", "market_cap", "beta",
        "tax_rate", "risk_free_rate", "terminal_growth_rate"
    ]
    
    CRITICAL_COMPS_FIELDS = [
        "target_ebitda_ltm", "target_revenue_ltm",
        "peer_multiples", "ev_ebitda_ltm"
    ]
    
    CRITICAL_DUPONT_FIELDS = [
        "net_income", "revenue", "total_assets", "shareholders_equity"
    ]
    
    def __init__(self):
        pass
    
    # =========================================================================
    # DCF ENHANCED PROCESSING
    # =========================================================================
    
    def process_dcf_inputs(
        self,
        request: DCFValuationRequest,
        raw_data: Dict[str, Any],
        calculated_metrics: Optional[Dict[str, Any]] = None
    ) -> Step6EnhancedResponse:
        """
        Process DCF inputs and generate enhanced response
        
        Args:
            request: Original DCF valuation request
            raw_data: Raw data fetched from APIs
            calculated_metrics: Pre-calculated metrics from engine
            
        Returns:
            Step6EnhancedResponse with full status tracking
        """
        session_id = request.session_id
        ticker = request.ticker
        company_name = request.company_name
        
        # Process historical financials
        historical_display = self._process_historical_financials(
            request.historical_financials,
            raw_data.get("historical", {})
        )
        
        # Process forecast drivers
        forecast_display = self._process_forecast_drivers(
            request.forecast_drivers,
            raw_data.get("forecast", {})
        )
        
        # Process market data
        market_display = self._process_market_data(
            request.market_data,
            raw_data.get("market", {})
        )
        
        # Process calculated metrics
        calc_metrics_display = self._process_calculated_metrics(
            calculated_metrics or {}
        )
        
        # Generate missing data summary
        missing_summary = self._generate_missing_data_summary(
            historical_display,
            forecast_display,
            market_display,
            self.CRITICAL_DCF_FIELDS
        )
        
        # Calculate data quality score
        data_quality_score = self._calculate_data_quality_score(
            missing_summary,
            historical_display,
            forecast_display
        )
        
        # Generate warnings and recommendations
        warnings = self._generate_warnings(
            historical_display,
            forecast_display,
            market_display
        )
        
        recommendations = self._generate_recommendations(
            missing_summary,
            warnings
        )
        
        # Determine allowed overrides
        allowed_overrides = self._get_allowed_overrides(
            forecast_display,
            market_display
        )
        
        return Step6EnhancedResponse(
            session_id=session_id,
            ticker=ticker,
            company_name=company_name,
            historical_financials=historical_display,
            forecast_drivers=forecast_display,
            market_data=market_display,
            calculated_metrics=calc_metrics_display,
            missing_data_summary=missing_summary,
            data_quality_score=data_quality_score,
            warnings=warnings,
            recommendations=recommendations,
            allowed_overrides=allowed_overrides
        )
    
    def _process_historical_financials(
        self,
        historical: Optional[DCFHistoricalFinancials],
        raw_historical: Dict[str, Any]
    ) -> HistoricalFinancialsDisplay:
        """Process historical financials with status tracking"""
        
        def create_data_field(field_name: str, value: Any, source: str = "yfinance") -> DataField:
            if value is not None:
                return DataField(
                    field_name=field_name,
                    value=value,
                    status=DataStatus.RETRIEVED,
                    source=source,
                    is_missing=False
                )
            else:
                return DataField(
                    field_name=field_name,
                    value=None,
                    status=DataStatus.MISSING,
                    source=None,
                    is_missing=True,
                    requires_manual_input=True
                )
        
        if not historical:
            return HistoricalFinancialsDisplay()
        
        # Process each field
        revenue_field = create_data_field("revenue", historical.revenue)
        cogs_field = create_data_field("cogs", historical.cogs)
        ebitda_field = create_data_field("ebitda", historical.ebitda)
        net_income_field = create_data_field("net_income", historical.net_income)
        operating_expenses_field = create_data_field("operating_expenses", historical.operating_expenses)
        depreciation_field = create_data_field("depreciation", historical.depreciation)
        capex_field = create_data_field("capex", historical.capex)
        fcf_field = create_data_field("free_cash_flow", historical.free_cash_flow)
        total_assets_field = create_data_field("total_assets", historical.total_assets)
        total_debt_field = create_data_field("total_debt", historical.total_debt)
        cash_field = create_data_field("cash_and_equivalents", historical.cash_and_equivalents)
        equity_field = create_data_field("shareholders_equity", historical.shareholders_equity)
        
        # Calculated metrics
        revenue_cagr_field = DataField(
            field_name="revenue_cagr",
            value=historical.revenue_cagr,
            status=DataStatus.CALCULATED if historical.revenue_cagr else DataStatus.MISSING,
            source="calculated",
            calculation_formula="((Ending Revenue / Beginning Revenue) ^ (1/Years)) - 1",
            is_missing=historical.revenue_cagr is None
        )
        
        avg_ebitda_margin_field = DataField(
            field_name="avg_ebitda_margin",
            value=historical.avg_ebitda_margin,
            status=DataStatus.CALCULATED if historical.avg_ebitda_margin else DataStatus.MISSING,
            source="calculated",
            calculation_formula="Average(EBITDA / Revenue)",
            is_missing=historical.avg_ebitda_margin is None
        )
        
        avg_roe_field = DataField(
            field_name="avg_roe",
            value=historical.avg_roe,
            status=DataStatus.CALCULATED if historical.avg_roe else DataStatus.MISSING,
            source="calculated",
            calculation_formula="Average(Net Income / Shareholders Equity)",
            is_missing=historical.avg_roe is None
        )
        
        return HistoricalFinancialsDisplay(
            revenue=revenue_field,
            cogs=cogs_field,
            ebitda=ebitda_field,
            net_income=net_income_field,
            operating_expenses=operating_expenses_field,
            depreciation=depreciation_field,
            capex=capex_field,
            free_cash_flow=fcf_field,
            total_assets=total_assets_field,
            total_debt=total_debt_field,
            cash_and_equivalents=cash_field,
            shareholders_equity=equity_field,
            revenue_cagr=revenue_cagr_field,
            avg_ebitda_margin=avg_ebitda_margin_field,
            avg_roe=avg_roe_field
        )
    
    def _process_forecast_drivers(
        self,
        forecast: Optional[DCFForecastDrivers],
        raw_forecast: Dict[str, Any]
    ) -> ForecastDriversDisplay:
        """Process forecast drivers with status tracking"""
        
        def create_data_field(field_name: str, value: Any, formula: Optional[str] = None) -> DataField:
            if value is not None:
                status = DataStatus.MANUAL_OVERRIDE if field_name in raw_forecast else DataStatus.ESTIMATED
                return DataField(
                    field_name=field_name,
                    value=value,
                    status=status,
                    source="user_input" if status == DataStatus.MANUAL_OVERRIDE else "ai_estimate",
                    is_missing=False,
                    calculation_formula=formula,
                    confidence_score=0.9 if status == DataStatus.MANUAL_OVERRIDE else 0.7
                )
            else:
                return DataField(
                    field_name=field_name,
                    value=None,
                    status=DataStatus.MISSING,
                    is_missing=True,
                    requires_manual_input=True
                )
        
        if not forecast:
            return ForecastDriversDisplay()
        
        return ForecastDriversDisplay(
            revenue_growth_forecast=create_data_field(
                "revenue_growth_forecast",
                forecast.revenue_growth_forecast,
                "User/AI provided growth rates for FY1-FY5 + Terminal"
            ),
            volume_growth_split=create_data_field(
                "volume_growth_split",
                forecast.volume_growth_split,
                "Split between volume vs price growth"
            ),
            inflation_rate=create_data_field(
                "inflation_rate",
                forecast.inflation_rate,
                "Inflation assumption for COGS/OpEx projections"
            ),
            ebitda_margin_forecast=create_data_field(
                "ebitda_margin_forecast",
                forecast.ebitda_margin_forecast
            ),
            tax_rate=create_data_field(
                "tax_rate",
                forecast.tax_rate,
                "Corporate tax rate applied to EBIT"
            ),
            capex_pct_of_revenue=create_data_field(
                "capex_pct_of_revenue",
                forecast.capex_pct_of_revenue,
                "CapEx = Revenue × CapEx %"
            ),
            ar_days=create_data_field(
                "ar_days",
                forecast.ar_days,
                "Accounts Receivable = (Revenue / 365) × AR Days"
            ),
            inv_days=create_data_field(
                "inv_days",
                forecast.inv_days,
                "Inventory = (COGS / 365) × Inventory Days"
            ),
            ap_days=create_data_field(
                "ap_days",
                forecast.ap_days,
                "Accounts Payable = (COGS / 365) × AP Days"
            ),
            risk_free_rate=create_data_field(
                "risk_free_rate",
                forecast.risk_free_rate,
                "10-year government bond yield"
            ),
            equity_risk_premium=create_data_field(
                "equity_risk_premium",
                forecast.equity_risk_premium,
                "Market risk premium for equity"
            ),
            beta=create_data_field(
                "beta",
                forecast.beta,
                "Stock beta vs market"
            ),
            cost_of_debt=create_data_field(
                "cost_of_debt",
                forecast.cost_of_debt,
                "Pre-tax cost of debt"
            ),
            wacc=create_data_field(
                "wacc",
                forecast.wacc,
                "WACC = (E/V × Re) + (D/V × Rd × (1-T))"
            ),
            terminal_growth_rate=create_data_field(
                "terminal_growth_rate",
                forecast.terminal_growth_rate,
                "Perpetual growth rate for terminal value"
            ),
            terminal_ebitda_multiple=create_data_field(
                "terminal_ebitda_multiple",
                forecast.terminal_ebitda_multiple,
                "Exit multiple for terminal value"
            )
        )
    
    def _process_market_data(
        self,
        market: Optional[DCFMarketData],
        raw_market: Dict[str, Any]
    ) -> MarketDataDisplay:
        """Process market data with status tracking"""
        
        def create_data_field(field_name: str, value: Any) -> DataField:
            if value is not None:
                return DataField(
                    field_name=field_name,
                    value=value,
                    status=DataStatus.RETRIEVED,
                    source="yfinance",
                    is_missing=False
                )
            else:
                return DataField(
                    field_name=field_name,
                    value=None,
                    status=DataStatus.MISSING,
                    is_missing=True,
                    requires_manual_input=True
                )
        
        if not market:
            return MarketDataDisplay()
        
        return MarketDataDisplay(
            current_stock_price=create_data_field("current_stock_price", market.current_stock_price),
            shares_outstanding=create_data_field("shares_outstanding", market.shares_outstanding),
            market_cap=create_data_field("market_cap", market.market_cap),
            beta=create_data_field("beta", market.beta),
            total_debt=create_data_field("total_debt", market.total_debt),
            cash=create_data_field("cash", market.cash)
        )
    
    def _process_calculated_metrics(
        self,
        metrics: Dict[str, Any]
    ) -> CalculatedMetricsDisplay:
        """Process calculated valuation metrics"""
        
        def create_calc_field(field_name: str, value: Any, formula: str) -> DataField:
            return DataField(
                field_name=field_name,
                value=value,
                status=DataStatus.CALCULATED if value is not None else DataStatus.MISSING,
                source="dcf_engine",
                calculation_formula=formula,
                is_missing=value is None
            )
        
        return CalculatedMetricsDisplay(
            wacc=create_calc_field(
                "wacc",
                metrics.get("wacc"),
                "WACC = (E/V × Re) + (D/V × Rd × (1-T))"
            ),
            terminal_value=create_calc_field(
                "terminal_value",
                metrics.get("terminal_value"),
                "TV = FCF_n × (1+g) / (WACC-g) OR TV = EBITDA_n × Multiple"
            ),
            enterprise_value=create_calc_field(
                "enterprise_value",
                metrics.get("enterprise_value"),
                "EV = PV(FCF) + PV(Terminal Value)"
            ),
            equity_value=create_calc_field(
                "equity_value",
                metrics.get("equity_value"),
                "Equity Value = EV - Debt + Cash"
            ),
            fair_value_per_share=create_calc_field(
                "fair_value_per_share",
                metrics.get("fair_value_per_share"),
                "Fair Value = Equity Value / Shares Outstanding"
            ),
            upside_downside=create_calc_field(
                "upside_downside",
                metrics.get("upside_downside"),
                "Upside = (Fair Value - Current Price) / Current Price"
            ),
            projected_revenues=create_calc_field(
                "projected_revenues",
                metrics.get("projected_revenues"),
                "Revenue_n = Revenue_(n-1) × (1 + Growth Rate)"
            ),
            projected_ebitda=create_calc_field(
                "projected_ebitda",
                metrics.get("projected_ebitda"),
                "EBITDA_n = Revenue_n × EBITDA Margin"
            ),
            projected_ucff=create_calc_field(
                "projected_ucff",
                metrics.get("projected_ucff"),
                "UFCF = EBIT×(1-T) + D&A - CapEx - ΔNWC"
            ),
            pv_of_fcf=create_calc_field(
                "pv_of_fcf",
                metrics.get("pv_of_fcf"),
                "PV = Σ(FCF_n / (1+WACC)^n)"
            )
        )
    
    def _generate_missing_data_summary(
        self,
        historical: HistoricalFinancialsDisplay,
        forecast: ForecastDriversDisplay,
        market: MarketDataDisplay,
        critical_fields: List[str]
    ) -> MissingDataSummary:
        """Generate summary of missing data"""
        
        total_fields = 0
        retrieved_count = 0
        calculated_count = 0
        missing_count = 0
        manual_override_count = 0
        
        critical_missing = []
        optional_missing = []
        
        # Count fields in each section
        for section in [historical, forecast, market]:
            for field_name, field_obj in section.__dict__.items():
                if isinstance(field_obj, DataField):
                    total_fields += 1
                    
                    if field_obj.status == DataStatus.RETRIEVED:
                        retrieved_count += 1
                    elif field_obj.status == DataStatus.CALCULATED:
                        calculated_count += 1
                    elif field_obj.status == DataStatus.MANUAL_OVERRIDE:
                        manual_override_count += 1
                        retrieved_count += 1  # Count as retrieved since user provided
                    elif field_obj.status == DataStatus.MISSING:
                        missing_count += 1
                        if field_name in critical_fields:
                            critical_missing.append(field_name)
                        else:
                            optional_missing.append(field_name)
        
        completion_percentage = ((retrieved_count + calculated_count + manual_override_count) / total_fields * 100) if total_fields > 0 else 0
        ready_for_valuation = len(critical_missing) == 0 and completion_percentage >= 70
        
        return MissingDataSummary(
            total_fields=total_fields,
            retrieved_count=retrieved_count,
            calculated_count=calculated_count,
            missing_count=missing_count,
            manual_override_count=manual_override_count,
            critical_missing=critical_missing,
            optional_missing=optional_missing,
            completion_percentage=round(completion_percentage, 1),
            ready_for_valuation=ready_for_valuation
        )
    
    def _calculate_data_quality_score(
        self,
        missing_summary: MissingDataSummary,
        historical: HistoricalFinancialsDisplay,
        forecast: ForecastDriversDisplay
    ) -> float:
        """Calculate overall data quality score (0-100)"""
        
        # Base score from completeness
        base_score = missing_summary.completion_percentage
        
        # Penalty for missing critical fields
        critical_penalty = len(missing_summary.critical_missing) * 5
        
        # Bonus for having key historical data (3+ years)
        historical_bonus = 0
        if historical.revenue and historical.revenue.value:
            if isinstance(historical.revenue.value, dict) and len(historical.revenue.value) >= 3:
                historical_bonus = 5
        
        # Penalty for estimated vs manual forecast drivers
        estimate_penalty = 0
        if forecast.revenue_growth_forecast:
            if forecast.revenue_growth_forecast.status == DataStatus.ESTIMATED:
                estimate_penalty = 3
        
        score = base_score - critical_penalty + historical_bonus - estimate_penalty
        return max(0, min(100, round(score, 1)))
    
    def _generate_warnings(
        self,
        historical: HistoricalFinancialsDisplay,
        forecast: ForecastDriversDisplay,
        market: MarketDataDisplay
    ) -> List[str]:
        """Generate data quality warnings"""
        
        warnings = []
        
        # Check for missing critical data
        if historical.revenue and historical.revenue.is_missing:
            warnings.append("Revenue data missing - valuation cannot proceed without historical revenue")
        
        if market.beta and market.beta.is_missing:
            warnings.append("Beta missing - using sector average estimate")
        
        if forecast.tax_rate and forecast.tax_rate.is_missing:
            warnings.append("Tax rate missing - using default 21% corporate rate")
        
        if forecast.risk_free_rate and forecast.risk_free_rate.is_missing:
            warnings.append("Risk-free rate missing - using current 10Y treasury yield")
        
        # Check for data quality issues
        if historical.ebitda and historical.ebitda.value:
            if isinstance(historical.ebitda.value, dict):
                values = [v for v in historical.ebitda.value.values() if v is not None]
                if len(values) > 1:
                    if any(v < 0 for v in values):
                        warnings.append("Negative EBITDA detected in historical periods")
        
        return warnings
    
    def _generate_recommendations(
        self,
        missing_summary: MissingDataSummary,
        warnings: List[str]
    ) -> List[str]:
        """Generate recommendations for improving data quality"""
        
        recommendations = []
        
        if missing_summary.critical_missing:
            recommendations.append(f"Provide manual inputs for critical missing fields: {', '.join(missing_summary.critical_missing[:3])}")
        
        if "Beta missing" in str(warnings):
            recommendations.append("Consider providing custom beta if company has unique risk profile")
        
        if missing_summary.completion_percentage < 80:
            recommendations.append("Improve data completeness by providing additional forecast assumptions")
        
        if not recommendations:
            recommendations.append("Data quality is sufficient for valuation")
        
        return recommendations
    
    def _get_allowed_overrides(
        self,
        forecast: ForecastDriversDisplay,
        market: MarketDataDisplay
    ) -> List[str]:
        """Get list of fields that can be manually overridden"""
        
        allowed = []
        
        # All forecast drivers can be overridden
        for field_name, field_obj in forecast.__dict__.items():
            if isinstance(field_obj, DataField):
                allowed.append(field_name)
        
        # Some market data can be overridden
        overrideable_market_fields = ["beta", "total_debt", "cash"]
        for field_name in overrideable_market_fields:
            allowed.append(field_name)
        
        return allowed
    
    # =========================================================================
    # COMPS ENHANCED PROCESSING
    # =========================================================================
    
    def process_comps_inputs(
        self,
        request: CompsValuationRequest,
        raw_data: Dict[str, Any],
        calculated_metrics: Optional[Dict[str, Any]] = None
    ) -> Step6CompsEnhancedResponse:
        """Process Comps inputs and generate enhanced response"""
        
        session_id = request.session_id
        target_ticker = request.target_ticker
        target_company_name = request.target_company_name
        
        # Process target data
        target_display = self._process_comps_target_data(request)
        
        # Process peer data
        peer_displays = self._process_comps_peer_data(request)
        
        # Process calculated metrics
        calc_metrics = self._process_comps_calculated_metrics(calculated_metrics or {})
        
        # Generate missing data summary
        missing_summary = self._generate_comps_missing_summary(
            target_display,
            peer_displays,
            self.CRITICAL_COMPS_FIELDS
        )
        
        # Calculate data quality score
        data_quality_score = self._calculate_comps_data_quality_score(
            missing_summary,
            len(request.peer_multiples)
        )
        
        # Count outliers removed
        outliers_removed = sum(
            1 for peer in peer_displays
            if peer.is_outlier and peer.is_outlier.value is True
        )
        
        # Generate warnings and recommendations
        warnings = self._generate_comps_warnings(target_display, peer_displays)
        recommendations = self._generate_comps_recommendations(missing_summary, warnings)
        
        # Get allowed overrides
        allowed_overrides = self._get_comps_allowed_overrides()
        
        return Step6CompsEnhancedResponse(
            session_id=session_id,
            target_ticker=target_ticker,
            target_company_name=target_company_name,
            target_data=target_display,
            peer_data=peer_displays,
            calculated_metrics=calc_metrics,
            missing_data_summary=missing_summary,
            data_quality_score=data_quality_score,
            outliers_removed=outliers_removed,
            warnings=warnings,
            recommendations=recommendations,
            allowed_overrides=allowed_overrides
        )
    
    def _process_comps_target_data(
        self,
        request: CompsValuationRequest
    ) -> CompsTargetDataDisplay:
        """Process target company data with status tracking"""
        
        def create_data_field(field_name: str, value: Any) -> DataField:
            if value is not None:
                return DataField(
                    field_name=field_name,
                    value=value,
                    status=DataStatus.RETRIEVED,
                    source="yfinance",
                    is_missing=False
                )
            else:
                return DataField(
                    field_name=field_name,
                    value=None,
                    status=DataStatus.MISSING,
                    is_missing=True,
                    requires_manual_input=True
                )
        
        return CompsTargetDataDisplay(
            ticker=request.target_ticker,
            company_name=request.target_company_name,
            market_cap=create_data_field("market_cap", request.target_market_cap),
            enterprise_value=create_data_field("enterprise_value", request.target_enterprise_value),
            revenue_ltm=create_data_field("revenue_ltm", request.target_revenue_ltm),
            ebitda_ltm=create_data_field("ebitda_ltm", request.target_ebitda_ltm),
            net_income_ltm=create_data_field("net_income_ltm", request.target_net_income_ltm),
            eps_ltm=create_data_field("eps_ltm", request.target_eps_ltm)
        )
    
    def _process_comps_peer_data(
        self,
        request: CompsValuationRequest
    ) -> List[CompsPeerDataDisplay]:
        """Process peer company data with status tracking"""
        
        peer_displays = []
        
        for peer in request.peer_multiples:
            def create_data_field(field_name: str, value: Any) -> DataField:
                if value is not None:
                    return DataField(
                        field_name=field_name,
                        value=value,
                        status=DataStatus.RETRIEVED,
                        source="yfinance",
                        is_missing=False
                    )
                else:
                    return DataField(
                        field_name=field_name,
                        value=None,
                        status=DataStatus.MISSING,
                        is_missing=True
                    )
            
            peer_display = CompsPeerDataDisplay(
                ticker=peer.ticker,
                company_name=peer.company_name,
                ev_ebitda_ltm=create_data_field("ev_ebitda_ltm", peer.ev_ebitda_ltm),
                ev_ebitda_fy1=create_data_field("ev_ebitda_fy1", peer.ev_ebitda_fy1),
                pe_ratio_ltm=create_data_field("pe_ratio_ltm", peer.pe_ratio_ltm),
                pe_ratio_fy1=create_data_field("pe_ratio_fy1", peer.pe_ratio_fy1),
                ev_revenue_ltm=create_data_field("ev_revenue_ltm", peer.ev_revenue_ltm),
                pb_ratio=create_data_field("pb_ratio", peer.pb_ratio),
                selection_reason=peer.selection_reason,
                is_outlier=None  # Will be set by IQR filtering logic
            )
            
            peer_displays.append(peer_display)
        
        return peer_displays
    
    def _process_comps_calculated_metrics(
        self,
        metrics: Dict[str, Any]
    ) -> CompsCalculatedMetricsDisplay:
        """Process calculated comps metrics"""
        
        def create_calc_field(field_name: str, value: Any, formula: str) -> DataField:
            return DataField(
                field_name=field_name,
                value=value,
                status=DataStatus.CALCULATED if value is not None else DataStatus.MISSING,
                source="comps_engine",
                calculation_formula=formula,
                is_missing=value is None
            )
        
        return CompsCalculatedMetricsDisplay(
            median_ev_ebitda=create_calc_field(
                "median_ev_ebitda",
                metrics.get("median_ev_ebitda"),
                "Median of peer EV/EBITDA multiples"
            ),
            mean_ev_ebitda=create_calc_field(
                "mean_ev_ebitda",
                metrics.get("mean_ev_ebitda"),
                "Mean of peer EV/EBITDA multiples"
            ),
            median_pe_ratio=create_calc_field(
                "median_pe_ratio",
                metrics.get("median_pe_ratio"),
                "Median of peer P/E multiples"
            ),
            mean_pe_ratio=create_calc_field(
                "mean_pe_ratio",
                metrics.get("mean_pe_ratio"),
                "Mean of peer P/E multiples"
            ),
            implied_ev_ebitda=create_calc_field(
                "implied_ev_ebitda",
                metrics.get("implied_ev_ebitda"),
                "Implied EV = Target EBITDA × Median Multiple"
            ),
            implied_pe_ratio=create_calc_field(
                "implied_pe_ratio",
                metrics.get("implied_pe_ratio"),
                "Implied P/E based on peer median"
            ),
            implied_market_cap=create_calc_field(
                "implied_market_cap",
                metrics.get("implied_market_cap"),
                "Implied Market Cap from comparable analysis"
            ),
            implied_share_price=create_calc_field(
                "implied_share_price",
                metrics.get("implied_share_price"),
                "Implied Share Price = Implied Market Cap / Shares Outstanding"
            ),
            upside_downside=create_calc_field(
                "upside_downside",
                metrics.get("upside_downside"),
                "Upside = (Implied Price - Current Price) / Current Price"
            )
        )
    
    def _generate_comps_missing_summary(
        self,
        target: CompsTargetDataDisplay,
        peers: List[CompsPeerDataDisplay],
        critical_fields: List[str]
    ) -> MissingDataSummary:
        """Generate missing data summary for Comps"""
        
        total_fields = 0
        retrieved_count = 0
        calculated_count = 0
        missing_count = 0
        manual_override_count = 0
        critical_missing = []
        optional_missing = []
        
        # Count target fields
        for field_name, field_obj in target.__dict__.items():
            if isinstance(field_obj, DataField):
                total_fields += 1
                if field_obj.status == DataStatus.RETRIEVED:
                    retrieved_count += 1
                elif field_obj.status == DataStatus.MISSING:
                    missing_count += 1
                    if field_name in critical_fields:
                        critical_missing.append(f"target_{field_name}")
                    else:
                        optional_missing.append(f"target_{field_name}")
        
        # Count peer fields (sample first 5 peers for efficiency)
        sample_peers = peers[:min(5, len(peers))]
        for peer in sample_peers:
            for field_name, field_obj in peer.__dict__.items():
                if isinstance(field_obj, DataField):
                    total_fields += 1
                    if field_obj.status == DataStatus.RETRIEVED:
                        retrieved_count += 1
                    elif field_obj.status == DataStatus.MISSING:
                        missing_count += 1
        
        completion_percentage = ((retrieved_count + calculated_count + manual_override_count) / total_fields * 100) if total_fields > 0 else 0
        ready_for_valuation = len(critical_missing) == 0 and completion_percentage >= 60 and len(peers) >= 3
        
        return MissingDataSummary(
            total_fields=total_fields,
            retrieved_count=retrieved_count,
            calculated_count=calculated_count,
            missing_count=missing_count,
            manual_override_count=manual_override_count,
            critical_missing=critical_missing,
            optional_missing=optional_missing,
            completion_percentage=round(completion_percentage, 1),
            ready_for_valuation=ready_for_valuation
        )
    
    def _calculate_comps_data_quality_score(
        self,
        missing_summary: MissingDataSummary,
        peer_count: int
    ) -> float:
        """Calculate Comps data quality score"""
        
        base_score = missing_summary.completion_percentage
        
        # Bonus for having more peers
        peer_bonus = min(10, peer_count * 2)  # Max 10 points bonus
        
        # Penalty for missing target data
        target_penalty = len([f for f in missing_summary.critical_missing if f.startswith("target_")]) * 5
        
        score = base_score + peer_bonus - target_penalty
        return max(0, min(100, round(score, 1)))
    
    def _generate_comps_warnings(
        self,
        target: CompsTargetDataDisplay,
        peers: List[CompsPeerDataDisplay]
    ) -> List[str]:
        """Generate Comps warnings"""
        
        warnings = []
        
        if target.ebitda_ltm and target.ebitda_ltm.is_missing:
            warnings.append("Target EBITDA missing - cannot calculate implied valuations")
        
        if len(peers) < 3:
            warnings.append(f"Only {len(peers)} peers available - recommend at least 3 for meaningful comparison")
        
        # Check for outlier multiples
        high_multiples = [
            p.ticker for p in peers
            if p.ev_ebitda_ltm and p.ev_ebitda_ltm.value and p.ev_ebitda_ltm.value > 50
        ]
        if high_multiples:
            warnings.append(f"Extremely high EV/EBITDA multiples detected for: {', '.join(high_multiples)}")
        
        return warnings
    
    def _generate_comps_recommendations(
        self,
        missing_summary: MissingDataSummary,
        warnings: List[str]
    ) -> List[str]:
        """Generate Comps recommendations"""
        
        recommendations = []
        
        if "Only" in str(warnings) and "peers available" in str(warnings):
            recommendations.append("Add more peer companies for better statistical significance")
        
        if missing_summary.critical_missing:
            recommendations.append(f"Provide manual inputs for: {', '.join(missing_summary.critical_missing[:3])}")
        
        if not recommendations:
            recommendations.append("Data quality is sufficient for comparable companies analysis")
        
        return recommendations
    
    def _get_comps_allowed_overrides(self) -> List[str]:
        """Get allowed override fields for Comps"""
        
        return [
            "target_market_cap",
            "target_enterprise_value",
            "target_revenue_ltm",
            "target_ebitda_ltm",
            "target_net_income_ltm",
            "apply_outlier_filtering",
            "iqr_multiplier"
        ]
    
    # =========================================================================
    # DUPONT ENHANCED PROCESSING
    # =========================================================================
    
    def process_dupont_inputs(
        self,
        request: DuPontRequest,
        raw_data: Dict[str, Any],
        calculated_metrics: Optional[Dict[str, Any]] = None
    ) -> Step6DuPontEnhancedResponse:
        """Process DuPont inputs and generate enhanced response"""
        
        session_id = request.session_id
        ticker = request.ticker
        
        # Process DuPont components
        dupont_display = self._process_dupont_components(request)
        
        # Process trend analysis if multi-year data available
        trend_display = self._process_dupont_trend_analysis(request, raw_data)
        
        # Generate missing data summary
        missing_summary = self._generate_dupont_missing_summary(
            dupont_display,
            self.CRITICAL_DUPONT_FIELDS
        )
        
        # Calculate data quality score
        data_quality_score = self._calculate_dupont_data_quality_score(
            missing_summary,
            dupont_display
        )
        
        # Generate warnings and recommendations
        warnings = self._generate_dupont_warnings(dupont_display)
        recommendations = self._generate_dupont_recommendations(missing_summary, warnings)
        
        # Get allowed overrides
        allowed_overrides = self._get_dupont_allowed_overrides()
        
        return Step6DuPontEnhancedResponse(
            session_id=session_id,
            ticker=ticker,
            company_name=request.company_name if hasattr(request, 'company_name') else None,
            dupont_components=dupont_display,
            trend_analysis=trend_display,
            missing_data_summary=missing_summary,
            data_quality_score=data_quality_score,
            warnings=warnings,
            recommendations=recommendations,
            allowed_overrides=allowed_overrides
        )
    
    def _process_dupont_components(
        self,
        request: DuPontRequest
    ) -> DuPontComponentsDisplay:
        """Process DuPont components with status tracking"""
        
        def create_data_field(field_name: str, value: Any, formula: Optional[str] = None) -> DataField:
            if value is not None:
                return DataField(
                    field_name=field_name,
                    value=value,
                    status=DataStatus.RETRIEVED if field_name in ["net_income", "revenue", "total_assets", "shareholders_equity"] else DataStatus.CALCULATED,
                    source="yfinance" if field_name in ["net_income", "revenue", "total_assets", "shareholders_equity"] else "calculated",
                    calculation_formula=formula,
                    is_missing=False
                )
            else:
                return DataField(
                    field_name=field_name,
                    value=None,
                    status=DataStatus.MISSING,
                    is_missing=True,
                    requires_manual_input=True,
                    calculation_formula=formula
                )
        
        # Get custom ratios if provided
        custom_ratios = request.custom_ratios if hasattr(request, 'custom_ratios') else None
        
        return DuPontComponentsDisplay(
            net_profit_margin=create_data_field(
                "net_profit_margin",
                custom_ratios.net_profit_margin if custom_ratios and custom_ratios.net_profit_margin else None,
                "Net Profit Margin = Net Income / Revenue"
            ),
            asset_turnover=create_data_field(
                "asset_turnover",
                custom_ratios.asset_turnover if custom_ratios and custom_ratios.asset_turnover else None,
                "Asset Turnover = Revenue / Total Assets"
            ),
            equity_multiplier=create_data_field(
                "equity_multiplier",
                custom_ratios.equity_multiplier if custom_ratios and custom_ratios.equity_multiplier else None,
                "Equity Multiplier = Total Assets / Shareholders Equity"
            ),
            roe=create_data_field(
                "roe",
                custom_ratios.roe if custom_ratios and custom_ratios.roe else None,
                "ROE = Net Profit Margin × Asset Turnover × Equity Multiplier"
            ),
            net_income=create_data_field(
                "net_income",
                custom_ratios.net_income if custom_ratios and custom_ratios.net_income else None
            ),
            revenue=create_data_field(
                "revenue",
                custom_ratios.revenue if custom_ratios and custom_ratios.revenue else None
            ),
            total_assets=create_data_field(
                "total_assets",
                custom_ratios.total_assets if custom_ratios and custom_ratios.total_assets else None
            ),
            shareholders_equity=create_data_field(
                "shareholders_equity",
                custom_ratios.shareholders_equity if custom_ratios and custom_ratios.shareholders_equity else None
            )
        )
    
    def _process_dupont_trend_analysis(
        self,
        request: DuPontRequest,
        raw_data: Dict[str, Any]
    ) -> Optional[DuPontTrendAnalysisDisplay]:
        """Process multi-year DuPont trend analysis"""
        
        # Check if we have multi-year data
        years = request.years if hasattr(request, 'years') else []
        
        if not years or len(years) < 2:
            return None
        
        # For now, return basic structure - would need historical DuPont data
        return DuPontTrendAnalysisDisplay(
            years=years,
            roe_trend=DataField(
                field_name="roe_trend",
                value=None,
                status=DataStatus.MISSING,
                is_missing=True,
                notes="Multi-year DuPont data not available"
            )
        )
    
    def _generate_dupont_missing_summary(
        self,
        dupont: DuPontComponentsDisplay,
        critical_fields: List[str]
    ) -> MissingDataSummary:
        """Generate DuPont missing data summary"""
        
        total_fields = 0
        retrieved_count = 0
        calculated_count = 0
        missing_count = 0
        manual_override_count = 0
        critical_missing = []
        optional_missing = []
        
        for field_name, field_obj in dupont.__dict__.items():
            if isinstance(field_obj, DataField):
                total_fields += 1
                
                if field_obj.status == DataStatus.RETRIEVED:
                    retrieved_count += 1
                elif field_obj.status == DataStatus.CALCULATED:
                    calculated_count += 1
                elif field_obj.status == DataStatus.MANUAL_OVERRIDE:
                    manual_override_count += 1
                    retrieved_count += 1
                elif field_obj.status == DataStatus.MISSING:
                    missing_count += 1
                    if field_name in critical_fields:
                        critical_missing.append(field_name)
                    else:
                        optional_missing.append(field_name)
        
        completion_percentage = ((retrieved_count + calculated_count + manual_override_count) / total_fields * 100) if total_fields > 0 else 0
        ready_for_valuation = len(critical_missing) == 0 and completion_percentage >= 75
        
        return MissingDataSummary(
            total_fields=total_fields,
            retrieved_count=retrieved_count,
            calculated_count=calculated_count,
            missing_count=missing_count,
            manual_override_count=manual_override_count,
            critical_missing=critical_missing,
            optional_missing=optional_missing,
            completion_percentage=round(completion_percentage, 1),
            ready_for_valuation=ready_for_valuation
        )
    
    def _calculate_dupont_data_quality_score(
        self,
        missing_summary: MissingDataSummary,
        dupont: DuPontComponentsDisplay
    ) -> float:
        """Calculate DuPont data quality score"""
        
        base_score = missing_summary.completion_percentage
        
        # Bonus if all 4 main components are present
        component_bonus = 0
        required_components = ["net_profit_margin", "asset_turnover", "equity_multiplier", "roe"]
        present_components = sum(
            1 for comp in required_components
            if getattr(dupont, comp) and not getattr(dupont, comp).is_missing
        )
        
        if present_components == 4:
            component_bonus = 10
        elif present_components >= 3:
            component_bonus = 5
        
        score = base_score + component_bonus
        return max(0, min(100, round(score, 1)))
    
    def _generate_dupont_warnings(
        self,
        dupont: DuPontComponentsDisplay
    ) -> List[str]:
        """Generate DuPont warnings"""
        
        warnings = []
        
        if dupont.net_income and dupont.net_income.is_missing:
            warnings.append("Net income data missing - cannot calculate ROE decomposition")
        
        if dupont.revenue and dupont.revenue.is_missing:
            warnings.append("Revenue data missing - cannot calculate profit margin")
        
        if dupont.roe and dupont.roe.value and dupont.roe.value < 0:
            warnings.append("Negative ROE detected - company may be unprofitable")
        
        return warnings
    
    def _generate_dupont_recommendations(
        self,
        missing_summary: MissingDataSummary,
        warnings: List[str]
    ) -> List[str]:
        """Generate DuPont recommendations"""
        
        recommendations = []
        
        if missing_summary.critical_missing:
            recommendations.append(f"Provide manual inputs for: {', '.join(missing_summary.critical_missing[:3])}")
        
        if "Negative ROE" in str(warnings):
            recommendations.append("Analyze which DuPont component is driving negative ROE")
        
        if not recommendations:
            recommendations.append("Data quality is sufficient for DuPont analysis")
        
        return recommendations
    
    def _get_dupont_allowed_overrides(self) -> List[str]:
        """Get allowed override fields for DuPont"""
        
        return [
            "net_profit_margin",
            "asset_turnover",
            "equity_multiplier",
            "net_income",
            "revenue",
            "total_assets",
            "shareholders_equity"
        ]


# Singleton instance
step6_processor = Step6EnhancedProcessor()
