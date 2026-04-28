"""
DCF Input Manager - Handles inputs from API, AI, or Manual sources
Provides unified interface for building DCFInputs with full source tracking
"""

from typing import Dict, Any, List, Optional, Union
from datetime import date
from dcf_engine_full import (
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
        
        Expected structure:
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
            }
        }
        """
        self.api_data = financial_data
        return self
    
    def load_ai_assumptions(self, ai_results: Dict[str, Any]) -> 'DCFInputManager':
        """
        Load AI-generated assumptions with rationale and sources.
        
        Expected structure:
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
    
    def _extract_historical_from_api(self) -> Dict[str, List[float]]:
        """Extract 3-year historical financials from API data."""
        financials = self.api_data.get("financials", {})
        
        def extract_series(data_dict: Dict) -> List[float]:
            """Extract values sorted by year (most recent first)."""
            if not data_dict:
                return [0.0, 0.0, 0.0]
            values = list(data_dict.values())
            # Pad or truncate to 3 years
            while len(values) < 3:
                values.append(0.0)
            return [float(v) if v else 0.0 for v in values[:3]]
        
        return {
            "revenue": extract_series(financials.get("revenue", {})),
            "cogs": extract_series(financials.get("cogs", financials.get("cost_of_revenue", {}))),
            "sga": extract_series(financials.get("operating_expenses", {})),
            "depreciation": extract_series(financials.get("depreciation", {})),
            "interest": extract_series(financials.get("interest_expense", {})),
            "capex": extract_series(financials.get("capital_expenditures", financials.get("capex", {})))
        }
    
    def _extract_balance_sheet_from_api(self) -> Dict[str, float]:
        """Extract opening balance sheet items from API data."""
        profile = self.api_data.get("profile", {})
        financials = self.api_data.get("financials", {})
        balance_sheet = financials.get("balance_sheet", {})
        
        # Get most recent values
        def get_latest(data_dict: Dict, default: float = 0.0) -> float:
            if not data_dict:
                return default
            values = [v for v in data_dict.values() if v]
            return float(values[0]) if values else default
        
        total_debt = get_latest(balance_sheet.get("total_debt", {}))
        cash = get_latest(balance_sheet.get("cash", balance_sheet.get("cash_and_equivalents", {})))
        
        return {
            "net_debt": total_debt - cash,
            "ppe": get_latest(balance_sheet.get("property_plant_equipment", {}), 
                             profile.get("totalAssets", 0.0) * 0.3),  # Estimate if not available
            "ar": get_latest(balance_sheet.get("accounts_receivable", {})),
            "inventory": get_latest(balance_sheet.get("inventory", {})),
            "ap": get_latest(balance_sheet.get("accounts_payable", {})),
            "shares_outstanding": profile.get("sharesOutstanding", 1000000.0),
            "current_price": profile.get("currentPrice", profile.get("current_price", 100.0))
        }
    
    def _build_scenario_drivers_from_ai(self) -> ScenarioDrivers:
        """Build ScenarioDrivers from AI assumptions."""
        drivers = ScenarioDrivers()
        
        # Revenue growth forecast (convert to volume/price split)
        revenue_forecast = self.ai_assumptions.get("revenue_growth_forecast", [])
        if revenue_forecast:
            # Split total growth into volume and price components (assume 60/40 split)
            volume_growth = []
            price_growth = []
            for item in revenue_forecast[:5]:
                total_growth = item.get("value", 0.0) / 100 if isinstance(item, dict) else item / 100
                volume_growth.append(total_growth * 0.6)
                price_growth.append(total_growth * 0.4)
            # Add terminal year
            volume_growth.append(volume_growth[-1] * 0.5)
            price_growth.append(price_growth[-1] * 0.5)
            
            drivers.volume_growth = volume_growth
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
        
        # Capex as % of revenue
        capex_pct = self.ai_assumptions.get("capex_percent_of_revenue", {})
        if isinstance(capex_pct, dict) and "value" in capex_pct:
            capex_rate = capex_pct["value"] / 100
        else:
            capex_rate = 0.05  # Default 5%
        
        # Inflation rate for COGS/OpEx
        inflation_item = self.ai_assumptions.get("inflation_rate", {})
        if isinstance(inflation_item, dict) and "value" in inflation_item:
            inflation_rate = inflation_item["value"] / 100
        else:
            inflation_rate = 0.025  # Default 2.5%
        
        drivers.inflation_rate = [inflation_rate] * 6
        
        # Working capital days
        ar_days = self.ai_assumptions.get("working_capital_days_receivables", {})
        inv_days = self.ai_assumptions.get("working_capital_days_inventory", {})
        ap_days = self.ai_assumptions.get("working_capital_days_payables", {})
        
        drivers.ar_days = [ar_days.get("value", 45) if isinstance(ar_days, dict) else ar_days] * 5
        drivers.inv_days = [inv_days.get("value", 25) if isinstance(inv_days, dict) else inv_days] * 5
        drivers.ap_days = [ap_days.get("value", 40) if isinstance(ap_days, dict) else ap_days] * 5
        
        return drivers
    
    def build_inputs(self, scenario_name: str = "Base Case") -> DCFInputs:
        """
        Build complete DCFInputs object with all sources integrated.
        
        Priority: Manual Override > AI > API > Default
        """
        # Extract data from sources
        historical = self._extract_historical_from_api()
        balance_sheet = self._extract_balance_sheet_from_api()
        
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
            historical_revenue=historical["revenue"],
            historical_cogs=historical["cogs"],
            historical_sga=historical["sga"],
            historical_other_opex=[h * 0.3 for h in historical["sga"]],  # Estimate
            historical_depreciation=historical["depreciation"],
            historical_interest=historical["interest"],
            historical_capex=historical["capex"],
            
            # Balance sheet from API
            historical_ar=balance_sheet["ar"],
            historical_inventory=balance_sheet["inventory"],
            historical_ap=balance_sheet["ap"],
            net_debt_opening=balance_sheet["net_debt"],
            shares_outstanding=balance_sheet["shares_outstanding"],
            current_stock_price=balance_sheet["current_price"],
            
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
