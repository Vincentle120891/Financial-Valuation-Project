"""
DCF Input Manager - Handles inputs from API, AI, or Manual sources
Provides unified interface for building DCFInputs with full source tracking

This service layer bridges the gap between:
1. Pydantic input models (international_inputs.py) - API validation
2. Engine dataclasses (dcf_engine.py) - Calculation logic
3. Multiple data sources (API, AI, Manual)

All inputs are tracked with source metadata for auditability.
"""

from typing import Dict, Any, List, Optional, Union
from datetime import date
import logging

logger = logging.getLogger(__name__)

from app.models.international.international_inputs import (
    DCFHistoricalFinancials,
    DCFForecastDrivers,
    DCFMarketData,
    InternationalFinancialInputs,
    # DuPont models
    DuPontRequest,
    DuPontComponents,
    DuPontAnalysisRequest,
    DuPontCustomInputs,
    # Comps models
    CompsSelectionRequest,
    CompsValuationRequest,
    CompsAnalysisRequest,
    PeerMultiple,
    CompsTargetCompany,
    CompsPeerCompany
)
from app.engines.international.dcf_engine import (
    DCFInputs, ScenarioDrivers, ComparableCompany, 
    InputWithMetadata, InputSource
)


class DCFInputManager:
    """
    Manages DCF input construction from multiple sources:
    - API: Financial data from yFinance, Alpha Vantage, etc.
    - AI: Forecast assumptions from LLM engines
    - Manual: User-provided overrides
    
    All inputs are tracked with source metadata for auditability.
    """
    
    def __init__(self):
        self.api_data: Dict[str, Any] = {}
        self.ai_assumptions: Dict[str, Any] = {}
        self.manual_overrides: Dict[str, Any] = {}
        
    def load_api_data(self, financial_data: Dict[str, Any]) -> 'DCFInputManager':
        """
        Load financial data from API (yFinance, Alpha Vantage, etc.)
        
        Expected structure matches fetch_financial_data() output:
        {
            "profile": {
                "symbol": "AAPL",
                "current_price": 150.0,
                "sharesOutstanding": 16000000,
                "totalDebt": 120000000,
                "cash": 50000000,
                "totalAssets": 350000000,
                ...
            },
            "financials": {
                "revenue": {"2022": 394328, "2021": 365817, "2020": 274515},
                "ebitda": {...},
                "net_income": {...},
                ...
            },
            "historical_financials": {
                "revenue": {...},
                "cogs": {...},
                ...
            }
        }
        """
        self.api_data = financial_data
        return self
    
    def load_ai_assumptions(self, ai_results: Dict[str, Any]) -> 'DCFInputManager':
        """
        Load AI-generated assumptions with rationale and sources.
        
        Expected structure from generate_ai_assumptions():
        {
            "wacc_percent": {"value": 8.5, "rationale": "...", "sources": "..."},
            "terminal_growth_rate_percent": {"value": 2.0, ...},
            "revenue_growth_forecast": [{"value": 5.0, ...}, ...],
            ...
        }
        """
        self.ai_assumptions = ai_results
        return self
    
    def apply_manual_override(self, key: str, value: Any, rationale: str = "Manual override") -> 'DCFInputManager':
        """
        Apply manual override to any input parameter.
        """
        self.manual_overrides[key] = {
            "value": value,
            "source": InputSource.MANUAL,
            "rationale": rationale,
            "sources": "User Input"
        }
        return self
    
    def _create_input_with_source(self, key: str, default_value: Any) -> InputWithMetadata:
        """
        Create InputWithMetadata by checking sources in priority order:
        Manual > AI > API > Default
        """
        # Check manual overrides first (highest priority)
        if key in self.manual_overrides:
            override = self.manual_overrides[key]
            return InputWithMetadata(
                value=override.get("value", default_value),
                source=override.get("source", InputSource.MANUAL),
                rationale=override.get("rationale", "Manual override"),
                sources=override.get("sources", "User Input")
            )
        
        # Check AI assumptions
        if key in self.ai_assumptions:
            ai_item = self.ai_assumptions[key]
            if isinstance(ai_item, dict) and "value" in ai_item:
                return InputWithMetadata(
                    value=ai_item["value"],
                    source=InputSource.AI,
                    rationale=ai_item.get("rationale", "AI-generated"),
                    sources=ai_item.get("sources", "AI Engine")
                )
            else:
                return InputWithMetadata(
                    value=ai_item,
                    source=InputSource.AI,
                    rationale="AI-generated",
                    sources="AI Engine"
                )
        
        # Check API data
        if key in self.api_data:
            api_value = self.api_data[key]
            return InputWithMetadata(
                value=api_value,
                source=InputSource.API,
                rationale="From financial API",
                sources=f"API: {self.api_data.get('source', 'Unknown')}"
            )
        
        # Return default
        return InputWithMetadata(
            value=default_value,
            source=InputSource.DEFAULT,
            rationale="System default",
            sources="Default Configuration"
        )
    
    def _extract_historical_from_api(self) -> DCFHistoricalFinancials:
        """Extract historical financials from API data into Pydantic model."""
        historical = self.api_data.get("historical_financials", {})
        
        return DCFHistoricalFinancials(
            revenue=historical.get("revenue", {}),
            cogs=historical.get("cogs", {}),
            ebitda=historical.get("ebitda", {}),
            net_income=historical.get("net_income", {}),
            operating_expenses=historical.get("operating_expenses", {}),
            sg_and_a=historical.get("sg_and_a", {}),
            depreciation=historical.get("depreciation", {}),
            capex=historical.get("capex", {}),
            free_cash_flow=historical.get("free_cash_flow", {}),
            total_assets=historical.get("total_assets", {}),
            total_debt=historical.get("total_debt", {}),
            cash_and_equivalents=historical.get("cash_and_equivalents", {}),
            inventory=historical.get("inventory", {}),
            accounts_receivable=historical.get("accounts_receivable", {}),
            accounts_payable=historical.get("accounts_payable", {}),
            shareholders_equity=historical.get("shareholders_equity", {}),
            revenue_cagr=historical.get("revenue_cagr"),
            avg_ebitda_margin=historical.get("avg_ebitda_margin"),
            avg_roe=historical.get("avg_roe")
        )
    
    def _extract_market_data_from_api(self) -> DCFMarketData:
        """Extract market data from API into Pydantic model."""
        profile = self.api_data.get("profile", {})
        info = profile.get("raw_info", {})
        
        return DCFMarketData(
            current_stock_price=profile.get("current_price"),
            shares_outstanding=info.get("sharesOutstanding"),
            market_cap=profile.get("market_cap"),
            beta=profile.get("beta"),
            total_debt=info.get("totalDebt"),
            cash=info.get("cash", info.get("totalCash")),
            currency=profile.get("currency", "USD")
        )
    
    def _build_scenario_drivers_from_ai(self) -> ScenarioDrivers:
        """Build ScenarioDrivers from AI assumptions."""
        drivers = ScenarioDrivers()
        
        # Revenue volume growth forecast (directly from AI, not split)
        volume_growth_forecast = self.ai_assumptions.get("revenue_volume_growth", [])
        if volume_growth_forecast:
            volume_growth = []
            for item in volume_growth_forecast[:5]:
                growth_rate = item.get("value", 0.0) / 100 if isinstance(item, dict) else item / 100
                volume_growth.append(growth_rate)
            # Add terminal year (half of last year)
            volume_growth.append(volume_growth[-1] * 0.5 if volume_growth else 0.005)
            drivers.volume_growth = volume_growth
        
        # Revenue price growth forecast (directly from AI)
        price_growth_forecast = self.ai_assumptions.get("revenue_price_growth", [])
        if price_growth_forecast:
            price_growth = []
            for item in price_growth_forecast[:5]:
                growth_rate = item.get("value", 0.0) / 100 if isinstance(item, dict) else item / 100
                price_growth.append(growth_rate)
            # Add terminal year (half of last year)
            price_growth.append(price_growth[-1] * 0.5 if price_growth else 0.005)
            drivers.price_growth = price_growth
        
        # Terminal growth rate
        tg_item = self.ai_assumptions.get("terminal_growth_rate_percent", {})
        if isinstance(tg_item, dict) and "value" in tg_item:
            drivers.terminal_growth_rate = tg_item["value"] / 100
        elif isinstance(tg_item, (int, float)):
            drivers.terminal_growth_rate = tg_item / 100
        
        # Terminal EBITDA multiple
        mult_item = self.ai_assumptions.get("terminal_ebitda_multiple", {})
        if isinstance(mult_item, dict) and "value" in mult_item:
            drivers.terminal_ebitda_multiple = mult_item["value"]
        elif isinstance(mult_item, (int, float)):
            drivers.terminal_ebitda_multiple = mult_item
        
        # Capital expenditure (absolute values in USD thousands)
        capex_forecast = self.ai_assumptions.get("capital_expenditure", [])
        if capex_forecast:
            capex_values = []
            for item in capex_forecast[:5]:
                capex_val = item.get("value", 4500.0) if isinstance(item, dict) else item
                capex_values.append(float(capex_val))
            # Add terminal year (slight increase)
            capex_values.append(capex_values[-1] * 1.03 if capex_values else 4500.0)
            drivers.capex = capex_values
        
        # Inflation rate for COGS/OpEx (array of rates per year)
        inflation_forecast = self.ai_assumptions.get("inflation_rate", [])
        if inflation_forecast:
            inflation_rates = []
            for item in inflation_forecast[:6]:
                inf_rate = item.get("value", 2.5) / 100 if isinstance(item, dict) else item / 100
                inflation_rates.append(inf_rate)
            # Ensure we have 6 periods (5 forecast + terminal)
            while len(inflation_rates) < 6:
                inflation_rates.append(inflation_rates[-1] if inflation_rates else 0.025)
            drivers.inflation_rate = inflation_rates
        
        # Working capital days
        ar_days_item = self.ai_assumptions.get("ar_days", {})
        inv_days_item = self.ai_assumptions.get("inv_days", {})
        ap_days_item = self.ai_assumptions.get("ap_days", {})
        
        ar_days_val = ar_days_item.get("value", 45) if isinstance(ar_days_item, dict) else ar_days_item
        inv_days_val = inv_days_item.get("value", 25) if isinstance(inv_days_item, dict) else inv_days_item
        ap_days_val = ap_days_item.get("value", 40) if isinstance(ap_days_item, dict) else ap_days_item
        
        drivers.ar_days = [float(ar_days_val)] * 5
        drivers.inv_days = [float(inv_days_val)] * 5
        drivers.ap_days = [float(ap_days_val)] * 5
        
        return drivers
    
    def build_inputs(self, scenario_name: str = "Base Case") -> DCFInputs:
        """
        Build complete DCFInputs object with all sources integrated.
        
        Priority: Manual Override > AI > API > Default
        
        This method is used when you want to use the Input Manager pattern.
        For direct usage from valuation_routes.py, see build_inputs_from_confirmed_assumptions()
        """
        # Extract data from sources
        historical = self._extract_historical_from_api()
        market_data = self._extract_market_data_from_api()
        
        # Build scenario drivers
        base_scenario = self._build_scenario_drivers_from_ai()
        
        # Get WACC-related inputs
        wacc_item = self._create_input_with_source("wacc_percent", 8.5)
        tax_rate_item = self._create_input_with_source("tax_rate_percent", 21.0)
        risk_free_item = self._create_input_with_source("risk_free_rate", 4.5)
        
        # Convert percentage inputs
        wacc_value = wacc_item.value / 100 if wacc_item.value > 1 else wacc_item.value
        tax_rate_value = tax_rate_item.value / 100 if tax_rate_item.value > 1 else tax_rate_item.value
        risk_free_value = risk_free_item.value / 100 if risk_free_item.value > 1 else risk_free_item.value
        
        # Build DCFInputs
        inputs = DCFInputs(
            # Historical financials from API
            historical_revenue=list(historical.revenue.values()) if historical.revenue else [0.0, 0.0, 0.0],
            historical_cogs=list(historical.cogs.values()) if historical.cogs else [0.0, 0.0, 0.0],
            historical_sga=list(historical.sg_and_a.values()) if historical.sg_and_a else [0.0, 0.0, 0.0],
            historical_other_opex=[h * 0.3 for h in (list(historical.sg_and_a.values()) if historical.sg_and_a else [0.0, 0.0, 0.0])],
            historical_depreciation=list(historical.depreciation.values()) if historical.depreciation else [0.0, 0.0, 0.0],
            historical_interest=[0.0, 0.0, 0.0],  # Would need to extract from financials
            historical_capex=list(historical.capex.values()) if historical.capex else [0.0, 0.0, 0.0],
            
            # Balance sheet from API
            historical_ar=historical.accounts_receivable.get(list(historical.accounts_receivable.keys())[0], 0.0) if historical.accounts_receivable else 0.0,
            historical_inventory=historical.inventory.get(list(historical.inventory.keys())[0], 0.0) if historical.inventory else 0.0,
            historical_ap=historical.accounts_payable.get(list(historical.accounts_payable.keys())[0], 0.0) if historical.accounts_payable else 0.0,
            net_debt_opening=market_data.total_debt - (market_data.cash or 0.0) if market_data.total_debt else 0.0,
            shares_outstanding=market_data.shares_outstanding or 1000000.0,
            current_stock_price=market_data.current_stock_price or 100.0,
            
            # Tax rate from AI/API
            statutory_tax_rate=tax_rate_value,
            
            # WACC market inputs
            risk_free_rate=risk_free_value,
            
            # Scenario drivers
            forecast_drivers={
                "Base Case": base_scenario,
                "Best Case": self._build_scenario_drivers_from_ai(),  # Would adjust upward
                "Worst Case": self._build_scenario_drivers_from_ai()   # Would adjust downward
            }
        )
        
        return inputs
    
    def get_input_audit_trail(self) -> Dict[str, Dict]:
        """
        Generate audit trail showing source of each input.
        """
        audit = {
            "api_data_keys": list(self.api_data.keys()),
            "ai_assumption_keys": list(self.ai_assumptions.keys()),
            "manual_overrides": {
                k: v for k, v in self.manual_overrides.items()
            },
            "source_summary": {
                "total_api_inputs": len([k for k in self.api_data if k]),
                "total_ai_inputs": len(self.ai_assumptions),
                "total_manual_overrides": len(self.manual_overrides)
            }
        }
        return audit


def build_dcf_inputs_from_confirmed_assumptions(
    confirmed_assumptions: Dict[str, Any],
    financial_data: Dict[str, Any],
    profile: Dict[str, Any],
    market: str = "international"
) -> DCFInputs:
    """
    Build DCFInputs directly from confirmed_assumptions (as used in valuation_routes.py).
    
    This function mirrors the logic currently in run_valuation_engine() but makes it
    reusable and testable as a separate service function.
    
    Args:
        confirmed_assumptions: AI/user confirmed assumptions from session
        financial_data: Financial data from yFinance
        profile: Company profile information
        market: Market type (vietnamese or international)
    
    Returns:
        DCFInputs object ready for DCFEngine
    """
    financials = financial_data.get('financials', {})
    
    # Extract historical data
    revenue_history = list(financials.get('revenue', {}).values())
    ebitda_history = list(financials.get('ebitda', {}).values())
    net_income_history = list(financials.get('net_income', {}).values())
    
    info = profile.get('raw_info', {})
    shares_outstanding = info.get('sharesOutstanding', 1000000) or 1000000
    current_price = profile.get('current_price', 100) or 100
    
    total_debt = info.get('totalDebt', 0) or 0
    cash = info.get('cash', info.get('totalCash', 0)) or 0
    net_debt = total_debt - cash
    ppe_net = info.get('totalAssets', 0) or 0
    
    def build_historical_year(rev, ebitda, ni):
        return {
            'revenue': rev or 0,
            'ebitda': ebitda or 0,
            'net_income': ni or 0,
            'cogs': (rev or 0) * 0.6 if rev else 0,
            'sga': (rev or 0) * 0.25 if rev else 0,
            'other_opex': (rev or 0) * 0.05 if rev else 0,
            'accounts_receivable': (rev or 0) * 0.1 if rev else 0,
            'inventory': (rev or 0) * 0.08 if rev else 0,
            'accounts_payable': (rev or 0) * 0.07 if rev else 0
        }
    
    hist_fy_minus_1 = build_historical_year(
        revenue_history[0] if len(revenue_history) > 0 else None,
        ebitda_history[0] if len(ebitda_history) > 0 else None,
        net_income_history[0] if len(net_income_history) > 0 else None
    )
    hist_fy_minus_2 = build_historical_year(
        revenue_history[1] if len(revenue_history) > 1 else None,
        ebitda_history[1] if len(ebitda_history) > 1 else None,
        net_income_history[1] if len(net_income_history) > 1 else None
    )
    hist_fy_minus_3 = build_historical_year(
        revenue_history[2] if len(revenue_history) > 2 else None,
        ebitda_history[2] if len(ebitda_history) > 2 else None,
        net_income_history[2] if len(net_income_history) > 2 else None
    )
    
    # Get forecast drivers from assumptions
    revenue_growth = confirmed_assumptions.get('revenue_growth_forecast', [0.05, 0.05, 0.04, 0.04, 0.03, 0.02])
    while len(revenue_growth) < 6:
        revenue_growth.append(0.02)
    
    wacc = confirmed_assumptions.get('wacc', 0.08)
    terminal_growth = confirmed_assumptions.get('terminal_growth_rate', 0.023)
    terminal_multiple = confirmed_assumptions.get('terminal_ebitda_multiple', 8.0)
    
    volume_split = confirmed_assumptions.get('volume_growth_split', 0.6)
    base_volume_growth = [g * volume_split for g in revenue_growth[:6]]
    base_price_growth = [g * (1 - volume_split) for g in revenue_growth[:6]]
    
    base_drivers = ScenarioDrivers(
        volume_growth=base_volume_growth,
        price_growth=base_price_growth,
        inflation_rate=[confirmed_assumptions.get('inflation_rate', 0.02)] * 6 if not isinstance(confirmed_assumptions.get('inflation_rate'), list) else confirmed_assumptions.get('inflation_rate', [0.02]*6)[:6],
        capex=[hist_fy_minus_1['revenue'] * confirmed_assumptions.get('capex_pct_of_revenue', 0.05)] * 6,
        ar_days=[confirmed_assumptions.get('ar_days', 45)] * 5,
        inv_days=[confirmed_assumptions.get('inv_days', 60)] * 5,
        ap_days=[confirmed_assumptions.get('ap_days', 30)] * 5,
        terminal_ebitda_multiple=terminal_multiple,
        terminal_growth_rate=terminal_growth
    )
    
    dcf_inputs = DCFInputs(
        valuation_date=date.today().isoformat(),
        currency="VND" if market == "vietnamese" else profile.get('currency', 'USD'),
        historical_fy_minus_1=hist_fy_minus_1,
        historical_fy_minus_2=hist_fy_minus_2,
        historical_fy_minus_3=hist_fy_minus_3,
        net_debt=net_debt,
        ppe_net=ppe_net,
        tax_basis_ppe=ppe_net * 0.8,
        tax_losses_nol=0,
        shares_outstanding=shares_outstanding,
        current_stock_price=current_price,
        projected_interest_expense=net_debt * 0.05 if net_debt > 0 else 0,
        useful_life_existing=confirmed_assumptions.get('useful_life_existing', 10.0),
        useful_life_new=confirmed_assumptions.get('useful_life_new', 10.0),
        forecast_drivers={
            "base_case": base_drivers,
            "best_case": base_drivers,
            "worst_case": base_drivers
        },
        wacc=wacc,
        risk_free_rate=confirmed_assumptions.get('risk_free_rate', 0.045),
        equity_risk_premium=confirmed_assumptions.get('equity_risk_premium', 0.055),
        beta=confirmed_assumptions.get('beta', 1.0),
        cost_of_debt=confirmed_assumptions.get('cost_of_debt', 0.05),
        tax_rate_statutory=confirmed_assumptions.get('tax_rate', 0.21),
        tax_loss_utilization_limit_pct=confirmed_assumptions.get('tax_loss_utilization_limit_pct', 0.80)
    )
    
    return dcf_inputs


# Convenience function for quick input creation
def create_dcf_inputs(
    api_data: Optional[Dict] = None,
    ai_assumptions: Optional[Dict] = None,
    manual_overrides: Optional[Dict] = None
) -> DCFInputs:
    """
    Quick helper to create DCFInputs from available sources.
    
    Example:
        inputs = create_dcf_inputs(
            api_data=yfinance_data,
            ai_assumptions=gemini_output,
            manual_overrides={"terminal_growth_rate": 0.025}
        )
    """
    manager = DCFInputManager()
    
    if api_data:
        manager.load_api_data(api_data)
    
    if ai_assumptions:
        manager.load_ai_assumptions(ai_assumptions)
    
    if manual_overrides:
        for key, value in manual_overrides.items():
            manager.apply_manual_override(key, value)
    
    return manager.build_inputs()


# =============================================================================
# COMPS INPUT BUILDER FUNCTIONS
# =============================================================================

def build_comps_selection_inputs(
    target_ticker: str,
    peer_list: Optional[List[str]] = None,
    sector: Optional[str] = None,
    industry: Optional[str] = None,
    max_peers: int = 10
) -> CompsSelectionRequest:
    """
    Validates peer lists and target data for comps selection.
    Returns a typed CompsSelectionRequest for peer selection logic.
    
    Args:
        target_ticker: Target company ticker symbol
        peer_list: Explicit list of peer tickers (optional)
        sector: Sector filter for auto-peer selection
        industry: Industry filter for auto-peer selection
        max_peers: Maximum number of peers to select
    
    Returns:
        CompsSelectionRequest object for peer selection
    """
    return CompsSelectionRequest(
        target_ticker=target_ticker,
        peer_list=peer_list,
        sector=sector,
        industry=industry,
        max_peers=max_peers
    )


def build_comps_valuation_inputs(
    session_id: str,
    target_ticker: str,
    financial_data: Dict[str, Any],
    peer_multiples: Optional[List[Dict[str, Any]]] = None,
    apply_outlier_filtering: bool = True,
    iqr_multiplier: float = 1.5
) -> CompsValuationRequest:
    """
    Validates peer lists and target data, integrates IQR outlier filtering logic,
    and structures data into CompsValuationRequest before passing to Comps engine.
    
    Args:
        session_id: Session identifier
        target_ticker: Target company ticker symbol
        financial_data: Financial data from yFinance
        peer_multiples: List of peer multiple dictionaries
        apply_outlier_filtering: Whether to apply IQR-based outlier filtering
        iqr_multiplier: IQR multiplier for outlier detection
    
    Returns:
        CompsValuationRequest object ready for TradingCompsAnalyzer
    """
    info = financial_data.get('raw_info', {})
    profile = financial_data.get('profile', {})
    
    # Calculate target company metrics
    market_cap = info.get('marketCap', 1000000000) or 1000000000
    enterprise_value = market_cap + (info.get('totalDebt', 0) or 0) - (info.get('cash', 0) or 0)
    
    financials = financial_data.get('financials', {})
    revenue_values = list(financials.get('revenue', {}).values())
    ebitda_values = list(financials.get('ebitda', {}).values())
    
    revenue_ltm = revenue_values[0] if revenue_values else 100000000
    ebitda_ltm = ebitda_values[0] if ebitda_values else revenue_ltm * 0.2
    net_income_ltm = revenue_ltm * 0.1
    eps_ltm = net_income_ltm / (info.get('sharesOutstanding', 1000000) or 1000000) * 1000000
    
    # Parse peer multiples into PeerMultiple objects
    parsed_peer_multiples: List[PeerMultiple] = []
    if peer_multiples:
        for peer in peer_multiples:
            parsed_peer_multiples.append(PeerMultiple(**peer))
    
    return CompsValuationRequest(
        session_id=session_id,
        target_ticker=target_ticker,
        target_company_name=profile.get('name', target_ticker),
        target_market_cap=market_cap,
        target_enterprise_value=enterprise_value,
        target_revenue_ltm=revenue_ltm,
        target_ebitda_ltm=ebitda_ltm,
        target_net_income_ltm=net_income_ltm,
        target_eps_ltm=eps_ltm,
        peer_multiples=parsed_peer_multiples,
        apply_outlier_filtering=apply_outlier_filtering,
        iqr_multiplier=iqr_multiplier,
        include_football_field=True
    )


def apply_iqr_outlier_filtering(
    peer_multiples: List[PeerMultiple],
    metric: str = 'ev_ebitda_ltm',
    iqr_multiplier: float = 1.5
) -> List[PeerMultiple]:
    """
    Applies IQR-based outlier filtering to peer multiples.
    Moved from route layer to service layer for reusability.
    
    Args:
        peer_multiples: List of peer multiples
        metric: Metric name to filter on (e.g., 'ev_ebitda_ltm', 'pe_ratio_ltm')
        iqr_multiplier: IQR multiplier for outlier detection
    
    Returns:
        Filtered list of peer multiples with outliers removed
    """
    if not peer_multiples:
        return []
    
    # Extract metric values
    values = []
    for peer in peer_multiples:
        value = getattr(peer, metric, None)
        if value is not None:
            values.append(value)
    
    if len(values) < 4:  # Need at least 4 data points for meaningful IQR
        return peer_multiples
    
    # Sort values for quartile calculation
    sorted_values = sorted(values)
    n = len(sorted_values)
    
    # Calculate Q1 (25th percentile) and Q3 (75th percentile)
    q1_idx = n // 4
    q3_idx = (3 * n) // 4
    
    q1 = sorted_values[q1_idx]
    q3 = sorted_values[q3_idx]
    iqr = q3 - q1
    
    # Calculate bounds
    lower_bound = q1 - (iqr_multiplier * iqr)
    upper_bound = q3 + (iqr_multiplier * iqr)
    
    # Filter peers
    filtered_peers = []
    for peer in peer_multiples:
        value = getattr(peer, metric, None)
        if value is not None and lower_bound <= value <= upper_bound:
            filtered_peers.append(peer)
    
    return filtered_peers if filtered_peers else peer_multiples


def build_comps_inputs(
    target_ticker: str,
    financial_data: Dict[str, Any],
    peer_tickers: Optional[List[str]] = None,
    apply_outlier_filtering: bool = True,
    iqr_multiplier: float = 1.5
) -> CompsAnalysisRequest:
    """
    Build CompsAnalysisRequest from financial data and peer selection.
    
    This function mirrors the logic in fetch_api_data() for comps analysis.
    
    Args:
        target_ticker: Target company ticker symbol
        financial_data: Financial data from yFinance (includes profile, financials, raw_info)
        peer_tickers: List of peer ticker symbols (auto-generated if None)
        apply_outlier_filtering: Whether to apply IQR-based outlier filtering
        iqr_multiplier: IQR multiplier for outlier detection (default 1.5)
    
    Returns:
        CompsAnalysisRequest object ready for TradingCompsAnalyzer
    """
    info = financial_data.get('raw_info', {})
    profile = financial_data.get('profile', {})
    
    # Calculate target company metrics
    market_cap = info.get('marketCap', 1000000000) or 1000000000
    enterprise_value = market_cap + (info.get('totalDebt', 0) or 0) - (info.get('cash', 0) or 0)
    
    financials = financial_data.get('financials', {})
    revenue_values = list(financials.get('revenue', {}).values())
    ebitda_values = list(financials.get('ebitda', {}).values())
    
    revenue_ltm = revenue_values[0] if revenue_values else 100000000
    ebitda_ltm = ebitda_values[0] if ebitda_values else revenue_ltm * 0.2
    
    shares_outstanding = info.get('sharesOutstanding', 1000000) or 1000000
    share_price = profile.get('current_price', 100) or 100
    
    # Build target company
    target = CompsTargetCompany(
        ticker=target_ticker,
        company_name=profile.get('name', target_ticker),
        market_cap=market_cap,
        enterprise_value=enterprise_value,
        revenue_ltm=revenue_ltm,
        ebitda_ltm=ebitda_ltm,
        ebit_ltm=ebitda_ltm * 0.75,
        net_income_ltm=revenue_ltm * 0.1,
        free_cash_flow_ltm=ebitda_ltm * 0.7,
        book_equity=market_cap * 0.4,
        shares_outstanding=shares_outstanding,
        share_price=share_price,
        currency=profile.get('currency', 'USD')
    )
    
    # Generate or use provided peers
    peers: List[CompsPeerCompany] = []
    
    if peer_tickers:
        # Use provided peer tickers
        for ticker in peer_tickers[:10]:  # Limit to 10 peers
            peers.append(CompsPeerCompany(
                ticker=ticker,
                company_name=f"{ticker} Corp",
                sector=info.get('sector', 'Technology'),
                industry=info.get('industry', 'Software'),
                selection_reason="User selected"
            ))
    else:
        # Auto-generate peers (similar to fetch_api_data logic)
        import random
        random.seed(42)
        
        sector = info.get('sector', 'Technology')
        industry = info.get('industry', 'Software')
        
        peer_names = ['Peer A', 'Peer B', 'Peer C', 'Peer D', 'Peer E']
        peer_tickers_auto = ['PEERA', 'PEERB', 'PEERC', 'PEERD', 'PEERE']
        
        for name, ticker_sym in zip(peer_names, peer_tickers_auto):
            variation = 0.8 + (random.random() * 0.4)
            peers.append(CompsPeerCompany(
                ticker=ticker_sym,
                company_name=f"{name} Corp",
                market_cap=market_cap * variation,
                enterprise_value=enterprise_value * variation,
                ebitda_ltm=ebitda_ltm * variation,
                ebitda_fy2023=ebitda_ltm * 1.05 * variation,
                ebitda_fy2024=ebitda_ltm * 1.10 * variation,
                eps_ltm=(revenue_ltm * 0.1 * variation) / 1000000,
                eps_fy2023=(revenue_ltm * 0.105 * variation) / 1000000,
                eps_fy2024=(revenue_ltm * 0.110 * variation) / 1000000,
                share_price=100 * variation,
                shares_outstanding=1000000 * variation,
                industry=industry,
                sector=sector,
                selection_reason=f"Same {sector} sector"
            ))
    
    return CompsAnalysisRequest(
        session_id="",  # Will be set by caller
        target=target,
        peers=peers if peers else None,
        apply_outlier_filtering=apply_outlier_filtering,
        include_football_field=True
    )


# =============================================================================
# DU PONT INPUT BUILDER FUNCTIONS
# =============================================================================

def build_dupont_request(
    ticker: str,
    years: List[int],
    custom_ratios: Optional[Dict[str, Any]] = None
) -> DuPontRequest:
    """
    Validates raw API data against DuPontRequest, calculates missing ratios if needed,
    and returns a typed object for the DuPont engine.
    
    Args:
        ticker: Company ticker symbol
        years: List of years for analysis
        custom_ratios: Optional custom ratio overrides (net_profit_margin, asset_turnover, equity_multiplier)
    
    Returns:
        DuPontRequest object ready for DuPont analysis
    """
    # Parse custom ratios into DuPontComponents if provided
    components = None
    if custom_ratios:
        components = DuPontComponents(**custom_ratios)
    
    return DuPontRequest(
        ticker=ticker,
        years=years,
        custom_ratios=components
    )


def build_dupont_inputs(
    ticker: str,
    financial_data: Dict[str, Any],
    years: Optional[List[int]] = None,
    custom_ratios: Optional[Dict[str, Any]] = None
) -> DuPontAnalysisRequest:
    """
    Build DuPontAnalysisRequest from financial data.
    
    This function prepares inputs for DuPont analysis based on the requirements
    defined in valuation_routes.py prepare_inputs() endpoint.
    
    Args:
        ticker: Company ticker symbol
        financial_data: Financial data from yFinance
        years: List of years for analysis (auto-extracted if not provided)
        custom_ratios: Optional custom ratio overrides
    
    Returns:
        DuPontAnalysisRequest object ready for DuPont engine
    """
    # Validate that we have the required financial data
    financials = financial_data.get('financials', {})
    
    # Extract years from financial data if not provided
    if years is None:
        years = list(financials.get('revenue', {}).keys())
        # Convert to int if they're strings
        try:
            years = [int(y) for y in years]
        except (ValueError, TypeError):
            years = list(range(2020, 2024))  # Default fallback
    
    # Check for required historical data (8 years preferred)
    revenue_history = financials.get('revenue', {})
    if not revenue_history or len(revenue_history) < 3:
        logger.warning(f"Insufficient historical revenue data for {ticker}: {len(revenue_history)} years")
    
    # Parse custom ratios into DuPontCustomInputs if provided
    custom_inputs_obj = None
    if custom_ratios:
        custom_inputs_obj = DuPontCustomInputs(**custom_ratios)
    
    return DuPontAnalysisRequest(
        session_id="",  # Will be set by caller
        ticker=ticker,
        custom_inputs=custom_inputs_obj
    )
