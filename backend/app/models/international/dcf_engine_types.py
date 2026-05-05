"""
Core DCF Engine Dataclasses
Moved from app.engines.international.dcf_engine to app.models.international.dcf_engine_types
after engines folder deprecation.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum
from datetime import date


class InputSource(str, Enum):
    """Source of input data for audit tracking."""
    API = "api"
    AI = "ai"
    MANUAL = "manual"
    DEFAULT = "default"


@dataclass
class InputWithMetadata:
    """Input value with source tracking for auditability."""
    value: Any
    source: InputSource
    rationale: str
    sources: str


@dataclass
class ScenarioDrivers:
    """Forecast drivers for a single scenario."""
    volume_growth: List[float] = field(default_factory=lambda: [0.05] * 6)
    price_growth: List[float] = field(default_factory=lambda: [0.02] * 6)
    cogs_percent_of_revenue: List[float] = field(default_factory=lambda: [0.60] * 6)
    sgna_percent_of_revenue: List[float] = field(default_factory=lambda: [0.15] * 6)
    other_opex_percent_of_revenue: List[float] = field(default_factory=lambda: [0.05] * 6)
    depreciation_percent_of_revenue: List[float] = field(default_factory=lambda: [0.03] * 6)
    capex: List[float] = field(default_factory=lambda: [5000.0] * 6)
    ar_days: List[float] = field(default_factory=lambda: [45.0] * 5)
    inv_days: List[float] = field(default_factory=lambda: [25.0] * 5)
    ap_days: List[float] = field(default_factory=lambda: [40.0] * 5)
    terminal_growth_rate: float = 0.025
    terminal_ebitda_multiple: float = 8.0
    inflation_rate: List[float] = field(default_factory=lambda: [0.025] * 6)


@dataclass
class DCFInputs:
    """Complete DCF model inputs."""
    # Historical financials (in thousands)
    historical_revenue: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    historical_cogs: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    historical_sga: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    historical_other_opex: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    historical_depreciation: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    historical_interest: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    historical_capex: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    
    # Balance sheet (in thousands)
    historical_ar: float = 0.0
    historical_inventory: float = 0.0
    historical_ap: float = 0.0
    net_debt_opening: float = 0.0
    shares_outstanding: float = 1000000.0
    current_stock_price: float = 100.0
    
    # Tax and rates
    statutory_tax_rate: float = 0.21
    risk_free_rate: float = 0.045
    
    # Forecast drivers by scenario
    forecast_drivers: Dict[str, ScenarioDrivers] = field(default_factory=dict)


@dataclass
class ComparableCompany:
    """Comparable company data for comps analysis."""
    ticker: str
    name: str
    market_cap: float
    enterprise_value: float
    revenue: float
    ebitda: float
    ev_revenue_multiple: float
    ev_ebitda_multiple: float
    pe_ratio: float
    pb_ratio: float


@dataclass
class DCFResult:
    """DCF valuation results."""
    enterprise_value: float
    equity_value: float
    fair_value_per_share: float
    current_price: float
    upside_downside: float
    wacc: float
    terminal_growth_rate: float
    npv_of_fcf: float
    npv_of_terminal_value: float
    valuation_date: date
    scenario_name: str
