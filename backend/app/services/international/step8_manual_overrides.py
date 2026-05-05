"""Step 8: Manual Overrides Layer - The Assumption Studio

This is the critical "Brain" of the workflow, bridging historical reality with future valuation.

Features:
1. Context-Aware Historical Trendlines (3-5 years from Step 6)
2. Modular AI Suggestion Engines (5 Button Strategy)
3. Smart Validation & Guardrails
4. What-If Preview (Mini-Step 9 sensitivity)
"""
import logging
from typing import Dict, List, Optional, Any, Tuple
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime
import json

logger = logging.getLogger(__name__)

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
    1. Context-Aware Historical Trendlines (3-5 years from Step 6)
    2. Modular AI Suggestion Engines (5 Button Strategy)
    3. Smart Validation & Guardrails
    4. What-If Preview (Mini-Step 9 sensitivity)
    
    Output: FullAssumptionsResponse with complete assumption set
    """
    
    # Forecast period configuration
    FORECAST_YEARS = [1, 2, 3, 4, 5]
    
    # DCF Assumption Categories Definition
    DCF_CATEGORIES = {
        AssumptionCategory.REVENUE_DRIVERS: {
            "name": "Revenue Drivers",
            "assumptions": [
                {
                    "metric": "Revenue Volume Growth",
                    "description": "Annual growth rate from volume increases",
                    "unit": "%",
                    "is_multi_year": True,
                    "validation": {"min": -0.20, "max": 0.50, "warning_min": 0.0, "warning_max": 0.30}
                },
                {
                    "metric": "Revenue Price Increase",
                    "description": "Annual growth rate from price increases",
                    "unit": "%",
                    "is_multi_year": True,
                    "validation": {"min": -0.10, "max": 0.30, "warning_min": 0.0, "warning_max": 0.15}
                }
            ]
        },
        AssumptionCategory.COST_MARGINS: {
            "name": "Cost & Margins",
            "assumptions": [
                {
                    "metric": "COGS % of Revenue",
                    "description": "Cost of goods sold as percentage of revenue",
                    "unit": "%",
                    "is_multi_year": False,
                    "validation": {"min": 0.10, "max": 0.90, "warning_min": 0.30, "warning_max": 0.70}
                },
                {
                    "metric": "SG&A % of Revenue",
                    "description": "Selling, general & administrative expenses as percentage of revenue",
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
        pass
    
    async def initialize_assumptions(
        self,
        ticker: str,
        valuation_model: str,
        step6_data: Dict[str, Any],
        step7_data: Optional[Dict[str, Any]] = None
    ) -> FullAssumptionsResponse:
        """
        Initialize Step 8 with historical trendlines from Step 6.
        No AI suggestions yet - user must click buttons to generate them.
        """
        model_enum = ValuationModel(valuation_model.upper())
        categories = {}
        
        if model_enum == ValuationModel.DCF:
            categories = await self._initialize_dcf_categories(ticker, step6_data, step7_data)
        elif model_enum == ValuationModel.DUPONT:
            categories = await self._initialize_dupont_categories(ticker, step6_data, step7_data)
        elif model_enum == ValuationModel.COMPS:
            categories = await self._initialize_comps_categories(ticker, step6_data, step7_data)
        
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
    
    async def _initialize_dcf_categories(
        self,
        ticker: str,
        step6_data: Dict[str, Any],
        step7_data: Optional[Dict[str, Any]] = None
    ) -> Dict[AssumptionCategory, AssumptionCategoryResponse]:
        """Initialize DCF assumption categories with historical trendlines"""
        categories = {}
        
        for category, config in self.DCF_CATEGORIES.items():
            assumptions = []
            for assumption_def in config["assumptions"]:
                # Build historical trendline from Step 6 data
                trendline = await self._build_historical_trendline(
                    metric=assumption_def["metric"],
                    step6_data=step6_data,
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
        step6_data: Dict[str, Any],
        step7_data: Optional[Dict[str, Any]] = None
    ) -> Dict[AssumptionCategory, AssumptionCategoryResponse]:
        """Initialize DuPont assumption categories with historical trendlines"""
        categories = {}
        
        for category, config in self.DUPONT_CATEGORIES.items():
            assumptions = []
            for assumption_def in config["assumptions"]:
                trendline = await self._build_historical_trendline(
                    metric=assumption_def["metric"],
                    step6_data=step6_data,
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
        step6_data: Dict[str, Any],
        step7_data: Optional[Dict[str, Any]] = None
    ) -> Dict[AssumptionCategory, AssumptionCategoryResponse]:
        """Initialize Comps assumption categories with historical trendlines"""
        categories = {}
        
        for category, config in self.COMPS_CATEGORIES.items():
            assumptions = []
            for assumption_def in config["assumptions"]:
                trendline = await self._build_historical_trendline(
                    metric=assumption_def["metric"],
                    step6_data=step6_data,
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
    
    async def _build_historical_trendline(
        self,
        metric: str,
        step6_data: Dict[str, Any],
        is_multi_year: bool = False
    ) -> Optional[HistoricalTrendline]:
        """Build historical trendline from Step 6 data for a given metric"""
        try:
            trend_points = []
            values = []
            
            # Extract historical financials from Step 6
            hist_financials = step6_data.get('historical_financials', {})
            years = hist_financials.get('years', [])
            
            if not years:
                return None
            
            # Map metric to historical data field
            field_mapping = {
                "Revenue Volume Growth": "revenue_growth",
                "Revenue Price Increase": "revenue_growth",  # Approximation
                "COGS % of Revenue": "cogs_percent",
                "SG&A % of Revenue": "sga_percent",
                "Effective Tax Rate": "effective_tax_rate",
                "Accounts Receivable Days": "ar_days",
                "Inventory Days": "inventory_days",
                "Accounts Payable Days": "ap_days",
                "Risk-Free Rate": None,  # External data
                "Market Risk Premium": None,  # External data
                "Country Risk Premium": None,  # External data
                "Pre-Tax Cost of Debt": "cost_of_debt",
                "Target Debt-to-Equity": "debt_to_equity",
                "Terminal Growth Rate": None,  # Forward-looking
                "Terminal EBITDA Multiple": "ev_ebitda_multiple",
                "Target Net Profit Margin": "net_margin",
                "Target Asset Turnover": "asset_turnover",
                "Target Equity Multiplier": "equity_multiplier",
                "P/E Multiple": "pe_multiple",
                "EV/EBITDA Multiple": "ev_ebitda_multiple",
                "P/B Multiple": "pb_multiple",
                "P/S Multiple": "ps_multiple"
            }
            
            field = field_mapping.get(metric)
            if not field:
                return None
            
            # Get historical values
            for i, year in enumerate(years[-5:]):  # Last 5 years max
                value = hist_financials.get(field, {}).get(year)
                if value is not None:
                    trend_points.append(HistoricalTrendPoint(year=year, value=float(value)))
                    values.append(float(value))
            
            if not values:
                return None
            
            # Calculate statistics
            avg_value = sum(values) / len(values)
            
            # Determine trend direction
            if len(values) >= 2:
                if values[-1] > values[0] * 1.1:
                    trend_direction = "increasing"
                elif values[-1] < values[0] * 0.9:
                    trend_direction = "decreasing"
                else:
                    trend_direction = "stable"
            else:
                trend_direction = "stable"
            
            # Calculate volatility
            if len(values) >= 2:
                variance = sum((x - avg_value) ** 2 for x in values) / len(values)
                std_dev = variance ** 0.5
                cv = std_dev / abs(avg_value) if avg_value != 0 else 0
                if cv > 0.3:
                    volatility = "high"
                elif cv > 0.15:
                    volatility = "medium"
                else:
                    volatility = "low"
            else:
                volatility = "low"
            
            # Calculate CAGR for growth metrics
            cagr = None
            if len(values) >= 2 and "Growth" in metric:
                n = len(values) - 1
                if values[0] != 0:
                    cagr = ((values[-1] / values[0]) ** (1/n)) - 1
            
            return HistoricalTrendline(
                metric=metric,
                trend_points=trend_points,
                average=avg_value,
                cagr=cagr,
                trend_direction=trend_direction,
                volatility=volatility
            )
        except Exception as e:
            logger.warning(f"Failed to build trendline for {metric}: {e}")
            return None
    
    async def generate_ai_suggestions_for_category(
        self,
        ticker: str,
        valuation_model: str,
        category: str,
        step6_data: Dict[str, Any],
        step7_data: Optional[Dict[str, Any]] = None
    ) -> AssumptionCategoryResponse:
        """
        Generate AI suggestions for a specific category (button click handler).
        This is called when user clicks one of the 5 AI suggestion buttons.
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
        
        # Generate AI suggestions for each assumption in category
        assumptions = []
        for assumption_def in config["assumptions"]:
            metric = assumption_def["metric"]
            
            # Get historical trendline
            trendline = await self._build_historical_trendline(
                metric=metric,
                step6_data=step6_data,
                is_multi_year=assumption_def.get("is_multi_year", False)
            )
            
            # Generate AI suggestion based on historical data and market context
            ai_suggestion = await self._generate_single_ai_suggestion(
                metric=metric,
                category=category_enum,
                trendline=trendline,
                step6_data=step6_data,
                step7_data=step7_data,
                validation_rules=assumption_def.get("validation", {})
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
    
    async def _generate_single_ai_suggestion(
        self,
        metric: str,
        category: AssumptionCategory,
        trendline: Optional[HistoricalTrendline],
        step6_data: Dict[str, Any],
        step7_data: Optional[Dict[str, Any]],
        validation_rules: Dict[str, float]
    ) -> Optional[AISuggestion]:
        """Generate AI suggestion for a single metric"""
        try:
            # Get historical average as baseline
            historical_avg = trendline.average if trendline else None
            trend_direction = trendline.trend_direction if trendline else "stable"
            volatility = trendline.volatility if trendline else "low"
            
            # Generate suggestion based on metric type
            suggested_value = None
            reasoning = ""
            confidence = "medium"
            
            if metric == "Revenue Volume Growth":
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
                # Use peer median from Step 7
                if step7_data and 'peer_median_ev_ebitda' in step7_data:
                    suggested_value = step7_data['peer_median_ev_ebitda']
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
            
            # Apply validation bounds
            if suggested_value is not None and validation_rules:
                min_val = validation_rules.get("min", 0)
                max_val = validation_rules.get("max", 1)
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
        except Exception as e:
            logger.error(f"Failed to generate AI suggestion for {metric}: {e}")
            return None
    
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
