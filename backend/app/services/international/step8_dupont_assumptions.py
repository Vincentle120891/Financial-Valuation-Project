"""Step 8: DuPont Assumption & AI Suggestion Studio

This is the critical "Brain" of the DuPont workflow, bridging historical reality with future valuation.

Purpose: DuPont-specific assumption generation and AI suggestions
- DuPont ROE Targets (Net Profit Margin, Asset Turnover, Equity Multiplier)

AI Usage in Step 8 DuPont:
- AI provides minimal suggestions (mostly calculated from historical data)
- Users can accept AI suggestions or manually override them
- All AI suggestions include rationale and confidence scores
- Focus on ROE decomposition inputs

Features:
1. Context-Aware Historical Trendlines (3-5 years from Step 6 + Step 7 gap-filled data)
2. Modular AI Suggestion Engines (Category-by-category generation)
3. Smart Validation & Guardrails
4. What-If Preview (Mini-Step 9 sensitivity)
"""
import logging
from typing import Dict, List, Optional, Any, Tuple
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime
import json
from .ai_engine import AIFallbackEngine
from .statistical_utils import (
    generate_historical_statistics,
    extract_numeric_values,
    calculate_average,
    calculate_median,
    calculate_cagr,
    calculate_volatility,
    calculate_year_over_year_growth
)

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
    """Categories for DuPont assumptions"""
    DUPONT_TARGETS = "DUPONT_TARGETS"

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

class DuPontAssumptionsResponse(BaseModel):
    """Complete Step 8 DuPont response with all categories"""
    session_id: str
    ticker: str
    timestamp: datetime
    valuation_model: ValuationModel = ValuationModel.DUPONT
    categories: Dict[str, AssumptionCategoryResponse]
    
    # Summary and validation
    all_categories_complete: bool = False
    all_validations_passed: bool = True
    total_validation_errors: List[str] = []
    ready_for_calculation: bool = False
    
    # What-if preview
    sensitivity_preview: Optional[Dict[str, Any]] = None
    message: str = ""


class DuPontStep8Processor:
    """
    Step 8: The DuPont Assumption Studio
    
    Features:
    1. Context-Aware Historical Trendlines (3-5 years from Step 6)
    2. Modular AI Suggestion Engines (Minimal AI - mostly calculated)
    3. Smart Validation & Guardrails
    4. What-If Preview (Mini-Step 9 sensitivity)
    
    Output: DuPontAssumptionsResponse with complete DuPont assumption set
    """
    
    # Forecast period configuration
    FORECAST_YEARS = [1, 2, 3, 4, 5]
    
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
    
    def __init__(self):
        self.ai_fallback = AIFallbackEngine()
    
    async def initialize_assumptions(
        self,
        ticker: str,
        step6_data: Dict[str, Any],
        step7_data: Optional[Dict[str, Any]] = None
    ) -> DuPontAssumptionsResponse:
        """
        Initialize Step 8 DuPont with historical trendlines from Step 6.
        No AI suggestions yet - user must click buttons to generate them.
        """
        categories = await self._initialize_dupont_categories(ticker, step6_data, step7_data)
        
        return DuPontAssumptionsResponse(
            session_id=f"step8_dupont_{ticker}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            ticker=ticker,
            timestamp=datetime.now(),
            valuation_model=ValuationModel.DUPONT,
            categories={k.value: v for k, v in categories.items()},
            all_categories_complete=False,
            all_validations_passed=True,
            ready_for_calculation=False,
            message="DuPont assumptions initialized with historical trendlines. Click AI suggestion buttons to generate recommendations."
        )
    
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
                # Build historical trendline from Step 6 data
                historical_trendline = await self._build_historical_trendline(
                    assumption_def["metric"],
                    step6_data,
                    step7_data
                )
                
                assumption = AssumptionInput(
                    metric=assumption_def["metric"],
                    category=category,
                    description=assumption_def["description"],
                    unit=assumption_def["unit"],
                    historical_trendline=historical_trendline,
                    is_multi_year=assumption_def["is_multi_year"],
                    is_valid=True
                )
                assumptions.append(assumption)
            
            categories[category] = AssumptionCategoryResponse(
                category=category,
                category_name=config["name"],
                assumptions=assumptions,
                ai_generated=False,
                message=f"Historical trendlines loaded. Click 'Generate AI Suggestions' to get recommendations for {config['name']}."
            )
        
        return categories
    
    async def _build_historical_trendline(
        self,
        metric: str,
        step6_data: Dict[str, Any],
        step7_data: Optional[Dict[str, Any]] = None
    ) -> Optional[HistoricalTrendline]:
        """Build historical trendline from Step 6 (and Step 7 if available) data"""
        try:
            # Extract historical data from Step 6
            historical_data = step6_data.get("dupont_historical_metrics", {})
            
            # Map metric names to data keys
            metric_mapping = {
                "Target Net Profit Margin": "net_profit_margin",
                "Target Asset Turnover": "asset_turnover",
                "Target Equity Multiplier": "equity_multiplier"
            }
            
            data_key = metric_mapping.get(metric, metric.lower().replace(" ", "_").replace("%", "").replace("/", "_"))
            
            # Get historical values
            values = historical_data.get(data_key, {})
            if not values:
                # Try alternative key formats
                for alt_key in [data_key.lower(), data_key.upper(), data_key.replace("_", "")]:
                    values = historical_data.get(alt_key, {})
                    if values:
                        break
            
            if not values:
                return None
            
            # Convert to DataField format for statistical_utils
            from app.api.schemas.unified_step_schemas import DataField
            data_fields = []
            for year, value in sorted(values.items()):
                if isinstance(year, str) and year.isdigit():
                    year = int(year)
                if isinstance(value, (int, float)) and value is not None:
                    data_fields.append(DataField(field_name=data_key, value=float(value), year=int(year)))
            
            if not data_fields:
                return None
            
            # Use statistical_utils to generate comprehensive statistics
            stats = generate_historical_statistics(data_fields, metric)
            
            if stats.get("status") == "insufficient_data":
                # Still build basic trendline with limited data
                trend_points = [HistoricalTrendPoint(year=y, value=v) for y, v in zip(stats.get("raw_years", []), stats.get("raw_values", []))]
                return HistoricalTrendline(
                    metric=metric,
                    trend_points=trend_points,
                    average=stats.get("average", 0.0) or 0.0,
                    cagr=None,
                    trend_direction="stable",
                    volatility="low"
                )
            
            # Build trend points from raw data
            trend_points = [HistoricalTrendPoint(year=y, value=v) for y, v in zip(stats["raw_years"], stats["raw_values"])]
            
            # Determine trend direction
            trend_direction = "stable"
            if stats["oldest_value"] and stats["latest_value"]:
                if stats["latest_value"] > stats["oldest_value"] * 1.1:
                    trend_direction = "increasing"
                elif stats["latest_value"] < stats["oldest_value"] * 0.9:
                    trend_direction = "decreasing"
            
            # Convert volatility (std_dev) to low/medium/high
            volatility = "low"
            if stats.get("volatility"):
                avg_val = stats.get("average", 0)
                if avg_val != 0:
                    cv = stats["volatility"] / abs(avg_val)
                    if cv > 0.3:
                        volatility = "high"
                    elif cv > 0.15:
                        volatility = "medium"
            
            return HistoricalTrendline(
                metric=metric,
                trend_points=trend_points,
                average=stats["average"],
                cagr=stats.get("cagr"),
                trend_direction=trend_direction,
                volatility=volatility,
                # Enhanced statistics from statistical_utils
                median=stats.get("median"),
                min_value=stats.get("min"),
                max_value=stats.get("max"),
                standard_deviation=stats.get("volatility"),
                average_yoy_growth=stats.get("average_yoy_growth"),
                yoy_growth_details=stats.get("yoy_growth_details"),
                year_range=stats.get("year_range"),
                periods=stats.get("periods"),
                latest_value=stats.get("latest_value"),
                oldest_value=stats.get("oldest_value")
            )
        except Exception as e:
            logger.error(f"Error building historical trendline for {metric}: {e}")
            return None
    
    async def generate_ai_suggestions_for_category(
        self,
        ticker: str,
        category: AssumptionCategory,
        step6_data: Dict[str, Any],
        step7_data: Optional[Dict[str, Any]] = None,
        current_assumptions: Optional[List[AssumptionInput]] = None
    ) -> AssumptionCategoryResponse:
        """Generate AI suggestions for a specific DuPont assumption category"""
        if category not in self.DUPONT_CATEGORIES:
            raise ValueError(f"Invalid DuPont category: {category}")
        
        config = self.DUPONT_CATEGORIES[category]
        assumptions = []
        
        for assumption_def in config["assumptions"]:
            # Generate AI suggestion
            ai_suggestion = await self._generate_single_ai_suggestion(
                ticker=ticker,
                metric=assumption_def["metric"],
                category=category,
                description=assumption_def["description"],
                validation_rules=assumption_def["validation"],
                step6_data=step6_data,
                step7_data=step7_data
            )
            
            assumption = AssumptionInput(
                metric=assumption_def["metric"],
                category=category,
                description=assumption_def["description"],
                unit=assumption_def["unit"],
                historical_trendline=await self._build_historical_trendline(
                    assumption_def["metric"], step6_data, step7_data
                ),
                ai_suggestion=ai_suggestion,
                is_multi_year=assumption_def["is_multi_year"],
                is_valid=True
            )
            assumptions.append(assumption)
        
        return AssumptionCategoryResponse(
            category=category,
            category_name=config["name"],
            assumptions=assumptions,
            ai_generated=True,
            generation_timestamp=datetime.now(),
            message=f"AI suggestions generated for {config['name']} based on historical trends and ROE decomposition analysis."
        )
    
    async def _generate_single_ai_suggestion(
        self,
        ticker: str,
        metric: str,
        category: AssumptionCategory,
        description: str,
        validation_rules: Dict[str, float],
        step6_data: Dict[str, Any],
        step7_data: Optional[Dict[str, Any]] = None
    ) -> AISuggestion:
        """Generate AI suggestion for a single DuPont assumption"""
        try:
            # Build prompt for AI engine
            prompt = self._build_dupont_assumption_prompt(
                ticker=ticker,
                metric=metric,
                category=category,
                description=description,
                validation_rules=validation_rules,
                step6_data=step6_data,
                step7_data=step7_data
            )
            
            # Call AI engine
            ai_response = await self.ai_fallback.generate_suggestion(prompt)
            
            # Parse AI response
            suggested_value = float(ai_response.get("value", 0.0))
            reasoning = ai_response.get("reasoning", "AI-based recommendation")
            confidence = ai_response.get("confidence", "medium")
            
            # Apply validation constraints
            min_val = validation_rules.get("min", float("-inf"))
            max_val = validation_rules.get("max", float("inf"))
            suggested_value = max(min_val, min(max_val, suggested_value))
            
            return AISuggestion(
                metric=metric,
                suggested_value=suggested_value,
                reasoning=reasoning,
                confidence_level=confidence,
                min_range=min_val,
                max_range=max_val,
                category=category
            )
        except Exception as e:
            logger.error(f"Error generating AI suggestion for {metric}: {e}")
            # Fallback to deterministic calculation
            fallback_value = self._generate_deterministic_dupont_fallback(
                metric=metric,
                category=category,
                validation_rules=validation_rules,
                step6_data=step6_data
            )
            return AISuggestion(
                metric=metric,
                suggested_value=fallback_value,
                reasoning=f"Calculated from historical averages (AI unavailable)",
                confidence_level="low",
                min_range=validation_rules.get("min", 0.0),
                max_range=validation_rules.get("max", 1.0),
                category=category
            )
    
    def _build_dupont_assumption_prompt(
        self,
        ticker: str,
        metric: str,
        category: AssumptionCategory,
        description: str,
        validation_rules: Dict[str, float],
        step6_data: Dict[str, Any],
        step7_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build prompt for DuPont assumption AI generation"""
        historical_trendline = None
        if step6_data:
            historical_trendline = self._build_historical_trendline_sync(metric, step6_data, step7_data)
        
        prompt = f"""Generate a forward-looking assumption for DuPont ROE analysis:

Company: {ticker}
Metric: {metric}
Category: {category.value}
Description: {description}

Validation Constraints:
- Min: {validation_rules.get('min', 'N/A')}
- Max: {validation_rules.get('max', 'N/A')}
- Warning Range: {validation_rules.get('warning_min', 'N/A')} to {validation_rules.get('warning_max', 'N/A')}

"""
        
        if historical_trendline:
            prompt += f"""Historical Context:
- Average: {historical_trendline.average:.2%}
- CAGR: {historical_trendline.cagr:.2%} if historical_trendline.cagr else 'N/A'
- Trend: {historical_trendline.trend_direction}
- Volatility: {historical_trendline.volatility}

Historical Values:
"""
            for point in historical_trendline.trend_points[-5:]:
                prompt += f"  - {point.year}: {point.value:.2%}\n"
        
        prompt += """
Provide a reasoned suggestion for this ROE decomposition component considering:
1. Historical trends and momentum
2. Industry benchmarks and peer comparisons
3. Company strategic objectives
4. ROE target alignment

Return JSON with: value (decimal), reasoning (string), confidence (low/medium/high)"""
        
        return prompt
    
    def _build_historical_trendline_sync(
        self,
        metric: str,
        step6_data: Dict[str, Any],
        step7_data: Optional[Dict[str, Any]] = None
    ) -> Optional[HistoricalTrendline]:
        """Synchronous version of _build_historical_trendline for prompt building"""
        try:
            historical_data = step6_data.get("dupont_historical_metrics", {})
            metric_mapping = {
                "Target Net Profit Margin": "net_profit_margin",
                "Target Asset Turnover": "asset_turnover",
                "Target Equity Multiplier": "equity_multiplier"
            }
            data_key = metric_mapping.get(metric, metric.lower().replace(" ", "_").replace("%", "").replace("/", "_"))
            values = historical_data.get(data_key, {})
            
            if not values:
                return None
            
            # Convert to DataField format for statistical_utils
            from app.api.schemas.unified_step_schemas import DataField
            data_fields = []
            for year, value in sorted(values.items()):
                if isinstance(year, str) and year.isdigit():
                    year = int(year)
                if isinstance(value, (int, float)) and value is not None:
                    data_fields.append(DataField(field_name=data_key, value=float(value), year=int(year)))
            
            if not data_fields:
                return None
            
            # Use statistical_utils to generate comprehensive statistics
            stats = generate_historical_statistics(data_fields, metric)
            
            if stats.get("status") == "insufficient_data":
                trend_points = [HistoricalTrendPoint(year=y, value=v) for y, v in zip(stats.get("raw_years", []), stats.get("raw_values", []))]
                return HistoricalTrendline(
                    metric=metric,
                    trend_points=trend_points,
                    average=stats.get("average", 0.0) or 0.0,
                    cagr=None,
                    trend_direction="stable",
                    volatility="low"
                )
            
            trend_points = [HistoricalTrendPoint(year=y, value=v) for y, v in zip(stats["raw_years"], stats["raw_values"])]
            
            trend_direction = "stable"
            if stats["oldest_value"] and stats["latest_value"]:
                if stats["latest_value"] > stats["oldest_value"] * 1.1:
                    trend_direction = "increasing"
                elif stats["latest_value"] < stats["oldest_value"] * 0.9:
                    trend_direction = "decreasing"
            
            volatility = "low"
            if stats.get("volatility"):
                avg_val = stats.get("average", 0)
                if avg_val != 0:
                    cv = stats["volatility"] / abs(avg_val)
                    if cv > 0.3:
                        volatility = "high"
                    elif cv > 0.15:
                        volatility = "medium"
            
            return HistoricalTrendline(
                metric=metric,
                trend_points=trend_points,
                average=stats["average"],
                cagr=stats.get("cagr"),
                trend_direction=trend_direction,
                volatility=volatility,
                median=stats.get("median"),
                min_value=stats.get("min"),
                max_value=stats.get("max"),
                standard_deviation=stats.get("volatility"),
                average_yoy_growth=stats.get("average_yoy_growth"),
                yoy_growth_details=stats.get("yoy_growth_details"),
                year_range=stats.get("year_range"),
                periods=stats.get("periods"),
                latest_value=stats.get("latest_value"),
                oldest_value=stats.get("oldest_value")
            )
        except Exception:
            return None
    
    def _generate_deterministic_dupont_fallback(
        self,
        metric: str,
        category: AssumptionCategory,
        validation_rules: Dict[str, float],
        step6_data: Dict[str, Any]
    ) -> float:
        """Generate deterministic fallback value for DuPont assumption"""
        try:
            historical_data = step6_data.get("dupont_historical_metrics", {})
            
            # Use historical average for DuPont components
            key = metric.lower().replace(" ", "_").replace("target_", "").replace("%", "").replace("/", "_")
            if key in historical_data:
                values = list(historical_data[key].values())
                if values:
                    avg = sum(v for v in values if isinstance(v, (int, float))) / len(values)
                    return max(validation_rules.get("min", 0), min(validation_rules.get("max", 1), avg))
            
            # Default to middle of validation range
            min_val = validation_rules.get("min", 0.0)
            max_val = validation_rules.get("max", 1.0)
            return (min_val + max_val) / 2
            
        except Exception:
            # Ultimate fallback: middle of range
            min_val = validation_rules.get("min", 0.0)
            max_val = validation_rules.get("max", 1.0)
            return (min_val + max_val) / 2
    
    async def apply_user_override(
        self,
        category: AssumptionCategory,
        metric: str,
        user_value: float,
        existing_assumption: AssumptionInput
    ) -> AssumptionInput:
        """Apply user manual override to an assumption"""
        # Validate user input
        validation_rules = None
        for cat_config in self.DUPONT_CATEGORIES.values():
            for assumption_def in cat_config["assumptions"]:
                if assumption_def["metric"] == metric:
                    validation_rules = assumption_def["validation"]
                    break
        
        is_valid = True
        validation_message = None
        warning_message = None
        
        if validation_rules:
            if user_value < validation_rules.get("min", float("-inf")) or user_value > validation_rules.get("max", float("inf")):
                is_valid = False
                validation_message = f"Value {user_value} is outside valid range [{validation_rules.get('min')}, {validation_rules.get('max')}]"
            elif user_value < validation_rules.get("warning_min", float("-inf")) or user_value > validation_rules.get("warning_max", float("inf")):
                warning_message = f"Value {user_value} is outside recommended range [{validation_rules.get('warning_min')}, {validation_rules.get('warning_max')}]\""
        
        # Update assumption
        updated = AssumptionInput(
            metric=existing_assumption.metric,
            category=existing_assumption.category,
            description=existing_assumption.description,
            unit=existing_assumption.unit,
            historical_trendline=existing_assumption.historical_trendline,
            ai_suggestion=existing_assumption.ai_suggestion,
            user_value=user_value,
            final_value=user_value,
            status=OverrideStatus.MANUAL_OVERRIDE,
            is_valid=is_valid,
            validation_message=validation_message,
            warning_message=warning_message,
            is_multi_year=existing_assumption.is_multi_year,
            year_values=existing_assumption.year_values
        )
        
        return updated
    
    async def validate_all_assumptions(
        self,
        categories: Dict[str, AssumptionCategoryResponse]
    ) -> Tuple[bool, List[str]]:
        """Validate all DuPont assumptions"""
        all_valid = True
        errors = []
        
        for category_response in categories.values():
            for assumption in category_response.assumptions:
                if not assumption.is_valid:
                    all_valid = False
                    if assumption.validation_message:
                        errors.append(f"{assumption.metric}: {assumption.validation_message}")
                elif assumption.final_value is None and assumption.ai_suggestion is None:
                    all_valid = False
                    errors.append(f"{assumption.metric}: No value provided")
        
        return all_valid, errors
    
    def _get_validation_rules(self, metric: str) -> Optional[Dict[str, float]]:
        """Get validation rules for a specific metric"""
        for config in self.DUPONT_CATEGORIES.values():
            for assumption_def in config["assumptions"]:
                if assumption_def["metric"] == metric:
                    return assumption_def["validation"]
        return None
