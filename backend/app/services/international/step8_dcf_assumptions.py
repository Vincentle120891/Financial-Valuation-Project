"""Step 8: DCF Assumption & AI Suggestion Studio

This is the critical "Brain" of the DCF workflow, bridging historical reality with future valuation.

Purpose: DCF-specific assumption generation and AI suggestions
- Revenue Drivers (Volume Growth, Price Increase) - multi-year
- Cost & Margins (COGS %, SG&A %, Tax Rate)
- Working Capital (AR Days, Inventory Days, AP Days)
- WACC Components (Risk-Free Rate, Market Risk Premium, Country Risk Premium, Cost of Debt, D/E Ratio)
- Terminal Value (Terminal Growth Rate, Terminal EBITDA Multiple)

AI Usage in Step 8 DCF:
- AI provides suggestions for all DCF assumptions based on historical trends, peer analysis, and market conditions
- Users can accept AI suggestions or manually override them
- All AI suggestions include rationale and confidence scores
- Key drivers: Revenue Growth, Margins, WACC components, Terminal Value

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
from .statistical_utils import generate_historical_statistics, extract_numeric_values

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

    # Enhanced statistical context from Step 6/7 historical data
    median: Optional[float] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    standard_deviation: Optional[float] = None
    average_yoy_growth: Optional[float] = None
    yoy_growth_details: Optional[List[Dict[str, Any]]] = None
    year_range: Optional[str] = None
    periods: Optional[int] = None
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

class DCFAssumptionsResponse(BaseModel):
    """Complete Step 8 DCF response with all categories"""
    session_id: str
    ticker: str
    timestamp: datetime
    valuation_model: ValuationModel = ValuationModel.DCF
    categories: Dict[str, AssumptionCategoryResponse]

    # Summary and validation
    all_categories_complete: bool = False
    all_validations_passed: bool = True
    total_validation_errors: List[str] = []
    ready_for_calculation: bool = False

    # What-if preview
    sensitivity_preview: Optional[Dict[str, Any]] = None
    message: str = ""


class DCFStep8Processor:
    """
    Step 8: The DCF Assumption Studio

    Features:
    1. Context-Aware Historical Trendlines (3-5 years from Step 6)
    2. Modular AI Suggestion Engines (5 Button Strategy)
    3. Smart Validation & Guardrails
    4. What-If Preview (Mini-Step 9 sensitivity)

    Output: DCFAssumptionsResponse with complete DCF assumption set
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

    def __init__(self):
        self.ai_fallback = AIFallbackEngine()

    async def initialize_assumptions(
        self,
        ticker: str,
        step6_data: Dict[str, Any],
        step7_data: Optional[Dict[str, Any]] = None
    ) -> DCFAssumptionsResponse:
        """
        Initialize Step 8 DCF with historical trendlines from Step 6.
        No AI suggestions yet - user must click buttons to generate them.
        """
        categories = await self._initialize_dcf_categories(ticker, step6_data, step7_data)

        return DCFAssumptionsResponse(
            session_id=f"step8_dcf_{ticker}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            ticker=ticker,
            timestamp=datetime.now(),
            valuation_model=ValuationModel.DCF,
            categories={k.value: v for k, v in categories.items()},
            all_categories_complete=False,
            all_validations_passed=True,
            ready_for_calculation=False,
            message="DCF assumptions initialized with historical trendlines. Click AI suggestion buttons to generate recommendations for each category."
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
            historical_data = step6_data.get("dcf_historical_metrics", {})

            # Map metric names to data keys
            metric_mapping = {
                "Revenue Volume Growth": "revenue",
                "Revenue Price Increase": "revenue",
                "COGS % of Revenue": "cogs",
                "SG&A % of Revenue": "sga",
                "Effective Tax Rate": "tax_expense",
                "Accounts Receivable Days": "accounts_receivable",
                "Inventory Days": "inventory",
                "Accounts Payable Days": "accounts_payable",
                "Risk-Free Rate": "risk_free_rate",
                "Market Risk Premium": "market_risk_premium",
                "Country Risk Premium": "country_risk_premium",
                "Pre-Tax Cost of Debt": "cost_of_debt",
                "Target Debt-to-Equity": "debt_to_equity",
                "Terminal Growth Rate": "terminal_growth",
                "Terminal EBITDA Multiple": "ebitda_multiple"
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

            # Build trend points
            trend_points = []
            numeric_values = []
            for year, value in sorted(values.items()):
                if isinstance(year, str) and year.isdigit():
                    year = int(year)
                if isinstance(value, (int, float)) and value is not None:
                    trend_points.append(HistoricalTrendPoint(year=int(year), value=float(value)))
                    numeric_values.append(float(value))

            if not trend_points:
                return None

            # Calculate statistics
            average = sum(numeric_values) / len(numeric_values) if numeric_values else 0.0

            # Calculate CAGR if we have multiple years
            cagr = None
            if len(numeric_values) >= 2:
                first_value = numeric_values[0]
                last_value = numeric_values[-1]
                n_years = len(numeric_values) - 1
                if first_value > 0 and n_years > 0:
                    cagr = ((last_value / first_value) ** (1 / n_years)) - 1

            # Determine trend direction
            trend_direction = "stable"
            if len(numeric_values) >= 2:
                if numeric_values[-1] > numeric_values[0] * 1.1:
                    trend_direction = "increasing"
                elif numeric_values[-1] < numeric_values[0] * 0.9:
                    trend_direction = "decreasing"

            # Calculate volatility
            volatility = "low"
            if len(numeric_values) >= 2:
                avg_val = average
                variance = sum((v - avg_val) ** 2 for v in numeric_values) / len(numeric_values)
                std_dev = variance ** 0.5
                cv = std_dev / abs(avg_val) if avg_val != 0 else 0
                if cv > 0.3:
                    volatility = "high"
                elif cv > 0.15:
                    volatility = "medium"

            return HistoricalTrendline(
                metric=metric,
                trend_points=trend_points,
                average=average,
                cagr=cagr,
                trend_direction=trend_direction,
                volatility=volatility
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
        """Generate AI suggestions for a specific DCF assumption category"""
        if category not in self.DCF_CATEGORIES:
            raise ValueError(f"Invalid DCF category: {category}")

        config = self.DCF_CATEGORIES[category]
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
            message=f"AI suggestions generated for {config['name']} based on historical trends, peer analysis, and market conditions."
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
        """Generate AI suggestion for a single DCF assumption"""
        try:
            # Build prompt for AI engine
            prompt = self._build_dcf_assumption_prompt(
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
            fallback_value = self._generate_deterministic_dcf_fallback(
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

    def _build_dcf_assumption_prompt(
        self,
        ticker: str,
        metric: str,
        category: AssumptionCategory,
        description: str,
        validation_rules: Dict[str, float],
        step6_data: Dict[str, Any],
        step7_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build prompt for DCF assumption AI generation

        Now includes comprehensive statistical context from Step 6/7 historical data:
        - CAGR, Average, Median, Min/Max
        - Standard Deviation (Volatility)
        - Year-over-Year Growth rates with details
        """
        historical_trendline = None
        if step6_data:
            historical_trendline = self._build_historical_trendline_sync(metric, step6_data, step7_data)

        prompt = f"""Generate a forward-looking assumption for DCF valuation:

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
            # Enhanced prompt with comprehensive statistics
            prompt += f"""Historical Context ({historical_trendline.year_range or 'N/A'}):
"""
            # Core metrics
            prompt += f"- Latest Value: {historical_trendline.latest_value:.2%}\n" if historical_trendline.latest_value else ""
            prompt += f"- Average: {historical_trendline.average:.2%}\n"
            prompt += f"- Median: {historical_trendline.median:.2%}\n" if historical_trendline.median else ""
            prompt += f"- CAGR: {historical_trendline.cagr:.2%}\n" if historical_trendline.cagr else "- CAGR: N/A\n"

            # Range and volatility
            if historical_trendline.min_value is not None and historical_trendline.max_value is not None:
                prompt += f"- Range: {historical_trendline.min_value:.2%} to {historical_trendline.max_value:.2%}\n"
            prompt += f"- Trend Direction: {historical_trendline.trend_direction}\n"
            prompt += f"- Volatility (Std Dev): {historical_trendline.standard_deviation:.4f}" if historical_trendline.standard_deviation else "- Volatility: N/A"
            if historical_trendline.volatility:
                prompt += f" ({historical_trendline.volatility})\n"
            else:
                prompt += "\n"

            # YoY growth analysis
            if historical_trendline.average_yoy_growth is not None:
                prompt += f"- Average YoY Growth: {historical_trendline.average_yoy_growth:.2%}\n"

            # Detailed YoY breakdown if available
            if historical_trendline.yoy_growth_details:
                prompt += "\nYear-over-Year Growth Breakdown:\n"
                for yoy in historical_trendline.yoy_growth_details[-5:]:
                    prompt += f"  - {yoy['year']}: {yoy['growth_rate']:.2%} (from {yoy['previous_value']:.2%} to {yoy['current_value']:.2%})\n"

            # Historical values timeline
            prompt += "\nHistorical Values Timeline:\n"
            for point in historical_trendline.trend_points[-5:]:
                prompt += f"  - {point.year}: {point.value:.2%}\n"

        prompt += """
Provide a reasoned suggestion for this forward-looking assumption considering:
1. Historical trends and momentum (CAGR, average, recent performance)
2. Industry benchmarks and peer comparisons
3. Current market conditions
4. Company-specific factors
5. Volatility and risk profile

Return JSON with: value (decimal), reasoning (string), confidence (low/medium/high)"""

        return prompt

    def _build_historical_trendline_sync(
        self,
        metric: str,
        step6_data: Dict[str, Any],
        step7_data: Optional[Dict[str, Any]] = None
    ) -> Optional[HistoricalTrendline]:
        """Synchronous version of _build_historical_trendline for prompt building

        Now uses statistical_utils to calculate comprehensive statistics including:
        - CAGR, Average, Median, Min/Max
        - Standard Deviation (Volatility)
        - Year-over-Year Growth rates
        """
        try:
            historical_data = step6_data.get("dcf_historical_metrics", {})
            metric_mapping = {
                "Revenue Volume Growth": "revenue",
                "Revenue Price Increase": "revenue",
                "COGS % of Revenue": "cogs",
                "SG&A % of Revenue": "sga",
                "Effective Tax Rate": "tax_expense",
            }
            data_key = metric_mapping.get(metric, metric.lower().replace(" ", "_").replace("%", "").replace("/", "_"))
            values = historical_data.get(data_key, {})

            if not values:
                return None

            # Convert raw values to DataField format for statistical analysis
            from app.schemas.unified_schema import DataField
            data_fields = []
            for year, value in sorted(values.items()):
                if isinstance(year, str) and year.isdigit():
                    year = int(year)
                if isinstance(value, (int, float)) and value is not None:
                    data_fields.append(DataField(
                        label=f"{metric} - {year}",
                        value=float(value),
                        unit="%" if "%" in metric else "USD",
                        year=int(year),
                        source="Step 6 Historical",
                        confidence=1.0
                    ))

            if not data_fields:
                return None

            # Use statistical utilities to generate comprehensive statistics
            stats = generate_historical_statistics(data_fields, metric)

            if stats.get("status") == "insufficient_data":
                return None

            # Build trend points from raw values
            trend_points = []
            numeric_values = []
            for year, value in sorted(values.items()):
                if isinstance(year, str) and year.isdigit():
                    year = int(year)
                if isinstance(value, (int, float)) and value is not None:
                    trend_points.append(HistoricalTrendPoint(year=int(year), value=float(value)))
                    numeric_values.append(float(value))

            if not trend_points:
                return None

            # Calculate basic metrics (already done in stats, but keeping for backward compatibility)
            average = sum(numeric_values) / len(numeric_values) if numeric_values else 0.0
            cagr = stats.get("cagr")

            # Determine trend direction
            trend_direction = "stable"
            if len(numeric_values) >= 2:
                if numeric_values[-1] > numeric_values[0] * 1.1:
                    trend_direction = "increasing"
                elif numeric_values[-1] < numeric_values[0] * 0.9:
                    trend_direction = "decreasing"

            # Map volatility from standard deviation
            volatility = "low"
            std_dev = stats.get("volatility")
            if std_dev is not None:
                avg_val = average
                cv = std_dev / abs(avg_val) if avg_val != 0 else 0
                if cv > 0.3:
                    volatility = "high"
                elif cv > 0.15:
                    volatility = "medium"

            # Return enhanced HistoricalTrendline with all statistical context
            return HistoricalTrendline(
                metric=metric,
                trend_points=trend_points,
                average=average,
                cagr=cagr,
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
            logger.warning(f"Error building historical trendline for {metric}: {e}")
            return None

    def _generate_deterministic_dcf_fallback(
        self,
        metric: str,
        category: AssumptionCategory,
        validation_rules: Dict[str, float],
        step6_data: Dict[str, Any]
    ) -> float:
        """Generate deterministic fallback value for DCF assumption"""
        try:
            historical_data = step6_data.get("dcf_historical_metrics", {})

            # Metric-specific fallback logic
            if "Growth" in metric or "Increase" in metric:
                # Use historical average growth
                if "revenue" in historical_data:
                    rev_values = list(historical_data["revenue"].values())
                    if len(rev_values) >= 2:
                        growth_rates = []
                        for i in range(1, len(rev_values)):
                            if rev_values[i-1] > 0:
                                growth_rates.append((rev_values[i] - rev_values[i-1]) / rev_values[i-1])
                        if growth_rates:
                            avg_growth = sum(growth_rates) / len(growth_rates)
                            return max(validation_rules.get("min", 0), min(validation_rules.get("max", 1), avg_growth))

            elif "%" in metric or "Rate" in metric:
                # Use historical average percentage
                key = metric.lower().replace(" ", "_").replace("%", "").replace("/", "_")
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
        for cat_config in self.DCF_CATEGORIES.values():
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
                warning_message = f"Value {user_value} is outside recommended range [{validation_rules.get('warning_min')}, {validation_rules.get('warning_max')}]"

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
        """Validate all DCF assumptions"""
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
        for config in self.DCF_CATEGORIES.values():
            for assumption_def in config["assumptions"]:
                if assumption_def["metric"] == metric:
                    return assumption_def["validation"]
        return None