"""
Step 8 Unified Schema Transformer - Vietnamese Market

This module transforms Vietnamese market Step 8 outputs from method-specific
schemas to the unified schema format (UnifiedStep8Response).

Transformation Strategy:
- Map vn_AIAssumptionsOutput → UnifiedStep8Response
- Convert assumption items to AssumptionInput format with historical trendlines
- Preserve ALL original data and calculations (Model Integrity)

Key Differences:
- Vietnamese Legacy: List of vn_AIAssumptionItem with parameter_name, suggested_value
- Unified: Dict of AssumptionCategoryResponse containing AssumptionInput list with
           historical trendlines, AI suggestions, and override capabilities

IMPORTANT: This transformer preserves ALL original data and calculations.
It only changes the wrapping structure to match the unified contract.
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from app.api.schemas.unified_step_schemas import (
    UnifiedStep8Response,
    AssumptionCategoryResponse,
    AssumptionInput,
    AISuggestion,
    HistoricalTrendline,
    HistoricalTrendPoint,
    AssumptionCategoryType,
    OverrideStatus,
    DataField as UnifiedDataField,
    DataStatus as UnifiedDataStatus,
)

from app.services.vietnamese.vn_step8_assumptions_processor import (
    vn_AIAssumptionsOutput,
    vn_AIAssumptionItem,
)

logger = logging.getLogger(__name__)


class VNStep8UnifiedTransformer:
    """
    Transforms Vietnamese Step 8 processor outputs to unified schema.

    This is a pure transformation layer - no business logic modification.
    All calculations and data values are preserved exactly as-is.
    """

    # Mapping from Vietnamese parameter names to unified categories
    PARAMETER_TO_CATEGORY_MAP = {
        # Revenue Drivers
        "revenue_growth_year_1": AssumptionCategoryType.REVENUE_DRIVERS,
        "revenue_growth_year_2": AssumptionCategoryType.REVENUE_DRIVERS,
        "revenue_growth_year_3": AssumptionCategoryType.REVENUE_DRIVERS,
        "revenue_growth_year_4": AssumptionCategoryType.REVENUE_DRIVERS,
        "revenue_growth_year_5": AssumptionCategoryType.REVENUE_DRIVERS,
        "volume_growth": AssumptionCategoryType.REVENUE_DRIVERS,
        "price_growth": AssumptionCategoryType.REVENUE_DRIVERS,

        # Cost & Margins
        "ebitda_margin_year_1": AssumptionCategoryType.COST_MARGINS,
        "ebitda_margin_year_2": AssumptionCategoryType.COST_MARGINS,
        "ebitda_margin_year_3": AssumptionCategoryType.COST_MARGINS,
        "operating_margin": AssumptionCategoryType.COST_MARGINS,
        "net_margin": AssumptionCategoryType.COST_MARGINS,
        "tax_rate": AssumptionCategoryType.COST_MARGINS,
        "cogs_pct_revenue": AssumptionCategoryType.COST_MARGINS,

        # Working Capital
        "ar_days": AssumptionCategoryType.WORKING_CAPITAL,
        "inventory_days": AssumptionCategoryType.WORKING_CAPITAL,
        "ap_days": AssumptionCategoryType.WORKING_CAPITAL,
        "working_capital_ratio": AssumptionCategoryType.WORKING_CAPITAL,

        # WACC Components
        "risk_free_rate": AssumptionCategoryType.WACC_COMPONENTS,
        "market_risk_premium": AssumptionCategoryType.WACC_COMPONENTS,
        "beta": AssumptionCategoryType.WACC_COMPONENTS,
        "cost_of_debt": AssumptionCategoryType.WACC_COMPONENTS,
        "wacc": AssumptionCategoryType.WACC_COMPONENTS,
        "country_risk_premium": AssumptionCategoryType.WACC_COMPONENTS,

        # Terminal Value
        "terminal_growth_rate": AssumptionCategoryType.TERMINAL_VALUE,
        "terminal_ebitda_multiple": AssumptionCategoryType.TERMINAL_VALUE,

        # DuPont Targets
        "roe_target": AssumptionCategoryType.DUPONT_TARGETS,
        "roa_target": AssumptionCategoryType.DUPONT_TARGETS,
        "asset_turnover_target": AssumptionCategoryType.DUPONT_TARGETS,
        "equity_multiplier_target": AssumptionCategoryType.DUPONT_TARGETS,

        # Comps Multiples
        "ev_ebitda_multiple": AssumptionCategoryType.COMPS_MULTIPLES,
        "pe_ratio": AssumptionCategoryType.COMPS_MULTIPLES,
        "pb_ratio": AssumptionCategoryType.COMPS_MULTIPLES,
        "ev_sales_multiple": AssumptionCategoryType.COMPS_MULTIPLES,
    }

    # Category display names
    CATEGORY_NAMES = {
        AssumptionCategoryType.REVENUE_DRIVERS: "Revenue Drivers",
        AssumptionCategoryType.COST_MARGINS: "Cost & Margins",
        AssumptionCategoryType.WORKING_CAPITAL: "Working Capital",
        AssumptionCategoryType.WACC_COMPONENTS: "WACC Components",
        AssumptionCategoryType.TERMINAL_VALUE: "Terminal Value",
        AssumptionCategoryType.DUPONT_TARGETS: "DuPont Targets",
        AssumptionCategoryType.COMPS_MULTIPLES: "Comps Multiples",
    }

    @staticmethod
    def determine_unit(parameter_name: str, default_unit: str) -> str:
        """Determine appropriate unit for parameter"""
        if any(x in parameter_name.lower() for x in ["growth", "margin", "rate", "ratio", "pct"]):
            return "%"
        if any(x in parameter_name.lower() for x in ["days", "period"]):
            return "days"
        if any(x in parameter_name.lower() for x in ["multiple", "x"]):
            return "x"
        return default_unit

    @staticmethod
    def create_historical_trendline(
        parameter_name: str,
        historical_financials: Optional[Dict[str, Any]]
    ) -> Optional[HistoricalTrendline]:
        """
        Create historical trendline from financial data.

        Args:
            parameter_name: Name of the parameter
            historical_financials: Historical financial data dictionary

        Returns:
            HistoricalTrendline or None if no data available
        """
        if not historical_financials:
            return None

        # Try to extract historical values for this parameter
        # This is simplified - actual implementation would need to map parameter to financial field
        trend_points = []

        # Look for historical data patterns
        for year_offset in range(5, 0, -1):
            year_key = f"{parameter_name}_year_{-year_offset}"
            if year_key in historical_financials:
                value = historical_financials[year_key]
                if value is not None:
                    trend_points.append(HistoricalTrendPoint(
                        year=datetime.now().year - year_offset,
                        value=float(value),
                        label=f"FY{datetime.now().year - year_offset}"
                    ))

        if not trend_points:
            return None

        # Calculate statistics
        values = [tp.value for tp in trend_points]
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
            variance = sum((v - avg_value) ** 2 for v in values) / len(values)
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

        # Calculate CAGR if we have enough data
        cagr = None
        if len(trend_points) >= 2:
            first_value = trend_points[0].value
            last_value = trend_points[-1].value
            years = trend_points[-1].year - trend_points[0].year
            if years > 0 and first_value != 0:
                cagr = ((last_value / first_value) ** (1 / years) - 1) * 100

        return HistoricalTrendline(
            metric=parameter_name,
            trend_points=trend_points,
            average=round(avg_value, 2),
            cagr=round(cagr, 2) if cagr else None,
            trend_direction=trend_direction,
            volatility=volatility
        )

    @staticmethod
    def create_ai_suggestion(
        assumption_item: vn_AIAssumptionItem,
        category: AssumptionCategoryType
    ) -> AISuggestion:
        """
        Convert Vietnamese AI assumption item to unified AISuggestion.

        Args:
            assumption_item: Vietnamese AI assumption
            category: Assumption category

        Returns:
            AISuggestion in unified format
        """
        # Convert confidence score from 0-1 to low/medium/high
        confidence = assumption_item.confidence_score
        if confidence >= 0.75:
            confidence_level = "high"
        elif confidence >= 0.5:
            confidence_level = "medium"
        else:
            confidence_level = "low"

        return AISuggestion(
            metric=assumption_item.parameter_name,
            suggested_value=float(assumption_item.suggested_value),
            reasoning=assumption_item.rationale,
            confidence_level=confidence_level,
            min_range=float(assumption_item.min_reasonable) if assumption_item.min_reasonable else 0.0,
            max_range=float(assumption_item.max_reasonable) if assumption_item.max_reasonable else 0.0,
            category=category
        )

    @staticmethod
    def map_parameter_to_category(parameter_name: str) -> AssumptionCategoryType:
        """Map parameter name to assumption category"""
        return VNStep8UnifiedTransformer.PARAMETER_TO_CATEGORY_MAP.get(
            parameter_name,
            AssumptionCategoryType.COST_MARGINS  # Default fallback
        )

    @staticmethod
    def group_assumptions_by_category(
        assumptions: List[vn_AIAssumptionItem],
        historical_financials: Optional[Dict[str, Any]] = None
    ) -> Dict[str, AssumptionCategoryResponse]:
        """
        Group Vietnamese assumptions by category and convert to unified format.

        Args:
            assumptions: List of Vietnamese AI assumptions
            historical_financials: Optional historical data for trendlines

        Returns:
            Dictionary of category key -> AssumptionCategoryResponse
        """
        categories_dict: Dict[str, AssumptionCategoryResponse] = {}

        for assumption in assumptions:
            # Determine category
            category = VNStep8UnifiedTransformer.map_parameter_to_category(
                assumption.parameter_name
            )
            category_key = category.value

            # Create historical trendline if data available
            trendline = VNStep8UnifiedTransformer.create_historical_trendline(
                assumption.parameter_name,
                historical_financials
            )

            # Create AI suggestion
            ai_suggestion = VNStep8UnifiedTransformer.create_ai_suggestion(
                assumption,
                category
            )

            # Create assumption input
            assumption_input = AssumptionInput(
                metric=assumption.parameter_name,
                category=category,
                description=assumption.rationale,
                unit=VNStep8UnifiedTransformer.determine_unit(
                    assumption.parameter_name,
                    assumption.unit
                ),
                historical_trendline=trendline,
                ai_suggestion=ai_suggestion,
                user_value=None,  # Will be set by user interaction
                final_value=float(assumption.suggested_value),
                status=OverrideStatus.DEFAULT,
                is_valid=True,
                validation_message=None,
                warning_message=None,
                is_multi_year=False,
                year_values={}
            )

            # Add to category
            if category_key not in categories_dict:
                categories_dict[category_key] = AssumptionCategoryResponse(
                    category=category,
                    category_name=VNStep8UnifiedTransformer.CATEGORY_NAMES.get(
                        category, category.value
                    ),
                    assumptions=[],
                    ai_generated=True,
                    generation_timestamp=datetime.utcnow(),
                    message=f"AI-generated assumptions for {VNStep8UnifiedTransformer.CATEGORY_NAMES.get(category, category.value)}"
                )

            categories_dict[category_key].assumptions.append(assumption_input)

        return categories_dict

    @staticmethod
    def validate_assumptions(
        categories: Dict[str, AssumptionCategoryResponse]
    ) -> tuple[bool, List[str]]:
        """
        Validate all assumptions in categories.

        Returns:
            Tuple of (all_valid, list_of_errors)
        """
        errors = []

        for category_key, category_response in categories.items():
            for assumption in category_response.assumptions:
                # Check if value is within reasonable range
                if assumption.ai_suggestion:
                    value = assumption.final_value
                    min_val = assumption.ai_suggestion.min_range
                    max_val = assumption.ai_suggestion.max_range

                    if value is not None:
                        if value < min_val * 0.5 or value > max_val * 1.5:
                            errors.append(
                                f"{assumption.metric}: Value {value} is outside reasonable range "
                                f"[{min_val}, {max_val}]"
                            )
                            assumption.is_valid = False
                            assumption.validation_message = "Value outside reasonable range"

        return len(errors) == 0, errors

    def transform(
        self,
        vn_output: vn_AIAssumptionsOutput,
        session_id: str,
        method: str,
        market: str,
        ticker: str,
        operation_type: str = "generate_ai",
        targeted_category: Optional[AssumptionCategoryType] = None
    ) -> UnifiedStep8Response:
        """
        Transform Vietnamese Step 8 output to unified schema.

        Args:
            vn_output: Output from vn_Step8AssumptionsProcessor
            session_id: Session identifier
            method: Valuation method (DCF, DUPONT, COMPS)
            market: Market type ("vietnam")
            ticker: Company ticker
            operation_type: Type of operation (initialize, generate_ai, apply_override)
            targeted_category: Specific category if operation was targeted

        Returns:
            UnifiedStep8Response conforming to unified schema
        """
        logger.info(f"Transforming Vietnamese Step 8 data for {ticker} ({method})")

        # Extract historical financials if available
        # Note: In real implementation, this would come from session cache or input
        historical_financials = None

        # Group assumptions by category
        categories = self.group_assumptions_by_category(
            assumptions=vn_output.assumptions,
            historical_financials=historical_financials
        )

        # Validate assumptions
        all_valid, validation_errors = self.validate_assumptions(categories)

        # Check if all categories are complete
        expected_categories = self._get_expected_categories_for_method(method.upper())
        all_complete = all(cat in categories for cat in expected_categories)

        # Build unified response
        response = UnifiedStep8Response(
            status=vn_output.status,
            session_id=session_id,
            method=method.upper(),
            market=market,
            operation_type=operation_type,
            ticker=ticker,
            valuation_model=method.upper(),
            categories=categories,
            targeted_category=targeted_category,
            all_categories_complete=all_complete,
            all_validations_passed=all_valid,
            total_validation_errors=validation_errors,
            ready_for_calculation=all_valid and all_complete,
            sensitivity_preview=None,  # Would be calculated in advanced implementation
            message=f"Generated {len(vn_output.assumptions)} AI assumptions for {ticker}. "
                   f"Sector: {vn_output.sector_analysis.get('sector', 'N/A')}. "
                   f"Warnings: {len(vn_output.warnings)}"
        )

        logger.info(f"Successfully transformed Vietnamese Step 8 data for {ticker}")
        return response

    def _get_expected_categories_for_method(self, method: str) -> List[str]:
        """Get expected categories for a valuation method"""
        if method == "DCF":
            return [
                AssumptionCategoryType.REVENUE_DRIVERS.value,
                AssumptionCategoryType.COST_MARGINS.value,
                AssumptionCategoryType.WORKING_CAPITAL.value,
                AssumptionCategoryType.WACC_COMPONENTS.value,
                AssumptionCategoryType.TERMINAL_VALUE.value,
            ]
        elif method == "DUPONT":
            return [
                AssumptionCategoryType.DUPONT_TARGETS.value,
                AssumptionCategoryType.COST_MARGINS.value,
            ]
        elif method == "COMPS":
            return [
                AssumptionCategoryType.COMPS_MULTIPLES.value,
                AssumptionCategoryType.COST_MARGINS.value,
            ]
        return []