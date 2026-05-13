"""Step 8: Comps Assumption & AI Suggestion Studio

This is the critical "Brain" of the Comps workflow, bridging historical reality with future valuation.

Purpose: Comps-specific assumption generation and AI suggestions
- Comps Multiples & Filters (P/E, EV/EBITDA, P/B, P/S, Outlier Filter Threshold)

AI Usage in Step 8 Comps:
- AI provides minimal suggestions (mostly calculated from peer data)
- Users can accept AI suggestions or manually override them
- All AI suggestions include rationale and confidence scores
- Focus on trading multiples and peer comparison filters

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
    """Categories for Comps assumptions"""
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

class CompsAssumptionsResponse(BaseModel):
    """Complete Step 8 Comps response with all categories"""
    session_id: str
    ticker: str
    timestamp: datetime
    valuation_model: ValuationModel = ValuationModel.COMPS
    categories: Dict[str, AssumptionCategoryResponse]
    
    # Summary and validation
    all_categories_complete: bool = False
    all_validations_passed: bool = True
    total_validation_errors: List[str] = []
    ready_for_calculation: bool = False
    
    # What-if preview
    sensitivity_preview: Optional[Dict[str, Any]] = None
    message: str = ""


class CompsStep8Processor:
    """
    Step 8: The Comps Assumption Studio
    
    Features:
    1. Context-Aware Historical Trendlines (3-5 years from Step 6)
    2. Modular AI Suggestion Engines (Minimal AI - mostly calculated from peers)
    3. Smart Validation & Guardrails
    4. What-If Preview (Mini-Step 9 sensitivity)
    
    Output: CompsAssumptionsResponse with complete Comps assumption set
    """
    
    # Forecast period configuration
    FORECAST_YEARS = [1, 2, 3, 4, 5]
    
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
    
    async def initialize_assumptions(
        self,
        ticker: str,
        step6_data: Dict[str, Any],
        step7_data: Optional[Dict[str, Any]] = None
    ) -> CompsAssumptionsResponse:
        """
        Initialize Step 8 Comps with historical trendlines from Step 6.
        No AI suggestions yet - user must click buttons to generate them.
        """
        categories = await self._initialize_comps_categories(ticker, step6_data, step7_data)
        
        return CompsAssumptionsResponse(
            session_id=f"step8_comps_{ticker}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            ticker=ticker,
            timestamp=datetime.now(),
            valuation_model=ValuationModel.COMPS,
            categories={k.value: v for k, v in categories.items()},
            all_categories_complete=False,
            all_validations_passed=True,
            ready_for_calculation=False,
            message="Comps assumptions initialized with historical trendlines. Click AI suggestion buttons to generate recommendations."
        )
    
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
            historical_data = step6_data.get("comps_historical_metrics", {})
            
            # Map metric names to data keys
            metric_mapping = {
                "P/E Multiple": "pe_multiple",
                "EV/EBITDA Multiple": "ev_ebitda_multiple",
                "P/B Multiple": "pb_multiple",
                "P/S Multiple": "ps_multiple",
                "Outlier Filter Threshold": "outlier_threshold"
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
        """Generate AI suggestions for a specific Comps assumption category"""
        if category not in self.COMPS_CATEGORIES:
            raise ValueError(f"Invalid Comps category: {category}")
        
        config = self.COMPS_CATEGORIES[category]
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
            message=f"AI suggestions generated for {config['name']} based on peer analysis and market multiples."
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
        """Generate AI suggestion for a single Comps assumption"""
        try:
            # Build prompt for AI engine
            prompt = self._build_comps_assumption_prompt(
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
            fallback_value = self._generate_deterministic_comps_fallback(
                metric=metric,
                category=category,
                validation_rules=validation_rules,
                step6_data=step6_data
            )
            return AISuggestion(
                metric=metric,
                suggested_value=fallback_value,
                reasoning=f"Calculated from peer averages (AI unavailable)",
                confidence_level="low",
                min_range=validation_rules.get("min", 0.0),
                max_range=validation_rules.get("max", 1.0),
                category=category
            )
    
    def _build_comps_assumption_prompt(
        self,
        ticker: str,
        metric: str,
        category: AssumptionCategory,
        description: str,
        validation_rules: Dict[str, float],
        step6_data: Dict[str, Any],
        step7_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build prompt for Comps assumption AI generation"""
        historical_trendline = None
        if step6_data:
            historical_trendline = self._build_historical_trendline_sync(metric, step6_data, step7_data)
        
        prompt = f"""Generate a forward-looking assumption for Comps valuation:

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
- Average: {historical_trendline.average:.2f}
- CAGR: {historical_trendline.cagr:.2%} if historical_trendline.cagr else 'N/A'
- Trend: {historical_trendline.trend_direction}
- Volatility: {historical_trendline.volatility}

Historical Values:
"""
            for point in historical_trendline.trend_points[-5:]:
                prompt += f"  - {point.year}: {point.value:.2f}\n"
        
        prompt += """
Provide a reasoned suggestion for this trading multiple considering:
1. Historical trends and momentum
2. Peer group median and mean multiples
3. Industry benchmarks
4. Market conditions and sector outlook
5. Company-specific factors vs peers

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
            historical_data = step6_data.get("comps_historical_metrics", {})
            metric_mapping = {
                "P/E Multiple": "pe_multiple",
                "EV/EBITDA Multiple": "ev_ebitda_multiple",
                "P/B Multiple": "pb_multiple",
                "P/S Multiple": "ps_multiple",
                "Outlier Filter Threshold": "outlier_threshold"
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
    
    def _generate_deterministic_comps_fallback(
        self,
        metric: str,
        category: AssumptionCategory,
        validation_rules: Dict[str, float],
        step6_data: Dict[str, Any]
    ) -> float:
        """Generate deterministic fallback value for Comps assumption"""
        try:
            historical_data = step6_data.get("comps_historical_metrics", {})
            
            # Use peer median for Comps multiples
            key = metric.lower().replace(" ", "_").replace("%", "").replace("/", "_")
            if key in historical_data:
                values = list(historical_data[key].values())
                if values:
                    # Use median for multiples (more robust than mean)
                    sorted_values = sorted(v for v in values if isinstance(v, (int, float)))
                    if sorted_values:
                        n = len(sorted_values)
                        median = sorted_values[n // 2] if n % 2 == 1 else (sorted_values[n // 2 - 1] + sorted_values[n // 2]) / 2
                        return max(validation_rules.get("min", 0), min(validation_rules.get("max", 100), median))
            
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
        for cat_config in self.COMPS_CATEGORIES.values():
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
        """Validate all Comps assumptions"""
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
        for config in self.COMPS_CATEGORIES.values():
            for assumption_def in config["assumptions"]:
                if assumption_def["metric"] == metric:
                    return assumption_def["validation"]
        return None
