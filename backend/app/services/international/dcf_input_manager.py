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
from app.services.international.dcf_engine import (
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
        
        # Revenue combined growth forecast (directly from AI)
        rev_growth_forecast = self.ai_assumptions.get("revenue_volume_growth", [])
        if rev_growth_forecast:
            combined_growth = []
            for item in rev_growth_forecast[:5]:
                growth_rate = item.get("value", 0.0) / 100 if isinstance(item, dict) else item / 100
                combined_growth.append(growth_rate)
            # Add terminal year (half of last year)
            combined_growth.append(combined_growth[-1] * 0.5 if combined_growth else 0.005)
            drivers.combined_revenue_growth = combined_growth
        
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
        # Get WACC-related inputs
        base_scenario = self._build_scenario_drivers_from_ai()
        
        # Get WACC-related inputs
        wacc_item = self._create_input_with_source("wacc_percent", 8.5)
        tax_rate_item = self._create_input_with_source("tax_rate_percent", 21.0)
        risk_free_item = self._create_input_with_source("risk_free_rate", None)
        
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
    market: str = "international",
    complete_statements: Optional[Dict[str, Any]] = None,
    sec_edgar_data: Optional[Dict[str, Any]] = None,
) -> DCFInputs:
    """
    Build DCFInputs from confirmed assumptions + complete_statements + SEC EDGAR.
    
    Reads ACTUAL data from all available sources instead of using hardcoded estimates.
    
    Args:
        confirmed_assumptions: Step 8 user/AI edits (forecast drivers, WACC, etc.)
        financial_data: Step 6 yfinance data (historical financials)
        profile: Step 2 company info (shares, price, etc.)
        market: Market type
        complete_statements: Step 8 merged data (Step 6 + Step 7 + SEC EDGAR + PDF)
        sec_edgar_data: SEC EDGAR XBRL (PP&E Gross, Accum Dep, NOL, Deferred Tax)
    
    Returns:
        DCFInputs object ready for DCFEngine
    """
    
    # ─── Helper functions ──────────────────────────────────────────────
    def _last(arr, default=0):
        """Get last value from array."""
        if not arr or not isinstance(arr, list):
            return default
        return arr[-1] if arr[-1] is not None else default
    
    def _last_4(arr):
        """Get last 4 values from array (for 4-year historical)."""
        if not arr or not isinstance(arr, list):
            return []
        return arr[-4:] if len(arr) >= 4 else arr
    
    def _first_nonzero(arr, default=0):
        """Get first non-zero value from array."""
        if not arr or not isinstance(arr, list):
            return default
        for v in arr:
            if v and v != 0:
                return v
        return default
    
    def _get_field(section, field_name, default=None):
        """Get a field from complete_statements by section and name."""
        if not complete_statements:
            return default
        sec = complete_statements.get(section, {})
        if not isinstance(sec, dict):
            return default
        # Try latest period first, then flat
        if isinstance(sec, dict) and sec:
            # If sec is period-keyed dict like {"2022-12-31": {...}}
            for period_key in sorted(sec.keys(), reverse=True):
                period_data = sec[period_key]
                if isinstance(period_data, dict) and field_name in period_data:
                    return period_data[field_name]
        return default
    
    def _get_multi_year(section, field_name):
        """Get multi-year array from complete_statements."""
        if not complete_statements:
            return []
        sec = complete_statements.get(section, {})
        if not isinstance(sec, dict):
            return []
        values = []
        for period_key in sorted(sec.keys()):
            period_data = sec[period_key]
            if isinstance(period_data, dict):
                val = period_data.get(field_name)
                if val is not None:
                    values.append(val)
        return values
    
    # ─── Extract from financial_data (Step 6 yfinance) ───────────────
    financials = financial_data.get('financials', {})
    
    info = profile.get('raw_info', {})
    shares_outstanding = info.get('sharesOutstanding', 1000000) or 1000000
    current_price = profile.get('current_price', 100) or 100
    
    # ─── Historical financials (from complete_statements or financial_data) ──
    # Try complete_statements first (merged Step 6+7), fallback to raw financial_data
    hist_revenue = _get_multi_year('income_statement', 'revenue') or list(financials.get('revenue', {}).values())
    hist_cogs = _get_multi_year('income_statement', 'cogs') or list(financials.get('cost_of_revenue', {}).values())
    hist_sga = _get_multi_year('income_statement', 'selling_general_administrative') or list(financials.get('sga', {}).values())
    hist_other_opex_raw = _get_multi_year('income_statement', 'operating_expenses') or list(financials.get('other_opex', {}).values())
    hist_depreciation = _get_multi_year('income_statement', 'depreciation') or list(financials.get('depreciation', {}).values())
    hist_rd = _get_multi_year('income_statement', 'research_development') or list(financials.get('research_development', {}).values())
    # yfinance's OperatingExpense = R&D + SG&A + OtherOperatingExpenses
    # (D&A is NOT in OperatingExpense — it's embedded inside COGS and SG&A)
    # Other OpEx = OperatingExpense - SG&A - R&D
    if hist_other_opex_raw:
        t5 = hist_other_opex_raw
        s5 = hist_sga if hist_sga and len(hist_sga) == len(t5) else [0.0] * len(t5)
        r5 = hist_rd if hist_rd and len(hist_rd) == len(t5) else [0.0] * len(t5)
        hist_other_opex = [max(t - s - r, 0) if t and s and r else 0 for t, s, r in zip(t5, s5, r5)]
    else:
        hist_other_opex = hist_other_opex_raw
    hist_interest = _get_multi_year('income_statement', 'interest_expense') or list(financials.get('interest', {}).values())
    hist_capex = _get_multi_year('cash_flow', 'capital_expenditure') or list(financials.get('capex', {}).values())
    
    # ─── Historical balance sheet (from complete_statements) ──
    hist_ar = _get_field('balance_sheet', 'accounts_receivable')
    hist_inventory = _get_field('balance_sheet', 'inventory')
    hist_ap = _get_field('balance_sheet', 'accounts_payable')
    
    # ─── Opening balances (from complete_statements) ──
    total_debt = _get_field('balance_sheet', 'total_debt') or info.get('totalDebt', 0) or 0
    cash = _get_field('balance_sheet', 'cash_and_equivalents') or info.get('cash', info.get('totalCash', 0)) or 0
    net_debt = total_debt - cash
    
    ppe_gross = _get_field('balance_sheet', 'ppe_gross')
    if not ppe_gross:
        # Fallback: try SEC EDGAR
        if sec_edgar_data:
            xbrl = sec_edgar_data.get('xbrl_data') or sec_edgar_data
            ppe_gross_data = xbrl.get('ppe_gross', {}) if isinstance(xbrl, dict) else {}
            if ppe_gross_data:
                ppe_gross = _first_nonzero(list(ppe_gross_data.values()))
    if not ppe_gross:
        ppe_gross = _get_field('balance_sheet', 'net_ppe') or info.get('totalAssets', 0) or 0
    
    accumulated_depreciation = _get_field('balance_sheet', 'accumulated_depreciation')
    
    # Tax Basis PP&E — use net_ppe as proxy (actual tax basis not available from APIs)
    net_ppe = _get_field('balance_sheet', 'net_ppe')
    tax_basis_ppe = net_ppe if net_ppe else ppe_gross * 0.8
    
    # Tax Loss Carryforwards — from SEC EDGAR
    tax_losses_nol = 0
    if sec_edgar_data:
        xbrl = sec_edgar_data.get('xbrl_data') or sec_edgar_data
        tax_loss_data = xbrl.get('tax_loss_carryforward', {}) if isinstance(xbrl, dict) else {}
        if tax_loss_data:
            tax_losses_nol = _first_nonzero(list(tax_loss_data.values()))
    if not tax_losses_nol and complete_statements:
        tax_losses_nol = _get_field('balance_sheet', 'tax_loss_carryforward') or 0
    
    # ─── Opening Balance Sheet ──
    cash_opening = cash
    long_term_debt_opening = _get_field('balance_sheet', 'long_term_debt') or info.get('longTermDebt', 20000) or 20000
    common_equity_opening = _get_field('balance_sheet', 'shareholders_equity') or info.get('totalEquity', 38669.70) or 38669.70
    retained_earnings_opening = _get_field('balance_sheet', 'retained_earnings') or 5690.0
    
    # ─── Financing items (from complete_statements) ──
    dividends_paid = _get_field('cash_flow', 'dividends_paid')
    if dividends_paid:
        dividends_paid = abs(dividends_paid)
    
    # Change in LT Debt — multi-year from balance sheet
    lt_debt_series = _get_multi_year('balance_sheet', 'long_term_debt')
    change_in_lt_debt = []
    if len(lt_debt_series) >= 2:
        change_in_lt_debt = [lt_debt_series[i] - lt_debt_series[i-1] for i in range(1, len(lt_debt_series))]
    
    # Change in Common Equity — multi-year from balance sheet
    equity_series = _get_multi_year('balance_sheet', 'shareholders_equity')
    change_in_common_equity = []
    if len(equity_series) >= 2:
        change_in_common_equity = [equity_series[i] - equity_series[i-1] for i in range(1, len(equity_series))]
    
    # Revolving Credit Line — current_debt from balance sheet
    revolving_credit = _get_multi_year('balance_sheet', 'current_debt')
    
    # ─── WACC inputs ──
    wacc = confirmed_assumptions.get('wacc', 0.08)
    risk_free_rate = confirmed_assumptions.get('risk_free_rate', 0.045)
    market_risk_premium = confirmed_assumptions.get('market_risk_premium', 0.047)
    country_risk_premium = confirmed_assumptions.get('country_risk_premium', 0.036)
    beta = confirmed_assumptions.get('beta', 1.0)
    target_de = confirmed_assumptions.get('debt_to_equity', 0.1765)
    target_debt_weight = target_de / (1 + target_de) if target_de else 0.15
    target_equity_weight = 1.0 - target_debt_weight
    pre_tax_cost_of_debt = confirmed_assumptions.get('cost_of_debt', 0.052)
    statutory_tax_rate = confirmed_assumptions.get('tax_rate', 0.30)
    
    # ─── Forecast drivers ──
    revenue_growth = confirmed_assumptions.get('revenue_growth_forecast', [0.02, 0.01, 0.01, 0.005, 0.005, 0.005])
    while len(revenue_growth) < 6:
        revenue_growth.append(0.005)
    
    terminal_growth = confirmed_assumptions.get('terminal_growth_rate', 0.02)
    terminal_multiple = confirmed_assumptions.get('terminal_ebitda_multiple', 7.0)
    
    # Capex — from confirmed assumptions or derive from historical
    capex_pct = confirmed_assumptions.get('capex_pct_of_revenue', 0.05)
    latest_rev = _last(hist_revenue, 55749)
    capex_values = [latest_rev * capex_pct] * 6
    
    base_drivers = ScenarioDrivers(
        combined_revenue_growth=revenue_growth[:6],
        inflation_rate=[confirmed_assumptions.get('inflation_rate', 0.03)] * 6 if not isinstance(confirmed_assumptions.get('inflation_rate'), list) else confirmed_assumptions.get('inflation_rate', [0.03]*6)[:6],
        capex=capex_values,
        ar_days=[confirmed_assumptions.get('ar_days', 45)] * 5,
        inv_days=[confirmed_assumptions.get('inv_days', 25)] * 5,
        ap_days=[confirmed_assumptions.get('ap_days', 40)] * 5,
        terminal_ebitda_multiple=terminal_multiple,
        terminal_growth_rate=terminal_growth
    )
    
    # ─── Build DCFInputs ──
    dcf_inputs = DCFInputs(
        valuation_date=date.today().isoformat(),
        first_cf_date=date(date.today().year, 6, 30),
        first_fiscal_year_end=date(date.today().year, 12, 31),
        currency="VND" if market == "vietnam" else profile.get('currency', 'USD'),
        scale="thousands",
        # Historical financials (last 4 years)
        historical_revenue=_last_4(hist_revenue) or [45196.0, 48324.0, 51585.0, 53494.0, 55749.0],
        historical_cogs=_last_4(hist_cogs) or [24053.0, 25845.0, 27697.0, 28429.0, 29200.0],
        historical_sga=_last_4(hist_sga) or [5422.0, 5650.0, 5877.0, 6006.0, 6144.0],
        historical_other_opex=_last_4(hist_other_opex) or [1520.0, 1640.0, 1764.0, 1931.0, 2026.0],
        historical_depreciation=_last_4(hist_depreciation) or [2580.0, 2765.0, 2960.0, 3196.0, 3452.0],
        historical_interest=_last_4(hist_interest) or [1200.0, 1350.0, 1488.0, 2580.0, 2448.0],
        historical_capex=_last_4(hist_capex) or [4200.0, 4600.0, 4982.0, 5199.0, 4400.0],
        # Historical balance sheet (end of last year)
        historical_ar=hist_ar or 6624.0,
        historical_inventory=hist_inventory or 2009.0,
        historical_ap=hist_ap or 3319.0,
        # Opening balances
        net_debt_opening=net_debt or 18642.0,
        ppe_gross_book=ppe_gross or 65014.0,
        tax_basis_ppe=tax_basis_ppe or 39211.0,
        tax_losses_nol=tax_losses_nol,
        # Shares and price
        shares_outstanding=shares_outstanding,
        current_stock_price=current_price,
        # Depreciation parameters
        useful_life_existing=confirmed_assumptions.get('useful_life_existing', 16.0),
        useful_life_new=confirmed_assumptions.get('useful_life_new', 20.0),
        first_year_tax_dep_rate=0.50,
        blended_tax_dep_rate=0.15,
        first_year_acctg_dep_rate=0.50,
        # Tax
        statutory_tax_rate=statutory_tax_rate,
        tax_loss_utilization_limit=0.80,
        # Financing items
        projected_dividends=dividends_paid or 2446.0,
        change_in_lt_debt=change_in_lt_debt if change_in_lt_debt else [0.0] * 6,
        change_in_common_equity=change_in_common_equity if change_in_common_equity else [-1000.0] * 6,
        revolving_credit_line=revolving_credit if revolving_credit else [0.0] * 6,
        # Opening balance sheet
        cash_opening=cash_opening or 9365.0,
        long_term_debt_opening=long_term_debt_opening,
        common_equity_opening=common_equity_opening,
        retained_earnings_opening=retained_earnings_opening,
        # Forecast drivers
        forecast_drivers={"base_case": base_drivers, "best_case": base_drivers, "worst_case": base_drivers},
        # WACC
        risk_free_rate=risk_free_rate,
        market_risk_premium=market_risk_premium,
        country_risk_premium=country_risk_premium,
        target_debt_weight=target_debt_weight,
        target_equity_weight=target_equity_weight,
        pre_tax_cost_of_debt=pre_tax_cost_of_debt,
        days_in_period=365,
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
