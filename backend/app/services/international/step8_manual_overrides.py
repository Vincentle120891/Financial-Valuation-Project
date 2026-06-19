"""Step 8: Assumption & AI Suggestion Studio

This is the critical "Brain" of the workflow, bridging historical reality with future valuation.

NEW LOGIC (per documentation updates):
- Step 8 is the dedicated phase for ASSUMPTIONS
- It calculates values programmatically from historical data
- It utilizes AI for SUGGESTIONS on forward-looking assumptions
- This is where forward-looking inputs are finalized before confirmation (Step 9)

AI Usage in Step 8:
- AI provides suggestions for assumptions based on historical trends, peer analysis, and market conditions
- Users can accept AI suggestions or manually override them
- All AI suggestions include rationale and confidence scores
- For DuPont/Comps: AI suggestions are minimal (mostly calculated)
- For DCF: AI suggests key drivers (Revenue Growth, Margins, WACC components, Terminal Value)

Features:
1. Context-Aware Historical Trendlines (3-5 years from merged complete_statements)
2. Modular AI Suggestion Engines (Category-by-category generation)
3. Smart Validation & Guardrails
4. What-If Preview (Mini-Step 9 sensitivity)

Data Flow (refactored per fix-step8-data-flow.md):
- Step 8 receives ONLY complete_statements (merged Step 6 + Step 7) + peer_median_ev_ebitda
- _build_historical_trendline reads directly from complete_statements
- statistical_utils functions used for all statistical calculations
"""
import logging
from typing import Dict, List, Optional, Any, Tuple
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime
import json
from .ai_engine import AIFallbackEngine
from .statistical_utils import (
    calculate_average,
    calculate_median,
    calculate_cagr,
    calculate_volatility,
    calculate_min_max,
    calculate_year_over_year_growth,
    calculate_weighted_growth
)

logger = logging.getLogger(__name__)

# =============================================================================
# METRIC-TO-STATEMENT FIELD MAPPING
# Maps assumption metric names to (section, field_name) in complete_statements.
# None means the metric has no historical data source (e.g., external rates).
# =============================================================================

# Calculation types for derived metrics
# "direct"   → read field value directly
# "ratio"    → numerator / denominator
# "days"     → (numerator / denominator) * 365
# "yoy"      → year-over-year growth rate of a single field
METRIC_CALC_CONFIG: Dict[str, Optional[Dict[str, Any]]] = {
    # DCF Revenue — YoY growth of revenue (combined volume + price)
    "Revenue Growth": {"type": "yoy", "field": "revenue", "section": "income_statement"},
    # DCF Cost & Margins — ratios
    "COGS Growth Rate": {"type": "yoy", "field": "cogs", "section": "income_statement"},
    "Capital Expenditure": {"type": "ratio", "numerator": "capex", "denominator": "revenue", "num_section": "cash_flow", "den_section": "income_statement"},
    "COGS % of Revenue": {"type": "ratio", "numerator": "cogs", "denominator": "revenue", "num_section": "income_statement", "den_section": "income_statement"},
    # OpEx Growth: YoY growth of non-R&D operating expenses (SG&A + Other OpEx)
    # NOT operating_expenses (which includes R&D) — R&D is forecasted separately
    "OpEx Growth": {"type": "yoy", "field": "sg_and_a", "section": "income_statement"},
    "Effective Tax Rate": {"type": "ratio", "numerator": "tax_provision", "denominator": "pretax_income", "num_section": "income_statement", "den_section": "income_statement"},
    # DCF Working Capital — days calculations
    "Accounts Receivable Days": {"type": "days", "numerator": "accounts_receivable", "denominator": "revenue", "num_section": "balance_sheet", "den_section": "income_statement"},
    "Inventory Days": {"type": "days", "numerator": "inventory", "denominator": "cogs", "num_section": "balance_sheet", "den_section": "income_statement"},
    "Accounts Payable Days": {"type": "days", "numerator": "accounts_payable", "denominator": "cogs", "num_section": "balance_sheet", "den_section": "income_statement"},
    # DCF WACC Components — no historical trendlines for market-derived rates
    "Risk-Free Rate": None,
    "Market Risk Premium": None,
    "Country Risk Premium": None,
    "Pre-Tax Cost of Debt": {"type": "latest_ratio", "numerator": "interest_expense", "denominator": "total_debt", "num_section": "income_statement", "den_section": "balance_sheet", "min_threshold": 0.01, "max_threshold": 0.25},
    "Target Debt-to-Equity": {"type": "ratio", "numerator": "total_debt", "denominator": "shareholders_equity", "num_section": "balance_sheet", "den_section": "balance_sheet"},
    "Beta": None,  # From market data or peer Hamada formula
    "WACC": None,  # Calculated from components: Rf + Beta x (MRP + CRP)
    # DCF Terminal Value
    "Terminal Growth Rate": None,
    # Terminal EBITDA Multiple is driven by peer median, not company historicals
    "Terminal EBITDA Multiple": None,
    # DuPont Targets — ratios
    "Target Net Profit Margin": {"type": "ratio", "numerator": "net_income", "denominator": "revenue", "num_section": "income_statement", "den_section": "income_statement"},
    "Target Asset Turnover": {"type": "ratio", "numerator": "revenue", "denominator": "total_assets", "num_section": "income_statement", "den_section": "balance_sheet"},
    "Target Equity Multiplier": {"type": "ratio", "numerator": "total_assets", "denominator": "shareholders_equity", "num_section": "balance_sheet", "den_section": "balance_sheet"},
    # Comps Multiples — driven by peer data, not company historicals
    "P/E Multiple": None,
    "EV/EBITDA Multiple": {"type": "direct", "field": "ebitda", "section": "income_statement"},
    "P/B Multiple": {"type": "direct", "field": "shareholders_equity", "section": "balance_sheet"},
    "P/S Multiple": {"type": "direct", "field": "revenue", "section": "income_statement"},
    "Outlier Filter Threshold": None,
    "Outlier Filter Std Dev": None,
    # DCF Financing — derived from historical balance sheet / cash flow data
    "Change in Long-Term Debt": {"type": "yoy_diff", "field": "long_term_debt", "section": "balance_sheet"},
    "Change in Common Equity": {"type": "yoy_diff", "field": "shareholders_equity", "section": "balance_sheet"},
    "Projected Interest Expense": {"type": "product", "numerator": "long_term_debt", "denominator": "interest_rate", "num_section": "balance_sheet", "den_section": "config"},
    "Dividend Payout Ratio": {"type": "ratio", "numerator": "dividends_paid", "denominator": "net_income", "num_section": "cash_flow", "den_section": "income_statement"},
    # DCF Model Parameters — defaults from DCFInputs, can be overridden
    "Cash Interest Rate": {"type": "default", "value": 0.01},
    "Revolving Credit Rate": {"type": "default", "value": 0.05},
    "LT Debt Interest Rate": {"type": "latest_ratio", "numerator": "interest_expense", "denominator": "long_term_debt", "num_section": "income_statement", "den_section": "balance_sheet", "min_threshold": 0.01, "max_threshold": 0.25, "fallback": 0.06},
    "Useful Life Existing Assets": {"type": "default", "value": 16.0},
    "Useful Life New Assets": {"type": "default", "value": 20.0},
    "First Year Tax Dep Rate": {"type": "default", "value": 0.50},
    "Blended Tax Dep Rate": {"type": "default", "value": 0.15},
    "First Year Acctg Dep Rate": {"type": "default", "value": 0.50},
}


class ValuationModel(str, Enum):
    """Type of valuation model to use"""
    DCF = "DCF"
    DUPONT = "DUPONT"
    COMPS = "COMPS"

class OverrideStatus(str, Enum):
    """Status of manual override"""
    ACCEPTED_AI = "ACCEPTED_AI"
    MANUAL_OVERRIDE = "MANUAL_OVERRIDE"
    DEFAULT = "DEFAULT"

class AssumptionCategory(str, Enum):
    """Categories for DCF assumptions"""
    REVENUE_DRIVERS = "REVENUE_DRIVERS"
    COST_MARGINS = "COST_MARGINS"
    WORKING_CAPITAL = "WORKING_CAPITAL"
    WACC_COMPONENTS = "WACC_COMPONENTS"
    TERMINAL_VALUE = "TERMINAL_VALUE"
    FINANCING = "FINANCING"
    MODEL_PARAMETERS = "MODEL_PARAMETERS"
    DUPONT_TARGETS = "DUPONT_TARGETS"
    COMPS_MULTIPLES = "COMPS_MULTIPLES"

class HistoricalTrendPoint(BaseModel):
    """A single point in a historical trend"""
    year: int
    value: float
    label: str = ""

class HistoricalTrendline(BaseModel):
    """Historical trend data for an assumption"""
    metric: str
    trend_points: List[HistoricalTrendPoint]
    average: float
    cagr: Optional[float] = None
    trend_direction: str = "stable"  # increasing, decreasing, stable
    volatility: str = "low"  # low, medium, high
    # Enhanced statistical context
    median: Optional[float] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    standard_deviation: Optional[float] = None
    average_yoy_growth: Optional[float] = None
    weighted_growth: Optional[float] = None  # Weighted blended YoY growth
    latest_value: Optional[float] = None
    oldest_value: Optional[float] = None

class AISuggestion(BaseModel):
    """AI suggestion for an assumption"""
    metric: str
    suggested_value: float
    reasoning: str
    confidence_level: str = "medium"  # low, medium, high
    min_range: float
    max_range: float
    category: AssumptionCategory

class AssumptionInput(BaseModel):
    """A single assumption input with full context"""
    metric: str
    category: AssumptionCategory
    description: str
    unit: str = "%"
    
    # Data provenance — tells the user WHERE the value came from
    data_source: Optional[str] = None
    
    # Historical context
    historical_trendline: Optional[HistoricalTrendline] = None
    
    # Current state
    ai_suggestion: Optional[AISuggestion] = None
    user_value: Optional[float] = None
    final_value: Optional[float] = None
    status: OverrideStatus = OverrideStatus.DEFAULT
    
    # Validation
    is_valid: bool = True
    validation_message: Optional[str] = None
    warning_message: Optional[str] = None
    
    # Multi-year support (for forecast years 1-5)
    is_multi_year: bool = False
    year_values: Dict[int, float] = {}  # year -> value

class AssumptionCategoryResponse(BaseModel):
    """Response for a single assumption category"""
    category: AssumptionCategory
    category_name: str
    assumptions: List[AssumptionInput]
    ai_generated: bool = False
    generation_timestamp: Optional[datetime] = None
    message: str = ""

class FullAssumptionsResponse(BaseModel):
    """Complete Step 8 response with all categories"""
    session_id: str
    ticker: str
    timestamp: datetime
    valuation_model: ValuationModel
    categories: Dict[str, AssumptionCategoryResponse]
    
    # Summary and validation
    all_categories_complete: bool = False
    all_validations_passed: bool = True
    total_validation_errors: List[str] = []
    ready_for_calculation: bool = False
    
    # What-if preview
    sensitivity_preview: Optional[Dict[str, Any]] = None
    message: str = ""


class Step8ManualOverridesProcessor:
    """
    Step 8: The Assumption Studio
    
    Features:
    1. Context-Aware Historical Trendlines (3-5 years from complete_statements)
    2. Modular AI Suggestion Engines (5 Button Strategy)
    3. Smart Validation & Guardrails
    4. What-If Preview (Mini-Step 9 sensitivity)
    
    Output: FullAssumptionsResponse with complete assumption set
    
    Data Flow (refactored):
    - Reads ONLY from complete_statements (merged Step 6 + Step 7)
    - Peer median values passed as simple floats (no raw step6/step7 data)
    - Uses statistical_utils for all statistical calculations
    """
    
    # Forecast period configuration
    FORECAST_YEARS = [1, 2, 3, 4, 5]
    
    # DCF Assumption Categories Definition
    DCF_CATEGORIES = {
        AssumptionCategory.REVENUE_DRIVERS: {
            "name": "Revenue Growth",
            "assumptions": [
                {
                    "metric": "Revenue Growth",
                    "description": "Annual revenue growth rate (combined volume + price effect)",
                    "unit": "%",
                    "is_multi_year": True,
                    "validation": {"min": -0.20, "max": 0.50, "warning_min": 0.0, "warning_max": 0.30}
                }
            ]
        },
        AssumptionCategory.COST_MARGINS: {
            "name": "Cost & Margins",
            "assumptions": [
                {
                    "metric": "COGS Growth Rate",
                    "description": "Projected annual growth rate of Cost of Goods Sold (based on historical COGS YoY growth)",
                    "unit": "%",
                    "is_multi_year": True,
                    "validation": {"min": -0.10, "max": 0.30, "warning_min": 0.01, "warning_max": 0.15}
                },
                {
                    "metric": "COGS % of Revenue",
                    "description": "Cost of goods sold as percentage of revenue",
                    "unit": "%",
                    "is_multi_year": False,
                    "validation": {"min": 0.10, "max": 0.90, "warning_min": 0.30, "warning_max": 0.70}
                },
                {
                    "metric": "OpEx Growth",
                    "description": "Year-over-year growth rate of operating expenses (SG&A)",
                    "unit": "%",
                    "is_multi_year": False,
                    "validation": {"min": 0.05, "max": 0.50, "warning_min": 0.10, "warning_max": 0.35}
                },
                {
                    "metric": "Effective Tax Rate",
                    "description": "Expected effective tax rate",
                    "unit": "%",
                    "is_multi_year": False,
                    "validation": {"min": 0.10, "max": 0.40, "warning_min": 0.15, "warning_max": 0.35}
                }
            ]
        },
        AssumptionCategory.WORKING_CAPITAL: {
            "name": "Working Capital",
            "assumptions": [
                {
                    "metric": "Accounts Receivable Days",
                    "description": "Average days to collect receivables",
                    "unit": "days",
                    "is_multi_year": False,
                    "validation": {"min": 0, "max": 180, "warning_min": 15, "warning_max": 90}
                },
                {
                    "metric": "Inventory Days",
                    "description": "Average days inventory held",
                    "unit": "days",
                    "is_multi_year": False,
                    "validation": {"min": 0, "max": 365, "warning_min": 10, "warning_max": 120}
                },
                {
                    "metric": "Accounts Payable Days",
                    "description": "Average days to pay suppliers",
                    "unit": "days",
                    "is_multi_year": False,
                    "validation": {"min": 0, "max": 180, "warning_min": 15, "warning_max": 90}
                },
                {
                    "metric": "Capital Expenditure",
                    "description": "Capital expenditure (absolute value from cash flow statement)",
                    "unit": "$",
                    "is_multi_year": False,
                    "validation": {"min": 0.0, "max": 0.30, "warning_min": 0.02, "warning_max": 0.15}
                }
            ]
        },
        AssumptionCategory.WACC_COMPONENTS: {
            "name": "WACC Components",
            "assumptions": [
                {
                    "metric": "Risk-Free Rate",
                    "description": "10-year government bond yield",
                    "unit": "%",
                    "is_multi_year": False,
                    "validation": {"min": 0.0, "max": 0.15, "warning_min": 0.02, "warning_max": 0.06}
                },
                {
                    "metric": "Market Risk Premium",
                    "description": "Expected excess return of market over risk-free rate",
                    "unit": "%",
                    "is_multi_year": False,
                    "validation": {"min": 0.03, "max": 0.12, "warning_min": 0.04, "warning_max": 0.08}
                },
                {
                    "metric": "Country Risk Premium",
                    "description": "Additional risk premium for country exposure",
                    "unit": "%",
                    "is_multi_year": False,
                    "validation": {"min": 0.0, "max": 0.10, "warning_min": 0.0, "warning_max": 0.05}
                },
                {
                    "metric": "Pre-Tax Cost of Debt",
                    "description": "Interest rate on debt before tax benefit",
                    "unit": "%",
                    "is_multi_year": False,
                    "validation": {"min": 0.02, "max": 0.25, "warning_min": 0.04, "warning_max": 0.12}
                },
                {
                    "metric": "Target Debt-to-Equity",
                    "description": "Target capital structure D/E ratio",
                    "unit": "ratio",
                    "is_multi_year": False,
                    "validation": {"min": 0.0, "max": 5.0, "warning_min": 0.2, "warning_max": 2.0}
                },
                {
                    "metric": "Beta",
                    "description": "Levered beta from peer analysis or market data",
                    "unit": "x",
                    "is_multi_year": False,
                    "validation": {"min": 0.1, "max": 3.0, "warning_min": 0.5, "warning_max": 2.0}
                },
                {
                    "metric": "WACC",
                    "description": "Weighted Average Cost of Capital (calculated from components)",
                    "unit": "%",
                    "is_multi_year": False,
                    "is_calculated": True,
                    "validation": {"min": 0.03, "max": 0.25, "warning_min": 0.06, "warning_max": 0.15}
                }
            ]
        },
        AssumptionCategory.TERMINAL_VALUE: {
            "name": "Terminal Value & Exit",
            "assumptions": [
                {
                    "metric": "Terminal Growth Rate",
                    "description": "Perpetual growth rate after forecast period",
                    "unit": "%",
                    "is_multi_year": False,
                    "validation": {"min": -0.02, "max": 0.08, "warning_min": 0.01, "warning_max": 0.04}
                },
                {
                    "metric": "Terminal EBITDA Multiple",
                    "description": "Exit multiple for terminal value calculation",
                    "unit": "x",
                    "is_multi_year": False,
                    "validation": {"min": 3.0, "max": 25.0, "warning_min": 6.0, "warning_max": 15.0}
                }
            ]
        },
        AssumptionCategory.FINANCING: {
            "name": "Financing",
            "assumptions": [
                {
                    "metric": "Change in Long-Term Debt",
                    "description": "Annual change in long-term debt (borrowing positive, repayments negative)",
                    "unit": "$",
                    "is_multi_year": True,
                    "validation": {"min": -1e12, "max": 1e12, "warning_min": -1e11, "warning_max": 1e11}
                },
                {
                    "metric": "Change in Common Equity",
                    "description": "Annual change in shareholders' equity (issuance positive, buybacks negative)",
                    "unit": "$",
                    "is_multi_year": True,
                    "validation": {"min": -1e12, "max": 1e12, "warning_min": -1e11, "warning_max": 1e11}
                },
                {
                    "metric": "Projected Interest Expense",
                    "description": "Projected interest expense based on LT debt opening × cost of debt",
                    "unit": "$",
                    "is_multi_year": False,
                    "validation": {"min": 0, "max": 1e12, "warning_min": 0, "warning_max": 1e10}
                },
                {
                    "metric": "Dividend Payout Ratio",
                    "description": "Dividends paid as a proportion of net income",
                    "unit": "%",
                    "is_multi_year": False,
                    "validation": {"min": 0.0, "max": 1.0, "warning_min": 0.0, "warning_max": 0.80}
                }
            ]
        },
        AssumptionCategory.MODEL_PARAMETERS: {
            "name": "DCF Model Parameters",
            "assumptions": [
                {
                    "metric": "Cash Interest Rate",
                    "description": "Interest rate earned on cash balances (typically risk-free or money market rate)",
                    "unit": "%",
                    "is_multi_year": False,
                    "default_value": 0.01,
                    "validation": {"min": 0.0, "max": 0.10, "warning_min": 0.005, "warning_max": 0.05}
                },
                {
                    "metric": "Revolving Credit Rate",
                    "description": "Interest rate on revolving credit facility (typically SOFR + spread)",
                    "unit": "%",
                    "is_multi_year": False,
                    "default_value": 0.05,
                    "validation": {"min": 0.0, "max": 0.20, "warning_min": 0.03, "warning_max": 0.10}
                },
                {
                    "metric": "LT Debt Interest Rate",
                    "description": "Interest rate on long-term debt (derived from interest expense / LT debt)",
                    "unit": "%",
                    "is_multi_year": False,
                    "default_value": 0.06,
                    "validation": {"min": 0.0, "max": 0.25, "warning_min": 0.03, "warning_max": 0.12}
                },
                {
                    "metric": "Useful Life Existing Assets",
                    "description": "Remaining useful life of existing PP&E (years, accounting convention)",
                    "unit": "years",
                    "is_multi_year": False,
                    "default_value": 16.0,
                    "validation": {"min": 1, "max": 50, "warning_min": 5, "warning_max": 30}
                },
                {
                    "metric": "Useful Life New Assets",
                    "description": "Useful life of newly acquired PP&E (years, accounting convention)",
                    "unit": "years",
                    "is_multi_year": False,
                    "default_value": 20.0,
                    "validation": {"min": 1, "max": 50, "warning_min": 5, "warning_max": 30}
                },
                {
                    "metric": "First Year Tax Dep Rate",
                    "description": "First-year tax depreciation rate (half-year convention)",
                    "unit": "%",
                    "is_multi_year": False,
                    "default_value": 0.50,
                    "validation": {"min": 0.0, "max": 1.0, "warning_min": 0.30, "warning_max": 0.60}
                },
                {
                    "metric": "Blended Tax Dep Rate",
                    "description": "Declining balance tax depreciation rate",
                    "unit": "%",
                    "is_multi_year": False,
                    "default_value": 0.15,
                    "validation": {"min": 0.0, "max": 0.50, "warning_min": 0.10, "warning_max": 0.25}
                },
                {
                    "metric": "First Year Acctg Dep Rate",
                    "description": "First-year accounting depreciation rate (half-year convention)",
                    "unit": "%",
                    "is_multi_year": False,
                    "default_value": 0.50,
                    "validation": {"min": 0.0, "max": 1.0, "warning_min": 0.30, "warning_max": 0.60}
                }
            ]
        }
    }
    
    # DuPont Categories
    DUPONT_CATEGORIES = {
        AssumptionCategory.DUPONT_TARGETS: {
            "name": "DuPont ROE Targets",
            "assumptions": [
                {
                    "metric": "Target Net Profit Margin",
                    "description": "Target net income as percentage of revenue",
                    "unit": "%",
                    "is_multi_year": False,
                    "validation": {"min": -0.50, "max": 0.60, "warning_min": 0.05, "warning_max": 0.40}
                },
                {
                    "metric": "Target Asset Turnover",
                    "description": "Target revenue per dollar of assets",
                    "unit": "x",
                    "is_multi_year": False,
                    "validation": {"min": 0.1, "max": 5.0, "warning_min": 0.5, "warning_max": 2.0}
                },
                {
                    "metric": "Target Equity Multiplier",
                    "description": "Target assets per dollar of equity",
                    "unit": "x",
                    "is_multi_year": False,
                    "validation": {"min": 1.0, "max": 10.0, "warning_min": 1.5, "warning_max": 4.0}
                }
            ]
        }
    }
    
    # Comps Categories
    COMPS_CATEGORIES = {
        AssumptionCategory.COMPS_MULTIPLES: {
            "name": "Comps Multiples & Filters",
            "assumptions": [
                {
                    "metric": "P/E Multiple",
                    "description": "Price-to-earnings multiple for valuation",
                    "unit": "x",
                    "is_multi_year": False,
                    "validation": {"min": 0.5, "max": 100, "warning_min": 5, "warning_max": 50}
                },
                {
                    "metric": "EV/EBITDA Multiple",
                    "description": "Enterprise value to EBITDA multiple",
                    "unit": "x",
                    "is_multi_year": False,
                    "validation": {"min": 1, "max": 50, "warning_min": 3, "warning_max": 25}
                },
                {
                    "metric": "P/B Multiple",
                    "description": "Price-to-book multiple",
                    "unit": "x",
                    "is_multi_year": False,
                    "validation": {"min": 0.1, "max": 20, "warning_min": 0.5, "warning_max": 10}
                },
                {
                    "metric": "P/S Multiple",
                    "description": "Price-to-sales multiple",
                    "unit": "x",
                    "is_multi_year": False,
                    "validation": {"min": 0.1, "max": 50, "warning_min": 0.5, "warning_max": 20}
                },
                {
                    "metric": "Outlier Filter Threshold",
                    "description": "Standard deviations for outlier exclusion",
                    "unit": "std dev",
                    "is_multi_year": False,
                    "validation": {"min": 1.0, "max": 4.0, "warning_min": 1.5, "warning_max": 3.0}
                }
            ]
        }
    }
    
    def __init__(self):
        self.ai_fallback = AIFallbackEngine()
    
    # =========================================================================
    # PUBLIC API
    # =========================================================================
    
    async def initialize_assumptions(
        self,
        ticker: str,
        valuation_model: str,
        complete_statements: Dict[str, Any],
        peer_medians: Optional[Dict[str, float]] = None,
        market_data: Optional[Dict[str, Any]] = None,
        peer_companies: Optional[List[Dict[str, Any]]] = None
    ) -> FullAssumptionsResponse:
        """
        Initialize Step 8 with historical trendlines from merged financial statements.
        Categories 1-4 auto-populate from historical statistics (trendlines, CAGR, mean, median).
        Terminal Value requires AI suggestion (news, valuation analysis).
        
        Args:
            ticker: Company ticker symbol
            valuation_model: "DCF", "DUPONT", or "COMPS"
            complete_statements: Merged Step 6 + Step 7 data from FinancialStatementsMerger
            peer_medians: Optional dict of peer median values (e.g., {"ev_ebitda": 10.5, "pe": 15.0})
            market_data: Step 2 risk_metrics (beta, risk_free_rate, market_risk_premium)
            peer_companies: Step 4 full peer company data (debt, equity, beta, tax_rate)
        """
        model_enum = ValuationModel(valuation_model.upper())
        categories = {}
        
        if model_enum == ValuationModel.DCF:
            categories = await self._initialize_dcf_categories(ticker, complete_statements)
        elif model_enum == ValuationModel.DUPONT:
            categories = await self._initialize_dupont_categories(ticker, complete_statements)
        elif model_enum == ValuationModel.COMPS:
            categories = await self._initialize_comps_categories(ticker, complete_statements)
        
        # Auto-populate final_value from historical trendlines for non-terminal categories
        self._auto_populate_from_trendlines(categories, model_enum)
        
        # WACC Pre-population from peer data (Excel model approach)
        peer_wacc_data = []
        if peer_companies:
            peer_wacc_data = self._build_peer_wacc_data(peer_companies)
            self._prepopulate_wacc_from_peers(categories, peer_wacc_data)
        
        # Pre-populate from Step 2 market data
        if market_data:
            self._prepopulate_wacc_from_market(categories, market_data)
            self._prepopulate_terminal_from_market(categories, market_data)
        
        # Pre-populate Terminal EBITDA Multiple from peer median
        if peer_medians and "ev_ebitda" in peer_medians:
            terminal_category = categories.get(AssumptionCategory.TERMINAL_VALUE)
            if terminal_category:
                for assumption in terminal_category.assumptions:
                    if assumption.metric == "Terminal EBITDA Multiple":
                        assumption.final_value = peer_medians["ev_ebitda"]
                        assumption.user_value = peer_medians["ev_ebitda"]
                        assumption.data_source = f"Peer median → EV/EBITDA multiple ({peer_medians['ev_ebitda']:.1f}x)"
        
        return FullAssumptionsResponse(
            session_id=f"step8_{ticker}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            ticker=ticker,
            timestamp=datetime.now(),
            valuation_model=model_enum,
            categories={k.value: v for k, v in categories.items()},
            all_categories_complete=False,
            all_validations_passed=True,
            ready_for_calculation=False,
            message="Assumptions initialized with historical trendlines. Click AI suggestion buttons to generate recommendations for each category."
        )
    
    async def generate_ai_suggestions_for_category(
        self,
        ticker: str,
        valuation_model: str,
        category: str,
        complete_statements: Dict[str, Any],
        peer_medians: Optional[Dict[str, float]] = None,
        api_keys: Optional[Dict[str, str]] = None
    ) -> AssumptionCategoryResponse:
        """
        Generate AI suggestions for a specific category (button click handler).
        This is called when user clicks one of the AI suggestion buttons.
        
        Args:
            ticker: Company ticker symbol
            valuation_model: "DCF", "DUPONT", or "COMPS"
            category: Category name (e.g., "REVENUE_DRIVERS")
            complete_statements: Merged Step 6 + Step 7 data
            peer_medians: Optional dict of peer median values
        """
        model_enum = ValuationModel(valuation_model.upper())
        category_enum = AssumptionCategory(category.upper())
        
        # Determine which category config to use
        if model_enum == ValuationModel.DCF:
            config = self.DCF_CATEGORIES.get(category_enum)
        elif model_enum == ValuationModel.DUPONT:
            config = self.DUPONT_CATEGORIES.get(category_enum)
        elif model_enum == ValuationModel.COMPS:
            config = self.COMPS_CATEGORIES.get(category_enum)
        else:
            raise ValueError(f"Unknown model: {valuation_model}")
        
        if not config:
            raise ValueError(f"Unknown category: {category} for model: {valuation_model}")
        
        # Use request-level API keys if provided, otherwise fall back to instance default
        ai_engine = AIFallbackEngine(api_keys=api_keys) if api_keys else self.ai_fallback
        
        # Generate AI suggestions for each assumption in category
        assumptions = []
        for assumption_def in config["assumptions"]:
            metric = assumption_def["metric"]
            
            # Get historical trendline from complete_statements
            trendline = await self._build_historical_trendline(
                metric=metric,
                complete_statements=complete_statements,
                is_multi_year=assumption_def.get("is_multi_year", False)
            )
            
            # Generate AI suggestion based on historical data and market context
            ai_suggestion = await self._generate_single_ai_suggestion(
                metric=metric,
                category=category_enum,
                trendline=trendline,
                complete_statements=complete_statements,
                peer_medians=peer_medians or {},
                validation_rules=assumption_def.get("validation", {}),
                ai_engine=ai_engine
            )
            
            assumption = AssumptionInput(
                metric=metric,
                category=category_enum,
                description=assumption_def["description"],
                unit=assumption_def["unit"],
                historical_trendline=trendline,
                ai_suggestion=ai_suggestion,
                final_value=ai_suggestion.suggested_value if ai_suggestion else None,
                status=OverrideStatus.ACCEPTED_AI if ai_suggestion else OverrideStatus.DEFAULT,
                is_multi_year=assumption_def.get("is_multi_year", False)
            )
            assumptions.append(assumption)
        
        return AssumptionCategoryResponse(
            category=category_enum,
            category_name=config["name"],
            assumptions=assumptions,
            ai_generated=True,
            generation_timestamp=datetime.now(),
            message=f"AI suggestions generated for {config['name']} based on historical trends and market data."
        )
    
    async def apply_user_override(
        self,
        ticker: str,
        valuation_model: str,
        category: str,
        metric: str,
        user_value: float,
        current_response: FullAssumptionsResponse
    ) -> FullAssumptionsResponse:
        """Apply a user override to a specific metric"""
        model_enum = ValuationModel(valuation_model.upper())
        category_enum = AssumptionCategory(category.upper())
        
        # Find the category and metric
        if category_enum.value not in current_response.categories:
            raise ValueError(f"Category {category} not found")
        
        category_response = current_response.categories[category_enum.value]
        
        # Find and update the metric
        found = False
        for assumption in category_response.assumptions:
            if assumption.metric == metric:
                assumption.user_value = user_value
                assumption.final_value = user_value
                assumption.status = OverrideStatus.MANUAL_OVERRIDE
                assumption.is_valid = True
                assumption.validation_message = "Valid"
                found = True
                break
        
        if not found:
            raise ValueError(f"Metric {metric} not found in category {category}")
        
        # Re-validate all inputs
        return await self.validate_all_assumptions(current_response)
    
    async def validate_all_assumptions(
        self,
        response: FullAssumptionsResponse
    ) -> FullAssumptionsResponse:
        """Validate all assumptions and update response"""
        validation_errors = []
        all_valid = True
        
        for category_key, category_response in response.categories.items():
            for assumption in category_response.assumptions:
                if assumption.final_value is None:
                    continue
                
                # Get validation rules based on metric
                validation_rules = self._get_validation_rules(
                    response.valuation_model.value,
                    category_response.category,
                    assumption.metric
                )
                
                if validation_rules:
                    min_val = validation_rules.get("min", float('-inf'))
                    max_val = validation_rules.get("max", float('inf'))
                    warning_min = validation_rules.get("warning_min", min_val)
                    warning_max = validation_rules.get("warning_max", max_val)
                    
                    if assumption.final_value < min_val or assumption.final_value > max_val:
                        assumption.is_valid = False
                        assumption.validation_message = f"Outside valid range [{min_val} - {max_val}]"
                        validation_errors.append(f"{assumption.metric}: {assumption.validation_message}")
                        all_valid = False
                    elif assumption.final_value < warning_min or assumption.final_value > warning_max:
                        assumption.is_valid = True
                        assumption.validation_message = "Valid but outside typical range"
                        assumption.warning_message = f"Typical range: [{warning_min} - {warning_max}]"
                    else:
                        assumption.is_valid = True
                        assumption.validation_message = "Valid"
        
        response.all_validations_passed = all_valid
        response.total_validation_errors = validation_errors
        response.ready_for_calculation = all_valid and len(response.categories) > 0
        
        if all_valid:
            response.message = "All assumptions validated successfully. Ready for final calculation in Step 9."
        else:
            response.message = f"Validation errors found: {', '.join(validation_errors)}"
        
        return response
    
    # =========================================================================
    # WACC PRE-POPULATION (from Step 2 market data + Step 4 peer companies)
    # =========================================================================
    
    def _build_peer_wacc_data(self, peer_companies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Build WACC calculation data from peer companies (Excel model approach).
        
        For each peer: calculate D/E ratio and unlevered beta using Hamada formula.
        """
        peer_data = []
        for peer in peer_companies:
            debt = peer.get("total_debt", peer.get("debt", 0)) or 0
            equity = peer.get("market_cap", peer.get("equity", 0)) or 0
            beta = peer.get("beta", 1.0) or 1.0
            tax_rate = peer.get("tax_rate", 0.30) or 0.30
            
            # Skip peers with invalid data
            if equity <= 0:
                logger.warning(f"Skipping peer {peer.get('ticker')}: equity={equity} (invalid)")
                continue
            
            d_e = debt / equity if equity > 0 else 0
            
            # Clamp D/E ratio to reasonable range (max 3.0)
            # Very high D/E ratios (e.g., from incorrect yfinance data) skew the average
            d_e = min(d_e, 3.0)
            
            unlevered_beta = beta / (1 + (1 - tax_rate) * d_e) if d_e > 0 else beta
            
            peer_data.append({
                "ticker": peer.get("ticker", peer.get("symbol", "")),
                "company_name": peer.get("company_name", peer.get("name", "")),
                "debt": debt,
                "equity": equity,
                "tax_rate": tax_rate,
                "levered_beta": beta,
                "d_e_ratio": d_e,
                "unlevered_beta": unlevered_beta,
            })
        return peer_data
    
    def _prepopulate_wacc_from_peers(self, categories: Dict, peer_wacc_data: List[Dict]):
        """Pre-populate WACC inputs from peer averages (Excel model approach).
        
        Calculates average D/E, tax rate, and unlevered beta from peers,
        then re-levers beta for the target company.
        """
        if not peer_wacc_data:
            return
        
        num_peers = len(peer_wacc_data)
        avg_tax = sum(p["tax_rate"] for p in peer_wacc_data) / num_peers
        avg_d_e = sum(p["d_e_ratio"] for p in peer_wacc_data) / num_peers
        avg_unlevered_beta = sum(p["unlevered_beta"] for p in peer_wacc_data) / num_peers
        
        # Log peer data for debugging
        for p in peer_wacc_data:
            logger.info(f"  Peer {p.get('ticker')}: debt={p.get('debt',0)/1e9:.1f}B, equity(market_cap)={p.get('equity',0)/1e9:.1f}B, D/E={p.get('d_e_ratio',0):.4f}, beta={p.get('levered_beta',0):.2f}, unlevered_β={p.get('unlevered_beta',0):.2f}, tax={p.get('tax_rate',0):.2%}")
        logger.info(f"Peer WACC averages: D/E={avg_d_e:.4f}, unlevered_β={avg_unlevered_beta:.2f}, tax={avg_tax:.2%}")
        
        # Re-lever beta for target company
        target_levered_beta = avg_unlevered_beta * (1 + (1 - avg_tax) * avg_d_e)
        logger.info(f"Hamada re-lever: {avg_unlevered_beta:.2f} × (1 + (1-{avg_tax:.2f}) × {avg_d_e:.4f}) = {target_levered_beta:.2f}")
        
        peer_tickers = ", ".join(p.get("ticker", "?") for p in peer_wacc_data[:5])
        peer_source_peers = f"{peer_tickers}{' +{} more'.format(num_peers - 5) if num_peers > 5 else ''}"
        
        wacc_category = categories.get(AssumptionCategory.WACC_COMPONENTS)
        if wacc_category:
            for assumption in wacc_category.assumptions:
                if assumption.metric == "Target Debt-to-Equity":
                    assumption.final_value = avg_d_e
                    assumption.user_value = avg_d_e
                    assumption.data_source = f"Peer avg D/E → {num_peers} peers ({peer_source_peers})"
                elif assumption.metric == "Beta":
                    assumption.final_value = target_levered_beta
                    assumption.user_value = target_levered_beta
                    assumption.data_source = f"Peer analysis → Hamada formula (avg unlevered β={avg_unlevered_beta:.2f} × re-lever, {num_peers} peers)"
    
    @staticmethod
    def _normalize_pct_value(val, field_name):
        """Normalize percentage values to decimal (0-1) format.
        
        Some upstream data stores percentages as whole numbers (e.g., 456 for 4.56%)
        instead of decimals (0.0456). This detects and fixes that.
        """
        if val is None or not isinstance(val, (int, float)):
            return val
        pct_fields = {
            'risk_free_rate', 'market_risk_premium', 'country_risk_premium',
            'tax_rate', 'wacc', 'terminal_growth_rate', 'cost_of_debt',
        }
        if field_name in pct_fields:
            if val > 1.0 and val <= 100.0:
                return val / 100.0
            if val > 100.0:
                return val / 10000.0  # Handle basis-point-like values
        return val

    def _prepopulate_wacc_from_market(self, categories: Dict, risk_metrics: Dict):
        """Pre-populate WACC inputs from Step 2 market data (FRED, yfinance)."""
        if not risk_metrics:
            return
        
        wacc_category = categories.get(AssumptionCategory.WACC_COMPONENTS)
        if wacc_category:
            for assumption in wacc_category.assumptions:
                if assumption.metric == "Risk-Free Rate":
                    val = risk_metrics.get("risk_free_rate", {})
                    if isinstance(val, dict):
                        val = val.get("value")
                    if val is not None:
                        val = self._normalize_pct_value(val, "risk_free_rate")
                        assumption.final_value = val
                        assumption.user_value = val
                        assumption.data_source = "Market data → 10Y Treasury yield (yfinance/FRED)"
                elif assumption.metric == "Market Risk Premium":
                    val = risk_metrics.get("market_risk_premium", {})
                    if isinstance(val, dict):
                        val = val.get("value")
                    if val is not None:
                        val = self._normalize_pct_value(val, "market_risk_premium")
                        assumption.final_value = val
                        assumption.user_value = val
                        assumption.data_source = "Market data → Equity Risk Premium (Damodaran/yfinance)"
                elif assumption.metric == "Country Risk Premium":
                    val = risk_metrics.get("country_risk_premium", {})
                    if isinstance(val, dict):
                        val = val.get("value")
                    if val is not None:
                        val = self._normalize_pct_value(val, "country_risk_premium")
                        assumption.final_value = val
                        assumption.user_value = val
                        assumption.data_source = "Market data → Country Risk Premium"
                elif assumption.metric == "Beta":
                    val = risk_metrics.get("beta", {})
                    if isinstance(val, dict):
                        val = val.get("value")
                    if val is not None and assumption.final_value is None:
                        assumption.final_value = val
                        assumption.user_value = val
                        assumption.data_source = "Market data → yfinance levered beta"
        # After pre-population, calculate WACC from components
        self._calculate_wacc(categories)
    
    def _calculate_wacc(self, categories: Dict):
        """Calculate WACC from pre-populated components.
        
        WACC = (D/V × Rd × (1-t)) + (E/V × (Rf + β × (MRP + CRP)))
        
        Where:
        - D/V = debt weight from D/E ratio
        - E/V = 1 - D/V
        - Rd = pre-tax cost of debt
        - t = statutory tax rate
        - Rf = risk-free rate
        - β = levered beta
        - MRP = market risk premium
        - CRP = country risk premium
        """
        wacc_category = categories.get(AssumptionCategory.WACC_COMPONENTS)
        if not wacc_category:
            return
        
        rf = None
        beta = None
        mrp = None
        crp = 0.0
        cod = 0.05  # default cost of debt
        de = 0.3    # default D/E ratio
        tax_rate = 0.21  # default tax rate
        
        for assumption in wacc_category.assumptions:
            val = assumption.final_value if assumption.final_value is not None else assumption.user_value
            if assumption.metric == "Risk-Free Rate":
                rf = self._normalize_pct_value(val, "risk_free_rate")
            elif assumption.metric == "Market Risk Premium":
                mrp = self._normalize_pct_value(val, "market_risk_premium")
            elif assumption.metric == "Country Risk Premium":
                crp = self._normalize_pct_value(val, "country_risk_premium") if val is not None else 0.0
            elif assumption.metric == "Pre-Tax Cost of Debt":
                if val is not None:
                    cod = self._normalize_pct_value(val, "pre_tax_cost_of_debt")
            elif assumption.metric == "Target Debt-to-Equity":
                if val is not None:
                    de = val
            elif assumption.metric == "Beta":
                beta = val
        
        # Get tax rate from COST_MARGINS category
        cost_margins = categories.get(AssumptionCategory.COST_MARGINS)
        if cost_margins:
            for a in cost_margins.assumptions:
                if a.metric == "Effective Tax Rate":
                    val = a.final_value if a.final_value is not None else a.user_value
                    if val is not None:
                        tax_rate = self._normalize_pct_value(val, "effective_tax_rate")
                    break
        
        if rf is not None and beta is not None and mrp is not None:
            # Full WACC formula
            dv = de / (1 + de) if de else 0.15
            ev = 1 - dv
            after_tax_cost_of_debt = cod * (1 - tax_rate)
            cost_of_equity = rf + beta * (mrp + crp)
            wacc = dv * after_tax_cost_of_debt + ev * cost_of_equity
            # Clamp to reasonable range (decimal format: 0.03 = 3%, 0.25 = 25%)
            wacc = max(0.03, min(0.25, wacc))
            crp_display = f" + CRP={crp*100:.2f}%" if crp > 0 else ""
            logger.info(
                f"WACC calculation: Rf={rf:.4f} Beta={beta:.4f} MRP={mrp:.4f} CRP={crp:.4f} "
                f"D/E={de:.2f} Rd={cod:.4f} t={tax_rate:.4f} → WACC={wacc:.4f}"
            )
            for assumption in wacc_category.assumptions:
                if assumption.metric == "WACC":
                    assumption.final_value = wacc
                    assumption.user_value = wacc
                    assumption.data_source = (
                        f"Calculated → ({dv*100:.1f}% × Rd({cod*100:.2f}%) × (1-t)) + "
                        f"({ev*100:.1f}% × (Rf({rf*100:.2f}%) + β({beta:.2f}) × MRP({mrp*100:.2f}%{crp_display})))"
                    )
                    logger.info(f"Set WACC assumption final_value={wacc:.4f} (decimal)")
                    break
            else:
                logger.warning(f"WACC metric not found in {len(wacc_category.assumptions)} assumptions: {[a.metric for a in wacc_category.assumptions]}")
        else:
            logger.warning(f"WACC calculation skipped: Rf={rf} Beta={beta} MRP={mrp}")
    
    # =========================================================================
    # 5-YEAR TREND-BASED PROJECTION
    # =========================================================================
    
    # Metrics where lower is better (for mean reversion direction)
    _LOWER_IS_BETTER = {
        "OpEx Growth", "Effective Tax Rate",
        "Accounts Receivable Days", "Inventory Days", "Accounts Payable Days",
    }
    
    # Forecast-relevant metrics that should get a 5-year projection series
    _FORECAST_DRIVER_METRICS = {
        "Revenue Growth", "Revenue Volume Growth", "Volume Growth",
        "COGS Growth Rate",
        "OpEx Growth", "Capital Expenditure", "Effective Tax Rate",
        "Accounts Receivable Days", "Inventory Days", "Accounts Payable Days",
        "COGS % of Revenue",
    }
    
    # Metric type classification for projection strategy
    _METRIC_PROJECTION_TYPE = {
        # Growth rates — use CAGR/avg YoY with convergence
        "Revenue Growth": "growth_rate",
        "Revenue Volume Growth": "growth_rate",
        "Volume Growth": "growth_rate",
        "COGS Growth Rate": "growth_rate",
        "OpEx Growth": "growth_rate",
        # Ratios — mean reversion from latest to average
        "Capital Expenditure": "ratio",
        "Effective Tax Rate": "ratio",
        "COGS % of Revenue": "ratio",
        # Working capital days — mean reversion toward average
        "Accounts Receivable Days": "days",
        "Inventory Days": "days",
        "Accounts Payable Days": "days",
    }
    
    # Default long-term stable rates by metric
    _LONG_TERM_DEFAULTS = {
        "Revenue Growth": 0.04,       # 4% long-term GDP-like growth
        "Revenue Volume Growth": 0.04,  # 4% long-term volume growth
        "Volume Growth": 0.04,        # 4% long-term volume growth
        "COGS Growth Rate": 0.03,     # 3% long-term COGS growth
        "OpEx Growth": 0.065,         # 6.5% — historical average for most companies
    }
    
    @classmethod
    def _project_five_year_series(
        cls,
        metric: str,
        trendline: "HistoricalTrendline",
        validation_rules: Optional[Dict[str, float]] = None,
    ) -> Dict[int, float]:
        """Generate a 5-year forecast projection series using trend-based methods.
        
        Projection strategies by metric type:
        - growth_rate: CAGR or avg YoY as base, converges toward long-term stable rate
        - ratio: Mean reversion — Year 1 = latest, gradually converges to 3-year average
        - days: Mean reversion toward historical average
        
        Args:
            metric: Metric name (e.g., "Revenue Growth")
            trendline: Historical trendline with statistics
            validation_rules: Optional min/max validation bounds
            
        Returns:
            Dict mapping forecast year (1-5) to projected value
        """
        projection_type = cls._METRIC_PROJECTION_TYPE.get(metric, "ratio")
        latest = trendline.latest_value
        average = trendline.average
        cagr = trendline.cagr
        avg_yoy = trendline.average_yoy_growth
        
        # Fallback: if no latest value, use average or median
        if latest is None:
            latest = average or trendline.median
        if latest is None:
            return {}
        
        min_val = validation_rules.get("min", float('-inf')) if validation_rules else float('-inf')
        max_val = validation_rules.get("max", float('inf')) if validation_rules else float('inf')
        
        # ── Mean reversion schedule (fraction of gap closed each year) ──
        reversion_schedule = [0.20, 0.30, 0.40, 0.50]
        
        def _clamp(v: float) -> float:
            """Clamp value to validation bounds"""
            return max(min_val, min(max_val, v))
        
        def _mean_revert(start: float, target: float, schedule: List[float]) -> List[float]:
            """Apply progressive mean reversion from start toward target"""
            values = []
            current = start
            for frac in schedule:
                current = current + (target - current) * frac
                values.append(current)
            return values
        
        # ── Projection by type ──
        if projection_type == "growth_rate":
            # Growth rates: Year 1 ≈ latest, converge toward long-term default
            base_rate = latest
            # Priority: weighted_growth > avg_yoy > cagr
            if trendline.weighted_growth is not None:
                base_rate = trendline.weighted_growth
            elif avg_yoy is not None:
                base_rate = avg_yoy
            elif cagr is not None:
                base_rate = cagr
            
            # Long-term target: use a stable default or the historical average
            lt_default = cls._LONG_TERM_DEFAULTS.get(metric)
            if lt_default is not None:
                target = lt_default
            else:
                target = average if average is not None else base_rate
            
            # If the metric should always be non-negative, clamp
            if metric in ("Inflation Rate",):
                base_rate = max(0.0, base_rate)
                target = max(0.02, target)  # At least 2% for inflation
            
            series = _mean_revert(base_rate, target, reversion_schedule)
            # Year 1 is the starting point before reversion
            projected = {1: _clamp(base_rate)}
            for i, v in enumerate(series):
                projected[i + 2] = _clamp(v)
            return projected
        
        elif projection_type == "days":
            # Working capital days: Year 1 = latest, converge to average
            start = latest
            target = average if average is not None else latest
            series = _mean_revert(start, target, reversion_schedule)
            projected = {1: _clamp(start)}
            for i, v in enumerate(series):
                projected[i + 2] = _clamp(v)
            return projected
        
        else:  # "ratio"
            # Ratios (CapEx, Tax Rate, COGS): Year 1 = latest, converge to average
            start = latest
            target = average if average is not None else latest
            
            # CapEx: special handling — must be non-negative
            if metric == "Capital Expenditure":
                start = max(0.0, start)
                target = max(0.0, target)
            
            # Tax Rate: reasonable bounds
            if metric == "Effective Tax Rate":
                start = max(0.05, min(0.40, start))
                target = max(0.15, min(0.35, target)) if target is not None else start
            
            series = _mean_revert(start, target, reversion_schedule)
            projected = {1: _clamp(start)}
            for i, v in enumerate(series):
                projected[i + 2] = _clamp(v)
            return projected
    
    def _auto_populate_from_trendlines(self, categories: Dict, model_enum: ValuationModel):
        """Auto-populate final_value from historical trendlines for categories 1-4.
        
        For each assumption that has a historical trendline:
        - Multi-year metrics: Use average_yoy_growth if available, else CAGR, else average
        - Single-year metrics: Use median (robust to outliers), else average
        - WACC/Terminal categories: Skip (handled by _prepopulate_wacc_from_market/peers)
        
        TERMINAL_VALUE is NOT auto-populated — it requires AI suggestion.
        """
        # Categories to auto-populate (all except TERMINAL_VALUE)
        AUTO_POPULATE_CATEGORIES = {
            AssumptionCategory.REVENUE_DRIVERS,
            AssumptionCategory.COST_MARGINS,
            AssumptionCategory.WORKING_CAPITAL,
            AssumptionCategory.WACC_COMPONENTS,
            AssumptionCategory.FINANCING,
            AssumptionCategory.MODEL_PARAMETERS,
        }
        
        # For DuPont and Comps, auto-populate their specific categories too
        if model_enum == ValuationModel.DUPONT:
            AUTO_POPULATE_CATEGORIES.add(AssumptionCategory.DUPONT_TARGETS)
        elif model_enum == ValuationModel.COMPS:
            AUTO_POPULATE_CATEGORIES.add(AssumptionCategory.COMPS_MULTIPLES)
        
        for cat_enum, cat_response in categories.items():
            if cat_enum not in AUTO_POPULATE_CATEGORIES:
                continue
            
            for assumption in cat_response.assumptions:
                # Skip if already pre-populated (e.g., WACC from peers/market)
                if assumption.final_value is not None:
                    continue
                
                trendline = assumption.historical_trendline
                if not trendline:
                    continue
                
                # Choose best value from trendline statistics
                value = None
                source = "historical_trendline"
                
                if assumption.is_multi_year:
                    # Multi-year: prefer weighted_growth for growth_rate metrics,
                    # then average_yoy_growth, then CAGR, then average
                    metric_type = self._METRIC_PROJECTION_TYPE.get(assumption.metric, "ratio")
                    if metric_type == "growth_rate" and trendline.weighted_growth is not None:
                        value = trendline.weighted_growth
                        source = "weighted_growth"
                    elif trendline.average_yoy_growth is not None:
                        value = trendline.average_yoy_growth
                        source = "avg_yoy_growth"
                    elif trendline.cagr is not None:
                        value = trendline.cagr
                        source = "cagr"
                    elif trendline.average is not None:
                        value = trendline.average
                        source = "average"
                else:
                    # Single-year: prefer median, then average, then latest_value
                    if trendline.median is not None:
                        value = trendline.median
                        source = "median"
                    elif trendline.average is not None:
                        value = trendline.average
                        source = "average"
                    elif trendline.latest_value is not None:
                        value = trendline.latest_value
                        source = "latest_value"
                
                if value is not None:
                    # Validate against validation rules
                    validation_rules = self._get_validation_rules(
                        model_enum.value, cat_enum, assumption.metric
                    )
                    if validation_rules:
                        min_val = validation_rules.get("min", float('-inf'))
                        max_val = validation_rules.get("max", float('inf'))
                        if value < min_val or value > max_val:
                            logger.warning(
                                f"Auto-populate {assumption.metric}: value {value:.4f} "
                                f"outside valid range [{min_val}, {max_val}], skipping"
                            )
                            continue
                    
                    assumption.final_value = value
                    assumption.user_value = value
                    assumption.status = OverrideStatus.DEFAULT
                    
                    # ── 5-Year Trend-Based Projection for forecast drivers ──
                    if assumption.metric in self._FORECAST_DRIVER_METRICS:
                        year_series = self._project_five_year_series(
                            metric=assumption.metric,
                            trendline=trendline,
                            validation_rules=validation_rules,
                        )
                        if year_series:
                            assumption.year_values = year_series
                            # Update final_value to Year 1 of projection
                            assumption.final_value = year_series.get(1, value)
                            assumption.user_value = assumption.final_value
                            logger.info(
                                f"Projected 5-year series for {assumption.metric}: "
                                f"Y1={year_series.get(1, 0):.4f}, "
                                f"Y3={year_series.get(3, 0):.4f}, "
                                f"Y5={year_series.get(5, 0):.4f}"
                            )
                    
                    # Map internal source key to human-readable data_source
                    # Check if metric is a fixed default (not from real historicals)
                    metric_config = METRIC_CALC_CONFIG.get(assumption.metric)
                    if metric_config and metric_config.get("type") == "default":
                        default_val = metric_config.get("value", value)
                        assumption.data_source = f"Industry default → {default_val} {assumption.unit}"
                    else:
                        _source_map = {
                            "avg_yoy_growth": "Historical → Avg YoY growth",
                            "cagr": "Historical → CAGR",
                            "average": "Historical → Mean",
                            "median": "Historical → Median",
                            "latest_value": "Historical → Latest period",
                        }
                        src_label = _source_map.get(source, f"Historical → {source}")
                        if assumption.metric in self._FORECAST_DRIVER_METRICS and assumption.year_values:
                            src_label += " → 5yr projection"
                        assumption.data_source = src_label
                    logger.info(
                        f"Auto-populated {assumption.metric} = {assumption.final_value:.4f} "
                        f"(source: {source}, year_values: {bool(assumption.year_values)})"
                    )
    
    def _prepopulate_terminal_from_market(self, categories: Dict, risk_metrics: Dict):
        """Pre-populate Terminal Growth Rate from market data (GDP growth estimate)."""
        if not risk_metrics:
            return
        
        terminal_category = categories.get(AssumptionCategory.TERMINAL_VALUE)
        if not terminal_category:
            return
        
        for assumption in terminal_category.assumptions:
            if assumption.metric == "Terminal Growth Rate" and assumption.final_value is None:
                # Try to get GDP growth from market data
                gdp_growth = risk_metrics.get("gdp_growth", {})
                if isinstance(gdp_growth, dict):
                    gdp_growth = gdp_growth.get("value")
                if gdp_growth is not None:
                    # Normalize GDP growth to decimal format
                    gdp_growth = self._normalize_pct_value(gdp_growth, "terminal_growth_rate")
                    # Conservative: 80% of GDP growth, capped at 5%
                    assumption.final_value = min(gdp_growth * 0.8, 0.05)
                    assumption.user_value = assumption.final_value
                    assumption.data_source = "Market data → GDP growth (80% × real GDP, capped at 5%)"
    
    # =========================================================================
    # SCENARIO GENERATION (Best/Worst from Base Case using historical volatility)
    # =========================================================================
    
    async def generate_scenarios(
        self,
        ticker: str,
        valuation_model: str,
        base_case: Dict[str, Any],
        complete_statements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate Best/Worst scenarios from Base Case using historical volatility.
        
        For each metric:
        1. Get historical trendline std_dev
        2. Best = base + std_dev (or base - std_dev for "lower is better" metrics)
        3. Worst = base - std_dev (or base + std_dev for "lower is better" metrics)
        4. Clamp to validation bounds
        
        Args:
            ticker: Company ticker symbol
            valuation_model: "DCF", "DUPONT", or "COMPS"
            base_case: Dict of {metric_name: value} for the base case
            complete_statements: Merged Step 6 + Step 7 data
        
        Returns:
            Dict with best_case, worst_case, and volatility data
        """
        scenarios = {"best_case": {}, "worst_case": {}}
        volatility = {}
        
        # Mapping from frontend field names to backend metric names (METRIC_CALC_CONFIG keys)
        frontend_to_backend_metric = {
            "sales_volume_growth": "Revenue Growth",
            "cogs_growth_rate": "COGS Growth Rate",
            "opex_growth": "OpEx Growth",
            "capital_expenditure": "Capital Expenditure",
            "receivables_days": "Accounts Receivable Days",
            "inventory_days": "Inventory Days",
            "payables_days": "Accounts Payable Days",
            "tax_rate": "Effective Tax Rate",
        }
        
        # Metrics where lower is better (inverted for Best/Worst)
        lower_is_better = {"OpEx Growth", "Effective Tax Rate",
                          "Accounts Receivable Days", "Inventory Days", "Accounts Payable Days"}
        
        for metric, base_value in base_case.items():
            if base_value is None:
                continue
            
            # Map frontend field name to backend metric name for trendline lookup
            backend_metric = frontend_to_backend_metric.get(metric, metric)
            
            # Get historical trendline std_dev
            trendline = await self._build_historical_trendline(
                backend_metric, complete_statements, is_multi_year=False
            )
            raw_std_dev = trendline.standard_deviation if trendline and trendline.standard_deviation else None
            
            # Accept either scalar or 5-year array from frontend
            if isinstance(base_value, list):
                years = base_value
            else:
                years = [base_value] * 5
            
            best_years = []
            worst_years = []
            std_dev_values = []
            
            for i, year_val in enumerate(years):
                if year_val is None:
                    best_years.append(year_val)
                    worst_years.append(year_val)
                    std_dev_values.append(0)
                    continue
                
                # Use historical std_dev if available, otherwise scale dynamically
                # by year index (wider spread for later years as uncertainty grows)
                if raw_std_dev is not None:
                    year_std = raw_std_dev
                else:
                    # Dynamic std_dev: base uncertainty grows with forecast horizon
                    year_factor = 1.0 + (i * 0.1)  # Year 1: 1.0x, Year 5: 1.4x
                    year_std = abs(year_val) * 0.15 * year_factor if year_val != 0 else 0.0
                
                # Clamp std_dev to reasonable bounds
                if "Days" in backend_metric:
                    year_std = min(year_std, 30.0)
                else:
                    year_std = min(year_std, abs(year_val) * 0.50) if year_val != 0 else 0.0
                
                std_dev_values.append(year_std)
                
                if backend_metric in lower_is_better:
                    best_years.append(year_val - year_std)
                    worst_years.append(year_val + year_std)
                else:
                    best_years.append(year_val + year_std)
                    worst_years.append(year_val - year_std)
            
            volatility[metric] = std_dev_values if len(std_dev_values) > 1 else (std_dev_values[0] if std_dev_values else 0)
            scenarios["best_case"][metric] = best_years if len(best_years) > 1 else (best_years[0] if best_years else base_value)
            scenarios["worst_case"][metric] = worst_years if len(worst_years) > 1 else (worst_years[0] if worst_years else base_value)
        
        return {
            "best_case": scenarios["best_case"],
            "worst_case": scenarios["worst_case"],
            "volatility": volatility
        }
    
    # =========================================================================
    # CATEGORY INITIALIZATION
    # =========================================================================
    
    async def _initialize_dcf_categories(
        self,
        ticker: str,
        complete_statements: Dict[str, Any]
    ) -> Dict[AssumptionCategory, AssumptionCategoryResponse]:
        """Initialize DCF assumption categories with historical trendlines"""
        categories = {}
        
        for category, config in self.DCF_CATEGORIES.items():
            assumptions = []
            for assumption_def in config["assumptions"]:
                # Build historical trendline directly from complete_statements
                trendline = await self._build_historical_trendline(
                    metric=assumption_def["metric"],
                    complete_statements=complete_statements,
                    is_multi_year=assumption_def.get("is_multi_year", False)
                )
                
                assumption = AssumptionInput(
                    metric=assumption_def["metric"],
                    category=category,
                    description=assumption_def["description"],
                    unit=assumption_def["unit"],
                    historical_trendline=trendline,
                    is_multi_year=assumption_def.get("is_multi_year", False)
                )
                assumptions.append(assumption)
            
            categories[category] = AssumptionCategoryResponse(
                category=category,
                category_name=config["name"],
                assumptions=assumptions,
                ai_generated=False,
                message=f"Historical trendlines loaded. Click 'Suggest {config['name']}' button for AI recommendations."
            )
        
        return categories
    
    async def _initialize_dupont_categories(
        self,
        ticker: str,
        complete_statements: Dict[str, Any]
    ) -> Dict[AssumptionCategory, AssumptionCategoryResponse]:
        """Initialize DuPont assumption categories with historical trendlines"""
        categories = {}
        
        for category, config in self.DUPONT_CATEGORIES.items():
            assumptions = []
            for assumption_def in config["assumptions"]:
                trendline = await self._build_historical_trendline(
                    metric=assumption_def["metric"],
                    complete_statements=complete_statements,
                    is_multi_year=assumption_def.get("is_multi_year", False)
                )
                
                assumption = AssumptionInput(
                    metric=assumption_def["metric"],
                    category=category,
                    description=assumption_def["description"],
                    unit=assumption_def["unit"],
                    historical_trendline=trendline,
                    is_multi_year=assumption_def.get("is_multi_year", False)
                )
                assumptions.append(assumption)
            
            categories[category] = AssumptionCategoryResponse(
                category=category,
                category_name=config["name"],
                assumptions=assumptions,
                ai_generated=False,
                message=f"Historical trendlines loaded. Click 'Suggest {config['name']}' button for AI recommendations."
            )
        
        return categories
    
    async def _initialize_comps_categories(
        self,
        ticker: str,
        complete_statements: Dict[str, Any]
    ) -> Dict[AssumptionCategory, AssumptionCategoryResponse]:
        """Initialize Comps assumption categories with historical trendlines"""
        categories = {}
        
        for category, config in self.COMPS_CATEGORIES.items():
            assumptions = []
            for assumption_def in config["assumptions"]:
                trendline = await self._build_historical_trendline(
                    metric=assumption_def["metric"],
                    complete_statements=complete_statements,
                    is_multi_year=assumption_def.get("is_multi_year", False)
                )
                
                assumption = AssumptionInput(
                    metric=assumption_def["metric"],
                    category=category,
                    description=assumption_def["description"],
                    unit=assumption_def["unit"],
                    historical_trendline=trendline,
                    is_multi_year=assumption_def.get("is_multi_year", False)
                )
                assumptions.append(assumption)
            
            categories[category] = AssumptionCategoryResponse(
                category=category,
                category_name=config["name"],
                assumptions=assumptions,
                ai_generated=False,
                message=f"Historical trendlines loaded. Click 'Suggest {config['name']}' button for AI recommendations."
            )
        
        return categories
    
    # =========================================================================
    # DATA EXTRACTION FROM COMPLETE_STATEMENTS
    # =========================================================================
    
    @staticmethod
    def _extract_from_complete_statements(
        metric: str,
        complete_statements: Dict[str, Any]
    ) -> Tuple[List[float], List[int]]:
        """
        Extract time series of values for a metric from complete_statements.
        
        Supports derived calculations:
        - "direct": read field value directly
        - "ratio": numerator / denominator
        - "days": (numerator / denominator) * 365
        - "yoy": year-over-year growth rate of a single field
        
        Args:
            metric: Assumption metric name (e.g., "Revenue Volume Growth")
            complete_statements: Merged financial statements from FinancialStatementsMerger
        
        Returns:
            Tuple of (values, years) sorted chronologically (oldest → newest)
        """
        config = METRIC_CALC_CONFIG.get(metric)
        if config is None:
            logger.info(f"[CapEx Debug] No METRIC_CALC_CONFIG for metric '{metric}'")
            return [], []
        
        calc_type = config["type"]
        logger.info(f"[CapEx Debug] Extracting '{metric}': type={calc_type}, section={config.get('section')}, field={config.get('field')}")
        
        def _get_field_values(section_name: str, field_name: str) -> Dict[int, float]:
            """Extract {year: value} from a section's field."""
            section = complete_statements.get(section_name, {})
            if not isinstance(section, dict):
                logger.info(f"[CapEx Debug] Section '{section_name}' not found. Top-level keys: {list(complete_statements.keys())}")
                return {}
            result = {}
            # Log first period's keys for debugging
            if section:
                first_period = next(iter(section), None)
                if first_period and isinstance(section[first_period], dict):
                    logger.info(f"[CapEx Debug] Section '{section_name}' period '{first_period}' fields: {list(section[first_period].keys())[:30]}")
            for period, period_data in section.items():
                if not isinstance(period_data, dict):
                    continue
                val = period_data.get(field_name)
                if val is None:
                    continue
                try:
                    year = int(period[:4]) if len(period) >= 4 else None
                except (ValueError, TypeError):
                    continue
                if year:
                    try:
                        result[year] = float(val)
                    except (ValueError, TypeError):
                        pass
            return result
        
        if calc_type == "direct":
            field_vals = _get_field_values(config["section"], config["field"])
            logger.info(f"[CapEx Debug] Direct field values for {config['section']}.{config['field']}: {len(field_vals)} entries, keys={sorted(field_vals.keys())}")
            if not field_vals:
                return [], []
            sorted_years = sorted(field_vals.keys())
            # Use absolute values for cash flow items (CapEx is typically negative)
            return [abs(field_vals[y]) for y in sorted_years], sorted_years
        
        elif calc_type == "ratio":
            num_vals = _get_field_values(config["num_section"], config["numerator"])
            den_vals = _get_field_values(config["den_section"], config["denominator"])
            common_years = sorted(set(num_vals) & set(den_vals))
            if not common_years:
                return [], []
            # Use abs() for numerator: items like CapEx are stored negative in cash flow
            # but the ratio should represent the magnitude relative to revenue
            numerator_name = config.get("numerator", "")
            use_abs = numerator_name in ("capex",)
            if use_abs:
                values = [abs(num_vals[y]) / den_vals[y] for y in common_years if den_vals[y] != 0]
            else:
                values = [num_vals[y] / den_vals[y] for y in common_years if den_vals[y] != 0]
            return values, common_years[:len(values)]
        
        elif calc_type == "days":
            num_vals = _get_field_values(config["num_section"], config["numerator"])
            den_vals = _get_field_values(config["den_section"], config["denominator"])
            common_years = sorted(set(num_vals) & set(den_vals))
            if not common_years:
                return [], []
            values = [(num_vals[y] / den_vals[y]) * 365 for y in common_years if den_vals[y] != 0]
            return values, common_years[:len(values)]
        
        elif calc_type == "yoy":
            field_vals = _get_field_values(config["section"], config["field"])
            if not field_vals or len(field_vals) < 2:
                return [], []
            sorted_years = sorted(field_vals.keys())
            values = []
            years_out = []
            for i in range(1, len(sorted_years)):
                prev_val = field_vals[sorted_years[i - 1]]
                if prev_val != 0:
                    growth = (field_vals[sorted_years[i]] - prev_val) / abs(prev_val)
                    values.append(growth)
                    years_out.append(sorted_years[i])
            return values, years_out
        
        elif calc_type == "latest_ratio":
            # Use only the most recent year's ratio (for Cost of Debt etc.)
            num_vals = _get_field_values(config["num_section"], config["numerator"])
            den_vals = _get_field_values(config["den_section"], config["denominator"])
            common_years = sorted(set(num_vals) & set(den_vals))
            if not common_years:
                return [], []
            latest_year = common_years[-1]
            if den_vals[latest_year] == 0:
                return [], []
            ratio = num_vals[latest_year] / den_vals[latest_year]
            # Apply thresholds if defined
            min_thresh = config.get("min_threshold")
            max_thresh = config.get("max_threshold")
            if min_thresh is not None and ratio < min_thresh:
                ratio = min_thresh
            if max_thresh is not None and ratio > max_thresh:
                ratio = max_thresh
            return [ratio], [latest_year]
        
        elif calc_type == "yoy_diff":
            # Year-over-year absolute difference of a field
            field_vals = _get_field_values(config["section"], config["field"])
            if not field_vals or len(field_vals) < 2:
                return [], []
            sorted_years = sorted(field_vals.keys())
            values = []
            years_out = []
            for i in range(1, len(sorted_years)):
                diff = field_vals[sorted_years[i]] - field_vals[sorted_years[i - 1]]
                values.append(diff)
                years_out.append(sorted_years[i])
            return values, years_out
        
        elif calc_type == "product":
            # Product of two fields: numerator × denominator
            num_vals = _get_field_values(config["num_section"], config["numerator"])
            # For "den_section" == "config", use a default interest rate
            if config.get("den_section") == "config":
                # Use latest LT debt × cost of debt (default 5%)
                den_vals = {y: 0.05 for y in num_vals}
            else:
                den_vals = _get_field_values(config["den_section"], config["denominator"])
            common_years = sorted(set(num_vals) & set(den_vals))
            if not common_years:
                return [], []
            values = [num_vals[y] * den_vals[y] for y in common_years]
            return values, common_years[:len(values)]
        
        elif calc_type == "default":
            # Fixed default value — no historical data needed
            default_val = config.get("value", 0)
            return [default_val], [2024]
        
        return [], []
    
    # =========================================================================
    # HISTORICAL TRENDLINE (refactored: reads from complete_statements,
    # uses statistical_utils for all calculations)
    # =========================================================================
    
    async def _build_historical_trendline(
        self,
        metric: str,
        complete_statements: Dict[str, Any],
        is_multi_year: bool = False
    ) -> Optional[HistoricalTrendline]:
        """Build historical trendline from complete_statements for a given metric.
        
        Reads directly from the merged financial statements (single data source).
        Uses statistical_utils functions for all statistical calculations.
        
        Args:
            metric: Assumption metric name
            complete_statements: Merged Step 6 + Step 7 financial data
            is_multi_year: Whether this metric spans multiple forecast years
        """
        try:
            values, years = self._extract_from_complete_statements(metric, complete_statements)
            
            if not values or not years:
                return None
            
            # Calculate comprehensive statistics using statistical_utils
            avg = calculate_average(values)
            median_val = calculate_median(values)
            min_max = calculate_min_max(values)
            std_dev = calculate_volatility(values)
            
            # Determine if this is a growth-rate metric (type "yoy")
            metric_calc_config = METRIC_CALC_CONFIG.get(metric, {}) or {}
            is_yoy_metric = metric_calc_config.get("type") == "yoy"
            
            # CAGR
            cagr = None
            if len(values) >= 2:
                periods = years[-1] - years[0]
                if periods > 0:
                    if is_yoy_metric:
                        # For growth-rate metrics (e.g. Revenue Growth, COGS Growth Rate),
                        # the values are YoY growth rates (potentially with different signs).
                        # Standard CAGR from these values is meaningless. Instead, compute
                        # the compound growth rate of the underlying absolute values using
                        # the average YoY growth rate (deferred to below after avg_yoy_growth
                        # is calculated).
                        pass
                    else:
                        cagr = calculate_cagr(values[0], values[-1], periods)
            
            # Year-over-year growth rates
            # For "yoy" type metrics, values ARE already YoY growth rates
            # (computed by _extract_from_complete_statements). Use them directly
            # — do NOT call calculate_year_over_year_growth() on them
            # (that would compute YoY growth OF YoY growth = double counting).
            avg_yoy_growth = None
            weighted_growth = None
            if is_yoy_metric:
                # values are already growth rates, use directly
                avg_yoy_growth = calculate_average(values)
                weighted_growth = calculate_weighted_growth(values)
            else:
                yoy_growth = calculate_year_over_year_growth(values, years)
                if yoy_growth:
                    growth_rates = [g["growth_rate"] for g in yoy_growth]
                    avg_yoy_growth = calculate_average(growth_rates)
                    weighted_growth = calculate_weighted_growth(growth_rates)
            
            # CAGR computation for growth-rate metrics and fallback for standard metrics
            periods = years[-1] - years[0] if len(years) >= 2 else 0
            if periods > 0:
                if is_yoy_metric and avg_yoy_growth is not None:
                    # For growth-rate metrics, compute CAGR of the underlying absolute
                    # values from the average YoY growth rate. This gives the compound
                    # growth rate that, if applied uniformly, would produce the same
                    # end value as the actual series.
                    try:
                        cagr = (1 + avg_yoy_growth) ** periods - 1
                    except (ValueError, OverflowError):
                        pass
                elif cagr is None and avg_yoy_growth is not None:
                    # Standard CAGR fallback when direct CAGR failed
                    # (e.g. negative first value)
                    try:
                        cagr = (1 + avg_yoy_growth) ** periods - 1
                    except (ValueError, OverflowError):
                        pass
            
            # Trend direction
            trend_direction = "stable"
            if len(values) >= 2:
                if values[-1] > values[0] * 1.1:
                    trend_direction = "increasing"
                elif values[-1] < values[0] * 0.9:
                    trend_direction = "decreasing"
            
            # Volatility category (derived from coefficient of variation)
            volatility = "low"
            if std_dev is not None and avg is not None and avg != 0:
                cv = std_dev / abs(avg)
                if cv > 0.3:
                    volatility = "high"
                elif cv > 0.15:
                    volatility = "medium"
            
            trend_points = [HistoricalTrendPoint(year=y, value=v) for y, v in zip(years, values)]
            
            return HistoricalTrendline(
                metric=metric,
                trend_points=trend_points,
                average=avg if avg is not None else 0.0,
                cagr=cagr,
                trend_direction=trend_direction,
                volatility=volatility,
                median=median_val,
                min_value=min_max["min"],
                max_value=min_max["max"],
                standard_deviation=std_dev,
                average_yoy_growth=avg_yoy_growth,
                weighted_growth=weighted_growth,
                latest_value=values[-1] if values else None,
                oldest_value=values[0] if values else None
            )
        except Exception as e:
            logger.warning(f"Failed to build trendline for {metric}: {e}")
            return None
    
    # =========================================================================
    # AI SUGGESTION ENGINE
    # =========================================================================
    
    async def _generate_single_ai_suggestion(
        self,
        metric: str,
        category: AssumptionCategory,
        trendline: Optional[HistoricalTrendline],
        complete_statements: Dict[str, Any],
        peer_medians: Dict[str, float],
        validation_rules: Dict[str, float],
        ai_engine=None
    ) -> Optional[AISuggestion]:
        """Generate AI suggestion for a single metric using LLM with fallback"""
        try:
            # Get historical average as baseline
            historical_avg = trendline.average if trendline else None
            trend_direction = trendline.trend_direction if trendline else "stable"
            volatility = trendline.volatility if trendline else "low"
            
            # Build comprehensive prompt for AI
            prompt = self._build_assumption_prompt(
                metric=metric,
                category=category,
                trendline=trendline,
                peer_medians=peer_medians,
                validation_rules=validation_rules
            )
            
            # Execute AI call with fallback (use request-level keys if available)
            engine = ai_engine or self.ai_fallback
            ai_result = engine.execute_with_fallback(
                prompt=prompt,
                timeout=60,
                max_retries=2,
                operation_name=f"assumption_{metric}"
            )
            
            if ai_result["success"] and ai_result["response"]:
                # Parse AI response
                try:
                    import re
                    response_text = ai_result["response"]
                    logger.debug(f"Raw AI response for {metric}: {response_text[:500]}")
                    
                    # Strategy 1: Try parsing the entire response as JSON first
                    response_json = None
                    try:
                        response_json = json.loads(response_text.strip())
                    except (json.JSONDecodeError, ValueError):
                        pass
                    
                    # Strategy 2: Strip markdown code blocks and try again
                    if response_json is None:
                        cleaned = re.sub(r'```(?:json)?\s*', '', response_text).strip()
                        cleaned = re.sub(r'```\s*$', '', cleaned).strip()
                        try:
                            response_json = json.loads(cleaned)
                        except (json.JSONDecodeError, ValueError):
                            pass
                    
                    # Strategy 3: Find balanced JSON object using brace matching
                    if response_json is None:
                        start = response_text.find('{')
                        if start != -1:
                            depth = 0
                            for i in range(start, len(response_text)):
                                if response_text[i] == '{':
                                    depth += 1
                                elif response_text[i] == '}':
                                    depth -= 1
                                    if depth == 0:
                                        try:
                                            response_json = json.loads(response_text[start:i+1])
                                        except (json.JSONDecodeError, ValueError):
                                            pass
                                        break
                    
                    if response_json:
                        suggested_value = float(response_json.get("suggested_value", 0))
                        reasoning = response_json.get("reasoning", "AI-generated suggestion")
                        confidence = response_json.get("confidence", "medium")
                        
                        # Apply validation bounds
                        if validation_rules:
                            min_val = validation_rules.get("min", 0)
                            max_val = validation_rules.get("max", 1)
                            # For multiples, allow higher max
                            if "Multiple" in metric or "Multiplier" in metric or "Turnover" in metric:
                                max_val = validation_rules.get("max", 10)
                            suggested_value = max(min_val, min(suggested_value, max_val))
                        
                        logger.info(f"✅ Successfully parsed AI suggestion for {metric}: {suggested_value}")
                        return AISuggestion(
                            metric=metric,
                            suggested_value=suggested_value,
                            reasoning=reasoning,
                            confidence_level=confidence,
                            min_range=validation_rules.get("warning_min", suggested_value * 0.8),
                            max_range=validation_rules.get("warning_max", suggested_value * 1.2),
                            category=category
                        )
                    else:
                        logger.warning(f"Failed to extract JSON from AI response for {metric}. Response preview: {response_text[:200]}")
                except Exception as parse_error:
                    logger.warning(f"Failed to parse AI response for {metric}: {parse_error}")
                    # Fall through to deterministic fallback
            
            # Deterministic fallback if AI fails
            logger.info(f"Using deterministic fallback for {metric}")
            return self._generate_deterministic_fallback(
                metric=metric,
                category=category,
                historical_avg=historical_avg,
                trend_direction=trend_direction,
                volatility=volatility,
                peer_medians=peer_medians,
                validation_rules=validation_rules
            )
            
        except Exception as e:
            logger.error(f"Failed to generate AI suggestion for {metric}: {e}")
            historical_avg = trendline.average if trendline else None
            trend_direction = trendline.trend_direction if trendline else "stable"
            volatility = trendline.volatility if trendline else "low"
            return self._generate_deterministic_fallback(
                metric=metric,
                category=category,
                historical_avg=historical_avg,
                trend_direction=trend_direction,
                volatility=volatility,
                peer_medians=peer_medians,
                validation_rules=validation_rules
            )
    
    def _build_assumption_prompt(
        self,
        metric: str,
        category: AssumptionCategory,
        trendline: Optional[HistoricalTrendline],
        peer_medians: Dict[str, float],
        validation_rules: Dict[str, float]
    ) -> str:
        """Build AI prompt for assumption generation"""
        historical_avg = trendline.average if trendline else None
        trend_direction = trendline.trend_direction if trendline else "stable"
        
        # Get peer data if available
        peer_median = None
        if "Multiple" in metric or "EBITDA" in metric:
            peer_median = peer_medians.get("ev_ebitda")
        elif "P/E" in metric:
            peer_median = peer_medians.get("pe")
        elif "P/B" in metric:
            peer_median = peer_medians.get("pb")
        elif "P/S" in metric:
            peer_median = peer_medians.get("ps")
        
        return f"""SYSTEM:
You are a financial analyst assistant. Output ONLY raw JSON. No markdown. No explanation outside the JSON.

USER:
Generate a forward-looking assumption for: {metric}

## Context
- Metric: {metric}
- Category: {category.value}
- Historical Average: {historical_avg if historical_avg else 'N/A'}
- Trend Direction: {trend_direction}
{f"- Peer Median Multiple: {peer_median}" if peer_median else ""}

## Return exactly this JSON structure
{{
  "suggested_value": <number>,
  "reasoning": "<one sentence explaining the suggestion>",
  "confidence": "<low|medium|high>"
}}

## Guidelines
- Use historical data as baseline when available
- Consider trend direction (increasing/decreasing/stable)
- Apply conservative adjustments for forward-looking estimates
- For multiples, use peer median when available
- Ensure value is reasonable within typical ranges

Now return the JSON:""".strip()
    
    def _generate_deterministic_fallback(
        self,
        metric: str,
        category: AssumptionCategory,
        historical_avg: Optional[float],
        trend_direction: str,
        volatility: str,
        peer_medians: Dict[str, float],
        validation_rules: Dict[str, float]
    ) -> Optional[AISuggestion]:
        """Deterministic fallback when AI fails — uses peer_medians instead of raw step6/step7 data"""
        suggested_value = None
        reasoning = ""
        confidence = "medium"
        if metric in ("Revenue Volume Growth", "Revenue Growth"):
            if historical_avg is not None:
                # Adjust based on trend
                if trend_direction == "increasing":
                    suggested_value = historical_avg * 1.1
                    reasoning = f"Historical avg {historical_avg:.1%} with upward trend. Suggesting 10% increase."
                elif trend_direction == "decreasing":
                    suggested_value = historical_avg * 0.9
                    reasoning = f"Historical avg {historical_avg:.1%} with downward trend. Suggesting conservative 10% decrease."
                else:
                    suggested_value = historical_avg
                    reasoning = f"Stable historical performance at {historical_avg:.1%}. Maintaining average."
            else:
                suggested_value = 0.05
                reasoning = "No historical data. Using industry default of 5%."
                confidence = "low"
        
        elif metric == "Revenue Price Increase":
            if historical_avg is not None:
                suggested_value = max(0.02, min(historical_avg, 0.05))
                reasoning = f"Based on historical pricing power ({historical_avg:.1%}), suggesting moderate increases aligned with inflation."
            else:
                suggested_value = 0.02
                reasoning = "No historical data. Using inflation-based default of 2%."
                confidence = "low"
        
        elif metric == "COGS % of Revenue":
            if historical_avg is not None:
                # Assume efficiency improvements
                suggested_value = historical_avg * 0.98
                reasoning = f"Historical avg {historical_avg:.1%}. Assuming slight efficiency gains (2% reduction)."
            else:
                suggested_value = 0.60
                reasoning = "No historical data. Using industry default of 60%."
                confidence = "low"
        
        elif metric == "Effective Tax Rate":
            if historical_avg is not None:
                suggested_value = historical_avg
                reasoning = f"Using historical effective tax rate of {historical_avg:.1%}."
            else:
                suggested_value = 0.21
                reasoning = "No historical data. Using statutory rate of 21%."
                confidence = "low"
        
        elif metric == "Terminal Growth Rate":
            # Always capped at GDP growth
            suggested_value = 0.025
            reasoning = "Capped at long-term GDP growth expectation of 2.5%. Conservative terminal assumption."
        
        elif metric == "Terminal EBITDA Multiple":
            # Use peer median from peer_medians dict
            peer_median = peer_medians.get("ev_ebitda")
            
            if peer_median is not None:
                suggested_value = peer_median
                reasoning = f"Based on peer median EV/EBITDA multiple of {suggested_value:.1f}x."
            elif historical_avg is not None:
                suggested_value = historical_avg
                reasoning = f"Using historical average multiple of {historical_avg:.1f}x."
            else:
                suggested_value = 10.0
                reasoning = "No data available. Using industry default of 10x."
                confidence = "low"
        
        elif metric == "Risk-Free Rate":
            # Use current 10Y Treasury
            suggested_value = 0.045
            reasoning = "Current 10-year US Treasury yield (~4.5%)."
        
        elif metric == "Market Risk Premium":
            suggested_value = 0.055
            reasoning = "Historical market risk premium of 5.5%."
        
        elif metric == "Pre-Tax Cost of Debt":
            if historical_avg is not None:
                suggested_value = historical_avg
                reasoning = f"Using historical cost of debt {historical_avg:.1%}."
            else:
                suggested_value = 0.06
                reasoning = "No historical data. Using estimated cost of 6%."
                confidence = "low"
        
        # DuPont Model Metrics
        elif metric == "Target Net Profit Margin":
            if historical_avg is not None:
                # Suggest slight improvement based on trend
                if trend_direction == "increasing":
                    suggested_value = historical_avg * 1.05
                    reasoning = f"Historical avg {historical_avg:.1%} with upward trend. Suggesting 5% improvement."
                elif trend_direction == "decreasing":
                    suggested_value = historical_avg * 0.95
                    reasoning = f"Historical avg {historical_avg:.1%} with downward trend. Conservative 5% reduction target."
                else:
                    suggested_value = historical_avg
                    reasoning = f"Stable historical performance at {historical_avg:.1%}. Maintaining average."
            else:
                suggested_value = 0.10
                reasoning = "No historical data. Using industry default net margin of 10%."
                confidence = "low"
        
        elif metric == "Target Asset Turnover":
            if historical_avg is not None:
                suggested_value = historical_avg
                reasoning = f"Using historical asset turnover of {historical_avg:.2f}x. Maintain efficiency."
            else:
                suggested_value = 1.0
                reasoning = "No historical data. Using industry default asset turnover of 1.0x."
                confidence = "low"
        
        elif metric == "Target Equity Multiplier":
            if historical_avg is not None:
                # Suggest maintaining or slightly reducing leverage
                suggested_value = min(historical_avg, historical_avg * 1.05)
                reasoning = f"Historical equity multiplier of {historical_avg:.2f}x. Suggesting stable to slightly reduced leverage."
            else:
                suggested_value = 2.0
                reasoning = "No historical data. Using industry default equity multiplier of 2.0x."
                confidence = "low"
        
        # Comps Model Metrics
        elif metric == "P/E Multiple":
            # Use peer median from peer_medians dict
            peer_median = peer_medians.get("pe")
            
            if peer_median is not None:
                suggested_value = peer_median
                reasoning = f"Based on peer median P/E of {suggested_value:.1f}x."
            elif historical_avg is not None:
                suggested_value = historical_avg
                reasoning = f"Using historical P/E of {historical_avg:.1f}x."
            else:
                suggested_value = 15.0
                reasoning = "No data available. Using industry default P/E of 15x."
                confidence = "low"
        
        elif metric == "EV/EBITDA Multiple":
            # Use peer median from peer_medians dict
            peer_median = peer_medians.get("ev_ebitda")
            
            if peer_median is not None:
                suggested_value = peer_median
                reasoning = f"Based on peer median EV/EBITDA of {suggested_value:.1f}x."
            elif historical_avg is not None:
                suggested_value = historical_avg
                reasoning = f"Using historical EV/EBITDA of {historical_avg:.1f}x."
            else:
                suggested_value = 10.0
                reasoning = "No data available. Using industry default EV/EBITDA of 10x."
                confidence = "low"
        
        elif metric == "P/B Multiple":
            # Use peer median from peer_medians dict
            peer_median = peer_medians.get("pb")
            
            if peer_median is not None:
                suggested_value = peer_median
                reasoning = f"Based on peer median P/B of {suggested_value:.1f}x."
            elif historical_avg is not None:
                suggested_value = historical_avg
                reasoning = f"Using historical P/B of {historical_avg:.1f}x."
            else:
                suggested_value = 2.0
                reasoning = "No data available. Using industry default P/B of 2x."
                confidence = "low"
        
        elif metric == "P/S Multiple":
            # Use peer median from peer_medians dict
            peer_median = peer_medians.get("ps")
            
            if peer_median is not None:
                suggested_value = peer_median
                reasoning = f"Based on peer median P/S of {suggested_value:.1f}x."
            elif historical_avg is not None:
                suggested_value = historical_avg
                reasoning = f"Using historical P/S of {historical_avg:.1f}x."
            else:
                suggested_value = 3.0
                reasoning = "No data available. Using industry default P/S of 3x."
                confidence = "low"
        
        elif metric == "Outlier Filter Std Dev" or metric == "Outlier Filter Threshold":
            # Default to 2 standard deviations for outlier removal
            suggested_value = 2.0
            reasoning = "Standard practice: exclude peers beyond 2 standard deviations from median."
        
        # Apply validation bounds
        if suggested_value is not None and validation_rules:
            min_val = validation_rules.get("min", float('-inf'))
            max_val = validation_rules.get("max", float('inf'))
            suggested_value = max(min_val, min(suggested_value, max_val))
        
        if suggested_value is None:
            return None
        
        return AISuggestion(
            metric=metric,
            suggested_value=suggested_value,
            reasoning=reasoning,
            confidence_level=confidence,
            min_range=validation_rules.get("warning_min", suggested_value * 0.8),
            max_range=validation_rules.get("warning_max", suggested_value * 1.2),
            category=category
        )
    
    # =========================================================================
    # VALIDATION
    # =========================================================================
    
    def _get_validation_rules(
        self,
        model: str,
        category: AssumptionCategory,
        metric: str
    ) -> Optional[Dict[str, float]]:
        """Get validation rules for a specific metric"""
        if model == "DCF":
            config = self.DCF_CATEGORIES.get(category)
        elif model == "DUPONT":
            config = self.DUPONT_CATEGORIES.get(category)
        elif model == "COMPS":
            config = self.COMPS_CATEGORIES.get(category)
        else:
            return None
        
        if not config:
            return None
        
        for assumption_def in config["assumptions"]:
            if assumption_def["metric"] == metric:
                return assumption_def.get("validation", {})
        
        return None
